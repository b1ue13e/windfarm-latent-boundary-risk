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
            "artifacts/final_evidence_package/export/tables/early_warning_consequence_audit.csv",
            "artifacts/final_evidence_package/export/tables/accountability_tradeoff.csv",
            "artifacts/final_evidence_package/export/tables/dispatch_reserve_main_table.csv",
            "artifacts/final_evidence_package/export/tables/engineering_unit_value_translation.csv",
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
                main.read_text(encoding="utf-8").replace("10.39-RMSE", "10.38-RMSE"),
                encoding="utf-8",
            )

            out = run_number_consistency_audit(root, root / "audit")
            summary = load_json(out / "tste_number_consistency_audit.json")

            self.assertEqual(summary["status"], "blocked_tste_number_mismatch")
            self.assertIn("rmse_price_vs_graph_wavenet", summary["failed_claims"])


if __name__ == "__main__":
    unittest.main()
