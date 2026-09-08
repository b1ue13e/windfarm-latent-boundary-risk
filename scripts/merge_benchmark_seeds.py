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

    # 1. Parts seeds (e.g. seeds 201, 202, 203, 204, 205)
    for p in parts_dirs:
        p_m = p / "decisive_results_by_seed.csv"
        p_b = p / "decisive_bootstrap_by_seed.csv"
        if p_m.exists():
            all_metrics.append(pd.read_csv(p_m))
        if p_b.exists():
            all_boots.append(pd.read_csv(p_b))

    # 2. Base directory (only if distinct from out_dir or if parts_dirs provided no data)
    if base_dir.resolve() != out_dir.resolve() or len(all_metrics) == 0:
        base_m = base_dir / "decisive_results_by_seed.csv"
        base_b = base_dir / "decisive_bootstrap_by_seed.csv"
        if base_m.exists():
            all_metrics.append(pd.read_csv(base_m))
        if base_b.exists():
            all_boots.append(pd.read_csv(base_b))

    if not all_metrics:
        print(f"No metric files found for farm {farm} in {base_dir} or {parts_dirs}")
        return

    df_metrics = pd.concat(all_metrics, ignore_index=True).drop_duplicates(
        subset=["farm", "seed", "regime", "model"], keep="last"
    )
    df_boot = pd.concat(all_boots, ignore_index=True).drop_duplicates(
        subset=["farm", "seed", "regime", "model"], keep="last"
    )

    df_metrics.to_csv(out_dir / "decisive_results_by_seed.csv", index=False)
    df_boot.to_csv(out_dir / "decisive_bootstrap_by_seed.csv", index=False)

    agg_df = df_metrics.groupby(["farm", "regime", "model"]).agg({
        "compliant": ["mean"],
        "violation_rate": ["mean", "std"],
        "reserve_mwh": ["mean", "std"],
        "shortage_mwh": ["mean", "std"],
        "total_cost": ["mean", "std"],
        "gamma_clean_val": ["mean", "std"],
        "gamma_stale_val": ["mean", "std"],
        "gamma_iso_test_diagnostic": ["mean", "std"],
        "delta_iso_test_diagnostic": ["mean", "std"],
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

    seeds_list = [int(s) for s in sorted(df_metrics["seed"].unique())]
    md_report = [
        f"# Decisive Fair Risk Benchmark Report: {farm.upper()}",
        f"**Date / Time**: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Benchmark Output Directory**: `{out_dir}`",
        f"**Evaluated Seeds**: {seeds_list} (Total: {len(seeds_list)} seeds)",
        f"**Delivery Horizon**: Lead Step 1 (10-minute dispatch delivery)",
        f"**Calibration Protocol**: State-Conditional Validation Multipliers (gamma_clean_val, gamma_stale_val) FROZEN on test set",
        f"**Target Reliability**: Violation Rate <= {TARGET_VIOLATION * 100.0:.1f}% (Critical Fractile q* = {CRITICAL_FRACTILE:.2f})",
        "",
        "## 1. Primary Evaluation: Frozen Validation Calibration Test Performance",
        "",
        "| Regime | Model | Compliant (Pass Rate) | Test Violation Rate | Reserve (MWh) | Shortage (MWh) | Total Cost Regret | Gamma Clean Val | Gamma Stale Val | Test Iso Gamma Diagnostic |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]

    for _, row in agg_df.iterrows():
        reg = row[("regime", "")]
        mod = row[("model", "")]
        pass_rate = f"{row[('compliant', 'mean')]*100.0:.0f}%"
        viol = f"{row[('violation_rate', 'mean')]*100.0:.1f}%"
        res = f"{row[('reserve_mwh', 'mean')]:.2f} +/- {row[('reserve_mwh', 'std')]:.2f}"
        sh = f"{row[('shortage_mwh', 'mean')]:.2f} +/- {row[('shortage_mwh', 'std')]:.2f}"
        cost = f"{row[('total_cost', 'mean')]:.1f} +/- {row[('total_cost', 'std')]:.1f}"
        gc = f"{row[('gamma_clean_val', 'mean')]:.2f}"
        gs = f"{row[('gamma_stale_val', 'mean')]:.2f}"
        g_diag = f"{row[('gamma_iso_test_diagnostic', 'mean')]:.2f}"
        d_diag = row.get(('delta_iso_test_diagnostic', 'mean'), 0.0)
        diag_str = f"{g_diag}" if (pd.isna(d_diag) or float(d_diag) <= 1e-4) else f"{g_diag} (+{float(d_diag):.1f})"
        md_report.append(f"| {reg} | {mod} | {pass_rate} | {viol} | {res} | {sh} | {cost} | {gc} | {gs} | {diag_str} |")

    md_report.extend([
        "",
        "## 2. Decision Route & Manuscript Track Verdict",
        f"**Track Recommendation**: `{verdict.get('track_recommendation', 'N/A')}`",
        f"**Recommended Decision Route**: `{verdict['recommended_route']}`",
        "",
        "### Criteria Evaluation:",
        f"- **State-Conditional Hybrid Compliant (All Regimes)**: {verdict.get('hybrid_compliant_all', False)}",
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
    import argparse
    parser = argparse.ArgumentParser(description="Merge multi-seed benchmark results")
    parser.add_argument("--farm", default="wtb", choices=["wtb", "kelmarsh", "penmanshiel"])
    parser.add_argument("--output-dir", default="artifacts/decisive_fair_risk")
    args = parser.parse_args()

    farm = args.farm
    base = Path(f"{args.output_dir}/{farm}")
    parts = []
    for s in [201, 202, 203, 204, 205]:
        p1 = Path(f"{args.output_dir}/wtb_parts/seed{s}/{farm}")
        p2 = Path(f"{args.output_dir}/parts/seed{s}/{farm}")
        p3 = Path(f"{args.output_dir}/seed{s}/{farm}")
        if p1.exists():
            parts.append(p1)
        elif p2.exists():
            parts.append(p2)
        elif p3.exists():
            parts.append(p3)
    out = Path(f"{args.output_dir}/{farm}")
    merge_seeds(farm, base, parts, out)
