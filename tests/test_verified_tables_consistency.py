from __future__ import annotations

import json
import re
import unittest
from pathlib import Path
import pandas as pd


class VerifiedTablesConsistencyTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[1]
        self.benchmark_root = self.root / "artifacts" / "clean_evidence_v2" / "risk_layer_benchmark"
        self.paper_path = self.root / "paper_tste_ieee.md"
        self.paper_text = self.paper_path.read_text(encoding="utf-8")
        self.supp_path = self.root / "paper_tste_supplementary.md"
        self.supp_text = self.supp_path.read_text(encoding="utf-8")
        self.combined_text = self.paper_text + "\n" + self.supp_text

    def test_all_six_suites_passed_hard_gates(self):
        suites = ["h1_lead1", "h6_lead6", "kelmarsh_h1", "kelmarsh_h6", "penmanshiel_h1", "penmanshiel_h6"]
        for s in suites:
            manifest_path = self.benchmark_root / s / "hard_gate_verified_manifest.json"
            self.assertTrue(manifest_path.exists(), f"Missing hard gate manifest for suite {s}")
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertTrue(data.get("passed_all_gates"), f"Hard gate failed for suite {s}: {data.get('failures')}")
            self.assertEqual(len(data.get("required_seeds", [])), 5, f"Expected 5 seeds for suite {s}")

    def test_table1_h6_benchmark_numbers_in_manuscript(self):
        h6_csv = self.benchmark_root / "h6_lead6" / "cross_seed_aggregate.csv"
        self.assertTrue(h6_csv.exists(), "Missing h6_lead6 cross_seed_aggregate.csv")
        df = pd.read_csv(h6_csv, header=[0, 1])
        df.columns = [c[0] if "Unnamed" in c[1] else f"{c[0]}_{c[1]}" for c in df.columns]

        for _, row in df.iterrows():
            cost_m = int(round(row["total_cost_mean"]))
            # Match LaTeX formatted or plain formatted number
            cost_with_braces = f"{cost_m:,}".replace(",", "{,}")
            cost_plain = f"{cost_m:,}"
            found = (cost_with_braces in self.paper_text) or (cost_plain in self.paper_text)
            self.assertTrue(
                found,
                f"Table 1 number for {row['regime']} {row['model']} (cost {cost_plain}) not found in manuscript!",
            )

    def test_table2_h6_paired_numbers_in_manuscript(self):
        paired_csv = self.benchmark_root / "h6_lead6" / "paired_significance.csv"
        self.assertTrue(paired_csv.exists(), "Missing h6_lead6 paired_significance.csv")
        df = pd.read_csv(paired_csv)

        for _, row in df.iterrows():
            delta_val = row["delta_cost_mean"] if "delta_cost_mean" in row else row["mean_cost_delta"]
            delta = int(round(delta_val))
            delta_with_braces = f"{abs(delta):,}".replace(",", "{,}")
            delta_plain = f"{abs(delta):,}"
            found = (delta_with_braces in self.paper_text) or (delta_plain in self.paper_text)
            self.assertTrue(
                found,
                f"Table 2 delta for {row['regime']} {row['model']} ({delta_plain}) not found in manuscript!",
            )

    def test_table3_h1_benchmark_numbers_in_manuscript(self):
        h1_csv = self.benchmark_root / "h1_lead1" / "cross_seed_aggregate.csv"
        self.assertTrue(h1_csv.exists(), "Missing h1_lead1 cross_seed_aggregate.csv")
        df = pd.read_csv(h1_csv, header=[0, 1])
        df.columns = [c[0] if "Unnamed" in c[1] else f"{c[0]}_{c[1]}" for c in df.columns]

        for _, row in df.iterrows():
            cost_m = int(round(row["total_cost_mean"]))
            cost_with_braces = f"{cost_m:,}".replace(",", "{,}")
            cost_plain = f"{cost_m:,}"
            found = (cost_with_braces in self.combined_text) or (cost_plain in self.combined_text)
            self.assertTrue(
                found,
                f"Table 3 (Table A11j) number for {row['regime']} {row['model']} (cost {cost_plain}) not found in manuscript/supplementary!",
            )

    def test_table4_h1_paired_numbers_in_manuscript(self):
        paired_csv = self.benchmark_root / "h1_lead1" / "paired_significance.csv"
        self.assertTrue(paired_csv.exists(), "Missing h1_lead1 paired_significance.csv")
        df = pd.read_csv(paired_csv)

        for _, row in df.iterrows():
            delta_val = row["delta_cost_mean"] if "delta_cost_mean" in row else row["mean_cost_delta"]
            delta = int(round(delta_val))
            delta_with_braces = f"{abs(delta):,}".replace(",", "{,}")
            delta_plain = f"{abs(delta):,}"
            found = (delta_with_braces in self.combined_text) or (delta_plain in self.combined_text)
            self.assertTrue(
                found,
                f"Table 4 (Table A11k) delta for {row['regime']} {row['model']} ({delta_plain}) not found in manuscript/supplementary!",
            )


if __name__ == "__main__":
    unittest.main()
