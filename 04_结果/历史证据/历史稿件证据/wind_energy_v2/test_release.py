"""Catch reversed comparisons, calibration substitutions and unsafe build routing."""
import copy
import json
from pathlib import Path

import pytest
from build import conversion_command
from validate_release import citation_keys, primary_display_facts, secondary_display_facts


def source():
    root = Path(__file__).resolve().parents[2]
    return json.loads((root / "analyses/independent_confirmation_execution_20261019/recovered/results/aggregate/primary.json").read_text())


def test_archived_primary_reports_positive_cost_premium():
    f = primary_display_facts(source())
    assert f == dict(premium="0.5641%", lower="0.3575%", upper="0.7708%",
                     candidate_risk="6.2025%", reference_risk="6.2004%")


@pytest.mark.parametrize("mutation", ["swap", "secondary_q", "reverse_ratio", "interval"])
def test_reporting_identity_failures_are_rejected(mutation):
    p = copy.deepcopy(source())
    if mutation == "swap":
        p["labels"].reverse()
    elif mutation == "secondary_q":
        p["labels"][0] = "P1/HGB/q0.925"
    elif mutation == "reverse_ratio":
        p["bounds"]["groups"][0]["relative_ratio_point"][0][1] *= -1
    else:
        p["bounds"]["groups"][0]["relative_ratio_upper"][0][1] = -1
    with pytest.raises(ValueError):
        primary_display_facts(p)


def test_build_is_limited_to_declared_documents():
    with pytest.raises(ValueError):
        conversion_command("../../scripts/run_independent_confirmation")
    for stem in ("manuscript", "supplementary"):
        c = conversion_command(stem)
        assert "pandoc" in c[0].lower() and c[1] == stem + ".md"
        assert "--citeproc" in c


def test_email_is_not_a_citation():
    assert citation_keys("dujuntao@aufe.edu.cn; [@paper2026; @other2024]; @narrative2022") == {
        "paper2026", "other2024", "narrative2022"}


def secondary_source():
    root = Path(__file__).resolve().parents[2]
    return json.loads((root / "analyses/independent_confirmation_execution_20261019/recovered/results/aggregate/secondary_span3.json").read_text())


def test_secondary_bridge_is_distinct_from_primary_bounds():
    assert secondary_display_facts(secondary_source()) == dict(
        q925_cost_upper="0.9742%", q950_cost_upper="3.5178%",
        q925_risk_upper="9.7699%", q950_risk_upper="6.7049%")


def test_possible_competitor_is_not_a_qualified_witness():
    data = secondary_source()
    group = next(g for g in data["results"] if g["condition"] == "pitch_withheld")
    decision = next(c for c in group["secondary_retrospective_full_q"] if c["epsilon"] == .02)
    decision["sufficient_set"]["risk_qualified_indices"].append(180)
    with pytest.raises(ValueError, match="possibly feasible but unqualified"):
        secondary_display_facts(data)
