"""Bounded WTB state-measurement pilot on an allocated PBS node."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from repo_paths import Path, repository_root
import platform
import shutil
import sys
import time

import joblib
import numpy as np
import sklearn
from threadpoolctl import threadpool_limits

ROOT = Path(repository_root())
sys.path.insert(0, str(ROOT))
from scripts.run_information_subset_study import sha, save, identity
from scripts.run_decision_information_development import load_raw_csv, learner
from windfarm_moe.information_subset import PinballMLP, nested_samples
from windfarm_moe.risk_frontier import offset_grid, shared_block_draws, simultaneous_envelope
from windfarm_moe.state_measurement import (CELLS, information_matrix, populations, account,
                                          choose_offset, joint_coordinates)

SOURCES = ("scripts/run_state_measurement_pilot.py", "windfarm_moe/state_measurement.py",
           "scripts/run_information_subset_study.py", "scripts/run_decision_information_development.py",
           "windfarm_moe/information_subset.py", "windfarm_moe/decision_information.py",
           "windfarm_moe/risk_frontier.py", "windfarm_moe/subset_inference.py")


def begin(args, inputs):
    import torch
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "source").mkdir()
    sources = [ROOT / p for p in SOURCES] + [args.protocol.resolve()]
    for p in sources:
        shutil.copyfile(p, args.output / "source" / p.name)
    receipt = dict(status="RUNNING", argv=sys.argv, started_utc=datetime.now(timezone.utc).isoformat(),
        stage=args.stage, task=args.task, seed=None, host=platform.node(), platform=platform.platform(),
        python=sys.version, numpy=np.__version__, sklearn=sklearn.__version__, torch=torch.__version__,
        cpu=platform.processor(), cpu_model=Path("/proc/cpuinfo").read_text().split("model name")[-1].splitlines()[0] if Path("/proc/cpuinfo").exists() else platform.processor(),
        backend="CPU two threads; no GPU allocation", pbs_job_id=os.environ.get("PBS_JOBID"),
        environment={k: os.environ.get(k) for k in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS")},
        protocol_sha256=sha(args.protocol), source_sha256={str(p.relative_to(ROOT)): sha(p) for p in sources},
        input_sha256={str(p.resolve()): sha(p) for p in inputs},
        git_commit=json.loads((ROOT / "deployment_manifest.json").read_text())["git_commit"] if (ROOT / "deployment_manifest.json").exists() else "local-test",
        scope="Already-viewed WTB development; synthetic availability; not field safety, causal or independent confirmation")
    save(args.output / "receipt.json", receipt)
    return receipt


def finish(args, receipt):
    for p, expected in receipt["input_sha256"].items():
        if sha(p) != expected:
            raise ValueError("Protected input changed: " + p)
    receipt.update(status="COMPLETED_DEVELOPMENT", finished_utc=datetime.now(timezone.utc).isoformat())
    save(args.output / "receipt.json", receipt)
    save(args.output / "manifest.json", {str(p.relative_to(args.output)): dict(bytes=p.stat().st_size, sha256=sha(p))
         for p in sorted(args.output.rglob("*")) if p.is_file() and p.name != "manifest.json"})
    print("COMPLETED", args.stage, args.task, flush=True)


def verify(path, cfgpath, stage):
    manifest = json.loads((path / "manifest.json").read_text())
    for name, rec in manifest.items():
        p = (path / name).resolve()
        if not p.is_relative_to(path.resolve()) or p.stat().st_size != rec["bytes"] or sha(p) != rec["sha256"]:
            raise ValueError("Archive mismatch: " + str(p))
    r = json.loads((path / "receipt.json").read_text())
    if r["status"] != "COMPLETED_DEVELOPMENT" or r["stage"] != stage or r["protocol_sha256"] != sha(cfgpath):
        raise ValueError("Wrong receipt identity")
    for name, value in r["source_sha256"].items():
        if sha(ROOT / name) != value:
            raise ValueError("Producer source differs: " + name)
    return r


def tasks(cfg):
    return [dict(estimator=e, cell=c, seed=s) for e in ("HGB", "MLP") for c in CELLS for s in cfg["seeds"]] + [
        dict(estimator="CONTROL", cell=c, seed=s) for c in ("Global", "Persistence") for s in cfg["seeds"]]


def stage(path, name):
    with np.load(path / f"{name}.npz") as z:
        return {k: z[k] for k in z.files}


def prepare(args, cfg):
    parent = Path(cfg["prepared_parent"])
    raw = Path(cfg["raw_csv"])
    rec = begin(args, [raw, parent / "output_manifest.json", parent / "execution_receipt.json"])
    if sha(raw) != cfg["raw_sha256"]:
        raise ValueError("Raw identity failed")
    old = json.loads((parent / "output_manifest.json").read_text())
    for name, item in old.items():
        p = (parent / name).resolve()
        if not p.is_relative_to(parent.resolve()) or sha(p) != item["sha256"] or p.stat().st_size != item["bytes"]:
            raise ValueError("Upstream archive changed: " + name)
    producer = json.loads((parent / "execution_receipt.json").read_text())
    if producer["protocol_sha256"] != cfg["parent_protocol_sha256"] or producer["status"] != "COMPLETED_DEVELOPMENT_NOT_CERTIFIED":
        raise ValueError("Upstream producer mismatch")
    for name, value in producer["source_sha256"].items():
        if sha(parent / "source" / Path(name).name) != value:
            raise ValueError("Unbound upstream source")
    data, nodes, metadata = load_raw_csv(raw)
    archived = np.load(parent / "physical_channels.npy", mmap_mode="r")
    if data.shape != (35280, 134, 4) or not np.array_equal(data, archived, equal_nan=True):
        raise ValueError("Raw-derived physical channels disagree")
    np.save(args.output / "physical_channels.npy", data)
    np.save(args.output / "node_ids.npy", nodes)
    oldstage = {name: stage_archive(parent / f"{name}_forecast.npz") for name in
                ("policy_fit", "calibration", "development_evaluation")}
    definitions = {"fit": ("policy_fit", 19440, 25193), "offset": ("calibration", 25200, 27641),
                   "selection": ("calibration", 27648, 30233), "evaluation": ("development_evaluation", 30240, 35273)}
    reports = {}
    upstream_metadata = json.loads((parent / "data_manifest.json").read_text())
    upstream_protocol = json.loads((parent / "source" / "protocol.json").read_text())
    task = upstream_protocol["task"]
    if (task["horizon_steps"], task["commitment_age_steps"], task["history_steps"],
            task["target_release_delay_steps"]) != (6, 6, 36, 1):
        raise ValueError("Upstream task differs")
    if upstream_metadata["stages"]["point_fit"] != [35, 12947]:
        raise ValueError("Unexpected point-fitting calendar")
    point_end = upstream_metadata["stages"]["point_fit"][1] - 1 + 12 + 1
    prior_end = point_end
    for name, (source, lo, hi) in definitions.items():
        oldz = oldstage[source]
        use = (oldz["anchors"] >= lo) & (oldz["anchors"] < hi)
        z = {k: v[use] for k, v in oldz.items()}
        a, f = z["anchors"], z["forecast"]
        if not np.array_equal(a, np.arange(lo, hi)) or not np.array_equal(z["target_indices"], a + 6) or not np.array_equal(z["publication_indices"], a - 6):
            raise ValueError("Forecast clock identity failed")
        if prior_end >= a[0] or point_end >= np.min(a - 6):
            raise ValueError("Target maturity or publication leakage")
        prior_end = a[-1] + 6 + 1
        y = data[a + 6, :, 1].astype(np.float64)
        shortfall = np.maximum(f.astype(np.float64) - y, 0)
        target, primary = populations(data, a)
        np.savez_compressed(args.output / f"{name}.npz", **z, shortfall=shortfall,
                            target_mask=target, primary_mask=primary)
        p, pitch = np.isfinite(data[a, :, 1]), np.isfinite(data[a, :, 3])
        cross = {f"target{int(t)}_P{int(pp)}_Z{int(zz)}": int(((target == t) & (p == pp) & (pitch == zz)).sum())
                 for t in (False, True) for pp in (False, True) for zz in (False, True)}
        reports[name] = dict(first_anchor=int(a[0]), last_anchor=int(a[-1]),
            latest_label_release=int(prior_end), earliest_publication=int(a[0] - 6),
            target_cells=int(target.sum()), primary_cells=int(primary.sum()),
            input_missing_counts={c: int((~np.isfinite(data[a, :, j])).sum()) for j, c in enumerate(("W", "P", "Q", "Z"))},
            cross_table=cross, shared_identity=identity(z | {"shortfall": shortfall, "target_mask": target, "primary_mask": primary}),
            weather_days=int(len(np.unique(a // 144))))
    metadata.update(stages=reports, upstream_manifest_sha256=sha(parent / "output_manifest.json"),
                    status="S0_S1_PASSED_FOR_DEVELOPMENT_NOT_FIELD_ARRIVAL_LOGS", model_fits=0)
    save(args.output / "qualification.json", metadata)
    save(args.output / "upstream_receipt.json", producer)
    finish(args, rec)


def stage_archive(path):
    with np.load(path) as z:
        return {k: z[k] for k in ("anchors", "forecast", "publication_indices", "target_indices")}


def feature(data, z, cell):
    return information_matrix(data, z["anchors"], z["forecast"], cell)


def control(data, z, cell, global_q):
    if cell == "Global":
        return np.full(z["forecast"].shape, global_q)
    p = data[z["anchors"], :, 1]
    return np.where(np.isfinite(p), np.maximum(z["forecast"] - p, 0), 0)


def fit(args, cfg):
    prepared = args.base / "prepared"
    verify(prepared, args.protocol, "prepare")
    t = tasks(cfg)[args.task]
    rec = begin(args, [prepared / "manifest.json"])
    rec.update(**t)
    data = np.load(prepared / "physical_channels.npy", mmap_mode="r")
    train = stage(prepared, "fit")
    n = min(cfg["max_fit_rows"], int(train["target_mask"].sum()))
    indices = nested_samples(train["target_mask"], [n], t["seed"])[n]
    np.save(args.output / "fit_indices.npy", indices)
    y = train["shortfall"].ravel()[indices]
    start = time.monotonic()
    if t["estimator"] == "CONTROL":
        global_q = float(np.quantile(y, .9, method="higher"))
        model = None
    else:
        x = feature(data, train, t["cell"])[indices]
        model = learner(cfg["hgb"], t["seed"], True) if t["estimator"] == "HGB" else PinballMLP(t["seed"], cfg["mlp"])
        model.fit(x, y)
        joblib.dump(model, args.output / "model.joblib")
        if t["estimator"] == "MLP":
            save(args.output / "training_trace.json", model.training_trace_)
        global_q = None
        del x
    rec.update(fit_rows=n, fit_indices=identity({"indices": indices}), fit_seconds=time.monotonic() - start,
               global_raw_quantile=global_q)
    print("FITTED", t, rec["fit_seconds"], flush=True)
    blocks = {}
    for name in ("offset", "selection"):
        z = stage(prepared, name)
        raw = control(data, z, t["cell"], global_q) if model is None else np.maximum(model.predict(feature(data, z, t["cell"])), 0).reshape(z["shortfall"].shape)
        np.savez_compressed(args.output / f"{name}_raw.npz", raw=raw)
        if name == "offset":
            offsets = offset_grid(z["shortfall"], raw, z["target_mask"], cfg["offset_quantiles"])
            save(args.output / "offsets.json", offsets)
        else:
            for q, delta in enumerate(offsets):
                r = np.maximum(raw + delta, 0)
                b = account(z["shortfall"], r, z["primary_mask"], z["anchors"])
                blocks.update({f"q{q}__{k}": v for k, v in b.items()})
    np.savez_compressed(args.output / "selection_blocks.npz", **blocks)
    finish(args, rec)


def collect(args, cfg, phase):
    groups = [(e, c) for e in ("HGB", "MLP") for c in CELLS] + [("CONTROL", c) for c in ("Global", "Persistence")]
    result, common_n, common_days = [], None, None
    for e, c in groups:
        records = []
        for seed in cfg["seeds"]:
            task = tasks(cfg).index(dict(estimator=e, cell=c, seed=seed))
            p = args.base / "fits" / str(task) if phase == "historical" else args.base / "evaluation" / str(task)
            if phase != "historical" and not (p / "manifest.json").exists():
                records.append(None)
                continue
            verify(p, args.protocol, "fit" if phase == "historical" else "evaluate")
            with np.load(p / ("selection_blocks.npz" if phase == "historical" else "blocks.npz")) as z:
                qlist = range(5) if phase == "historical" else [0]
                rs = []
                for q in qlist:
                    prefix = f"q{q}__" if phase == "historical" else "primary__"
                    n, days = z[prefix + "N"], z[prefix + "days"]
                    if common_n is None:
                        common_n, common_days = n, days
                    elif not np.array_equal(n, common_n) or not np.array_equal(days, common_days):
                        raise ValueError("Scoring population is unpaired")
                    rs.append({k: z[prefix + k] for k in ("C", "V", "U", "R")})
                records.append(rs)
        result.append(dict(estimator=e, cell=c, records=records))
    return result, common_n, common_days


def select(args, cfg):
    collected, n, days = collect(args, cfg, "historical")
    rec = begin(args, [args.base / "fits" / str(i) / "manifest.json" for i in range(len(tasks(cfg)))])
    c = np.stack([np.stack([g["records"][s][q]["C"] for g in collected for q in range(5)]) for s in range(5)])
    v = np.stack([np.stack([g["records"][s][q]["V"] for g in collected for q in range(5)]) for s in range(5)])
    # Joint historical risk plus all possible no-Z F/simple-control q comparisons.
    w, dh = shared_block_draws(len(n), cfg["n_boot"], 3, cfg["bootstrap_seed"])
    dn = w @ n
    if np.any(dn <= 0):
        raise ValueError("Empty historical weather draw")
    vp = v.sum(axis=-1).ravel() / n.sum()
    vd = w @ v.reshape(-1, len(n)).T / dn[:, None]
    cp = c.mean(axis=0).sum(axis=-1) / n.sum()
    cd = w @ c.mean(axis=0).T / dn[:, None]
    if np.any(cp <= 0) or np.any(cd <= 0):
        raise ValueError("Nonpositive historical cost")
    pairs = [(base * 5 + q, simple * 5 + j) for base in (0, 6) for q in range(5)
             for simple in (12, 13) for j in range(5)]
    point = np.r_[vp, [(cp[a] - cp[b]) / cp[b] for a, b in pairs]]
    draws = np.column_stack([vd] + [((cd[:, a] - cd[:, b]) / cd[:, b])[:, None] for a, b in pairs])
    bounds = simultaneous_envelope(point, draws, .05)
    risk_hi = bounds["upper"][:vp.size].reshape(5, len(collected), 5)
    choice = {}
    for k, g in enumerate(collected):
        q = choose_offset(c[:, k * 5:k * 5 + 5].sum(axis=-1) / n.sum(), risk_hi[:, k], cfg["offset_quantiles"])
        choice[f'{g["estimator"]}:{g["cell"]}'] = dict(q_index=q, q=None if q is None else cfg["offset_quantiles"][q],
            status="NO_HISTORICAL_CHOICE" if q is None else "HISTORICALLY_QUALIFIED",
            per_instance_risk_upper=None if q is None else risk_hi[:, k, q],
            mean_cost=None if q is None else cp[k * 5 + q])
    adequacy = {}
    for e, base in (("HGB", 0), ("MLP", 6)):
        reference = choice[f"{e}:F"]
        value = dict(status="NOT_CLEARLY_INFERIOR_WITHIN_REGISTERED_CHECK", contrasts=[])
        if reference["q_index"] is None:
            value["status"] = "NO_HISTORICAL_CHOICE"
        else:
            a = base * 5 + reference["q_index"]
            for simple, k in (("Global", 12), ("Persistence", 13)):
                q = choice[f"CONTROL:{simple}"]["q_index"]
                if q is None:
                    continue
                b = k * 5 + q
                j = vp.size + pairs.index((a, b))
                value["contrasts"].append(dict(control=simple, premium=point[j], lower=bounds["lower"][j], upper=bounds["upper"][j]))
                if bounds["lower"][j] > .01:
                    value["status"] = "BASELINE_ADEQUACY_UNRESOLVED_STOP_PRIMARY_RECIPE"
        adequacy[e] = value
    cstar = choice["HGB:F"]["mean_cost"]
    save(args.output / "historical_choices.json", dict(choices=choice, baseline_adequacy=adequacy, Cstar=cstar,
        Cstar_source="Historical HGB F five-instance mean cost at chosen q; common across estimators and directions",
        family_size=len(point), risk_coordinates=vp.size, cost_coordinates=len(pairs), alpha=.05,
        critical=bounds["critical"], draw_sha256=dh, n_boot=cfg["n_boot"], block_span=3,
        scope="Approximate historical qualification; choices frozen before any new evaluation inference"))
    save(args.output / "all_historical_bounds.json", dict(point=point, lower=bounds["lower"], upper=bounds["upper"],
                                                        risk_layout="seed,group,q", cost_pairs=pairs, days=days))
    # All cells share the exact same training sample for a given instance.
    for s, seed in enumerate(cfg["seeds"]):
        hashes = {sha(args.base / "fits" / str(i) / "fit_indices.npy") for i, t in enumerate(tasks(cfg)) if t["seed"] == seed}
        if len(hashes) != 1:
            raise ValueError("Training rows differ across paired cells/estimators")
    finish(args, rec)


def evaluate(args, cfg):
    frozen = args.base / "selection"
    verify(frozen, args.protocol, "select")
    t = tasks(cfg)[args.task]
    fitroot = args.base / "fits" / str(args.task)
    producer = verify(fitroot, args.protocol, "fit")
    choice = json.loads((frozen / "historical_choices.json").read_text())
    selected = choice["choices"][f'{t["estimator"]}:{t["cell"]}']
    if selected["q_index"] is None:
        print("NO_HISTORICAL_CHOICE", t, flush=True)
        return
    if choice["Cstar"] is None or any(v["status"] != "NOT_CLEARLY_INFERIOR_WITHIN_REGISTERED_CHECK" for v in choice["baseline_adequacy"].values()):
        raise ValueError("Historical no-Z baseline gate failed; no evaluation permitted")
    rec = begin(args, [fitroot / "manifest.json", frozen / "manifest.json", args.base / "prepared" / "manifest.json"])
    rec.update(**t)
    data = np.load(args.base / "prepared" / "physical_channels.npy", mmap_mode="r")
    z = stage(args.base / "prepared", "evaluation")
    if t["estimator"] == "CONTROL":
        raw = control(data, z, t["cell"], producer["global_raw_quantile"])
    else:
        model = joblib.load(fitroot / "model.joblib")
        raw = np.maximum(model.predict(feature(data, z, t["cell"])), 0).reshape(z["shortfall"].shape)
    delta = json.loads((fitroot / "offsets.json").read_text())[selected["q_index"]]
    action = np.maximum(raw + delta, 0)
    np.savez_compressed(args.output / "actions.npz", raw=raw, calibrated=action)
    blocks = {}
    metrics = {}
    for name, mask, r in (("primary", z["primary_mask"], action), ("all_target_Zobs", z["target_mask"], action),
                          ("raw_primary", z["primary_mask"], raw)):
        b = account(z["shortfall"], r, mask, z["anchors"])
        blocks.update({f"{name}__{k}": v for k, v in b.items()})
        metrics[name] = {k: float(b[k].sum() / b["N"].sum()) for k in ("C", "V", "U", "R")}
        metrics[name]["cells"] = int(b["N"].sum())
        # Independent expression: L=S+10*pinball_.9(S-r), with dt applied once.
        sv, rv = z["shortfall"][mask].astype(float), r[mask].astype(float)
        residual = sv - rv
        independent = (sv + 10 * np.maximum(.9 * residual, -.1 * residual)) / 6
        measured = b["C"].sum() / b["N"].sum()
        if abs(independent.mean() - measured) > 1e-8 + 1e-10 * abs(measured):
            raise ValueError("Independent action accounting failed")
    np.savez_compressed(args.output / "blocks.npz", **blocks)
    save(args.output / "metrics.json", metrics)
    save(args.output / "action_audit.json", dict(status="PASS", formula="S+10*pinball_.9; dt once; float64",
        offset=delta, q=selected["q"], scoring_identity=identity({k: z[k] for k in ("anchors", "forecast", "target_indices", "primary_mask", "shortfall")})))
    finish(args, rec)


def aggregate(args, cfg):
    collected, n, days = collect(args, cfg, "evaluation")
    rec = begin(args, [args.base / "selection" / "manifest.json"] +
        [args.base / "evaluation" / str(i) / "manifest.json" for i in range(len(tasks(cfg)))
         if (args.base / "evaluation" / str(i) / "manifest.json").exists()])
    historical = json.loads((args.base / "selection" / "historical_choices.json").read_text())
    valid = [g for g in collected if all(r is not None for r in g["records"])]
    arrays = {key: np.stack([np.stack([g["records"][s][0][key] for g in valid]) for s in range(5)]) for key in ("C", "V", "U", "R")}
    labels = [f'{g["estimator"]}:{g["cell"]}' for g in valid]
    comparisons = []
    for e in ("HGB", "MLP"):
        for name, a, b, kind in (("fresh_state", "F", "FZ", "G"), ("old_state", "O6", "OZ6", "G"),
                ("old_power", "O6", "OP6", "G"), ("P_premium_vs_Z", "OP6", "OZ6", "D"),
                ("residual_state", "OP6", "OPZ6", "G"),
                ("severity_P_vs_Z", "OZ6", "OP6", "G"),
                ("severity_P_vs_PZ", "OPZ6", "OP6", "G")):
            if f"{e}:{a}" in labels and f"{e}:{b}" in labels:
                comparisons.append((f"{e}:{name}", labels.index(f"{e}:{a}"), labels.index(f"{e}:{b}"), kind))
    envelopes = {}
    for span in (3, 1, 7):
        result = joint_coordinates(arrays["C"], arrays["V"], arrays["U"], n, comparisons,
            historical["Cstar"], cfg["n_boot"], span, cfg["bootstrap_seed"] + 1, .05)
        envelopes[str(span)] = result
    primary = envelopes["3"]
    intervals = {}
    for j, label in enumerate(primary["labels"]):
        intervals["|".join(map(str, label))] = dict(point=primary["point"][j], lower=primary["lower"][j], upper=primary["upper"][j])
    risk = {}
    for k, label in enumerate(labels):
        indices = [s * len(labels) + k for s in range(5)]
        risk[label] = bool(np.all(primary["upper"][indices] <= .1))
    outcomes = {}
    for e in ("HGB", "MLP"):
        def pair_pass(name, low=None, high=None, severity=True):
            item = next((x for x in comparisons if x[0] == f"{e}:{name}"), None)
            if item is None:
                return False
            key, a, b, kind = item
            interval = intervals[f"{key}|cost|{kind}"]
            ok = risk[labels[a]] and risk[labels[b]]
            if low is not None:
                ok &= interval["lower"] > low
            if high is not None:
                ok &= interval["upper"] <= high
            if severity:
                ok &= all(intervals[f"{key}|severity_candidate_minus_reference|{s}"]["upper"] <= .001 for s in range(5))
            return bool(ok)
        A = pair_pass("fresh_state", low=.01) or pair_pass("residual_state", low=.01)
        B = (pair_pass("old_state", low=.01) and pair_pass("old_power", low=.01)
             and pair_pass("P_premium_vs_Z", high=.01, severity=False)
             and pair_pass("residual_state", high=.01, severity=False)
             and pair_pass("severity_P_vs_Z") and pair_pass("severity_P_vs_PZ"))
        C = all(pair_pass(name, high=.01, severity=False) for name in ("fresh_state", "old_state", "residual_state"))
        outcomes[e] = dict(route_A=A, route_B=B, bounded_low_gain_three_endpoint_pairs=C,
                           status="CANDIDATE_FOR_NEXT_STAGE_REVIEW" if A or B or C else "STOP_INVESTMENT_UNRESOLVED_OR_FAILED_GATES")
    save(args.output / "summary.json", dict(labels=labels, mean_cost=arrays["C"].sum(axis=-1).mean(axis=0) / n.sum(),
        instance_risk=arrays["V"].sum(axis=-1) / n.sum(), instance_uncovered=arrays["U"].sum(axis=-1) / n.sum(),
        risk_qualified=risk, registered_intervals=intervals, outcomes=outcomes,
        Cstar=historical["Cstar"], primary_family_size=primary["family_size"], days=days,
        n_cells=int(n.sum()), claim="Finite-program development only; no field/causal/independent confirmation claim",
        budget=dict(new_main_model_fits=60, simple_control_instances=10, additional_stages_started=False)))
    save(args.output / "envelopes.json", envelopes)
    np.savez_compressed(args.output / "paired_day_totals.npz", **arrays, N=n, days=days)
    finish(args, rec)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("prepare", "fit", "select", "evaluate", "aggregate"))
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--task", type=int, default=-1)
    args = parser.parse_args()
    cfg = json.loads(args.protocol.read_text())
    if cfg["seeds"] != list(range(201, 206)) or len(tasks(cfg)) != 70 or cfg["max_fit_rows"] != 360000:
        raise ValueError("Unregistered pilot grid")
    if args.stage in ("fit", "evaluate") and not 0 <= args.task < 70:
        raise ValueError("Task out of bounded grid")
    with threadpool_limits(2):
        globals()[args.stage](args, cfg)


if __name__ == "__main__":
    main()
