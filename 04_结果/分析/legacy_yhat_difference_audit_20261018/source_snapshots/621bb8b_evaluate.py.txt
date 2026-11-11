from __future__ import annotations

from pathlib import Path
import time
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import torch
from sklearn.metrics import adjusted_rand_score, confusion_matrix, normalized_mutual_info_score

from .utils import ensure_dir, save_json, to_device


def _masked_numpy_metrics(pred: np.ndarray, target: np.ndarray, mask: np.ndarray) -> dict[str, float]:
    weight = mask.astype(np.float64)
    safe_pred = np.nan_to_num(pred.astype(np.float64), nan=0.0)
    safe_target = np.nan_to_num(target.astype(np.float64), nan=0.0)
    denom = max(weight.sum(), 1.0)
    mae = (np.abs(safe_pred - safe_target) * weight).sum() / denom
    rmse = np.sqrt((((safe_pred - safe_target) ** 2) * weight).sum() / denom)
    return {"mae": float(mae), "rmse": float(rmse)}


def _save_regime_metrics_csv(metrics: dict[str, Any], output_path: Path) -> None:
    rows = [{"slice": "overall", **metrics["overall"]}, {"slice": "switch_window", **metrics["switch_window"]}]
    for name, values in metrics["by_regime"].items():
        rows.append({"slice": f"regime::{name}", **values})
    pd.DataFrame(rows).to_csv(output_path, index=False)


def _plot_confusion(conf: np.ndarray, labels: list[str], output_path: Path) -> None:
    plt.figure(figsize=(6, 5))
    sns.heatmap(conf, annot=True, fmt="d", cmap="Blues", xticklabels=labels, yticklabels=labels)
    plt.xlabel("Predicted Expert")
    plt.ylabel("Physical Regime")
    plt.tight_layout()
    plt.savefig(output_path, dpi=180)
    plt.close()


def evaluate_model(
    model: torch.nn.Module,
    data_loader: torch.utils.data.DataLoader,
    bundle: Any,
    device: torch.device,
    eval_config: Any,
    output_dir: Path | str,
) -> dict[str, Any]:
    output_dir = ensure_dir(output_dir)
    model.eval()
    eval_start = time.perf_counter()

    pred_batches = []
    target_batches = []
    mask_batches = []
    primary_batches = []
    primary_valid_batches = []
    aux_batches = []
    aux_valid_batches = []
    anchor_batches = []
    gate_batches = []
    num_batches = 0

    with torch.no_grad():
        for batch in data_loader:
            num_batches += 1
            batch = to_device(batch, device)
            pred, gate_prob, _ = model(
                batch["x_hist"],
                batch["edge_index_hist"],
                batch["edge_weight_hist"],
                batch["feature_mask_hist"],
                batch["anchor_physics"],
            )
            pred_batches.append(pred.cpu().numpy())
            target_batches.append(batch["target"].cpu().numpy())
            mask_batches.append(batch["target_mask"].cpu().numpy())
            primary_batches.append(batch["regime_primary"].cpu().numpy())
            primary_valid_batches.append(batch["regime_primary_valid"].cpu().numpy())
            aux_batches.append(batch["regime_aux"].cpu().numpy())
            aux_valid_batches.append(batch["regime_aux_valid"].cpu().numpy())
            anchor_batches.append(batch["anchor_index"].cpu().numpy())
            if gate_prob is not None:
                gate_batches.append(gate_prob.cpu().numpy())

    if not pred_batches:
        metrics = {"overall": {"mae": float("nan"), "rmse": float("nan")}, "by_regime": {}, "switch_window": {}}
        save_json(output_dir / "metrics.json", metrics)
        return metrics

    pred = np.concatenate(pred_batches, axis=0)
    target = np.concatenate(target_batches, axis=0)
    mask = np.concatenate(mask_batches, axis=0)
    regime_primary = np.concatenate(primary_batches, axis=0)
    regime_primary_valid = np.concatenate(primary_valid_batches, axis=0)
    regime_aux = np.concatenate(aux_batches, axis=0)
    regime_aux_valid = np.concatenate(aux_valid_batches, axis=0)
    anchor_index = np.concatenate(anchor_batches, axis=0)
    anchor_physics = np.asarray(bundle.physics)[anchor_index]
    eval_seconds = time.perf_counter() - eval_start
    num_windows = int(pred.shape[0])
    throughput = float(num_windows / eval_seconds) if eval_seconds > 0.0 else float("nan")

    metrics = {
        "overall": _masked_numpy_metrics(pred, target, mask),
        "efficiency": {
            "eval_seconds": float(eval_seconds),
            "num_windows": num_windows,
            "num_batches": int(num_batches),
            "windows_per_second": throughput,
        },
    }
    primary_names = bundle.metadata["primary_regime_names"]
    metrics["by_regime"] = {}
    for regime_id, regime_name in enumerate(primary_names):
        selector = regime_primary == regime_id
        regime_mask = mask * selector[:, None, :]
        metrics["by_regime"][regime_name] = _masked_numpy_metrics(pred, target, regime_mask)

    switch_window = int(getattr(eval_config, "switch_window", 0) or (3 * bundle.metadata.get("steps_per_hour", 6)))
    switch_selector = np.zeros_like(regime_primary, dtype=bool)
    if regime_primary.shape[0] > 1:
        changes = regime_primary[1:] != regime_primary[:-1]
        rows, nodes = np.where(changes)
        for row, node in zip(rows, nodes):
            lo = max(0, row + 1 - switch_window)
            hi = min(regime_primary.shape[0], row + 2 + switch_window)
            switch_selector[lo:hi, node] = True
    metrics["switch_window"] = _masked_numpy_metrics(pred, target, mask * switch_selector[:, None, :])

    if gate_batches:
        gate_prob = np.concatenate(gate_batches, axis=0)
        primary_num_classes = bundle.metadata["primary_num_classes"]
        supervised_gate = gate_prob[..., :primary_num_classes]
        gate_label = supervised_gate.argmax(axis=-1)
        valid = regime_primary_valid > 0.0
        flat_true = regime_primary[valid]
        flat_pred = gate_label[valid]
        labels = list(range(primary_num_classes))
        conf = (
            confusion_matrix(flat_true, flat_pred, labels=labels)
            if flat_true.size
            else np.zeros((primary_num_classes, primary_num_classes), dtype=np.int64)
        )
        metrics["gate_alignment"] = {
            "nmi": float(normalized_mutual_info_score(flat_true, flat_pred)) if flat_true.size else float("nan"),
            "ari": float(adjusted_rand_score(flat_true, flat_pred)) if flat_true.size else float("nan"),
            "confusion_matrix": conf.tolist(),
            "expert_usage": gate_prob.mean(axis=(0, 1)).tolist(),
            "expert_usage_entropy": float(
                -np.sum(
                    np.clip(gate_prob.mean(axis=(0, 1)), 1e-12, None)
                    * np.log(np.clip(gate_prob.mean(axis=(0, 1)), 1e-12, None))
                )
            ),
            "expert_usage_variance": float(np.var(gate_prob.mean(axis=(0, 1)))),
        }
        if not eval_config.skip_visuals:
            _plot_confusion(conf, primary_names[:primary_num_classes], output_dir / "gate_regime_confusion.png")
    else:
        gate_prob = None

    save_json(output_dir / "metrics.json", metrics)
    _save_regime_metrics_csv(metrics, output_dir / "regime_wise_metrics.csv")

    np.save(output_dir / "pred.npy", pred.astype(np.float32))
    np.save(output_dir / "target.npy", target.astype(np.float32))
    np.save(output_dir / "mask.npy", mask.astype(np.float32))
    np.save(output_dir / "regime_primary.npy", regime_primary.astype(np.int16))
    np.save(output_dir / "regime_primary_valid.npy", regime_primary_valid.astype(np.float32))
    np.save(output_dir / "regime_aux.npy", regime_aux.astype(np.int16))
    np.save(output_dir / "regime_aux_valid.npy", regime_aux_valid.astype(np.float32))
    np.save(output_dir / "anchor_index.npy", anchor_index.astype(np.int64))
    np.save(output_dir / "anchor_physics.npy", anchor_physics.astype(np.float32))
    if gate_prob is not None:
        np.save(output_dir / "gate_prob.npy", gate_prob.astype(np.float32))
    return metrics
