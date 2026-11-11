from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

ALPHA = 0.05
EPS_C = 0.0
EPS_V = 0.0
V_MAX = 0.10
N_BOOT = 10_000
STABILITY_SEED = 20261018
SEEDS = (201, 202, 203, 204, 205)
POLICIES = ("B", "C", "D", "D10")
COMPLEXITY = {"B": 0, "C": 1, "D": 2, "D10": 3}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_rows(root: Path) -> list[dict[str, np.ndarray | int]]:
    rows = []
    for seed in SEEDS:
        path = root / f"seed{seed}_full_policy_day_blocks.npz"
        with np.load(path) as archive:
            row = {"seed": seed, **{key: np.asarray(archive[key], dtype=float) for key in archive.files}}
        required = {"n", "B_cost", "B_viol"} | {f"{policy}_{metric}" for policy in POLICIES for metric in ("cost", "viol")}
        missing = sorted(required.difference(row))
        if missing:
            raise ValueError(f"seed {seed} missing required arrays: {missing}")
        block_lengths = {key: int(np.asarray(value).shape[0]) for key, value in row.items() if key != "seed"}
        if set(block_lengths.values()) != {35}:
            raise ValueError(f"seed {seed} must contain exactly 35 aligned daily blocks: {block_lengths}")
        rows.append(row)
    if len(rows) != 5:
        raise ValueError(f"expected five seed arrays, found {len(rows)}")
    if any(int(np.asarray(rows[0][key]).shape[0]) != int(np.asarray(row[key]).shape[0]) for row in rows[1:] for key in rows[0] if key != "seed"):
        raise ValueError("seed arrays do not have equal block lengths")
    return rows


def draw_aggregate(rows: list[dict[str, np.ndarray | int]], rng: np.random.Generator) -> dict[str, dict[str, float]]:
    n_seed = len(rows)
    n_block = len(rows[0]["n"])
    selected_seed_indices = rng.integers(0, n_seed, size=n_seed)
    totals = {policy: {"cost": 0.0, "viol": 0.0} for policy in POLICIES}
    baseline = {"cost": 0.0, "viol": 0.0}
    total_n = 0.0

    for seed_index in selected_seed_indices:
        row = rows[int(seed_index)]
        block_indices = rng.integers(0, n_block, size=n_block)
        total_n += float(np.asarray(row["n"])[block_indices].sum())
        baseline["cost"] += float(np.asarray(row["B_cost"])[block_indices].sum())
        baseline["viol"] += float(np.asarray(row["B_viol"])[block_indices].sum())
        for policy in POLICIES:
            totals[policy]["cost"] += float(np.asarray(row[f"{policy}_cost"])[block_indices].sum())
            totals[policy]["viol"] += float(np.asarray(row[f"{policy}_viol"])[block_indices].sum())

    baseline_violation = baseline["viol"] / total_n
    result: dict[str, dict[str, float]] = {}
    for policy in POLICIES:
        violation = totals[policy]["viol"] / total_n
        result[policy] = {
            "cost_delta_kwh": totals[policy]["cost"] - baseline["cost"],
            "violation_delta": violation - baseline_violation,
            "absolute_violation": violation,
        }
    return result


def is_feasible(metrics: dict[str, float]) -> bool:
    return (
        metrics["cost_delta_kwh"] <= EPS_C
        and metrics["violation_delta"] <= EPS_V
        and metrics["absolute_violation"] <= V_MAX
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Estimate E04 selector stability on frozen policy block arrays.")
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--preregistration", type=Path, required=True)
    parser.add_argument("--primary-result", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-csv", type=Path, required=True)
    args = parser.parse_args()

    input_root = args.input_root.resolve()
    preregistration = args.preregistration.resolve()
    primary_result = args.primary_result.resolve()
    rows = load_rows(input_root)

    input_files = {}
    for seed in SEEDS:
        path = input_root / f"seed{seed}_full_policy_day_blocks.npz"
        input_files[path.name] = {
            "path": str(path),
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }

    rng = np.random.default_rng(STABILITY_SEED)
    feasible_counts = {policy: 0 for policy in POLICIES}
    first_selection_counts = {policy: 0 for policy in POLICIES}
    no_feasible_count = 0
    all_draws = []

    for draw_id in range(N_BOOT):
        metrics = draw_aggregate(rows, rng)
        feasible = [policy for policy in POLICIES if is_feasible(metrics[policy])]
        first = min(feasible, key=lambda policy: COMPLEXITY[policy]) if feasible else None
        for policy in feasible:
            feasible_counts[policy] += 1
        if first is None:
            no_feasible_count += 1
        else:
            first_selection_counts[first] += 1
        all_draws.append({
            "draw": draw_id,
            "feasible_policies": feasible,
            "first_selected_policy": first,
            **{policy: metrics[policy] for policy in POLICIES},
        })

    def frequency(count: int) -> float:
        return count / N_BOOT

    def mc_se(value: float) -> float:
        return float(np.sqrt(value * (1.0 - value) / N_BOOT))

    summary_rows = []
    for policy in POLICIES:
        feasible_frequency = frequency(feasible_counts[policy])
        first_frequency = frequency(first_selection_counts[policy])
        summary_rows.append({
            "policy": policy,
            "complexity_rank": COMPLEXITY[policy],
            "feasible_count": feasible_counts[policy],
            "feasible_frequency": feasible_frequency,
            "feasible_frequency_mc_se": mc_se(feasible_frequency),
            "first_selected_count": first_selection_counts[policy],
            "first_selected_frequency": first_frequency,
            "first_selected_frequency_mc_se": mc_se(first_frequency),
            "n_boot": N_BOOT,
            "stability_seed": STABILITY_SEED,
        })

    no_feasible_frequency = frequency(no_feasible_count)
    result = {
        "experiment": "E05",
        "status": "CONDITIONAL_DIAGNOSTIC",
        "question": "How often does the frozen E04 risk-constrained selector produce a feasible policy under the registered joint seed/block resampling rule?",
        "protocol": {
            "alpha": ALPHA,
            "epsilon_C_kwh": EPS_C,
            "epsilon_V": EPS_V,
            "v_max": V_MAX,
            "n_boot": N_BOOT,
            "stability_seed": STABILITY_SEED,
            "unit": "5 training seeds x 35 daily blocks, joint resampling",
            "candidate_policies": list(POLICIES),
            "complexity_order": list(POLICIES),
            "population": "WTB Full",
            "primary_selector_unchanged": True,
            "frequency_used_to_modify_primary_selection": False,
        },
        "input_binding": {
            "input_root": str(input_root),
            "preregistration": {
                "path": str(preregistration),
                "bytes": preregistration.stat().st_size,
                "sha256": sha256_file(preregistration),
            },
            "primary_result": {
                "path": str(primary_result),
                "bytes": primary_result.stat().st_size,
                "sha256": sha256_file(primary_result),
            },
            "policy_arrays": input_files,
            "execution_receipt_available_for_input_arrays": False,
            "limitation": "Diagnostic is conditional on the frozen local v4 arrays; it does not repair the missing original replay receipt.",
        },
        "summary": {
            "no_feasible_count": no_feasible_count,
            "no_feasible_frequency": no_feasible_frequency,
            "no_feasible_frequency_mc_se": mc_se(no_feasible_frequency),
            "feasible_frequency": {policy: frequency(feasible_counts[policy]) for policy in POLICIES},
            "first_selected_frequency": {policy: frequency(first_selection_counts[policy]) for policy in POLICIES},
            "sum_first_selected_frequency": sum(frequency(first_selection_counts[policy]) for policy in POLICIES),
            "stability_rule_threshold": 0.80,
            "stability_rule_status": "UNSTABLE SELECTION" if any(
                frequency(first_selection_counts[policy]) < 0.80 for policy in POLICIES
            ) else "STABLE SELECTION",
        },
        "rows": summary_rows,
        "primary_result_preserved": {
            "path": str(primary_result),
            "status": "NO FEASIBLE POLICY preserved from E04 primary result",
        },
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    csv_lines = [
        "policy,complexity_rank,feasible_count,feasible_frequency,feasible_frequency_mc_se,first_selected_count,first_selected_frequency,first_selected_frequency_mc_se,n_boot,stability_seed"
    ]
    for row in summary_rows:
        csv_lines.append(",".join(str(row[key]) for key in (
            "policy", "complexity_rank", "feasible_count", "feasible_frequency",
            "feasible_frequency_mc_se", "first_selected_count", "first_selected_frequency",
            "first_selected_frequency_mc_se", "n_boot", "stability_seed"
        )))
    args.output_csv.write_text("\n".join(csv_lines) + "\n", encoding="utf-8")

    print(json.dumps({"output_json": str(args.output_json), "output_csv": str(args.output_csv), "summary": result["summary"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
