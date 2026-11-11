"""Read-only diagnosis of historical duplicate coordinates; no row removal."""
import argparse
from datetime import datetime, timezone
import importlib.util
import json
import os
from repo_paths import Path, repository_root
import platform
import sys
import zipfile

import numpy as np
import pandas as pd


def classify_duplicates(frame, fields):
    duplicate = frame.loc[frame.duplicated("coordinate", keep=False)]
    if duplicate.empty:
        return dict(rows=len(frame), unique_coordinates=len(frame), extra_rows=0,
                    duplicate_groups=0, conflicting_groups=0, conflicting_examples=[])
    grouped = duplicate.groupby("coordinate", sort=True)
    varying = grouped[fields].nunique(dropna=False)
    conflict = varying.index[(varying > 1).any(axis=1)]
    examples = []
    for key in list(conflict[:10]):
        part = duplicate.loc[duplicate["coordinate"] == key]
        examples.append(dict(coordinate=int(key), months=part["month"].tolist(),
                             differing_fields=varying.columns[varying.loc[key] > 1].tolist()))
    return dict(rows=len(frame), unique_coordinates=int(frame["coordinate"].nunique()),
                extra_rows=int(frame.duplicated("coordinate").sum()), duplicate_groups=int(len(grouped)),
                conflicting_groups=len(conflict), conflicting_examples=examples,
                within_one_month_groups=int((grouped["month"].nunique() == 1).sum()),
                all_consumed_values_numerically_identical=not len(conflict))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--qualifier", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    if not os.environ.get("PBS_JOBID"):
        raise ValueError("Historical measurement diagnosis requires allocated node")
    spec = importlib.util.spec_from_file_location("frozen_strict_source_qualifier", args.qualifier)
    q = importlib.util.module_from_spec(spec);spec.loader.exec_module(q)
    args.output.mkdir(exist_ok=False, parents=True)
    record = dict(status="RUNNING", started_utc=datetime.now(timezone.utc).isoformat(), years={},
                  source_sha256=q.digest(__file__), qualifier_sha256=q.digest(args.qualifier),
                  python=sys.version, pandas=pd.__version__, numpy=np.__version__, host=platform.node(),
                  pbs_job_id=os.environ["PBS_JOBID"], argv=sys.argv, test_2025_opened=False,
                  rows_removed=0, original_failed_qualification_unchanged=True)
    q.save(args.output / "receipt.json", record)
    for year in (2023, 2024):
        q.historical_year(year)
        archive = args.source / f"{year}.zip"
        receipt = json.loads((args.source / f"receipt_{year}.json").read_text(encoding="utf-8"))
        before = q.digest(archive)
        if before != receipt["sha256"]:
            raise ValueError("Acquired input mismatch")
        tables = {}
        with zipfile.ZipFile(archive) as z:
            for table, fields in q.TABLES.items():
                frames = []
                for month in range(1, 13):
                    members = [n for n in z.namelist() if Path(n).name == f"{table}_{year}_{month:02d}.csv"]
                    if len(members) != 1:
                        raise ValueError("Ambiguous historical table")
                    with z.open(members[0]) as f:header = q.read_header(f, table)
                    with z.open(members[0]) as f:
                        for frame in pd.read_csv(f, sep=header["delimiter"], encoding=header["encoding"],
                              usecols=["TimeStamp", header["station"], *fields], chunksize=100000):
                            index, ids = q.coordinates(frame, year, header["station"])
                            small = pd.DataFrame({"coordinate": index, "month": month})
                            for field in fields:
                                small[field] = pd.to_numeric(frame[field], errors="raise").to_numpy(dtype=float)
                            frames.append(small)
                tables[table] = classify_duplicates(pd.concat(frames, ignore_index=True), fields)
                print("DUPLICATE_DIAGNOSIS", year, table, tables[table], flush=True)
        if q.digest(archive) != before:
            raise ValueError("Input changed during read-only diagnosis")
        record["years"][year] = dict(input_sha256=before, tables=tables)
        q.save(args.output / "receipt.json", record)
    record.update(status="DUPLICATES_DIAGNOSED_NOT_QUALIFIED", finished_utc=datetime.now(timezone.utc).isoformat())
    q.save(args.output / "receipt.json", record)


if __name__ == "__main__":
    main()
