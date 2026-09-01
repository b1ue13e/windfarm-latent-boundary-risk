from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

from main import build_parser
from windfarm_moe.anchor_stress import (
    build_anchor_stress_caches,
    run_anchor_stress_early_warning,
    run_anchor_stress_guard,
    run_anchor_stress_training,
)
from windfarm_moe.utils import load_json, save_json


class AnchorStressTests(unittest.TestCase):
    def test_parser_accepts_commands(self) -> None:
        cache_args = build_parser().parse_args(
            ["anchor-stress-cache", "--source-cache-dir", "cache", "--output-cache-root", "out"]
        )
        guard_args = build_parser().parse_args(
            ["anchor-stress-guard", "--suite-root", "runs", "--cache-root", "cache", "--output-dir", "out"]
        )
        train_args = build_parser().parse_args(
            [
                "anchor-stress-train",
                "--cache-root",
                "cache",
                "--output-root",
                "runs",
                "--model-mode",
                "moe_phys_full",
                "--run-prefix",
                "lhb_full_anchor_stress_seed",
            ]
        )
        early_args = build_parser().parse_args(
            ["anchor-stress-early-warning", "--suite-root", "runs", "--output-dir", "out"]
        )

        self.assertEqual(cache_args.command, "anchor-stress-cache")
        self.assertEqual(train_args.command, "anchor-stress-train")
        self.assertEqual(train_args.seeds, "201,202,203,204,205")
        self.assertEqual(train_args.model_mode, "moe_phys_full")
        self.assertEqual(train_args.run_prefix, "lhb_full_anchor_stress_seed")
        self.assertEqual(guard_args.command, "anchor-stress-guard")
        self.assertEqual(guard_args.seeds, "201,202,203,204,205")
        self.assertEqual(early_args.command, "anchor-stress-early-warning")
        self.assertEqual(early_args.variants, "canonical")

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

    def test_signature_variants_remove_defining_channels_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = _write_cache(root / "source" / "wtb_245d")

            output = build_anchor_stress_caches(
                source_cache_dir=source,
                output_cache_root=root / "signature_cache",
                variants="signature_full,signature_core",
            )

            source_features = np.load(source / "features.npy")
            source_physics = np.load(source / "physics.npy")
            source_regime = np.load(source / "regime_primary.npy")

            full = output / "wtb_245d_signature_full"
            full_features = np.load(full / "features.npy")
            full_mask = np.load(full / "feature_mask.npy")
            full_physics = np.load(full / "physics.npy")
            full_physics_model = np.load(full / "physics_model.npy")
            full_meta = load_json(full / "metadata.json")

            # Label-defining channels removed from encoder features.
            self.assertTrue(np.allclose(full_features[..., 0], 0.0))  # Wspd
            self.assertTrue(np.allclose(full_features[..., 7], 0.0))  # Pab_mean
            self.assertTrue(np.allclose(full_mask[..., 0], 0.0))
            self.assertTrue(np.allclose(full_mask[..., 7], 0.0))
            # Consequence channels retained (Patv_hist, Pab_std).
            self.assertTrue(np.allclose(full_features[..., 10], source_features[..., 10]))
            self.assertTrue(np.allclose(full_features[..., 8], source_features[..., 8]))
            # Model-facing gate anchor loses Wspd/Pab_mean, keeps wake/Patv.
            self.assertTrue(np.allclose(full_physics_model[..., 0], 0.0))
            self.assertTrue(np.allclose(full_physics_model[..., 1], 0.0))
            self.assertTrue(np.allclose(full_physics_model[..., 2], source_physics[..., 2]))
            self.assertTrue(np.allclose(full_physics_model[..., 3], source_physics[..., 3]))
            # Raw physics and regime labels untouched for evaluation.
            self.assertTrue(np.allclose(full_physics, source_physics))
            self.assertTrue(np.allclose(np.load(full / "regime_primary.npy"), source_regime))
            self.assertEqual(full_meta["anchor_stress_variant"], "signature_full")

            core = output / "wtb_245d_signature_core"
            core_features = np.load(core / "features.npy")
            core_physics_model = np.load(core / "physics_model.npy")
            # Additionally removes the power channel.
            self.assertTrue(np.allclose(core_features[..., 10], 0.0))  # Patv_hist
            self.assertTrue(np.allclose(core_physics_model[..., 3], 0.0))  # Patv anchor
            self.assertTrue(np.allclose(np.load(core / "physics.npy"), source_physics))

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

    def test_training_command_writes_standard_variant_seed_runs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = _write_cache(root / "source" / "wtb_245d")
            cache_root = build_anchor_stress_caches(
                source_cache_dir=source,
                output_cache_root=root / "anchor_cache",
                variants="no_patv",
            )

            def fake_train(_bundle, run_dir, _model_config, train_config, _eval_config):
                metrics = Path(run_dir) / "test_metrics"
                metrics.mkdir(parents=True)
                save_json(
                    metrics / "metrics.json",
                    {
                        "overall": {"rmse": 2.0},
                        "switch_window": {"rmse": 2.5},
                        "gate_alignment": {"nmi": 0.7, "ari": 0.6},
                        "leakage_guard": {"pass": True},
                    },
                )
                return {"best_epoch": 1, "seed": train_config.seed}

            with patch("windfarm_moe.anchor_stress.train_model", side_effect=fake_train):
                output = run_anchor_stress_training(
                    cache_root=cache_root,
                    output_root=root / "runs",
                    variants="no_patv",
                    seeds="201,202",
                    epochs=1,
                    limit_train_batches=1,
                    limit_val_batches=1,
                )

            run_201 = output / "no_patv" / "wtb_bal_align_force_seed201"
            manifest = pd.read_csv(output / "anchor_stress_training_manifest.csv")
            summary = load_json(run_201 / "training_summary.json")

            self.assertTrue((run_201 / "test_metrics" / "metrics.json").exists())
            self.assertEqual(set(manifest["seed"]), {201, 202})
            self.assertEqual(summary["anchor_stress_variant"], "no_patv")
            self.assertEqual(summary["variant_key"], "bal_align_force")
            self.assertEqual(summary["loss_weights"]["physics_force"], 10000.0)

    def test_training_command_can_match_external_wind_full_router(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = _write_cache(root / "source" / "external_wind_la_haute_borne_chronological")
            cache_root = build_anchor_stress_caches(
                source_cache_dir=source,
                output_cache_root=root / "anchor_cache",
                variants="no_patv",
            )

            def fake_train(_bundle, run_dir, _model_config, train_config, _eval_config):
                metrics = Path(run_dir) / "test_metrics"
                metrics.mkdir(parents=True)
                save_json(
                    metrics / "metrics.json",
                    {
                        "overall": {"rmse": 2.0},
                        "switch_window": {"rmse": 2.5},
                        "gate_alignment": {"nmi": 0.9, "ari": 0.8},
                        "leakage_guard": {"pass": True},
                    },
                )
                return {"best_epoch": 1, "seed": train_config.seed}

            with patch("windfarm_moe.anchor_stress.train_model", side_effect=fake_train):
                output = run_anchor_stress_training(
                    cache_root=cache_root,
                    output_root=root / "runs",
                    variants="no_patv",
                    seeds="201",
                    epochs=1,
                    model_mode="moe_phys_full",
                    run_prefix="lhb_full_anchor_stress_seed",
                )

            run_201 = output / "no_patv" / "lhb_full_anchor_stress_seed201"
            summary = load_json(run_201 / "training_summary.json")

            self.assertTrue((run_201 / "test_metrics" / "metrics.json").exists())
            self.assertEqual(summary["model_mode"], "moe_phys_full")
            self.assertEqual(summary["variant_key"], "full")
            self.assertEqual(summary["label"], "Physics-Aligned MoE")
            self.assertEqual(summary["loss_weights"]["aux"], 250.0)
            self.assertEqual(summary["loss_weights"]["smooth"], 0.05)

    def test_early_warning_audit_reports_gate_value_under_label_delay(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            run_dir = root / "runs" / "wtb_bal_align_force_seed201"
            _write_early_warning_run(run_dir)

            output = run_anchor_stress_early_warning(
                suite_root=root / "runs",
                output_dir=root / "early",
                variants="canonical",
                seeds="201",
                early_window_steps=2,
                pretrigger_steps="1,2",
                delay_steps="1,2",
                availability_rates="1.0,0.5",
                noise_levels="0.1:0.1",
                min_delay_recall_gain=0.10,
                min_low_availability_recall_gain=0.10,
            )
            guard = load_json(output / "anchor_stress_early_warning_guard.json")
            summary = pd.read_csv(output / "anchor_stress_early_warning_summary.csv")
            delay = summary[summary["scenario"] == "label_delay"].sort_values("degradation_level").iloc[-1]

            self.assertEqual(guard["status"], "complete_anchor_stress_supports_label_degradation_value")
            self.assertTrue(guard["checks"]["gate_beats_delayed_threshold_labels"])
            self.assertGreater(float(delay["gate_recall_mean"]), float(delay["threshold_recall_mean"]))
            self.assertTrue((output / "anchor_stress_early_warning_summary.tex").exists())
            self.assertTrue((output / "README.md").exists())


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
            "primary_num_classes": 3,
            "pred_len": 1,
            "steps_per_hour": 6,
        },
    )
    return cache


def _write_early_warning_run(run_dir: Path) -> None:
    metrics = run_dir / "test_metrics"
    metrics.mkdir(parents=True)
    regime = np.array(
        [
            [1, 1],
            [1, 1],
            [1, 1],
            [2, 1],
            [2, 1],
            [2, 2],
            [2, 2],
            [1, 2],
        ],
        dtype=np.int16,
    )
    gate = np.zeros((regime.shape[0], regime.shape[1], 3), dtype=np.float32)
    for row in range(regime.shape[0]):
        for node in range(regime.shape[1]):
            gate[row, node, regime[row, node]] = 0.95
            gate[row, node, 0] += 0.05
    physics = np.zeros((regime.shape[0], regime.shape[1], 4), dtype=np.float32)
    physics[..., 0] = np.where(regime == 2, 12.0, 8.0)
    physics[..., 1] = np.where(regime == 2, 4.0, 1.0)
    np.save(metrics / "gate_prob.npy", gate)
    np.save(metrics / "regime_primary.npy", regime)
    np.save(metrics / "regime_primary_valid.npy", np.ones_like(regime, dtype=np.float32))
    np.save(metrics / "anchor_physics.npy", physics)


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
