"""Independent accounting and selection-rule verification for fair joint runs."""
from repo_paths import Path, repository_root
import argparse,json
import numpy as np
import pandas as pd


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--protocol',type=Path,required=True)
    parser.add_argument('--runs',type=Path,required=True);parser.add_argument('--summary',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();cfg=json.loads(args.protocol.read_text());verified=0
    for seed in cfg['seeds']:
        root=args.runs/f'seed{seed}';rows=pd.read_csv(root/'metrics.csv');assert len(rows)==36
        metadata=json.loads((root/'models.json').read_text())
        for rep,width in [('FULL_DYN',118),('FULL_DYN_G',119),('FULL_DYN_Z',125)]:
            for model in cfg['models']:assert metadata[rep+'__'+model]['n_features']==width
        with np.load(root/'coordinates.npz') as z:coords={k:z[k] for k in z.files}
        with np.load(root/'actions.npz') as actions,np.load(root/'daily.npz') as days:
            for row in rows.to_dict('records'):
                key=row['key'];phase=row['phase'];r=actions[key+'__'+phase]
                s=coords[phase+'__shortfall'];mask=coords[phase+'__mask'];anchors=coords[phase+'__anchors']
                assert int(mask.sum())==row['N'] and np.isfinite(r[mask]).all() and np.all(r[mask]>=0)
                if phase=='evaluate':assert row['N']==672939
                R=np.where(mask,r/6,0);U=np.where(mask,np.maximum(s-r,0)/6,0);V=mask&(s>r)
                for metric,grid in [('C',R+10*U),('R',R),('U',U),('V',V)]:
                    np.testing.assert_allclose(grid.sum()/mask.sum(),row[metric],rtol=1e-12,atol=1e-10)
                    expected=[grid[anchors//144==d].sum() for d in np.unique(anchors//144)]
                    np.testing.assert_allclose(expected,days[key+'__'+phase+'__all__'+metric],rtol=1e-12,atol=1e-8)
                verified+=1
    summary=args.summary;hist=json.loads((summary/'historical_endpoints.json').read_text())
    assert len(hist)==528
    choices=json.loads((summary/'choices.json').read_text());assert not choices['uses_evaluation_selection']
    eligible={}
    for key,advertised in choices['eligible'].items():
        selected=[r for r in hist if r['left']==key]
        C=[r for r in selected if r['metric']=='D'];H=[r for r in selected if r['metric']=='H'];V=[r for r in selected if r['metric']=='V']
        good=(len(C)==1 and len(H)==5 and len(V)==5 and all(r['upper'] is not None and not r['unknown'] for r in selected)
              and C[0]['upper']<=.01 and all(r['upper']<=.001 for r in H) and all(r['upper']<=.1 for r in V))
        assert good==advertised;eligible[key]=good
    frame=pd.read_csv(summary/'per_fit.csv');cost=frame[frame.phase=='select'].groupby('key').C.mean()
    for role,reps in [('POWER',['COMPACT','FULL_DYN']),('SCORE',['COMPACT_G','FULL_DYN_G']),('PITCH',['COMPACT_Z','FULL_DYN_Z'])]:
        k=choices['choices'][role]
        candidates=[name for name in cost.index if name.split('__')[0] in reps]
        if role=='POWER':candidates.append(cfg['reference']['key'])
        elif choices['choices']['POWER'] is not None:candidates.append(choices['choices']['POWER'])
        valid=[name for name in candidates if eligible[name]]
        if k is None:assert not valid or not choices['reference_qualified']
        else:assert eligible[k] and abs(cost[k]-cost[valid].min())<1e-10
    intervals=json.loads((summary/'intervals.json').read_text());assert len(intervals)==1860
    for span in [1,3,7]:assert len([r for r in intervals if r['span']==span])==620
    args.out.parent.mkdir(parents=True,exist_ok=True)
    if args.out.exists():raise ValueError('Preserve previous audit')
    args.out.write_text(json.dumps(dict(status='FAIR_WIDTHS_ACCOUNTING_AND_JOINT_HISTORY_RULES_RECONCILED',
        new_metric_rows=verified,historical_coordinates=528,evaluation_slots_per_span=620,
        inference_coverage_certified=False),indent=2),encoding='utf-8')
    print('AUDITED FAIR JOINT',verified,flush=True)


if __name__=='__main__':main()
