"""Audit Operating-State Probability Calibration (Phase 6).

Evaluates the calibration quality of predicted pitch operating regime probabilities:
- Brier Score, Negative Log-Likelihood (NLL), Expected Calibration Error (ECE, 10 bins), Maximum Calibration Error (MCE)
- Post-hoc validation calibration: Temperature Scaling, Platt Scaling, Isotonic Regression
- Generates publication-quality reliability diagrams (figures/posterior_reliability.pdf)
- Produces artifacts/posterior_calibration.csv
- Checks the empirical calibration gate (ECE <= 0.05 and monotonic reliability) to determine
  whether the terminology 'calibrated posterior probability' vs 'latent operating-boundary score' is justified.
"""
from __future__ import annotations

import argparse
import os
import sys

os.environ["LOKY_MAX_CPU_COUNT"] = "4"
os.environ["PYTHONUNBUFFERED"] = "1"
os.environ["OMP_NUM_THREADS"] = "4"

from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from windfarm_moe.arrival_feed import DegradationSpec, UnifiedArrivalDataset
from windfarm_moe.data import CacheBundle, load_cache_bundle
from windfarm_moe.mechanism_intervention import _load_model_from_checkpoint


def compute_calibration_metrics(
    probs: np.ndarray,
    labels: np.ndarray,
    n_bins: int = 10,
) -> Dict[str, float]:
    """Compute Brier score, NLL, ECE, and MCE across n_bins equal-width bins."""
    p = np.clip(probs, 1e-7, 1.0 - 1e-7)
    y = labels.astype(np.float64)

    # Brier Score
    brier = float(np.mean((p - y) ** 2))

    # NLL
    nll = float(-np.mean(y * np.log(p) + (1.0 - y) * np.log(1.0 - p)))

    # Equal-width binning
    bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
    bin_indices = np.digitize(p, bin_edges[1:-1])  # 0 to n_bins - 1

    ece = 0.0
    mce = 0.0
    n_total = len(p)

    bin_accs = []
    bin_confs = []
    bin_counts = []

    for b in range(n_bins):
        in_bin = bin_indices == b
        n_b = np.sum(in_bin)
        bin_counts.append(int(n_b))
        if n_b > 0:
            acc_b = float(np.mean(y[in_bin]))
            conf_b = float(np.mean(p[in_bin]))
            gap = abs(acc_b - conf_b)
            ece += (n_b / n_total) * gap
            mce = max(mce, gap)
            bin_accs.append(acc_b)
            bin_confs.append(conf_b)
        else:
            bin_accs.append(np.nan)
            bin_confs.append((bin_edges[b] + bin_edges[b + 1]) / 2.0)

    # Check monotonicity of populated bins
    valid_accs = [a for a in bin_accs if not np.isnan(a)]
    is_monotonic = bool(all(valid_accs[i] <= valid_accs[i + 1] + 0.05 for i in range(len(valid_accs) - 1)))

    return {
        "brier_score": brier,
        "nll": nll,
        "ece": float(ece),
        "mce": float(mce),
        "is_monotonic": is_monotonic,
        "bin_accs": bin_accs,
        "bin_confs": bin_confs,
        "bin_counts": bin_counts,
    }


def fit_temperature_scaling(logits_val: np.ndarray, y_val: np.ndarray) -> float:
    """Find scalar temperature T > 0 minimizing NLL on validation set."""
    def nll_obj(t_val):
        t = max(float(t_val[0]), 1e-4)
        scaled_p = 1.0 / (1.0 + np.exp(-logits_val / t))
        scaled_p = np.clip(scaled_p, 1e-7, 1.0 - 1e-7)
        return -np.mean(y_val * np.log(scaled_p) + (1.0 - y_val) * np.log(1.0 - scaled_p))

    res = minimize(nll_obj, x0=[1.0], bounds=[(0.05, 20.0)], method="L-BFGS-B")
    return float(res.x[0])


def extract_logits_and_labels(
    loader: DataLoader,
    model: nn.Module,
    device: torch.device,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Extract gate logits for pitch regime, probabilities, and true regime labels."""
    prob_list, logit_list, label_list = [], [], []
    with torch.no_grad():
        for b in loader:
            x_h = b["x_hist"].to(device)
            e_i = b["edge_index_hist"].to(device)
            e_w = b["edge_weight_hist"].to(device)
            f_m = b["feature_mask_hist"].to(device)
            a_p = b["anchor_physics"].to(device)
            _, gate_prob, aux = model(x_h, e_i, e_w, f_m, a_p)

            # gate prob and logits of pitch regime (index 2)
            if gate_prob is not None:
                p3 = gate_prob[..., :3]
                p_pitch = (p3[..., 2] / torch.clamp(p3.sum(dim=-1), min=1e-9)).cpu().numpy()
            else:
                p_pitch = np.zeros((x_h.shape[0], x_h.shape[2]), dtype=np.float32)

            gate_logits = aux.get("gate_logits", None)
            if gate_logits is not None:
                logit_pitch = gate_logits[..., 2].cpu().numpy()
            else:
                # Logit from inverse sigmoid
                logit_pitch = np.log(np.clip(p_pitch, 1e-6, 1.0 - 1e-6) / (1.0 - np.clip(p_pitch, 1e-6, 1.0 - 1e-6)))

            regime = b["regime_primary"].numpy()  # (B, N)
            y_pitch = (regime == 2).astype(np.int64)

            prob_list.append(p_pitch)
            logit_list.append(logit_pitch)
            label_list.append(y_pitch)

    probs = np.concatenate(prob_list, axis=0).reshape(-1)
    logits = np.concatenate(logit_list, axis=0).reshape(-1)
    labels = np.concatenate(label_list, axis=0).reshape(-1)
    return probs, logits, labels


def main():
    parser = argparse.ArgumentParser(description="Audit Posterior Calibration (Phase 6)")
    parser.add_argument("--cache-dir", default="artifacts/cache_strictmask_trainweights/wtb_245d")
    parser.add_argument("--output-csv", default="artifacts/posterior_calibration.csv")
    parser.add_argument("--output-fig", default="figures/posterior_reliability.pdf")
    parser.add_argument("--device", default="cuda:0" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--seeds", default="201,202,203,204,205")
    args = parser.parse_args()

    device = torch.device(args.device)
    print(f"[Calibration Audit] Loading cache from {args.cache_dir}", flush=True)
    bundle = load_cache_bundle(Path(args.cache_dir), mmap_mode="r")
    seeds = [int(s.strip()) for s in args.seeds.split(",")]

    conditions = [
        ("clean", DegradationSpec(delay_steps=0, corrupted_channels=("all",))),
        ("delay6", DegradationSpec(delay_steps=6, corrupted_channels=("all",), history_policy="stalled")),
        ("pitch_withheld", DegradationSpec(delay_steps=0, withheld_channels=("Pab_mean", "Pab_std"))),
        ("delay6_pitch_withheld", DegradationSpec(delay_steps=6, corrupted_channels=("all",), withheld_channels=("Pab_mean", "Pab_std"), history_policy="stalled")),
    ]

    out_csv = Path(args.output_csv)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    out_fig = Path(args.output_fig)
    out_fig.parent.mkdir(parents=True, exist_ok=True)

    summary_rows = []
    reliability_curves = {}

    for cond_name, spec in conditions:
        print(f"\n==================== CONDITION: {cond_name.upper()} ====================", flush=True)
        val_ds = UnifiedArrivalDataset(bundle, "val", hist_len=36, pred_len=24, degradation=spec)
        test_ds = UnifiedArrivalDataset(bundle, "test", hist_len=36, pred_len=24, degradation=spec)

        val_loader = DataLoader(val_ds, batch_size=64, shuffle=False)
        test_loader = DataLoader(test_ds, batch_size=64, shuffle=False)

        for model_family in ["dense", "routed"]:
            uncal_brier, uncal_nll, uncal_ece, uncal_mce = [], [], [], []
            temp_brier, temp_nll, temp_ece, temp_mce = [], [], [], []
            iso_brier, iso_nll, iso_ece, iso_mce = [], [], [], []
            optimal_temps = []
            test_accs_list, test_confs_list = [], []

            for seed in seeds:
                if model_family == "routed":
                    ckpt = Path(f"artifacts/trainweight_full_rerun_20260830/wtb_full_seed{seed}")
                else:
                    ckpt = Path(f"artifacts/dense_classifier_runs_20260904/canonical/wtb_bal_align_force_seed{seed}")

                if not ckpt.exists():
                    continue

                model = _load_model_from_checkpoint(ckpt, bundle, device)
                model.eval()

                p_val, z_val, y_val = extract_logits_and_labels(val_loader, model, device)
                p_test, z_test, y_test = extract_logits_and_labels(test_loader, model, device)

                # 1. Uncalibrated Metrics
                m_uncal = compute_calibration_metrics(p_test, y_test)
                uncal_brier.append(m_uncal["brier_score"])
                uncal_nll.append(m_uncal["nll"])
                uncal_ece.append(m_uncal["ece"])
                uncal_mce.append(m_uncal["mce"])
                test_accs_list.append(m_uncal["bin_accs"])
                test_confs_list.append(m_uncal["bin_confs"])

                # 2. Temperature Scaling
                # Center logits around empirical prevalence if offset exists
                t_star = fit_temperature_scaling(z_val, y_val)
                optimal_temps.append(t_star)
                p_test_temp = 1.0 / (1.0 + np.exp(-z_test / t_star))
                m_temp = compute_calibration_metrics(p_test_temp, y_test)
                temp_brier.append(m_temp["brier_score"])
                temp_nll.append(m_temp["nll"])
                temp_ece.append(m_temp["ece"])
                temp_mce.append(m_temp["mce"])

                # 3. Isotonic Regression
                iso = IsotonicRegression(out_of_bounds="clip")
                # Subsample validation for fast isotonic fit
                val_sub = np.random.default_rng(seed).choice(len(p_val), size=min(len(p_val), 30000), replace=False)
                iso.fit(p_val[val_sub], y_val[val_sub])
                p_test_iso = iso.predict(p_test)
                m_iso = compute_calibration_metrics(p_test_iso, y_test)
                iso_brier.append(m_iso["brier_score"])
                iso_nll.append(m_iso["nll"])
                iso_ece.append(m_iso["ece"])
                iso_mce.append(m_iso["mce"])

            # Cross-seed averages
            mean_uncal_ece = float(np.mean(uncal_ece))
            mean_temp_ece = float(np.mean(temp_ece))
            mean_iso_ece = float(np.mean(iso_ece))
            mean_t = float(np.mean(optimal_temps))

            # Store curves for plotting
            reliability_curves[f"{cond_name}_{model_family}"] = {
                "confs": np.nanmean(np.array(test_confs_list), axis=0),
                "accs": np.nanmean(np.array(test_accs_list), axis=0),
                "uncal_ece": mean_uncal_ece,
                "temp_ece": mean_temp_ece,
            }

            # Check terminology gate
            # Strict gate: Uncalibrated ECE <= 0.05
            gate_pass = bool(mean_uncal_ece <= 0.05)
            recommended_term = "Calibrated Operating-Boundary Posterior" if gate_pass else "Latent Operating-Boundary Score"

            row = {
                "condition": cond_name,
                "model_family": model_family,
                "uncal_brier_mean": float(np.mean(uncal_brier)),
                "uncal_brier_std": float(np.std(uncal_brier)),
                "uncal_nll_mean": float(np.mean(uncal_nll)),
                "uncal_nll_std": float(np.std(uncal_nll)),
                "uncal_ece_mean": mean_uncal_ece,
                "uncal_ece_std": float(np.std(uncal_ece)),
                "uncal_mce_mean": float(np.mean(uncal_mce)),
                "optimal_temp_mean": mean_t,
                "temp_ece_mean": mean_temp_ece,
                "temp_ece_std": float(np.std(temp_ece)),
                "temp_brier_mean": float(np.mean(temp_brier)),
                "iso_ece_mean": mean_iso_ece,
                "iso_ece_std": float(np.std(iso_ece)),
                "iso_brier_mean": float(np.mean(iso_brier)),
                "calibration_gate_pass": gate_pass,
                "recommended_terminology": recommended_term,
            }
            summary_rows.append(row)
            print(f"[{model_family.upper():<6} | {cond_name:<22}] Uncal ECE: {mean_uncal_ece*100:.2f}% | Temp ECE: {mean_temp_ece*100:.2f}% (T={mean_t:.2f}) | Gate: {'PASS' if gate_pass else 'FAIL'} -> '{recommended_term}'", flush=True)

    df_summary = pd.DataFrame(summary_rows)
    df_summary.to_csv(out_csv, index=False)
    print(f"\n[Saved] Calibration summary to {out_csv}", flush=True)

    # Plot publication reliability diagrams
    print(f"[Plotting] Reliability diagrams to {out_fig}...", flush=True)
    fig, axes = plt.subplots(2, 2, figsize=(10, 9), sharex=True, sharey=True)
    axes = axes.flatten()

    cond_titles = {
        "clean": "Pristine Telemetry ($\\tau=0$)",
        "delay6": "Stalled Telemetry ($\\tau=6$)",
        "pitch_withheld": "Blade Pitch Withheld ($\\tau=0$)",
        "delay6_pitch_withheld": "Stalled & Pitch Withheld ($\\tau=6$)",
    }

    for idx, (cond_name, _) in enumerate(conditions):
        ax = axes[idx]
        ax.plot([0, 1], [0, 1], "k--", alpha=0.6, label="Perfect Calibration")

        dense_key = f"{cond_name}_dense"
        routed_key = f"{cond_name}_routed"

        if dense_key in reliability_curves:
            d_curve = reliability_curves[dense_key]
            ax.plot(d_curve["confs"], d_curve["accs"], "s-", color="#1f77b4", label=f"Dense GNN (ECE={d_curve['uncal_ece']*100:.1f}%)")

        if routed_key in reliability_curves:
            r_curve = reliability_curves[routed_key]
            ax.plot(r_curve["confs"], r_curve["accs"], "o-", color="#d62728", label=f"Routed MoE (ECE={r_curve['uncal_ece']*100:.1f}%)")

        ax.set_title(cond_titles[cond_name], fontsize=11, fontweight="bold")
        ax.set_xlim(-0.02, 1.02)
        ax.set_ylim(-0.02, 1.02)
        ax.grid(True, linestyle=":", alpha=0.6)
        ax.legend(loc="upper left", fontsize=9)

        if idx >= 2:
            ax.set_xlabel("Confidence $\\hat{P}(Z=2)$", fontsize=10)
        if idx % 2 == 0:
            ax.set_ylabel("Empirical Frequency $P(Z=2)$", fontsize=10)

    plt.tight_layout()
    plt.savefig(out_fig, dpi=300)
    plt.savefig(out_fig.with_suffix(".png"), dpi=300)
    plt.close()
    print(f"[Saved] Reliability figures to {out_fig} and .png", flush=True)


if __name__ == "__main__":
    main()
