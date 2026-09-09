"""Wind Farm PCC Bus-Level Power Aggregation & Reserve Sizing Evaluation Script.

Evaluates wind farm Point of Common Coupling (PCC) aggregated power and reserve sizing
across 134 WTB wind turbines under:
  (a) global-pcc-quantile
  (b) gaussian-pcc-param
  (c) soft-pab-aggregate
  (d) joint-posterior-aggregate

Key focus: Transitional regime where 10% to 90% of turbines are in regime 2 (pitching),
testing whether spatial portfolio smoothing at the farm bus eliminates or preserves
the economic value of the jointly-learned boundary-risk posterior.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
from scipy import stats


QUANTILE_GRID = [0.50, 0.60, 0.70, 0.80, 0.85, 0.90, 0.95, 0.975, 0.99]
DT = 1.0 / 6.0  # 10-minute dispatch interval (in hours)


def ppitch_from_gate(gate: np.ndarray) -> np.ndarray:
    """Extract P(pitch) from gate probabilities (class index 2)."""
    p3 = gate[..., :3]
    return p3[..., 2] / np.maximum(p3.sum(axis=-1), 1e-9)


def resolve_seeds(base_dir: Path, requested_seeds: List[int]) -> List[int]:
    """Resolve seed directories, falling back to discovered seeds if requested are missing."""
    available = []
    for s in requested_seeds:
        if (base_dir / f"wtb_full_seed{s}").exists():
            available.append(s)
    if available:
        return available

    # Fallback to any existing wtb_full_seed*
    discovered = []
    for p in sorted(base_dir.glob("wtb_full_seed*")):
        try:
            num = int(p.name.replace("wtb_full_seed", ""))
            discovered.append(num)
        except ValueError:
            pass
    if discovered:
        print(f"Warning: requested seeds {requested_seeds} not found in {base_dir}. Using discovered seeds: {discovered}")
        return discovered
    raise FileNotFoundError(f"No wtb_full_seed* directories found in {base_dir}")


def fit_optimal_quantile(s_val: np.ndarray, rho: float) -> Tuple[float, float, float]:
    """Fit optimal reserve r from quantile grid to minimize total cost on validation."""
    best = None
    for q in QUANTILE_GRID:
        r = float(np.quantile(s_val, q))
        shortage = np.maximum(s_val - r, 0.0)
        cost = (r * s_val.size + rho * shortage.sum()) * DT
        if best is None or cost < best[0]:
            best = (cost, q, r)
    return best[0], best[1], best[2]


def fit_gaussian_reserve(residuals_val: np.ndarray, s_val: np.ndarray, rho: float) -> Tuple[float, float]:
    """Fit parametric Gaussian reserve r = max(0, mu + z_q * sigma) minimizing cost on validation."""
    mu = float(np.mean(residuals_val))
    sigma = float(np.std(residuals_val))
    best = None
    for q in QUANTILE_GRID:
        z = stats.norm.ppf(q)
        r = max(0.0, mu + z * sigma)
        shortage = np.maximum(s_val - r, 0.0)
        cost = (r * s_val.size + rho * shortage.sum()) * DT
        if best is None or cost < best[0]:
            best = (cost, r)
    return best[0], best[1]


def fit_binned_policy(
    s_val: np.ndarray,
    signal_val: np.ndarray,
    n_bins: int,
    rho: float
) -> Tuple[np.ndarray, Dict[int, float]]:
    """Fit quantile-binned conditional reserve policy on validation."""
    edges = np.quantile(signal_val, np.linspace(0, 1, n_bins + 1)[1:-1])
    # Handle non-unique bin edges
    if len(np.unique(edges)) < len(edges):
        edges = np.linspace(signal_val.min(), signal_val.max(), n_bins + 1)[1:-1]

    bin_assignments = np.clip(np.searchsorted(edges, signal_val), 0, n_bins - 1)
    reserves = {}
    for b in range(n_bins):
        sb = s_val[bin_assignments == b]
        if sb.size < 20:
            sb = s_val
        _, _, r = fit_optimal_quantile(sb, rho)
        reserves[b] = r
    return edges, reserves


def compute_pinball_loss(shortfall: np.ndarray, reserve: np.ndarray, q: float) -> float:
    """Compute average Pinball loss for quantile q."""
    diff = shortfall - reserve
    return float(np.mean(np.maximum(q * diff, (q - 1.0) * diff)))


def evaluate_single_seed(
    run_dir: Path,
    seed: int,
    rho: float = 10.0,
    trans_min: float = 0.10,
    trans_max: float = 0.90,
    n_bins: int = 5,
    min_active_turbines: int = 50,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Evaluate PCC aggregation for one seed under val-calibration, test-evaluation protocol."""
    # 1. Load validation metrics
    v_dir = run_dir / "val_metrics"
    v_pred = np.load(v_dir / "pred.npy")        # (N_v, 24, 134)
    v_target = np.load(v_dir / "target.npy")    # (N_v, 24, 134)
    v_mask = np.load(v_dir / "mask.npy") > 0.5  # (N_v, 24, 134)
    v_gate = np.load(v_dir / "gate_prob.npy")   # (N_v, 134, 4)
    v_anchor = np.load(v_dir / "anchor_physics.npy") # (N_v, 134, 4)
    v_reg = np.load(v_dir / "regime_primary.npy")    # (N_v, 134)
    v_reg_val = np.load(v_dir / "regime_primary_valid.npy") > 0.5

    # 2. Load test metrics
    t_dir = run_dir / "test_metrics"
    t_pred = np.load(t_dir / "pred.npy")        # (N_t, 24, 134)
    t_target = np.load(t_dir / "target.npy")    # (N_t, 24, 134)
    t_mask = np.load(t_dir / "mask.npy") > 0.5  # (N_t, 24, 134)
    t_gate = np.load(t_dir / "gate_prob.npy")   # (N_t, 134, 4)
    t_anchor = np.load(t_dir / "anchor_physics.npy")
    t_reg = np.load(t_dir / "regime_primary.npy")
    t_reg_val = np.load(t_dir / "regime_primary_valid.npy") > 0.5

    H = v_pred.shape[1]
    n_turbines = v_pred.shape[2]
    q_target = 1.0 - 1.0 / rho if rho > 1.0 else 0.50

    # 3. Farm-level aggregation across turbines (Causally Symmetric Operational Protocol)
    # At issue time t=0, dispatch operator knows which turbines are online and reporting.
    # To prevent future target mask leakage into the dispatch forecast:
    # - Model prediction P_pred aggregates turbines verified online at anchor time t=0.
    # - Evaluation enforces joint validity (anchor online AND target valid) to ensure fair pairing.
    v_anchor_avail = v_mask[:, 0:1, :]  # (N_v, 1, n_turbines)
    t_anchor_avail = t_mask[:, 0:1, :]  # (N_t, 1, n_turbines)

    v_eval_mask = v_anchor_avail & v_mask
    t_eval_mask = t_anchor_avail & t_mask

    v_P_pred = np.sum(np.where(v_eval_mask, v_pred, 0.0), axis=-1)      # (N_v, H)
    v_P_target = np.sum(np.where(v_eval_mask, v_target, 0.0), axis=-1)  # (N_v, H)
    v_active = v_eval_mask.sum(axis=-1)                                 # (N_v, H)
    v_valid_step = v_active >= min_active_turbines

    t_P_pred = np.sum(np.where(t_eval_mask, t_pred, 0.0), axis=-1)      # (N_t, H)
    t_P_target = np.sum(np.where(t_eval_mask, t_target, 0.0), axis=-1)  # (N_t, H)
    t_active = t_eval_mask.sum(axis=-1)                                 # (N_t, H)
    t_valid_step = t_active >= min_active_turbines

    # Shortfall: s = max(P_pred - P_target, 0)
    v_shortfall = np.maximum(v_P_pred - v_P_target, 0.0)
    t_shortfall = np.maximum(t_P_pred - t_P_target, 0.0)
    v_res = v_P_pred - v_P_target
    t_res = t_P_pred - t_P_target

    # 4. Transitional regime identification:
    # fraction of turbines in regime 2 (pitching) at issue time
    v_pitch_count = np.sum((v_reg == 2) & v_reg_val, axis=1)
    v_valid_turb = np.maximum(v_reg_val.sum(axis=1), 1)
    v_pitch_ratio = v_pitch_count / v_valid_turb

    t_pitch_count = np.sum((t_reg == 2) & t_reg_val, axis=1)
    t_valid_turb = np.maximum(t_reg_val.sum(axis=1), 1)
    t_pitch_ratio = t_pitch_count / t_valid_turb

    v_trans_step = (v_pitch_ratio >= trans_min) & (v_pitch_ratio <= trans_max)
    t_trans_step = (t_pitch_ratio >= trans_min) & (t_pitch_ratio <= trans_max)

    # 5. Farm-level feature signals:
    # (a) soft-pab: average pitch angle Pab across turbines at issue time
    v_pab = v_anchor[..., 1]  # (N_v, 134)
    t_pab = t_anchor[..., 1]  # (N_t, 134)
    v_farm_pab = np.mean(v_pab, axis=1)
    t_farm_pab = np.mean(t_pab, axis=1)

    # (b) joint-posterior: average gate P(pitch) across turbines at issue time
    v_ppitch = ppitch_from_gate(v_gate)
    t_ppitch = ppitch_from_gate(t_gate)
    v_farm_ppitch = np.mean(v_ppitch, axis=1)
    t_farm_ppitch = np.mean(t_ppitch, axis=1)

    eval_conditions = [
        ("transitional", v_trans_step, t_trans_step),
        ("all_steps", np.ones_like(v_trans_step, dtype=bool), np.ones_like(t_trans_step, dtype=bool)),
    ]

    records = []
    regime_stats = {
        "seed": seed,
        "total_test_windows": int(t_pred.shape[0]),
        "transitional_test_windows": int(np.sum(t_trans_step)),
        "transitional_fraction": float(np.mean(t_trans_step)),
        "mean_active_turbines": float(np.mean(t_active[t_valid_step])),
    }

    for cond_name, v_cond_step, t_cond_step in eval_conditions:
        v_sel = np.repeat(v_cond_step[:, None], H, axis=1) & v_valid_step
        t_sel = np.repeat(t_cond_step[:, None], H, axis=1) & t_valid_step

        s_v = v_shortfall[v_sel]
        s_t = t_shortfall[t_sel]
        res_v = v_res[v_sel]

        v_pab_cells = np.repeat(v_farm_pab[:, None], H, axis=1)[v_sel]
        t_pab_cells = np.repeat(t_farm_pab[:, None], H, axis=1)[t_sel]

        v_gate_cells = np.repeat(v_farm_ppitch[:, None], H, axis=1)[v_sel]
        t_gate_cells = np.repeat(t_farm_ppitch[:, None], H, axis=1)[t_sel]

        n_test_cells = int(s_t.size)
        if n_test_cells == 0:
            continue

        # Strategy 1: Global PCC Quantile
        _, _, r_global_scalar = fit_optimal_quantile(s_v, rho)
        r_global = np.full(n_test_cells, r_global_scalar)

        # Strategy 2: Gaussian PCC Parametric
        _, r_gauss_scalar = fit_gaussian_reserve(res_v, s_v, rho)
        r_gauss = np.full(n_test_cells, r_gauss_scalar)

        # Strategy 3: Continuous Soft-Pab Aggregate Rule
        edges_pab, res_pab_map = fit_binned_policy(s_v, v_pab_cells, n_bins, rho)
        bin_t_pab = np.clip(np.searchsorted(edges_pab, t_pab_cells), 0, n_bins - 1)
        r_soft_pab = np.array([res_pab_map[b] for b in bin_t_pab])

        # Strategy 4: Jointly-Learned Posterior Weighted Aggregate
        edges_gate, res_gate_map = fit_binned_policy(s_v, v_gate_cells, n_bins, rho)
        bin_t_gate = np.clip(np.searchsorted(edges_gate, t_gate_cells), 0, n_bins - 1)
        r_joint_post = np.array([res_gate_map[b] for b in bin_t_gate])

        policies = {
            "global-pcc-quantile": r_global,
            "gaussian-pcc-param": r_gauss,
            "soft-pab-aggregate": r_soft_pab,
            "joint-posterior-aggregate": r_joint_post,
        }

        for pol_name, r_arr in policies.items():
            shortage = np.maximum(s_t - r_arr, 0.0)
            res_cost = float(r_arr.sum() * DT)
            short_cost = float(rho * shortage.sum() * DT)
            tot_cost = res_cost + short_cost
            viol_rate = float(np.mean(s_t > r_arr))
            pb_loss = compute_pinball_loss(s_t, r_arr, q_target)

            records.append({
                "seed": seed,
                "condition": cond_name,
                "policy": pol_name,
                "rho": rho,
                "total_cost": tot_cost,
                "reserve_cost": res_cost,
                "shortage_cost": short_cost,
                "shortage_energy": float(shortage.sum() * DT),
                "violation_rate": viol_rate,
                "pinball_loss": pb_loss,
                "n_cells": n_test_cells,
                "mean_reserve_kw": float(np.mean(r_arr)),
            })

    return records, regime_stats


def compute_paired_bootstrap(
    df_raw: pd.DataFrame,
    rhos: List[float],
    n_bootstraps: int = 20000,
    rng: np.random.Generator = None
) -> pd.DataFrame:
    """Compute seed-paired differences and 95% bootstrap confidence intervals."""
    if rng is None:
        rng = np.random.default_rng(42)

    metrics = ["total_cost", "pinball_loss", "violation_rate", "shortage_energy", "reserve_cost"]
    strategies = ["joint-posterior-aggregate", "soft-pab-aggregate", "gaussian-pcc-param"]
    baselines = ["global-pcc-quantile", "gaussian-pcc-param", "soft-pab-aggregate"]

    summary_rows = []

    for cond in df_raw["condition"].unique():
        cond_df = df_raw[df_raw["condition"] == cond]
        for rho in rhos:
            sub = cond_df[cond_df["rho"] == rho]
            for strat in strategies:
                for base in baselines:
                    if strat == base:
                        continue
                    for metric in metrics:
                        wide = sub.pivot(index="seed", columns="policy", values=metric)
                        if strat not in wide.columns or base not in wide.columns:
                            continue
                        paired = (wide[strat] - wide[base]).dropna().to_numpy()
                        n_seeds = len(paired)
                        if n_seeds == 0:
                            continue

                        delta_mean = float(np.mean(paired))
                        delta_std = float(np.std(paired, ddof=1)) if n_seeds > 1 else 0.0

                        # Paired bootstrap
                        boot_samples = rng.choice(paired, size=(n_bootstraps, n_seeds), replace=True).mean(axis=1)
                        ci_low = float(np.percentile(boot_samples, 2.5))
                        ci_high = float(np.percentile(boot_samples, 97.5))

                        # Wilcoxon signed-rank test
                        w_p = np.nan
                        if n_seeds >= 5 and not np.all(paired == 0):
                            try:
                                res_w = stats.wilcoxon(paired)
                                w_p = float(res_w.pvalue)
                            except Exception:
                                pass

                        excludes_zero = bool((ci_high < 0.0) or (ci_low > 0.0))

                        summary_rows.append({
                            "condition": cond,
                            "rho": rho,
                            "metric": metric,
                            "strategy": strat,
                            "baseline": base,
                            "delta_mean": delta_mean,
                            "delta_std": delta_std,
                            "ci_low": ci_low,
                            "ci_high": ci_high,
                            "ci_excludes_zero": excludes_zero,
                            "wilcoxon_p": w_p,
                            "n_seeds": n_seeds,
                            "strat_mean": float(wide[strat].mean()),
                            "base_mean": float(wide[base].mean()),
                        })

    return pd.DataFrame(summary_rows)


def main():
    parser = argparse.ArgumentParser(description="Evaluate wind farm PCC bus-level power aggregation & reserve sizing.")
    parser.add_argument("--repo-root", default=".", help="Repository root path.")
    parser.add_argument("--suite-dir", default="artifacts/trainweight_full_rerun_20260830", help="Path to full rerun suite.")
    parser.add_argument("--output-dir", default="artifacts/farm_aggregate_reserve_20260905", help="Output directory for results.")
    parser.add_argument("--seeds", default="201,202,203,204,205", help="Comma-separated random seeds.")
    parser.add_argument("--rhos", default="10.0,5.0,20.0", help="Shortage penalty ratios.")
    parser.add_argument("--trans-min", type=float, default=0.10, help="Transitional pitching ratio lower bound.")
    parser.add_argument("--trans-max", type=float, default=0.90, help="Transitional pitching ratio upper bound.")
    parser.add_argument("--n-bins", type=int, default=5, help="Number of quantile bins.")
    parser.add_argument("--n-bootstraps", type=int, default=20000, help="Bootstrap iterations.")
    args = parser.parse_args()

    repo_root = Path(args.repo_root)
    suite_dir = (repo_root / args.suite_dir).resolve()
    out_dir = (repo_root / args.output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    requested_seeds = [int(s.strip()) for s in args.seeds.split(",") if s.strip()]
    rhos = [float(r.strip()) for r in args.rhos.split(",") if r.strip()]

    actual_seeds = resolve_seeds(suite_dir, requested_seeds)
    print(f"Executing Wind Farm PCC Bus-Level Power Aggregation across seeds: {actual_seeds}")
    print(f"Suite Directory: {suite_dir}")
    print(f"Output Directory: {out_dir}")
    print(f"Rhos: {rhos}, Transitional Range: [{args.trans_min}, {args.trans_max}], N Bins: {args.n_bins}")

    all_records = []
    regime_stats_list = []

    for seed in actual_seeds:
        run_dir = suite_dir / f"wtb_full_seed{seed}"
        print(f"Processing seed {seed} from {run_dir.name}...")
        for rho in rhos:
            records, r_stats = evaluate_single_seed(
                run_dir=run_dir,
                seed=seed,
                rho=rho,
                trans_min=args.trans_min,
                trans_max=args.trans_max,
                n_bins=args.n_bins,
            )
            all_records.extend(records)
        regime_stats_list.append(r_stats)

    df_raw = pd.DataFrame(all_records)
    raw_path = out_dir / "farm_pcc_by_seed.csv"
    df_raw.to_csv(raw_path, index=False)
    print(f"Saved raw per-seed results to {raw_path}")

    df_regime = pd.DataFrame(regime_stats_list)
    regime_path = out_dir / "farm_pcc_regime_stats.csv"
    df_regime.to_csv(regime_path, index=False)
    print(f"Saved regime statistics to {regime_path}")

    # Compute Paired Summary
    print(f"Computing paired differences and {args.n_bootstraps} bootstrap CIs...")
    df_summary = compute_paired_bootstrap(df_raw, rhos=rhos, n_bootstraps=args.n_bootstraps)
    summary_path = out_dir / "farm_pcc_paired_summary.csv"
    df_summary.to_csv(summary_path, index=False)
    print(f"Saved paired summary to {summary_path}")

    # Print summary highlights for total_cost at rho=10
    print("\n==========================================================================")
    print("=== Wind Farm PCC Aggregate Reserve Pricing Highlights (rho=10.0) ===")
    print("==========================================================================")
    trans_highlight = df_summary[
        (df_summary["condition"] == "transitional") &
        (df_summary["rho"] == 10.0) &
        (df_summary["metric"] == "total_cost")
    ]
    print("\n[Transitional Regime: 10% - 90% Turbines Pitching]")
    print(trans_highlight[["strategy", "baseline", "delta_mean", "ci_low", "ci_high", "ci_excludes_zero", "wilcoxon_p"]].to_string(index=False))

    all_highlight = df_summary[
        (df_summary["condition"] == "all_steps") &
        (df_summary["rho"] == 10.0) &
        (df_summary["metric"] == "total_cost")
    ]
    print("\n[All Farm Steps: Full Operational Envelope]")
    print(all_highlight[["strategy", "baseline", "delta_mean", "ci_low", "ci_high", "ci_excludes_zero", "wilcoxon_p"]].to_string(index=False))

    # Guard JSON for reproducibility check
    guard_data = {
        "status": "farm_aggregate_reserve_completed",
        "seeds": actual_seeds,
        "rhos": rhos,
        "n_bootstraps": args.n_bootstraps,
        "transitional_total_cost_deltas": {},
    }
    for _, row in trans_highlight.iterrows():
        key = f"{row['strategy']}_vs_{row['baseline']}"
        guard_data["transitional_total_cost_deltas"][key] = {
            "delta_mean": float(row["delta_mean"]),
            "ci_95": [float(row["ci_low"]), float(row["ci_high"])],
            "ci_excludes_zero": bool(row["ci_excludes_zero"]),
            "wilcoxon_p": None if math.isnan(row["wilcoxon_p"]) else float(row["wilcoxon_p"]),
        }

    guard_path = out_dir / "farm_pcc_guard.json"
    with open(guard_path, "w", encoding="utf-8") as f:
        json.dump(guard_data, f, indent=2)
    print(f"\nGuard metadata written to {guard_path}")


if __name__ == "__main__":
    main()
