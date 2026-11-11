from fractions import Fraction as F
import numpy as np
from windfarm_moe.budget_sources import PopulationSpec,qualify_arrays
from windfarm_moe.budget_runtime import evaluate_frozen_source,ResourceAdmissionError
import pytest
from windfarm_moe.budget_diagnostic_core import SEEDS, map_pair,score_pair,combine_fits


def test_end_to_end_grouped_draws_match_ungrouped_exact_scores():
    spec=PopulationSpec(0,288,2,576,0,2)
    anchors=np.arange(288);mask=np.ones((288,2),bool)
    p=np.tile([0.,2.],(288,1));z=np.tile([1.,1.],(288,1));target=np.tile([.5,0.],(288,1))
    runs={s:dict(anchors=anchors,mask=mask,P=p,Z=z,S=target,node_ids=(0,1)) for s in SEEDS}
    indices=np.tile(np.array([[0,0],[1,1],[0,1]]),(6667,1))[:20000]
    source=qualify_arrays(runs,indices,spec=spec,mode='SYNTHETIC',rules_sha256='a'*64,span=3)
    result=evaluate_frozen_source(source)
    assert result.metadata['n_draws']==20000 and len(result.trace['draw_to_config'])==20000
    for config in result.trace['configurations']:
        days=np.repeat(anchors//144,2)
        weights=np.array(config['day_counts'])[days]
        for anchor in ('P','Z'):
            for method in ('M','S'):
                setting=map_pair(p.ravel(),z.ravel(),anchor,method,weights)
                expected=combine_fits({seed:score_pair(target.ravel(),setting.P,setting.Z) for seed in SEEDS})
                receipt=config['settings']['A'+anchor+'_'+method]['combined']
                assert receipt['ideal_U']==expected.ideal_U and receipt['ideal_V']==expected.ideal_V
                assert receipt['U']==expected.U and receipt['V']==expected.V
    assert result.metadata['critical_value'] is None  # Constant nonexact endpoints.
    vector=evaluate_frozen_source(source,backend='vector_exact')
    assert [(r.point,r.lower,r.upper,r.point_status,r.interval_status) for r in result.rows]==\
           [(r.point,r.lower,r.upper,r.point_status,r.interval_status) for r in vector.rows]
    assert vector.metadata['vector_backend_sha256']
    with pytest.raises(ResourceAdmissionError) as error:
        evaluate_frozen_source(source,max_exact_group_visits=1)
    assert error.value.plan['exact_group_visits_upper']>1
