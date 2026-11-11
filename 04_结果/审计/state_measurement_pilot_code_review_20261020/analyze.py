"""Audit original bounds/decisions and expose retained trade-offs; no refits."""
from pathlib import Path
import hashlib
import json

import numpy as np
from threadpoolctl import threadpool_limits

ROOT = Path(__file__).resolve().parents[2]
import sys
sys.path.insert(0, str(ROOT))
from windfarm_moe.state_measurement_review import specified_b, original_b_expression

HERE = Path(__file__).resolve().parent
PILOT = ROOT / "experiments/state_measurement_pilot_20261020"
PAIRS = [("fresh_state", "F", "FZ", "G"), ("old_state", "O6", "OZ6", "G"),
         ("old_power", "O6", "OP6", "G"), ("P_premium_vs_Z", "OP6", "OZ6", "D"),
         ("residual_state", "OP6", "OPZ6", "G"), ("severity_P_vs_Z", "OZ6", "OP6", "G"),
         ("severity_P_vs_PZ", "OPZ6", "OP6", "G")]


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def independent_envelope(arrays, summary, original):
    """Rebuild shared circular draws and all coordinates without pilot helpers."""
    c, v, u, n = (arrays[key] for key in ("C", "V", "U", "N"))
    nb, nd, span = original["n_boot"], len(n), 3
    generator = np.random.default_rng(20261031)
    starts = generator.integers(0, nd, size=(nb, (nd + span - 1) // span))
    idx = ((starts[:, :, None] + np.arange(span)) % nd).reshape(nb, -1)[:, :nd]
    weight = np.zeros((nb, nd))
    np.add.at(weight, (np.arange(nb)[:, None], idx), 1.)
    draw_hash = hashlib.sha256(idx.astype("<i8").tobytes()).hexdigest()
    if draw_hash != original["draw_sha256"]:
        raise ValueError("Independent draw identity failed")
    denom = weight @ n
    cost = c.sum(axis=2).mean(axis=0) / n.sum()
    cost_draws = weight @ c.mean(axis=0).T / denom[:, None]
    point = list((v.sum(axis=2) / n.sum()).ravel())
    draws = [weight @ v.reshape(-1, nd).T / denom[:, None]]
    labels = [("risk", seed, k) for seed in range(5) for k in range(len(summary["labels"]))]
    for estimator in ("HGB", "MLP"):
        for name, ca, cb, kind in PAIRS:
            a, b = [summary["labels"].index(estimator + ":" + cell) for cell in (ca, cb)]
            ref = a if kind == "G" else b
            point.append((cost[a] - cost[b]) / cost[ref])
            draws.append(((cost_draws[:, a] - cost_draws[:, b]) / cost_draws[:, ref])[:, None])
            labels.append((estimator + ":" + name, "cost", kind))
            delta = 10 * (u[:, b] - u[:, a]) / summary["Cstar"]
            point.extend(delta.sum(axis=1) / n.sum())
            draws.append(weight @ delta.T / denom[:, None])
            labels.extend((estimator + ":" + name, "severity_candidate_minus_reference", seed) for seed in range(5))
    point, draws = np.array(point), np.column_stack(draws)
    sd = draws.std(axis=0, ddof=1)
    variable = sd > 1e-14
    max_stat = np.max(np.abs((draws[:, variable] - point[variable]) / sd[variable]), axis=1)
    critical = np.quantile(max_stat, .95, method="higher")
    lo, hi = point - critical * sd, point + critical * sd
    lo[~variable], hi[~variable] = -np.inf, np.inf
    if [list(x) for x in labels] != original["labels"]:
        raise ValueError("Coordinate order or direction differs")
    errors = {}
    for name, actual in (("point", point), ("lower", lo), ("upper", hi)):
        expected = np.asarray(original[name], float)
        if not np.allclose(actual, expected, atol=1e-10, rtol=1e-10):
            raise ValueError("Independent inference mismatch: " + name)
        errors[name] = float(np.max(np.abs(actual - expected)))
    return dict(status="MATCHED", coordinates=len(point), n_boot=nb, span=span,
                draw_sha256=draw_hash, critical=float(critical), maximum_errors=errors,
                scope="Numerical reproduction only, not verification of dependent-bootstrap coverage")


def main():
    s = read(PILOT / "summary.json")
    env = read(PILOT / "development_envelopes.json")["3"]
    with np.load(PILOT / "evidence/results/aggregate/paired_day_totals.npz") as z:
        arrays = {k: z[k] for k in z.files}
    with threadpool_limits(2):
        inference = independent_envelope(arrays, s, env)
    decisions = {}
    for estimator in ("HGB", "MLP"):
        def check(name, low=None, high=None, severity=True):
            _, ca, cb, kind = next(pair for pair in PAIRS if pair[0] == name)
            v = s["registered_intervals"][f"{estimator}:{name}|cost|{kind}"]
            ok = s["risk_qualified"][f"{estimator}:{ca}"] and s["risk_qualified"][f"{estimator}:{cb}"]
            if low is not None:
                ok &= v["lower"] > low
            if high is not None:
                ok &= v["upper"] <= high
            if severity:
                ok &= all(s["registered_intervals"][f"{estimator}:{name}|severity_candidate_minus_reference|{seed}"]["upper"] <= .001 for seed in range(5))
            return bool(ok)
        old = original_b_expression(ROOT / "scripts/run_state_measurement_pilot.py", check)
        proper = specified_b(check)
        if old != s["outcomes"][estimator]["route_B"]:
            raise ValueError("Failed reproduction of original classifier")
        decisions[estimator] = dict(original_B=old, specified_B=proper,
                                    current_verdict_changed=old != proper)
    counterexample = lambda name, low=None, high=None, severity=True: not (
        name in ("old_state", "old_power") and severity)
    i, j = [s["labels"].index("HGB:" + cell) for cell in ("OP6", "OPZ6")]
    cost = s["registered_intervals"]["HGB:residual_state|cost|G"]
    h = [s["registered_intervals"][f"HGB:severity_P_vs_PZ|severity_candidate_minus_reference|{seed}"]
         for seed in range(5)]
    mean_u = arrays["U"].sum(axis=2).mean(axis=0) / arrays["N"].sum()
    mean_r = arrays["R"].sum(axis=2).mean(axis=0) / arrays["N"].sum()
    risk = {}
    nk = len(s["labels"])
    for k, label in enumerate(s["labels"]):
        lower = max(env["lower"][seed * nk + k] for seed in range(5))
        upper = max(env["upper"][seed * nk + k] for seed in range(5))
        risk[label] = dict(max_instance_lower=lower, max_instance_upper=upper,
            status="QUALIFIED" if upper <= .1 else "EVIDENCE_OF_EXCEEDANCE" if lower > .1 else "UNRESOLVED_QUALIFICATION")
    output = dict(inference_reproduction=inference, b_implementation_discrepancy=dict(
        unexpected_extra_guards=["U(OZ6)-U(O6)", "U(OP6)-U(O6)"],
        counterexample_original=original_b_expression(ROOT / "scripts/run_state_measurement_pilot.py", counterexample),
        counterexample_specified=specified_b(counterexample), current_data=decisions),
        retained_HGB_OP_to_OPZ=dict(cost_premium=dict(point=-cost["point"], lower=-cost["upper"], upper=-cost["lower"]),
            uncovered_before=float(mean_u[i]), uncovered_after=float(mean_u[j]),
            uncovered_reduction_relative=float(1 - mean_u[j] / mean_u[i]),
            reserve_before=float(mean_r[i]), reserve_after=float(mean_r[j]),
            reserve_increase_relative=float(mean_r[j] / mean_r[i] - 1),
            normalized_U_OP_minus_OPZ_mean=dict(point=float(np.mean([v["point"] for v in h])),
                lower=float(np.mean([v["lower"] for v in h])), upper=float(np.mean([v["upper"] for v in h]))),
            instances_exceeding_original_severity_tolerance_by_lower_bound=[seed + 201 for seed, v in enumerate(h) if v["lower"] > .001],
            scope="Post-hoc interpretation of original registered coordinates; no new selection or field qualification"),
        risk_status=risk, added_model_fits=0, new_measurements=0,
        original_source_sha256=hashlib.sha256((ROOT / "scripts/run_state_measurement_pilot.py").read_bytes().replace(b"\r\n", b"\n")).hexdigest())
    (HERE / "findings.json").write_text(json.dumps(output, indent=2), encoding="utf-8", newline="\n")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
