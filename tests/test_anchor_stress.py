from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from main import build_parser
from windfarm_moe.anchor_stress import build_anchor_stress_caches, run_anchor_stress_guard
from windfarm_moe.utils import load_json, save_json


class AnchorStressTests(unittest.TestCase):
    def test_parser_accepts_commands(self) -> None:
        cache_args = build_parser().parse_args(
            ["anchor-stress-cache", "--source-cache-dir", "cache", "--output-cache-root", "out"]
        )
        guard_args = build_parser().parse_args(
            ["anchor-stress-guard", "--suite-root", "runs", "--cache-root", "cache", "--output-dir", "out"]
        )

        self.assertEqual(cache_args.command, "anchor-stress-cache")
        self.assertEqual(guard_args.command, "anchor-stress-guard")
        self.assertEqual(guard_args.seeds, "201,202,203")

    def test_cache_variants_modify_anchor_channels(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = _write_cache(root / "source" / "wtb_245d")

            output = build_anchor_stress_caches(
                source_cache_dir=source,
                output_cache_root=root / "anchor_cache",
                variants="no_patv,lagged_pab_wspd",
            )

            no_patv = output / "wtb_245d_no_patv"
            lagged = output / "wtb_245d_lagged_pab_wspd"
            no_patv_meta = load_json(no_patv / "metadata.json")
            no_patv_physics = np.load(no_patv / "physics.npy")
            lagged_features = np.load(lagged / "features.npy")
            source_features = np.load(source / "features.npy")

            self.assertEqual(no_patv_meta["anchor_stress_variant"], "no_patv")
            self.assertTrue(np.allclose(no_patv_physics[..., 3], 0.0))
            self.assertTrue(np.allclose(lagged_features[1:, :, 0], source_features[:-1, :, 0]))
            self.assertTrue((output / "anchor_stress_cache_manifest.json").exists())

    def test_guard_reports_claim_downgrade_when_nmi_below_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            suite = root / "runs"
            for seed, nmi in [(201, 0.5), (202, 0.6), (203, 0.55)]:
                _write_run(suite / "no_patv" / f"wtb_bal_align_force_seed{seed}", seed=seed, nmi=nmi)
            cache_root = root / "cache"
            cache_root.mkdir()
            save_json(cache_root / "anchor_stress_cache_manifest.json", {"variants": ["no_patv"]})

            output = run_anchor_stress_guard(
                suite_root=suite,
                cache_root=cache_root,
                output_dir=root / "guard",
                variants="no_patv",
                seeds="201,202,203",
                min_nmi=0.65,
            )

            summary = pd.read_csv(output / "anchor_stress_summary.csv")
            guard = load_json(output / "anchor_stress_guard.json")

            self.assertEqual(guard["status"], "complete_anchor_stress_requires_claim_downgrade")
            self.assertFalse(bool(summary.iloc[0]["nmi_gate_pass"]))
            self.assertEqual(summary.iloc[0]["claim_boundary"], "downgrade_to_declared_anchor_constrained_routing")
            self.assertTrue((output / "anchor_stress_summary.tex").exists())


def _write_cache(cache: Path) -> Path:
    cache.mkdir(parents=True)
    steps, nodes = 5, 2
    features = np.zeros((steps, nodes, 11), dtype=np.float32)
    for idx in range(features.shape[-1]):
        features[..., idx] = idx + np.arange(steps, dtype=np.float32)[:, None]
    physics = np.zeros((steps, nodes, 4), dtype=np.float32)
    for idx in range(physics.shape[-1]):
        physics[..., idx] = 10 + idx + np.arange(steps, dtype=np.float32)[:, None]
    arrays = {
        "features": features,
        "feature_mask": np.ones_like(features, dtype=np.float32),
        "target": np.ones((steps, nodes), dtype=np.float32),
        "target_mask": np.ones((steps, nodes), dtype=np.float32),
        "regime_primary": np.ones((steps, nodes), dtype=np.int16),
        "regime_primary_valid": np.ones((steps, nodes), dtype=np.float32),
        "regime_aux": np.zeros((steps, nodes), dtype=np.int16),
        "regime_aux_valid": np.ones((steps, nodes), dtype=np.float32),
        "physics": physics,
        "physics_model": physics.copy(),
        "edge_index": np.zeros((steps, nodes, 1), dtype=np.int16),
        "edge_weight": np.ones((steps, nodes, 1), dtype=np.float32),
        "coords": np.zeros((nodes, 2), dtype=np.float32),
        "time_index": np.arange(steps, dtype=np.int64),
        "node_ids": np.arange(nodes, dtype=np.int32),
    }
    for name, value in arrays.items():
        np.save(cache / f"{name}.npy", value)
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
        },
    )
    return cache


def _write_run(run_dir: Path, *, seed: int, nmi: float) -> None:
    metrics = run_dir / "test_metrics"
    metrics.mkdir(parents=True)
    save_json(run_dir / "training_summary.json", {"seed": seed, "variant_key": "bal_align_force"})
    save_json(
        metrics / "metrics.json",
        {
            "overall": {"rmse": 1.0},
            "switch_window": {"rmse": 1.2},
            "gate_alignment": {"nmi": nmi, "ari": nmi + 0.1},
            "leakage_guard": {"pass": True},
        },
    )
