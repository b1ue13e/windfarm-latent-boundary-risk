from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from main import build_parser
from windfarm_moe.boundary_slice import run_boundary_slice_audit
from windfarm_moe.utils import save_json


class BoundarySliceAuditTests(unittest.TestCase):
    def test_parser_accepts_boundary_slice_command(self) -> None:
        args = build_parser().parse_args(
            ["boundary-slice-audit", "--output-dir", "out", "--cache-dir", "cache", "--boundary-band", "0.8"]
        )

        self.assertEqual(args.command, "boundary-slice-audit")
        self.assertEqual(args.boundary_band, 0.8)

    def test_boundary_slice_outputs_boundary_effects(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            cache = root / "cache"
            cache.mkdir()
            save_json(
                cache / "metadata.json",
                {
                    "dataset": "wtb",
                    "physics_names": ["Wspd", "Pab_mean", "wake_score", "Patv"],
                    "primary_regime_names": ["idle", "mppt", "pitch_control", "transition"],
                },
            )

            # Four anchors, two nodes. The first two are near rated wind and
            # include both MPPT and pitch labels; the last two are core slices.
            physics = np.zeros((4, 2, 4), dtype=np.float32)
            physics[..., 0] = np.array([[10.2, 10.8], [10.4, 10.9], [8.0, 8.2], [12.5, 12.8]], dtype=np.float32)
            physics[..., 1] = np.array([[0.0, 3.0], [0.0, 3.0], [0.0, 0.0], [3.0, 3.0]], dtype=np.float32)
            np.save(cache / "physics.npy", physics)

            run_dir = root / "runs" / "aligned_seed1"
            metrics_dir = run_dir / "test_metrics"
            metrics_dir.mkdir(parents=True)
            windows = 4
            nodes = 2
            pred_len = 1
            target = np.zeros((windows, pred_len, nodes), dtype=np.float32)
            pred = np.zeros_like(target)
            pred[:2] = 3.0
            mask = np.ones_like(target, dtype=np.float32)
            regime = np.array([[1, 2], [1, 2], [1, 1], [2, 2]], dtype=np.int16)
            valid = np.ones_like(regime, dtype=np.float32)
            gate = np.zeros((windows, nodes, 3), dtype=np.float32)
            for t in range(windows):
                for n in range(nodes):
                    gate[t, n, regime[t, n]] = 1.0
            anchor_index = np.arange(windows, dtype=np.int64)

            np.save(metrics_dir / "pred.npy", pred)
            np.save(metrics_dir / "target.npy", target)
            np.save(metrics_dir / "mask.npy", mask)
            np.save(metrics_dir / "regime_primary.npy", regime)
            np.save(metrics_dir / "regime_primary_valid.npy", valid)
            np.save(metrics_dir / "gate_prob.npy", gate)
            np.save(metrics_dir / "anchor_index.npy", anchor_index)

            run_table = root / "runs.csv"
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
            ).to_csv(run_table, index=False)

            output_dir = run_boundary_slice_audit(
                run_table=run_table,
                cache_dir=cache,
                output_dir=root / "boundary",
                root_dir=root,
                models="Aligned MoE",
                boundary_band=1.0,
                core_margin=1.0,
                bootstrap_samples=20,
                seed=7,
            )

            raw = pd.read_csv(output_dir / "boundary_slice_raw.csv")
            summary = pd.read_csv(output_dir / "boundary_slice_summary.csv")
            effects = pd.read_csv(output_dir / "boundary_slice_effects.csv")

            self.assertEqual(set(raw["slice"]), {"boundary_band", "nonboundary_valid", "mppt_core", "pitch_core"})
            boundary = summary[summary["slice"] == "boundary_band"].iloc[0]
            self.assertEqual(int(boundary["n_anchor_cells_mean"]), 4)
            self.assertAlmostEqual(float(boundary["rmse_mean"]), 3.0)
            self.assertIn("boundary_band_minus_nonboundary_valid", set(effects["comparison"]))
            self.assertTrue((output_dir / "boundary_slice_report.md").exists())


if __name__ == "__main__":
    unittest.main()
