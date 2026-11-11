"""Replay frozen generators and independently score their sealed actions."""
import argparse,hashlib,json,os,platform,sys,time
from repo_paths import Path, repository_root
import numpy as np


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def independent_days(actions,y,mask,anchors):
    rows=[]
    for day in np.unique(anchors//144):
        ix=anchors//144==day;valid=mask[ix];r=actions[ix][valid];s=y[ix][valid]
        short=np.maximum(s-r,0)
        rows.append([np.sum(r+10*short)/6,np.sum(r)/6,np.sum(short)/6,np.count_nonzero(s>r)])
    return np.asarray(rows)


def deficit_bins(actions,y,mask):
    d=(y-actions)[mask]
    return [int(np.count_nonzero((d>0)&(d<=1))),int(np.count_nonzero((d>1)&(d<=5))),
            int(np.count_nonzero((d>5)&(d<=20))),int(np.count_nonzero(d>20))]


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();out=args.output;out.mkdir(parents=True,exist_ok=False)
    start=time.monotonic();p=args.run/'results/campaign';cfg=json.loads((p/'protocol.json').read_text())
    versions=json.loads((p/'source_versions.json').read_text());assert all(sha(args.run/k)==v for k,v in versions.items())
    sys.path.insert(0,str(args.run))
    from windfarm_moe.actual_mixture_update import MixtureConfig,run_mixture,run_matched_ew
    from windfarm_moe.delayed_calibration_baselines import DelayedCalibrationConfig,run_delayed_calibration
    cache=Path(cfg['evaluation_cache']);a=np.load(cache/'anchors.npy');y=np.load(cache/'shortfall.npy');m=np.load(cache/'mask.npy')
    h=Path(cfg['historical_cache']);ha=np.load(h/'anchors.npy');hy=np.load(h/'shortfall.npy');hm=np.load(h/'mask.npy')
    verified=[];bins=[];errors=[]
    for seed in range(201,206):
        for arm in ['P','Z']:
            x=np.load(cache/f'{arm}_seed{seed}.npy')
            folder=p/f'instances/evaluate/{arm}_seed{seed}'
            expected=np.load(folder/'daily.npz')['ledger'];receipt=json.loads((folder/'receipt.json').read_text())
            initial={g:json.loads((p/f'initializers/evaluate/{g}_{arm}_seed{seed}.json').read_text()) for g in ['COST','CAP']}
            def compare(recipe,r):
                rid=recipe['id'];digest=hashlib.sha256(np.ascontiguousarray(r,dtype='<f8').tobytes()).hexdigest()
                error=float(np.max(np.abs(independent_days(r,y,m,a)-expected[rid])))
                vequal=np.array_equal(independent_days(r,y,m,a)[:,3],expected[rid,:,3])
                row=dict(id=rid,seed=seed,arm=arm,action_hash_equal=digest==receipt['action_sha256'][str(rid)],
                    independent_daily_max_error=error,strict_V_counts_exact=bool(vequal))
                verified.append(row)
                if not row['action_hash_equal'] or not vequal or error>1e-7:errors.append(row)
            for recipe in [r for r in cfg['recipes'] if r['family']=='controls']:
                rec=initial[recipe['goal']]
                if recipe['kind']=='control_exact':r=np.sum(x*np.asarray(rec['weights']),axis=-1)
                elif recipe['kind']=='control_fixed':r=np.sum(x*np.asarray(rec['canonical_initial']),axis=-1)
                else:r=run_matched_ew(x,y,m,a,np.asarray(rec['canonical_initial']))
                compare(recipe,r)
            for goal in ['COST','CAP']:
                group=[r for r in cfg['recipes'] if r['kind']=='actual' and r['goal']==goal]
                result=run_mixture(x,y,m,a,[MixtureConfig(**r['config']) for r in group],
                    np.asarray(initial[goal]['canonical_initial']),score=False,return_actions=True)
                for j,recipe in enumerate(group):compare(recipe,result['actions'][j])
            if arm=='P':
                hx=np.load(h/f'{arm}_seed{seed}.npy',mmap_mode='r')
                reference=np.r_[hx[:,:,0],x[:,:,0]];target=np.r_[hy,y];valid=np.r_[hm,m];anchors=np.r_[ha,a]
                for rid in [182,186]:
                    recipe=cfg['recipes'][rid];old=recipe['legacy']
                    action=run_delayed_calibration(reference,target,valid,anchors,
                        DelayedCalibrationConfig(**old['config']),save_trace=False).actions[len(ha):]
                    compare(recipe,action)
                    bins.append(dict(id=rid,seed=seed,bins=['(0,1]kW','(1,5]kW','(5,20]kW','>20kW'],
                        reference_counts=deficit_bins(x[:,:,0],y,m),candidate_counts=deficit_bins(action,y,m),
                        independent_energy_sums=independent_days(action,y,m,a).sum(axis=0).tolist()))
    result=dict(status='VERIFIED' if not errors else 'REPLAY_DISCREPANCIES_PRESERVED',job_id=os.environ.get('PBS_JOBID'),
        python=sys.version,numpy=np.__version__,host=platform.node(),elapsed_seconds=time.monotonic()-start,
        source_versions_match=True,generator='same sealed generator; no independent optimizer-proof claim',
        scoring='independent energy reduction and strict event counts',verified_cases=verified,
        discrepancy_cases=errors,deficit_bins=bins,original_thresholds_changed=False,new_fit=False)
    (out/'audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(status=result['status'],cases=len(verified),errors=len(errors),elapsed=result['elapsed_seconds'])))
    if errors:raise SystemExit(1)


if __name__=='__main__':main()
