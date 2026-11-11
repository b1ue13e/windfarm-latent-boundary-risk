"""Synthetic daily-ledger tests; no measurement, model or remote access."""
from repo_paths import Path, repository_root
import csv
import json

import numpy as np
import pytest

from windfarm_moe.supplement_inference import (
    DailyReader, _assemble, _coordinate, _read_coordinates, assemble_inference,
)
from windfarm_moe.supplement_endpoint_adapter import adapt_endpoint_family


ROOT = Path(repository_root())
COORDINATES = ROOT / "research_audit/minimum_supplement_plan_v3_20261021/COMPARISON_COORDINATES.csv"
RULES = ROOT / "research_audit/minimum_supplement_plan_v3_20261021/RULES.json"


def fixture_ledgers(tmp_path):
    base = tmp_path / "results"
    days = np.arange(8)
    n = np.array([1., 2., 3., 1., 4., 2., 1., 3.])
    ledgers = []
    for worker in range(10):
        est, seed = ("HGB" if worker < 5 else "MLP"), 201 + worker % 5
        row = dict(identity_id=f"Praw_{est}_{seed}", estimator=est, seed=seed,
                   compute_status="EVALUATION_COMPLETED", history_compute_status="EVALUATION_COMPLETED")
        ledgers.append(row)
        old, fit = base / "accounting" / str(worker), base / "fits" / str(worker)
        old.mkdir(parents=True)
        fit.mkdir(parents=True)
        arrays = {}
        for arm_id, arm in enumerate(("O6", "OP6", "OZ6", "F", "FZ", "OPZ6")):
            r = n * (2. + days * .2 + arm_id * .1 + worker * .01)
            u = n * (.2 + (days % 3) * .01 + arm_id * .02)
            v = (days % 2).astype(float)
            block = dict(C=r + 10 * u, R=r, U=u, V=v, N=n, days=days)
            for family in ("H_P", "E_P"):
                arrays.update({f"{family}|{arm}|{key}": value for key, value in block.items()})
            if arm in ("F", "FZ", "OP6", "OPZ6"):
                for axis, groups in (("wind_proxy", ("below_10p5", "at_or_above_10p5", "missing")),
                                     ("past60_ramp", ("down_gt150", "up_gt150", "within150", "unknown_endpoint"))):
                    for group_id, group in enumerate(groups):
                        # Distinct stratum denominators exercise interaction dependencies.
                        bn = n + group_id
                        bb = {key: value.copy() for key, value in block.items()}
                        bb["N"] = bn
                        bb["C"] = bn * (3 + days * .3 + arm_id * .1 * (group_id + 1))
                        arrays.update({f"E_R|{arm}|{axis}|{group}|{key}": value for key, value in bb.items()})
            if arm in ("OP6", "OPZ6"):
                gb = {key: value.copy() for key, value in block.items()}
                gb["U"] = np.zeros(8)
                gb["V"] = np.zeros(8)
                gb["C"] = r.copy()
                gb["gap_U"] = n * (1. + .03 * days + arm_id * .01)
                arrays.update({f"E_G|{arm}|{key}": value for key, value in gb.items()})
        np.savez_compressed(old / "daily_totals.npz", **arrays)
        raw = dict(C=n * (4. + days * .2 + worker * .01), R=n * (3. + days * .1),
                   U=n * (.1 + days * .01), V=(days % 3 == 0).astype(float), N=n, days=days)
        for phase in ("selection", "evaluation"):
            np.savez_compressed(fit / f"{phase}_blocks.npz", **raw)
    return base, ledgers, days, n


def make_reader(base, ledgers, days, weights=None):
    if weights is None:
        weights = np.vstack((np.eye(8), np.ones((2, 8))))
    return DailyReader(base, ledgers, {"H_P": days, "evaluation": days},
                       {"H_P": weights, "evaluation": weights})


def find_row(family, metric, *, comparison="", arm="", seed="", group=""):
    return next(r for r in _read_coordinates(COORDINATES)
                if r["family"] == family and r["metric"] == metric and r["block_span"] == "3"
                and r["estimator"] == "HGB" and r["comparison"] == comparison
                and r["arm"] == arm and r["fit_seed"] == seed and r["group"] == group)


def test_pooling_uses_totals_and_complete_five_fits(tmp_path):
    base, ledgers, days, n = fixture_ledgers(tmp_path)
    reader = make_reader(base, ledgers, days)
    pooled = reader.get("E_P", "HGB", None, "Praw", "C")
    expected = np.mean([np.sum(n * (4. + days * .2 + worker * .01)) / n.sum() for worker in range(5)])
    assert pooled.point == pytest.approx(expected)
    assert pooled.point != pytest.approx(np.mean(4. + days * .2 + .02))
    ledgers[0]["compute_status"] = "COMPUTATION_FAILED"
    failed = make_reader(base, ledgers, days).get("E_P", "HGB", None, "Praw", "C")
    assert failed.point is None and failed.failure
    # Evaluation failure does not cancel an available valid historical phase.
    assert make_reader(base, ledgers, days).get("H_P", "HGB", 201, "Praw", "C").point is not None


def test_history_phase_failure_does_not_filter_evaluation(tmp_path):
    base, ledgers, days, _ = fixture_ledgers(tmp_path)
    ledgers[0]["history_compute_status"] = "COMPUTATION_FAILED"
    (base / "fits/0/selection_blocks.npz").unlink()
    reader = make_reader(base, ledgers, days)
    assert reader.get("H_P", "HGB", 201, "Praw", "V").failure
    assert reader.get("E_P", "HGB", 201, "Praw", "V").point is not None


def test_relative_cost_zero_does_not_remove_absolute_endpoints(tmp_path):
    base, ledgers, days, _ = fixture_ledgers(tmp_path)
    for worker in range(5):
        path = base / "accounting" / str(worker) / "daily_totals.npz"
        with np.load(path) as archive:
            data = {key: archive[key] for key in archive.files}
        data["E_P|OP6|C"] = np.zeros(8)
        np.savez_compressed(path, **data)
    reader = make_reader(base, ledgers, days)
    rel = _coordinate(find_row("E_P", "D_C", comparison="Praw-minus-OP6"), reader, 40.)
    absolute = _coordinate(find_row("E_P", "delta_R", comparison="Praw-minus-OP6"), reader, 40.)
    result = adapt_endpoint_family([rel, absolute], family_id="E_P", span=3)
    assert result["coordinates"][0]["point_status"] == "UNDEFINED_REFERENCE_DENOMINATOR"
    assert result["coordinates"][1]["interval_status"] == "ESTIMATED_APPROX"


def test_group_zero_deficit_keeps_cost_gap_and_risk_uncertainty(tmp_path):
    base, ledgers, days, _ = fixture_ledgers(tmp_path)
    reader = make_reader(base, ledgers, days)
    rows = [find_row("E_G", "delta_C", comparison="OPZ6-minus-OP6"),
            find_row("E_G", "gap_U", arm="OP6"),
            find_row("E_G", "absolute_V_G", arm="OP6", seed="201")]
    result = adapt_endpoint_family([_coordinate(r, reader, 40.) for r in rows], family_id="E_G", span=3)
    assert result["coordinates"][0]["point_status"] == "DEFINED"
    assert result["coordinates"][1]["interval_status"] == "ESTIMATED_APPROX"
    assert result["coordinates"][2]["interval_status"] == "UNINFORMATIVE_DOMAIN"
    assert result["coordinates"][2]["lower"] == 0 and result["coordinates"][2]["upper"] == 1
    assert all(c["observation_annotations"] == ["OBSERVED_BOTH_U_ZERO"] for c in result["coordinates"])


def test_empty_group_is_local_and_draw_zero_retains_every_row(tmp_path):
    base, ledgers, days, _ = fixture_ledgers(tmp_path)
    for worker in range(5):
        path = base / "accounting" / str(worker) / "daily_totals.npz"
        with np.load(path) as archive:
            arrays = {key: archive[key] for key in archive.files}
        for arm in ("OP6", "OPZ6"):
            for field in ("C", "R", "U", "V", "gap_U", "N"):
                arrays[f"E_G|{arm}|{field}"] = np.zeros(8)
        # A fixed stratum has one observed nonempty day. The identity draw
        # schedule intentionally includes seven zero-denominator rows.
        for arm in ("OP6", "OPZ6"):
            for field in ("C", "R", "U", "V", "N"):
                arrays[f"E_R|{arm}|wind_proxy|missing|{field}"] = np.array([1., 0, 0, 0, 0, 0, 0, 0])
        np.savez_compressed(path, **arrays)
    reader = make_reader(base, ledgers, days)
    rows = [find_row("E_G", "gap_U", arm="OP6"),
            find_row("E_R", "delta_C", comparison="OPZ6-minus-OP6", group="missing")]
    group = adapt_endpoint_family([_coordinate(rows[0], reader, 40.)], family_id="E_G", span=3)
    stratum = adapt_endpoint_family([_coordinate(rows[1], reader, 40.)], family_id="E_R", span=3)
    assert group["coordinates"][0]["point_status"] == "UNDEFINED_POPULATION"
    assert not group["coordinates"][0]["observation_annotations"]
    assert group["status"] == "NO_ESTIMABLE_INTERVALS" and group["critical"] is None
    endpoint = stratum["coordinates"][0]
    assert endpoint["point_status"] == "DEFINED" and endpoint["point"] == 0
    assert endpoint["reason"] == "DRAW_DENOMINATOR_UNSUPPORTED"
    assert endpoint["draw_count"] == 10 and len(endpoint["draw_values"]) == 10
    assert not endpoint["all_draw_denominators_valid"]
    # Zero group support does not cancel a distinct ordinary E_P endpoint.
    assert reader.get("E_P", "HGB", 201, "OP6", "C").point is not None


def test_interaction_is_direct_high_minus_low_and_keeps_draw_dependencies(tmp_path):
    base, ledgers, days, _ = fixture_ledgers(tmp_path)
    reader = make_reader(base, ledgers, days)
    row = find_row("E_R", "interaction_C", comparison="OPZ6-minus-OP6", group="high_increment-minus-low_increment")
    coordinate = _coordinate(row, reader, 40.)
    expected = sum(coef * reader.get("E_R", "HGB", None, arm, "C", "wind_proxy", group).point
                   for coef, arm, group in [(1, "OPZ6", "at_or_above_10p5"),
                                            (-1, "OP6", "at_or_above_10p5"),
                                            (-1, "OPZ6", "below_10p5"), (1, "OP6", "below_10p5")])
    assert coordinate.point == pytest.approx(expected)
    assert len(coordinate.population_denominator) == 2
    assert coordinate.draw_population_denominators.shape == (10, 2)


def test_full_ledger_outputs_sealed_before_labels_without_real_data(tmp_path):
    base, ledgers, _, _ = fixture_ledgers(tmp_path)
    output = tmp_path / "inference"
    output.mkdir()
    rules = json.loads(RULES.read_text())
    _assemble(base, output, COORDINATES, rules, ledgers, n_boot=32, strict_calendar=False)
    index = json.loads((output / "families.json").read_text())
    assert len(index["family_artifacts"]) == 12 and index["planned_coordinates"] == 882
    count = 0
    eval_hashes = {}
    for link in index["family_artifacts"]:
        family = json.loads((output / link).read_text())
        count += len(family["coordinates"])
        assert family["draw_count"] == 32 and family["draw_rows_deleted"] == 0
        with np.load(output / family["draw_artifact"]["path"], allow_pickle=False) as archive:
            assert archive["draw_values"].shape == (32, len(family["coordinates"]))
            assert archive["day_weights"].shape == (32, 8)
        if family["family_id"] != "H_P":
            eval_hashes.setdefault(family["span"], set()).add(family["shared_draw_schedule_sha256"])
    assert count == 882 and all(len(values) == 1 for values in eval_hashes.values())
    seal = json.loads((output / "inference_seal.json").read_text())
    labels = json.loads((output / "labels.json").read_text())
    assert seal["labels_generated"] is False
    assert labels["generated_after_output_seal"] and len(labels["heads"]) == 10
    assert not labels["labels_control_evaluation"] and not labels["original_ABC_rejudged"]


def test_public_entry_refuses_changed_draw_count_or_missing_seal(tmp_path):
    rules = json.loads(RULES.read_text())
    rules["inference"]["n_boot"] = 32
    with pytest.raises(ValueError, match="frozen inference"):
        assemble_inference(tmp_path, tmp_path, COORDINATES, rules, [])
    rules = json.loads(RULES.read_text())
    with pytest.raises(ValueError, match="sealed"):
        assemble_inference(tmp_path, tmp_path, COORDINATES, rules, [])
