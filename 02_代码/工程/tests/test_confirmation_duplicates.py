import importlib.util
from repo_paths import Path, repository_root
import pandas as pd

path = Path(repository_root()) / "scripts/diagnose_confirmation_duplicates.py"
spec = importlib.util.spec_from_file_location("source_duplicates_test", path)
m = importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


def test_exact_and_conflicting_duplicate_groups_are_distinguished_without_deletion():
    frame = pd.DataFrame(dict(coordinate=[1, 1, 2, 2], month=[1, 2, 2, 2], power=[10., 10., 20., 21.]))
    before = frame.copy(deep=True)
    r = m.classify_duplicates(frame, ["power"])
    assert r["duplicate_groups"] == 2 and r["extra_rows"] == 2
    assert r["conflicting_groups"] == 1 and not r["all_consumed_values_numerically_identical"]
    assert r["conflicting_examples"][0]["coordinate"] == 2
    pd.testing.assert_frame_equal(frame, before)


def test_nan_identical_and_unique_sources_remain_unmodified():
    frame = pd.DataFrame(dict(coordinate=[1, 1], month=[1, 2], pitch=[float("nan"), float("nan")]))
    r = m.classify_duplicates(frame, ["pitch"])
    assert r["all_consumed_values_numerically_identical"] and r["conflicting_groups"] == 0
    assert m.classify_duplicates(frame.iloc[:1], ["pitch"])["extra_rows"] == 0
