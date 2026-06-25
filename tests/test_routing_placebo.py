from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from main import build_parser
from windfarm_moe.routing_placebo import run_routing_placebo_audit


class RoutingPlaceboAuditTests(unittest.TestCase):
    def test_parser_accepts_routing_placebo_command(self) -> None:
        args = build_parser().parse_args(["routing-placebo", "--output-dir", "out"])

        self.assertEqual(args.command, "routing-placebo")
        self.assertEqual(args.temporal_shifts, "18,144")

    def test_routing_placebo_outputs_negative_controls(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            run_dir = root / "runs" / "aligned_seed1"
            metrics_dir = run_dir / "test_metrics"
            metrics_dir.mkdir(parents=True)

            regime = np.array(
                [
                    [0, 1, 2],
                    [0, 1, 2],
                    [0, 1, 2],
                    [0, 1, 2],
                    [0, 1, 2],
                    [0, 1, 2],
                ],
                dtype=np.int16,
            )
            gate = np.zeros((6, 3, 4), dtype=np.float32)
            for label in range(3):
                gate[..., label] = np.where(regime == label, 0.95, 0.02)
            gate[..., 3] = 0.01
            gate = gate / gate.sum(axis=-1, keepdims=True)

            np.save(metrics_dir / "regime_primary.npy", regime)
            np.save(metrics_dir / "regime_primary_valid.npy", np.ones_like(regime, dtype=np.float32))
            np.save(metrics_dir / "gate_prob.npy", gate)

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

            output_dir = run_routing_placebo_audit(
                run_table=table,
                output_dir=root / "placebo",
                root_dir=root,
                models="Aligned MoE",
                temporal_shifts=[1],
                bootstrap_samples=20,
                seed=7,
            )

            raw = pd.read_csv(output_dir / "routing_placebo_raw.csv")
            summary = pd.read_csv(output_dir / "routing_placebo_summary.csv")
            effects = pd.read_csv(output_dir / "routing_placebo_effects.csv")

            self.assertTrue((output_dir / "routing_placebo_report.md").exists())
            self.assertIn("global_shuffle", raw["condition"].tolist())
            actual = summary[summary["condition"] == "actual"].iloc[0]
            self.assertGreater(actual["nmi_mean"], 0.99)
            global_effect = effects[effects["control_condition"] == "global_shuffle"].iloc[0]
            self.assertGreater(global_effect["delta_nmi_mean"], 0.5)


if __name__ == "__main__":
    unittest.main()
