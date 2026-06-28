from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from main import build_parser
from windfarm_moe.science_readiness import run_science_readiness_dashboard
from windfarm_moe.utils import load_json, save_json


class ScienceReadinessDashboardTests(unittest.TestCase):
    def test_parser_accepts_science_readiness_dashboard(self) -> None:
        args = build_parser().parse_args(
            [
                "science-readiness-dashboard",
                "--output-dir",
                "out",
                "--future-holdout-evidence-guard",
                "future_evidence.json",
                "--spatial-holdout-evidence-guard",
                "spatial_evidence.json",
                "--strict-ablation-evidence-guard",
                "ablation_evidence.json",
                "--threshold-controls-evidence-guard",
                "threshold_evidence.json",
                "--external-wind-guard",
                "external_guard.json",
                "--external-wind-source-guard",
                "external_source_guard.json",
                "--external-wind-adaptation-guard",
                "external_adaptation_guard.json",
                "--final-evidence-manifest",
                "final_manifest.json",
            ]
        )

        self.assertEqual(args.command, "science-readiness-dashboard")
        self.assertEqual(args.output_dir, "out")
        self.assertEqual(args.future_holdout_evidence_guard, "future_evidence.json")
        self.assertEqual(args.spatial_holdout_evidence_guard, "spatial_evidence.json")
        self.assertEqual(args.strict_ablation_evidence_guard, "ablation_evidence.json")
        self.assertEqual(args.threshold_controls_evidence_guard, "threshold_evidence.json")
        self.assertEqual(args.external_wind_guard, "external_guard.json")
        self.assertEqual(args.external_wind_source_guard, "external_source_guard.json")
        self.assertEqual(args.external_wind_adaptation_guard, "external_adaptation_guard.json")
        self.assertEqual(args.final_evidence_manifest, "final_manifest.json")

    def test_dashboard_summarizes_incomplete_evidence_chain(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            strict = root / "strict_guard.json"
            future = root / "future_guard.json"
            future_evidence = root / "future_evidence_guard.json"
            spatial = root / "spatial_guard.json"
            spatial_evidence = root / "spatial_evidence_guard.json"
            ablation_evidence = root / "ablation_evidence_guard.json"
            threshold_evidence = root / "threshold_evidence_guard.json"
            reviewer = root / "reviewer_config.json"
            audit = root / "audit.md"
            save_json(
                strict,
                {
                    "status": "ready_to_execute_training",
                    "expected_runs": 30,
                    "complete_runs": 10,
                    "missing_runs": 20,
                    "checks": {"all_expected_runs_complete": False},
                },
            )
            save_json(future, {"status": "ready_to_execute_training", "checks": {}})
            save_json(
                future_evidence,
                {
                    "status": "ready_to_execute_training",
                    "expected_runs": 5,
                    "complete_runs": 0,
                    "missing_runs": 5,
                    "checks": {"all_expected_runs_complete": False},
                },
            )
            save_json(
                spatial,
                {
                    "status": "ready_to_execute_training",
                    "expected_runs": 15,
                    "complete_runs": 0,
                    "missing_runs": 15,
                    "checks": {"all_expected_runs_complete": False},
                },
            )
            save_json(
                spatial_evidence,
                {
                    "status": "ready_to_execute_training",
                    "expected_runs": 15,
                    "complete_runs": 0,
                    "missing_runs": 15,
                    "checks": {"all_expected_runs_complete": False},
                },
            )
            save_json(
                ablation_evidence,
                {
                    "status": "ready_to_execute_training",
                    "expected_runs": 50,
                    "complete_runs": 0,
                    "missing_runs": 50,
                    "checks": {"all_expected_runs_complete": False},
                },
            )
            save_json(
                threshold_evidence,
                {
                    "status": "queued_or_in_progress",
                    "expected_runs": 20,
                    "complete_runs": 4,
                    "missing_runs": 16,
                    "checks": {"all_expected_runs_complete": False},
                },
            )
            save_json(reviewer, {"n_runs": 5})
            audit.write_text(
                "ERA5: persistence wins headline RMSE; routing calibrates gate-regime agreement; "
                "not broad forecast repair and not broad deployment.\n",
                encoding="utf-8",
            )

            output_dir = run_science_readiness_dashboard(
                output_dir=root / "dashboard",
                root_dir=root,
                strict_baseline_guard=strict,
                future_holdout_guard=future,
                future_holdout_evidence_guard=future_evidence,
                spatial_holdout_guard=spatial,
                spatial_holdout_evidence_guard=spatial_evidence,
                strict_ablation_evidence_guard=ablation_evidence,
                threshold_controls_evidence_guard=threshold_evidence,
                reviewer_pack_config=reviewer,
                audit_doc=audit,
                ablation_suite_dir=root / "ablation_missing",
            )
            dashboard = load_json(output_dir / "science_readiness_status.json")

            self.assertEqual(dashboard["overall_status"], "active_incomplete")
            by_requirement = {row["requirement"]: row for row in dashboard["items"]}
            self.assertEqual(
                by_requirement[
                    "Strict-cache strong baselines: Graph WaveNet, Graph Transformer, GAT-GRU, PatchTST, iTransformer, TiDE"
                ]["complete"],
                10,
            )
            self.assertEqual(by_requirement["Pre-specified future-period holdout"]["missing"], 5)
            self.assertEqual(by_requirement["WTB east-cluster spatial turbine-group holdout"]["missing"], 15)
            self.assertEqual(
                by_requirement["Strict-cache wrong-threshold mechanism negative controls"]["complete"],
                4,
            )
            self.assertEqual(by_requirement["ERA5 claim narrowed away from forecasting advantage"]["status"], "pass")
            self.assertTrue((output_dir / "science_readiness_items.csv").exists())
            self.assertTrue((output_dir / "README.md").exists())
            refresh_script = output_dir / "refresh_readiness.ps1"
            self.assertTrue(refresh_script.exists())
            self.assertIn("strict-baseline-guard", refresh_script.read_text(encoding="utf-8"))

    def test_dashboard_can_mark_within_wtb_ready_when_external_is_not_citable(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            final_manifest = root / "final_manifest.json"
            external_guard = root / "external_guard.json"
            source_guard = root / "external_source_guard.json"
            adaptation_guard = root / "external_adaptation_guard.json"
            audit = root / "audit.md"
            save_json(
                final_manifest,
                {
                    "status": "complete_ready_for_submission_tables",
                    "claim_gate": "within_wtb_only",
                },
            )
            save_json(
                external_guard,
                {
                    "status": "blocked_external_wind_incomplete",
                    "claim_gate": "blocked_not_citable",
                    "expected_runs": 80,
                    "complete_runs": 0,
                },
            )
            save_json(
                source_guard,
                {
                    "status": "complete_external_source_evidence",
                    "claim_gate": "within_wtb_only",
                    "min_files": 31,
                    "n_local_exists": 31,
                },
            )
            save_json(
                adaptation_guard,
                {
                    "status": "complete_site_specific_adaptation_diagnostic",
                    "claim_gate": "within_wtb_external_diagnostics_only",
                    "site_specific_adaptation_wording_allowed": False,
                    "n_routing_runs": 40,
                    "n_adapted_runs": 40,
                },
            )
            audit.write_text(
                "ERA5: persistence wins headline RMSE; routing calibrates gate-regime agreement; "
                "not broad forecast repair and not broad deployment.\n",
                encoding="utf-8",
            )

            output_dir = run_science_readiness_dashboard(
                output_dir=root / "dashboard",
                root_dir=root,
                final_evidence_manifest=final_manifest,
                external_wind_guard=external_guard,
                external_wind_source_guard=source_guard,
                external_wind_adaptation_guard=adaptation_guard,
                audit_doc=audit,
            )
            dashboard = load_json(output_dir / "science_readiness_status.json")
            by_requirement = {row["requirement"]: row for row in dashboard["items"]}

            self.assertEqual(dashboard["overall_status"], "within_wtb_submission_ready_external_not_citable")
            self.assertEqual(dashboard["claim_gate"], "within_wtb_only")
            self.assertEqual(dashboard["external_wind_claim_gate"], "blocked_not_citable")
            self.assertEqual(
                by_requirement["External Kelmarsh/Penmanshiel portability guard"]["status"],
                "blocked_not_citable",
            )
            self.assertEqual(
                by_requirement["Kelmarsh/Penmanshiel site-specific small-calibration adaptation"]["status"],
                "diagnostic_only",
            )
            self.assertEqual(by_requirement["Final evidence manifest claim gate"]["status"], "within_wtb_ready")


if __name__ == "__main__":
    unittest.main()
