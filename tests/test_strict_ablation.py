from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np

from main import build_parser
from windfarm_moe.strict_ablation import run_strict_ablation_evidence_guard, run_strict_ablation_guard
from windfarm_moe.utils import load_json, save_json


class StrictAblationGuardTests(unittest.TestCase):
    def _write_strict_cache(self, root: Path, cache_root: str = "cache") -> Path:
        cache_dir = root / cache_root / "wtb_245d"
        cache_dir.mkdir(parents=True, exist_ok=True)
        np.save(cache_dir / "feature_mask.npy", np.ones((432, 2, 2), dtype=np.float32))
        np.save(cache_dir / "regime_primary_valid.npy", np.ones((432, 2), dtype=np.float32))
        save_json(
            cache_dir / "metadata.json",
            {
                "dataset": "wtb",
                "feature_names": ["Wspd", "Pab_mean"],
                "split_bounds": {"train": [0, 144], "val": [144, 288], "test": [288, 432]},
                "train_days": 1,
                "val_days": 1,
                "test_days": 1,
                "hist_len": 3,
                "pred_len": 2,
                "strict_anchor_mask_patch": {"removed_regime_valid": 0},
            },
        )
        return cache_dir

    def _write_complete_run(self, run_dir: Path, variant_key: str, seed: int, mode: str) -> None:
        run_dir.mkdir(parents=True, exist_ok=True)
        save_json(
            run_dir / "training_summary.json",
            {
                "seed": seed,
                "variant_key": variant_key,
                "experiment_group": "ablation",
                "model_mode": mode,
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

    def _write_gate_artifacts(self, gate_dir: Path, n_runs: int = 3, gate_status: str = "passed") -> None:
        (gate_dir / "checkpoint_replay").mkdir(parents=True, exist_ok=True)
        (gate_dir / "mechanism_intervention").mkdir(parents=True, exist_ok=True)
        save_json(gate_dir / "mechanism_evidence_gate_config.json", {"gate_status": gate_status, "n_audited_runs": n_runs})
        for path in [
            gate_dir / "mechanism_gate_run_table.csv",
            gate_dir / "checkpoint_replay" / "checkpoint_replay_audit.csv",
            gate_dir / "checkpoint_replay" / "checkpoint_replay_summary.csv",
            gate_dir / "mechanism_intervention" / "mechanism_intervention_effects.csv",
        ]:
            path.write_text("model,value\nm,1\n", encoding="utf-8")

    def test_parser_accepts_strict_ablation_guard_command(self) -> None:
        args = build_parser().parse_args(
            [
                "strict-ablation-guard",
                "--output-dir",
                "out",
                "--variant-keys",
                "bal_align_force,context_align_force,anchor_only",
                "--seeds",
                "201",
            ]
        )

        self.assertEqual(args.command, "strict-ablation-guard")
        self.assertEqual(args.variant_keys, "bal_align_force,context_align_force,anchor_only")

    def test_parser_accepts_strict_ablation_evidence_guard_command(self) -> None:
        args = build_parser().parse_args(
            [
                "strict-ablation-evidence-guard",
                "--output-dir",
                "out",
                "--variant-keys",
                "bal_align_force,context_align_force,anchor_only",
                "--seeds",
                "201",
            ]
        )

        self.assertEqual(args.command, "strict-ablation-evidence-guard")
        self.assertEqual(args.gate_variant_keys, "bal_align_force,context_align_force,anchor_only")

    def test_strict_ablation_guard_ready_when_runs_are_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_strict_cache(root)

            output_dir = run_strict_ablation_guard(
                output_dir=root / "guard",
                root_dir=root,
                cache_root="cache",
                suite_dir=root / "suite",
                train_days=1,
                val_days=1,
                test_days=1,
                hist_len=3,
                pred_len=2,
                variant_keys="bal_align_force,context_align_force,anchor_only",
                seeds="201",
            )
            guard = load_json(output_dir / "strict_ablation_guard.json")

            self.assertEqual(guard["status"], "ready_to_execute_training")
            self.assertEqual(guard["expected_runs"], 3)
            self.assertEqual(guard["missing_runs"], 3)
            self.assertTrue(guard["checks"]["routing_control_variants_included"])

    def test_strict_ablation_guard_completes_when_all_runs_exist(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_strict_cache(root)
            suite = root / "suite"
            for variant_key, mode in {
                "bal_align_force": "moe_full_no_aux",
                "context_align_force": "moe_context_align",
                "anchor_only": "moe_anchor_only",
            }.items():
                self._write_complete_run(suite / f"wtb_{variant_key}_seed201", variant_key, 201, mode)

            output_dir = run_strict_ablation_guard(
                output_dir=root / "guard",
                root_dir=root,
                cache_root="cache",
                suite_dir=suite,
                train_days=1,
                val_days=1,
                test_days=1,
                hist_len=3,
                pred_len=2,
                variant_keys="bal_align_force,context_align_force,anchor_only",
                seeds="201",
            )
            guard = load_json(output_dir / "strict_ablation_guard.json")

            self.assertEqual(guard["status"], "complete_ready_for_strict_ablation_table")
            self.assertEqual(guard["complete_runs"], 3)

    def test_strict_ablation_guard_blocks_missing_routing_controls(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_strict_cache(root)

            output_dir = run_strict_ablation_guard(
                output_dir=root / "guard",
                root_dir=root,
                cache_root="cache",
                suite_dir=root / "suite",
                train_days=1,
                val_days=1,
                test_days=1,
                hist_len=3,
                pred_len=2,
                variant_keys="bal_align_force",
                seeds="201",
            )
            guard = load_json(output_dir / "strict_ablation_guard.json")

            self.assertEqual(guard["status"], "blocked_missing_routing_controls")
            self.assertFalse(guard["checks"]["routing_control_variants_included"])

    def test_strict_ablation_evidence_guard_counts_missing_runs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_strict_cache(root)

            output_dir = run_strict_ablation_evidence_guard(
                output_dir=root / "evidence",
                root_dir=root,
                cache_root="cache",
                suite_dir=root / "suite",
                train_days=1,
                val_days=1,
                test_days=1,
                hist_len=3,
                pred_len=2,
                variant_keys="bal_align_force,context_align_force,anchor_only",
                seeds="201",
            )
            guard = load_json(output_dir / "strict_ablation_evidence_guard.json")

            self.assertEqual(guard["status"], "ready_to_execute_training")
            self.assertEqual(guard["expected_runs"], 3)
            self.assertEqual(guard["missing_runs"], 3)

    def test_strict_ablation_evidence_guard_blocks_missing_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_strict_cache(root)
            suite = root / "suite"
            for variant_key, mode in {
                "bal_align_force": "moe_full_no_aux",
                "context_align_force": "moe_context_align",
                "anchor_only": "moe_anchor_only",
            }.items():
                self._write_complete_run(suite / f"wtb_{variant_key}_seed201", variant_key, 201, mode)

            output_dir = run_strict_ablation_evidence_guard(
                output_dir=root / "evidence",
                root_dir=root,
                cache_root="cache",
                suite_dir=suite,
                routing_gate_dir=root / "missing_gate",
                train_days=1,
                val_days=1,
                test_days=1,
                hist_len=3,
                pred_len=2,
                variant_keys="bal_align_force,context_align_force,anchor_only",
                seeds="201",
            )
            guard = load_json(output_dir / "strict_ablation_evidence_guard.json")

            self.assertEqual(guard["status"], "blocked_missing_routing_control_gate")
            self.assertTrue(guard["checks"]["all_expected_runs_complete"])
            self.assertFalse(guard["checks"]["all_required_gate_files_present"])

    def test_strict_ablation_evidence_guard_accepts_runs_and_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_strict_cache(root)
            suite = root / "suite"
            for variant_key, mode in {
                "bal_align_force": "moe_full_no_aux",
                "context_align_force": "moe_context_align",
                "anchor_only": "moe_anchor_only",
            }.items():
                self._write_complete_run(suite / f"wtb_{variant_key}_seed201", variant_key, 201, mode)
            self._write_gate_artifacts(root / "gate", n_runs=3)

            output_dir = run_strict_ablation_evidence_guard(
                output_dir=root / "evidence",
                root_dir=root,
                cache_root="cache",
                suite_dir=suite,
                routing_gate_dir=root / "gate",
                train_days=1,
                val_days=1,
                test_days=1,
                hist_len=3,
                pred_len=2,
                variant_keys="bal_align_force,context_align_force,anchor_only",
                seeds="201",
            )
            guard = load_json(output_dir / "strict_ablation_evidence_guard.json")

            self.assertEqual(guard["status"], "complete_ready_for_strict_ablation_evidence")
            self.assertTrue(guard["checks"]["routing_gate_audited_runs_cover_expected"])
            self.assertTrue((output_dir / "strict_ablation_evidence_file_status.csv").exists())


if __name__ == "__main__":
    unittest.main()
