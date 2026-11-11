"""Audit E04 time-step identity before exploratory wind/ramp/regime slicing.

Original arrays and thresholds are read-only. Reconstructed actions must close
all original daily counts, violations and costs before policy slices are used.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
import sys
from datetime import datetime, timedelta, timezone
from repo_paths import Path, repository_root

import numpy as np

ROOT = Path(repository_root())
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SEEDS = (201, 202, 203, 204, 205)
POLICIES = ('B', 'C', 'D', 'D10')
H = 6
Q = 0.90
CAP = 0.10
DT = 1 / 6


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def write_json(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def write_csv(path, rows):
    if not rows:
        return
    with path.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def metadata_path_difference(local, bound):
    differences = {key: {'local': local.get(key), 'receipt_bound': bound.get(key)}
                   for key in set(local) | set(bound) if local.get(key) != bound.get(key)}
    if set(differences) - {'class_weight_source_cache'}:
        raise ValueError('numeric or schema metadata differs from receipt-bound metadata')
    return differences


def native_blocks(anchors):
    if not np.all(np.diff(anchors) == 1):
        raise ValueError('native block anchors must be contiguous')
    return np.arange(len(anchors)) // 144


def assert_target_alignment(values, cache, anchors, lead):
    if not np.array_equal(values, cache[anchors + lead], equal_nan=True):
        raise ValueError(f'target alignment failed at lead {lead}')


def transition_mask(states):
    diff = np.diff(states, axis=0, prepend=states[:1]) != 0
    transition = diff.copy()
    for offset in range(1, 4):
        transition[offset:] |= diff[:-offset]
        transition[:-offset] |= diff[offset:]
    return transition


def check_daily_closure(policy, blocks, valid, violation, cost, reference):
    nblocks = len(reference['n'])
    n = np.bincount(blocks, weights=valid.astype(float), minlength=nblocks)
    v = np.bincount(blocks, weights=np.where(valid, violation.astype(float), 0), minlength=nblocks)
    c = np.bincount(blocks, weights=np.where(valid, cost, 0), minlength=nblocks)
    if not np.array_equal(n, reference['n']):
        raise ValueError('daily population closure failed')
    if not np.array_equal(v, reference[f'{policy}_viol']):
        raise ValueError(f'{policy}: daily violation closure failed; max difference {np.max(np.abs(v-reference[f"{policy}_viol"]))}')
    if not np.array_equal(c, reference[f'{policy}_cost']):
        raise ValueError(f'{policy}: exact daily cost closure failed; max difference {np.max(np.abs(c-reference[f"{policy}_cost"]))}')
    return {'n_exact': True, 'violations_exact': True, 'cost_exact': True, 'n_blocks': nblocks}


def summarize_partition(labels, valid, violation, reserve, shortfall, signed_error):
    rows = []
    for group in np.unique(labels):
        mask = valid & (labels == group)
        n = int(mask.sum())
        if not n:
            continue
        v = int(violation[mask].sum())
        rows.append({'group': str(group), 'n': n, 'violations': v,
                     'violation_rate': v / n, 'signed_excess_count': v - CAP * n,
                     'mean_reserve_kw': float(reserve[mask].mean()),
                     'mean_shortfall_kw': float(shortfall[mask].mean()),
                     'mean_forecast_error_kw': float(signed_error[mask].mean()),
                     'shortage_kwh': float(np.maximum(shortfall[mask] - reserve[mask], 0).sum() * DT)})
    return rows


def binned_reserve(s_val, x_val, x_test, mask_val, edges):
    fallback = float(np.quantile(s_val[mask_val], Q))
    quantiles, sizes = [], []
    result = np.zeros_like(x_test, dtype=s_val.dtype)
    for i in range(len(edges) - 1):
        m = mask_val & (x_val >= edges[i]) & (x_val < edges[i + 1])
        sizes.append(int(m.sum()))
        q = float(np.quantile(s_val[m], Q)) if m.sum() > 20 else fallback
        quantiles.append(q)
        result[(x_test >= edges[i]) & (x_test < edges[i + 1])] = q
    return result, quantiles, sizes


def posterior_actions(s_val, w_val, w_test, p_val, p_test, mask_val, b_test, wind_edges):
    edges = np.quantile(p_val[mask_val], np.linspace(0, 1, 6))
    edges[0], edges[-1] = -np.inf, np.inf
    c_test, _, _ = binned_reserve(s_val, p_val, p_test, mask_val, edges)
    c_val, _, _ = binned_reserve(s_val, p_val, p_val, mask_val, edges)
    b_val, _, _ = binned_reserve(s_val, w_val, w_val, mask_val, wind_edges)
    candidates = []
    for delta in [0.5, 1.0, 1.5, 2.0]:
        candidates.append((f'wspd_band_{delta}', abs(w_val - 10.5) <= delta, abs(w_test - 10.5) <= delta))
    for tau in [0.05, 0.1, 0.2, 0.5]:
        candidates.append((f'post_ge_{tau}', p_val >= tau, p_test >= tau))
    for low, high in [(0.1, 0.9), (0.2, 0.8), (0.05, 0.95)]:
        candidates.append((f'post_band_{low}_{high}', (p_val >= low) & (p_val <= high), (p_test >= low) & (p_test <= high)))
    scores = []
    for name, val_mask, test_mask in candidates:
        r_val = np.where(val_mask, c_val, b_val)
        score = float(np.sum((r_val + 10 * np.maximum(s_val - r_val, 0))[mask_val]) * DT)
        scores.append((name, score, test_mask))
    selected = min(scores, key=lambda row: row[1])
    return {'C': c_test, 'D': np.where(selected[2], c_test, b_test),
            'D10': np.where(abs(w_test - 10.5) <= 1.0, c_test, b_test)}, {
                'selected_validation_rule': selected[0],
                'candidate_validation_costs': {name: score for name, score, _ in scores}}


def infer_posteriors(bundle, checkpoint_path, device, seed):
    import torch
    from torch.utils.data import DataLoader
    from windfarm_moe.arrival_feed import DegradationSpec, UnifiedArrivalDataset
    from windfarm_moe.config import ModelConfig
    from windfarm_moe.model import RegimeAwareForecaster
    torch.manual_seed(seed)
    checkpoint = torch.load(checkpoint_path, map_location=device)
    model = RegimeAwareForecaster(feature_dim=int(bundle.features.shape[-1]),
                                 pred_len=int(bundle.metadata['pred_len']),
                                 mode=checkpoint['train_config']['mode'],
                                 config=ModelConfig(**checkpoint['model_config'])).to(device)
    model.load_state_dict(checkpoint['model_state'])
    model.eval()
    output = {}
    spec = DegradationSpec(delay_steps=0, withheld_channels=('Pab_mean', 'Pab_std'))
    for split in ('val', 'test'):
        dataset = UnifiedArrivalDataset(bundle, split, hist_len=36, pred_len=24, degradation=spec)
        values = []
        with torch.no_grad():
            for batch in DataLoader(dataset, batch_size=64, shuffle=False):
                _, gate, _ = model(batch['x_hist'].to(device), batch['edge_index_hist'].to(device),
                                   batch['edge_weight_hist'].to(device), batch['feature_mask_hist'].to(device),
                                   batch['anchor_physics'].to(device))
                p3 = gate[..., :3]
                values.append((p3[..., 2] / torch.clamp(p3.sum(dim=-1), min=1e-9)).cpu().numpy())
        output[split] = np.concatenate(values).ravel()
        print(f'posterior seed={seed} split={split} complete', flush=True)
    return output


def run(output, replay_posteriors, device):
    if output.exists():
        raise FileExistsError('Use a new analysis directory; existing evidence is never overwritten')
    if not output.resolve().is_relative_to((ROOT / 'analyses').resolve()):
        raise ValueError('New outputs must be in the analyses directory')
    cache = ROOT / 'artifacts/raw_replay_20261015_v2/cache_wtb'
    inputs = ROOT / 'experiments/E06/remote_e06_inputs/e06_exact_inputs'
    ref_root = ROOT / 'experiments/E04/results/e04_v2'
    provenance_path = ROOT / 'analyses/remote/J04/e06_bundle/evidence/provenance.json'
    provenance = json.loads(provenance_path.read_text(encoding='utf-8'))
    expected = {Path(entry['path']).name: entry['sha256'].lower() for entry in provenance['inputs']}
    metadata_path = inputs / 'cache_metadata.json'
    paths = [inputs / 'fixed_forecast_residuals.npz', metadata_path,
             *[cache / f'{name}.npy' for name in ('physics', 'physics_model', 'time_index', 'node_ids', 'target', 'target_mask', 'regime_primary', 'regime_primary_valid', 'feature_mask')]]
    if replay_posteriors:
        paths += [cache / f'{name}.npy' for name in ('features', 'edge_index', 'edge_weight', 'regime_aux', 'regime_aux_valid', 'coords')]
    source_files = ['windfarm_moe/data.py', 'windfarm_moe/arrival_feed.py', 'windfarm_moe/model.py', 'windfarm_moe/config.py']
    hashes = {}
    for path in paths:
        digest = sha(path)
        expected_name = 'metadata.json' if path == metadata_path else path.name
        if digest != expected[expected_name]:
            raise ValueError(f'J04 input hash mismatch: {path}')
        hashes[str(path.relative_to(ROOT))] = digest
    for name in source_files:
        path = ROOT / name
        if sha(path) != provenance['source_sha256'][name]:
            raise ValueError(f'Executed-source mismatch: {name}')
        hashes[name] = sha(path)
    metadata = json.loads(metadata_path.read_text(encoding='utf-8'))
    local_metadata = json.loads((cache / 'metadata.json').read_text(encoding='utf-8'))
    metadata_difference = metadata_path_difference(local_metadata, metadata)
    hashes[str((cache / 'metadata.json').relative_to(ROOT))] = sha(cache / 'metadata.json')
    f = np.load(inputs / 'fixed_forecast_residuals.npz')
    arrays = {name: np.load(cache / f'{name}.npy', mmap_mode='r') for name in ('physics', 'physics_model', 'time_index', 'node_ids', 'target', 'target_mask', 'regime_primary', 'regime_primary_valid', 'feature_mask')}
    anchors, val_anchors = f['anchor_indices_test'], f['anchor_indices_val']
    for split, a in [('val', val_anchors), ('test', anchors)]:
        start, stop = metadata['split_bounds'][split]
        expected_anchors = np.arange(start + 35, stop - 24)
        if not np.array_equal(a, expected_anchors):
            raise ValueError(f'{split}: dataset window anchors differ')
        if not np.array_equal(f[f'anchor_time_index_{split}'], arrays['time_index'][a]):
            raise ValueError(f'{split}: anchor day/slot mismatch')
        if not np.array_equal(f[f'z_label_{split}'], arrays['regime_primary'][a]):
            raise ValueError(f'{split}: regime labels mismatch')
        for lead in range(1, 7):
            assert_target_alignment(f[f'ytrue_{split}'][:, lead - 1], arrays['target'], a, lead)
            assert_target_alignment(f[f'mask_{split}'][:, lead - 1], arrays['target_mask'], a, lead)
        for seed in SEEDS:
            actual = np.maximum(f[f'yhat_{split}_seed{seed}'] - f[f'ytrue_{split}'], 0) * f[f'mask_{split}']
            if not np.array_equal(actual, f[f'shortfall_{split}_seed{seed}'], equal_nan=True):
                raise ValueError(f'{split}/{seed}: frozen shortfall identity failed')
    if not np.array_equal(f['node_ids'], arrays['node_ids']):
        raise ValueError('node identity mismatch')
    timeline = arrays['time_index'][:, 0].astype(int) * 144 + arrays['time_index'][:, 1]
    if not np.all(np.diff(timeline) == 1):
        raise ValueError('day/slot timeline is not contiguous')
    n_nodes = len(arrays['node_ids'])
    block_by_time = native_blocks(anchors)
    blocks = np.repeat(block_by_time, n_nodes)
    valid = ((f['mask_test'][:, 5] > 0.5) & arrays['regime_primary_valid'][anchors].astype(bool)).ravel()
    val_valid = (f['mask_val'][:, 5] > 0.5).ravel()
    wmean, wstd = (float(metadata['feature_stats']['Wspd'][key]) for key in ('mean', 'std'))
    w = (arrays['physics_model'][anchors, :, 0] * wstd + wmean).ravel()
    wv = (arrays['physics_model'][val_anchors, :, 0] * wstd + wmean).ravel()
    wind_edges = np.linspace(0., 25., 11)
    wind_edges[0], wind_edges[-1] = -np.inf, np.inf
    wind_bin = np.searchsorted(wind_edges, w, side='right') - 1
    boundary = abs(w - 10.5) <= 1.0
    regime = arrays['regime_primary'][anchors]
    transition = transition_mask(regime).ravel()
    known_regime = arrays['regime_primary_valid'][anchors].astype(bool)
    # Sensitivity: original transition labels may involve invalid neighboring states.
    adjacent_valid = known_regime.copy()
    for off in range(1, 4):
        adjacent_valid[off:] &= known_regime[:-off]
        adjacent_valid[:-off] &= known_regime[off:]
    target, target_mask = arrays['target'], arrays['target_mask']
    past = (target[anchors] - target[anchors - 6]).ravel()
    future = (target[anchors + 6] - target[anchors]).ravel()
    past_known = ((target_mask[anchors] > 0.5) & (target_mask[anchors - 6] > 0.5)).ravel()
    future_known = ((target_mask[anchors] > 0.5) & (target_mask[anchors + 6] > 0.5)).ravel()
    def ramp_labels(delta, known):
        labels = np.where(delta < -150, 'down_gt150kW', np.where(delta > 150, 'up_gt150kW', 'within150kW'))
        return np.where(known, labels, 'unknown_endpoint')
    axes = {
        'wind_policy_bin': np.array([f'bin_{i:02d}' for i in wind_bin]),
        'boundary_9p5_11p5': np.where(boundary, 'boundary', 'outside'),
        'issue_regime': regime.ravel().astype(str),
        'transition_original': np.where(transition, 'transition', 'steady'),
        'transition_neighbor_validity': np.where(adjacent_valid.ravel(), 'neighbors_valid', 'neighbor_invalid'),
        'past60_power_ramp': ramp_labels(past, past_known),
        'future60_power_ramp_expost': ramp_labels(future, future_known),
        'wind_observed_at_issue': np.where(arrays['feature_mask'][anchors, :, 0].ravel() > 0.5, 'observed', 'imputed'),
    }
    axes['wind_x_transition'] = np.char.add(np.char.add(axes['wind_policy_bin'], ':'), axes['transition_original'])
    axes['wind_x_future_ramp_expost'] = np.char.add(np.char.add(axes['wind_policy_bin'], ':'), axes['future60_power_ramp_expost'])
    references = {}
    ref_manifest_path = ref_root / 'e04_v2_output_manifest.json'
    ref_manifest = json.loads(ref_manifest_path.read_text(encoding='utf-8'))
    ref_expected = {entry['path']: entry['sha256'] for entry in ref_manifest['files']}
    hashes[str(ref_manifest_path.relative_to(ROOT))] = sha(ref_manifest_path)
    for seed in SEEDS:
        path = ref_root / f'seed{seed}_full_policy_day_blocks.npz'
        if sha(path) != ref_expected[path.name]:
            raise ValueError(f'E04-v2 manifest mismatch: {path.name}')
        hashes[str(path.relative_to(ROOT))] = sha(path)
        references[seed] = dict(np.load(path))
        j04 = ROOT / f'analyses/remote/J04/e06_bundle/seed{seed}_full_policy_day_blocks.npz'
        original = dict(np.load(j04))
        if any(not np.array_equal(original[k], references[seed][k]) for k in references[seed]):
            raise ValueError('J04 arrays differ numerically from E04-v2 reference')
        hashes[str(j04.relative_to(ROOT))] = sha(j04)
    output.mkdir(parents=True, exist_ok=False)
    started = datetime.now(timezone(timedelta(hours=8))).isoformat()
    audit = {'status': 'ALIGNMENT_VERIFIED_BEFORE_SLICING', 'started_Asia_Shanghai': started,
             'scope': 'WTB Full; h=6; original mask and native 144-anchor blocks',
             'anchor_test_bounds': anchors[[0, -1]].tolist(),
             'anchor_val_bounds': val_anchors[[0, -1]].tolist(),
             'first_issue_day_slot': arrays['time_index'][anchors[0]].tolist(),
             'last_issue_day_slot': arrays['time_index'][anchors[-1]].tolist(),
             'n_valid_per_seed': int(valid.sum()), 'n_anchors': len(anchors), 'n_nodes': n_nodes,
             'all_six_target_leads_exact': True, 'shortfall_identities_exact_5seeds_2splits': True,
             'node_ids_exact': True, 'mask_and_anchor_time_exact': True,
             'j04_e04_day_arrays_numerically_identical': True,
             'source_hashes_match_J04': source_files, 'input_hashes_before': hashes.copy(),
             'metadata_localization_difference_only': metadata_difference,
             'wind_physical_recovery_max_abs_mps': float(np.max(abs(w - arrays['physics'][anchors, :, 0].ravel()))),
             'training_seeds': list(SEEDS), 'analysis_rng_seed': 20261020,
             'slice_definitions': {'ramp_threshold_kw': 150, 'ramp_interval_steps': 6,
                                   'boundary_mps': [9.5, 11.5], 'wind_edges': ['-inf',2.5,5,7.5,10,12.5,15,17.5,20,22.5,'inf'],
                                   'transition': 'original non-circular +/-3 around issue-time regime changes; includes future labels',
                                   'future_ramp': 'realized power at issue+6 minus issue; diagnostic only',
                                   'high_blocks': 'five largest pooled B day rates; outcome-selected descriptive localization'},
             'environment': {'python': platform.python_version(), 'numpy': np.__version__, 'platform': platform.platform(),
                             'cpu': os.environ.get('PROCESSOR_IDENTIFIER', platform.processor()), 'device': device},
             'argv': [sys.executable, *sys.argv], 'script_sha256': sha(Path(__file__))}
    write_json(output / 'alignment.json', audit)
    bundle = None
    if replay_posteriors:
        import torch
        from windfarm_moe.data import load_cache_bundle
        torch.set_num_threads(4)
        torch.backends.cudnn.benchmark = False
        bundle = load_cache_bundle(cache, mmap_mode='r')
        audit['environment'].update({'torch': torch.__version__, 'cuda': torch.version.cuda,
                                     'gpu': torch.cuda.get_device_name(0) if 'cuda' in device else 'not used',
                                     'cudnn_benchmark': False,
                                     'deterministic_algorithms': torch.are_deterministic_algorithms_enabled()})
    slices, daily_rows, calibration_rows = [], [], []
    closures, b_actions, shortfalls = {}, {}, {}
    high_rates = sum(references[s]['B_viol'] for s in SEEDS) / sum(references[s]['n'] for s in SEEDS)
    high_blocks = np.argsort(high_rates)[-5:][::-1]
    axes['high_B_blocks'] = np.where(np.isin(blocks, high_blocks), 'high5', 'other30')
    axes['highblock_x_wind'] = np.char.add(np.char.add(axes['high_B_blocks'], ':'), axes['wind_policy_bin'])
    axes['highblock_x_future_ramp_expost'] = np.char.add(np.char.add(axes['high_B_blocks'], ':'), axes['future60_power_ramp_expost'])
    for seed in SEEDS:
        sv = f[f'shortfall_val_seed{seed}'][:, 5].ravel()
        st = f[f'shortfall_test_seed{seed}'][:, 5].ravel()
        error = (f[f'yhat_test_seed{seed}'][:, 5] - f['ytrue_test'][:, 5]).ravel()
        b, quantiles, sizes = binned_reserve(sv, wv, w, val_valid, wind_edges)
        actions = {'B': b}
        b_actions[seed], shortfalls[seed] = b, st
        closures[str(seed)] = {'B': check_daily_closure('B', blocks, valid, st > b, (b+10*np.maximum(st-b,0))*DT, references[seed])}
        for i, (q, size) in enumerate(zip(quantiles, sizes)):
            m = val_valid & (wv >= wind_edges[i]) & (wv < wind_edges[i+1])
            mt = valid & (wind_bin == i)
            calibration_rows.append({'seed': seed, 'wind_bin': i, 'val_n': size, 'reserve_q90_kw': q,
                                     'fallback': size <= 20, 'val_violation_rate': float(np.mean(sv[m] > np.float32(q))) if size else None,
                                     'test_n': int(mt.sum()), 'test_violation_rate': float(np.mean(st[mt] > b[mt])) if mt.any() else None,
                                     'test_mean_error_kw': float(error[mt].mean()) if mt.any() else None,
                                     'test_mean_shortfall_kw': float(st[mt].mean()) if mt.any() else None})
        if replay_posteriors:
            checkpoint = inputs / f'checkpoints/seed{seed}_best_model.pt'
            checkpoint_hash = sha(checkpoint)
            seed_checkpoint_hashes = [entry['sha256'].lower() for entry in provenance['inputs']
                                      if entry['path'].endswith(f'/seed{seed}/best_model.pt')]
            if seed_checkpoint_hashes != [checkpoint_hash]:
                raise ValueError(f'checkpoint provenance mismatch seed {seed}')
            hashes[str(checkpoint.relative_to(ROOT))] = checkpoint_hash
            p = infer_posteriors(bundle, checkpoint, device, seed)
            other_actions, details = posterior_actions(sv, wv, w, p['val'], p['test'], val_valid, b, wind_edges)
            closures[str(seed)]['posterior_replay'] = details
            for policy, reserve in other_actions.items():
                try:
                    closure = check_daily_closure(policy, blocks, valid, st > reserve,
                                                  (reserve+10*np.maximum(st-reserve,0))*DT, references[seed])
                    closures[str(seed)][policy] = closure
                    actions[policy] = reserve
                except ValueError as exc:
                    closures[str(seed)][policy] = {'status': 'NOT_ACCEPTED_FOR_SLICING', 'reason': str(exc)}
            write_json(output / f'closure_seed{seed}.json', closures[str(seed)])
        for policy, reserve in actions.items():
            violation = st > reserve
            for axis, labels in axes.items():
                partition = summarize_partition(labels, valid, violation, reserve, st, error)
                if sum(row['n'] for row in partition) != valid.sum() or sum(row['violations'] for row in partition) != np.sum(violation[valid]):
                    raise ValueError(f'slice partition failed: {seed}/{policy}/{axis}')
                slices += [{'seed': seed, 'policy': policy, 'axis': axis, **row} for row in partition]
            for day in range(35):
                dm = valid & (blocks == day)
                rows = summarize_partition(axes['wind_policy_bin'], dm, violation, reserve, st, error)
                daily_rows += [{'seed': seed, 'policy': policy, 'block_1based': day+1, **row} for row in rows]
        print(f'seed={seed}: accepted policies {list(actions)}', flush=True)
    # Exact two-factor algebra across seed-specific shortfalls and B calibrations.
    matrix = np.array([[np.mean(shortfalls[s][valid] > b_actions[r][valid]) for r in SEEDS] for s in SEEDS])
    components = []
    for i, s in enumerate(SEEDS):
        for j, r in enumerate(SEEDS):
            if i == j:
                continue
            target_component = 0.5 * ((matrix[i,i]-matrix[j,i])+(matrix[i,j]-matrix[j,j]))
            reserve_component = 0.5 * ((matrix[i,i]-matrix[i,j])+(matrix[j,i]-matrix[j,j]))
            if not np.isclose(target_component + reserve_component, matrix[i,i] - matrix[j,j]):
                raise ValueError('seed difference decomposition failed')
            components.append({'seed': s, 'reference_seed': r, 'violation_rate_difference': float(matrix[i,i]-matrix[j,j]),
                               'shortfall_swap_component': float(target_component), 'reserve_swap_component': float(reserve_component)})
    block_map = []
    for day in range(35):
        ids = np.flatnonzero(block_by_time == day)
        first, last = anchors[ids[[0,-1]]]
        block_map.append({'block_1based': day+1, 'issue_anchor_first': int(first), 'issue_anchor_last': int(last),
                          'issue_day_first': int(arrays['time_index'][first,0]), 'issue_slot_first': int(arrays['time_index'][first,1]),
                          'issue_day_last': int(arrays['time_index'][last,0]), 'issue_slot_last': int(arrays['time_index'][last,1]),
                          'target_day_first': int(arrays['time_index'][first+6,0]), 'target_slot_first': int(arrays['time_index'][first+6,1]),
                          'target_day_last': int(arrays['time_index'][last+6,0]), 'target_slot_last': int(arrays['time_index'][last+6,1]),
                          'n_anchor_positions': len(ids), 'valid_n_per_seed': int(references[201]['n'][day]),
                          'pooled_B_rate': float(high_rates[day]), 'in_high5': bool(day in high_blocks)})
    after = {name: sha(ROOT / name) for name in hashes}
    if hashes != after:
        raise ValueError('Protected input changed during diagnostic')
    audit.update({'finished_Asia_Shanghai': datetime.now(timezone(timedelta(hours=8))).isoformat(),
                  'input_hashes_before': hashes, 'input_hashes_after': after, 'inputs_unchanged': True,
                  'closures': closures, 'high_B_blocks_1based': (high_blocks+1).tolist(),
                  'limitations': ['Post-hoc descriptive slices, no causal or deployment certification',
                                 'High-rate blocks are outcome-selected; no selection-adjusted inference',
                                 'Future ramp and original transition labels are ex-post oracle diagnostics',
                                 'Seed changes the frozen forecast/shortfall target as well as reserve calibration',
                                 'No posterior policy is sliced unless all original daily n/violation/cost arrays close exactly',
                                 'Seed-swap evaluation is algebraic localization, not a new policy or causal intervention',
                                 'No actual calendar date is inferred from WTB day numbers']})
    write_json(output / 'alignment.json', audit)
    write_csv(output / 'slices_by_seed.csv', slices)
    write_csv(output / 'daily_wind_slices.csv', daily_rows)
    write_csv(output / 'calibration_by_wind_seed.csv', calibration_rows)
    write_csv(output / 'block_time_map.csv', block_map)
    write_csv(output / 'seed_difference_decomposition.csv', components)
    write_json(output / 'seed_swap_matrix.json', {'shortfall_seeds_rows': SEEDS, 'reserve_seeds_columns': SEEDS,
                                               'violation_rates': matrix.tolist(), 'diagnostic_only': True})
    print(json.dumps({'output': str(output), 'inputs_unchanged': True, 'high_blocks': (high_blocks+1).tolist(),
                      'accepted_policies_by_seed': {s: [p for p in POLICIES if closures[s].get(p, {}).get('cost_exact')] for s in closures}}, indent=2), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--replay-posteriors', action='store_true')
    parser.add_argument('--device', default='cuda:0')
    args = parser.parse_args()
    run(args.output_dir.resolve(), args.replay_posteriors, args.device)
