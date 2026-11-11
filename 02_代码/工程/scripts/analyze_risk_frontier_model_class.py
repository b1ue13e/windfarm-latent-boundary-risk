"""Result-informed secondary audit of the existing complete finite action grid."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import importlib.metadata
import json
import os
from repo_paths import Path, repository_root
import platform
import shutil
import sys

import numpy as np
from threadpoolctl import threadpool_limits

ROOT = Path(repository_root())
sys.path.insert(0, str(ROOT))
from windfarm_moe.risk_frontier import shared_block_draws, simultaneous_envelope, near_optimal_set


def flatten_grid(values: np.ndarray) -> np.ndarray:
    a = np.asarray(values)
    if a.ndim != 5:
        raise ValueError("Expected condition/seed/model/level/block array")
    c, s, k, q, b = a.shape
    return a.reshape(c, s, k * q, b)


def exact_ratios(offsets: np.ndarray) -> np.ndarray:
    """A common model and identical frozen offsets imply the same function."""
    a = np.asarray(offsets, dtype=np.float64)
    if a.ndim != 4 or not np.isfinite(a).all():
        raise ValueError("Expected condition/seed/model/level offsets")
    c, s, k, q = a.shape
    result = np.zeros((c, k * q, k * q), bool)
    for m in range(k):
        for x in range(q):
            for y in range(q):
                result[:, m * q + x, m * q + y] = np.all(a[:, :, m, x] == a[:, :, m, y], axis=1)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    cfg = json.loads(args.protocol.read_text())
    parent = Path(cfg["parent_root"])
    spec = importlib.util.spec_from_file_location("frozen_frontier_grid_runtime", parent / "scripts/run_risk_cost_frontier.py")
    if spec is None or spec.loader is None:
        raise ValueError("Cannot import frozen grid reader")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if module.sha(parent / "compact_evidence.tar.gz") != cfg["parent_archive_sha256"]:
        raise ValueError("Parent full-grid evidence mismatch")
    pp = parent / "experiments/risk_cost_frontier_development_20261018/protocol.json"
    original = json.loads(pp.read_text())
    for key in ("conditions", "seeds", "variants", "offset_quantiles"):
        if original[key] != cfg[key]:
            raise ValueError("Secondary audit cannot change the action grid")
    if any(original["task"][key] != cfg[key] for key in ("rho", "v_max", "alpha")) or original["task"]["nominal_cost_quantile"] != cfg["nominal_cost_quantile"]:
        raise ValueError("Secondary audit cannot change costs or risk thresholds")
    costs, risks, counts, inputs = module.load_grid(parent / "results/evaluate", original, module.sha(pp), "evaluate")
    offsets, resource_orders = [], []
    for condition in cfg["conditions"]:
        cc = []
        for seed in cfg["seeds"]:
            f = parent / f"results/historical/seed{seed}/{condition}/historical_grid.npz"
            inputs.append(f)
            with np.load(f) as a:
                cc.append(a["offsets"])
        offsets.append(cc)
        resource_path = parent / f"results/evaluate/seed201/{condition}/resources.json"
        inputs.append(resource_path)
        resources = json.loads(resource_path.read_text())["resources"]
        resource_orders.append([resources[v]["order"] for v in cfg["variants"] for q in cfg["offset_quantiles"]])
    proof = exact_ratios(np.asarray(offsets))
    costs, risks = flatten_grid(costs), flatten_grid(risks)
    nc, ns, nk, nb = costs.shape
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "source").mkdir()
    sources = [Path(__file__), ROOT / "windfarm_moe/risk_frontier.py", args.protocol, parent / "scripts/run_risk_cost_frontier.py"]
    for p in sources:
        shutil.copyfile(p, args.output / "source" / p.name)
    inputs += [pp, parent / "compact_evidence.tar.gz"]
    receipt = {"status": "RUNNING_SECONDARY_DEVELOPMENT", "started_utc": datetime.now(timezone.utc).isoformat(),
               "source_sha256": {str(p): module.sha(p) for p in sources}, "input_sha256": {str(p): module.sha(p) for p in inputs},
               "argv": sys.argv, "python": sys.version, "numpy": np.__version__, "host": platform.node(),
               "torch_installed": importlib.metadata.version("torch"), "platform": platform.platform(),
               "pbs_job_id": os.environ.get("PBS_JOBID"), "rng_seed": cfg["rng_seed"],
               "scope": cfg["scope"], "compute": "CPU postprocessing only; no CUDA or model refit"}
    module.save(args.output / "receipt.json", receipt)
    results = []
    for span in [cfg["primary_span_days"], *cfg["sensitivity_spans_days"]]:
        weights, identity = shared_block_draws(nb, cfg["n_boot"], span, cfg["rng_seed"])
        cp, cd = module.weighted_draws(costs.mean(axis=1), counts, weights)
        rp, rd = module.weighted_draws(risks, counts, weights)
        if np.any(cp <= 0) or np.any(cd <= 0):
            raise ValueError("Relative cost undefined")
        ratio = cp[:, :, None] / cp[:, None, :] - 1
        dratio = cd[:, :, :, None] / cd[:, :, None, :] - 1
        exact = np.concatenate((np.zeros(rp.size, bool), proof.ravel()))
        point = np.concatenate((rp.ravel(), ratio.ravel()))
        draws = np.column_stack((rd.reshape(len(weights), -1), dratio.reshape(len(weights), -1)))
        bounds = simultaneous_envelope(point, draws, cfg["alpha"], exact)
        lo = np.clip(bounds["lower"][:rp.size].reshape(rp.shape), 0, 1)
        hi = np.clip(bounds["upper"][:rp.size].reshape(rp.shape), 0, 1)
        regret = bounds["upper"][rp.size:].reshape(ratio.shape)
        cases = {}
        labels = [f"{v}@{q:.3f}" for v in cfg["variants"] for q in cfg["offset_quantiles"]]
        for ci, condition in enumerate(cfg["conditions"]):
            curve = [near_optimal_set(lo[ci], hi[ci], regret[ci], np.ones(nk, bool), resource_orders[ci], e, cfg["v_max"])
                     for e in cfg["epsilon_curve"]]
            cases[condition] = {"policies": labels, "mean_cost": cp[ci], "risk_point_per_seed": rp[ci],
                                "risk_lower_per_seed": lo[ci], "risk_upper_per_seed": hi[ci],
                                "relative_regret_upper": regret[ci], "epsilon_curve": curve,
                                "resource_order": resource_orders[ci]}
        results.append({"span": span, "critical": bounds["critical"], "shared_draws_sha256": identity, "cases": cases})
        print("AUDITED_ALL_GRID_SPAN", span, flush=True)
        del draws, dratio, rd, cd, bounds
    module.save(args.output / "model_class_results.json", {"status": cfg["status"], "scope": cfg["scope"],
                "coordinate_family_size": int(nc * (ns * nk + nk * nk)), "results": results,
                "unbounded_json": "null means unbounded/unidentified", "deployment_certified": False,
                "primary_historical_recipe_unchanged": True})
    module.finish(args.output, receipt)
    print("SECONDARY_GRID_AUDIT_COMPLETED", flush=True)


if __name__ == "__main__":
    with threadpool_limits(limits=2):
        main()
