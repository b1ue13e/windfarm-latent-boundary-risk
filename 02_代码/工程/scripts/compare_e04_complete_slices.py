"""Read-only four-policy slice comparison and an unexecuted E07 protocol draft."""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import os
import platform
import sys
from datetime import datetime, timedelta, timezone
from repo_paths import Path, repository_root

import numpy as np

ROOT=Path(repository_root())
POLICIES=('B','C','D','D10')
SEEDS=tuple(range(201,206))
BASE=ROOT/'analyses/e04_c201_exactness_20261018/reconciliation'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_csv(path):
    with path.open(encoding='utf-8-sig',newline='') as handle:
        return list(csv.DictReader(handle))


def write_csv(path,rows):
    with path.open('w',encoding='utf-8',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=list(rows[0]))
        writer.writeheader();writer.writerows(rows)


def paired_count_deltas(rows):
    groups={}
    for row in rows:
        groups.setdefault((row['axis'],str(row['group'])),{})[row['policy']]=row
    output=[]
    for (axis,group),policies in sorted(groups.items()):
        if set(policies)!=set(POLICIES):
            raise ValueError('Slice must contain all four policies')
        counts={int(p['n']) for p in policies.values()}
        if len(counts)!=1:
            raise ValueError('Slice population differs across policies')
        n=counts.pop()
        b=int(policies['B']['violations'])
        c=int(policies['C']['violations'])
        output.append({'axis':axis,'group':group,'n':n,
                       **{p+'_violation_pct':100*int(policies[p]['violations'])/n for p in POLICIES},
                       'C_minus_B_violations':c-b,'C_minus_B_violation_pp':100*(c-b)/n})
    return output


def proposed_protocol():
    return {
        'experiment_id':'E07-HISTORICAL-ONLY-RECALIBRATION',
        'status':'DRAFT_NOT_EXECUTED_PENDING_ACTIVATION_MANIFESTS',
        'prepared_date_Asia_Shanghai':'2026-10-18',
        'design_informed_by':'Previously inspected E04 full test and complete five-seed diagnostic; not prospective evidence for that same test.',
        'data':{
            'site':'WTB, same 134 nodes; no unregistered site substitution',
            'calibration_role':'Former E04 test is historical calibration for a strictly later new evaluation only',
            'calibration_anchor_start':30275,'calibration_anchor_end':35255,
            'calibration_latest_target_index':35261,'label_embargo_steps':1,
            'n_calibration_anchors':4981,'calibration_native_blocks':35,
            'new_test_first_anchor':35280,'new_test_issue_steps':5040,
            'new_test_last_anchor':40319,'offline_padding_last_index':40343,
            'new_test_window':'Prospective WTB days 246-280; actual source availability UNKNOWN',
            'confirmation_reuses_legacy_test':False,'update_using_new_test_labels':False,
            'calibration_frozen_before_test':True,
            'label_arrival_rule':'All calibration target/quality labels must have actually arrived at least one 10-minute step before test start',
            'feature_ingress':'UnifiedArrivalDataset; historical scaler/fill only; pitch withheld; past ramp uses genuinely arrived power and masks',
            'evaluation_mask':'Same frozen target-valid AND offline anchor-regime-valid definition for every policy; true regimes never enter decisions',
        },
        'frozen_objects':{'training_seeds':list(SEEDS),'horizon_steps':6,'dt_hours':1/6,'rho':10.,
                          'baseline':'B0 = original, unmodified B calibration/rule',
                          'base_policies':['B0','C0','D0','D10_0'],
                          'no_forecaster_retraining':True,'no_test_scaler_or_bin_fitting':True},
        'gates':{'alpha':.05,'q_star':.90,'v_max':.10,'epsilon_C_kwh':0.,'epsilon_V':0.,
                 'primary_candidate':'B_WR','cost_and_violation_reference':'B0',
                 'require_original_E04_ucb':True,'require_shared_day_ucb':True,
                 'primary_rule':'For each of cost difference, violation difference, absolute violation, max(original U95, shared-day U95) <= original threshold',
                 'no_secondary_winner_substitution':True},
        'calibration':{
            'variants':['G','WR'],'score':'shortfall - frozen_base_reserve',
            'score_quantile':.90,'quantile_method':'higher',
            'offset':'max(0, percentile95 of historical day-block bootstrap Q0.90 scores)',
            'reserve_rule':'base_reserve + frozen_offset; never clip or tune after new test',
            'n_boot':2000,'rng_seed':20261022,
            'groups':'WR: original ten wind bins x past60 power ramp {down<-150, within[-150,150], up>150 kW}',
            'min_group_cells_per_seed':1000,'min_distinct_native_blocks':14,
            'fallback_order':['wind_x_past_ramp','wind','global'],
            'missing_ramp_fallback':'wind','missing_wind_fallback':'global',
            'support_selection_uses_only_history':True,
            'global_insufficient':'CALIBRATION_INSUFFICIENT; no safety-certified fallback',
            'empty_bootstrap_group':'use its predeclared parent on that draw; if global empty, fail closed',
            'forbidden_features':['future_ramp','true_transition','current_pitch','high_test_block_id','test_realized_shortfall'],
            'frozen_through_entire_new_test':True,
            'coverage_theorem_claim':'NONE for dependent/drifting WTB data; bootstrap offset is empirical, not a certified distribution-free guarantee'},
        'evaluation':{
            'primary_population':'Full, all registered new issue indices and common mask',
            'primary_comparator':'B0; never replace with B_WR for feasibility',
            'secondary_comparator_for_representation':'C_WR/D_WR/D10_WR versus B_WR, same historical calibration and information',
            'secondary_candidates':['B_G','C_G','D_G','D10_G','C_WR','D_WR','D10_WR'],
            'original_controls':['B0','C0','D0','D10_0'],
            'primary_boot':20000,'primary_rng_seed':20261023,
            'shared_day_rule':'resample 5 seeds, then same 35 native day-block indices for all selected seeds and policies',
            'cost_scale':'retain E04 selector sum-over-sampled-seeds; report per-seed means separately',
            'diagnostic_sensitivity':'3/7-day shared circular blocks, seed 20261024, 20000 draws; cannot rescue primary failure',
            'secondary_selection_status':'descriptive only; do not certify a selected secondary winner on the same new test',
            'failure_outcomes':['NO_FEASIBLE_PRIMARY','CALIBRATION_INSUFFICIENT','NUMERICAL_AUDIT_FAILED','DATA_NOT_AVAILABLE'],
        },
        'activation':{
            'original_result_files_read_only':True,
            'base_policy_bundle_manifest_sha256':None,
            'calibration_bundle_manifest_sha256':None,
            'prospective_collection_spec_manifest_sha256':None,
            'new_test_availability':'UNKNOWN; current cache ends before new test',
            'required_before_test':['freeze protocol/code commit','bind common future cohort/collection specification without viewing outcomes',
                                    'archive all base/calibration posteriors, edges, bin IDs, reserves and mature-label times',
                                    'predeclare numeric profile before CUDA; exact archived-action n/violation/cost audit',
                                    'freeze all offsets/support/fallbacks before opening new test outcomes'],
        },
    }


def validate_protocol(plan):
    g=plan['gates']; d=plan['data']
    if any(g[key]!=value for key,value in {'alpha':.05,'q_star':.90,'v_max':.10,'epsilon_C_kwh':0.,'epsilon_V':0.}.items()):
        raise ValueError('Original threshold changed')
    if d['confirmation_reuses_legacy_test'] or d['new_test_first_anchor']<=35279:
        raise ValueError('Cannot reuse legacy observed test as confirmation')
    if d['update_using_new_test_labels'] or not d['calibration_frozen_before_test']:
        raise ValueError('Recalibration must not consume new test labels')
    if d['calibration_latest_target_index']>=d['new_test_first_anchor']-d['label_embargo_steps']:
        raise ValueError('Calibration outcomes must be mature before evaluation')
    if plan['frozen_objects']['training_seeds']!=list(SEEDS) or g['cost_and_violation_reference']!='B0':
        raise ValueError('Frozen seed set or baseline changed')
    if plan['calibration']['score_quantile']!=.90:
        raise ValueError('Nominal score quantile threshold changed')


def run(output):
    if output.exists():
        raise FileExistsError('New comparison directory required')
    source=BASE/'complete_slices'; summary=BASE/'complete_summary'
    paths=[BASE/'result.json',source/'alignment.json',source/'slices_by_seed.csv',summary/'pooled_summary.json',summary/'pooled_slices.csv',
           ROOT/'analyses/e04_regime_slices_20261018/summary/pooled_slices.csv']
    paths += [ROOT/f'experiments/E04/results/e04_v2/seed{s}_full_policy_day_blocks.npz' for s in SEEDS]
    before={str(p.relative_to(ROOT)):sha(p) for p in paths}
    result=json.loads(paths[0].read_text(encoding='utf-8'))
    if result['status']!='ALL_20_SEED_POLICY_CELLS_EXACT':
        raise ValueError('Complete numerical evidence unavailable')
    alignment=json.loads((source/'alignment.json').read_text(encoding='utf-8'))
    if not alignment['inputs_unchanged'] or not all(alignment['closures'][str(s)][p].get('n_exact')
            and alignment['closures'][str(s)][p].get('violations_exact') and alignment['closures'][str(s)][p].get('cost_exact')
            for s in SEEDS for p in POLICIES):
        raise ValueError('Incomplete exact seed/policy grid')
    metadata=json.loads((summary/'pooled_summary.json').read_text(encoding='utf-8'))
    for name,digest in metadata['input_sha256'].items():
        if sha(source/name)!=digest:
            raise ValueError('Pooled source binding mismatch')
    spec=importlib.util.spec_from_file_location('frozen_pool',ROOT/'scripts/summarize_e04_regime_slices.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    by_seed=read_csv(source/'slices_by_seed.csv')
    rows=module.pool_rows(by_seed,list(POLICIES))
    if rows!=metadata['pooled_rows']:
        raise ValueError('Exact aggregation reproduction failed')
    matrix=paired_count_deltas(rows)
    previous=read_csv(paths[5]); new_keys={(r['policy'],r['axis'],r['group']):r for r in rows}
    for row in previous:
        current=new_keys[(row['policy'],row['axis'],row['group'])]
        if int(row['n'])!=current['n'] or int(row['violations'])!=current['violations']:
            raise ValueError('Previous B/D/D10 count attribution changed')
    seed_direction=[]
    for s in SEEDS:
        values=paired_count_deltas([r for r in by_seed if int(r['seed'])==s])
        seed_direction += [{'seed':s,**r} for r in values]
    full=[]
    raw={s:dict(np.load(ROOT/f'experiments/E04/results/e04_v2/seed{s}_full_policy_day_blocks.npz')) for s in SEEDS}
    n=sum(r['n'].sum() for r in raw.values())
    for p in POLICIES:
        costs=np.array([raw[s][p+'_cost'].sum() for s in SEEDS])
        base=np.array([raw[s]['B_cost'].sum() for s in SEEDS])
        full.append({'policy':p,'n_across_repeated_seed_evaluations':int(n),'violations':int(sum(r[p+'_viol'].sum() for r in raw.values())),
                     'violation_pct':100*sum(r[p+'_viol'].sum() for r in raw.values())/n,
                     'mean_psrei_kwh':float(costs.mean()),'mean_cost_delta_vs_B_kwh':float((costs-base).mean())})
    daily_ranking=[]
    daily_n=sum(r['n'] for r in raw.values())
    for p in POLICIES:
        daily_v=sum(r[p+'_viol'] for r in raw.values())
        order=np.argsort(daily_v/daily_n)[::-1]
        for rank,index in enumerate(order,1):
            daily_ranking.append({'policy':p,'rank':rank,'native_block_1based':int(index+1),
                                  'n_across_seed_evaluations':int(daily_n[index]),
                                  'violations':int(daily_v[index]),'violation_pct':100*daily_v[index]/daily_n[index]})
    for p in POLICIES:
        axes={r['axis'] for r in rows if r['policy']==p}
        for axis in axes:
            axis_rows=[r for r in rows if r['policy']==p and r['axis']==axis]
            if sum(r['n'] for r in axis_rows)!=n or sum(r['violations'] for r in axis_rows)!=next(r['violations'] for r in full if r['policy']==p):
                raise ValueError('Slice partition does not recover the full population')
    plan=proposed_protocol();validate_protocol(plan)
    after={str(p.relative_to(ROOT)):sha(p) for p in paths}
    if before!=after:
        raise ValueError('Read-only evidence changed')
    output.mkdir(parents=True,exist_ok=False)
    write_csv(output/'risk_matrix.csv',matrix)
    write_csv(output/'seed_pairing.csv',seed_direction)
    write_csv(output/'full_policy_metrics.csv',full)
    write_csv(output/'daily_block_ranking.csv',daily_ranking)
    primary_axes=['wind_policy_bin','transition_original','past60_power_ramp','future60_power_ramp_expost','boundary_9p5_11p5','high_B_blocks']
    write_csv(output/'risk_and_procurement_descriptive.csv',[r for r in rows if r['axis'] in primary_axes])
    directions={}
    for axis,group in [('wind_policy_bin','bin_02'),('transition_original','steady'),('transition_original','transition'),('past60_power_ramp','down_gt150kW')]:
        values=[r['C_minus_B_violation_pp'] for r in seed_direction if r['axis']==axis and r['group']==group]
        directions[axis+':'+group]={'C_worse_seeds':sum(v>0 for v in values),'C_better_seeds':sum(v<0 for v in values),'deltas_pp':values}
    record={'status':'VERIFIED_DESCRIPTIVE_COMPARISON_ONLY','time_Asia_Shanghai':datetime.now(timezone(timedelta(hours=8))).isoformat(),
            'inputs_before':before,'inputs_after':after,'inputs_unchanged':True,'all_20_exact_cells_confirmed':True,
            'previous_B_D_D10_counts_unchanged':True,'all_partitions_recover_full_counts':True,'seed_directions':directions,
            'own_top5_blocks':{p:[r['native_block_1based'] for r in daily_ranking if r['policy']==p and r['rank']<=5] for p in POLICIES},
            'protocol_fitted_or_executed':False,'protocol_activation_ready':False,
            'argv':[sys.executable,*sys.argv],'script_sha256':sha(Path(__file__)),
            'environment':{'device':'CPU, no training','python':platform.python_version(),'numpy':np.__version__,
                           'cpu':os.environ.get('PROCESSOR_IDENTIFIER',platform.processor()),'platform':platform.platform()},
            'limitations':['descriptive, post-hoc, not causal attribution or simultaneous inference',
                           'same 35 days recur across seeds; totals are repeated evaluations, not independent samples',
                           'future ramp/true transition/high block IDs are diagnostic only',
                           'slice reserve/shortage summaries are as archived; do not reconstruct exact slice PSREI from rounded means']}
    (output/'comparison.json').write_text(json.dumps(record,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    (output/'proposed_protocol.json').write_text(json.dumps(plan,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps({'output':str(output),'directions':directions,'full':full,'history_inputs_unchanged':True},indent=2),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,required=True)
    run(parser.parse_args().output_dir.resolve())
