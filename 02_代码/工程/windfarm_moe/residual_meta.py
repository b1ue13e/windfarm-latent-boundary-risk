"""Direct residual quantile meta-head optimization with causal anchor baseline."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from repo_paths import Path, repository_root
from typing import Any

import joblib
import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor
from threadpoolctl import threadpool_limits

META_ARMS = ("C", "P", "Z")
QUANTILE_GRID = (0.90, 0.925, 0.95, 0.975)
LEAVES_GRID = (7, 15, 31)
L2_GRID = (1.0, 10.0)
FIXED_HGBR_PARAMS = dict(
    loss="quantile",
    max_iter=128,
    max_bins=127,
    learning_rate=0.05,
    min_samples_leaf=64,
    early_stopping=False,
)
DEFAULT_TURBINE_NORM = 134.0
COMMON_FEATURE_NAMES = (
    "anchor_b",
    "raw_ref_expert0",
    "clock_sin",
    "clock_cos",
    "node_id_norm",
)
EXPERT_FEATURE_NAMES = tuple(f"raw_expert{k}" for k in range(1, 9))


@dataclass(frozen=True)
class ResidualMetaConfig:
    id: int
    q: float
    leaves: int
    l2: float

    def to_recipe(self) -> dict[str, Any]:
        return dict(
            id=int(self.id),
            q=float(self.q),
            leaves=int(self.leaves),
            l2=float(self.l2),
            config=dict(
                q=float(self.q),
                leaves=int(self.leaves),
                l2=float(self.l2),
                loss="quantile",
                max_iter=128,
                max_bins=127,
                learning_rate=0.05,
                min_samples_leaf=64,
                early_stopping=False,
            ),
        )


def build_meta_recipes() -> list[dict[str, Any]]:
    """Deterministic 24-recipe grid: 4 q x 3 leaves x 2 l2 (IDs 0..23)."""
    recipes: list[dict[str, Any]] = []
    for q in QUANTILE_GRID:
        for leaves in LEAVES_GRID:
            for l2 in L2_GRID:
                cfg = ResidualMetaConfig(id=len(recipes), q=float(q), leaves=int(leaves), l2=float(l2))
                recipes.append(cfg.to_recipe())
    assert len(recipes) == 24
    return recipes


def feature_names_for_arm(arm: str) -> tuple[str, ...]:
    if arm not in META_ARMS:
        raise ValueError(f"Unsupported meta arm: {arm!r}")
    if arm == "C":
        return COMMON_FEATURE_NAMES
    return COMMON_FEATURE_NAMES + EXPERT_FEATURE_NAMES


def verify_common_ref_expert0(x_p: np.ndarray, x_z: np.ndarray) -> np.ndarray:
    """Verify REF expert 0 is bitwise identical between arms P and Z."""
    p_arr = np.asarray(x_p)
    z_arr = np.asarray(x_z)
    if p_arr.ndim != 3 or z_arr.ndim != 3 or p_arr.shape != z_arr.shape or p_arr.shape[-1] != 9:
        raise ValueError(f"Expected matching [T, N, 9] expert arrays for P and Z, got {p_arr.shape} vs {z_arr.shape}")
    if not np.isfinite(p_arr).all() or not np.isfinite(z_arr).all():
        raise ValueError("Expert arrays must be finite")
    if not np.array_equal(p_arr[:, :, 0], z_arr[:, :, 0]):
        raise ValueError("REF expert 0 is not bitwise identical between P and Z")
    return np.asarray(p_arr[:, :, 0], dtype=np.float64)


def build_meta_features(
    b: np.ndarray,
    x: np.ndarray,
    anchors: np.ndarray,
    arm: str,
    *,
    turbine_norm: float = DEFAULT_TURBINE_NORM,
) -> np.ndarray:
    """Build deterministic causal feature tensor [T, N, F] without scalers, labels, or masks.

    Arm C (5 features):
      0: causal anchor baseline b[t, n]
      1: raw REF expert 0 x[t, n, 0]
      2: sin(2*pi*(anchor[t] % 144) / 144)
      3: cos(2*pi*(anchor[t] % 144) / 144)
      4: deterministic normalized turbine index n / 134.0

    Arms P / Z (13 features):
      0..4: exact same 5 common features (expert 0 not duplicated)
      5..12: corresponding arm's 8 additional raw expert outputs x[t, n, 1:9]
    """
    if arm not in META_ARMS:
        raise ValueError(f"Unsupported meta arm: {arm!r}")
    b_arr = np.asarray(b, dtype=np.float64)
    x_arr = np.asarray(x, dtype=np.float64)
    a_arr = np.asarray(anchors)
    if b_arr.ndim != 2:
        raise ValueError(f"Expected 2D causal baseline b [T, N], got shape {b_arr.shape}")
    t_steps, n_nodes = b_arr.shape
    if a_arr.shape != (t_steps,):
        raise ValueError(f"Anchors shape {a_arr.shape} does not match T={t_steps}")
    if not np.isfinite(b_arr).all() or np.any(b_arr < 0.0):
        raise ValueError("Causal anchor baseline b must be finite and nonnegative")
    if not np.isfinite(x_arr).all():
        raise ValueError("Expert inputs x must be finite")

    if x_arr.ndim == 2:
        if arm != "C" or x_arr.shape != (t_steps, n_nodes):
            raise ValueError(f"2D expert input only allowed for arm C with shape {(t_steps, n_nodes)}, got {x_arr.shape}")
        ref0 = x_arr
        extra = None
    elif x_arr.ndim == 3:
        if x_arr.shape[:2] != (t_steps, n_nodes) or x_arr.shape[2] < (1 if arm == "C" else 9):
            raise ValueError(f"Unexpected 3D expert shape {x_arr.shape} for arm {arm}")
        if arm in ("P", "Z") and x_arr.shape[2] != 9:
            raise ValueError(f"Arms P and Z require exactly 9 raw experts, got {x_arr.shape[2]}")
        ref0 = x_arr[:, :, 0]
        extra = None if arm == "C" else x_arr[:, :, 1:9]
    else:
        raise ValueError(f"Unsupported expert array ndim={x_arr.ndim}")

    slot = np.mod(a_arr.astype(np.int64), 144).astype(np.float64)
    angle = (2.0 * np.pi / 144.0) * slot
    clock_sin = np.broadcast_to(np.sin(angle)[:, None], (t_steps, n_nodes))
    clock_cos = np.broadcast_to(np.cos(angle)[:, None], (t_steps, n_nodes))
    node_id = np.broadcast_to(
        (np.arange(n_nodes, dtype=np.float64) / float(turbine_norm))[None, :],
        (t_steps, n_nodes),
    )

    common = np.stack([b_arr, ref0, clock_sin, clock_cos, node_id], axis=-1)
    if arm == "C":
        return np.ascontiguousarray(common, dtype=np.float64)
    assert extra is not None
    full = np.concatenate([common, extra], axis=-1)
    assert full.shape == (t_steps, n_nodes, 13)
    return np.ascontiguousarray(full, dtype=np.float64)


def flatten_row_major(features_3d: np.ndarray) -> np.ndarray:
    """Row-major flatten [T, N, F] -> [T*N, F]."""
    arr = np.asarray(features_3d, dtype=np.float64)
    if arr.ndim != 3:
        raise ValueError(f"Expected 3D feature tensor [T, N, F], got {arr.shape}")
    t_steps, n_nodes, n_feat = arr.shape
    return np.ascontiguousarray(arr).reshape(t_steps * n_nodes, n_feat)


def extract_valid_fit_rows(
    features_3d: np.ndarray,
    b: np.ndarray,
    y: np.ndarray,
    mask: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, str]:
    """Extract valid historical rows in row-major order and hash fit indices."""
    feat = np.asarray(features_3d, dtype=np.float64)
    b_arr = np.asarray(b, dtype=np.float64)
    y_arr = np.asarray(y, dtype=np.float64)
    m_arr = np.asarray(mask, dtype=bool)
    if feat.ndim != 3 or b_arr.shape != feat.shape[:2] or y_arr.shape != b_arr.shape or m_arr.shape != b_arr.shape:
        raise ValueError("Mismatched shapes in extract_valid_fit_rows")

    flat_feat = flatten_row_major(feat)
    flat_b = np.ascontiguousarray(b_arr, dtype=np.float64).reshape(-1)
    flat_y = np.ascontiguousarray(y_arr, dtype=np.float64).reshape(-1)
    flat_m = np.ascontiguousarray(m_arr, dtype=bool).reshape(-1)

    valid_indices = np.flatnonzero(flat_m).astype(np.int64)
    if valid_indices.size == 0:
        raise ValueError("No valid historical rows available for fitting")
    x_valid = np.ascontiguousarray(flat_feat[valid_indices], dtype=np.float64)
    b_valid = np.ascontiguousarray(flat_b[valid_indices], dtype=np.float64)
    y_valid = np.ascontiguousarray(flat_y[valid_indices], dtype=np.float64)
    if not np.isfinite(x_valid).all() or not np.isfinite(b_valid).all() or not np.isfinite(y_valid).all():
        raise ValueError("Non-finite values in valid historical fit rows")
    if np.any(b_valid < 0.0) or np.any(y_valid < 0.0):
        raise ValueError("Negative baseline or target in valid historical fit rows")
    residual_target = y_valid - b_valid
    fit_indices_sha = hashlib.sha256(np.ascontiguousarray(valid_indices, dtype="<i8").tobytes()).hexdigest()
    return x_valid, residual_target, b_valid, y_valid, fit_indices_sha


def make_hgbr_estimator(q: float, leaves: int, l2: float, seed: int) -> HistGradientBoostingRegressor:
    """Create HistGradientBoostingRegressor with all required parameters explicit."""
    return HistGradientBoostingRegressor(
        loss="quantile",
        quantile=float(q),
        max_iter=128,
        max_leaf_nodes=int(leaves),
        max_bins=127,
        learning_rate=0.05,
        min_samples_leaf=64,
        l2_regularization=float(l2),
        early_stopping=False,
        random_state=int(seed),
    )


def fit_residual_meta_head(
    x_valid: np.ndarray,
    b_valid: np.ndarray,
    y_valid: np.ndarray,
    *,
    q: float,
    leaves: int,
    l2: float,
    seed: int,
    arm: str,
    min_rows: int = 64,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Fit a single direct residual quantile meta-head on valid matured historical rows.

    Target is signed residual r_res = y - b in kW (negative allowed when b > y).
    Predicted reserve action is clamped at 0: r_hat = max(0.0, b + pred_res).
    Economic objective C = (r_hat + 10 * max(y - r_hat, 0)) / 6 and uncovered U = max(y - r_hat, 0) / 6
    are always reported against original raw shortfall y; fit_qualified is recorded purely as metadata.
    On empty/insufficient rows or estimator exception, declares explicit anchor fallback (pred_res = 0 -> r_hat = b).
    """
    x_arr = np.asarray(x_valid, dtype=np.float64)
    b_arr = np.asarray(b_valid, dtype=np.float64).reshape(-1)
    y_arr = np.asarray(y_valid, dtype=np.float64).reshape(-1)

    if b_arr.size > 0 and y_arr.size == b_arr.size and np.isfinite(b_arr).all() and np.isfinite(y_arr).all():
        anchor_u_kw = float(np.maximum(y_arr - b_arr, 0.0).mean())
        anchor_c_kwh = float((b_arr + 10.0 * np.maximum(y_arr - b_arr, 0.0)).mean() / 6.0)
        anchor_v_rate = float(np.mean(y_arr > b_arr))
    else:
        anchor_u_kw = float("nan")
        anchor_c_kwh = float("nan")
        anchor_v_rate = float("nan")

    params_explicit = dict(
        loss="quantile",
        quantile=float(q),
        max_iter=128,
        max_leaf_nodes=int(leaves),
        max_bins=127,
        learning_rate=0.05,
        min_samples_leaf=64,
        l2_regularization=float(l2),
        early_stopping=False,
        random_state=int(seed),
    )

    try:
        if x_arr.ndim != 2 or b_arr.shape != (x_arr.shape[0],) or y_arr.shape != (x_arr.shape[0],):
            raise ValueError(f"Invalid fit array shapes: X={x_arr.shape}, b={b_arr.shape}, y={y_arr.shape}")
        if x_arr.shape[0] < max(1, int(min_rows)):
            raise ValueError(f"Insufficient valid historical rows ({x_arr.shape[0]} < {max(1, int(min_rows))})")
        if not np.isfinite(x_arr).all() or not np.isfinite(b_arr).all() or not np.isfinite(y_arr).all():
            raise ValueError("Non-finite values encountered in fit arrays")
        if np.any(b_arr < 0.0) or np.any(y_arr < 0.0):
            raise ValueError("Negative baseline or target encountered in fit arrays")

        residual_target = y_arr - b_arr
        with threadpool_limits(limits=1):
            estimator = make_hgbr_estimator(q=q, leaves=leaves, l2=l2, seed=seed)
            estimator.fit(x_arr, residual_target)
            pred_res = np.asarray(estimator.predict(x_arr), dtype=np.float64).reshape(-1)
        if not np.isfinite(pred_res).all():
            raise ValueError("Non-finite training predictions from fitted estimator")

        raw_action = b_arr + pred_res
        clamp_count = int(np.count_nonzero(raw_action < 0.0))
        fit_action = np.maximum(0.0, raw_action)
        fit_u_kw = float(np.maximum(y_arr - fit_action, 0.0).mean())
        fit_c_kwh = float((fit_action + 10.0 * np.maximum(y_arr - fit_action, 0.0)).mean() / 6.0)
        fit_v_rate = float(np.mean(y_arr > fit_action))
        fit_qualified = bool(fit_c_kwh <= anchor_c_kwh and fit_u_kw <= anchor_u_kw)

        params_all = dict(estimator.get_params(deep=False))

        bundle = dict(
            schema="residual-meta-head-v1",
            kind="hgbr_quantile",
            fallback_to_anchor=False,
            status="FITTED_OK",
            fit_success=True,
            optimality_certified=False,
            arm=str(arm),
            seed=int(seed),
            params=params_explicit,
            params_all=params_all,
            feature_names=list(feature_names_for_arm(arm)),
            n_features=int(x_arr.shape[1]),
            estimator=estimator,
        )
        info = dict(
            status="FITTED_OK",
            fallback_to_anchor=False,
            fit_success=True,
            optimality_certified=False,
            params=params_explicit,
            params_all=params_all,
            feature_names=list(feature_names_for_arm(arm)),
            n_features=int(x_arr.shape[1]),
            valid_fit_cells=int(x_arr.shape[0]),
            negative_residual_fraction=float(np.mean(residual_target < 0.0)),
            predicted_negative_offset_fraction=float(np.mean(pred_res < 0.0)),
            fit_zero_clamp_count=clamp_count,
            fit_objective_C_kwh=fit_c_kwh,
            fit_mean_uncovered_power_kw=fit_u_kw,
            fit_violation_rate=fit_v_rate,
            anchor_objective_C_kwh=anchor_c_kwh,
            anchor_mean_uncovered_power_kw=anchor_u_kw,
            anchor_violation_rate=anchor_v_rate,
            fit_qualified=fit_qualified,
            fit_qualified_note="Pure diagnostic metadata; never used to filter or alter models/evaluations",
        )
        return bundle, info
    except Exception as exc:
        bundle = dict(
            schema="residual-meta-head-v1",
            kind="anchor_fallback",
            fallback_to_anchor=True,
            status="FIT_ERROR_DECLARED_ANCHOR_FALLBACK",
            fit_success=False,
            optimality_certified=False,
            arm=str(arm),
            seed=int(seed),
            params=params_explicit,
            params_all=None,
            feature_names=list(feature_names_for_arm(arm)),
            n_features=int(len(feature_names_for_arm(arm))),
            estimator=None,
            error=repr(exc),
        )
        info = dict(
            status="FIT_ERROR_DECLARED_ANCHOR_FALLBACK",
            fallback_to_anchor=True,
            fit_success=False,
            optimality_certified=False,
            params=params_explicit,
            params_all=None,
            feature_names=list(feature_names_for_arm(arm)),
            n_features=int(len(feature_names_for_arm(arm))),
            valid_fit_cells=int(x_arr.shape[0]) if x_arr.ndim == 2 else 0,
            negative_residual_fraction=0.0,
            predicted_negative_offset_fraction=0.0,
            fit_zero_clamp_count=0,
            fit_objective_C_kwh=anchor_c_kwh if np.isfinite(anchor_c_kwh) else None,
            fit_mean_uncovered_power_kw=anchor_u_kw if np.isfinite(anchor_u_kw) else None,
            fit_violation_rate=anchor_v_rate if np.isfinite(anchor_v_rate) else None,
            anchor_objective_C_kwh=anchor_c_kwh if np.isfinite(anchor_c_kwh) else None,
            anchor_mean_uncovered_power_kw=anchor_u_kw if np.isfinite(anchor_u_kw) else None,
            anchor_violation_rate=anchor_v_rate if np.isfinite(anchor_v_rate) else None,
            fit_qualified=False,
            fit_qualified_note="Pure diagnostic metadata; fallback preserves anchor baseline b without filtering",
            error=repr(exc),
        )
        return bundle, info


def predict_residual_meta_actions(
    bundle: dict[str, Any],
    features_3d: np.ndarray,
    b: np.ndarray,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Predict full-grid reserve actions r_hat = max(0, b + pred_residual) without qualification or mask filtering."""
    feat = np.asarray(features_3d, dtype=np.float64)
    b_arr = np.asarray(b, dtype=np.float64)
    if feat.ndim != 3 or b_arr.shape != feat.shape[:2]:
        raise ValueError(f"Mismatched feature shape {feat.shape} and baseline shape {b_arr.shape}")
    if not np.isfinite(feat).all() or not np.isfinite(b_arr).all() or np.any(b_arr < 0.0):
        raise ValueError("Features and baseline b must be finite, with b >= 0")

    expected_n_feat = int(bundle.get("n_features", feat.shape[-1]))
    if feat.shape[-1] != expected_n_feat:
        raise ValueError(f"Feature dimension {feat.shape[-1]} differs from model expected {expected_n_feat}")

    if bool(bundle.get("fallback_to_anchor", False)) or bundle.get("estimator") is None:
        pred_res = np.zeros_like(b_arr, dtype=np.float64)
        actions = np.ascontiguousarray(b_arr, dtype=np.float64)
        pred_info = dict(
            model_status=str(bundle.get("status", "FIT_ERROR_DECLARED_ANCHOR_FALLBACK")),
            fallback_to_anchor=True,
            zero_clamp_count=0,
            negative_offset_count=0,
            mean_predicted_residual_kw=0.0,
        )
        return actions, pred_info

    flat_feat = flatten_row_major(feat)
    estimator = bundle["estimator"]
    with threadpool_limits(limits=1):
        flat_pred = np.asarray(estimator.predict(flat_feat), dtype=np.float64)
    if flat_pred.shape != (flat_feat.shape[0],) or not np.isfinite(flat_pred).all():
        raise ValueError("Invalid or non-finite residual predictions")
    pred_res = flat_pred.reshape(b_arr.shape)
    raw_actions = b_arr + pred_res
    zero_clamp_count = int(np.count_nonzero(raw_actions < 0.0))
    neg_offset_count = int(np.count_nonzero(pred_res < 0.0))
    actions = np.ascontiguousarray(np.maximum(0.0, raw_actions), dtype=np.float64)
    pred_info = dict(
        model_status=str(bundle.get("status", "FITTED_OK")),
        fallback_to_anchor=False,
        zero_clamp_count=zero_clamp_count,
        negative_offset_count=neg_offset_count,
        mean_predicted_residual_kw=float(pred_res.mean()),
    )
    return actions, pred_info


def save_meta_model(path: Path | str, bundle: dict[str, Any], *, compress: int = 1) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, p, compress=compress)


def load_meta_model(path: Path | str) -> dict[str, Any]:
    p = Path(path)
    obj = joblib.load(p)
    if not isinstance(obj, dict) or obj.get("schema") != "residual-meta-head-v1":
        raise ValueError(f"Invalid serialized residual meta model at {p}")
    return obj
