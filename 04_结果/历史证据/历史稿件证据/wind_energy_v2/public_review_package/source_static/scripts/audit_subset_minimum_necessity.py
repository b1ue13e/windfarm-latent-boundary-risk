"""Distinguish certified sufficiency from exclusion of all smaller policies."""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import tarfile

import numpy as np


def diagnose(risk_lower, risk_upper, ratio_lower, resources, chosen, epsilon, cap=.1):
    """Audit necessity after the frozen selector has certified sufficiency."""
    lo, hi = np.asarray(risk_lower, float), np.asarray(risk_upper, float)
    lower = np.asarray(ratio_lower, dtype=float)
    lower = np.where(np.isnan(lower), -np.inf, lower)
    order = [tuple(r) for r in resources]
    if lo.ndim != 2 or lo.shape != hi.shape or lower.shape != (len(order), len(order)) or lo.shape[1] != len(order):
        raise ValueError("Invalid necessity audit dimensions")
    if np.isnan(lo).any() or np.isnan(hi).any() or epsilon < 0:
        raise ValueError("Invalid necessity audit observations")
    if not chosen:
        return dict(status="NO_CERTIFIED_SUFFICIENT_POLICY", chosen=[], smaller=[], excluded=[], unresolved=[])
    minimum = order[chosen[0]]
    if any(order[m] != minimum or np.any(hi[:, m] > cap) for m in chosen):
        raise ValueError("Chosen policies are not equally resourced and risk-qualified")
    smaller = [j for j, r in enumerate(order) if r < minimum]
    # Historical nonqualification cannot rule out true risk feasibility.
    feasible_witnesses = np.flatnonzero(np.all(hi <= cap, axis=0))
    excluded, unresolved = [], []
    for j in smaller:
        bad_seeds = np.flatnonzero(lo[:, j] > cap)
        if len(bad_seeds):
            excluded.append(dict(index=j, reason="RISK_LOWER_ABOVE_CAP", witness_seed_indices=bad_seeds.tolist()))
            continue
        witnesses = [int(k) for k in feasible_witnesses if lower[j, k] > epsilon]
        if witnesses:
            k = max(witnesses, key=lambda k: lower[j, k])
            excluded.append(dict(index=j, reason="COST_LOWER_EXCEEDS_MARGIN_VS_FEASIBLE", witness_policy=k,
                                 ratio_lower=float(lower[j, k])))
        else:
            unresolved.append(j)
    return dict(status="FINITE_FAMILY_MINIMUM_IDENTIFIED" if not unresolved else "MINIMUM_UNRESOLVED",
                chosen=chosen, smaller=smaller, excluded=excluded, unresolved=unresolved)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--addendum", type=Path, required=True)
    p.add_argument("--guard", type=Path, required=True)
    args = p.parse_args()
    before = sha(args.input)
    data = json.loads(args.input.read_text(encoding="utf-8"))
    args.output.mkdir(exist_ok=False, parents=True)
    results, rows = [], []
    for group in data["results"]:
        for analysis in ("primary_historical_recipe", "secondary_retrospective_grid"):
            if analysis.startswith("primary"):
                indices = np.array([c["index"] for c in group["historical_choices"]])
            else:
                indices = np.arange(len(group["labels"]))
            labels = [group["labels"][i] for i in indices]
            for selection in group[analysis]:
                result = diagnose(np.asarray(group["risk_lower"])[:, indices], np.asarray(group["risk_upper"])[:, indices],
                       np.asarray(group["relative_ratio_lower"], dtype=float)[np.ix_(indices, indices)],
                       [group["resources"][i] for i in indices], selection["minimum_resource_indices"], selection["epsilon"])
                metadata = dict(condition=group["condition"], budget=group["budget"], span=group["span"],
                                analysis=analysis, epsilon=selection["epsilon"])
                results.append(dict(**metadata, **result, labels=labels))
                rows.append(dict(**metadata, status=result["status"], sufficient_policies=";".join(labels[i] for i in result["chosen"]),
                     smaller_count=len(result["smaller"]), excluded_count=len(result["excluded"]),
                     unresolved_smaller=";".join(labels[i] for i in result["unresolved"])))
    (args.output / "necessity.json").write_text(json.dumps(dict(results=results, scope="Only frozen finite family, condition/budget, five instances, epsilon and approximate joint bounds. Not all models or information-theoretic minimality."), indent=2), encoding="utf-8")
    with (args.output / "necessity.csv").open("x", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    if sha(args.input) != before:
        raise ValueError("Input changed during derived audit")
    receipt = dict(status="DERIVED_NECESSITY_AUDIT", input_sha256=before, source_sha256=sha(__file__),
                   addendum_sha256=sha(args.addendum), utc=datetime.now(timezone.utc).isoformat(), argv=sys.argv,
                   before_evaluation_guard_sha256=sha(args.guard),
                   python=sys.version, numpy=np.__version__, original_training_selection_and_results_unchanged=True)
    (args.output / "receipt.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    with tarfile.open(args.output / "necessity_evidence.tar.gz", "x:gz") as t:
        for name in ("necessity.json", "necessity.csv", "receipt.json"):
            t.add(args.output / name, arcname=name)
        t.add(Path(__file__), arcname="source.py")
        t.add(args.addendum, arcname="pre_result_addendum.md")
        t.add(args.guard, arcname="before_evaluation_guard.json")


if __name__ == "__main__":
    main()
