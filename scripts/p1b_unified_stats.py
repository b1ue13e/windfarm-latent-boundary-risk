"""P1b: hierarchical week-block bootstrap and unified mechanism-control statistics
table with exact Bonferroni (99.615% CI for m=13) multiplicity control."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(".")


def hierarchical_block_bootstrap() -> dict:
    daily = pd.read_csv(
        ROOT / "artifacts" / "decision_reserve_trainweight_allclean_20260830" / "reserve_decision_daily_costs.csv"
    )
    out = {}
    out_dir = ROOT / "artifacts" / "p1_stats_20260904"
    out_dir.mkdir(parents=True, exist_ok=True)

    for model in ["Boundary-forced router", "Physics-Aligned MoE"]:
        sub = daily[(daily["model"] == model) & (daily["cost_ratio"] == 10.0)]
        seeds = sorted(sub["seed"].unique())
        diffs = []
        for seed in seeds:
            s = sub[sub["seed"] == seed]
            gate = s[s["policy"] == "gate-bin"].sort_values("day")["daily_cost"].to_numpy()
            glob = s[s["policy"] == "global"].sort_values("day")["daily_cost"].to_numpy()
            n = min(len(gate), len(glob))
            diffs.append(gate[:n] - glob[:n])
        min_days = min(len(d) for d in diffs)
        block = 7
        n_blocks = min_days // block
        # Shape: (n_seeds, n_blocks)
        blocks = np.stack([d[: min_days][: n_blocks * block].reshape(n_blocks, block).sum(axis=1) for d in diffs])
        n_seeds = len(diffs)

        observed_per_seed = blocks.sum(axis=1)
        observed_mean_over_seeds = float(observed_per_seed.mean())

        # Hierarchical bootstrap:
        # Outer loop: resample seeds with replacement
        # Inner loop: resample weekly blocks with replacement within each selected seed
        rng = np.random.default_rng(20260904)
        n_boot = 50000
        boot_hier = np.empty(n_boot, dtype=np.float64)
        for b in range(n_boot):
            sampled_seed_indices = rng.integers(0, n_seeds, size=n_seeds)
            seed_totals = [
                rng.choice(blocks[idx], size=n_blocks, replace=True).sum()
                for idx in sampled_seed_indices
            ]
            boot_hier[b] = np.mean(seed_totals)

        # Within-seed block bootstrap (conditioned on observed seeds)
        boot_within = np.zeros(n_boot, dtype=np.float64)
        for i in range(n_seeds):
            boot_within += rng.choice(blocks[i], size=(n_boot, n_blocks), replace=True).sum(axis=1) / float(n_seeds)

        out[model] = {
            "n_seeds": int(n_seeds),
            "n_days_per_seed": int(min_days),
            "observed_delta_mean_per_seed": observed_mean_over_seeds,
            "hierarchical_week_block_ci_low": float(np.percentile(boot_hier, 2.5)),
            "hierarchical_week_block_ci_high": float(np.percentile(boot_hier, 97.5)),
            "within_seed_week_block_ci_low": float(np.percentile(boot_within, 2.5)),
            "within_seed_week_block_ci_high": float(np.percentile(boot_within, 97.5)),
        }

    with open(out_dir / "pooled_time_block_bootstrap.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(json.dumps(out, indent=2))
    return out


def unified_control_table() -> pd.DataFrame:
    base = ROOT / "artifacts" / "breakthrough_20260904"
    out_dir = ROOT / "artifacts" / "p1_stats_20260904"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Gather data for all 13 controls
    # 1. Soft-rule contrast (8 controls)
    df_sr = pd.read_csv(ROOT / "artifacts" / "soft_rule_contrast_20260903" / "soft_rule_contrast_by_seed.csv")
    clean_sr = df_sr[(df_sr["condition"] == "clean") & (df_sr["rho"] == 10.0)]
    pivot_sr = clean_sr.pivot(index="seed", columns="policy", values="total_cost")

    # 2. Kelmarsh (3 controls)
    df_k = pd.read_csv(base / "kelmarsh_reserve_by_seed.csv")
    pivot_k = df_k.pivot(index="seed", columns="policy", values="total_cost")

    # 3. GBDT (1 control)
    df_gbdt = pd.read_csv(base / "gbdt_reserve_pricing_by_seed.csv")
    pivot_gbdt = df_gbdt.pivot(index="seed", columns="policy", values="total_cost")

    # 4. Dense classifier (1 control)
    df_dense = pd.read_csv(base / "dense_pricing_by_seed.csv")
    pivot_dense = df_dense.pivot(index="seed", columns="policy", values="total_cost")

    controls = [
        ("soft-rule: soft-gate-bin vs global", "soft-gate-bin", "global", "clean", pivot_sr["soft-gate-bin"] - pivot_sr["global"]),
        ("soft-rule: soft-gate-bin vs physical-bin", "soft-gate-bin", "physical-bin", "clean", pivot_sr["soft-gate-bin"] - pivot_sr["physical-bin"]),
        ("soft-rule: soft-wspd-bin vs global", "soft-wspd-bin", "global", "clean", pivot_sr["soft-wspd-bin"] - pivot_sr["global"]),
        ("soft-rule: soft-wspd-bin vs physical-bin", "soft-wspd-bin", "physical-bin", "clean", pivot_sr["soft-wspd-bin"] - pivot_sr["physical-bin"]),
        ("soft-rule: soft-dist-bin vs global", "soft-dist-bin", "global", "clean", pivot_sr["soft-dist-bin"] - pivot_sr["global"]),
        ("soft-rule: soft-dist-bin vs physical-bin", "soft-dist-bin", "physical-bin", "clean", pivot_sr["soft-dist-bin"] - pivot_sr["physical-bin"]),
        ("soft-rule: soft-pab-bin vs global", "soft-pab-bin", "global", "clean", pivot_sr["soft-pab-bin"] - pivot_sr["global"]),
        ("soft-rule: soft-pab-bin vs physical-bin", "soft-pab-bin", "physical-bin", "clean", pivot_sr["soft-pab-bin"] - pivot_sr["physical-bin"]),
        ("K1: soft-gate-bin vs global (kelmarsh)", "soft-gate-bin", "global", "kelmarsh-sparse", pivot_k["soft-gate-bin"] - pivot_k["global"]),
        ("K1: soft-gate-bin vs soft-pab-bin (kelmarsh)", "soft-gate-bin", "soft-pab-bin", "kelmarsh-sparse", pivot_k["soft-gate-bin"] - pivot_k["soft-pab-bin"]),
        ("K1: soft-pab-bin vs global (kelmarsh)", "soft-pab-bin", "global", "kelmarsh-sparse", pivot_k["soft-pab-bin"] - pivot_k["global"]),
        ("K3: GBDT posterior vs joint gate", "soft-gbdt-bin", "soft-gate-bin", "clean", pivot_gbdt["soft-gbdt-bin"] - pivot_gbdt["soft-gate-bin"]),
        ("K4: dense posterior vs joint gate", "soft-dense-bin", "soft-gate-bin", "clean", pivot_dense["soft-dense-bin"] - pivot_dense["soft-gate-bin"]),
    ]

    m = len(controls)
    alpha = 0.05
    bonf_alpha = alpha / m  # 0.00384615
    q_low_95 = 0.025
    q_high_95 = 0.975
    q_low_bonf = bonf_alpha / 2.0  # 0.001923
    q_high_bonf = 1.0 - q_low_bonf  # 0.998077

    rng = np.random.default_rng(20260904)
    n_boot = 50000

    rows = []
    for tag, strategy, baseline, condition, diff_series in controls:
        vals = diff_series.dropna().to_numpy(dtype=np.float64)
        boots = rng.choice(vals, size=(n_boot, len(vals)), replace=True).mean(axis=1)

        mean_val = float(np.mean(vals))
        ci95_l = float(np.percentile(boots, q_low_95 * 100))
        ci95_h = float(np.percentile(boots, q_high_95 * 100))
        bonf_l = float(np.percentile(boots, q_low_bonf * 100))
        bonf_h = float(np.percentile(boots, q_high_bonf * 100))

        ci95_sig = not (ci95_l <= 0.0 <= ci95_h)
        bonf_sig = not (bonf_l <= 0.0 <= bonf_h)

        rows.append({
            "control": tag,
            "strategy": strategy,
            "baseline": baseline,
            "condition": condition,
            "n_seeds": len(vals),
            "delta": mean_val,
            "ci95_low": ci95_l,
            "ci95_high": ci95_h,
            "ci95_excludes_zero": bool(ci95_sig),
            "family_size_m": int(m),
            "bonferroni_threshold": float(bonf_alpha),
            "bonf_ci_low": bonf_l,
            "bonf_ci_high": bonf_h,
            "bonf_excludes_zero": bool(bonf_sig),
        })

    out = pd.DataFrame(rows)
    out.to_csv(out_dir / "unified_control_table.csv", index=False)
    print(out.to_string(index=False))
    return out


def main() -> None:
    print("=== hierarchical week-block bootstrap ===")
    hierarchical_block_bootstrap()
    print()
    print("=== unified mechanism-control table ===")
    unified_control_table()
    print("P1B_DONE")


if __name__ == "__main__":
    main()

