"""Post-hoc algebraic necessary condition, not a new selected control policy."""
from pathlib import Path
import json

import numpy as np


def uniform_extra_bound(delta_R, event_rate):
    """At most delta_R*V unmet-energy reduction for constant extra reserve.

    U(r)-U(r+d)=E[min((S-r)+,d)]/6 <= (d/6)P(S>r).
    d>=0 and nonnegative baseline reserve imply extra mean R=d/6.
    No evaluation-period margin is fitted or used for scoring by this bound.
    """
    dr, v = np.asarray(delta_R, float), np.asarray(event_rate, float)
    if dr.shape != v.shape or not np.isfinite(dr).all() or not np.isfinite(v).all() or np.any((v < 0) | (v > 1)):
        raise ValueError("Invalid reserve/event summaries")
    feasible = dr >= 0
    return feasible, np.where(feasible, dr * v, np.nan)


def main():
    here = Path(__file__).resolve().parent
    summary = json.loads((here / "summary.json").read_text())
    with np.load(here / "evidence/results/aggregate/day_totals.npz") as a:
        n = a["N"].sum()
        r, u, v = (a[k].sum(axis=-1) / n for k in ("R", "U", "V"))
    records = {}
    for recipe in ("Original", "Common"):
        for est in ("HGB", "MLP"):
            p = summary["labels"].index(f"{recipe}:{est}:OP6")
            z = summary["labels"].index(f"{recipe}:{est}:OPZ6")
            dr, du = r[:, z] - r[:, p], u[:, p] - u[:, z]
            feasible, cap = uniform_extra_bound(dr, v[:, p])
            records[f"{recipe}:{est}"] = dict(seeds=list(range(201, 206)), extra_R=dr.tolist(),
                observed_U_decrease=du.tolist(), baseline_event_rate=v[:, p].tolist(),
                nonnegative_extra_budget_feasible=feasible.tolist(),
                uniform_extra_purchase_U_decrease_upper=[float(x) if ok else None for x, ok in zip(cap, feasible)],
                excess_over_upper=[float(d - c) if ok else None for d, c, ok in zip(du, cap, feasible)],
                all_five_finite_window_excesses_positive=bool(feasible.all() and np.all(du > cap)))
    out = dict(status="POST_HOC_FINITE_WINDOW_ALGEBRAIC_CHECK_ONLY", records=records,
        scope="No statistical confirmation, no Bayes information claim, no prediction/calibration refit. Rules out only constant nonnegative additive purchase within each fixed instance's realized average reserve increment in this observed cohort, not adaptive power-only policies.",
        new_evaluation_policy_constructed=False, new_thresholds=False,
        primary_frozen_596_coordinate_conclusions_unchanged=True)
    target = here / "additional_purchase_bound.json"
    blob = json.dumps(out, indent=2)
    if target.exists():
        if target.read_text(encoding="utf-8") != blob:
            raise ValueError("Existing algebraic audit differs; preserve it and use a new version")
    else:
        target.write_text(blob, encoding="utf-8", newline="\n")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
