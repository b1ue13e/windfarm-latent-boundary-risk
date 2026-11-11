"""Project archived R fields into display CSVs without statistical calculation.

Run this file with Python's standard library only. Inputs are the bundled,
byte-identical original JSONs. No research module is imported and no model,
bootstrap, evaluation, aggregation, or unit conversion is executed.
"""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


BASE = Path(__file__).resolve().parent
SOURCE_PREFIX = "analyses/decision_information_execution_20261018/"
COST_REL = "evidence/results/aggregate/paired_intervals.json"
EXPECTED_COST_SHA = "1de4be76bf901008eb006a5baca2f253325efd7499287287296369b1cc56822c"
DIAGNOSTIC_SHAS = {
    201: "94bbbd95b9fa48f9d7431c61aff5e7cdc72caecfd826d07ea6bd04c47be1f7d0",
    202: "b67bbe21561e4d8b45ab60d4d00d618a3867fb8a86d4443b983edaf5307fb151",
    203: "ccd24f55e3f53874330236b3647479bdf4620bf81a3ed1ac0c6da8ffe9a0caa4",
    204: "630c3cb389abefb684851a424729c40fe3b3fa869a2b2cc059206fe19f5617e8",
    205: "6ad217655cd4efd1c8557368fc4fb9b09ae64caec045aa6f5dee39176948810b",
}
PAIRS = {
    ("B_Consequences", "A_Wind"): "B-A",
    ("C_PitchScore", "B_Consequences"): "C-B",
    ("C_PitchScore", "C_WindScore"): "C-WindScore",
    ("C_PitchScore", "C_ShuffledScore"): "C-ShuffledScore",
    ("D_TruePitch_Diagnostic", "B_Consequences"): "D-B",
    ("E_Compressed", "B_Consequences"): "E-B",
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_original(relative: str, expected_sha: str) -> object:
    data = (BASE / "original" / relative).read_bytes()
    if sha(data) != expected_sha:
        raise AssertionError(f"Original input hash mismatch: {relative}")
    return json.loads(data.decode("utf-8-sig"))


def write_csv(path: Path, records: list[dict]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)


def main() -> None:
    intervals = load_original(COST_REL, EXPECTED_COST_SHA)
    if not isinstance(intervals, list) or len(intervals) != 504:
        raise AssertionError("Original R interval list changed")
    cost_rows = []
    for index, item in enumerate(intervals):
        pair = (item["left"], item["right"])
        if item["metric"] != "loss_sum" or pair not in PAIRS:
            continue
        if item["block_span"] not in (1, 3, 7):
            raise AssertionError("Unexpected original span")
        cost_rows.append({
            "study": "R",
            "comparison": PAIRS[pair],
            "condition": item["condition"],
            "metric": item["metric"],
            "left": item["left"],
            "right": item["right"],
            "block_span": item["block_span"],
            "point": item["point"],
            "ci95_lower": item["ci95"][0],
            "ci95_upper": item["ci95"][1],
            "simultaneous_ci_lower": item["simultaneous_ci"][0],
            "simultaneous_ci_upper": item["simultaneous_ci"][1],
            "n_boot": item["n_boot"],
            "resampling_seed": item["resampling_seed"],
            "family_size": item["family_size"],
            "unit": item["unit"],
            "inference_role": item["inference_role"],
            "coverage_status": item["coverage_status"],
            "seed_inference": item["seed_inference"],
            "bootstrap_indices_sha256": item["bootstrap_indices_sha256"],
            "record_index": index,
            "source_field": f"[{index}]",
            "source_file": SOURCE_PREFIX + COST_REL,
            "offline_source_file": "original/" + COST_REL,
            "source_file_sha256": EXPECTED_COST_SHA,
        })
    if len(cost_rows) != 108:
        raise AssertionError("Expected six conditions by six contrasts by three spans")
    for condition in {row["condition"] for row in cost_rows}:
        keys = [(row["comparison"], row["block_span"]) for row in cost_rows
                if row["condition"] == condition]
        if len(keys) != 18 or len(set(keys)) != 18:
            raise AssertionError("Missing or duplicate contrast/span")
    cost_path = BASE / "display_R_cost.csv"
    write_csv(cost_path, cost_rows)

    # Each MSE value is copied directly from one original diagnostic record.
    # No five-fit average, spread, interval, or percentage is calculated.
    mse_rows = []
    diagnostic_inputs = {}
    for seed, expected_sha in DIAGNOSTIC_SHAS.items():
        relative = f"evidence/results/runs/seed{seed}/pitch_withheld/models_and_diagnostics.json"
        diagnostic = load_original(relative, expected_sha)
        diagnostic_inputs[seed] = diagnostic
        for probe in ("pitch", "wind", "shuffle"):
            mse_rows.append({
                "study": "R",
                "condition": "pitch_withheld",
                "fit_seed": seed,
                "probe": probe,
                "metric": "continuous_pitch_mse_degrees_squared",
                "value": diagnostic["continuous_pitch_mse_degrees_squared"][probe],
                "unit": "degree^2",
                "state_diagnostic_cells": diagnostic["state_diagnostic_cells"],
                "population_rule": "finite current continuous pitch; not the future-P decision mask definition",
                "probe_input_scope": diagnostic["probe_input_scope"],
                "inference_role": "descriptive original per-fit diagnostic; no stored uncertainty interval",
                "source_file": SOURCE_PREFIX + relative,
                "source_field": "continuous_pitch_mse_degrees_squared." + probe,
                "offline_source_file": "original/" + relative,
                "source_file_sha256": expected_sha,
            })
    mse_path = BASE / "display_R_mse_per_fit.csv"
    write_csv(mse_path, mse_rows)

    # Independently re-read the delivered CSV strings and compare their values
    # to the original source fields; this checks projection, not inference.
    cost_checks = 0
    with cost_path.open(encoding="utf-8-sig", newline="") as handle:
        delivered_cost = list(csv.DictReader(handle))
    for row in delivered_cost:
        original = intervals[int(row["record_index"])]
        for column, value in (
            ("point", original["point"]),
            ("ci95_lower", original["ci95"][0]),
            ("ci95_upper", original["ci95"][1]),
            ("simultaneous_ci_lower", original["simultaneous_ci"][0]),
            ("simultaneous_ci_upper", original["simultaneous_ci"][1]),
        ):
            if float(row[column]) != value:
                raise AssertionError(f"Numeric projection changed: {row['source_field']} {column}")
            cost_checks += 1
        for column in (
            "condition", "metric", "left", "right", "unit", "inference_role",
            "coverage_status", "seed_inference", "bootstrap_indices_sha256",
        ):
            if row[column] != original[column]:
                raise AssertionError(f"Text projection changed: {row['source_field']} {column}")
            cost_checks += 1
        for column in ("block_span", "n_boot", "resampling_seed", "family_size"):
            if int(row[column]) != original[column]:
                raise AssertionError(f"Integer projection changed: {row['source_field']} {column}")
            cost_checks += 1

    mse_checks = 0
    with mse_path.open(encoding="utf-8-sig", newline="") as handle:
        delivered_mse = list(csv.DictReader(handle))
    for row in delivered_mse:
        original = diagnostic_inputs[int(row["fit_seed"])]
        if float(row["value"]) != original["continuous_pitch_mse_degrees_squared"][row["probe"]]:
            raise AssertionError("MSE projection changed")
        if int(row["state_diagnostic_cells"]) != original["state_diagnostic_cells"]:
            raise AssertionError("MSE population count changed")
        if row["probe_input_scope"] != original["probe_input_scope"]:
            raise AssertionError("MSE input-scope string changed")
        mse_checks += 3
    if len(delivered_cost) != 108 or len(delivered_mse) != 15:
        raise AssertionError("Delivered projection row counts changed")

    assertions = {
        "status": "PASS_EXACT_STORED_FIELD_PROJECTION",
        "script_sha256": sha(Path(__file__).read_bytes()),
        "input_identity": {
            SOURCE_PREFIX + COST_REL: EXPECTED_COST_SHA,
            **{SOURCE_PREFIX + f"evidence/results/runs/seed{s}/pitch_withheld/models_and_diagnostics.json": h
               for s, h in DIAGNOSTIC_SHAS.items()},
        },
        "cost_projection": {
            "rows": len(delivered_cost),
            "comparisons": list(PAIRS.values()),
            "conditions": sorted({row["condition"] for row in delivered_cost}),
            "spans": [1, 3, 7],
            "original_field_equality_assertions": cost_checks,
            "csv_sha256": sha(cost_path.read_bytes()),
        },
        "mse_projection": {
            "rows": len(delivered_mse),
            "fit_seeds": list(DIAGNOSTIC_SHAS),
            "probes": ["pitch", "wind", "shuffle"],
            "original_field_equality_assertions": mse_checks,
            "csv_sha256": sha(mse_path.read_bytes()),
        },
        "limits": {
            "no_new_statistics_or_intervals": True,
            "no_mse_average_or_aggregation": True,
            "no_unit_conversion": True,
            "no_research_module_imported": True,
            "no_model_or_array_evaluation": True,
            "no_bootstrap_or_index_regeneration": True,
            "assertions_are_field_checks_not_independent_observations": True,
        },
    }
    (BASE / "DISPLAY_R_ASSERTIONS.json").write_text(
        json.dumps(assertions, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"PASS: {len(delivered_cost)} stored cost rows; {len(delivered_mse)} per-fit MSE rows; exact source fields")


if __name__ == "__main__":
    main()
