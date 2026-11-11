"""Independent specification and feature checks for a frozen pilot audit."""
from __future__ import annotations

import ast
from repo_paths import Path, repository_root

import numpy as np


def original_b_expression(source: Path, pair_pass):
    """Evaluate only the trusted repository's pure B Boolean expression."""
    tree = ast.parse(source.read_text(encoding="utf-8"))
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "aggregate")
    assignments = [n for n in ast.walk(function) if isinstance(n, ast.Assign)
                   and any(isinstance(t, ast.Name) and t.id == "B" for t in n.targets)]
    if len(assignments) != 1:
        raise ValueError("Ambiguous legacy B expression")
    expression = ast.Expression(body=assignments[0].value)
    return bool(eval(compile(expression, str(source), "eval"), {"__builtins__": {}}, {"pair_pass": pair_pass}))


def specified_b(pair_pass):
    """PLAN §3: update cost gates; only two explicitly named severity guards."""
    return bool(pair_pass("old_state", low=.01, severity=False)
        and pair_pass("old_power", low=.01, severity=False)
        and pair_pass("P_premium_vs_Z", high=.01, severity=False)
        and pair_pass("residual_state", high=.01, severity=False)
        and pair_pass("severity_P_vs_Z") and pair_pass("severity_P_vs_PZ"))


def independent_features(data, anchors, forecast, cell, flat_rows):
    """Construct requested time/node rows directly, without arrived_history."""
    if cell not in ("F", "FZ", "O6", "OP6", "OZ6", "OPZ6"):
        raise ValueError("Unknown cell")
    rows = np.asarray(flat_rows, dtype=np.int64)
    nn = data.shape[1]
    times = anchors[rows // nn]
    nodes = rows % nn
    f = forecast[rows // nn, nodes]
    age = 0 if cell in ("F", "FZ") else 6
    phase = 2 * np.pi * (times % 144) / 144
    pieces = [f, np.sin(phase), np.cos(phase), nodes / max(nn - 1, 1)]
    for channel in range(3):
        for lag in range(35, -1, -1):
            pieces.append(data[times - lag, nodes, channel] if lag >= age
                          else np.full(len(rows), np.nan))
    p = np.column_stack([data[times - age - lag, nodes, 1] for lag in range(5, -1, -1)]).astype(float)
    mean = np.mean(p, axis=1)
    # Direct least-squares covariance form, independently of the main builder.
    slope = np.sum(p * (np.arange(6) - 2.5), axis=1) / 17.5
    last = data[times - age, nodes, 1]
    pieces += [mean, np.std(p, axis=1, ddof=0), slope,
               last - data[times - age - 1, nodes, 1], last - data[times - age - 6, nodes, 1], f - last]
    if cell in ("OP6", "OPZ6"):
        current = data[times, nodes, 1]
        pieces += [current, f - current, current - last]
    if cell in ("FZ", "OZ6", "OPZ6"):
        pieces.append(data[times, nodes, 3])
    return np.column_stack(pieces).astype(np.float32)


def deficit_profile(shortfall, reserve, mask):
    """Describe magnitudes without changing the registered strict event rule."""
    margin = np.asarray(shortfall, float)[mask] - np.asarray(reserve, float)[mask]
    edges = (0., .01, .1, 1., 10., np.inf)
    counts = [int(np.sum((margin > lo) & (margin <= hi))) for lo, hi in zip(edges[:-1], edges[1:])]
    return dict(cells=len(margin), strict_events=int(np.sum(margin > 0)),
                positive_deficit_bins_kw=["(0,.01]", "(.01,.1]", "(.1,1]", "(1,10]", "(10,inf)"],
                counts=counts, descriptive_only=True, registered_rule="S > r unchanged")
