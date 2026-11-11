from __future__ import annotations

import gc
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch.utils.data import DataLoader

from .config import EvalConfig, ModelConfig, TrainConfig
from .data import CacheBundle, RegimeWindowDataset
from .evaluate import evaluate_model
from .losses import (
    alignment_loss,
    auxiliary_bce_loss,
    gate_smoothness_loss,
    moe_load_balancing_loss,
    masked_mae,
    masked_mse_loss,
    physics_force_loss,
)
from .model import RegimeAwareForecaster
from .utils import ensure_dir, save_json, seed_everything, to_device


def _safe_print(message: str) -> None:
    try:
        print(message)
    except OSError:
        return


def snapshot_model_state(model: torch.nn.Module) -> dict[str, torch.Tensor]:
    return {name: tensor.detach().cpu().clone() for name, tensor in model.state_dict().items()}


def _build_dataloader(
    dataset: RegimeWindowDataset,
    batch_size: int,
    shuffle: bool,
    num_workers: int,
) -> DataLoader:
    return DataLoader(dataset, batch_size=batch_size, shuffle=shuffle, num_workers=num_workers, pin_memory=True)


def _compute_loss(
    batch: dict[str, torch.Tensor],
    pred: torch.Tensor,
    gate_prob: torch.Tensor | None,
    aux: dict[str, torch.Tensor],
    bundle: CacheBundle,
    primary_weights: torch.Tensor,
    pitch_force_weights: torch.Tensor | None,
    wake_pos_weight: torch.Tensor | None,
    train_config: TrainConfig,
) -> tuple[torch.Tensor, dict[str, float]]:
    loss = masked_mse_loss(pred, batch["target"], batch["target_mask"])
    weights = train_config.effective_loss_weights()
    breakdown = {"pred": float(loss.detach().item())}

    if gate_prob is not None:
        if weights["align"] > 0.0:
            align = alignment_loss(
                aux["gate_logits"],
                batch["regime_primary"],
                batch["regime_primary_valid"],
                primary_weights,
                bundle.metadata["primary_num_classes"],
            )
            loss = loss + weights["align"] * align
            breakdown["align"] = float(align.detach().item())

        if weights["physics_force"] > 0.0 and bundle.metadata.get("dataset") == "wtb":
            force = physics_force_loss(
                aux["gate_logits"],
                batch["regime_primary"],
                batch["regime_primary_valid"],
                mppt_expert_index=1,
                pitch_expert_index=2,
                class_weights=pitch_force_weights,
            )
            loss = loss + weights["physics_force"] * force
            breakdown["physics_force"] = float(force.detach().item())

        wake_expert_index = bundle.metadata.get("wake_expert_index")
        if weights["aux"] > 0.0 and wake_expert_index is not None:
            aux_loss = auxiliary_bce_loss(
                aux["gate_logits"][..., wake_expert_index],
                batch["regime_aux"],
                batch["regime_aux_valid"],
                pos_weight=wake_pos_weight,
            )
            loss = loss + weights["aux"] * aux_loss
            breakdown["aux"] = float(aux_loss.detach().item())

        if weights["smooth"] > 0.0:
            smooth = gate_smoothness_loss(gate_prob, batch["edge_index_hist"][:, -1], batch["edge_weight_hist"][:, -1])
            loss = loss + weights["smooth"] * smooth
            breakdown["smooth"] = float(smooth.detach().item())

        if weights["balance"] > 0.0:
            balanced_gate = gate_prob[..., : bundle.metadata["primary_num_classes"]]
            balance = moe_load_balancing_loss(
                balanced_gate,
                top_k=train_config.balance_top_k,
                sample_mask=batch["regime_primary_valid"],
            )
            loss = loss + weights["balance"] * balance
            breakdown["balance"] = float(balance.detach().item())

    breakdown["total"] = float(loss.detach().item())
    return loss, breakdown


def _validate(
    model: RegimeAwareForecaster,
    loader: DataLoader,
    bundle: CacheBundle,
    device: torch.device,
    primary_weights: torch.Tensor,
    pitch_force_weights: torch.Tensor | None,
    wake_pos_weight: torch.Tensor | None,
    train_config: TrainConfig,
) -> dict[str, float]:
    model.eval()
    total_loss = 0.0
    total_mae = 0.0
    total_rmse = 0.0
    total_batches = 0
    with torch.no_grad():
        for batch_index, batch in enumerate(loader):
            if train_config.limit_val_batches is not None and batch_index >= train_config.limit_val_batches:
                break
            batch = to_device(batch, device)
            pred, gate_prob, aux = model(
                batch["x_hist"],
                batch["edge_index_hist"],
                batch["edge_weight_hist"],
                batch["feature_mask_hist"],
                batch["anchor_physics"],
            )
            loss, _ = _compute_loss(
                batch,
                pred,
                gate_prob,
                aux,
                bundle,
                primary_weights,
                pitch_force_weights,
                wake_pos_weight,
                train_config,
            )
            total_loss += float(loss.item())
            total_mae += float(masked_mae(pred, batch["target"], batch["target_mask"]).item())
            total_rmse += float(masked_mse_loss(pred, batch["target"], batch["target_mask"]).sqrt().item())
            total_batches += 1
    total_batches = max(total_batches, 1)
    return {
        "loss": total_loss / total_batches,
        "mae": total_mae / total_batches,
        "rmse": total_rmse / total_batches,
    }


def train_model(
    bundle: CacheBundle,
    output_root: Path | str,
    model_config: ModelConfig,
    train_config: TrainConfig,
    eval_config: EvalConfig,
) -> dict[str, Any]:
    output_root = ensure_dir(output_root)
    seed_everything(train_config.seed)
    train_start = time.perf_counter()
    hist_len = bundle.metadata["hist_len"]
    pred_len = bundle.metadata["pred_len"]
    train_dataset = RegimeWindowDataset(bundle, "train", hist_len, pred_len)
    val_dataset = RegimeWindowDataset(bundle, "val", hist_len, pred_len)
    test_dataset = RegimeWindowDataset(bundle, "test", hist_len, pred_len)

    train_loader = _build_dataloader(train_dataset, train_config.batch_size, True, train_config.num_workers)
    val_loader = _build_dataloader(val_dataset, train_config.batch_size, False, train_config.num_workers)
    test_loader = _build_dataloader(test_dataset, train_config.batch_size, False, train_config.num_workers)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    tuned_model_config = ModelConfig(
        hidden_dim=model_config.hidden_dim,
        num_experts=model_config.num_experts,
        dropout=model_config.dropout,
        tau=model_config.tau,
        gate_hidden_dim=model_config.gate_hidden_dim,
        primary_num_classes=bundle.metadata["primary_num_classes"],
        gate_physics_dim=bundle.physics.shape[-1],
    )
    model = RegimeAwareForecaster(
        feature_dim=bundle.features.shape[-1],
        pred_len=pred_len,
        mode=train_config.mode,
        config=tuned_model_config,
    ).to(device)
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=train_config.learning_rate,
        weight_decay=train_config.weight_decay,
    )
    scaler = torch.amp.GradScaler(device.type, enabled=device.type == "cuda")
    primary_weights = torch.tensor(bundle.metadata["primary_class_weights"], dtype=torch.float32, device=device)
    pitch_force_weights = None
    if "pitch_force_weights" in bundle.metadata:
        pitch_force_weights = torch.tensor(bundle.metadata["pitch_force_weights"], dtype=torch.float32, device=device)
    elif bundle.metadata.get("dataset") == "wtb":
        pitch_valid = ((bundle.regime_primary == 1) | (bundle.regime_primary == 2)).astype(bool)
        pitch_labels = (bundle.regime_primary == 2).astype("int64")
        if np.any(pitch_valid):
            pitch_counts = np.bincount(pitch_labels[pitch_valid].reshape(-1), minlength=2).astype("float32")
            pitch_counts = np.where(pitch_counts > 0.0, pitch_counts, 1.0)
            pitch_weights = pitch_counts.sum() / (2.0 * pitch_counts)
            pitch_weights = pitch_weights / pitch_weights.mean()
            pitch_force_weights = torch.tensor(pitch_weights, dtype=torch.float32, device=device)
    wake_pos_weight = None
    if "wake_pos_weight" in bundle.metadata:
        wake_pos_weight = torch.tensor(bundle.metadata["wake_pos_weight"], dtype=torch.float32, device=device)

    best_state = None
    best_val_rmse = float("inf")
    best_epoch = -1
    patience_counter = 0
    history: list[dict[str, Any]] = []

    for epoch in range(train_config.epochs):
        model.train()
        epoch_start = time.time()
        running_loss = 0.0
        running_batches = 0
        for batch_index, batch in enumerate(train_loader):
            if train_config.limit_train_batches is not None and batch_index >= train_config.limit_train_batches:
                break
            batch = to_device(batch, device)
            optimizer.zero_grad(set_to_none=True)
            with torch.amp.autocast(device_type=device.type, enabled=device.type == "cuda"):
                pred, gate_prob, aux = model(
                    batch["x_hist"],
                    batch["edge_index_hist"],
                    batch["edge_weight_hist"],
                    batch["feature_mask_hist"],
                    batch["anchor_physics"],
                )
                loss, breakdown = _compute_loss(
                    batch,
                    pred,
                    gate_prob,
                    aux,
                    bundle,
                    primary_weights,
                    pitch_force_weights,
                    wake_pos_weight,
                    train_config,
                )
            scaler.scale(loss).backward()
            scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(model.parameters(), train_config.grad_clip_norm)
            scaler.step(optimizer)
            scaler.update()
            running_loss += float(loss.item())
            running_batches += 1
            if (batch_index + 1) % train_config.log_every == 0:
                pieces = [f"loss={loss.item():.4f}", f"pred={breakdown.get('pred', 0.0):.4f}"]
                for key in ("align", "physics_force", "aux", "balance"):
                    if key in breakdown:
                        pieces.append(f"{key}={breakdown[key]:.4f}")
                _safe_print(f"epoch={epoch + 1} batch={batch_index + 1} " + " ".join(pieces))

        train_loss = running_loss / max(running_batches, 1)
        val_metrics = _validate(
            model,
            val_loader,
            bundle,
            device,
            primary_weights,
            pitch_force_weights,
            wake_pos_weight,
            train_config,
        )
        history.append(
            {
                "epoch": epoch + 1,
                "train_loss": train_loss,
                "val_loss": val_metrics["loss"],
                "val_mae": val_metrics["mae"],
                "val_rmse": val_metrics["rmse"],
                "epoch_seconds": time.time() - epoch_start,
            }
        )
        _safe_print(
            f"[epoch {epoch + 1}] train_loss={train_loss:.4f} "
            f"val_loss={val_metrics['loss']:.4f} val_rmse={val_metrics['rmse']:.4f}"
        )
        if val_metrics["rmse"] < best_val_rmse:
            best_val_rmse = val_metrics["rmse"]
            best_epoch = epoch + 1
            best_state = {
                "model_state": snapshot_model_state(model),
                "model_config": tuned_model_config.__dict__,
                "train_config": train_config.__dict__,
                "metadata": bundle.metadata,
            }
            torch.save(best_state, Path(output_root) / "best_model.pt")
            patience_counter = 0
        else:
            patience_counter += 1
            if patience_counter >= train_config.patience:
                break

    if best_state is None:
        raise RuntimeError("Training did not produce a checkpoint.")

    model.load_state_dict(best_state["model_state"])
    val_summary = evaluate_model(model, val_loader, bundle, device, eval_config, Path(output_root) / "val_metrics")
    test_summary = evaluate_model(model, test_loader, bundle, device, eval_config, Path(output_root) / "test_metrics")
    holdout_summary = None
    if "holdout" in bundle.metadata.get("split_bounds", {}):
        holdout_dataset = RegimeWindowDataset(bundle, "holdout", hist_len, pred_len)
        holdout_loader = _build_dataloader(holdout_dataset, train_config.batch_size, False, train_config.num_workers)
        holdout_summary = evaluate_model(
            model,
            holdout_loader,
            bundle,
            device,
            eval_config,
            Path(output_root) / "holdout_metrics",
        )
    total_train_seconds = time.perf_counter() - train_start
    result = {
        "best_epoch": best_epoch,
        "best_val_rmse": best_val_rmse,
        "total_train_seconds": float(total_train_seconds),
        "history": history,
        "val_summary": val_summary,
        "test_summary": test_summary,
    }
    if holdout_summary is not None:
        result["holdout_summary"] = holdout_summary
    save_json(Path(output_root) / "training_summary.json", result)
    if device.type == "cuda":
        model.to("cpu")
        best_state = None
        optimizer = None
        scaler = None
        train_loader = None
        val_loader = None
        test_loader = None
        torch.cuda.synchronize()
        torch.cuda.empty_cache()
        gc.collect()
    return result
