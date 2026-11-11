"""Test interpretation-sensitive mappings to immutable statistical summaries."""
import importlib.util
from pathlib import Path

import pytest

SOURCE = Path(__file__).resolve().parents[1] / "scripts/build_figures.py"
spec = importlib.util.spec_from_file_location("wind_energy_figures", SOURCE)
figures = importlib.util.module_from_spec(spec)
spec.loader.exec_module(figures)


def test_primary_uses_paired_ratio_in_correct_direction():
    rows = figures.primary_rows()
    cost = rows[0]
    assert cost["point"] == pytest.approx(.5641474815991643)
    assert cost["lower"] == pytest.approx(.35746800646510356)
    assert cost["upper"] == pytest.approx(.770826956733225)
    assert len(rows) == 11
    assert max(r["upper"] for r in rows[1:]) < 10
    assert {r["seed"] for r in rows[1:]} == set(range(201, 206))


def test_secondary_is_separate_family_and_preserves_all_smaller_candidates():
    points, excluded = figures.secondary_rows()
    assert len(points) == 15
    assert len(excluded) == 15
    assert sum(r["reason"] == "RISK_LOWER_ABOVE_CAP" for r in excluded) == 2
    assert sum(r["reason"] == "COST_LOWER_EXCEEDS_MARGIN_VS_FEASIBLE" for r in excluded) == 13
    q925 = next(r for r in points if r["label"] == "P1/HGB/q0.925")
    q950 = next(r for r in points if r["label"] == "P1/HGB/q0.95")
    assert q925["cost"] == pytest.approx(65.73923230784504)
    assert q925["max_instance_risk_upper"] == pytest.approx(9.76988760696712)
    # Full-q multiplicity yields different bounds from the primary 14-coordinate family.
    assert q950["max_instance_risk_upper"] > max(r["upper"] for r in figures.primary_rows()[1:])


def test_boundary_does_not_invent_missing_wtb_cells_or_independent_cases():
    towie, wtb = figures.boundary_rows()
    assert len(towie) == 30
    assert len(wtb) == 28
    cells = {(r["condition"], int(r["budget"])) for r in wtb}
    assert len(cells) == 14
    assert len(cells) < 6 * 4
    for condition, budget in cells:
        selected = [r for r in wtb if r["condition"] == condition and int(r["budget"]) == budget]
        assert len(selected) == 2
        assert {r["status"] for r in selected} == {"NO_CERTIFIED_SUFFICIENT_POLICY"}


def test_all_output_sources_are_read_only_existing_files():
    assert all((figures.REPO / relative).is_file() for relative in figures.SOURCES)
    assert len(set(figures.SOURCES)) == len(figures.SOURCES)


def test_creation_timestamp_is_not_labelled_review_completion():
    figure, _, rows = figures.fig1()
    try:
        assert any(r["stage"] == "package_created" for r in rows)
        assert not any(r["stage"] == "actual_freeze" for r in rows)
        assert "package created" in figure.texts[0].get_text()
    finally:
        figures.plt.close(figure)
