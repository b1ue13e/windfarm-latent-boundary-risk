from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from scripts.verify_tste_number_consistency import run_number_consistency_audit
from windfarm_moe.utils import load_json


class TsteNumberConsistencyTests(unittest.TestCase):
    def _copy_fixture(self, root: Path) -> None:
        repo = Path.cwd()
        for rel in [
            "artifacts/paper_assets/tables/table_main_benchmark.csv",
            "artifacts/paper_assets/tables/table_wtb_ablation.csv",
            "artifacts/anchor_stress_early_warning_wtb_strictmask/anchor_stress_early_warning_summary.csv",
            "artifacts/early_warning_classifier_baseline_wtb/early_warning_classifier_baseline_summary.csv",
            "artifacts/final_evidence_package/export/tables/early_warning_consequence_audit.csv",
            "artifacts/class_weight_boundary_audit/class_weight_sensitivity_summary.csv",
            "artifacts/mechanism_behavior_pack_wtb/gate_transition_lead_lag.csv",
            "artifacts/anchor_stress_guard/anchor_stress_summary.csv",
            "artifacts/fair_degradation_replay_20260903/fair_degradation_summary.csv",
            "artifacts/decision_reserve_trainweight_allclean_20260830/reserve_decision_summary.csv",
            "artifacts/decision_reserve_trainweight_allclean_20260830/reserve_decision_raw_runs.csv",
            "artifacts/signature_gate_lhb_guard_20260902/anchor_stress_summary.csv",
            "artifacts/external_wind_guard_windowfix/external_wind_guard.json",
            "artifacts/external_wind_lhb_guard_full_5seed/external_wind_guard.json",
            "artifacts/external_wind_lhb_anchor_intervention_full/lhb_anchor_observability_guard.json",
            "artifacts/farm_aggregate_reserve_20260905/farm_pcc_paired_summary.csv",
            "artifacts/markov_gilbert_eval_honest/markov_gilbert_guard.json",
            "artifacts/iec_density_rolling_eval/iec_rolling_guard.json",
            "docs/tste_trainonly_rerun_results_20260830.md",
            "paper_tste_ieee.md",
            "paper_tste_supplementary.md",
            "cover_letter_tste.md",
        ]:
            src = repo / rel
            dst = root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)

    def test_number_consistency_audit_passes_current_submission_tokens(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._copy_fixture(root)

            out = run_number_consistency_audit(root, root / "audit")
            summary = load_json(out / "tste_number_consistency_audit.json")

            self.assertEqual(summary["status"], "complete_tste_number_consistency")
            self.assertEqual(summary["n_failed"], 0)

    def test_number_consistency_audit_blocks_missing_manuscript_token(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._copy_fixture(root)
            main = root / "paper_tste_ieee.md"
            main.write_text(
                main.read_text(encoding="utf-8").replace("224.34", "224.33"),
                encoding="utf-8",
            )

            out = run_number_consistency_audit(root, root / "audit")
            summary = load_json(out / "tste_number_consistency_audit.json")

            self.assertEqual(summary["status"], "blocked_tste_number_mismatch")
            self.assertIn("best_strict_cache_baseline_overall_rmse", summary["failed_claims"])


if __name__ == "__main__":
    unittest.main()
