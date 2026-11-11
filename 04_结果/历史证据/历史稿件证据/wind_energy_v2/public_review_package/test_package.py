"""Regression checks for the portable record auditor; no research execution."""
import json
import csv
from pathlib import Path
import shutil
import tempfile
import unittest

import verify_package as verify
import refresh_manifest


class PackageTest(unittest.TestCase):
    def test_full_record_audit(self):
        report = verify.audit(verify.HERE)
        self.assertEqual(report["status"], "PASS_ARCHIVED_RECORD_AUDIT")
        self.assertEqual(report["secondary"]["cost_bridge"]["smaller"], 15)
        self.assertFalse(report["new_resampling"])

    def test_sha_tampering_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "a").write_bytes(b"original")
            manifest = {"files": {"a": {"bytes": 8, "sha256": verify.sha(root / "a")}}}
            (root / "MANIFEST.json").write_text(json.dumps(manifest))
            self.assertEqual(verify.verify_manifest(root), 1)
            (root / "a").write_bytes(b"modified")
            with self.assertRaisesRegex(ValueError, "SHA256 mismatch"):
                verify.verify_manifest(root)

    def test_manifest_cannot_escape_package(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            manifest = {"files": {"../outside": {"bytes": 0, "sha256": ""}}}
            (root / "MANIFEST.json").write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "escapes package"):
                verify.verify_manifest(root)

    def test_risk_nonqualification_does_not_prove_infeasibility(self):
        group = {"risk_lower": [[.08,.05]], "risk_upper": [[.12,.08]],
                 "relative_ratio_upper": [[0,.03],[0,0]], "relative_ratio_lower": [[0,.01],[0,0]],
                 "resources": [[0,1,4],[1,1,5]]}
        self.assertEqual(verify.near_optimal(group,[0,1],[True,True],.02)[-1],[1])
        result = verify.minimum_audit(group,[0,1],[1],.02)
        self.assertEqual(result["status"], "MINIMUM_UNRESOLVED")

    def test_cost_witness_must_be_risk_qualified(self):
        group = {"risk_lower": [[.05,.05]], "risk_upper": [[.09,.12]],
                 "relative_ratio_lower": [[0,.30],[0,0]], "resources": [[0,1,4],[1,1,5]]}
        result = verify.minimum_audit(group,[0,1],[1],.02)
        self.assertEqual(result["status"], "MINIMUM_UNRESOLVED")

    def test_missing_file_fails(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "MANIFEST.json").write_text(json.dumps({"files":{"missing":{"bytes":0,"sha256":""}}}))
            with self.assertRaisesRegex(ValueError,"Missing file"):
                verify.verify_manifest(root)

    def test_v2_figure3_numeric_tampering_fails(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            for relative in ("data/confirmation/secondary_span3.json","protocol/confirmation_protocol.json",
                             "figure_data/v2/fig3_secondary_minimality.csv","figure_data/v2/fig3_field_manifest.json"):
                target=root/relative;target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(verify.HERE/relative,target)
            self.assertEqual(verify.verify_fig3_v2(root)["rows"],17)
            relative="figure_data/v2/fig3_secondary_minimality.csv"
            data=verify.rows(root,relative);data[0]["worst_paired_cost_upper_percent"]="0.5"
            with (root/relative).open("w",encoding="utf-8",newline="")as stream:
                writer=csv.DictWriter(stream,fieldnames=list(data[0]));writer.writeheader();writer.writerows(data)
            with self.assertRaisesRegex(ValueError,"numeric field differs"):
                verify.verify_fig3_v2(root)

    def test_refresh_rejects_unknown_payload_and_personal_paths(self):
        with tempfile.TemporaryDirectory()as folder:
            root=Path(folder)
            (root/"unknown.secret").write_text("data")
            with self.assertRaisesRegex(ValueError,"Unapproved payload"):
                refresh_manifest.safe_payload(root)
            (root/"unknown.secret").unlink()
            (root/"README.md").write_text("C"+":"+"/"+"Users"+"/"+"example/file")
            with self.assertRaisesRegex(ValueError,"Sensitive"):
                refresh_manifest.safe_payload(root)


if __name__ == "__main__":
    unittest.main()
