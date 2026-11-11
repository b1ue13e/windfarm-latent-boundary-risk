from repo_paths import Path, repository_root
import importlib.util

import numpy as np
import pytest

ROOT = Path(repository_root())
spec = importlib.util.spec_from_file_location("legacy_alignment", ROOT / "scripts/audit_legacy_cache_alignment.py")
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def test_future_targets_follow_anchor_plus_h_without_h_zero():
    anchors = audit.expected_anchors((0, 10), hist=3, pred=2)
    assert np.array_equal(anchors, np.arange(2, 8))
    target = np.arange(20, dtype=np.float32).reshape(10, 2)
    saved = target[anchors[:, None] + np.array([1, 2])[None, :]]
    wrong = target[anchors[:, None] + np.array([0, 1])[None, :]]
    assert not audit.exact_array(saved, wrong)["byte_identical"]


def test_node_permutation_preserves_length_and_sum_but_not_identity():
    a = np.arange(24, dtype=np.float32).reshape(4, 3, 2)
    b = a[:, :, ::-1]
    assert a.shape == b.shape and a.sum() == b.sum()
    assert audit.exact_array(a, b)["mismatched_element_bytes"] == a.size


def test_nan_payload_bytes_are_not_hidden_by_equal_nan_or_tolerance():
    a = np.array([0x7FC00001], dtype=np.uint32).view(np.float32)
    b = np.array([0x7FC00002], dtype=np.uint32).view(np.float32)
    assert np.isnan(a).all() and np.isnan(b).all()
    assert audit.exact_array(a, a.copy())["byte_identical"]
    assert not audit.exact_array(a, b)["byte_identical"]


def test_masking_a_nan_does_not_make_zero_and_support_is_checked_separately():
    m = np.array([1., 1., 0.], dtype=np.float32)
    issue = np.array([1., 0., 1.], dtype=np.float32)
    sf = np.maximum(np.array([2., 3., np.nan], dtype=np.float32), 0.) * m
    counts = audit.support_counts(m, issue, sf)
    assert counts["future_target_valid"] == 2 and counts["both_valid"] == 1
    assert counts["target_valid_issue_invalid"] == 1
    assert counts["shortfall_nonfinite"] == 1 and counts["nonfinite_inside_target_mask"] == 0


def test_matching_decision_aggregates_cannot_identify_posterior_coordinates():
    p = np.array([0.1, 0.2, 0.8, 0.9])
    swapped = p[[1, 0, 3, 2]]
    reserve = lambda x: np.where(x < 0.5, 3.0, 9.0)
    assert not audit.exact_array(p, swapped)["byte_identical"]
    assert audit.exact_array(reserve(p), reserve(swapped))["byte_identical"]


def test_exact_checker_rejects_different_dtypes_and_sub_ulp_value_changes():
    a = np.array([1.], dtype=np.float32)
    assert not audit.exact_array(a, a.astype(np.float64))["byte_identical"]
    assert not audit.exact_array(a, np.nextafter(a, np.float32(2.)))["byte_identical"]


def test_destination_guard_preserves_prior_records_and_original_assets():
    with pytest.raises(ValueError):
        audit.output_guard(ROOT / "artifacts/matched_budget")
    with pytest.raises(FileExistsError):
        audit.output_guard(ROOT / "analyses/legacy_cache_alignment_audit_20261018")
