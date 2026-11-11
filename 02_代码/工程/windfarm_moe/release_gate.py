"""Compact release gate & conditional calibration learner between frozen SAFE and COST endpoints.

Both SAFE (BR009_P) and COST (MC049_{C/P/Z}) are frozen upstream development picks
disclosed as EXPLORATORY rather than independent confirmations. Neither tree splits
nor leaf optimization certifies global optimality or alters scientific thresholds.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from repo_paths import Path, repository_root
from typing import Any, Mapping

import joblib
import numpy as np
from sklearn.tree import DecisionTreeRegressor
from threadpoolctl import threadpool_limits

from windfarm_moe.release_bank import ALL_FEATURE_NAMES, CURRENT_FEATURE_NAMES, RELEASE_LAG_STEPS

RELEASE_GATE_SCHEMA = "release-gate-v1"
CONSTANT_ALPHA_GRID: tuple[float, ...] = (0.1, 0.25, 0.5, 0.75, 0.9)
GATE_FEATURE_SETS: tuple[str, ...] = ("current", "feedback")
GATE_DEPTH_GRID: tuple[int, ...] = (1, 2)
GATE_LAMBDA_U_GRID: tuple[float, ...] = (0.0, 1.0, 10.0)
CALIBRATION_QUANTILE_GRID: tuple[float, ...] = (0.90, 0.925, 0.95, 0.975)

MIN_SAMPLES_LEAF: int = 512
MIN_SAMPLES_SPLIT: int = 1024
BISECTION_STEPS: int = 60
REPAIR_STEPS: int = 60
SUBGRADIENT_GAP_TOL: float = 1e-9

FIXED_TREE_PARAMS: dict[str, Any] = dict(
    criterion="squared_error", splitter="best", min_samples_split=MIN_SAMPLES_SPLIT,
    min_samples_leaf=MIN_SAMPLES_LEAF, min_weight_fraction_leaf=0.0, max_features=None,
    max_leaf_nodes=None, min_impurity_decrease=0.0, ccp_alpha=0.0, monotonic_cst=None,
)


@dataclass(frozen=True)
class ReleaseGateRecipe:
    id: int
    kind: str
    name: str
    alpha: float | None = None
    feature_set: str | None = None
    max_depth: int | None = None
    lambda_u: float = 0.0
    q: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return dict(
            id=int(self.id), kind=str(self.kind), name=str(self.name),
            alpha=None if self.alpha is None else float(self.alpha),
            feature_set=self.feature_set,
            max_depth=None if self.max_depth is None else int(self.max_depth),
            lambda_u=float(self.lambda_u), q=None if self.q is None else float(self.q),
        )


def build_release_gate_recipes() -> list[dict[str, Any]]:
    """Deterministic 24-recipe grid (IDs 0..23)."""
    recipes: list[dict[str, Any]] = [
        ReleaseGateRecipe(0, "SAFE", "SAFE", alpha=0.0).to_dict(),
        ReleaseGateRecipe(1, "COST", "COST", alpha=1.0).to_dict(),
    ]
    for a in CONSTANT_ALPHA_GRID:
        recipes.append(ReleaseGateRecipe(len(recipes), "CONSTANT", f"CONST_{int(round(a * 100)):02d}", alpha=float(a)).to_dict())
    recipes.append(ReleaseGateRecipe(len(recipes), "GLOBAL_FIT", "GLOBAL_FIT", lambda_u=0.0).to_dict())
    for fset in GATE_FEATURE_SETS:
        for depth in GATE_DEPTH_GRID:
            for lam in GATE_LAMBDA_U_GRID:
                recipes.append(ReleaseGateRecipe(
                    len(recipes), "GATE", f"GATE_{fset.upper()}_D{depth}_L{int(lam)}",
                    feature_set=fset, max_depth=int(depth), lambda_u=float(lam),
                ).to_dict())
    for q in CALIBRATION_QUANTILE_GRID:
        recipes.append(ReleaseGateRecipe(
            len(recipes), "CONDITIONAL_CALIBRATION", f"COND_CAL_Q{int(round(q * 1000)):03d}",
            feature_set="feedback", max_depth=2, q=float(q),
        ).to_dict())
    assert len(recipes) == 24
    return recipes


build_recipes = build_release_gate_recipes


def coerce_recipe(recipe: int | Mapping[str, Any] | ReleaseGateRecipe) -> dict[str, Any]:
    grid = build_release_gate_recipes()
    if isinstance(recipe, ReleaseGateRecipe):
        recipe = recipe.to_dict()
    if isinstance(recipe, (int, np.integer)) and not isinstance(recipe, (bool, np.bool_)):
        rid = int(recipe)
        if 0 <= rid < len(grid):
            return dict(grid[rid])
        raise ValueError(f"Recipe id out of range [0, 23]: {rid}")
    if isinstance(recipe, Mapping) and "id" in recipe:
        rid = int(recipe["id"])
        if 0 <= rid < len(grid):
            canonical = dict(grid[rid])
            for k, v in recipe.items():
                if k in canonical and canonical[k] != v:
                    raise ValueError(f"Recipe field {k}={v!r} does not match canonical {canonical[k]!r}")
            return canonical
    raise ValueError(f"Invalid recipe specification: {recipe!r}")


def make_decision_tree(max_depth: int, seed: int, min_samples_leaf: int = MIN_SAMPLES_LEAF) -> DecisionTreeRegressor:
    if isinstance(max_depth, (bool, np.bool_)) or int(max_depth) not in (1, 2):
        raise ValueError(f"max_depth must be 1 or 2, got {max_depth!r}")
    if isinstance(seed, (bool, np.bool_)) or not isinstance(seed, (int, np.integer)):
        raise ValueError(f"seed must be an integer, got {seed!r}")
    leaf_min = int(min_samples_leaf)
    if leaf_min < 1:
        raise ValueError(f"min_samples_leaf must be >= 1, got {min_samples_leaf!r}")
    return DecisionTreeRegressor(
        criterion="squared_error", splitter="best", max_depth=int(max_depth),
        min_samples_split=max(2, 2 * leaf_min), min_samples_leaf=leaf_min,
        min_weight_fraction_leaf=0.0, max_features=None, random_state=int(seed),
        max_leaf_nodes=None, min_impurity_decrease=0.0, ccp_alpha=0.0, monotonic_cst=None,
    )


def actual_cell_loss(action: np.ndarray, shortfall: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Compute per-cell actual C (kWh), U (kWh), and strict V indicator against original S."""
    r = np.asarray(action, dtype=np.float64)
    y = np.asarray(shortfall, dtype=np.float64)
    u = np.maximum(y - r, 0.0) / 6.0
    return r / 6.0 + 10.0 * u, u, (y > r).astype(np.float64)


def compute_regret_label(safe: np.ndarray, cost: np.ndarray, shortfall: np.ndarray, lambda_u: float = 0.0) -> np.ndarray:
    """Compute per-cell gate split label (C_cost - C_safe) + lambda_u * 10 * (U_cost - U_safe) in kWh."""
    if isinstance(lambda_u, (bool, np.bool_)) or not np.isfinite(lambda_u) or float(lambda_u) < 0.0:
        raise ValueError(f"lambda_u must be finite and nonnegative, got {lambda_u!r}")
    c_safe, u_safe, _ = actual_cell_loss(safe, shortfall)
    c_cost, u_cost, _ = actual_cell_loss(cost, shortfall)
    return (c_cost - c_safe) + float(lambda_u) * 10.0 * (u_cost - u_safe)


def extract_feature_matrix(bank: Mapping[str, Any], feature_set: str, selector: Any = None) -> np.ndarray:
    """Assemble 3D causal feature tensor [T_sel, N, F] for 'current' (5D) or 'feedback' (11D) without touching shortfall/mask."""
    if feature_set not in GATE_FEATURE_SETS:
        raise ValueError(f"Unsupported feature_set: {feature_set!r}")
    cur = np.asarray(bank["current_features"], dtype=np.float64)
    if cur.ndim != 3 or cur.shape[2] != 5 or not np.isfinite(cur).all():
        raise ValueError(f"Invalid current_features array with shape {cur.shape}")
    cur_sel = cur if selector is None else cur[selector]
    if feature_set == "current":
        return np.ascontiguousarray(cur_sel, dtype=np.float64)
    fb = np.asarray(bank["feedback_features"], dtype=np.float64)
    if fb.ndim != 3 or fb.shape[:2] != cur.shape[:2] or fb.shape[2] not in (6, 11) or not np.isfinite(fb).all():
        raise ValueError(f"Invalid feedback_features array with shape {fb.shape}")
    if fb.shape[2] == 11 and not np.array_equal(fb[:, :, :5], cur):
        raise ValueError("Full feedback features must retain the five current columns")
    fb_sel = fb if selector is None else fb[selector]
    full = fb_sel if fb.shape[2] == 11 else np.concatenate([cur_sel, fb_sel], axis=-1)
    if full.shape[2] != 11 or not np.isfinite(full).all():
        raise ValueError("Combined feedback feature tensor must have finite shape [T, N, 11]")
    return np.ascontiguousarray(full, dtype=np.float64)


def solve_leaf_alpha(
    safe: np.ndarray, cost: np.ndarray, shortfall: np.ndarray, lambda_u: float = 0.0,
    *, bisection_steps: int = BISECTION_STEPS,
) -> dict[str, Any]:
    """Exact 1D convex piecewise-linear optimizer for r(alpha) = safe + alpha * (cost - safe) on [0, 1]."""
    b = np.asarray(safe, dtype=np.float64).reshape(-1)
    c = np.asarray(cost, dtype=np.float64).reshape(-1)
    y = np.asarray(shortfall, dtype=np.float64).reshape(-1)
    if b.size == 0 or c.shape != b.shape or y.shape != b.shape:
        raise ValueError("safe, cost, and shortfall must be non-empty 1D arrays of matching length")
    if not (np.isfinite(b).all() and np.isfinite(c).all() and np.isfinite(y).all()):
        raise ValueError("safe, cost, and shortfall must be finite")
    if np.any(b < 0.0) or np.any(c < 0.0) or np.any(y < 0.0):
        raise ValueError("safe, cost, and shortfall must be nonnegative")
    if isinstance(lambda_u, (bool, np.bool_)) or not np.isfinite(lambda_u) or float(lambda_u) < 0.0:
        raise ValueError("lambda_u must be finite and nonnegative")

    lam = float(lambda_u)
    rho_eff = 10.0 + 10.0 * lam
    d = c - b
    n = float(b.size)

    def _eval_alpha(a_val: float) -> tuple[float, float, float, float]:
        r = b + float(a_val) * d
        u_arr = np.maximum(y - r, 0.0) / 6.0
        return (
            float(np.mean(r / 6.0 + rho_eff * u_arr)),
            float(np.mean(r / 6.0 + 10.0 * u_arr)),
            float(np.mean(u_arr)),
            float(np.mean(y > r)),
        )

    obj_0, c_0, u_0, v_0 = _eval_alpha(0.0)
    cap_u = u_0
    if _eval_alpha(1.0)[2] <= cap_u:
        alpha_max, cap_binding = 1.0, False
    else:
        lo, hi = 0.0, 1.0
        for _ in range(max(1, int(bisection_steps))):
            mid = 0.5 * (lo + hi)
            if _eval_alpha(mid)[2] <= cap_u:
                lo = mid
            else:
                hi = mid
        alpha_max, cap_binding = float(lo), True

    # Right derivative at alpha = 0+
    nz = d != 0.0
    neg_branch = nz & ((y > b) | ((y == b) & (d < 0.0)))
    pos_branch = nz & ((y < b) | ((y == b) & (d > 0.0)))
    slope0 = np.zeros_like(d)
    slope0[neg_branch] = d[neg_branch] * (1.0 - rho_eff) / 6.0
    slope0[pos_branch] = d[pos_branch] / 6.0
    deriv = float(np.sum(slope0) / n)

    if deriv >= 0.0 or alpha_max == 0.0:
        chosen_kink = 0.0
    else:
        cand_a = np.where(nz, (y - b) / np.where(nz, d, 1.0), -1.0)
        in_open = nz & (cand_a > 0.0) & (cand_a < alpha_max)
        if np.any(in_open):
            ka = cand_a[in_open]
            jumps = rho_eff * np.abs(d[in_open]) / (6.0 * n)
            order = np.argsort(ka, kind="mergesort")
            uniq_a, inv = np.unique(ka[order], return_inverse=True)
            cum_deriv = deriv + np.cumsum(np.bincount(inv, weights=jumps[order]))
            cross_idx = np.flatnonzero(cum_deriv >= 0.0)
            chosen_kink = float(uniq_a[cross_idx[0]]) if cross_idx.size > 0 else float(alpha_max)
        else:
            chosen_kink = float(alpha_max)

    candidates = [0.0]
    for cand in (chosen_kink, alpha_max):
        fc = float(min(max(cand, 0.0), alpha_max))
        if all(fc != existing for existing in candidates):
            candidates.append(fc)

    repaired = False
    best_alpha, best_eval = 0.0, (obj_0, c_0, u_0, v_0)
    for cand in candidates:
        ev = _eval_alpha(cand)
        cand_a = cand
        if ev[2] > cap_u:
            repaired = True
            a_cur = cand
            for _ in range(REPAIR_STEPS):
                a_cur = float(np.nextafter(a_cur, 0.0)) if a_cur > 1e-15 else 0.0
                ev_rep = _eval_alpha(a_cur)
                if ev_rep[2] <= cap_u:
                    cand_a, ev = a_cur, ev_rep
                    break
                a_cur *= 0.5
            else:
                cand_a, ev = 0.0, (obj_0, c_0, u_0, v_0)
        if ev[2] <= cap_u and ev[0] < best_eval[0]:
            best_alpha, best_eval = cand_a, ev

    # Subgradient lower bound on [0, alpha_max]
    r_star = b + best_alpha * d
    s_left = np.where(nz & ((y > r_star) | ((y == r_star) & (d > 0.0))), d * (1.0 - rho_eff) / 6.0, np.where(nz, d / 6.0, 0.0))
    s_right = np.where(nz & ((y > r_star) | ((y == r_star) & (d < 0.0))), d * (1.0 - rho_eff) / 6.0, np.where(nz, d / 6.0, 0.0))
    g_left, g_right = float(np.sum(s_left) / n), float(np.sum(s_right) / n)
    subgrad = 0.0 if (g_left <= 0.0 <= g_right) else (g_right if g_right < 0.0 else g_left)
    lower_bound = best_eval[0] + min(subgrad * (0.0 - best_alpha), subgrad * (alpha_max - best_alpha))
    opt_gap = max(0.0, float(best_eval[0] - lower_bound))
    leaf_certified = bool((not repaired) and (not cap_binding or best_alpha < alpha_max or subgrad <= 0.0) and opt_gap <= SUBGRADIENT_GAP_TOL)

    return dict(
        alpha=float(best_alpha), alpha_max=float(alpha_max), chosen_kink=float(chosen_kink),
        cap_binding=bool(cap_binding), repaired_toward_zero=bool(repaired),
        penalized_objective_kwh=float(best_eval[0]), actual_C_kwh=float(best_eval[1]),
        actual_U_kwh=float(best_eval[2]), actual_V_rate=float(best_eval[3]),
        safe_C_kwh=float(c_0), safe_U_kwh=float(u_0), safe_V_rate=float(v_0),
        subgradient_lower_bound_kwh=float(lower_bound), subgradient_gap_kwh=float(opt_gap),
        leaf_optimality_certified=bool(leaf_certified), n_cells=int(b.size),
    )


def _select_mature_training_slice(
    bank: Mapping[str, Any], fit_selector: Any, episode_start: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, int]:
    if isinstance(episode_start, (bool, np.bool_)) or not isinstance(episode_start, (int, np.integer)):
        raise ValueError(f"episode_start must be an integer anchor, got {episode_start!r}")
    ep_start = int(episode_start)
    anchors = np.asarray(bank["anchors"], dtype=np.int64)
    shortfall = np.asarray(bank["shortfall"], dtype=np.float64)
    mask = np.asarray(bank["mask"], dtype=bool)
    safe = np.asarray(bank["safe"], dtype=np.float64)
    cost = np.asarray(bank["cost"], dtype=np.float64)
    if anchors.ndim != 1 or shortfall.ndim != 2 or shortfall.shape[0] != anchors.shape[0] or shortfall.shape[1] < 1:
        raise ValueError("Invalid bank anchors or shortfall shape")
    if any(x.shape != shortfall.shape for x in (mask, safe, cost)):
        raise ValueError("Bank mask, safe, and cost must match shortfall shape [T, N]")
    if np.any(anchors < 0) or (anchors.size > 1 and np.any(np.diff(anchors) <= 0)):
        raise ValueError("Bank anchors must be nonnegative and strictly increasing")
    if not np.isfinite(safe).all() or np.any(safe < 0.0) or not np.isfinite(cost).all() or np.any(cost < 0.0):
        raise ValueError("Bank safe and cost actions must be finite and nonnegative on the full grid")

    if fit_selector is None:
        sel_idx = np.flatnonzero(anchors + RELEASE_LAG_STEPS < ep_start)
    elif isinstance(fit_selector, slice):
        sel_idx = np.arange(anchors.size, dtype=np.int64)[fit_selector]
    else:
        arr_sel = np.asarray(fit_selector)
        if arr_sel.dtype == bool:
            if arr_sel.shape != (anchors.shape[0],):
                raise ValueError(f"Boolean fit_selector shape {arr_sel.shape} does not match T={anchors.shape[0]}")
            sel_idx = np.flatnonzero(arr_sel)
        elif arr_sel.dtype.kind in "iu":
            sel_idx = np.asarray(arr_sel, dtype=np.int64).reshape(-1)
        else:
            raise ValueError(f"Unsupported fit_selector dtype: {arr_sel.dtype}")

    sel_anchors = anchors[sel_idx]
    if sel_anchors.size > 0 and np.any(sel_anchors + RELEASE_LAG_STEPS >= ep_start):
        bad = int(sel_anchors[sel_anchors + RELEASE_LAG_STEPS >= ep_start][0])
        raise ValueError(f"Illegal fit_selector includes unmatured anchor {bad} ({bad}+{RELEASE_LAG_STEPS} >= {ep_start})")

    y_sel = shortfall[sel_idx]
    selected_mask = mask[sel_idx]
    if not np.isfinite(y_sel[selected_mask]).all() or np.any(y_sel[selected_mask] < 0.0):
        raise ValueError("Valid masked shortfall cells must be finite and nonnegative")
    return sel_idx, sel_anchors, safe[sel_idx], cost[sel_idx], y_sel, ep_start


def _build_pair(base: dict[str, Any], extra_model: dict[str, Any], extra_receipt: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    return dict(base, **extra_model), dict(base, **extra_receipt)


def fit_rule(
    bank: Mapping[str, Any], recipe: int | Mapping[str, Any] | ReleaseGateRecipe,
    seed: int, fit_selector: Any, episode_start: int, *, min_samples_leaf: int = MIN_SAMPLES_LEAF,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Fit a release-gate or conditional-calibration recipe on strictly matured historical rows."""
    rec = coerce_recipe(recipe)
    rid, kind = int(rec["id"]), str(rec["kind"])
    if isinstance(seed, (bool, np.bool_)) or not isinstance(seed, (int, np.integer)):
        raise ValueError(f"seed must be an integer, got {seed!r}")
    seed_int, leaf_min = int(seed), int(min_samples_leaf)

    sel_idx, sel_anchors, safe_sel, cost_sel, y_sel, ep_start = _select_mature_training_slice(bank, fit_selector, episode_start)
    m_sel = np.asarray(bank["mask"], dtype=bool)[sel_idx]
    valid_indices = np.flatnonzero(np.ascontiguousarray(m_sel, dtype=bool).reshape(-1)).astype(np.int64)
    n_valid = int(valid_indices.size)
    valid_row_sha = hashlib.sha256(np.ascontiguousarray(valid_indices, dtype="<i8").tobytes()).hexdigest()
    arm = str((bank.get("metadata") or {}).get("arm", "UNKNOWN"))

    base = dict(
        schema=RELEASE_GATE_SCHEMA, recipe_id=rid, recipe=rec, kind=kind, arm=arm,
        seed=seed_int, episode_start=ep_start, optimality_certified=False,
        valid_fit_cells=n_valid, valid_row_sha256=valid_row_sha, selected_issue_count=int(sel_anchors.size),
    )

    if kind in ("SAFE", "COST", "CONSTANT"):
        alpha_const = float(rec["alpha"])
        return _build_pair(
            dict(base, status="FIXED_CONSTANT_OK", fallback_to_safe=False, alpha=alpha_const),
            dict(feature_set=None, feature_names=[], n_features=0, tree=None, leaf_alphas={}, leaf_shifts={}, leaf_stats={}),
            dict(),
        )

    flat_b = np.ascontiguousarray(safe_sel, dtype=np.float64).reshape(-1)[valid_indices]
    flat_c = np.ascontiguousarray(cost_sel, dtype=np.float64).reshape(-1)[valid_indices]
    flat_y = np.ascontiguousarray(y_sel, dtype=np.float64).reshape(-1)[valid_indices]

    if kind == "GLOBAL_FIT":
        if n_valid == 0:
            return _untrained_safe_fallback(base, "Empty matured history")
        leaf_res = solve_leaf_alpha(flat_b, flat_c, flat_y, lambda_u=0.0)
        alpha_val = float(leaf_res["alpha"])
        return _build_pair(
            dict(base, status="FITTED_OK", fallback_to_safe=False, optimality_certified=bool(leaf_res["leaf_optimality_certified"]), alpha=alpha_val),
            dict(feature_set=None, feature_names=[], n_features=0, tree=None, leaf_alphas={0: alpha_val}, leaf_shifts={}, leaf_stats={0: leaf_res}),
            dict(global_fit_stats=leaf_res),
        )

    fset = str(rec["feature_set"])
    feat_names = list(CURRENT_FEATURE_NAMES if fset == "current" else ALL_FEATURE_NAMES)
    feat_3d = extract_feature_matrix(bank, fset, selector=sel_idx)
    n_feat = int(feat_3d.shape[2])

    if n_valid < leaf_min:
        return _untrained_safe_fallback(
            base, f"Insufficient valid cells ({n_valid} < {leaf_min})",
            feature_set=fset, feature_names=feat_names, n_features=n_feat,
        )

    flat_x = np.ascontiguousarray(feat_3d, dtype=np.float64).reshape(-1, n_feat)[valid_indices]
    tree = make_decision_tree(max_depth=int(rec["max_depth"]), seed=seed_int, min_samples_leaf=leaf_min)
    tree_params = dict(tree.get_params(deep=False))

    if kind == "GATE":
        lam = float(rec["lambda_u"])
        labels = compute_regret_label(flat_b, flat_c, flat_y, lambda_u=lam)
        with threadpool_limits(limits=1):
            tree.fit(flat_x, labels)
            leaf_ids = np.asarray(tree.apply(flat_x), dtype=np.int64)
        uniq_leaves = np.unique(leaf_ids)
        leaf_alphas: dict[int, float] = {}
        leaf_stats: dict[int, dict[str, Any]] = {}
        for lid in uniq_leaves:
            lmask = leaf_ids == lid
            if int(np.count_nonzero(lmask)) < leaf_min:
                raise AssertionError(f"Tree leaf {int(lid)} support < min_samples_leaf {leaf_min}")
            lres = solve_leaf_alpha(flat_b[lmask], flat_c[lmask], flat_y[lmask], lambda_u=lam)
            leaf_alphas[int(lid)] = float(lres["alpha"])
            leaf_stats[int(lid)] = lres
        common = dict(
            base, status="FITTED_OK", fallback_to_safe=False, alpha=None, lambda_u=lam,
            feature_set=fset, feature_names=feat_names, n_features=n_feat, tree_params=tree_params,
        )
        return _build_pair(
            common,
            dict(tree=tree, leaf_alphas=leaf_alphas, leaf_shifts={}, leaf_stats=leaf_stats),
            dict(n_leaves=int(len(uniq_leaves)), leaf_alphas={str(k): v for k, v in leaf_alphas.items()}, leaf_stats={str(k): v for k, v in leaf_stats.items()}),
        )

    if kind == "CONDITIONAL_CALIBRATION":
        q_val = float(rec["q"])
        residuals = flat_y - flat_c
        with threadpool_limits(limits=1):
            tree.fit(flat_x, residuals)
            leaf_ids = np.asarray(tree.apply(flat_x), dtype=np.int64)
        uniq_leaves = np.unique(leaf_ids)
        leaf_shifts: dict[int, float] = {}
        leaf_stats = {}
        for lid in uniq_leaves:
            lmask = leaf_ids == lid
            lcount = int(np.count_nonzero(lmask))
            if lcount < leaf_min:
                raise AssertionError(f"Calibration leaf {int(lid)} support < min_samples_leaf {leaf_min}")
            shift_val = float(np.quantile(residuals[lmask], q_val, method="higher"))
            c_leaf, u_leaf, v_leaf = actual_cell_loss(np.maximum(flat_c[lmask] + shift_val, 0.0), flat_y[lmask])
            leaf_shifts[int(lid)] = shift_val
            leaf_stats[int(lid)] = dict(
                shift_kw=shift_val, q=q_val, n_cells=lcount,
                actual_C_kwh=float(np.mean(c_leaf)), actual_U_kwh=float(np.mean(u_leaf)), actual_V_rate=float(np.mean(v_leaf)),
            )
        common = dict(
            base, status="FITTED_OK", fallback_to_safe=False, alpha=None, q=q_val,
            feature_set=fset, feature_names=feat_names, n_features=n_feat, tree_params=tree_params,
        )
        return _build_pair(
            common,
            dict(tree=tree, leaf_alphas={}, leaf_shifts=leaf_shifts, leaf_stats=leaf_stats),
            dict(n_leaves=int(len(uniq_leaves)), leaf_shifts={str(k): v for k, v in leaf_shifts.items()}, leaf_stats={str(k): v for k, v in leaf_stats.items()}),
        )

    raise ValueError(f"Unsupported recipe kind: {kind!r}")


def _untrained_safe_fallback(
    base: dict[str, Any], reason: str, *, feature_set: str | None = None,
    feature_names: list[str] | None = None, n_features: int = 0,
) -> tuple[dict[str, Any], dict[str, Any]]:
    common = dict(base, status="UNTRAINED_ANCHOR", fallback_to_safe=True, alpha=0.0, fallback_reason=str(reason))
    return _build_pair(
        common,
        dict(feature_set=feature_set, feature_names=list(feature_names or []), n_features=int(n_features), tree=None, leaf_alphas={}, leaf_shifts={}, leaf_stats={}),
        dict(),
    )


def predict_rule(model: Mapping[str, Any], bank: Mapping[str, Any], selector: Any = None) -> tuple[np.ndarray, dict[str, Any]]:
    """Predict full-grid reserve actions without touching bank['shortfall'] or bank['mask']."""
    if not isinstance(model, Mapping) or model.get("schema") != RELEASE_GATE_SCHEMA:
        raise ValueError("Invalid release gate model dictionary")
    safe_all = np.asarray(bank["safe"], dtype=np.float64)
    cost_all = np.asarray(bank["cost"], dtype=np.float64)
    if safe_all.ndim != 2 or cost_all.shape != safe_all.shape:
        raise ValueError("Bank safe and cost must share 2D shape [T, N]")
    safe = safe_all if selector is None else np.asarray(safe_all[selector], dtype=np.float64)
    cost = cost_all if selector is None else np.asarray(cost_all[selector], dtype=np.float64)
    if safe.ndim != 2 or safe.shape[0] < 1 or safe.shape[1] < 1:
        raise ValueError("Selected prediction grid must be non-empty 2D [T_sel, N]")
    if not np.isfinite(safe).all() or np.any(safe < 0.0) or not np.isfinite(cost).all() or np.any(cost < 0.0):
        raise ValueError("Selected safe and cost actions must be finite and nonnegative")

    status = str(model.get("status", "UNTRAINED_ANCHOR"))
    kind = str(model.get("kind", "SAFE"))
    if bool(model.get("fallback_to_safe", False)) or status == "UNTRAINED_ANCHOR":
        actions = np.ascontiguousarray(safe.copy(), dtype=np.float64)
        alpha_grid = np.zeros_like(safe, dtype=np.float64)
        return actions, dict(
            status=status, kind=kind, fallback_to_safe=True, mean_alpha=0.0,
            min_alpha=0.0, max_alpha=0.0, alpha_grid=alpha_grid, leaf_support={}, zero_clamp_count=0,
        )

    if kind in ("SAFE", "COST", "CONSTANT", "GLOBAL_FIT"):
        alpha_val = float(model["alpha"])
        if not np.isfinite(alpha_val) or alpha_val < 0.0 or alpha_val > 1.0:
            raise ValueError(f"Invalid scalar alpha in model: {alpha_val!r}")
        raw_act = safe.copy() if alpha_val == 0.0 else cost.copy() if alpha_val == 1.0 else safe + alpha_val * (cost - safe)
        actions = np.ascontiguousarray(np.maximum(raw_act, 0.0), dtype=np.float64)
        alpha_grid = np.full_like(safe, alpha_val, dtype=np.float64)
        return actions, dict(
            status=status, kind=kind, fallback_to_safe=False, mean_alpha=alpha_val,
            min_alpha=alpha_val, max_alpha=alpha_val, alpha_grid=alpha_grid,
            leaf_support={0: int(safe.size)}, zero_clamp_count=int(np.count_nonzero(raw_act < 0.0)),
        )

    fset = str(model["feature_set"])
    feat_3d = extract_feature_matrix(bank, fset, selector=selector)
    n_feat = int(model["n_features"])
    if feat_3d.shape[:2] != safe.shape or feat_3d.shape[2] != n_feat:
        raise ValueError(f"Feature shape {feat_3d.shape} does not match expected {(*safe.shape, n_feat)}")
    flat_x = feat_3d.reshape(-1, n_feat)
    with threadpool_limits(limits=1):
        leaf_ids = np.asarray(model["tree"].apply(flat_x), dtype=np.int64)
    uniq_leaves, counts = np.unique(leaf_ids, return_counts=True)
    leaf_support = {int(k): int(v) for k, v in zip(uniq_leaves, counts)}

    if kind == "GATE":
        leaf_alphas = {int(k): float(v) for k, v in (model.get("leaf_alphas") or {}).items()}
        alpha_flat = np.empty(flat_x.shape[0], dtype=np.float64)
        for lid in uniq_leaves:
            if int(lid) not in leaf_alphas:
                raise ValueError(f"Predicted leaf {int(lid)} missing from model leaf_alphas")
            alpha_flat[leaf_ids == lid] = leaf_alphas[int(lid)]
        alpha_grid = alpha_flat.reshape(safe.shape)
        raw_act = safe + alpha_grid * (cost - safe)
        actions = np.ascontiguousarray(np.maximum(raw_act, 0.0), dtype=np.float64)
        return actions, dict(
            status=status, kind=kind, fallback_to_safe=False,
            mean_alpha=float(np.mean(alpha_grid)), min_alpha=float(np.min(alpha_grid)), max_alpha=float(np.max(alpha_grid)),
            alpha_grid=alpha_grid, leaf_support=leaf_support, zero_clamp_count=int(np.count_nonzero(raw_act < 0.0)),
        )

    if kind == "CONDITIONAL_CALIBRATION":
        leaf_shifts = {int(k): float(v) for k, v in (model.get("leaf_shifts") or {}).items()}
        shift_flat = np.empty(flat_x.shape[0], dtype=np.float64)
        for lid in uniq_leaves:
            if int(lid) not in leaf_shifts:
                raise ValueError(f"Predicted leaf {int(lid)} missing from model leaf_shifts")
            shift_flat[leaf_ids == lid] = leaf_shifts[int(lid)]
        shift_grid = shift_flat.reshape(cost.shape)
        raw_act = cost + shift_grid
        actions = np.ascontiguousarray(np.maximum(raw_act, 0.0), dtype=np.float64)
        return actions, dict(
            status=status, kind=kind, fallback_to_safe=False, mean_alpha=None, min_alpha=None, max_alpha=None,
            alpha_grid=None, mean_shift_kw=float(np.mean(shift_grid)), shift_grid=shift_grid,
            leaf_support=leaf_support, zero_clamp_count=int(np.count_nonzero(raw_act < 0.0)),
        )

    raise ValueError(f"Unsupported model kind in predict_rule: {kind!r}")


def save_release_gate_model(path: Path | str, model: Mapping[str, Any], *, compress: int = 1) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(dict(model), p, compress=compress)


def load_release_gate_model(path: Path | str) -> dict[str, Any]:
    p = Path(path)
    obj = joblib.load(p)
    if not isinstance(obj, dict) or obj.get("schema") != RELEASE_GATE_SCHEMA:
        raise ValueError(f"Invalid serialized release gate model at {p}")
    return obj
