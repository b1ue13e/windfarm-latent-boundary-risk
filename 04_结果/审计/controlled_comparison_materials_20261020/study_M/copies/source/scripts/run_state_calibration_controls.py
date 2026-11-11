"""No-refit controls using archived WTB predictions from frozen checkpoints."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import shutil
import sys

import numpy as np
from threadpoolctl import threadpool_limits

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.run_state_measurement_pilot import verify as verify_parent, tasks as old_tasks, stage, SOURCES as OLD_SOURCES
from scripts.run_information_subset_study import sha, save
from windfarm_moe.risk_frontier import shared_block_draws, simultaneous_envelope
from windfarm_moe.state_measurement_controls import (CELLS, POLICIES, RECIPES, STATE_PAIRS,
    common_level, budget_shift, event_days, fast_account, labels_and_comparisons,
    controls_envelope, corrected_routes)


def begin(args, inputs):
    args.output.mkdir(parents=True, exist_ok=False)
    sources = [ROOT / p for p in OLD_SOURCES] + [Path(__file__),
        ROOT / "windfarm_moe/state_measurement_review.py", ROOT / "windfarm_moe/state_measurement_controls.py",
        ROOT / "experiments/state_measurement_pilot_20261020/protocol.json", args.protocol.resolve()]
    src = {str(p.relative_to(ROOT)): sha(p) for p in sources}
    for name in src:
        dest = args.output / "source" / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, dest)
    rec = dict(status="RUNNING", stage=args.stage, worker=args.worker, argv=sys.argv,
        started_utc=datetime.now(timezone.utc).isoformat(), source_sha256=src,
        input_sha256={str(p.resolve()): sha(p) for p in inputs}, protocol_sha256=sha(args.protocol),
        python=sys.version, numpy=np.__version__, sklearn=importlib.metadata.version("scikit-learn"),
        torch=importlib.metadata.version("torch"), platform=platform.platform(), host=platform.node(),
        cpu_model=Path("/proc/cpuinfo").read_text().split("model name")[-1].splitlines()[0] if Path("/proc/cpuinfo").exists() else platform.processor(),
        pbs_job_id=os.environ.get("PBS_JOBID"), threads=2, backend="CPU archived prediction accounting only",
        git_commit=json.loads((ROOT / "deployment_manifest.json").read_text())["git_commit"],
        new_model_fits=0, new_measurements=0, scope="Exposed WTB development, post-hoc diagnostic; no independent confirmation")
    save(args.output / "receipt.json", rec)
    return rec


def finish(args, rec):
    for name, value in rec["input_sha256"].items():
        if sha(name) != value:
            raise ValueError("Protected input changed: " + name)
    rec.update(status="COMPLETED_NO_REFIT_DEVELOPMENT", finished_utc=datetime.now(timezone.utc).isoformat())
    save(args.output / "receipt.json", rec)
    save(args.output / "manifest.json", {str(p.relative_to(args.output)): dict(bytes=p.stat().st_size, sha256=sha(p))
        for p in sorted(args.output.rglob("*")) if p.is_file() and p.name != "manifest.json"})
    print("COMPLETED", args.stage, args.worker, flush=True)


def verify(path, args, expected):
    manifest = json.loads((path / "manifest.json").read_text())
    for name, record in manifest.items():
        p = (path / name).resolve()
        if not p.is_relative_to(path.resolve()) or p.stat().st_size != record["bytes"] or sha(p) != record["sha256"]:
            raise ValueError("New bundle identity failed: " + str(p))
    rec = json.loads((path / "receipt.json").read_text())
    if rec["status"] != "COMPLETED_NO_REFIT_DEVELOPMENT" or rec["stage"] != expected or rec["protocol_sha256"] != sha(args.protocol):
        raise ValueError("New bundle stage/protocol mismatch")
    for name, value in rec["source_sha256"].items():
        if sha(ROOT / name) != value:
            raise ValueError("Implementation changed: " + name)
    return rec


def context(cfg):
    parent = Path(cfg["parent_results"])
    old_protocol = ROOT / "experiments/state_measurement_pilot_20261020/protocol.json"
    return parent, old_protocol, json.loads(old_protocol.read_text())


def worker_id(cfg, worker):
    if not 0 <= worker < 10:
        raise ValueError("Worker outside two estimators by five instances")
    return ("HGB" if worker < 5 else "MLP"), cfg["seeds"][worker % 5]


def task_for(oldcfg, est, cell, seed):
    return old_tasks(oldcfg).index(dict(estimator=est, cell=cell, seed=seed))


def load_raw(parent, oldcfg, est, seed, phase):
    values, offsets = {}, {}
    for cell in CELLS:
        path = parent / "fits" / str(task_for(oldcfg, est, cell, seed))
        if phase == "evaluation":
            with np.load(parent / "evaluation" / str(task_for(oldcfg, est, cell, seed)) / "actions.npz") as a:
                values[cell] = a["raw"]
        else:
            with np.load(path / f"{phase}_raw.npz") as a:
                values[cell] = a["raw"]
        offsets[cell] = np.asarray(json.loads((path / "offsets.json").read_text()), float)
    return values, offsets


def selected_q(choices, est, cell, recipe, common):
    if recipe == "Common":
        return common
    q = choices[f"{est}:{cell}"]["q_index"]
    if q is None:
        raise ValueError("No original historical choice")
    return q


def actions_for(raw, offsets, shifts, choices, est, common):
    actions = {}
    for recipe in RECIPES:
        for cell in CELLS:
            q = selected_q(choices, est, cell, recipe, common)
            actions[f"{recipe}|{cell}"] = np.maximum(raw[cell] + offsets[cell][q], 0)
        for name, base, state_cell in STATE_PAIRS:
            p = selected_q(choices, est, base, recipe, common)
            z = selected_q(choices, est, state_cell, recipe, common)
            delta = shifts[f"{name}|{p}|{z}"]["delta_kw"]
            actions[f"{recipe}|Match_{name}"] = np.maximum(actions[f"{recipe}|{base}"] + delta, 0)
    return actions


def prepare(args, cfg):
    parent, oldp, oldcfg = context(cfg)
    verify_parent(parent / "prepared", oldp, "prepare")
    verify_parent(parent / "selection", oldp, "select")
    inputs = [parent / "prepared/manifest.json", parent / "selection/manifest.json"]
    inputs += [parent / "fits" / str(i) / "manifest.json" for i in range(70)]
    rec = begin(args, inputs)
    historical = json.loads((parent / "selection/historical_choices.json").read_text())
    oldbounds = json.loads((parent / "selection/all_historical_bounds.json").read_text())
    upper = np.asarray(oldbounds["upper"][:350]).reshape(5, 14, 5)
    q = common_level(upper[:, :12], cfg["levels"])
    if q is None:
        raise ValueError("NO_HISTORICAL_COMMON_LEVEL; no fallback allowed")
    source_v = np.zeros((5, 70, 18))
    n, days, model_hashes = None, None, {}
    for i, t in enumerate(old_tasks(oldcfg)):
        path = parent / "fits" / str(i)
        verify_parent(path, oldp, "fit")
        mf = json.loads((path / "manifest.json").read_text())
        if t["estimator"] != "CONTROL":
            model_hashes[str(i)] = mf["model.joblib"]["sha256"]
        group = ((0 if t["estimator"] == "HGB" else 6) + CELLS.index(t["cell"])) if t["estimator"] != "CONTROL" else 12 + (t["cell"] == "Persistence")
        with np.load(path / "selection_blocks.npz") as a:
            for k in range(5):
                if n is None:
                    n, days = a[f"q{k}__N"], a[f"q{k}__days"]
                if not np.array_equal(n, a[f"q{k}__N"]) or not np.array_equal(days, a[f"q{k}__days"]):
                    raise ValueError("Historical common population mismatch")
                source_v[t["seed"] - 201, group * 5 + k] = a[f"q{k}__V"]
    np.savez_compressed(args.output / "original_risks.npz", V=source_v, N=n, days=days)
    save(args.output / "prepared.json", dict(common_q_index=q, common_q=cfg["levels"][q],
        common_rule="First level passing original historical joint bound for all60 main instances; never reselected",
        original_choices=historical["choices"], Cstar=historical["Cstar"],
        original_model_sha256=model_hashes, old_prepare_manifest_sha256=sha(parent / "prepared/manifest.json"),
        old_selection_manifest_sha256=sha(parent / "selection/manifest.json")))
    finish(args, rec)


def history(args, cfg):
    parent, oldp, oldcfg = context(cfg)
    verify(args.base / "prepared", args, "prepare")
    meta = json.loads((args.base / "prepared/prepared.json").read_text())
    est, seed = worker_id(cfg, args.worker)
    paths = [parent / "fits" / str(task_for(oldcfg, est, c, seed)) for c in CELLS]
    for p in paths:
        verify_parent(p, oldp, "fit")
    inputs = [args.base / "prepared/manifest.json"] + [p / name for p in paths for name in ("offset_raw.npz", "selection_raw.npz", "offsets.json")]
    inputs += [parent / "prepared/offset.npz", parent / "prepared/selection.npz"]
    rec = begin(args, inputs); rec.update(estimator=est, seed=seed)
    offset, select = stage(parent / "prepared", "offset"), stage(parent / "prepared", "selection")
    offraw, offsets = load_raw(parent, oldcfg, est, seed, "offset")
    selraw, _ = load_raw(parent, oldcfg, est, seed, "selection")
    shifts = {}
    risk = np.zeros((3, 5, 5, len(np.unique(select["anchors"] // 144))))
    for pair, (name, base, state_cell) in enumerate(STATE_PAIRS):
        for p in range(5):
            base_off = np.maximum(offraw[base] + offsets[base][p], 0)
            base_sel = np.maximum(selraw[base] + offsets[base][p], 0)
            for z in range(5):
                target_off = np.maximum(offraw[state_cell] + offsets[state_cell][z], 0)
                fitted = budget_shift(base_off, target_off, offset["primary_mask"])
                shifts[f"{name}|{p}|{z}"] = fitted
                r = np.maximum(base_sel + fitted["delta_kw"], 0)
                risk[pair, p, z] = event_days(select["shortfall"], r, select["primary_mask"], select["anchors"])
    save(args.output / "shifts.json", shifts)
    np.savez_compressed(args.output / "historical_risks.npz", V=risk)
    actions = actions_for(selraw, offsets, shifts, meta["original_choices"], est, meta["common_q_index"])
    totals = {}
    for key, r in actions.items():
        b = fast_account(select["shortfall"], r, select["primary_mask"], select["anchors"])
        totals.update({key + "|" + k: v for k, v in b.items()})
    np.savez_compressed(args.output / "historical_blocks.npz", **totals)
    finish(args, rec)


def freeze(args, cfg):
    verify(args.base / "prepared", args, "prepare")
    meta = json.loads((args.base / "prepared/prepared.json").read_text())
    paths = [args.base / "history" / str(i) for i in range(10)]
    for p in paths:
        verify(p, args, "history")
    rec = begin(args, [args.base / "prepared/manifest.json"] + [p / "manifest.json" for p in paths])
    with np.load(args.base / "prepared/original_risks.npz") as z:
        original, n = z["V"], z["N"]
    grid = np.zeros((5, 220, len(n))); grid[:, :70] = original
    for w in range(10):
        with np.load(paths[w] / "historical_risks.npz") as z:
            start = 70 + (w // 5) * 75
            grid[w % 5, start:start + 75] = z["V"].reshape(75, len(n))
    weights, dh = shared_block_draws(len(n), cfg["n_boot"], 3, cfg["history_seed"])
    denom = weights @ n
    point = grid.sum(axis=-1).ravel() / n.sum()
    boot = weights @ grid.reshape(-1, len(n)).T / denom[:, None]
    bound = simultaneous_envelope(point, boot, .05)
    upper = bound["upper"].reshape(5, 220)
    historical = {}
    for recipe in RECIPES:
        for e, est in enumerate(("HGB", "MLP")):
            for cell in POLICIES:
                if cell in CELLS:
                    q = selected_q(meta["original_choices"], est, cell, recipe, meta["common_q_index"])
                    index = (e * 6 + CELLS.index(cell)) * 5 + q
                else:
                    name = cell[len("Match_"):]
                    pair, (_, base, state_cell) = next((j, p) for j, p in enumerate(STATE_PAIRS) if p[0] == name)
                    p = selected_q(meta["original_choices"], est, base, recipe, meta["common_q_index"])
                    z = selected_q(meta["original_choices"], est, state_cell, recipe, meta["common_q_index"])
                    index = 70 + e * 75 + pair * 25 + p * 5 + z
                key = f"{recipe}:{est}:{cell}"
                historical[key] = dict(all_instances_qualified=bool(np.all(upper[:, index] <= .1)),
                    per_instance_upper=upper[:, index], risk_grid_column=index)
    save(args.output / "frozen.json", dict(**meta, historical_qualification=historical,
        historical_family_size=1100, historical_critical=bound["critical"], historical_draw_sha256=dh,
        rules="No q/margin changes after freeze; failed historical qualification remains diagnostic, never deployable",
        fixed_before_new_development_scoring=True))
    save(args.output / "historical_bounds.json", dict(point=point, lower=bound["lower"], upper=bound["upper"]))
    finish(args, rec)


def evaluate(args, cfg):
    parent, oldp, oldcfg = context(cfg)
    verify(args.base / "freeze", args, "freeze")
    verify(args.base / "history" / str(args.worker), args, "history")
    frozen = json.loads((args.base / "freeze/frozen.json").read_text())
    est, seed = worker_id(cfg, args.worker)
    paths = [parent / "evaluation" / str(task_for(oldcfg, est, c, seed)) for c in CELLS]
    for p in paths:
        verify_parent(p, oldp, "evaluate")
    rec = begin(args, [args.base / "freeze/manifest.json", args.base / "history" / str(args.worker) / "manifest.json",
                       parent / "prepared/evaluation.npz"] + [p / "actions.npz" for p in paths])
    rec.update(estimator=est, seed=seed)
    z = stage(parent / "prepared", "evaluation")
    raw, offsets = load_raw(parent, oldcfg, est, seed, "evaluation")
    shifts = json.loads((args.base / "history" / str(args.worker) / "shifts.json").read_text())
    actions = actions_for(raw, offsets, shifts, frozen["original_choices"], est, frozen["common_q_index"])
    for cell, path in zip(CELLS, paths):
        with np.load(path / "actions.npz") as old:
            if not np.array_equal(old["calibrated"], actions["Original|" + cell]):
                raise ValueError("Original action reconstruction changed")
    np.savez_compressed(args.output / "actions.npz", **actions)
    blocks, metrics, checks = {}, {}, 0
    with np.load(args.output / "actions.npz") as serialized:
        for name in actions:
            r = serialized[name]
            if not np.array_equal(r, actions[name]):
                raise ValueError("Serialized action changed")
            for population, mask in (("primary", z["primary_mask"]), ("all_target", z["target_mask"])):
                b = fast_account(z["shortfall"], r, mask, z["anchors"])
                sv, rv = z["shortfall"][mask], r[mask]
                residual = sv - rv
                independently = np.mean((sv + 10 * np.maximum(.9 * residual, -.1 * residual)) / 6)
                mean = b["C"].sum() / b["N"].sum()
                if abs(independently - mean) > 1e-8 + abs(mean) * 1e-10:
                    raise ValueError("Independent pinball accounting failed")
                checks += 1
                key = name + "|" + population
                blocks.update({key + "|" + k: v for k, v in b.items()})
                metrics[key] = {k: float(b[k].sum() / b["N"].sum()) for k in ("C", "R", "U", "V")}
                metrics[key]["N"] = int(b["N"].sum())
    np.savez_compressed(args.output / "blocks.npz", **blocks)
    save(args.output / "metrics.json", metrics)
    save(args.output / "audit.json", dict(status="SERIALIZED_ACTIONS_AND_INDEPENDENT_PINBALL_PASS", records=checks,
        original_actions_exact=True, historical_shifts_frozen=True, evaluation_budget_rematching=False))
    finish(args, rec)


def aggregate(args, cfg):
    verify(args.base / "freeze", args, "freeze")
    paths = [args.base / "evaluate" / str(w) for w in range(10)]
    for p in paths:
        verify(p, args, "evaluate")
    rec = begin(args, [args.base / "freeze/manifest.json"] + [p / "manifest.json" for p in paths])
    frozen = json.loads((args.base / "freeze/frozen.json").read_text())
    labels, pairs = labels_and_comparisons()
    arrays = {k: np.zeros((5, len(labels), 35)) for k in ("C", "U", "R", "V")}
    n, days = None, None
    metrics = []
    for w, path in enumerate(paths):
        est, seed = worker_id(cfg, w)
        with np.load(path / "blocks.npz") as z:
            for recipe in RECIPES:
                for cell in POLICIES:
                    key = f"{recipe}|{cell}|primary|"
                    if n is None:
                        n, days = z[key + "N"], z[key + "days"]
                    if not np.array_equal(n, z[key + "N"]) or not np.array_equal(days, z[key + "days"]):
                        raise ValueError("Paired population/day mismatch")
                    k = labels.index(f"{recipe}:{est}:{cell}")
                    for name in arrays:
                        arrays[name][seed - 201, k] = z[key + name]
        metrics.append(dict(worker=w, estimator=est, seed=seed, metrics=json.loads((path / "metrics.json").read_text())))
    arrays.update(N=n, days=days)
    np.savez_compressed(args.output / "day_totals.npz", **arrays)
    env = {str(span): controls_envelope(arrays, pairs, frozen["Cstar"], cfg["n_boot"], span, cfg["evaluation_seed"])
           for span in (3, 1, 7)}
    primary = env["3"]
    if primary["family_size"] != 596:
        raise ValueError("Unexpected complete coordinate family")
    intervals = {"|".join(map(str, name)): dict(point=primary["point"][i], lower=primary["lower"][i], upper=primary["upper"][i])
                 for i, name in enumerate(primary["labels"])}
    risk = {label: bool(np.all(primary["upper"][[s * len(labels) + k for s in range(5)]] <= .1))
            for k, label in enumerate(labels)}
    qualified = {label: risk[label] and frozen["historical_qualification"][label]["all_instances_qualified"] for label in labels}
    routes = {f"{recipe}:{est}": corrected_routes(f"{recipe}:{est}:", intervals, qualified)
              for recipe in RECIPES for est in ("HGB", "MLP")}
    attribution = {}
    for recipe in RECIPES:
        for est in ("HGB", "MLP"):
            for name, base, state_cell in STATE_PAIRS:
                prefix = f"{recipe}:{est}:"
                key = prefix + "allocation_" + name
                g, u, r = (intervals[key + suffix] for suffix in ("|cost|G", "|mean_U", "|mean_R"))
                instance = [intervals[key + "|instance_U|" + str(s)] for s in range(5)]
                both = qualified[prefix + state_cell] and qualified[prefix + "Match_" + name]
                info = both and r["upper"] <= 0 and u["upper"] < -.001 and g["lower"] >= -.01 and all(x["upper"] <= .001 for x in instance)
                premium_upper = g["upper"] / (1 - g["upper"]) if g["upper"] < 1 else np.inf
                margin = both and r["lower"] >= 0 and premium_upper <= .01 and all(-x["lower"] <= .001 for x in instance)
                attribution[prefix + name] = dict(state_allocation_candidate=bool(info), matched_power_sufficient=bool(margin),
                    historical_and_development_risk_pass=bool(both), matched_power_cost_premium_upper=premium_upper,
                    note="Mean_R is state minus historical-budget control; no evaluation rematching or new tolerance")
    save(args.output / "summary.json", dict(labels=labels, common_q=frozen["common_q"], Cstar=frozen["Cstar"],
        mean_metrics={key: arrays[key].sum(axis=-1).mean(axis=0) / n.sum() for key in ("C", "R", "U", "V")},
        interval=intervals, development_risk_qualified=risk, jointly_qualified=qualified,
        corrected_routes=routes, attribution=attribution, family_size=596, cells=int(n.sum()),
        scope="Frozen old weights, result-informed WTB development; finite control comparisons, not Bayes information or field certification"))
    save(args.output / "envelopes.json", env)
    save(args.output / "instance_metrics.json", metrics)
    finish(args, rec)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("stage", choices=("prepare", "history", "freeze", "evaluate", "aggregate"))
    p.add_argument("--protocol", type=Path, required=True)
    p.add_argument("--base", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--worker", type=int, default=-1)
    args = p.parse_args(); cfg = json.loads(args.protocol.read_text())
    if cfg["seeds"] != list(range(201, 206)) or cfg["levels"] != [.9, .925, .95, .975, .99] or cfg["n_boot"] != 20000:
        raise ValueError("Frozen grid changed")
    if cfg["thresholds"] != dict(cost=.01, risk=.1, severity=.001):
        raise ValueError("Original thresholds changed")
    with threadpool_limits(2):
        globals()[args.stage](args, cfg)


if __name__ == "__main__":
    main()
