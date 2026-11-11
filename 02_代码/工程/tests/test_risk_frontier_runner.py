"""Small synthetic integration tests, never empirical wind evidence."""
import argparse
import importlib.util
import json
from repo_paths import Path, repository_root

import numpy as np
import pytest


@pytest.fixture(scope="module")
def runner():
    path = Path(repository_root()) / "scripts/run_risk_cost_frontier.py"
    spec = importlib.util.spec_from_file_location("risk_frontier_test_runner", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_split_excludes_targets_not_released_before_selection(runner):
    anchors = np.arange(100, 151)
    fit, select = runner.split_calibration(anchors, 120, 150, 6, 1)
    np.testing.assert_array_equal(anchors[fit], np.arange(100, 113))
    np.testing.assert_array_equal(anchors[select], np.arange(120, 143))
    assert not fit[(anchors >= 113) & (anchors <= 119)].any()


def test_weighted_draws_keeps_seed_and_candidate_axes(runner):
    values = np.arange(2 * 3 * 4, dtype=float).reshape(2, 3, 4)
    counts = np.array([2., 3., 4., 5.])
    weights = np.array([[1, 1, 1, 1], [2, 0, 2, 0]], float)
    point, draws = runner.weighted_draws(values, counts, weights)
    assert draws.shape == (2, 2, 3)
    np.testing.assert_allclose(point, values.sum(axis=-1) / 14)
    np.testing.assert_allclose(draws[1], (2 * values[..., 0] + 2 * values[..., 2]) / 12)


def test_choose_then_aggregate_uses_frozen_choices_and_joint_risk(runner, tmp_path):
    protocol = {"seeds": [201, 202], "conditions": ["one", "two"], "variants": ["A", "B"],
                "offset_quantiles": [.9, .99], "task": {"alpha": .05},
                "inference": {"n_boot": 300, "primary_span_days": 3,
                              "sensitivity_spans_days": [1, 7], "rng_seed": 42,
                              "epsilon_curve": [0, .01, .05]}}
    pp = tmp_path / "protocol.json"
    runner.save(pp, protocol)
    historical, evaluation, choice = (tmp_path / name for name in ("historical", "evaluation", "choice"))
    counts = np.full(8, 100.)
    for condition in protocol["conditions"]:
        for seed in protocol["seeds"]:
            for stage, base in (("historical", historical), ("evaluate", evaluation)):
                out = base / f"seed{seed}" / condition
                receipt = runner.begin(out, pp, [], {"stage": stage, "seed": seed, "condition": condition})
                receipt["coordinate_identity"] = runner.array_identity({"anchors": np.arange(8), "mask": np.ones((8, 1), bool)})
                arrays = {}
                for vi, name in enumerate(protocol["variants"]):
                    for qi in range(2):
                        arrays[f"{name}__q{qi}__loss_sum"] = counts * (12 - 3 * vi + qi + .1 * np.arange(8))
                        arrays[f"{name}__q{qi}__violation_sum"] = np.arange(8) % 3 + (18 if qi == 0 else 1)
                grid_name = "historical_grid.npz" if stage == "historical" else "evaluation_grid.npz"
                np.savez(out / grid_name, counts=counts, block_ids=np.arange(8), **arrays)
                runner.save(out / "resources.json", {"resources": {"A": {"order": [1, 1, 10]}, "B": {"order": [3, 1, 30]}}})
                runner.finish(out, receipt)
    runner.choose(argparse.Namespace(historical=historical, output=choice, protocol=pp), protocol)
    frozen = json.loads((choice / "choices.json").read_text())["choices"]
    assert all(v["q_index"] == 1 and v["historically_qualified"] for c in frozen.values() for v in c.values())
    for condition in protocol["conditions"]:
        for seed in protocol["seeds"]:
            out = evaluation / f"seed{seed}" / condition
            producer = json.loads((out / "receipt.json").read_text())
            producer["input_sha256"][str((choice / "choices.json").resolve())] = runner.sha(choice / "choices.json")
            runner.finish(out, producer)
    output = tmp_path / "aggregate"
    runner.aggregate(argparse.Namespace(runs=evaluation, choice=choice, output=output, protocol=pp), protocol)
    result = json.loads((output / "frontier_results.json").read_text())
    assert not result["deployment_certified"]
    case = result["results"][0]["cases"]["one"]
    assert case["epsilon_curve"][-1]["minimum_resource_indices"] == [1]
    # Source identity and completed status cannot be replaced by merely existing files.
    with pytest.raises(ValueError, match="identity mismatch"):
        runner.verify(choice, runner.sha(pp), "historical")
    wrong = historical / "seed202/two"
    producer = json.loads((wrong / "receipt.json").read_text())
    producer["coordinate_identity"] = runner.array_identity({"anchors": np.arange(8) + 1, "mask": np.ones((8, 1), bool)})
    runner.finish(wrong, producer)
    with pytest.raises(ValueError, match="coordinate/target/mask"):
        runner.load_grid(historical, protocol, runner.sha(pp), "historical")


def test_consumed_input_binding_rejects_same_protocol_different_bytes(runner, tmp_path):
    p = tmp_path / "historic.npz"
    p.write_bytes(b"offsets-before-selection")
    receipt = {"input_sha256": {str(p): runner.sha(p)}}
    runner.require_consumed_input(receipt, p)
    p.write_bytes(b"different-offsets-after-selection")
    with pytest.raises(ValueError, match="did not consume"):
        runner.require_consumed_input(receipt, p)
