from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from main import build_parser
from windfarm_moe.config import DataConfig
from windfarm_moe.future_holdout import (
    REVIEWER_STAT_REQUIRED_FILES,
    run_future_holdout_evidence_guard,
    run_future_holdout_guard,
    write_future_holdout_protocol,
)
from windfarm_moe.strict_anchor import patch_strict_anchor_mask
from windfarm_moe.utils import load_json, save_json


class FutureHoldoutProtocolTests(unittest.TestCase):
    def _write_raw_inputs(self, root: Path) -> None:
        (root / "wtbdata_245days.csv").write_text("stub\n", encoding="utf-8")
        (root / "sdwpf_baidukddcup2022_turb_location.CSV").write_text("stub\n", encoding="utf-8")

    def _write_future_cache(
        self,
        root: Path,
        cache_root: str = "cache_future",
        missing_anchor: bool = False,
    ) -> Path:
        config = DataConfig(
            dataset="wtb",
            root_dir=root,
            cache_root=cache_root,
            train_days=4,
            val_days=2,
            test_days=2,
            holdout_days=2,
            hist_len=3,
            pred_len=2,
        )
        cache = config.cache_dir()
        cache.mkdir(parents=True)
        save_json(
            cache / "metadata.json",
            {
                "feature_names": ["Wspd", "Pab_mean", "Etmp"],
                "split_bounds": config.split_bounds(),
                "train_days": 4,
                "val_days": 2,
                "test_days": 2,
                "holdout_days": 2,
            },
        )
        feature_mask = np.ones((4, 2, 3), dtype=np.float32)
        if missing_anchor:
            feature_mask[1, 0, 0] = 0.0
        np.save(cache / "feature_mask.npy", feature_mask)
        np.save(cache / "regime_primary_valid.npy", np.ones((4, 2), dtype=np.float32))
        return cache

    def _write_complete_future_run(self, run_dir: Path, seed: int = 301) -> None:
        metrics = {
            "overall": {"rmse": 123.0},
            "switch_window": {"rmse": 145.0},
            "gate_alignment": {"nmi": 0.8, "ari": 0.7},
        }
        run_dir.mkdir(parents=True)
        (run_dir / "best_model.pt").write_bytes(b"weights")
        (run_dir / "holdout_metrics").mkdir()
        save_json(run_dir / "holdout_metrics" / "metrics.json", metrics)
        save_json(
            run_dir / "training_summary.json",
            {
                "seed": seed,
                "variant_key": "bal_align_force",
                "experiment_group": "ablation",
                "model_mode": "moe_full_no_aux",
                "holdout_summary": metrics,
            },
        )

    def _write_future_audits(
        self,
        mechanism_dir: Path,
        placebo_dir: Path,
        boundary_dir: Path,
        reviewer_dir: Path,
        gate_status: str = "passed",
    ) -> None:
        (mechanism_dir / "checkpoint_replay").mkdir(parents=True)
        (mechanism_dir / "mechanism_intervention").mkdir(parents=True)
        placebo_dir.mkdir(parents=True)
        boundary_dir.mkdir(parents=True)
        reviewer_dir.mkdir(parents=True)
        save_json(mechanism_dir / "mechanism_evidence_gate_config.json", {"gate_status": gate_status})
        for path in [
            mechanism_dir / "mechanism_gate_run_table.csv",
            mechanism_dir / "checkpoint_replay" / "checkpoint_replay_audit.csv",
            mechanism_dir / "checkpoint_replay" / "checkpoint_replay_summary.csv",
            mechanism_dir / "mechanism_intervention" / "mechanism_intervention_effects.csv",
            placebo_dir / "routing_placebo_summary.csv",
            placebo_dir / "routing_placebo_effects.csv",
            boundary_dir / "boundary_slice_summary.csv",
            boundary_dir / "boundary_slice_effects.csv",
        ]:
            path.write_text("model,value\nm,1\n", encoding="utf-8")
        for filename in REVIEWER_STAT_REQUIRED_FILES:
            target = reviewer_dir / filename
            if target.suffix == ".json":
                save_json(target, {"n_runs": 1})
            elif target.suffix == ".gz":
                target.write_bytes(b"not-real-gzip-but-nonempty")
            elif target.suffix == ".png":
                target.write_bytes(b"png")
            else:
                target.write_text("model,value\nm,1\n", encoding="utf-8")

    def test_parser_accepts_future_holdout_protocol_command(self) -> None:
        args = build_parser().parse_args(
            [
                "future-holdout-protocol",
                "--output-dir",
                "out",
                "--train-days",
                "160",
                "--val-days",
                "25",
                "--test-days",
                "25",
                "--holdout-days",
                "35",
            ]
        )

        self.assertEqual(args.command, "future-holdout-protocol")
        self.assertEqual(args.holdout_days, 35)

    def test_write_future_holdout_protocol_outputs_split_and_commands(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = write_future_holdout_protocol(
                output_dir=Path(temp_dir) / "protocol",
                train_days=4,
                val_days=2,
                test_days=2,
                holdout_days=2,
                hist_len=3,
                pred_len=2,
                seeds=[301, 302],
            )

            protocol = load_json(output_dir / "future_holdout_protocol.json")
            split_df = pd.read_csv(output_dir / "future_holdout_split.csv")
            commands = (output_dir / "future_holdout_commands.ps1").read_text(encoding="utf-8")

            self.assertEqual(protocol["status"], "protocol_only_not_executed")
            self.assertIn("holdout", set(split_df["split"]))
            self.assertIn("--split holdout", commands)
            self.assertIn("--seeds 301,302", commands)

    def test_parser_accepts_future_holdout_guard_command(self) -> None:
        args = build_parser().parse_args(
            ["future-holdout-guard", "--protocol-dir", "protocol", "--output-dir", "guard"]
        )

        self.assertEqual(args.command, "future-holdout-guard")
        self.assertEqual(args.protocol_dir, "protocol")

    def test_parser_accepts_future_holdout_evidence_guard_command(self) -> None:
        args = build_parser().parse_args(
            [
                "future-holdout-evidence-guard",
                "--protocol-dir",
                "protocol",
                "--output-dir",
                "guard",
                "--seeds",
                "301",
            ]
        )

        self.assertEqual(args.command, "future-holdout-evidence-guard")
        self.assertEqual(args.seeds, "301")

    def test_future_holdout_guard_blocks_missing_raw_data(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            protocol_dir = write_future_holdout_protocol(
                output_dir=root / "protocol",
                root_dir=root,
                train_days=4,
                val_days=2,
                test_days=2,
                holdout_days=2,
                hist_len=3,
                pred_len=2,
                seeds=[301],
            )
            guard_dir = run_future_holdout_guard(
                protocol_dir=protocol_dir,
                output_dir=root / "guard",
                root_dir=root,
                train_days=4,
                val_days=2,
                test_days=2,
                holdout_days=2,
                hist_len=3,
                pred_len=2,
            )
            guard = load_json(guard_dir / "future_holdout_guard.json")

            self.assertEqual(guard["status"], "blocked_missing_raw_data")
            self.assertFalse(guard["checks"]["raw_dynamic_exists"])

    def test_future_holdout_guard_blocks_unpatched_anchor_cache(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            protocol_dir = write_future_holdout_protocol(
                output_dir=root / "protocol",
                root_dir=root,
                cache_root="cache_future",
                train_days=4,
                val_days=2,
                test_days=2,
                holdout_days=2,
                hist_len=3,
                pred_len=2,
                seeds=[301],
            )
            self._write_raw_inputs(root)
            self._write_future_cache(root, cache_root="cache_future")

            guard_dir = run_future_holdout_guard(
                protocol_dir=protocol_dir,
                output_dir=root / "guard",
                root_dir=root,
                cache_root="cache_future",
                train_days=4,
                val_days=2,
                test_days=2,
                holdout_days=2,
                hist_len=3,
                pred_len=2,
            )
            guard = load_json(guard_dir / "future_holdout_guard.json")

            self.assertEqual(guard["status"], "blocked_cache_not_strict_anchor_masked")
            self.assertFalse(guard["checks"]["cache_has_strict_anchor_patch_marker"])
            self.assertTrue(guard["checks"]["cache_strict_anchor_check_ran"])
            self.assertTrue(guard["checks"]["cache_strict_anchor_violations_zero"])

    def test_future_holdout_guard_accepts_patched_strict_anchor_cache(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            protocol_dir = write_future_holdout_protocol(
                output_dir=root / "protocol",
                root_dir=root,
                cache_root="cache_future",
                train_days=4,
                val_days=2,
                test_days=2,
                holdout_days=2,
                hist_len=3,
                pred_len=2,
                seeds=[301],
            )
            self._write_raw_inputs(root)
            cache = self._write_future_cache(root, cache_root="cache_future", missing_anchor=True)
            patch_strict_anchor_mask(cache, output_dir=root / "patch_report")

            guard_dir = run_future_holdout_guard(
                protocol_dir=protocol_dir,
                output_dir=root / "guard",
                root_dir=root,
                cache_root="cache_future",
                train_days=4,
                val_days=2,
                test_days=2,
                holdout_days=2,
                hist_len=3,
                pred_len=2,
            )
            guard = load_json(guard_dir / "future_holdout_guard.json")

            self.assertEqual(guard["status"], "ready_to_execute_training")
            self.assertTrue(guard["checks"]["cache_has_strict_anchor_patch_marker"])
            self.assertTrue(guard["checks"]["cache_strict_anchor_violations_zero"])
            self.assertEqual(guard["strict_anchor_mask_report"]["strict_anchor_violations"], 0)

    def test_future_holdout_evidence_guard_counts_missing_runs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            protocol_dir = write_future_holdout_protocol(output_dir=root / "protocol", seeds=[301])
            cache = self._write_future_cache(root, cache_root="cache_future", missing_anchor=True)
            patch_strict_anchor_mask(cache, output_dir=root / "patch_report")

            guard_dir = run_future_holdout_evidence_guard(
                protocol_dir=protocol_dir,
                output_dir=root / "evidence_guard",
                suite_dir=root / "runs",
                cache_dir=cache,
                seeds=[301],
            )
            guard = load_json(guard_dir / "future_holdout_evidence_guard.json")

            self.assertEqual(guard["status"], "ready_to_execute_training")
            self.assertEqual(guard["expected_runs"], 1)
            self.assertEqual(guard["complete_runs"], 0)
            self.assertEqual(guard["missing_runs"], 1)

    def test_future_holdout_evidence_guard_blocks_when_audits_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            protocol_dir = write_future_holdout_protocol(output_dir=root / "protocol", seeds=[301])
            cache = self._write_future_cache(root, cache_root="cache_future", missing_anchor=True)
            patch_strict_anchor_mask(cache, output_dir=root / "patch_report")
            self._write_complete_future_run(root / "runs" / "wtb_bal_align_force_seed301")

            guard_dir = run_future_holdout_evidence_guard(
                protocol_dir=protocol_dir,
                output_dir=root / "evidence_guard",
                suite_dir=root / "runs",
                cache_dir=cache,
                seeds=[301],
            )
            guard = load_json(guard_dir / "future_holdout_evidence_guard.json")

            self.assertEqual(guard["status"], "blocked_missing_holdout_audits")
            self.assertEqual(guard["complete_runs"], 1)
            self.assertFalse(guard["checks"]["all_required_audit_files_present"])

    def test_future_holdout_evidence_guard_accepts_complete_runs_and_audits(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            protocol_dir = write_future_holdout_protocol(output_dir=root / "protocol", seeds=[301])
            cache = self._write_future_cache(root, cache_root="cache_future", missing_anchor=True)
            patch_strict_anchor_mask(cache, output_dir=root / "patch_report")
            self._write_complete_future_run(root / "runs" / "wtb_bal_align_force_seed301")
            self._write_future_audits(root / "mechanism", root / "placebo", root / "boundary", root / "reviewer")

            guard_dir = run_future_holdout_evidence_guard(
                protocol_dir=protocol_dir,
                output_dir=root / "evidence_guard",
                suite_dir=root / "runs",
                cache_dir=cache,
                mechanism_dir=root / "mechanism",
                placebo_dir=root / "placebo",
                boundary_slice_dir=root / "boundary",
                reviewer_pack_dir=root / "reviewer",
                seeds=[301],
            )
            guard = load_json(guard_dir / "future_holdout_evidence_guard.json")

            self.assertEqual(guard["status"], "complete_ready_for_future_holdout_evidence")
            self.assertTrue(guard["checks"]["all_expected_runs_complete"])
            self.assertTrue((guard_dir / "future_holdout_run_status.csv").exists())
            self.assertTrue((guard_dir / "future_holdout_audit_file_status.csv").exists())


if __name__ == "__main__":
    unittest.main()
