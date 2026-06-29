from __future__ import annotations

import argparse
import gc
import sys
import time
from pathlib import Path

import torch
from torch.utils.data import DataLoader

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from windfarm_moe.config import EvalConfig, ModelConfig
from windfarm_moe.data import RegimeWindowDataset, load_cache_bundle
from windfarm_moe.evaluate import evaluate_model
from windfarm_moe.model import RegimeAwareForecaster
from windfarm_moe.utils import ensure_dir, save_json


def _model_config_from_checkpoint(raw: dict) -> ModelConfig:
    fields = set(ModelConfig.__dataclass_fields__)
    values = {key: value for key, value in dict(raw).items() if key in fields}
    return ModelConfig(**values)


def recover_one(
    cache_dir: Path,
    run_dir: Path,
    seed: int,
    variant_key: str,
    experiment_group: str,
    device: torch.device,
) -> None:
    bundle = load_cache_bundle(cache_dir)
    hist_len = int(bundle.metadata["hist_len"])
    pred_len = int(bundle.metadata["pred_len"])
    checkpoint_path = run_dir / "best_model.pt"
    if not checkpoint_path.exists():
        raise FileNotFoundError(f"Missing checkpoint: {checkpoint_path}")

    state = torch.load(checkpoint_path, map_location=device)
    model_config = _model_config_from_checkpoint(dict(state.get("model_config", {})))
    train_config = dict(state.get("train_config", {}))
    mode = str(train_config.get("mode", "moe_phys_full"))
    batch_size = int(train_config.get("batch_size", 16))
    label = str(train_config.get("label") or "Physics-Aligned MoE")
    eval_config = EvalConfig(
        skip_visuals=True,
        save_predictions=True,
        switch_window=3 * int(bundle.metadata.get("steps_per_hour", 6)),
    )

    model = RegimeAwareForecaster(
        feature_dim=int(bundle.features.shape[-1]),
        pred_len=pred_len,
        mode=mode,
        config=model_config,
    ).to(device)
    model.load_state_dict(state["model_state"])

    pin_memory = device.type == "cuda"
    val_loader = DataLoader(
        RegimeWindowDataset(bundle, "val", hist_len, pred_len),
        batch_size=batch_size,
        shuffle=False,
        num_workers=0,
        pin_memory=pin_memory,
    )
    test_loader = DataLoader(
        RegimeWindowDataset(bundle, "test", hist_len, pred_len),
        batch_size=batch_size,
        shuffle=False,
        num_workers=0,
        pin_memory=pin_memory,
    )

    started = time.perf_counter()
    val_summary = evaluate_model(model, val_loader, bundle, device, eval_config, run_dir / "val_metrics")
    test_summary = evaluate_model(model, test_loader, bundle, device, eval_config, run_dir / "test_metrics")
    result = {
        "recovered_from_checkpoint": True,
        "recovery_note": "Evaluation recovered from best_model.pt after interrupted paper-batch finalization.",
        "recovery_seconds": float(time.perf_counter() - started),
        "val_summary": val_summary,
        "test_summary": test_summary,
        "model_mode": mode,
        "hidden_dim": int(model_config.hidden_dim),
        "num_experts": int(model_config.num_experts),
        "label": label,
        "seed": int(seed),
        "variant_key": variant_key,
        "experiment_group": experiment_group,
        "dataset": "external_wind",
        "farm": bundle.metadata.get("farm", ""),
        "target_farm": bundle.metadata.get("target_farm", ""),
        "external_split": bundle.metadata.get("external_split", ""),
        "source_url": bundle.metadata.get("source_url", ""),
        "target_source_url": bundle.metadata.get("target_source_url", ""),
        "license": bundle.metadata.get("license", ""),
    }
    save_json(run_dir / "training_summary.json", result)
    lock_path = run_dir / ".run_lock.json"
    if lock_path.exists():
        lock_path.unlink()

    del model, state, val_loader, test_loader, bundle
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


def main() -> None:
    parser = argparse.ArgumentParser(description="Recover external-wind eval artifacts from best_model.pt checkpoints.")
    parser.add_argument("--cache-dir", type=Path, required=True)
    parser.add_argument("--suite-dir", type=Path, required=True)
    parser.add_argument("--variant-key", type=str, default="full")
    parser.add_argument("--experiment-group", type=str, default="main")
    parser.add_argument("--dataset", type=str, default="external_wind")
    parser.add_argument("--seeds", type=str, required=True)
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    device_name = torch.cuda.get_device_name(torch.cuda.current_device()) if device.type == "cuda" else "cpu"
    print(f"device={device} name={device_name}", flush=True)
    for token in [item.strip() for item in args.seeds.split(",") if item.strip()]:
        seed = int(token)
        run_dir = ensure_dir(args.suite_dir / f"{args.dataset}_{args.variant_key}_seed{seed}")
        print(f"recover_seed={seed} run_dir={run_dir}", flush=True)
        recover_one(args.cache_dir, run_dir, seed, args.variant_key, args.experiment_group, device)
        print(f"done_seed={seed}", flush=True)


if __name__ == "__main__":
    main()
