from __future__ import annotations
import json
from pathlib import Path
import numpy as np

ALPHA = 0.05
EPS_C = 0.0
EPS_V = 0.0
V_MAX = 0.10
N_BOOT = 20000
SEED = 20261017
POLICIES = ["B", "C", "D", "D10"]
COMPLEXITY = {"B": 0, "C": 1, "D": 2, "D10": 3}


def load_arrays(root: Path):
    rows = []
    for seed in [201, 202, 203, 204, 205]:
        z = np.load(root / f"seed{seed}_full_policy_day_blocks.npz")
        rows.append({"seed": seed, **{k: np.asarray(z[k], dtype=float) for k in z.files}})
    return rows


def bootstrap(rows, rng):
    # Joint seed x daily-block resampling. Each selected seed contributes a
    # resampled set of 35 blocks; cells are never treated as independent.
    ns = len(rows)
    nb = len(rows[0]["n"])
    out = {p: {"dc": np.empty(N_BOOT), "dv": np.empty(N_BOOT), "va": np.empty(N_BOOT)} for p in POLICIES}
    for b in range(N_BOOT):
        selected = rng.integers(0, ns, size=ns)
        totals = {p: [0.0, 0.0, 0.0] for p in POLICIES}  # cost, violation count, n
        base = [0.0, 0.0, 0.0]
        for idx in selected:
            r = rows[idx]
            block_idx = rng.integers(0, nb, size=nb)
            n = r["n"][block_idx].sum()
            base[0] += r["B_cost"][block_idx].sum()
            base[1] += r["B_viol"][block_idx].sum()
            base[2] += n
            for p in POLICIES:
                totals[p][0] += r[f"{p}_cost"][block_idx].sum()
                totals[p][1] += r[f"{p}_viol"][block_idx].sum()
                totals[p][2] += n
        vb = base[1] / base[2]
        for p in POLICIES:
            vp = totals[p][1] / totals[p][2]
            out[p]["dc"][b] = totals[p][0] - base[0]
            out[p]["dv"][b] = vp - vb
            out[p]["va"][b] = vp
    return out


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    rows = load_arrays(args.root)
    rng = np.random.default_rng(SEED)
    boot = bootstrap(rows, rng)
    result = {
        "protocol": {
            "alpha": ALPHA, "epsilon_C_kwh": EPS_C, "epsilon_V": EPS_V,
            "v_max": V_MAX, "n_boot": N_BOOT, "seed": SEED,
            "unit": "5 training seeds x 35 daily blocks, joint resampling",
            "complexity_order": POLICIES,
            "primary_population": "Full",
        },
        "policies": {},
    }
    feasible = []
    for p in POLICIES:
        dc = boot[p]["dc"]
        dv = boot[p]["dv"]
        va = boot[p]["va"]
        stats = {
            "cost_delta_point_kwh": float(np.mean(dc)),
            "cost_delta_ucb95_kwh": float(np.quantile(dc, 1 - ALPHA)),
            "violation_delta_point": float(np.mean(dv)),
            "violation_delta_ucb95": float(np.quantile(dv, 1 - ALPHA)),
            "absolute_violation_point": float(np.mean(va)),
            "absolute_violation_ucb95": float(np.quantile(va, 1 - ALPHA)),
        }
        stats["feasible"] = bool(
            stats["cost_delta_ucb95_kwh"] <= EPS_C
            and stats["violation_delta_ucb95"] <= EPS_V
            and stats["absolute_violation_ucb95"] <= V_MAX
        )
        result["policies"][p] = stats
        if stats["feasible"]:
            feasible.append(p)
    result["selection"] = {
        "status": "SELECTED" if feasible else "NO FEASIBLE POLICY",
        "selected_policy": min(feasible, key=lambda p: COMPLEXITY[p]) if feasible else None,
        "feasible_policies": feasible,
        "stability_rule": "selection frequency >= 0.80; frequency not estimated in this aggregate selector",
        "note": "No test-time threshold, baseline, candidate set, or complexity order was changed after observing outcomes.",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
