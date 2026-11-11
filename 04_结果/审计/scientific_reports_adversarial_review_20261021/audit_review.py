"""Check existing review sources without running any experimental implementation."""
from pathlib import Path
import csv
import hashlib
import json
import math
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DRAFT = ROOT / "manuscripts/scientific_reports"


def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    checks = []

    def check(name, passed, evidence):
        checks.append({"check": name, "passed": bool(passed), "evidence": evidence})

    before = load(HERE / "PRESERVATION_BEFORE.json")
    changed = [name for name, record in before["files"].items()
               if not (ROOT / name).is_file() or sha(ROOT / name) != record["sha256"]]
    check("draft_v2_and_authority_files_unchanged", not changed,
          {"count": len(before["files"]), "changed": changed})
    m = load(DRAFT / "source_data/M_original_summary.json")
    later = load(DRAFT / "source_data/M_controls_summary.json")
    r = load(DRAFT / "source_data/R_paired_intervals.json")
    check("original154", m["primary_family_size"] == 154, m["primary_family_size"])
    check("later596", later["family_size"] == 596, later["family_size"])
    for estimator in ("HGB", "MLP"):
        key = f"{estimator}:P_premium_vs_Z|cost|D"
        record = m["registered_intervals"][key]
        check("direct_power_pitch_original:" + estimator,
              record["upper"] < 0 and record["lower"] <= record["point"] <= record["upper"],
              record)
        record = later["interval"]["Common:" + key]
        check("direct_power_pitch_common:" + estimator,
              record["upper"] < 0 and record["lower"] <= record["point"] <= record["upper"],
              record)
    expected = {
        ("B_Consequences", "A_Wind"): -2.734363955871603,
        ("C_PitchScore", "B_Consequences"): -0.06798086059689047,
        ("D_TruePitch_Diagnostic", "B_Consequences"): -0.13238054925177659,
        ("E_Compressed", "B_Consequences"): 1.7195662509603067,
    }
    for (left, right), point in expected.items():
        row = next(x for x in r if x["left"] == left and x["right"] == right
                   and x["condition"] == "pitch_withheld" and x["metric"] == "loss_sum"
                   and x["block_span"] == 3)
        check("R_primary:" + left, row["point"] == point and row["family_size"] == 42, row)
    for left in ("C_PitchScore", "D_TruePitch_Diagnostic"):
        row = next(x for x in r if x["left"] == left and x["right"] == "B_Consequences"
                   and x["condition"] == "pitch_withheld" and x["metric"] == "loss_sum"
                   and x["block_span"] == 1)
        lo, hi = row["simultaneous_ci"]
        check("R_one_day_crosses_zero:" + left, lo <= 0 <= hi, row)
    for right in ("C_WindScore", "C_ShuffledScore"):
        row = next(x for x in r if x["left"] == "C_PitchScore" and x["right"] == right
                   and x["condition"] == "pitch_withheld" and x["metric"] == "loss_sum"
                   and x["block_span"] == 3)
        lo, hi = row["simultaneous_ci"]
        check("semantic_control_unresolved:" + right, lo <= 0 <= hi, row)
    check("D_minus_C_not_generated",
          not any({x["left"], x["right"]} == {"D_TruePitch_Diagnostic", "C_PitchScore"} for x in r),
          "Existing pair list only; no new contrast computed")
    check("all12_corrected_routes_false", len(later["corrected_routes"]) == 4
          and all(set(v) == {"A", "B", "C"} and not any(v.values())
                  for v in later["corrected_routes"].values()), later["corrected_routes"])
    q = later["jointly_qualified"]
    check("common_hgb_pitch_endpoint_unqualified", not q["Common:HGB:OZ6"], q["Common:HGB:OZ6"])
    check("common_mlp_direct_endpoints_qualified", q["Common:MLP:OP6"] and q["Common:MLP:OZ6"],
          [q["Common:MLP:OP6"], q["Common:MLP:OZ6"]])
    witness = later["interval"]["Common:HGB:severity_P_vs_PZ|instance_U|3"]
    check("fixed_seed204_adverse_severity_witness", witness["lower"] > .001
          and math.isclose(witness["lower"], .0028220972446333786, abs_tol=1e-16), witness)
    # Check saved display transformations; do not invoke the plot builder.
    figure = load(DRAFT / "qa/figure_receipt.json")
    records = figure.get("fields", figure.get("source_fields", []))
    if not records:
        records = next(v for v in figure.values() if isinstance(v, list) and v
                       and isinstance(v[0], dict) and "figure" in v[0])
    for index, item in enumerate(records):
        if item["figure"] == "fig2":
            point, lower, upper = item["source_values"]
            want = [-100*point, -100*upper, -100*lower] if "-G" in item["transformation"] else [100*point, 100*lower, 100*upper]
            check(f"fig2_transform:{index}", all(math.isclose(x, y, rel_tol=1e-12, abs_tol=1e-12)
                  for x, y in zip(want, item["displayed_values"])), item)
    check("fig2_has20_cost_comparisons", sum(x["figure"] == "fig2" for x in records) == 20,
          figure.get("row_selection", {}))
    check("fig3_has6_cost_comparisons_and15_mse_points",
          sum(x["figure"] == "fig3" and "record_index" in x for x in records) == 6
          and sum(x["figure"] == "fig3" and "displayed_value" in x for x in records) == 15,
          "Pitch-withheld primary six comparisons, fifteen fixed-fit point diagnostics")
    with (HERE / "ISSUES.csv").open(encoding="utf-8-sig", newline="") as handle:
        issues = list(csv.DictReader(handle))
    check("review_issue_counts", len(issues) == 8 and sum(x["severity"] == "S3" for x in issues) == 6
          and sum(x["severity"] == "S2" for x in issues) == 2, issues)
    clock = load(HERE / "CLOCK_BOUNDARY_AUDIT.json")
    check("clock_index_bytes_match_original", clock["sha_matches_original"], clock["source"])
    check("clock_retrospective_state_fit_exception",
          clock["first_nominal_publication"] < clock["latest_assumed_label_release"] < clock["first_state_issue"], clock)
    check("clock_policy_stage_publication_later_than_fit_labels",
          clock["first_policy_nominal_publication"] > clock["latest_assumed_label_release"], clock)
    with (HERE / "CLAIM_EVIDENCE_DISPLAY_REVIEW.csv").open(encoding="utf-8-sig", newline="") as handle:
        claims = list(csv.DictReader(handle))
    check("claim_map_sources_exist", all((DRAFT / x["source_file"]).exists() for x in claims), len(claims))
    for name in ("scientific_reports_figures_and_sources.zip", "scientific_reports_review_draft_sources.zip"):
        path = DRAFT / name
        with zipfile.ZipFile(path) as archive:
            corrupt = archive.testzip()
        check("existing_zip_crc:" + name, corrupt is None, {"sha256": sha(path), "first_corrupt": corrupt})
    prior = load(DRAFT / "qa/release_checks.json")
    check("prior92_checks_available_not_new_science", len(prior["checks"]) == 92
          and all(x["passed"] for x in prior["checks"]),
          "Unchanged candidate is hash-bound; this is not a rerun of the mutating release validator")
    cache = load(HERE / "cached_numbers/tste_number_consistency_audit.json")
    gate = load(HERE / "gate_execution.json")
    check("legacy_checks_complete_bounded_scope", cache["n_checks"] == 77 and cache["n_failed"] == 0
          and gate["claim_gate_exit"] == gate["cached_number_gate_exit"] == 0, gate)
    result = {"status": "PASS_READ_ONLY_REVIEW_SOURCE_CHECKS" if all(c["passed"] for c in checks) else "FAIL",
              "checks": checks, "n_checks": len(checks),
              "new_experiments_calibration_bootstrap_or_measurements": False,
              "scope": "Document/source/field identities and existing bound interpretation; no inferential coverage or journal acceptance certification"}
    (HERE / "REVIEW_SOURCE_CHECKS.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(result["status"], result["n_checks"], "checks")
    failed = [c["check"] for c in checks if not c["passed"]]
    if failed:
        print("FAILED", failed)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
