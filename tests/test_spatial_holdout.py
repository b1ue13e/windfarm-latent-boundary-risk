from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np

from main import build_parser
from windfarm_moe.spatial_holdout import (
    REVIEWER_STAT_REQUIRED_FILES,
    build_spatial_holdout_cache,
    run_spatial_holdout_evidence_guard,
    run_spatial_holdout_guard,
    write_spatial_holdout_protocol,
)
from windfarm_moe.utils import load_json, save_json


class SpatialHoldoutTests(unittest.TestCase):
    def _write_cache(self, cache_dir: Path) -> None:
        cache_dir.mkdir(parents=True, exist_ok=True)
        total_steps = 12
        num_nodes = 5
        np.save(cache_dir / "features.npy", np.zeros((total_steps, num_nodes, 2), dtype=np.float32))
        np.save(cache_dir / "feature_mask.npy", np.ones((total_steps, num_nodes, 2), dtype=np.float32))
        np.save(cache_dir / "target.npy", np.zeros((total_steps, num_nodes), dtype=np.float32))
        np.save(cache_dir / "target_mask.npy", np.ones((total_steps, num_nodes), dtype=np.float32))
        np.save(cache_dir / "regime_primary.npy", np.zeros((total_steps, num_nodes), dtype=np.int16))
        np.save(cache_dir / "regime_primary_valid.npy", np.ones((total_steps, num_nodes), dtype=np.float32))
        np.save(cache_dir / "regime_aux.npy", np.zeros((total_steps, num_nodes), dtype=np.int16))
        np.save(cache_dir / "regime_aux_valid.npy", np.ones((total_steps, num_nodes), dtype=np.float32))
        np.save(cache_dir / "edge_index.npy", np.full((total_steps, num_nodes, 1), -1, dtype=np.int16))
        np.save(cache_dir / "edge_weight.npy", np.zeros((total_steps, num_nodes, 1), dtype=np.float32))
        np.save(cache_dir / "physics.npy", np.zeros((total_steps, num_nodes, 4), dtype=np.float32))
        np.save(cache_dir / "physics_model.npy", np.zeros((total_steps, num_nodes, 4), dtype=np.float32))
        np.save(cache_dir / "coords.npy", np.array([[0, 0], [1, 0], [2, 0], [3, 0], [4, 0]], dtype=np.float32))
        np.save(cache_dir / "time_index.npy", np.arange(total_steps, dtype=np.int64))
        np.save(cache_dir / "node_ids.npy", np.arange(101, 106, dtype=np.int32))
        save_json(
            cache_dir / "metadata.json",
            {
                "dataset": "wtb",
                "feature_names": ["Wspd", "Pab_mean"],
                "split_bounds": {"train": [0, 4], "val": [4, 8], "test": [8, 12]},
                "hist_len": 2,
                "pred_len": 1,
                "strict_anchor_mask_patch": {"removed_regime_valid": 0},
            },
        )

    def _write_complete_run(self, run_dir: Path, variant_key: str, seed: int) -> None:
        specs = {
            "bal_align_force": ("MoE + L_bal + L_align + L_force", "moe_full_no_aux"),
            "context_align_force": ("Context-supervised router", "moe_context_align"),
            "anchor_only": ("Anchor-only router", "moe_anchor_only"),
        }
        label, mode = specs[variant_key]
        metrics = {
            "overall": {"rmse": 100.0},
            "switch_window": {"rmse": 120.0},
            "gate_alignment": {"nmi": 0.8, "ari": 0.7},
        }
        run_dir.mkdir(parents=True)
        (run_dir / "test_metrics").mkdir()
        save_json(run_dir / "test_metrics" / "metrics.json", metrics)
        save_json(
            run_dir / "training_summary.json",
            {
                "seed": seed,
                "variant_key": variant_key,
                "experiment_group": "ablation",
                "model_mode": mode,
                "label": label,
                "test_summary": metrics,
            },
        )

    def _write_spatial_audits(self, mechanism_dir: Path, reviewer_dir: Path, n_runs: int = 3) -> None:
        (mechanism_dir / "checkpoint_replay").mkdir(parents=True)
        (mechanism_dir / "mechanism_intervention").mkdir(parents=True)
        reviewer_dir.mkdir(parents=True)
        save_json(
            mechanism_dir / "mechanism_evidence_gate_config.json",
            {"gate_status": "passed", "n_audited_runs": n_runs},
        )
        for path in [
            mechanism_dir / "mechanism_gate_run_table.csv",
            mechanism_dir / "checkpoint_replay" / "checkpoint_replay_audit.csv",
            mechanism_dir / "checkpoint_replay" / "checkpoint_replay_summary.csv",
            mechanism_dir / "mechanism_intervention" / "mechanism_intervention_effects.csv",
        ]:
            path.write_text("model,value\nm,1\n", encoding="utf-8")
        for filename in REVIEWER_STAT_REQUIRED_FILES:
            target = reviewer_dir / filename
            if target.suffix == ".json":
                save_json(target, {"n_runs": n_runs})
            elif target.suffix == ".gz":
                target.write_bytes(b"nonempty")
            elif target.suffix == ".png":
                target.write_bytes(b"png")
            else:
                target.write_text("model,value\nm,1\n", encoding="utf-8")

    def test_parser_accepts_spatial_holdout_commands(self) -> None:
        protocol_args = build_parser().parse_args(["spatial-holdout-protocol", "--output-dir", "out"])
        cache_args = build_parser().parse_args(["spatial-holdout-cache"])
        guard_args = build_parser().parse_args(
            ["spatial-holdout-guard", "--protocol-dir", "protocol", "--output-dir", "guard"]
        )
        evidence_args = build_parser().parse_args(
            ["spatial-holdout-evidence-guard", "--protocol-dir", "protocol", "--output-dir", "evidence"]
        )

        self.assertEqual(protocol_args.command, "spatial-holdout-protocol")
        self.assertEqual(cache_args.command, "spatial-holdout-cache")
        self.assertEqual(guard_args.command, "spatial-holdout-guard")
        self.assertEqual(evidence_args.command, "spatial-holdout-evidence-guard")

    def test_build_spatial_holdout_cache_masks_train_and_test_nodes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source"
            output = root / "out"
            self._write_cache(source)

            build_spatial_holdout_cache(source, output, strategy="east", fraction=0.4)

            target_mask = np.load(output / "target_mask.npy")
            metadata = load_json(output / "metadata.json")
            holdout = metadata["spatial_holdout_patch"]["holdout_node_indices"]
            train_nodes = [idx for idx in range(5) if idx not in holdout]

            self.assertEqual(holdout, [3, 4])
            self.assertTrue((target_mask[0:8, holdout] == 0).all())
            self.assertTrue((target_mask[8:12, train_nodes] == 0).all())
            self.assertTrue((target_mask[8:12, holdout] == 1).all())

    def test_write_spatial_holdout_protocol_outputs_commands(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = write_spatial_holdout_protocol(
                output_dir=Path(temp_dir),
                source_cache_dir="source_cache",
                output_cache_root="derived_cache",
                suite_dir="suite",
                seeds="1,2",
            )
            protocol = load_json(output_dir / "spatial_holdout_protocol.json")
            commands = (output_dir / "spatial_holdout_commands.ps1").read_text(encoding="utf-8")

            self.assertEqual(protocol["seeds"], [1, 2])
            self.assertIn("spatial-holdout-cache", commands)
            self.assertIn("context_align_force,anchor_only", commands)

    def test_spatial_holdout_guard_accepts_strict_spatial_cache(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source"
            cache_root = root / "derived_cache"
            suite_dir = root / "suite"
            protocol_dir = root / "protocol"
            self._write_cache(source)
            write_spatial_holdout_protocol(
                output_dir=protocol_dir,
                source_cache_dir=source,
                output_cache_root=str(cache_root),
                suite_dir=suite_dir,
                seeds="401",
            )
            build_spatial_holdout_cache(source, cache_root / "wtb_245d", strategy="east", fraction=0.4)

            output_dir = run_spatial_holdout_guard(
                protocol_dir=protocol_dir,
                output_dir=root / "guard",
                source_cache_dir=source,
                output_cache_root=str(cache_root),
                suite_dir=suite_dir,
                strategy="east",
                fraction=0.4,
                seeds="401",
                variant_keys="bal_align_force",
            )
            guard = load_json(output_dir / "spatial_holdout_guard.json")

            self.assertEqual(guard["status"], "ready_to_execute_training")
            self.assertTrue(guard["checks"]["cache_has_strict_anchor_patch_marker"])
            self.assertTrue(guard["checks"]["cache_spatial_mask_policy_pass"])
            self.assertEqual(guard["spatial_mask_report"]["holdout_node_count"], 2)

    def test_spatial_holdout_guard_blocks_non_strict_cache(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source"
            cache_root = root / "derived_cache"
            protocol_dir = root / "protocol"
            self._write_cache(source)
            write_spatial_holdout_protocol(
                output_dir=protocol_dir,
                source_cache_dir=source,
                output_cache_root=str(cache_root),
                suite_dir=root / "suite",
                seeds="401",
            )
            build_spatial_holdout_cache(source, cache_root / "wtb_245d", strategy="east", fraction=0.4)
            metadata_path = cache_root / "wtb_245d" / "metadata.json"
            metadata = load_json(metadata_path)
            metadata.pop("strict_anchor_mask_patch")
            save_json(metadata_path, metadata)

            output_dir = run_spatial_holdout_guard(
                protocol_dir=protocol_dir,
                output_dir=root / "guard",
                source_cache_dir=source,
                output_cache_root=str(cache_root),
                strategy="east",
                fraction=0.4,
                seeds="401",
                variant_keys="bal_align_force",
            )
            guard = load_json(output_dir / "spatial_holdout_guard.json")

            self.assertEqual(guard["status"], "blocked_cache_not_strict_anchor_masked")
            self.assertFalse(guard["checks"]["cache_has_strict_anchor_patch_marker"])

    def test_spatial_holdout_evidence_guard_counts_missing_runs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source"
            cache_root = root / "derived_cache"
            suite_dir = root / "suite"
            protocol_dir = root / "protocol"
            self._write_cache(source)
            write_spatial_holdout_protocol(
                output_dir=protocol_dir,
                source_cache_dir=source,
                output_cache_root=str(cache_root),
                suite_dir=suite_dir,
                seeds="401",
            )
            build_spatial_holdout_cache(source, cache_root / "wtb_245d", strategy="east", fraction=0.4)

            output_dir = run_spatial_holdout_evidence_guard(
                protocol_dir=protocol_dir,
                output_dir=root / "evidence",
                suite_dir=suite_dir,
                cache_dir=cache_root / "wtb_245d",
                seeds="401",
                variant_keys="bal_align_force,context_align_force,anchor_only",
            )
            guard = load_json(output_dir / "spatial_holdout_evidence_guard.json")

            self.assertEqual(guard["status"], "ready_to_execute_training")
            self.assertEqual(guard["expected_runs"], 3)
            self.assertEqual(guard["complete_runs"], 0)

    def test_spatial_holdout_evidence_guard_blocks_missing_audits(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source"
            cache_root = root / "derived_cache"
            suite_dir = root / "suite"
            protocol_dir = root / "protocol"
            self._write_cache(source)
            write_spatial_holdout_protocol(
                output_dir=protocol_dir,
                source_cache_dir=source,
                output_cache_root=str(cache_root),
                suite_dir=suite_dir,
                seeds="401",
            )
            build_spatial_holdout_cache(source, cache_root / "wtb_245d", strategy="east", fraction=0.4)
            for variant_key in ["bal_align_force", "context_align_force", "anchor_only"]:
                self._write_complete_run(suite_dir / f"wtb_{variant_key}_seed401", variant_key, seed=401)

            output_dir = run_spatial_holdout_evidence_guard(
                protocol_dir=protocol_dir,
                output_dir=root / "evidence",
                suite_dir=suite_dir,
                cache_dir=cache_root / "wtb_245d",
                seeds="401",
                variant_keys="bal_align_force,context_align_force,anchor_only",
            )
            guard = load_json(output_dir / "spatial_holdout_evidence_guard.json")

            self.assertEqual(guard["status"], "blocked_missing_spatial_audits")
            self.assertTrue(guard["checks"]["all_expected_runs_complete"])
            self.assertFalse(guard["checks"]["all_required_audit_files_present"])

    def test_spatial_holdout_evidence_guard_accepts_complete_runs_and_audits(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source"
            cache_root = root / "derived_cache"
            suite_dir = root / "suite"
            protocol_dir = root / "protocol"
            self._write_cache(source)
            write_spatial_holdout_protocol(
                output_dir=protocol_dir,
                source_cache_dir=source,
                output_cache_root=str(cache_root),
                suite_dir=suite_dir,
                seeds="401",
            )
            build_spatial_holdout_cache(source, cache_root / "wtb_245d", strategy="east", fraction=0.4)
            for variant_key in ["bal_align_force", "context_align_force", "anchor_only"]:
                self._write_complete_run(suite_dir / f"wtb_{variant_key}_seed401", variant_key, seed=401)
            self._write_spatial_audits(root / "mechanism", root / "reviewer", n_runs=3)

            output_dir = run_spatial_holdout_evidence_guard(
                protocol_dir=protocol_dir,
                output_dir=root / "evidence",
                suite_dir=suite_dir,
                cache_dir=cache_root / "wtb_245d",
                mechanism_dir=root / "mechanism",
                reviewer_pack_dir=root / "reviewer",
                seeds="401",
                variant_keys="bal_align_force,context_align_force,anchor_only",
            )
            guard = load_json(output_dir / "spatial_holdout_evidence_guard.json")

            self.assertEqual(guard["status"], "complete_ready_for_spatial_holdout_evidence")
            self.assertTrue(guard["checks"]["mechanism_audited_runs_cover_expected"])
            self.assertTrue((output_dir / "spatial_holdout_evidence_run_status.csv").exists())


if __name__ == "__main__":
    unittest.main()
