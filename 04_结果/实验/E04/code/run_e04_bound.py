"""Run an E04 command and emit a bound receipt only for complete outputs.

Usage example:
  python run_e04_bound.py --bundle results/run1 \
    --preregistration experiments/E04/PREREGISTRATION_E04_V2.json \
    --input cache=artifacts/cache_wtb/metadata.json \
    --output seed201_full_policy_day_blocks.npz \
    -- python replay_e04.py --seed 201
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from e04_provenance import (
    write_execution_plan,
    write_execution_receipt,
    write_output_manifest,
)


def parse_input(value: str) -> tuple[str, Path]:
    role, separator, path = value.partition("=")
    if not separator or not role or not path:
        raise argparse.ArgumentTypeError("inputs must use ROLE=PATH")
    return role, Path(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--preregistration", type=Path, required=True)
    parser.add_argument("--input", dest="inputs", action="append", type=parse_input, default=[])
    parser.add_argument("--output", dest="outputs", action="append", required=True)
    parser.add_argument("--git-commit", default=None)
    parser.add_argument("--working-dir", type=Path, default=Path.cwd())
    raw_args = sys.argv[1:]
    if "--" not in raw_args:
        parser.error("a command is required after --")
    separator = raw_args.index("--")
    args = parser.parse_args(raw_args[:separator])
    args.command = raw_args[separator + 1:]
    if not args.command:
        parser.error("a command is required after --")

    bundle = args.bundle.resolve()
    inputs = [("preregistration", args.preregistration.resolve()), *args.inputs]
    output_paths = [bundle / name for name in args.outputs]
    plan = write_execution_plan(
        bundle,
        argv=args.command,
        inputs=inputs,
        output_names=args.outputs,
        git_commit=args.git_commit,
        working_dir=args.working_dir,
        metadata={"wrapper": "run_e04_bound.py"},
    )
    completed = subprocess.run(args.command, cwd=args.working_dir, check=False)
    if completed.returncode != 0:
        print(f"E04 command failed with exit code {completed.returncode}; no EXECUTED receipt written", file=sys.stderr)
        return completed.returncode or 1
    missing = [str(path) for path in output_paths if not path.is_file()]
    if missing:
        print("E04 command exited 0 but declared outputs are missing: " + ", ".join(missing), file=sys.stderr)
        return 2
    manifest = write_output_manifest(bundle, output_paths)
    receipt = write_execution_receipt(
        bundle,
        argv=args.command,
        inputs=inputs,
        output_manifest=manifest,
        exit_code=completed.returncode,
        git_commit=args.git_commit,
        plan_path=plan,
        metadata={"wrapper": "run_e04_bound.py", "working_dir": str(args.working_dir.resolve())},
    )
    print(f"E04 EXECUTED receipt={receipt} manifest={manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
