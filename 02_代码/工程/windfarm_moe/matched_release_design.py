"""Matched historical-vintage release gate scheduling and full family builder.

Implements the two-vintage ('inner' starting at 28087 and 'outer' starting at 28944)
snapshot fitting, causal scheduled action prediction without target/mask access,
and the 1400-policy / 7257-comparison / 152-alias / 87970-coordinate inference family.
"""
from __future__ import annotations

from typing import Any, Mapping

import numpy as np

from windfarm_moe.release_bank import RELEASE_LAG_STEPS
from windfarm_moe.release_gate import (
    MIN_SAMPLES_LEAF,
    build_recipes,
    coerce_recipe,
    fit_rule,
    predict_rule,
)
from windfarm_moe.residual_meta import META_ARMS

VINTAGES: tuple[str, ...] = ("inner", "outer")
VINTAGE_PREFIX: dict[str, str] = {"inner": "EM0", "outer": "EM1"}
VINTAGE_START_ANCHOR: dict[str, int] = {"inner": 28087, "outer": 28944}

SNAPSHOTS: dict[str, dict[str, tuple[int, int]]] = {
    "inner": {
        "A": (28519, 28526),
        "B": (28937, 28944),
        "C": (29376, 29384),
        "D": (30233, 30240),
    },
    "outer": {
        "C": (29376, 29384),
        "E": (29808, 29816),
        "D": (30233, 30240),
    },
}

SNAPSHOT_ORDER: dict[str, tuple[str, ...]] = {
    "inner": ("A", "B", "C", "D"),
    "outer": ("C", "E", "D"),
}

VALIDATION_WINDOWS: dict[str, dict[str, tuple[int, int]]] = {
    "inner": {
        "A": (28526, 28937),
        "B": (28944, 29376),
        "C": (29384, 30233),
    },
    "outer": {
        "C": (29384, 29808),
        "E": (29816, 30233),
    },
}

POPULATION_WINDOWS: dict[str, tuple[int, int]] = {
    "inner": (28087, 28937),
    "outer": (28944, 30233),
    "evaluate": (30240, 35273),
}

STATIC_RECIPE_IDS: tuple[int, ...] = tuple(range(0, 7))
LEARNED_RECIPE_IDS: tuple[int, ...] = tuple(range(7, 24))
GLOBAL_FIT_RECIPE_ID: int = 7
GATE_RECIPE_IDS: tuple[int, ...] = tuple(range(8, 20))
CURRENT_GATE_RECIPE_IDS: tuple[int, ...] = tuple(range(8, 14))
FEEDBACK_GATE_RECIPE_IDS: tuple[int, ...] = tuple(range(14, 20))
CALIBRATION_RECIPE_IDS: tuple[int, ...] = tuple(range(20, 24))
PRIMARY_CAL_RECIPE_ID: int = 22

EXPECTED_PARENT_POLICIES: int = 1256
EXPECTED_PARENT_COMPARISONS: int = 5697
EXPECTED_PARENT_ALIASES: int = 148
EXPECTED_NEW_POLICIES: int = 144
EXPECTED_NEW_COMPARISONS: int = 1560
EXPECTED_NEW_ALIASES: int = 4
EXPECTED_TOTAL_POLICIES: int = 1400
EXPECTED_TOTAL_COMPARISONS: int = 7257
EXPECTED_TOTAL_ALIASES: int = 152
EXPECTED_NOMINAL_COORDINATES: int = 87970


def _validate_vintage(vintage: str) -> str:
    if not isinstance(vintage, str) or vintage not in SNAPSHOTS:
        raise ValueError(f"Unsupported vintage {vintage!r}; expected one of {VINTAGES}")
    return vintage


def _strict_recipe_id(recipe_id: int | Mapping[str, Any]) -> int:
    rec = coerce_recipe(recipe_id)
    return int(rec["id"])


def policy_name(vintage: str, rid: int, arm: str) -> str:
    """Format canonical matched-endpoint policy role name."""
    v = _validate_vintage(vintage)
    if isinstance(rid, (bool, np.bool_)) or not isinstance(rid, (int, np.integer)):
        raise ValueError(f"Recipe id must be an integer in 0..23, got {rid!r}")
    rid_int = int(rid)
    if not 0 <= rid_int < 24:
        raise ValueError(f"Recipe id out of range [0, 23]: {rid_int}")
    if arm not in META_ARMS:
        raise ValueError(f"Unsupported meta arm {arm!r}; expected one of {META_ARMS}")
    return f"{VINTAGE_PREFIX[v]}_{rid_int:03d}_{arm}"


def prediction_view(bank: Mapping[str, Any]) -> dict[str, Any]:
    """Expose only arrived covariates to predict_rule, excluding shortfall, mask, and anchors."""
    return {k: bank[k] for k in ("safe", "cost", "current_features", "feedback_features")}


def _summarize_prediction_diagnostics(
    model: Mapping[str, Any],
    pred_meta: Mapping[str, Any],
    safe_slice: np.ndarray,
    cost_slice: np.ndarray,
) -> dict[str, Any]:
    kind = str(model.get("kind", "SAFE"))
    alpha_grid = pred_meta.get("alpha_grid")
    if alpha_grid is not None:
        ag = np.asarray(alpha_grid, dtype=np.float64)
        mean_a: float | None = float(np.mean(ag))
        min_a: float | None = float(np.min(ag))
        max_a: float | None = float(np.max(ag))
        g_enabled_frac = float(np.mean(ag > 0.0))
    else:
        raw_mean = pred_meta.get("mean_alpha")
        raw_min = pred_meta.get("min_alpha")
        raw_max = pred_meta.get("max_alpha")
        mean_a = None if raw_mean is None else float(raw_mean)
        min_a = None if raw_min is None else float(raw_min)
        max_a = None if raw_max is None else float(raw_max)
        g_enabled_frac = (
            1.0 if kind == "CONDITIONAL_CALIBRATION" and not pred_meta.get("fallback_to_safe") else 0.0
        )

    shift_grid = pred_meta.get("shift_grid")
    if shift_grid is not None:
        sg = np.asarray(shift_grid, dtype=np.float64)
        mean_shift: float | None = float(np.mean(sg))
        min_shift: float | None = float(np.min(sg))
        max_shift: float | None = float(np.max(sg))
    else:
        raw_shift = pred_meta.get("mean_shift_kw")
        mean_shift = None if raw_shift is None else float(raw_shift)
        min_shift = None
        max_shift = None

    leaf_stats = model.get("leaf_stats") or {}
    leaf_cf_summary: dict[str, Any] = {}
    for lk, lv in leaf_stats.items():
        if isinstance(lv, Mapping) and "safe_C_kwh" in lv and "actual_C_kwh" in lv:
            dc = float(lv["actual_C_kwh"]) - float(lv["safe_C_kwh"])
            d10u = 10.0 * (float(lv["actual_U_kwh"]) - float(lv["safe_U_kwh"]))
            leaf_cf_summary[str(lk)] = dict(
                alpha=float(lv.get("alpha", 0.0)),
                mean_counterfactual_delta_C_kwh=dc,
                mean_counterfactual_delta_10U_kwh=d10u,
                n_cells=int(lv.get("n_cells", 0)),
            )
        elif isinstance(lv, Mapping):
            leaf_cf_summary[str(lk)] = {
                str(k): (int(v) if isinstance(v, (int, np.integer)) and not isinstance(v, (bool, np.bool_))
                         else float(v) if isinstance(v, (float, np.floating))
                         else v)
                for k, v in lv.items()
            }

    return dict(
        kind=kind,
        status=str(model.get("status", "UNKNOWN")),
        fallback_to_safe=bool(pred_meta.get("fallback_to_safe", False)),
        mean_alpha=mean_a,
        min_alpha=min_a,
        max_alpha=max_a,
        g_enabled_fraction=g_enabled_frac,
        mean_shift_kw=mean_shift,
        min_shift_kw=min_shift,
        max_shift_kw=max_shift,
        leaf_support={str(k): int(v) for k, v in (pred_meta.get("leaf_support") or {}).items()},
        leaf_counterfactual_stats=leaf_cf_summary,
        zero_clamp_count=int(pred_meta.get("zero_clamp_count", 0)),
        mean_cost_minus_safe_kw=float(
            np.mean(np.asarray(cost_slice, dtype=np.float64) - np.asarray(safe_slice, dtype=np.float64))
        ),
    )


def fit_snapshot_models(
    bank: Mapping[str, Any],
    vintage: str,
    seed: int,
    min_samples_leaf: int = MIN_SAMPLES_LEAF,
) -> tuple[dict[tuple[str, int], dict[str, Any]], dict[tuple[str, int], dict[str, Any]]]:
    """Fit all 24 release gate recipes across all causal snapshots for the given vintage."""
    v = _validate_vintage(vintage)
    anchors = np.asarray(bank["anchors"], dtype=np.int64)
    if anchors.ndim != 1:
        raise ValueError(f"Bank anchors must be 1D, got shape {anchors.shape}")
    min_anchor = VINTAGE_START_ANCHOR[v]

    recipes = build_recipes()
    snaps = SNAPSHOTS[v]
    order = SNAPSHOT_ORDER[v]
    models: dict[tuple[str, int], dict[str, Any]] = {}
    receipts: dict[tuple[str, int], dict[str, Any]] = {}

    for snap_key in order:
        cut, enabled = snaps[snap_key]
        if int(cut) + RELEASE_LAG_STEPS > int(enabled):
            raise ValueError(f"Snapshot {snap_key} cut={cut} and enabled={enabled} violate +7 maturity")
        sel = (anchors >= min_anchor) & (anchors < int(cut))
        if np.any(sel) and int(np.max(anchors[sel])) + RELEASE_LAG_STEPS >= int(enabled):
            bad_anchor = int(np.max(anchors[sel]))
            raise ValueError(
                f"Snapshot {snap_key} selected anchor {bad_anchor} violates +{RELEASE_LAG_STEPS} < {enabled}"
            )
        for rec in recipes:
            rid = int(rec["id"])
            model, receipt = fit_rule(
                bank,
                rec,
                seed=seed,
                fit_selector=sel,
                episode_start=int(enabled),
                min_samples_leaf=int(min_samples_leaf),
            )
            model_out = dict(
                model,
                vintage=v,
                vintage_start_anchor=int(min_anchor),
                snapshot=snap_key,
                cut_anchor=int(cut),
                enabled_anchor=int(enabled),
            )
            receipt_out = dict(
                receipt,
                vintage=v,
                vintage_start_anchor=int(min_anchor),
                snapshot=snap_key,
                cut_anchor=int(cut),
                enabled_anchor=int(enabled),
            )
            models[snap_key, rid] = model_out
            receipts[snap_key, rid] = receipt_out

    expected_count = 24 * len(order)
    if len(models) != expected_count or len(receipts) != expected_count:
        raise AssertionError(f"Expected {expected_count} snapshot models, got {len(models)}")
    return models, receipts


def scheduled_actions(
    bank: Mapping[str, Any],
    models: Mapping[tuple[str, int], Mapping[str, Any]],
    vintage: str,
    recipe_id: int,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Predict scheduled actions across snapshots without touching shortfall or mask."""
    v = _validate_vintage(vintage)
    rid = _strict_recipe_id(recipe_id)
    anchors = np.asarray(bank["anchors"], dtype=np.int64)
    safe = np.asarray(bank["safe"], dtype=np.float64)
    cost = np.asarray(bank["cost"], dtype=np.float64)
    if anchors.ndim != 1 or safe.ndim != 2 or cost.shape != safe.shape or safe.shape[0] != anchors.shape[0]:
        raise ValueError("Invalid bank anchors, safe, or cost shape in scheduled_actions")

    order = SNAPSHOT_ORDER[v]
    snaps = SNAPSHOTS[v]
    for snap_key in order:
        if (snap_key, rid) not in models:
            raise KeyError(f"Missing model for snapshot ({snap_key!r}, {rid}) in vintage {v!r}")

    view = prediction_view(bank)
    actions = np.ascontiguousarray(safe.copy(), dtype=np.float64)
    diagnostics: dict[str, Any] = {}

    for j, snap_key in enumerate(order):
        _, start = snaps[snap_key]
        stop = snaps[order[j + 1]][1] if j + 1 < len(order) else np.iinfo(np.int64).max
        if rid in STATIC_RECIPE_IDS and j == 0:
            sel = anchors < stop
        else:
            sel = (anchors >= start) & (anchors < stop)
        if not np.any(sel):
            continue
        model = models[snap_key, rid]
        pred, meta = predict_rule(model, view, sel)
        actions[sel] = pred
        diagnostics[snap_key] = _summarize_prediction_diagnostics(model, meta, safe[sel], cost[sel])

    return actions, diagnostics


def build_family(
    parent_inference: Mapping[str, Any],
) -> tuple[list[str], list[bool], list[tuple[str, str]], list[tuple[str, str]]]:
    """Extend the 1256-policy prospective release family with 144 matched-vintage roles."""
    fd = parent_inference.get("family_definition")
    if not isinstance(fd, Mapping):
        raise ValueError("parent_inference missing family_definition mapping")

    old_names_raw = parent_inference.get("policy_names")
    if old_names_raw is None:
        old_names_raw = fd.get("policy_names")
    if not isinstance(old_names_raw, list) or len(old_names_raw) != EXPECTED_PARENT_POLICIES:
        raise ValueError(
            f"Parent policy_names count {None if not isinstance(old_names_raw, list) else len(old_names_raw)} "
            f"!= {EXPECTED_PARENT_POLICIES}"
        )
    old_names = [str(x) for x in old_names_raw]

    raw_avail = parent_inference.get("available")
    if not isinstance(raw_avail, list) or len(raw_avail) not in (1184, EXPECTED_PARENT_POLICIES):
        raise ValueError("Parent available list missing or has unexpected length")
    available = [bool(x) for x in raw_avail]

    raw_comps = fd.get("comparisons")
    if not isinstance(raw_comps, list) or len(raw_comps) != EXPECTED_PARENT_COMPARISONS:
        raise ValueError(
            f"Parent comparisons count {None if not isinstance(raw_comps, list) else len(raw_comps)} "
            f"!= {EXPECTED_PARENT_COMPARISONS}"
        )

    raw_aliases = fd.get("frozen_aliases")
    if not isinstance(raw_aliases, list) or len(raw_aliases) != EXPECTED_PARENT_ALIASES:
        raise ValueError(
            f"Parent frozen_aliases count {None if not isinstance(raw_aliases, list) else len(raw_aliases)} "
            f"!= {EXPECTED_PARENT_ALIASES}"
        )

    def _resolve_pair(pair: Any) -> tuple[str, str]:
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            raise ValueError(f"Invalid pair entry: {pair!r}")
        out: list[str] = []
        for item in pair:
            if isinstance(item, (int, np.integer)) and not isinstance(item, (bool, np.bool_)):
                idx = int(item)
                if not 0 <= idx < len(old_names):
                    raise ValueError(f"Parent policy index {idx} out of range")
                out.append(old_names[idx])
            elif isinstance(item, str):
                if item not in old_names:
                    raise ValueError(f"Unknown policy name in parent pair: {item!r}")
                out.append(item)
            else:
                raise ValueError(f"Unsupported policy reference in pair: {item!r}")
        return out[0], out[1]

    comparisons: list[tuple[str, str]] = [_resolve_pair(p) for p in raw_comps]
    aliases: list[tuple[str, str]] = [_resolve_pair(p) for p in raw_aliases]

    new_names = [
        policy_name(v, rid, arm)
        for v in VINTAGES
        for rid in range(24)
        for arm in META_ARMS
    ]
    if len(new_names) != EXPECTED_NEW_POLICIES:
        raise AssertionError(f"Expected {EXPECTED_NEW_POLICIES} new policies, got {len(new_names)}")
    names = old_names + new_names

    # 1. Each new role vs REF, R0182_P, BR009_P, BR009_Z, MC049_{arm}, GR{rid:03d}_{arm} (144 * 6 = 864 pairs)
    for v in VINTAGES:
        for rid in range(24):
            for arm in META_ARMS:
                left = policy_name(v, rid, arm)
                for right in (
                    "REF",
                    "R0182_P",
                    "BR009_P",
                    "BR009_Z",
                    f"MC049_{arm}",
                    f"GR{rid:03d}_{arm}",
                ):
                    comparisons.append((left, right))

    # 2. Each role vs same-vintage matched SAFE EMv_000_P (excluding rid 0) and same-arm COST EMv_001_{arm} (excluding rid 1) (276 pairs)
    for v in VINTAGES:
        safe_ref = policy_name(v, 0, "P")
        for rid in range(24):
            for arm in META_ARMS:
                left = policy_name(v, rid, arm)
                if rid != 0:
                    comparisons.append((left, safe_ref))
                if rid != 1:
                    comparisons.append((left, policy_name(v, 1, arm)))

    # 3. Within each vintage and rid: P vs C, Z vs C, Z vs P (2 * 24 * 3 = 144 pairs)
    for v in VINTAGES:
        for rid in range(24):
            comparisons.append((policy_name(v, rid, "P"), policy_name(v, rid, "C")))
            comparisons.append((policy_name(v, rid, "Z"), policy_name(v, rid, "C")))
            comparisons.append((policy_name(v, rid, "Z"), policy_name(v, rid, "P")))

    # 4. rid 8..23 vs same-vintage same-arm GLOBAL 007 (2 * 16 * 3 = 96 pairs)
    for v in VINTAGES:
        for rid in (*GATE_RECIPE_IDS, *CALIBRATION_RECIPE_IDS):
            for arm in META_ARMS:
                comparisons.append((policy_name(v, rid, arm), policy_name(v, GLOBAL_FIT_RECIPE_ID, arm)))

    # 5. rid 8..19 vs same-vintage same-arm CAL 022 (2 * 12 * 3 = 72 pairs)
    for v in VINTAGES:
        for rid in GATE_RECIPE_IDS:
            for arm in META_ARMS:
                comparisons.append((policy_name(v, rid, arm), policy_name(v, PRIMARY_CAL_RECIPE_ID, arm)))

    # 6. rid 14..19 vs same-vintage same-arm matched current gate (rid - 6) (2 * 6 * 3 = 36 pairs)
    for v in VINTAGES:
        for rid in FEEDBACK_GATE_RECIPE_IDS:
            for arm in META_ARMS:
                comparisons.append((policy_name(v, rid, arm), policy_name(v, rid - 6, arm)))

    # 7. Across vintages for identical rid and arm: outer minus inner (24 * 3 = 72 pairs)
    for rid in range(24):
        for arm in META_ARMS:
            comparisons.append((policy_name("outer", rid, arm), policy_name("inner", rid, arm)))

    # 8. New aliases: per vintage EMv_000_C vs EMv_000_P and EMv_000_Z vs EMv_000_P (2 * 2 = 4 aliases)
    for v in VINTAGES:
        aliases.append((policy_name(v, 0, "C"), policy_name(v, 0, "P")))
        aliases.append((policy_name(v, 0, "Z"), policy_name(v, 0, "P")))

    if len(names) != EXPECTED_TOTAL_POLICIES or len(set(names)) != EXPECTED_TOTAL_POLICIES:
        raise ValueError(f"Total policy names {len(names)} != {EXPECTED_TOTAL_POLICIES} or contains duplicates")
    if len(comparisons) != EXPECTED_TOTAL_COMPARISONS:
        raise ValueError(f"Total comparisons {len(comparisons)} != {EXPECTED_TOTAL_COMPARISONS}")
    if len(set(comparisons)) != EXPECTED_TOTAL_COMPARISONS:
        raise ValueError("Duplicate comparisons in extended family")
    if len(aliases) != EXPECTED_TOTAL_ALIASES or len(set(aliases)) != EXPECTED_TOTAL_ALIASES:
        raise ValueError(f"Total aliases {len(aliases)} != {EXPECTED_TOTAL_ALIASES} or contains duplicates")
    if 11 * len(names) + 10 * len(comparisons) != EXPECTED_NOMINAL_COORDINATES:
        raise ValueError("Nominal coordinate count mismatch")

    return names, available, comparisons, aliases
