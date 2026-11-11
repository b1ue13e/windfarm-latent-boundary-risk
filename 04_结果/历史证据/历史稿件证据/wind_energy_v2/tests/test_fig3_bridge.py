"""Protect the full-family sufficient-set bridge and witness responsibilities."""
import importlib.util
from pathlib import Path

import pytest

SOURCE = Path(__file__).resolve().parents[1] / "scripts/build_figures.py"
spec = importlib.util.spec_from_file_location("wind_energy_v2_figure_bridge", SOURCE)
figures = importlib.util.module_from_spec(spec)
spec.loader.exec_module(figures)


def test_full_family_upper_bounds_are_stored_cost_requirements():
    secondary, primary = figures.sufficiency_bridge_rows()
    assert secondary["index"] == 41 and primary["index"] == 42
    assert secondary["worst_paired_cost_upper_percent"] == pytest.approx(.9741996453634834)
    assert primary["worst_paired_cost_upper_percent"] == pytest.approx(3.517815071811852)
    assert secondary["cost_upper_certified"] and secondary["sufficient"]
    assert not primary["cost_upper_certified"] and not primary["sufficient"]
    assert {r["cost_tolerance_percent"] for r in (secondary, primary)} == {2}
    assert {r["risk_cap_percent"] for r in (secondary, primary)} == {10}
    assert "not a proven" in primary["interpretation"]


def test_controlling_competitor_is_not_misrepresented_as_qualified():
    for row in figures.sufficiency_bridge_rows():
        assert row["controlling_competitor_index"] == 180
        assert row["controlling_competitor"] == "PQ36/HGB/q0.9"
        assert row["competitor_possibly_feasible"]
        assert not row["competitor_risk_qualified"]
        assert row["competitor_max_risk_upper_percent"] > 10


def test_risk_bounds_are_from_secondary_family_not_primary():
    secondary, primary = figures.sufficiency_bridge_rows()
    assert secondary["max_instance_risk_upper_percent"] == pytest.approx(9.76988760696712)
    assert primary["max_instance_risk_upper_percent"] == pytest.approx(6.70488602271627)
    assert primary["max_instance_risk_upper_percent"] != pytest.approx(6.202467798539352)


def test_all_exclusions_have_valid_qualified_witnesses_or_risk_lower():
    rows = figures.exclusion_bridge_rows()
    assert len(rows) == 15
    assert {r["index"] for r in rows} == set(range(10)) | set(range(220, 225))
    cost = [r for r in rows if "witness_index" in r]
    risk = [r for r in rows if "witness_index" not in r]
    assert len(cost) == 13 and len(risk) == 2
    assert {r["witness_index"] for r in cost} == {171, 181}
    assert all(r["witness_risk_qualified"] and r["witness_max_risk_upper_percent"] <= 10
               and r["ratio_lower"] > .02 for r in cost)
    assert all(all(float(value) > 10 for value in r["witness_risk_lower_percent"].split(";"))
               for r in risk)


def test_figure_has_complementary_three_panels_without_new_error_bars():
    figures.configure_style()
    figure, axes, rows = figures.fig3()
    try:
        assert len(axes) == 3
        assert len(rows) == 17
        assert all(len(axis.containers) == 0 for axis in axes)
        assert any("not proven excess" in text.get_text() for text in figure.texts)
        assert any("not risk-qualified" in text.get_text() for text in figure.texts)
    finally:
        figures.plt.close(figure)
