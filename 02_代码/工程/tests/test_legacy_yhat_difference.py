import importlib.util
from repo_paths import Path, repository_root

import numpy as np
import pytest

ROOT = Path(repository_root())
spec = importlib.util.spec_from_file_location("yhat_audit", ROOT / "scripts/audit_legacy_yhat_difference.py")
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def test_complete_batch_counts_identify16_without_claiming64_is_tested():
    assert audit.possible_batch_sizes(4261, 267) == [16]
    assert audit.possible_batch_sizes(4981, 312) == [16]
    assert 64 not in audit.possible_batch_sizes(4981, 312)


def test_ulp_description_does_not_turn_one_ulp_into_exact_match():
    a = np.array([1., -1.], dtype=np.float32)
    b = np.nextafter(a, np.float32(2.))
    assert audit.ulp_summary(a, b)["histogram"]["1..1"] == 2
    assert not audit.exact_array(a, b)["byte_identical"]


def test_signed_zero_and_nonfinite_are_not_silently_accepted():
    a = np.array([0., np.inf], dtype=np.float32)
    b = np.array([-0., np.inf], dtype=np.float32)
    description = audit.ulp_summary(a, b)
    assert description["excluded_nonfinite"] == 1
    assert not audit.exact_array(a, b)["byte_identical"]


def test_static_specialization_preserves_real_changes_to_moe_path():
    old = 'class M:\n def f(self,x):\n  return x+1\n'
    added = 'class M:\n def f(self,x):\n  if self.is_dense_classifier:\n   return x*7\n  return x+1\n'
    changed = added.replace('return x+1', 'return x+2')
    assert audit.moe_source_comparison(old, added)["full_module_AST_after_recorded_mode_specialization_equal"]
    assert not audit.moe_source_comparison(old, changed)["full_module_AST_after_recorded_mode_specialization_equal"]


def test_ulp_inspection_rejects_dtype_reinterpretation():
    with pytest.raises(ValueError):
        audit.ulp_summary(np.array([1.], dtype=np.float64), np.array([1.], dtype=np.float64))
