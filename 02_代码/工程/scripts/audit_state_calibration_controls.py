"""Reconstruct every serialized no-refit control and its daily accounting."""
from __future__ import annotations

import argparse
import json
from repo_paths import Path, repository_root
import shutil
import sys

import numpy as np
from threadpoolctl import threadpool_limits

ROOT = Path(repository_root())
sys.path.insert(0, str(ROOT))
from scripts.run_state_calibration_controls import (begin, finish, verify, context, stage, load_raw,
    worker_id, selected_q, CELLS, POLICIES, RECIPES, STATE_PAIRS)
from scripts.run_state_measurement_pilot import verify as verify_parent
from scripts.run_information_subset_study import sha, save
from scripts.audit_state_measurement_pilot import audit_actions


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--protocol", type=Path, required=True)
    p.add_argument("--base", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args(); args.stage = "audit"; args.worker = -1
    cfg = json.loads(args.protocol.read_text())
    parent, oldp, oldcfg = context(cfg)
    verify(args.base / "freeze", args, "freeze")
    verify_parent(parent / "prepared", oldp, "prepare")
    paths = [args.base / "evaluate" / str(w) for w in range(10)]
    for path in paths:
        verify(path, args, "evaluate")
    rec = begin(args, [args.base / "freeze/manifest.json", parent / "prepared/evaluation.npz"] + [path / "manifest.json" for path in paths])
    for name in ("scripts/audit_state_calibration_controls.py", "scripts/audit_state_measurement_pilot.py"):
        rec["source_sha256"][name] = sha(ROOT / name)
        dest = args.output / "source" / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, dest)
    frozen = json.loads((args.base / "freeze/frozen.json").read_text())
    z = stage(parent / "prepared", "evaluation")
    records = []
    with threadpool_limits(2):
        for w, path in enumerate(paths):
            est, seed = worker_id(cfg, w)
            raw, offsets = load_raw(parent, oldcfg, est, seed, "evaluation")
            shifts = json.loads((args.base / "history" / str(w) / "shifts.json").read_text())
            with np.load(path / "actions.npz") as actions, np.load(path / "blocks.npz") as blocks:
                for recipe in RECIPES:
                    for cell in POLICIES:
                        if cell in CELLS:
                            q = selected_q(frozen["original_choices"], est, cell, recipe, frozen["common_q_index"])
                            source, delta = raw[cell], offsets[cell][q]
                        else:
                            name = cell[len("Match_"):]
                            _, base, target = next(pair for pair in STATE_PAIRS if pair[0] == name)
                            pq = selected_q(frozen["original_choices"], est, base, recipe, frozen["common_q_index"])
                            zq = selected_q(frozen["original_choices"], est, target, recipe, frozen["common_q_index"])
                            source = actions[f"{recipe}|{base}"]
                            delta = shifts[f"{name}|{pq}|{zq}"]["delta_kw"]
                        r = actions[f"{recipe}|{cell}"]
                        for population, mask in (("primary", z["primary_mask"]), ("all_target", z["target_mask"])):
                            prefix = f"{recipe}|{cell}|{population}|"
                            observed = {key: blocks[prefix + key] for key in ("C", "R", "U", "V", "N", "days")}
                            check = audit_actions(z["shortfall"], z["anchors"], mask, source, r, delta, observed)
                            records.append(dict(worker=w, estimator=est, seed=seed, recipe=recipe,
                                                policy=cell, population=population, **check))
    if len(records) != 360:
        raise ValueError("Incomplete accounting audit")
    save(args.output / "audit.json", dict(status="ALL_SERIALIZED_TRANSFORMS_AND_ACCOUNTS_PASS", records=records,
        checks=sum(row["checks"] for row in records), groups=len(records),
        maximum_mean_error=max(row["maximum_mean_absolute_error"] for row in records),
        matched_rules_checked="Historical delta only; correct clip-after-calibrated-base; no evaluation re-matching",
        new_fits=0))
    finish(args, rec)


if __name__ == "__main__":
    main()
