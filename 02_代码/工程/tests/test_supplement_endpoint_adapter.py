"""Small deterministic fixtures for V3 endpoint support; no research data."""
import json

import numpy as np
import pytest

from windfarm_moe.risk_frontier import simultaneous_envelope
from windfarm_moe.supplement_endpoint_adapter import (
    EndpointCoordinate, adapt_endpoint_family, observed_deficit_annotations, pooled_mean,
)


def coordinate(cid, point=2., draws=None, *, population=5., draw_population=None,
               domain="SIGNED_REAL", reference=1., draw_reference=None, failure=None):
    draws = np.array([1., 2., 3., 2.]) if draws is None else np.asarray(draws, float)
    if draw_population is None:
        draw_population = np.full(len(draws), population)
    return EndpointCoordinate(cid, point, draws, population, draw_population, domain,
                              reference, draw_reference, failure)


def family(*coords):
    return adapt_endpoint_family(coords, family_id="E_G", span=3,
                                 draw_ids=["draw-0", "draw-1", "draw-2", "draw-3"])


def test_t06_both_u_zero_does_not_cancel_procurement_cost_or_gap():
    annotation = observed_deficit_annotations([0., 0.], [0., 0.], 2)
    assert annotation == ["OBSERVED_BOTH_U_ZERO"]
    result = family(coordinate("U", 0, np.zeros(4)),
                    coordinate("V", 0, np.zeros(4), domain="RISK_0_1"),
                    coordinate("R"), coordinate("C"),
                    coordinate("gap", domain="NONNEGATIVE"))
    rows = {r["coordinate_id"]: r for r in result["coordinates"]}
    assert result["finite_coordinate_ids"] == ["R", "C", "gap"]
    assert rows["V"]["interval_status"] == "UNINFORMATIVE_DOMAIN"
    assert (rows["V"]["lower"], rows["V"]["upper"]) == (0., 1.)
    assert rows["U"]["point"] == 0. and rows["U"]["exact"] is False
    assert all(rows[cid]["interval_status"] == "ESTIMATED_APPROX" for cid in ["R", "C", "gap"])


def test_t07_one_zero_arm_does_not_cancel_variable_paired_shortfall_contrast():
    result = family(coordinate("V_a", 0, np.zeros(4), domain="RISK_0_1"),
                    coordinate("delta_U", -.3, [-.1, -.4, -.5, -.2]))
    assert result["coordinates"][0]["upper"] == 1.
    assert result["coordinates"][1]["interval_status"] == "ESTIMATED_APPROX"
    assert observed_deficit_annotations([0, 0], [0, 1], 2) == []


def test_t08_observed_zero_population_is_missing_not_zero_and_only_local():
    result = family(coordinate("empty", 0., np.zeros(4), population=0.), coordinate("sibling"))
    empty, sibling = result["coordinates"]
    assert empty["point"] is None and empty["point_status"] == "UNDEFINED_POPULATION"
    assert empty["reason"] == "OBSERVED_POPULATION_ZERO"
    assert sibling["interval_status"] == "ESTIMATED_APPROX"
    assert observed_deficit_annotations([], [], 0) == []


def test_t08_reference_zero_only_cancels_relative_cost_not_absolute_endpoints():
    result = family(coordinate("relative_C", None, [np.nan] * 4, reference=0.),
                    coordinate("absolute_R"), coordinate("absolute_U"), coordinate("absolute_V"))
    relative = result["coordinates"][0]
    assert relative["point"] is None
    assert relative["point_status"] == "UNDEFINED_REFERENCE_DENOMINATOR"
    assert result["finite_coordinate_ids"] == ["absolute_R", "absolute_U", "absolute_V"]


@pytest.mark.parametrize("denominator_kind", ["population", "reference"])
def test_t09_one_unsupported_draw_keeps_point_every_row_and_siblings(denominator_kind):
    args = {"draw_population": [5, 0, 5, 5]} if denominator_kind == "population" else {
        "draw_reference": [1, 0, 1, 1]}
    unsupported = coordinate("unsupported", **args)
    before = unsupported.draws.copy()
    result = family(unsupported, coordinate("sibling"))
    row = result["coordinates"][0]
    assert row["point"] == 2. and row["point_status"] == "DEFINED"
    assert row["interval_status"] == "UNINFORMATIVE_DOMAIN"
    assert row["draw_denominator_valid"] == [True, False, True, True]
    assert row["draw_values"] == [1., 2., 3., 2.]
    assert result["draw_count"] == 4 and result["draw_rows_deleted"] == 0
    assert result["draw_ids"] == ["draw-0", "draw-1", "draw-2", "draw-3"]
    assert result["finite_coordinate_ids"] == ["sibling"]
    np.testing.assert_array_equal(unsupported.draws, before)


def test_t10_no_estimable_columns_have_no_critical_and_sibling_family_continues(monkeypatch):
    import windfarm_moe.supplement_endpoint_adapter as adapter
    real = adapter.simultaneous_envelope
    calls = []
    def wrapped(*args, **kwargs):
        calls.append(args)
        return real(*args, **kwargs)
    monkeypatch.setattr(adapter, "simultaneous_envelope", wrapped)
    unavailable = family(coordinate("zero_V", 0., np.zeros(4), domain="RISK_0_1"),
                         coordinate("empty", None, np.zeros(4), population=0))
    assert unavailable["status"] == "NO_ESTIMABLE_INTERVALS"
    assert unavailable["critical"] is None and unavailable["critical_source"] is None
    assert unavailable["planned_coordinate_ids"] == ["zero_V", "empty"]
    assert not calls
    available = family(coordinate("other_family_coordinate"))
    assert available["status"] == "ESTIMATED_APPROX" and len(calls) == 1


def test_t11_empirical_constants_never_become_exact_and_domains_are_json_safe():
    result = family(coordinate("signed_zero", 0., np.zeros(4)),
                    coordinate("zero_risk", 0., np.zeros(4), domain="RISK_0_1"),
                    coordinate("zero_gap", 0., np.zeros(4), domain="NONNEGATIVE"))
    rows = result["coordinates"]
    assert all(r["exact"] is False for r in rows)
    assert [(r["lower"], r["upper"]) for r in rows] == [(None, None), (0., 1.), (0., None)]
    assert all(r["reason"] == "EMPIRICAL_ZERO_VARIANCE" for r in rows)
    assert all(r["interval_status"] == "UNINFORMATIVE_DOMAIN" for r in rows)
    json.dumps(result, allow_nan=False)


def test_t12_partial_family_preserves_ids_and_matches_old_envelope_all_draw_rows(monkeypatch):
    import windfarm_moe.supplement_endpoint_adapter as adapter
    records = []
    real = adapter.simultaneous_envelope
    def wrapped(point, draws, alpha, exact):
        records.append((point.copy(), draws.copy(), alpha, exact.copy()))
        return real(point, draws, alpha, exact)
    monkeypatch.setattr(adapter, "simultaneous_envelope", wrapped)
    result = family(coordinate("nonfinite_draw", draws=[1, np.nan, 2, 3]),
                    coordinate("positive"), coordinate("negative", -2, [-1, -2, -3, -2]),
                    coordinate("constant", 9., [9.] * 4))
    assert result["planned_coordinate_ids"] == ["nonfinite_draw", "positive", "negative", "constant"]
    assert result["finite_coordinate_ids"] == ["positive", "negative"]
    assert len(result["coordinates"]) == 4
    assert records[0][1].shape == (4, 2) and records[0][2] == .05
    np.testing.assert_array_equal(records[0][3], [False, False])
    expected = simultaneous_envelope(np.array([2., -2.]),
                                     np.array([[1., -1.], [2., -2.], [3., -3.], [2., -2.]]), .05)
    assert result["critical"] == expected["critical"]
    for j, row in enumerate(result["coordinates"][1:3]):
        assert row["lower"] == expected["lower"][j]
        assert row["upper"] == expected["upper"][j]
    assert result["coordinates"][0]["draw_values"] == [1., None, 2., 3.]
    json.dumps(result, allow_nan=False)


def test_t13_computational_failure_is_not_zero_population_or_risk_failure():
    result = family(coordinate("failed_fit", None, [np.nan] * 4, population=0,
                               failure="FIT_FAILED"), coordinate("completed_fit"))
    failed = result["coordinates"][0]
    assert failed["point"] is None and failed["point_status"] == "UNAVAILABLE_COMPUTATION"
    assert failed["interval_status"] == "NOT_AVAILABLE_COMPUTATION"
    assert failed["reason"] == "COMPUTATION_FAILURE:FIT_FAILED"
    assert result["finite_coordinate_ids"] == ["completed_fit"]


def test_endpoint_order_prioritizes_population_then_formula_and_point():
    result = family(coordinate("empty", None, [np.nan] * 4, population=0, reference=0))
    assert result["coordinates"][0]["point_status"] == "UNDEFINED_POPULATION"


def test_population_status_precedes_nonfinite_secondary_formula_denominator():
    result = family(coordinate("empty", None, [np.nan] * 4, population=0, reference=np.nan))
    assert result["coordinates"][0]["point_status"] == "UNDEFINED_POPULATION"


def test_observed_zero_does_not_accept_empty_array_as_fully_covered():
    with pytest.raises(ValueError, match="positive population"):
        observed_deficit_annotations([], [], 1)


def test_vector_population_dependencies_support_stratum_interactions():
    coord = EndpointCoordinate("interaction", 2., [1, 2, 3, 2], [5, 8],
                               [[5, 8], [0, 8], [5, 8], [5, 8]])
    row = family(coord)["coordinates"][0]
    assert row["point"] == 2. and row["draw_denominator_valid"] == [True, False, True, True]
    assert row["interval_status"] == "UNINFORMATIVE_DOMAIN"


def test_unequal_day_counts_pool_totals_not_day_means_and_keep_empty_calendar_day():
    # Unweighted daily means would give 6, while the valid-interval mean is 3.
    estimate = pooled_mean([2., 10., 0.], [1., 3., 0.],
                           np.array([[1., 1., 1.], [0., 0., 3.], [3., 0., 0.], [0., 3., 0.]]))
    assert estimate.point == 3. and estimate.population_denominator == 4.
    np.testing.assert_array_equal(estimate.draw_population_denominators, [4, 0, 3, 9])
    assert np.isnan(estimate.draws[1]) and len(estimate.draws) == 4
    row = family(EndpointCoordinate("pooled", estimate.point, estimate.draws,
                                    estimate.population_denominator,
                                    estimate.draw_population_denominators))["coordinates"][0]
    assert row["point"] == 3. and row["interval_status"] == "UNINFORMATIVE_DOMAIN"


def test_pooled_empty_population_never_returns_a_zero_mean():
    estimate = pooled_mean([0., 0.], [0., 0.], np.ones((4, 2)))
    assert estimate.point is None and np.isnan(estimate.draws).all()


def test_invalid_zero_count_daily_total_is_not_silently_discarded():
    with pytest.raises(ValueError, match="nonzero empty-day total"):
        pooled_mean([1., 0.], [0., 1.], np.ones((4, 2)))


def test_empty_nominal_family_retains_given_draw_identity_without_legacy_call():
    result = adapt_endpoint_family([], family_id="empty", span=3, draw_ids=["a", "b", "c", "d"])
    assert result["critical"] is None and result["status"] == "NO_ESTIMABLE_INTERVALS"
    assert result["draw_count"] == 4 and result["draw_ids"] == ["a", "b", "c", "d"]


@pytest.mark.parametrize("bad", ["domain", "ids", "rows", "span", "alpha"])
def test_invalid_contract_inputs_rejected(bad):
    coords = [coordinate("x")]
    args = {"family_id": "E_G", "span": 3, "alpha": .05}
    if bad == "domain":
        coords = [coordinate("x", domain="not-a-domain")]
    elif bad == "ids":
        coords *= 2
    elif bad == "rows":
        coords += [coordinate("y", draws=[1, 2, 3])]
    elif bad == "span":
        args["span"] = 5
    else:
        args["alpha"] = 0
    with pytest.raises(ValueError):
        adapt_endpoint_family(coords, **args)
