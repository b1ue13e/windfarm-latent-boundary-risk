"""Verify all numbers in Table A12 Panel B and Table A12b against CSV artifacts."""
from __future__ import annotations

import math
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
AUDIT_DIR = ROOT / "artifacts" / "dynamic_price_settlement_audit"
ELEXON_CSV = ROOT / "artifacts" / "elexon_bmrs_imbalance" / "elexon_system_prices_2016_2024.csv"

def verify_table_a12():
    km = pd.read_csv(AUDIT_DIR / "kelmarsh_real_price_paired_summary.csv")
    pm = pd.read_csv(AUDIT_DIR / "penmanshiel_real_price_paired_summary.csv")
    elexon = pd.read_csv(ELEXON_CSV)

    print("=== 1. ELEXON BMRS OVERALL STATS ===")
    n_periods = len(elexon)
    mean_sbp = elexon["systemBuyPrice"].mean()
    min_sbp = elexon["systemBuyPrice"].min()
    max_sbp = elexon["systemBuyPrice"].max()
    print(f"Periods: {n_periods:,}, Mean: {mean_sbp:.2f}, Min: {min_sbp:.2f}, Max: {max_sbp:.2f}")

    print("\n=== 2. TABLE A12 PANEL B VERIFICATION ===")
    panel_b_specs = [
        # (farm_df, farm_name, baseline, rho, n_turb, n_yr)
        (km, "Kelmarsh", "global", 10.0, 6, 7.0),
        (km, "Kelmarsh", "soft-pab-bin", 10.0, 6, 7.0),
        (km, "Kelmarsh", "global", 5.0, 6, 7.0),
        (km, "Kelmarsh", "soft-pab-bin", 5.0, 6, 7.0),
        (km, "Kelmarsh", "global", 20.0, 6, 7.0),
        (km, "Kelmarsh", "soft-pab-bin", 20.0, 6, 7.0),
        (pm, "Penmanshiel", "global", 10.0, 14, 6.0),
        (pm, "Penmanshiel", "soft-pab-bin", 10.0, 14, 6.0),
        (pm, "Penmanshiel", "global", 5.0, 14, 6.0),
        (pm, "Penmanshiel", "soft-pab-bin", 5.0, 14, 6.0),
        (pm, "Penmanshiel", "global", 20.0, 14, 6.0),
        (pm, "Penmanshiel", "soft-pab-bin", 20.0, 14, 6.0),
    ]

    panel_b_results = []
    for f_df, farm, base, rho, n_turb, n_yr in panel_b_specs:
        sub = f_df[(f_df["window"] == "walkforward_rolling_pooled") & (f_df["baseline"] == base) & (np.isclose(f_df["rho"], rho))]
        c = sub[sub["metric"] == "total_cashflow_gbp"].iloc[0]
        p = sub[sub["metric"] == "shortfall_cashflow_gbp"].iloc[0]
        s = sub[sub["metric"] == "shortage_mwh"].iloc[0]

        net_sav = -c["delta_mean"]
        ci_low = -c["ci_high"]
        ci_high = -c["ci_low"]
        pen_sav = -p["delta_mean"]
        av_short = -s["delta_mean"]
        val_turb_yr = net_sav / (n_turb * n_yr)
        excl = c["ci_excludes_zero"]

        panel_b_results.append({
            "farm": farm,
            "baseline": base,
            "rho": int(rho),
            "av_short_mwh": av_short,
            "pen_sav_gbp": pen_sav,
            "net_sav_gbp": net_sav,
            "ci_low": ci_low,
            "ci_high": ci_high,
            "excl_zero": excl,
            "val_turb_yr": val_turb_yr,
        })
        print(f"[{farm} rho={int(rho):2d} vs {base:12s}] Shortage={av_short:+8.1f} MWh | PenSav={pen_sav/1e3:+7.1f}k | NetSav={net_sav/1e3:+7.1f}k | CI=[{ci_low/1e3:+6.1f}k, {ci_high/1e3:+6.1f}k] | Excl={excl} | Val/TurbYr={val_turb_yr:+7.1f}")

    print("\n=== 3. TABLE A12b ANNUAL BREAKDOWN VERIFICATION ===")
    elexon["year"] = pd.to_datetime(elexon["settlementDate"]).dt.year
    annual_sbp = elexon.groupby("year")["systemBuyPrice"].agg(["mean", "max"]).to_dict("index")

    phase_map = {
        1: ("2016", "Baseline Commissioning"),
        2: ("2017", "Mature Operation"),
        3: ("2018", "Mature Operation"),
        4: ("2019", "Mature Operation"),
        5: ("2020", "COVID Lockdown / High RES"),
        6: ("2021", "European Energy Crisis"),
        7: ("2022", "Peak Commodity Shock / War"),
        8: ("2023", "Post-Crisis Normalization"),
        9: ("2024", "Mature Decadal Operation"),
    }

    annual_results = []
    for y_idx in range(1, 10):
        win = f"year_{y_idx}"
        year_int = 2015 + y_idx
        yr_str, phase = phase_map[y_idx]

        sub = km[(km["window"] == win) & (km["baseline"] == "global") & (km["rho"] == 10.0)]
        c = sub[sub["metric"] == "total_cashflow_gbp"].iloc[0]
        s = sub[sub["metric"] == "shortage_mwh"].iloc[0]

        net_sav = -c["delta_mean"]
        ci_low = -c["ci_high"]
        ci_high = -c["ci_low"]
        av_short = -s["delta_mean"]
        excl = c["ci_excludes_zero"]

        sbp_m = annual_sbp[year_int]["mean"]
        sbp_max = annual_sbp[year_int]["max"]

        annual_results.append({
            "year_idx": y_idx,
            "year": yr_str,
            "phase": phase,
            "mean_sbp": sbp_m,
            "max_sbp": sbp_max,
            "av_short_mwh": av_short,
            "net_sav_gbp": net_sav,
            "ci_low": ci_low,
            "ci_high": ci_high,
            "excl_zero": excl,
        })
        print(f"[Year {y_idx} ({yr_str})] SBP Mean={sbp_m:6.2f}, Max={sbp_max:7.2f} | Shortage={av_short:+6.1f} MWh | NetSav={net_sav/1e3:+6.1f}k | CI=[{ci_low/1e3:+6.1f}k, {ci_high/1e3:+6.1f}k] | Excl={excl}")

    return panel_b_results, annual_results

if __name__ == "__main__":
    verify_table_a12()
