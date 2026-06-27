from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from main import build_parser
from windfarm_moe.reproducibility import DEFAULT_REPRODUCIBILITY_FILES, run_reproducibility_manifest
from windfarm_moe.utils import load_json, save_json


class ReproducibilityManifestTests(unittest.TestCase):
    def test_default_manifest_tracks_final_evidence_and_external_guard(self) -> None:
        paths = {str(row["path"]) for row in DEFAULT_REPRODUCIBILITY_FILES}

        self.assertIn("artifacts/final_evidence_package/manifest/evidence_manifest_final.json", paths)
        self.assertIn("artifacts/final_evidence_package/export/final_table_export_status.json", paths)
        self.assertIn("artifacts/operational_baselines_wtb_strictmask/wtb_operational_baselines.csv", paths)
        self.assertIn("artifacts/decision_reserve_wtb_operational_windows/reserve_decision_operational_windows.csv", paths)
        self.assertIn("artifacts/decision_reserve_wtb_operational_windows/reserve_decision_horizon_time_sensitivity.csv", paths)
        self.assertIn("artifacts/decision_reserve_wtb_operational_windows/reserve_decision_horizon_quantile_whatif.csv", paths)
        self.assertIn("artifacts/reserve_quantile_baseline/reserve_quantile_baseline.csv", paths)
        self.assertIn("artifacts/reserve_toy_operational_cost/reserve_toy_operational_cost.csv", paths)
        self.assertIn("artifacts/decision_reserve_wtb_operational_windows_guard/reserve_decision_guard.json", paths)
        self.assertIn("artifacts/anchor_stress_guard/anchor_stress_guard.json", paths)
        self.assertIn(
            "artifacts/anchor_stress_early_warning_wtb_strictmask/anchor_stress_early_warning_guard.json",
            paths,
        )
        self.assertIn(
            "artifacts/anchor_stress_early_warning_wtb_strictmask/anchor_stress_early_warning_summary.csv",
            paths,
        )
        self.assertIn("artifacts/applied_energy_diagnostics/graphical_abstract_applied_energy.png", paths)
        self.assertIn("artifacts/external_wind_guard/external_wind_guard.json", paths)
        self.assertIn("artifacts/external_wind_small_calibration_adaptation/adaptation_guard.json", paths)
        self.assertIn("artifacts/external_wind_small_calibration_adaptation/adaptation_summary.csv", paths)
        self.assertIn("artifacts/reproduction_package_20260611/rebuild_final_evidence_package.ps1", paths)

    def test_parser_accepts_reproducibility_manifest_command(self) -> None:
        args = build_parser().parse_args(
            [
                "reproducibility-manifest",
                "--output-dir",
                "out",
                "--hash-max-mb",
                "1",
            ]
        )

        self.assertEqual(args.command, "reproducibility-manifest")
        self.assertEqual(args.output_dir, "out")

    def test_manifest_completes_when_required_files_and_weights_exist(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            required = root / "required.txt"
            required.write_text("ok\n", encoding="utf-8")
            self._write_weights(root)

            output_dir = run_reproducibility_manifest(
                output_dir=root / "manifest",
                root_dir=root,
                evidence_files=[
                    {"category": "test", "label": "Required", "path": "required.txt", "required": True}
                ],
            )
            manifest = load_json(output_dir / "reproducibility_manifest.json")

            self.assertEqual(manifest["status"], "complete_ready_for_reproducibility_package")
            self.assertEqual(manifest["strict_model_weight_count"], 5)
            self.assertTrue((output_dir / "reproducibility_file_manifest.csv").exists())

    def test_manifest_is_preliminary_when_dashboard_has_active_gaps(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            required = root / "required.txt"
            required.write_text("ok\n", encoding="utf-8")
            self._write_weights(root)
            dashboard = root / "artifacts" / "science_readiness_dashboard_20260611"
            dashboard.mkdir(parents=True)
            save_json(dashboard / "science_readiness_status.json", {"overall_status": "active_incomplete"})

            output_dir = run_reproducibility_manifest(
                output_dir=root / "manifest",
                root_dir=root,
                evidence_files=[
                    {"category": "test", "label": "Required", "path": "required.txt", "required": True}
                ],
            )
            manifest = load_json(output_dir / "reproducibility_manifest.json")

            self.assertEqual(manifest["status"], "preliminary_active_experiment_gaps")
            self.assertTrue(manifest["checks"]["active_experiment_gaps"])

    def test_manifest_completes_for_within_wtb_ready_dashboard_status(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            required = root / "required.txt"
            required.write_text("ok\n", encoding="utf-8")
            self._write_weights(root)
            dashboard = root / "artifacts" / "science_readiness_dashboard_20260611"
            dashboard.mkdir(parents=True)
            save_json(
                dashboard / "science_readiness_status.json",
                {"overall_status": "within_wtb_submission_ready_external_not_citable"},
            )

            output_dir = run_reproducibility_manifest(
                output_dir=root / "manifest",
                root_dir=root,
                evidence_files=[
                    {"category": "test", "label": "Required", "path": "required.txt", "required": True}
                ],
            )
            manifest = load_json(output_dir / "reproducibility_manifest.json")

            self.assertEqual(manifest["status"], "complete_ready_for_reproducibility_package")
            self.assertFalse(manifest["checks"]["active_experiment_gaps"])

    def test_manifest_blocks_when_required_file_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_weights(root)

            output_dir = run_reproducibility_manifest(
                output_dir=root / "manifest",
                root_dir=root,
                evidence_files=[
                    {"category": "test", "label": "Missing", "path": "missing.txt", "required": True}
                ],
            )
            manifest = load_json(output_dir / "reproducibility_manifest.json")

            self.assertEqual(manifest["status"], "blocked_missing_reproducibility_inputs")
            self.assertEqual(manifest["n_missing_required_files"], 1)

    def _write_weights(self, root: Path) -> None:
        for seed in [201, 202, 203, 204, 205]:
            path = root / "artifacts" / "strictmask_validation_wtb_full" / f"wtb_bal_align_force_seed{seed}"
            path.mkdir(parents=True)
            (path / "best_model.pt").write_bytes(b"weights")


if __name__ == "__main__":
    unittest.main()
