"""Archive posterior/bin evidence while executing the hash-bound original C code.

Read-only inputs, new output directory only, no tolerance in the acceptance gate.
Two replay repeats are diagnostic, not a search over numerical configurations.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import platform
import sys
from datetime import datetime, timezone
from repo_paths import Path, repository_root

import numpy as np


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def policy_fragment(source):
    tree = ast.parse(source)
    main = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'main')
    loop = next(n for n in main.body if isinstance(n, ast.For) and isinstance(n.target, ast.Name) and n.target.id == 'seed')
    start = next((i for i, n in enumerate(loop.body) if isinstance(n, ast.FunctionDef) and n.name == 'get_probs'), None)
    stop = next((i for i, n in enumerate(loop.body) if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'r_B_val' for t in n.targets)), None)
    if start is None or stop is None or stop <= start:
        raise ValueError('Cannot locate original policy boundaries')
    return ast.fix_missing_locations(ast.Module(body=loop.body[start:stop], type_ignores=[]))


def bin_ids(probabilities, edges):
    ids = np.full(probabilities.shape, -1, dtype=np.int16)
    for i in range(len(edges) - 1):
        ids[(probabilities >= edges[i]) & (probabilities < edges[i+1])] = i
    if np.any(ids < 0):
        raise ValueError('Unassigned posterior bin')
    return ids


def compare_daily(blocks, mask, shortfall, reserve, cost, reference):
    nd = len(reference['n'])
    n = np.bincount(blocks, weights=mask.astype(float), minlength=nd)
    violation = np.bincount(blocks, weights=np.where(mask, (shortfall > reserve).astype(float), 0.), minlength=nd)
    summed_cost = np.bincount(blocks, weights=np.where(mask, cost, 0.), minlength=nd)
    exact = {'n_exact': bool(np.array_equal(n, reference['n'])),
             'violation_exact': bool(np.array_equal(violation, reference['C_viol'])),
             'cost_exact': bool(np.array_equal(summed_cost, reference['C_cost']))}
    return {**exact, 'accepted': all(exact.values()),
            'daily_n': n.tolist(), 'daily_violation': violation.tolist(),
            'daily_cost': summed_cost.tolist(),
            'daily_cost_delta': (summed_cost-reference['C_cost']).tolist(),
            'max_absolute_cost_delta_kwh': float(abs(summed_cost-reference['C_cost']).max()),
            'total_cost_delta_kwh': float((summed_cost-reference['C_cost']).sum()),
            'mismatched_cost_blocks_1based': (np.flatnonzero(summed_cost != reference['C_cost'])+1).tolist()}


def runtime(torch):
    return {'host': platform.node(), 'python': sys.version, 'numpy': np.__version__,
            'torch': torch.__version__, 'cuda': torch.version.cuda,
            'gpu': torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
            'cudnn': torch.backends.cudnn.version(),
            'cudnn_benchmark': torch.backends.cudnn.benchmark,
            'cudnn_deterministic': torch.backends.cudnn.deterministic,
            'cudnn_tf32': torch.backends.cudnn.allow_tf32,
            'matmul_tf32': torch.backends.cuda.matmul.allow_tf32,
            'deterministic_algorithms': torch.are_deterministic_algorithms_enabled(),
            'torch_threads': torch.get_num_threads(),
            'cublas_workspace_config': os.environ.get('CUBLAS_WORKSPACE_CONFIG'),
            'omp_threads_env': os.environ.get('OMP_NUM_THREADS'),
            'pbs_job_id': os.environ.get('PBS_JOBID')}


def run(args):
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError('Refusing to overwrite an existing evidence directory')
    source = args.original_source.resolve()
    provenance = json.loads(args.provenance.read_text(encoding='utf-8'))
    if sha(source) != provenance['executed_script']['sha256']:
        raise ValueError('Original executed source hash mismatch')
    expected = {Path(entry['path']).name: entry['sha256'].lower() for entry in provenance['inputs']}
    checkpoint_expected = [entry['sha256'].lower() for entry in provenance['inputs'] if entry['path'].endswith('/seed201/best_model.pt')]
    if checkpoint_expected != [sha(args.checkpoint)]:
        raise ValueError('Seed201 checkpoint does not match original provenance')
    ref_manifest = json.loads(args.reference_manifest.read_text(encoding='utf-8'))
    ref_hashes = {Path(row['path']).name: row['sha256'] for row in ref_manifest['files']}
    if sha(args.reference) != ref_hashes[args.reference.name]:
        raise ValueError('Original reference manifest mismatch')
    protected = {str(source): sha(source), str(args.provenance.resolve()): sha(args.provenance),
                 str(args.checkpoint.resolve()): sha(args.checkpoint),
                 str(args.reference.resolve()): sha(args.reference),
                 str(args.reference_manifest.resolve()): sha(args.reference_manifest)}
    for path in [args.residuals, args.metadata, *sorted(args.cache.glob('*.npy'))]:
        expected_name = 'metadata.json' if path == args.metadata else path.name
        digest = sha(path)
        if digest != expected[expected_name]:
            raise ValueError(f'Original input mismatch: {path}')
        protected[str(path.resolve())] = digest
    source_text = source.read_text(encoding='utf-8')
    fragment = policy_fragment(source_text)
    os.environ['WINDFARM_REPO_ROOT'] = str(args.workspace.resolve())
    os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(args.workspace.resolve()))
    original_ns = {'__name__': 'hash_bound_original_source', '__file__': str(source)}
    exec(compile(ast.parse(source_text), str(source), 'exec'), original_ns)
    torch = original_ns['torch']
    for module in list(sys.modules.values()):
        name = getattr(module, '__file__', None)
        if name and Path(name).resolve().is_relative_to(args.workspace.resolve() / 'windfarm_moe') and name.endswith('.py'):
            path = Path(name).resolve()
            relative = path.relative_to(args.workspace.resolve()).as_posix()
            if sha(path) != provenance['source_sha256'][relative]:
                raise ValueError(f'Imported source mismatch: {relative}')
            protected[str(path)] = sha(path)
    if args.profile == 'prior_local':
        torch.set_num_threads(4)
        torch.backends.cudnn.benchmark = False
    # Seed is explicit for replay; historical initialization RNG was not archived.
    torch.manual_seed(201)
    np.random.seed(20261021)
    bundle = original_ns['load_cache_bundle'](args.cache, mmap_mode='r')
    bound_metadata = json.loads(args.metadata.read_text(encoding='utf-8'))
    differences = {k: [bundle.metadata.get(k), bound_metadata.get(k)] for k in set(bundle.metadata) | set(bound_metadata) if bundle.metadata.get(k) != bound_metadata.get(k)}
    if set(differences) - {'class_weight_source_cache'}:
        raise ValueError('Cache numeric metadata differs from bound original')
    protected[str((args.cache/'metadata.json').resolve())] = sha(args.cache/'metadata.json')
    bundle.metadata = bound_metadata
    f = np.load(args.residuals)
    spec = original_ns['DegradationSpec'](delay_steps=0, withheld_channels=('Pab_mean', 'Pab_std'))
    val_ds = original_ns['UnifiedArrivalDataset'](bundle, 'val', hist_len=36, pred_len=24, degradation=spec)
    test_ds = original_ns['UnifiedArrivalDataset'](bundle, 'test', hist_len=36, pred_len=24, degradation=spec)
    for split, ds in [('val', val_ds), ('test', test_ds)]:
        if not np.array_equal(ds.anchor_indices, f[f'anchor_indices_{split}']):
            raise ValueError('Frozen anchors differ')
        if not np.array_equal(bundle.time_index[ds.anchor_indices], f[f'anchor_time_index_{split}']):
            raise ValueError('Frozen time coordinates differ')
    if not np.array_equal(bundle.node_ids, f['node_ids']):
        raise ValueError('Frozen node identity differs')
    val_loader = original_ns['DataLoader'](val_ds, batch_size=64, shuffle=False)
    test_loader = original_ns['DataLoader'](test_ds, batch_size=64, shuffle=False)
    device = torch.device(args.device)
    checkpoint = torch.load(args.checkpoint, map_location=device)
    from windfarm_moe.config import ModelConfig
    from windfarm_moe.model import RegimeAwareForecaster
    model = RegimeAwareForecaster(feature_dim=int(bundle.features.shape[-1]), pred_len=int(bundle.metadata['pred_len']),
                                 mode=str(checkpoint['train_config']['mode']), config=ModelConfig(**checkpoint['model_config'])).to(device)
    model.load_state_dict(checkpoint['model_state'])
    model.eval()
    wstats = bound_metadata['feature_stats']['Wspd']
    # Exact float32 recovery used by the original C source for Policy B context.
    wspd_val = (np.asarray(bundle.physics_model, dtype=np.float32)[val_ds.anchor_indices, :, 0].ravel()
                * float(wstats['std']) + float(wstats['mean']))
    wspd_test = (np.asarray(bundle.physics_model, dtype=np.float32)[test_ds.anchor_indices, :, 0].ravel()
                 * float(wstats['std']) + float(wstats['mean']))
    s_v = f['shortfall_val_seed201'][:, 5].ravel()
    s_t = f['shortfall_test_seed201'][:, 5].ravel()
    m_val = f['mask_val'][:, 5].ravel() > 0.5
    m_test = ((f['mask_test'][:, 5] > 0.5) & np.asarray(bundle.regime_primary_valid)[test_ds.anchor_indices].astype(bool)).ravel()
    blocks = np.repeat(np.arange(len(test_ds)) // 144, len(bundle.node_ids))
    reference = dict(np.load(args.reference))
    output.mkdir(parents=True, exist_ok=False)
    plan = {'started_utc': datetime.now(timezone.utc).isoformat(), 'command_argv': [sys.executable, *sys.argv],
            'profile': args.profile, 'runtime': runtime(torch), 'inputs_before': protected,
            'original_policy_ast_sha256': hashlib.sha256(ast.dump(fragment).encode()).hexdigest(),
            'script_sha256': sha(Path(__file__)), 'training_seed': 201, 'replay_numpy_seed': 20261021,
            'repeats': args.repeats, 'alpha': .05, 'q_star': .90, 'v_max': .10,
            'metadata_path_only_difference': differences,
            'limitations': ['Current default flags are observed replay flags, not a retrospective attestation of historical flags.',
                            'Repeat runs are fixed diagnostics, not a search for favorable results.',
                            'Exact daily gate has no numerical tolerance; original artifacts are not modified.']}
    write_json(output/'plan.json', plan)
    reports = []
    for repeat in range(1, args.repeats+1):
        ns = {**original_ns, 'seed':201, 'device':device, 'model':model, 'val_loader':val_loader, 'test_loader':test_loader,
              's_v':s_v, 's_t':s_t, 'm_val':m_val, 'wspd_val':wspd_val, 'wspd_test':wspd_test}
        exec(compile(fragment, str(source), 'exec'), ns)
        reserve = ns['r_C']
        cost = (reserve + 10*np.maximum(s_t-reserve,0)) * (1/6)
        report = compare_daily(blocks, m_test, s_t, reserve, cost, reference)
        edges = ns['pi_bins']
        val_bins, test_bins = bin_ids(ns['p_v'], edges), bin_ids(ns['p_t'], edges)
        report.update({'repeat': repeat, 'posterior_edges': edges.tolist(), 'reserve_quantiles': ns['c_bin_q'],
                       'val_bin_counts_valid': np.bincount(val_bins[m_val], minlength=5).tolist(),
                       'test_bin_counts_valid': np.bincount(test_bins[m_test], minlength=5).tolist(),
                       'runtime': runtime(torch)})
        archive = output/f'repeat{repeat}_posterior_and_bins.npz'
        np.savez_compressed(archive, posterior_val=ns['p_v'], posterior_test=ns['p_t'],
                            posterior_edges=edges, reserve_quantiles=np.asarray(ns['c_bin_q']),
                            val_bin_ids=val_bins, test_bin_ids=test_bins, reserve_test=reserve,
                            anchor_indices_val=val_ds.anchor_indices, anchor_indices_test=test_ds.anchor_indices,
                            node_ids=bundle.node_ids)
        report['archive_sha256'] = sha(archive)
        write_json(output/f'repeat{repeat}_report.json', report)
        reports.append(report)
        print(json.dumps({'repeat':repeat,'accepted':report['accepted'], 'maximum_daily_cost_delta':report['max_absolute_cost_delta_kwh'],
                          'edges':report['posterior_edges'], 'reserve_q':report['reserve_quantiles']}), flush=True)
    after = {p: sha(p) for p in protected}
    if protected != after:
        raise ValueError('Protected input mutated during replay')
    manifest = {'finished_utc': datetime.now(timezone.utc).isoformat(), 'inputs_unchanged':True, 'inputs_after':after,
                'all_repeats_exact':all(r['accepted'] for r in reports),
                'output_sha256':{p.name:sha(p) for p in output.iterdir() if p.is_file()},
                'scientific_status':'numeric replay evidence only; original selector and independent review status unchanged'}
    write_json(output/'manifest.json', manifest)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','original-source','provenance','cache','metadata','residuals','checkpoint','reference','reference-manifest','output'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--profile', choices=['original_source','prior_local'], required=True)
    parser.add_argument('--device', default='cuda:0')
    parser.add_argument('--repeats', type=int, default=2)
    run(parser.parse_args())
