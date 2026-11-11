"""Sparse-context conditional cutting-plane convex reserve pool over signed increments.

This module optimizes context-specific simplex weights w in R^{G x 25} over bounded
signed increments delta_k = max(X_k - b, -d * b) around a causal protection anchor
b >= 0 with relief d in [0, 1]. Context partition thresholds are learned exclusively
from the arrived common reference forecast on the full historical grid (never from
targets, validity masks, or future inputs) and are frozen for all downstream scoring.
Neither a master LP optimum nor historical cap feasibility certifies future field
event risk or modifies any scientific qualification threshold.
"""
from __future__ import annotations

import time
import traceback
from typing import Any, Sequence

import numpy as np
from scipy.optimize import linprog
from threadpoolctl import threadpool_limits

from .bounded_relief import FLOATING_FLOOR_TOLERANCE, signed_experts

ALLOWED_GROUPS: tuple[int, ...] = (1, 3)
ALLOWED_CAP_MODES: tuple[str, ...] = ("COST", "POOLED", "DAY")
ALLOWED_TIME_BUDGET_CEILINGS: tuple[float, ...] = (8.0, 60.0)
DEFAULT_BISECTION_STEPS: int = 60


def _validate_time_budget_ceiling(time_budget_ceiling: float) -> float:
    if (
        isinstance(time_budget_ceiling, (bool, np.bool_))
        or not isinstance(time_budget_ceiling, (int, float, np.integer, np.floating))
        or not np.isfinite(time_budget_ceiling)
    ):
        raise ValueError(f"time_budget_ceiling must be a finite scalar in {ALLOWED_TIME_BUDGET_CEILINGS}")
    ceiling = float(time_budget_ceiling)
    if ceiling not in ALLOWED_TIME_BUDGET_CEILINGS:
        raise ValueError(f"time_budget_ceiling must be one of {ALLOWED_TIME_BUDGET_CEILINGS}, got {time_budget_ceiling!r}")
    return ceiling


def _validate_groups(groups: int) -> int:
    if isinstance(groups, (bool, np.bool_)) or not isinstance(groups, (int, np.integer)) or int(groups) not in ALLOWED_GROUPS:
        raise ValueError(f"groups must be an integer in {ALLOWED_GROUPS}, got {groups!r}")
    return int(groups)


def _validate_relief(relief: float) -> float:
    if (
        isinstance(relief, (bool, np.bool_))
        or not np.isscalar(relief)
        or not np.isfinite(relief)
        or float(relief) < 0.0
        or float(relief) > 1.0
    ):
        raise ValueError("relief d must be a finite scalar in [0, 1]")
    return float(relief)


def _validate_cap_mode(cap_mode: str) -> str:
    if not isinstance(cap_mode, str) or cap_mode not in ALLOWED_CAP_MODES:
        raise ValueError(f"cap_mode must be one of {ALLOWED_CAP_MODES}, got {cap_mode!r}")
    return str(cap_mode)


def _validate_reference_array(reference: np.ndarray, expected_shape: tuple[int, int] | None = None) -> np.ndarray:
    ref = np.asarray(reference, dtype=np.float64)
    if (
        ref.ndim != 2
        or ref.shape[0] < 1
        or ref.shape[1] < 1
        or (expected_shape is not None and ref.shape != expected_shape)
        or not np.isfinite(ref).all()
        or np.any(ref < 0.0)
    ):
        raise ValueError("Expected complete finite nonnegative 2D reference array [T, N]")
    return ref


def _validate_cuts(cuts: Any, groups: int) -> list[float]:
    g = _validate_groups(groups)
    if cuts is None:
        raw_list: list[float] = []
    else:
        arr = np.asarray(cuts, dtype=np.float64)
        if arr.ndim != 1 or not np.isfinite(arr).all():
            raise ValueError("Context cuts must be a 1D sequence of finite floats")
        raw_list = [float(v) for v in arr.tolist()]
    expected_len = 0 if g == 1 else g - 1
    if len(raw_list) != expected_len:
        raise ValueError(f"groups={g} requires {expected_len} context cuts, got {len(raw_list)}")
    if len(raw_list) == 2 and raw_list[0] > raw_list[1]:
        raise ValueError("Context cuts must be nondecreasing")
    return raw_list


def fit_context_cuts(reference: np.ndarray, groups: int = 3) -> list[float]:
    """Compute context thresholds on the full historical reference grid without masks or targets."""
    g = _validate_groups(groups)
    ref = _validate_reference_array(reference)
    if g == 1:
        return []
    q = np.quantile(ref.reshape(-1), [1.0 / 3.0, 2.0 / 3.0], method="linear")
    cuts = [float(q[0]), float(q[1])]
    if not np.isfinite(cuts).all() or cuts[0] > cuts[1]:
        raise ValueError("Computed nonfinite or decreasing context cuts")
    return cuts


def context_ids(reference: np.ndarray, cuts: Any) -> np.ndarray:
    """Assign deterministic context group IDs via searchsorted(..., side='right')."""
    ref = _validate_reference_array(reference)
    if cuts is None:
        cut_arr = np.empty(0, dtype=np.float64)
    else:
        cut_arr = np.asarray(cuts, dtype=np.float64)
        if cut_arr.ndim != 1 or cut_arr.size not in (0, 2) or not np.isfinite(cut_arr).all():
            raise ValueError("Context cuts must be a 1D finite sequence of length 0 or 2")
        if cut_arr.size == 2 and cut_arr[0] > cut_arr[1]:
            raise ValueError("Context cuts must be nondecreasing")
    if cut_arr.size == 0:
        return np.zeros(ref.shape, dtype=np.int64)
    return np.asarray(np.searchsorted(cut_arr, ref, side="right"), dtype=np.int64)


def _anchor_weights(groups: int, n_experts: int = 25) -> np.ndarray:
    w = np.zeros((groups, n_experts), dtype=np.float64)
    w[:, 0] = 1.0
    return w


def _validate_weight_matrix(weights: Any, groups: int, n_experts: int = 25) -> np.ndarray:
    w = np.asarray(weights, dtype=np.float64).copy()
    if w.ndim == 1 and groups == 1 and w.shape == (n_experts,):
        w = w[None, :]
    if (
        w.ndim != 2
        or w.shape != (groups, n_experts)
        or not np.isfinite(w).all()
        or np.any(w < 0.0)
        or not np.allclose(w.sum(axis=1), 1.0, atol=1e-12, rtol=0.0)
    ):
        raise ValueError(f"Expected simplex weight matrix of shape ({groups}, {n_experts})")
    return w


def _evaluate_conditional_action(
    b: np.ndarray,
    delta: np.ndarray,
    ctx: np.ndarray,
    weights: np.ndarray,
    relief: float,
) -> tuple[np.ndarray, int, float]:
    """Evaluate r = b + sum_k w[ctx, k] * delta_k with mathematical floor (1 - d) * b."""
    w_cell = weights[ctx]
    step = np.sum(delta * w_cell, axis=-1)
    if not np.isfinite(step).all():
        raise FloatingPointError("Nonfinite conditional signed increment mixture")
    if relief == 0.0 and np.any(step < 0.0):
        raise FloatingPointError("Invalid negative step under zero relief")

    raw = b + step
    if not np.isfinite(raw).all():
        raise FloatingPointError("Nonfinite conditional signed action")
    if relief == 0.0 and np.any(raw < b):
        raise FloatingPointError("Protection floor lost under zero relief")

    floor = (1.0 - relief) * b
    deficit = floor - raw
    if np.any(deficit > FLOATING_FLOOR_TOLERANCE) or np.any(raw < -FLOATING_FLOOR_TOLERANCE):
        raise ValueError("Conditional action violated mathematical floor (1 - d) * b")

    guard_mask = (raw < floor) | (raw < 0.0)
    guard_count = int(np.count_nonzero(guard_mask))
    max_violation = float(np.max(np.maximum(deficit, -raw))) if guard_count else 0.0
    if guard_count:
        act = np.maximum(np.maximum(raw, floor), 0.0)
    else:
        act = raw
    return act, guard_count, max_violation


def initialize_anchor_record(
    groups: int = 3,
    relief: float = 0.0,
    cap_mode: str = "COST",
    *,
    n_raw_experts: int = 24,
) -> dict[str, Any]:
    """Build outcome-free inner-phase anchor record without fitting cuts on current reference."""
    g = _validate_groups(groups)
    d = _validate_relief(relief)
    mode = _validate_cap_mode(cap_mode)
    if isinstance(n_raw_experts, (bool, np.bool_)) or int(n_raw_experts) != 24:
        raise ValueError("Conditional pool requires exactly 24 raw experts (25 signed increments)")
    k = 25
    cuts = [] if g == 1 else [0.0, 0.0]
    w0 = _anchor_weights(g, k).tolist()
    return dict(
        schema="conditional-convex-pool-v1",
        status="NO_PRIOR_OOF_ANCHOR",
        optimal=False,
        numerical_fitted=False,
        groups=g,
        relief=d,
        cap_mode=mode,
        cuts=cuts,
        cuts_source="NO_PRIOR_OOF_ANCHOR_NO_HISTORICAL_CUTS",
        weights=w0,
        raw_weights=w0,
        canonical_initial=w0,
        objective=None,
        lower_bound=None,
        gap=None,
        mean_uncovered_power=None,
        uncovered_cap=None,
        day_caps=None,
        day_uncovered_power=None,
        day_ids=[],
        day_valid_counts=[],
        max_cap_violation=0.0,
        anchor_objective=None,
        anchor_mean_uncovered_power=None,
        valid_fit_cells=0,
        total_cells=0,
        fit_issue_count=0,
        group_total_counts=[0] * g,
        group_valid_counts=[0] * g,
        empty_groups=list(range(g)),
        actual_feasible=True,
        raw_actual_feasible=True,
        repaired_to_anchor=False,
        repair_alpha=0.0,
        repaired_candidate_attempted=False,
        boundary_guard_count=0,
        max_boundary_violation=0.0,
        iterations=0,
        elapsed_seconds=0.0,
        time_limit=0.0,
        max_iter=0,
        relative_tolerance=1e-7,
        numerical_tolerance=None,
        n_raw_experts=24,
        n_experts=25,
        support_smoothing=0.0,
        numerical_failure=None,
        time_budget_ceiling=8.0,
        warm_start_provided=False,
        warm_start_accepted=False,
        warm_start_objective=None,
    )


def fit_conditional_pool(
    x: np.ndarray,
    b: np.ndarray,
    y: np.ndarray,
    mask: np.ndarray,
    anchors: np.ndarray,
    reference: np.ndarray,
    *,
    groups: int = 3,
    relief: float = 0.0,
    cap_mode: str = "COST",
    time_limit: float = 8.0,
    time_budget_ceiling: float = 8.0,
    max_iter: int = 1200,
    tol: float = 1e-7,
    cuts: Sequence[float] | None = None,
    warm_start_weights: Any = None,
    bisection_steps: int = DEFAULT_BISECTION_STEPS,
) -> dict[str, Any]:
    """Fit context-conditional 25-expert simplex weights by sparse cutting-plane optimization."""
    start = time.monotonic()
    g = _validate_groups(groups)
    d = _validate_relief(relief)
    mode = _validate_cap_mode(cap_mode)
    ceiling_f = _validate_time_budget_ceiling(time_budget_ceiling)

    if (
        isinstance(time_limit, (bool, np.bool_))
        or not np.isscalar(time_limit)
        or not np.isfinite(time_limit)
        or float(time_limit) <= 0.0
    ):
        raise ValueError("time_limit must be a positive finite number of seconds")
    if (
        isinstance(max_iter, (bool, np.bool_))
        or not isinstance(max_iter, (int, np.integer))
        or int(max_iter) < 1
    ):
        raise ValueError("max_iter must be a positive integer")
    if (
        isinstance(tol, (bool, np.bool_))
        or not np.isscalar(tol)
        or not np.isfinite(tol)
        or float(tol) <= 0.0
    ):
        raise ValueError("tol must be a positive finite scalar")
    if (
        isinstance(bisection_steps, (bool, np.bool_))
        or not isinstance(bisection_steps, (int, np.integer))
        or int(bisection_steps) < 1
    ):
        raise ValueError("bisection_steps must be a positive integer")

    time_limit_f = float(min(float(time_limit), ceiling_f))
    max_iter_i = int(max_iter)
    tol_f = float(tol)
    bisection_i = int(bisection_steps)

    x_arr = np.asarray(x, dtype=np.float64)
    b_arr = np.asarray(b, dtype=np.float64)
    y_arr = np.asarray(y, dtype=np.float64)
    m_arr = np.asarray(mask)
    a_arr = np.asarray(anchors)

    if (
        b_arr.ndim != 2
        or b_arr.shape[0] < 1
        or b_arr.shape[1] < 1
        or x_arr.ndim != 3
        or x_arr.shape != (*b_arr.shape, 24)
        or y_arr.shape != b_arr.shape
        or m_arr.shape != b_arr.shape
        or m_arr.dtype != bool
        or a_arr.shape != (b_arr.shape[0],)
        or a_arr.dtype.kind not in "iu"
        or np.any(a_arr < 0)
        or np.any(a_arr[1:] <= a_arr[:-1])
        or not np.isfinite(x_arr).all()
        or np.any(x_arr < 0.0)
        or not np.isfinite(b_arr).all()
        or np.any(b_arr < 0.0)
    ):
        raise ValueError("Invalid expert [T,N,24], baseline [T,N], target [T,N], mask [T,N], or clock [T]")

    ref_arr = _validate_reference_array(reference, expected_shape=b_arr.shape)

    # Cuts are computed on the full historical reference grid before any mask/target inspection.
    if cuts is None:
        frozen_cuts = fit_context_cuts(ref_arr, g)
        cuts_source = "HISTORICAL_REFERENCE_GRID_QUANTILES" if g == 3 else "SINGLE_POOL_NO_CUTS"
    else:
        frozen_cuts = _validate_cuts(cuts, g)
        cuts_source = "EXPLICIT_FROZEN_CUTS"

    ctx_grid = context_ids(ref_arr, frozen_cuts)
    group_total_counts = [int(np.count_nonzero(ctx_grid == grp)) for grp in range(g)]
    group_valid_counts = [int(np.count_nonzero(m_arr & (ctx_grid == grp))) for grp in range(g)]
    empty_groups = [int(grp) for grp in range(g) if group_valid_counts[grp] == 0]

    valid_count = int(np.count_nonzero(m_arr))
    t_steps, n_nodes = b_arr.shape
    total_cells = int(t_steps * n_nodes)
    k = 25
    anchor_w = _anchor_weights(g, k)
    warm_w: np.ndarray | None = None
    if warm_start_weights is not None:
        warm_w = _validate_weight_matrix(warm_start_weights, g, k)
        for grp in empty_groups:
            if not np.array_equal(warm_w[grp], anchor_w[grp]):
                raise ValueError(f"Empty valid group {grp} in warm_start_weights must equal exact anchor vertex e0")

    if valid_count == 0:
        w_list = anchor_w.tolist()
        return dict(
            schema="conditional-convex-pool-v1",
            status="EMPTY_VALID_POPULATION_ANCHOR",
            optimal=False,
            numerical_fitted=False,
            groups=g,
            relief=d,
            cap_mode=mode,
            cuts=frozen_cuts,
            cuts_source=cuts_source,
            weights=w_list,
            raw_weights=w_list,
            canonical_initial=w_list,
            objective=None,
            lower_bound=None,
            gap=None,
            mean_uncovered_power=None,
            uncovered_cap=None,
            day_caps=None,
            day_uncovered_power=None,
            day_ids=[],
            day_valid_counts=[],
            max_cap_violation=0.0,
            anchor_objective=None,
            anchor_mean_uncovered_power=None,
            valid_fit_cells=0,
            total_cells=total_cells,
            fit_issue_count=t_steps,
            group_total_counts=group_total_counts,
            group_valid_counts=group_valid_counts,
            empty_groups=empty_groups,
            actual_feasible=True,
            raw_actual_feasible=True,
            repaired_to_anchor=False,
            repair_alpha=0.0,
            repaired_candidate_attempted=False,
            boundary_guard_count=0,
            max_boundary_violation=0.0,
            iterations=0,
            elapsed_seconds=float(time.monotonic() - start),
            time_limit=time_limit_f,
            time_budget_ceiling=ceiling_f,
            max_iter=max_iter_i,
            relative_tolerance=tol_f,
            numerical_tolerance=None,
            n_raw_experts=24,
            n_experts=k,
            support_smoothing=0.0,
            numerical_failure=None,
            warm_start_provided=bool(warm_w is not None),
            warm_start_accepted=False,
            warm_start_objective=None,
        )

    y_valid = np.asarray(y_arr[m_arr], dtype=np.float64)
    if not np.isfinite(y_valid).all() or np.any(y_valid < 0.0):
        raise ValueError("Valid masked historical targets must be finite and nonnegative")

    delta_grid = signed_experts(x_arr, b_arr, d)
    b_valid = np.ascontiguousarray(b_arr[m_arr], dtype=np.float64)
    delta_valid = np.ascontiguousarray(delta_grid[m_arr], dtype=np.float64)
    ctx_valid = np.ascontiguousarray(ctx_grid[m_arr], dtype=np.int64)

    day_grid = np.broadcast_to((a_arr.astype(np.int64) // 144)[:, None], b_arr.shape)
    day_valid = np.ascontiguousarray(day_grid[m_arr], dtype=np.int64)
    unique_days = np.unique(day_valid)
    day_ids = [int(day) for day in unique_days.tolist()]
    day_masks = [day_valid == int(day) for day in unique_days]
    day_valid_counts = [int(np.count_nonzero(dm)) for dm in day_masks]

    anchor_z = np.maximum(y_valid - b_valid, 0.0)
    anchor_u = float(anchor_z.mean())
    anchor_c = float((b_valid + 10.0 * anchor_z).mean() / 6.0)
    pooled_cap = anchor_u if mode == "POOLED" else None
    day_caps = (
        [float(anchor_z[dm].mean()) for dm in day_masks]
        if mode == "DAY"
        else None
    )

    dim = g * k
    group_masks = [ctx_valid == grp for grp in range(g)]
    mean_delta_by_group = np.zeros((g, k), dtype=np.float64)
    for grp in range(g):
        gm = group_masks[grp]
        if np.any(gm):
            mean_delta_by_group[grp] = delta_valid[gm].sum(axis=0) / float(valid_count)

    cost_planes: list[np.ndarray] = []
    cap_planes: list[tuple[np.ndarray, float]] = []

    def evaluate_candidate(
        w_mat: np.ndarray, *, add_cuts: bool = True
    ) -> tuple[float, float, list[float] | None, bool, float, int, float]:
        r_vec, g_cnt, max_viol = _evaluate_conditional_action(b_valid, delta_valid, ctx_valid, w_mat, d)
        diff = y_valid - r_vec
        z_vec = np.maximum(diff, 0.0)
        f_val = float((r_vec + 10.0 * z_vec).mean() / 6.0)
        h_pooled = float(z_vec.mean())
        w_flat = w_mat.reshape(dim)

        if add_cuts:
            slope = np.where(diff > 0.0, -9.0, np.where(diff < 0.0, 1.0, 0.0)) / 6.0
            g_cost = np.zeros((g, k), dtype=np.float64)
            for grp in range(g):
                gm = group_masks[grp]
                if np.any(gm):
                    g_cost[grp] = (slope[gm] @ delta_valid[gm]) / float(valid_count)
            g_cost_flat = g_cost.reshape(dim)
            cost_planes.append(np.r_[g_cost_flat, f_val - float(g_cost_flat @ w_flat)])

        if mode == "COST":
            return f_val, h_pooled, None, True, 0.0, g_cnt, max_viol

        if mode == "POOLED":
            assert pooled_cap is not None
            if add_cuts:
                active = diff > 0.0
                gh = np.zeros((g, k), dtype=np.float64)
                for grp in range(g):
                    mask_g = group_masks[grp] & active
                    if np.any(mask_g):
                        gh[grp] = -delta_valid[mask_g].sum(axis=0) / float(valid_count)
                gh_flat = gh.reshape(dim)
                cap_planes.append((np.r_[gh_flat, h_pooled - float(gh_flat @ w_flat)], pooled_cap))
            excess = max(0.0, h_pooled - pooled_cap)
            return f_val, h_pooled, None, bool(h_pooled <= pooled_cap), float(excess), g_cnt, max_viol

        assert day_caps is not None
        active = diff > 0.0
        h_days: list[float] = []
        max_excess = 0.0
        all_ok = True
        for dm, n_d, cap_d in zip(day_masks, day_valid_counts, day_caps):
            hd = float(z_vec[dm].mean())
            h_days.append(hd)
            if hd > cap_d:
                all_ok = False
                max_excess = max(max_excess, hd - cap_d)
            if add_cuts:
                gh_d = np.zeros((g, k), dtype=np.float64)
                active_dm = dm & active
                for grp in range(g):
                    mask_dg = active_dm & group_masks[grp]
                    if np.any(mask_dg):
                        gh_d[grp] = -delta_valid[mask_dg].sum(axis=0) / float(n_d)
                gh_d_flat = gh_d.reshape(dim)
                cap_planes.append((np.r_[gh_d_flat, hd - float(gh_d_flat @ w_flat)], cap_d))
        return f_val, h_pooled, h_days, all_ok, float(max_excess), g_cnt, max_viol

    best_w = anchor_w.copy()
    raw_last_w = anchor_w.copy()
    best_f = anchor_c
    best_u = anchor_u
    best_day_u = list(day_caps) if day_caps is not None else None
    best_guard_cnt = 0
    best_guard_viol = 0.0
    lower = 0.0
    iterations = 0
    repaired_any = False
    best_repaired = False
    best_repair_alpha = 0.0
    raw_last_feasible = True
    numerical_failure: str | None = None
    warm_start_accepted = False
    warm_start_objective: float | None = None

    if warm_w is not None:
        with threadpool_limits(limits=1):
            fw, uw, day_uw, okw, _, gcw, gvw = evaluate_candidate(warm_w, add_cuts=True)
        if not okw:
            raise ValueError("warm_start_weights violated historical cap feasibility")
        warm_start_accepted = True
        warm_start_objective = fw
        best_w = warm_w.copy()
        raw_last_w = warm_w.copy()
        best_f = fw
        best_u = uw
        best_day_u = day_uw
        best_guard_cnt = gcw
        best_guard_viol = gvw

    try:
        with threadpool_limits(limits=1):
            # Evaluate anchor vertex e0 (feasible under every cap mode) and uniform mixture
            # (adds one initial cutting plane without updating best_w if cap-infeasible).
            f0, u0, day_u0, ok0, _, gc0, gv0 = evaluate_candidate(anchor_w, add_cuts=True)
            if not ok0:
                raise FloatingPointError("Anchor weights violated anchor-defined cap")
            if warm_w is None or f0 < best_f:
                best_w = anchor_w.copy()
                raw_last_w = anchor_w.copy()
                best_f = f0
                best_u = u0
                best_day_u = day_u0
                best_guard_cnt = gc0
                best_guard_viol = gv0

            w_unif = np.zeros((g, k), dtype=np.float64)
            for grp in range(g):
                if group_valid_counts[grp] == 0:
                    w_unif[grp, 0] = 1.0
                else:
                    w_unif[grp, :] = 1.0 / float(k)
            fu, uu, day_uu, oku, _, gcu, gvu = evaluate_candidate(w_unif, add_cuts=True)
            if oku and fu < best_f:
                best_w = w_unif.copy()
                raw_last_w = w_unif.copy()
                best_f = fu
                best_u = uu
                best_day_u = day_uu
                best_guard_cnt = gcu
                best_guard_viol = gvu

            A_eq = np.zeros((g, dim + 1), dtype=np.float64)
            for grp in range(g):
                A_eq[grp, grp * k : (grp + 1) * k] = 1.0
            b_eq = np.ones(g, dtype=np.float64)

            bounds: list[tuple[float, float | None]] = []
            for grp in range(g):
                if group_valid_counts[grp] == 0:
                    bounds.append((1.0, 1.0))
                    bounds.extend([(0.0, 0.0)] * (k - 1))
                else:
                    bounds.extend([(0.0, 1.0)] * k)
            bounds.append((0.0, None))
            c_obj = np.r_[np.zeros(dim, dtype=np.float64), 1.0]

            status = "ITERATION_LIMIT"
            for iterations in range(1, max_iter_i + 1):
                remaining = time_limit_f - (time.monotonic() - start)
                if remaining <= 0.0:
                    status = "TIME_LIMIT"
                    break

                cp_arr = np.asarray(cost_planes, dtype=np.float64)
                A_ub = np.c_[cp_arr[:, :dim], -np.ones(len(cp_arr), dtype=np.float64)]
                b_ub = -cp_arr[:, dim]
                if cap_planes:
                    cap_mat = np.asarray([row for row, _ in cap_planes], dtype=np.float64)
                    cap_rhs = np.asarray([cap_val for _, cap_val in cap_planes], dtype=np.float64)
                    A_ub = np.r_[A_ub, np.c_[cap_mat[:, :dim], np.zeros(len(cap_mat), dtype=np.float64)]]
                    b_ub = np.r_[b_ub, cap_rhs - cap_mat[:, dim]]

                solved = linprog(
                    c_obj,
                    A_ub=A_ub,
                    b_ub=b_ub,
                    A_eq=A_eq,
                    b_eq=b_eq,
                    bounds=bounds,
                    method="highs",
                    options={
                        "threads": 1,
                        "time_limit": float(remaining),
                        "primal_feasibility_tolerance": 1e-8,
                        "dual_feasibility_tolerance": 1e-8,
                    },
                )
                if not solved.success or solved.x is None or not np.isfinite(solved.fun):
                    if int(getattr(solved, "status", -1)) == 1 and "time" in str(getattr(solved, "message", "")).lower():
                        status = "TIME_LIMIT"
                    else:
                        status = f"MASTER_{getattr(solved, 'status', 'FAILED')}"
                    break

                lower = max(lower, float(solved.fun))
                raw_sol = np.asarray(solved.x[:dim], dtype=np.float64).reshape(g, k)
                if np.min(raw_sol) < -1e-7 or np.max(np.abs(raw_sol.sum(axis=1) - 1.0)) > 1e-7:
                    status = "MASTER_NUMERIC_UNRESOLVED"
                    break

                w_cand = np.maximum(raw_sol, 0.0)
                for grp in range(g):
                    if group_valid_counts[grp] == 0:
                        w_cand[grp] = 0.0
                        w_cand[grp, 0] = 1.0
                    else:
                        s_grp = float(w_cand[grp].sum())
                        if s_grp <= 0.0 or not np.isfinite(s_grp):
                            w_cand[grp] = 0.0
                            w_cand[grp, 0] = 1.0
                        else:
                            w_cand[grp] /= s_grp

                raw_last_w = w_cand.copy()
                fc, uc, day_uc, okc, _, gcc, gvc = evaluate_candidate(w_cand, add_cuts=True)
                raw_last_feasible = okc

                if okc:
                    if fc < best_f:
                        best_w = w_cand.copy()
                        best_f = fc
                        best_u = uc
                        best_day_u = day_uc
                        best_guard_cnt = gcc
                        best_guard_viol = gvc
                        best_repaired = False
                        best_repair_alpha = 0.0
                else:
                    repaired_any = True
                    lo = 0.0
                    hi = 1.0
                    rep_w = anchor_w.copy()
                    rep_f = anchor_c
                    rep_u = anchor_u
                    rep_day_u = list(day_caps) if day_caps is not None else None
                    rep_gc = gc0
                    rep_gv = gv0
                    for _ in range(bisection_i):
                        mid = 0.5 * (lo + hi)
                        blend = (1.0 - mid) * w_cand + mid * anchor_w
                        blend = np.maximum(blend, 0.0)
                        for grp in range(g):
                            if group_valid_counts[grp] == 0:
                                blend[grp] = 0.0
                                blend[grp, 0] = 1.0
                            else:
                                blend[grp] /= blend[grp].sum()
                        fb, ub, day_ub, okb, _, gcb, gvb = evaluate_candidate(blend, add_cuts=False)
                        if okb:
                            hi = mid
                            rep_w = blend
                            rep_f = fb
                            rep_u = ub
                            rep_day_u = day_ub
                            rep_gc = gcb
                            rep_gv = gvb
                        else:
                            lo = mid
                    # Evaluate the repaired feasible point to add supporting cost/cap cuts at the boundary
                    if hi < 1.0:
                        evaluate_candidate(rep_w, add_cuts=True)
                    if rep_f < best_f:
                        best_w = rep_w.copy()
                        best_f = rep_f
                        best_u = rep_u
                        best_day_u = rep_day_u
                        best_guard_cnt = rep_gc
                        best_guard_viol = rep_gv
                        best_repaired = True
                        best_repair_alpha = float(hi)

                tol_abs = tol_f * max(1.0, abs(best_f))
                if lower > best_f + tol_abs:
                    status = "BOUND_CONTRADICTION"
                    break
                if best_f - lower <= tol_abs:
                    status = "OPTIMAL_NUMERICAL_BOUNDS"
                    break
    except Exception as exc:
        numerical_failure = repr(exc)
        status = "NUMERICAL_FAILURE_ANCHOR_FALLBACK"
        best_w = anchor_w.copy()
        raw_last_w = anchor_w.copy()
        best_f = anchor_c
        best_u = anchor_u
        best_day_u = list(day_caps) if day_caps is not None else None
        best_guard_cnt = 0
        best_guard_viol = 0.0
        lower = 0.0
        best_repaired = True
        best_repair_alpha = 1.0
        raw_last_feasible = False

    if status == "BOUND_CONTRADICTION":
        best_w = anchor_w.copy()
        best_f = anchor_c
        best_u = anchor_u
        best_day_u = list(day_caps) if day_caps is not None else None
        best_guard_cnt = 0
        best_guard_viol = 0.0
        lower = 0.0
        best_repaired = True
        best_repair_alpha = 1.0

    # Force empty context groups to exact anchor e0
    for grp in empty_groups:
        best_w[grp] = 0.0
        best_w[grp, 0] = 1.0

    # Final independent evaluation of best_w to guarantee exact actual feasibility and metrics
    final_f, final_u, final_day_u, final_ok, final_excess, final_gc, final_gv = evaluate_candidate(
        best_w, add_cuts=False
    )
    if not final_ok:
        best_w = anchor_w.copy()
        final_f, final_u, final_day_u, final_ok, final_excess, final_gc, final_gv = evaluate_candidate(
            best_w, add_cuts=False
        )
        best_repaired = True
        best_repair_alpha = 1.0
        status = f"{status}_ANCHOR_REPAIRED"

    if best_repaired and best_repair_alpha > 0.0:
        status = "REPAIRED_FEASIBLE_UNKNOWN_OPTIMALITY"
        optimal = False
    else:
        optimal = bool(status == "OPTIMAL_NUMERICAL_BOUNDS" and final_ok and numerical_failure is None)

    tol_abs = tol_f * max(1.0, abs(final_f))
    gap = float(max(0.0, final_f - lower))

    return dict(
        schema="conditional-convex-pool-v1",
        status=status,
        optimal=optimal,
        numerical_fitted=True,
        groups=g,
        relief=d,
        cap_mode=mode,
        cuts=frozen_cuts,
        cuts_source=cuts_source,
        weights=best_w.tolist(),
        raw_weights=raw_last_w.tolist(),
        canonical_initial=best_w.tolist(),
        objective=final_f,
        lower_bound=float(lower),
        gap=gap,
        mean_uncovered_power=final_u,
        uncovered_cap=pooled_cap,
        day_caps=day_caps,
        day_uncovered_power=final_day_u,
        day_ids=day_ids,
        day_valid_counts=day_valid_counts,
        max_cap_violation=float(final_excess),
        anchor_objective=anchor_c,
        anchor_mean_uncovered_power=anchor_u,
        valid_fit_cells=valid_count,
        total_cells=total_cells,
        fit_issue_count=t_steps,
        group_total_counts=group_total_counts,
        group_valid_counts=group_valid_counts,
        empty_groups=empty_groups,
        actual_feasible=bool(final_ok),
        raw_actual_feasible=bool(raw_last_feasible),
        repaired_to_anchor=bool(best_repaired),
        repair_alpha=float(best_repair_alpha),
        repaired_candidate_attempted=bool(repaired_any),
        repaired_any_iteration=bool(repaired_any),
        boundary_guard_count=int(final_gc),
        max_boundary_violation=float(final_gv),
        iterations=int(iterations),
        elapsed_seconds=float(time.monotonic() - start),
        time_limit=time_limit_f,
        time_budget_ceiling=ceiling_f,
        max_iter=max_iter_i,
        relative_tolerance=tol_f,
        numerical_tolerance=float(tol_abs),
        n_raw_experts=24,
        n_experts=k,
        support_smoothing=0.0,
        numerical_failure=numerical_failure,
        warm_start_provided=bool(warm_w is not None),
        warm_start_accepted=bool(warm_start_accepted),
        warm_start_objective=warm_start_objective,
        mean_delta_by_group=mean_delta_by_group.tolist(),
    )


def predict_conditional_pool(
    x: np.ndarray,
    b: np.ndarray,
    reference: np.ndarray,
    record: dict[str, Any],
) -> tuple[np.ndarray, dict[str, Any]]:
    """Predict static conditional-pool reserve actions without masks or cut recomputation."""
    if not isinstance(record, dict):
        raise ValueError("record must be a dictionary returned by fit_conditional_pool or initialize_anchor_record")

    g = _validate_groups(record.get("groups", 3))
    d = _validate_relief(record.get("relief", 0.0))
    mode = _validate_cap_mode(record.get("cap_mode", "COST"))
    frozen_cuts = _validate_cuts(record.get("cuts", []), g)
    w_mat = _validate_weight_matrix(record.get("weights"), g, 25)

    x_arr = np.asarray(x, dtype=np.float64)
    b_arr = np.asarray(b, dtype=np.float64)
    if (
        b_arr.ndim != 2
        or b_arr.shape[0] < 1
        or b_arr.shape[1] < 1
        or x_arr.ndim != 3
        or x_arr.shape != (*b_arr.shape, 24)
        or not np.isfinite(x_arr).all()
        or np.any(x_arr < 0.0)
        or not np.isfinite(b_arr).all()
        or np.any(b_arr < 0.0)
    ):
        raise ValueError("Invalid expert [T,N,24] or causal baseline [T,N] for prediction")

    ref_arr = _validate_reference_array(reference, expected_shape=b_arr.shape)
    ctx = context_ids(ref_arr, frozen_cuts)
    delta = signed_experts(x_arr, b_arr, d)
    actions, guard_cnt, max_viol = _evaluate_conditional_action(b_arr, delta, ctx, w_mat, d)

    group_cell_counts = [int(np.count_nonzero(ctx == grp)) for grp in range(g)]
    meta = dict(
        groups=g,
        relief=d,
        cap_mode=mode,
        cuts=list(frozen_cuts),
        group_cell_counts=group_cell_counts,
        boundary_guard_count=int(guard_cnt),
        max_boundary_violation=float(max_viol),
        recomputed_cuts_on_prediction=False,
        mask_gated_prediction=False,
    )
    return actions, meta
