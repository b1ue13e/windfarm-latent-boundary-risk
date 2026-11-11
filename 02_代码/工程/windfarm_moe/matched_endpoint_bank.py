"""Causal, immutable endpoint vintages with continuous online trajectories."""
from __future__ import annotations
from repo_paths import Path, repository_root
from dataclasses import replace
import hashlib,json
import numpy as np
from scripts.run_mixture_closed_loop import PHASES,sha,verify_cache
from scripts.run_meta_pool import load_verified_parent_stream_bank
from windfarm_moe.release_bank import (
    verify_parent_campaign_freeze,_load_verified_causal_profile,
    _verify_nan_outside_mask_and_finite_valid,compute_current_features,compute_feedback_features,
    SAFE_REPLAY_CONFIGS,COST_CALIBRATION_CONFIG,_nan_exact_sha256,
    CURRENT_FEATURE_NAMES,ALL_FEATURE_NAMES,
)
from windfarm_moe.meta_action_stream import prefix_sha256,join_banks
from windfarm_moe.residual_meta import load_meta_model,build_meta_features,predict_residual_meta_actions,verify_common_ref_expert0
from windfarm_moe.bounded_relief import signed_experts,run_signed
from windfarm_moe.delayed_calibration_baselines import run_delayed_calibration

ROOT=Path(__file__).resolve().parents[1]
VINTAGES=('inner','outer')
FROZEN_META_IDS=(0,12,18)

def select_legal_anchors(anchors,vintage,include_evaluation=False):
    if vintage not in VINTAGES:raise ValueError('Use a historical inner/outer vintage only')
    a=np.asarray(anchors)
    lo=PHASES[vintage][0]
    valid=(a>=lo)&(a<PHASES['outer'][1])
    valid &= ~((a>=PHASES['inner'][1])&(a<PHASES['outer'][0]))
    if include_evaluation:valid|=(a>=PHASES['evaluate'][0])&(a<PHASES['evaluate'][1])
    return valid

def run_fixed_trajectory(xp,baseline,raw12,shortfall,mask,anchors,weights,initial_shift):
    """One start, one model version, one trajectory; no phase resets."""
    a=np.asarray(anchors,dtype=np.int64)
    if a.ndim!=1 or len(a)==0 or np.any(np.diff(a)<=0):raise ValueError('Strictly increasing anchors required')
    delta=signed_experts(xp,baseline,relief=.01)
    # The original three-row batch is intentional: preserve original arithmetic.
    safe=run_signed(delta,baseline,shortfall,mask,a,SAFE_REPLAY_CONFIGS,weights,
                    relief=.01,score=False,return_actions=True)
    cal=run_delayed_calibration(raw12,shortfall,mask,a,
        replace(COST_CALIBRATION_CONFIG,initial_shift=float(initial_shift)),save_trace=True)
    return np.ascontiguousarray(safe['actions'][0]),np.ascontiguousarray(cal.actions),dict(
        safe_feedback_updates=int(safe['metadata']['feedback_updates']),
        safe_final_weights=safe['metadata']['final_weights'][0],
        safe_release_trace=safe['metadata']['release_trace'],
        cost_processed_issues=int(cal.processed_feedback_issues),
        cost_initial_shift=float(initial_shift),cost_final_shift=float(cal.trace['shift'][-1]),
        cost_shift_trace=cal.trace['shift'].tolist(),phase_restarts=0)

def _load_meta_vintage(cfg,freeze,vintage,seed,arm,rid):
    folder=Path(cfg['meta_parent_results'])
    rel=f'models/{vintage}/{arm}_seed{seed}/M{rid:03d}.joblib'
    rp=rel.replace('.joblib','_receipt.json')
    expected=freeze['all_models'].get(rel);expected_r=freeze['all_model_receipts'].get(rp)
    if not expected or sha(folder/rel)!=expected or sha(folder/rp)!=expected_r:
        raise ValueError('Frozen meta vintage identity differs')
    receipt=json.loads((folder/rp).read_text())
    model=load_meta_model(folder/rel)
    start,_,cut=PHASES[vintage]
    for obj in (model,receipt):
        if (obj.get('phase'),obj.get('arm'),obj.get('seed'),obj.get('recipe_id'))!=(vintage,arm,seed,rid):
            raise ValueError('Meta vintage identity mismatch')
        if obj.get('fit_window')!=[27648,cut] or obj.get('episode_start')!=start or obj.get('last_label_release')!=cut-1+7:
            raise ValueError('Meta training clock mismatch')
        if obj['last_label_release']>=start:raise ValueError('Meta is not available at vintage start')
        profile=cfg['parent_profiles'][f'profiles/historical_seed{seed}.npy']['sha256']
        if obj.get('source_manifest_sha256')!=cfg['historical_manifest_sha256'] or obj.get('parent_profile_sha256')!=profile:
            raise ValueError('Meta was trained against a different cache or baseline profile')
    if receipt['model_sha256']!=expected:raise ValueError('Meta receipt binding mismatch')
    return model,dict(path=rel,sha256=expected,receipt_sha256=expected_r,fit_window=[27648,cut],episode_start=start)

def _load_stream(cfg,freeze,phase,seed,arm):
    return load_verified_parent_stream_bank(Path(cfg['stream_parent_results']),freeze,phase,seed,arm)[0]

def build_matched_bank(cfg,seed,arm,vintage,include_evaluation=False,root=ROOT):
    if seed not in range(201,206) or isinstance(seed,bool) or arm not in ('C','P','Z'):
        raise ValueError('Fixed arm and seed required')
    if vintage not in VINTAGES:raise ValueError('Evaluation model must never be backfilled into history')
    _,mr,_=verify_parent_campaign_freeze(cfg['meta_parent_results'],cfg['meta_parent_freeze_sha256'],label='MR')
    _,mc,_=verify_parent_campaign_freeze(cfg['stream_parent_results'],cfg['stream_parent_freeze_sha256'],label='MC')
    safe_dir,br,_=verify_parent_campaign_freeze(cfg['safe_parent_results'],cfg['safe_parent_freeze_sha256'],
        input_protocol_path=cfg.get('safe_parent_input_protocol'),label='BR')
    arrays={k:[] for k in ('anchors','shortfall','mask','xp','xz','baseline')};source_info={}
    kinds=['historical']+(['evaluate'] if include_evaluation else [])
    for kind in kinds:
        cache=Path(cfg['historical_cache'] if kind=='historical' else cfg['evaluation_cache'])
        manifest=cfg['historical_manifest_sha256'] if kind=='historical' else cfg['evaluation_manifest_sha256']
        verify_cache(cache,manifest)
        a=np.load(cache/'anchors.npy');y=np.load(cache/'shortfall.npy');mask=np.load(cache/'mask.npy')
        xp=np.load(cache/f'P_seed{seed}.npy',mmap_mode='r');xz=np.load(cache/f'Z_seed{seed}.npy',mmap_mode='r')
        verify_common_ref_expert0(xp,xz)
        baseline,base_sha=_load_verified_causal_profile(cfg,kind,seed)
        if y.shape!=baseline.shape:raise ValueError('R186 source shape mismatch')
        select=select_legal_anchors(a,vintage,include_evaluation)
        for key,value in [('anchors',a),('shortfall',y),('mask',mask),('xp',xp),('xz',xz),('baseline',baseline)]:
            arrays[key].append(np.ascontiguousarray(value[select]))
        source_info[kind]=dict(cache_manifest_sha256=manifest,baseline_profile_sha256=base_sha)
    values={k:np.concatenate(v,axis=0) for k,v in arrays.items()}
    a,y,m,xp,xz,b=[values[k] for k in ('anchors','shortfall','mask','xp','xz','baseline')]
    _verify_nan_outside_mask_and_finite_valid(y,m)
    start,phase_end,cut=PHASES[vintage]
    if a[0]!=start or np.any(a<start):raise ValueError('Vintage begins at wrong clock')
    expected_n=(2139 if vintage=='inner' else 1289)+(5033 if include_evaluation else 0)
    if len(a)!=expected_n:raise ValueError('Matched population differs from registered issue count')
    original=_load_stream(cfg,mc,vintage,seed,arm)
    n_first=len(original['anchors'])
    for key,arr in [('anchors',a),('shortfall',y),('mask',m)]:
        if np.ascontiguousarray(arr[:n_first]).tobytes()!=np.ascontiguousarray(original[key]).tobytes():
            raise ValueError('First-phase source population byte mismatch: '+key)
    feat=build_meta_features(b,xz if arm=='Z' else xp,a,arm)
    raw={};models={}
    for rid in FROZEN_META_IDS:
        model,record=_load_meta_vintage(cfg,mr,vintage,seed,arm,rid)
        prediction,_=predict_residual_meta_actions(model,feat,b)
        if prefix_sha256(prediction[:n_first])!=original['metadata']['raw_action_sha256'][str(rid)]:
            raise ValueError(f'Original meta first-phase prediction differs for {rid}')
        raw[rid]=prediction;models[str(rid)]=record
    # Carry only a state that was already mature when outer first became legal.
    initial_shift=0.;shift_source=dict(kind='original_inner_cold_start',last_label_release=None)
    if vintage=='outer':
        inner=_load_stream(cfg,mc,'inner',seed,arm)
        joined=join_banks([inner,original])
        old=run_delayed_calibration(joined['raw_actions'][12],joined['shortfall'],joined['mask'],joined['anchors'],
            COST_CALIBRATION_CONFIG,save_trace=True)
        initial_shift=float(old.trace['shift'][len(inner['anchors'])])
        last=int(inner['anchors'][-1])+7
        if last>=start:raise ValueError('Carried tracker state uses an immature label')
        shift_source=dict(kind='original_mature_inner_prefix',last_label_release=last,
            inner_raw_sha256=prefix_sha256(inner['raw_actions'][12]),inner_issue_count=len(inner['anchors']))
    init_rel=f'initializers/{vintage}/P_seed{seed}/COST_d0p01.json'
    init_path=safe_dir/init_rel
    if sha(init_path)!=br['all_initializers'].get(init_rel):raise ValueError('Frozen SAFE initial weight differs')
    init=json.loads(init_path.read_text());w=np.asarray(init['canonical_initial'])
    if init['fit_window']!=[27648,cut] or init['last_label_release']>=start or init['episode_start']!=start:
        raise ValueError('SAFE initialization clock mismatch')
    safe,cost,trajectory=run_fixed_trajectory(xp,b,raw[12],y,m,a,w,initial_shift)
    for folder,rid,act in [(safe_dir,9,safe),(Path(cfg['stream_parent_results']),49,cost)]:
        original_arm='P' if rid==9 else arm
        receipt_path=folder/f'instances/{vintage}/{original_arm}_seed{seed}/receipt.json'
        receipt=json.loads(receipt_path.read_text());expected=receipt['action_sha256'][str(rid)]
        if receipt['status'][str(rid)]!='COMPLETED' or prefix_sha256(act[:n_first])!=expected:
            raise ValueError(f'Original endpoint first-phase SHA mismatch: {rid}/{vintage}/{arm}/{seed}')
    current,crossings=compute_current_features(xp[:,:,0],safe,cost,raw[0],raw[18])
    feedback,release_trace=compute_feedback_features(safe,cost,y,m,a)
    full_feedback=np.concatenate([current,feedback],axis=-1)
    metadata=dict(schema='matched-endpoint-bank-v1',seed=seed,arm=arm,vintage=vintage,
        include_evaluation=bool(include_evaluation),evaluation_touched=bool(include_evaluation),
        endpoint_fit_window=[27648,cut],endpoint_start=start,first_phase_issues=n_first,
        frozen_meta_models=models,safe_initial_weight_sha256=sha(init_path),initial_shift_source=shift_source,
        online_trajectory=trajectory,phase_restarts=0,upstream_models_refitted=False,source_info=source_info,
        width_meta_ids=[0,18],width_negative_crossings_count=int(crossings),
        current_feature_names=list(CURRENT_FEATURE_NAMES),feedback_feature_names=list(ALL_FEATURE_NAMES),
        feedback_release_trace=release_trace.tolist(),
        first_phase_raw_shas={str(k):prefix_sha256(v[:n_first]) for k,v in raw.items()},
        first_phase_safe_sha256=prefix_sha256(safe[:n_first]),first_phase_cost_sha256=prefix_sha256(cost[:n_first]),
        common_incumbent_note='All arms share a P-only SAFE endpoint; C is not power-free',
        shortfall_raw_sha256=_nan_exact_sha256(y),mask_sha256=hashlib.sha256(m.tobytes()).hexdigest(),
        anchors_sha256=hashlib.sha256(a.astype('<i8').tobytes()).hexdigest(),independent_confirmation=False)
    result=dict(anchors=a,shortfall=y,mask=m,reference=xp[:,:,0].copy(),safe=safe,cost=cost,
        current_features=current,feedback_only_features=feedback,feedback_features=full_feedback,metadata=metadata)
    for value in result.values():
        if isinstance(value,np.ndarray):value.flags.writeable=False
    return result
