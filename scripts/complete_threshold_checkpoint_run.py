from __future__ import annotations

import argparse
import time
import sys
from pathlib import Path
from typing import Any

import torch
from torch.utils.data import DataLoader

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from windfarm_moe.config import EvalConfig, ModelConfig
from windfarm_moe.data import RegimeWindowDataset, load_cache_bundle
from windfarm_moe.evaluate import evaluate_model
from windfarm_moe.model import RegimeAwareForecaster
from windfarm_moe.paper import _build_wtb_threshold_bundle
from windfarm_moe.utils import ensure_dir, save_json


def _parse_threshold_from_variant(variant_key: str) -> dict[str, float]:
    if variant_key.startswith("sens_rated_"):
        value = float(variant_key.removeprefix("sens_rated_").replace("p", "."))
        return {"rated_wind": value, "pitch_threshold": 2.0}
    if variant_key.startswith("sens_pitch_"):
        value = float(variant_key.removeprefix("sens_pitch_").replace("p", "."))
        return {"rated_wind": 10.5, "pitch_threshold": value}
    raise ValueError(f"Unsupported threshold variant: {variant_key}")


def _load_model(run_dir: Path, bundle: Any, device: torch.device) -> tuple[RegimeAwareForecaster, dict[str, Any]]:
    checkpoint_path = run_dir / "best_model.pt"
    if not checkpoint_path.exists():
        raise FileNotFoundError(f"Missing checkpoint: {checkpoint_path}")
    checkpoint = torch.load(checkpoint_path, map_location=device)
    model_config = ModelConfig(**checkpoint["model_config"])
    train_config = dict(checkpoint["train_config"])
    model = RegimeAwareForecaster(
        feature_dim=int(bundle.features.shape[-1]),
        pred_len=int(bundle.metadata["pred_len"]),
        mode=str(train_config["mode"]),
        config=model_config,
    ).to(device)
    model.load_state_dict(checkpoint["model_state"])
    model.eval()
    return model, checkpoint


def complete_run(
    cache_dir: Path,
    run_dir: Path,
    variant_key: str,
    seed: int,
    batch_size: int,
    device_name: str,
) -> None:
    run_dir = ensure_dir(run_dir)
    base_bundle = load_cache_bundle(cache_dir)
    threshold = _parse_threshold_from_variant(variant_key)
    bundle = _build_wtb_threshold_bundle(base_bundle, **threshold)
    device = torch.device(device_name)
    model, checkpoint = _load_model(run_dir, bundle, device)
    eval_config = EvalConfig(skip_visuals=True, save_predictions=True, switch_window=3 * int(bundle.metadata.get("steps_per_hour", 6)))
    hist_len = int(bundle.metadata["hist_len"])
    pred_len = int(bundle.metadata["pred_len"])
    start = time.perf_counter()

    summaries: dict[str, Any] = {}
    for split in ["val", "test"]:
        dataset = RegimeWindowDataset(bundle, split, hist_len, pred_len)
        loader = DataLoader(dataset, batch_size=int(batch_size), shuffle=False, num_workers=0, pin_memory=False)
        summaries[f"{split}_summary"] = evaluate_model(
            model,
            loader,
            bundle,
            device,
            eval_config,
            run_dir / f"{split}_metrics",
        )

    best_val_rmse = summaries["val_summary"].get("overall", {}).get("rmse")
    train_config = dict(checkpoint.get("train_config", {}))
    result = {
        "best_epoch": int(train_config.get("best_epoch", -1)) if str(train_config.get("best_epoch", "")).strip() else -1,
        "best_val_rmse": float(best_val_rmse) if best_val_rmse is not None else float("nan"),
        "total_train_seconds": float(time.perf_counter() - start),
        "history": [],
        "val_summary": summaries["val_summary"],
        "test_summary": summaries["test_summary"],
        "seed": int(seed),
        "variant_key": variant_key,
        "experiment_group": "sensitivity",
        "model_mode": str(train_config.get("mode", "moe_phys_full")),
        "setting_group": "rated_wind" if variant_key.startswith("sens_rated_") else "pitch_threshold",
        "setting_value": threshold["rated_wind"] if variant_key.startswith("sens_rated_") else threshold["pitch_threshold"],
        "setting_label": (
            f"rated_wind={threshold['rated_wind']:.1f}"
            if variant_key.startswith("sens_rated_")
            else f"pitch_threshold={threshold['pitch_threshold']:.1f}"
        ),
        "completion_note": "completed_from_best_model_checkpoint_after_interrupted_final_evaluation",
    }
    save_json(run_dir / "training_summary.json", result)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache-dir", required=True)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--variant-key", required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--device", default="cpu")
    args = parser.parse_args()
    complete_run(
        cache_dir=Path(args.cache_dir),
        run_dir=Path(args.run_dir),
        variant_key=args.variant_key,
        seed=args.seed,
        batch_size=args.batch_size,
        device_name=args.device,
    )
    print(f"Completed checkpoint run: {args.run_dir}")


if __name__ == "__main__":
    main()
