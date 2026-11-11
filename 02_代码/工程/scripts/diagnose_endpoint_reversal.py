"""Read-only attribution of frozen endpoint losses; no fits or new decisions."""
from repo_paths import Path, repository_root
import sys,json,argparse,hashlib,platform,os,time
ROOT=Path(repository_root());sys.path.insert(0,str(ROOT))
import numpy as np
from threadpoolctl import threadpool_limits
from windfarm_moe.release_bank import build_release_bank,COST_CALIBRATION_CONFIG
from scripts.run_meta_pool import load_verified_parent_stream_bank
from windfarm_moe.release_bank import verify_parent_campaign_freeze
from windfarm_moe.meta_action_stream import join_banks,prefix_sha256
from windfarm_moe.delayed_calibration_baselines import run_delayed_calibration

def attribution(safe,cost,shortfall,mask):
    """Exact C=R+10U identity, decomposed by realized action order."""
    b,c,s=[np.asarray(v,dtype=float)[mask] for v in (safe,cost,shortfall)]
    n=len(s)
    if n==0:raise ValueError('Empty population')
    dr=(c-b)/6;du=(np.maximum(s-c,0)-np.maximum(s-b,0))/6;dc=dr+10*du
    out=dict(cells=n,delta_C=float(dc.mean()),delta_R=float(dr.mean()),delta_U=float(du.mean()),
        delta_10U=float(10*du.mean()),shortfall_mean=float(s.mean()),shortfall_nonzero_fraction=float(np.mean(s>0)),
        shortfall_quantiles=np.quantile(s,[.5,.9,.95,.99],method='higher').tolist(),groups={})
    for name,use in [('release',c<b),('add',c>b),('equal',c==b),('target_zero',s==0),('target_positive',s>0)]:
        rr=float(dr[use].sum()/n);uu=float(du[use].sum()/n)
        out['groups'][name]=dict(cells=int(use.sum()),fraction=float(use.mean()),
            delta_R_contribution=rr,delta_U_contribution=uu,delta_C_contribution=rr+10*uu,
            shortage_to_procurement_ratio=None if rr==0 else float(uu/(-rr)))
    assert abs(out['delta_C']-sum(out['groups'][k]['delta_C_contribution'] for k in ('release','add','equal')))<1e-10
    return out

def summarize_rows(b,c,s,m):
    a=attribution(b,c,s,m)
    def point(r):
        x=r[m];y=s[m];u=np.maximum(y-x,0)/6
        return dict(C=float(np.mean(x/6+10*u)),R=float(np.mean(x/6)),U=float(np.mean(u)),V=float(np.mean(y>x)))
    a.update(safe=point(b),cost=point(c))
    return a

def run(cfg,seed,out):
    if out.exists():raise FileExistsError(out)
    start=time.process_time()
    bank=build_release_bank(cfg,seed,'Z',True,root=ROOT)
    mc,freeze,_=verify_parent_campaign_freeze(cfg['stream_parent_results'],cfg['stream_parent_freeze_sha256'])
    phases=['inner','outer','evaluate']
    sources=[load_verified_parent_stream_bank(mc,freeze,p,seed,'Z')[0] for p in phases]
    joined=join_banks(sources);raw=joined['raw_actions'][12]
    assert np.array_equal(joined['anchors'],bank['anchors'])
    assert joined['shortfall'].tobytes()==bank['shortfall'].tobytes() and joined['mask'].tobytes()==bank['mask'].tobytes()
    cal=run_delayed_calibration(raw,bank['shortfall'],bank['mask'],bank['anchors'],COST_CALIBRATION_CONFIG,save_trace=True)
    assert prefix_sha256(cal.actions)==prefix_sha256(bank['cost'])
    a=bank['anchors'];b=bank['safe'];c=bank['cost'];s=bank['shortfall'];m=bank['mask']
    windows=dict(inner=(28087,28937),outer=(28944,30233),evaluate=(30240,35273),
        A=(28526,28937),B=(28944,29376),C=(29384,30233),
        eval_first7=(30240,31248),eval_after7=(31248,35273))
    result={};trace=[]
    for name,(lo,hi) in windows.items():
        use=(a>=lo)&(a<hi)
        summary=summarize_rows(b[use],c[use],s[use],m[use])
        summary['raw_vs_safe']=summarize_rows(b[use],raw[use],s[use],m[use])
        summary['cal_vs_raw']=summarize_rows(raw[use],c[use],s[use],m[use])
        shift=cal.trace['shift'][use]
        summary['calibration_shift']=dict(first=float(shift[0]),last=float(shift[-1]),min=float(shift.min()),
            max=float(shift.max()),mean=float(shift.mean()),negative_fraction=float(np.mean(shift<0)))
        summary['issue_count']=int(use.sum())
        summary['action_hashes']={k:prefix_sha256(v[use]) for k,v in [('safe',b),('raw12',raw),('cost',c)]}
        result[name]=summary
    for day in np.unique(a//144):
        use=a//144==day
        d=summarize_rows(b[use],c[use],s[use],m[use]);d.update(day=int(day),phase='inner' if a[use][0]<28937 else 'outer' if a[use][0]<30233 else 'evaluate')
        d['raw_vs_safe_delta_C']=attribution(b[use],raw[use],s[use],m[use])['delta_C']
        trace.append(d)
    r=dict(status='FROZEN_ENDPOINT_ATTRIBUTION_ONLY',seed=seed,arm='Z',windows=result,daily=trace,
        fitting_performed=False,new_policy_actions=False,calibration_replayed_not_refitted=True,
        bootstrap_performed=False,cpu_seconds=time.process_time()-start,
        environment=dict(python=sys.version,numpy=np.__version__,hostname=platform.node(),pbs_jobid=os.environ.get('PBS_JOBID')),
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        input_protocol_sha256=hashlib.sha256(json.dumps(cfg,sort_keys=True).encode()).hexdigest())
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps(dict(seed=seed,cpu_seconds=r['cpu_seconds'],status=r['status'])))
    return r
def main():
    p=argparse.ArgumentParser();p.add_argument('--protocol',type=Path,required=True);p.add_argument('--seed',type=int,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.seed not in range(201,206) or not os.environ.get('PBS_JOBID'):raise ValueError('Fixed seed and bounded allocation required')
    with threadpool_limits(limits=1):run(json.loads(a.protocol.read_text()),a.seed,a.output)
if __name__=='__main__':main()
