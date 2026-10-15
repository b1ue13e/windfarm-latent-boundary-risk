"""Exact read-only audit of saved factorial actions, tables and daily blocks."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--extension-manifest-sha256', required=True)
    args = parser.parse_args()
    if not os.environ.get('PBS_JOBID'):
        raise RuntimeError('Audit only in PBS allocation')
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    root = args.workspace.resolve()
    extension = root / 'metis_execution/extensions/factorial_four_conditions_v2_attempt1'
    manifest = extension / 'extension_manifest.json'
    if sha(manifest) != args.extension_manifest_sha256:
        raise ValueError('Wrong original extension identity')
    package = json.loads(manifest.read_text())
    for row in package['files']:
        if sha(extension / row['name']) != row['sha256']:
            raise ValueError('Extension source changed')
    for row in package['frozen_files']:
        if sha(root / row['relative_path']) != row['sha256']:
            raise ValueError('Frozen dependency changed')
    sys.path[:0] = [str(extension), str(root / 'scripts'), str(root)]
    import numpy as np
    import pandas as pd
    import torch
    from raw_replay import verify_run_receipt, verify_records
    from replay_factorial_four_conditions import CONDITIONS, VARIANTS, paired_blocks
    from replay_factorial import binned, categorical
    from windfarm_moe.data import load_cache_bundle
    base = root / 'artifacts/raw_replay_20261015_v2'
    family = base / 'factorial_four_conditions_v2'
    cache = load_cache_bundle(base / 'cache_wtb', mmap_mode='r')
    canonical = np.load(base / 'fixed_forecast_residuals.npz')
    completed = []
    frames = []
    parser_differences = []
    def successful(path):
        record = json.loads(path.read_text())
        if (record.get('status') != 'EXECUTED' or record.get('exit_code') != 0 or
            not record.get('inputs') or not record.get('outputs') or record.get('missing_outputs')):
            raise ValueError('Incomplete successful execution: ' + str(path))
        verify_run_receipt(path)
    for condition in CONDITIONS:
        for seed in range(201, 206):
            receipt = family / f'execution/{condition}_{seed}/record.json'
            successful(receipt)
            directory = family / condition / f'seed{seed}'
            verify_records(json.loads((directory / 'output_manifest.json').read_text()))
            frame = pd.read_csv(directory / 'seed_results.csv', float_precision='round_trip')
            # Match the frozen summarizer's actual default CSV parse, separately
            # from round-trip checks of the original per-run serialized metrics.
            aggregate_input = pd.read_csv(directory / 'seed_results.csv')
            numeric = frame.select_dtypes(include='number').columns
            parser_differences.append({'condition': condition, 'seed': seed,
                'numeric_cells_changed_by_default_csv_parser': int(np.count_nonzero(
                    frame[numeric].to_numpy() != aggregate_input[numeric].to_numpy()))})
            expected = {(h, p, v) for h in (1, 6) for p in ('Full', 'Boundary') for v in VARIANTS}
            if (len(frame) != 44 or set(zip(frame.horizon, frame.population, frame.variant)) != expected or
                set(frame.condition) != {condition} or set(frame.seed) != {seed}):
                raise ValueError('Incomplete/duplicate factorial cells')
            frames.append(aggregate_input)
            for horizon in (1, 6):
                with np.load(directory / f'h{horizon}_predictions.npz') as predictions:
                    shortfall = predictions['shortfall']
                    mask = predictions['mask']
                    anchors = canonical['anchor_indices_test']
                    if not np.array_equal(predictions['anchor_indices'], anchors):
                        raise ValueError('Canonical anchors differ')
                    checks = {
                        'shortfall': canonical[f'shortfall_test_seed{seed}'][:, horizon - 1, :].reshape(-1),
                        'mask': (canonical['mask_test'][:, horizon - 1, :].reshape(-1) > .5),
                        'anchor_time_index': cache.time_index[anchors], 'node_ids': cache.node_ids,
                        'raw_wind': np.asarray(cache.physics[anchors, :, cache.metadata['physics_names'].index('Wspd')]).reshape(-1),
                        'day_ids': np.repeat(cache.time_index[anchors, 0], len(cache.node_ids))}
                    for key, expected_values in checks.items():
                        equal = np.array_equal(predictions[key], expected_values, equal_nan=True) if expected_values.dtype.kind in 'fc' else np.array_equal(predictions[key], expected_values)
                        if not equal:
                            raise ValueError('Canonical identity differs: ' + key)
                    actions = {variant: predictions[variant] for variant in VARIANTS}
                    posterior = {}
                    for model_family in ('aligned', 'dense_classifier'):
                        posterior[model_family] = {}
                        for split in ('val', 'test'):
                            gate = np.load(directory / model_family / split / 'gate.npy', mmap_mode='r')
                            posterior[model_family][split] = (gate[..., 2].reshape(-1) /
                                np.maximum(gate[..., :3].sum(-1).reshape(-1), 1e-9))
                    val_shortfall = canonical[f'shortfall_val_seed{seed}'][:, horizon - 1, :].reshape(-1)
                    val_mask = canonical['mask_val'][:, horizon - 1, :].reshape(-1) > .5
                    global_q = float(np.quantile(val_shortfall[val_mask], .9))
                    oracle_val = np.asarray(cache.regime_primary[canonical['anchor_indices_val']]).reshape(-1)
                    oracle_test = np.asarray(cache.regime_primary[anchors]).reshape(-1)
                    rng = np.random.default_rng(seed)
                    permutations = {
                        'posterior_val_permutation': rng.permutation(len(posterior['aligned']['val'])),
                        'posterior_test_permutation': rng.permutation(len(posterior['aligned']['test'])),
                        'oracle_val_permutation': rng.permutation(len(oracle_val)),
                        'oracle_test_permutation': rng.permutation(len(oracle_test))}
                    for key, values in permutations.items():
                        if not np.array_equal(predictions[key], values):
                            raise ValueError('Seeded control permutation differs: ' + key)
                    if (not np.array_equal(predictions['shuffled_val_labels'], oracle_val[permutations['oracle_val_permutation']]) or
                        not np.array_equal(predictions['shuffled_test_labels'], oracle_test[permutations['oracle_test_permutation']])):
                        raise ValueError('Shuffled diagnostic labels differ')
                    selected_head_indices = np.flatnonzero(val_mask)
                    if len(selected_head_indices) > 20000:
                        selected_head_indices = rng.choice(selected_head_indices, 20000, replace=False)
                    with np.load(directory / 'aligned/val/observed_inputs.npz') as arrived:
                        val_wind = arrived['wind'].reshape(-1)
                    expected_actions = {
                        'C_Posterior': binned(posterior['aligned']['val'], posterior['aligned']['test'],
                            val_shortfall, val_mask)[0],
                        'I_Dense_Posterior': binned(posterior['dense_classifier']['val'], posterior['dense_classifier']['test'],
                            val_shortfall, val_mask)[0],
                        'F_Randomized_Posterior': binned(
                            posterior['aligned']['val'][predictions['posterior_val_permutation']],
                            posterior['aligned']['test'][predictions['posterior_test_permutation']],
                            val_shortfall, val_mask)[0],
                        'D_Global': np.full_like(shortfall, global_q),
                        'G_Oracle_Diagnostic': categorical(oracle_val, oracle_test, val_shortfall, val_mask),
                        'E_Shuffled_Oracle_Diagnostic': categorical(predictions['shuffled_val_labels'],
                            predictions['shuffled_test_labels'], val_shortfall, val_mask),
                        'K_Wind_Bins': binned(val_wind, predictions['observed_wind'], val_shortfall,
                            val_mask, fixed_edges=np.linspace(0, 25, 11)[1:-1])[0],
                        'J_Posterior_Alias': actions['C_Posterior'],
                        'H_Shrinkage': .95 * actions['C_Posterior'] + .05 * global_q}
                    for variant, expected_values in expected_actions.items():
                        if not np.array_equal(actions[variant], expected_values):
                            raise ValueError('Reserve control algebra differs: ' + variant)
                    for population, selected in [('Full', mask),
                            ('Boundary', mask & (np.abs(predictions['raw_wind'] - 10.5) <= 1.))]:
                        for variant, values in actions.items():
                            if not np.isfinite(values[selected]).all() or not np.isfinite(shortfall[selected]).all():
                                raise ValueError('Nonfinite valid action/target')
                            reserve = float(values[selected].sum() / 6)
                            shortage = float(np.maximum(shortfall[selected] - values[selected], 0).sum() / 6)
                            actual = dict(n_cells=int(selected.sum()), reserve_kwh=reserve,
                                shortage_kwh=shortage, psrei_kwh=reserve + 10 * shortage,
                                violation_rate=float(np.mean(shortfall[selected] > values[selected])))
                            row = frame[(frame.horizon == horizon) & (frame.population == population) &
                                        (frame.variant == variant)].iloc[0]
                            for key, value in actual.items():
                                if row[key] != value:
                                    raise ValueError(f'Exact CSV mismatch: {condition}/{seed}/h{horizon}/{population}/{variant}/{key}')
                        expected_blocks = paired_blocks(actions, shortfall, selected, predictions['day_ids'])
                        with np.load(directory / f'h{horizon}_{population}_day_blocks.npz') as saved:
                            if set(saved.files) != set(expected_blocks):
                                raise ValueError('Daily block keys differ')
                            for key, values in expected_blocks.items():
                                if not np.array_equal(saved[key], values):
                                    raise ValueError('Exact native daily-block mismatch: ' + key)
                selected_sets = []
                for variant in ('A_No_Alignment_Context', 'B_Aligned_Context'):
                    head = directory / f'h{horizon}/{variant}'
                    checkpoint = torch.load(head / 'head.pt', map_location='cpu', weights_only=False)
                    if checkpoint['epochs'] != 5 or checkpoint['seed'] != seed or len(checkpoint['history']) != 5:
                        raise ValueError('Incomplete head training history')
                    if ([entry['epoch'] for entry in checkpoint['history']] != list(range(1, 6)) or
                        checkpoint['lr'] != .01 or checkpoint['batch_size'] != 2048 or
                        not np.isfinite([entry['pinball_loss'] for entry in checkpoint['history']]).all()):
                        raise ValueError('Nonfinite head losses')
                    if not all(torch.isfinite(tensor).all() for tensor in checkpoint['model_state'].values()):
                        raise ValueError('Nonfinite head parameters')
                    selected_sets.append(np.load(head / 'selected_validation_indices.npy'))
                if not np.array_equal(*selected_sets):
                    raise ValueError('A/B validation-head populations differ')
                if not np.array_equal(selected_sets[0], selected_head_indices):
                    raise ValueError('Seeded head training sample differs')
            completed.append({'condition': condition, 'seed': seed,
                              'receipt_sha256': sha(receipt), 'cells': 44})
    successful(family / 'execution/aggregate/record.json')
    aggregate = family / 'aggregate'
    verify_records(json.loads((aggregate / 'output_manifest.json').read_text()))
    result = pd.concat(frames, ignore_index=True)
    saved_rows = pd.read_csv(aggregate / 'all_seed_results.csv', float_precision='round_trip')
    pd.testing.assert_frame_equal(result, saved_rows, check_exact=True)
    summary = result.groupby(['condition', 'horizon', 'population', 'variant']).agg(
        psrei_mean=('psrei_kwh', 'mean'), psrei_sd=('psrei_kwh', 'std'), n_seeds=('seed', 'nunique'),
        violation_mean=('violation_rate', 'mean'), reserve_mean=('reserve_kwh', 'mean'),
        shortage_mean=('shortage_kwh', 'mean')).reset_index()
    saved_summary = pd.read_csv(aggregate / 'summary.csv', float_precision='round_trip')
    pd.testing.assert_frame_equal(summary, saved_summary, check_exact=True)
    if len(result) != 880 or len(summary) != 176 or not summary.n_seeds.eq(5).all():
        raise ValueError('Incomplete full-family seed coverage')
    report = {'pbs_job_id': os.environ['PBS_JOBID'], 'status': 'EXACT_ARTIFACT_ARITHMETIC_VERIFIED',
        'runs': completed, 'rows': len(result), 'summary_rows': len(summary),
        'audit_source_sha256': sha(__file__), 'extension_manifest_sha256': sha(manifest),
        'csv_parser_observations': parser_differences,
        'scientific_completion': False,
        'scope': 'actions/targets/head-history/native-block/table arithmetic only; no superiority or whole-paper certificate'}
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
