"""Qualify historical years only; this entry point refuses the sealed test."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import csv
import hashlib
import io
import json
from pathlib import Path
import platform
import shutil
import sys
import zipfile

import numpy as np
import pandas as pd

TABLES = {
    "tblSCTurbine": ["wtc_AcWindSp_mean", "wtc_PitcPosA_mean", "wtc_PitcPosB_mean", "wtc_PitcPosC_mean"],
    "tblSCTurGrid": ["wtc_ActPower_mean", "wtc_ReactPwr_mean"],
}


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False), encoding="utf-8")


def historical_year(year):
    if year not in (2023, 2024):
        raise ValueError("This qualification entry point must never open sealed 2025")


def inspect_header(raw, table):
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        encoding = "utf-16"
    else:
        encoding = "utf-8-sig"
    line = raw.decode(encoding).splitlines()[0]
    delimiter = csv.Sniffer().sniff(line, delimiters=",;\t").delimiter
    columns = next(csv.reader([line], delimiter=delimiter))
    if len(columns) != len(set(columns)):
        raise ValueError("Duplicate source column names")
    station = [c for c in ("StationId", "StationNr") if c in columns]
    if len(station) != 1 or "TimeStamp" not in columns or any(c not in columns for c in TABLES[table]):
        raise ValueError("Required field or unambiguous join key missing: " + table + " " + repr(columns))
    return dict(encoding=encoding, delimiter=delimiter, station=station[0], fields=TABLES[table], columns=columns)


def read_header(handle, table):
    prefix = handle.read(4)
    handle.seek(0)
    encoding = "utf-16" if prefix.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig"
    text = io.TextIOWrapper(handle, encoding=encoding).readline()
    return inspect_header(text.encode(encoding), table)


def coordinates(frame, year, station):
    historical_year(year)
    times = pd.to_datetime(frame["TimeStamp"], format="ISO8601", utc=True, errors="raise")
    # pandas versions may expose datetime64[us]; explicitly obtain ns resolution.
    ns = times.to_numpy(dtype="datetime64[ns]").astype(np.int64)
    if np.any(ns % (600 * 10**9)):
        raise ValueError("Timestamps off the UTC 10-minute grid")
    start, end = [pd.Timestamp(f"{y}-01-01", tz="UTC").value for y in (year, year + 1)]
    if np.any(ns < start) or np.any(ns > end):
        raise ValueError("Measurement timestamp outside bound calendar year")
    ids = pd.to_numeric(frame[station], errors="raise").to_numpy(dtype=float)
    if not np.isfinite(ids).all() or np.any(ids != np.floor(ids)) or np.any((ids < 2304510) | (ids > 2304530)):
        raise ValueError("Unknown or noninteger turbine station ID")
    index = ((ns - start) // (600 * 10**9)) * 21 + ids.astype(np.int64) - 2304510
    return index, ids.astype(np.int64)


def audit_year(archive, year, output):
    historical_year(year)
    first, last = [pd.Timestamp(f"{y}-01-01", tz="UTC").value for y in (year, year + 1)]
    # Permit exact next-year midnight because source times mark period END.
    # This audits source coordinates; model stage issue windows stay half-open.
    expected = int(((last - first) // (600 * 10**9) + 1) * 21)
    result = dict(year=year, archive_sha256=digest(archive), expected_time_node_cells=expected, tables={})
    with zipfile.ZipFile(archive) as z:
        names = z.namelist()
        for table, fields in TABLES.items():
            seen = np.zeros(expected, bool)
            stations, months, nonfinite = set(), [], {c: 0 for c in fields}
            negative = {c: 0 for c in fields}
            rows = 0
            schema = None
            for month in range(1, 13):
                matches = [n for n in names if Path(n).name == f"{table}_{year}_{month:02d}.csv"]
                if len(matches) != 1:
                    raise ValueError("Need exactly one bound monthly table: " + repr(matches))
                member = matches[0]
                with z.open(member) as f:
                    # Only the historical header is read at this stage.
                    header = read_header(f, table)
                if schema is None:
                    schema = header
                elif {k: v for k, v in header.items() if k != "columns"} != {k: v for k, v in schema.items() if k != "columns"}:
                    raise ValueError("Historical schema changed across months")
                nrows = 0
                with z.open(member) as f:
                    for frame in pd.read_csv(f, sep=header["delimiter"], encoding=header["encoding"],
                                             usecols=["TimeStamp", header["station"], *fields], chunksize=100000):
                        indices, ids = coordinates(frame, year, header["station"])
                        if len(np.unique(indices)) != len(indices) or seen[indices].any():
                            raise ValueError("Duplicate time/turbine coordinates; no automatic row deletion")
                        seen[indices] = True
                        stations.update(ids.tolist())
                        for col in fields:
                            a = pd.to_numeric(frame[col], errors="raise").to_numpy(dtype=float)
                            nonfinite[col] += int((~np.isfinite(a)).sum())
                            negative[col] += int(np.sum(np.isfinite(a) & (a < 0)))
                        nrows += len(frame)
                months.append(dict(member=member, rows=nrows))
                rows += nrows
            if stations != set(range(2304510, 2304531)):
                raise ValueError("Not all 21 registered historical turbines present")
            result["tables"][table] = dict(rows=rows, unique_cells=int(seen.sum()),
                  absent_grid_cells=int((~seen).sum()), nonfinite_observed=nonfinite,
                  negative_observed_preserved=negative, station_ids=sorted(stations), schema=schema, months=months)
    save(output / f"qualification_{year}.json", result)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--binding", type=Path, required=True)
    p.add_argument("--binding-sha256", required=True)
    args = p.parse_args()
    import os
    if not os.environ.get("PBS_JOBID"):
        raise ValueError("Real measurement qualification requires an allocated PBS node")
    if digest(args.binding) != args.binding_sha256:
        raise ValueError("Source binding differs from pre-acquisition freeze")
    binding = json.loads(args.binding.read_text(encoding="utf-8"))
    start = json.loads((args.source / "start_receipt.json").read_text(encoding="utf-8"))
    if start["binding_sha256"] != args.binding_sha256:
        raise ValueError("Actual acquisition used a different source binding")
    args.output.mkdir(exist_ok=False, parents=True)
    shutil.copyfile(__file__, args.output / "qualification_source.py")
    shutil.copyfile(args.binding, args.output / "source_binding.json")
    receipt = dict(status="RUNNING_HISTORICAL_QUALIFICATION", started_utc=datetime.now(timezone.utc).isoformat(),
                   python=sys.version, pandas=pd.__version__, numpy=np.__version__, host=platform.node(),
                   pbs_job_id=os.environ["PBS_JOBID"], argv=sys.argv, source_sha256=digest(__file__),
                   source_binding_sha256=args.binding_sha256,
                   protected_test_opened=False, years=[2023, 2024])
    save(args.output / "receipt.json", receipt)
    try:
        results = []
        for year in (2023, 2024):
            bound = json.loads((args.source / f"receipt_{year}.json").read_text(encoding="utf-8"))
            archive = args.source / f"{year}.zip"
            official = next(r for r in binding["archives"] if r["year"] == year)
            if bound["official_md5"] != official["official_md5"] or archive.stat().st_size != official["bytes"]:
                raise ValueError("Acquired file differs from official pre-bound archive")
            if bound["status"] != "OPAQUE_ARCHIVE_MD5_VERIFIED_CONTENT_UNOPENED" or digest(archive) != bound["sha256"]:
                raise ValueError("Historical archive is not the verified acquired source")
            results.append(audit_year(archive, year, args.output))
            if digest(archive) != bound["sha256"]:
                raise ValueError("Read-only historical input changed during qualification")
            shutil.copyfile(args.source / f"receipt_{year}.json", args.output / f"acquisition_receipt_{year}.json")
            print("QUALIFIED_HISTORICAL_YEAR", year, flush=True)
        receipt.update(status="HISTORICAL_SCHEMA_QUALIFIED_2025_STILL_SEALED",
                       finished_utc=datetime.now(timezone.utc).isoformat(), input_sha256={str(args.source / f"{y}.zip"): r["archive_sha256"] for y, r in zip((2023, 2024), results)})
    except BaseException as error:
        receipt.update(status="QUALIFICATION_FAILED_DATA_GAP", error=repr(error), finished_utc=datetime.now(timezone.utc).isoformat())
        save(args.output / "receipt.json", receipt)
        raise
    save(args.output / "receipt.json", receipt)
    save(args.output / "manifest.json", {p.name: dict(bytes=p.stat().st_size, sha256=digest(p))
                                         for p in args.output.iterdir() if p.is_file() and p.name != "manifest.json"})


if __name__ == "__main__":
    main()
