from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from main import build_parser
from windfarm_moe.time_forward import run_time_forward_audit


class TimeForwardAuditTests(unittest.TestCase):
    def test_parser_accepts_time_forward_command(self) -> None:
        args = build_parser().parse_args(["time-forward-audit", "--output-dir", "out", "--num-blocks", "3", "--cache-dir", "cache"])

        self.assertEqual(args.command, "time-forward-audit")
        self.assertEqual(args.num_blocks, 3)
        self.assertEqual(args.cache_dir, "cache")

    def test_time_forward_outputs_late_vs_early_effects(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            run_dir = root / "runs" / "aligned_seed1"
            metrics_dir = run_dir / "test_metrics"
            metrics_dir.mkdir(parents=True)
            cache_dir = root / "cache"
            cache_dir.mkdir()

            windows = 8
            nodes = 2
            pred_len = 1
            target = np.zeros((windows, pred_len, nodes), dtype=np.float32)
            pred = np.zeros_like(target)
            pred[6:] = 4.0
            mask = np.ones_like(target, dtype=np.float32)
            regime = np.tile(np.array([[0, 1]], dtype=np.int16), (windows, 1))
            valid = np.ones_like(regime, dtype=np.float32)
            gate = np.zeros((windows, nodes, 3), dtype=np.float32)
            gate[..., 0] = np.where(regime == 0, 0.95, 0.02)
            gate[..., 1] = np.where(regime == 1, 0.95, 0.02)
            gate[..., 2] = 0.03
            gate = gate / gate.sum(axis=-1, keepdims=True)
            anchor_index = np.arange(100, 100 + windows, dtype=np.int64)
            physics = np.zeros((110, nodes, 4), dtype=np.float32)
            physics[..., 0] = 8.0
            physics[..., 1] = 1.0
            physics[106:, :, 0] = 12.0
            physics[106:, :, 1] = 3.0

            np.save(metrics_dir / "pred.npy", pred)
            np.save(metrics_dir / "target.npy", target)
            np.save(metrics_dir / "mask.npy", mask)
            np.save(metrics_dir / "regime_primary.npy", regime)
            np.save(metrics_dir / "regime_primary_valid.npy", valid)
            np.save(metrics_dir / "gate_prob.npy", gate)
            np.save(metrics_dir / "anchor_index.npy", anchor_index)
            np.save(cache_dir / "physics.npy", physics)
            from windfarm_moe.utils import save_json

            save_json(
                cache_dir / "metadata.json",
                {"dataset": "wtb", "physics_names": ["Wspd", "Pab_mean", "wake_score", "Patv"]},
            )

            table = root / "runs.csv"
            pd.DataFrame(
                [
                    {
                        "dataset": "wtb",
                        "model": "Aligned MoE",
                        "seed": 1,
                        "variant_key": "aligned",
                        "experiment_group": "main",
                        "run_dir": run_dir.relative_to(root),
                    }
                ]
            ).to_csv(table, index=False)

            output_dir = run_time_forward_audit(
                run_table=table,
                output_dir=root / "time_forward",
                root_dir=root,
                cache_dir=cache_dir,
                models="Aligned MoE",
                num_blocks=4,
                bootstrap_samples=20,
                seed=7,
            )

            raw = pd.read_csv(output_dir / "time_forward_raw.csv")
            summary = pd.read_csv(output_dir / "time_forward_summary.csv")
            effects = pd.read_csv(output_dir / "time_forward_effects.csv")
            shift = pd.read_csv(output_dir / "time_forward_shift_diagnostics.csv")
            shift_effects = pd.read_csv(output_dir / "time_forward_shift_effects.csv")
            from windfarm_moe.utils import load_json

            shift_guard = load_json(output_dir / "time_forward_shift_guard.json")

            self.assertTrue((output_dir / "time_forward_report.md").exists())
            self.assertTrue((output_dir / "table_strict_wtb_late_shift_diagnostics.tex").exists())
            self.assertEqual(len(raw), 4)
            self.assertEqual(len(shift), 4)
            early = summary[summary["block_id"] == 1].iloc[0]
            late = summary[summary["block_id"] == 4].iloc[0]
            self.assertLess(early["overall_rmse_mean"], late["overall_rmse_mean"])
            effect = effects.iloc[0]
            self.assertGreater(effect["delta_overall_rmse_mean"], 0.0)
            self.assertGreater(shift_effects.iloc[0]["delta_wspd_mean_mean"], 0.0)
            self.assertEqual(shift_guard["status"], "passed_late_period_shift_diagnostics")


if __name__ == "__main__":
    unittest.main()
