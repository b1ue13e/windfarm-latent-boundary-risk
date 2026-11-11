from repo_paths import Path, repository_root
import importlib.util

import numpy as np
import pytest

ROOT = Path(repository_root())
spec = importlib.util.spec_from_file_location("legacy_accounting", ROOT / "scripts/audit_legacy_posterior_accounting.py")
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def test_finite_posterior_independent_baseline_can_fail_float32_identity():
    r = np.full(4096, 123.456, dtype=np.float32)
    s = np.full(4096, 456.789, dtype=np.float32)
    mask = np.ones(len(r), dtype=bool)
    assert not audit.accounting(r, s, mask, "original")["passes_original_assert"]
    fixed = audit.accounting(r, s, mask, "float64")
    assert fixed["passes_original_assert"]
    assert fixed["violations"] == len(r)


def test_upcast_is_before_subtraction_and_leaves_input_actions_untouched():
    r = np.array([0.0, 0.125, 123.456, 1499.9], dtype=np.float32)
    s = np.array([0.0, 0.125, 456.789, 1500.0], dtype=np.float32)
    before = (r.tobytes(), s.tobytes())
    mask = np.array([True, True, True, False])
    row = audit.accounting(r, s, mask, "float64")
    assert row["n"] == 3 and row["violations"] == 1
    assert row["shortage_dtype"] == "float64"
    assert audit.accounting(r, s, mask, "sum64_only")["shortage_dtype"] == "float32"
    assert (r.tobytes(), s.tobytes()) == before


def test_original_source_saves_before_failure_and_no_phase_one_csv_before_assert():
    p = ROOT / audit.LINEAGE / "evidence/run_matched_budget_frontier.py_before_step125.txt"
    result = audit.source_structure(p)
    assert result["save_before_assert_before_csv"]
    assert result["helper_has_no_calls_that_write"]
    assert result["original_assert_threshold_present"]


def test_strict_csv_check_does_not_adopt_looser_legacy_test_tolerance(tmp_path):
    p = tmp_path / "probe.csv"
    p.write_text("C,R,U\n11.001,1,1\n", encoding="utf-8")
    result = audit.strict_csv_identity(p, [("C", "R", "U")])
    assert result["failed_original_assert"] == 1
    assert result["threshold_kwh"] == 1e-4


def test_output_guard_rejects_original_results_and_existing_records(tmp_path):
    with pytest.raises(ValueError):
        audit.check_output(ROOT / "artifacts/matched_budget")
    with pytest.raises(FileExistsError):
        audit.check_output(ROOT / "analyses/legacy_generation_lineage_audit_20261018")


def test_cache_shape_and_range_errors_are_not_silently_accepted(tmp_path):
    p = tmp_path / "probe.npz"
    arrays = {f"p_{split}_seed{seed}": np.array([0.1, 0.9], dtype=np.float32)
              for split in ("val", "test") for seed in audit.SEEDS}
    arrays["p_val_seed201"] = np.array([np.nan, 1.1], dtype=np.float32)
    np.savez_compressed(p, **arrays)
    rows = audit.cache_inventory(p, {"val": 3, "test": 2})["arrays"]
    row = next(r for r in rows if r["key"] == "p_val_seed201")
    assert not row["finite"] and row["out_of_range"] == 1 and not row["shape_matches"]
