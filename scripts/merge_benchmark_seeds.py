import json
import time
import sys
from pathlib import Path
import pandas as pd
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.decisive_fair_risk_benchmark import evaluate_route_verdict, TARGET_VIOLATION, CRITICAL_FRACTILE


def merge_seeds(farm: str, base_dir: Path, parts_dirs: list[Path], out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    all_metrics = []
    all_boots = []

    # 1. Base seed (e.g. seed 201)
    base_m = base_dir / "decisive_results_by_seed.csv"
    base_b = base_dir / "decisive_bootstrap_by_seed.csv"
    if base_m.exists():
        df_m = pd.read_csv(base_m)
        all_metrics.append(df_m)
    if base_b.exists():
        df_b = pd.read_csv(base_b)
        all_boots.append(df_b)

    # 2. Parts seeds (e.g. seeds 202, 203, 204, 205)
    for p in parts_dirs:
        p_m = p / "decisive_results_by_seed.csv"
        p_b = p / "decisive_bootstrap_by_seed.csv"
        if p_m.exists():
            all_metrics.append(pd.read_csv(p_m))
        if p_b.exists():
            all_boots.append(pd.read_csv(p_b))

    df_metrics = pd.concat(all_metrics, ignore_index=True).drop_duplicates(subset=["farm", "seed", "regime", "model"])
    df_boot = pd.concat(all_boots, ignore_index=True).drop_duplicates(subset=["farm", "seed", "regime", "model"])

    df_metrics.to_csv(out_dir / "decisive_results_by_seed.csv", index=False)
    df_boot.to_csv(out_dir / "decisive_bootstrap_by_seed.csv", index=False)

    agg_df = df_metrics.groupby(["farm", "regime", "model"]).agg({
        "gamma_iso_test": ["mean", "std"],
        "violation_rate": ["mean", "std"],
        "reserve_mwh": ["mean", "std"],
        "shortage_mwh": ["mean", "std"],
        "total_cost": ["mean", "std"],
        "false_alarm_rate": ["mean", "std"],
        "event_recall": ["mean", "std"],
        "brier_score": ["mean", "std"],
        "ece": ["mean", "std"],
        "pinball_loss": ["mean", "std"],
    }).reset_index()
    agg_df.to_csv(out_dir / "decisive_cross_seed_aggregate.csv", index=False)

    verdict = evaluate_route_verdict(agg_df)
    with open(out_dir / "route_dispatch_verdict.json", "w", encoding="utf-8") as f:
        json.dump(verdict, f, indent=2)

    seeds_list = sorted(df_metrics["seed"].unique())
    md_report = [
        f"# Decisive Fair Risk Benchmark Report: {farm.upper()}",
        f"**Date / Time**: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Benchmark Output Version**: `artifacts/decisive_benchmark_v1`",
        f"**Evaluated Seeds**: {seeds_list} (Total: {len(seeds_list)} seeds)",
        f"**Delivery Horizon**: Lead Step 1 (10-minute dispatch delivery)",
        f"**Target Reliability**: Strict Iso-Reliability Violation Rate <= {TARGET_VIOLATION * 100.0:.1f}% (Critical Fractile q* = {CRITICAL_FRACTILE:.2f})",
        "",
        "## 1. Strict Iso-Reliability Performance Summary (Across Seeds)",
        "",
        "| Regime | Model | Test Iso Gamma | Test Violation Rate | Reserve (MWh) | Shortage (MWh) | Total Cost Regret | False Alarm Rate | Event Recall |",
        "|---|---|---|---|---|---|---|---|---|",
    ]

    for _, row in agg_df.iterrows():
        reg = row[("regime", "")]
        mod = row[("model", "")]
        gamma = f"{row[('gamma_iso_test', 'mean')]:.2f}"
        viol = f"{row[('violation_rate', 'mean')]*100.0:.1f}%"
        res = f"{row[('reserve_mwh', 'mean')]:.2f} +/- {row[('reserve_mwh', 'std')]:.2f}"
        sh = f"{row[('shortage_mwh', 'mean')]:.2f} +/- {row[('shortage_mwh', 'std')]:.2f}"
        cost = f"{row[('total_cost', 'mean')]:.1f} +/- {row[('total_cost', 'std')]:.1f}"
        far = f"{row[('false_alarm_rate', 'mean')]*100.0:.1f}%"
        rec = f"{row[('event_recall', 'mean')]*100.0:.1f}%"
        md_report.append(f"| {reg} | {mod} | {gamma} | {viol} | {res} | {sh} | {cost} | {far} | {rec} |")

    md_report.extend([
        "",
        "## 2. Decision Route Dispatch Verdict",
        f"**Recommended Route**: `{verdict['recommended_route']}`",
        "",
        "### Criteria Evaluation:",
        f"- **Dense vs MoE Equivalent**: {verdict['dense_vs_moe_equivalent']} (Dense/MoE Cost Ratio: {verdict['dense_vs_moe_ratio']:.3f})",
        f"- **Simple Quantile Wins over Deep**: {verdict['simple_quantile_beats_deep']}",
        f"- **Recognition Better but Decision Not Improved**: {verdict['recognition_better_decision_no']}",
        f"- **Cross-Farm Increment Confirmed**: {verdict['cross_farm_increment']}",
        "",
        "### Decision Rationale:",
    ])
    for r in verdict["rationales"]:
        md_report.append(f"- {r}")

    (out_dir / "benchmark_report.md").write_text("\n".join(md_report), encoding="utf-8")
    print(f"Merged {len(seeds_list)} seeds for {farm.upper()} into {out_dir}")
    print(verdict)


if __name__ == "__main__":
    base = Path("artifacts/decisive_benchmark_v1/risk_layer_benchmark/wtb")
    parts = [
        Path("artifacts/decisive_benchmark_v1/risk_layer_benchmark/wtb_parts/seed202/wtb"),
        Path("artifacts/decisive_benchmark_v1/risk_layer_benchmark/wtb_parts/seed203/wtb"),
        Path("artifacts/decisive_benchmark_v1/risk_layer_benchmark/wtb_parts/seed204/wtb"),
        Path("artifacts/decisive_benchmark_v1/risk_layer_benchmark/wtb_parts/seed205/wtb"),
    ]
    out = Path("artifacts/decisive_benchmark_v1/risk_layer_benchmark/wtb")
    merge_seeds("wtb", base, parts, out)
