from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from main import build_parser
from windfarm_moe.reproduction_package import write_reproduction_package
from windfarm_moe.utils import load_json


class ReproductionPackageTests(unittest.TestCase):
    def test_parser_accepts_reproduction_package_command(self) -> None:
        args = build_parser().parse_args(["reproduction-package", "--output-dir", "out"])

        self.assertEqual(args.command, "reproduction-package")
        self.assertEqual(args.output_dir, "out")

    def test_reproduction_package_writes_guard_and_queue_entrypoints(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = write_reproduction_package(Path(temp_dir) / "package")

            index = load_json(output_dir / "reproduction_index.json")
            self.assertEqual(index["kind"], "science_reproduction_package")
            self.assertTrue((output_dir / "refresh_guards_only.ps1").exists())
            self.assertTrue((output_dir / "run_active_experiment_queues.ps1").exists())
            self.assertTrue((output_dir / "rebuild_submission_artifacts.ps1").exists())
            self.assertTrue((output_dir / "rebuild_final_evidence_package.ps1").exists())
            self.assertTrue((output_dir / "generate_uncapped_per_example_reviewer_stats.ps1").exists())
            self.assertTrue((output_dir / "external_wind_protocol.ps1").exists())

            refresh_text = (output_dir / "refresh_guards_only.ps1").read_text(encoding="utf-8")
            queue_text = (output_dir / "run_active_experiment_queues.ps1").read_text(encoding="utf-8")
            artifact_text = (output_dir / "rebuild_submission_artifacts.ps1").read_text(encoding="utf-8")
            final_text = (output_dir / "rebuild_final_evidence_package.ps1").read_text(encoding="utf-8")
            uncapped_text = (output_dir / "generate_uncapped_per_example_reviewer_stats.ps1").read_text(encoding="utf-8")
            external_text = (output_dir / "external_wind_protocol.ps1").read_text(encoding="utf-8")
            readme_text = (output_dir / "README.md").read_text(encoding="utf-8")

            self.assertIn("refresh_readiness.ps1", refresh_text)
            self.assertIn("strictmask_baseline_rerun_wtb_full", queue_text)
            self.assertIn("strict_followup_queue_20260611.ps1", queue_text)
            self.assertIn("strict-evidence-export", artifact_text)
            self.assertIn("reserve-decision-guard", artifact_text)
            self.assertIn("reviewer-stat-pack --dataset wtb", artifact_text)
            self.assertIn("--boundary-negative-guard-dir artifacts/boundary_negative_controls_wtb", artifact_text)
            self.assertIn("--required-models \"Graph WaveNet,PatchTST,Physics-Aligned MoE,MoE + L_bal + L_align + L_force\"", artifact_text)
            self.assertIn("--required-seeds 201,202,203,204,205", artifact_text)
            self.assertIn("--max-per-example-rows 200000", artifact_text)
            self.assertIn("capped preview", artifact_text)
            self.assertIn("final-evidence-manifest", final_text)
            self.assertIn("final-table-export", final_text)
            self.assertIn("reviewer-stat-pack --dataset wtb", final_text)
            self.assertIn("--required-models \"Graph WaveNet,PatchTST,Physics-Aligned MoE,MoE + L_bal + L_align + L_force\"", final_text)
            self.assertIn("--required-seeds 201,202,203,204,205", final_text)
            self.assertIn("--max-per-example-rows 200000", final_text)
            self.assertIn("capped preview", final_text)
            self.assertIn("--max-per-example-rows 0", uncapped_text)
            self.assertIn("strictmask_combined_reviewer_stats_uncapped_per_example", uncapped_text)
            self.assertIn("not the complete per-example table", readme_text)
            self.assertIn("tables/strict_wtb_seed_metrics.csv", final_text)
            self.assertIn("generated/table_strict_wtb_seed_metrics.tex", final_text)
            self.assertNotIn("generated/table_strict_wtb_seed_metrics.csv", final_text)
            self.assertIn("strict_wtb_evidence_manifest.json", final_text)
            self.assertIn("paired_multiplicity_table.csv", final_text)
            self.assertIn("operational-baselines", final_text)
            self.assertIn("decision_reserve_wtb_operational_windows/reserve_decision_operational_windows.csv", final_text)
            self.assertIn("reserve_decision_system_baselines.csv", final_text)
            self.assertIn("reserve_decision_cost_ratio_sensitivity.csv", final_text)
            self.assertIn("decision_reserve_wtb_operational_windows_guard/reserve_decision_guard.json", final_text)
            self.assertIn("external_wind_run_status.csv", final_text)
            self.assertIn("external_wind_cache_status.csv", final_text)
            self.assertIn("external-wind-portability-rescue", final_text)
            self.assertIn("external_wind_recalibration_summary.csv", final_text)
            self.assertIn("external_wind_recalibration_guard.json", final_text)
            self.assertIn("evidence-freeze-guard", final_text)
            self.assertIn("final_evidence_freeze_guard/evidence_freeze_guard.json", final_text)
            self.assertIn("external_wind_source_manifest.csv", final_text)
            self.assertIn("external_wind_source_status.csv", final_text)
            self.assertIn("external_wind_source_guard.json", final_text)
            self.assertIn("external-wind-source-guard", final_text)
            self.assertIn("external_wind_scada_inspection.csv", final_text)
            self.assertIn("external_wind_protocol.json", final_text)
            self.assertIn("external_wind_reviewer_pack_commands.ps1", final_text)
            self.assertIn("external-wind-guard", final_text)
            self.assertIn("external_wind_kelmarsh_to_penmanshiel_leave_one_farm_out", final_text)
            self.assertIn("run_external_wind_full_evidence.ps1", external_text)
            self.assertIn("$DownloadScada", external_text)
            self.assertIn("$RunTraining", external_text)
            self.assertIn("$RunAllTrainingCommands", external_text)
            self.assertIn("$ParallelTraining", external_text)
            self.assertIn("missing 5-seed runs only", readme_text)
            self.assertIn("external_wind_full_evidence", index["scripts"])
            self.assertIn("generate_uncapped_per_example_reviewer_stats", index["scripts"])


if __name__ == "__main__":
    unittest.main()
