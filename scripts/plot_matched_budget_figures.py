"""Generate publication-ready figures for Matched-Reserve-Budget Frontier and Sensitivity Analysis.

Produces:
1. figures/matched_budget_transition_frontier.pdf / .png
2. figures/matched_budget_control_slices.pdf
3. figures/rho_sensitivity.pdf
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

plt.rcParams.update({
    "font.family": "serif",
    "font.size": 10,
    "axes.labelsize": 11,
    "axes.titlesize": 11,
    "legend.fontsize": 9,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "figure.titlesize": 12,
    "lines.linewidth": 1.5,
    "lines.markersize": 4,
})

REPO_ROOT = Path("e:/论文3")
ARTIFACTS_DIR = REPO_ROOT / "artifacts/matched_budget"
FIG_DIR = REPO_ROOT / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

def plot_transition_frontier():
    df_a = pd.read_csv(ARTIFACTS_DIR / "exact_matched_budget_frontier.csv")
    df_boot = pd.read_csv(ARTIFACTS_DIR / "bootstrap_frontier_statistics.csv")
    
    # Filter Transition slice
    trans_a = df_a[df_a["slice"] == "Transition"]
    trans_boot = df_boot[df_boot["slice"] == "Transition"]
    
    # Aggregate across seeds
    grid_mean = trans_a.groupby("budget_idx").agg({
        "target_budget_kwh": "mean",
        "R_base_kwh": "mean",
        "R_post_kwh": "mean",
        "U_base_kwh": "mean",
        "U_post_kwh": "mean",
        "V_base_pct": "mean",
        "V_post_pct": "mean",
        "delta_U_kwh": "mean",
        "delta_V_pct": "mean",
    }).reset_index()
    
    boot_mean = trans_boot.groupby("budget_idx").agg({
        "target_budget_kwh": "mean",
        "delta_U_mean_kwh": "mean",
        "delta_U_ci_low": "mean",
        "delta_U_ci_high": "mean",
        "delta_V_mean_pct": "mean",
        "delta_V_ci_low": "mean",
        "delta_V_ci_high": "mean",
    }).reset_index()
    
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(14, 4), dpi=300)
    
    # Panel A: R vs U
    r_vals = grid_mean["target_budget_kwh"].values / 1e6
    u_base = grid_mean["U_base_kwh"].values / 1e3
    u_post = grid_mean["U_post_kwh"].values / 1e3
    
    ax1.plot(r_vals, u_base, "s-", color="#1f77b4", label="Wspd-Bins Baseline ($M_{\\mathrm{base}}$)")
    ax1.plot(r_vals, u_post, "o-", color="#d62728", label="Boundary Posterior ($M_{\\mathrm{post}}$)")
    ax1.set_xlabel("Reserve Procurement Energy ($10^6$ kWh)")
    ax1.set_ylabel("Uncovered Shortfall ($10^3$ kWh)")
    ax1.set_title("(a) Reliability Frontier ($U$ vs. $R$)")
    ax1.grid(True, linestyle="--", alpha=0.5)
    ax1.legend(loc="upper right")
    
    # Panel B: R vs Violation
    v_base = grid_mean["V_base_pct"].values
    v_post = grid_mean["V_post_pct"].values
    
    ax2.plot(r_vals, v_base, "s-", color="#1f77b4", label="Wspd-Bins Baseline")
    ax2.plot(r_vals, v_post, "o-", color="#d62728", label="Boundary Posterior")
    ax2.axhline(10.0, color="gray", linestyle=":", label="10% Target ($q^*=0.90$)")
    ax2.set_xlabel("Reserve Procurement Energy ($10^6$ kWh)")
    ax2.set_ylabel("Violation Rate (%)")
    ax2.set_title("(b) Violation Rate ($V$ vs. $R$)")
    ax2.grid(True, linestyle="--", alpha=0.5)
    ax2.legend(loc="upper right")
    
    # Panel C: Paired Delta U with 95% Bootstrap CI
    du_mean = boot_mean["delta_U_mean_kwh"].values / 1e3
    du_low = boot_mean["delta_U_ci_low"].values / 1e3
    du_high = boot_mean["delta_U_ci_high"].values / 1e3
    
    ax3.plot(r_vals, du_mean, "o-", color="#2ca02c", label="Paired $\\Delta U$ (Post - Base)")
    ax3.fill_between(r_vals, du_low, du_high, color="#2ca02c", alpha=0.2, label="95% Bootstrap CI")
    ax3.axhline(0.0, color="black", linestyle="-", linewidth=1.0)
    ax3.set_xlabel("Reserve Procurement Energy ($10^6$ kWh)")
    ax3.set_ylabel("Paired Shortfall Delta ($10^3$ kWh)")
    ax3.set_title("(c) Allocation Efficiency Delta ($\\Delta U$)")
    ax3.grid(True, linestyle="--", alpha=0.5)
    ax3.legend(loc="upper right")
    
    plt.tight_layout()
    fig.savefig(FIG_DIR / "matched_budget_transition_frontier.pdf")
    fig.savefig(FIG_DIR / "matched_budget_transition_frontier.png")
    plt.close(fig)
    print("Saved matched_budget_transition_frontier.pdf/png")

def plot_control_slices():
    df_a = pd.read_csv(ARTIFACTS_DIR / "exact_matched_budget_frontier.csv")
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.2), dpi=300)
    
    slice_configs = [
        ("Transition", r"Primary: Transition Window ($\pm 3$ steps)", axes[0]),
        ("Steady", "Negative Control: Stationary Window", axes[1]),
        ("Full", "Global Control: Full Wind Farm", axes[2]),
    ]
    
    for slice_name, title, ax in slice_configs:
        sub = df_a[df_a["slice"] == slice_name]
        mean_df = sub.groupby("budget_idx").agg({
            "target_budget_kwh": "mean",
            "U_base_kwh": "mean",
            "U_post_kwh": "mean",
        }).reset_index()
        
        r_vals = mean_df["target_budget_kwh"].values / 1e6
        u_base = mean_df["U_base_kwh"].values / 1e3
        u_post = mean_df["U_post_kwh"].values / 1e3
        
        ax.plot(r_vals, u_base, "s-", color="#1f77b4", label="Wspd-Bins Baseline ($M_{\\mathrm{base}}$)")
        ax.plot(r_vals, u_post, "o-", color="#d62728", label="Boundary Posterior ($M_{\\mathrm{post}}$)")
        ax.set_xlabel("Reserve Procurement ($10^6$ kWh)")
        ax.set_ylabel("Uncovered Shortfall ($10^3$ kWh)")
        ax.set_title(title)
        ax.grid(True, linestyle="--", alpha=0.5)
        ax.legend(loc="upper right")
        
    plt.tight_layout()
    fig.savefig(FIG_DIR / "matched_budget_control_slices.pdf")
    plt.close(fig)
    print("Saved matched_budget_control_slices.pdf")

def plot_rho_sensitivity():
    df_frozen = pd.read_csv(ARTIFACTS_DIR / "frozen_policy_rho_sensitivity.csv")
    df_reopt = pd.read_csv(ARTIFACTS_DIR / "reoptimized_rho_sensitivity.csv")
    
    reopt_trans = df_reopt[(df_reopt["seed"] == "Mean") & (df_reopt["slice"] == "Transition")]
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.2), dpi=300)
    
    # Panel A: Frozen Policy Algebraic Crossover
    rho_f = df_frozen["rho"].values
    d_psrei_f = df_frozen["delta_psrei_kwh"].values / 1e3
    
    ax1.plot(rho_f, d_psrei_f, "o-", color="#332288", label="Frozen Policy: $\\Delta C(\\rho) = \\Delta R + \\rho \\Delta U$")
    ax1.axhline(0.0, color="black", linestyle="-", linewidth=1.0)
    ax1.axvline(40.97, color="#d62728", linestyle="--", label="Algebraic Crossover $\\rho_{\\mathrm{break}} \\approx 40.97$")
    ax1.set_xlabel("Shortage Penalty Ratio $\\rho$")
    ax1.set_ylabel("$\\Delta \\mathrm{PSREI}$ (Post - Base, $10^3$ kWh)")
    ax1.set_title("(a) Frozen-Policy Algebraic Crossover")
    ax1.grid(True, linestyle="--", alpha=0.5)
    ax1.legend(loc="upper right")
    
    # Panel B: Re-Optimized Policy Sensitivity
    rho_r = reopt_trans["rho"].values
    d_psrei_r = reopt_trans["delta_PSREI_kwh"].values / 1e3
    
    ax2.plot(rho_r, d_psrei_r, "s-", color="#e7298a", label=r"Re-Optimized: $q^*(\rho) = 1 - 1/\rho$")
    ax2.axhline(0.0, color="black", linestyle="-", linewidth=1.0)
    ax2.set_xlabel("Shortage Penalty Ratio $\\rho$")
    ax2.set_ylabel("$\\Delta \\mathrm{PSREI}$ (Post - Base, $10^3$ kWh)")
    ax2.set_title("(b) Validation Re-Optimized Policy Sensitivity")
    ax2.grid(True, linestyle="--", alpha=0.5)
    ax2.legend(loc="upper left")
    
    plt.tight_layout()
    fig.savefig(FIG_DIR / "rho_sensitivity.pdf")
    plt.close(fig)
    print("Saved rho_sensitivity.pdf")

if __name__ == "__main__":
    plot_transition_frontier()
    plot_control_slices()
    plot_rho_sensitivity()
