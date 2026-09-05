import pandas as pd

km = pd.read_csv('artifacts/dynamic_price_settlement_audit/kelmarsh_real_price_paired_summary.csv')
pm = pd.read_csv('artifacts/dynamic_price_settlement_audit/penmanshiel_real_price_paired_summary.csv')

print('=== KELMARSH WALKFORWARD POOLED (rho=10) ===')
sub_km = km[(km['window'] == 'walkforward_rolling_pooled') & (km['rho'] == 10.0)]
for _, r in sub_km.iterrows():
    print(f"{r['metric']:25s} vs {r['baseline']:15s} delta={r['delta_mean']:12.2f} CI=[{r['ci_low']:10.2f}, {r['ci_high']:10.2f}] excl_zero={r['ci_excludes_zero']}")

print('\n=== PENMANSHIEL WALKFORWARD POOLED (rho=10) ===')
sub_pm = pm[(pm['window'] == 'walkforward_rolling_pooled') & (pm['rho'] == 10.0)]
for _, r in sub_pm.iterrows():
    print(f"{r['metric']:25s} vs {r['baseline']:15s} delta={r['delta_mean']:12.2f} CI=[{r['ci_low']:10.2f}, {r['ci_high']:10.2f}] excl_zero={r['ci_excludes_zero']}")

print('\n=== ANNUAL BREAKDOWN KELMARSH (vs global, rho=10, total_cashflow_gbp) ===')
sub_km_yr = km[km['window'].str.startswith('year_') & (km['rho'] == 10.0) & (km['baseline'] == 'global') & (km['metric'] == 'total_cashflow_gbp')]
for _, r in sub_km_yr.iterrows():
    print(f"{r['window']:10s} delta={r['delta_mean']:10.2f} CI=[{r['ci_low']:10.2f}, {r['ci_high']:10.2f}] excl={r['ci_excludes_zero']}")

print('\n=== ANNUAL BREAKDOWN PENMANSHIEL (vs global, rho=10, total_cashflow_gbp) ===')
sub_pm_yr = pm[pm['window'].str.startswith('year_') & (pm['rho'] == 10.0) & (pm['baseline'] == 'global') & (pm['metric'] == 'total_cashflow_gbp')]
for _, r in sub_pm_yr.iterrows():
    print(f"{r['window']:10s} delta={r['delta_mean']:10.2f} CI=[{r['ci_low']:10.2f}, {r['ci_high']:10.2f}] excl={r['ci_excludes_zero']}")

print('\n=== 13 ROLLING FOLDS (rho=10, total_cashflow_gbp vs global) ===')
for f, df in [('Kelmarsh', km), ('Penmanshiel', pm)]:
    rf = df[df['window'].str.startswith('rolling_fold_') & (df['rho'] == 10.0) & (df['baseline'] == 'global') & (df['metric'] == 'total_cashflow_gbp')]
    for _, r in rf.iterrows():
        print(f"{f:12s} {r['window']:16s} delta={r['delta_mean']:10.2f} CI=[{r['ci_low']:10.2f}, {r['ci_high']:10.2f}] excl={r['ci_excludes_zero']}")

print('\n=== 13 ROLLING FOLDS (rho=10, shortfall_cashflow_gbp vs global) ===')
for f, df in [('Kelmarsh', km), ('Penmanshiel', pm)]:
    rf = df[df['window'].str.startswith('rolling_fold_') & (df['rho'] == 10.0) & (df['baseline'] == 'global') & (df['metric'] == 'shortfall_cashflow_gbp')]
    for _, r in rf.iterrows():
        print(f"{f:12s} {r['window']:16s} delta={r['delta_mean']:10.2f} CI=[{r['ci_low']:10.2f}, {r['ci_high']:10.2f}] excl={r['ci_excludes_zero']}")

