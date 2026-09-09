"""Train Capacity-Matched Dense Backbone (Directed-Diffusion GRU) on WTB.

Model Architecture:
- Backbone: Directed-Diffusion GRU (SpatioTemporalEncoder in windfarm_moe)
- Hidden dim: Resolved by find_capacity_matched_dense_hidden_dim (76 for WTB)
- Head: 1 expert (ExpertHead dense_head, no gating, no routing)
- Losses: Pure MSE prediction loss (align=0, aux=0, smooth=0, balance=0, physics_force=0)
- Seeds: 201, 202, 203, 204, 205
"""
from __future__ import annotations

import os
import sys

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
os.environ["OMP_NUM_THREADS"] = "4"
os.environ["MKL_NUM_THREADS"] = "4"
os.environ["PYTHONUNBUFFERED"] = "1"

import argparse
import time
from pathlib import Path

import torch

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from windfarm_moe.config import EvalConfig, ModelConfig, TrainConfig
from windfarm_moe.data import load_cache_bundle
from windfarm_moe.paper import resolve_capacity_matched_hidden_dim
from windfarm_moe.train import train_model


def train_dense_seed(
    seed: int,
    device_str: str,
    cache_dir: str,
    output_base: str,
    epochs: int = 20,
    patience: int = 5,
    batch_size: int = 16,
    lr: float = 2e-3,
    weight_decay: float = 1e-4,
    num_workers: int = 4,
):
    print(f"\n=======================================================", flush=True)
    print(f"Starting Training Capacity-Matched Dense for Seed {seed} on {device_str}", flush=True)
    print(f"=======================================================", flush=True)

    cache_path = Path(cache_dir)
    if not cache_path.exists():
        raise FileNotFoundError(f"Cache dir {cache_path} not found")

    bundle = load_cache_bundle(cache_path, mmap_mode="r")

    matched_hidden = resolve_capacity_matched_hidden_dim(
        bundle=bundle,
        mode="baseline_dense",
        hidden_dim=64,
        num_experts=4,
        tau=0.7,
        dropout=0.1,
    )
    print(f"Resolved Capacity-Matched hidden_dim: {matched_hidden} (MoE hidden=64)", flush=True)

    model_config = ModelConfig(
        hidden_dim=matched_hidden,
        num_experts=1,
        dropout=0.1,
        tau=0.7,
        primary_num_classes=bundle.metadata["primary_num_classes"],
        gate_physics_dim=int(bundle.physics.shape[-1]),
    )

    train_config = TrainConfig(
        mode="baseline_dense",
        batch_size=batch_size,
        epochs=epochs,
        learning_rate=lr,
        weight_decay=weight_decay,
        grad_clip_norm=1.0,
        patience=patience,
        num_workers=num_workers,
        seed=seed,
        log_every=200,
        align_weight=0.0,
        aux_weight=0.0,
        smooth_weight=0.0,
        balance_weight=0.0,
        physics_force_weight=0.0,
        label="Capacity-Matched Dense Diffusion-GRU",
    )

    eval_config = EvalConfig(
        skip_visuals=True,
        save_predictions=True,
        switch_window=3 * int(bundle.metadata.get("steps_per_hour", 6)),
    )

    out_dir = Path(output_base) / f"wtb_dense_seed{seed}"
    out_dir.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    result = train_model(
        bundle=bundle,
        output_root=out_dir,
        model_config=model_config,
        train_config=train_config,
        eval_config=eval_config,
    )
    elapsed = time.time() - t0

    print(f"\n[TRAINING COMPLETE] Seed {seed} in {elapsed:.1f}s", flush=True)
    print(f"  Best epoch: {result.get('best_epoch')}", flush=True)
    print(f"  Best val RMSE: {result.get('best_val_rmse'):.4f}", flush=True)
    print(f"  Saved to: {out_dir / 'best_model.pt'}\n", flush=True)
    return result


def main():
    parser = argparse.ArgumentParser(description="Train Capacity-Matched Dense Backbone on WTB")
    parser.add_argument("--seed", type=int, default=201)
    parser.add_argument("--device", type=str, default="cuda:0")
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--patience", type=int, default=5)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--lr", type=float, default=2e-3)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--num-workers", type=int, default=4)
    parser.add_argument("--cache-dir", type=str, default="artifacts/cache_strictmask_trainweights/wtb_245d")
    parser.add_argument("--output-base", type=str, default="artifacts/capacity_matched_dense_wtb")
    args = parser.parse_args()

    train_dense_seed(
        seed=args.seed,
        device_str=args.device,
        cache_dir=args.cache_dir,
        output_base=args.output_base,
        epochs=args.epochs,
        patience=args.patience,
        batch_size=args.batch_size,
        lr=args.lr,
        weight_decay=args.weight_decay,
        num_workers=args.num_workers,
    )


if __name__ == "__main__":
    main()
