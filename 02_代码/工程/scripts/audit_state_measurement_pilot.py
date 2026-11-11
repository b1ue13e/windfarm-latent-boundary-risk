"""Independently reconstruct archived pilot actions and daily accounting."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from repo_paths import Path, repository_root
import sys

import numpy as np

ROOT = Path(repository_root())
sys.path.insert(0, str(ROOT))
from scripts.run_state_measurement_pilot import verify, sha, save, stage, tasks


def audit_actions(shortfall, anchors, mask, raw, calibrated, delta, archived):
    s, r, m = np.asarray(shortfall, float), np.asarray(calibrated, float), np.asarray(mask)
    if not np.array_equal(r, np.maximum(raw + delta, 0)):
        raise ValueError("Archived action/offset mismatch")
    days = np.asarray(anchors) // 144
    unique = np.unique(days)
    if not np.array_equal(unique, archived["days"]):
        raise ValueError("Archived days differ")
    ss, rr = s[m], r[m]
    blocks = np.broadcast_to((days - unique[0])[:, None], m.shape)[m]
    uncovered = np.maximum(ss - rr, 0) / 6
    values = {"N": np.ones(len(ss)), "V": ss > rr, "R": rr / 6,
              "U": uncovered, "C": rr / 6 + 10 * uncovered}
    maximum_mean_error = 0.
    for key, value in values.items():
        rebuilt = np.bincount(blocks, weights=value, minlength=len(unique))
        observed = archived[key]
        if key in ("N", "V"):
            if not np.array_equal(rebuilt, observed):
                raise ValueError("Exact archived count mismatch: " + key)
        else:
            error = np.abs(rebuilt - observed) / np.maximum(archived["N"], 1)
            tolerance = 1e-8 + 1e-10 * np.abs(observed) / np.maximum(archived["N"], 1)
            if np.any(error > tolerance):
                raise ValueError("Archived accounting mismatch: " + key)
            maximum_mean_error = max(maximum_mean_error, float(error.max()))
    return dict(checks=7, maximum_mean_absolute_error=maximum_mean_error)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    cfg = json.loads(args.protocol.read_text())
    verify(args.base / "prepared", args.protocol, "prepare")
    verify(args.base / "selection", args.protocol, "select")
    choices = json.loads((args.base / "selection/historical_choices.json").read_text())["choices"]
    z = stage(args.base / "prepared", "evaluation")
    audits, skipped = [], []
    for i, t in enumerate(tasks(cfg)):
        selected = choices[f'{t["estimator"]}:{t["cell"]}']
        if selected["q_index"] is None:
            skipped.append(dict(task=i, reason="NO_HISTORICAL_CHOICE"))
            continue
        p = args.base / "evaluation" / str(i)
        verify(p, args.protocol, "evaluate")
        with np.load(p / "actions.npz") as actions, np.load(p / "blocks.npz") as blocks:
            raw, calibrated = actions["raw"], actions["calibrated"]
            delta = json.loads((args.base / "fits" / str(i) / "offsets.json").read_text())[selected["q_index"]]
            for prefix, mask, a, b, offset in (("primary", z["primary_mask"], raw, calibrated, delta),
                    ("all_target_Zobs", z["target_mask"], raw, calibrated, delta),
                    ("raw_primary", z["primary_mask"], raw, raw, 0)):
                archived = {k: blocks[prefix + "__" + k] for k in ("C", "U", "R", "V", "N", "days")}
                audits.append(dict(task=i, population=prefix, **audit_actions(
                    z["shortfall"], z["anchors"], mask, a, b, offset, archived)))
    args.output.mkdir(parents=True, exist_ok=False)
    save(args.output / "audit.json", dict(status="PASS_ARCHIVED_ACTION_ACCOUNTING", audits=audits, skipped=skipped,
        records=len(audits), exact_and_tolerance_checks=sum(a["checks"] for a in audits),
        source_sha256=sha(__file__), protocol_sha256=sha(args.protocol), python=sys.version, numpy=np.__version__,
        pbs_job_id=os.environ.get("PBS_JOBID"), finished_utc=datetime.now(timezone.utc).isoformat(),
        scope="Reconstructs serialized actions and totals; no model refit or checkpoint prediction replay"))
    print("AUDIT PASS", len(audits), flush=True)


if __name__ == "__main__":
    main()
