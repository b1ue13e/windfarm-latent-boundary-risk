"""Historical-only fixed convex reserve aggregation by a full-sample LP.

This baseline optimizes the original asymmetric cost over a fixed simplex of
expert actions. Neither convex cost nor an LP optimum guarantees event risk,
future performance, causal sensor value, or a field procurement benefit.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import importlib
import time
from typing import Any, Sequence
import warnings

import numpy as np
import scipy
from scipy import sparse
from scipy.optimize import linprog
from threadpoolctl import threadpool_limits


RHO = 10.
DT_HOURS = 1. / 6.
# These tolerances certify only a numerical solver result; they are not any
# experiment's scientific cost/risk/severity margin or significance threshold.
FEASIBILITY_TOLERANCE = 1e-7
OBJECTIVE_RELATIVE_TOLERANCE = 1e-7


@dataclass(frozen=True)
class StaticConvexResult:
    weights: np.ndarray | None
    status: str
    optimal: bool
    solver_status: int | None
    objective: float | None
    solver_objective: float | None
    primal_residual: dict[str, float | bool | None]
    message: str
    metadata: dict[str, Any]
    mean_uncovered_power: float | None = None
    uncovered_cap: float | None = None


def _highs_version() -> str:
    for name in ('scipy.optimize._highspy._core', 'scipy.optimize._highs._highs_constants'):
        try:
            module = importlib.import_module(name)
            parts = [getattr(module, 'HIGHS_VERSION_' + part) for part in ('MAJOR','MINOR','PATCH')]
            return '.'.join(map(str, parts))
        except (ImportError, AttributeError):
            pass
    return 'UNKNOWN: bundled HiGHS version not exposed by this SciPy build'


def _hash(array: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(array).view(np.uint8)).hexdigest()


def _indices(value: Sequence[int] | None, population: int) -> np.ndarray:
    if value is None:
        return np.arange(population, dtype=np.int64)
    raw = np.asarray(value)
    if raw.ndim != 1:
        raise ValueError('Training indices must be a one-dimensional integer list')
    if not raw.size:
        return np.empty(0, dtype=np.int64)
    if (raw.dtype.kind not in 'iu' or np.any(raw < 0) or np.any(raw >= population)
            or len(np.unique(raw)) != len(raw)):
        raise ValueError('Training indices must be unique, in-range integers')
    return raw.astype(np.int64, copy=True)


def _cost(actions: np.ndarray, target: np.ndarray) -> float:
    return float(np.mean((actions + RHO*np.maximum(target-actions, 0))*DT_HOURS))


def fit_static_convex(experts_flat: np.ndarray, S: np.ndarray, *,
                      time_limit: float = 120.,
                      training_indices: Sequence[int] | None = None,
                      uncovered_cap: float | None = None) -> StaticConvexResult:
    """Minimize mean [X theta + 10*(S-X theta)+]/6 over theta>=0,sum(theta)=1.

    All supplied rows are used by default, with no random subsampling. Explicit
    training indices change only the historical fitting population; unselected
    targets and feature values are not consumed or checked. The caller must
    establish that selected targets mature before the prediction window.

    Variables are theta[K] and nonnegative u[N], with -X theta-u<=-S. An optional
    nonnegative uncovered_cap is mean uncovered power, in S/action units (kW),
    represented by sum(u)/N<=cap, equivalent to sum(u)<=N*cap. The objective
    remains the original C. This learning constraint is not a V guarantee or a
    change to any downstream original signed-H qualification margin. An
    optimizer time/iteration limit is always preserved as non-optimal even if
    a feasible incumbent happens to beat every single expert on these rows.

    ``optimal`` requires the solver's successful optimal status, feasible
    numerical residuals, recomputed original objective agreement, and training
    cost no worse than the best individual expert *satisfying the same cap*,
    when such an expert exists, within a recorded arithmetic tolerance. A cap
    may admit a mixture but no single expert; that comparison then stays None.
    This is numerical evidence, not an exact arithmetic certificate.
    """
    started = time.perf_counter()
    if (isinstance(time_limit, (bool, np.bool_)) or not np.isscalar(time_limit)
            or not np.isfinite(time_limit) or time_limit <= 0):
        raise ValueError('time_limit must be a finite positive number of seconds')
    if uncovered_cap is not None and (isinstance(uncovered_cap, (bool, np.bool_))
            or not np.isscalar(uncovered_cap) or not np.isfinite(uncovered_cap) or uncovered_cap < 0):
        raise ValueError('uncovered_cap must be finite nonnegative mean uncovered power')
    uncovered_cap = None if uncovered_cap is None else float(uncovered_cap)
    x0, y0 = np.asarray(experts_flat, dtype=np.float64), np.asarray(S, dtype=np.float64)
    if x0.ndim != 2 or x0.shape[1] == 0 or y0.shape != (x0.shape[0],):
        raise ValueError('Expected experts[N,K] and shortfall[N], K>=1')
    ix = _indices(training_indices, len(x0))
    x, y = x0[ix], y0[ix]
    if not np.isfinite(x).all() or np.any(x < 0) or not np.isfinite(y).all() or np.any(y < 0):
        raise ValueError('Selected historical actions and shortfalls must be finite nonnegative')
    n, k = x.shape
    options = dict(time_limit=float(time_limit), threads=1, random_seed=0,
                   primal_feasibility_tolerance=FEASIBILITY_TOLERANCE,
                   dual_feasibility_tolerance=FEASIBILITY_TOLERANCE)
    meta = dict(scipy_version=scipy.__version__, numpy_version=np.__version__, highs_version=_highs_version(),
                solver='scipy.optimize.linprog/HiGHS', solver_options=options,
                threadpool_limit=1, time_limit_seconds=float(time_limit),
                fit_population=n, supplied_population=len(x0), n_experts=k,
                selection_mode=('ALL_SUPPLIED_ROWS_NO_SUBSAMPLING' if training_indices is None
                                else 'EXPLICIT_INDICES_NO_SUBSAMPLING'),
                training_indices_sha256=_hash(ix), fit_experts_sha256=_hash(x),
                fit_targets_sha256=_hash(y), feasibility_tolerance=FEASIBILITY_TOLERANCE,
                objective_relative_tolerance=OBJECTIVE_RELATIVE_TOLERANCE,
                warnings=[], risk_guarantee=False, independent_confirmation=False,
                training_cost_not_above_best_expert_numerically=False,
                solver_optimal=False, numerical_evidence_verified=False,
                no_automatic_subsampling=True, objective_units='kWh-equivalent per selected cell',
                uncovered_cap=uncovered_cap, uncovered_cap_units='same as S/action: mean kW',
                actual_mean_uncovered_power=None,
                uncovered_constraint_representation='sum(u)/N <= cap; equivalent sum(u)<=N*cap')
    residual = dict(weight_sum_error=None, max_bound_violation=None,
                    max_inequality_violation=None, max_primal_violation=None,
                    uncovered_cap_violation=None, slack_cap_violation=None)
    if not n:
        meta['elapsed_seconds'] = time.perf_counter()-started
        return StaticConvexResult(None, 'UNDEFINED_POPULATION', False, None,
                                  None, None, residual, 'No historical fitting cells', meta,
                                  uncovered_cap=uncovered_cap)
    with np.errstate(over='ignore', invalid='ignore'):
        coefficient = np.r_[np.sum(x/(6*n), axis=0), np.full(n, RHO/(6*n))]
        expert_cost = np.mean((x+RHO*np.maximum(y[:, None]-x, 0))*DT_HOURS, axis=0)
        expert_uncovered = np.mean(np.maximum(y[:, None]-x, 0), axis=0)
    if not np.isfinite(coefficient).all() or not np.isfinite(expert_cost).all():
        raise ValueError('Historical LP coefficients or reference costs overflowed')
    # No dense N-by-(K+N) matrix is constructed.
    inequalities = sparse.hstack((-sparse.csr_matrix(x), -sparse.eye(n, format='csr')), format='csr')
    inequality_rhs = -y
    if uncovered_cap is not None:
        cap_row = sparse.csr_matrix((np.full(n, 1./n),
                      (np.zeros(n, dtype=np.int64), k+np.arange(n))), shape=(1,k+n))
        inequalities = sparse.vstack((inequalities, cap_row), format='csr')
        inequality_rhs = np.r_[-y, uncovered_cap]
    equality = sparse.csr_matrix((np.ones(k), (np.zeros(k, dtype=np.int64), np.arange(k))),
                                 shape=(1, k+n))
    eligible = np.ones(k, dtype=bool) if uncovered_cap is None else expert_uncovered <= uncovered_cap
    best_eligible = float(expert_cost[eligible].min()) if eligible.any() else None
    meta.update(best_single_expert_cost=best_eligible,
                best_unconstrained_single_expert_cost=float(expert_cost.min()),
                single_expert_comparison_scope='same optional uncovered cap, no event-risk screen',
                feasible_single_expert_indices=np.flatnonzero(eligible).tolist(),
                per_expert_mean_uncovered_power=expert_uncovered.tolist(),
                per_expert_training_costs=expert_cost.tolist(), lp_variables=n+k,
                lp_inequalities=int(inequalities.shape[0]), lp_nonzeros=int(inequalities.nnz),
                setup_seconds=time.perf_counter()-started)
    caught = []
    solver_started = time.perf_counter()
    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            with threadpool_limits(limits=1):
                solved = linprog(coefficient, A_ub=inequalities, b_ub=inequality_rhs,
                                 A_eq=equality, b_eq=np.ones(1), bounds=(0., None),
                                 method='highs', options=options)
    except Exception as exc:
        meta['warnings'] = [dict(category=type(w.message).__name__, message=str(w.message)) for w in caught]
        meta.update(solver_seconds=time.perf_counter()-solver_started,
                    elapsed_seconds=time.perf_counter()-started)
        return StaticConvexResult(None, 'SOLVER_ERROR', False, None, None, None,
                                  residual, repr(exc), meta, uncovered_cap=uncovered_cap)
    meta['warnings'] = [dict(category=type(w.message).__name__, message=str(w.message)) for w in caught]
    meta.update(solver_seconds=time.perf_counter()-solver_started,
                solver_iterations=getattr(solved, 'nit', None))
    solver_status = int(solved.status)
    message = str(solved.message)
    solver_optimal = solver_status == 0 and bool(solved.success)
    meta['solver_optimal'] = solver_optimal
    fun = getattr(solved, 'fun', None)
    solver_objective = float(fun) if fun is not None and np.isfinite(fun) else None
    weights = None
    objective = None
    feasible = False
    numeric = False
    actual_uncovered = None
    values = getattr(solved, 'x', None)
    if values is not None:
        values = np.asarray(values, dtype=np.float64)
        if values.shape == (k+n,) and np.isfinite(values).all():
            raw_w, slack = values[:k], values[k:]
            action = np.sum(x*raw_w[None, :], axis=-1)
            objective = _cost(action, y)
            actual_uncovered = float(np.mean(np.maximum(y-action, 0)))
            eq_error = float(abs(raw_w.sum()-1.))
            bound_error = float(max(0., -values.min()))
            inequality_error = float(max(0., np.max(y-action-slack)))
            actual_cap_error = (0. if uncovered_cap is None else max(0., actual_uncovered-uncovered_cap))
            slack_cap_error = (0. if uncovered_cap is None else max(0., float(slack.mean())-uncovered_cap))
            primal = max(eq_error, bound_error, inequality_error, actual_cap_error, slack_cap_error)
            residual.update(weight_sum_error=eq_error, max_bound_violation=bound_error,
                            max_inequality_violation=max(inequality_error, slack_cap_error), max_primal_violation=primal,
                            uncovered_cap_violation=(None if uncovered_cap is None else actual_cap_error),
                            slack_cap_violation=(None if uncovered_cap is None else slack_cap_error))
            feasible = (primal <= FEASIBILITY_TOLERANCE and (raw_w >= 0).all()
                        and np.isfinite(objective))
            objective_tol = OBJECTIVE_RELATIVE_TOLERANCE*max(1., abs(objective),
                                                          0. if best_eligible is None else abs(best_eligible))
            objective_gap = (abs(objective-solver_objective) if solver_objective is not None else float('inf'))
            excess = None if best_eligible is None else float(objective-best_eligible)
            numeric = bool(feasible and objective_gap <= objective_tol
                           and (excess is None or excess <= objective_tol))
            meta.update(raw_weights=raw_w.tolist(), objective_tolerance=objective_tol,
                        recomputed_minus_best_expert=excess,
                        actual_mean_uncovered_power=actual_uncovered,
                        objective_reconciliation_error=(objective_gap if np.isfinite(objective_gap) else None))
            if feasible:
                weights = np.array(raw_w, copy=True)
                weights.setflags(write=False)
    optimal = bool(solver_optimal and numeric)
    meta['numerical_evidence_verified'] = bool(numeric)
    meta['training_cost_not_above_best_expert_numerically'] = (optimal if best_eligible is not None
                                                             else None if optimal else False)
    if optimal:
        status = 'OPTIMAL'
    elif solver_status == 0:
        status = 'OPTIMAL_NUMERIC_UNRESOLVED'
    elif solver_status == 1:
        status = 'TIME_LIMIT' if 'time' in message.lower() else 'ITERATION_OR_RESOURCE_LIMIT'
        if feasible:
            status += '_FEASIBLE_INCUMBENT'
    else:
        status = {2:'INFEASIBLE', 3:'UNBOUNDED', 4:'NUMERICAL_FAILURE'}.get(
            solver_status, 'SOLVER_STATUS_'+str(solver_status))
        if feasible:
            status += '_FEASIBLE_INCUMBENT'
    meta['elapsed_seconds'] = time.perf_counter()-started
    return StaticConvexResult(weights, status, optimal, solver_status, objective,
                              solver_objective, residual, message, meta, actual_uncovered, uncovered_cap)


def predict_static(experts: np.ndarray, weights: np.ndarray) -> np.ndarray:
    """Apply a historical fixed simplex weight vector without targets or masks.

    No normalization or clipping is performed. The same explicit numerical
    simplex tolerance used by fitting is checked before the fixed prediction.
    """
    x, w = np.asarray(experts, dtype=np.float64), np.asarray(weights, dtype=np.float64)
    if (x.ndim < 1 or x.shape[-1] == 0 or w.shape != (x.shape[-1],)
            or not np.isfinite(x).all() or np.any(x < 0)
            or not np.isfinite(w).all() or np.any(w < 0)
            or abs(w.sum()-1.) > FEASIBILITY_TOLERANCE):
        raise ValueError('Invalid finite expert actions or fixed simplex weights')
    with np.errstate(over='ignore', invalid='ignore'):
        result = np.sum(x*w, axis=-1)
    if not np.isfinite(result).all():
        raise FloatingPointError('Nonfinite fixed convex prediction')
    return result
