import numpy as np
import pytest
from dataclasses import replace
from windfarm_moe.budget_sources import PopulationSpec, qualify_arrays, array_sha256
from windfarm_moe.budget_diagnostic_core import SEEDS


def synthetic():
    spec=PopulationSpec(0,288,2,576,0,2)
    a=np.arange(288);m=np.ones((288,2),bool);r=np.tile([1.,2.],(288,1))
    runs={s:dict(anchors=a.copy(),mask=m.copy(),P=r.copy(),Z=r.copy(),S=r.copy(),node_ids=(0,1)) for s in SEEDS}
    idx=np.tile([0,1],(20000,1))
    return spec,runs,idx


def qualify(spec,runs,idx):return qualify_arrays(runs,idx,spec=spec,mode='SYNTHETIC',rules_sha256='a'*64,span=3)


def test_exact_row_compression_preserves_population_and_inputs():
    spec,runs,idx=synthetic();before=array_sha256(runs[201]['P'])
    out=qualify(spec,runs,idx)
    assert sum(out.groups[201][1])==576 and len(out.groups[201][0])==4
    assert before==array_sha256(runs[201]['P'])
    assert not out.indices.flags.writeable and out.identity['mode']=='SYNTHETIC'


@pytest.mark.parametrize('change',['anchor','mask','node','target','draw','seed'])
def test_source_mismatch_fails_without_repairing_population(change):
    spec,runs,idx=synthetic()
    if change=='anchor':runs[205]['anchors'][0]=1
    if change=='mask':runs[205]['mask'][0,0]=False
    if change=='node':runs[205]['node_ids']=(1,0)
    if change=='target':runs[205]['S'][0,0]=float('nan')
    if change=='draw':idx[0,0]=2
    if change=='seed':del runs[205]
    with pytest.raises(ValueError):qualify(spec,runs,idx)


def test_synthetic_receipt_cannot_claim_original_population():
    spec,runs,idx=synthetic()
    with pytest.raises(ValueError,match='Original frozen population'):
        qualify_arrays(runs,idx,spec=spec,mode='ARCHIVED',rules_sha256='a'*64,span=3)


def test_compression_preserves_signed_zero_bit_identity():
    spec,runs,idx=synthetic()
    for run in runs.values():
        run['P'][:]=0.;run['P'][0,0]=-0.
    out=qualify(spec,runs,idx)
    table,counts=out.groups[201]
    negative=np.signbit(table[:,1])
    assert negative.sum()==1 and counts[negative].sum()==1
