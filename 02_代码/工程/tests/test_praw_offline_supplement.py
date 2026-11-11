"""Synthetic boundary checks for the separate, complete Praw comparison.

These fixtures neither fit a learner nor read the research measurement arrays.
"""
from __future__ import annotations

import ast
import builtins
import argparse
import importlib.util
import inspect
import json
from repo_paths import Path, repository_root

import numpy as np
import pytest

from windfarm_moe import praw_offline_supplement as auxiliary
from windfarm_moe import state_measurement as legacy


class FixedPrediction:
    """A fixed test double, deliberately without a fit method."""

    def __init__(self, value=0.0):
        self.value = value
        self.calls = 0

    def predict(self, features):
        self.calls += 1
        return np.full(len(features), self.value, dtype=float)


def registry():
    return auxiliary.freeze_registry({"seeds": [201, 202, 203, 204, 205]})


def evaluation_inputs(shortfall=12.0):
    # The first day has one record and the second has six. Pooled means must
    # therefore use the total count rather than an unweighted daily mean.
    mask = np.ones((4, 2), dtype=bool)
    mask[0, 1] = False
    return {
        "features": np.ones((8, 119), dtype=np.float32),
        "shortfall": np.full((4, 2), shortfall, dtype=float),
        "mask": mask,
        "anchors": np.array([143, 144, 145, 146]),
    }


def completed_records(value=0.0, shortfall=12.0):
    identities = registry()
    models = {item["identity_id"]: FixedPrediction(value) for item in identities}
    offsets = {item["identity_id"]: 0.0 for item in identities}
    records = auxiliary.evaluate_all(identities, models, offsets,
                                     evaluation_inputs(shortfall))
    return identities, models, offsets, records


def test_T01_raw_power_is_one_extra_column_on_exact_legacy_background():
    data = np.arange(120 * 2 * 4, dtype=float).reshape(120, 2, 4)
    anchors = np.array([45, 46, 47])
    forecast = np.array([[500., 510.], [520., 530.], [540., 550.]])
    original = legacy.information_matrix(data, anchors, forecast, "O6")
    raw = auxiliary.praw_information_matrix(data, anchors, forecast)
    assert raw.shape == (6, 119)
    np.testing.assert_array_equal(raw[:, :118], original)
    np.testing.assert_array_equal(raw[:, 118], data[anchors, :, 1].ravel())
    engineered = legacy.information_matrix(data, anchors, forecast, "OP6")
    assert engineered.shape[1] == raw.shape[1] + 2
    np.testing.assert_array_equal(raw, engineered[:, :119])


def test_T01_no_pitch_or_future_target_and_no_repair_of_missing_raw_power():
    data = np.ones((120, 2, 4), dtype=float)
    anchors = np.array([45, 46, 47])
    forecast = np.full((3, 2), 500.)
    data[45, 0, 1] = -3.0
    data[46, 1, 1] = np.nan
    before = auxiliary.praw_information_matrix(data, anchors, forecast)
    changed = data.copy()
    changed[..., 3] = -999999.
    changed[anchors[-1] + 1:] = 123456.
    after = auxiliary.praw_information_matrix(changed, anchors, forecast)
    np.testing.assert_array_equal(after, before)
    assert before[0, -1] == -3.0
    assert np.isnan(before[3, -1])


def test_T02_registry_is_fixed_ten_identities_and_rejects_seed_substitution():
    identities = registry()
    assert [item["identity_id"] for item in identities] == [
        f"Praw_{estimator}_{seed}"
        for estimator in ("HGB", "MLP") for seed in range(201, 206)
    ]
    assert len({item["identity_id"] for item in identities}) == 10
    assert {(item["estimator"], item["seed"]) for item in identities} == {
        (estimator, seed) for estimator in ("HGB", "MLP")
        for seed in range(201, 206)
    }
    for seeds in ([201, 202, 203, 204], [201, 202, 203, 204, 206],
                  [201, 202, 203, 204, 204]):
        with pytest.raises(ValueError):
            auxiliary.freeze_registry({"seeds": seeds})


def test_T02_evaluator_has_no_qualification_selector_or_file_dependency(monkeypatch):
    identities = registry()
    models = {item["identity_id"]: FixedPrediction(1.) for item in identities}
    offsets = {item["identity_id"]: -0.5 for item in identities}
    inputs = evaluation_inputs()

    def forbidden(*args, **kwargs):
        pytest.fail("Offline evaluation accessed a label file or legacy selector")

    parameters = inspect.signature(auxiliary.evaluate_all).parameters
    assert list(parameters) == ["registry", "models", "offsets", "inputs", "predict_fn"]
    assert not any(p.kind == inspect.Parameter.VAR_KEYWORD for p in parameters.values())
    monkeypatch.setattr(builtins, "open", forbidden)
    monkeypatch.setattr(Path, "read_text", forbidden)
    monkeypatch.setattr(legacy, "choose_offset", forbidden)
    result = auxiliary.evaluate_all(identities, models, offsets, inputs)
    assert len(result) == 10
    assert all(item["compute_status"] == "EVALUATION_COMPLETED" for item in result)
    assert all(model.calls == 1 for model in models.values())
    for item in result:
        np.testing.assert_array_equal(item["actions"], np.full((4, 2), .5))
        assert set(item["blocks"]) >= {"C", "R", "U", "V", "N"}


def test_T02_changed_or_all_failed_labels_cannot_change_evaluation_visibility():
    identities, models, offsets, first = completed_records(value=1.)
    # This metadata may be displayed after sealing, but must not be consulted
    # even if a caller carries it in the fixed identity registry.
    altered = [dict(item, history_qualification="NOT_QUALIFIED_BY_BOUND",
                    evaluation_qualification="UNDETERMINED_INTERVAL")
               for item in identities]
    second = auxiliary.evaluate_all(altered, models, offsets, evaluation_inputs())
    assert [item["identity_id"] for item in first] == [item["identity_id"] for item in second]
    for old, new in zip(first, second):
        assert old["compute_status"] == new["compute_status"] == "EVALUATION_COMPLETED"
        np.testing.assert_array_equal(new["actions"], old["actions"])
        for metric in ("C", "R", "U", "V", "N", "days"):
            np.testing.assert_array_equal(new["blocks"][metric], old["blocks"][metric])
    with pytest.raises(TypeError):
        auxiliary.evaluate_all(identities, models, offsets, evaluation_inputs(),
                               qualification={"all": False})


def test_T03_finite_high_loss_is_retained_for_every_estimator_and_fit():
    identities, models, _, records = completed_records(value=0., shortfall=1e9)
    assert [item["identity_id"] for item in records] == [item["identity_id"] for item in identities]
    assert all(model.calls == 1 for model in models.values())
    assert all(item["compute_status"] == "EVALUATION_COMPLETED" for item in records)
    for item in records:
        assert item["blocks"]["C"].sum() > 1e9
        assert item["blocks"]["N"].sum() == 7
        assert item["blocks"]["V"].sum() == 7
        assert np.isfinite(item["blocks"]["U"]).all()


def test_T04_each_head_has_own_signed_higher_quantile_offset():
    shortfall = np.array([0., 2., 4., 10., np.nan])
    mask = np.array([True, True, True, True, False])
    raw_first = np.array([5., 5., 5., 20., 100.])
    raw_second = np.array([0., 0., 0., 0., 100.])
    first = auxiliary.fit_signed_offset(raw_first, shortfall, mask)
    second = auxiliary.fit_signed_offset(raw_second, shortfall, mask)
    assert first == np.quantile([-5., -3., -1., -10.], .925, method="higher") == -1.
    assert second == 10.
    assert first != second
    # Offset calibration sees target-valid historical rows, not a pitch-valid
    # primary subset, and has no test-target argument or free q search.
    parameters = inspect.signature(auxiliary.fit_signed_offset).parameters
    assert "evaluation" not in " ".join(parameters)
    with pytest.raises(ValueError):
        auxiliary.fit_signed_offset(raw_first, shortfall, mask, q=.95)
    with pytest.raises(ValueError):
        auxiliary.fit_signed_offset(raw_first, shortfall, np.zeros(5, bool))


def test_T04_action_clips_before_signed_offset_and_does_not_recalibrate():
    identities = registry()
    models = {item["identity_id"]: FixedPrediction(-10.) for item in identities}
    offsets = {item["identity_id"]: 2. for item in identities}
    first = auxiliary.evaluate_all(identities, models, offsets, evaluation_inputs(12.))
    second = auxiliary.evaluate_all(identities, models, offsets, evaluation_inputs(1e8))
    for left, right in zip(first, second):
        np.testing.assert_array_equal(left["raw"], np.zeros((4, 2)))
        np.testing.assert_array_equal(left["actions"], np.full((4, 2), 2.))
        np.testing.assert_array_equal(right["actions"], left["actions"])
    assert set(offsets.values()) == {2.}


def test_T13_prediction_or_missing_model_failure_keeps_all_ten_terminal_records():
    identities = registry()
    models = {item["identity_id"]: FixedPrediction(2.) for item in identities}
    offsets = {item["identity_id"]: 0. for item in identities}
    models["Praw_HGB_203"] = FixedPrediction(np.nan)
    del models["Praw_MLP_205"]
    records = auxiliary.evaluate_all(identities, models, offsets, evaluation_inputs())
    assert len(records) == 10
    by_id = {item["identity_id"]: item for item in records}
    for identity_id in ("Praw_HGB_203", "Praw_MLP_205"):
        item = by_id[identity_id]
        assert item["compute_status"] == "COMPUTATION_FAILED"
        assert item["failure_reason"]
        assert item.get("blocks") is None
        assert item.get("actions") is None
    assert sum(item["compute_status"] == "EVALUATION_COMPLETED" for item in records) == 8
    pooled = auxiliary.pooled_five_fit_metrics(records)
    for estimator in ("HGB", "MLP"):
        assert pooled[estimator]["status"] == "UNAVAILABLE_INCOMPLETE_FITS"
        assert pooled[estimator]["fit_count"] == 4
        assert all(pooled[estimator][metric] is None for metric in ("C", "R", "U", "V"))


def test_unequal_day_counts_pool_totals_and_only_complete_five_fit_average():
    blocks = dict(C=np.array([100., 9.]), R=np.array([10., 9.]),
                  U=np.array([9., 0.]), V=np.array([1., 0.]),
                  N=np.array([1., 9.]), days=np.array([0, 1]))
    means = auxiliary.pool_daily_totals(blocks)
    assert means["N"] == 10
    for metric in ("C", "R", "U", "V"):
        assert means[metric] == pytest.approx(blocks[metric].sum() / 10)
    assert means["C"] != pytest.approx(np.mean(blocks["C"] / blocks["N"]))
    _, _, _, records = completed_records(value=1.)
    pooled = auxiliary.pooled_five_fit_metrics(records)
    for estimator in ("HGB", "MLP"):
        rows = [item for item in records if item["estimator"] == estimator]
        assert pooled[estimator]["status"] == "COMPLETE_FIVE_FIT"
        assert pooled[estimator]["fit_count"] == 5
        for metric in ("C", "R", "U", "V"):
            expected = np.mean([auxiliary.pool_daily_totals(item["blocks"])[metric]
                                for item in rows])
            assert pooled[estimator][metric] == pytest.approx(expected)


def test_common_reference_rejects_original_selected_q_and_wrong_q_metadata():
    common = {"recipe": "Common", "q": .925, "token": "historical-common"}
    original = {"recipe": "Original", "q": .95, "token": "not-comparable"}
    mapping = {"Common|HGB|OP6|201|0.925": common,
               "Original|HGB|OP6|201|0.95": original}
    assert auxiliary.bind_common_reference(mapping, "HGB", "OP6", 201) is common
    with pytest.raises((ValueError, KeyError)):
        auxiliary.bind_common_reference({"Original|HGB|OP6|201|0.95": original},
                                        "HGB", "OP6", 201)
    for bad in ({"recipe": "Original", "q": .925},
                {"recipe": "Common", "q": .95}):
        with pytest.raises(ValueError):
            auxiliary.bind_common_reference({"Common|HGB|OP6|201|0.925": bad},
                                            "HGB", "OP6", 201)
    with pytest.raises(ValueError):
        auxiliary.bind_common_reference(mapping, "HGB", "OP6", 201, q=.95)


def test_T14_independent_cli_contains_no_qualified_only_or_legacy_evaluate_driver():
    root = Path(repository_root())
    path = root / "scripts" / "run_praw_offline_supplement.py"
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    options = [arg.value for node in ast.walk(tree)
               if isinstance(node, ast.Call)
               and isinstance(node.func, ast.Attribute)
               and node.func.attr == "add_argument"
               for arg in node.args if isinstance(arg, ast.Constant)
               and isinstance(arg.value, str)]
    assert "--qualified-only" not in options
    assert "--risk-qualified-only" not in options
    # The auxiliary code may share leaf feature/accounting functions, but it
    # must not invoke the old risk-filtered evaluate entry.
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "scripts.run_state_measurement_pilot":
            assert not any(alias.name in ("evaluate", "select") for alias in node.names)
    assert "test_no_historical_choice_never_opens_evaluation" in (
        root / "tests" / "test_state_measurement_runner.py").read_text(encoding="utf-8")


def test_original_contract_and_raw_result_files_are_not_test_inputs():
    # The tests use no project raw/result archive: this fixture merely binds
    # the declared head identities to the human-reviewed static rules.
    path = (Path(repository_root()) / "research_audit" /
            "minimum_supplement_plan_v3_20261021" / "RULES.json")
    rules = json.loads(path.read_text(encoding="utf-8"))
    assert [item["identity_id"] for item in registry()] == [
        item["id"] for item in rules["new_fit_budget"]["heads"]]
    assert rules["evaluation_policy"]["qualification_controls_evaluation"] is False
    assert rules["immutable"]["primary_offset_quantile"] == .925


def load_auxiliary_runner():
    path = Path(repository_root()) / "scripts/run_praw_offline_supplement.py"
    spec = importlib.util.spec_from_file_location("praw_boundary_runner", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("selection_failure_mode", [None, "predict", "feature", "load"])
def test_T04_runner_reuses_exact_fit_indices_before_evaluation_without_pitch_filter(
        tmp_path, monkeypatch, selection_failure_mode):
    runner = load_auxiliary_runner()
    identities = registry()
    row = identities[0]
    root = Path(repository_root())
    original = json.loads((root / "experiments/state_measurement_pilot_20261020/protocol.json")
                          .read_text(encoding="utf-8"))
    parent = tmp_path / "parent"
    prepared = parent / "prepared"
    prepared.mkdir(parents=True)
    physical = np.ones((200, 2, 4), dtype=np.float32)
    physical[..., 3] = np.nan  # All training-time pitch is missing in this fixture.
    np.save(prepared / "physical_channels.npy", physical)
    task = runner.original_tasks(original).index(
        dict(estimator=row["estimator"], cell="O6", seed=row["seed"]))
    index_path = parent / "fits" / str(task) / "fit_indices.npy"
    index_path.parent.mkdir(parents=True)
    # Retain production's 360,000-row contract without allocating its feature
    # matrix: a lazy, broadcast-only feature double records the exact indexing.
    indices = np.arange(2, 360002, dtype=np.int64)[::-1]
    np.save(index_path, indices)
    base = tmp_path / "auxiliary"
    (base / "prepared").mkdir(parents=True)
    (base / "prepared/registry.json").write_text(json.dumps(identities))
    output = base / "fits" / "0"
    args = argparse.Namespace(base=base, output=output, worker=0, stage="fit")
    observed = {"phases": [], "predict_phases": [], "fit_complete": False}
    train_shortfall = np.arange(360002, dtype=float).reshape(180001, 2)
    train = dict(anchors=np.arange(180001), forecast=np.zeros((180001, 2)),
                 shortfall=train_shortfall, target_mask=np.ones((180001, 2), bool),
                 primary_mask=np.zeros((180001, 2), bool))

    class LazyTrainingFeatures:
        def __getitem__(self, selected):
            np.testing.assert_array_equal(selected, indices)
            observed["selected_indices"] = np.asarray(selected).copy()
            return np.broadcast_to(np.zeros((1, 119), np.float32), (len(selected), 119))

    class TrainingSpy:
        def fit(self, features, target):
            assert features.shape == (360000, 119)
            np.testing.assert_array_equal(target, train_shortfall.ravel()[indices])
            observed["fit_complete"] = True
            return self

        def predict(self, features):
            phase = int(features[0, 0])
            observed["predict_phases"].append(phase)
            if selection_failure_mode == "predict" and phase == 2:
                raise RuntimeError("synthetic historical prediction failure")
            return np.ones(len(features))

    def begin_fixture(call_args, _inputs):
        call_args.output.mkdir(parents=True, exist_ok=False)
        return {}

    def load_stage_fixture(_prepared, phase):
        observed["phases"].append(phase)
        if phase == "fit":
            return train
        if selection_failure_mode == "load" and phase == "selection":
            raise OSError("synthetic historical load failure")
        assert observed["fit_complete"]
        if phase in ("selection", "evaluation"):
            # Test access is only allowed after fitting and own calibration
            # have completed and the historical offset file is sealed.
            assert (output / "own_offset.json").is_file()
            assert (output / "model.joblib").is_file()
        values = evaluation_inputs(shortfall=12.)
        marker = {"offset": 1, "selection": 2, "evaluation": 3}[phase]
        return dict(anchors=values["anchors"], forecast=np.full((4, 2), marker),
                    shortfall=values["shortfall"], target_mask=np.ones((4, 2), bool),
                    primary_mask=values["mask"])

    def feature_fixture(_data, anchors, forecast):
        assert np.isnan(_data[..., 3]).all()
        if len(anchors) == 180001:
            return LazyTrainingFeatures()
        if selection_failure_mode == "feature" and forecast[0, 0] == 2:
            raise RuntimeError("synthetic historical feature failure")
        return np.full((8, 119), forecast[0, 0], dtype=np.float32)

    def dump_fixture(_model, path):
        Path(path).write_bytes(b"synthetic-model-not-a-fitted-research-estimator")

    monkeypatch.setattr(runner, "context", lambda _args: ({}, {}, parent, original))
    monkeypatch.setattr(runner, "verify_bundle", lambda *args: {})
    monkeypatch.setattr(runner, "begin", begin_fixture)
    monkeypatch.setattr(runner, "finish", lambda *_args: None)
    monkeypatch.setattr(runner, "learner", lambda *args: TrainingSpy())
    monkeypatch.setattr(runner, "load_stage", load_stage_fixture)
    monkeypatch.setattr(runner, "praw_information_matrix", feature_fixture)
    monkeypatch.setattr(runner.joblib, "dump", dump_fixture)
    runner.fit_worker(args)
    assert observed["phases"] == ["fit", "offset", "selection", "evaluation"]
    assert observed["predict_phases"] == (
        [1, 3] if selection_failure_mode in ("feature", "load") else [1, 2, 3])
    np.testing.assert_array_equal(np.load(output / "fit_indices.npy"), indices)
    own_offset = json.loads((output / "own_offset.json").read_text())
    assert own_offset["offset_kw"] == 11.
    assert own_offset["q"] == .925
    assert own_offset["population"] == "offset_target_mask"
    assert (output / "evaluation_actions.npz").is_file()
    with np.load(output / "evaluation_actions.npz") as archive:
        np.testing.assert_array_equal(archive["actions"], np.full((4, 2), 12.))
    status = json.loads((output / "identity.json").read_text())
    assert status["compute_status"] == "EVALUATION_COMPLETED"
    assert status["evaluation_compute_status"] == "EVALUATION_COMPLETED"
    assert (output / "evaluation_blocks.npz").is_file()
    if selection_failure_mode:
        assert status["history_compute_status"] == "COMPUTATION_FAILED"
        assert "historical" in status["selection_failure_reason"]
        assert selection_failure_mode in status["selection_failure_reason"]
        assert not (output / "selection_actions.npz").exists()
        assert not (output / "selection_blocks.npz").exists()
    else:
        assert status["history_compute_status"] == "EVALUATION_COMPLETED"
        assert (output / "selection_blocks.npz").is_file()
    assert status["evaluation_hash"]
