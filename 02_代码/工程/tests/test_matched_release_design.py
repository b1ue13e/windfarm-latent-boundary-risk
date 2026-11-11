"""Unit tests for windfarm_moe.matched_release_design."""
from __future__ import annotations

import copy
import json

import numpy as np
import pytest

from windfarm_moe.matched_release_design import (
    EXPECTED_NEW_ALIASES,
    EXPECTED_NEW_COMPARISONS,
    EXPECTED_NEW_POLICIES,
    EXPECTED_NOMINAL_COORDINATES,
    EXPECTED_PARENT_ALIASES,
    EXPECTED_PARENT_COMPARISONS,
    EXPECTED_PARENT_POLICIES,
    EXPECTED_TOTAL_ALIASES,
    EXPECTED_TOTAL_COMPARISONS,
    EXPECTED_TOTAL_POLICIES,
    POPULATION_WINDOWS,
    SNAPSHOTS,
    SNAPSHOT_ORDER,
    STATIC_RECIPE_IDS,
    VALIDATION_WINDOWS,
    VINTAGE_START_ANCHOR,
    build_family,
    fit_snapshot_models,
    policy_name,
    prediction_view,
    scheduled_actions,
)
from windfarm_moe.release_bank import RELEASE_LAG_STEPS
from windfarm_moe.release_gate import build_recipes, fit_rule
from windfarm_moe.residual_meta import META_ARMS


def _make_vintage_bank(vintage: str = "inner", nodes: int = 8, seed: int = 201) -> dict:
    rng = np.random.default_rng(seed)
    if vintage == "inner":
        anchors = np.r_[
            np.arange(28087, 28107),
            np.arange(28510, 28519),
            np.arange(28526, 28536),
            np.arange(28930, 28937),
            np.arange(28944, 28954),
            np.arange(29370, 29376),
            np.arange(29384, 29394),
            np.arange(30225, 30233),
            np.arange(30240, 30250),
        ].astype(np.int64)
    else:
        anchors = np.r_[
            np.arange(28944, 28964),
            np.arange(29368, 29376),
            np.arange(29384, 29394),
            np.arange(29800, 29808),
            np.arange(29816, 29826),
            np.arange(30225, 30233),
            np.arange(30240, 30250),
        ].astype(np.int64)

    n = int(anchors.size)
    safe = rng.uniform(5.0, 25.0, size=(n, nodes))
    delta = rng.uniform(-4.0, 3.0, size=(n, nodes))
    cost = np.maximum(safe + delta, 0.1)
    ref = rng.uniform(2.0, 15.0, size=(n, nodes))
    width = rng.uniform(0.5, 5.0, size=(n, nodes))
    cur = np.stack([ref, safe, cost, cost - safe, width], axis=-1)
    fb_extra = rng.normal(0.0, 0.5, size=(n, nodes, 6))
    fb = np.concatenate([cur, fb_extra], axis=-1)
    shortfall = np.maximum(safe - 2.0 + 3.0 * (cur[:, :, 3] > -0.5) + rng.uniform(-1.0, 4.0, size=(n, nodes)), 0.0)
    mask = np.ones((n, nodes), dtype=bool)
    mask[0, 0] = False
    shortfall[~mask] = np.nan

    return dict(
        anchors=anchors,
        safe=safe,
        cost=cost,
        current_features=cur,
        feedback_features=fb,
        shortfall=shortfall,
        mask=mask,
        metadata=dict(arm="P", seed=seed, vintage=vintage),
    )


def _make_constructed_parent(use_integer_indices: bool = True) -> dict:
    base_names = ["REF", "R0182_P", "BR009_P", "BR009_Z", "MC049_C", "MC049_P", "MC049_Z"]
    gr_names = [f"GR{rid:03d}_{arm}" for rid in range(24) for arm in META_ARMS]
    filler_count = EXPECTED_PARENT_POLICIES - len(base_names) - len(gr_names)
    filler_names = [f"NR{i:04d}" for i in range(filler_count)]
    policy_names = base_names + filler_names + gr_names
    assert len(policy_names) == EXPECTED_PARENT_POLICIES

    comps = []
    idx = 1
    while len(comps) < EXPECTED_PARENT_COMPARISONS:
        left = idx % EXPECTED_PARENT_POLICIES
        right = (idx // EXPECTED_PARENT_POLICIES) % EXPECTED_PARENT_POLICIES
        if left != right:
            pair = [left, right] if use_integer_indices else [policy_names[left], policy_names[right]]
            comps.append(pair)
        idx += 1

    aliases = []
    for k in range(EXPECTED_PARENT_ALIASES):
        left, right = k + 1, 0
        aliases.append([left, right] if use_integer_indices else [policy_names[left], policy_names[right]])

    return dict(
        policy_names=policy_names,
        available=[True] * EXPECTED_PARENT_POLICIES,
        family_definition=dict(
            policy_names=policy_names,
            comparisons=comps,
            frozen_aliases=aliases,
        ),
    )


def test_constants_and_strict_7_step_maturity_gaps():
    assert SNAPSHOTS == {
        "inner": {"A": (28519, 28526), "B": (28937, 28944), "C": (29376, 29384), "D": (30233, 30240)},
        "outer": {"C": (29376, 29384), "E": (29808, 29816), "D": (30233, 30240)},
    }
    assert VALIDATION_WINDOWS == {
        "inner": {"A": (28526, 28937), "B": (28944, 29376), "C": (29384, 30233)},
        "outer": {"C": (29384, 29808), "E": (29816, 30233)},
    }
    assert VINTAGE_START_ANCHOR == {"inner": 28087, "outer": 28944}
    assert POPULATION_WINDOWS == {
        "inner": (28087, 28937),
        "outer": (28944, 30233),
        "evaluate": (30240, 35273),
    }
    for v, snaps in SNAPSHOTS.items():
        for key, (cut, enabled) in snaps.items():
            # Last anchor < cut is at most cut - 1; (cut - 1) + 7 < enabled <=> cut + 7 <= enabled
            assert (cut - 1) + RELEASE_LAG_STEPS < enabled, f"{v}:{key} violates +7 maturity"
    # Verify outer has exactly two validation windows C and E
    assert tuple(VALIDATION_WINDOWS["outer"].keys()) == ("C", "E")
    assert tuple(VALIDATION_WINDOWS["inner"].keys()) == ("A", "B", "C")


@pytest.mark.parametrize("vintage,expected_snaps", [("inner", ("A", "B", "C", "D")), ("outer", ("C", "E", "D"))])
def test_fit_snapshot_models_returns_all_24_recipes_without_filtering(vintage: str, expected_snaps: tuple[str, ...]):
    bank = _make_vintage_bank(vintage=vintage, nodes=8)
    models, receipts = fit_snapshot_models(bank, vintage=vintage, seed=201, min_samples_leaf=16)
    expected_keys = {(s, rid) for s in expected_snaps for rid in range(24)}
    assert set(models.keys()) == expected_keys
    assert set(receipts.keys()) == expected_keys
    assert len(models) == 24 * len(expected_snaps)

    # Even if shortfall is all zeros or valid rows are smaller than min_samples_leaf, all 24*snaps are returned
    sparse_bank = copy.deepcopy(bank)
    models_hi, receipts_hi = fit_snapshot_models(sparse_bank, vintage=vintage, seed=201, min_samples_leaf=999999)
    assert set(models_hi.keys()) == expected_keys
    assert set(receipts_hi.keys()) == expected_keys
    for s in expected_snaps:
        for rid in range(8, 24):
            assert models_hi[s, rid]["fallback_to_safe"] is True
            assert models_hi[s, rid]["status"] == "UNTRAINED_ANCHOR"


def test_fit_snapshot_models_respects_vintage_start_and_excludes_pre_start_anchors():
    # Combined historical bank containing both inner [28087..) and outer [28944..) anchors
    combined = _make_vintage_bank(vintage="inner", nodes=4)
    outer_only = {
        k: (v[combined["anchors"] >= 28944].copy() if isinstance(v, np.ndarray) else copy.deepcopy(v))
        for k, v in combined.items()
    }
    # Corrupt pre-28944 rows in combined bank; outer vintage fit must ignore them completely
    corrupted = copy.deepcopy(combined)
    pre_outer = corrupted["anchors"] < 28944
    corrupted["shortfall"][pre_outer] = 999999.0

    models_comb, receipts_comb = fit_snapshot_models(corrupted, vintage="outer", seed=201, min_samples_leaf=8)
    models_out, receipts_out = fit_snapshot_models(outer_only, vintage="outer", seed=201, min_samples_leaf=8)

    for key in models_out:
        assert receipts_comb[key]["selected_issue_count"] == receipts_out[key]["selected_issue_count"]
        assert receipts_comb[key]["valid_fit_cells"] == receipts_out[key]["valid_fit_cells"]
        assert receipts_comb[key]["valid_row_sha256"] == receipts_out[key]["valid_row_sha256"]
        act_c, _ = scheduled_actions(outer_only, models_comb, "outer", key[1])
        act_o, _ = scheduled_actions(outer_only, models_out, "outer", key[1])
        np.testing.assert_array_equal(act_c, act_o)


@pytest.mark.parametrize("vintage", ["inner", "outer"])
@pytest.mark.parametrize("rid,field", [(0, "safe"), (1, "cost")])
def test_endpoints_exact_across_all_rows(vintage: str, rid: int, field: str):
    bank = _make_vintage_bank(vintage=vintage, nodes=6)
    bank["cost"][:] = 1e-12
    models, _ = fit_snapshot_models(bank, vintage=vintage, seed=201, min_samples_leaf=16)
    act, diag = scheduled_actions(bank, models, vintage=vintage, recipe_id=rid)
    assert act.tobytes() == bank[field].tobytes()
    json.dumps(diag, allow_nan=False)


def test_schedule_warmup_static_vs_learned_and_no_future_leakage_from_d():
    # Inner schedule: A enabled 28526, B 28944, C 29384, D 30240
    inner_bank = _make_vintage_bank(vintage="inner", nodes=2)
    inner_bank["anchors"] = np.array([28087, 28525, 28526, 28943, 28944, 29383, 29384, 30239, 30240, 30500], dtype=np.int64)
    for k in ("safe", "cost", "shortfall", "mask", "current_features", "feedback_features"):
        inner_bank[k] = inner_bank[k][:10]

    base_b = _make_vintage_bank(vintage="inner", nodes=4)
    models_inner = {}
    alphas_inner = {"A": 0.1, "B": 0.2, "C": 0.3, "D": 0.8}
    for key in SNAPSHOT_ORDER["inner"]:
        for rid in (2, 7):
            m, _ = fit_rule(base_b, 2, 201, slice(0, 20), 28526)
            m["alpha"] = alphas_inner[key] if rid == 7 else 0.1
            models_inner[key, rid] = m

    # Learned recipe 7: SAFE (alpha=0) before 28526, then A/B/C/D; D only acts at >= 30240
    act_learned, diag_learned = scheduled_actions(inner_bank, models_inner, "inner", 7)
    expected_alpha_learned = np.array([0.0, 0.0, 0.1, 0.1, 0.2, 0.2, 0.3, 0.3, 0.8, 0.8])[:, None]
    np.testing.assert_allclose(
        act_learned,
        inner_bank["safe"] + expected_alpha_learned * (inner_bank["cost"] - inner_bank["safe"]),
        rtol=0.0,
        atol=0.0,
    )

    # Mutating D model must not alter any prediction prior to 30240
    models_inner_mut = copy.deepcopy(models_inner)
    models_inner_mut["D", 7]["alpha"] = 0.99
    act_mut, _ = scheduled_actions(inner_bank, models_inner_mut, "inner", 7)
    np.testing.assert_array_equal(act_learned[:8], act_mut[:8])
    assert not np.array_equal(act_learned[8:], act_mut[8:])

    # Static recipe 2 (in 0..6): predicted on ALL rows including before first enabled anchor (no warmup displacement)
    act_static, _ = scheduled_actions(inner_bank, models_inner, "inner", 2)
    np.testing.assert_allclose(
        act_static,
        inner_bank["safe"] + 0.1 * (inner_bank["cost"] - inner_bank["safe"]),
        rtol=0.0,
        atol=0.0,
    )

    # Outer schedule: C enabled 29384, E 29816, D 30240
    outer_bank = _make_vintage_bank(vintage="outer", nodes=2)
    outer_bank["anchors"] = np.array([28944, 29383, 29384, 29815, 29816, 30239, 30240, 31000], dtype=np.int64)
    for k in ("safe", "cost", "shortfall", "mask", "current_features", "feedback_features"):
        outer_bank[k] = outer_bank[k][:8]

    models_outer = {}
    alphas_outer = {"C": 0.25, "E": 0.5, "D": 0.75}
    for key in SNAPSHOT_ORDER["outer"]:
        for rid in (3, 7):
            m, _ = fit_rule(base_b, 3, 201, slice(0, 20), 28526)
            m["alpha"] = alphas_outer[key] if rid == 7 else 0.25
            models_outer[key, rid] = m

    act_outer_learned, _ = scheduled_actions(outer_bank, models_outer, "outer", 7)
    expected_alpha_outer = np.array([0.0, 0.0, 0.25, 0.25, 0.5, 0.5, 0.75, 0.75])[:, None]
    np.testing.assert_allclose(
        act_outer_learned,
        outer_bank["safe"] + expected_alpha_outer * (outer_bank["cost"] - outer_bank["safe"]),
        rtol=0.0,
        atol=0.0,
    )
    act_outer_static, _ = scheduled_actions(outer_bank, models_outer, "outer", 3)
    np.testing.assert_allclose(
        act_outer_static,
        outer_bank["safe"] + 0.25 * (outer_bank["cost"] - outer_bank["safe"]),
        rtol=0.0,
        atol=0.0,
    )


def test_target_and_mask_disappear_during_prediction_and_diagnostics_compact_json():
    bank = _make_vintage_bank(vintage="inner", nodes=8)
    models, _ = fit_snapshot_models(bank, vintage="inner", seed=201, min_samples_leaf=16)

    # Remove shortfall and mask completely from prediction input bank
    pred_bank = {k: v for k, v in bank.items() if k not in ("shortfall", "mask")}
    assert not ({"shortfall", "mask", "anchors"} & set(prediction_view(bank).keys()))

    for rid in range(24):
        act_full, diag_full = scheduled_actions(bank, models, "inner", rid)
        act_notarget, diag_notarget = scheduled_actions(pred_bank, models, "inner", rid)
        np.testing.assert_array_equal(act_full, act_notarget)
        assert diag_full == diag_notarget
        # Ensure diagnostics are compact and JSON serializable without alpha_grid or shift_grid
        encoded = json.dumps(diag_notarget, allow_nan=False)
        assert isinstance(encoded, str)
        for snap_diag in diag_notarget.values():
            assert "alpha_grid" not in snap_diag
            assert "shift_grid" not in snap_diag
            assert "leaf_support" in snap_diag
            assert "mean_alpha" in snap_diag
            assert "min_alpha" in snap_diag
            assert "max_alpha" in snap_diag


def test_policy_name_and_build_family_dimensions_uniqueness_and_parent_preservation():
    assert policy_name("inner", 0, "P") == "EM0_000_P"
    assert policy_name("outer", 23, "Z") == "EM1_023_Z"

    parent_int = _make_constructed_parent(use_integer_indices=True)
    parent_str = _make_constructed_parent(use_integer_indices=False)

    names, avail, comps, aliases = build_family(parent_int)
    names_s, avail_s, comps_s, aliases_s = build_family(parent_str)
    assert (names, avail, comps, aliases) == (names_s, avail_s, comps_s, aliases_s)

    assert len(names) == EXPECTED_TOTAL_POLICIES == 1400
    assert len(set(names)) == 1400
    assert names[:EXPECTED_PARENT_POLICIES] == parent_int["policy_names"]
    assert avail == parent_int["available"]

    # Check exact order of 144 new roles: vintage (inner, outer), rid 0..23, arm C/P/Z
    expected_new_names = [
        f"EM{0 if v == 'inner' else 1}_{rid:03d}_{arm}"
        for v in ("inner", "outer")
        for rid in range(24)
        for arm in ("C", "P", "Z")
    ]
    assert names[EXPECTED_PARENT_POLICIES:] == expected_new_names
    assert len(expected_new_names) == EXPECTED_NEW_POLICIES == 144

    # Parent comparisons and aliases strictly preserved at prefix
    assert len(comps) == EXPECTED_TOTAL_COMPARISONS == 7257
    assert len(set(comps)) == 7257
    assert comps[:EXPECTED_PARENT_COMPARISONS] == [tuple(p) for p in parent_str["family_definition"]["comparisons"]]

    assert len(aliases) == EXPECTED_TOTAL_ALIASES == 152
    assert len(set(aliases)) == 152
    assert aliases[:EXPECTED_PARENT_ALIASES] == [tuple(p) for p in parent_str["family_definition"]["frozen_aliases"]]
    assert aliases[EXPECTED_PARENT_ALIASES:] == [
        ("EM0_000_C", "EM0_000_P"),
        ("EM0_000_Z", "EM0_000_P"),
        ("EM1_000_C", "EM1_000_P"),
        ("EM1_000_Z", "EM1_000_P"),
    ]

    # Nominal coordinates check
    assert 11 * len(names) + 10 * len(comps) == EXPECTED_NOMINAL_COORDINATES == 87970

    # Spot check each of the 7 new comparison categories
    new_comps_set = set(comps[EXPECTED_PARENT_COMPARISONS:])
    assert len(new_comps_set) == EXPECTED_NEW_COMPARISONS == 1560
    assert ("EM0_012_P", "REF") in new_comps_set
    assert ("EM1_012_P", "GR012_P") in new_comps_set
    assert ("EM0_005_C", "EM0_000_P") in new_comps_set
    assert ("EM0_000_C", "EM0_000_P") not in new_comps_set  # rid 0 excluded from matched SAFE comparison
    assert ("EM1_005_Z", "EM1_001_Z") in new_comps_set
    assert ("EM1_001_Z", "EM1_001_Z") not in new_comps_set  # rid 1 excluded from matched COST comparison
    assert ("EM0_010_P", "EM0_010_C") in new_comps_set
    assert ("EM1_010_Z", "EM1_010_P") in new_comps_set
    assert ("EM0_008_C", "EM0_007_C") in new_comps_set
    assert ("EM1_023_Z", "EM1_007_Z") in new_comps_set
    assert ("EM0_019_P", "EM0_022_P") in new_comps_set
    assert ("EM1_014_C", "EM1_008_C") in new_comps_set
    assert ("EM1_015_P", "EM0_015_P") in new_comps_set
