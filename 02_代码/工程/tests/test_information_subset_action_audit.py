import importlib.util
from repo_paths import Path, repository_root
import numpy as np
from windfarm_moe.decision_information import block_totals


def test_independent_array_accounting_matches_exact_with_invalid_cells():
    p = Path(repository_root()) / "scripts/audit_information_subset_actions.py"
    spec = importlib.util.spec_from_file_location("subset_actions_test", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    rng = np.random.default_rng(1)
    s = rng.uniform(0, 500, (300, 4))
    valid = rng.random(s.shape) > .1
    s[~valid] = np.nan
    raw = rng.uniform(0, 500, s.shape)
    anchors = np.arange(30240, 30540)
    a = m.direct_totals(s, raw, -17., valid, anchors)
    b = block_totals(s, np.maximum(raw - 17., 0), valid, anchors)
    for key in a:
        np.testing.assert_array_equal(a[key], b[key])
