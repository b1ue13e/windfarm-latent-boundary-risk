"""Project completed result records into supplement attachments without analysis.

No research model, bootstrap, calibration or raw-measurement file is imported.
Original CSV attachments are copied byte for byte. JSON projections retain stored
numbers; percentage formatting is reserved for manuscript display.
"""
from __future__ import annotations

import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
AGGREGATE = ROOT / "analyses/independent_confirmation_execution_20261019/recovered/results/aggregate"
COPIES = {
    "towie_all_90_cases.csv": "analyses/independent_confirmation_execution_20261019/derived/secondary_cases.csv",
    "wtb_all_420_sufficiency_cases.csv": "analyses/claim_revision_recovery_20261019/derived/all_decision_cases.csv",
    "wtb_all_420_minimum_cases.csv": "analyses/claim_revision_recovery_20261019/necessity/necessity.csv",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def stored_group(span: int) -> dict:
    groups = read_json(AGGREGATE / f"secondary_span{span}.json")["results"]
    return next(group for group in groups if group["condition"] == "pitch_withheld")


def stored_case(group: dict) -> dict:
    return next(case for case in group["secondary_retrospective_full_q"] if case["epsilon"] == 0.02)


def registered_rows() -> list[dict]:
    rows = []
    for group in read_json(AGGREGATE / "secondary_span3.json")["results"]:
        for index, (label, resource) in enumerate(zip(group["labels"], group["resources"], strict=True)):
            subset, estimator, quantile = label.split("/")
            rows.append({
                "condition": group["condition"], "stored_index": index,
                "policy_label": label, "subset": subset, "estimator": estimator,
                "offset_quantile": quantile.removeprefix("q"),
                "incremental_channels": resource[0], "learned_predictor_passes": resource[1],
                "raw_input_width": resource[2],
            })
    return rows


def witness_rows() -> list[dict]:
    group = stored_group(3)
    case = stored_case(group)
    rows = []
    for record in case["minimum_audit"]["excluded"]:
        index = record["index"]
        witnesses = record.get("witness_seed_indices", [])
        policy = record.get("witness_policy")
        rows.append({
            "stored_index": index, "smaller_policy": group["labels"][index],
            "reason": record["reason"],
            "witness_policy": "" if policy is None else group["labels"][policy],
            "stored_relative_cost_lower": record.get("ratio_lower", ""),
            "witness_seed_ids": ";".join(str(201 + seed) for seed in witnesses),
            "stored_witness_risk_lower": ";".join(str(group["risk_lower"][seed][index]) for seed in witnesses),
        })
    return rows


def sensitivity_rows() -> list[dict]:
    rows = []
    for span in (1, 3, 7):
        group = stored_group(span)
        case = stored_case(group)
        for index in case["minimum_audit"]["chosen"]:
            rows.append({
                "span_days": span, "policy_label": group["labels"][index],
                "mean_cost": group["mean_cost"][index],
                "max_instance_risk_upper": max(row[index] for row in group["risk_upper"]),
                "minimum_status": case["minimum_audit"]["status"],
                "smaller_count": len(case["minimum_audit"]["smaller"]),
                "excluded_count": len(case["minimum_audit"]["excluded"]),
                "coordinate_family_size": group["coordinate_family_size"],
            })
    return rows


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    output = HERE / "supplement_data"
    output.mkdir(parents=True, exist_ok=True)
    sources = [ROOT / source for source in COPIES.values()]
    sources += [AGGREGATE / f"secondary_span{span}.json" for span in (1, 3, 7)]
    before = {str(path.relative_to(ROOT)).replace("\\", "/"): sha(path) for path in sources}
    for name, source in COPIES.items():
        shutil.copyfile(ROOT / source, output / name)
    projected = {
        "registered_confirmation_policies.csv": registered_rows(),
        "towie_q925_all_15_witnesses.csv": witness_rows(),
        "towie_q925_block_sensitivity.csv": sensitivity_rows(),
    }
    for name, rows in projected.items():
        write_csv(output / name, rows)
    after = {str(path.relative_to(ROOT)).replace("\\", "/"): sha(path) for path in sources}
    if after != before:
        raise RuntimeError("A read-only source changed during projection")
    outputs = {}
    for path in sorted(output.glob("*.csv")):
        with path.open(newline="", encoding="utf-8") as stream:
            count = sum(1 for _ in csv.DictReader(stream))
        outputs[path.name] = {"sha256": sha(path), "rows": count}
    receipt = {
        "status": "STORED_RECORD_PROJECTION_ONLY", "utc": datetime.now(timezone.utc).isoformat(),
        "python": sys.version, "script_sha256": sha(Path(__file__)),
        "source_sha256_before": before, "source_sha256_after": after, "outputs": outputs,
        "new_training": False, "new_prediction": False, "new_calibration": False,
        "new_resampling": False, "new_measurements": False,
        "scope": "CSV copies and literal JSON field projections; max/count operations summarize already stored fields, not new inferential estimates.",
    }
    (output / "projection_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": receipt["status"], "outputs": outputs}, indent=2))


if __name__ == "__main__":
    main()
