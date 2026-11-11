import importlib.util
from repo_paths import Path, repository_root
import numpy as np

path = Path(repository_root()) / "scripts/audit_subset_minimum_necessity.py"
spec = importlib.util.spec_from_file_location("minimum_necessity_test", path)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def test_sufficient_larger_policy_does_not_rule_out_smaller_unknown():
    result = m.diagnose([[.01, .01]], [[.12, .08]], [[0, -.01], [-.02, 0]], [[0, 1, 4], [1, 1, 5]], [1], .02)
    assert result["status"] == "MINIMUM_UNRESOLVED" and result["unresolved"] == [0]


def test_risk_lower_or_paired_cost_lower_can_exclude_all_smaller():
    result = m.diagnose([[.11, .01, .01]], [[.15, .08, .07]],
                        [[0, 0, 0], [0, 0, .03], [0, -.05, 0]],
                        [[0, 1, 4], [1, 1, 5], [2, 1, 6]], [2], .02)
    assert result["status"] == "FINITE_FAMILY_MINIMUM_IDENTIFIED"
    assert [x["reason"] for x in result["excluded"]] == ["RISK_LOWER_ABOVE_CAP", "COST_LOWER_EXCEEDS_MARGIN_VS_FEASIBLE"]


def test_unqualified_witness_and_equality_at_zero_do_not_exclude():
    result = m.diagnose([[.01, .01, .01]], [[.09, .12, .08]],
                        [[0, .5, 0], [0, 0, 0], [0, 0, 0]],
                        [[0, 1, 4], [1, 1, 5], [2, 1, 6]], [2], 0)
    assert result["status"] == "MINIMUM_UNRESOLVED"
    assert 0 in result["unresolved"]


def test_no_certified_policy_and_algebraic_ties_remain_honest():
    lo, hi = [[.01, .01]], [[.08, .09]]
    assert m.diagnose(lo, hi, [[0, 0], [0, 0]], [[0, 1, 4], [0, 1, 4]], [], .02)["status"] == "NO_CERTIFIED_SUFFICIENT_POLICY"
    r = m.diagnose(lo, hi, [[0, None], [None, 0]], [[0, 1, 4], [0, 1, 4]], [0, 1], .02)
    assert r["chosen"] == [0, 1] and r["status"] == "FINITE_FAMILY_MINIMUM_IDENTIFIED"
