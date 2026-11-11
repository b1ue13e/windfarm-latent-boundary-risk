"""Independent arithmetic replay of the new subset study's stored raw actions."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import importlib.util
import json
from repo_paths import Path, repository_root
import platform
import sys

import numpy as np


def direct_totals(shortfall, raw, offset, valid, anchors):
    """Reconstruct all block fields without the producer's accounting function."""
    r = np.maximum(np.asarray(raw, dtype=np.float64) + offset, 0)
    s = np.asarray(shortfall, dtype=np.float64)
    loss = np.zeros(s.shape, np.float64)
    loss[valid] = (r[valid] + 10 * np.maximum(s[valid] - r[valid], 0)) * (1 / 6)
    grids = {"count": valid, "loss_sum": loss, "reserve_sum": np.where(valid, r / 6, 0),
             "shortage_sum": np.where(valid, np.maximum(s - r, 0) / 6, 0), "violation_sum": valid & (s > r)}
    days = np.asarray(anchors) // 144
    ids = np.unique(days)
    return {"block_ids": ids, **{k: np.array([v[days == d].sum(dtype=np.float64) for d in ids]) for k, v in grids.items()}}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--study-root", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    import os
    if not os.environ.get("PBS_JOBID"):
        raise ValueError("Real archived-action replay requires allocated PBS node")
    entry = args.study_root / "scripts/run_information_subset_study.py"
    spec = importlib.util.spec_from_file_location("frozen_subset_action_producer", entry)
    producer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(producer)
    protocol = args.study_root / "experiments/information_subset_development_20261019/protocol.json"
    cfg = json.loads(protocol.read_text(encoding="utf-8"))
    m, prepared, data, original = producer.parent(cfg)
    with np.load(prepared / "development_evaluation_forecast.npz") as a:
        anchors, forecast = a["anchors"], a["forecast"].astype(np.float64)
        if not np.array_equal(a["target_indices"], anchors + 6):
            raise ValueError("Target identity mismatch")
    realized = data[anchors + 6, :, 1].astype(np.float64)
    valid = np.isfinite(realized)
    shortfall = np.full(valid.shape, np.nan)
    shortfall[valid] = np.maximum(forecast[valid] - realized[valid], 0)
    args.output.mkdir(exist_ok=False, parents=True)
    checks, checked = 0, []
    expected_identity = producer.identity(dict(anchors=anchors, forecast=forecast.astype(np.float32), true=realized,
                                               mask=valid, shortfall=shortfall))
    for index, task in enumerate(producer.tasks(cfg)):
        root = args.study_root / "results/evaluate" / str(index)
        receipt = producer.verify(root, protocol, "evaluate", task)
        metadata = json.loads((root / "metadata.json").read_text(encoding="utf-8"))
        if metadata["stage_identity"] != expected_identity:
            raise ValueError("Archived actions target/coordinate mismatch")
        with np.load(root / "evaluation_blocks.npz") as totals:
            for budget in task["budgets"]:
                with np.load(root / f"evaluation_raw_{budget}.npz") as a:
                    raw, offsets = a["raw"], a["offsets"]
                if raw.shape != shortfall.shape or not np.isfinite(raw).all() or np.any(raw < 0):
                    raise ValueError("Invalid raw reserve array")
                for qi, offset in enumerate(offsets):
                    expected = direct_totals(shortfall, raw, offset, valid, anchors)
                    for key, values in expected.items():
                        if not np.array_equal(values, totals[f"{budget}__{qi}__{key}"]):
                            raise ValueError(f"Exact action-accounting failure: {index}/{budget}/{qi}/{key}")
                        checks += 1
        checked.append(dict(task_index=index, manifest_sha256=producer.sha(root / "manifest.json")))
        if index % 50 == 0:
            print("ACTION_AUDIT_TASK", index, checks, flush=True)
    producer.save(args.output / "audit.json", dict(status="ALL_NEW_ACTION_ARRAYS_EXACT", array_checks=checks,
                   tasks=len(checked), checked=checked, source_sha256=producer.sha(__file__),
                   protocol_sha256=producer.sha(protocol), coordinate_identity=expected_identity,
                   python=sys.version, numpy=np.__version__, host=platform.node(), pbs_job_id=os.environ["PBS_JOBID"],
                   finished_utc=datetime.now(timezone.utc).isoformat(), argv=sys.argv,
                   scope="Arithmetic identity of new archived actions only; no scientific or deployment certification"))


if __name__ == "__main__":
    main()
