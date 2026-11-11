import ast
import importlib.util
from repo_paths import Path, repository_root

import numpy as np

PATH = Path(__file__).parents[1] / "scripts/run_state_calibration_controls.py"
SPEC = importlib.util.spec_from_file_location("controls_runner", PATH)
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def test_original_common_and_budget_use_frozen_indices_and_clipping_order():
    raw = {c: np.array([[0., 5.]]) for c in runner.CELLS}
    offsets = {c: np.array([-.5, 1., 2., 3., 4.]) for c in runner.CELLS}
    choices = {"HGB:" + c: dict(q_index=0 if c in ("F", "O6", "OP6") else 2) for c in runner.CELLS}
    shifts = {f"{name}|{p}|{z}": dict(delta_kw=-1. if p == 1 else 2.)
              for name, _, _ in runner.STATE_PAIRS for p in range(5) for z in range(5)}
    out = runner.actions_for(raw, offsets, shifts, choices, "HGB", 1)
    assert len(out) == 18
    assert np.array_equal(out["Original|F"], [[0., 4.5]])
    assert np.array_equal(out["Original|FZ"], [[2., 7.]])
    assert np.array_equal(out["Original|Match_fresh_state"], [[2., 6.5]])
    assert np.array_equal(out["Common|F"], [[1., 6.]])
    assert np.array_equal(out["Common|Match_fresh_state"], [[0., 5.]])
    # Input choices/constants are unchanged by scoring, including another future batch.
    other = runner.actions_for({c: v + 100 for c, v in raw.items()}, offsets, shifts, choices, "HGB", 1)
    assert np.array_equal(other["Common|Match_fresh_state"], [[100., 105.]])
    assert shifts["fresh_state|1|1"]["delta_kw"] == -1


def test_no_learning_fit_call_and_history_reads_only_historical_raw_phases():
    tree = ast.parse(PATH.read_text(encoding="utf-8"))
    assert not any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "fit" for n in ast.walk(tree))
    history = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "history")
    reads = [n for n in ast.walk(history) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "load_raw"]
    assert {n.args[-1].value for n in reads} == {"offset", "selection"}
