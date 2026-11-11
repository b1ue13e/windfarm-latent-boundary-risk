"""Replay release rules by explicit tree traversal and independent cell losses."""
from repo_paths import Path, repository_root
import sys,argparse,json,hashlib,time
ROOT=Path(repository_root())
sys.path.insert(0,str(ROOT))
import numpy as np
import joblib
from threadpoolctl import threadpool_limits
from windfarm_moe.release_bank import build_release_bank

SNAPS=(('A',28526,28944),('B',28944,29384),('C',29384,30240),('D',30240,10**10))
PHASES={'inner':(28087,28937),'outer':(28944,30233),'evaluate':(30240,35273)}
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def traverse(model,bank,sel):
    b,c=bank['safe'][sel],bank['cost'][sel]
    if model.get('fallback_to_safe'):return b.copy()
    kind=model['kind']
    if kind in ('SAFE','COST','CONSTANT','GLOBAL_FIT'):
        a=float(model['alpha'])
        return b.copy() if a==0 else c.copy() if a==1 else np.maximum(b+a*(c-b),0)
    x=bank['current_features' if model['feature_set']=='current' else 'feedback_features'][sel]
    x=np.asarray(x,dtype=np.float32).reshape(-1,x.shape[-1])
    tree=model['tree'].tree_
    ids=np.zeros(len(x),dtype=np.int64)
    for _ in range(3):
        active=tree.children_left[ids]>=0
        if not active.any():break
        rows=np.flatnonzero(active);n=ids[active]
        ids[rows]=np.where(x[rows,tree.feature[n]]<=tree.threshold[n],tree.children_left[n],tree.children_right[n])
    if np.any(tree.children_left[ids]>=0):raise ValueError('Tree exceeds fixed depth two')
    values=model['leaf_alphas' if kind=='GATE' else 'leaf_shifts']
    vals=np.array([values[int(k)] for k in ids]).reshape(b.shape)
    return np.maximum(b+vals*(c-b),0) if kind=='GATE' else np.maximum(c+vals,0)

def run(results,cfg,output):
    if output.exists():raise FileExistsError(output)
    start=time.process_time();freeze=json.loads((results/'FINAL_FREEZE.json').read_text())
    count=0;maxerr=0.;models_checked=0
    for si,seed in enumerate(range(201,206)):
        for ai,arm in enumerate(('C','P','Z')):
            shard=si*3+ai
            hist=freeze['histories'][shard]
            models={}
            for item in hist['models']:
                p=results/item['path']
                assert digest(p)==item['sha256']
                models[item['snapshot'],item['recipe_id']]=joblib.load(p);models_checked+=1
            bank=build_release_bank(cfg,seed,arm,True,root=ROOT)
            meta=json.loads((results/'shards/evaluate'/f'shard_{shard:02d}_{arm}_seed{seed}'/'full_bank_metadata.json').read_text())
            for key in ('safe_sha256','cost_sha256','shortfall_raw_sha256','mask_sha256','anchors_sha256','current_features_sha256','feedback_features_sha256'):
                assert bank['metadata'][key]==meta[key],key
            for rid in range(24):
                action=bank['safe'].copy()
                for key,start_a,stop_a in SNAPS:
                    sel=(bank['anchors']>=start_a)&(bank['anchors']<stop_a)
                    if rid<7 and key=='A':sel=bank['anchors']<stop_a
                    if sel.any():action[sel]=traverse(models[key,rid],bank,sel)
                for phase,(lo,hi) in PHASES.items():
                    use=(bank['anchors']>=lo)&(bank['anchors']<hi)
                    r=action[use];s=bank['shortfall'][use];m=bank['mask'][use];a=bank['anchors'][use]
                    folder=results/'instances'/phase/f'{arm}_seed{seed}'
                    rec=json.loads((folder/'receipt.json').read_text())['policies'][str(rid)]
                    actualhash=hashlib.sha256(np.ascontiguousarray(r,dtype='<f8').tobytes()).hexdigest()
                    assert actualhash==rec['action_sha256'],(seed,arm,rid,phase)
                    rows=[];ns=[]
                    for day in np.unique(a//144):
                        d=(a//144)==day;rr=r[d][m[d]];yy=s[d][m[d]]
                        u=np.maximum(yy-rr,0)/6
                        rows.append([np.sum(rr/6+10*u),np.sum(rr/6),np.sum(u),np.count_nonzero(yy>rr)])
                        ns.append(len(rr))
                    with np.load(folder/'daily.npz') as z:
                        assert np.array_equal(ns,z['counts'])
                        diff=float(np.max(abs(np.asarray(rows)-z['ledger'][rid])))
                        assert diff<=1e-8,(seed,arm,rid,phase,diff)
                    maxerr=max(maxerr,diff);count+=1
    result=dict(status='INDEPENDENT_ACTION_REPLAY_MATCHES',scored_instances=count,model_records_verified=models_checked,
        prediction_api_imported=False,production_loss_imported=False,max_daily_sum_error=maxerr,
        original_tolerance=1e-8,cpu_seconds=time.process_time()-start)
    output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
    return result
def main():
    p=argparse.ArgumentParser();p.add_argument('--results',type=Path,required=True);p.add_argument('--protocol',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    with threadpool_limits(limits=1):run(a.results,json.loads(a.protocol.read_text()),a.output)
if __name__=='__main__':main()
