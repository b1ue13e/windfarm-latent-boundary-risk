import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from pathlib import Path

def plot_gate_stability():
    csv_path = Path("artifacts/multiyear_gate_representation_audit/gate_representation_decay_raw.csv")
    if not csv_path.exists():
        print("Raw CSV not found.")
        return

    df = pd.read_csv(csv_path)

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.2), dpi=300)
    plt.subplots_adjust(wspace=0.28)

    # 1. Kelmarsh Representation Stability
    ax1 = axes[0]
    km = df[df["farm"] == "kelmarsh"]
    km_summary = km.groupby("calendar_year").agg({
        "nmi_ground_truth": ["mean", "std"],
        "inverse_wasserstein_pitch": ["mean", "std"],
        "inverse_wasserstein_all": ["mean", "std"],
    })
    years = km_summary.index

    nmi_m = km_summary[("nmi_ground_truth", "mean")]
    nmi_s = km_summary[("nmi_ground_truth", "std")]
    inv_w_pitch_m = km_summary[("inverse_wasserstein_pitch", "mean")]
    inv_w_pitch_s = km_summary[("inverse_wasserstein_pitch", "std")]
    inv_w_all_m = km_summary[("inverse_wasserstein_all", "mean")]
    inv_w_all_s = km_summary[("inverse_wasserstein_all", "std")]

    ax1.plot(years, inv_w_pitch_m, "o-", color="#1f77b4", lw=2, label=r"Inv-$\mathcal{W}_1(p_{\mathrm{pitch}})$")
    ax1.fill_between(years, inv_w_pitch_m - inv_w_pitch_s, inv_w_pitch_m + inv_w_pitch_s, color="#1f77b4", alpha=0.15)
    
    ax1.plot(years, inv_w_all_m, "s--", color="#2ca02c", lw=1.8, label=r"Inv-$\bar{\mathcal{W}}_1(\mathrm{all\ experts})$")
    ax1.fill_between(years, inv_w_all_m - inv_w_all_s, inv_w_all_m + inv_w_all_s, color="#2ca02c", alpha=0.15)

    ax1.set_title("(a) Kelmarsh (9 Years, 6 Turbines)\nRepresentation Similarity vs Commissioning", fontsize=11, fontweight="bold")
    ax1.set_xlabel("Calendar Year", fontsize=10)
    ax1.set_ylabel(r"Inverse Wasserstein Similarity $1 / (1 + \mathcal{W}_1)$", fontsize=10)
    ax1.set_ylim(0.95, 1.005)
    ax1.grid(True, alpha=0.3, linestyle="--")
    ax1.legend(loc="lower left", fontsize=9)

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

    ax2.plot(pm_years, p_inv_w_pitch_m, "o-", color="#ff7f0e", lw=2, label=r"Inv-$\mathcal{W}_1(p_{\mathrm{pitch}})$")
    ax2.fill_between(pm_years, p_inv_w_pitch_m - p_inv_w_pitch_s, p_inv_w_pitch_m + p_inv_w_pitch_s, color="#ff7f0e", alpha=0.15)
    
    ax2.plot(pm_years, p_inv_w_all_m, "s--", color="#d62728", lw=1.8, label=r"Inv-$\bar{\mathcal{W}}_1(\mathrm{all\ experts})$")
    ax2.fill_between(pm_years, p_inv_w_all_m - p_inv_w_all_s, p_inv_w_all_m + p_inv_w_all_s, color="#d62728", alpha=0.15)

    ax2.set_title("(b) Penmanshiel (8.6 Years, 15 Turbines)\nRepresentation Similarity vs Commissioning", fontsize=11, fontweight="bold")
    ax2.set_xlabel("Calendar Year", fontsize=10)
    ax2.set_ylabel(r"Inverse Wasserstein Similarity $1 / (1 + \mathcal{W}_1)$", fontsize=10)
    ax2.set_ylim(0.92, 1.005)
    ax2.grid(True, alpha=0.3, linestyle="--")
    ax2.legend(loc="lower left", fontsize=9)

    # 3. Ground-Truth Boundary Alignment (NMI) over time
    ax3 = axes[2]
    # Filter valid NMI
    km_valid_nmi = km[km["nmi_ground_truth"] > 0].groupby("calendar_year")["nmi_ground_truth"].agg(["mean", "std"])
    pm_valid_nmi = pm[pm["nmi_ground_truth"] > 0].groupby("calendar_year")["nmi_ground_truth"].agg(["mean", "std"])

    ax3.plot(km_valid_nmi.index, km_valid_nmi["mean"], "o-", color="#1f77b4", lw=2, label="Kelmarsh Ground-Truth NMI")
    ax3.fill_between(km_valid_nmi.index, km_valid_nmi["mean"] - km_valid_nmi["std"], km_valid_nmi["mean"] + km_valid_nmi["std"], color="#1f77b4", alpha=0.15)

    if not pm_valid_nmi.empty:
        ax3.plot(pm_valid_nmi.index, pm_valid_nmi["mean"], "s--", color="#ff7f0e", lw=1.8, label="Penmanshiel Ground-Truth NMI")
        ax3.fill_between(pm_valid_nmi.index, pm_valid_nmi["mean"] - pm_valid_nmi["std"], pm_valid_nmi["mean"] + pm_valid_nmi["std"], color="#ff7f0e", alpha=0.15)

    ax3.set_title("(c) Physical Boundary Alignment (NMI)\nMulti-Year Ground-Truth Tracking", fontsize=11, fontweight="bold")
    ax3.set_xlabel("Calendar Year", fontsize=10)
    ax3.set_ylabel("Normalized Mutual Information (NMI)", fontsize=10)
    ax3.set_ylim(0.0, 0.45)
    ax3.grid(True, alpha=0.3, linestyle="--")
    ax3.legend(loc="upper right", fontsize=9)

    out_dirs = [
        Path("artifacts/multiyear_gate_representation_audit"),
        Path("artifacts/paper_assets/figures"),
    ]
    for od in out_dirs:
        od.mkdir(parents=True, exist_ok=True)
        fig.savefig(od / "figure_gate_representation_stability.pdf", bbox_inches="tight")
        fig.savefig(od / "figure_gate_representation_stability.png", bbox_inches="tight")
    print("Saved figure_gate_representation_stability to audit and paper_assets directories.")

if __name__ == "__main__":
    plot_gate_stability()
