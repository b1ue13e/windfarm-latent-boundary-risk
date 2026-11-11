"""Pre-bound Hill of Towie history -> freeze -> single unlock -> confirmation.

Every numeric stage requires a PBS allocation. No test-driven refit is exposed.
Completed bundles are immutable and verified before reuse.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from repo_paths import Path, repository_root
import platform
import subprocess
import sys
import time
import zipfile

import joblib
import numpy as np
import pandas as pd
import sklearn
from threadpoolctl import threadpool_limits

ROOT = Path(repository_root())
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'experiments/independent_confirmation_20261019'))
from windfarm_moe.independent_confirmation import (
    START_NS, STEP_NS, anchor_window, features, point_features, task_table, resource,
    totals_for_offsets, historical_selection, confirmation_verdict)
from windfarm_moe.information_subset import subset_grid, telemetry_columns, nested_samples, PinballMLP
from windfarm_moe.risk_frontier import offset_grid, near_optimal_set
from windfarm_moe.subset_inference import streamed_envelopes
from run_decision_information_development import learner
from prepare_confirmation_history import add_equal_copies
from audit_subset_minimum_necessity import diagnose
import qualify_hill_of_towie as qualifier


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
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
    path.write_text(json.dumps(clean(value), ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')


def sources(cfg: dict) -> dict:
    return {name: sha(ROOT / name) for name in cfg['source_files']}


def begin(path: Path, args, cfg: dict, inputs: list[Path], stage: str) -> dict:
    import torch
    path.mkdir(parents=True, exist_ok=False)
    info = dict(status='RUNNING', stage=stage, argv=sys.argv,
                started_utc=datetime.now(timezone.utc).isoformat(), protocol_sha256=sha(args.protocol),
                sources=sources(cfg), inputs={str(p.resolve()): sha(p) for p in inputs},
                python=sys.version, numpy=np.__version__, pandas=pd.__version__, sklearn=sklearn.__version__,
                torch=torch.__version__, cuda_build=torch.version.cuda, backend='CPU only',
                pbs_job=os.environ.get('PBS_JOBID'), host=platform.node(), platform=platform.platform(),
                seed_instances=cfg['seeds'], hyperparameters=cfg['estimators'], mlp=cfg['mlp'],
                deployment=json.loads((ROOT / 'deployment_manifest.json').read_text()) if (ROOT / 'deployment_manifest.json').exists() else None)
    save(path / 'receipt.json', info)
    return info


def finish(path: Path, receipt: dict) -> None:
    for name, value in receipt['inputs'].items():
        if sha(Path(name)) != value:
            raise ValueError('Protected input changed: ' + name)
    receipt.update(status='COMPLETE', finished_utc=datetime.now(timezone.utc).isoformat())
    save(path / 'receipt.json', receipt)
    save(path / 'manifest.json', {p.name: dict(bytes=p.stat().st_size, sha256=sha(p))
                                for p in sorted(path.iterdir()) if p.is_file() and p.name != 'manifest.json'})


def verify(path: Path, args, cfg: dict) -> dict:
    manifest = json.loads((path / 'manifest.json').read_text())
    if 'receipt.json' not in manifest:
        raise ValueError('Receipt not bound')
    for name, row in manifest.items():
        p = path / name
        if p.resolve().parent != path.resolve() or p.stat().st_size != row['bytes'] or sha(p) != row['sha256']:
            raise ValueError('Bundle identity mismatch: ' + str(p))
    receipt = json.loads((path / 'receipt.json').read_text())
    if receipt['status'] != 'COMPLETE' or receipt['protocol_sha256'] != sha(args.protocol) or receipt['sources'] != sources(cfg):
        raise ValueError('Wrong frozen source/protocol/status')
    return receipt


def existing(path: Path, args, cfg: dict) -> bool:
    if (path / 'manifest.json').exists():
        verify(path, args, cfg)
        print('VERIFIED_EXISTING', path, flush=True)
        return True
    return False


def check_coordinates(frame, year: int, station: str) -> np.ndarray:
    ns = pd.to_datetime(frame['TimeStamp'], format='ISO8601', utc=True, errors='raise').to_numpy(dtype='datetime64[ns]').astype('i8')
    start = int(np.datetime64(f'{year}-01-01', 'ns').astype('i8'))
    end = int(np.datetime64(f'{year+1}-01-01', 'ns').astype('i8'))
    ids = pd.to_numeric(frame[station], errors='raise').to_numpy(dtype=float)
    if (np.any(ns % STEP_NS) or np.any(ns < start) or np.any(ns > end) or not np.isfinite(ids).all()
            or np.any(ids != np.floor(ids)) or np.any((ids < 2304510) | (ids > 2304530))):
        raise ValueError('Invalid period-END timestamp or turbine ID')
    return ((ns - start) // STEP_NS) * 21 + ids.astype('i8') - 2304510


def read_table(archive: Path, year: int, table: str, storage: np.ndarray, seen: np.ndarray,
               boundary_only: bool = False, expected_schema: dict | None = None) -> dict:
    duplicates, rows, schemas, stations = 0, 0, [], set()
    with zipfile.ZipFile(archive) as z:
        names = z.namelist()
        for month in ([12] if boundary_only else range(1, 13)):
            members = [n for n in names if Path(n).name == f'{table}_{year}_{month:02d}.csv']
            if len(members) != 1:
                raise ValueError('Missing or ambiguous monthly table')
            with z.open(members[0]) as f:
                header = qualifier.read_header(f, table)
            schema = {k: header[k] for k in ('encoding', 'delimiter', 'station', 'fields')}
            if expected_schema is not None and schema != expected_schema:
                raise ValueError('Consumed schema differs from historical freeze')
            schemas.append(schema)
            with z.open(members[0]) as f:
                for frame in pd.read_csv(f, sep=header['delimiter'], encoding=header['encoding'],
                                        usecols=['TimeStamp', header['station'], *header['fields']], chunksize=100000):
                    indices = check_coordinates(frame, year, header['station'])
                    values = np.column_stack([pd.to_numeric(frame[c], errors='raise').to_numpy(dtype=float) for c in header['fields']])
                    if boundary_only:
                        boundary = int((np.datetime64(f'{year+1}-01-01') - np.datetime64(f'{year}-01-01')) / np.timedelta64(600, 's')) * 21
                        keep = indices >= boundary
                        indices, values = indices[keep] - boundary, values[keep]
                    else:
                        stations.update((indices % 21 + 2304510).tolist())
                    if len(indices):
                        duplicates += add_equal_copies(indices, values, seen, storage)
                        rows += len(indices)
    if not boundary_only and stations != set(range(2304510, 2304531)):
        raise ValueError('Not all bound turbines observed')
    if any(s != schemas[0] for s in schemas):
        raise ValueError('Consumed schema changed within year')
    return dict(rows=rows, redundant_equal_copies=duplicates, schema=schemas[0], unique_cells=int(seen.sum()))


def preflight(args, cfg: dict) -> None:
    destination = ROOT / 'preflight_receipt.json'
    if destination.exists():
        raise ValueError('Preflight receipt already exists; do not overwrite')
    before = sources(cfg)
    deployment = json.loads((ROOT / 'deployment_manifest.json').read_text())
    command = [sys.executable, '-m', 'pytest', '-q', 'tests/test_independent_confirmation.py',
               'tests/test_information_subset.py', 'tests/test_subset_inference.py',
               'tests/test_confirmation_lossless_adapter.py']
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace')
    with (ROOT / 'preflight.log').open('x', encoding='utf-8') as f:
        f.write(result.stdout + result.stderr)
    unchanged = sources(cfg) == before
    record = dict(exit_code=result.returncode if unchanged else -1, pbs_job=os.environ['PBS_JOBID'],
                  utc=datetime.now(timezone.utc).isoformat(), sources=before,
                  protocol_sha256=sha(args.protocol), git_commit=deployment['git_commit'],
                  command=command, python=sys.version, host=platform.node(),
                  source_unchanged_during_tests=unchanged)
    with destination.open('x', encoding='utf-8') as f:
        json.dump(record, f, indent=2)
    print(result.stdout + result.stderr, flush=True)
    if record['exit_code']:
        raise ValueError('Allocated-node preflight failed; receipt preserved')


def prepare(args, cfg: dict) -> None:
    out = args.output / 'prepared'
    if existing(out, args, cfg):
        return
    hist = Path(cfg['historical_root'])
    for name, value in cfg['historical_input_sha256'].items():
        if sha(hist / name) != value:
            raise ValueError('Historical source identity differs')
    source = Path(cfg['annual_source_root'])
    archive = source / '2024.zip'
    if sha(archive) != cfg['annual_sha256']['2024']:
        raise ValueError('Historical annual archive differs')
    receipt = begin(out, args, cfg, [hist / n for n in cfg['historical_input_sha256']] + [archive, ROOT / 'preflight_receipt.json'], 'prepare')
    data = np.load(hist / 'historical_physical_channels.npy', mmap_mode='r')
    times = np.load(hist / 'historical_time_end_ns.npy')
    if data.shape != (105265, 21, 4) or not np.array_equal(times, START_NS + np.arange(len(data), dtype='i8') * STEP_NS):
        raise ValueError('Historical grid not bound chronology')
    # Freeze the six raw consumed boundary fields and presence before test read.
    arrays, schemas = {}, {}
    for table, fields in qualifier.TABLES.items():
        values, seen = np.full((21, len(fields)), np.nan), np.zeros(21, bool)
        report = read_table(archive, 2024, table, values, seen, boundary_only=True)
        arrays[table + '_values'], arrays[table + '_seen'] = values, seen
        schemas[table] = report['schema']
    np.savez_compressed(out / 'raw_2024_boundary.npz', **arrays)
    save(out / 'consumed_schema.json', schemas)
    first, last = cfg['windows']['point_fit']
    trimmed = (np.datetime64(last.replace('Z', ''), 'ns') - 6 * np.timedelta64(600, 's'))
    anchors = anchor_window(first, str(trimmed), 12)
    policy_first = anchor_window(*cfg['windows']['policy_fit'], 6)[0]
    if anchors[-1] + 12 + 1 >= policy_first - 6:
        raise ValueError('Point-fit labels not mature before first forecast publication')
    x = point_features(data, anchors)
    y = data[anchors + 12, :, 1].reshape(-1)
    indices = nested_samples(np.isfinite(y), [cfg['point_rows']], cfg['point_seed'])[cfg['point_rows']]
    model = learner(cfg['estimators'], cfg['point_seed'], False)
    model.fit(x[indices], y[indices])
    np.save(out / 'point_fit_indices.npy', indices)
    joblib.dump(model, out / 'point_forecaster.joblib')
    del x, y
    for stage in ('policy_fit', 'offset_fit', 'selection'):
        issues = anchor_window(*cfg['windows'][stage], 6)
        forecast = forecast_at(model, data, issues)
        np.savez_compressed(out / (stage + '.npz'), anchors=issues, forecast=forecast)
    receipt['point_last_label_release'] = int(anchors[-1] + 13)
    receipt['first_forecast_publication'] = int(policy_first - 6)
    finish(out, receipt)


def forecast_at(model, data: np.ndarray, anchors: np.ndarray) -> np.ndarray:
    values = []
    for i in range(0, len(anchors), 256):
        a = anchors[i:i+256] - 6
        values.append(np.maximum(model.predict(point_features(data, a)), 0).reshape(len(a), data.shape[1]))
    result = np.concatenate(values).astype(np.float32)
    if not np.isfinite(result).all():
        raise ValueError('Nonfinite common forecast')
    return result


def stage_data(args, cfg: dict, stage: str, condition: dict) -> dict:
    prepared = args.output / ('unlocked' if stage == 'confirmation' else 'prepared')
    source = prepared / 'physical_channels.npy' if stage == 'confirmation' else Path(cfg['historical_root']) / 'historical_physical_channels.npy'
    data = np.load(source, mmap_mode='r')
    with np.load(prepared / (stage + '.npz')) as a:
        anchors, forecast = a['anchors'], a['forecast']
    true = data[anchors + 6, :, 1].astype(np.float64)
    mask = np.isfinite(true)
    shortfall = np.where(mask, np.maximum(forecast.astype(np.float64) - true, 0), np.nan)
    x = features(data, anchors, forecast, condition['delay_steps'])
    ident = {k: hashlib.sha256(np.ascontiguousarray(v).tobytes()).hexdigest() for k, v in
             dict(anchors=anchors, forecast=forecast, true=true, mask=mask, shortfall=shortfall).items()}
    return dict(X=x, anchors=anchors, forecast=forecast, true=true, mask=mask, shortfall=shortfall, identity=ident)


def predict(model, stage: dict, task: dict, condition: dict) -> np.ndarray:
    if task['estimator'] == 'Persistence':
        p = stage['X'][:, 4 + 36 + 35 - condition['delay_steps']]
        r = np.where(np.isfinite(p), np.maximum(stage['forecast'].reshape(-1) - p, 0), 0)
    else:
        channels, length = subset_grid()[task['subset']]
        cols = telemetry_columns(channels, length, condition['delay_steps'], condition['pitch_available'])
        r = np.maximum(model.predict(stage['X'][:, cols]), 0)
    if not np.isfinite(r).all():
        raise ValueError('Nonfinite raw prediction')
    return r.astype(np.float64).reshape(stage['mask'].shape)


def historical(args, cfg: dict) -> None:
    task = task_table(cfg)[args.task_index]
    out = args.output / 'historical' / str(args.task_index)
    if existing(out, args, cfg):
        return
    verify(args.output / 'prepared', args, cfg)
    inputs = [args.output / 'prepared/manifest.json', Path(cfg['historical_root']) / 'historical_physical_channels.npy']
    receipt = begin(out, args, cfg, inputs, 'historical')
    receipt['task'] = task
    cond = cfg['conditions'][task['condition']]
    fit = stage_data(args, cfg, 'policy_fit', cond)
    model, fit_seconds = None, 0.0
    if task['estimator'] != 'Persistence':
        channels, length = subset_grid()[task['subset']]
        cols = telemetry_columns(channels, length, cond['delay_steps'], cond['pitch_available'])
        indices = nested_samples(fit['mask'], [cfg['reserve_rows']], task['seed'])[cfg['reserve_rows']]
        np.save(out / 'fit_indices.npy', indices)
        model = learner(cfg['estimators'], task['seed'], True) if task['estimator'] == 'HGB' else PinballMLP(task['seed'], cfg['mlp'])
        start = time.monotonic()
        model.fit(fit['X'][indices][:, cols], fit['shortfall'].reshape(-1)[indices])
        fit_seconds = time.monotonic() - start
        joblib.dump(model, out / 'model.joblib')
    del fit
    cal = stage_data(args, cfg, 'offset_fit', cond)
    raw = predict(model, cal, task, cond)
    offsets = offset_grid(cal['shortfall'], raw, cal['mask'], cfg['offset_quantiles'])
    np.save(out / 'offsets.npy', offsets)
    del cal, raw
    selection = stage_data(args, cfg, 'selection', cond)
    raw = predict(model, selection, task, cond)
    np.savez_compressed(out / 'blocks.npz', **totals_for_offsets(selection['shortfall'], raw, selection['mask'], selection['anchors'], offsets))
    save(out / 'metadata.json', dict(task=task, identity=selection['identity'], resource=resource(task, cond),
                                    fit_seconds=fit_seconds, training_trace=getattr(model, 'training_trace_', None)))
    finish(out, receipt)
    print('HISTORICAL_COMPLETE', args.task_index, task, flush=True)


def groups_at(args, cfg: dict, stage: str) -> tuple:
    table = task_table(cfg)
    groups, details, manifests = [], [], []
    identities, samples = None, {}
    for name, condition in cfg['conditions'].items():
        costs, violations, labels, resources, descriptors = [], [], [], [], []
        counts, days = None, None
        for first_task in [t for t in table if t['condition'] == name and t['seed'] == cfg['seeds'][0]]:
            workers = []
            for seed in cfg['seeds']:
                index = table.index({**first_task, 'seed': seed})
                path = args.output / stage / str(index)
                r = verify(path, args, cfg)
                if r['task'] != {**first_task, 'seed': seed}:
                    raise ValueError('Task coordinates differ')
                metadata = json.loads((path / 'metadata.json').read_text())
                if identities is None:
                    identities = metadata['identity']
                elif identities != metadata['identity']:
                    raise ValueError('Unequal forecast/target/population')
                if stage == 'historical' and first_task['estimator'] != 'Persistence':
                    digest = sha(path / 'fit_indices.npy')
                    if seed in samples and samples[seed] != digest:
                        raise ValueError('Unpaired historical samples')
                    samples[seed] = digest
                manifests.append(path / 'manifest.json')
                hist = args.output / 'historical' / str(index)
                workers.append((dict(np.load(path / 'blocks.npz')), np.load(hist / 'offsets.npy')))
            for qi, q in enumerate(cfg['offset_quantiles']):
                cc, vv, offsets = [], [], []
                for blocks, off in workers:
                    c, d = blocks[f'{qi}__count'], blocks[f'{qi}__block_ids']
                    if counts is None:
                        counts, days = c.copy(), d.copy()
                    if not np.array_equal(counts, c) or not np.array_equal(days, d):
                        raise ValueError('Unpaired day coordinates or population')
                    cc.append(blocks[f'{qi}__loss_sum']); vv.append(blocks[f'{qi}__violation_sum']); offsets.append(float(off[qi]))
                costs.append(cc); violations.append(vv)
                labels.append(f"{first_task['subset']}/{first_task['estimator']}/q{q}")
                resources.append(resource(first_task, condition))
                descriptors.append((first_task['subset'], first_task['estimator'], offsets))
        exact = np.eye(len(labels), dtype=bool)
        for i, left in enumerate(descriptors):
            for j, right in enumerate(descriptors):
                if left == right:
                    exact[i,j] = True
        groups.append(dict(costs=np.asarray(costs).transpose(1,0,2), violations=np.asarray(violations).transpose(1,0,2), counts=counts, exact_pair=exact))
        details.append(dict(condition=name, labels=labels, resources=resources, block_ids=days))
    return groups, details, list(dict.fromkeys(manifests))


def choose(args, cfg: dict) -> None:
    out = args.output / 'chosen'
    if existing(out, args, cfg):
        return
    groups, details, manifests = groups_at(args, cfg, 'historical')
    receipt = begin(out, args, cfg, manifests + [args.output / 'prepared/manifest.json'], 'choose')
    bounds = streamed_envelopes(groups, cfg['n_boot'], 3, cfg['bootstrap_seed'], cfg['alpha'])
    choices = []
    for env, meta in zip(bounds['groups'], details):
        selection = historical_selection(env, meta['labels'], meta['resources'], cfg['offset_quantiles'], cfg['epsilon_curve'], cfg['v_max'])
        choices.append(dict(**meta, **selection))
    save(out / 'bounds.json', bounds)
    save(out / 'choices.json', dict(groups=choices, uses_confirmation=False, primary_epsilon=.02,
                                   recipe_scope='One historically selected q per base model, including unqualified diagnostics as possible competitors; full q family is secondary'))
    # This package binds actual historical weights, scalers, indices, offsets,
    # forecast, source/raw-boundary and all executable code before any test read.
    save(out / 'freeze.json', dict(protocol_sha256=sha(args.protocol), sources=sources(cfg),
         historical_manifests={str(p.resolve()): sha(p) for p in manifests},
         prepared_manifest_sha256=sha(args.output / 'prepared/manifest.json'),
         choices_sha256=sha(out / 'choices.json'), historical_only=True,
         preflight_receipt_sha256=sha(ROOT / 'preflight_receipt.json'),
         deployment_sha256=sha(ROOT / 'deployment_manifest.json'),
         created_utc=datetime.now(timezone.utc).isoformat()))
    finish(out, receipt)
    print('HISTORICAL_PACKAGE_FROZEN', sha(out / 'freeze.json'), flush=True)


def validate_freeze(args, cfg: dict) -> dict:
    verify(args.output / 'chosen', args, cfg)
    freeze = json.loads((args.output / 'chosen/freeze.json').read_text())
    preflight = json.loads((ROOT / 'preflight_receipt.json').read_text())
    deployment = json.loads((ROOT / 'deployment_manifest.json').read_text())
    if (sha(ROOT / 'preflight_receipt.json') != freeze['preflight_receipt_sha256']
            or sha(ROOT / 'deployment_manifest.json') != freeze['deployment_sha256']
            or preflight['exit_code'] != 0 or not preflight['pbs_job']
            or preflight['sources'] != sources(cfg)
            or preflight['protocol_sha256'] != sha(args.protocol)
            or preflight['git_commit'] != deployment['git_commit']
            or deployment['protocol_sha256'] != sha(args.protocol)
            or deployment['sources'] != sources(cfg) or not deployment['git_commit']):
        raise ValueError('Preflight/deployment provenance not frozen')
    review_path = ROOT / 'REVIEW_RELEASE.json'
    review = json.loads(review_path.read_text())
    if (sha(review_path) != deployment['review_release_sha256']
            or review['status'] != 'PASS_FOR_PRE_UNLOCK_IMPLEMENTATION'
            or review['blocking_findings']):
        raise ValueError('Independent implementation review not released')
    for name, digest in review['sources'].items():
        if sha(ROOT / name) != digest:
            raise ValueError('Implementation changed after review')
    if freeze['sources'] != sources(cfg) or freeze['protocol_sha256'] != sha(args.protocol):
        raise ValueError('Frozen executable differs')
    if sha(args.output / 'chosen/choices.json') != freeze['choices_sha256']:
        raise ValueError('Historical choices differ')
    if sha(args.output / 'prepared/manifest.json') != freeze['prepared_manifest_sha256']:
        raise ValueError('Prepared manifest differs')
    verify(args.output / 'prepared', args, cfg)
    for path, digest in freeze['historical_manifests'].items():
        if sha(Path(path)) != digest:
            raise ValueError('Historical manifest differs')
        verify(Path(path).parent, args, cfg)
    for name, digest in cfg['historical_input_sha256'].items():
        if sha(Path(cfg['historical_root']) / name) != digest:
            raise ValueError('Frozen historical source changed')
    return freeze


def unlock(args, cfg: dict) -> None:
    out = args.output / 'unlocked'
    if existing(out, args, cfg):
        return
    validate_freeze(args, cfg)
    source = Path(cfg['annual_source_root'])
    archive = source / '2025.zip'
    if sha(archive) != cfg['annual_sha256']['2025'] or archive.stat().st_size != cfg['test_archive_bytes']:
        raise ValueError('Sealed archive identity differs')
    prepared = args.output / 'prepared'
    receipt = begin(out, args, cfg, [archive, args.output / 'chosen/freeze.json', prepared / 'manifest.json'], 'unlock')
    event = dict(utc=datetime.now(timezone.utc).isoformat(), pbs_job=os.environ['PBS_JOBID'],
                 freeze_sha256=sha(args.output / 'chosen/freeze.json'), protocol_sha256=sha(args.protocol),
                 archive_sha256=cfg['annual_sha256']['2025'], reason='One pre-bound confirmation read after complete historical package freeze')
    with (args.output / 'UNLOCK_EVENT.json').open('x', encoding='utf-8') as f:
        json.dump(event, f, indent=2)
    nt = 365 * 144 + 1
    boundary = dict(np.load(prepared / 'raw_2024_boundary.npz'))
    schemas = json.loads((prepared / 'consumed_schema.json').read_text())
    data, reports = {}, {}
    for table, fields in qualifier.TABLES.items():
        values, seen = np.full((nt * 21, len(fields)), np.nan), np.zeros(nt * 21, bool)
        values[:21], seen[:21] = boundary[table + '_values'], boundary[table + '_seen']
        reports[table] = read_table(archive, 2025, table, values, seen, expected_schema=schemas[table])
        data[table] = values
    channels = np.full((nt * 21, 4), np.nan)
    turbine, grid = data['tblSCTurbine'], data['tblSCTurGrid']
    channels[:,0] = np.where(np.isfinite(turbine[:,0]) & (turbine[:,0] >= 0), turbine[:,0], np.nan)
    channels[:,1:3] = np.where(np.isfinite(grid), grid, np.nan)
    valid = np.isfinite(turbine[:,1:4]).all(axis=1)
    channels[valid,3] = turbine[valid,1:4].mean(axis=1)
    channels = channels.reshape(nt,21,4)
    historical = np.load(Path(cfg['historical_root']) / 'historical_physical_channels.npy')
    np.testing.assert_array_equal(historical[-1], channels[0])
    merged = np.concatenate((historical, channels[1:]), axis=0)
    np.save(out / 'physical_channels.npy', merged)
    issues = anchor_window(*cfg['windows']['confirmation'], 6)
    model = joblib.load(prepared / 'point_forecaster.joblib')
    forecast = forecast_at(model, merged, issues)
    np.savez_compressed(out / 'confirmation.npz', anchors=issues, forecast=forecast)
    receipt.update(qualification='CONFIRMATION_COORDINATES_QUALIFIED', tables=reports,
                   finite_target_count=int(np.isfinite(merged[issues+6,:,1]).sum()),
                   negative_power_preserved=int(np.sum(np.isfinite(channels[:,:,1]) & (channels[:,:,1] < 0))),
                   test_opened=True, refit=False, event_sha256=sha(args.output / 'UNLOCK_EVENT.json'))
    finish(out, receipt)
    print('TEST_COORDINATES_QUALIFIED_NO_REFIT', flush=True)


def evaluate(args, cfg: dict) -> None:
    task = task_table(cfg)[args.task_index]
    out = args.output / 'evaluate' / str(args.task_index)
    if existing(out, args, cfg):
        return
    hist = args.output / 'historical' / str(args.task_index)
    producer = verify(hist, args, cfg)
    verify(args.output / 'unlocked', args, cfg)
    verify(args.output / 'chosen', args, cfg)
    if producer['task'] != task:
        raise ValueError('Historical model task mismatch')
    receipt = begin(out, args, cfg, [hist / 'manifest.json', args.output / 'unlocked/manifest.json',
                                    args.output / 'chosen/freeze.json'], 'evaluate')
    receipt['task'] = task
    condition = cfg['conditions'][task['condition']]
    stage = stage_data(args, cfg, 'confirmation', condition)
    model = None if task['estimator'] == 'Persistence' else joblib.load(hist / 'model.joblib')
    raw = predict(model, stage, task, condition)
    offsets = np.load(hist / 'offsets.npy')
    blocks = totals_for_offsets(stage['shortfall'], raw, stage['mask'], stage['anchors'], offsets)
    # Independent flattened-cell accumulation avoids the producer's day slicing.
    m, shortfall = stage['mask'], stage['shortfall']
    days = np.repeat(stage['anchors'] // 144, m.shape[1])[m.reshape(-1)]
    day_ids = np.unique(stage['anchors'] // 144)
    for qi, offset in enumerate(offsets):
        reserve = np.maximum(raw + offset, 0)[m]
        actual = shortfall[m]
        direct = np.bincount(days, weights=(reserve + 10 * np.maximum(actual-reserve, 0))/6, minlength=int(day_ids[-1])+1)[day_ids]
        count = np.bincount(days, minlength=int(day_ids[-1])+1)[day_ids]
        violation = np.bincount(days, weights=(actual > reserve).astype(float), minlength=int(day_ids[-1])+1)[day_ids]
        if (not np.allclose(direct, blocks[f'{qi}__loss_sum'], rtol=0, atol=1e-7)
                or not np.array_equal(count, blocks[f'{qi}__count'])
                or not np.array_equal(violation, blocks[f'{qi}__violation_sum'])):
            raise ValueError('Action accounting failed')
    np.savez_compressed(out / 'raw_actions.npz', raw=raw, offsets=offsets, anchors=stage['anchors'],
                        shortfall=stage['shortfall'], mask=stage['mask'])
    np.savez_compressed(out / 'blocks.npz', **blocks)
    save(out / 'metadata.json', dict(task=task, identity=stage['identity'], resource=resource(task, condition),
                                    historical_model_manifest_sha256=sha(hist / 'manifest.json'),
                                    independent_array_checks=len(cfg['offset_quantiles']) * len(np.unique(stage['anchors']//144)) * 3,
                                    refit=False))
    finish(out, receipt)
    print('CONFIRMATION_EVALUATED', args.task_index, flush=True)


def aggregate(args, cfg: dict) -> None:
    out = args.output / 'aggregate'
    if existing(out, args, cfg):
        return
    groups, details, manifests = groups_at(args, cfg, 'evaluate')
    verify(args.output / 'chosen', args, cfg)
    choices = json.loads((args.output / 'chosen/choices.json').read_text())['groups']
    receipt = begin(out, args, cfg, manifests + [args.output / 'chosen/manifest.json'], 'aggregate')
    # The primary family contains only pre-test selected primary policies plus
    # the frozen reference, never all models searched on the confirmation year.
    primary_index = next(i for i, item in enumerate(details) if item['condition'] == 'pitch_withheld')
    chosen = choices[primary_index]
    indices = sorted(set(chosen['sets']['0.02']['original_indices'] + [chosen['reference_index']]))
    g = groups[primary_index]
    primary = dict(costs=g['costs'][:,indices], violations=g['violations'][:,indices], counts=g['counts'],
                   exact_pair=g['exact_pair'][np.ix_(indices,indices)])
    primary_bounds = streamed_envelopes([primary], cfg['n_boot'], 3, cfg['bootstrap_seed'], cfg['alpha'])
    selected = [indices.index(i) for i in chosen['sets']['0.02']['original_indices']]
    verdict = confirmation_verdict(primary_bounds['groups'][0], selected, indices.index(chosen['reference_index']),
                                   .02, cfg['v_max'], chosen['reference_historically_qualified'])
    save(out / 'primary.json', dict(verdict=verdict, labels=[details[primary_index]['labels'][i] for i in indices], bounds=primary_bounds,
                                   choices_sha256=sha(args.output / 'chosen/choices.json'), uses_test_selection=False))
    print('PRIMARY_CONFIRMATION', verdict['status'], flush=True)
    results = []
    for span in (3,1,7):
        bound = streamed_envelopes(groups, cfg['n_boot'], span, cfg['bootstrap_seed'], cfg['alpha'])
        for env, meta, hist_choice in zip(bound['groups'], details, choices):
            fixed = {}
            for eps in cfg['epsilon_curve']:
                chosen_indices = hist_choice['sets'][str(eps)]['original_indices']
                fixed[str(eps)] = confirmation_verdict(env, chosen_indices, hist_choice['reference_index'],
                                                     eps, cfg['v_max'], hist_choice['reference_historically_qualified'])
            all_family = []
            for eps in cfg['epsilon_curve']:
                identified = near_optimal_set(env['risk_lower'], env['risk_upper'], env['relative_ratio_upper'],
                            [True]*len(meta['labels']), meta['resources'], eps, cfg['v_max'])
                necessity = diagnose(env['risk_lower'], env['risk_upper'], env['relative_ratio_lower'],
                                     meta['resources'], identified['minimum_resource_indices'], eps, cfg['v_max'])
                all_family.append(dict(epsilon=eps, sufficient_set=identified, minimum_audit=necessity))
            results.append(dict(**meta, span=span, **env, historical_frozen_assessment=fixed,
                                secondary_retrospective_full_q=all_family,
                                critical=bound['critical'], coordinate_family_size=bound['coordinate_family_size'],
                                draw_sha256=bound['draw_sha256']))
        save(out / f'secondary_span{span}.json', dict(results=results[-len(groups):],
             scope='Predeclared secondary sensitivity and test-side finite-family capability; never substitutes primary confirmation'))
        print('SECONDARY_COMPLETE', span, flush=True)
    save(out / 'summary.json', dict(primary_status=verdict['status'], independent_confirmation_evaluated=True,
         model_refits_after_unlock=0, primary_scope='Pre-test selected pitch-withheld recipe versus fixed full-information reference at 2%',
         E07_activated=False, no_field_safety_certificate=True))
    finish(out, receipt)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('stage', choices=['preflight','prepare','historical','choose','unlock','evaluate','aggregate'])
    p.add_argument('--protocol', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--task-index', type=int, default=0)
    args = p.parse_args()
    if not os.environ.get('PBS_JOBID'):
        raise ValueError('Numeric confirmation execution requires allocated PBS node')
    cfg = json.loads(args.protocol.read_text(encoding='utf-8'))
    if cfg['seeds'] != [201,202,203,204,205] or cfg['v_max'] != .1 or cfg['primary_epsilon'] != .02:
        raise ValueError('Unsupported scientific configuration')
    try:
        with threadpool_limits(limits=2):
            globals()[args.stage](args, cfg)
    except BaseException as exc:
        stage_path = {'prepare':'prepared', 'choose':'chosen', 'unlock':'unlocked'}.get(args.stage, args.stage)
        output = args.output / stage_path
        if args.stage in ('historical','evaluate'):
            output = output / str(args.task_index)
        receipt_path = output / 'receipt.json'
        if receipt_path.exists() and not (output / 'manifest.json').exists():
            record = json.loads(receipt_path.read_text())
            if record.get('status') == 'RUNNING':
                record.update(status='FAILED_PRESERVED', error=repr(exc), finished_utc=datetime.now(timezone.utc).isoformat())
                save(receipt_path, record)
        raise


if __name__ == '__main__':
    main()
