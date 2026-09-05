"""Generate complete Table A12 LaTeX block for paper_tste_supplementary.md."""
import pandas as pd
import numpy as np

km = pd.read_csv('artifacts/dynamic_price_settlement_audit/kelmarsh_real_price_paired_summary.csv')
pm = pd.read_csv('artifacts/dynamic_price_settlement_audit/penmanshiel_real_price_paired_summary.csv')

def get_row(df, win, base, rho, metric):
    sub = df[(df["window"] == win) & (df["baseline"] == base) & (np.isclose(df["rho"], rho)) & (df["metric"] == metric)]
    return sub.iloc[0] if not sub.empty else None

def fmt_gbp(val):
    sign = "+" if val > 0 else "-"
    abs_v = abs(val)
    if abs_v >= 1e6:
        return f"{sign}\\pounds {abs_v/1e6:.2f}M"
    elif abs_v >= 1e3:
        return f"{sign}\\pounds {abs_v/1e3:.1f}k"
    else:
        return f"{sign}\\pounds {abs_v:.0f}"

def fmt_mwh(val):
    sign = "+" if val > 0 else "-"
    abs_v = abs(val)
    if abs_v >= 1e3:
        return f"{sign}{abs_v/1e3:.1f}k"
    else:
        return f"{sign}{abs_v:.1f}"

print("=== VERIFYING KELMARSH ROWS ===")
for rho in [10.0, 5.0, 20.0]:
    for base, base_name in [('global', 'Global Quantile'), ('soft-pab-bin', 'Physical Pitch Rule')]:
        r_cash = get_row(km, "walkforward_rolling_pooled", base, rho, "total_cashflow_gbp")
        r_pen = get_row(km, "walkforward_rolling_pooled", base, rho, "shortfall_cashflow_gbp")
        r_mwh = get_row(km, "walkforward_rolling_pooled", base, rho, "shortage_mwh")
        
        # Savings vs baseline: baseline - strat = - delta
        sav_cash = -r_cash["delta_mean"]
        ci_cash_low = -r_cash["ci_high"]
        ci_cash_high = -r_cash["ci_low"]
        excl_cash = r_cash["ci_excludes_zero"]

        sav_pen = -r_pen["delta_mean"]
        ci_pen_low = -r_pen["ci_high"]
        ci_pen_high = -r_pen["ci_low"]
        excl_pen = r_pen["ci_excludes_zero"]

        av_mwh = -r_mwh["delta_mean"]

        turb_yr_val = sav_cash / (6 * 7.0) # 6 turbines, 7 rolling years

        print(f"KM rho={int(rho)} vs {base_name:20s}: AvShort={fmt_mwh(av_mwh):8s} PenSav={fmt_gbp(sav_pen):12s} NetCashSav={fmt_gbp(sav_cash):12s} CI=[{fmt_gbp(ci_cash_low)}, {fmt_gbp(ci_cash_high)}] excl={excl_cash} Val/TurbYr={fmt_gbp(turb_yr_val)}")

print("\n=== VERIFYING PENMANSHIEL ROWS ===")
for rho in [10.0, 5.0, 20.0]:
    for base, base_name in [('global', 'Global Quantile'), ('soft-pab-bin', 'Physical Pitch Rule')]:
        r_cash = get_row(pm, "walkforward_rolling_pooled", base, rho, "total_cashflow_gbp")
        r_pen = get_row(pm, "walkforward_rolling_pooled", base, rho, "shortfall_cashflow_gbp")
        r_mwh = get_row(pm, "walkforward_rolling_pooled", base, rho, "shortage_mwh")

        sav_cash = -r_cash["delta_mean"]
        ci_cash_low = -r_cash["ci_high"]
        ci_cash_high = -r_cash["ci_low"]
        excl_cash = r_cash["ci_excludes_zero"]

        sav_pen = -r_pen["delta_mean"]
        ci_pen_low = -r_pen["ci_high"]
        ci_pen_high = -r_pen["ci_low"]
        excl_pen = r_pen["ci_excludes_zero"]

        av_mwh = -r_mwh["delta_mean"]
        turb_yr_val = sav_cash / (14 * 6.0) # 14 turbines, 6 rolling years

        print(f"PM rho={int(rho)} vs {base_name:20s}: AvShort={fmt_mwh(av_mwh):8s} PenSav={fmt_gbp(sav_pen):12s} NetCashSav={fmt_gbp(sav_cash):12s} CI=[{fmt_gbp(ci_cash_low)}, {fmt_gbp(ci_cash_high)}] excl={excl_cash} Val/TurbYr={fmt_gbp(turb_yr_val)}")
