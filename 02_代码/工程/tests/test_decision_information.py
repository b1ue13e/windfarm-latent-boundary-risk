"""Software fixtures for arrived information and paired decision inference.

These synthetic arrays test implementation semantics, not scientific claims.
"""
from __future__ import annotations

import importlib.util
from repo_paths import Path, repository_root

import numpy as np
import pandas as pd
import pytest
from threadpoolctl import threadpool_limits

from windfarm_moe.decision_information import (
    arrived_history,
    block_totals,
    paired_interval,
    sample_loss,
    validate_temporal_stages,
)


def _telemetry() -> np.ndarray:
    return np.arange(12 * 2 * 2, dtype=np.float64).reshape(12, 2, 2)


def test_arrived_history_has_fixed_window_and_nested_arrival_masks():
    values = _telemetry()
    anchors = np.array([5, 9])
    clean = arrived_history(values, anchors, history_steps=4, delay_steps=0)
    delayed = arrived_history(values, anchors, history_steps=4, delay_steps=2)

    assert clean.shape == delayed.shape == (2, 2, 4, 2)
    for row, anchor in enumerate(anchors):
        expected = values[anchor - 3 : anchor + 1].transpose(1, 0, 2)
        np.testing.assert_array_equal(clean[row], expected)
    np.testing.assert_array_equal(delayed[:, :, :2], clean[:, :, :2])
    assert np.isnan(delayed[:, :, 2:]).all()


def test_unarrived_and_future_telemetry_perturbations_do_not_change_features():
    values = _telemetry()
    perturbed = values.copy()
    # At issue 7 with delay 2, only source times <= 5 have arrived.
    perturbed[6:] = -1e12
    before = arrived_history(values, np.array([7]), history_steps=5, delay_steps=2)
    after = arrived_history(perturbed, np.array([7]), history_steps=5, delay_steps=2)
    np.testing.assert_array_equal(before, after)


def test_early_history_is_missing_instead_of_negative_index_wraparound():
    values = _telemetry()
    history = arrived_history(values, np.array([0]), history_steps=4, delay_steps=0)
    assert np.isnan(history[0, :, :3]).all()
    np.testing.assert_array_equal(history[0, :, 3], values[0])


@pytest.mark.parametrize("delay", [4, 5, 20])
def test_delay_at_least_window_length_cannot_reveal_window_values(delay):
    result = arrived_history(_telemetry(), np.array([8]), history_steps=4, delay_steps=delay)
    assert result.shape == (1, 2, 4, 2)
    assert np.isnan(result).all()


def test_sample_loss_uses_float64_and_procurement_plus_uncovered_shortfall():
    result = sample_loss(np.array([5, 1], dtype=np.float32), np.array([3, 3], dtype=np.float32))
    assert result.dtype == np.float64
    np.testing.assert_allclose(result, np.array([23.0, 3.0]) / 6)


@pytest.mark.parametrize(
    ("shortfall", "reserve"),
    [
        (np.array([1.0]), np.array([[1.0]])),
        (np.array([-1.0]), np.array([0.0])),
        (np.array([1.0]), np.array([-0.1])),
        (np.array([np.nan]), np.array([1.0])),
        (np.array([1.0]), np.array([np.inf])),
    ],
)
def test_sample_loss_rejects_invalid_data_and_shape_broadcasting(shortfall, reserve):
    with pytest.raises(ValueError):
        sample_loss(shortfall, reserve)


def _masked_block_fixture():
    shortfall = np.array([[3.0, np.nan], [4.0, 1.0], [np.nan, 2.0], [1.0, np.nan]])
    reserve = np.array([[1.0, np.nan], [2.0, 1.0], [np.nan, 3.0], [0.0, np.nan]])
    mask = np.array([[1, 0], [1, 1], [0, 1], [1, 0]])
    anchors = np.array([0, 143, 144, 289])
    return shortfall, reserve, mask, anchors


def test_block_totals_use_absolute_anchor_blocks_and_allow_only_masked_nan():
    shortfall, reserve, mask, anchors = _masked_block_fixture()
    result = block_totals(shortfall, reserve, mask, anchors, steps_per_block=144)
    np.testing.assert_array_equal(result["block_ids"], [0, 1, 2])
    np.testing.assert_array_equal(result["count"], [3, 1, 1])
    np.testing.assert_allclose(result["loss_sum"], np.array([44.0, 3.0, 10.0]) / 6)
    np.testing.assert_allclose(result["reserve_sum"], np.array([4.0, 3.0, 0.0]) / 6)
    np.testing.assert_allclose(result["shortage_sum"], np.array([4.0, 0.0, 1.0]) / 6)
    np.testing.assert_array_equal(result["violation_sum"], [2, 0, 1])


@pytest.mark.parametrize("invalid_mask", [np.nan, np.inf, 0.5, -1.0, 2.0])
def test_block_totals_reject_nonbinary_or_nonfinite_masks(invalid_mask):
    shortfall, reserve, mask, anchors = _masked_block_fixture()
    mask = mask.astype(float)
    mask[0, 0] = invalid_mask
    with pytest.raises(ValueError):
        block_totals(shortfall, reserve, mask, anchors)


@pytest.mark.parametrize(("which", "bad"), [("shortfall", np.nan), ("reserve", np.nan), ("reserve", -1.0)])
def test_block_totals_reject_invalid_values_at_valid_coordinates(which, bad):
    shortfall, reserve, mask, anchors = _masked_block_fixture()
    (shortfall if which == "shortfall" else reserve)[0, 0] = bad
    with pytest.raises(ValueError):
        block_totals(shortfall, reserve, mask, anchors)


def _interval(numerators, counts, left=0, right=1, **kwargs):
    return paired_interval(
        numerators, counts, left, right,
        n_boot=600, block_span=kwargs.pop("block_span", 2), seed=20261019, **kwargs,
    )


def test_paired_interval_weights_cells_instead_of_averaging_block_means():
    # One cell with loss 10 and nine with loss 0: the mean is 1, not 5.
    numerators = np.array([[[10.0, 0.0], [0.0, 0.0]]])
    result = _interval(numerators, np.array([1, 9]), block_span=1)
    assert result["point"] == pytest.approx(1.0)


def test_identical_candidate_has_exact_zero_difference_and_interval():
    block_values = np.array([[1.0, 10.0, 2.0, 8.0, 3.0, 12.0]])
    numerators = np.stack([block_values, block_values], axis=1)
    result = _interval(numerators, np.array([1, 2, 3, 1, 4, 2]))
    assert result["point"] == 0.0
    np.testing.assert_array_equal(result["ci95"], [0.0, 0.0])
    np.testing.assert_array_equal(result["simultaneous_ci"], [0.0, 0.0])


def test_reversing_comparison_preserves_draws_and_negates_interval():
    numerators = np.array([
        [[3.0, 11.0, 4.0, 8.0, 1.0, 14.0], [1.0, 4.0, 8.0, 3.0, 2.0, 9.0]],
        [[4.0, 13.0, 3.0, 7.0, 2.0, 15.0], [2.0, 3.0, 9.0, 4.0, 1.0, 8.0]],
    ])
    counts = np.array([1, 3, 2, 1, 4, 2])
    forward = _interval(numerators, counts, left=0, right=1, family_size=3)
    reverse = _interval(numerators, counts, left=1, right=0, family_size=3)
    assert forward["bootstrap_indices_sha256"] == reverse["bootstrap_indices_sha256"]
    assert reverse["point"] == pytest.approx(-forward["point"])
    np.testing.assert_allclose(reverse["ci95"], -np.asarray(forward["ci95"])[::-1])
    np.testing.assert_allclose(reverse["simultaneous_ci"], -np.asarray(forward["simultaneous_ci"])[::-1])
    assert forward["simultaneous_ci"][0] <= forward["ci95"][0]
    assert forward["simultaneous_ci"][1] >= forward["ci95"][1]


def test_copying_seed_does_not_invent_independent_weather_evidence():
    one_seed = np.array([[[3.0, 12.0, 2.0, 14.0, 1.0, 7.0], [1.0, 4.0, 6.0, 5.0, 2.0, 3.0]]])
    counts = np.array([1, 2, 3, 2, 1, 4])
    single = _interval(one_seed, counts)
    repeated = _interval(np.repeat(one_seed, 5, axis=0), counts)
    assert repeated["point"] == pytest.approx(single["point"])
    np.testing.assert_allclose(repeated["ci95"], single["ci95"])
    np.testing.assert_allclose(repeated["simultaneous_ci"], single["simultaneous_ci"])
    assert repeated["bootstrap_indices_sha256"] == single["bootstrap_indices_sha256"]


def test_temporal_stages_wait_for_last_targets_to_arrive():
    # Last fit issue 9 + horizon 6 + label delay 1 = 16, before calibration 17.
    stages = {"fit": (0, 10), "calibrate": (17, 27), "evaluate": (34, 44)}
    assert validate_temporal_stages(stages, horizon=6, label_delay=1) is None


@pytest.mark.parametrize(
    "stages",
    [
        {"fit": (0, 10), "calibrate": (16, 26)},  # Arrival at the decision instant is not strictly earlier.
        {"fit": (0, 10), "calibrate": (9, 20)},
        {"fit": (4, 4), "calibrate": (17, 27)},
        {"fit": (0, 10), "calibrate": (17, 27), "evaluate": (33, 44)},
    ],
)
def test_temporal_stages_reject_overlap_empty_stage_and_unmatured_targets(stages):
    with pytest.raises(ValueError):
        validate_temporal_stages(stages, horizon=6, label_delay=1)


@pytest.fixture(scope="module")
def development_script():
    path = Path(repository_root()) / "scripts/run_decision_information_development.py"
    spec = importlib.util.spec_from_file_location("decision_information_development_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _raw_frame():
    rows = []
    for time, stamp in enumerate(["00:00", "00:10", "00:20"]):
        for node in [9, 3]:
            rows.append({
                "TurbID": node, "Day": 1, "Tmstamp": stamp,
                "Wspd": float(10 * time + node),
                "Patv": float(100 * time + node), "Prtv": float(node - time),
                "Pab1": 1.0, "Pab2": 4.0, "Pab3": 7.0,
            })
    frame = pd.DataFrame(rows)
    frame.loc[(frame.Tmstamp == "00:00") & (frame.TurbID == 3), "Patv"] = -3.0
    frame.loc[(frame.Tmstamp == "00:10") & (frame.TurbID == 9), "Patv"] = 0.0
    frame.loc[(frame.Tmstamp == "00:10") & (frame.TurbID == 3), "Pab2"] = np.nan
    return frame


def test_raw_csv_reconstructs_explicit_coordinates_and_complete_pitch_only(development_script, tmp_path):
    raw = _raw_frame().iloc[[5, 0, 3, 1, 4, 2]]
    path = tmp_path / "synthetic.csv"
    raw.to_csv(path, index=False)
    data, nodes, metadata = development_script.load_raw_csv(path)

    assert data.shape == (3, 2, 4)
    np.testing.assert_array_equal(nodes, [3, 9])
    np.testing.assert_array_equal(data[:, :, 0], [[3, 9], [13, 19], [23, 29]])
    assert data[0, 0, 1] == -3.0
    assert data[1, 1, 1] == 0.0
    assert metadata["negative_power_cells_preserved"] == 1
    assert metadata["zero_power_cells_preserved"] == 1
    assert data[0, 0, 3] == 4.0
    assert np.isnan(data[1, 0, 3])
    assert metadata["missing_counts"]["pitch"] == 1


@pytest.mark.parametrize("coordinate_error", ["duplicate", "missing"])
def test_raw_csv_rejects_duplicate_and_missing_coordinates(development_script, tmp_path, coordinate_error):
    raw = _raw_frame()
    if coordinate_error == "duplicate":
        raw = pd.concat([raw, raw.iloc[[1]]], ignore_index=True)
    else:
        # Preserve the final timestamp, so a missing interior coordinate cannot look like a shorter file.
        raw = raw.drop(index=2)
    path = tmp_path / "invalid.csv"
    raw.to_csv(path, index=False)
    with pytest.raises(ValueError, match="coordinates"):
        development_script.load_raw_csv(path)


def _stage_protocol():
    return {
        "task": {"horizon_steps": 6, "target_release_delay_steps": 1,
                 "commitment_age_steps": 6, "history_steps": 24},
        "stage_days": {"point_fit": [1, 1], "state_fit": [2, 2], "policy_fit": [3, 3],
                       "calibration": [4, 4], "development_evaluation": [5, 5]},
    }


def test_stages_for_accounts_for_twelve_step_point_target_maturity(development_script):
    protocol = _stage_protocol()
    stages = development_script.stages_for(protocol, n_times=720)
    assert stages["point_fit"] == (23, 131)
    assert stages["state_fit"] == (144, 281)
    assert stages["point_fit"][1] - 1 + 12 + 1 < stages["state_fit"][0]
    assert stages["calibration"][1] - 1 + 6 + 1 < stages["development_evaluation"][0]


def test_stages_for_rejects_overlapping_stage_calendar(development_script):
    protocol = _stage_protocol()
    protocol["stage_days"]["state_fit"] = [1, 2]
    with pytest.raises(ValueError):
        development_script.stages_for(protocol, n_times=720)


@pytest.mark.parametrize("pitch_available", [False, True])
def test_all_feature_groups_share_forecast_and_ignore_unarrived_telemetry(development_script, pitch_available):
    data = np.arange(12 * 2 * 4, dtype=np.float32).reshape(12, 2, 4)
    anchors = np.array([7])
    forecast = np.array([[21.0, 34.0]], dtype=np.float32)
    groups = development_script.feature_groups(data, anchors, forecast, 5, 2, pitch_available)
    perturbed = data.copy()
    perturbed[6:] = -1e8
    after = development_script.feature_groups(perturbed, anchors, forecast, 5, 2, pitch_available)
    for name in groups:
        np.testing.assert_array_equal(groups[name], after[name])
        np.testing.assert_array_equal(groups[name][:, 0], forecast.reshape(-1))
        np.testing.assert_array_equal(groups[name][:, :4], groups["A"][:, :4])
    np.testing.assert_array_equal(groups["B"][:, :groups["A"].shape[1]], groups["A"])

    # A changed lawful published commitment must be visible to every comparison group.
    changed = development_script.feature_groups(data, anchors, forecast + 100, 5, 2, pitch_available)
    for name in groups:
        np.testing.assert_array_equal(changed[name][:, 0], forecast.reshape(-1) + 100)
        np.testing.assert_array_equal(changed[name][:, 1:], groups[name][:, 1:])


def test_withheld_pitch_cannot_enter_direct_feature_groups(development_script):
    data = np.arange(12 * 2 * 4, dtype=np.float32).reshape(12, 2, 4)
    anchors = np.array([7])
    forecast = np.array([[1.0, 2.0]], dtype=np.float32)
    first = development_script.feature_groups(data, anchors, forecast, 5, 0, False)
    data[..., 3] = 1e9
    second = development_script.feature_groups(data, anchors, forecast, 5, 0, False)
    for name in first:
        np.testing.assert_array_equal(first[name], second[name])


def test_missing_wind_uses_global_quantile_not_last_wind_bin(development_script):
    fit_wind = np.repeat([1.0, 20.0], 60)
    # Last wind bin deliberately differs from the pooled fallback.
    shortfall = np.repeat([100.0, 1.0], 60)
    predictions, info = development_script.bin_policy(
        fit_wind, shortfall, np.ones(120, dtype=bool),
        {"evaluation": np.array([np.nan, 20.0, 1.0])},
    )
    assert info["missing_fallback"] == 100.0
    np.testing.assert_array_equal(predictions["evaluation"], [100.0, 1.0, 100.0])


def test_tiny_histogram_quantile_flow_accepts_nan_and_history_only_calibration(development_script):
    settings = {"max_iter": 4, "max_leaf_nodes": 3, "min_samples_leaf": 3,
                "learning_rate": 0.2, "l2_regularization": 0.1}
    x = np.column_stack((np.linspace(0, 1, 60), np.ones(60)))
    x[::4, 0] = np.nan
    x[:, 1] = np.nan  # A fully unavailable channel is a lawful input, not a reason to remove samples.
    y = 2.0 + np.arange(60) % 7
    with threadpool_limits(limits=1):
        model = development_script.learner(settings, seed=201, quantile=True)
        model.fit(x[:40], y[:40])
        cal = np.maximum(model.predict(x[40:50]), 0)
        raw = np.maximum(model.predict(x[50:]), 0)
    assert np.isfinite(cal).all() and np.isfinite(raw).all()
    correction = np.quantile(y[40:50] - cal, 0.9, method="higher")
    reserve = np.maximum(raw + correction, 0)
    totals = block_totals(y[50:, None], reserve[:, None], np.ones((10, 1), dtype=bool), np.arange(50, 60))
    assert totals["count"].sum() == 10
    assert np.isfinite(totals["loss_sum"]).all()
    assert model.named_steps["regressor"].early_stopping is False
    transformed = model.named_steps["missing"].transform(x)
    assert np.isfinite(transformed).all()
    assert transformed.shape[1] > x.shape[1]


def test_bundle_rejects_modified_output_and_mismatched_producer(development_script, tmp_path):
    module = development_script
    payload = tmp_path / "array.bin"
    payload.write_bytes(b"archived-actions")
    receipt_path = tmp_path / "execution_receipt.json"
    receipt = {"status": "COMPLETED_DEVELOPMENT_NOT_CERTIFIED", "protocol_sha256": "abc",
               "arguments": {"stage": "run", "seed": 201, "condition": "fresh"},
               "source_sha256": {str(Path(module.__file__)): module.digest(Path(module.__file__)),
                   "decision_information.py": module.digest(Path(module.ROOT) / "windfarm_moe/decision_information.py")}}

    def seal():
        module.write_json(receipt_path, receipt)
        module.write_json(tmp_path / "output_manifest.json", {
            p.name: {"bytes": p.stat().st_size, "sha256": module.digest(p)}
            for p in (payload, receipt_path)})

    seal()
    assert module.verify_bundle(tmp_path, "abc", "run", 201, "fresh") == receipt
    with pytest.raises(ValueError, match="protocol/stage"):
        module.verify_bundle(tmp_path, "wrong", "run", 201, "fresh")
    with pytest.raises(ValueError, match="seed mismatch"):
        module.verify_bundle(tmp_path, "abc", "run", 202, "fresh")
    with pytest.raises(ValueError, match="condition mismatch"):
        module.verify_bundle(tmp_path, "abc", "run", 201, "delay1")
    payload.write_bytes(b"modified-actions")
    with pytest.raises(ValueError, match="output mismatch"):
        module.verify_bundle(tmp_path, "abc", "run", 201, "fresh")
    receipt["status"] = "RUNNING_DEVELOPMENT"
    seal()
    with pytest.raises(ValueError, match="not complete"):
        module.verify_bundle(tmp_path, "abc", "run", 201, "fresh")


def test_development_rejects_unimplemented_scientific_parameter_changes(development_script):
    import json
    protocol_path = Path(repository_root()) / "experiments/decision_information_development_20261018/protocol.json"
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    development_script.validate_protocol(protocol)
    protocol["task"]["rho"] = 20
    with pytest.raises(ValueError, match="supports only"):
        development_script.validate_protocol(protocol)
