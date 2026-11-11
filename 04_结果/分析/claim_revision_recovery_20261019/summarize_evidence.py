"""Derive claim tables from the frozen archive; never refit or resample."""
from pathlib import Path
from datetime import datetime, timezone
import collections
import csv
import hashlib
import json
import platform
import sys

ROOT = Path(__file__).resolve().parent


def sha(p):
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_csv(path, rows):
    with path.open("x", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)


def main():
    out = ROOT / "derived"
    out.mkdir(exist_ok=False)
    inputs = [ROOT / "evidence/study/results/aggregate/results.json", ROOT / "necessity/necessity.csv",
              ROOT / "evidence/post/report/historical_learning_curves.csv", ROOT / "source_metadata/history_adapter/receipt.json"]
    before = {str(p.relative_to(ROOT)): sha(p) for p in inputs}
    result = json.loads(inputs[0].read_text(encoding="utf-8"))
    necessity = list(csv.DictReader(inputs[1].open(encoding="utf-8")))
    curves = list(csv.DictReader(inputs[2].open(encoding="utf-8")))
    summary = dict(necessity_counts=dict(collections.Counter(r["status"] for r in necessity)),
                   original_fit_settings_unchanged=True, new_models_trained=False, new_bootstrap=False)
    rows = []
    for group in result["results"]:
        for analysis in ("primary_historical_recipe", "secondary_retrospective_grid"):
            labels = ([x["label"] for x in group["historical_choices"]] if analysis.startswith("primary") else group["labels"])
            for selection in group[analysis]:
                rows.append(dict(span=group["span"], condition=group["condition"], budget=group["budget"],
                     analysis=analysis, epsilon=selection["epsilon"], status=selection["status"],
                     risk_qualified_count=len(selection["risk_qualified_indices"]),
                     sufficient_resource_set=";".join(labels[i] for i in selection["minimum_resource_indices"])))
    write_csv(out / "all_decision_cases.csv", rows)
    summary["primary_span_epsilon02"] = dict(cases=sum(r["span"] == 3 and r["epsilon"] == .02 for r in rows),
          identified=sum(r["span"] == 3 and r["epsilon"] == .02 and r["status"] == "IDENTIFIED_DEVELOPMENT_SET" for r in rows),
          all_cases_have_risk_qualified=all(r["risk_qualified_count"] > 0 for r in rows if r["span"] == 3 and r["epsilon"] == .02))
    selected = [r for r in curves if r["span_days"] == "3" and r["condition"] == "pitch_withheld"]
    write_csv(out / "withheld_selected_curves.csv", selected)
    table = []
    for budget in (10000, 40000, 120000, 360000):
        row = next(r for r in selected if r["subset"] == "PQ1" and r["estimator"] == "HGB" and int(r["group_budget"]) == budget)
        case = next(r for r in necessity if r["span"] == "3" and r["analysis"] == "primary_historical_recipe"
                    and r["epsilon"] == "0.05" and r["condition"] == "pitch_withheld" and int(r["budget"]) == budget)
        table.append(dict(budget=budget, policy=row["policy"], mean_cost=float(row["mean_cost_kwh"]),
             maximum_instance_risk_upper=float(row["joint_max_instance_risk_upper"]),
             smaller=int(case["smaller_count"]), excluded=int(case["excluded_count"]),
             unresolved=int(case["smaller_count"]) - int(case["excluded_count"]), minimum_status=case["status"]))
    write_csv(out / "pq1_candidate_table.csv", table)
    worse, better, nonmonotone = 0, 0, {}
    for subset in sorted({r["subset"] for r in selected if r["estimator"] != "Persistence"}):
        for estimator in ("HGB", "MLP"):
            values = sorted((r for r in selected if r["subset"] == subset and r["estimator"] == estimator), key=lambda r: int(r["fit_rows"]))
            costs = [float(r["mean_cost_kwh"]) for r in values]
            if not (all(a <= b for a, b in zip(costs, costs[1:])) or all(a >= b for a, b in zip(costs, costs[1:]))):
                nonmonotone[estimator] = nonmonotone.get(estimator, 0) + 1
        for budget in (10000, 40000, 120000, 360000):
            hgb = next(float(r["mean_cost_kwh"]) for r in selected if r["subset"] == subset and r["estimator"] == "HGB" and int(r["fit_rows"]) == budget)
            mlp = next(float(r["mean_cost_kwh"]) for r in selected if r["subset"] == subset and r["estimator"] == "MLP" and int(r["fit_rows"]) == budget)
            worse += mlp > hgb; better += mlp < hgb
    summary["descriptive_estimator_comparison"] = dict(mlp_point_cost_higher=worse, lower=better,
         nonmonotone_curves=nonmonotone, scope="Selected q, fixed recipes, previously viewed development window; no universal estimator or saturation claim")
    summary["source_qualification"] = {k: json.loads(inputs[3].read_text(encoding="utf-8"))[k]
          for k in ("status", "shape", "phase_finite_target_counts", "test_archive_2025_opened", "consumed_value_conflicts", "negative_power_preserved")}
    for path in inputs:
        if sha(path) != before[str(path.relative_to(ROOT))]:
            raise ValueError("Protected evidence changed")
    (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (out / "receipt.json").write_text(json.dumps(dict(input_sha256=before, source_sha256=sha(Path(__file__)),
         utc=datetime.now(timezone.utc).isoformat(), python=sys.version, host=platform.node(), argv=sys.argv,
         scope="Read-only derived evidence reporting; no raw output, policy or threshold changes"), indent=2), encoding="utf-8")
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
