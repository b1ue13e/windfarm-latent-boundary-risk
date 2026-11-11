import copy
import importlib.util
import json
from pathlib import Path
import pytest

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('p0_projection', HERE/'project_evidence.py')
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
ROOT=Path(r'E:\论文3')


def test_coordinate_policy_identity_and_reject_mislabelling():
    p=ROOT/'experiments/conditional_refine_20261025_v2/recovered/results/campaign/inference_span3.json'
    d=json.loads(p.read_text())
    c=m.select_coordinate(d,'E:907:U','BR009_Z','R0182_P')
    assert c['upper']<0
    with pytest.raises(ValueError,match='identity mismatch'):
        m.select_coordinate(d,'E:907:U','R0182_P','BR009_Z')


def test_projection_preserves_families_unknown_and_no_new_inference():
    d=json.loads((HERE/'outputs_v1/SUMMARY.json').read_text(encoding='utf-8'))
    assert d['new_fits']==d['new_bootstrap']==d['new_measurements']==0
    assert d['original_inputs_unchanged']
    assert all(m.sha(p)==h for p,h in d['inputs_sha256'].items())
    assert {r['family_size'] for r in d['points'] if r['policy']=='EM1_003_P'}=={88052}
    assert {r['family_size'] for r in d['BR_vs_R182_coordinates']}=={64654}
    assert all(r['qualified']=='UNKNOWN' for r in d['qualifications'] if r['policy']=='REF')
    for r in d['points']:
        assert abs(r['C']-r['R']-10*r['U'])<1e-8
    v=next(r for r in d['BR_vs_R182_coordinates'] if r['span']==3 and r['metric']=='V')
    assert v['lower']<0<v['upper']


def test_m_projection_is_exact_copy_with_separate_population():
    import csv
    rows=list(csv.DictReader((HERE/'outputs_v1/M_PRAW_VS_OZ6_ORIGINAL_COORDINATES.csv').open(encoding='utf-8-sig')))
    assert len(rows)==114
    assert all(r['population']=='M_primary_evaluation' for r in rows)
    source=list(csv.DictReader((ROOT/'analyses/praw_supplement_v3_execution_20261021/all_endpoints.csv').open(encoding='utf-8-sig')))
    source={r['coordinate_id']:r for r in source}
    for r in rows:
        assert all(r[k]==source[r['coordinate_id']][k] for k in ('point','lower','upper','interval_status','source_file'))
    for estimator in ('HGB','MLP'):
        c=next(r for r in rows if r['span']=='3' and r['estimator']==estimator and r['comparison']=='Praw-minus-OZ6' and r['metric']=='D_C')
        assert float(c['upper'])<0
        h=[r for r in rows if r['span']=='3' and r['estimator']==estimator and r['comparison']=='Praw-minus-OZ6' and r['metric']=='H_U']
        assert len(h)==5 and any(float(x['upper'])>0 for x in h)
