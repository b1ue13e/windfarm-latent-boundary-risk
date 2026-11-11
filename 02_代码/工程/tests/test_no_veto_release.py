"""Unit tests for windfarm_moe.no_veto_release (EM1_008_Z no-veto ablation)."""
from __future__ import annotations

from collections.abc import Mapping
import copy
import json
from typing import Any

import numpy as np
import pytest

import windfarm_moe.no_veto_release as nvr
from windfarm_moe.no_veto_release import no_veto_actions, select_major_leaf
import windfarm_moe.release_gate as rg


class _ForbiddenTargetMaskBank(Mapping):
    """Bank wrapper that raises if target, shortfall, mask, or tree features are accessed."""

    FORBIDDEN_KEYS = frozenset({"target", "shortfall", "mask", "current_features", "feedback_features"})

    def __init__(self, payload: dict[str, Any]):
        self._payload = payload

    def __getitem__(self, key: str) -> Any:
        if key in self.FORBIDDEN_KEYS:
            raise AssertionError(f"Forbidden access to bank[{key!r}] in no_veto_actions")
        return self._payload[key]

    def __iter__(self):
        return iter(self._payload)

    def __len__(self) -> int:
        return len(self._payload)

    def __contains__(self, key: object) -> bool:
        return key in self._payload


class _PoisonedTree:
    """Tree stub that fails immediately if apply or predict is called."""

    def apply(self, *args: Any, **kwargs: Any) -> Any:
        raise AssertionError("no_veto_release must never evaluate tree.apply on evaluation inputs")

    def predict(self, *args: Any, **kwargs: Any) -> Any:
        raise AssertionError("no_veto_release must never evaluate tree.predict on evaluation inputs")


def _make_gate_model(
    snapshot: str,
    leaf_alphas: dict[Any, Any],
    leaf_cells: dict[Any, Any],
    *,
    status: str = "FITTED_OK",
    fallback_to_safe: bool = False,
    cut_anchor: int | None = None,
    enabled_anchor: int | None = None,
    episode_start: int | None = None,
    extra_fields: dict[str, Any] | None = None,
) -> dict[str, Any]:
    default_cuts = {"C": (29376, 29384), "E": (29808, 29816), "D": (30233, 30240)}
    def_cut, def_en = default_cuts[snapshot]
    c_anchor = def_cut if cut_anchor is None else cut_anchor
    e_anchor = def_en if enabled_anchor is None else enabled_anchor
    ep_start = def_en if episode_start is None else episode_start

    stats: dict[Any, Any] = {}
    total_cells = 0
    for k, n_c in leaf_cells.items():
        alpha_v = leaf_alphas.get(k, 0.0)
        stats[k] = dict(
            alpha=alpha_v if isinstance(alpha_v, (int, float)) else 0.0,
            alpha_max=1.0,
            chosen_kink=alpha_v if isinstance(alpha_v, (int, float)) else 0.0,
            cap_binding=False,
            repaired_toward_zero=False,
            penalized_objective_kwh=42.0,
            actual_C_kwh=42.0,
            actual_U_kwh=0.4,
            actual_V_rate=0.03,
            safe_C_kwh=42.5,
            safe_U_kwh=0.41,
            safe_V_rate=0.032,
            subgradient_lower_bound_kwh=42.0,
            subgradient_gap_kwh=0.0,
            leaf_optimality_certified=True,
            n_cells=n_c,
        )
        if isinstance(n_c, (int, np.integer)) and not isinstance(n_c, bool):
            total_cells += int(n_c)

    model: dict[str, Any] = dict(
        schema="release-gate-v1",
        recipe_id=8,
        kind="GATE",
        arm="Z",
        seed=201,
        vintage="outer",
        vintage_start_anchor=28944,
        snapshot=snapshot,
        cut_anchor=c_anchor,
        enabled_anchor=e_anchor,
        episode_start=ep_start,
        status=status,
        fallback_to_safe=fallback_to_safe,
        alpha=0.0 if fallback_to_safe or status == "UNTRAINED_ANCHOR" else None,
        valid_fit_cells=total_cells,
        selected_issue_count=432,
        n_leaves=len(stats),
        tree=_PoisonedTree(),
        leaf_alphas=dict(leaf_alphas),
        leaf_stats=stats,
        # Distractor evaluation leaf share fields that select_major_leaf must NEVER use:
        leaf_support={"1": 10, "2": 999999, "5": 888888},
        evaluation_leaf_share={"1": 0.01, "2": 0.99, "5": 0.99},
    )
    if extra_fields:
        model.update(extra_fields)
    return model


def test_select_major_leaf_picks_historical_max_not_alpha_max_or_eval_share_and_preserves_input():
    # Leaf 2 has smaller alpha (0.25) and tiny distractor evaluation share,
    # while Leaf 5 has larger alpha (0.95) and huge distractor evaluation share,
    # but Leaf 2 has the largest historical n_cells (150000 > 30000 > 2000).
    model = _make_gate_model(
        "D",
        leaf_alphas={"1": 0.80, "2": 0.25, "5": 0.95},
        leaf_cells={"1": 2000, "2": 150000, "5": 30000},
    )
    orig_tree = model["tree"]
    before_dict = {k: copy.deepcopy(v) for k, v in model.items() if k != "tree"}

    res = select_major_leaf(model)
    assert res["alpha"] == 0.25
    assert res["leaf_id"] == 2
    assert res["historical_cells"] == 150000
    assert isinstance(res["reason"], str) and len(res["reason"]) > 0

    after_dict = {k: copy.deepcopy(v) for k, v in model.items() if k != "tree"}
    assert after_dict == before_dict
    assert model["tree"] is orig_tree


def test_select_major_leaf_tie_breaks_by_smallest_integer_leaf_id():
    # String keys "10" and "2" tie at 50000 historical cells.
    # Lexicographically "10" < "2", but as integer leaf IDs 2 < 10!
    model = _make_gate_model(
        "E",
        leaf_alphas={"10": 0.75, "2": 0.35, "7": 0.90},
        leaf_cells={"10": 50000, "2": 50000, "7": 49999},
    )
    res = select_major_leaf(model)
    assert res["leaf_id"] == 2
    assert res["alpha"] == 0.35
    assert res["historical_cells"] == 50000
    assert "TIE" in res["reason"]


def test_select_major_leaf_fallback_untrained_and_all_zero_alphas():
    # 1. fallback_to_safe=True
    fb_model = _make_gate_model(
        "C",
        leaf_alphas={},
        leaf_cells={},
        status="FITTED_OK",
        fallback_to_safe=True,
        extra_fields={"valid_fit_cells": 120, "n_leaves": 0},
    )
    res_fb = select_major_leaf(fb_model)
    assert res_fb["alpha"] == 0.0
    assert res_fb["historical_cells"] == 120
    assert res_fb["leaf_id"] is None

    # 2. status == UNTRAINED_ANCHOR with fallback_to_safe=False
    untrained_model = _make_gate_model(
        "C",
        leaf_alphas={},
        leaf_cells={},
        status="UNTRAINED_ANCHOR",
        fallback_to_safe=False,
        extra_fields={"valid_fit_cells": 0, "n_leaves": 0},
    )
    res_un = select_major_leaf(untrained_model)
    assert res_un["alpha"] == 0.0
    assert res_un["historical_cells"] == 0
    assert res_un["leaf_id"] is None
    assert res_un["reason"] == "UNTRAINED_ANCHOR"

    # 3. Normal GATE model where all leaf alphas are 0.0
    zero_model = _make_gate_model(
        "C",
        leaf_alphas={1: 0.0, 2: 0.0},
        leaf_cells={1: 56617, 2: 1100},
    )
    res_zero = select_major_leaf(zero_model)
    assert res_zero["alpha"] == 0.0
    assert res_zero["leaf_id"] == 1
    assert res_zero["historical_cells"] == 56617
    assert "ZERO" in res_zero["reason"]


@pytest.mark.parametrize(
    "mutator,err_match",
    [
        (lambda m: m["leaf_alphas"].update({"1": -0.01}), "within \\[0, 1\\]"),
        (lambda m: m["leaf_alphas"].update({"1": 1.0001}), "within \\[0, 1\\]"),
        (lambda m: m["leaf_alphas"].update({"1": float("nan")}), "within \\[0, 1\\]"),
        (lambda m: m["leaf_alphas"].update({"1": float("inf")}), "within \\[0, 1\\]"),
        (lambda m: m["leaf_alphas"].update({"1": True}), "finite float"),
        (lambda m: m["leaf_stats"]["1"].update({"alpha": 0.99}), "does not match leaf_alphas"),
        (lambda m: m["leaf_stats"]["1"].update({"n_cells": 0}), "positive training support"),
        (lambda m: m["leaf_stats"]["1"].update({"n_cells": -5}), "must be >= 0"),
        (lambda m: m["leaf_stats"]["1"].update({"n_cells": 12.5}), "finite integer"),
        (lambda m: m["leaf_stats"]["1"].update({"n_cells": float("nan")}), "finite integer"),
        (lambda m: m["leaf_stats"]["1"].update({"n_cells": True}), "boolean"),
        (lambda m: m["leaf_stats"]["1"].update({"actual_C_kwh": float("inf")}), "must be finite"),
        (lambda m: m["leaf_alphas"].pop("2"), "do not match leaf_stats keys"),
        (lambda m: m["leaf_stats"].pop("2"), "do not match leaf_stats keys"),
        (lambda m: (m["leaf_alphas"].clear(), m["leaf_stats"].clear()), "empty"),
        (lambda m: m.update({"valid_fit_cells": 999}), "valid_fit_cells"),
        (lambda m: m.update({"selected_issue_count": -1}), "selected_issue_count"),
    ],
)
def test_select_major_leaf_rejects_invalid_alpha_support_and_mismatched_keys(mutator, err_match):
    # Ensure invalid leaf 1 cannot be silently bypassed in favor of valid leaf 2
    model = _make_gate_model(
        "D",
        leaf_alphas={"1": 0.4, "2": 0.2},
        leaf_cells={"1": 1000, "2": 50000},
    )
    mutator(model)
    with pytest.raises(ValueError, match=err_match):
        select_major_leaf(model)


def test_no_veto_actions_schedule_boundaries_early_safe_and_no_d_backfill(monkeypatch):
    # Forbid calling predict_rule or fit_rule
    monkeypatch.setattr(rg, "predict_rule", lambda *a, **k: (_ for _ in ()).throw(AssertionError("predict_rule called")))
    monkeypatch.setattr(rg, "fit_rule", lambda *a, **k: (_ for _ in ()).throw(AssertionError("fit_rule called")))

    anchors = np.array(
        [
            28944,  # index 0: outer start (pre-C -> SAFE)
            29375,  # index 1: last training cut before C (pre-C -> SAFE)
            29383,  # index 2: 1 step before C enabled (pre-C -> SAFE)
            29384,  # index 3: C enabled start -> alpha_C = 0.25
            29807,  # index 4: in C -> alpha_C = 0.25
            29815,  # index 5: 1 step before E enabled -> alpha_C = 0.25
            29816,  # index 6: E enabled start -> alpha_E = 0.60
            30232,  # index 7: in E -> alpha_E = 0.60
            30239,  # index 8: 1 step before D enabled -> alpha_E = 0.60
            30240,  # index 9: D enabled start -> alpha_D = 0.85
            35272,  # index 10: evaluation end -> alpha_D = 0.85
        ],
        dtype=np.int64,
    )
    t_steps = anchors.size
    safe = np.stack([np.linspace(10.0, 20.0, t_steps), np.linspace(5.0, 15.0, t_steps)], axis=1)
    cost = np.stack([np.linspace(6.0, 16.0, t_steps), np.linspace(9.0, 25.0, t_steps)], axis=1)

    bank = dict(anchors=anchors, safe=safe, cost=cost)
    models = {
        "C": _make_gate_model("C", {"1": 0.25, "2": 0.90}, {"1": 40000, "2": 5000}),
        "E": _make_gate_model("E", {"3": 0.10, "4": 0.60}, {"3": 10000, "4": 80000}),
        "D": _make_gate_model("D", {"1": 0.85, "2": 0.05}, {"1": 120000, "2": 3000}),
    }
    models_copy = {
        k: {mk: copy.deepcopy(mv) for mk, mv in v.items() if mk != "tree"}
        for k, v in models.items()
    }

    actions, receipt = no_veto_actions(_ForbiddenTargetMaskBank(bank), models)

    # Independent hand calculation:
    expected = np.empty_like(safe)
    # Indices 0, 1, 2 (< 29384): exact SAFE.copy()
    expected[:3] = safe[:3].copy()
    # Indices 3, 4, 5 ([29384, 29816)): alpha_C = 0.25
    expected[3:6] = np.maximum(safe[3:6] + 0.25 * (cost[3:6] - safe[3:6]), 0.0)
    # Indices 6, 7, 8 ([29816, 30240)): alpha_E = 0.60
    expected[6:9] = np.maximum(safe[6:9] + 0.60 * (cost[6:9] - safe[6:9]), 0.0)
    # Indices 9, 10 (>= 30240): alpha_D = 0.85
    expected[9:] = np.maximum(safe[9:] + 0.85 * (cost[9:] - safe[9:]), 0.0)

    assert actions.tobytes() == expected.tobytes()
    assert actions[:3].tobytes() == safe[:3].tobytes()

    # Verify D does not backfill before 30240: mutating D's alpha only changes indices >= 9
    models_d_changed = copy.deepcopy(models)
    models_d_changed["D"]["leaf_alphas"]["1"] = 0.0
    models_d_changed["D"]["leaf_stats"]["1"]["alpha"] = 0.0
    actions_d0, _ = no_veto_actions(bank, models_d_changed)
    assert actions_d0[:9].tobytes() == actions[:9].tobytes()
    assert not np.array_equal(actions_d0[9:], actions[9:])

    # Verify input models were not modified
    for k, v in models.items():
        assert {mk: mv for mk, mv in v.items() if mk != "tree"} == models_copy[k]

    # Verify receipt is compact JSON-serializable and has expected summary statistics
    encoded = json.dumps(receipt, allow_nan=False)
    assert len(encoded) < 4096
    assert "actions" not in receipt
    expected_mean_alpha = (3 * 0.0 + 3 * 0.25 + 3 * 0.60 + 2 * 0.85) / 11.0
    assert np.isclose(receipt["mean_alpha"], expected_mean_alpha, rtol=0.0, atol=1e-15)
    assert receipt["snapshots"]["C"]["alpha"] == 0.25
    assert receipt["snapshots"]["C"]["leaf_id"] == 1
    assert receipt["snapshots"]["C"]["historical_cells"] == 40000
    assert receipt["snapshots"]["E"]["alpha"] == 0.60
    assert receipt["snapshots"]["E"]["leaf_id"] == 4
    assert receipt["snapshots"]["D"]["alpha"] == 0.85
    assert receipt["snapshots"]["D"]["leaf_id"] == 1


def test_target_and_mask_ignored_when_missing_or_corrupted():
    anchors = np.array([28944, 29384, 29816, 30240], dtype=np.int64)
    safe = np.array([[12.0, 8.0], [15.0, 9.0], [14.0, 7.0], [20.0, 11.0]], dtype=np.float64)
    cost = np.array([[10.0, 6.0], [11.0, 12.0], [9.0, 10.0], [13.0, 14.0]], dtype=np.float64)
    models = {
        "C": _make_gate_model("C", {1: 0.2}, {1: 1000}),
        "E": _make_gate_model("E", {1: 0.5}, {1: 2000}),
        "D": _make_gate_model("D", {1: 0.8}, {1: 3000}),
    }

    bank_clean = dict(anchors=anchors, safe=safe, cost=cost)
    bank_with_nan_targets = dict(
        anchors=anchors,
        safe=safe,
        cost=cost,
        target=np.full_like(safe, np.nan),
        shortfall=np.full_like(safe, -1e300),
        mask=np.zeros_like(safe, dtype=bool),
    )
    bank_with_alt_targets = dict(
        anchors=anchors,
        safe=safe,
        cost=cost,
        target=np.full_like(safe, 999999.0),
        shortfall=np.full_like(safe, 888888.0),
        mask=np.ones_like(safe, dtype=bool),
    )

    act0, rec0 = no_veto_actions(bank_clean, models)
    act1, rec1 = no_veto_actions(bank_with_nan_targets, models)
    act2, rec2 = no_veto_actions(bank_with_alt_targets, models)
    act3, rec3 = no_veto_actions(_ForbiddenTargetMaskBank(bank_with_nan_targets), models)

    assert act0.tobytes() == act1.tobytes() == act2.tobytes() == act3.tobytes()
    assert rec0 == rec1 == rec2 == rec3
    # Full grid is evaluated even when mask is all-False
    assert rec1["total_cells"] == 8
    assert rec1["snapshots"]["D"]["evaluated_cells"] == 2


def test_fair_floating_point_kernel_alpha0_alpha1_and_large_scale_cancellation():
    """Verify enabled segments use np.maximum(safe + alpha * (cost - safe), 0.0) rather than cost.copy()."""
    # Construct safe and cost where IEEE-754 float64 `safe + 1.0 * (cost - safe) != cost`
    # due to catastrophic cancellation in `cost - safe`:
    # Let safe = 1e16, cost = 0.1.
    # In float64, cost - safe = 0.1 - 1e16 = -1e16 (the 0.1 is below 1e16's ULP=2.0).
    # Then safe + 1.0 * (cost - safe) = 1e16 + (-1e16) = 0.0 != cost (0.1)!
    # A second cell: safe = 1e16 + 2.0, cost = 0.3 -> cost - safe = -1e16 - 2.0 -> sum = 0.0 != 0.3.
    safe_val = np.array([[10.0, 20.0], [12.0, 8.0], [1e16, 1e16 + 2.0], [1e16, 5.0]], dtype=np.float64)
    cost_val = np.array([[3.0, 25.0], [4.0, 19.0], [0.1, 0.3], [0.1, 9.0]], dtype=np.float64)

    # Confirm the IEEE-754 property on row 2:
    gate_formula_row2 = np.maximum(safe_val[2] + 1.0 * (cost_val[2] - safe_val[2]), 0.0)
    assert not np.array_equal(gate_formula_row2, cost_val[2])
    assert np.all(gate_formula_row2 == 0.0)

    anchors = np.array([28944, 29384, 29816, 30240], dtype=np.int64)
    bank = dict(anchors=anchors, safe=safe_val, cost=cost_val)
    # C has alpha=0.0, E has alpha=1.0, D has alpha=1.0
    models = {
        "C": _make_gate_model("C", {1: 0.0}, {1: 1000}),
        "E": _make_gate_model("E", {1: 1.0}, {1: 2000}),
        "D": _make_gate_model("D", {1: 1.0}, {1: 3000}),
    }

    actions, _ = no_veto_actions(bank, models)

    # Row 0 (28944 < 29384): pre-C SAFE.copy()
    assert actions[0].tobytes() == safe_val[0].tobytes()
    # Row 1 (29384 in C, alpha=0.0): np.maximum(safe + 0.0*(cost-safe), 0.0) == safe
    expected_row1 = np.maximum(safe_val[1] + 0.0 * (cost_val[1] - safe_val[1]), 0.0)
    assert actions[1].tobytes() == expected_row1.tobytes()
    assert np.all(actions[1] == safe_val[1])
    # Row 2 (29816 in E, alpha=1.0): must match GATE kernel formula, NOT cost.copy()!
    assert actions[2].tobytes() == gate_formula_row2.tobytes()
    assert actions[2].tobytes() != cost_val[2].tobytes()
    # Row 3 (30240 in D, alpha=1.0): must also match GATE kernel formula
    expected_row3 = np.maximum(safe_val[3] + 1.0 * (cost_val[3] - safe_val[3]), 0.0)
    assert actions[3].tobytes() == expected_row3.tobytes()


@pytest.mark.parametrize(
    "bad_case,err_match",
    [
        ("bank_start_too_early", "starting anchor .* >= 28944"),
        ("missing_enabled_anchor", "missing required field 'enabled_anchor'"),
        ("missing_episode_start", "missing required field 'episode_start'"),
        ("missing_cut_anchor", "missing required field 'cut_anchor'"),
        ("wrong_c_enabled", "Snapshot 'C' enabled_anchor"),
        ("wrong_e_enabled", "Snapshot 'E' enabled_anchor"),
        ("wrong_d_episode_start", "Snapshot 'D' enabled_anchor"),
        ("wrong_c_cut", "Snapshot 'C' cut_anchor=29377 must equal 29376"),
        ("wrong_e_cut", "Snapshot 'E' cut_anchor=29809 must equal 29808"),
        ("wrong_d_cut", "Snapshot 'D' cut_anchor=30234 must equal 30233"),
        ("explicit_last_cut_unmatured", "violates \\+7 < 30240|must be < cut_anchor"),
        ("explicit_last_cut_at_cut", "must be < cut_anchor"),
        ("missing_snapshot_e", "Missing required outer snapshot model 'E'"),
    ],
)
def test_no_veto_actions_rejects_bad_timing_and_missing_fields(bad_case: str, err_match: str):
    anchors = np.array([28944, 29375, 29384, 29807, 29816, 30232, 30240], dtype=np.int64)
    safe = np.ones((anchors.size, 2), dtype=np.float64) * 10.0
    cost = np.ones((anchors.size, 2), dtype=np.float64) * 8.0
    bank = dict(anchors=anchors, safe=safe, cost=cost)
    models = {
        "C": _make_gate_model("C", {1: 0.1}, {1: 1000}),
        "E": _make_gate_model("E", {1: 0.2}, {1: 2000}),
        "D": _make_gate_model("D", {1: 0.3}, {1: 3000}),
    }

    if bad_case == "bank_start_too_early":
        bank["anchors"] = np.array([28943, 29384, 29816, 30240], dtype=np.int64)
        bank["safe"] = safe[:4]
        bank["cost"] = cost[:4]
    elif bad_case == "missing_enabled_anchor":
        models["C"].pop("enabled_anchor")
    elif bad_case == "missing_episode_start":
        models["E"].pop("episode_start")
    elif bad_case == "missing_cut_anchor":
        models["D"].pop("cut_anchor")
    elif bad_case == "wrong_c_enabled":
        models["C"]["enabled_anchor"] = 29385
    elif bad_case == "wrong_e_enabled":
        models["E"]["enabled_anchor"] = 29815
    elif bad_case == "wrong_d_episode_start":
        models["D"]["episode_start"] = 30241
    elif bad_case == "wrong_c_cut":
        models["C"]["cut_anchor"] = 29377
    elif bad_case == "wrong_e_cut":
        models["E"]["cut_anchor"] = 29809
    elif bad_case == "wrong_d_cut":
        models["D"]["cut_anchor"] = 30234
    elif bad_case == "explicit_last_cut_unmatured":
        models["D"]["last_training_cut"] = 30233
    elif bad_case == "explicit_last_cut_at_cut":
        models["C"]["lasttrainingcut"] = 29376
    elif bad_case == "missing_snapshot_e":
        models.pop("E")

    with pytest.raises((ValueError, KeyError), match=err_match):
        no_veto_actions(bank, models)


def test_real_frozen_em1_008_z_joblib_models_compat():
    from pathlib import Path
    import joblib

    root = Path(__file__).resolve().parents[1]
    model_dir = root / "experiments/endpoint_match_20261025/frozen_weights/results/campaign/models/outer"
    if not model_dir.exists():
        pytest.skip("Frozen joblib models not present locally")

    models = {
        snap: joblib.load(model_dir / snap / "Z_seed201" / "EM008.joblib")
        for snap in ("C", "E", "D")
    }
    models_before = {
        snap: {k: copy.deepcopy(v) for k, v in m.items() if k != "tree"}
        for snap, m in models.items()
    }

    sel_c = select_major_leaf(models["C"])
    sel_e = select_major_leaf(models["E"])
    sel_d = select_major_leaf(models["D"])
    assert sel_c["leaf_id"] == 1 and sel_c["historical_cells"] == 56617 and sel_c["alpha"] == 0.0
    assert sel_d["leaf_id"] == 1 and sel_d["historical_cells"] == 170443
    assert np.isclose(sel_d["alpha"], 0.43132465125830866, rtol=0.0, atol=1e-15)

    anchors = np.array([28944, 29375, 29384, 29807, 29816, 30232, 30240, 30241], dtype=np.int64)
    safe = np.full((anchors.size, 3), 20.0, dtype=np.float64)
    cost = np.full((anchors.size, 3), 14.0, dtype=np.float64)
    bank = _ForbiddenTargetMaskBank(dict(anchors=anchors, safe=safe, cost=cost))

    actions, receipt = no_veto_actions(bank, models)
    assert actions.shape == safe.shape
    assert np.all(actions[:2] == 20.0)
    assert np.allclose(actions[6:], np.maximum(20.0 + sel_d["alpha"] * (14.0 - 20.0), 0.0), rtol=0.0, atol=0.0)
    json.dumps(receipt, allow_nan=False)

    for snap, m in models.items():
        assert {k: v for k, v in m.items() if k != "tree"} == models_before[snap]

