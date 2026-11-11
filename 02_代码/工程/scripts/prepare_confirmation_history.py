"""Build a historical coordinate function only from provably equal copies.

The original strict row-uniqueness failure stays unchanged. Any conflicting
consumed value rejects the entire adapter run; no preferred row is selected.
This entry point never opens 2025.zip or overwrites original archives.
"""
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


def equal_values(left, right):
    return np.all((left == right) | (np.isnan(left) & np.isnan(right)), axis=-1)


def add_equal_copies(indices, values, seen, storage):
    """Resolve equal representations; reject all within/across-chunk conflicts."""
    indices, values = np.asarray(indices), np.asarray(values, dtype=np.float64)
    order = np.argsort(indices, kind="stable")
    ids, x = indices[order], values[order]
    repeated = ids[1:] == ids[:-1]
    if np.any(repeated & ~equal_values(x[1:], x[:-1])):
        raise ValueError("Conflicting consumed observations inside a coordinate group")
    keep = np.r_[True, ~repeated]
    ids, x = ids[keep], x[keep]
    known = seen[ids]
    if np.any(known & ~equal_values(storage[ids], x)):
        raise ValueError("Conflicting consumed observations across files/chunks/years")
    extra = int(len(indices) - np.sum(~known))
    storage[ids[~known]] = x[~known]
    seen[ids] = True
    return extra


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--qualifier", type=Path, required=True)
    p.add_argument("--binding", type=Path, required=True)
    p.add_argument("--binding-sha256", required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    if not os.environ.get("PBS_JOBID"):
        raise ValueError("Real historical coordinate preparation needs allocated node")
    spec = importlib.util.spec_from_file_location("unchanged_strict_qualifier", args.qualifier)
    q = importlib.util.module_from_spec(spec);spec.loader.exec_module(q)
    if q.digest(args.binding) != args.binding_sha256:
        raise ValueError("Pre-acquisition source binding mismatch")
    binding = json.loads(args.binding.read_text(encoding="utf-8"))
    args.output.mkdir(exist_ok=False, parents=True)
    receipt = dict(status="RUNNING_LOSSLESS_HISTORICAL_ADAPTER", started_utc=datetime.now(timezone.utc).isoformat(),
            source_sha256=q.digest(__file__), qualifier_sha256=q.digest(args.qualifier), binding_sha256=args.binding_sha256,
            python=sys.version, numpy=np.__version__, pandas=pd.__version__, host=platform.node(),
            pbs_job_id=os.environ["PBS_JOBID"], argv=sys.argv, original_strict_row_uniqueness_failure_preserved=True,
            strict_raw_row_uniqueness_passed=False, test_archive_2025_opened=False, input_sha256={}, tables={})
    q.save(args.output / "receipt.json", receipt)
    start, end = [pd.Timestamp(s, tz="UTC").value for s in ("2023-01-01", "2025-01-01")]
    step = 600 * 10**9
    nt = int((end - start) // step) + 1
    values = {t: np.full((nt * 21, len(fields)), np.nan) for t, fields in q.TABLES.items()}
    seen = {t: np.zeros(nt * 21, bool) for t in q.TABLES}
    counts = {t: dict(raw_rows=0, redundant_equal_copies=0, schemas=[], station_ids_by_year={}) for t in q.TABLES}
    try:
        for year in (2023, 2024):
            q.historical_year(year)
            archive = args.source / f"{year}.zip"
            acq = json.loads((args.source / f"receipt_{year}.json").read_text(encoding="utf-8"))
            bound = next(f for f in binding["archives"] if f["year"] == year)
            before = q.digest(archive)
            if acq["sha256"] != before or acq["official_md5"] != bound["official_md5"] or archive.stat().st_size != bound["bytes"]:
                raise ValueError("Acquired historical archive identity mismatch")
            base = int((pd.Timestamp(f"{year}-01-01", tz="UTC").value - start) // step) * 21
            with zipfile.ZipFile(archive) as z:
                for table, fields in q.TABLES.items():
                    station_ids = set()
                    for month in range(1, 13):
                        members = [n for n in z.namelist() if Path(n).name == f"{table}_{year}_{month:02d}.csv"]
                        if len(members) != 1:
                            raise ValueError("Ambiguous historical monthly table")
                        with z.open(members[0]) as f:header = q.read_header(f, table)
                        counts[table]["schemas"].append(dict(year=year, month=month, schema=header))
                        with z.open(members[0]) as f:
                            for frame in pd.read_csv(f, sep=header["delimiter"], encoding=header["encoding"],
                                    usecols=["TimeStamp", header["station"], *fields], chunksize=100000):
                                index, ids = q.coordinates(frame, year, header["station"])
                                station_ids.update(ids.tolist())
                                x = np.column_stack([pd.to_numeric(frame[c], errors="raise").to_numpy(dtype=float) for c in fields])
                                counts[table]["raw_rows"] += len(index)
                                counts[table]["redundant_equal_copies"] += add_equal_copies(index + base, x, seen[table], values[table])
                    if station_ids != set(range(2304510, 2304531)):
                        raise ValueError("Not all 21 registered turbines present in historical table/year")
                    counts[table]["station_ids_by_year"][year] = sorted(station_ids)
            if q.digest(archive) != before:
                raise ValueError("Protected archive changed")
            receipt["input_sha256"][str(archive)] = before
            print("HISTORICAL_YEAR_CONSISTENT", year, flush=True)
        data = np.full((nt * 21, 4), np.nan)
        turbine, grid = values["tblSCTurbine"], values["tblSCTurGrid"]
        data[:, 0] = np.where(np.isfinite(turbine[:, 0]) & (turbine[:, 0] >= 0), turbine[:, 0], np.nan)
        data[:, 1:3] = np.where(np.isfinite(grid), grid, np.nan)
        pitch_valid = np.isfinite(turbine[:, 1:4]).all(axis=1)
        data[pitch_valid, 3] = turbine[pitch_valid, 1:4].mean(axis=1)
        data = data.reshape(nt, 21, 4)
        times = start + np.arange(nt, dtype=np.int64) * step
        phase_counts = {}
        for name, first, last, horizon in [("point_fit", "2023-01-01", "2023-07-01", 12),
              ("policy_fit", "2023-07-01", "2024-01-01", 6), ("offset_fit", "2024-01-01", "2024-07-01", 6),
              ("selection", "2024-07-01", "2025-01-01", 6)]:
            lo, hi = [int((pd.Timestamp(s, tz="UTC").value - start) // step) for s in (first, last)]
            anchors = np.arange(max(lo, 35), hi - horizon - 1)
            phase_counts[name] = int(np.isfinite(data[anchors + horizon, :, 1]).sum())
        if phase_counts["point_fit"] < 120000 or phase_counts["policy_fit"] < 360000:
            raise ValueError("Insufficient pre-bound historical training observations")
        for table in counts:
            counts[table]["unique_physical_coordinates"] = int(seen[table].sum())
            counts[table]["absent_grid_coordinates"] = int((~seen[table]).sum())
            if counts[table]["raw_rows"] - counts[table]["redundant_equal_copies"] != int(seen[table].sum()):
                raise ValueError("Representation multiplicity did not close")
        np.save(args.output / "historical_physical_channels.npy", data)
        np.save(args.output / "historical_time_end_ns.npy", times)
        receipt.update(status="HISTORICAL_COORDINATE_FUNCTION_QUALIFIED", finished_utc=datetime.now(timezone.utc).isoformat(),
              tables=counts, phase_finite_target_counts=phase_counts, shape=list(data.shape),
              columns=["wind", "power", "reactive", "pitch"], consumed_value_conflicts=0,
              negative_power_preserved=int(np.sum(np.isfinite(data[..., 1]) & (data[..., 1] < 0))),
              interval_boundary="2024 archive may contain 2025-01-01T00:00 period-END of the last 2024 interval. This is historical issue context, never a future scored target or a read of 2025.zip.",
              scope="Historical source coordinates only; original raw-row uniqueness failure remains. Not independent model confirmation or 2025 schema qualification.")
    except BaseException as exc:
        receipt.update(status="HISTORICAL_ADAPTER_REJECTED_DATA_GAP", error=repr(exc), finished_utc=datetime.now(timezone.utc).isoformat())
        q.save(args.output / "receipt.json", receipt)
        raise
    q.save(args.output / "receipt.json", receipt)
    q.save(args.output / "manifest.json", {p.name: dict(bytes=p.stat().st_size, sha256=q.digest(p)) for p in args.output.iterdir() if p.is_file() and p.name != "manifest.json"})


if __name__ == "__main__":
    main()
