"""Frozen finite information-subset development study, with staged evaluation."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
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
from windfarm_moe.information_subset import subset_grid, telemetry_columns, nested_samples, PinballMLP
from windfarm_moe.decision_information import block_totals
from windfarm_moe.risk_frontier import offset_grid, shared_block_draws, simultaneous_envelope, near_optimal_set


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def clean(value):
    if isinstance(value, np.ndarray):
        return clean(value.tolist())
    if isinstance(value, np.generic):
        return clean(value.item())
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    if isinstance(value, float) and not np.isfinite(value):
        return None
    return value


def save(path, value):
    Path(path).write_text(json.dumps(clean(value), indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")


def identity(arrays):
    return {k: {"shape": list(v.shape), "dtype": v.dtype.str,
                "sha256": hashlib.sha256(np.ascontiguousarray(v).tobytes()).hexdigest()} for k, v in arrays.items()}


def begin(out, protocol, inputs, arguments):
    import torch
    out.mkdir(parents=True, exist_ok=False)
    sources = [Path(__file__), ROOT / "windfarm_moe/information_subset.py",
               ROOT / "windfarm_moe/decision_information.py", ROOT / "windfarm_moe/risk_frontier.py", protocol]
    if (ROOT / "windfarm_moe/subset_inference.py").exists():
        sources.append(ROOT / "windfarm_moe/subset_inference.py")
    (out / "source").mkdir()
    for path in sources:
        shutil.copyfile(path, out / "source" / path.name)
    receipt = dict(status="RUNNING", started_utc=datetime.now(timezone.utc).isoformat(),
                   arguments=arguments, argv=sys.argv, protocol_sha256=sha(protocol),
                   source_sha256={str(p): sha(p) for p in sources},
                   input_sha256={str(p.resolve()): sha(p) for p in inputs},
                   python=sys.version, numpy=np.__version__, sklearn=sklearn.__version__, torch=torch.__version__,
                   torch_cuda_build=torch.version.cuda, backend="CPU; no CUDA computation", host=platform.node(),
                   platform=platform.platform(), pbs_job_id=os.environ.get("PBS_JOBID"),
                   allocated_cpus=os.environ.get("OMP_NUM_THREADS"),
                   git_commit=json.loads((ROOT / "deployment_manifest.json").read_text(encoding="utf-8"))["git_commit"] if (ROOT / "deployment_manifest.json").exists() else "workspace tests; exact source hashes recorded",
                   scope="Viewed WTB development only; original E04/E07 unchanged")
    save(out / "receipt.json", receipt)
    return receipt


def finish(out, receipt):
    for name, expected in receipt["input_sha256"].items():
        if sha(name) != expected:
            raise ValueError("Protected input changed: " + name)
    receipt.update(status="COMPLETED_DEVELOPMENT", finished_utc=datetime.now(timezone.utc).isoformat())
    save(out / "receipt.json", receipt)
    save(out / "manifest.json", {str(p.relative_to(out)): dict(bytes=p.stat().st_size, sha256=sha(p))
                                for p in sorted(out.rglob("*")) if p.is_file() and p.name != "manifest.json"})


def verify(out, protocol, stage, task=None):
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    if "receipt.json" not in manifest:
        raise ValueError("Unbound receipt")
    for name, record in manifest.items():
        p = (out / name).resolve()
        if not p.is_relative_to(out.resolve()) or p.stat().st_size != record["bytes"] or sha(p) != record["sha256"]:
            raise ValueError("Archived bytes differ: " + str(p))
    r = json.loads((out / "receipt.json").read_text(encoding="utf-8"))
    if r["status"] != "COMPLETED_DEVELOPMENT" or r["protocol_sha256"] != sha(protocol) or r["arguments"]["stage"] != stage:
        raise ValueError("Wrong stage/protocol")
    if task is not None and r["arguments"].get("task") != task:
        raise ValueError("Wrong task identity")
    if r["source_sha256"].get(str(Path(__file__))) != sha(__file__):
        raise ValueError("Consumer implementation differs")
    for name, value in r["source_sha256"].items():
        if Path(name).name != protocol.name and sha(name) != value:
            raise ValueError("Source implementation differs")
    return r


def tasks(cfg):
    result = []
    for condition in cfg["conditions"]:
        subsets = list(subset_grid()) if condition == "pitch_withheld" else cfg["pressure_subsets"]
        budgets = cfg["budgets"] if condition == "pitch_withheld" else cfg["pressure_budgets"]
        for seed in cfg["seeds"]:
            for subset in subsets:
                for estimator in ("HGB", "MLP"):
                    result.append(dict(condition=condition, seed=seed, subset=subset,
                                       estimator=estimator, budgets=budgets))
            result.append(dict(condition=condition, seed=seed, subset="P1", estimator="Persistence", budgets=[0]))
    return result


def parent(cfg):
    root = Path(cfg["parent_root"])
    path = root / "experiments/decision_information_development_20261018/protocol.json"
    if sha(path) != cfg["parent_protocol_sha256"]:
        raise ValueError("Wrong frozen parent")
    spec = importlib.util.spec_from_file_location("subset_frozen_parent", root / "scripts/run_decision_information_development.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    prepared = root / "results/prepared"
    m.verify_bundle(prepared, sha(path), "prepare")
    original = json.loads(path.read_text(encoding="utf-8"))
    if original["conditions"] != cfg["conditions"] or original["seeds"] != cfg["seeds"]:
        raise ValueError("Changed parent information conditions")
    data = np.load(prepared / "physical_channels.npy", mmap_mode="r")
    return m, prepared, data, original


def stage_data(m, prepared, data, name, condition):
    s = m.load_stage(prepared, data, name, condition, 36, 6)
    s["X"] = np.column_stack((m.common_matrix(s["forecast"], s["anchors"], data.shape[1]),
                               m.history_matrix(data, s["anchors"], [0, 1, 2, 3], 36, condition["delay_steps"])))
    del s["A"], s["B"]
    s["identity"] = identity({k: s[k] for k in ("anchors", "forecast", "true", "mask", "shortfall")})
    return s


def raw_predict(model, x, forecast, task, columns):
    if task["estimator"] == "Persistence":
        p = x[:, 4 + 36 + 35 - task["delay_steps"]]
        # Missing last power falls back to zero raw reserve, then historical calibration.
        return np.where(np.isfinite(p), np.maximum(forecast.reshape(-1) - p, 0), 0).astype(np.float64)
    return np.maximum(model.predict(x[:, columns]), 0).astype(np.float64)


def historical(args, cfg):
    task = tasks(cfg)[args.task_index]
    out = args.output / "historical" / str(args.task_index)
    if (out / "manifest.json").exists():
        verify(out, args.protocol, "historical", task)
        print("VERIFIED_EXISTING_HISTORY", args.task_index, flush=True)
        return
    m, prepared, data, original = parent(cfg)
    condition = cfg["conditions"][task["condition"]]
    fit = stage_data(m, prepared, data, "policy_fit", condition)
    cal = stage_data(m, prepared, data, "calibration", condition)
    inputs = [prepared / p for p in ("output_manifest.json", "physical_channels.npy", "policy_fit_forecast.npz", "calibration_forecast.npz")]
    receipt = begin(out, args.protocol, inputs, dict(stage="historical", task=task))
    grid = subset_grid()
    channels, lookback = grid[task["subset"]]
    cols = telemetry_columns(channels, lookback, condition["delay_steps"], condition["pitch_available"])
    if task["estimator"] == "Persistence":
        cols = np.asarray([0, 4 + 36 + 35 - condition["delay_steps"]])
    samples = nested_samples(fit["mask"], cfg["budgets"], task["seed"])
    masks = {"offset": cal["anchors"] + 7 < cfg["selection_first_anchor"],
             "selection": cal["anchors"] >= cfg["selection_first_anchor"]}
    if np.any(masks["offset"] & masks["selection"]) or not all(v.any() for v in masks.values()):
        raise ValueError("Invalid historical maturity split")
    all_totals, records = {}, {}
    for budget in task["budgets"]:
        t = time.monotonic()
        model = None
        fit_seconds = 0.0
        if task["estimator"] != "Persistence":
            indices = samples[budget]
            np.save(out / f"fit_indices_{budget}.npy", indices)
            xx, yy = fit["X"][indices][:, cols], fit["shortfall"].reshape(-1)[indices]
            model = m.learner(original["learner"], task["seed"], True) if task["estimator"] == "HGB" else PinballMLP(task["seed"], cfg["mlp"])
            fit_start = time.monotonic()
            model.fit(xx, yy)
            fit_seconds = time.monotonic() - fit_start
            joblib.dump(model, out / f"model_{budget}.joblib")
        actual = {**task, "delay_steps": condition["delay_steps"]}
        inference_start = time.monotonic()
        raw = raw_predict(model, cal["X"], cal["forecast"], actual, cols).reshape(cal["mask"].shape)
        inference_seconds = time.monotonic() - inference_start
        valid = cal["mask"][masks["offset"]]
        offsets = offset_grid(cal["shortfall"][masks["offset"]], raw[masks["offset"]], valid, cfg["offset_quantiles"])
        np.savez_compressed(out / f"calibration_{budget}.npz", raw=raw, offsets=offsets)
        for qi, offset in enumerate(offsets):
            z = masks["selection"]
            totals = block_totals(cal["shortfall"][z], np.maximum(raw[z] + offset, 0), cal["mask"][z], cal["anchors"][z])
            for key, value in totals.items():
                all_totals[f"{budget}__{qi}__{key}"] = value
        records[budget] = dict(seconds=time.monotonic() - t, fit_seconds=fit_seconds,
                               calibration_prediction_seconds=inference_seconds, predicted_rows=len(raw.reshape(-1)),
                               raw_input_width=len(cols),
                               channel_count=1 if task["estimator"] == "Persistence" else len(channels) + int(condition["pitch_available"]),
                               columns=cols.tolist(), training_trace=getattr(model, "training_trace_", None),
                               model_bytes=(out / f"model_{budget}.joblib").stat().st_size if model is not None else 0)
        print("FIT_COMPLETE", args.task_index, task, budget, records[budget]["seconds"], flush=True)
    np.savez_compressed(out / "historical_blocks.npz", **all_totals)
    save(out / "metadata.json", dict(task=task, records=records, stage_identity={"fit": fit["identity"], "calibration": cal["identity"]},
                                      offset_anchor_sha=identity({"anchors": cal["anchors"][masks["offset"]]}),
                                      selection_anchor_sha=identity({"anchors": cal["anchors"][masks["selection"]]})))
    finish(out, receipt)


def load_groups(args, cfg, stage):
    table = tasks(cfg)
    groups, inputs, details = [], [], []
    verified, identities, fit_samples = set(), None, {}
    for condition in cfg["conditions"]:
        budgets = cfg["budgets"] if condition == "pitch_withheld" else cfg["pressure_budgets"]
        for budget in budgets:
            subset_tasks = [(i, t) for i, t in enumerate(table) if t["condition"] == condition and t["seed"] == cfg["seeds"][0]]
            labels, cost, violation, counts, resources, offset_records = [], [], [], None, [], []
            for ti, task in subset_tasks:
                n = 0 if task["estimator"] == "Persistence" else budget
                for qi, q in enumerate(cfg["offset_quantiles"]):
                    labels.append(f'{task["subset"]}/{task["estimator"]}/n{n}/q{q}')
                    cc, vv, offsets = [], [], []
                    for seed in cfg["seeds"]:
                        actual = {**task, "seed": seed}
                        index = table.index(actual)
                        path = args.output / stage / str(index)
                        if path not in verified:
                            verify(path, args.protocol, stage, actual)
                            metadata = json.loads((path / "metadata.json").read_text(encoding="utf-8"))
                            if identities is None:
                                identities = metadata["stage_identity"]
                            elif identities != metadata["stage_identity"]:
                                raise ValueError("Different target/forecast/coordinate population")
                            if stage == "historical" and actual["estimator"] != "Persistence":
                                for nb in actual["budgets"]:
                                    key = (seed, nb)
                                    value = sha(path / f"fit_indices_{nb}.npy")
                                    if key in fit_samples and fit_samples[key] != value:
                                        raise ValueError("Unpaired training samples")
                                    fit_samples[key] = value
                            if stage == "evaluate" and metadata["choices_sha256"] != sha(args.output / "choose/choices.json"):
                                raise ValueError("Evaluation consumed different choices")
                            verified.add(path)
                        inp = path / ("historical_blocks.npz" if stage == "historical" else "evaluation_blocks.npz")
                        if inp not in inputs:
                            inputs.extend([inp, path / "manifest.json", path / "metadata.json"])
                        with np.load(inp) as a:
                            prefix = f"{n}__{qi}__"
                            count, blocks = a[prefix + "count"], a[prefix + "block_ids"]
                            if counts is None:
                                counts, block_ids = count.copy(), blocks.copy()
                            elif not np.array_equal(counts, count) or not np.array_equal(block_ids, blocks):
                                raise ValueError("Mismatched paired population")
                            cc.append(a[prefix + "loss_sum"])
                            vv.append(a[prefix + "violation_sum"])
                        offset_file = (args.output / "historical" / str(index) / f"calibration_{n}.npz" if stage == "historical"
                                       else path / f"evaluation_raw_{n}.npz")
                        with np.load(offset_file) as a:
                            offsets.append(float(a["offsets"][qi]))
                        if offset_file not in inputs:
                            inputs.append(offset_file)
                    cost.append(cc)
                    violation.append(vv)
                    channels, lookback = subset_grid()[task["subset"]]
                    width = len(telemetry_columns(channels, lookback, cfg["conditions"][condition]["delay_steps"], cfg["conditions"][condition]["pitch_available"]))
                    persistent = task["estimator"] == "Persistence"
                    resources.append([1 if persistent else len(channels) + int(cfg["conditions"][condition]["pitch_available"]),
                                      0 if task["estimator"] == "Persistence" else 1, width])
                    if persistent:
                        resources[-1][-1] = 2
                    offset_records.append((task["subset"], task["estimator"], n, offsets))
            exact = np.eye(len(labels), dtype=bool)
            for i, left in enumerate(offset_records):
                for j, right in enumerate(offset_records):
                    if left[:3] == right[:3] and left[3] == right[3]:
                        exact[i, j] = True
            groups.append(dict(costs=np.asarray(cost).transpose(1, 0, 2), violations=np.asarray(violation).transpose(1, 0, 2), counts=counts, exact_pair=exact))
            details.append(dict(condition=condition, budget=budget, labels=labels, resources=resources))
    return groups, list(dict.fromkeys(inputs)), details


def choose(args, cfg):
    groups, inputs, details = load_groups(args, cfg, "historical")
    out = args.output / "choose"
    receipt = begin(out, args.protocol, inputs, dict(stage="choose"))
    weights, drawhash = shared_block_draws(len(groups[0]["counts"]), cfg["n_boot"], 3, cfg["bootstrap_seed"])
    points, draws = [], []
    for g in groups:
        points.append(g["violations"].sum(axis=-1) / g["counts"].sum())
        draws.append(np.einsum("bd,skd->bsk", weights, g["violations"]) / (weights @ g["counts"])[:, None, None])
    bounds = simultaneous_envelope(np.concatenate([p.ravel() for p in points]), np.column_stack([d.reshape(len(weights), -1) for d in draws]), .05)
    position, choices = 0, []
    for g, d, point in zip(groups, details, points):
        upper = np.clip(bounds["upper"][position:position + point.size].reshape(point.shape), 0, 1)
        position += point.size
        nbase = len(d["labels"]) // len(cfg["offset_quantiles"])
        costs = g["costs"].mean(axis=0).sum(axis=-1) / g["counts"].sum()
        selected = []
        for base in range(nbase):
            indices = np.arange(base * 5, base * 5 + 5)
            feasible = [i for i in indices if np.all(upper[:, i] <= .1)]
            picked = min(feasible, key=lambda i: (costs[i], i)) if feasible else int(indices[-1])
            selected.append(dict(index=int(picked), label=d["labels"][picked], qualified=bool(feasible)))
        choices.append({**d, "selected": selected, "risk_upper": upper})
    save(out / "choices.json", dict(groups=choices, critical=bounds["critical"], draw_sha256=drawhash,
                                     rule=cfg["historical_rule"], uses_evaluation=False))
    finish(out, receipt)


def evaluate(args, cfg):
    task = tasks(cfg)[args.task_index]
    hist, chosen = args.output / "historical" / str(args.task_index), args.output / "choose"
    producer = verify(hist, args.protocol, "historical", task)
    choice_receipt = verify(chosen, args.protocol, "choose")
    consumed = choice_receipt["input_sha256"]
    if consumed.get(str((hist / "manifest.json").resolve())) != sha(hist / "manifest.json"):
        raise ValueError("Choice not bound to actual historical model")
    out = args.output / "evaluate" / str(args.task_index)
    m, prepared, data, original = parent(cfg)
    condition = cfg["conditions"][task["condition"]]
    ev = stage_data(m, prepared, data, "development_evaluation", condition)
    calpath = prepared / "calibration_forecast.npz"
    if producer["input_sha256"].get(str(calpath.resolve())) != sha(calpath):
        raise ValueError("Historical target source mismatch")
    inputs = [hist / "manifest.json", hist / "metadata.json", chosen / "manifest.json", chosen / "choices.json",
              prepared / "output_manifest.json", prepared / "physical_channels.npy", prepared / "development_evaluation_forecast.npz"]
    inputs += [hist / f"calibration_{n}.npz" for n in task["budgets"]]
    inputs += [hist / f"model_{n}.joblib" for n in task["budgets"] if n]
    receipt = begin(out, args.protocol, inputs, dict(stage="evaluate", task=task))
    channels, lookback = subset_grid()[task["subset"]]
    cols = telemetry_columns(channels, lookback, condition["delay_steps"], condition["pitch_available"])
    all_totals, timing = {}, {}
    for n in task["budgets"]:
        started = time.monotonic()
        model = joblib.load(hist / f"model_{n}.joblib") if n else None
        loaded = time.monotonic()
        raw = raw_predict(model, ev["X"], ev["forecast"], {**task, "delay_steps": condition["delay_steps"]}, cols).reshape(ev["mask"].shape)
        timing[n] = dict(model_load_seconds=loaded - started, prediction_seconds=time.monotonic() - loaded,
                         predicted_rows=raw.size)
        with np.load(hist / f"calibration_{n}.npz") as a:
            offsets = a["offsets"]
        np.savez_compressed(out / f"evaluation_raw_{n}.npz", raw=raw, offsets=offsets)
        for qi, offset in enumerate(offsets):
            totals = block_totals(ev["shortfall"], np.maximum(raw + offset, 0), ev["mask"], ev["anchors"])
            for key, value in totals.items():
                all_totals[f"{n}__{qi}__{key}"] = value
    np.savez_compressed(out / "evaluation_blocks.npz", **all_totals)
    save(out / "metadata.json", dict(task=task, stage_identity=ev["identity"], timing=timing,
                                     choices_sha256=sha(chosen / "choices.json")))
    finish(out, receipt)
    print("EVALUATED", args.task_index, flush=True)


def aggregate(args, cfg):
    from windfarm_moe.subset_inference import streamed_envelopes
    groups, inputs, details = load_groups(args, cfg, "evaluate")
    verify(args.output / "choose", args.protocol, "choose")
    choice_path = args.output / "choose/choices.json"
    choices = json.loads(choice_path.read_text(encoding="utf-8"))["groups"]
    inputs.append(choice_path)
    receipt = begin(args.output / "aggregate", args.protocol, inputs, dict(stage="aggregate"))
    results = []
    for span in (3, 1, 7):
        envelope = streamed_envelopes(groups, cfg["n_boot"], span, cfg["bootstrap_seed"], .05)
        for g, detail, choice, bound in zip(groups, details, choices, envelope["groups"]):
            if detail["labels"] != choice["labels"]:
                raise ValueError("Choice candidate labels differ")
            indices = np.array([c["index"] for c in choice["selected"]])
            historical_pass = [c["qualified"] for c in choice["selected"]]
            lo, hi = bound["risk_lower"], bound["risk_upper"]
            ratio = bound["relative_ratio_upper"]
            order = detail["resources"]
            selected = [near_optimal_set(lo[:, indices], hi[:, indices], ratio[np.ix_(indices, indices)], historical_pass,
                                         [order[i] for i in indices], e, .1) for e in cfg["epsilon_curve"]]
            capability = [near_optimal_set(lo, hi, ratio, np.ones(len(order), bool), order, e, .1) for e in cfg["epsilon_curve"]]
            results.append(dict(span=span, **detail, **bound, historical_choices=choice["selected"],
                                primary_historical_recipe=selected, secondary_retrospective_grid=capability,
                                bootstrap_critical=envelope["critical"], draw_sha256=envelope["draw_sha256"]))
        print("AGGREGATED_SPAN", span, flush=True)
    save(args.output / "aggregate/results.json", dict(status="DEVELOPMENT_ONLY", results=results,
             scope=cfg["scope"], stop_rules=cfg["stop_rules"], deployment_certified=False))
    finish(args.output / "aggregate", receipt)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("stage", choices=["historical", "choose", "evaluate", "aggregate", "list"])
    p.add_argument("--protocol", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--task-index", type=int, default=0)
    args = p.parse_args()
    cfg = json.loads(args.protocol.read_text(encoding="utf-8"))
    if cfg["offset_quantiles"] != [.9, .925, .95, .975, .99] or cfg["v_max"] != .1:
        raise ValueError("Frozen action grid or cap changed")
    if args.stage == "list":
        print(json.dumps(tasks(cfg)))
    else:
        globals()[args.stage](args, cfg)


if __name__ == "__main__":
    with threadpool_limits(limits=2):
        main()
