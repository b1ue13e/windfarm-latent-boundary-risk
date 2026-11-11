"""Execute the V3 supplement without invoking the legacy deployment selector."""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from repo_paths import Path, repository_root
import platform
import shutil
import subprocess
import sys
import time

import joblib
import numpy as np
from threadpoolctl import threadpool_limits

ROOT = Path(repository_root())
sys.path.insert(0, str(ROOT))
from scripts.run_decision_information_development import learner
from scripts.run_state_measurement_pilot import tasks as original_tasks
from windfarm_moe.information_subset import PinballMLP
from windfarm_moe.praw_offline_supplement import (freeze_registry, praw_information_matrix,
    fit_signed_offset, evaluate_all, pool_daily_totals)
from windfarm_moe.state_measurement import account


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def save(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def load_stage(prepared: Path, phase: str) -> dict[str, np.ndarray]:
    with np.load(prepared / f"{phase}.npz", allow_pickle=False) as archive:
        return {k: archive[k] for k in archive.files}


def verify_bundle(path: Path, stage: str | None = None) -> dict:
    manifest = json.loads((path / "manifest.json").read_text())
    for name, info in manifest.items():
        member = (path / name).resolve()
        if not member.is_relative_to(path.resolve()) or not member.is_file():
            raise ValueError("Invalid archived member: " + str(member))
        if member.stat().st_size != info["bytes"] or sha(member) != info["sha256"]:
            raise ValueError("Archive mismatch: " + str(member))
    receipt = json.loads((path / "receipt.json").read_text())
    if not receipt["status"].startswith("COMPLETED") or (stage and receipt["stage"] != stage):
        raise ValueError("Unfinished or incorrect producer stage: " + str(path))
    return receipt


def begin(args: argparse.Namespace, inputs: list[Path]) -> dict:
    args.output.mkdir(parents=True, exist_ok=False)
    sources = [Path(__file__), ROOT / "windfarm_moe/praw_offline_supplement.py",
        ROOT / "windfarm_moe/supplement_endpoint_adapter.py",
        ROOT / "windfarm_moe/supplement_group_accounting.py",
        ROOT / "windfarm_moe/supplement_inference.py",
        ROOT / "windfarm_moe/state_measurement.py", ROOT / "windfarm_moe/information_subset.py",
        ROOT / "windfarm_moe/decision_information.py", ROOT / "windfarm_moe/risk_frontier.py",
        ROOT / "scripts/run_state_measurement_pilot.py",
        ROOT / "scripts/run_decision_information_development.py", args.protocol, args.rules, args.coordinates]
    src = {}
    for path in sources:
        relative = str(path.resolve().relative_to(ROOT)).replace("\\", "/")
        target = args.output / "source" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        src[relative] = sha(path)
    rec = dict(stage=args.stage, worker=args.worker, status="RUNNING", argv=sys.argv,
        started_utc=datetime.now(timezone.utc).isoformat(), host=platform.node(), platform=platform.platform(),
        python=sys.version, executable=sys.executable,
        packages={k: importlib.metadata.version(k) for k in ("numpy", "scikit-learn", "torch", "pandas", "joblib")},
        cpu=Path("/proc/cpuinfo").read_text().split("model name")[-1].splitlines()[0] if Path("/proc/cpuinfo").exists() else platform.processor(),
        pbs_job_id=os.environ.get("PBS_JOBID"), threads=2, backend="CPU; fixed original recipes; no GPU required",
        thread_environment={k: os.environ.get(k) for k in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS")},
        git_commit=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() if (ROOT / ".git").exists() else json.loads((ROOT / "deployment_manifest.json").read_text())["git_commit"],
        protocol_sha256=sha(args.protocol), rules_sha256=sha(args.rules), coordinates_sha256=sha(args.coordinates),
        source_sha256=src, input_sha256={str(p.resolve()): sha(p) for p in inputs},
        scope="Exposed WTB retrospective supplementary comparison; no independent confirmation or field savings")
    save(args.output / "receipt.json", rec)
    return rec


def finish(args: argparse.Namespace, rec: dict) -> None:
    for name, expected in rec["input_sha256"].items():
        if sha(Path(name)) != expected:
            raise ValueError("Read-only input changed: " + name)
    rec.update(status="COMPLETED_V3_SUPPLEMENT", finished_utc=datetime.now(timezone.utc).isoformat())
    save(args.output / "receipt.json", rec)
    save(args.output / "manifest.json", {str(p.relative_to(args.output)).replace("\\", "/"):
        dict(bytes=p.stat().st_size, sha256=sha(p)) for p in sorted(args.output.rglob("*"))
        if p.is_file() and p.name != "manifest.json"})
    print("COMPLETED", args.stage, args.worker, flush=True)


def context(args: argparse.Namespace) -> tuple[dict, dict, Path, dict]:
    cfg, rules = json.loads(args.protocol.read_text()), json.loads(args.rules.read_text())
    if not cfg["execution_authorized"] or cfg["rules_sha256"] != sha(args.rules):
        raise ValueError("Execution authorization/rules binding missing")
    if cfg["coordinates_sha256"] != sha(args.coordinates):
        raise ValueError("Predeclared coordinate ledger changed")
    for package, expected in cfg["expected_packages"].items():
        if importlib.metadata.version(package) != expected:
            raise ValueError("Original recipe environment mismatch: " + package)
    if rules["version"] != "V3" or rules["immutable"]["primary_offset_quantile"] != .925:
        raise ValueError("Wrong supplementary policy")
    if cfg["max_new_model_fits"] != 10 or cfg["optional_budget_active"]:
        raise ValueError("No expanded fit budget or optional normalization is authorized")
    parent = Path(cfg["parent_results"])
    original = json.loads((ROOT / "experiments/state_measurement_pilot_20261020/protocol.json").read_text())
    if sha(ROOT / "experiments/state_measurement_pilot_20261020/protocol.json") != rules["source_protocol_sha256"]:
        raise ValueError("Original protocol changed")
    return cfg, rules, parent, original


def prepare(args: argparse.Namespace) -> None:
    cfg, rules, parent, original = context(args)
    registry = freeze_registry(rules)
    prepared = parent / "prepared"
    old_receipt = verify_bundle(prepared, "prepare")
    if old_receipt["protocol_sha256"] != rules["source_protocol_sha256"]:
        raise ValueError("Original prepared data protocol mismatch")
    for name, digest in old_receipt["source_sha256"].items():
        if sha(ROOT / name) != digest:
            raise ValueError("Original successful feature/recipe source changed: " + name)
    common = Path(cfg["controls_results"]) / "prepared"
    verify_bundle(common, "prepare")
    meta = json.loads((common / "prepared.json").read_text())
    if meta["common_q"] != .925 or meta["common_q_index"] != 1 or meta["Cstar"] != rules["immutable"]["Cstar"]:
        raise ValueError("Common q or Cstar reference mismatch")
    bundle_paths = [prepared, common]
    for task, identity in enumerate(original_tasks(original)):
        if identity["estimator"] == "CONTROL":
            continue
        for phase, expected in (("fits", "fit"), ("evaluation", "evaluate")):
            path = parent / phase / str(task)
            producer = verify_bundle(path, expected)
            if any(producer[k] != identity[k] for k in ("estimator", "cell", "seed")):
                raise ValueError("Original identity mismatch")
            for name, digest in producer["source_sha256"].items():
                if sha(ROOT / name) != digest:
                    raise ValueError("Original successful producer source changed: " + name)
            bundle_paths.append(path)
    for i in range(10):
        path = Path(cfg["controls_results"]) / "evaluate" / str(i)
        verify_bundle(path, "evaluate")
        bundle_paths.append(path)
    rec = begin(args, [p / "manifest.json" for p in bundle_paths] + [prepared / "node_ids.npy"])
    for phase, bounds in rules["stages"].items():
        z = load_stage(prepared, "selection" if phase == "historical" else phase)
        a = z["anchors"]
        if not np.array_equal(a, np.arange(*bounds)) or not np.array_equal(z["target_indices"], a + 6) or not np.array_equal(z["publication_indices"], a - 6):
            raise ValueError("Source clocks/targets do not match V3")
    nodes = np.load(prepared / "node_ids.npy")
    if len(nodes) != 134 or len(set(nodes.tolist())) != 134:
        raise ValueError("Fixed134 node identity invalid")
    for row in registry:
        same_seed = [parent / "fits" / str(i) / "fit_indices.npy" for i, t in enumerate(original_tasks(original))
                     if t["seed"] == row["seed"] and t["estimator"] != "CONTROL"]
        if len({sha(p) for p in same_seed}) != 1:
            raise ValueError("Original paired training rows disagree")
    save(args.output / "registry.json", registry)
    save(args.output / "source_verification.json", dict(common_q=.925, Cstar=meta["Cstar"],
        original_node_ids_sha256=sha(prepared / "node_ids.npy"),
        physical_sha256=sha(prepared / "physical_channels.npy"), labels_read_for_scheduling=False,
        actual_field_arrival="UNKNOWN", model_fits=0))
    finish(args, rec)


def fit_worker(args: argparse.Namespace) -> None:
    cfg, rules, parent, original = context(args)
    verify_bundle(args.base / "prepared", "prepare")
    registry = json.loads((args.base / "prepared/registry.json").read_text())
    row = registry[args.worker]
    task = original_tasks(original).index(dict(estimator=row["estimator"], cell="O6", seed=row["seed"]))
    prepared = parent / "prepared"
    verify_bundle(prepared, "prepare")
    index_path = parent / "fits" / str(task) / "fit_indices.npy"
    rec = begin(args, [prepared / "manifest.json", index_path, args.base / "prepared/manifest.json"] +
        [prepared / name for name in ("physical_channels.npy", "node_ids.npy", "fit.npz", "offset.npz", "selection.npz", "evaluation.npz")])
    rec.update(**row)
    data = np.load(prepared / "physical_channels.npy", mmap_mode="r")
    model, offset = None, None
    status = dict(**row, compute_status="PLANNED", failure_reason=None,
                  label_used_for_evaluation_selection=False)
    try:
        train = load_stage(prepared, "fit")
        indices = np.load(index_path)
        if indices.shape != (360000,) or not np.asarray(train["target_mask"]).ravel()[indices].all():
            raise ValueError("SOURCE_CONTRACT_INVALID: original training rows invalid")
        np.save(args.output / "fit_indices.npy", indices)
        x = praw_information_matrix(data, train["anchors"], train["forecast"])[indices]
        y = train["shortfall"].ravel()[indices]
        model = learner(original["hgb"], row["seed"], True) if row["estimator"] == "HGB" else PinballMLP(row["seed"], original["mlp"])
        start = time.monotonic()
        model.fit(x, y)
        rec["fit_seconds"] = time.monotonic() - start
        rec["fit_rows"] = len(indices)
        joblib.dump(model, args.output / "model.joblib")
        if row["estimator"] == "MLP":
            save(args.output / "training_trace.json", model.training_trace_)
        del x, y, train
        z = load_stage(prepared, "offset")
        raw = np.maximum(model.predict(praw_information_matrix(data, z["anchors"], z["forecast"])), 0).reshape(z["shortfall"].shape)
        offset = fit_signed_offset(raw, z["shortfall"], z["target_mask"])
        np.savez_compressed(args.output / "offset_raw.npz", raw=raw)
        save(args.output / "own_offset.json", dict(q=.925, offset_kw=offset,
            method="higher", fit_indices_sha256=sha(index_path), population="offset_target_mask"))
        del raw, z
        status["compute_status"] = "CALIBRATED"
    except (ValueError, RuntimeError, MemoryError, OSError) as exc:
        status.update(compute_status="COMPUTATION_FAILED", failure_reason=f"{type(exc).__name__}: {exc}")
    if status["compute_status"] == "CALIBRATED":
        for phase in ("selection", "evaluation"):
            try:
                z = load_stage(prepared, phase)
                inputs = dict(features=praw_information_matrix(data, z["anchors"], z["forecast"]),
                    shortfall=z["shortfall"], mask=z["primary_mask"], anchors=z["anchors"])
                evaluated = evaluate_all([row], {row["identity_id"]: model}, {row["identity_id"]: offset}, inputs)[0]
                if evaluated["compute_status"] == "EVALUATION_COMPLETED":
                    np.savez_compressed(args.output / f"{phase}_actions.npz", raw=evaluated["raw"], actions=evaluated["actions"])
                    np.savez_compressed(args.output / f"{phase}_blocks.npz", **evaluated["blocks"])
                    save(args.output / f"{phase}_metrics.json", pool_daily_totals(evaluated["blocks"]))
                del inputs, z
            except (ValueError, RuntimeError, MemoryError, OSError) as exc:
                evaluated = dict(compute_status="COMPUTATION_FAILED", failure_reason=f"{type(exc).__name__}: {exc}")
            if evaluated["compute_status"] != "EVALUATION_COMPLETED":
                status[f"{phase}_failure_reason"] = evaluated["failure_reason"]
            status["history_compute_status" if phase == "selection" else "evaluation_compute_status"] = evaluated["compute_status"]
            if phase == "evaluation":
                status.update(compute_status=evaluated["compute_status"], failure_reason=evaluated["failure_reason"])
            del evaluated
    status.update(model_hash=sha(args.output / "model.joblib") if (args.output / "model.joblib").exists() else None,
                  offset_hash=sha(args.output / "own_offset.json") if (args.output / "own_offset.json").exists() else None,
                  evaluation_hash=sha(args.output / "evaluation_actions.npz") if (args.output / "evaluation_actions.npz").exists() else None,
                  source_hashes=rec.get("source_sha256", {}))
    save(args.output / "identity.json", status)
    finish(args, rec)


def account_worker(args: argparse.Namespace) -> None:
    from windfarm_moe.supplement_group_accounting import fixed_group_masks, group_account
    cfg, rules, parent, original = context(args)
    verify_bundle(args.base / "prepared", "prepare")
    registry = json.loads((args.base / "prepared/registry.json").read_text())
    identity = registry[args.worker]
    prepared, oldactions = parent / "prepared", Path(cfg["controls_results"]) / "evaluate" / str(args.worker)
    verify_bundle(prepared, "prepare")
    verify_bundle(oldactions, "evaluate")
    old_fit_paths = [parent / "fits" / str(original_tasks(original).index(
        dict(estimator=identity["estimator"], cell=cell, seed=identity["seed"])))
        for cell in ("O6", "OP6", "OZ6", "F", "FZ", "OPZ6")]
    for path in old_fit_paths:
        verify_bundle(path, "fit")
    rec = begin(args, [prepared / "manifest.json", oldactions / "manifest.json"] +
        [p / name for p in old_fit_paths for name in ("offsets.json", "selection_raw.npz")])
    data = np.load(prepared / "physical_channels.npy", mmap_mode="r")
    arrays, coverage, points = {}, {}, {}
    for phase, family in (("selection", "H_P"), ("evaluation", "E_P")):
        z = load_stage(prepared, phase)
        for cell in ("O6", "OP6", "OZ6", "F", "FZ", "OPZ6"):
            task = original_tasks(original).index(dict(estimator=identity["estimator"], cell=cell, seed=identity["seed"]))
            fitpath = parent / "fits" / str(task)
            offsets = json.loads((fitpath / "offsets.json").read_text())
            if phase == "selection":
                with np.load(fitpath / "selection_raw.npz") as archive:
                    raw = archive["raw"]
                action = np.maximum(raw + offsets[1], 0)
            else:
                with np.load(oldactions / "actions.npz") as archive:
                    action = archive["Common|" + cell]
                with np.load(parent / "evaluation" / str(task) / "actions.npz") as archive:
                    if not np.array_equal(action, np.maximum(archive["raw"] + offsets[1], 0)):
                        raise ValueError("Common .925 reference reconstruction mismatch")
            b = account(z["shortfall"], action, z["primary_mask"], z["anchors"])
            arrays.update({f"{family}|{cell}|{k}": value for k, value in b.items()})
            points[f"{family}|{cell}"] = pool_daily_totals(b)
            if phase == "evaluation":
                a = z["anchors"]
                wind, ramp = data[a, :, 0], data[a, :, 1] - data[a - 6, :, 1]
                groups = {"wind_proxy|below_10p5": np.isfinite(wind) & (wind < 10.5),
                    "wind_proxy|at_or_above_10p5": np.isfinite(wind) & (wind >= 10.5),
                    "wind_proxy|missing": ~np.isfinite(wind),
                    "past60_ramp|down_gt150": np.isfinite(ramp) & (ramp < -150),
                    "past60_ramp|up_gt150": np.isfinite(ramp) & (ramp > 150),
                    "past60_ramp|within150": np.isfinite(ramp) & (ramp >= -150) & (ramp <= 150),
                    "past60_ramp|unknown_endpoint": ~np.isfinite(ramp)}
                for axis in ("wind_proxy", "past60_ramp"):
                    partition = np.sum([v for k, v in groups.items() if k.startswith(axis + "|")], axis=0)
                    if not np.all(partition == 1):
                        raise ValueError("Regime masks must form a complete disjoint partition")
                if cell in ("F", "FZ", "OP6", "OPZ6"):
                    for key, membership in groups.items():
                        bgroup = account(z["shortfall"], action, z["primary_mask"] & membership, a)
                        arrays.update({f"E_R|{cell}|{key}|{k}": value for k, value in bgroup.items()})
                        points[f"E_R|{cell}|{key}"] = pool_daily_totals(bgroup)
                if cell in ("OP6", "OPZ6"):
                    target, pair = fixed_group_masks(data, a, z["forecast"])
                    g = group_account(data, a, z["forecast"], action, pair)
                    arrays.update({f"E_G|{cell}|{k}": value for k, value in g.items()})
                    points[f"E_G|{cell}"] = pool_daily_totals(g)
                    coverage.update(target_intervals=int(target.sum()), pair_intervals=int(pair.sum()),
                        issue_intervals=len(a), fixed_members=134,
                        target_mask_sha256=hashlib.sha256(target.tobytes()).hexdigest(),
                        pair_mask_sha256=hashlib.sha256(pair.tobytes()).hexdigest(),
                        no_online_membership_switch=True)
    np.savez_compressed(args.output / "daily_totals.npz", **arrays)
    save(args.output / "point_metrics.json", points)
    save(args.output / "group_coverage.json", coverage)
    finish(args, rec)


def infer(args: argparse.Namespace) -> None:
    from windfarm_moe.supplement_inference import assemble_inference
    cfg, rules, parent, original = context(args)
    del parent, original
    paths = [args.base / branch / str(i) for branch in ("fits", "accounting") for i in range(10)]
    for path in paths:
        verify_bundle(path)
    rec = begin(args, [p / "manifest.json" for p in paths])
    ledger = [json.loads((args.base / "fits" / str(i) / "identity.json").read_text()) for i in range(10)]
    save(args.output / "sealed_evaluation_ledger.json", ledger)
    assemble_inference(args.base, args.output, args.coordinates, rules, ledger)
    rec.update(new_model_fits=0, inference_is_post_seal=True)
    finish(args, rec)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("prepare", "fit", "account", "infer"), required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--rules", type=Path, required=True)
    parser.add_argument("--coordinates", type=Path, required=True)
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--worker", type=int, default=-1)
    args = parser.parse_args()
    if args.stage in ("fit", "account") and not 0 <= args.worker < 10:
        parser.error("A fixed worker index 0..9 is required")
    with threadpool_limits(limits=2):
        {"prepare": prepare, "fit": fit_worker, "account": account_worker, "infer": infer}[args.stage](args)


if __name__ == "__main__":
    main()
