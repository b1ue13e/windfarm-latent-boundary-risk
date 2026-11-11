"""Reconcile the new finite calibration programs independently from cell actions."""
from repo_paths import Path, repository_root
import argparse,json
import numpy as np
import pandas as pd


def main():
    p=argparse.ArgumentParser();p.add_argument('--runs',type=Path,required=True)
    p.add_argument('--summary',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    args=p.parse_args()
    if args.out.exists():raise ValueError('Preserve old audit')
    count=0
    for seed in range(201,206):
        root=args.runs/f'seed{seed}'
        receipt=json.loads((root/'receipt.json').read_text());assert receipt['status']=='COMPLETED_DEVELOPMENT'
        assert all(v<=1e-9 for v in json.loads((root/'parent_bridge.json').read_text()).values())
        rows=pd.read_csv(root/'metrics.csv');assert len(rows)==60
        with np.load(root/'coordinates.npz') as z:coords={k:z[k] for k in z.files}
        with np.load(root/'actions.npz') as aa,np.load(root/'daily.npz') as dd:
            for row in rows.to_dict('records'):
                phase=row['phase'];key=row['key'];r=aa[key+'__'+phase]
                s=coords[phase+'__shortfall'];mask=coords[phase+'__mask'];anchors=coords[phase+'__anchors']
                if phase=='evaluate':assert mask.sum()==672939
                assert int(mask.sum())==row['N'] and np.isfinite(r[mask]).all() and np.all(r[mask]>=0)
                rv=np.where(mask,r/6,0);uv=np.where(mask,np.maximum(s-r,0)/6,0)
                vv=mask&(s>r);cv=rv+10*uv
                for metric,grid in [('R',rv),('U',uv),('V',vv),('C',cv)]:
                    np.testing.assert_allclose(grid.sum()/mask.sum(),row[metric],rtol=1e-12,atol=1e-11)
                    expected=[grid[anchors//144==day].sum() for day in np.arange((anchors//144).min(),(anchors//144).max()+1)]
                    np.testing.assert_allclose(expected,dd[key+'__'+phase+'__all__'+metric],rtol=1e-12,atol=1e-8)
                count+=1
    perfit=pd.read_csv(args.summary/'per_fit.csv')
    means=perfit[perfit.phase=='select'].groupby('key').C.mean()
    selection=json.loads((args.summary/'choices.json').read_text());assert not selection['uses_evaluation_selection']
    choice=selection['choices']
    for name,reps in [('POWER',['COMPACT','FULL']),('SCORE',['COMPACT_G'])]:
        keys=[k for k in means.index if k.split('__')[0] in reps]
        assert abs(means[choice[name]]-means[keys].min())<1e-12
    zkeys=[k for k in means.index if k.split('__')[0] in ['COMPACT_Z','FULL_Z']]+[choice['POWER']]
    assert abs(means[choice['PITCH']]-means[zkeys].min())<1e-12
    for span,record in json.loads((args.summary/'inference.json').read_text()).items():
        assert record['n_coordinates']==370
    intervals=json.loads((args.summary/'intervals.json').read_text());assert len(intervals)==1110
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(dict(status='ACCOUNTING_AND_HISTORICAL_SELECTION_RECONCILED',
        metric_rows=count,replication='five fixed fitted instances on shared weather',
        coverage_certified=False,mechanism_certified=False),indent=2),encoding='utf-8')
    print('AUDITED',count,'metric rows',flush=True)


if __name__=='__main__':main()
