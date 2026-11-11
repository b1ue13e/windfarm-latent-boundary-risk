import importlib.util
from repo_paths import Path, repository_root

import numpy as np

PATH = Path(__file__).parents[1] / "experiments/state_calibration_controls_20261020/analyze_additional_purchase.py"
SPEC = importlib.util.spec_from_file_location("purchase_bound", PATH)
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


def test_algebraic_bound_for_every_constant_positive_shift_and_single_dt():
    s = np.array([0., .01, .1, 1., 50., 300.])
    r = np.array([0., 0., 0., 1., 20., 100.])
    for d in (0., .001, .2, 1., 10., 100.):
        delta_R = np.array([d / 6])
        feasible, bound = module.uniform_extra_bound(delta_R, np.array([np.mean(s > r)]))
        actual = np.mean(np.maximum(s - r, 0) - np.maximum(s - r - d, 0)) / 6
        assert feasible[0] and actual <= bound[0] + 1e-12
    feasible, bound = module.uniform_extra_bound(np.array([-1.]), np.array([.1]))
    assert not feasible[0] and np.isnan(bound[0])
