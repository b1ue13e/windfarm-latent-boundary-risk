from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from main import build_parser
from windfarm_moe.operational_baselines import run_operational_baselines
from windfarm_moe.utils import load_json, save_json


class OperationalBaselineTests(unittest.TestCase):
    def test_parser_accepts_operational_baselines(self) -> None:
        args = build_parser().parse_args(["operational-baselines", "--output-dir", "out"])

        self.assertEqual(args.command, "operational-baselines")
        self.assertIn("persistence", args.baselines)

    def test_run_operational_baselines_outputs_predictions_and_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            cache = self._build_cache(root)
            output = run_operational_baselines(
                cache_dir=cache,
                output_dir=root / "operational",
                baselines="persistence,power_curve,dlinear",
                max_train_samples=120,
                max_dlinear_samples=80,
                tree_estimators=5,
            )

            summary = pd.read_csv(output / "wtb_operational_baselines.csv")
            self.assertEqual(set(summary["variant_key"]), {"persistence", "power_curve", "dlinear"})
            self.assertTrue((output / "table_wtb_operational_baselines.tex").exists())
            for key in ["persistence", "power_curve", "dlinear"]:
                run_dir = output / key
                self.assertTrue((run_dir / "metrics.json").exists())
                self.assertTrue((run_dir / "pred.npy").exists())
                metrics = load_json(run_dir / "metrics.json")
                self.assertIn("overall", metrics)
                self.assertIn("switch_window", metrics)

    def _build_cache(self, root: Path) -> Path:
        cache = root / "cache"
        cache.mkdir()
        rng = np.random.default_rng(7)
        total_steps = 90
        num_nodes = 3
        num_features = 11
        wind = rng.uniform(2.0, 14.0, size=(total_steps, num_nodes)).astype(np.float32)
        power = np.clip((wind - 3.0) ** 3 * 12.0, 0.0, 1200.0).astype(np.float32)
        power += rng.normal(0.0, 20.0, size=power.shape).astype(np.float32)
        power = np.clip(power, 0.0, None)
        features = np.zeros((total_steps, num_nodes, num_features), dtype=np.float32)
        features[..., 0] = wind
        features[..., 7] = np.where(wind > 10.5, 5.0, 0.0)
        features[..., 9] = 0.0
        features[..., 10] = power
        physics = np.zeros((total_steps, num_nodes, 4), dtype=np.float32)
        physics[..., 0] = wind
        physics[..., 1] = features[..., 7]
        physics[..., 3] = power
        regime = np.where(wind < 3.0, 0, np.where(wind < 10.5, 1, 2)).astype(np.int16)
        edge_index = np.full((total_steps, num_nodes, 1), -1, dtype=np.int16)
        edge_weight = np.zeros((total_steps, num_nodes, 1), dtype=np.float32)
        np.save(cache / "features.npy", features)
        np.save(cache / "feature_mask.npy", np.ones_like(features, dtype=np.float32))
        np.save(cache / "target.npy", power)
        np.save(cache / "target_mask.npy", np.ones_like(power, dtype=np.float32))
        np.save(cache / "regime_primary.npy", regime)
        np.save(cache / "regime_primary_valid.npy", np.ones_like(power, dtype=np.float32))
        np.save(cache / "regime_aux.npy", np.zeros_like(regime, dtype=np.int16))
        np.save(cache / "regime_aux_valid.npy", np.ones_like(power, dtype=np.float32))
        np.save(cache / "edge_index.npy", edge_index)
        np.save(cache / "edge_weight.npy", edge_weight)
        np.save(cache / "physics.npy", physics)
        np.save(cache / "coords.npy", np.zeros((num_nodes, 2), dtype=np.float32))
        np.save(cache / "time_index.npy", np.arange(total_steps, dtype=np.int64))
        np.save(cache / "node_ids.npy", np.arange(num_nodes, dtype=np.int32))
        save_json(
            cache / "metadata.json",
            {
                "dataset": "wtb",
                "feature_names": [
                    "Wspd",
                    "Wdir_sin",
                    "Wdir_cos",
                    "Ndir_sin",
                    "Ndir_cos",
                    "Etmp",
                    "Itmp",
                    "Pab_mean",
                    "Pab_std",
                    "Prtv",
                    "Patv_hist",
                ],
                "physics_names": ["Wspd", "Pab_mean", "wake_score", "Patv"],
                "primary_regime_names": ["idle", "mppt", "pitch_control", "transition"],
                "primary_num_classes": 3,
                "split_bounds": {"train": [0, 50], "val": [50, 70], "test": [70, 90]},
                "hist_len": 6,
                "pred_len": 4,
                "steps_per_hour": 6,
            },
        )
        return cache


if __name__ == "__main__":
    unittest.main()
