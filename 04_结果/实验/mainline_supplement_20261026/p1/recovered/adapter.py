"""Mainline 2026 adapter for fixed P1/HGB/q0.95 and WPQ36/HGB/q0.95 confirmation.

Strictly bounded to:
1. preflight: Validate legacy freeze/source/model hashes, task table and 2026 archive
   metadata without opening/listing/parsing 2026.zip.
2. evaluate: Require verified freeze and single explicit UNLOCK_EVENT before opening
   2026 Jan-Apr tblSCTurbine and tblSCTurGrid. Strictly no fit, no calibration,
   no outcome exclusions, reuse frozen point forecaster and legacy models/offsets.
3. aggregate: Evaluate exactly the two fixed policies across five fit instances (14 joint
   coordinates: 10 risks + 4 pairwise cost ratios) using streamed_envelopes (B=20000, span=3 primary, 1/7 sensitivity).
   Primary criterion: relative cost <= 2% and all 5-instance risks <= 0.10.
   H is descriptive only (may be UNKNOWN), never a gating criterion.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import importlib
import json
import os
from pathlib import Path
import platform
import sys
import zipfile

import joblib
import numpy as np
import pandas as pd
import sklearn
from threadpoolctl import threadpool_limits

STEP_NS = 600 * 10**9
START_NS = int(np.datetime64("2023-01-01", "ns").astype(np.int64))


def sha(path: Path | str) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def md5_file(path: Path | str) -> str:
    h = hashlib.md5()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def clean(value):
    if isinstance(value, np.ndarray):
        return clean(value.tolist())
    if isinstance(value, np.generic):
        return clean(value.item())
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [clean(v) for v in value]
    if isinstance(value, float) and not np.isfinite(value):
        return None
    return value


def save(path: Path, value: dict) -> None:
    path.write_text(json.dumps(clean(value), ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def load_json(path: Path | str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def begin(path: Path, args, cfg: dict, inputs: list[Path], stage: str) -> dict:
    import torch
    if path.exists() and any(path.iterdir()):
        raise FileExistsError(f"Incomplete stage preserved; refuse overwrite: {path}")
    path.mkdir(parents=True, exist_ok=True)
    info = dict(
        status="RUNNING",
        stage=stage,
        argv=sys.argv,
        started_utc=datetime.now(timezone.utc).isoformat(),
        protocol_sha256=sha(args.protocol),
        inputs={str(p.resolve()): sha(p) for p in inputs},
        adapter_sha256=sha(__file__),
        configuration=cfg,
        python=sys.version,
        numpy=np.__version__,
        pandas=pd.__version__,
        sklearn=sklearn.__version__,
        torch=torch.__version__,
        cuda_build=torch.version.cuda,
        backend="CPU only (2 threads)",
        pbs_job=os.environ.get("PBS_JOBID"),
        host=platform.node(),
        platform=platform.platform(),
        cpu=next((x.split(':',1)[1].strip() for x in Path('/proc/cpuinfo').read_text().splitlines()
                  if x.startswith('model name')),platform.processor()) if Path('/proc/cpuinfo').exists() else platform.processor(),
        seeds=cfg.get("seeds", [201, 202, 203, 204, 205]),
        primary_q=cfg.get("primary_q", 0.95),
        offset_index=cfg.get("offset_index", 2),
    )
    save(path / "receipt.json", info)
    return info


def finish(path: Path, receipt: dict) -> None:
    for name, value in receipt.get("inputs", {}).items():
        if sha(Path(name)) != value:
            raise ValueError(f"Protected input changed during run: {name}")
    receipt.update(status="COMPLETE", finished_utc=datetime.now(timezone.utc).isoformat())
    save(path / "receipt.json", receipt)
    manifest = {
        p.name: dict(bytes=p.stat().st_size, sha256=sha(p))
        for p in sorted(path.iterdir())
        if p.is_file() and p.name != "manifest.json"
    }
    save(path / "manifest.json", manifest)


def verify_bundle(path: Path, args, cfg: dict, allowed_statuses: tuple[str, ...] = ("COMPLETE",)) -> dict:
    manifest_file = path / "manifest.json"
    if not manifest_file.exists():
        raise ValueError(f"Bundle manifest missing: {manifest_file}")
    manifest = load_json(manifest_file)
    if "receipt.json" not in manifest:
        raise ValueError("Receipt not bound in manifest")
    for name, row in manifest.items():
        p = path / name
        if not p.exists() or p.stat().st_size != row["bytes"] or sha(p) != row["sha256"]:
            raise ValueError(f"Bundle file mismatch: {p}")
    receipt = load_json(path / "receipt.json")
    if receipt.get("status") not in allowed_statuses or receipt.get("protocol_sha256") != sha(args.protocol):
        raise ValueError(f"Bundle status/protocol mismatch in {path}: status={receipt.get('status')}")
    return receipt


def existing(path: Path, args, cfg: dict, allowed_statuses: tuple[str, ...] = ("COMPLETE",)) -> bool:
    if (path / "manifest.json").exists():
        verify_bundle(path, args, cfg, allowed_statuses)
        print("VERIFIED_EXISTING", path, flush=True)
        return True
    return False


def setup_legacy_runtime(cfg: dict, legacy_root: Path):
    scripts_dir = legacy_root / "scripts"
    qual_dir = legacy_root / "experiments/independent_confirmation_20261019"
    for d in (qual_dir, scripts_dir, legacy_root):
        s = str(d.resolve()) if d.exists() else str(d)
        if s not in sys.path:
            sys.path.insert(0, s)

    expected_sources = cfg.get("source_sha256", {})
    if not expected_sources:
        raise ValueError("source_sha256 mapping missing in protocol")
    for rel_path, expected_hash in expected_sources.items():
        target = legacy_root / rel_path
        if not target.exists():
            raise FileNotFoundError(f"Required legacy source missing: {target}")
        if sha(target) != expected_hash:
            raise ValueError(f"Legacy source hash mismatch: {rel_path} (expected {expected_hash}, got {sha(target)})")


def resolve_archive_path(archive_cfg: dict | str, base_dirs: list[Path]) -> Path:
    raw_path = archive_cfg["path"] if isinstance(archive_cfg, dict) else archive_cfg
    p = Path(raw_path)
    if p.exists():
        return p
    for b in base_dirs:
        cand = b / p.name
        if cand.exists():
            return cand
    return p


def require_legacy_inputs(cfg):
    for name, info in cfg['verified_inputs'].items():
        p = Path(name)
        if p.stat().st_size != info['bytes'] or sha(p) != info['sha256']:
            raise ValueError('Original input identity mismatch: '+name)


def validate_scientific_configuration(cfg):
    fixed = dict(seeds=[201,202,203,204,205], months=[1,2,3,4], primary_q=.95,
                 offset_index=2, cost_epsilon=.02, v_max=.1, n_boot=20000,
                 bootstrap_seed=20261029, primary_span=3, sensitivity_spans=[1,7],alpha=.05,
                 new_fits_allowed=0,no_outcome_exclusions=True)
    if any(cfg.get(k)!=v for k,v in fixed.items()):
        raise ValueError('Scientific configuration differs from frozen design')
    if cfg['window'] != dict(start='2026-01-01T00:00:00Z',end='2026-05-01T00:00:00Z'):
        raise ValueError('Window differs from frozen design')
    expected = [(8+45*i,'P1',201+i) for i in range(5)]+[(42+45*i,'WPQ36',201+i) for i in range(5)]
    actual=[]
    for t in cfg['selected_tasks']:
        task=t['task']
        if task['condition']!='pitch_withheld' or task['estimator']!='HGB':
            raise ValueError('Unexpected policy condition/estimator')
        actual.append((t['task_index'],task['subset'],task['seed']))
    if sorted(actual)!=sorted(expected):
        raise ValueError('Task indices or five paired instances changed')


def validate_freeze(args, cfg):
    p=args.output/'chosen/freeze.json'
    if not p.exists():
        raise FileNotFoundError(f'Frozen historical package missing at {p}')
    f=load_json(p)
    if (f['protocol_sha256']!=sha(args.protocol) or f['adapter_sha256']!=sha(__file__)
            or f['legacy_freeze_sha256']!=cfg['legacy_freeze_sha256'] or f['review_status']!='PASS_BEFORE_UNLOCK'):
        raise ValueError('Executable/protocol/legacy freeze identity mismatch')
    pf=args.output/'preflight/preflight_receipt.json'
    if sha(pf)!=f['preflight_receipt_sha256']:
        raise ValueError('Preflight receipt identity mismatch')
    r=load_json(pf)
    if (r['status']!='PREFLIGHT_PASS_NO_TEST_READ' or r['protocol_sha256']!=sha(args.protocol)
            or r['adapter_sha256']!=sha(__file__) or not r['pbs_job']):
        raise ValueError('Preflight not bound to current allocated executable')
    if datetime.fromisoformat(r['utc'])>=datetime.fromisoformat(f['created_utc']):
        raise ValueError('Preflight must precede freeze')
    if datetime.fromisoformat(f['created_utc'])>=datetime.now(timezone.utc):
        raise ValueError('Freeze timestamp must precede execution')
    return f


# ---------------------------------------------------------------------------
# Stage 1: Preflight
# ---------------------------------------------------------------------------
def preflight(args, cfg: dict) -> None:
    out = args.output / "preflight"
    if existing(out, args, cfg, allowed_statuses=("PREFLIGHT_PASS_NO_TEST_READ", "COMPLETE")):
        return
    out.mkdir(parents=True, exist_ok=True)
    receipt_path = out / "preflight_receipt.json"
    if receipt_path.exists():
        raise ValueError("Preflight receipt already exists; do not overwrite")

    legacy_root = Path(cfg["legacy_root"])
    setup_legacy_runtime(cfg, legacy_root)
    archive_cfg = cfg.get("new_archive", {})
    archive_path = resolve_archive_path(archive_cfg, [Path(cfg.get("remote_root", ".")), args.protocol.parent, Path(".")])

    # 1. Verify archive exists and size/checksum match metadata without opening ZIP
    if not archive_path.exists():
        raise FileNotFoundError(f"New archive not found at: {archive_path}")
    act_size = archive_path.stat().st_size
    if isinstance(archive_cfg, dict) and "bytes" in archive_cfg and act_size != archive_cfg["bytes"]:
        raise ValueError(f"Archive byte mismatch: expected {archive_cfg['bytes']}, got {act_size}")
    if isinstance(archive_cfg, dict) and "md5" in archive_cfg:
        act_md5 = md5_file(archive_path)
        if act_md5 != archive_cfg["md5"]:
            raise ValueError(f"Archive MD5 mismatch: expected {archive_cfg['md5']}, got {act_md5}")
    if isinstance(archive_cfg, dict) and "sha256" in archive_cfg:
        act_sha = sha(archive_path)
        if act_sha != archive_cfg["sha256"]:
            raise ValueError(f"Archive SHA256 mismatch: expected {archive_cfg['sha256']}, got {act_sha}")

    # 2. Strict legacy freeze verification: must exist and match
    freeze_file = legacy_root / "results/chosen/freeze.json"
    if not freeze_file.exists():
        freeze_file = legacy_root / "history_freeze/freeze.json"
    if not freeze_file.exists():
        raise FileNotFoundError(f"Legacy freeze.json missing at {legacy_root}")
    if cfg.get("legacy_freeze_sha256") and sha(freeze_file) != cfg["legacy_freeze_sha256"]:
        raise ValueError(f"Legacy freeze SHA256 mismatch: expected {cfg['legacy_freeze_sha256']}, got {sha(freeze_file)}")

    # 3. Check selected_tasks
    tasks = cfg.get("selected_tasks", [])
    if len(tasks) != 10:
        raise ValueError(f"Expected exactly 10 selected tasks, got {len(tasks)}")
    expected_combos = sorted((s, seed) for s in ("P1", "WPQ36") for seed in cfg.get("seeds", [201, 202, 203, 204, 205]))
    act_combos = sorted((t["task"]["subset"], t["task"]["seed"]) for t in tasks)
    if act_combos != expected_combos:
        raise ValueError(f"Selected tasks do not match expected 10 policies: {act_combos} != {expected_combos}")

    # 4. Strictly check verified inputs exist and match
    verified_inputs = cfg.get("verified_inputs", {})
    if not verified_inputs:
        raise ValueError("verified_inputs mapping missing in protocol")
    for inp_path, info in verified_inputs.items():
        p = Path(inp_path)
        if not p.exists():
            cand = legacy_root / Path(inp_path).name
            if cand.exists():
                p = cand
            else:
                rel = inp_path.split("independent_confirmation_20261019_v1/")[-1] if "independent_confirmation_20261019_v1/" in inp_path else inp_path
                cand2 = legacy_root / rel
                if cand2.exists():
                    p = cand2
        if not p.exists():
            raise FileNotFoundError(f"Required verified input missing: {inp_path}")
        if p.stat().st_size != info["bytes"] or sha(p) != info["sha256"]:
            raise ValueError(f"Verified input identity mismatch for {inp_path}")

    # 5. Scientific invariants check: no changing q, seed, window, budget, threshold
    if cfg.get("seeds") != [201, 202, 203, 204, 205]:
        raise ValueError("Seeds must be exactly [201, 202, 203, 204, 205]")
    if cfg.get("primary_q") != 0.95 or cfg.get("offset_index") != 2:
        raise ValueError("Primary evaluation quantile must be exactly q0.95 at index 2")
    if cfg.get("cost_epsilon") != 0.02 or cfg.get("v_max") != 0.10:
        raise ValueError("Cost tolerance must be 0.02 and v_max must be 0.10")
    if cfg.get("window", {}).get("start") != "2026-01-01T00:00:00Z" or cfg.get("window", {}).get("end") != "2026-05-01T00:00:00Z":
        raise ValueError("Window must be 2026-01-01T00:00:00Z to 2026-05-01T00:00:00Z")

    record = dict(
        status="PREFLIGHT_PASS_NO_TEST_READ",
        utc=datetime.now(timezone.utc).isoformat(),
        protocol_sha256=sha(args.protocol),
        adapter_sha256=sha(__file__),
        archive=dict(path=str(archive_path), bytes=act_size, sha256=sha(archive_path)),
        archive_never_opened=True,
        archive_never_listed=True,
        legacy_freeze_verified=True,
        selected_task_count=len(tasks),
        checked_legacy_inputs=len(verified_inputs),
        python=sys.version,
        host=platform.node(),
        pbs_job=os.environ.get("PBS_JOBID"),
    )
    save(receipt_path, record)
    save(out / "receipt.json", record)
    save(out / "manifest.json", {
        "preflight_receipt.json": dict(bytes=receipt_path.stat().st_size, sha256=sha(receipt_path)),
        "receipt.json": dict(bytes=(out / "receipt.json").stat().st_size, sha256=sha(out / "receipt.json")),
    })
    print("PREFLIGHT_VERIFIED_NO_ZIP_OPEN", flush=True)


# ---------------------------------------------------------------------------
# Stage 2: Evaluate
# ---------------------------------------------------------------------------
def check_coordinates(frame, year: int, station: str) -> np.ndarray:
    times = pd.to_datetime(frame["TimeStamp"], format="ISO8601", utc=True, errors="raise")
    ns = times.to_numpy(dtype="datetime64[ns]").astype(np.int64)
    start = int(np.datetime64(f"{year}-01-01", "ns").astype(np.int64))
    end = int(np.datetime64(f"{year+1}-01-01", "ns").astype(np.int64))
    ids = pd.to_numeric(frame[station], errors="raise").to_numpy(dtype=float)
    if (np.any(ns % STEP_NS) or np.any(ns < start) or np.any(ns > end)
            or not np.isfinite(ids).all() or np.any(ids != np.floor(ids))
            or np.any((ids < 2304510) | (ids > 2304530))):
        raise ValueError("Invalid period-END timestamp or turbine ID")
    return ((ns - start) // STEP_NS) * 21 + ids.astype(np.int64) - 2304510


def add_equal_copies(indices, values, seen, storage):
    indices, values = np.asarray(indices), np.asarray(values, dtype=np.float64)
    order = np.argsort(indices, kind="stable")
    ids, x = indices[order], values[order]
    repeated = ids[1:] == ids[:-1]
    if np.any(repeated & ~np.all((x[1:] == x[:-1]) | (np.isnan(x[1:]) & np.isnan(x[:-1])), axis=-1)):
        raise ValueError("Conflicting consumed observations inside coordinate group")
    keep = np.r_[True, ~repeated]
    ids, x = ids[keep], x[keep]
    known = seen[ids]
    if np.any(known & ~np.all((storage[ids] == x) | (np.isnan(storage[ids]) & np.isnan(x)), axis=-1)):
        raise ValueError("Conflicting consumed observations across files or boundaries")
    extra = int(len(indices) - np.sum(~known))
    storage[ids[~known]] = x[~known]
    seen[ids] = True
    return extra


def read_table_2026(archive: Path, year: int, table: str, storage: np.ndarray, seen: np.ndarray,
                     months: list[int], expected_schema: dict, qualifier_mod) -> dict:
    duplicates, rows, stations = 0, 0, set()
    with zipfile.ZipFile(archive) as z:
        names = z.namelist()
        for month in months:
            members = [n for n in names if Path(n).name == f"{table}_{year}_{month:02d}.csv"]
            if len(members) != 1:
                raise ValueError(f"Missing or ambiguous table for {table} {year}-{month:02d}")
            with z.open(members[0]) as f:
                header = qualifier_mod.read_header(f, table)
            schema = {k: header[k] for k in ("encoding", "delimiter", "station", "fields")}
            if schema != expected_schema:
                raise ValueError(f"Consumed schema differs for {table} month {month}")
            with z.open(members[0]) as f:
                for frame in pd.read_csv(f, sep=header["delimiter"], encoding=header["encoding"],
                                         usecols=["TimeStamp", header["station"], *header["fields"]], chunksize=100000):
                    indices = check_coordinates(frame, year, header["station"])
                    values = np.column_stack([pd.to_numeric(frame[c], errors="raise").to_numpy(dtype=float) for c in header["fields"]])
                    stations.update((indices % 21 + 2304510).tolist())
                    if len(indices):
                        duplicates += add_equal_copies(indices, values, seen, storage)
                        rows += len(indices)
    if stations != set(range(2304510, 2304531)):
        raise ValueError("Not all 21 bound turbines observed in 2026 table")
    return dict(rows=rows, redundant_equal_copies=duplicates, unique_cells=int(seen.sum()))


def evaluate(args, cfg: dict) -> None:
    validate_freeze(args, cfg)
    legacy_root = Path(cfg["legacy_root"])
    setup_legacy_runtime(cfg, legacy_root)

    for name in ('windfarm_moe.independent_confirmation','windfarm_moe.information_subset',
                 'windfarm_moe.decision_information','windfarm_moe.risk_frontier'):
        module = importlib.import_module(name)
        if not Path(module.__file__).resolve().is_relative_to(legacy_root.resolve()):
            raise ValueError(f"Imported module outside original frozen runtime: {name}")

    from windfarm_moe.independent_confirmation import anchor_window, features, totals_for_offsets
    from windfarm_moe.information_subset import subset_grid, telemetry_columns
    from windfarm_moe.decision_information import arrived_history

    qual_path = legacy_root / "experiments/independent_confirmation_20261019/qualify_hill_of_towie.py"
    if not qual_path.exists():
        qual_path = legacy_root / "qualify_hill_of_towie.py"
    spec = importlib.util.spec_from_file_location("qualifier", qual_path)
    qualifier = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(qualifier)

    archive_cfg = cfg.get("new_archive", {})
    archive_path = resolve_archive_path(archive_cfg, [Path(cfg.get("remote_root", ".")), args.protocol.parent, Path(".")])

    # 1. Gate: Verify chosen/freeze.json and preflight
    freeze_path = args.output / "chosen/freeze.json"
    if not freeze_path.exists():
        raise FileNotFoundError(f"Frozen historical package missing at {freeze_path}; unlock refused")
    freeze = load_json(freeze_path)
    if freeze.get("protocol_sha256") != sha(args.protocol):
        raise ValueError("Frozen package protocol SHA mismatch")
    if freeze.get("legacy_freeze_sha256") != cfg.get("legacy_freeze_sha256"):
        raise ValueError("Legacy freeze SHA mismatch in chosen/freeze.json")
    if freeze.get("review_status") != "PASS_BEFORE_UNLOCK":
        raise ValueError("Freeze review status is not PASS_BEFORE_UNLOCK")

    preflight_receipt_path = args.output / "preflight/preflight_receipt.json"
    if not preflight_receipt_path.exists():
        raise FileNotFoundError("Preflight receipt missing; execute preflight stage first")
    preflight_receipt = load_json(preflight_receipt_path)
    if preflight_receipt.get("status") != "PREFLIGHT_PASS_NO_TEST_READ":
        raise ValueError(f"Preflight status was not pass: {preflight_receipt.get('status')}")
    if sha(preflight_receipt_path) != freeze["preflight_receipt_sha256"]:
        raise ValueError("Preflight receipt SHA mismatch in freeze")

    # 2. Exclusive unlock event creation
    unlock_event_path = args.output / "UNLOCK_EVENT.json"
    if not unlock_event_path.exists():
        if sha(archive_path) != archive_cfg.get("sha256") or archive_path.stat().st_size != archive_cfg.get("bytes"):
            raise ValueError("Raw 2026 archive mismatch before unlock event")
        unlock_event = dict(
            utc=datetime.now(timezone.utc).isoformat(),
            pbs_job=os.environ.get("PBS_JOBID"),
            freeze_sha256=sha(freeze_path),
            protocol_sha256=sha(args.protocol),
            archive_sha256=archive_cfg.get("sha256"),
            reason="One authorized unlock for 2026 Jan-Apr evaluation after freeze review",
        )
        with unlock_event_path.open("x", encoding="utf-8") as f:
            json.dump(unlock_event, f, indent=2)
        print("UNLOCK_EVENT_RECORDED", flush=True)
    else:
        # Validate existing unlock event
        evt = load_json(unlock_event_path)
        if (evt.get("freeze_sha256") != sha(freeze_path) or evt.get("protocol_sha256") != sha(args.protocol)
                or evt.get('archive_sha256') != archive_cfg['sha256']):
            raise ValueError("Existing UNLOCK_EVENT binds different freeze or protocol")

    evt = load_json(unlock_event_path)
    if datetime.fromisoformat(freeze['created_utc']) >= datetime.fromisoformat(evt['utc']):
        raise ValueError('Freeze must strictly precede unlock')

    # 3. Coordinate preparation & boundary verification
    unlocked_dir = args.output / "unlocked"
    merged_path = unlocked_dir / "physical_channels.npy"
    conf_path = unlocked_dir / "confirmation.npz"

    nt_2026 = 120 * 144 + 1
    total_cells = nt_2026 * 21

    if not existing(unlocked_dir, args, cfg):
        legacy_channels_path = legacy_root / 'results/unlocked/physical_channels.npy'
        raw_2025_archive = Path(cfg['annual_source_root']) / '2025.zip'
        if sha(raw_2025_archive) != cfg['raw_2025_archive_sha256']:
            raise ValueError('Original2025 archive identity mismatch')
        forecaster_path = legacy_root / 'results/prepared/point_forecaster.joblib'
        require_legacy_inputs(cfg)
        receipt_unlocked = begin(unlocked_dir, args, cfg,
                                [freeze_path, unlock_event_path, archive_path, raw_2025_archive,
                                 legacy_channels_path, forecaster_path], 'unlock')
        ctx_info = cfg.get("context_file", {})
        legacy_channels_path = legacy_root / "results/unlocked/physical_channels.npy"
        if not legacy_channels_path.exists():
            legacy_channels_path = Path("results/unlocked/physical_channels.npy")
        if legacy_channels_path.exists() and ctx_info.get("sha256"):
            if sha(legacy_channels_path) != ctx_info["sha256"]:
                raise ValueError("Legacy context physical_channels.npy SHA mismatch")
        legacy_hist = np.load(legacy_channels_path, mmap_mode="r")
        if legacy_hist.shape != (1096*144+1,21,4):
            raise ValueError('Historical context shape/clock mismatch')

        schemas = cfg.get("schema", {})
        data_tables = {}

        # Boundary preparation: Seed 2026 storage[:21] with raw 6 fields from legacy 2025 Dec boundary
        for table, fields in qualifier.TABLES.items():
            storage = np.full((total_cells, len(fields)), np.nan)
            seen = np.zeros(total_cells, bool)

            # Required raw six-field equality, before any channel transformation.
            boundary_vals = np.full((21, len(fields)), np.nan)
            boundary_seen = np.zeros(21, bool)
            with zipfile.ZipFile(raw_2025_archive) as z_25:
                m12_files = [n for n in z_25.namelist() if Path(n).name == f"{table}_2025_12.csv"]
                if len(m12_files) != 1:
                    raise ValueError('Need exactly one original December table: '+table)
                if len(m12_files) == 1:
                    with z_25.open(m12_files[0]) as f:
                        hdr = qualifier.read_header(f, table)
                    if {k:hdr[k] for k in ('encoding','delimiter','station','fields')} != schemas[table]:
                        raise ValueError('Original December consumed schema mismatch')
                    with z_25.open(m12_files[0]) as f:
                        for frame in pd.read_csv(f, sep=hdr["delimiter"], encoding=hdr["encoding"],
                                                 usecols=["TimeStamp", hdr["station"], *hdr["fields"]], chunksize=100000):
                            idx = check_coordinates(frame, 2025, hdr["station"])
                            val = np.column_stack([pd.to_numeric(frame[c], errors="raise").to_numpy(dtype=float) for c in hdr["fields"]])
                            bnd = int((np.datetime64("2026-01-01") - np.datetime64("2025-01-01")) / np.timedelta64(600, "s")) * 21
                            keep = idx >= bnd
                            if np.any(keep):
                                add_equal_copies(idx[keep] - bnd, val[keep], boundary_seen, boundary_vals)
            storage[:21] = boundary_vals
            seen[:21] = boundary_seen
            receipt_unlocked.setdefault('boundary',{})[table] = dict(
                seen=int(boundary_seen.sum()),raw_values_sha256=hashlib.sha256(boundary_vals.tobytes()).hexdigest())

            read_table_2026(archive_path, 2026, table, storage, seen, cfg.get("months", [1, 2, 3, 4]), schemas[table], qualifier)
            data_tables[table] = storage

        channels_2026 = np.full((total_cells, 4), np.nan)
        turbine, grid = data_tables["tblSCTurbine"], data_tables["tblSCTurGrid"]
        channels_2026[:, 0] = np.where(np.isfinite(turbine[:, 0]) & (turbine[:, 0] >= 0), turbine[:, 0], np.nan)
        channels_2026[:, 1:3] = np.where(np.isfinite(grid), grid, np.nan)
        valid_pitch = np.isfinite(turbine[:, 1:4]).all(axis=1)
        channels_2026[valid_pitch, 3] = turbine[valid_pitch, 1:4].mean(axis=1)
        channels_2026 = channels_2026.reshape(nt_2026, 21, 4)

        np.testing.assert_array_equal(legacy_hist[-1], channels_2026[0])

        merged = np.concatenate((legacy_hist, channels_2026[1:]), axis=0)
        np.save(merged_path, merged)

        issues = anchor_window(cfg["window"]["start"], cfg["window"]["end"], 6)
        forecaster_path = legacy_root / "results/prepared/point_forecaster.joblib"
        if not forecaster_path.exists():
            forecaster_path = Path("results/prepared/point_forecaster.joblib")
        forecaster = joblib.load(forecaster_path)

        fc_values = []
        for i in range(0, len(issues), 256):
            a = issues[i:i+256] - 6
            h = arrived_history(merged[..., :2], a, 36, 0)
            feat = h.transpose(0, 1, 3, 2).reshape(len(a) * merged.shape[1], -1)
            pred = np.maximum(forecaster.predict(feat), 0).reshape(len(a), merged.shape[1])
            if not np.isfinite(pred).all():
                raise ValueError("Nonfinite forecast prediction generated")
            fc_values.append(pred)
        forecast = np.concatenate(fc_values).astype(np.float32)
        np.savez_compressed(conf_path, anchors=issues, forecast=forecast)

        receipt_unlocked.update(finite_target_count=int(np.isfinite(merged[issues+6,:,1]).sum()),
             negative_power_preserved=int(np.sum(channels_2026[:,:,1]<0)),
             n_issues=len(issues),first_issue=int(issues[0]),last_issue=int(issues[-1]),
             months=cfg['months'],refit=False,exclusions='none; original finite future-power mask only')

        finish(unlocked_dir, receipt_unlocked)

    merged = np.load(merged_path, mmap_mode="r")
    with np.load(conf_path) as a:
        anchors, forecast = a["anchors"], a["forecast"]

    true = merged[anchors + 6, :, 1].astype(np.float64)
    mask = np.isfinite(true)
    shortfall = np.where(mask, np.maximum(forecast.astype(np.float64) - true, 0), np.nan)
    x_features = features(merged, anchors, forecast, 0)

    # 4. Evaluate selected tasks
    eval_dir = args.output / "evaluate"
    eval_dir.mkdir(parents=True, exist_ok=True)
    task_filter = [args.task_index] if getattr(args, "task_index", None) is not None and args.task_index >= 0 else None

    for item in cfg.get("selected_tasks", []):
        t_idx = item["task_index"]
        if task_filter is not None and t_idx not in task_filter:
            continue
        out_t = eval_dir / str(t_idx)
        if existing(out_t, args, cfg):
            continue
        task = item["task"]
        model_path = legacy_root / f"results/historical/{t_idx}/model.joblib"
        offsets_path = legacy_root / f"results/historical/{t_idx}/offsets.npy"
        if not model_path.exists():
            model_path = Path(f"results/historical/{t_idx}/model.joblib")
            offsets_path = Path(f"results/historical/{t_idx}/offsets.npy")

        # Verify model/offsets SHA
        if item.get("files", {}).get("model.joblib"):
            exp_sha = item["files"]["model.joblib"]["sha256"]
            if sha(model_path) != exp_sha:
                raise ValueError(f"Model hash mismatch for task {t_idx}")
        if item.get("files", {}).get("offsets.npy"):
            exp_sha = item["files"]["offsets.npy"]["sha256"]
            if sha(offsets_path) != exp_sha:
                raise ValueError(f"Offsets hash mismatch for task {t_idx}")

        receipt = begin(out_t, args, cfg, [freeze_path, unlock_event_path, merged_path, conf_path, model_path, offsets_path], "evaluate")
        receipt["task"] = task

        model = joblib.load(model_path)
        offsets = np.load(offsets_path)

        channels_sub, length = subset_grid()[task["subset"]]
        cols = telemetry_columns(channels_sub, length, 0, False)
        raw = np.maximum(model.predict(x_features[:, cols]), 0).astype(np.float64).reshape(mask.shape)
        if not np.isfinite(raw).all():
            raise ValueError(f"Nonfinite model prediction for task {t_idx}")

        blocks = totals_for_offsets(shortfall, raw, mask, anchors, offsets)

        days = np.repeat(anchors // 144, mask.shape[1])[mask.reshape(-1)]
        day_ids = np.unique(anchors // 144)
        for qi, off in enumerate(offsets):
            reserve = np.maximum(raw + off, 0)[mask]
            act = shortfall[mask]
            direct_loss = np.bincount(days, weights=(reserve + 10 * np.maximum(act - reserve, 0))/6, minlength=int(day_ids[-1])+1)[day_ids]
            count = np.bincount(days, minlength=int(day_ids[-1])+1)[day_ids]
            viol = np.bincount(days, weights=(act > reserve).astype(float), minlength=int(day_ids[-1])+1)[day_ids]
            if (not np.allclose(direct_loss, blocks[f"{qi}__loss_sum"], rtol=0, atol=1e-7)
                    or not np.array_equal(count, blocks[f"{qi}__count"])
                    or not np.array_equal(viol, blocks[f"{qi}__violation_sum"])):
                raise ValueError(f"Action accounting check failed for task {t_idx} q{qi}")

        np.savez_compressed(out_t / "raw_actions.npz", raw=raw, offsets=offsets, anchors=anchors, shortfall=shortfall, mask=mask)
        np.savez_compressed(out_t / "blocks.npz", **blocks)
        save(out_t / "metadata.json", dict(
            task=task,
            resource=item.get("resource"),
            q095_offset=float(offsets[cfg.get("offset_index", 2)]),
            refit=False,
        ))
        finish(out_t, receipt)
        print("EVALUATED_TASK", t_idx, task["subset"], task["seed"], flush=True)


# ---------------------------------------------------------------------------
# Stage 3: Aggregate
# ---------------------------------------------------------------------------
def aggregate(args, cfg: dict) -> None:
    out = args.output / "aggregate"
    if existing(out, args, cfg):
        return
    out.mkdir(parents=True, exist_ok=True)
    setup_legacy_runtime(cfg, Path(cfg["legacy_root"]))
    from windfarm_moe.subset_inference import streamed_envelopes

    eval_dir = args.output / "evaluate"
    manifests = []
    costs, violations, reserves, shortages = [], [], [], []
    counts, day_ids = None, None
    labels = ["P1/HGB/q0.95", "WPQ36/HGB/q0.95"]
    q_idx = cfg.get("offset_index", 2)

    for subset in ("P1", "WPQ36"):
        subset_tasks = [t for t in cfg["selected_tasks"] if t["task"]["subset"] == subset]
        subset_tasks = sorted(subset_tasks, key=lambda x: x["task"]["seed"])
        c_seeds, v_seeds, r_seeds, u_seeds = [], [], [], []
        for item in subset_tasks:
            t_idx = item["task_index"]
            p_dir = eval_dir / str(t_idx)
            verify_bundle(p_dir, args, cfg)
            manifests.append(p_dir / "manifest.json")
            with np.load(p_dir / "blocks.npz") as b:
                cnt = b[f"{q_idx}__count"]
                d_id = b[f"{q_idx}__block_ids"]
                if counts is None:
                    counts, day_ids = cnt.copy(), d_id.copy()
                else:
                    if not np.array_equal(counts, cnt) or not np.array_equal(day_ids, d_id):
                        raise ValueError("Unpaired day coordinates across seeds")
                c_seeds.append(b[f"{q_idx}__loss_sum"])
                v_seeds.append(b[f"{q_idx}__violation_sum"])
                r_seeds.append(b[f"{q_idx}__reserve_sum"])
                u_seeds.append(b[f"{q_idx}__shortage_sum"])
        costs.append(c_seeds)
        violations.append(v_seeds)
        reserves.append(r_seeds); shortages.append(u_seeds)

    costs_arr = np.asarray(costs, dtype=float).transpose(1, 0, 2)
    viol_arr = np.asarray(violations, dtype=float).transpose(1, 0, 2)
    if costs_arr.shape!=(5,2,len(counts)) or viol_arr.shape!=costs_arr.shape:
        raise ValueError('Expected five paired fits by two policies by weather day')
    if len(cfg['selected_tasks'])!=10:
        raise ValueError('Expected exactly ten selected policy instances')
    exact_pair = np.eye(2, dtype=bool)

    group = dict(costs=costs_arr, violations=viol_arr, counts=counts, exact_pair=exact_pair)
    receipt = begin(out, args, cfg, manifests, "aggregate")

    n_boot = cfg.get("n_boot", 20000)
    b_seed = cfg.get("bootstrap_seed", 20261029)
    alpha = cfg.get("alpha", 0.05)
    cost_eps = cfg.get("cost_epsilon", 0.02)
    v_max = cfg.get("v_max", 0.10)

    bounds_3 = streamed_envelopes([group], n_boot, cfg.get("primary_span", 3), b_seed, alpha)
    if bounds_3['coordinate_family_size']!=14:
        raise ValueError('Primary coordinate family must remain14')
    env_3 = bounds_3["groups"][0]
    rpoint=np.asarray(reserves).transpose(1,0,2).sum(axis=2)/counts.sum()
    upoint=np.asarray(shortages).transpose(1,0,2).sum(axis=2)/counts.sum()
    cpoint=costs_arr.sum(axis=2)/counts.sum()
    if not np.allclose(cpoint,rpoint+10*upoint,atol=1e-8,rtol=0):
        raise ValueError('Daily C/R/U accounting identity failed')
    descriptive=dict(order=['C','R','U','V'],per_fit=np.stack((cpoint,rpoint,upoint,env_3['risk_point']),axis=-1),
                     mean=np.stack((cpoint,rpoint,upoint,env_3['risk_point']),axis=-1).mean(axis=0),
                     unit='C/R/U kWh-equivalent per valid turbine interval;V fraction',H='UNKNOWN;not registered',
                     n_valid_per_fit=float(counts.sum()),n_weather_days=len(counts))

    cand_risk_upper = float(np.max(env_3["risk_upper"][:, 0]))
    ref_risk_upper = float(np.max(env_3["risk_upper"][:, 1]))
    paired_cost_ratio_upper = float(env_3["relative_ratio_upper"][0, 1])

    cand_risk_pass = bool(cand_risk_upper <= v_max)
    ref_risk_pass = bool(ref_risk_upper <= v_max)
    cost_pass = bool(paired_cost_ratio_upper <= cost_eps)
    primary_confirmed = bool(cand_risk_pass and ref_risk_pass and cost_pass)

    verdict = dict(
        status="ALL_FROZEN_CANDIDATES_CONFIRMED" if primary_confirmed else "CONFIRMATION_NOT_ESTABLISHED",
        candidate_risk_pass=cand_risk_pass,
        candidate_max_risk_upper=cand_risk_upper,
        reference_risk_pass=ref_risk_pass,
        reference_max_risk_upper=ref_risk_upper,
        paired_cost_pass=cost_pass,
        relative_cost_ratio_upper=paired_cost_ratio_upper,
        epsilon=cost_eps,
        v_max=v_max,
        h_status="UNKNOWN (descriptive only; no H gate defined in primary protocol)",
    )

    primary_res = dict(
        verdict=verdict,
        labels=labels,
        bounds=bounds_3,
        primary_coordinate_family=bounds_3["coordinate_family_size"],  # exactly 14
        mean_cost=env_3["mean_cost"].tolist(),
        descriptive=descriptive,
        risk_point=env_3["risk_point"].tolist(),
        risk_lower=env_3["risk_lower"].tolist(),
        risk_upper=env_3["risk_upper"].tolist(),
        relative_ratio_point=env_3["relative_ratio_point"].tolist(),
        relative_ratio_lower=env_3["relative_ratio_lower"].tolist(),
        relative_ratio_upper=env_3["relative_ratio_upper"].tolist(),
    )
    save(out / "primary.json", primary_res)

    sensitivity = {}
    for span in cfg.get("sensitivity_spans", [1, 7]):
        b_span = streamed_envelopes([group], n_boot, span, b_seed, alpha)
        e_span = b_span["groups"][0]
        sensitivity[f"span_{span}"] = dict(
            candidate_max_risk_upper=float(np.max(e_span["risk_upper"][:, 0])),
            reference_max_risk_upper=float(np.max(e_span["risk_upper"][:, 1])),
            relative_cost_ratio_upper=float(e_span["relative_ratio_upper"][0, 1]),
            confirmed=bool(np.max(e_span["risk_upper"][:, 0]) <= v_max and
                           np.max(e_span["risk_upper"][:, 1]) <= v_max and
                           e_span["relative_ratio_upper"][0, 1] <= cost_eps)
        )
    save(out / "sensitivity.json", sensitivity)

    summary = dict(
        study_id=cfg.get("study_id"),
        primary_status=verdict["status"],
        confirmed=primary_confirmed,
        coordinate_count=bounds_3["coordinate_family_size"],
        labels=labels,
        mean_cost=env_3["mean_cost"].tolist(),
        risk_point=env_3["risk_point"].tolist(),
        risk_upper=env_3["risk_upper"].tolist(),
        relative_ratio_point=env_3["relative_ratio_point"].tolist(),
        relative_ratio_upper=env_3["relative_ratio_upper"].tolist(),
        paired_cost_upper_percent=paired_cost_ratio_upper * 100,
        candidate_max_risk_upper_percent=cand_risk_upper * 100,
        reference_max_risk_upper_percent=ref_risk_upper * 100,
        sensitivity=sensitivity,
        H_threshold_applied=False,
        U_R_H_role="descriptive only; point estimates reported in primary and summary",
    )
    save(out / "summary.json", summary)
    finish(out, receipt)
    print("AGGREGATE_COMPLETE", verdict["status"], flush=True)


# ---------------------------------------------------------------------------
# CLI Entrypoint
# ---------------------------------------------------------------------------
def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--protocol", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--stage", choices=["preflight", "evaluate", "aggregate"], required=True)
    p.add_argument("--task-index", type=int, default=-1)
    args = p.parse_args()

    if not os.environ.get("PBS_JOBID"):
        raise ValueError("Numeric adapter execution requires an allocated PBS node (PBS_JOBID missing)")

    cfg = load_json(args.protocol)
    validate_scientific_configuration(cfg)
    try:
        with threadpool_limits(limits=2):
            if args.stage == "preflight":
                preflight(args, cfg)
            elif args.stage == "evaluate":
                evaluate(args, cfg)
            elif args.stage == "aggregate":
                aggregate(args, cfg)
    except BaseException as exc:
        for rcpt in args.output.rglob('receipt.json') if args.output.exists() else []:
            target_stage_dir=rcpt.parent
            if (target_stage_dir/'manifest.json').exists():
                continue
            try:
                rec = load_json(rcpt)
                if rec.get("status") == "RUNNING":
                    rec.update(status="FAILED_PRESERVED", error=repr(exc), finished_utc=datetime.now(timezone.utc).isoformat())
                    save(rcpt, rec)
            except Exception:
                pass
        raise


if __name__ == "__main__":
    main()
