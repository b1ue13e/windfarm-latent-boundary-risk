"""Frozen-family weather-block inference for directly modelled array shortfall.

Five fits are fixed; natural weather days are the only resampling unit. This
module deliberately has no dependency on the old 35-day inference campaign.
"""
from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Mapping, Sequence
import numpy as np

SEEDS = tuple(range(201, 206))
METRICS = ("C", "R", "U", "V")
THRESHOLDS = dict(important_cost_gain=.01, cost_noninferiority=.01,
                  H_U=.001, absolute_risk=.10, alpha=.05)


def conjunction(values):
    if any(x is False for x in values):
        return False
    return None if any(x is None for x in values) else True


def decision(row, threshold, strict=False):
    if row["status"] not in ("ESTIMABLE_APPROX", "EXACT_ALGEBRAIC_ZERO"):
        return None
    lo, hi = row["lower"], row["upper"]
    if hi is not None and (hi < threshold if strict else hi <= threshold):
        return True
    if lo is not None and (lo >= threshold if strict else lo > threshold):
        return False
    return None


def bootstrap_calendar(n_days, *, span, n_boot=20000, seed=20261030):
    if n_days < 1 or span not in (1, 3, 7) or n_boot < 2:
        raise ValueError("Invalid registered weather calendar or draws")
    starts = np.random.default_rng(seed).integers(0, n_days, (n_boot, math.ceil(n_days/span)))
    indices = ((starts[..., None] + np.arange(span)) % n_days).reshape(n_boot, -1)[:, :n_days]
    weights = np.bincount((np.arange(n_boot)[:, None]*n_days+indices).ravel(),
                          minlength=n_boot*n_days).reshape(n_boot, n_days)
    return indices, weights


def historical_definitions(names):
    definitions = []
    for name in names:
        for seed in SEEDS:
            definitions.append(dict(id=f"HV:{name}:{seed}", kind="absolute_risk", left=name,
                                    right=None, metric="V", fit=seed))
        for seed in SEEDS:
            definitions.append(dict(id=f"HH:{name}:{seed}", kind="paired_severity", left=name,
                                    right="P_G", metric="H_U", fit=seed))
        definitions.append(dict(id=f"HD:{name}", kind="paired_mean", left=name,
                                right="P_G", metric="D", fit=None))
    return definitions


def normalize_definitions(rows):
    out = []
    for source in rows:
        row = dict(source)
        row["fit"] = None if row.get("fit") in (None, "", "None") else int(row["fit"])
        row["right"] = None if row.get("right") in (None, "", "None") else row["right"]
        if row["kind"] == "regime_selected_increment":
            row["regime"] = row["id"].split(":")[1]
        out.append(row)
    if len({r["id"] for r in out}) != len(out):
        raise ValueError("Duplicate nominal endpoint")
    return out


def _array_hash(array, dtype="<f8"):
    return hashlib.sha256(np.ascontiguousarray(array, dtype=dtype).tobytes()).hexdigest()


def infer_group_family(ledger, counts, names: Sequence[str], definitions, *, cstar,
                       span=3, seed=20261030, n_boot=20000, available=None, aliases=(),
                       regime_ledgers=None, regime_counts=None):
    """Infer fixed definitions, preserving unavailable and undefined endpoints.

    ledger has [5 fits, roles, days, C/R/U/V] daily sums. Regime ledgers have
    the same shape, with their own counts. A signed H_U reads U, never C.
    """
    data = np.asarray(ledger, dtype=np.float64)
    count = np.asarray(counts, dtype=np.float64)
    names = list(names)
    definitions = normalize_definitions(definitions)
    if (data.ndim != 4 or data.shape[0] != 5 or data.shape[1] != len(names)
            or data.shape[3] != 4 or count.shape != (data.shape[2],)
            or len(set(names)) != len(names) or not np.isfinite(count).all()
            or np.any(count < 0) or np.any(count != np.floor(count))):
        raise ValueError("Invalid fixed-fit group ledger/population")
    if not np.isfinite(cstar) or cstar <= 0:
        raise ValueError("Historical group Cstar must be finite and strictly positive")
    availability = [True]*len(names) if available is None else list(available)
    if len(availability) != len(names) or any(not isinstance(v, (bool, np.bool_)) for v in availability):
        raise ValueError("Explicit role availability differs")
    availability = [bool(v) for v in availability]
    indices, weights = bootstrap_calendar(len(count), span=span, n_boot=n_boot, seed=seed)
    parent = list(range(len(names)))

    def find(i):
        while parent[i] != i:
            i = parent[i]
        return i

    alias_records = []
    for left, right in aliases:
        l, r = names.index(left), names.index(right)
        if not availability[l] or not availability[r]:
            alias_records.append(dict(left=left, right=right, verified=False, reason="SOURCE_UNAVAILABLE"))
            continue
        if not np.array_equal(data[:, l], data[:, r]):
            raise ValueError("Complete five-fit alias ledger differs")
        for regime in (regime_ledgers or {}):
            rg = np.asarray(regime_ledgers[regime])
            if not np.array_equal(rg[:, l], rg[:, r]):
                raise ValueError("Complete alias regime ledger differs")
        parent[find(l)] = find(r)
        alias_records.append(dict(left=left, right=right, verified=True,
                                  reason="INDEPENDENT_PROGRAM_BINDING_AND_COMPLETE_LEDGER_EQUALITY"))

    regimes = {}
    for regime, values in (regime_ledgers or {}).items():
        rc = np.asarray((regime_counts or {})[regime], dtype=np.float64)
        rd = np.asarray(values, dtype=np.float64)
        if rd.shape != data.shape or rc.shape != count.shape or np.any(rc < 0) or not np.isfinite(rc).all():
            raise ValueError("Invalid regime population")
        regimes[regime] = (rd, rc)

    def source_values(source, source_count, definition):
        l = names.index(definition["left"])
        r = None if definition["right"] is None else names.index(definition["right"])
        metric = definition["metric"]
        col = 0 if metric == "D" else 2 if metric == "H_U" else METRICS.index(metric)
        fits = list(range(5)) if definition["fit"] is None else [SEEDS.index(definition["fit"])]
        if not availability[l] or (r is not None and not availability[r]):
            return None, None, "SOURCE_UNAVAILABLE", 0, False
        inputs = [source[fits, l, :, col]] + ([] if r is None else [source[fits, r, :, col]])
        if any(not np.isfinite(v).all() or np.any(v < 0) for v in inputs):
            return None, None, "SOURCE_INVALID", 0, False
        if metric == "V" and any(np.any(v > source_count) or np.any(v != np.floor(v)) for v in inputs):
            return None, None, "SOURCE_INVALID", 0, False
        if any(np.any((v != 0) & (source_count == 0)) for v in inputs):
            return None, None, "SOURCE_INVALID", 0, False
        observed_n = float(source_count.sum())
        if observed_n == 0:
            return None, None, "ZERO_OBSERVED_DENOMINATOR", 0, False
        daily = source[fits, l, :, col].copy()
        if r is not None:
            daily -= source[fits, r, :, col]
        daily = daily.mean(axis=0)
        denominator = weights @ source_count
        observed_den = observed_n
        invalid = denominator == 0
        if metric == "D":
            baseline = source[:, r, :, 0].mean(axis=0)
            if not np.isfinite(baseline).all() or np.any(baseline < 0):
                return None, None, "SOURCE_INVALID", 0, False
            observed_den = float(baseline.sum())
            if observed_den == 0:
                return None, None, "ZERO_OBSERVED_COST_DENOMINATOR", 0, False
            denominator = weights @ baseline
            invalid = invalid | (denominator == 0)
        scale = 10./cstar if metric == "H_U" else 1.
        point = float(scale*daily.sum()/observed_den)
        n_invalid = int(invalid.sum())
        if n_invalid:
            return point, None, "ZERO_DRAW_DENOMINATOR", n_invalid, False
        exact = r is not None and find(l) == find(r)
        if exact:
            return 0., np.zeros(n_boot), "EXACT_ALGEBRAIC_ZERO", 0, True
        samples = scale*(weights @ daily)/denominator
        if not np.isfinite(samples).all() or not np.isfinite(point):
            return point if np.isfinite(point) else None, None, "NUMERIC_UNRESOLVED", 0, False
        return point, samples, "DEFINED", 0, False

    rows, samples_list = [], []
    for d in definitions:
        domain = [0., 1.] if d["metric"] == "V" and d["right"] is None else [-1., 1.] if d["metric"] == "V" else [None, None]
        if d["kind"] == "direct_regime_interaction" and d["metric"] == "V":
            domain = [-2., 2.]
        row = dict(id=d["id"], definition=d.copy(), point=None, lower=domain[0], upper=domain[1],
                   domain=domain, standard_error=None, exact=False, status="SOURCE_UNAVAILABLE", n_invalid_draws=0)
        if d["kind"] == "direct_regime_interaction":
            if "high" not in regimes or "low" not in regimes:
                values = (None, None, "REGIME_UNAVAILABLE", 0, False)
            else:
                hi = source_values(*regimes["high"], d)
                lo = source_values(*regimes["low"], d)
                point = None if hi[0] is None or lo[0] is None else hi[0]-lo[0]
                if hi[1] is None or lo[1] is None:
                    values = (point, None, hi[2] if hi[1] is None else lo[2], max(hi[3], lo[3]), False)
                else:
                    exact = hi[4] and lo[4]
                    values = (point, hi[1]-lo[1], "EXACT_ALGEBRAIC_ZERO" if exact else "DEFINED", 0, exact)
        elif d["kind"] == "regime_selected_increment":
            values = source_values(*regimes[d["regime"]], d) if d["regime"] in regimes else (None, None, "REGIME_UNAVAILABLE", 0, False)
        else:
            values = source_values(data, count, d)
        point, sample, status, invalid, exact = values
        row.update(point=point, status=status, n_invalid_draws=invalid, exact=exact)
        use = None
        if status == "EXACT_ALGEBRAIC_ZERO":
            row.update(point=0., lower=0., upper=0., standard_error=0.)
        elif sample is not None:
            sd = float(np.std(sample, ddof=1))
            row["standard_error"] = sd
            if not np.isfinite(sd):
                row["status"] = "NUMERIC_UNRESOLVED"
            elif sd <= 1e-14:
                row["status"] = "ZERO_EMPIRICAL_VARIANCE"
            else:
                row["status"] = "ESTIMABLE_APPROX"
                use = sample
        rows.append(row)
        samples_list.append(use)
    usable = [i for i, x in enumerate(rows) if x["status"] == "ESTIMABLE_APPROX"]
    critical = None
    if usable:
        maxima = np.zeros(n_boot)
        for i in usable:
            maxima = np.maximum(maxima, np.abs(samples_list[i]-rows[i]["point"])/rows[i]["standard_error"])
        critical = float(np.quantile(maxima, .95, method="higher"))
        for i in usable:
            row = rows[i]; width = critical*row["standard_error"]
            row["lower"] = max(-np.inf if row["domain"][0] is None else row["domain"][0], row["point"]-width)
            row["upper"] = min(np.inf if row["domain"][1] is None else row["domain"][1], row["point"]+width)
    source = hashlib.sha256()
    source.update(np.ascontiguousarray(data, dtype="<f8").tobytes())
    source.update(np.ascontiguousarray(count, dtype="<f8").tobytes())
    source.update(json.dumps(dict(names=names, available=availability), sort_keys=True).encode())
    return dict(schema="pitch-group-inference-v1", policy_names=names, available=availability,
                coordinates=rows, definitions=definitions, family_size=len(rows),
                thresholds=THRESHOLDS.copy(), Cstar_G=float(cstar), critical_value=critical,
                span=span, n_boot=int(n_boot), resampling_seed=int(seed), n_days=len(count),
                n_observed_groups=float(count.sum()), fixed_fit_ids=list(SEEDS),
                bootstrap_indices_sha256=_array_hash(indices, "<i8"),
                bootstrap_weights_sha256=_array_hash(weights, "<i8"), source_sha256=source.hexdigest(),
                alias_verification=alias_records, estimable_coordinates=len(usable),
                independent_confirmation=False, selection_adjusted=False, coverage_certified=False,
                production_draw_specification=n_boot == 20000 and seed == 20261030,
                inference_target="Fixed five fits conditional on the realized online trajectory; shared weather-day approximation")


def historical_qualification(inference, names):
    lookup = {x["id"]: x for x in inference["coordinates"]}
    out = {}
    for name in names:
        cost = decision(lookup[f"HD:{name}"], .01)
        h = conjunction([decision(lookup[f"HH:{name}:{s}"], .001) for s in SEEDS])
        risk = conjunction([decision(lookup[f"HV:{name}:{s}"], .10) for s in SEEDS])
        out[name] = dict(qualified=conjunction([cost, h, risk]), cost_noninferior=cost,
                         five_instance_H_U_noninferior=h, absolute_risk_qualified=risk)
    return out


def comparison_labels(inference, pairs):
    lookup = {x["id"]: x for x in inference["coordinates"]}
    risk = {}
    for name in inference["policy_names"]:
        risk[name] = conjunction([decision(lookup[f"Q:{name}:V:{s}"], .10) for s in SEEDS])
    rows = []
    for j, pair in enumerate(pairs):
        left, right = pair["left"], pair["right"]
        d = lookup[f"E:{j}:D"]
        h = conjunction([decision(lookup[f"E:{j}:H_U:{s}"], .001) for s in SEEDS])
        u = decision(lookup[f"E:{j}:U"], 0., True)
        v = decision(lookup[f"E:{j}:V"], 0., True)
        ni = decision(d, .01); gain = decision(d, -.01, True)
        r = decision(lookup[f"E:{j}:R"], 0.)
        qualified = [h, risk[left], risk[right]]
        rows.append(dict(left=left, right=right, important_cost_gain=gain,
            cost_noninferiority=ni, U_benefit=u, V_benefit=v, nonincrease_R=r,
            five_instance_H_U_noninferiority=h, left_absolute_risk_qualified=risk[left],
            right_absolute_risk_qualified=risk[right],
            COST_IMPORTANT=conjunction([gain]+qualified),
            PROTECTION=conjunction([ni,u,v]+qualified),
            GROUP_PRIMARY_GO=conjunction([r, (True if True in [conjunction([gain]+qualified),conjunction([ni,u,v]+qualified)] else None if None in [conjunction([gain]+qualified),conjunction([ni,u,v]+qualified)] else False)])))
    return dict(absolute_risk=risk, comparisons=rows)
