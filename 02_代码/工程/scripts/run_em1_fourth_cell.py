"""Zero-fit fourth cell, frozen-history barrier and complete-family inference."""
from __future__ import annotations
import argparse, hashlib, importlib.util, json, os, sys, time, traceback
from repo_paths import Path, repository_root
ROOT=Path(repository_root());sys.path.insert(0,str(ROOT))
import numpy as np
from threadpoolctl import threadpool_limits
from scripts.run_em1_minimal_followup import (sha,read,save_new,bind,array_sha,environment,
    deadline_check,_pair_names)
from windfarm_moe.stable_contrast_inference import THRESHOLDS,CSTAR,infer_stable_campaign

ROLE='D_ALPHA_ALL_TREE_Z'
PAIRS=[(ROLE,'EM1_007_Z'),('EM1_008_Z',ROLE),('NV_MAJOR_Z','EM1_007_Z')]
SNAPS={'C':(29376,29384,29816),'E':(29808,29816,30240),'D':(30233,30240,10**12)}
HERE=ROOT/'experiments/conditional_training_fourth_cell_20261025'
N_COORDINATES=11*1402+10*7263


def action_view(bank):
    return {k:bank[k] for k in ('anchors','safe','cost','current_features')}


def independent_module():
    spec=importlib.util.spec_from_file_location('fourth_independent',HERE/'summary.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def config_check(cfg):
    if cfg.get('expected_family') != dict(policies=1402, pairs=7263, aliases=152, coordinates=N_COORDINATES):
        raise ValueError('Complete D-extended family dimensions differ')
    if (cfg['seeds']!=list(range(201,206)) or cfg['spans']!=[1,3,7] or cfg['n_boot']!=20000
        or cfg['resampling_seed']!=20261022 or cfg['thresholds']!=THRESHOLDS
        or cfg['cstar_report_only']!=CSTAR or cfg['new_role']!=ROLE
        or cfg['comparisons']!=[list(p) for p in PAIRS] or cfg['max_cpu_seconds']!=2400
        or cfg['stage_limits']!=dict(s0=120,freeze=300,evaluate=120,aggregate=600,audit=300,reserve=480)
        or cfg['expected_family']!=dict(policies=1402,pairs=7263,aliases=152,coordinates=N_COORDINATES)):
        raise ValueError('Frozen fourth-cell specification changed')
    if 120+300+5*120+600+300+480!=cfg['max_cpu_seconds']:
        raise ValueError('Stage reservation exceeds the 2400 CPU-second cap')


def source_check(cfg):
    if not cfg['source_hashes']:raise ValueError('Unsealed sources')
    for rel,digest in cfg['source_hashes'].items():
        if sha(ROOT/rel)!=digest:raise ValueError('Source identity differs: '+rel)
    archive=ROOT/'source_payload.zip'
    if not archive.exists() or sha(archive)!=os.environ.get('CAMPAIGN_RELEASE'):
        raise ValueError('PBS source archive identity differs')


def parent_data(cfg):
    p=Path(cfg['parent_results']);names=read(p/'all_policy_names.json')
    completion=read(p/'completion.json')
    for name,digest in cfg['parent_bindings'].items():
        if sha(p/name)!=digest:raise ValueError('Parent follow-up input differs: '+name)
    for name,binding in completion['files'].items():
        if bind(p/name)!=binding:raise ValueError('Parent completion binding differs')
    if (len(names['names']),len(names['comparisons']),len(names['aliases']),names['nominal_family_size'])!=(1401,7260,152,88011):
        raise ValueError('Unexpected complete parent family')
    with np.load(p/'all_daily_ledger.npz') as z:data={k:z[k].copy() for k in z.files}
    if data['ledger'].shape!=(5,1401,35,4) or int(data['counts'].sum())!=672939:
        raise ValueError('Parent population differs')
    return p,names,data


def matched_parent(cfg):
    from windfarm_moe.release_bank import verify_parent_campaign_freeze
    p,f,pc=verify_parent_campaign_freeze(cfg['matched_results'],cfg['matched_freeze_sha256'],label='Matched parent')
    if pc!=cfg['matched_protocol']:raise ValueError('Matched parent protocol differs')
    return p,f


def models_for(cfg,seed):
    from windfarm_moe.release_gate import load_release_gate_model
    p,f=matched_parent(cfg);row=f['histories'][(seed-201)*3+2]
    if sha(p/row['path'])!=row['sha256']:raise ValueError('Matched history receipt differs')
    h=read(p/row['path'])
    if (h['status'],h['seed'],h['arm'],h['evaluation_touched'])!=('COMPLETED',seed,'Z',False):
        raise ValueError('Historical seed identity differs')
    version=row['versions']['outer']
    if version!=h['versions']['outer']:raise ValueError('Historical outer version differs')
    models={};receipts={};bindings={}
    for snap,(cut,begin,_) in SNAPS.items():
        for rid in (7,8):
            record=next(x for x in version['models'] if x['snapshot']==snap and x['recipe_id']==rid)
            mp,rp=p/record['path'],p/record['receipt_path']
            if sha(mp)!=record['sha256'] or sha(rp)!=record['receipt_sha256']:
                raise ValueError('Source model/receipt SHA differs')
            model,receipt=load_release_gate_model(mp),read(rp)
            for obj in (model,receipt):
                if (obj['seed'],obj['arm'],obj['vintage'],obj['snapshot'],obj['recipe_id'],obj['cut_anchor'],obj['enabled_anchor'],obj['episode_start'])!=(seed,'Z','outer',snap,rid,cut,begin,begin):
                    raise ValueError('Model snapshot/maturity differs')
                if (cut-1)+7>=begin:raise ValueError('Immature source model')
            if model.get('kind') != ('GLOBAL_FIT' if rid==7 else 'GATE'):
                raise ValueError('Frozen A/C recipe kind mismatch')
            models[snap,rid]=model;receipts[snap,rid]=receipt
            if rid==7 and float(model['alpha'])!=float(receipt['global_fit_stats']['alpha']):
                raise ValueError('Global model coefficient differs from source receipt')
            if rid==8:
                if model['feature_set']!='current' or model['n_features']!=5:
                    raise ValueError('Frozen EM008 current-feature tree differs')
                for key in ('leaf_alphas','leaf_stats'):
                    if {str(k):v for k,v in model[key].items()}!=receipt[key]:
                        raise ValueError('Gate model leaf parameters differ from source receipt')
            bindings[f'{snap}:{rid}']=dict(model_path=record['path'],model=bind(mp),receipt_path=record['receipt_path'],receipt=bind(rp))
    return p,version,models,receipts,bindings


def tree_nodes(tree):
    t=tree.tree_
    return {k:getattr(t,k).tolist() for k in ('children_left','children_right','feature','threshold')}


def freeze_parameters(global_receipt,gate_receipt,tree):
    if (global_receipt.get('status')!='FITTED_OK' or gate_receipt.get('status')!='FITTED_OK'
        or global_receipt.get('fallback_to_safe') or gate_receipt.get('fallback_to_safe')):
        raise ValueError('Expected completed frozen source models')
    for key in ('seed','arm','vintage','snapshot','cut_anchor','enabled_anchor','episode_start',
                'valid_row_sha256','selected_issue_count','valid_fit_cells'):
        if global_receipt.get(key)!=gate_receipt.get(key):
            raise ValueError('Global/gate historical training identity differs: '+key)
    alpha=float(global_receipt['global_fit_stats']['alpha'])
    if not np.isfinite(alpha) or not 0<=alpha<=1 or alpha!=float(global_receipt['alpha']):
        raise ValueError('Invalid frozen global alpha')
    leaves={int(k):v for k,v in gate_receipt['leaf_stats'].items()}
    if not leaves:raise ValueError('Missing historical release branch')
    major=min(leaves,key=lambda k:(-int(leaves[k]['n_cells']),k))
    if any(float(gate_receipt['leaf_alphas'][str(k)])!=0 for k in leaves if k!=major):
        raise ValueError('Expected one historical release branch and zero veto branch')
    return dict(global_receipt=global_receipt,gate_receipt=gate_receipt,tree_nodes=tree_nodes(tree),
        alpha_all=alpha,release_leaf=major,leaf_alphas={str(k):alpha if k==major else 0. for k in leaves},
        release_leaf_rule='largest historical training support; tied minimum leaf id',new_fits=0)


def fourth_actions(bank,trees,parameters):
    """Production action; reads only arrived anchors/endpoints/current features."""
    a=np.asarray(bank['anchors'],dtype=np.int64);safe=np.asarray(bank['safe'],dtype=np.float64)
    cost=np.asarray(bank['cost'],dtype=np.float64);x=np.asarray(bank['current_features'],dtype=np.float64)
    if (a.ndim!=1 or np.any(np.diff(a)<=0) or safe.ndim!=2 or cost.shape!=safe.shape
        or x.shape!=(*safe.shape,5) or len(a)!=len(safe) or not np.isfinite(x).all()
        or not np.isfinite(safe).all() or not np.isfinite(cost).all() or np.any(safe<0) or np.any(cost<0)):
        raise ValueError('Invalid causal action view')
    actions=safe.copy();route=np.full(safe.shape,-1,dtype=np.int64)
    for snap,(_,begin,end) in SNAPS.items():
        par=parameters[snap]
        alpha=float(par['alpha_all'])
        if not np.isfinite(alpha) or not 0<=alpha<=1:
            raise ValueError('Invalid frozen global alpha')
        if any(float(v)!=(alpha if int(k)==int(par['release_leaf']) else 0.)
               for k,v in par['leaf_alphas'].items()):
            raise ValueError('D leaf map must apply the global alpha only on the frozen release branch')
        use=(a>=begin)&(a<end)
        if not use.any():continue
        ids=np.asarray(trees[snap].apply(x[use].reshape(-1,5)),dtype=np.int64)
        alphas=parameters[snap]['leaf_alphas'];weights=np.empty(ids.shape,dtype=np.float64)
        for lid in np.unique(ids):
            if str(int(lid)) not in alphas:raise ValueError('Unknown frozen tree leaf')
            weights[ids==lid]=float(alphas[str(int(lid))])
        actions[use]=np.maximum(safe[use]+weights.reshape(safe[use].shape)*(cost[use]-safe[use]),0.)
        route[use]=ids.reshape(safe[use].shape)
    return np.ascontiguousarray(actions),route


def verify_original_actions(bank,models,phase_receipt):
    """Replay source A/C directly from frozen parameters, without model fitting."""
    a=bank['anchors'];safe=bank['safe'];cost=bank['cost'];x=bank['current_features']
    out={7:safe.copy(),8:safe.copy(),'route':np.full(safe.shape,-1,dtype=np.int64)}
    for snap,(_,begin,end) in SNAPS.items():
        use=(a>=begin)&(a<end)
        if not use.any():continue
        alpha=float(models[snap,7]['alpha'])
        out[7][use]=safe[use].copy() if alpha==0 else cost[use].copy() if alpha==1 else np.maximum(safe[use]+alpha*(cost[use]-safe[use]),0.)
        ids=models[snap,8]['tree'].apply(x[use].reshape(-1,5))
        out['route'][use]=np.asarray(ids,dtype=np.int64).reshape(safe[use].shape)
        w=np.asarray([models[snap,8]['leaf_alphas'][int(i)] for i in ids]).reshape(safe[use].shape)
        out[8][use]=np.maximum(safe[use]+w*(cost[use]-safe[use]),0.)
    for phase,receipt in phase_receipt.items():
        begin,end=(28944,30233) if phase=='outer' else (30240,35273);sel=(a>=begin)&(a<end)
        for rid in (7,8):
            action=out[rid]
            if array_sha(action[sel])!=receipt['policies'][str(rid)]['action_sha256']:
                raise ValueError('Frozen original A/C action SHA mismatch')
        for rid,k in [('0','safe'),('1','cost')]:
            if array_sha(bank[k][sel])!=receipt['policies'][rid]['action_sha256']:
                raise ValueError('Frozen SAFE/COST action SHA mismatch')
        if array_sha(bank['shortfall'][sel])!=receipt['target_sha256'] or array_sha(bank['mask'][sel],None)!=receipt['mask_sha256']:
            raise ValueError('Frozen target/mask SHA mismatch')
    return out


def s0(cfg,out,deadline):
    from windfarm_moe.release_bank import load_release_bank
    from scripts.run_matched_release import bankpath,read_phase
    parent_data(cfg);matched_parent(cfg);records={}
    for seed in cfg['seeds']:
        deadline_check(deadline);p,v,models,_,binding=models_for(cfg,seed)
        bank=load_release_bank(bankpath(p,'outer','Z',seed),
            expected_sha256=v['bank_manifest']['npz_sha256'],
            expected_metadata_sha256=v['bank_manifest']['metadata_sha256'])
        receipt,_=read_phase(p,'outer','outer',seed,'Z',v['phases']['outer'])
        actions=verify_original_actions(bank,models,{'outer':receipt})
        records[str(seed)]=dict(models=binding,source_A_action_sha256=array_sha(actions[7]),
            source_C_action_sha256=array_sha(actions[8]),source_route_sha256=array_sha(actions['route'],'<i8'),
            bank_manifest=v['bank_manifest'],source_action_shas_exact=True)
    save_new(out/'s0.json',dict(status='COMPLETED',model_bindings=records,environment=environment(),new_fits=0,
        matched_first_phase_actions_rebuilt=True,parent_family_complete=True))


def freeze(cfg,out,deadline):
    from windfarm_moe.release_bank import load_release_bank
    from scripts.run_matched_release import bankpath,read_phase
    from scripts.run_mixture_closed_loop import score_actions
    if read(out/'s0.json')['status']!='COMPLETED':raise ValueError('Source barrier absent')
    if (out/'FINAL_FREEZE.json').exists():raise FileExistsError('Fourth-cell freeze already exists')
    independent=independent_module();records={}
    for seed in cfg['seeds']:
        deadline_check(deadline);p,v,models,receipts,bindings=models_for(cfg,seed)
        manifest=v['bank_manifest'];bank=load_release_bank(bankpath(p,'outer','Z',seed),
            expected_sha256=manifest['npz_sha256'],expected_metadata_sha256=manifest['metadata_sha256'])
        parameters={};paths={};folder=out/'history'/f'seed{seed}';folder.mkdir(parents=True,exist_ok=False)
        for snap in SNAPS:
            par=freeze_parameters(receipts[snap,7],receipts[snap,8],models[snap,8]['tree'])
            par['source_bindings']=dict(global_source=bindings[f'{snap}:7'],gate_source=bindings[f'{snap}:8'])
            parameters[snap]=par;paths[snap]=folder/f'policy_{snap}.json';save_new(paths[snap],par)
        trees={k:models[k,8]['tree'] for k in SNAPS};view=action_view(bank)
        actual,route=fourth_actions(view,trees,parameters)
        rebuilt,manual_route,choices=independent.independent_actions(view,paths)
        if actual.tobytes()!=rebuilt.tobytes() or not np.array_equal(route,manual_route):
            raise ValueError('Independent historical node traversal/action mismatch')
        oldrec,oldz=read_phase(p,'outer','outer',seed,'Z',v['phases']['outer'])
        original=verify_original_actions(bank,models,{'outer':oldrec})
        if not np.array_equal(route,original['route']):
            raise ValueError('D route differs from original source C leaf IDs')
        daily,n,days=score_actions(actual,bank['shortfall'],bank['mask'],bank['anchors'])
        rd,rn,rday=independent.independent_daily(actual,bank['shortfall'],bank['mask'],bank['anchors'])
        if not np.allclose(daily,rd,rtol=0,atol=1e-8) or not np.array_equal(n,rn) or not np.array_equal(days,rday):
            raise ValueError('Independent historical daily mismatch')
        np.savez_compressed(folder/'history_actions.npz',actions=actual,route=route,anchors=bank['anchors'])
        np.savez_compressed(folder/'history_daily.npz',ledger=daily,counts=n,days=days)
        records[str(seed)]=dict(status='FROZEN',seed=seed,parameters={s:dict(path=str(paths[s].relative_to(out)),**bind(paths[s])) for s in SNAPS},
            model_bindings=bindings,bank_manifest=manifest,history_actions=bind(folder/'history_actions.npz'),
            history_daily=bind(folder/'history_daily.npz'),action_sha256=array_sha(actual),route_sha256=array_sha(route,'<i8'),
            independent_action_bytes_exact=True,independent_daily_max_abs=float(np.max(np.abs(daily-rd))),
            independent_choices=choices,evaluation_touched=False)
    save_new(out/'FINAL_FREEZE.json',dict(status='FROZEN',seeds=records,source_hashes=cfg['source_hashes'],
        protocol_sha256=sha(out/'protocol_original.json'),evaluation_touched=False,new_fits=0,environment=environment()))
    save_new(out/'EVALUATION_OPEN.json',dict(freeze_sha256=sha(out/'FINAL_FREEZE.json'),
        protocol_sha256=sha(out/'protocol_original.json'),source_hashes=cfg['source_hashes']))


def verified_freeze(cfg,out):
    f=read(out/'FINAL_FREEZE.json')
    opened=read(out/'EVALUATION_OPEN.json')
    if (opened['freeze_sha256']!=sha(out/'FINAL_FREEZE.json') or opened['source_hashes']!=cfg['source_hashes']
        or opened['protocol_sha256']!=sha(out/'protocol_original.json')):
        raise ValueError('Evaluation opening barrier differs')
    if f['source_hashes']!=cfg['source_hashes'] or f['protocol_sha256']!=sha(out/'protocol_original.json') or f['evaluation_touched']:
        raise ValueError('Fourth-cell freeze identity changed')
    if set(f['seeds'])!={str(seed) for seed in range(201,206)}:
        raise ValueError('All five historical instances must be frozen before evaluation')
    for seed,row in f['seeds'].items():
        for snap,rec in row['parameters'].items():
            if bind(out/rec['path'])!={k:rec[k] for k in ('sha256','bytes')}:raise ValueError('Frozen D policy changed')
            par=read(out/rec['path'])
            if par['source_bindings']!=dict(global_source=row['model_bindings'][f'{snap}:7'],gate_source=row['model_bindings'][f'{snap}:8']):
                raise ValueError('Frozen D policy source receipt/model bindings differ')
            if (float(par['global_receipt']['global_fit_stats']['alpha'])!=float(par['alpha_all'])
                or int(par['release_leaf']) not in {int(x) for x in par['gate_receipt']['leaf_stats']}):
                raise ValueError('Frozen D source coefficient/routing consistency differs')
        for name,key in [('history_actions.npz','history_actions'),('history_daily.npz','history_daily')]:
            if bind(out/'history'/f'seed{seed}'/name)!=row[key]:raise ValueError('Frozen D historical output changed')
    return f


def evaluate(cfg,out,seed,deadline):
    from windfarm_moe.matched_endpoint_bank import build_matched_bank
    from windfarm_moe.release_bank import load_release_bank
    from scripts.run_matched_release import bankpath,read_phase,check_bank
    from scripts.run_prospective_release import verify_prefix
    from scripts.run_mixture_closed_loop import score_actions
    f=verified_freeze(cfg,out);fsha=sha(out/'FINAL_FREEZE.json');independent=independent_module()
    if seed not in cfg['seeds']:raise ValueError('Unregistered fixed fit')
    folder=out/'evaluate'/f'seed{seed}'
    if folder.exists():raise FileExistsError('Evaluation output exists')
    p,v,models,receipts,bindings=models_for(cfg,seed);fr=f['seeds'][str(seed)]
    if bindings!=fr['model_bindings']:raise ValueError('Models changed after D freeze')
    hist=load_release_bank(bankpath(p,'outer','Z',seed),expected_sha256=v['bank_manifest']['npz_sha256'],expected_metadata_sha256=v['bank_manifest']['metadata_sha256'])
    deadline_check(deadline);bank=build_matched_bank(cfg['matched_protocol'],seed,'Z','outer',True,root=ROOT);check_bank(bank,'outer',True)
    if verify_prefix(hist,bank)!=1289:raise ValueError('Historical bank prefix differs')
    eval_receipt=read(p/'shards/evaluate'/f'{(seed-201)*3+2:02d}.json');binding=eval_receipt['versions']['outer']
    if sha(p/binding['metadata_path'])!=binding['metadata_sha256'] or read(p/binding['metadata_path'])!=bank['metadata']:
        raise ValueError('Full endpoint metadata differs')
    paths={s:out/fr['parameters'][s]['path'] for s in SNAPS};parameters={s:read(paths[s]) for s in SNAPS}
    for snap,par in parameters.items():
        if (par['global_receipt']!=receipts[snap,7] or par['gate_receipt']!=receipts[snap,8]
            or par['tree_nodes']!=tree_nodes(models[snap,8]['tree'])):
            raise ValueError('Frozen D parameter content differs from original A/C source')
    actual,route=fourth_actions(action_view(bank),{s:models[s,8]['tree'] for s in SNAPS},parameters)
    rebuilt,manual_route,choices=independent.independent_actions(action_view(bank),paths)
    if actual.tobytes()!=rebuilt.tobytes() or not np.array_equal(route,manual_route):
        raise ValueError('Independent evaluation node traversal/action mismatch')
    with np.load(out/'history'/f'seed{seed}'/'history_actions.npz') as z:
        if actual[:1289].tobytes()!=z['actions'].tobytes() or not np.array_equal(route[:1289],z['route']):
            raise ValueError('D action history prefix differs from pre-evaluation freeze')
    oldhistory,_=read_phase(p,'outer','outer',seed,'Z',v['phases']['outer'])
    oldeval,oldz=read_phase(p,'outer','evaluate',seed,'Z',binding['phase'])
    original=verify_original_actions(bank,models,{'outer':oldhistory,'evaluate':oldeval})
    if not np.array_equal(route,original['route']):
        raise ValueError('D evaluation route differs from original C leaf IDs')
    pp=Path(cfg['parent_results']);pc=read(pp/'completion.json')
    if sha(pp/'completion.json')!=cfg['parent_bindings']['completion.json']:
        raise ValueError('Parent B completion identity changed')
    bpath=pp.parent/'replay'/f'seed{seed}'/'receipt.json'
    if sha(bpath)!=pc['replay_receipts'][str(seed)]['sha256']:
        raise ValueError('Parent B action receipt changed')
    breceipt=read(bpath)
    sel=(bank['anchors']>=30240)&(bank['anchors']<35273);a,y,m=bank['anchors'][sel],bank['shortfall'][sel],bank['mask'][sel]
    daily,n,days=score_actions(actual[sel],y,m,a);rd,rn,rday=independent.independent_daily(actual[sel],y,m,a)
    ref,refn,refdays=score_actions(bank['reference'][sel],y,m,a)
    if (not np.allclose(daily,rd,rtol=0,atol=1e-8) or not np.array_equal(n,rn) or not np.array_equal(days,rday)
        or not np.array_equal(n,oldz['counts']) or not np.array_equal(days,oldz['days'])
        or not np.array_equal(ref,oldz['reference'])):raise ValueError('Independent evaluation ledger/population mismatch')
    folder.mkdir(parents=True,exist_ok=False)
    np.savez_compressed(folder/'daily.npz',ledger=daily,reference=ref,counts=n,days=days)
    np.savez_compressed(folder/'actions.npz',actions=actual[sel],route=route[sel],anchors=a)
    save_new(folder/'receipt.json',dict(status='COMPLETED',seed=seed,role=ROLE,freeze_sha256=fsha,
        source_hashes=cfg['source_hashes'],daily=bind(folder/'daily.npz'),actions=bind(folder/'actions.npz'),
        action_sha256=array_sha(actual[sel]),route_sha256=array_sha(route[sel],'<i8'),
        frozen_history_prefix_exact=True,independent_action_bytes_exact=True,independent_route_exact=True,
        independent_daily_max_abs=float(np.max(np.abs(daily-rd))),independent_choices=choices,
        source_A_action_sha256=array_sha(original[7][sel]),source_C_action_sha256=array_sha(original[8][sel]),
        source_B_action_sha256=breceipt['phases']['evaluate']['action_sha256'],source_B_receipt=bind(bpath),
        target_sha256=array_sha(y),mask_sha256=array_sha(m,None),full_bank_metadata_sha256=sha(p/binding['metadata_path']),
        metrics=(daily.sum(0)/n.sum()).tolist(),scored_cells=int(n.sum()),issues=int(sel.sum()),
        qualification_filter=False,new_fits=0,environment=environment()))


def extended_family(info):
    names=list(info['names']);available=list(info['available']);pairs=[_pair_names(p,names) for p in info['comparisons']]
    aliases=[_pair_names(p,names) for p in info['aliases']]
    if ROLE in names or (len(names),len(pairs),len(aliases))!=(1401,7260,152):raise ValueError('Invalid parent complete family')
    names.append(ROLE);available.append(True);pairs+=PAIRS
    if (len(set(pairs))!=7263 or len(available)!=1402 or len(aliases)!=152
        or len(set(names))!=1402 or 11*len(names)+10*len(pairs)!=N_COORDINATES):
        raise ValueError('Expanded family differs')
    return names,available,pairs,aliases


def aggregate(cfg,out,deadline):
    verified_freeze(cfg,out);parent,info,old=parent_data(cfg);names,available,pairs,aliases=extended_family(info)
    rows=[];bindings={}
    for si,seed in enumerate(cfg['seeds']):
        folder=out/'evaluate'/f'seed{seed}';r=read(folder/'receipt.json')
        if r['status']!='COMPLETED' or r['seed']!=seed or r['freeze_sha256']!=sha(out/'FINAL_FREEZE.json') or r['qualification_filter'] or r['source_hashes']!=cfg['source_hashes']:
            raise ValueError('Mandatory instance incomplete or changed')
        if bind(folder/'daily.npz')!=r['daily'] or bind(folder/'actions.npz')!=r['actions']:
            raise ValueError('Evaluation result identity changed')
        with np.load(folder/'daily.npz') as z:
            if (not np.array_equal(z['counts'],old['counts']) or not np.array_equal(z['days'],old['day_ids'])
                or not np.allclose(z['reference'],old['ledger'][si,0],atol=1e-8,rtol=0)
                or z['ledger'].shape!=(35,4)):raise ValueError('Reference/population bridge differs')
            rows.append(z['ledger'].copy())
        bindings[str(seed)]=bind(folder/'receipt.json')
    data=np.concatenate([old['ledger'],np.stack(rows)[:,None]],axis=1);folder=out/'step3';folder.mkdir(parents=True,exist_ok=False)
    np.savez_compressed(folder/'all_daily_ledger.npz',ledger=data,counts=old['counts'],day_ids=old['day_ids'])
    save_new(folder/'all_policy_names.json',dict(names=names,available=available,comparisons=pairs,aliases=aliases,nominal_family_size=N_COORDINATES))
    for span in cfg['spans']:
        deadline_check(deadline);inf=infer_stable_campaign(data,old['counts'],names,pairs,span=span,seed=20261022,n_boot=20000,available=available,aliases=aliases)
        if inf['family_size']!=N_COORDINATES:raise ValueError('Nominal family changed')
        save_new(folder/f'inference_span{span}.json',inf)
    files=['all_daily_ledger.npz','all_policy_names.json']+[f'inference_span{s}.json' for s in cfg['spans']]
    save_new(folder/'completion.json',dict(status='COMPLETED',files={n:bind(folder/n) for n in files},
        source_hashes=cfg['source_hashes'],parent_prefix_exact=True,mandatory_fixed_fits=cfg['seeds'],
        evaluation_receipts=bindings,new_fits=0,qualification_filter=False,independent_confirmation=False,environment=environment()))


def main():
    p=argparse.ArgumentParser();p.add_argument('--protocol',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--stage',choices=['s0','freeze','evaluate','aggregate'],required=True);p.add_argument('--seed',type=int,default=201);a=p.parse_args()
    if not os.environ.get('PBS_JOBID'):raise ValueError('Bounded PBS job required')
    cfg=read(a.protocol);config_check(cfg);source_check(cfg);a.output.mkdir(parents=True,exist_ok=True)
    pc=a.output/'protocol_original.json'
    if pc.exists():
        if pc.read_bytes()!=a.protocol.read_bytes():raise ValueError('Protocol changed')
    else:
        with pc.open('xb') as f:f.write(a.protocol.read_bytes())
    deadline=time.monotonic()+cfg['stage_limits'][a.stage]
    try:
        with threadpool_limits(limits=1):
            if a.stage=='evaluate':evaluate(cfg,a.output,a.seed,deadline)
            else:globals()[a.stage](cfg,a.output,deadline)
    except BaseException as exc:
        save_new(a.output/'failures'/f'{a.stage}_{a.seed}_{os.environ["PBS_JOBID"]}.json',dict(error=repr(exc),traceback=traceback.format_exc(),environment=environment()))
        raise


if __name__=='__main__':main()
