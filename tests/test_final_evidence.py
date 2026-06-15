from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from main import build_parser
from windfarm_moe.final_evidence import build_final_evidence_manifest, export_final_tables
from windfarm_moe.utils import load_json, save_json


class FinalEvidenceTests(unittest.TestCase):
    def _write_complete_run(self, run_dir: Path) -> None:
        metrics = run_dir / "test_metrics"
        metrics.mkdir(parents=True, exist_ok=True)
        save_json(run_dir / "training_summary.json", {"best_epoch": 1})
        save_json(metrics / "metrics.json", {"overall": {"rmse": 1.0}})
        np.save(metrics / "pred.npy", np.zeros((2, 1, 1), dtype=np.float32))
        np.save(metrics / "target.npy", np.zeros((2, 1, 1), dtype=np.float32))
        np.save(metrics / "mask.npy", np.ones((2, 1, 1), dtype=np.float32))
        np.save(metrics / "regime_primary.npy", np.zeros((2, 1), dtype=np.int16))
        np.save(metrics / "regime_primary_valid.npy", np.ones((2, 1), dtype=np.float32))
        np.save(metrics / "anchor_index.npy", np.arange(2, dtype=np.int64))
        np.save(metrics / "anchor_physics.npy", np.zeros((2, 1, 4), dtype=np.float32))

    def _write_external_guard(
        self,
        path: Path,
        status: str = "portable_mechanism_ready",
        claim_gate: str = "portable_mechanism_passed",
    ) -> None:
        save_json(
            path,
            {
                "status": status,
                "claim_gate": claim_gate,
                "expected_runs": 80,
                "complete_runs": 80,
                "expected_routing_runs": 40,
                "complete_routing_runs": 40,
                "mean_nmi": 0.6,
                "mean_ari": 0.4,
                "checks": {
                    "cross_farm_both_directions_complete": True,
                    "chronological_sanity_complete": True,
                    "forecast_metric_values_present": True,
                    "routing_metric_values_present": True,
                    "no_wtb_or_sdwpf_source": True,
                },
            },
        )

    def _write_external_source_guard(
        self,
        path: Path,
        status: str = "complete_external_source_evidence",
        claim_gate: str = "within_wtb_only",
    ) -> None:
        save_json(
            path,
            {
                "status": status,
                "claim_gate": claim_gate,
                "n_files": 31,
                "total_selected_bytes": 11050081691,
                "n_local_exists": 31,
                "n_checksum_match": 31,
                "n_manifest_only": 0,
                "checks": {
                    "manifest_exists": True,
                    "manifest_has_rows": True,
                    "required_farms_present": True,
                    "file_count_meets_minimum": True,
                    "total_selected_bytes_meets_minimum": True,
                    "all_selected_files_local_exists": True,
                    "all_selected_files_checksum_match": True,
                    "no_manifest_only_rows": True,
                    "license_is_cc_by_4": True,
                    "no_wtb_or_sdwpf_source": True,
                },
            },
        )

    def test_parser_accepts_final_evidence_commands(self) -> None:
        args = build_parser().parse_args(
            [
                "final-evidence-manifest",
                "--output-dir",
                "out",
                "--run-table",
                "runs.csv",
                "--cache-dir",
                "cache",
                "--external-source-guard",
                "source_guard.json",
            ]
        )

        self.assertEqual(args.command, "final-evidence-manifest")
        self.assertEqual(args.external_source_guard, "source_guard.json")

    def test_final_manifest_blocks_legacy_three_seed_table(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            cache = root / "cache"
            cache.mkdir()
            np.save(cache / "features.npy", np.zeros((2, 2), dtype=np.float32))
            save_json(cache / "metadata.json", {"dataset": "wtb"})
            run_table = root / "runs.csv"
            pd.DataFrame(
                [{"model": "M", "seed": seed, "run_dir": f"run{seed}"} for seed in [201, 202, 203, 204, 205]]
            ).to_csv(run_table, index=False)
            legacy = root / "legacy_table.csv"
            legacy.write_text("model,seed\nM,101\nM,102\nM,103\n", encoding="utf-8")

            out = build_final_evidence_manifest(
                output_dir=root / "manifest",
                run_table=run_table,
                cache_dir=cache,
                table_outputs=str(legacy),
                seeds="201,202,203,204,205",
            )
            manifest = load_json(out / "evidence_manifest_final.json")

            self.assertEqual(manifest["status"], "blocked_final_evidence_incomplete")
            self.assertFalse(manifest["checks"]["no_legacy_three_seed_tables"])
            self.assertFalse(manifest["checks"]["run_artifacts_complete"])

    def test_final_manifest_does_not_flag_statistical_values_as_legacy_seeds(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            cache = root / "cache"
            cache.mkdir()
            np.save(cache / "features.npy", np.zeros((2, 2), dtype=np.float32))
            save_json(cache / "metadata.json", {"dataset": "wtb"})
            rows = []
            for seed in [201, 202, 203, 204, 205]:
                run_dir = root / f"run{seed}"
                self._write_complete_run(run_dir)
                rows.append({"model": "M", "seed": seed, "run_dir": run_dir.relative_to(root)})
            run_table = root / "runs.csv"
            pd.DataFrame(rows).to_csv(run_table, index=False)
            stats_table = root / "paired_effects_summary.csv"
            pd.DataFrame(
                [
                    {
                        "model": "M",
                        "n_seed_pairs": 10,
                        "rmse_reference_mean": 210.103,
                        "paired_permutation_p_value": 0.000999,
                    }
                ]
            ).to_csv(stats_table, index=False)

            out = build_final_evidence_manifest(
                output_dir=root / "manifest",
                run_table=run_table,
                cache_dir=cache,
                table_outputs=str(stats_table),
                seeds="201,202,203,204,205",
                models="M",
            )
            manifest = load_json(out / "evidence_manifest_final.json")

            self.assertTrue(manifest["checks"]["no_legacy_three_seed_tables"])
            self.assertEqual(manifest["legacy_three_seed_offenders"], [])

    def test_final_manifest_passes_with_complete_five_seed_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            cache = root / "cache"
            cache.mkdir()
            np.save(cache / "features.npy", np.zeros((2, 2), dtype=np.float32))
            save_json(cache / "metadata.json", {"dataset": "wtb"})
            rows = []
            for seed in [201, 202, 203, 204, 205]:
                run_dir = root / f"run{seed}"
                self._write_complete_run(run_dir)
                rows.append({"model": "M", "seed": seed, "run_dir": run_dir.relative_to(root)})
            run_table = root / "runs.csv"
            pd.DataFrame(rows).to_csv(run_table, index=False)

            out = build_final_evidence_manifest(
                output_dir=root / "manifest",
                run_table=run_table,
                cache_dir=cache,
                seeds="201,202,203,204,205",
                models="M",
            )
            manifest = load_json(out / "evidence_manifest_final.json")

            self.assertEqual(manifest["claim_gate"], "within_wtb_only")
            self.assertTrue(manifest["checks"]["run_artifacts_complete"])
            self.assertTrue(manifest["checks"]["run_table_has_required_5_seeds"])
            self.assertTrue(manifest["checks"]["manifest_schema_complete"])
            self.assertTrue(manifest["checks"]["cache_sha256_present"])
            self.assertEqual(manifest["schema"]["missing_required_manifest_keys"], [])
            self.assertEqual(manifest["schema"]["empty_required_manifest_values"], [])

    def test_final_manifest_resolves_run_table_paths_relative_to_cwd_when_needed(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temp_dir:
            root = Path(temp_dir)
            cache = root / "cache"
            cache.mkdir()
            np.save(cache / "features.npy", np.zeros((2, 2), dtype=np.float32))
            save_json(cache / "metadata.json", {"dataset": "wtb"})
            rows = []
            for seed in [201, 202, 203, 204, 205]:
                run_dir = root / "repo_relative_runs" / f"run{seed}"
                self._write_complete_run(run_dir)
                rows.append({"model": "M", "seed": seed, "run_dir": str(run_dir.relative_to(Path.cwd()))})
            run_table_dir = root / "pack"
            run_table_dir.mkdir()
            run_table = run_table_dir / "runs.csv"
            pd.DataFrame(rows).to_csv(run_table, index=False)

            out = build_final_evidence_manifest(
                output_dir=root / "manifest",
                run_table=run_table,
                cache_dir=cache,
                seeds="201,202,203,204,205",
                models="M",
            )
            manifest = load_json(out / "evidence_manifest_final.json")

            self.assertTrue(manifest["checks"]["run_artifacts_complete"])

    def test_final_manifest_blocks_missing_cache_hash(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            cache = root / "cache"
            cache.mkdir()
            rows = []
            for seed in [201, 202, 203, 204, 205]:
                run_dir = root / f"run{seed}"
                self._write_complete_run(run_dir)
                rows.append({"model": "M", "seed": seed, "run_dir": run_dir.relative_to(root)})
            run_table = root / "runs.csv"
            pd.DataFrame(rows).to_csv(run_table, index=False)

            out = build_final_evidence_manifest(
                output_dir=root / "manifest",
                run_table=run_table,
                cache_dir=cache,
                seeds="201,202,203,204,205",
                models="M",
            )
            manifest = load_json(out / "evidence_manifest_final.json")

            self.assertEqual(manifest["status"], "blocked_final_evidence_incomplete")
            self.assertFalse(manifest["checks"]["cache_sha256_present"])
            self.assertFalse(manifest["checks"]["manifest_schema_complete"])
            self.assertIn("cache_sha256", manifest["schema"]["empty_required_manifest_values"])

    def test_final_manifest_downgrades_requested_external_guard_when_not_citable(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            cache = root / "cache"
            cache.mkdir()
            np.save(cache / "features.npy", np.zeros((2, 2), dtype=np.float32))
            save_json(cache / "metadata.json", {"dataset": "wtb"})
            rows = []
            for seed in [201, 202, 203, 204, 205]:
                run_dir = root / f"run{seed}"
                self._write_complete_run(run_dir)
                rows.append({"model": "M", "seed": seed, "run_dir": run_dir.relative_to(root)})
            run_table = root / "runs.csv"
            pd.DataFrame(rows).to_csv(run_table, index=False)
            external_guard = root / "external_guard.json"
            save_json(external_guard, {"status": "blocked_external_wind_incomplete", "claim_gate": "blocked_not_citable"})

            out = build_final_evidence_manifest(
                output_dir=root / "manifest",
                run_table=run_table,
                cache_dir=cache,
                external_guard=external_guard,
                seeds="201,202,203,204,205",
                models="M",
            )
            manifest = load_json(out / "evidence_manifest_final.json")

            self.assertEqual(manifest["claim_gate"], "within_wtb_only")
            self.assertEqual(manifest["status"], "complete_ready_for_submission_tables")
            self.assertFalse(manifest["checks"]["external_guard_passing_if_requested"])
            self.assertFalse(manifest["checks"]["external_portability_ready"])
            self.assertTrue(manifest["checks"]["claim_gate_citable"])

    def test_final_manifest_treats_external_blocked_guards_as_nonblocking_for_internal_citation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            cache = root / "cache"
            cache.mkdir()
            np.save(cache / "features.npy", np.zeros((2, 2), dtype=np.float32))
            save_json(cache / "metadata.json", {"dataset": "wtb"})
            rows = []
            for seed in [201, 202, 203, 204, 205]:
                run_dir = root / f"run{seed}"
                self._write_complete_run(run_dir)
                rows.append({"model": "M", "seed": seed, "run_dir": run_dir.relative_to(root)})
            run_table = root / "runs.csv"
            pd.DataFrame(rows).to_csv(run_table, index=False)
            guard = root / "external_wind_guard.json"
            source_guard = root / "external_source_guard.json"
            save_json(guard, {"status": "blocked_external_wind_incomplete", "claim_gate": "blocked_not_citable"})
            self._write_external_source_guard(source_guard)

            out = build_final_evidence_manifest(
                output_dir=root / "manifest",
                run_table=run_table,
                cache_dir=cache,
                guard_paths=str(guard),
                external_guard=guard,
                external_source_guard=source_guard,
                seeds="201,202,203,204,205",
                models="M",
            )
            manifest = load_json(out / "evidence_manifest_final.json")

            self.assertEqual(manifest["claim_gate"], "within_wtb_only")
            self.assertEqual(manifest["status"], "complete_ready_for_submission_tables")
            self.assertFalse(manifest["checks"]["external_guard_passing_if_requested"])
            self.assertTrue(manifest["checks"]["guard_statuses_passing"])
            self.assertFalse(manifest["checks"]["external_portability_ready"])

    def test_final_manifest_disallow_within_wtb_blocks_incomplete_external_guard(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            cache = root / "cache"
            cache.mkdir()
            np.save(cache / "features.npy", np.zeros((2, 2), dtype=np.float32))
            save_json(cache / "metadata.json", {"dataset": "wtb"})
            rows = []
            for seed in [201, 202, 203, 204, 205]:
                run_dir = root / f"run{seed}"
                self._write_complete_run(run_dir)
                rows.append({"model": "M", "seed": seed, "run_dir": run_dir.relative_to(root)})
            run_table = root / "runs.csv"
            pd.DataFrame(rows).to_csv(run_table, index=False)
            external_guard = root / "external_guard.json"
            save_json(external_guard, {"status": "blocked_external_wind_incomplete", "claim_gate": "blocked_not_citable"})

            out = build_final_evidence_manifest(
                output_dir=root / "manifest",
                run_table=run_table,
                cache_dir=cache,
                external_guard=external_guard,
                seeds="201,202,203,204,205",
                models="M",
                allow_within_wtb_only=False,
            )
            manifest = load_json(out / "evidence_manifest_final.json")

            self.assertEqual(manifest["claim_gate"], "blocked_not_citable")
            self.assertEqual(manifest["status"], "blocked_final_evidence_incomplete")
            self.assertFalse(manifest["checks"]["external_portability_ready"])

    def test_final_manifest_downgrades_external_claim_when_source_guard_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            cache = root / "cache"
            cache.mkdir()
            np.save(cache / "features.npy", np.zeros((2, 2), dtype=np.float32))
            save_json(cache / "metadata.json", {"dataset": "wtb"})
            rows = []
            for seed in [201, 202, 203, 204, 205]:
                run_dir = root / f"run{seed}"
                self._write_complete_run(run_dir)
                rows.append({"model": "M", "seed": seed, "run_dir": run_dir.relative_to(root)})
            run_table = root / "runs.csv"
            pd.DataFrame(rows).to_csv(run_table, index=False)
            external_guard = root / "external_guard.json"
            self._write_external_guard(external_guard)

            out = build_final_evidence_manifest(
                output_dir=root / "manifest",
                run_table=run_table,
                cache_dir=cache,
                external_guard=external_guard,
                seeds="201,202,203,204,205",
                models="M",
            )
            manifest = load_json(out / "evidence_manifest_final.json")

            self.assertEqual(manifest["claim_gate"], "within_wtb_only")
            self.assertEqual(manifest["status"], "complete_ready_for_submission_tables")
            self.assertFalse(manifest["checks"]["external_source_guard_passing_if_external_requested"])
            self.assertFalse(manifest["checks"]["external_source_guard_status_passing"])
            self.assertFalse(manifest["checks"]["external_portability_ready"])

    def test_final_manifest_downgrades_external_claim_when_source_guard_incomplete(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            cache = root / "cache"
            cache.mkdir()
            np.save(cache / "features.npy", np.zeros((2, 2), dtype=np.float32))
            save_json(cache / "metadata.json", {"dataset": "wtb"})
            rows = []
            for seed in [201, 202, 203, 204, 205]:
                run_dir = root / f"run{seed}"
                self._write_complete_run(run_dir)
                rows.append({"model": "M", "seed": seed, "run_dir": run_dir.relative_to(root)})
            run_table = root / "runs.csv"
            pd.DataFrame(rows).to_csv(run_table, index=False)
            external_guard = root / "external_guard.json"
            external_source_guard = root / "external_source_guard.json"
            self._write_external_guard(external_guard)
            self._write_external_source_guard(
                external_source_guard,
                status="blocked_external_source_incomplete",
                claim_gate="blocked_not_citable",
            )

            out = build_final_evidence_manifest(
                output_dir=root / "manifest",
                run_table=run_table,
                cache_dir=cache,
                external_guard=external_guard,
                external_source_guard=external_source_guard,
                seeds="201,202,203,204,205",
                models="M",
            )
            manifest = load_json(out / "evidence_manifest_final.json")

            self.assertEqual(manifest["claim_gate"], "within_wtb_only")
            self.assertEqual(manifest["status"], "complete_ready_for_submission_tables")
            self.assertFalse(manifest["checks"]["external_source_guard_passing_if_external_requested"])
            self.assertFalse(manifest["checks"]["external_portability_ready"])

    def test_final_manifest_allows_portable_mechanism_only_after_external_and_source_guards_pass(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            cache = root / "cache"
            cache.mkdir()
            np.save(cache / "features.npy", np.zeros((2, 2), dtype=np.float32))
            save_json(cache / "metadata.json", {"dataset": "wtb"})
            rows = []
            for seed in [201, 202, 203, 204, 205]:
                run_dir = root / f"run{seed}"
                self._write_complete_run(run_dir)
                rows.append({"model": "M", "seed": seed, "run_dir": run_dir.relative_to(root)})
            run_table = root / "runs.csv"
            pd.DataFrame(rows).to_csv(run_table, index=False)
            external_guard = root / "external_guard.json"
            external_source_guard = root / "external_source_guard.json"
            self._write_external_guard(external_guard)
            self._write_external_source_guard(external_source_guard)

            out = build_final_evidence_manifest(
                output_dir=root / "manifest",
                run_table=run_table,
                cache_dir=cache,
                external_guard=external_guard,
                external_source_guard=external_source_guard,
                seeds="201,202,203,204,205",
                models="M",
            )
            manifest = load_json(out / "evidence_manifest_final.json")

            self.assertEqual(manifest["claim_gate"], "portable_mechanism_passed")
            self.assertEqual(manifest["status"], "complete_ready_for_submission_tables")
            self.assertTrue(manifest["checks"]["external_guard_passing_if_requested"])
            self.assertTrue(manifest["checks"]["external_guard_protocol_complete_if_requested"])
            self.assertTrue(manifest["checks"]["external_source_guard_passing_if_external_requested"])
            self.assertTrue(manifest["checks"]["external_source_total_bytes_meets_minimum"])
            self.assertTrue(manifest["checks"]["external_complete_80_runs"])
            self.assertTrue(manifest["checks"]["external_complete_40_routing_runs"])

    def test_final_manifest_downgrades_thin_external_guard_even_with_portable_strings(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            cache = root / "cache"
            cache.mkdir()
            np.save(cache / "features.npy", np.zeros((2, 2), dtype=np.float32))
            save_json(cache / "metadata.json", {"dataset": "wtb"})
            rows = []
            for seed in [201, 202, 203, 204, 205]:
                run_dir = root / f"run{seed}"
                self._write_complete_run(run_dir)
                rows.append({"model": "M", "seed": seed, "run_dir": run_dir.relative_to(root)})
            run_table = root / "runs.csv"
            pd.DataFrame(rows).to_csv(run_table, index=False)
            external_guard = root / "external_guard.json"
            save_json(external_guard, {"status": "portable_mechanism_ready", "claim_gate": "portable_mechanism_passed"})

            out = build_final_evidence_manifest(
                output_dir=root / "manifest",
                run_table=run_table,
                cache_dir=cache,
                external_guard=external_guard,
                seeds="201,202,203,204,205",
                models="M",
            )
            manifest = load_json(out / "evidence_manifest_final.json")

            self.assertEqual(manifest["claim_gate"], "within_wtb_only")
            self.assertEqual(manifest["status"], "complete_ready_for_submission_tables")
            self.assertTrue(manifest["checks"]["external_guard_passing_if_requested"])
            self.assertFalse(manifest["checks"]["external_guard_protocol_complete_if_requested"])
            self.assertFalse(manifest["checks"]["external_complete_80_runs"])
            self.assertFalse(manifest["checks"]["external_portability_ready"])

    def test_final_manifest_with_complete_but_nonportable_external_guard_stays_within_wtb(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            cache = root / "cache"
            cache.mkdir()
            np.save(cache / "features.npy", np.zeros((2, 2), dtype=np.float32))
            save_json(cache / "metadata.json", {"dataset": "wtb"})
            rows = []
            for seed in [201, 202, 203, 204, 205]:
                run_dir = root / f"run{seed}"
                self._write_complete_run(run_dir)
                rows.append({"model": "M", "seed": seed, "run_dir": run_dir.relative_to(root)})
            run_table = root / "runs.csv"
            pd.DataFrame(rows).to_csv(run_table, index=False)
            external_guard = root / "external_guard.json"
            external_source_guard = root / "external_source_guard.json"
            self._write_external_guard(
                external_guard,
                status="complete_but_within_wtb_only",
                claim_gate="within_wtb_only",
            )
            self._write_external_source_guard(external_source_guard)

            out = build_final_evidence_manifest(
                output_dir=root / "manifest",
                run_table=run_table,
                cache_dir=cache,
                external_guard=external_guard,
                external_source_guard=external_source_guard,
                seeds="201,202,203,204,205",
                models="M",
            )
            manifest = load_json(out / "evidence_manifest_final.json")

            self.assertEqual(manifest["claim_gate"], "within_wtb_only")
            self.assertEqual(manifest["status"], "complete_ready_for_submission_tables")
            self.assertTrue(manifest["checks"]["external_guard_passing_if_requested"])
            self.assertTrue(manifest["checks"]["external_guard_protocol_complete_if_requested"])
            self.assertTrue(manifest["checks"]["external_source_guard_passing_if_external_requested"])

    def test_final_manifest_blocks_guard_with_blocked_status(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            cache = root / "cache"
            cache.mkdir()
            np.save(cache / "features.npy", np.zeros((2, 2), dtype=np.float32))
            save_json(cache / "metadata.json", {"dataset": "wtb"})
            rows = []
            for seed in [201, 202, 203, 204, 205]:
                run_dir = root / f"run{seed}"
                self._write_complete_run(run_dir)
                rows.append({"model": "M", "seed": seed, "run_dir": run_dir.relative_to(root)})
            run_table = root / "runs.csv"
            pd.DataFrame(rows).to_csv(run_table, index=False)
            guard = root / "bad_guard.json"
            save_json(guard, {"status": "blocked_boundary_negative_controls"})

            out = build_final_evidence_manifest(
                output_dir=root / "manifest",
                run_table=run_table,
                cache_dir=cache,
                guard_paths=str(guard),
                seeds="201,202,203,204,205",
                models="M",
            )
            manifest = load_json(out / "evidence_manifest_final.json")

            self.assertEqual(manifest["claim_gate"], "blocked_not_citable")
            self.assertEqual(manifest["status"], "blocked_final_evidence_incomplete")
            self.assertFalse(manifest["checks"]["guard_statuses_passing"])

    def test_final_table_export_refuses_blocked_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manifest = root / "manifest.json"
            save_json(manifest, {"claim_gate": "blocked_not_citable", "table_outputs": {}, "source_artifacts": {}})

            with self.assertRaises(ValueError):
                export_final_tables(manifest, root / "out")

    def test_final_table_export_refuses_incomplete_manifest_even_when_citable(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manifest = root / "manifest.json"
            save_json(
                manifest,
                {
                    "claim_gate": "within_wtb_only",
                    "status": "blocked_final_evidence_incomplete",
                    "table_outputs": {},
                    "source_artifacts": {},
                },
            )

            with self.assertRaisesRegex(ValueError, "not complete_ready_for_submission_tables"):
                export_final_tables(manifest, root / "out")

    def test_final_table_export_copies_tables_sources_figures_guards_and_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manifest_dir = root / "manifest"
            manifest_dir.mkdir()
            table = root / "table.csv"
            source = root / "source.csv"
            figure = root / "figure.png"
            guard = root / "guard.json"
            checks = manifest_dir / "final_evidence_checks.csv"
            run_a = root / "run_a"
            run_b = root / "run_b"
            (run_a / "test_metrics").mkdir(parents=True)
            (run_b / "test_metrics").mkdir(parents=True)
            table.write_text("model,rmse\nM,1\n", encoding="utf-8")
            source.write_text("x,y\n1,2\n", encoding="utf-8")
            figure.write_bytes(b"png")
            np.save(run_a / "test_metrics" / "pred.npy", np.zeros((2, 1, 1), dtype=np.float32))
            np.save(run_b / "test_metrics" / "pred.npy", np.zeros((2, 1, 1), dtype=np.float32))
            save_json(guard, {"status": "passed_boundary_negative_controls"})
            checks.write_text("check,passed\nok,True\n", encoding="utf-8")
            manifest = manifest_dir / "evidence_manifest_final.json"
            save_json(
                manifest,
                {
                    "claim_gate": "within_wtb_only",
                    "status": "complete_ready_for_submission_tables",
                    "table_outputs": {"table.csv": {"path": str(table)}},
                    "source_artifacts": {"source.csv": {"path": str(source)}},
                    "figure_outputs": {"figure.png": {"path": str(figure)}},
                    "guard_status": {"guard": {"path": str(guard), "status": "passed_boundary_negative_controls"}},
                    "seeds": [201, 202],
                    "models": ["A", "B"],
                    "run_artifacts": {
                        "rows": [
                            {"model": "A", "seed": 201, "run_dir": str(run_a), "complete": True},
                            {"model": "B", "seed": 202, "run_dir": str(run_b), "complete": True},
                        ]
                    },
                },
            )

            out = export_final_tables(manifest, root / "out")
            status = load_json(out / "final_table_export_status.json")

            self.assertEqual(status["status"], "complete")
            self.assertTrue((out / "tables" / "table.csv").exists())
            self.assertTrue((out / "source_data" / "source.csv").exists())
            self.assertTrue((out / "figures" / "figure.png").exists())
            self.assertTrue((out / "guards" / "guard.json").exists())
            self.assertTrue((out / "manifest" / "evidence_manifest_final.json").exists())
            self.assertTrue((out / "manifest" / "final_evidence_checks.csv").exists())
            self.assertTrue((out / "source_data_index.csv").exists())
            self.assertTrue((out / "figure_index.csv").exists())
            self.assertTrue((out / "source_trace_manifest.csv").exists())
            self.assertTrue((out / "source_trace_manifest.json").exists())
            trace = pd.read_csv(out / "source_trace_manifest.csv")
            self.assertIn("script_or_command", trace.columns)
            self.assertIn("raw_prediction_count", trace.columns)
            self.assertEqual(int(trace["raw_prediction_count"].max()), 2)
            status = load_json(out / "final_table_export_status.json")
            self.assertTrue(status["checks"]["source_trace_manifest_written"])


if __name__ == "__main__":
    unittest.main()
