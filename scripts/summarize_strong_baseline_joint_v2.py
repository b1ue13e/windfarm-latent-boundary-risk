from __future__ import annotations
import argparse, json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.hierarchical_bootstrap import compute_hierarchical_joint_bootstrap
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(); p.add_argument('--input',default='artifacts/strong_baseline_joint_v2/strong_baseline_native_day_blocks_v2.npz'); p.add_argument('--output',default='artifacts/strong_baseline_joint_v2/strong_baseline_joint_interaction_v2.json'); p.add_argument('--bootstrap',type=int,default=5000); p.add_argument('--seed',type=int,default=20261015); a=p.parse_args()
    raw=np.load(ROOT/a.input); seeds=sorted({int(k.split('_')[0][4:]) for k in raw.files}); trans={s:raw[f'seed{s}_trans'] for s in seeds}; steady={s:raw[f'seed{s}_steady'] for s in seeds}
    if len({len(x) for x in trans.values()}|{len(x) for x in steady.values()})!=1: raise ValueError('block length mismatch')
    inter={s:trans[s]-steady[s] for s in seeds}
    j=compute_hierarchical_joint_bootstrap(inter,n_boot=a.bootstrap,two_stage_resample=True,random_seed=a.seed)
    out={'analysis':'native original strong-baseline path; two-stage seed x daily-block bootstrap','n_seeds':j['n_seeds'],'n_time_blocks':j['n_blocks'],'mean_interaction_kwh':j['joint_mean'],'median_seed_interaction_kwh':j['joint_median'],'seed_sd_kwh':j['joint_std'],'ci95_low_kwh':j['joint_ci_95'][0],'ci95_high_kwh':j['joint_ci_95'][1],'P_interaction_le_0':j['joint_p_non_inferior'],'seed_interactions_kwh':j['seed_estimates'],'note':'P(interaction<=0) is an empirical directional probability, not a classical p-value; no arithmetic mean of seed p-values or CI endpoints.'}
    (ROOT/a.output).write_text(json.dumps(out,indent=2),encoding='utf-8')
if __name__=='__main__': main()
