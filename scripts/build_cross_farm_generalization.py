"""Synthesize Comprehensive Cross-Farm Generalization Table across WTB, Kelmarsh, and Penmanshiel."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd
from scipy import stats


FARMS_METADATA = {
    "wtb": {
        "display_name": "WTB (China)",
        "turbines": 134,
        "h1_path": "artifacts/clean_evidence_v2/risk_layer_benchmark/h1_lead1/results_by_seed.csv",
        "h6_path": "artifacts/clean_evidence_v2/risk_layer_benchmark/h6_lead6/results_by_seed.csv",
    },
    "kelmarsh": {
        "display_name": "Kelmarsh (UK)",
        "turbines": 6,
        "h1_path": "artifacts/clean_evidence_v2/risk_layer_benchmark/kelmarsh_h1/results_by_seed.csv",
        "h6_path": "artifacts/clean_evidence_v2/risk_layer_benchmark/kelmarsh_h6/results_by_seed.csv",
    },
    "penmanshiel": {
        "display_name": "Penmanshiel (UK)",
        "turbines": 14,
        "h1_path": "artifacts/clean_evidence_v2/risk_layer_benchmark/penmanshiel_h1/results_by_seed.csv",
        "h6_path": "artifacts/clean_evidence_v2/risk_layer_benchmark/penmanshiel_h6/results_by_seed.csv",
    },
}


def main():
    parser = argparse.ArgumentParser(description="Cross-Farm Generalization Synthesizer")
    parser.add_argument("--root-dir", default=".", help="Root directory containing artifacts")
    parser.add_argument("--output-dir", default="artifacts/clean_evidence_v2/risk_layer_benchmark")
    args = parser.parse_args()

    root = Path(args.root_dir)
    out_dir = root / args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    all_dfs = []

    for farm_key, meta in FARMS_METADATA.items():
        for h_key, rel_path in [("h1", meta["h1_path"]), ("h6", meta["h6_path"])]:
            csv_path = root / rel_path
            if not csv_path.exists():
                print(f"Warning: {csv_path} does not exist yet. Skipping.")
                continue
            df = pd.read_csv(csv_path)
            df["farm_key"] = farm_key
            df["farm_display"] = meta["display_name"]
            df["turbines"] = meta["turbines"]
            df["horizon_lead"] = 1 if h_key == "h1" else 6
            all_dfs.append(df)

    if not all_dfs:
        print("No results found across farms!")
        return

    full_df = pd.concat(all_dfs, ignore_index=True)
    full_df.to_csv(out_dir / "all_farms_raw_seeds.csv", index=False)
    print(f"Loaded {len(full_df)} total seed evaluations across {full_df['farm_key'].nunique()} farms.")

    # Cross-Farm Summary Table
    # Group by Farm, Horizon, Regime, Model
    summary_rows = []
    farms = full_df["farm_key"].unique()
    horizons = sorted(full_df["horizon_lead"].unique())
    regimes = ["clean", "delay6", "sensor_noise", "markov_burst"]

    for farm in farms:
        f_meta = FARMS_METADATA[farm]
        f_df = full_df[full_df["farm_key"] == farm]

        for h in horizons:
            fh_df = f_df[f_df["horizon_lead"] == h]
            if fh_df.empty:
                continue

            for reg in regimes:
                reg_df = fh_df[fh_df["regime"] == reg]
                if reg_df.empty:
                    continue

                # Find Joint Routed baseline values for pairing
                routed_sub = reg_df[reg_df["model"] == "Joint Routed"].sort_values("seed")
                routed_costs = routed_sub["total_cost"].values if not routed_sub.empty else None

                models = sorted(reg_df["model"].unique())
                for m in models:
                    m_sub = reg_df[reg_df["model"] == m].sort_values("seed")
                    m_costs = m_sub["total_cost"].values
                    m_viols = m_sub["violation_rate"].values
                    m_res = m_sub["total_reserve"].values
                    m_short = m_sub["total_shortage"].values
                    m_pin = m_sub["pinball_loss"].values

                    cost_mean = float(np.mean(m_costs))
                    cost_std = float(np.std(m_costs))
                    viol_mean = float(np.mean(m_viols))
                    viol_std = float(np.std(m_viols))
                    res_mean = float(np.mean(m_res))
                    short_mean = float(np.mean(m_short))
                    pin_mean = float(np.mean(m_pin))

                    # Paired comparison vs Joint Routed
                    delta_cost = 0.0
                    delta_pct = 0.0
                    p_val = np.nan
                    if routed_costs is not None and len(routed_costs) == len(m_costs) and len(m_costs) > 1:
                        diff = m_costs - routed_costs
                        delta_cost = float(np.mean(diff))
                        delta_pct = float((np.mean(diff) / np.mean(routed_costs)) * 100.0)
                        if m != "Joint Routed":
                            _, p_val = stats.ttest_rel(m_costs, routed_costs)

                    summary_rows.append({
                        "Farm": f_meta["display_name"],
                        "Turbines": f_meta["turbines"],
                        "Horizon_Lead": f"h={h}",
                        "Regime": reg,
                        "Model": m,
                        "Mean_Cost": cost_mean,
                        "Std_Cost": cost_std,
                        "Violation_Rate": viol_mean,
                        "Violation_Std": viol_std,
                        "Delta_Cost_vs_Routed": delta_cost,
                        "Delta_Pct_vs_Routed": delta_pct,
                        "p_value_vs_Routed": float(p_val) if np.isfinite(p_val) else None,
                        "Reserve_kW": res_mean,
                        "Shortage_kWh": short_mean,
                        "Pinball_Loss": pin_mean,
                        "Reliability_Compliant": bool(viol_mean <= 0.10),
                    })

    summary_df = pd.DataFrame(summary_rows)
    summary_df.to_csv(out_dir / "cross_farm_generalization_table.csv", index=False)

    print("\n==================== CROSS-FARM GENERALIZATION SYNTHESIS COMPLETE ====================")
    print(summary_df[["Farm", "Horizon_Lead", "Regime", "Model", "Mean_Cost", "Violation_Rate", "Delta_Pct_vs_Routed", "p_value_vs_Routed", "Reliability_Compliant"]].to_string(index=False))


if __name__ == "__main__":
    main()
