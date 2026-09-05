"""Aggregate and compute paired bootstrap confidence intervals for IEC 61400-12-1 multi-year rolling evaluation.

Reads per-GPU results across seeds 201-205, computes 20,000 paired bootstrap resamples,
and produces convergent confidence intervals and guard metadata.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


def summarize_farm(out_dir: Path, farm: str, rhos: list[float] = [10.0, 5.0, 20.0]):
    csvs = list(out_dir.glob(f"{farm}_gpu*_results.csv"))
    if csvs:
        dfs = [pd.read_csv(p) for p in csvs]
        df = pd.concat(dfs, ignore_index=True).drop_duplicates(subset=["farm", "seed", "window", "policy", "rho"])
        df.to_csv(out_dir / f"{farm}_rolling_by_seed.csv", index=False)
        print(f"[{farm}] Aggregated {len(df)} rows across {df['seed'].nunique()} seeds: {sorted(df['seed'].unique())}")
    elif (out_dir / f"{farm}_rolling_by_seed.csv").exists():
        df = pd.read_csv(out_dir / f"{farm}_rolling_by_seed.csv")
        print(f"[{farm}] Loaded {len(df)} rows from existing {farm}_rolling_by_seed.csv across {df['seed'].nunique()} seeds")
    else:
        print(f"No results found for {farm} in {out_dir}")
        return None

    rng = np.random.default_rng(42)
    summary = []

    windows = sorted(df["window"].unique())
    for win in windows:
        w_df = df[df["window"] == win]
        for rho in rhos:
            sub = w_df[w_df["rho"] == rho]
            for strat in ["soft-gate-bin", "soft-pab-bin"]:
                for base in ["global", "soft-pab-bin"]:
                    if strat == base:
                        continue
                    for metric in ["total_cost", "violation_rate", "shortage", "reserve"]:
                        wide = sub.pivot(index="seed", columns="policy", values=metric)
                        if strat not in wide.columns or base not in wide.columns:
                            continue
                        d = (wide[strat] - wide[base]).dropna().to_numpy()
                        if len(d) == 0:
                            continue
                        boots = rng.choice(d, size=(20000, len(d)), replace=True).mean(axis=1)
                        ci_low = float(np.percentile(boots, 2.5))
                        ci_high = float(np.percentile(boots, 97.5))
                        summary.append({
                            "farm": farm,
                            "window": win,
                            "rho": rho,
                            "metric": metric,
                            "strategy": strat,
                            "baseline": base,
                            "delta_mean": float(d.mean()),
                            "ci_low": ci_low,
                            "ci_high": ci_high,
                            "ci_excludes_zero": bool(ci_low > 0.0 or ci_high < 0.0),
                            "n_seeds": int(len(d)),
                            "strat_mean": float(wide[strat].mean()),
                            "base_mean": float(wide[base].mean()),
                        })

    # Compute Walk-Forward Rolling Pooled Window (summing across all rolling folds)
    rolling_folds = sorted([w for w in df["window"].unique() if "rolling_" in w])
    if rolling_folds:
        print(f"[{farm}] Computing walkforward_rolling_pooled across {len(rolling_folds)} folds: {rolling_folds}")
        rf_df = df[df["window"].isin(rolling_folds)]
        for rho in rhos:
            sub = rf_df[rf_df["rho"] == rho]
            for strat in ["soft-gate-bin", "soft-pab-bin"]:
                for base in ["global", "soft-pab-bin"]:
                    if strat == base:
                        continue
                    for metric in ["total_cost", "shortage", "reserve"]:
                        grouped = sub.groupby(["seed", "policy"])[metric].sum().unstack()
                        if strat not in grouped.columns or base not in grouped.columns:
                            continue
                        d = (grouped[strat] - grouped[base]).dropna().to_numpy()
                        if len(d) == 0:
                            continue
                        boots = rng.choice(d, size=(20000, len(d)), replace=True).mean(axis=1)
                        ci_low = float(np.percentile(boots, 2.5))
                        ci_high = float(np.percentile(boots, 97.5))
                        summary.append({
                            "farm": farm,
                            "window": "walkforward_rolling_pooled",
                            "rho": rho,
                            "metric": metric,
                            "strategy": strat,
                            "baseline": base,
                            "delta_mean": float(d.mean()),
                            "ci_low": ci_low,
                            "ci_high": ci_high,
                            "ci_excludes_zero": bool(ci_low > 0.0 or ci_high < 0.0),
                            "n_seeds": int(len(d)),
                            "strat_mean": float(grouped[strat].mean()),
                            "base_mean": float(grouped[base].mean()),
                        })

    sdf = pd.DataFrame(summary)
    summary_path = out_dir / f"{farm}_rolling_paired_summary.csv"
    sdf.to_csv(summary_path, index=False)
    print(f"[{farm}] Summary written to {summary_path}")

    # Print highlights at rho=10 for total_cost
    cost_summary = sdf[(sdf["rho"] == 10.0) & (sdf["metric"] == "total_cost") & (sdf["strategy"] == "soft-gate-bin") & (sdf["baseline"] == "global")]
    print(f"\n=== [{farm}] Soft-gate vs Global Total Cost (rho=10) ===")
    print(cost_summary[["window", "delta_mean", "ci_low", "ci_high", "ci_excludes_zero", "n_seeds"]].to_string(index=False))
    return sdf


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="/root/paper3_audit_rerun_20260830/artifacts/iec_density_rolling_eval")
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    kelmarsh_summary = summarize_farm(out_dir, "kelmarsh")
    penmanshiel_summary = summarize_farm(out_dir, "penmanshiel")
    lhb_summary = summarize_farm(out_dir, "la_haute_borne")

    guard = {
        "status": "iec_density_multiyear_rolling_completed",
        "kelmarsh_completed": kelmarsh_summary is not None,
        "penmanshiel_completed": penmanshiel_summary is not None,
        "lhb_completed": lhb_summary is not None,
    }
    if kelmarsh_summary is not None:
        k_pooled = kelmarsh_summary[(kelmarsh_summary["window"] == "pooled_multiyear_full") & (kelmarsh_summary["rho"] == 10.0) & (kelmarsh_summary["metric"] == "total_cost") & (kelmarsh_summary["strategy"] == "soft-gate-bin") & (kelmarsh_summary["baseline"] == "global")]
        if not k_pooled.empty:
            guard["kelmarsh_static_freeze_delta_cost"] = float(k_pooled["delta_mean"].iloc[0])
            guard["kelmarsh_static_freeze_ci_95"] = [float(k_pooled["ci_low"].iloc[0]), float(k_pooled["ci_high"].iloc[0])]
            guard["kelmarsh_static_freeze_ci_excludes_zero"] = bool(k_pooled["ci_excludes_zero"].iloc[0])
        k_wf = kelmarsh_summary[(kelmarsh_summary["window"] == "walkforward_rolling_pooled") & (kelmarsh_summary["rho"] == 10.0) & (kelmarsh_summary["metric"] == "total_cost") & (kelmarsh_summary["strategy"] == "soft-gate-bin") & (kelmarsh_summary["baseline"] == "global")]
        if not k_wf.empty:
            guard["kelmarsh_walkforward_pooled_delta_cost"] = float(k_wf["delta_mean"].iloc[0])
            guard["kelmarsh_walkforward_pooled_ci_95"] = [float(k_wf["ci_low"].iloc[0]), float(k_wf["ci_high"].iloc[0])]
            guard["kelmarsh_walkforward_pooled_ci_excludes_zero"] = bool(k_wf["ci_excludes_zero"].iloc[0])

    if penmanshiel_summary is not None:
        p_pooled = penmanshiel_summary[(penmanshiel_summary["window"] == "pooled_multiyear_full") & (penmanshiel_summary["rho"] == 10.0) & (penmanshiel_summary["metric"] == "total_cost") & (penmanshiel_summary["strategy"] == "soft-gate-bin") & (penmanshiel_summary["baseline"] == "global")]
        if not p_pooled.empty:
            guard["penmanshiel_static_freeze_delta_cost"] = float(p_pooled["delta_mean"].iloc[0])
            guard["penmanshiel_static_freeze_ci_95"] = [float(p_pooled["ci_low"].iloc[0]), float(p_pooled["ci_high"].iloc[0])]
            guard["penmanshiel_static_freeze_ci_excludes_zero"] = bool(p_pooled["ci_excludes_zero"].iloc[0])
        p_wf = penmanshiel_summary[(penmanshiel_summary["window"] == "walkforward_rolling_pooled") & (penmanshiel_summary["rho"] == 10.0) & (penmanshiel_summary["metric"] == "total_cost") & (penmanshiel_summary["strategy"] == "soft-gate-bin") & (penmanshiel_summary["baseline"] == "global")]
        if not p_wf.empty:
            guard["penmanshiel_walkforward_pooled_delta_cost"] = float(p_wf["delta_mean"].iloc[0])
            guard["penmanshiel_walkforward_pooled_ci_95"] = [float(p_wf["ci_low"].iloc[0]), float(p_wf["ci_high"].iloc[0])]
            guard["penmanshiel_walkforward_pooled_ci_excludes_zero"] = bool(p_wf["ci_excludes_zero"].iloc[0])

    if lhb_summary is not None:
        l_pooled = lhb_summary[(lhb_summary["window"] == "pooled_annual_full") & (lhb_summary["rho"] == 10.0) & (lhb_summary["metric"] == "total_cost") & (lhb_summary["strategy"] == "soft-gate-bin") & (lhb_summary["baseline"] == "global")]
        if not l_pooled.empty:
            guard["lhb_pooled_delta_cost"] = float(l_pooled["delta_mean"].iloc[0])
            guard["lhb_pooled_ci_95"] = [float(l_pooled["ci_low"].iloc[0]), float(l_pooled["ci_high"].iloc[0])]
            guard["lhb_pooled_ci_excludes_zero"] = bool(l_pooled["ci_excludes_zero"].iloc[0])
        l_wf = lhb_summary[(lhb_summary["window"] == "walkforward_rolling_pooled") & (lhb_summary["rho"] == 10.0) & (lhb_summary["metric"] == "total_cost") & (lhb_summary["strategy"] == "soft-gate-bin") & (lhb_summary["baseline"] == "global")]
        if not l_wf.empty:
            guard["lhb_walkforward_pooled_delta_cost"] = float(l_wf["delta_mean"].iloc[0])
            guard["lhb_walkforward_pooled_ci_95"] = [float(l_wf["ci_low"].iloc[0]), float(l_wf["ci_high"].iloc[0])]
            guard["lhb_walkforward_pooled_ci_excludes_zero"] = bool(l_wf["ci_excludes_zero"].iloc[0])

    guard_file = out_dir / "iec_rolling_guard.json"
    guard_file.write_text(json.dumps(guard, indent=2), encoding="utf-8")
    print(f"\nFinal guard saved to {guard_file}:")
    print(json.dumps(guard, indent=2))


if __name__ == "__main__":
    main()
