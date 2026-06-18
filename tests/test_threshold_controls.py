from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from main import build_parser
from windfarm_moe.threshold_controls import (
    REVIEWER_STAT_REQUIRED_FILES,
    THRESHOLD_CONTROL_SPECS,
    THRESHOLD_SEMANTIC_REQUIRED_FILES,
    run_threshold_label_validity_audit,
    run_threshold_controls_evidence_guard,
    run_threshold_controls_guard,
    run_threshold_controls_semantic_guard,
)
from windfarm_moe.utils import load_json, save_json


class ThresholdControlsGuardTests(unittest.TestCase):
    def _write_strict_cache(self, root: Path, cache_root: str = "cache") -> Path:
        cache_dir = root / cache_root / "wtb_245d"
        cache_dir.mkdir(parents=True, exist_ok=True)
        physics = np.zeros((432, 2, 4), dtype=np.float32)
        regimes = np.zeros((432, 2), dtype=np.int16)
        flat_physics = physics.reshape(-1, 4)
        flat_regimes = regimes.reshape(-1)
        blocks = [
            (0, 180, 2.0, 90.0, 0),  # idle
            (180, 360, 8.0, 1.0, 1),  # mppt dropped by rated_wind=7.0
            (360, 540, 8.0, 1.0, 1),  # mppt dropped by pitch_threshold=0.5
            (540, 700, 12.0, 10.0, 2),  # pitch dropped by rated_wind=13.0 and pitch_threshold=20.0
            (700, 864, 14.0, 30.0, 2),  # pitch retained by high-threshold controls
        ]
        for start, end, wspd, pab, regime in blocks:
            flat_physics[start:end, 0] = wspd
            flat_physics[start:end, 1] = pab
            flat_regimes[start:end] = regime
        np.save(cache_dir / "physics.npy", physics)
        np.save(cache_dir / "regime_primary.npy", regimes)
        np.save(cache_dir / "feature_mask.npy", np.ones((432, 2, 11), dtype=np.float32))
        np.save(cache_dir / "regime_primary_valid.npy", np.ones((432, 2), dtype=np.float32))
        save_json(
            cache_dir / "metadata.json",
            {
                "dataset": "wtb",
                "feature_names": ["Wspd", "Pab_mean"],
                "physics_names": ["Wspd", "Pab_mean", "wake_score", "Patv"],
                "split_bounds": {"train": [0, 144], "val": [144, 288], "test": [288, 432]},
                "train_days": 1,
                "val_days": 1,
                "test_days": 1,
                "hist_len": 3,
                "pred_len": 2,
                "wtb_thresholds": {"rated_wind": 10.5, "pitch_threshold": 2.0},
                "strict_anchor_mask_patch": {"removed_regime_valid": 0},
            },
        )
        return cache_dir

    def _write_complete_run(self, run_dir: Path, variant_key: str, seed: int) -> None:
        spec = THRESHOLD_CONTROL_SPECS[variant_key]
        run_dir.mkdir(parents=True, exist_ok=True)
        save_json(
            run_dir / "training_summary.json",
            {
                "seed": seed,
                "variant_key": variant_key,
                "experiment_group": "sensitivity",
                "model_mode": spec["mode"],
                "setting_group": spec["setting_group"],
                "setting_value": spec["setting_value"],
                "setting_label": spec["setting_label"],
            },
        )
        metrics_dir = run_dir / "test_metrics"
        metrics_dir.mkdir(parents=True, exist_ok=True)
        save_json(
            metrics_dir / "metrics.json",
            {
                "overall": {"rmse": 1.0},
                "switch_window": {"rmse": 1.1},
                "gate_alignment": {"nmi": 0.5, "ari": 0.4},
            },
        )

    def _write_reviewer_pack(self, pack_dir: Path, n_runs: int) -> None:
        pack_dir.mkdir(parents=True, exist_ok=True)
        save_json(pack_dir / "reviewer_stat_pack_config.json", {"n_runs": n_runs})
        for filename in REVIEWER_STAT_REQUIRED_FILES:
            path = pack_dir / filename
            path.parent.mkdir(parents=True, exist_ok=True)
            if filename == "reviewer_stat_pack_config.json":
                continue
            path.write_text("placeholder\n", encoding="utf-8")

    def _write_positive_mechanism(self, mechanism_dir: Path) -> None:
        mechanism_dir.mkdir(parents=True, exist_ok=True)
        (mechanism_dir / "mechanism_intervention_summary.csv").write_text(
            "intervention,n_runs,nmi_mean,ari_mean\n"
            "actual,5,0.87,0.91\n"
            "anchor_boundary_zero,5,0.17,0.05\n",
            encoding="utf-8",
        )
        (mechanism_dir / "mechanism_intervention_effects.csv").write_text(
            "intervention,n_runs,drop_nmi_mean,drop_ari_mean\n"
            "anchor_boundary_zero,5,0.70,0.86\n",
            encoding="utf-8",
        )

    def _write_threshold_mechanism_raw(self, mechanism_dir: Path, variant_keys: list[str], seeds: list[int]) -> None:
        mechanism_dir.mkdir(parents=True, exist_ok=True)
        rows = [
            "variant_key,seed,run_dir,intervention,nmi,ari,replay_status",
        ]
        for variant_key in variant_keys:
            for seed in seeds:
                run_dir = f"suite/wtb_{variant_key}_seed{seed}"
                rows.append(f"{variant_key},{seed},{run_dir},actual,0.52,0.41,matches_reference")
                rows.append(f"{variant_key},{seed},{run_dir},anchor_boundary_zero,0.48,0.39,")
        (mechanism_dir / "mechanism_intervention_raw.csv").write_text("\n".join(rows) + "\n", encoding="utf-8")

    def test_parser_accepts_threshold_controls_guard_command(self) -> None:
        args = build_parser().parse_args(
            [
                "threshold-controls-guard",
                "--output-dir",
                "out",
                "--variant-keys",
                "sens_rated_7p0,sens_rated_13p0,sens_pitch_0p5,sens_pitch_20p0",
                "--seeds",
                "201",
            ]
        )

        self.assertEqual(args.command, "threshold-controls-guard")
        self.assertEqual(args.seeds, "201")

    def test_parser_accepts_threshold_controls_semantic_guard_command(self) -> None:
        args = build_parser().parse_args(
            [
                "threshold-controls-semantic-guard",
                "--output-dir",
                "out",
                "--mechanism-dir",
                "mechanism",
                "--positive-mechanism-dir",
                "positive",
                "--variant-keys",
                "sens_rated_7p0,sens_pitch_0p5",
                "--seeds",
                "201",
            ]
        )

        self.assertEqual(args.command, "threshold-controls-semantic-guard")
        self.assertEqual(args.mechanism_dir, "mechanism")

    def test_parser_accepts_threshold_controls_evidence_boundary_guard_arg(self) -> None:
        args = build_parser().parse_args(
            [
                "threshold-controls-evidence-guard",
                "--output-dir",
                "out",
                "--boundary-negative-guard-dir",
                "boundary",
                "--seeds",
                "201",
            ]
        )

        self.assertEqual(args.command, "threshold-controls-evidence-guard")
        self.assertEqual(args.boundary_negative_guard_dir, "boundary")

    def test_parser_accepts_threshold_label_validity_audit(self) -> None:
        args = build_parser().parse_args(
            [
                "threshold-label-validity-audit",
                "--output-dir",
                "out",
                "--rated-wind-grid",
                "10.0,10.5,11.0",
                "--pitch-threshold-grid",
                "1.5,2.0,2.5",
                "--seeds",
                "201",
            ]
        )

        self.assertEqual(args.command, "threshold-label-validity-audit")
        self.assertEqual(args.rated_wind_grid, "10.0,10.5,11.0")

    def test_threshold_label_validity_audit_relabels_saved_gates(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            cache_dir = root / "cache" / "wtb_245d"
            cache_dir.mkdir(parents=True)
            physics = np.zeros((6, 2, 4), dtype=np.float32)
            physics[:3, :, 0] = 8.0
            physics[:3, :, 1] = 1.0
            physics[3:, :, 0] = 12.0
            physics[3:, :, 1] = 3.0
            np.save(cache_dir / "physics.npy", physics)
            save_json(
                cache_dir / "metadata.json",
                {
                    "dataset": "wtb",
                    "physics_names": ["Wspd", "Pab_mean", "wake_score", "Patv"],
                    "wtb_thresholds": {"rated_wind": 10.5, "pitch_threshold": 2.0},
                },
            )
            run_dir = root / "runs" / "boundary_seed201"
            metrics = run_dir / "test_metrics"
            metrics.mkdir(parents=True)
            anchor_index = np.arange(6, dtype=np.int64)
            gate = np.zeros((6, 2, 3), dtype=np.float32)
            gate[:3, :, 1] = 1.0
            gate[3:, :, 2] = 1.0
            np.save(metrics / "anchor_index.npy", anchor_index)
            np.save(metrics / "gate_prob.npy", gate)
            run_table = root / "runs.csv"
            pd.DataFrame(
                [
                    {
                        "dataset": "wtb",
                        "model": "Boundary-forced router",
                        "seed": 201,
                        "variant_key": "bal_align_force",
                        "experiment_group": "ablation",
                        "run_dir": run_dir.relative_to(root),
                    }
                ]
            ).to_csv(run_table, index=False)
            boundary_guard = root / "boundary_negative"
            boundary_guard.mkdir()
            save_json(
                boundary_guard / "boundary_negative_controls_guard.json",
                {
                    "status": "passed_boundary_negative_controls",
                    "checks": {
                        "each_negative_control_changes_shared_labels": True,
                        "no_negative_control_reproduces_high_nmi_or_ari_and_intervention_drop": True,
                    },
                },
            )

            output_dir = run_threshold_label_validity_audit(
                run_table=run_table,
                cache_dir=cache_dir,
                output_dir=root / "threshold_validity",
                root_dir=root,
                models="Boundary-forced router",
                seeds="201",
                boundary_negative_guard_dir=boundary_guard,
            )
            guard = load_json(output_dir / "threshold_label_validity_guard.json")
            summary = pd.read_csv(output_dir / "threshold_label_validity_summary.csv")

            self.assertEqual(guard["status"], "passed_threshold_label_validity_audit")
            self.assertEqual(guard["complete_grid_cells"], 9)
            self.assertTrue((output_dir / "control_taxonomy.csv").exists())
            self.assertTrue((output_dir / "table_threshold_label_validity.tex").exists())
            self.assertEqual(len(summary), 9)
            self.assertGreater(float(summary["nmi_mean"].min()), 0.99)

    def test_threshold_controls_guard_ready_when_runs_are_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_strict_cache(root)

            output_dir = run_threshold_controls_guard(
                output_dir=root / "guard",
                root_dir=root,
                cache_root="cache",
                suite_dir=root / "suite",
                train_days=1,
                val_days=1,
                test_days=1,
                hist_len=3,
                pred_len=2,
                seeds="201",
            )
            guard = load_json(output_dir / "threshold_controls_guard.json")

            self.assertEqual(guard["status"], "ready_to_execute_training")
            self.assertEqual(guard["expected_runs"], 4)
            self.assertEqual(guard["missing_runs"], 4)
            self.assertTrue(guard["checks"]["wrong_threshold_control_variants_included"])

    def test_threshold_controls_guard_completes_when_all_runs_exist(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_strict_cache(root)
            suite = root / "suite"
            for variant_key in THRESHOLD_CONTROL_SPECS:
                self._write_complete_run(suite / f"wtb_{variant_key}_seed201", variant_key, 201)

            output_dir = run_threshold_controls_guard(
                output_dir=root / "guard",
                root_dir=root,
                cache_root="cache",
                suite_dir=suite,
                train_days=1,
                val_days=1,
                test_days=1,
                hist_len=3,
                pred_len=2,
                seeds="201",
            )
            guard = load_json(output_dir / "threshold_controls_guard.json")

            self.assertEqual(guard["status"], "complete_ready_for_threshold_control_table")
            self.assertEqual(guard["complete_runs"], 4)

    def test_threshold_controls_guard_blocks_missing_required_controls(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_strict_cache(root)

            output_dir = run_threshold_controls_guard(
                output_dir=root / "guard",
                root_dir=root,
                cache_root="cache",
                suite_dir=root / "suite",
                train_days=1,
                val_days=1,
                test_days=1,
                hist_len=3,
                pred_len=2,
                variant_keys="sens_rated_7p0",
                seeds="201",
            )
            guard = load_json(output_dir / "threshold_controls_guard.json")

            self.assertEqual(guard["status"], "blocked_missing_wrong_threshold_controls")
            self.assertFalse(guard["checks"]["wrong_threshold_control_variants_included"])

    def test_threshold_controls_semantic_guard_passes_when_wrong_threshold_fails_to_copy_semantics(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            variants = ["sens_rated_7p0", "sens_rated_13p0", "sens_pitch_0p5", "sens_pitch_20p0"]
            self._write_threshold_mechanism_raw(root / "mechanism", variants, [201])
            self._write_positive_mechanism(root / "positive")

            output_dir = run_threshold_controls_semantic_guard(
                output_dir=root / "semantic_guard",
                mechanism_dir=root / "mechanism",
                positive_mechanism_dir=root / "positive",
                seeds="201",
            )
            guard = load_json(output_dir / "threshold_controls_semantic_guard.json")

            self.assertEqual(guard["status"], "passed_wrong_threshold_negative_control")
            self.assertEqual(guard["complete_pairs"], 4)
            self.assertTrue(guard["checks"]["wrong_threshold_actual_nmi_below_positive"])
            self.assertTrue(guard["checks"]["wrong_threshold_boundary_drop_below_positive"])

    def test_threshold_controls_semantic_guard_fails_when_wrong_threshold_preserves_semantics(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            variants = ["sens_rated_7p0", "sens_rated_13p0", "sens_pitch_0p5", "sens_pitch_20p0"]
            mechanism_dir = root / "mechanism"
            mechanism_dir.mkdir(parents=True)
            rows = ["variant_key,seed,run_dir,intervention,nmi,ari,replay_status"]
            for variant_key in variants:
                run_dir = f"suite/wtb_{variant_key}_seed201"
                rows.append(f"{variant_key},201,{run_dir},actual,0.83,0.80,matches_reference")
                rows.append(f"{variant_key},201,{run_dir},anchor_boundary_zero,0.28,0.21,")
            (mechanism_dir / "mechanism_intervention_raw.csv").write_text("\n".join(rows) + "\n", encoding="utf-8")
            self._write_positive_mechanism(root / "positive")

            output_dir = run_threshold_controls_semantic_guard(
                output_dir=root / "semantic_guard",
                mechanism_dir=mechanism_dir,
                positive_mechanism_dir=root / "positive",
                seeds="201",
            )
            guard = load_json(output_dir / "threshold_controls_semantic_guard.json")

            self.assertEqual(guard["status"], "failed_wrong_threshold_preserves_canonical_routing")
            self.assertFalse(guard["checks"]["wrong_threshold_actual_nmi_below_positive"])

    def test_threshold_controls_evidence_guard_requires_semantic_negative_control(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_strict_cache(root)
            suite = root / "suite"
            for variant_key in THRESHOLD_CONTROL_SPECS:
                self._write_complete_run(suite / f"wtb_{variant_key}_seed201", variant_key, 201)
            self._write_reviewer_pack(root / "reviewer", n_runs=4)

            output_dir = run_threshold_controls_evidence_guard(
                output_dir=root / "evidence_guard",
                root_dir=root,
                cache_root="cache",
                suite_dir=suite,
                reviewer_pack_dir=root / "reviewer",
                semantic_guard_dir=root / "semantic_guard_missing",
                boundary_negative_guard_dir=root / "boundary_negative_missing",
                train_days=1,
                val_days=1,
                test_days=1,
                hist_len=3,
                pred_len=2,
                seeds="201",
            )
            guard = load_json(output_dir / "threshold_controls_evidence_guard.json")

            self.assertEqual(guard["status"], "blocked_missing_threshold_semantic_negative_control")
            self.assertFalse(guard["checks"]["all_required_semantic_guard_files_present"])

    def test_threshold_controls_evidence_guard_completes_with_semantic_negative_control(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_strict_cache(root)
            suite = root / "suite"
            for variant_key in THRESHOLD_CONTROL_SPECS:
                self._write_complete_run(suite / f"wtb_{variant_key}_seed201", variant_key, 201)
            self._write_reviewer_pack(root / "reviewer", n_runs=4)
            for filename in THRESHOLD_SEMANTIC_REQUIRED_FILES:
                path = root / "semantic_guard" / filename
                path.parent.mkdir(parents=True, exist_ok=True)
                if filename.endswith(".json"):
                    save_json(
                        path,
                        {"status": "passed_wrong_threshold_negative_control", "complete_pairs": 4},
                    )
                else:
                    path.write_text("placeholder\n", encoding="utf-8")

            output_dir = run_threshold_controls_evidence_guard(
                output_dir=root / "evidence_guard",
                root_dir=root,
                cache_root="cache",
                suite_dir=suite,
                reviewer_pack_dir=root / "reviewer",
                semantic_guard_dir=root / "semantic_guard",
                train_days=1,
                val_days=1,
                test_days=1,
                hist_len=3,
                pred_len=2,
                seeds="201",
            )
            guard = load_json(output_dir / "threshold_controls_evidence_guard.json")

            self.assertEqual(guard["status"], "complete_ready_for_threshold_control_evidence")
            self.assertTrue(guard["checks"]["semantic_guard_passed"])

    def test_threshold_controls_evidence_guard_accepts_boundary_negative_controls(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_strict_cache(root)
            suite = root / "suite"
            for variant_key in THRESHOLD_CONTROL_SPECS:
                self._write_complete_run(suite / f"wtb_{variant_key}_seed201", variant_key, 201)
            self._write_reviewer_pack(root / "reviewer", n_runs=4)
            boundary_guard = root / "boundary_negative"
            boundary_guard.mkdir(parents=True, exist_ok=True)
            save_json(
                boundary_guard / "boundary_negative_controls_guard.json",
                {
                    "status": "passed_boundary_negative_controls",
                    "checks": {
                        "each_negative_control_changes_shared_labels": True,
                        "no_negative_control_reproduces_high_nmi_or_ari_and_intervention_drop": True,
                    },
                },
            )

            output_dir = run_threshold_controls_evidence_guard(
                output_dir=root / "evidence_guard",
                root_dir=root,
                cache_root="cache",
                suite_dir=suite,
                reviewer_pack_dir=root / "reviewer",
                semantic_guard_dir=root / "semantic_guard_missing",
                boundary_negative_guard_dir=boundary_guard,
                train_days=1,
                val_days=1,
                test_days=1,
                hist_len=3,
                pred_len=2,
                seeds="201",
            )
            guard = load_json(output_dir / "threshold_controls_evidence_guard.json")

            self.assertEqual(guard["status"], "complete_ready_for_threshold_control_evidence")
            self.assertFalse(guard["checks"]["all_required_semantic_guard_files_present"])
            self.assertFalse(guard["checks"]["semantic_guard_passed"])
            self.assertTrue(guard["checks"]["boundary_negative_guard_passed"])
            self.assertTrue(guard["checks"]["semantic_negative_control_passed"])


if __name__ == "__main__":
    unittest.main()
