"""Replay external saved-weight inference and exact decision/statistical artifacts."""
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
    parser.add_argument('--frozen-input-manifest-sha256', required=True)
    args = parser.parse_args()
    if not os.environ.get('PBS_JOBID'):
        raise RuntimeError('Audit only inside PBS allocation')
    root = args.workspace.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    frozen = root / 'metis_input_manifest.json'
    if sha(frozen) != args.frozen_input_manifest_sha256:
        raise ValueError('Wrong frozen source/input manifest')
    for row in json.loads(frozen.read_text()):
        if sha(root / row['relative_path']) != row['sha256']:
            raise ValueError('Frozen input/source differs: ' + row['relative_path'])
    sys.path[:0] = [str(root / 'scripts'), str(root)]
    import numpy as np
    import pandas as pd
    import torch
    from raw_replay import verify_run_receipt, verify_records
    from replay_provenance import provenance, finalize, file_record
    from windfarm_moe.data import load_cache_bundle, RegimeWindowDataset
    from repair_exp01_pitch_withheld_v3 import infer_gates, assert_forecast_alignment, fit_bins, block_delta
    from hierarchical_bootstrap import compute_hierarchical_joint_bootstrap
    if not torch.cuda.is_available():
        raise RuntimeError('Allocated GPU required for original inference replay')
    base = root / 'artifacts/raw_replay_external_models_20261015'
    transfer = base / 'matched_transfer'
    source = root / 'artifacts/raw_replay_20261015_v2/models/aligned_force'
    def successful(path):
        record = json.loads(path.read_text())
        if (record.get('status') != 'EXECUTED' or record.get('exit_code') != 0 or
            not record.get('inputs') or not record.get('outputs') or record.get('missing_outputs')):
            raise ValueError('Incomplete successful execution: ' + str(path))
        verify_run_receipt(path)
        return record
    successful(base / 'execution/matched_transfer/record.json')
    cache_map = json.loads((base / 'cache_map.json').read_text())
    seeds = pd.read_csv(transfer / 'exp01_pitchmasked_v3_seed_results.csv', float_precision='round_trip')
    joint = pd.read_csv(transfer / 'exp01_pitchmasked_v3_joint_statistics.csv', float_precision='round_trip')
    if (len(seeds) != 20 or len(joint) != 4 or seeds.duplicated(['farm_id', 'seed', 'horizon']).any() or
        set(zip(seeds.farm_id, seeds.seed, seeds.horizon)) !=
        {(f, s, h) for f in ('kelmarsh', 'penmanshiel') for s in range(201, 206) for h in ('h=1', 'h=6')}):
        raise ValueError('Incomplete/duplicate external rows')
    native = np.load(transfer / 'exp01_native_day_blocks_v4.npz')
    provenance(output, [frozen, base / 'cache_map.json',
        base / 'execution/matched_transfer/record.json',
        transfer / 'exp01_pitchmasked_v3_seed_results.csv',
        transfer / 'exp01_pitchmasked_v3_joint_statistics.csv',
        transfer / 'exp01_native_day_blocks_v4.npz'],
        {'scope': 'exact inference/actions/blocks/statistics audit; no scientific certificate',
         'pbs_job_id': os.environ['PBS_JOBID'], 'bootstrap': 5000, 'bootstrap_seed': 20261014})
    results = []
    blocks = {}
    operation_order = []
    gate_provenance = json.loads((transfer / 'exp01_pitchmasked_v3_provenance.json').read_text())['results']
    for farm in ('kelmarsh', 'penmanshiel'):
        cache_path = Path(cache_map[farm])
        if not cache_path.is_absolute():
            cache_path = root / cache_path
        bundle = load_cache_bundle(cache_path, mmap_mode='r')
        if (bundle.metadata['hist_len'], bundle.metadata['pred_len']) != (36, 24):
            raise ValueError('Unexpected external window protocol')
        verify_records(json.loads((cache_path.parent / 'output_manifest.json').read_text()))
        for seed in range(201, 206):
            source_run = source / f'seed{seed}'
            successful(root / f'artifacts/raw_replay_20261015_v2/execution/train_aligned_force_{seed}/record.json')
            successful(base / f'execution/{farm}_{seed}/record.json')
            forecast = base / farm / f'seed{seed}'
            verify_records(json.loads((forecast / 'output_manifest.json').read_text()))
            verify_records(json.loads((source_run / 'output_manifest.json').read_text()))
            recorded = [p for p in gate_provenance if p['farm'] == farm and p['seed'] == seed]
            if len(recorded) != 1 or recorded[0]['checkpoint_sha256'] != sha(source_run / 'best_model.pt'):
                raise ValueError('Source checkpoint provenance differs')
            if (recorded[0]['summary_sha256'] != sha(source_run / 'training_summary.json') or
                recorded[0]['target_cache_metadata_sha256'] != sha(cache_path / 'metadata.json')):
                raise ValueError('Source summary/target cache provenance differs')
            gates = {}
            anchors = {}
            target = {}
            mask = {}
            pred = {}
            directory = output / farm / f'seed{seed}'
            directory.mkdir(parents=True, exist_ok=False)
            for split in ('val', 'test'):
                gate_path = transfer / f'{farm}_seed{seed}_{split}_gate_pitchmasked.npy'
                if sha(gate_path) != recorded[0]['gate_hashes'][split]:
                    raise ValueError('Saved inference hash differs')
                replay, indices, checkpoint, _ = infer_gates(source_run, bundle, split, torch.device('cuda'))
                if (checkpoint.get('metadata', {}).get('dataset') != 'wtb' or
                    checkpoint.get('metadata', {}).get('num_nodes') != 134):
                    raise ValueError('Checkpoint is not the registered WTB source')
                saved = np.load(gate_path)
                if not np.array_equal(replay, saved):
                    np.save(directory / f'{split}_nonexact_replay_gate.npy', replay)
                    raise ValueError(f'Exact weight-to-gate replay differs: {farm}/{seed}/{split}')
                gates[split] = saved
                anchors[split] = RegimeWindowDataset(bundle, split, 36, 24).anchor_indices
                if not np.array_equal(indices, anchors[split]):
                    raise ValueError('Replay anchor population differs')
                metrics = forecast / f'{split}_metrics'
                if not np.array_equal(np.load(metrics / 'anchor_index.npy'), indices):
                    raise ValueError('Forecast/gate anchor population differs')
                target[split] = np.stack([np.asarray(bundle.target[a + 1:a + 25]) for a in indices])
                mask[split] = np.stack([np.asarray(bundle.target_mask[a + 1:a + 25]) for a in indices]).astype(bool)
                assert_forecast_alignment(metrics, bundle, indices, target[split], mask[split])
                pred[split] = np.load(metrics / 'pred.npy')
            wind_index = bundle.metadata['physics_names'].index('Wspd')
            wind = {split: np.asarray(bundle.physics_model[anchors[split], :, wind_index]) for split in ('val', 'test')}
            for lead in (0, 5):
                horizon = f'h={lead + 1}'
                sv = np.maximum(pred['val'][:, lead, :] - target['val'][:, lead, :], 0)
                st = np.maximum(pred['test'][:, lead, :] - target['test'][:, lead, :], 0)
                mv, mt = mask['val'][:, lead, :], mask['test'][:, lead, :]
                we, wq = fit_bins(wind['val'], sv, mv, 10)
                rb = wq[np.clip(np.digitize(wind['test'], we), 0, len(wq) - 1)]
                ge, gq = fit_bins(gates['val'][..., 2], sv, mv, 5)
                rc = gq[np.clip(np.digitize(gates['test'][..., 2], ge), 0, len(gq) - 1)]
                valid = mt & np.isfinite(st)
                cost_b = float(np.sum((rb + 10 * np.maximum(st - rb, 0))[valid]) * (1.0 / 6.0))
                cost_c = float(np.sum((rc + 10 * np.maximum(st - rc, 0))[valid]) * (1.0 / 6.0))
                values = {'psrei_kwh': cost_c, 'baseline_psrei_kwh': cost_b, 'delta_psrei_kwh': cost_c - cost_b,
                    'violation_rate_pct': float(np.mean(st[valid] > rc[valid]) * 100),
                    'baseline_violation_rate_pct': float(np.mean(st[valid] > rb[valid]) * 100),
                    'n_evaluated_cells': int(valid.sum())}
                row = seeds[(seeds.farm_id == farm) & (seeds.seed == seed) & (seeds.horizon == horizon)].iloc[0]
                if (row['checkpoint_sha256'] != sha(source_run / 'best_model.pt') or
                    row['training_summary_sha256'] != sha(source_run / 'training_summary.json') or
                    row['pitch_withheld_before_inference'] != True):
                    raise ValueError('Per-row source/withholding identity differs')
                for key, value in values.items():
                    if row[key] != value:
                        raise ValueError(f'Exact external CSV mismatch: {farm}/{seed}/{horizon}/{key}')
                delta, count = block_delta(st, rc, rb, valid, anchors['test'])
                prefix = f'{farm}_{horizon}_seed{seed}'
                if not np.array_equal(delta, native[prefix + '_delta']) or not np.array_equal(count, native[prefix + '_count']):
                    raise ValueError('Exact native paired-block mismatch')
                blocks.setdefault((farm, horizon), {})[seed] = delta
                block_ids = np.searchsorted(np.unique(anchors['test']), anchors['test']) // 144
                components = {}
                for label, reserve in [('posterior', rc), ('wind', rb)]:
                    for metric, cells in [('reserve_kwh', reserve * (1.0 / 6.0)),
                            ('shortage_kwh', np.maximum(st - reserve, 0) * (1.0 / 6.0)),
                            ('cost_kwh', (reserve + 10 * np.maximum(st - reserve, 0)) * (1.0 / 6.0))]:
                        components[label + '_' + metric] = np.bincount(block_ids,
                            weights=np.where(valid, cells, 0).sum(axis=1), minlength=len(delta))
                operation_order.append({'farm': farm, 'seed': seed, 'horizon': horizon,
                    'native_sum_minus_separate_cost_delta_kwh': float(delta.sum() - values['delta_psrei_kwh']),
                    'native_minus_separate_block_cost_delta_kwh':
                        (delta - (components['posterior_cost_kwh'] - components['wind_cost_kwh'])).tolist()})
                np.savez_compressed(directory / f'h{lead + 1}_audit_actions.npz',
                    canonical_forecast=pred['test'][:, lead, :], physical_target=target['test'][:, lead, :],
                    shortfall=st, valid=valid, reserve_posterior=rc, reserve_wind=rb,
                    val_shortfall=sv, val_valid=mv, val_anchors=anchors['val'],
                    wind_edges=we, wind_quantiles=wq, posterior_edges=ge, posterior_quantiles=gq,
                    anchor_indices=anchors['test'], time_index=bundle.time_index[anchors['test']],
                    node_ids=bundle.node_ids, native_delta=delta, native_count=count,
                    issue_block_ids=block_ids, **components)
                results.append({'farm': farm, 'seed': seed, 'horizon': horizon,
                    'checkpoint_sha256': sha(source_run / 'best_model.pt'),
                    'source_output_manifest_sha256': sha(source_run / 'output_manifest.json'),
                    'local_forecast_output_manifest_sha256': sha(forecast / 'output_manifest.json'),
                    'local_forecast_receipt_sha256': sha(base / f'execution/{farm}_{seed}/record.json'),
                    'raw_cache_output_manifest_sha256': sha(cache_path.parent / 'output_manifest.json'),
                    'metrics': values})
            print(f'EXACT_EXTERNAL_SEED_PASS {farm} {seed}', flush=True)
        del bundle
    statistics = []
    for (farm, horizon), seed_blocks in blocks.items():
        statistic = compute_hierarchical_joint_bootstrap(seed_blocks, n_boot=5000,
            two_stage_resample=True, random_seed=20261014)
        row = joint[(joint.farm_id == farm) & (joint.horizon == horizon)]
        if len(row) != 1:
            raise ValueError('Incomplete/duplicate joint rows')
        row = row.iloc[0]
        mapping = {'n_seeds': statistic['n_seeds'], 'n_time_blocks': statistic['n_blocks'],
            'mean_delta_psrei_kwh': statistic['joint_mean'], 'median_seed_delta_kwh': statistic['joint_median'],
            'seed_sd_kwh': statistic['joint_std'], 'joint_ci95_low_kwh': statistic['joint_ci_95'][0],
            'joint_ci95_high_kwh': statistic['joint_ci_95'][1],
            'joint_p_noninferior_P_delta_le_0': statistic['joint_p_non_inferior']}
        for key, value in mapping.items():
            if row[key] != value:
                raise ValueError(f'Exact hierarchical statistic mismatch: {farm}/{horizon}/{key}')
        np.save(output / f'{farm}_{horizon}_joint_resampling.npy', statistic['boot_samples'])
        statistics.append({'farm': farm, 'horizon': horizon, 'values': mapping})
    report = {'pbs_job_id': os.environ['PBS_JOBID'], 'status': 'EXACT_EXTERNAL_EVIDENCE_VERIFIED',
        'source_sha256': sha(__file__), 'results': results, 'statistics': statistics,
        'operation_order_observations': operation_order, 'scientific_completion': False,
        'scope': 'current raw-window external inference/actions/statistics only; no legacy reinstatement or whole-paper certificate'}
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    finalize(output)
    print(json.dumps({'status': report['status'], 'seed_rows': len(results), 'joint_rows': len(statistics),
                      'scientific_completion': False}), flush=True)


if __name__ == '__main__':
    main()
