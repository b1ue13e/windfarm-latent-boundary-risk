from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from e04_provenance import provenance_for_selector, verify_e04_receipt

ALPHA = 0.05
EPS_C = 0.0
EPS_V = 0.0
V_MAX = 0.10
N_PRIMARY_BOOT = 20_000
N_STABILITY_BOOT = 10_000
BOOT_SEED = 20261017
POLICIES = ["B", "C", "D", "D10"]
COMPLEXITY = {"B": 0, "C": 1, "D": 2, "D10": 3}


def load_rows(root: Path):
    return [
        {"seed": seed, **{k: np.asarray(np.load(root / f"seed{seed}_full_policy_day_blocks.npz")[k], dtype=float) for k in np.load(root / f"seed{seed}_full_policy_day_blocks.npz").files}}
        for seed in (201, 202, 203, 204, 205)
    ]


def draw_aggregate(rows, rng):
    n_seed = len(rows)
    n_block = len(rows[0]["n"])
    chosen_seed = rng.integers(0, n_seed, size=n_seed)
    totals = {p: {"cost": 0.0, "viol": 0.0} for p in POLICIES}
    base = {"cost": 0.0, "viol": 0.0}
    total_n = 0.0
    for idx in chosen_seed:
        row = rows[idx]
        blocks = rng.integers(0, n_block, size=n_block)
        total_n += row["n"][blocks].sum()
        base["cost"] += row["B_cost"][blocks].sum()
        base["viol"] += row["B_viol"][blocks].sum()
        for policy in POLICIES:
            totals[policy]["cost"] += row[f"{policy}_cost"][blocks].sum()
            totals[policy]["viol"] += row[f"{policy}_viol"][blocks].sum()
    base_v = base["viol"] / total_n
    result = {}
    for policy in POLICIES:
        v = totals[policy]["viol"] / total_n
        result[policy] = {
            "cost_delta": totals[policy]["cost"] - base["cost"],
            "violation_delta": v - base_v,
            "absolute_violation": v,
        }
    return result


def primary_ucb(rows, rng):
    draws = {p: {"cost": np.empty(N_PRIMARY_BOOT), "dv": np.empty(N_PRIMARY_BOOT), "v": np.empty(N_PRIMARY_BOOT)} for p in POLICIES}
    for i in range(N_PRIMARY_BOOT):
        one = draw_aggregate(rows, rng)
        for p in POLICIES:
            draws[p]["cost"][i] = one[p]["cost_delta"]
            draws[p]["dv"][i] = one[p]["violation_delta"]
            draws[p]["v"][i] = one[p]["absolute_violation"]
    return draws


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--preregistration", type=Path, required=True)
    args = parser.parse_args()

    expected_outputs = [f"seed{seed}_full_policy_day_blocks.npz" for seed in (201, 202, 203, 204, 205)]
    verified = verify_e04_receipt(
        args.receipt,
        preregistration=args.preregistration,
        expected_output_names=expected_outputs,
    )
    if Path(verified["bundle_root"]).resolve() != args.root.resolve():
        raise ValueError("E04 receipt bundle does not match selector root")
    rows = load_rows(args.root)
    primary_rng = np.random.default_rng(BOOT_SEED)
    primary = primary_ucb(rows, primary_rng)

    policy_stats = {}
    feasible = []
    for p in POLICIES:
        cost = primary[p]["cost"]
        dv = primary[p]["dv"]
        v = primary[p]["v"]
        stats = {
            "cost_delta_point_kwh": float(cost.mean()),
            "cost_delta_ucb95_kwh": float(np.quantile(cost, 1 - ALPHA)),
            "violation_delta_point": float(dv.mean()),
            "violation_delta_ucb95": float(np.quantile(dv, 1 - ALPHA)),
            "absolute_violation_point": float(v.mean()),
            "absolute_violation_ucb95": float(np.quantile(v, 1 - ALPHA)),
        }
        stats["feasible"] = bool(
            stats["cost_delta_ucb95_kwh"] <= EPS_C
            and stats["violation_delta_ucb95"] <= EPS_V
            and stats["absolute_violation_ucb95"] <= V_MAX
        )
        policy_stats[p] = stats
        if stats["feasible"]:
            feasible.append(p)

    stability_rng = np.random.default_rng(BOOT_SEED + 1)
    stability_counts = {p: 0 for p in POLICIES}
    stability_none = 0
    for _ in range(N_STABILITY_BOOT):
        one = draw_aggregate(rows, stability_rng)
        selected = None
        for p in POLICIES:
            if one[p]["cost_delta"] <= EPS_C and one[p]["violation_delta"] <= EPS_V and one[p]["absolute_violation"] <= V_MAX:
                selected = p
                break
        if selected is None:
            stability_none += 1
        else:
            stability_counts[selected] += 1

    result = {
        "protocol": {
            "version": "E04-v2",
            "alpha": ALPHA,
            "epsilon_C_kwh": EPS_C,
            "epsilon_V": EPS_V,
            "v_max": V_MAX,
            "n_primary_boot": N_PRIMARY_BOOT,
            "n_stability_boot": N_STABILITY_BOOT,
            "primary_seed": BOOT_SEED,
            "stability_seed": BOOT_SEED + 1,
            "unit": "5 training seeds x 35 daily blocks, joint resampling",
            "complexity_order": POLICIES,
            "primary_population": "Full",
            "stability_is_diagnostic": True,
        },
        "policies": policy_stats,
        "selection": {
            "status": "SELECTED" if feasible else "NO FEASIBLE POLICY",
            "selected_policy": min(feasible, key=lambda p: COMPLEXITY[p]) if feasible else None,
            "feasible_policies": feasible,
            "no_feasible_frequency": stability_none / N_STABILITY_BOOT,
            "selection_frequency": {p: stability_counts[p] / N_STABILITY_BOOT for p in POLICIES},
            "note": "Stability frequencies are diagnostic; thresholds, candidates, baseline, and complexity order were immutable in E04-v2 preregistration.",
        },
    }
    result["provenance"] = provenance_for_selector(verified, Path(__file__))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
