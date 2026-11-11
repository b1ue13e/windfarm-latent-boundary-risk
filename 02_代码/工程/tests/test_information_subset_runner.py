import argparse
import importlib.util
import json
from repo_paths import Path, repository_root
from types import SimpleNamespace

import numpy as np
import pytest


@pytest.fixture
def runner():
    path = Path(repository_root()) / "scripts/run_information_subset_study.py"
    spec = importlib.util.spec_from_file_location("information_subset_runner_test", path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class TinyQuantile:
    def fit(self, x, y):
        self.value = float(np.quantile(y, .9))
        return self

    def predict(self, x):
        return np.full(len(x), self.value)


def test_task_grid_frozen_1480_fits_and_shared_budgets(runner):
    cfg = dict(conditions={k: {} for k in ["pitch_withheld", "fresh", "delay1", "delay2", "delay3", "delay6_stress"]},
               seeds=list(range(201, 206)), pressure_subsets=["Common", "P1", "WP1", "WP6", "WP36", "WPQ36"],
               budgets=[10000, 40000, 120000, 360000], pressure_budgets=[120000, 360000])
    table = runner.tasks(cfg)
    assert len(table) == 550
    assert sum(len(t["budgets"]) for t in table if t["estimator"] != "Persistence") == 1480
    assert sum(t["estimator"] == "Persistence" for t in table) == 30


def test_historical_choice_precedes_eval_and_binds_actual_bytes(runner, tmp_path, monkeypatch):
    cfg = dict(conditions={"pitch_withheld": dict(delay_steps=0, pitch_available=False)}, seeds=[201, 202],
               budgets=[10, 20], pressure_budgets=[20], pressure_subsets=["P1"], selection_first_anchor=400,
               offset_quantiles=[.9, .925, .95, .975, .99], n_boot=200, bootstrap_seed=42,
               historical_rule="no evaluation access", mlp={})
    pp = tmp_path / "protocol.json"
    runner.save(pp, cfg)
    prep = tmp_path / "prepared"
    prep.mkdir()
    for name in ["output_manifest.json", "physical_channels.npy", "policy_fit_forecast.npz", "calibration_forecast.npz", "development_evaluation_forecast.npz"]:
        (prep / name).write_bytes(b"immutable synthetic fixture")
    m = SimpleNamespace(learner=lambda *args: TinyQuantile())
    monkeypatch.setattr(runner, "parent", lambda cfg: (m, prep, None, {"learner": {}}))
    monkeypatch.setattr(runner, "subset_grid", lambda: {"P1": ((1,), 1)})
    monkeypatch.setattr(runner, "PinballMLP", lambda *args: TinyQuantile())

    def fake_stage(m, prepared, data, name, condition):
        anchors = np.arange(100, 700) if name == "calibration" else np.arange(1000, 1300)
        n = len(anchors)
        s = (np.arange(n) % 81).astype(float).reshape(n, 1)
        x = np.full((n, 148), 15, dtype=np.float32)
        return dict(anchors=anchors, forecast=np.full((n, 1), 20.), true=20 - s,
                    mask=np.ones((n, 1), bool), shortfall=s, X=x,
                    identity={"anchors": anchors.tolist(), "target_fixture": name})

    monkeypatch.setattr(runner, "stage_data", fake_stage)
    out = tmp_path / "results"
    args = argparse.Namespace(protocol=pp, output=out, task_index=0)
    with pytest.raises(FileNotFoundError):
        runner.evaluate(args, cfg)
    for i in range(len(runner.tasks(cfg))):
        args.task_index = i
        runner.historical(args, cfg)
    assert not (out / "evaluate").exists()
    runner.choose(args, cfg)
    choice = json.loads((out / "choose/choices.json").read_text())
    assert choice["uses_evaluation"] is False
    for i in range(len(runner.tasks(cfg))):
        args.task_index = i
        runner.evaluate(args, cfg)
    groups, inputs, detail = runner.load_groups(args, cfg, "evaluate")
    assert len(groups) == 2
    assert groups[0]["costs"].shape[:2] == (2, 15)
    meta = out / "evaluate/0/metadata.json"
    meta.write_text("changed", encoding="utf-8")
    with pytest.raises(ValueError, match="Archived bytes"):
        runner.load_groups(args, cfg, "evaluate")


def test_persistence_last_arrived_power_and_missing_fallback(runner):
    x = np.zeros((2, 148), np.float32)
    x[:, 4 + 36 + 35 - 6] = [30, np.nan]
    pred = runner.raw_predict(None, x, np.array([[100.], [100.]]),
                              dict(estimator="Persistence", delay_steps=6), np.arange(4))
    np.testing.assert_array_equal(pred, [70, 0])
