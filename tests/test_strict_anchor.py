from __future__ import annotations

import tempfile
import unittest
import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import torch

from main import build_parser
from windfarm_moe.strict_anchor import patch_strict_anchor_mask
from windfarm_moe.utils import load_json, save_json


def _load_anchor_stress_module():
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "build_anchor_only_stress_comparison.py"
    spec = importlib.util.spec_from_file_location("anchor_stress_script", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class StrictAnchorMaskTests(unittest.TestCase):
    def test_parser_accepts_strict_anchor_mask_command(self) -> None:
        args = build_parser().parse_args(["strict-anchor-mask-cache", "--cache-dir", "cache"])

        self.assertEqual(args.command, "strict-anchor-mask-cache")
        self.assertEqual(args.cache_dir, "cache")

    def test_patch_removes_regime_valid_where_anchor_features_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = Path(temp_dir) / "cache"
            cache.mkdir()
            save_json(
                cache / "metadata.json",
                {
                    "feature_names": ["Wspd", "Pab_mean", "Etmp"],
                    "split_bounds": {"train": [0, 2], "val": [2, 3], "test": [3, 4]},
                },
            )
            feature_mask = np.ones((4, 2, 3), dtype=np.float32)
            feature_mask[1, 0, 0] = 0.0
            feature_mask[2, 1, 1] = 0.0
            regime_valid = np.ones((4, 2), dtype=np.float32)
            aux_valid = np.ones((4, 2), dtype=np.float32)
            np.save(cache / "feature_mask.npy", feature_mask)
            np.save(cache / "regime_primary_valid.npy", regime_valid)
            np.save(cache / "regime_aux_valid.npy", aux_valid)

            output_dir = patch_strict_anchor_mask(cache, output_dir=cache / "patch_report")

            patched = np.load(cache / "regime_primary_valid.npy")
            patched_aux = np.load(cache / "regime_aux_valid.npy")
            metadata = load_json(cache / "metadata.json")
            report = load_json(output_dir / "strict_anchor_mask_patch_report.json")

            self.assertEqual(float(patched[1, 0]), 0.0)
            self.assertEqual(float(patched[2, 1]), 0.0)
            self.assertEqual(float(patched.sum()), 6.0)
            self.assertEqual(float(patched_aux.sum()), 6.0)
            self.assertEqual(metadata["strict_anchor_mask_patch"]["removed_regime_valid"], 2)
            self.assertEqual(report["strict_anchor_violations_after_patch"], 0)

    def test_anchor_stress_new_scenarios_mutate_only_replay_batch(self) -> None:
        module = _load_anchor_stress_module()
        batch = {
            "anchor_physics": torch.tensor(
                [
                    [[10.0, 1.0, 0.0, 100.0], [11.0, 4.0, 0.0, 200.0]],
                    [[8.0, 0.5, 0.0, 80.0], [12.0, 5.0, 0.0, 240.0]],
                ],
                dtype=torch.float32,
            ),
            "regime_primary": torch.tensor([[1, 2], [1, 2]], dtype=torch.int64),
            "regime_primary_valid": torch.ones((2, 2), dtype=torch.float32),
        }
        original = batch["anchor_physics"].clone()

        for scenario in [
            "anchor_boundary_noise_0p25std",
            "anchor_boundary_noise_1p0std",
            "domain_shift",
            "few_label_10pct",
            "partial_label_pitch_only",
        ]:
            mutated = module._mutate_anchor(
                batch,
                scenario,
                wspd_idx=0,
                pab_idx=1,
                rated_wind=10.5,
                pitch_threshold=2.0,
                boundary_band=1.0,
                wspd_std=2.0,
                pab_std=1.0,
            )
            self.assertTrue(torch.equal(batch["anchor_physics"], original))
            self.assertFalse(torch.equal(mutated["anchor_physics"], original), scenario)

    def test_anchor_necessity_summary_scopes_trainable_claim_to_stress(self) -> None:
        module = _load_anchor_stress_module()
        summary = pd.DataFrame(
            [
                {
                    "scenario": "actual",
                    "model": module.PROPOSED,
                    "overall_rmse_mean": 2.0,
                    "pitch_control_rmse_mean": 2.0,
                    "boundary_rmse_mean": 2.0,
                    "nmi_mean": 0.4,
                    "ari_mean": 0.3,
                    "dominant_flip_rate_mean": 0.0,
                },
                {
                    "scenario": "actual",
                    "model": module.ANCHOR_ONLY,
                    "overall_rmse_mean": 1.9,
                    "pitch_control_rmse_mean": 2.1,
                    "boundary_rmse_mean": 2.1,
                    "nmi_mean": 0.8,
                    "ari_mean": 0.7,
                    "dominant_flip_rate_mean": 0.0,
                },
                {
                    "scenario": "anchor_boundary_missing",
                    "model": module.PROPOSED,
                    "overall_rmse_mean": 2.1,
                    "pitch_control_rmse_mean": 2.2,
                    "boundary_rmse_mean": 2.2,
                    "nmi_mean": 0.35,
                    "ari_mean": 0.25,
                    "dominant_flip_rate_mean": 0.1,
                },
                {
                    "scenario": "anchor_boundary_missing",
                    "model": module.ANCHOR_ONLY,
                    "overall_rmse_mean": 3.0,
                    "pitch_control_rmse_mean": 3.2,
                    "boundary_rmse_mean": 3.3,
                    "nmi_mean": 0.2,
                    "ari_mean": 0.1,
                    "dominant_flip_rate_mean": 0.7,
                },
            ]
        )
        degradation = pd.DataFrame(
            [
                {
                    "scenario": "anchor_boundary_missing",
                    "model": module.PROPOSED,
                    "delta_overall_rmse_mean": 0.1,
                    "delta_pitch_control_rmse_mean": 0.2,
                    "delta_boundary_rmse_mean": 0.2,
                    "drop_nmi_mean": 0.05,
                    "drop_ari_mean": 0.05,
                },
                {
                    "scenario": "anchor_boundary_missing",
                    "model": module.ANCHOR_ONLY,
                    "delta_overall_rmse_mean": 1.1,
                    "delta_pitch_control_rmse_mean": 1.1,
                    "delta_boundary_rmse_mean": 1.2,
                    "drop_nmi_mean": 0.6,
                    "drop_ari_mean": 0.6,
                },
            ]
        )
        effects = pd.DataFrame(
            [
                {
                    "scenario": "anchor_boundary_missing",
                    "n_seed_pairs": 5,
                    "proposed_minus_anchor_only_delta_overall_rmse_mean": -1.0,
                    "proposed_minus_anchor_only_delta_pitch_control_rmse_mean": -0.9,
                    "proposed_minus_anchor_only_delta_boundary_rmse_mean": -1.0,
                    "proposed_minus_anchor_only_drop_nmi_mean": -0.55,
                }
            ]
        )

        necessity = module._necessity_summary(summary, degradation, effects, ["actual", "anchor_boundary_missing"])

        actual = necessity[necessity["scenario"] == "actual"].iloc[0]
        missing = necessity[necessity["scenario"] == "anchor_boundary_missing"].iloc[0]
        self.assertTrue(bool(actual["anchor_only_wins_clean_semantic_nmi_ari"]))
        self.assertFalse(bool(actual["trainable_router_necessary"]))
        self.assertTrue(bool(missing["trainable_router_necessary"]))
        self.assertEqual(missing["claim_scope"], "robustness_only")


if __name__ == "__main__":
    unittest.main()
