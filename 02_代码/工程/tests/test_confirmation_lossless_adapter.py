import importlib.util
from repo_paths import Path, repository_root
import numpy as np
import pytest

path = Path(repository_root()) / "scripts/prepare_confirmation_history.py"
spec = importlib.util.spec_from_file_location("source_equal_copies_test", path)
m = importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


def test_equal_observation_copies_leave_physical_population_and_values_unchanged():
    seen, values = np.zeros(4, bool), np.full((4, 2), np.nan)
    extra = m.add_equal_copies([2, 1, 2], [[-10, np.nan], [20, 5], [-10, np.nan]], seen, values)
    assert extra == 1
    assert m.add_equal_copies([2, 3], [[-10, np.nan], [0, 0]], seen, values) == 1
    np.testing.assert_array_equal(seen, [False, True, True, True])
    np.testing.assert_array_equal(values[1:], [[20, 5], [-10, np.nan], [0, 0]])


@pytest.mark.parametrize("across", [False, True])
def test_any_consumed_conflict_rejects_before_writing_or_choosing_a_value(across):
    seen, values = np.zeros(4, bool), np.full((4, 1), np.nan)
    if across:
        m.add_equal_copies([1], [[10]], seen, values)
        index, new = [1], [[11]]
    else:
        index, new = [1, 1], [[10], [11]]
    before_seen, before_values = seen.copy(), values.copy()
    with pytest.raises(ValueError, match="Conflicting"):
        m.add_equal_copies(index, new, seen, values)
    np.testing.assert_array_equal(seen, before_seen)
    np.testing.assert_array_equal(values, before_values)
