from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from main import build_parser
from windfarm_moe.boundary_negative_controls import run_boundary_negative_controls
from windfarm_moe.utils import load_json


class BoundaryNegativeControlTests(unittest.TestCase):
    def _write_run(self, root: Path) -> Path:
        run_dir = root / "runs" / "aligned_seed201"
        metrics = run_dir / "test_metrics"
        metrics.mkdir(parents=True)
        regime = np.array([[1, 2], [1, 2], [1, 2], [1, 2]], dtype=np.int16)
        gate = np.zeros((4, 2, 4), dtype=np.float32)
        for cls in [1, 2]:
            gate[..., cls] = np.where(regime == cls, 0.95, 0.02)
        gate[..., 0] = 0.01
        gate[..., 3] = 0.01
        gate = gate / gate.sum(axis=-1, keepdims=True)
        physics = np.zeros((4, 2, 4), dtype=np.float32)
        physics[..., 0] = np.array([[8, 12], [8, 12], [8, 12], [8, 12]], dtype=np.float32)
        physics[..., 1] = np.array([[1, 5], [1, 5], [1, 5], [1, 5]], dtype=np.float32)
        np.save(metrics / "regime_primary.npy", regime)
        np.save(metrics / "regime_primary_valid.npy", np.ones_like(regime, dtype=np.float32))
        np.save(metrics / "gate_prob.npy", gate)
        np.save(metrics / "anchor_physics.npy", physics)
        return run_dir

    def test_parser_accepts_boundary_negative_controls(self) -> None:
        args = build_parser().parse_args(["boundary-negative-controls", "--output-dir", "out"])

        self.assertEqual(args.command, "boundary-negative-controls")

    def test_boundary_negative_controls_emit_guard(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            run_dir = self._write_run(root)
            table = root / "runs.csv"
            pd.DataFrame([{"model": "Aligned", "seed": 201, "run_dir": run_dir.relative_to(root)}]).to_csv(table, index=False)

            out = run_boundary_negative_controls(
                run_table=table,
                cache_dir=root / "cache",
                output_dir=root / "out",
                root_dir=root,
                models="Aligned",
                controls="random_boundary",
                seed=1,
            )
            guard = load_json(out / "boundary_negative_controls_guard.json")

            self.assertTrue((out / "boundary_negative_controls_raw.csv").exists())
            self.assertIn("status", guard)
            self.assertGreaterEqual(guard["n_raw_rows"], 2)
            self.assertIn("positive_boundary_intervention_drop_mean", guard)
            self.assertTrue(guard["checks"]["each_negative_control_changes_shared_labels"])

    def test_wrong_threshold_controls_relabel_shared_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            run_dir = self._write_run(root)
            table = root / "runs.csv"
            pd.DataFrame([{"model": "Aligned", "seed": 201, "run_dir": run_dir.relative_to(root)}]).to_csv(table, index=False)

            out = run_boundary_negative_controls(
                run_table=table,
                cache_dir=root / "cache",
                output_dir=root / "out",
                root_dir=root,
                models="Aligned",
                controls="wrong_rated_low,wrong_rated_high,wrong_pitch_low,wrong_pitch_high",
                min_shared_label_change=0.05,
                min_positive_intervention_drop=-1.0,
                max_control_nmi=2.0,
                max_control_ari=2.0,
                max_control_intervention_drop=2.0,
                seed=1,
            )
            guard = load_json(out / "boundary_negative_controls_guard.json")

            self.assertTrue(guard["checks"]["each_negative_control_changes_shared_labels"])
            for condition in ["wrong_rated_low", "wrong_rated_high", "wrong_pitch_low", "wrong_pitch_high"]:
                self.assertGreaterEqual(
                    guard["negative_control_min_shared_label_change_by_condition"][condition],
                    0.75,
                )

    def test_boundary_negative_controls_block_when_a_control_does_not_relabel_shared_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            run_dir = self._write_run(root)
            table = root / "runs.csv"
            pd.DataFrame([{"model": "Aligned", "seed": 201, "run_dir": run_dir.relative_to(root)}]).to_csv(table, index=False)

            out = run_boundary_negative_controls(
                run_table=table,
                cache_dir=root / "cache",
                output_dir=root / "out",
                root_dir=root,
                models="Aligned",
                controls="time_shift_boundary",
                time_shift_steps=0,
                seed=1,
            )
            guard = load_json(out / "boundary_negative_controls_guard.json")

            self.assertEqual(guard["status"], "blocked_boundary_negative_controls")
            self.assertFalse(guard["checks"]["each_negative_control_changes_shared_labels"])
            self.assertEqual(guard["negative_control_min_shared_label_change_by_condition"]["time_shift_boundary"], 0.0)

    def test_boundary_negative_controls_block_when_fake_boundary_keeps_drop(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            run_dir = root / "runs" / "shifted_gate_seed201"
            metrics = run_dir / "test_metrics"
            metrics.mkdir(parents=True)
            regime = np.array([[1, 2], [2, 1], [1, 2], [2, 1]], dtype=np.int16)
            gate = np.zeros((4, 2, 4), dtype=np.float32)
            shifted = np.roll(regime, 1, axis=0)
            for row in range(regime.shape[0]):
                for node in range(regime.shape[1]):
                    gate[row, node, shifted[row, node]] = 1.0
            physics = np.zeros((4, 2, 4), dtype=np.float32)
            physics[..., 0] = np.array([[8, 12], [12, 8], [8, 12], [12, 8]], dtype=np.float32)
            physics[..., 1] = np.array([[1, 5], [5, 1], [1, 5], [5, 1]], dtype=np.float32)
            np.save(metrics / "regime_primary.npy", regime)
            np.save(metrics / "regime_primary_valid.npy", np.ones_like(regime, dtype=np.float32))
            np.save(metrics / "gate_prob.npy", gate)
            np.save(metrics / "anchor_physics.npy", physics)
            table = root / "runs.csv"
            pd.DataFrame([{"model": "Aligned", "seed": 201, "run_dir": run_dir.relative_to(root)}]).to_csv(table, index=False)

            out = run_boundary_negative_controls(
                run_table=table,
                cache_dir=root / "cache",
                output_dir=root / "out",
                root_dir=root,
                models="Aligned",
                controls="time_shift_boundary",
                max_control_nmi=0.50,
                max_control_ari=0.50,
                max_control_intervention_drop=0.10,
                min_positive_intervention_drop=-1.0,
                time_shift_steps=1,
                seed=1,
            )
            guard = load_json(out / "boundary_negative_controls_guard.json")

            self.assertEqual(guard["status"], "blocked_boundary_negative_controls")
            self.assertGreaterEqual(guard["n_dangerous_rows"], 1)


if __name__ == "__main__":
    unittest.main()
