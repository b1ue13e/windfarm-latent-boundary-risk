"""Policy flattening and functional identity for the secondary grid audit."""
import importlib.util
from repo_paths import Path, repository_root

import numpy as np


def test_all_grid_keeps_model_level_policy_order_and_common_seed_level():
    p = Path(repository_root()) / "scripts/analyze_risk_frontier_model_class.py"
    spec = importlib.util.spec_from_file_location("all_grid_test", p)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    a = np.arange(2 * 3 * 2 * 4 * 5).reshape(2, 3, 2, 4, 5)
    f = module.flatten_grid(a)
    assert f.shape == (2, 3, 8, 5)
    for m in range(2):
        for q in range(4):
            np.testing.assert_array_equal(f[:, :, m * 4 + q], a[:, :, m, q])
    offsets = np.zeros((2, 3, 2, 4))
    offsets[:, :, 0, 1] = 1
    offsets[1, 2, 0, 2] = 2
    exact = module.exact_ratios(offsets)
    assert exact[0, 0, 2]  # Same model and all three equal offsets.
    assert not exact[1, 0, 2]  # One instance differs: cannot use individual best levels.
    assert not exact[0, 0, 4]  # Different model: equal offsets do not prove identical functions.
    assert np.diagonal(exact, axis1=1, axis2=2).all()
