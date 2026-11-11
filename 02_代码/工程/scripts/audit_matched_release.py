"""Independent tree traversal and daily scoring for fixed-vintage trajectories."""
from repo_paths import Path, repository_root
import sys,json,argparse,time,hashlib
ROOT=Path(repository_root());sys.path.insert(0,str(ROOT))
import numpy as np
import joblib
from threadpoolctl import threadpool_limits
from scripts.audit_release_actions import traverse
from windfarm_moe.matched_endpoint_bank import build_matched_bank

PHASES={'inner':(28087,28937),'outer':(28944,30233),'evaluate':(30240,35273)}
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(cfg,out,dst,seed_filter=None):
    if dst.exists():raise FileExistsError(dst)
    start=time.process_time();freeze=json.loads((out/'FINAL_FREEZE.json').read_text())
    count=records=0;maxerr=0.
    for shard,h in enumerate(freeze['histories']):
        seed=201+shard//3;arm=('C','P','Z')[shard%3]
        if seed_filter is not None and seed!=seed_filter:
            continue
        if digest(out/h['path'])!=h['sha256']:raise ValueError('Historical identity changed')
        for vintage,hr in h['versions'].items():
            bank=build_matched_bank(cfg,seed,arm,vintage,True,root=ROOT)
            models={}
            for m in hr['models']:
                if digest(out/m['path'])!=m['sha256']:raise ValueError('Model byte identity differs')
                model=joblib.load(out/m['path']);models[m['snapshot'],m['recipe_id']]=model;records+=1
            enabled=sorted([(k,int(values[1])) for k,values in cfg['snapshots'][vintage].items()],key=lambda z:z[1])
            for rid in range(24):
                action=bank['safe'].copy()
                if rid<=6:
                    use=np.ones(len(bank['anchors']),dtype=bool)
                    action[:]=traverse(models[enabled[0][0],rid],bank,use)
                else:
                    for j,(key,lo) in enumerate(enabled):
                        hi=enabled[j+1][1] if j+1<len(enabled) else 10**10
                        use=(bank['anchors']>=lo)&(bank['anchors']<hi)
                        if use.any():action[use]=traverse(models[key,rid],bank,use)
                phases=PHASES if vintage=='inner' else {k:PHASES[k] for k in ['outer','evaluate']}
                for phase,(lo,hi) in phases.items():
                    use=(bank['anchors']>=lo)&(bank['anchors']<hi)
                    a=bank['anchors'][use];r=action[use];s=bank['shortfall'][use];mask=bank['mask'][use]
                    folder=out/vintage/'instances'/phase/f'{arm}_seed{seed}'
                    rec=json.loads((folder/'receipt.json').read_text())
                    actual=hashlib.sha256(np.ascontiguousarray(r,dtype='<f8').tobytes()).hexdigest()
                    if actual!=rec['policies'][str(rid)]['action_sha256']:raise ValueError('Independent action SHA mismatch')
                    rows=[];counts=[]
                    for day in np.unique(a//144):
                        d=a//144==day;rr=r[d][mask[d]];yy=s[d][mask[d]];u=np.maximum(yy-rr,0)/6
                        rows.append([np.sum(rr/6+10*u),np.sum(rr/6),np.sum(u),np.count_nonzero(yy>rr)]);counts.append(len(rr))
                    with np.load(folder/'daily.npz') as z:
                        if not np.array_equal(counts,z['counts']):raise ValueError('Population mismatch')
                        err=float(np.max(abs(np.asarray(rows)-z['ledger'][rid])))
                        if err>1e-8:raise ValueError('Independent loss differs beyond original tolerance')
                    maxerr=max(maxerr,err);count+=1
    expected_instances=1800 if seed_filter is None else 360
    expected_models=2520 if seed_filter is None else 504
    if count!=expected_instances or records!=expected_models:raise ValueError('Incomplete independent replay')
    result=dict(status='INDEPENDENT_MATCHED_ACTION_REPLAY_VERIFIED',scored_instances=count,model_records=records,
        production_prediction_or_scheduler_imported=False,production_loss_imported=False,
        maximum_daily_sum_difference=maxerr,tolerance_unchanged=1e-8,cpu_seconds=time.process_time()-start,seed=seed_filter)
    dst.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
def main():
    p=argparse.ArgumentParser();p.add_argument('--protocol',type=Path,required=True);p.add_argument('--results',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--seed',type=int,choices=range(201,206))
    a=p.parse_args()
    with threadpool_limits(limits=1):run(json.loads(a.protocol.read_text()),a.results,a.output,a.seed)
if __name__=='__main__':main()
