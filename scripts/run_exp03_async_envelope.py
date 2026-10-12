"""EXP-03 protocol materialization and trace audit.

This runner intentionally does not invent PSREI results. It materializes a
frozen integer-step packet trace and mask for the Metis payload. A downstream
benchmark must provide paired baseline/challenger costs under that exact trace.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.exp03_async_packet_protocol import BufferPolicy, make_trace, replay_trace


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/exp03_async"))
    parser.add_argument("--steps", type=int, default=48)
    parser.add_argument("--max-lateness", type=int, default=2)
    args = parser.parse_args()
    if args.steps < 4:
        raise ValueError("steps must be >= 4")
    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    values = {
        "wspd": [float(8.0 + 0.05 * t) for t in range(args.steps)],
        "patv": [float(900.0 + 2.0 * t) for t in range(args.steps)],
        "etmp": [float(12.0 + 0.01 * t) for t in range(args.steps)],
    }
    delays = {
        "wspd": [0 if t % 5 else 2 for t in range(args.steps)],
        "patv": [1 if t % 7 else 3 for t in range(args.steps)],
        "etmp": [0 if t % 3 else 1 for t in range(args.steps)],
    }
    channels = tuple(values)
    packets = make_trace(values, delays, seed=20261012)
    trace_path = out / "arrival_trace.jsonl"
    with trace_path.open("w", encoding="utf-8", newline="\n") as handle:
        for packet in packets:
            handle.write(json.dumps(packet.__dict__, sort_keys=True) + "\n")
    snapshots = replay_trace(packets, channels, args.steps, BufferPolicy(args.max_lateness))
    mask = [{"time": row["time"], "mask": row["mask"]} for row in snapshots]
    (out / "missing_mask.json").write_text(json.dumps(mask, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    protocol = {
        "experiment": "EXP-03",
        "label": "synthetic asynchronous envelope",
        "time_unit": "integer dispatch step (10 minutes in the source protocol)",
        "fields": ["event_time", "arrival_time", "channel_id", "sequence_id"],
        "same_arrival_order": ["arrival_time", "sequence_id", "channel_id"],
        "causal_rule": "only arrival_time <= dispatch_time is visible",
        "future_backfill": False,
        "max_lateness": args.max_lateness,
        "drop_policy": "drop packets later than max_lateness; record missing mask",
        "operating_targets_violation_pct": [5, 10, 15],
        "primary_estimand": "PSREI-vs-delay curve and tau*",
        "industrial_prevalence_inference": False,
        "seed": 20261012,
    }
    (out / "protocol.json").write_text(json.dumps(protocol, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    digest = sha256_file(trace_path)
    (out / "input_trace_hash.txt").write_text(digest + "\n", encoding="ascii")
    print(json.dumps({"trace": str(trace_path), "packets": len(packets), "trace_sha256": digest}, indent=2))


if __name__ == "__main__":
    main()
