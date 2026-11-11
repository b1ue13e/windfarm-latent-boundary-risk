import ast
import json
import importlib.util
from repo_paths import Path, repository_root

import numpy as np
import pytest

ROOT = Path(repository_root())
SPEC = importlib.util.spec_from_file_location('c201_audit', ROOT / 'scripts/audit_e04_c201_exactness.py')
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


def test_extracts_original_c_pipeline_without_downstream_mutation():
    source = '''
def main():
    for seed in seeds:
        def get_probs(loader):
            return loader
        p_v = get_probs(val_loader)
        r_C = p_v
        r_B_val = 0
        forbidden = 1
'''
    module = audit.policy_fragment(source)
    assert [type(s).__name__ for s in module.body] == ['FunctionDef', 'Assign', 'Assign']
    assert 'forbidden' not in ast.dump(module)


def test_exact_gate_rejects_cost_drift_without_tolerance():
    ref = {'n': np.array([2.]), 'C_viol': np.array([1.]), 'C_cost': np.array([2.])}
    report = audit.compare_daily(np.zeros(2, dtype=int), np.ones(2, dtype=bool),
                                 np.array([2., 0.]), np.ones(2), np.array([1., 1.0000001]), ref)
    assert report['n_exact'] and report['violation_exact']
    assert not report['cost_exact'] and not report['accepted']


def test_bin_membership_retains_half_open_edges_and_ties():
    edges = np.array([-np.inf, .5, np.inf])
    assert audit.bin_ids(np.array([0., .5, 1.]), edges).tolist() == [0, 1, 1]


def test_extraction_fails_closed_without_source_boundary():
    with pytest.raises(ValueError, match='policy boundaries'):
        audit.policy_fragment('def main():\n    for seed in seeds:\n        r_C=0\n')


def test_complete_grid_requires_every_seed_policy_cell():
    spec=importlib.util.spec_from_file_location('c201_merge',ROOT/'scripts/reconcile_e04_c201_evidence.py')
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    closures={str(s):{p:{'n_exact':True,'violations_exact':True,'cost_exact':True}
                         for p in ('B','C','D','D10')} for s in range(201,206)}
    assert module.full_grid_closed(closures)
    closures['201']['C']['cost_exact']=False
    assert not module.full_grid_closed(closures)


def archive_fixture(tmp_path, accepted):
    spec=importlib.util.spec_from_file_location('c201_verified',ROOT/'scripts/reconcile_e04_c201_evidence.py')
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    archive=tmp_path/'repeat1_posterior_and_bins.npz'
    np.savez(archive,posterior_val=np.array([.1,.2]))
    report={'n_exact':True,'violation_exact':True,'cost_exact':accepted,'accepted':accepted,
            'archive_sha256':module.sha(archive)}
    report_path=tmp_path/'repeat1_report.json'
    report_path.write_text(json.dumps(report))
    manifest={'inputs_unchanged':True,'output_sha256':{p.name:module.sha(p) for p in [archive,report_path]}}
    (tmp_path/'manifest.json').write_text(json.dumps(manifest))
    return module,archive


def test_reconciliation_rejects_nonexact_archive(tmp_path):
    module,_=archive_fixture(tmp_path,False)
    with pytest.raises(ValueError,match='exactness gate'):
        module.verified_archive(tmp_path,1)


def test_reconciliation_rejects_changed_posterior_bytes(tmp_path):
    module,path=archive_fixture(tmp_path,True)
    assert module.verified_archive(tmp_path,1)['posterior_val'].tolist()==[.1,.2]
    path.write_bytes(b'altered')
    with pytest.raises(ValueError,match='hash mismatch'):
        module.verified_archive(tmp_path,1)
