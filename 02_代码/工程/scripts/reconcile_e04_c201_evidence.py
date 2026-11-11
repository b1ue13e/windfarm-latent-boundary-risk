"""Consume an audited A100 posterior snapshot in a new five-seed slice replay.

The original slicing code is unchanged. Only seed201 inference is supplied from
the predesignated A100 repeat1 archive; all daily exactness checks remain active.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import subprocess
import sys
from repo_paths import Path, repository_root

import numpy as np

ROOT = Path(repository_root())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verified_archive(directory, repeat):
    manifest = json.loads((directory/'manifest.json').read_text(encoding='utf-8'))
    if not manifest['inputs_unchanged']:
        raise ValueError('Audit input integrity was not verified')
    for name, digest in manifest['output_sha256'].items():
        if sha(directory/name) != digest:
            raise ValueError(f'Archived audit output hash mismatch: {name}')
    report = json.loads((directory/f'repeat{repeat}_report.json').read_text(encoding='utf-8'))
    if not all(report[key] for key in ('n_exact','violation_exact','cost_exact','accepted')):
        raise ValueError('Archived C201 replay did not pass exactness gate')
    path = directory/f'repeat{repeat}_posterior_and_bins.npz'
    if sha(path) != report['archive_sha256']:
        raise ValueError('Posterior archive binding mismatch')
    with np.load(path) as archive:
        return {key: archive[key] for key in archive.files}


def full_grid_closed(closures):
    return all(closures.get(str(seed), {}).get(policy, {}).get('n_exact') is True
               and closures[str(seed)][policy].get('violations_exact') is True
               and closures[str(seed)][policy].get('cost_exact') is True
               for seed in range(201,206) for policy in ('B','C','D','D10'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence-dir', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists():
        raise FileExistsError('Use a new reconciliation directory')
    original_alignment_path = ROOT/'analyses/e04_regime_slices_20261018/alignment.json'
    original_alignment = json.loads(original_alignment_path.read_text(encoding='utf-8'))
    slice_script = ROOT/'scripts/analyze_e04_regime_slices.py'
    if sha(slice_script) != original_alignment['script_sha256']:
        raise ValueError('Original slice algorithm changed')
    snapshots = {f'{host}_{repeat}': verified_archive(args.evidence_dir/host, repeat)
                 for host in ('a100','rtx5060') for repeat in (1,2)}
    primary = snapshots['a100_1']  # Fixed identity, never chosen from numerical fit.
    baseline = primary
    comparisons = {}
    for name, data in snapshots.items():
        comparisons[name] = {}
        for field in ('posterior_val','posterior_test','val_bin_ids','test_bin_ids','reserve_quantiles','reserve_test'):
            diff = data[field].astype(float)-baseline[field].astype(float)
            comparisons[name][field] = {'changed_values': int(np.count_nonzero(diff)), 'max_absolute_difference':float(abs(diff).max())}
        edge_mask = np.isfinite(data['posterior_edges']) & np.isfinite(baseline['posterior_edges'])
        comparisons[name]['finite_edges_max_abs_difference'] = float(abs(data['posterior_edges'][edge_mask]-baseline['posterior_edges'][edge_mask]).max())
    spec = importlib.util.spec_from_file_location('unchanged_e04_slices', slice_script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    original_infer = module.infer_posteriors
    plan_path = args.evidence_dir/'a100/plan.json'
    plan = json.loads(plan_path.read_text(encoding='utf-8'))
    expected_checkpoint = next(v for k,v in plan['inputs_before'].items() if '/seed201/best_model.pt' in k)
    def supplied_infer(bundle, checkpoint_path, device, seed):
        if seed != 201:
            return original_infer(bundle, checkpoint_path, device, seed)
        if module.sha(checkpoint_path) != expected_checkpoint:
            raise ValueError('Seed201 checkpoint differs from audited posterior source')
        for split in ('val','test'):
            start, stop = bundle.metadata['split_bounds'][split]
            if not np.array_equal(primary[f'anchor_indices_{split}'], np.arange(start+35,stop-24)):
                raise ValueError('Archived posterior anchor alignment mismatch')
        if not np.array_equal(primary['node_ids'], bundle.node_ids):
            raise ValueError('Archived posterior node alignment mismatch')
        print('seed=201: using hash-verified A100 repeat1 posteriors; exact daily gate remains active', flush=True)
        return {'val':primary['posterior_val'].copy(), 'test':primary['posterior_test'].copy()}
    module.infer_posteriors = supplied_infer
    args.output_dir.mkdir(parents=True, exist_ok=False)
    protected = {str(original_alignment_path):sha(original_alignment_path), str(slice_script):sha(slice_script),
                 **{str(p):sha(p) for host in ('a100','rtx5060') for p in (args.evidence_dir/host).glob('*') if p.is_file()}}
    binding = {'status':'AUDITED_POSTERIOR_INPUT_NOT_ORIGINAL_LOG_REPLACEMENT',
               'primary_snapshot':'a100/repeat1_posterior_and_bins.npz',
               'primary_snapshot_sha256':sha(args.evidence_dir/'a100/repeat1_posterior_and_bins.npz'),
               'primary_audit_runtime':plan['runtime'], 'original_slice_script_sha256':sha(slice_script),
               'wrapper_sha256':sha(Path(__file__)), 'command_argv':[sys.executable,*sys.argv],
               'comparisons_against_a100_repeat1':comparisons,
               'inputs_before':protected,
               'limitations':['Historical failed-run posteriors were not archived; its exact numerical cause remains unverified.',
                              'Daily aggregate closure does not prove bitwise identity to absent historical posterior logs.',
                              'Seed201 uses an audited A100 archive; other seeds replay on local RTX5060.',
                              'No original result, threshold or matching tolerance is changed.']}
    (args.output_dir/'binding.json').write_text(json.dumps(binding,indent=2)+'\n',encoding='utf-8')
    module.run((args.output_dir/'complete_slices').resolve(), True, 'cuda:0')
    new_alignment = json.loads((args.output_dir/'complete_slices/alignment.json').read_text(encoding='utf-8'))
    if not full_grid_closed(new_alignment['closures']):
        raise ValueError('Full five-seed grid did not close; incomplete grid is not certified')
    result = subprocess.run([sys.executable,str(ROOT/'scripts/summarize_e04_regime_slices.py'),
                             '--input-dir',str(args.output_dir/'complete_slices'),
                             '--output-dir',str(args.output_dir/'complete_summary')],check=True)
    if any(sha(path)!=digest for path,digest in protected.items()):
        raise ValueError('An existing evidence input changed during reconciliation')
    grid = []
    for seed in range(201,206):
        for policy in ('B','C','D','D10'):
            grid.append({'seed':seed,'policy':policy,'blocks':35,'n_exact':True,'violations_exact':True,'cost_exact':True,
                         'posterior_source':'A100 repeat1 archived replay' if seed==201 and policy!='B' else 'local reconstruction'})
    with (args.output_dir/'exactness_grid.csv').open('w',newline='',encoding='utf-8') as handle:
        writer=csv.DictWriter(handle,fieldnames=list(grid[0]))
        writer.writeheader();writer.writerows(grid)
    final={'status':'ALL_20_SEED_POLICY_CELLS_EXACT','five_seed_C_evidence_closed':True,
           'protected_inputs_unchanged':True,'n_seed_policy_cells':20,'blocks_per_cell':35,
           'independent_scientific_review_status':'NOT UPGRADED',
           'historical_4p256908_cost_difference_cause':'UNRESOLVED; missing failed-run posterior archive'}
    (args.output_dir/'result.json').write_text(json.dumps(final,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(final,indent=2),flush=True)


if __name__=='__main__':
    main()
