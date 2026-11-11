import argparse
import importlib.util
import json
from repo_paths import Path, repository_root

import numpy as np
import pytest

SPEC = importlib.util.spec_from_file_location("state_pilot", Path(__file__).parents[1] / "scripts/run_state_measurement_pilot.py")
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


class ConstantQuantile:
    def fit(self, x, y):
        self.value = float(np.quantile(y, .9))
        return self

    def predict(self, x):
        return np.full(len(x), self.value)


def test_grid_is_60_model_fits_and_10_simple_instances():
    grid = runner.tasks({"seeds": list(range(201, 206))})
    assert len(grid) == 70
    assert len([t for t in grid if t["estimator"] != "CONTROL"]) == 60
    assert grid[0] == dict(estimator="HGB", cell="F", seed=201)
    assert grid[30] == dict(estimator="MLP", cell="F", seed=201)
    assert all(sum(t == other for other in grid) == 1 for t in grid)


def test_relative_cli_protocol_has_bound_receipt(tmp_path):
    protocol = Path("experiments/state_measurement_pilot_20261020/protocol.json")
    args = argparse.Namespace(output=tmp_path / "run", protocol=protocol, stage="prepare", task=-1)
    rec = runner.begin(args, [])
    assert rec["protocol_sha256"] == runner.sha(protocol)
    assert protocol.as_posix() in rec["source_sha256"] or str(protocol) in rec["source_sha256"]


def test_historical_fit_keeps_missing_pitch_rows_and_never_reads_evaluation(tmp_path, monkeypatch):
    protocol = Path("experiments/state_measurement_pilot_20261020/protocol.json")
    cfg = json.loads(protocol.read_text(encoding="utf-8"))
    prep = tmp_path / "prepared"
    prep.mkdir()
    (prep / "manifest.json").write_text("{}")
    data = np.ones((1000, 2, 4), dtype=np.float32)
    data[40:250, :, 3] = np.nan
    np.save(prep / "physical_channels.npy", data)
    for name, lo, hi in (("fit", 40, 250), ("offset", 300, 500), ("selection", 600, 800)):
        a = np.arange(lo, hi)
        target, primary = runner.populations(data, a)
        s = np.tile((a % 17)[:, None], (1, 2)).astype(float)
        np.savez(prep / f"{name}.npz", anchors=a, forecast=np.ones_like(s) * 30,
                 shortfall=s, target_mask=target, primary_mask=primary)
    monkeypatch.setattr(runner, "verify", lambda *args: {})
    monkeypatch.setattr(runner, "learner", lambda *args: ConstantQuantile())
    for task in (0, 5):  # F/FZ same seed, including all missing-Z training rows
        args = argparse.Namespace(base=tmp_path, output=tmp_path / "fits" / str(task),
                                  protocol=protocol, task=task, stage="fit")
        runner.fit(args, cfg)
        assert len(np.load(args.output / "fit_indices.npy")) == 420
        assert (args.output / "selection_blocks.npz").is_file()
    assert np.array_equal(np.load(tmp_path / "fits/0/fit_indices.npy"), np.load(tmp_path / "fits/5/fit_indices.npy"))
    assert not (tmp_path / "evaluation").exists()


def test_simple_control_uses_issue_power_and_keeps_target_out():
    d = np.ones((60, 2, 4))
    d[40, 0, 1] = -2
    d[40, 1, 1] = np.nan
    z = dict(anchors=np.array([40]), forecast=np.array([[10., 10.]]))
    assert np.array_equal(runner.control(d, z, "Persistence", None), [[12, 0]])
    assert np.array_equal(runner.control(d, z, "Global", 4), [[4, 4]])


def test_no_historical_choice_never_opens_evaluation(tmp_path, monkeypatch, capsys):
    cfg = {"seeds": list(range(201, 206))}
    frozen = tmp_path / "selection"
    frozen.mkdir()
    (frozen / "historical_choices.json").write_text(json.dumps(dict(choices={"HGB:F": {"q_index": None}})))
    monkeypatch.setattr(runner, "verify", lambda *args: {})
    monkeypatch.setattr(runner, "begin", lambda *args: pytest.fail("Must not create evaluation outputs"))
    args = argparse.Namespace(base=tmp_path, protocol=tmp_path / "protocol.json", task=0)
    runner.evaluate(args, cfg)
    assert "NO_HISTORICAL_CHOICE" in capsys.readouterr().out


def test_failed_baseline_blocks_evaluation(tmp_path, monkeypatch):
    cfg = {"seeds": list(range(201, 206))}
    frozen = tmp_path / "selection"
    frozen.mkdir()
    (frozen / "historical_choices.json").write_text(json.dumps(dict(
        choices={"HGB:F": {"q_index": 0}}, Cstar=5,
        baseline_adequacy={"HGB": {"status": "BASELINE_ADEQUACY_UNRESOLVED_STOP_PRIMARY_RECIPE"}})))
    monkeypatch.setattr(runner, "verify", lambda *args: {})
    args = argparse.Namespace(base=tmp_path, protocol=tmp_path / "protocol.json", task=0)
    with pytest.raises(ValueError, match="baseline gate"):
        runner.evaluate(args, cfg)
