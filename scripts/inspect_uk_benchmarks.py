import pandas as pd
from pathlib import Path

root = Path('artifacts/clean_evidence_v2/risk_layer_benchmark')
for suite in ['kelmarsh_h6', 'penmanshiel_h6', 'kelmarsh_h1', 'penmanshiel_h1']:
    agg = pd.read_csv(root / suite / 'cross_seed_aggregate.csv', header=[0,1])
    agg.columns = [c[0] if 'Unnamed' in c[1] else f'{c[0]}_{c[1]}' for c in agg.columns]
    paired = pd.read_csv(root / suite / 'paired_significance.csv')
    print(f'*** {suite} ***')
    for reg in ['clean', 'delay6', 'sensor_noise', 'markov_burst']:
        sub_agg = agg[agg['regime'] == reg]
        sub_p = paired[paired['regime'] == reg]
        jr = sub_agg[sub_agg['model'] == 'Joint Routed']
        gbdt = sub_agg[sub_agg['model'] == 'Missingness-Aware GBDT']
        phys = sub_agg[sub_agg['model'] == 'Continuous Physical Quantile']
        print(f'[{reg}]')
        if not jr.empty:
            c = int(round(jr['total_cost_mean'].values[0]))
            s = int(round(jr['total_cost_std'].values[0]))
            v = jr['violation_rate_mean'].values[0] * 100
            print(f'  Joint Routed: cost={c} +/- {s}, viol={v:.2f}%')
        if not gbdt.empty:
            c = int(round(gbdt['total_cost_mean'].values[0]))
            s = int(round(gbdt['total_cost_std'].values[0]))
            v = gbdt['violation_rate_mean'].values[0] * 100
            print(f'  GBDT: cost={c} +/- {s}, viol={v:.2f}%')
        if not phys.empty:
            c = int(round(phys['total_cost_mean'].values[0]))
            s = int(round(phys['total_cost_std'].values[0]))
            v = phys['violation_rate_mean'].values[0] * 100
            print(f'  Physical: cost={c} +/- {s}, viol={v:.2f}%')
        for _, r in sub_p.iterrows():
            if r['model'] in ['Missingness-Aware GBDT', 'Continuous Physical Quantile']:
                d = int(round(r['mean_cost_delta']))
                lo = int(round(r['ci_95_lo']))
                hi = int(round(r['ci_95_hi']))
                sig = r['significant_95']
                print(f'  delta vs {r["model"]}: {d} CI [{lo}, {hi}] sig={sig}')
