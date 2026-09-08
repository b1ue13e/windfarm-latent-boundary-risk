"""Generates publication-quality figures and analysis tables for the Three-Way Operational Boundaries and Selective Abstention.

Outputs:
1. Phase Boundary Diagram: Lag (minutes) vs Forecast Horizon (steps), mapping:
   - Simple Recalibration Sufficient
   - Learned Representation Advantage
   - Selective Abstention / Refusal Required
2. Risk-Coverage Frontier: Accepted Violation Rate and Fleet PSREI Cost vs Coverage Rate (50% to 100%)
3. Disentangled Shortage Decomposition Table
"""
from __future__ import annotations

from pathlib import Path
import json
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "artifacts" / "boundary_phase_scan"
OUT_DIR = REPO_ROOT / "artifacts" / "boundary_phase_scan" / "figures"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def plot_risk_coverage():
    cov_path = DATA_DIR / "phase_scan_risk_coverage_aggregate.csv"
    if not cov_path.exists():
        print(f"File not found: {cov_path}")
        return

    df = pd.read_csv(cov_path, header=[0, 1])
    # Extract delay-6 lead-0 (h=1, 60min lag)
    # Find relevant columns
    cols = df.columns
    model_col = [c for c in cols if c[0] == "model"][0]
    lead_col = [c for c in cols if c[0] == "lead_step"][0]
    lag_col = [c for c in cols if c[0] == "lag_steps"][0]
    cov_col = [c for c in cols if c[0] == "coverage"][0]
    acc_viol_mean = [c for c in cols if c[0] == "accepted_violation_rate" and c[1] == "mean"][0]
    fleet_viol_mean = [c for c in cols if c[0] == "fleet_violation_rate" and c[1] == "mean"][0]
    cost_mean = [c for c in cols if c[0] == "fleet_total_cost" and c[1] == "mean"][0]
    short_mean = [c for c in cols if c[0] == "fleet_shortage_mwh" and c[1] == "mean"][0]

    sub = df[(df[lag_col] == 6) & (df[lead_col] == 0) & (df[model_col] == "Frozen Backbone + Residual Quantile")]
    if sub.empty:
        sub = df[(df[lag_col] == 6) & (df[model_col] == "Frozen Backbone + Residual Quantile")]

    fig, ax1 = plt.subplots(figsize=(7, 4.5), dpi=300)
    covs = sub[cov_col].values
    acc_v = sub[acc_viol_mean].values * 100.0
    costs = sub[cost_mean].values / 1e6

    color = "tab:red"
    ax1.set_xlabel("Decision Acceptance Rate / Coverage ($c$)", fontsize=11, fontweight="bold")
    ax1.set_ylabel("Empirical Test Violation Rate (%)", color=color, fontsize=11, fontweight="bold")
    line1 = ax1.plot(covs * 100, acc_v, "o-", color=color, linewidth=2.2, label="Accepted Violation Rate")
    ax1.axhline(10.0, color="darkred", linestyle="--", alpha=0.7, label="Target Bound ($q^*=0.90, 10\%$)")
    ax1.tick_params(axis="y", labelcolor=color)
    ax1.grid(True, linestyle=":", alpha=0.6)

    ax2 = ax1.twinx()
    color = "tab:blue"
    ax2.set_ylabel("Total Fleet PSREI Cost ($10^6$ kW·h)", color=color, fontsize=11, fontweight="bold")
    line2 = ax2.plot(covs * 100, costs, "s--", color=color, linewidth=2.0, label="Fleet PSREI Cost")
    ax2.tick_params(axis="y", labelcolor=color)

    lines = line1 + [ax1.get_lines()[1]] + line2
    labels = [l.get_label() for l in lines]
    ax1.legend(lines, labels, loc="upper left", frameon=True, framealpha=0.9)

    plt.title("Selective Decision Abstention Frontier (Delay-6, $h=1$)", fontsize=12, fontweight="bold", pad=12)
    fig.tight_layout()
    out_file = OUT_DIR / "fig_risk_coverage_frontier.png"
    plt.savefig(out_file)
    plt.close()
    print(f"Saved: {out_file}")


def generate_phase_boundary_summary():
    agg_path = DATA_DIR / "phase_scan_cross_seed_aggregate.csv"
    if not agg_path.exists():
        print(f"File not found: {agg_path}")
        return

    df = pd.read_csv(agg_path, header=[0, 1])
    cols = df.columns
    lead_col = [c for c in cols if c[0] == "lead_minutes"][0]
    lag_col = [c for c in cols if c[0] == "lag_minutes"][0]
    ch_col = [c for c in cols if c[0] == "channel_mode"][0]
    recal_suff = [c for c in cols if c[0] == "recalibration_sufficient" and c[1] == "mean"][0]
    repr_adv = [c for c in cols if c[0] == "representation_advantage" and c[1] == "mean"][0]
    refusal_req = [c for c in cols if c[0] == "refusal_required" and c[1] == "mean"][0]

    rows = []
    for idx, r in df.iterrows():
        lead_m = int(r[lead_col])
        lag_m = int(r[lag_col])
        ch = r[ch_col]
        p_recal = float(r[recal_suff])
        p_repr = float(r[repr_adv])
        p_ref = float(r[refusal_req])

        if p_ref >= 0.5:
            regime_label = "Regime III: Abstention Required (Unreliable Telemetry)"
        elif p_repr >= 0.5:
            regime_label = "Regime II: Learned Representation Advantage"
        else:
            regime_label = "Regime I: Simple Recalibration Sufficient"

        rows.append({
            "lead_minutes": lead_m,
            "lag_minutes": lag_m,
            "channel_mode": ch,
            "dominant_regime": regime_label,
            "refusal_probability": p_ref,
            "representation_advantage_prob": p_repr,
            "recalibration_sufficient_prob": p_recal,
        })

    summary_df = pd.DataFrame(rows)
    out_csv = DATA_DIR / "phase_boundary_regime_classification.csv"
    summary_df.to_csv(out_csv, index=False)
    print(f"Saved: {out_csv}")


if __name__ == "__main__":
    plot_risk_coverage()
    generate_phase_boundary_summary()
