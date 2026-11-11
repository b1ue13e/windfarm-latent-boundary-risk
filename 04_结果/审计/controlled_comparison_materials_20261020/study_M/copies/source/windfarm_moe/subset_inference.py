"""Memory-bounded paired inference for the predeclared finite subset study."""
from __future__ import annotations

import numpy as np
from .risk_frontier import shared_block_draws


def streamed_envelopes(groups, n_boot, span, seed, alpha, chunk_size=256):
    """Joint max-standardized envelope across all groups, risks and cost ratios.

    Groups contain seed/candidate/day totals, shared day counts, and optional
    algebraically exact ratio coordinates. No seed or turbine resampling.
    """
    if not groups or not 0 < alpha < 1 or chunk_size < 1:
        raise ValueError("Invalid envelope request")
    counts = np.asarray(groups[0]["counts"], float)
    if counts.ndim != 1 or not np.isfinite(counts).all() or np.any(counts < 0) or counts.sum() <= 0:
        raise ValueError("Invalid day counts")
    weights, drawhash = shared_block_draws(len(counts), n_boot, span, seed)
    denom = weights @ counts
    if np.any(denom <= 0):
        raise ValueError("Empty resampled target population")
    maxima = np.zeros(n_boot)
    records, ncoord = [], 0

    def measure(point, draws, exact):
        sd = draws.std(axis=0, ddof=1)
        varying = (sd > 1e-14) & ~exact
        if varying.any():
            maxima[:] = np.maximum(maxima, np.max(np.abs((draws[:, varying] - point[varying]) / sd[varying]), axis=1))
        return sd, ~(varying | exact)

    for g in groups:
        c, v = np.asarray(g["costs"], float), np.asarray(g["violations"], float)
        if c.ndim != 3 or c.shape != v.shape or c.shape[2] != len(counts) or not np.array_equal(counts, g["counts"]):
            raise ValueError("Unpaired groups or invalid seed/candidate/day totals")
        if not np.isfinite(c).all() or not np.isfinite(v).all() or np.any(c < 0) or np.any(v < 0) or np.any(v > counts):
            raise ValueError("Invalid observed cost or violation totals")
        ns, nk, nd = c.shape
        exact = np.asarray(g.get("exact_pair", np.eye(nk, dtype=bool)), bool)
        if exact.shape != (nk, nk) or not np.all(exact.diagonal()):
            raise ValueError("Invalid algebraic ratio identity")
        cost = c.mean(axis=0).sum(axis=-1) / counts.sum()
        dc = (weights @ c.mean(axis=0).T) / denom[:, None]
        if np.any(cost <= 0) or np.any(dc <= 0):
            raise ValueError("Relative cost undefined for nonpositive costs")
        rp = v.sum(axis=-1) / counts.sum()
        rsd, runknown = np.empty(rp.size), np.empty(rp.size, bool)
        flat_v = v.reshape(-1, nd)
        for start in range(0, rp.size, chunk_size):
            stop = min(start + chunk_size, rp.size)
            draws = (weights @ flat_v[start:stop].T) / denom[:, None]
            rsd[start:stop], runknown[start:stop] = measure(rp.ravel()[start:stop], draws, np.zeros(stop - start, bool))
        ratio = cost[:, None] / cost[None, :] - 1
        ratio[exact] = 0.0
        sd, unknown = np.empty(nk * nk), np.empty(nk * nk, bool)
        for start in range(0, nk * nk, chunk_size):
            pair = np.arange(start, min(start + chunk_size, nk * nk))
            left, right = pair // nk, pair % nk
            draws = dc[:, left] / dc[:, right] - 1
            draws[:, exact.ravel()[pair]] = 0.0
            sd[pair], unknown[pair] = measure(ratio.ravel()[pair], draws, exact.ravel()[pair])
        records.append(dict(mean_cost=cost, mean_cost_ci_low=np.quantile(dc, .025, axis=0),
                            mean_cost_ci_high=np.quantile(dc, .975, axis=0), risk_point=rp,
                            risk_sd=rsd.reshape(rp.shape), risk_unknown=runknown.reshape(rp.shape),
                            ratio_point=ratio, ratio_sd=sd.reshape(nk, nk), ratio_unknown=unknown.reshape(nk, nk), exact=exact))
        ncoord += rp.size + nk * nk
    critical = float(np.quantile(maxima, 1 - alpha, method="higher"))
    output = []
    for r in records:
        lo, hi = r["risk_point"] - critical * r["risk_sd"], r["risk_point"] + critical * r["risk_sd"]
        lo[r["risk_unknown"]], hi[r["risk_unknown"]] = 0, 1
        lower, upper = r["ratio_point"] - critical * r["ratio_sd"], r["ratio_point"] + critical * r["ratio_sd"]
        lower[r["ratio_unknown"]], upper[r["ratio_unknown"]] = -np.inf, np.inf
        lower[r["exact"]], upper[r["exact"]] = 0, 0
        output.append(dict(mean_cost=r["mean_cost"], mean_cost_ci_low=r["mean_cost_ci_low"],
                           mean_cost_ci_high=r["mean_cost_ci_high"], risk_point=r["risk_point"],
                           risk_lower=np.clip(lo, 0, 1), risk_upper=np.clip(hi, 0, 1),
                           relative_ratio_point=r["ratio_point"], relative_ratio_lower=lower, relative_ratio_upper=upper))
    return dict(groups=output, critical=critical, draw_sha256=drawhash, coordinate_family_size=ncoord,
                coverage="Approximate shared-day-block envelope, conditional on frozen seed instances")
