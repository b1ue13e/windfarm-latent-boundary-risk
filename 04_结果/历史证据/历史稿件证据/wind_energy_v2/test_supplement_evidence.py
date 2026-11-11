"""Read-only regression checks for the supplement's stored-record projection."""
import csv
import json
import unittest

import export_supplement_evidence as export


class ProjectionTest(unittest.TestCase):
    def test_saved_csv_copies_are_byte_identical(self):
        for target, source in export.COPIES.items():
            self.assertEqual((export.HERE / "supplement_data" / target).read_bytes(), (export.ROOT / source).read_bytes())

    def test_source_csv_dimensions_and_failed_states(self):
        expected = {
            "towie_all_90_cases.csv": 90,
            "wtb_all_420_sufficiency_cases.csv": 420,
            "wtb_all_420_minimum_cases.csv": 420,
        }
        for target, source in export.COPIES.items():
            with (export.ROOT / source).open(encoding="utf-8", newline="") as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(len(rows), expected[target])
        source = export.ROOT / export.COPIES["towie_all_90_cases.csv"]
        with source.open(encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        failures = [row for row in rows if row["historical_fixed_status"] == "CONFIRMATION_NOT_ESTABLISHED"]
        self.assertEqual(len(failures), 3)
        self.assertEqual({row["condition"] for row in failures}, {"delay3"})

    def test_all_registered_policies_preserve_stored_resources(self):
        rows = export.registered_rows()
        self.assertEqual(len(rows), 550)
        self.assertEqual(sum(row["condition"] == "pitch_withheld" for row in rows), 225)
        chosen = [row for row in rows if row["condition"] == "pitch_withheld" and row["policy_label"] == "P1/HGB/q0.925"]
        self.assertEqual(len(chosen), 1)
        self.assertEqual([chosen[0][key] for key in ("incremental_channels", "learned_predictor_passes", "raw_input_width")], [1, 1, 5])

    def test_wtb_has_14_settings_and_28_primary_span_assessments(self):
        source = export.ROOT / export.COPIES["wtb_all_420_sufficiency_cases.csv"]
        with source.open(encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(len({(row["condition"], row["budget"]) for row in rows}), 14)
        main = [row for row in rows if row["span"] == "3" and float(row["epsilon"]) == 0.02]
        self.assertEqual(len(main), 28)
        self.assertTrue(all(row["status"] == "NO_IDENTIFIED_POLICY" for row in main))
        self.assertTrue(all(int(row["risk_qualified_count"]) > 0 for row in main))

    def test_witnesses_are_stored_records_not_recomputed_bounds(self):
        rows = export.witness_rows()
        group = export.stored_group(3)
        records = export.stored_case(group)["minimum_audit"]["excluded"]
        self.assertEqual(len(rows), 15)
        self.assertEqual(sum(row["reason"] == "RISK_LOWER_ABOVE_CAP" for row in rows), 2)
        for row, record in zip(rows, records, strict=True):
            self.assertEqual(row["stored_index"], record["index"])
            self.assertEqual(row["stored_relative_cost_lower"], record.get("ratio_lower", ""))
        self.assertEqual(export.stored_case(group)["minimum_audit"]["chosen"], [41])
        self.assertNotIn(group["labels"].index("P1/HGB/q0.95"), export.stored_case(group)["sufficient_set"]["eligible_indices"])

    def test_sensitivity_retains_three_separate_stored_families(self):
        rows = export.sensitivity_rows()
        self.assertEqual([row["span_days"] for row in rows], [1, 3, 7])
        self.assertEqual({row["policy_label"] for row in rows}, {"P1/HGB/q0.925"})
        self.assertTrue(all(row["smaller_count"] == row["excluded_count"] == 15 for row in rows))
        self.assertTrue(all(row["coordinate_family_size"] == 74500 for row in rows))


if __name__ == "__main__":
    unittest.main()
