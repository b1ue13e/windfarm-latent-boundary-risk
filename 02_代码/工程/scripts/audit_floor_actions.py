"""Replay every evaluation action in the two-program residual addendum."""
import argparse,json,hashlib,sys,os,time,platform
from repo_paths import Path, repository_root
import numpy as np


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    a=parser.parse_args();start=time.monotonic();p=a.run/'results/campaign';a.output.mkdir(parents=True,exist_ok=False)
    sys.path.insert(0,str(a.run))
    from windfarm_moe.protected_residual import residual_experts,guarded_action
    from windfarm_moe.actual_mixture_update import MixtureConfig,run_mixture
    cfg=json.loads((p/'protocol.json').read_text());folder=Path(cfg['evaluation_cache'])
    anchors=np.load(folder/'anchors.npy');target=np.load(folder/'shortfall.npy');mask=np.load(folder/'mask.npy');checks=[]
    for seed in range(201,206):
        base=np.load(p/f'profiles/evaluate_seed{seed}.npy')
        for arm in ['P','Z']:
            x=np.load(folder/f'{arm}_seed{seed}.npy');delta=residual_experts(x,base)
            init=json.loads((p/f'initializers/evaluate/{arm}_seed{seed}.json').read_text());w=np.asarray(init['canonical_initial'])
            fixed=guarded_action(base,delta,w)
            online=base+run_mixture(delta,np.maximum(target-base,0),mask,anchors,
                [MixtureConfig(**cfg['online_config'][arm])],w,score=False,return_actions=True)['actions'][0]
            expected=np.load(p/f'instances/evaluate/{arm}_seed{seed}/daily.npz')['ledger']
            receipt=json.loads((p/f'instances/evaluate/{arm}_seed{seed}/receipt.json').read_text())
            for i,r in enumerate([fixed,online]):
                body=hashlib.sha256(np.ascontiguousarray(r,dtype='<f8').tobytes()).hexdigest();assert body==receipt['action_sha256'][i]
                assert np.all(r>=base);rows=[]
                for day in np.unique(anchors//144):
                    ix=anchors//144==day;m=mask[ix];v=r[ix][m];y=target[ix][m];u=np.maximum(y-v,0)
                    rows.append([np.sum(v+10*u)/6,np.sum(v)/6,np.sum(u)/6,np.count_nonzero(y>v)])
                error=float(np.max(np.abs(np.asarray(rows)-expected[i])))
                assert error<1e-7 and np.array_equal(np.asarray(rows)[:,3],expected[i,:,3])
                checks.append(dict(seed=seed,arm=arm,program=i,action_hash_equal=True,
                    independent_daily_max_error=error,strict_events_equal=True,pointwise_floor=True))
    result=dict(status='VERIFIED',checks=checks,job_id=os.environ.get('PBS_JOBID'),host=platform.node(),
        python=sys.version,numpy=np.__version__,elapsed_seconds=time.monotonic()-start,
        frozen_generator_reused=True,independent_scoring=True,new_fit=False,science_target_unchanged=True)
    (a.output/'audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(status='VERIFIED',cases=len(checks),elapsed=result['elapsed_seconds'])))


if __name__=='__main__':main()
