"""One-shot I/O dependency: submit schema audit after two opaque downloads.

This login-node helper never imports a CSV/ZIP/numerical library or opens test
measurements; the actual qualification runs on a PBS allocation.
"""
from pathlib import Path
import argparse
from datetime import datetime, timezone
import json
import subprocess
import time


def ready(source):
    for year in (2023, 2024):
        if (source / f"failure_{year}.json").exists():
            raise RuntimeError("Historical source acquisition failed: " + str(year))
        if not (source / f"receipt_{year}.json").is_file():
            return False
    return True


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--binding", type=Path, required=True)
    p.add_argument("--binding-sha256", required=True)
    args = p.parse_args()
    start = time.monotonic()
    while not ready(args.source):
        if time.monotonic() - start > 6 * 3600:
            raise TimeoutError("No historical measurement audit started; download dependency timed out")
        time.sleep(30)
    command = ["qsub", "-v", f"QUALIFY_ROOT={args.root},QUALIFY_SOURCE={args.source},QUALIFY_BINDING={args.binding},QUALIFY_BINDING_SHA={args.binding_sha256}",
               "-o", str(args.root / "qualification.log"), str(args.root / "run_lf.pbs")]
    job = subprocess.check_output(command, text=True).strip()
    record = dict(submitted_utc=datetime.now(timezone.utc).isoformat(), job=job, command=command,
                  sealed_test_opened=False)
    with (args.root / "qualification_job.json").open("x", encoding="utf-8") as f:
        json.dump(record, f, indent=2)
    print(json.dumps(record), flush=True)


if __name__ == "__main__":
    main()
