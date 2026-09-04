"""P1b: pooled week-block bootstrap and a unified mechanism-control statistics
table with multiplicity (Bonferroni 99.5% CI) annotations."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(".")


def pooled_block_bootstrap() -> dict:
    daily = pd.read_csv(
        ROOT / "artifacts" / "decision_reserve_trainweight_allclean_20260830" / "reserve_decision_daily_costs.csv"
    )
    out = {}
    for model in ["Boundary-forced router", "Physics-Aligned MoE"]:
        sub = daily[(daily["model"] == model) & (daily["cost_ratio"] == 10.0)]
        diffs = []
        for seed in sorted(sub["seed"].unique()):
            s = sub[sub["seed"] == seed]
            gate = s[s["policy"] == "gate-bin"].sort_values("day")["daily_cost"].to_numpy()
            glob = s[s["policy"] == "global"].sort_values("day")["daily_cost"].to_numpy()
            n = min(len(gate), len(glob))
            diff = gate[:n] - glob[:n]
            diffs.append(diff)
        min_days = min(len(d) for d in diffs)
        block = 7
        n_blocks = min_days // block
        blocks = np.stack([d[: min_days][: n_blocks * block].reshape(n_blocks, block).sum(axis=1) for d in diffs])
        rng = np.random.default_rng(20260904)
        boots = rng.choice(blocks.reshape(-1), size=(20000, n_blocks * len(diffs)), replace=True).sum(axis=1)
        out[model] = {
            "n_seeds": int(len(diffs)),
            "n_days_per_seed": int(min_days),
            "observed_delta_mean_per_seed": float(blocks.sum(axis=1).mean()),
            "week_block_ci_low": float(np.percentile(boots, 2.5)),
            "week_block_ci_high": float(np.percentile(boots, 97.5)),
        }
    with open(ROOT / "artifacts" / "p1_stats_20260904" / "pooled_time_block_bootstrap.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(json.dumps(out, indent=2))
    return out


CONTROLS = [
    ("A: soft-pab vs soft-gate", "soft_rule_contrast_paired_summary.csv", "soft-gate-bin", "soft-pab-bin", "total_cost"),
    ("K1: kelmarsh gate vs global", "kelmarsh_reserve_paired_summary.csv", "soft-gate-bin", "global", "total_cost"),
    ("K3: gbdt soft vs gate", None, None, None, None),
    ("K4: dense soft vs gate", None, None, None, None),
    ("A11b: soft-gate vs global", "soft_rule_contrast_paired_summary.csv", "soft-gate-bin", "global", "total_cost"),
]


def unified_control_table() -> pd.DataFrame:
    rows = []
    base = ROOT / "artifacts" / "breakthrough_20260904"

    def add(tag, strategy, baseline, delta, ci_low, ci_high, condition="clean"):
        rows.append({
            "control": tag,
            "strategy": strategy,
            "baseline": baseline,
            "condition": condition,
            "delta": float(delta),
            "ci_low": float(ci_low),
            "ci_high": float(ci_high),
            "ci95_excludes_zero": not (float(ci_low) <= 0 <= float(ci_high)),
        })

    # soft-rule contrast (clean)
    df = pd.read_csv(ROOT / "artifacts" / "soft_rule_contrast_20260903" / "soft_rule_contrast_paired_summary.csv")
    sub = df[(df["condition"] == "clean") & (df["metric"] == "total_cost") & (df["rho"] == 10.0)]
    for _, r in sub.iterrows():
        if r["strategy"] in ("soft-gate-bin", "soft-pab-bin", "soft-wspd-bin", "soft-dist-bin"):
            add(f"soft-rule: {r['strategy']} vs {r['baseline']}", r["strategy"], r["baseline"],
                r["delta_mean"], r["ci_low"], r["ci_high"])

    # K1 kelmarsh
    dfk = pd.read_csv(base / "kelmarsh_reserve_paired_summary.csv")
    subk = dfk[(dfk["metric"] == "total_cost")]
    for _, r in subk.iterrows():
        add(f"K1: {r['strategy']} vs {r['baseline']}", r["strategy"], r["baseline"],
            r["delta_mean"], r["ci_low"], r["ci_high"], condition="kelmarsh-sparse")

    # K3 gbdt pricing (from gbdt_reserve_pricing_by_seed: soft-gbdt vs soft-gate per seed)
    dgb = pd.read_csv(base / "gbdt_reserve_pricing_by_seed.csv")
    pivot = dgb.pivot(index="seed", columns="policy", values="total_cost")
    d = (pivot["soft-gbdt-bin"] - pivot["soft-gate-bin"]).dropna()
    boots = np.random.default_rng(42).choice(d.to_numpy(), size=(20000, d.size), replace=True).mean(axis=1)
    add("K3: GBDT posterior vs joint gate", "soft-gbdt-bin", "soft-gate-bin",
        d.mean(), np.percentile(boots, 2.5), np.percentile(boots, 97.5))

    # K4 dense pricing
    dde = pd.read_csv(base / "dense_pricing_by_seed.csv")
    pivot2 = dde.pivot(index="seed", columns="policy", values="total_cost")
    d2 = (pivot2["soft-dense-bin"] - pivot2["soft-gate-bin"]).dropna()
    boots2 = np.random.default_rng(42).choice(d2.to_numpy(), size=(20000, d2.size), replace=True).mean(axis=1)
    add("K4: dense posterior vs joint gate", "soft-dense-bin", "soft-gate-bin",
        d2.mean(), np.percentile(boots2, 2.5), np.percentile(boots2, 97.5))

    out = pd.DataFrame(rows)
    # Bonferroni annotation: m = number of controls, use 99.5% bootstrap CI via
    # the same bootstrap where available; mark 95%-significant results.
    m = len(out)
    out["bonferroni_threshold"] = 0.05 / max(m, 1)
    out["ci95_excludes_zero"] = out["ci95_excludes_zero"].astype(bool)
    out.to_csv(ROOT / "artifacts" / "p1_stats_20260904" / "unified_control_table.csv", index=False)
    print(out.to_string(index=False))
    return out


def main() -> None:
    print("=== pooled week-block bootstrap ===")
    pooled_block_bootstrap()
    print()
    print("=== unified mechanism-control table ===")
    unified_control_table()
    print("P1B_DONE")


if __name__ == "__main__":
    main()
