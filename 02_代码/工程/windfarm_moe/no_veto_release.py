"""Pure-function no-veto release ablation for frozen EM1_008_Z snapshot models.

Evaluates the same frozen outer-vintage models, identical SAFE/COST endpoints,
and identical C/E/D snapshot schedule while removing the tree veto branch by
applying the historically dominant training leaf's alpha uniformly across the
full grid in each enabled segment, without fitting or calling predict_rule/fit_rule.
"""
from __future__ import annotations

import math
from typing import Any, Mapping

import numpy as np

OUTER_VINTAGE_START_ANCHOR: int = 28944
RELEASE_LAG_STEPS: int = 7

OUTER_SNAPSHOT_ORDER: tuple[str, ...] = ("C", "E", "D")
OUTER_SNAPSHOT_SCHEDULE: dict[str, tuple[int, int]] = {
    "C": (29376, 29384),
    "E": (29808, 29816),
    "D": (30233, 30240),
}

_LAST_TRAINING_CUT_KEYS: tuple[str, ...] = (
    "last_training_cut",
    "lasttrainingcut",
    "last_training_anchor",
    "max_training_anchor",
)


class _ForbiddenBankAccessError(RuntimeError):
    """Raised if target/shortfall/mask fields are accessed on a bank."""


def _is_strict_int(value: Any) -> bool:
    return isinstance(value, (int, np.integer)) and not isinstance(value, (bool, np.bool_))


def _require_nonneg_int(value: Any, field_name: str) -> int:
    if isinstance(value, (bool, np.bool_)):
        raise ValueError(f"{field_name} must be a non-negative integer, got boolean {value!r}")
    if isinstance(value, (int, np.integer)):
        ival = int(value)
    elif isinstance(value, (float, np.floating)):
        fval = float(value)
        if not math.isfinite(fval) or not fval.is_integer():
            raise ValueError(f"{field_name} must be a finite integer, got {value!r}")
        ival = int(fval)
    else:
        raise ValueError(f"{field_name} must be a non-negative integer, got {value!r}")
    if ival < 0:
        raise ValueError(f"{field_name} must be >= 0, got {ival}")
    return ival


def _parse_leaf_id(raw_key: Any, field_name: str = "leaf_id") -> int:
    if isinstance(raw_key, (bool, np.bool_)):
        raise ValueError(f"{field_name} must be an integer, got boolean {raw_key!r}")
    if isinstance(raw_key, (int, np.integer)):
        lid = int(raw_key)
    elif isinstance(raw_key, str):
        s = raw_key.strip()
        if not s or (s[0] in "+-" and not s[1:].isdigit()) or (s[0] not in "+-" and not s.isdigit()):
            raise ValueError(f"{field_name} string must represent an integer, got {raw_key!r}")
        lid = int(s)
    else:
        raise ValueError(f"{field_name} must be an integer or integer string, got {raw_key!r}")
    if lid < 0:
        raise ValueError(f"{field_name} must be non-negative, got {lid}")
    return lid


def _validate_alpha(raw_alpha: Any, field_name: str = "alpha") -> float:
    if isinstance(raw_alpha, (bool, np.bool_)) or not isinstance(raw_alpha, (int, float, np.number)):
        raise ValueError(f"{field_name} must be a finite float in [0, 1], got {raw_alpha!r}")
    aval = float(raw_alpha)
    if not math.isfinite(aval) or aval < 0.0 or aval > 1.0:
        raise ValueError(f"{field_name} must be finite and within [0, 1], got {aval!r}")
    return aval


def _validate_leaf_stat_entry(lid: int, stat_entry: Any) -> int:
    if not isinstance(stat_entry, Mapping):
        raise ValueError(f"leaf_stats[{lid}] must be a mapping, got {type(stat_entry).__name__}")
    if "n_cells" not in stat_entry:
        raise ValueError(f"leaf_stats[{lid}] missing required 'n_cells' field")
    n_cells = _require_nonneg_int(stat_entry["n_cells"], f"leaf_stats[{lid}]['n_cells']")
    if n_cells <= 0:
        raise ValueError(f"leaf_stats[{lid}]['n_cells'] must have positive training support (> 0), got {n_cells}")

    for k, v in stat_entry.items():
        if k == "n_cells" or isinstance(v, (bool, np.bool_)):
            continue
        if isinstance(v, (int, np.integer)):
            if int(v) < 0:
                raise ValueError(f"leaf_stats[{lid}][{k!r}] must be non-negative, got {v!r}")
        elif isinstance(v, (float, np.floating)):
            if not math.isfinite(float(v)):
                raise ValueError(f"leaf_stats[{lid}][{k!r}] must be finite, got {v!r}")
        else:
            raise ValueError(f"leaf_stats[{lid}][{k!r}] has unsupported non-numeric value {v!r}")

    if "alpha" in stat_entry:
        _validate_alpha(stat_entry["alpha"], f"leaf_stats[{lid}]['alpha']")
    return n_cells


def select_major_leaf(model: Mapping[str, Any]) -> dict[str, Any]:
    """Select the historically largest training leaf and its alpha without accessing evaluation data.

    Returns dict(alpha, leaf_id, historical_cells, reason) without mutating ``model``.
    """
    if not isinstance(model, Mapping):
        raise ValueError(f"model must be a mapping, got {type(model).__name__}")

    for count_field in ("valid_fit_cells", "selected_issue_count", "n_leaves"):
        if count_field in model and model[count_field] is not None:
            _require_nonneg_int(model[count_field], f"model[{count_field!r}]")

    fallback_flag = model.get("fallback_to_safe", False)
    if not isinstance(fallback_flag, (bool, np.bool_)):
        raise ValueError(f"fallback_to_safe must be a boolean, got {fallback_flag!r}")
    status = str(model.get("status", ""))

    if bool(fallback_flag) or status == "UNTRAINED_ANCHOR":
        if "alpha" in model and model["alpha"] is not None:
            fb_alpha = _validate_alpha(model["alpha"], "fallback model['alpha']")
            if fb_alpha != 0.0:
                raise ValueError(f"Fallback model alpha must be 0.0, got {fb_alpha!r}")
        hist_cells = (
            _require_nonneg_int(model["valid_fit_cells"], "model['valid_fit_cells']")
            if "valid_fit_cells" in model and model["valid_fit_cells"] is not None
            else 0
        )
        reason = "UNTRAINED_ANCHOR" if status == "UNTRAINED_ANCHOR" else "FALLBACK_TO_SAFE"
        return dict(
            alpha=0.0,
            leaf_id=None,
            historical_cells=int(hist_cells),
            reason=reason,
        )

    kind = str(model.get("kind", "GATE"))
    if kind != "GATE":
        raise ValueError(f"Expected GATE model or fallback model, got kind={kind!r}")

    raw_alphas = model.get("leaf_alphas")
    raw_stats = model.get("leaf_stats")
    if not isinstance(raw_alphas, Mapping) or not isinstance(raw_stats, Mapping):
        raise ValueError("GATE model must provide mapping 'leaf_alphas' and 'leaf_stats'")
    if len(raw_alphas) == 0 or len(raw_stats) == 0:
        raise ValueError("Non-fallback GATE model has empty 'leaf_alphas' or 'leaf_stats' (no training support)")

    alphas_by_leaf: dict[int, float] = {}
    for k, v in raw_alphas.items():
        lid = _parse_leaf_id(k, "leaf_alphas key")
        if lid in alphas_by_leaf:
            raise ValueError(f"Duplicate integer leaf id {lid} in leaf_alphas")
        alphas_by_leaf[lid] = _validate_alpha(v, f"leaf_alphas[{k!r}]")

    stats_by_leaf: dict[int, int] = {}
    for k, v in raw_stats.items():
        lid = _parse_leaf_id(k, "leaf_stats key")
        if lid in stats_by_leaf:
            raise ValueError(f"Duplicate integer leaf id {lid} in leaf_stats")
        n_cells = _validate_leaf_stat_entry(lid, v)
        if "alpha" in v:
            stat_alpha = _validate_alpha(v["alpha"], f"leaf_stats[{k!r}]['alpha']")
            if lid in alphas_by_leaf and not math.isclose(stat_alpha, alphas_by_leaf[lid], rel_tol=0.0, abs_tol=1e-15):
                raise ValueError(
                    f"leaf_stats[{lid}]['alpha']={stat_alpha!r} does not match leaf_alphas[{lid}]={alphas_by_leaf[lid]!r}"
                )
        stats_by_leaf[lid] = n_cells

    if set(alphas_by_leaf.keys()) != set(stats_by_leaf.keys()):
        raise ValueError(
            f"leaf_alphas keys {sorted(alphas_by_leaf.keys())} do not match leaf_stats keys {sorted(stats_by_leaf.keys())}"
        )

    if "n_leaves" in model and model["n_leaves"] is not None:
        expected_n_leaves = _require_nonneg_int(model["n_leaves"], "model['n_leaves']")
        if expected_n_leaves != len(stats_by_leaf):
            raise ValueError(f"model['n_leaves']={expected_n_leaves} does not match leaf count {len(stats_by_leaf)}")

    total_cells = sum(stats_by_leaf.values())
    if total_cells <= 0:
        raise ValueError("Total historical training support across leaves must be > 0")
    if "valid_fit_cells" in model and model["valid_fit_cells"] is not None:
        vfc = _require_nonneg_int(model["valid_fit_cells"], "model['valid_fit_cells']")
        if vfc <= 0 or vfc != total_cells:
            raise ValueError(f"model['valid_fit_cells']={vfc} does not match sum of leaf n_cells={total_cells}")

    best_lid = min(stats_by_leaf.keys(), key=lambda lid: (-stats_by_leaf[lid], lid))
    best_cells = int(stats_by_leaf[best_lid])
    best_alpha = float(alphas_by_leaf[best_lid])
    all_zero = all(a == 0.0 for a in alphas_by_leaf.values())
    if all_zero:
        best_alpha = 0.0
    max_count = sum(1 for c in stats_by_leaf.values() if c == best_cells)
    if all_zero:
        reason = "ALL_LEAF_ALPHAS_ZERO_TIE_MIN_LEAF_ID" if max_count > 1 else "ALL_LEAF_ALPHAS_ZERO"
    else:
        reason = "MAJOR_LEAF_TIE_MIN_LEAF_ID" if max_count > 1 else "MAJOR_LEAF_MAX_N_CELLS"

    return dict(
        alpha=best_alpha,
        leaf_id=int(best_lid),
        historical_cells=best_cells,
        reason=reason,
    )


def _extract_snapshot_models(models: Mapping[ Any, Any]) -> dict[str, Mapping[str, Any]]:
    if not isinstance(models, Mapping):
        raise ValueError(f"models must be a mapping, got {type(models).__name__}")
    resolved: dict[str, Mapping[str, Any]] = {}
    for snap in OUTER_SNAPSHOT_ORDER:
        if snap in models:
            m = models[snap]
        elif (snap, 8) in models:
            m = models[(snap, 8)]
        else:
            raise KeyError(f"Missing required outer snapshot model {snap!r} in models")
        if not isinstance(m, Mapping):
            raise ValueError(f"Model for snapshot {snap!r} must be a mapping, got {type(m).__name__}")
        resolved[snap] = m
    extra_str_keys = {k for k in models.keys() if isinstance(k, str)} - set(OUTER_SNAPSHOT_ORDER)
    if extra_str_keys:
        raise ValueError(f"Unexpected snapshot keys in models: {sorted(extra_str_keys)}")
    return resolved


def _verify_snapshot_model_timing(snap: str, model: Mapping[str, Any], bank_anchors: np.ndarray) -> dict[str, int]:
    exp_cut, exp_enabled = OUTER_SNAPSHOT_SCHEDULE[snap]

    if "enabled_anchor" not in model:
        raise ValueError(f"Snapshot {snap!r} model missing required field 'enabled_anchor'")
    if "episode_start" not in model:
        raise ValueError(f"Snapshot {snap!r} model missing required field 'episode_start'")
    if "cut_anchor" not in model:
        raise ValueError(f"Snapshot {snap!r} model missing required field 'cut_anchor'")

    enabled_anchor = _require_nonneg_int(model["enabled_anchor"], f"models[{snap!r}]['enabled_anchor']")
    episode_start = _require_nonneg_int(model["episode_start"], f"models[{snap!r}]['episode_start']")
    cut_anchor = _require_nonneg_int(model["cut_anchor"], f"models[{snap!r}]['cut_anchor']")

    if enabled_anchor != exp_enabled or episode_start != exp_enabled:
        raise ValueError(
            f"Snapshot {snap!r} enabled_anchor={enabled_anchor}, episode_start={episode_start} "
            f"must both equal {exp_enabled}"
        )
    if cut_anchor != exp_cut:
        raise ValueError(f"Snapshot {snap!r} cut_anchor={cut_anchor} must equal {exp_cut}")

    if "snapshot" in model and model["snapshot"] is not None and str(model["snapshot"]) != snap:
        raise ValueError(f"Snapshot {snap!r} model has mismatched snapshot={model['snapshot']!r}")
    if "vintage" in model and model["vintage"] is not None and str(model["vintage"]) != "outer":
        raise ValueError(f"Snapshot {snap!r} model has mismatched vintage={model['vintage']!r}")
    if "vintage_start_anchor" in model and model["vintage_start_anchor"] is not None:
        v_start = _require_nonneg_int(model["vintage_start_anchor"], f"models[{snap!r}]['vintage_start_anchor']")
        if v_start != OUTER_VINTAGE_START_ANCHOR:
            raise ValueError(
                f"Snapshot {snap!r} vintage_start_anchor={v_start} must equal {OUTER_VINTAGE_START_ANCHOR}"
            )

    explicit_last_cut: int | None = None
    for k in _LAST_TRAINING_CUT_KEYS:
        if k in model and model[k] is not None:
            val = _require_nonneg_int(model[k], f"models[{snap!r}][{k!r}]")
            if explicit_last_cut is not None and val != explicit_last_cut:
                raise ValueError(f"Snapshot {snap!r} conflicting last training cut fields: {val} != {explicit_last_cut}")
            explicit_last_cut = val

    train_anchors = bank_anchors[(bank_anchors >= OUTER_VINTAGE_START_ANCHOR) & (bank_anchors < cut_anchor)]
    bank_max_train_anchor = int(np.max(train_anchors)) if train_anchors.size > 0 else int(cut_anchor - 1)

    if explicit_last_cut is not None:
        if explicit_last_cut >= cut_anchor:
            raise ValueError(
                f"Snapshot {snap!r} last_training_cut={explicit_last_cut} must be < cut_anchor={cut_anchor}"
            )
        if explicit_last_cut + RELEASE_LAG_STEPS >= enabled_anchor:
            raise ValueError(
                f"Snapshot {snap!r} last_training_cut={explicit_last_cut} violates +{RELEASE_LAG_STEPS} < {enabled_anchor}"
            )
        last_training_anchor = explicit_last_cut
    else:
        last_training_anchor = bank_max_train_anchor

    if (cut_anchor - 1) + RELEASE_LAG_STEPS >= enabled_anchor:
        raise ValueError(
            f"Snapshot {snap!r} cut_anchor={cut_anchor} violates (cut_anchor - 1) + {RELEASE_LAG_STEPS} < {enabled_anchor}"
        )
    if bank_max_train_anchor + RELEASE_LAG_STEPS >= enabled_anchor:
        raise ValueError(
            f"Snapshot {snap!r} max training anchor {bank_max_train_anchor} violates +{RELEASE_LAG_STEPS} < {enabled_anchor}"
        )

    return dict(
        cut_anchor=int(cut_anchor),
        enabled_anchor=int(enabled_anchor),
        episode_start=int(episode_start),
        last_training_cut_max_anchor=int(last_training_anchor),
    )


def no_veto_actions(
    bank: Mapping[str, Any],
    models: Mapping[Any, Any],
) -> tuple[np.ndarray, dict[str, Any]]:
    """Compute full-grid no-veto release actions and compact JSON-serializable receipt.

    Reads only ``bank['anchors']``, ``bank['safe']``, and ``bank['cost']``. Never touches
    ``target``, ``shortfall``, or ``mask``. Applies ``SAFE.copy()`` before C (29384) and
    ``np.maximum(safe + alpha * (cost - safe), 0.0)`` on each enabled segment C, E, D.
    """
    if not isinstance(bank, Mapping):
        raise ValueError(f"bank must be a mapping, got {type(bank).__name__}")
    for req_key in ("anchors", "safe", "cost"):
        if req_key not in bank:
            raise KeyError(f"bank missing required key {req_key!r}")

    anchors_raw = np.asarray(bank["anchors"])
    if anchors_raw.ndim != 1 or anchors_raw.size < 1 or anchors_raw.dtype.kind not in "iu":
        raise ValueError("bank['anchors'] must be a non-empty 1D integer array")
    anchors = np.asarray(anchors_raw, dtype=np.int64)
    if anchors.size > 1 and np.any(np.diff(anchors) <= 0):
        raise ValueError("bank['anchors'] must be strictly increasing")
    if int(anchors[0]) < OUTER_VINTAGE_START_ANCHOR:
        raise ValueError(
            f"bank starting anchor {int(anchors[0])} must be >= {OUTER_VINTAGE_START_ANCHOR} for outer vintage"
        )

    safe_raw = np.asarray(bank["safe"], dtype=np.float64)
    cost_raw = np.asarray(bank["cost"], dtype=np.float64)
    if safe_raw.ndim != 2 or safe_raw.shape[0] != anchors.shape[0] or safe_raw.shape[1] < 1:
        raise ValueError(f"bank['safe'] must have 2D shape [T, N] matching anchors T={anchors.shape[0]}")
    if cost_raw.shape != safe_raw.shape:
        raise ValueError(f"bank['cost'] shape {cost_raw.shape} must match bank['safe'] shape {safe_raw.shape}")
    if not np.isfinite(safe_raw).all() or np.any(safe_raw < 0.0):
        raise ValueError("bank['safe'] must be finite and non-negative on the full grid")
    if not np.isfinite(cost_raw).all() or np.any(cost_raw < 0.0):
        raise ValueError("bank['cost'] must be finite and non-negative on the full grid")

    snap_models = _extract_snapshot_models(models)

    snap_selections: dict[str, dict[str, Any]] = {}
    snap_timings: dict[str, dict[str, int]] = {}
    for snap in OUTER_SNAPSHOT_ORDER:
        m = snap_models[snap]
        snap_timings[snap] = _verify_snapshot_model_timing(snap, m, anchors)
        snap_selections[snap] = select_major_leaf(m)

    actions = np.ascontiguousarray(safe_raw.copy(), dtype=np.float64)
    row_alphas = np.zeros(anchors.shape[0], dtype=np.float64)

    segment_bounds: dict[str, tuple[int, int | None]] = {
        "C": (OUTER_SNAPSHOT_SCHEDULE["C"][1], OUTER_SNAPSHOT_SCHEDULE["E"][1]),
        "E": (OUTER_SNAPSHOT_SCHEDULE["E"][1], OUTER_SNAPSHOT_SCHEDULE["D"][1]),
        "D": (OUTER_SNAPSHOT_SCHEDULE["D"][1], None),
    }

    snapshots_receipt: dict[str, dict[str, Any]] = {}
    for snap in OUTER_SNAPSHOT_ORDER:
        seg_start, seg_stop = segment_bounds[snap]
        if seg_stop is None:
            sel = anchors >= seg_start
        else:
            sel = (anchors >= seg_start) & (anchors < seg_stop)

        alpha_val = float(snap_selections[snap]["alpha"])
        lid_val = snap_selections[snap]["leaf_id"]
        hist_cells = int(snap_selections[snap]["historical_cells"])
        reason = str(snap_selections[snap]["reason"])
        timing = snap_timings[snap]

        n_steps = int(np.count_nonzero(sel))
        n_cells = int(n_steps * safe_raw.shape[1])

        if n_steps > 0:
            s_seg = safe_raw[sel]
            c_seg = cost_raw[sel]
            raw_seg = s_seg + alpha_val * (c_seg - s_seg)
            actions[sel] = np.maximum(raw_seg, 0.0)
            row_alphas[sel] = alpha_val

        snapshots_receipt[snap] = dict(
            alpha=alpha_val,
            leaf_id=lid_val,
            historical_cells=hist_cells,
            reason=reason,
            cut_anchor=int(timing["cut_anchor"]),
            enabled_anchor=int(timing["enabled_anchor"]),
            episode_start=int(timing["episode_start"]),
            last_training_cut_max_anchor=int(timing["last_training_cut_max_anchor"]),
            segment_start_anchor=int(seg_start),
            segment_stop_anchor=None if seg_stop is None else int(seg_stop),
            evaluated_steps=n_steps,
            evaluated_cells=n_cells,
            mean_alpha=alpha_val if n_steps > 0 else 0.0,
        )

    pre_c_sel = anchors < OUTER_SNAPSHOT_SCHEDULE["C"][1]
    pre_c_steps = int(np.count_nonzero(pre_c_sel))

    receipt: dict[str, Any] = dict(
        vintage="outer",
        vintage_start_anchor=int(OUTER_VINTAGE_START_ANCHOR),
        bank_start_anchor=int(anchors[0]),
        bank_end_anchor=int(anchors[-1]),
        total_steps=int(anchors.shape[0]),
        n_nodes=int(safe_raw.shape[1]),
        total_cells=int(safe_raw.size),
        pre_c_safe_steps=pre_c_steps,
        pre_c_safe_cells=int(pre_c_steps * safe_raw.shape[1]),
        mean_alpha=float(np.mean(row_alphas)),
        snapshots=snapshots_receipt,
    )
    return actions, receipt
