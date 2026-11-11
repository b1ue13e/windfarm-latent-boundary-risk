"""Historical post-processing and retrospective risk/cost identification.

Only new output directories are written. Parent models/actions remain immutable.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import importlib.util
import json
import os
from repo_paths import Path, repository_root
import platform
import shutil
import sys
import time
from typing import Any

import joblib
import numpy as np
import sklearn
from threadpoolctl import threadpool_limits

ROOT = Path(repository_root())
sys.path.insert(0, str(ROOT))
from windfarm_moe.decision_information import block_totals
from windfarm_moe.risk_frontier import offset_grid, shared_block_draws, simultaneous_envelope, near_optimal_set


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def clean(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return clean(value.tolist())
    if isinstance(value, np.generic):
        return clean(value.item())
    if isinstance(value, dict):
        return {k: clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    if isinstance(value, float) and not np.isfinite(value):
        return None
    return value


def save(path: Path, value: Any) -> None:
    path.write_text(json.dumps(clean(value), indent=2, allow_nan=False), encoding="utf-8")


def array_identity(arrays: dict[str, np.ndarray]) -> dict[str, Any]:
    return {name: {"shape": list(np.asarray(value).shape), "dtype": np.asarray(value).dtype.str,
                   "sha256": hashlib.sha256(np.ascontiguousarray(value).tobytes()).hexdigest()}
            for name, value in arrays.items()}


def require_consumed_input(receipt: dict[str, Any], path: Path) -> None:
    bound = {str(Path(name).resolve()): value for name, value in receipt["input_sha256"].items()}
    if bound.get(str(path.resolve())) != sha(path):
        raise ValueError("Selected upstream did not consume this input: " + str(path))


def begin(out: Path, protocol_path: Path, inputs: list[Path], arguments: dict[str, Any]) -> dict[str, Any]:
    out.mkdir(parents=True, exist_ok=False)
    sources = [Path(__file__), ROOT / "windfarm_moe/risk_frontier.py", ROOT / "windfarm_moe/decision_information.py", protocol_path]
    (out / "source").mkdir()
    for p in sources:
        shutil.copyfile(p, out / "source" / p.name)
    record = {"status": "RUNNING_DEVELOPMENT", "started_utc": datetime.now(timezone.utc).isoformat(),
              "arguments": arguments, "argv": sys.argv, "protocol_sha256": sha(protocol_path),
              "source_sha256": {str(p): sha(p) for p in sources},
              "input_sha256": {str(p.resolve()): sha(p) for p in inputs},
              "python": sys.version, "numpy": np.__version__, "sklearn": sklearn.__version__,
              "torch_installed": importlib.metadata.version("torch"), "host": platform.node(),
              "platform": platform.platform(), "pbs_job_id": os.environ.get("PBS_JOBID"),
              "backend": "CPU; no CUDA computation", "scope": "already-viewed WTB development; no E04/E07 or deployment certification"}
    save(out / "receipt.json", record)
    return record


def finish(out: Path, receipt: dict[str, Any]) -> None:
    for name, identity in receipt["input_sha256"].items():
        if sha(Path(name)) != identity:
            raise ValueError("Protected input changed: " + name)
    receipt.update(status="COMPLETED_DEVELOPMENT", finished_utc=datetime.now(timezone.utc).isoformat())
    save(out / "receipt.json", receipt)
    save(out / "manifest.json", {str(p.relative_to(out)): {"bytes": p.stat().st_size, "sha256": sha(p)}
                                for p in sorted(out.rglob("*")) if p.is_file() and p.name != "manifest.json"})


def verify(path: Path, protocol_hash: str, stage: str, seed: int | None = None,
           condition: str | None = None) -> dict[str, Any]:
    manifest = json.loads((path / "manifest.json").read_text())
    if "receipt.json" not in manifest:
        raise ValueError("Receipt is not covered by the manifest")
    for name, item in manifest.items():
        p = (path / name).resolve()
        if not p.is_relative_to(path.resolve()) or p.stat().st_size != item["bytes"] or sha(p) != item["sha256"]:
            raise ValueError("Upstream manifest mismatch: " + name)
    receipt = json.loads((path / "receipt.json").read_text())
    if receipt["status"] != "COMPLETED_DEVELOPMENT" or receipt["protocol_sha256"] != protocol_hash:
        raise ValueError("Incomplete or mixed-protocol upstream")
    for key, expected in (("stage", stage), ("seed", seed), ("condition", condition)):
        if expected is not None and receipt["arguments"].get(key) != expected:
            raise ValueError("Upstream identity mismatch: " + key)
    bound = {Path(k).name: v for k, v in receipt["source_sha256"].items()}
    for p in (Path(__file__), ROOT / "windfarm_moe/risk_frontier.py", ROOT / "windfarm_moe/decision_information.py"):
        if bound[p.name] != sha(p):
            raise ValueError("Mixed source implementation")
    return receipt


def parent_runtime(protocol: dict[str, Any]) -> tuple[Any, Path, dict[str, Any]]:
    root = Path(protocol["parent_root"])
    if sha(root / "compact_evidence.tar.gz") != protocol["parent_archive_sha256"]:
        raise ValueError("Parent evidence archive identity mismatch")
    spec = importlib.util.spec_from_file_location("frozen_parent_frontier_runtime", root / "scripts/run_decision_information_development.py")
    if spec is None or spec.loader is None:
        raise ValueError("Cannot load frozen parent runtime")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    pp = root / "experiments/decision_information_development_20261018/protocol.json"
    if sha(pp) != protocol["parent_protocol_sha256"]:
        raise ValueError("Parent protocol identity mismatch")
    parent = json.loads(pp.read_text())
    module.verify_bundle(root / "results/prepared", sha(pp), "prepare")
    return module, root, parent


def split_calibration(anchors: np.ndarray, split: int, evaluation_start: int, horizon: int, release: int) -> tuple[np.ndarray, np.ndarray]:
    issue = np.asarray(anchors)
    fit = issue + horizon + release < split
    select = (issue >= split) & (issue + horizon + release < evaluation_start)
    if not fit.any() or not select.any() or np.any(fit & select):
        raise ValueError("Empty or overlapping calibration/selection stages")
    if issue[fit].max() + horizon + release >= issue[select].min():
        raise ValueError("Calibration targets not mature before selection")
    return fit, select


def bins_predict(model: dict[str, Any], wind: np.ndarray) -> np.ndarray:
    r = np.full(wind.shape, model["missing_fallback"], dtype=np.float64)
    valid = np.isfinite(wind)
    r[valid] = np.asarray(model["quantiles"])[np.searchsorted(model["edges"], wind[valid], side="right")]
    return r


def historical(args: argparse.Namespace, protocol: dict[str, Any]) -> None:
    p, parent_root, old = parent_runtime(protocol)
    parent_run = parent_root / f"results/runs/seed{args.seed}/{args.condition}"
    p.verify_bundle(parent_run, protocol["parent_protocol_sha256"], "run", args.seed, args.condition)
    prepared = parent_root / "results/prepared"
    weights = sorted(parent_run.glob("*.joblib"))
    inputs = [prepared / "physical_channels.npy", prepared / "calibration_forecast.npz", prepared / "output_manifest.json",
              parent_run / "output_manifest.json", parent_run / "wind_bins.json", *weights,
              parent_root / "scripts/run_decision_information_development.py"]
    receipt = begin(args.output, args.protocol, inputs, {"stage": "historical", "seed": args.seed, "condition": args.condition})
    receipt["parent_prepared_manifest_sha256"] = sha(prepared / "output_manifest.json")
    data = np.load(prepared / "physical_channels.npy", mmap_mode="r")
    cond, task = old["conditions"][args.condition], old["task"]
    stage = p.load_stage(prepared, data, "calibration", cond, task["history_steps"], task["horizon_steps"])
    fit, select = split_calibration(stage["anchors"], protocol["stages"]["selection_first_anchor"],
                                    protocol["stages"]["evaluation_first_anchor"], 6, 1)
    receipt["coordinate_identity"] = array_identity({"anchors": stage["anchors"], "target_indices": stage["anchors"] + 6,
        "publication_indices": stage["anchors"] - 6, "node_ids": np.load(prepared / "node_ids.npy"),
        "forecast": stage["forecast"], "mask": stage["mask"], "shortfall": stage["shortfall"],
        "realized": stage["true"], "offset_fit_mask": fit, "selection_mask": select})
    probes = {name: joblib.load(parent_run / f"state_{name}.joblib") for name in ("pitch", "wind", "shuffle")}
    mats, scores = p.augment(stage, probes, data)
    raw, resources, timings = {}, {}, {}
    wind = stage["A"][:, 4 + task["history_steps"] - 1 - cond["delay_steps"]]
    bin_model = json.loads((parent_run / "wind_bins.json").read_text())
    for variant in protocol["variants"]:
        timer = time.monotonic()
        if variant == "WindBins":
            prediction = bins_predict(bin_model, wind)
            resource = [1, 0, 1]
            model_bytes = (parent_run / "wind_bins.json").stat().st_size
        else:
            model_path = parent_run / f"policy_{variant}.joblib"
            model = joblib.load(model_path)
            prediction = np.maximum(model.predict(mats[variant]), 0)
            extra = {"C_PitchScore": "pitch", "C_WindScore": "wind", "C_ShuffledScore": "shuffle", "E_Compressed": "pitch"}.get(variant)
            channels = (2 if cond["pitch_available"] else 1) if variant == "A_Wind" else (4 if cond["pitch_available"] else 3)
            width = int(model.n_features_in_) + (int(probes[extra].n_features_in_) if extra else 0)
            resource = [channels, 2 if extra else 1, width]
            model_bytes = model_path.stat().st_size + ((parent_run / f"state_{extra}.joblib").stat().st_size if extra else 0)
        raw[variant] = prediction.reshape(stage["shortfall"].shape).astype(np.float64)
        resources[variant] = {"order": resource, "serialized_model_bytes": model_bytes}
        timings[variant] = time.monotonic() - timer
    arrays, offsets = {}, []
    reference_count, reference_blocks, reference_identity = None, None, None
    fit_mask = stage["mask"][fit]
    for variant in protocol["variants"]:
        offset = offset_grid(stage["shortfall"][fit], raw[variant][fit], fit_mask, protocol["offset_quantiles"])
        offsets.append(offset)
        for qi, value in enumerate(offset):
            action = np.maximum(np.maximum(raw[variant][select], 0) + value, 0)
            totals = block_totals(stage["shortfall"][select], action, stage["mask"][select], stage["anchors"][select])
            if reference_count is None:
                reference_count, reference_blocks = totals["count"], totals["block_ids"]
            if not np.array_equal(reference_count, totals["count"]) or not np.array_equal(reference_blocks, totals["block_ids"]):
                raise ValueError("Historical candidate population changed")
            for name in ("loss_sum", "violation_sum", "reserve_sum", "shortage_sum"):
                arrays[f"{variant}__q{qi}__{name}"] = totals[name]
    np.savez_compressed(args.output / "raw_calibration_actions.npz", **raw)
    np.savez_compressed(args.output / "historical_grid.npz", offsets=np.asarray(offsets), counts=reference_count,
                        block_ids=reference_blocks, **arrays)
    np.savez_compressed(args.output / "historical_coordinates.npz", anchors=stage["anchors"], fit=fit, select=select,
                        target_indices=stage["anchors"] + 6, release_indices=stage["anchors"] + 7,
                        shortfall=stage["shortfall"], mask=stage["mask"], forecast=stage["forecast"])
    save(args.output / "resources.json", {"resources": resources, "policy_prediction_seconds": timings,
         "scope": "Calibration-batch predictions; teacher timings not isolated, not an end-to-end latency benchmark"})
    finish(args.output, receipt)
    print("HISTORICAL_COMPLETED", args.seed, args.condition, flush=True)


def load_grid(base: Path, protocol: dict[str, Any], protocol_hash: str, stage: str) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[Path]]:
    costs, risks, inputs = [], [], []
    reference_count, reference_blocks, reference_identity = None, None, None
    nq = len(protocol["offset_quantiles"])
    for condition in protocol["conditions"]:
        cc, rr = [], []
        for seed in protocol["seeds"]:
            path = base / f"seed{seed}" / condition
            producer = verify(path, protocol_hash, stage, seed, condition)
            if reference_identity is None:
                reference_identity = producer["coordinate_identity"]
            elif producer["coordinate_identity"] != reference_identity:
                raise ValueError("Grid coordinate/target/mask/forecast identity differs")
            archive_path = path / ("historical_grid.npz" if stage == "historical" else "evaluation_grid.npz")
            inputs.append(archive_path)
            with np.load(archive_path) as a:
                if reference_count is None:
                    reference_count, reference_blocks = a["counts"], a["block_ids"]
                if not np.array_equal(reference_count, a["counts"]) or not np.array_equal(reference_blocks, a["block_ids"]):
                    raise ValueError("Grid counts/blocks differ across seeds or conditions")
                cc.append([[a[f"{v}__q{q}__loss_sum"] for q in range(nq)] for v in protocol["variants"]])
                rr.append([[a[f"{v}__q{q}__violation_sum"] for q in range(nq)] for v in protocol["variants"]])
        costs.append(cc)
        risks.append(rr)
    if reference_count is None or not np.all(np.diff(reference_blocks) == 1):
        raise ValueError("Missing or discontinuous blocks")
    return np.asarray(costs), np.asarray(risks), reference_count, inputs


def weighted_draws(values: np.ndarray, counts: np.ndarray, weights: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    denominator = weights @ counts
    if np.any(denominator <= 0):
        raise ValueError("Empty resampled support; no redraw")
    point = values.sum(axis=-1) / counts.sum()
    draws = (weights @ values.reshape(-1, len(counts)).T) / denominator[:, None]
    return point, draws.reshape((len(weights),) + values.shape[:-1])


def choose(args: argparse.Namespace, protocol: dict[str, Any]) -> None:
    costs, risks, counts, inputs = load_grid(args.historical, protocol, sha(args.protocol), "historical")
    receipt = begin(args.output, args.protocol, inputs, {"stage": "choose"})
    cfg = protocol["inference"]
    w, identity = shared_block_draws(len(counts), cfg["n_boot"], cfg["primary_span_days"], cfg["rng_seed"])
    points, draws = weighted_draws(risks, counts, w)
    bounds = simultaneous_envelope(points.ravel(), draws.reshape(len(w), -1), protocol["task"]["alpha"])
    upper = np.clip(bounds["upper"].reshape(points.shape), 0, 1)
    mean_cost = costs.sum(axis=-1).mean(axis=1) / counts.sum()
    choices = {}
    for ci, condition in enumerate(protocol["conditions"]):
        choices[condition] = {}
        for vi, variant in enumerate(protocol["variants"]):
            qualified = np.flatnonzero(np.all(upper[ci, :, vi] <= .10, axis=0))
            qi = int(min(qualified, key=lambda q: (mean_cost[ci, vi, q], q))) if len(qualified) else len(protocol["offset_quantiles"]) - 1
            choices[condition][variant] = {"q_index": qi, "quantile": protocol["offset_quantiles"][qi],
                "historically_qualified": bool(len(qualified)), "selection_cost": mean_cost[ci, vi, qi],
                "all_seed_risk_upper": upper[ci, :, vi, qi].tolist(),
                "status": "FROZEN_HISTORICAL_CHOICE" if len(qualified) else "UNQUALIFIED_DIAGNOSTIC_FALLBACK"}
    save(args.output / "choices.json", {"choices": choices, "joint_critical": bounds["critical"],
         "shared_indices_sha256": identity, "seed": cfg["rng_seed"], "n_boot": cfg["n_boot"],
         "scope": "Frozen before evaluation stage execution, but development design used previously inspected test outcomes"})
    np.savez_compressed(args.output / "selection_bounds.npz", risk_point=points, risk_upper=upper, counts=counts)
    finish(args.output, receipt)
    print("CHOICES_FROZEN", flush=True)


def evaluate(args: argparse.Namespace, protocol: dict[str, Any]) -> None:
    choice_receipt = verify(args.choice, sha(args.protocol), "choose")
    hdir = args.historical / f"seed{args.seed}" / args.condition
    verify(hdir, sha(args.protocol), "historical", args.seed, args.condition)
    require_consumed_input(choice_receipt, hdir / "historical_grid.npz")
    p, parent_root, old = parent_runtime(protocol)
    parent_run = parent_root / f"results/runs/seed{args.seed}/{args.condition}"
    parent_receipt = p.verify_bundle(parent_run, protocol["parent_protocol_sha256"], "run", args.seed, args.condition)
    if parent_receipt["prepared_manifest_sha256"] != sha(parent_root / "results/prepared/output_manifest.json"):
        raise ValueError("Parent run belongs to another prepared bundle")
    inputs = [args.choice / "choices.json", args.choice / "manifest.json", hdir / "historical_grid.npz",
              hdir / "resources.json", parent_run / "evaluation_coordinates.npz", parent_run / "evaluation_actions.npz",
              parent_run / "output_manifest.json"]
    receipt = begin(args.output, args.protocol, inputs, {"stage": "evaluate", "seed": args.seed, "condition": args.condition})
    decision = json.loads((args.choice / "choices.json").read_text())["choices"][args.condition]
    with np.load(hdir / "historical_grid.npz") as a:
        offsets = a["offsets"]
    arrays, actions, rows = {}, {}, []
    exact_checks = 0
    with np.load(parent_run / "evaluation_coordinates.npz") as coordinates, np.load(parent_run / "evaluation_actions.npz") as original:
        anchors, mask, shortfall = coordinates["anchors"], coordinates["mask"], coordinates["shortfall"]
        if anchors[0] != protocol["stages"]["evaluation_first_anchor"] or not np.array_equal(coordinates["target_indices"], anchors + 6):
            raise ValueError("Evaluation target/issue changed")
        receipt["coordinate_identity"] = array_identity({key: coordinates[key] for key in (
            "anchors", "target_indices", "publication_indices", "node_ids", "forecast", "realized", "shortfall", "mask")})
        for vi, variant in enumerate(protocol["variants"]):
            raw = original[variant + "_raw"]
            if raw.dtype != np.float64:
                raise ValueError("Original raw action is not float64")
            for qi, offset in enumerate(offsets[vi]):
                action = np.maximum(np.maximum(raw, 0) + offset, 0)
                totals = block_totals(shortfall, action, mask, anchors)
                for name, value in totals.items():
                    if name not in ("count", "block_ids"):
                        arrays[f"{variant}__q{qi}__{name}"] = value
                rows.append({"variant": variant, "quantile": protocol["offset_quantiles"][qi], "q_index": qi,
                             "mean_loss": totals["loss_sum"].sum() / totals["count"].sum(),
                             "violation": totals["violation_sum"].sum() / totals["count"].sum(),
                             "selected": qi == decision[variant]["q_index"]})
                if qi == decision[variant]["q_index"]:
                    actions[variant] = action
        np.savez_compressed(args.output / "selected_actions.npz", **actions)
        np.savez_compressed(args.output / "evaluation_grid.npz", offsets=offsets, counts=totals["count"], block_ids=totals["block_ids"], **arrays)
        with np.load(args.output / "selected_actions.npz") as stored, np.load(args.output / "evaluation_grid.npz") as grid:
            for variant in protocol["variants"]:
                result = block_totals(shortfall, stored[variant], mask, anchors)
                qi = decision[variant]["q_index"]
                for name, value in result.items():
                    expected = grid["counts" if name == "count" else "block_ids"] if name in ("count", "block_ids") else grid[f"{variant}__q{qi}__{name}"]
                    if not np.array_equal(value, expected):
                        raise ValueError("Stored selected-action accounting failed")
                    exact_checks += 1
    shutil.copyfile(hdir / "resources.json", args.output / "resources.json")
    save(args.output / "grid_metrics.json", {"seed": args.seed, "condition": args.condition, "rows": rows,
         "exact_selected_action_array_checks": exact_checks, "choices_sha256": sha(args.choice / "choices.json")})
    finish(args.output, receipt)
    print("EVALUATED_EXACT", args.seed, args.condition, exact_checks, flush=True)


def aggregate(args: argparse.Namespace, protocol: dict[str, Any]) -> None:
    verify(args.choice, sha(args.protocol), "choose")
    for condition in protocol["conditions"]:
        for seed in protocol["seeds"]:
            producer = verify(args.runs / f"seed{seed}" / condition, sha(args.protocol), "evaluate", seed, condition)
            require_consumed_input(producer, args.choice / "choices.json")
    costs, risks, counts, inputs = load_grid(args.runs, protocol, sha(args.protocol), "evaluate")
    inputs.extend([args.choice / "choices.json", args.choice / "manifest.json"])
    receipt = begin(args.output, args.protocol, inputs, {"stage": "aggregate"})
    chosen = json.loads((args.choice / "choices.json").read_text())["choices"]
    nc, ns, nk, nq, nb = costs.shape
    selected_cost, selected_risk = np.zeros((nc, ns, nk, nb)), np.zeros((nc, ns, nk, nb))
    for ci, condition in enumerate(protocol["conditions"]):
        for vi, variant in enumerate(protocol["variants"]):
            qi = chosen[condition][variant]["q_index"]
            selected_cost[ci, :, vi] = costs[ci, :, vi, qi]
            selected_risk[ci, :, vi] = risks[ci, :, vi, qi]
    outputs = []
    cfg = protocol["inference"]
    for span in [cfg["primary_span_days"], *cfg["sensitivity_spans_days"]]:
        weights, identity = shared_block_draws(nb, cfg["n_boot"], span, cfg["rng_seed"])
        cp, cd = weighted_draws(selected_cost.mean(axis=1), counts, weights)
        rp, rd = weighted_draws(selected_risk, counts, weights)
        if np.any(cp <= 0) or np.any(cd <= 0):
            raise ValueError("Nonpositive cost cannot define relative near-optimality")
        ratios = cp[:, :, None] / cp[:, None, :] - 1
        ratio_draws = cd[:, :, :, None] / cd[:, :, None, :] - 1
        point = np.concatenate((rp.ravel(), ratios.ravel()))
        draws = np.column_stack((rd.reshape(len(weights), -1), ratio_draws.reshape(len(weights), -1)))
        exact = np.concatenate((np.zeros(rp.size, bool), np.broadcast_to(np.eye(nk, dtype=bool), ratios.shape).ravel()))
        bound = simultaneous_envelope(point, draws, .05, exact)
        lower = np.clip(bound["lower"][:rp.size].reshape(rp.shape), 0, 1)
        upper = np.clip(bound["upper"][:rp.size].reshape(rp.shape), 0, 1)
        regret = bound["upper"][rp.size:].reshape(ratios.shape)
        cases = {}
        for ci, condition in enumerate(protocol["conditions"]):
            resource_rows = []
            for seed in protocol["seeds"]:
                rr = json.loads((args.runs / f"seed{seed}" / condition / "resources.json").read_text())["resources"]
                resource_rows.append([rr[v]["order"] for v in protocol["variants"]])
            if any(row != resource_rows[0] for row in resource_rows[1:]):
                raise ValueError("Resource-order dimensions changed across instances")
            historical_pass = [chosen[condition][v]["historically_qualified"] for v in protocol["variants"]]
            curve = [near_optimal_set(lower[ci], upper[ci], regret[ci], historical_pass, resource_rows[0], eps)
                     for eps in cfg["epsilon_curve"]]
            cases[condition] = {"variants": protocol["variants"], "mean_cost": cp[ci], "risk_point_per_seed": rp[ci],
                                "risk_lower_per_seed": lower[ci], "risk_upper_per_seed": upper[ci],
                                "relative_regret_upper": regret[ci], "historically_qualified": historical_pass,
                                "resources": resource_rows[0], "epsilon_curve": curve}
        outputs.append({"span": span, "role": "primary" if span == cfg["primary_span_days"] else "sensitivity",
                        "critical": bound["critical"], "draw_indices_sha256": identity, "cases": cases})
    save(args.output / "frontier_results.json", {"status": "COMPLETED_RETROSPECTIVE_DEVELOPMENT",
         "scope": "Seven historically generated candidates, conditional on frozen instances; not independent confirmation",
         "unbounded_json": "null denotes an unbounded unidentified confidence coordinate",
         "all_seed_risk_required": True, "deployment_certified": False, "E07_activated": False,
         "results": outputs})
    finish(args.output, receipt)
    print("FRONTIER_AGGREGATED", nc, ns, nk, flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=["historical", "choose", "evaluate", "aggregate"])
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--historical", type=Path)
    parser.add_argument("--choice", type=Path)
    parser.add_argument("--runs", type=Path)
    parser.add_argument("--seed", type=int, default=201)
    parser.add_argument("--condition", default="pitch_withheld")
    args = parser.parse_args()
    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    if protocol["task"] != {"horizon_steps": 6, "target_release_delay_steps": 1, "rho": 10., "dt_hours": 1 / 6, "nominal_cost_quantile": .9, "v_max": .1, "alpha": .05}:
        raise ValueError("Unsupported task parameters")
    if args.seed not in protocol["seeds"] or args.condition not in protocol["conditions"]:
        raise ValueError("Unregistered worker identity")
    with threadpool_limits(limits=2):
        {"historical": historical, "choose": choose, "evaluate": evaluate, "aggregate": aggregate}[args.stage](args, protocol)


if __name__ == "__main__":
    main()
