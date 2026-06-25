from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from main import build_parser
from windfarm_moe.mechanism_behavior import run_mechanism_behavior_pack
from windfarm_moe.utils import load_json


class MechanismBehaviorTests(unittest.TestCase):
    def _write_run(self, root: Path) -> Path:
        run_dir = root / "runs" / "behavior_seed201"
        metrics = run_dir / "test_metrics"
        metrics.mkdir(parents=True)
        pred = np.ones((5, 3, 2), dtype=np.float32)
        target = np.zeros((5, 3, 2), dtype=np.float32)
        mask = np.ones_like(pred, dtype=np.float32)
        regime = np.array([[1, 2], [1, 2], [2, 2], [2, 1], [1, 1]], dtype=np.int16)
        gate = np.zeros((5, 2, 4), dtype=np.float32)
        for row in range(regime.shape[0]):
            for node in range(regime.shape[1]):
                gate[row, node, regime[row, node]] = 0.9
                gate[row, node, 0] += 0.1
        physics = np.zeros((5, 2, 4), dtype=np.float32)
        physics[..., 0] = np.array([[10, 11], [10, 11], [12, 12], [12, 9], [9, 9]], dtype=np.float32)
        physics[..., 3] = 100.0
        np.save(metrics / "pred.npy", pred)
        np.save(metrics / "target.npy", target)
        np.save(metrics / "mask.npy", mask)
        np.save(metrics / "regime_primary.npy", regime)
        np.save(metrics / "regime_primary_valid.npy", np.ones_like(regime, dtype=np.float32))
        np.save(metrics / "gate_prob.npy", gate)
        np.save(metrics / "anchor_physics.npy", physics)
        return run_dir

    def test_parser_accepts_mechanism_behavior_pack(self) -> None:
        args = build_parser().parse_args(["mechanism-behavior-pack", "--output-dir", "out"])

        self.assertEqual(args.command, "mechanism-behavior-pack")

    def test_mechanism_behavior_pack_outputs_tables(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            run_dir = self._write_run(root)
            table = root / "runs.csv"
            pd.DataFrame([{"model": "Aligned", "seed": 201, "run_dir": run_dir.relative_to(root)}]).to_csv(table, index=False)

            out = run_mechanism_behavior_pack(table, root / "out", root_dir=root, models="Aligned")
            config = load_json(out / "mechanism_behavior_pack_config.json")

            self.assertEqual(config["status"], "complete_ready_for_mechanism_behavior_evidence")
            self.assertTrue((out / "expert_power_curve.csv").exists())
            self.assertTrue((out / "gate_transition_lead_lag.csv").exists())
            self.assertTrue((out / "mechanism_behavior_pack_guard.json").exists())


if __name__ == "__main__":
    unittest.main()
