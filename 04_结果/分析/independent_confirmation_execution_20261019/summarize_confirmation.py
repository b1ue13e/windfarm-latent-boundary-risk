"""Read frozen output only; no fitting, selection changes or resampling."""
from pathlib import Path
from datetime import datetime, timezone
import collections
import csv
import hashlib
import json
import platform
import sys

BASE=Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    source=BASE/'recovered/results/aggregate'
    inputs=[source/'primary.json']+[source/f'secondary_span{s}.json' for s in (3,1,7)]
    identities={str(p.relative_to(BASE)):sha(p) for p in inputs}
    out=BASE/'derived';out.mkdir(exist_ok=False)
    primary=json.loads(inputs[0].read_text());env=primary['bounds']['groups'][0]
    assert primary['labels']==['P1/HGB/q0.95','WPQ36/HGB/q0.95']
    rows=[];span3=[]
    for path in inputs[1:]:
        for group in json.loads(path.read_text())['results']:
            for item in group['secondary_retrospective_full_q']:
                audit=item['minimum_audit'];fixed=group['historical_frozen_assessment'][str(item['epsilon'])]
                row=dict(span=group['span'],condition=group['condition'],epsilon=item['epsilon'],
                    sufficient_set=';'.join(group['labels'][i] for i in item['sufficient_set']['minimum_resource_indices']),
                    minimum_status=audit['status'],smaller_count=len(audit['smaller']),excluded_count=len(audit['excluded']),
                    unresolved_count=len(audit['unresolved']),historical_fixed_status=fixed['status'])
                rows.append(row)
                if row['span']==3 and row['epsilon'] in (.02,.05):span3.append(row)
    for name,records in [('secondary_cases.csv',rows),('primary_span_secondary.csv',span3)]:
        with (out/name).open('x',encoding='utf-8',newline='') as fp:
            writer=csv.DictWriter(fp,fieldnames=list(records[0]));writer.writeheader();writer.writerows(records)
    selected=json.loads(inputs[1].read_text())['results'][0]
    assert selected['condition']=='pitch_withheld'
    minimum=next(x for x in selected['secondary_retrospective_full_q'] if x['epsilon']==.02)
    chosen=minimum['sufficient_set']['minimum_resource_indices']
    assert [selected['labels'][i] for i in chosen]==['P1/HGB/q0.925']
    summary=dict(primary_status=primary['verdict']['status'],labels=primary['labels'],mean_cost=env['mean_cost'],
       candidate_max_instance_risk_upper=max(x[0] for x in env['risk_upper']),
       reference_max_instance_risk_upper=max(x[1] for x in env['risk_upper']),
       relative_cost_point=env['relative_ratio_point'][0][1],relative_cost_interval=[env['relative_ratio_lower'][0][1],env['relative_ratio_upper'][0][1]],
       primary_coordinate_family=primary['bounds']['coordinate_family_size'],
       secondary_case_counts=dict(collections.Counter(r['minimum_status'] for r in rows)),
       historical_fixed_case_counts=dict(collections.Counter(r['historical_fixed_status'] for r in rows)),
       withheld_secondary_two_percent=dict(label=selected['labels'][chosen[0]],
           cost=selected['mean_cost'][chosen[0]],risk_upper=max(x[chosen[0]] for x in selected['risk_upper']),
           resource=selected['resources'][chosen[0]],minimum_status=minimum['minimum_audit']['status'],
           smaller_count=len(minimum['minimum_audit']['smaller']),excluded_count=len(minimum['minimum_audit']['excluded']),
           exclusion_reasons=dict(collections.Counter(x['reason'] for x in minimum['minimum_audit']['excluded']))),
       failures=[r for r in rows if r['historical_fixed_status']=='CONFIRMATION_NOT_ESTABLISHED'],
       scope='Primary fixed-reference mean-cost noninferiority, not cost superiority or full-q minimality. Secondary q.925 finite-family resource minimum is retrospective, not a selected confirmatory policy. All90 cases share data.')
    for p in inputs:
        assert sha(p)==identities[str(p.relative_to(BASE))]
    (out/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    (out/'receipt.json').write_text(json.dumps(dict(utc=datetime.now(timezone.utc).isoformat(),
        inputs_sha256=identities,source_sha256=sha(Path(__file__)),argv=sys.argv,python=sys.version,
        host=platform.node(),new_fit=False,new_bootstrap=False),indent=2),encoding='utf-8')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    main()
