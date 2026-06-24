from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from main import build_parser
from windfarm_moe.reserve_baselines import run_reserve_probabilistic_baseline
from windfarm_moe.utils import load_json, save_json


class ReserveProbabilisticBaselineTests(unittest.TestCase):
    def test_parser_accepts_command(self) -> None:
        args = build_parser().parse_args(
            ["reserve-probabilistic-baseline", "--output-dir", "out", "--bootstrap-samples", "7"]
        )

        self.assertEqual(args.command, "reserve-probabilistic-baseline")
        self.assertEqual(args.bootstrap_samples, 7)

    def test_run_outputs_summary_comparison_and_tex(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            table = _write_run_fixture(root)
            cache = _write_cache(root)
            output = root / "reserve_quantile"

            run_reserve_probabilistic_baseline(
                run_table=table,
                cache_dir=cache,
                output_dir=output,
                root_dir=root,
                cost_ratios=[10.0],
                main_ratio=10.0,
                quantiles=[0.5, 0.8, 0.95],
                bootstrap_samples=8,
            )

            summary = pd.read_csv(output / "reserve_quantile_baseline.csv")
            comparison = pd.read_csv(output / "reserve_quantile_baseline_comparison.csv")
            config = load_json(output / "reserve_quantile_baseline.json")

            self.assertTrue((output / "reserve_quantile_baseline.tex").exists())
            self.assertTrue((output / "reserve_quantile_baseline_raw.csv").exists())
            self.assertIn("global_quantile", set(summary["baseline"]))
            self.assertIn("physical_bin_quantile", set(summary["baseline"]))
            self.assertIn("gate_bin_quantile", set(summary["baseline"]))
            self.assertIn("boundary", set(summary["subset"]))
            self.assertIn("interpretation", comparison.columns)
            self.assertEqual(config["main_ratio"], 10.0)


def _write_cache(root: Path) -> Path:
    cache = root / "cache" / "wtb_245d"
    cache.mkdir(parents=True)
    steps = 12
    nodes = 2
    regime = np.tile(np.array([[1, 2]], dtype=np.int16), (steps, 1))
    valid = np.ones((steps, nodes), dtype=np.float32)
    physics = np.zeros((steps, nodes, 4), dtype=np.float32)
    physics[..., 0] = np.linspace(9.8, 11.2, steps)[:, None]
    physics[..., 1] = np.where(physics[..., 0] > 10.5, 3.0, 1.0)
    for name, value in {
        "regime_primary": regime,
        "regime_primary_valid": valid,
        "physics": physics,
        "time_index": np.stack([np.zeros(steps, dtype=np.int16), np.arange(steps, dtype=np.int16)], axis=1),
    }.items():
        np.save(cache / f"{name}.npy", value)
    save_json(
        cache / "metadata.json",
        {
            "dataset": "wtb",
            "steps_per_hour": 6,
            "pred_len": 2,
            "split_bounds": {"val": [0, 6], "test": [6, 12]},
            "wtb_thresholds": {"rated_wind": 10.5},
        },
    )
    return cache


def _write_run_fixture(root: Path) -> Path:
    table = root / "runs.csv"
    rows = []
    specs = [
        ("Graph WaveNet", "Graph WaveNet", "graph_wavenet", "strong_baselines"),
        ("PatchTST", "PatchTST", "patchtst", "strong_baselines"),
        ("Physics-Aligned MoE", "Physics-Aligned MoE", "full", "ablation"),
        ("MoE + L_bal + L_align + L_force", "Boundary-forced router", "bal_align_force", "ablation"),
    ]
    for model_name, display, variant, group in specs:
        for seed in [201, 202, 203, 204, 205]:
            run_dir = root / "runs" / f"{variant}_{seed}"
            _write_metrics(run_dir / "val_metrics", seed=seed, has_gate=group == "ablation")
            _write_metrics(run_dir / "test_metrics", seed=seed + 1, has_gate=group == "ablation")
            rows.append(
                {
                    "model": model_name,
                    "seed": seed,
                    "experiment_group": group,
                    "variant_key": variant,
                    "run_dir": str(run_dir.relative_to(root)),
                    "overall_rmse": 100.0 + seed % 10,
                }
            )
    pd.DataFrame(rows).to_csv(table, index=False)
    return table


def _write_metrics(metrics: Path, *, seed: int, has_gate: bool) -> None:
    metrics.mkdir(parents=True, exist_ok=True)
    windows, horizon, nodes = 4, 2, 2
    base = np.arange(windows * horizon * nodes, dtype=np.float32).reshape(windows, horizon, nodes)
    target = base + 10.0
    pred = target + ((seed % 3) + 1.0)
    pred[::2] = target[::2] - 1.0
    mask = np.ones_like(target, dtype=np.float32)
    regime = np.tile(np.array([[1, 2]], dtype=np.int16), (windows, 1))
    np.save(metrics / "pred.npy", pred)
    np.save(metrics / "target.npy", target)
    np.save(metrics / "mask.npy", mask)
    np.save(metrics / "regime_primary.npy", regime)
    np.save(metrics / "regime_primary_valid.npy", np.ones((windows, nodes), dtype=np.float32))
    np.save(metrics / "anchor_index.npy", np.arange(windows, dtype=np.int64))
    if has_gate:
        gate = np.zeros((windows, nodes, 4), dtype=np.float32)
        gate[..., 2] = np.linspace(0.1, 0.9, windows)[:, None]
        gate[..., 1] = 1.0 - gate[..., 2]
        np.save(metrics / "gate_prob.npy", gate)
