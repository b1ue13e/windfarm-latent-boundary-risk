"""Independent cell-to-day reconciliation for the completed add-back pilot."""
from repo_paths import Path, repository_root
import argparse,json
import numpy as np
import pandas as pd


def audit(runs,summary,out):
    if out.exists():raise ValueError('Audit output already exists')
    records=[]
    for seed in range(201,206):
        root=runs/f'seed{seed}'
        receipt=json.loads((root/'receipt.json').read_text())
        assert receipt['status']=='COMPLETED_DEVELOPMENT'
        bridge=json.loads((root/'parent_bridge.json').read_text())
        assert all(value<=1e-9 for value in bridge.values())
        clock=json.loads((root/'probe_clock.json').read_text())
        assert len(clock['removed_issues'])==6
        metrics=pd.read_csv(root/'metrics.csv')
        with np.load(root/'evaluation_coordinates.npz') as coordinates:
            s=coordinates['shortfall'];m=coordinates['mask'];anchors=coordinates['anchors'];groups=coordinates['groups']
        assert s.shape==m.shape and m.sum()==672939
        ids=anchors//144
        assert len(np.unique(ids))==35
        with np.load(root/'daily.npz') as days,np.load(root/'actions.npz') as actions:
            for row in metrics.to_dict('records'):
                key=row['arm']+'__'+row['version'];r=actions[key]
                reserve=np.zeros_like(s);u=np.zeros_like(s);v=np.zeros_like(s)
                reserve[m]=r[m]/6
                u[m]=np.maximum(s[m]-r[m],0)/6
                v[m]=(s[m]>r[m]).astype(float)
                costs=reserve+10*u
                for metric,grid in [('R',reserve),('U',u),('V',v),('C',costs)]:
                    np.testing.assert_allclose(grid.sum()/m.sum(),row[metric],rtol=1e-12,atol=1e-11)
                    for group,gm in [('all',m),('other',m&(groups==0)),('down',m&(groups==1)),('unknown',m&(groups==2))]:
                        expected=np.asarray([np.where(gm[ids==d],grid[ids==d],0).sum() for d in np.unique(ids)])
                        np.testing.assert_allclose(days[key+'__'+group+'__'+metric],expected,rtol=1e-12,atol=1e-8)
                assert row['N']==m.sum()
                records.append(dict(seed=seed,arm=row['arm'],version=row['version'],verified=True))
    infer=json.loads((summary/'inference.json').read_text())
    assert infer['family_size']==58 and infer['count']==672939 and infer['n_days']==35
    intervals=json.loads((summary/'paired_intervals.json').read_text())
    assert len(intervals)==58*3
    assert all(r['point'] is not None or r['status'].startswith('UNRESOLVED') for r in intervals)
    result=dict(status='ACCOUNTING_AND_IDENTITY_RECONCILED',rows=records,
                statistical_scope='No independent validation of temporal coverage or mechanism',
                no_new_fits=True,no_original_files_modified=True)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print('AUDITED',len(records),'seed/arm/version rows',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--runs',type=Path,required=True)
    p.add_argument('--summary',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();audit(a.runs,a.summary,a.out)
