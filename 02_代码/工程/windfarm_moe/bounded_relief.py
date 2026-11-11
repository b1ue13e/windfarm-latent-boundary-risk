"""Bounded signed-relief reserve actions and delayed projected mixture updates.

This module implements reversible optimization over bounded signed increments
delta_k = max(X_k - b, -d * b) around a causal protection anchor b >= 0 with
relief d in [0, 1]. The original target S and all scientific thresholds remain
unchanged. Because w lies on the probability simplex and delta_k >= -d * b,
any convex action b + sum_k w_k delta_k has exact mathematical lower bound
(1 - d) * b >= 0.
"""
from __future__ import annotations

from dataclasses import asdict
import traceback
import numpy as np

from .actual_mixture_update import MixtureConfig, actual_gradient, project_simplex
from .static_convex_bundle import fit_bundle

FLOATING_FLOOR_TOLERANCE = 1e-12


def _validate_relief(relief: float) -> float:
    if (isinstance(relief, (bool, np.bool_)) or not np.isscalar(relief)
            or not np.isfinite(relief) or relief < 0.0 or relief > 1.0):
        raise ValueError("Relief fraction d must be a finite scalar in [0, 1]")
    return float(relief)


def _validate_baseline_and_experts(
    experts: np.ndarray,
    baseline: np.ndarray,
    *,
    require_nine_experts: bool = False,
) -> tuple[np.ndarray, np.ndarray]:
    x = np.asarray(experts, dtype=np.float64)
    b = np.asarray(baseline, dtype=np.float64)
    if (b.ndim < 1 or x.ndim != b.ndim + 1 or x.shape[:b.ndim] != b.shape
            or x.shape[-1] < 1 or (require_nine_experts and x.shape[-1] != 9)
            or np.any(np.asarray(b.shape) < 1)
            or not np.isfinite(b).all() or np.any(b < 0.0)
            or not np.isfinite(x).all() or np.any(x < 0.0)):
        raise ValueError("Invalid causal baseline or raw expert array")
    return x, b


def _validate_simplex_weights(weights: np.ndarray, k: int, c: int | None = None) -> np.ndarray:
    w = np.asarray(weights, dtype=np.float64).copy()
    if c is not None and w.ndim == 1:
        w = np.broadcast_to(w, (c, k)).copy()
    if w.ndim == 1:
        if (w.shape != (k,) or not np.isfinite(w).all() or np.any(w < 0.0)
                or not np.isclose(w.sum(), 1.0, atol=1e-12, rtol=0.0)):
            raise ValueError("Invalid simplex weight vector")
        return w
    if (w.ndim != 2 or w.shape[1] != k or (c is not None and w.shape[0] != c)
            or not np.isfinite(w).all() or np.any(w < 0.0)
            or not np.allclose(w.sum(axis=1), 1.0, atol=1e-12, rtol=0.0)):
        raise ValueError("Invalid simplex weight matrix")
    return w


def signed_experts(experts, baseline, relief=0.0):
    """Construct [0, max(X - b[..., None], -d * b[..., None])] with d in [0, 1]."""
    d = _validate_relief(relief)
    x, b = _validate_baseline_and_experts(experts, baseline)
    lower = -d * b[..., None]
    delta = np.maximum(x - b[..., None], lower)
    zero = np.zeros((*b.shape, 1), dtype=np.float64)
    return np.concatenate([zero, delta], axis=-1)


def signed_action(baseline, increments, weights, relief=0.0, *, return_info=False):
    """Evaluate b + sum_k w_k * delta_k with lower-bound floor (1 - d) * b."""
    d = _validate_relief(relief)
    b = np.asarray(baseline, dtype=np.float64)
    inc = np.asarray(increments, dtype=np.float64)
    if (b.ndim < 1 or inc.ndim != b.ndim + 1 or inc.shape[:b.ndim] != b.shape
            or inc.shape[-1] < 2 or np.any(np.asarray(b.shape) < 1)
            or not np.isfinite(b).all() or np.any(b < 0.0)
            or not np.isfinite(inc).all()):
        raise ValueError("Invalid baseline or signed increments")
    if np.any(inc[..., 0] != 0.0):
        raise ValueError("Signed increments must keep anchor increment 0 in slot 0")
    min_inc = -d * b[..., None]
    if np.any(inc < min_inc - FLOATING_FLOOR_TOLERANCE):
        raise ValueError("Signed increments violate -d * b relief bound")
    if d == 0.0 and np.any(inc < 0.0):
        raise ValueError("Zero relief requires nonnegative increments")

    w = _validate_simplex_weights(weights, inc.shape[-1])
    if w.ndim == 1:
        step = np.sum(inc * w, axis=-1)
        floor = (1.0 - d) * b
        base = b
    else:
        expand = (slice(None),) + (None,) * b.ndim + (slice(None),)
        step = np.sum(inc[None, ...] * w[expand], axis=-1)
        floor = (1.0 - d) * b[None, ...]
        base = b[None, ...]

    if not np.isfinite(step).all():
        raise FloatingPointError("Nonfinite signed increment mixture")
    if d == 0.0 and np.any(step < 0.0):
        raise ValueError("Invalid nonnegative residual")

    raw = base + step
    if not np.isfinite(raw).all():
        raise FloatingPointError("Nonfinite signed action")
    if d == 0.0 and np.any(raw < base):
        raise FloatingPointError("Protection floor lost")

    deficit = floor - raw
    if np.any(deficit > FLOATING_FLOOR_TOLERANCE) or np.any(raw < -FLOATING_FLOOR_TOLERANCE):
        raise ValueError("Signed action violated mathematical floor (1 - d) * b")

    guard_mask = (raw < floor) | (raw < 0.0)
    guard_count = int(np.count_nonzero(guard_mask))
    max_guard_ulps = float(np.max(np.maximum(deficit, -raw))) if guard_count else 0.0
    if guard_count:
        result = np.maximum(np.maximum(raw, floor), 0.0)
    else:
        result = raw

    if return_info:
        return result, dict(
            boundary_guard_count=guard_count,
            max_boundary_violation=max_guard_ulps,
            relief=d,
        )
    return result


def fit_signed(
    experts,
    baseline,
    y,
    *,
    relief=0.0,
    goal="COST",
    time_limit=10.0,
    max_iter=1000,
    relative_tolerance=1e-7,
    bisection_steps=60,
):
    """Fit convex weights on flattened (b + delta) for COST or anchor-referenced CAP."""
    d = _validate_relief(relief)
    if goal not in ("COST", "CAP"):
        raise ValueError("Goal must be 'COST' or 'CAP'")
    if (isinstance(time_limit, (bool, np.bool_)) or not np.isscalar(time_limit)
            or not np.isfinite(time_limit) or time_limit <= 0.0):
        raise ValueError("time_limit must be a positive finite number of seconds")
    time_limit = float(min(float(time_limit), 10.0))

    x = np.asarray(experts, dtype=np.float64)
    b = np.asarray(baseline, dtype=np.float64)
    target = np.asarray(y, dtype=np.float64)
    if (b.ndim < 1 or target.shape != b.shape or x.ndim != b.ndim + 1
            or x.shape[:b.ndim] != b.shape or x.shape[-1] < 1
            or b.size < 1 or not np.isfinite(b).all() or np.any(b < 0.0)
            or not np.isfinite(target).all() or np.any(target < 0.0)
            or not np.isfinite(x).all() or np.any(x < 0.0)):
        raise ValueError("Expected complete finite nonnegative historical arrays")

    delta = signed_experts(x, b, d)
    k = delta.shape[-1]
    b_flat = b.reshape(-1)
    y_flat = target.reshape(-1)
    delta_flat = delta.reshape(-1, k)
    shifted = np.maximum(b_flat[:, None] + delta_flat, 0.0)

    anchor_w = np.zeros(k, dtype=np.float64)
    anchor_w[0] = 1.0
    anchor_u = float(np.maximum(y_flat - b_flat, 0.0).mean())
    anchor_c = float((b_flat + 10.0 * np.maximum(y_flat - b_flat, 0.0)).mean() / 6.0)
    cap = anchor_u if goal == "CAP" else None

    try:
        bundle = fit_bundle(
            shifted,
            y_flat,
            uncovered_cap=cap,
            time_limit=time_limit,
            max_iter=max_iter,
            relative_tolerance=relative_tolerance,
        )
    except Exception as exc:
        return dict(
            weights=anchor_w.copy(),
            raw_bundle_weights=anchor_w.copy(),
            status="BUNDLE_NUMERICAL_FAILURE_ANCHOR_FALLBACK",
            bundle_status="BUNDLE_EXCEPTION",
            optimal=False,
            bundle_optimal=False,
            objective=anchor_c,
            bundle_objective=anchor_c,
            lower_bound=0.0,
            gap=anchor_c,
            mean_uncovered_power=anchor_u,
            bundle_mean_uncovered_power=anchor_u,
            uncovered_cap=cap,
            anchor_mean_uncovered_power=anchor_u,
            anchor_objective=anchor_c,
            actual_affine_feasible=True,
            repaired_to_anchor=True,
            repair_alpha=1.0,
            boundary_guard_count=0,
            max_boundary_violation=0.0,
            relief=d,
            goal=goal,
            time_limit=time_limit,
            support_smoothing=0.0,
            canonical_initial=anchor_w.copy(),
            numerical_failure=repr(exc),
            traceback=traceback.format_exc(),
        )
    record = asdict(bundle)
    raw_w = _validate_simplex_weights(bundle.weights, k)
    act, guard_info = signed_action(b_flat, delta_flat, raw_w, d, return_info=True)
    actual_u = float(np.maximum(y_flat - act, 0.0).mean())
    actual_c = float((act + 10.0 * np.maximum(y_flat - act, 0.0)).mean() / 6.0)
    raw_actual_affine_feasible = True if cap is None else bool(actual_u <= cap)

    repaired = False
    repair_alpha = 0.0
    w = raw_w.copy()
    status = str(bundle.status)
    optimal = bool(bundle.optimal)

    if cap is not None and actual_u > cap:
        repaired = True
        lo = 0.0
        hi = 1.0
        best_w = anchor_w.copy()
        best_u = anchor_u
        best_c = anchor_c
        best_guard = dict(boundary_guard_count=0, max_boundary_violation=0.0, relief=d)
        for _ in range(max(1, int(bisection_steps))):
            mid = 0.5 * (lo + hi)
            cand_w = (1.0 - mid) * raw_w + mid * anchor_w
            cand_w = np.maximum(cand_w, 0.0)
            cand_w /= cand_w.sum()
            cand_act, cand_guard = signed_action(b_flat, delta_flat, cand_w, d, return_info=True)
            cand_u = float(np.maximum(y_flat - cand_act, 0.0).mean())
            if cand_u <= cap:
                hi = mid
                best_w = cand_w
                best_u = cand_u
                best_c = float((cand_act + 10.0 * np.maximum(y_flat - cand_act, 0.0)).mean() / 6.0)
                best_guard = cand_guard
            else:
                lo = mid
        repair_alpha = float(hi)
        w = best_w
        actual_u = best_u
        actual_c = best_c
        guard_info = best_guard
        if repair_alpha > 0.0:
            optimal = False
            status = f"{status}_CAP_REPAIRED"

    gap = max(0.0, actual_c - float(bundle.lower_bound))
    record.update(
        weights=w,
        raw_bundle_weights=raw_w,
        status=status,
        bundle_status=str(bundle.status),
        optimal=optimal,
        bundle_optimal=bool(bundle.optimal),
        objective=actual_c,
        bundle_objective=float(bundle.objective),
        lower_bound=float(bundle.lower_bound),
        gap=gap,
        mean_uncovered_power=actual_u,
        bundle_mean_uncovered_power=float(bundle.mean_uncovered_power),
        uncovered_cap=cap,
        anchor_mean_uncovered_power=anchor_u,
        anchor_objective=anchor_c,
        raw_actual_affine_feasible=raw_actual_affine_feasible,
        actual_affine_feasible=(True if cap is None else bool(actual_u <= cap)),
        repaired_to_anchor=repaired,
        repair_alpha=repair_alpha,
        boundary_guard_count=guard_info["boundary_guard_count"],
        max_boundary_violation=guard_info["max_boundary_violation"],
        relief=d,
        goal=goal,
        time_limit=time_limit,
        support_smoothing=0.0,
        canonical_initial=w.copy(),
        numerical_failure=None,
    )
    return record


def _coerce_configs(configs) -> list[MixtureConfig]:
    if isinstance(configs, MixtureConfig):
        items = [configs]
    elif isinstance(configs, dict):
        items = [MixtureConfig(**configs)]
    else:
        items = [cfg if isinstance(cfg, MixtureConfig) else MixtureConfig(**cfg) for cfg in configs]
    if not items:
        raise ValueError("At least one frozen configuration is required")
    for cfg in items:
        if (isinstance(cfg.eta, (bool, np.bool_))
                or isinstance(cfg.schedule_power, (bool, np.bool_))
                or isinstance(cfg.severity_step, (bool, np.bool_))
                or isinstance(cfg.cost_scale, (bool, np.bool_))
                or isinstance(cfg.proximity_strength, (bool, np.bool_))
                or not np.isscalar(cfg.eta)
                or not np.isscalar(cfg.schedule_power)
                or not np.isscalar(cfg.severity_step)
                or not np.isscalar(cfg.cost_scale)
                or not np.isscalar(cfg.proximity_strength)
                or not np.isfinite([
                    cfg.eta,
                    cfg.schedule_power,
                    cfg.severity_step,
                    cfg.cost_scale,
                    cfg.proximity_strength,
                ]).all()
                or cfg.eta < 0.0
                or cfg.severity_step < 0.0
                or cfg.proximity_strength < 0.0
                or cfg.schedule_power not in (0.0, 0.5, 1.0)
                or cfg.cost_scale != 100.0):
            raise ValueError("Invalid frozen numerical configuration")
    return items


def run_signed(
    x,
    baseline,
    y,
    mask,
    anchors,
    configs,
    initial_weights,
    *,
    relief=0.0,
    score=True,
    return_actions=True,
):
    """Run delayed projected updates over bounded signed increments delta."""
    d = _validate_relief(relief)
    x_arr = np.asarray(x, dtype=np.float64)
    b = np.asarray(baseline, dtype=np.float64)
    y_arr = np.asarray(y, dtype=np.float64)
    m = np.asarray(mask)
    a = np.asarray(anchors)
    cfg_list = _coerce_configs(configs)

    if (b.ndim != 2 or b.shape[0] < 1 or b.shape[1] < 1
            or y_arr.shape != b.shape or m.shape != b.shape or m.dtype != bool
            or a.shape != (len(b),) or a.dtype.kind not in "iu"
            or np.any(a < 0) or np.any(a[1:] <= a[:-1])
            or not np.isfinite(b).all() or np.any(b < 0.0)
            or x_arr.ndim != 3 or x_arr.shape[:2] != b.shape or not np.isfinite(x_arr).all()):
        raise ValueError("Invalid expert, baseline, target, mask or clock arrays")

    t, n = b.shape
    if x_arr.shape[2] >= 2 and np.all(x_arr[:, :, 0] == 0.0) and np.any(x_arr < 0.0):
        min_inc = -d * b[:, :, None]
        if np.any(x_arr < min_inc - FLOATING_FLOOR_TOLERANCE):
            raise ValueError("Signed increments violate -d * b relief bound")
        delta = x_arr
    elif (x_arr.shape[2] == 10 and np.all(x_arr[:, :, 0] == 0.0)
          and np.all(x_arr >= -d * b[:, :, None] - FLOATING_FLOOR_TOLERANCE)):
        delta = x_arr
    else:
        if np.any(x_arr < 0.0):
            raise ValueError("Raw expert arrays must be nonnegative")
        delta = signed_experts(x_arr, b, d)

    c = len(cfg_list)
    k = delta.shape[2]
    w = _validate_simplex_weights(initial_weights, k, c)
    w0 = w.copy()

    eta = np.array([cfg.eta for cfg in cfg_list], dtype=np.float64)
    power = np.array([cfg.schedule_power for cfg in cfg_list], dtype=np.float64)
    gamma = np.array([cfg.severity_step for cfg in cfg_list], dtype=np.float64)
    mu = np.array([float(cfg.proximity_strength) for cfg in cfg_list], dtype=np.float64)
    lam = np.zeros(c, dtype=np.float64)

    days = np.unique(a // 144)
    day_index = {int(day): idx for idx, day in enumerate(days)}
    ledger = np.zeros((c, len(days), 4), dtype=np.float64)
    counts = np.zeros(len(days), dtype=np.int64)
    saved = np.empty((c, t, n), dtype=np.float64) if return_actions else None

    pending = {}
    cursor = 0
    last_release = -1
    trace = np.full(t, -1, dtype=np.int64)
    maximum_lambda = np.zeros(c, dtype=np.float64)
    updates = 0
    boundary_guard_counts = np.zeros(c, dtype=np.int64)
    total_boundary_guard_count = 0
    max_boundary_violation = 0.0

    for i, now in enumerate(a):
        while cursor < i and int(a[cursor]) + 7 < int(now):
            valid = m[cursor]
            count = int(valid.sum())
            previous = pending.pop(cursor)
            last_release = int(a[cursor]) + 7
            if count:
                yy = y_arr[cursor, valid]
                dd = delta[cursor, valid]
                bb = b[cursor, valid]
                if not np.isfinite(yy).all() or np.any(yy < 0.0):
                    raise ValueError("Invalid matured target")
                actual = previous[:, valid]
                factor = (1.0 + (int(a[cursor]) - int(a[0])) / 144.0) ** (-power)
                gradient = actual_gradient(dd, yy, actual, multipliers=lam, node_count=n)
                active = eta > 0.0
                if active.any():
                    if not np.any(mu[active] > 0.0):
                        w[active] = project_simplex(
                            w[active] - (eta[active] * factor[active])[:, None] * gradient[active]
                        )
                    else:
                        active_zero = active & (mu == 0.0)
                        if active_zero.any():
                            w[active_zero] = project_simplex(
                                w[active_zero]
                                - (eta[active_zero] * factor[active_zero])[:, None]
                                * gradient[active_zero]
                            )
                        active_prox = active & (mu > 0.0)
                        if active_prox.any():
                            step_prox = (eta[active_prox] * factor[active_prox])[:, None]
                            mu_prox = mu[active_prox][:, None]
                            v_prox = (
                                w[active_prox]
                                - step_prox * gradient[active_prox]
                                + (step_prox * mu_prox) * w0[active_prox]
                            ) / (1.0 + step_prox * mu_prox)
                            w[active_prox] = project_simplex(v_prox)
                actual_u = np.maximum(yy[None, :] - actual, 0.0).sum(axis=1) / (6.0 * n)
                reference_u = np.maximum(yy - bb, 0.0).sum() / (6.0 * n)
                lam = np.maximum(0.0, lam + gamma * factor * 10.0 * (actual_u - reference_u) / 100.0)
                if not np.isfinite(lam).all():
                    raise FloatingPointError("Nonfinite severity multiplier")
                maximum_lambda = np.maximum(maximum_lambda, lam)
                updates += 1
            cursor += 1

        step = np.sum(delta[i][None, :, :] * w[:, None, :], axis=-1)
        if not np.isfinite(step).all():
            raise FloatingPointError("Nonfinite signed increment action")
        raw_current = b[i][None, :] + step
        if not np.isfinite(raw_current).all():
            raise FloatingPointError("Nonfinite actual signed action")
        floor = (1.0 - d) * b[i][None, :]
        if d == 0.0 and (np.any(step < 0.0) or np.any(raw_current < b[i][None, :])):
            raise FloatingPointError("Protection floor lost")
        deficit = floor - raw_current
        if np.any(deficit > FLOATING_FLOOR_TOLERANCE) or np.any(raw_current < -FLOATING_FLOOR_TOLERANCE):
            raise FloatingPointError("Signed action violated mathematical floor")
        guard_mask = (raw_current < floor) | (raw_current < 0.0)
        if np.any(guard_mask):
            per_cfg = np.count_nonzero(guard_mask, axis=1)
            boundary_guard_counts += per_cfg
            total_boundary_guard_count += int(per_cfg.sum())
            max_boundary_violation = max(
                max_boundary_violation,
                float(np.max(np.maximum(deficit, -raw_current))),
            )
            current = np.maximum(np.maximum(raw_current, floor), 0.0)
        else:
            current = raw_current

        pending[i] = current.copy()
        trace[i] = last_release
        if saved is not None:
            saved[:, i] = current
        if score:
            di = day_index[int(now) // 144]
            valid = m[i]
            count = int(valid.sum())
            counts[di] += count
            if count:
                yy = y_arr[i, valid]
                if not np.isfinite(yy).all() or np.any(yy < 0.0):
                    raise ValueError("Invalid scored target")
                rr = current[:, valid] / 6.0
                uu = np.maximum(yy[None, :] - current[:, valid], 0.0) / 6.0
                ledger[:, di, 0] += np.sum(rr + 10.0 * uu, axis=1)
                ledger[:, di, 1] += rr.sum(axis=1)
                ledger[:, di, 2] += uu.sum(axis=1)
                ledger[:, di, 3] += (yy[None, :] > current[:, valid]).sum(axis=1)

    return dict(
        actions=saved,
        ledger=ledger,
        counts=counts,
        days=days,
        metadata=dict(
            configs=[cfg.__dict__ for cfg in cfg_list],
            relief=d,
            proximity_strengths=mu.tolist(),
            final_weights=w.tolist(),
            final_lambda_u=lam.tolist(),
            maximum_lambda_u=maximum_lambda.tolist(),
            release_trace=trace.tolist(),
            feedback_updates=updates,
            pending_rows=t - cursor,
            boundary_guard_count=int(total_boundary_guard_count),
            boundary_guard_counts=boundary_guard_counts.tolist(),
            max_boundary_violation=float(max_boundary_violation),
            feedback_rule="source_anchor+7<decision_anchor",
            zero_kink_subgradient=True,
            severity_reference="causal_anchor_b",
            node_weighting="valid-cell sum / fixed node count",
            cost_scale=100.0,
            support_smoothing=0.0,
            strict_V_is_not_optimized_or_certified=True,
            scientific_thresholds_changed=False,
            episode_restart=True,
        ),
    )
