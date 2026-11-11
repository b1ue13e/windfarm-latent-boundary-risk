"""Small invented fixture tests formatting only; never empirical evidence."""
import importlib.util
from repo_paths import Path, repository_root


def test_report_preserves_unqualified_choices_and_both_analysis_layers():
    path = Path(repository_root()) / "scripts/report_information_subset_study.py"
    spec = importlib.util.spec_from_file_location("subset_report_test", path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    choice = dict(index=0, qualified=False, label="P1/HGB/n10/q0.99")
    frontier = dict(epsilon=.02, status="NO_IDENTIFIED_POLICY", minimum_resource_indices=[])
    g = dict(span=3, condition="pitch_withheld", budget=10, historical_choices=[choice],
             labels=[choice["label"]], risk_point=[[.12], [.13]], risk_lower=[[.09], [.10]], risk_upper=[[.15], [.16]],
             mean_cost=[10], mean_cost_ci_low=[9], mean_cost_ci_high=[11],
             primary_historical_recipe=[frontier], secondary_retrospective_grid=[frontier])
    rows, frontiers = m.rows_from_result(dict(results=[g]))
    assert rows[0]["historical_selected"] and not rows[0]["historical_qualified"]
    assert rows[0]["max_instance_risk"] == .13
    assert len(frontiers) == 2 and all(r["status"] == "NO_IDENTIFIED_POLICY" for r in frontiers)
