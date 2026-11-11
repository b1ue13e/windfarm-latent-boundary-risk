"""Project saved M fields for figures; no estimator, metrics or bootstrap calls."""
from pathlib import Path
import csv
import hashlib
import json

BASE = Path(__file__).resolve().parent
PILOT = BASE / "copies/pilot"
CONTROLS = BASE / "copies/controls"
loaded = {}


def read(path):
    loaded[str(path.relative_to(BASE))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return json.loads(path.read_text(encoding="utf-8"))


def pointer(path, key):
    return str(path.relative_to(BASE)) + "::" + key


def write(name, records):
    fields = list(dict.fromkeys(k for r in records for k in r))
    path = BASE / name
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(records)
    with path.open(encoding="utf-8-sig", newline="") as f:
        back = list(csv.DictReader(f))
    assert len(back) == len(records)
    comparisons = 0
    for original, saved in zip(records, back):
        for k, v in original.items():
            if v is None:
                assert saved[k] == ""
            elif isinstance(v, bool):
                assert saved[k] == str(v)
            elif isinstance(v, (int, float)):
                assert float(saved[k]) == v
            else:
                assert saved[k] == str(v)
            comparisons += 1
    return dict(file=name, rows=len(records), exact_scalar_roundtrip_assertions=comparisons,
                sha256=hashlib.sha256(path.read_bytes()).hexdigest())


pilot_file, controls_file = PILOT / "summary.json", CONTROLS / "summary.json"
p, c = read(pilot_file), read(controls_file)
choice_file, frozen_file = PILOT / "historical_choices.json", CONTROLS / "frozen.json"
choices, frozen = read(choice_file), read(frozen_file)
assert p["primary_family_size"] == 154 and c["family_size"] == 596
assert p["n_cells"] == c["cells"] == 671538
assert p["Cstar"] == c["Cstar"] == frozen["Cstar"]

names = ["fresh_state", "old_state", "old_power", "P_premium_vs_Z", "residual_state"]
pair = dict(fresh_state=("F", "FZ"), old_state=("O6", "OZ6"),
            old_power=("O6", "OP6"), P_premium_vs_Z=("OP6", "OZ6"),
            residual_state=("OP6", "OPZ6"))
costs = []
for name in names:
    a, b = pair[name]
    kind = "D" if name == "P_premium_vs_Z" else "G"
    for estimator in ("HGB", "MLP"):
        for recipe, family, obj, path, field in [
                ("Original", 154, p, pilot_file, "registered_intervals"),
                ("Original", 596, c, controls_file, "interval"),
                ("Common", 596, c, controls_file, "interval")]:
            key = (estimator if family == 154 else recipe + ":" + estimator) + ":" + name + "|cost|" + kind
            interval = obj[field][key]
            row = dict(recipe=recipe, estimator=estimator, comparison=name, A=a, B=b,
                       kind=kind, family=family, block_days=3, unit="fraction",
                       formula="(C_A-C_B)/C_A" if kind == "G" else "(C_A-C_B)/C_B",
                       source=pointer(path, field + "." + key))
            row.update(interval)
            assert all(row[k] == obj[field][key][k] for k in ("point", "lower", "upper"))
            costs.append(row)
assert len(costs) == 30

programs = []
raw_metrics = PILOT / "instance_metrics.csv"
loaded[str(raw_metrics.relative_to(BASE))] = hashlib.sha256(raw_metrics.read_bytes()).hexdigest()
with raw_metrics.open(encoding="utf-8-sig", newline="") as f:
    for line, row in enumerate(csv.DictReader(f), 2):
        if row["estimator"] not in ("HGB", "MLP"):
            continue
        label = row["estimator"] + ":" + row["cell"]
        r = dict(recipe="Original", family=154, estimator=row["estimator"], cell=row["cell"],
                 aggregation="fixed instance", seed=row["seed"], q=row["q"],
                 C=row["primary_C"], R=row["primary_R"], U=row["primary_U"], V=row["primary_V"],
                 n_cells=row["primary_cells"],
                 historical_choice_status=choices["choices"][label]["status"],
                 development_group_risk_qualified=p["risk_qualified"][label],
                 metrics_source=str(raw_metrics.relative_to(BASE)) + ":line=" + str(line),
                 q_source=str(raw_metrics.relative_to(BASE)) + ":line=" + str(line) + ":q",
                 qualification_source=pointer(pilot_file, "risk_qualified." + label),
                 unit_C="kWh-equivalent/valid turbine interval", unit_RU="kWh/valid turbine interval", unit_V="fraction")
        programs.append(r)
for i, label in enumerate(c["labels"]):
    recipe, estimator, cell = label.split(":")
    if cell.startswith("Match_"):
        continue
    choice_key = estimator + ":" + cell
    q = c["common_q"] if recipe == "Common" else frozen["original_choices"][choice_key]["q"]
    r = dict(recipe=recipe, family=596, estimator=estimator, cell=cell,
             aggregation="stored five-instance mean", seed="fixed 201..205", q=q,
             n_cells=c["cells"], historical_all_instances_qualified=frozen["historical_qualification"][label]["all_instances_qualified"],
             development_group_risk_qualified=c["development_risk_qualified"][label],
             jointly_qualified=c["jointly_qualified"][label],
             q_source=pointer(controls_file, "common_q") if recipe == "Common" else pointer(frozen_file, "original_choices." + choice_key + ".q"),
             qualification_source=pointer(controls_file, "jointly_qualified." + label),
             unit_C="kWh-equivalent/valid turbine interval", unit_RU="kWh/valid turbine interval", unit_V="fraction")
    for metric in ("C", "R", "U", "V"):
        r[metric] = c["mean_metrics"][metric][i]
        r[metric + "_source"] = pointer(controls_file, f"mean_metrics.{metric}[{i}]")
        assert r[metric] == c["mean_metrics"][metric][i]
    programs.append(r)
assert len(programs) == 84

decomposition = []
for key, interval in c["interval"].items():
    if not (key.endswith("|mean_R") or key.endswith("|mean_U")):
        continue
    recipe, estimator, comparison = key.split("|")[0].split(":")
    metric = key.split("|")[1]
    r = dict(recipe=recipe, estimator=estimator, comparison=comparison, metric=metric,
             family=596, block_days=3, Cstar=c["Cstar"],
             formula="10*(U_B-U_A)/Cstar" if metric == "mean_U" else "(R_B-R_A)/Cstar",
             unit="dimensionless signed normalized difference; not relative-percent change",
             source=pointer(controls_file, "interval." + key), **interval)
    assert all(r[k] == c["interval"][key][k] for k in ("point", "lower", "upper"))
    decomposition.append(r)
assert len(decomposition) == 104

routes = []
for key, outcome in c["corrected_routes"].items():
    recipe, estimator = key.split(":")
    routes.append(dict(recipe=recipe, estimator=estimator, family=596, **outcome,
                       source=pointer(controls_file, "corrected_routes." + key),
                       interpretation="All conjunctions false; individual effects remain reportable"))
assert len(routes) == 4
validation = dict(status="PASS_EXACT_PROJECTION_OF_SAVED_FIELDS", source_sha256=loaded,
                  outputs=[write("display_M_cost.csv", costs), write("display_M_programs.csv", programs),
                           write("display_M_decomposition.csv", decomposition), write("display_M_routes.csv", routes)],
                  note="30 cost rows preserve original154 and Original/Common596 as separate families; JSON null is an empty CSV cell, not zero; no new statistics or percentages calculated",
                  models_loaded=0, inference=0, calibration=0, bootstrap=0, experiments=0)
(BASE / "DISPLAY_M_VALIDATION.json").write_text(json.dumps(validation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"status": validation["status"], "rows": {x["file"]: x["rows"] for x in validation["outputs"]}}))
