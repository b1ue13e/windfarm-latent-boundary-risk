"""
plot_gate_representation_stability.py
Publication-ready multi-year temporal representation stability figure for IEEE TSTE.
Formatted according to scientific-visualization standard:
- 7.16 in double-column width
- Okabe-Ito colorblind-friendly palette
- Strict typography hierarchy and despine styling
"""

import os
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

def plot_gate_stability():
    csv_path = Path("artifacts/multiyear_gate_representation_audit/gate_representation_decay_raw.csv")
    if not csv_path.exists():
        print("Raw CSV not found.")
        return

    df = pd.read_csv(csv_path)

    # IEEE Publication Typography & Style
    plt.rcParams["font.family"] = "sans-serif"
    plt.rcParams["font.sans-serif"] = ["Arial", "Helvetica", "DejaVu Sans"]
    plt.rcParams["mathtext.fontset"] = "dejavusans"
    plt.rcParams["axes.edgecolor"] = "#333333"
    plt.rcParams["axes.linewidth"] = 0.75
    plt.rcParams["xtick.direction"] = "in"
    plt.rcParams["ytick.direction"] = "in"

    # Strict IEEE double-column dimension: 7.16 in width x 2.4 in height
    fig, axes = plt.subplots(1, 3, figsize=(7.16, 2.4), dpi=600)
    plt.subplots_adjust(left=0.07, right=0.985, top=0.86, bottom=0.17, wspace=0.32)

    # Okabe-Ito publication palette
    c_km_pitch = "#0072B2"  # Deep Blue
    c_km_all = "#009E73"    # Emerald
    c_pm_pitch = "#D55E00"  # Vermillion
    c_pm_all = "#7E22CE"    # Deep Purple

    # 1. Kelmarsh Representation Stability
    ax1 = axes[0]
    km = df[df["farm"] == "kelmarsh"]
    km_summary = km.groupby("calendar_year").agg({
        "nmi_ground_truth": ["mean", "std"],
        "inverse_wasserstein_pitch": ["mean", "std"],
        "inverse_wasserstein_all": ["mean", "std"],
    })
    years = km_summary.index

    inv_w_pitch_m = km_summary[("inverse_wasserstein_pitch", "mean")]
    inv_w_pitch_s = km_summary[("inverse_wasserstein_pitch", "std")]
    inv_w_all_m = km_summary[("inverse_wasserstein_all", "mean")]
    inv_w_all_s = km_summary[("inverse_wasserstein_all", "std")]

    ax1.plot(years, inv_w_pitch_m, "o-", color=c_km_pitch, lw=1.2, ms=3.5, label=r"Inv-$\mathcal{W}_1(p_{\mathrm{pitch}})$")
    ax1.fill_between(years, inv_w_pitch_m - inv_w_pitch_s, inv_w_pitch_m + inv_w_pitch_s, color=c_km_pitch, alpha=0.15)
    
    ax1.plot(years, inv_w_all_m, "s--", color=c_km_all, lw=1.1, ms=3.0, label=r"Inv-$\bar{\mathcal{W}}_1(\mathrm{all})$")
    ax1.fill_between(years, inv_w_all_m - inv_w_all_s, inv_w_all_m + inv_w_all_s, color=c_km_all, alpha=0.15)

    ax1.set_title("(a) Kelmarsh (9 Yrs, 6 Turbines)", fontsize=7.6, fontweight="bold", pad=4)
    ax1.set_xlabel("Calendar Year", fontsize=7.0, labelpad=2)
    ax1.set_ylabel(r"Inverse $\mathcal{W}_1$ Similarity $1 / (1 + \mathcal{W}_1)$", fontsize=6.8, labelpad=2)
    ax1.set_ylim(0.95, 1.005)
    ax1.tick_params(axis="both", labelsize=6.0, length=3.0, width=0.6)
    ax1.grid(True, alpha=0.20, linestyle="--", linewidth=0.5)
    ax1.legend(loc="lower left", fontsize=5.8, frameon=False, borderpad=0.2, handlelength=1.4)
    ax1.spines["top"].set_visible(False)
    ax1.spines["right"].set_visible(False)

    # 2. Penmanshiel Representation Stability
    ax2 = axes[1]
    pm = df[df["farm"] == "penmanshiel"]
    pm_summary = pm.groupby("calendar_year").agg({
        "inverse_wasserstein_pitch": ["mean", "std"],
        "inverse_wasserstein_all": ["mean", "std"],
    })
    pm_years = pm_summary.index

    p_inv_w_pitch_m = pm_summary[("inverse_wasserstein_pitch", "mean")]
    p_inv_w_pitch_s = pm_summary[("inverse_wasserstein_pitch", "std")]
    p_inv_w_all_m = pm_summary[("inverse_wasserstein_all", "mean")]
    p_inv_w_all_s = pm_summary[("inverse_wasserstein_all", "std")]

    ax2.plot(pm_years, p_inv_w_pitch_m, "o-", color=c_pm_pitch, lw=1.2, ms=3.5, label=r"Inv-$\mathcal{W}_1(p_{\mathrm{pitch}})$")
    ax2.fill_between(pm_years, p_inv_w_pitch_m - p_inv_w_pitch_s, p_inv_w_pitch_m + p_inv_w_pitch_s, color=c_pm_pitch, alpha=0.15)
    
    ax2.plot(pm_years, p_inv_w_all_m, "s--", color=c_pm_all, lw=1.1, ms=3.0, label=r"Inv-$\bar{\mathcal{W}}_1(\mathrm{all})$")
    ax2.fill_between(pm_years, p_inv_w_all_m - p_inv_w_all_s, p_inv_w_all_m + p_inv_w_all_s, color=c_pm_all, alpha=0.15)

    ax2.set_title("(b) Penmanshiel (8.6 Yrs, 15 Turbines)", fontsize=7.6, fontweight="bold", pad=4)
    ax2.set_xlabel("Calendar Year", fontsize=7.0, labelpad=2)
    ax2.set_ylabel(r"Inverse $\mathcal{W}_1$ Similarity $1 / (1 + \mathcal{W}_1)$", fontsize=6.8, labelpad=2)
    ax2.set_ylim(0.92, 1.005)
    ax2.tick_params(axis="both", labelsize=6.0, length=3.0, width=0.6)
    ax2.grid(True, alpha=0.20, linestyle="--", linewidth=0.5)
    ax2.legend(loc="lower left", fontsize=5.8, frameon=False, borderpad=0.2, handlelength=1.4)
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)

    # 3. Ground-Truth Boundary Alignment (NMI) over time
    ax3 = axes[2]
    km_valid_nmi = km[km["nmi_ground_truth"] > 0].groupby("calendar_year")["nmi_ground_truth"].agg(["mean", "std"])
    pm_valid_nmi = pm[pm["nmi_ground_truth"] > 0].groupby("calendar_year")["nmi_ground_truth"].agg(["mean", "std"])

    ax3.plot(km_valid_nmi.index, km_valid_nmi["mean"], "o-", color=c_km_pitch, lw=1.2, ms=3.5, label="Kelmarsh NMI")
    ax3.fill_between(km_valid_nmi.index, km_valid_nmi["mean"] - km_valid_nmi["std"], km_valid_nmi["mean"] + km_valid_nmi["std"], color=c_km_pitch, alpha=0.15)

    if not pm_valid_nmi.empty:
        ax3.plot(pm_valid_nmi.index, pm_valid_nmi["mean"], "s--", color=c_pm_pitch, lw=1.1, ms=3.0, label="Penmanshiel NMI")
        ax3.fill_between(pm_valid_nmi.index, pm_valid_nmi["mean"] - pm_valid_nmi["std"], pm_valid_nmi["mean"] + pm_valid_nmi["std"], color=c_pm_pitch, alpha=0.15)

    ax3.set_title("(c) Physical Boundary Alignment (NMI)", fontsize=7.6, fontweight="bold", pad=4)
    ax3.set_xlabel("Calendar Year", fontsize=7.0, labelpad=2)
    ax3.set_ylabel("Normalized Mutual Info (NMI)", fontsize=6.8, labelpad=2)
    ax3.set_ylim(0.0, 0.45)
    ax3.tick_params(axis="both", labelsize=6.0, length=3.0, width=0.6)
    ax3.grid(True, alpha=0.20, linestyle="--", linewidth=0.5)
    ax3.legend(loc="upper right", fontsize=5.8, frameon=False, borderpad=0.2, handlelength=1.4)
    ax3.spines["top"].set_visible(False)
    ax3.spines["right"].set_visible(False)

    out_dirs = [
        Path("artifacts/multiyear_gate_representation_audit"),
        Path("artifacts/paper_assets/figures"),
        Path("figures"),
    ]
    for od in out_dirs:
        od.mkdir(parents=True, exist_ok=True)
        fig.savefig(od / "figure_gate_representation_stability.pdf", format="pdf", bbox_inches="tight", pad_inches=0.02)
        fig.savefig(od / "figure_gate_representation_stability.png", dpi=600, bbox_inches="tight", pad_inches=0.02)
    
    plt.close(fig)
    print("Saved publication-standard figure_gate_representation_stability to audit, paper_assets, and figures directories.")

if __name__ == "__main__":
    plot_gate_stability()
