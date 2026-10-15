"""Preserve exact-repeat failures; compare fixed default/deterministic executions."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import sys


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--mode', choices=['default', 'deterministic'], required=True)
    parser.add_argument('--frozen-input-manifest-sha256', required=True)
    args = parser.parse_args()
    if not os.environ.get('PBS_JOBID'):
        raise RuntimeError('Diagnosis only in allocated PBS GPU resources')
    if args.mode == 'deterministic':
        if 'torch' in sys.modules:
            raise RuntimeError('Set CUDA configuration before importing torch')
        os.environ['CUBLAS_WORKSPACE_CONFIG'] = ':4096:8'
    root = args.workspace.resolve()
    frozen = root / 'metis_input_manifest.json'
    if sha(frozen) != args.frozen_input_manifest_sha256:
        raise ValueError('Frozen manifest identity differs')
    for row in json.loads(frozen.read_text()):
        if sha(root / row['relative_path']) != row['sha256']:
            raise ValueError('Frozen input/source changed')
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    sys.path[:0] = [str(root / 'scripts'), str(root)]
    import numpy as np
    import torch
    from raw_replay import verify_records
    from replay_provenance import provenance, finalize
    from windfarm_moe.data import load_cache_bundle
    from repair_exp01_pitch_withheld_v3 import infer_gates
    if not torch.cuda.is_available():
        raise RuntimeError('Allocated CUDA GPU required')
    if args.mode == 'deterministic':
        torch.use_deterministic_algorithms(True)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
        torch.backends.cudnn.allow_tf32 = False
        torch.backends.cuda.matmul.allow_tf32 = False
    source = root / 'artifacts/raw_replay_20261015_v2/models/aligned_force/seed201'
    cache_map_path = root / 'artifacts/raw_replay_external_models_20261015/cache_map.json'
    cache_path = Path(json.loads(cache_map_path.read_text())['kelmarsh'])
    if not cache_path.is_absolute():
        cache_path = root / cache_path
    verify_records(json.loads((source / 'output_manifest.json').read_text()))
    verify_records(json.loads((cache_path.parent / 'output_manifest.json').read_text()))
    saved = root / 'artifacts/raw_replay_external_models_20261015/matched_transfer/kelmarsh_seed201_val_gate_pitchmasked.npy'
    provenance(output, [source / 'best_model.pt', source / 'output_manifest.json', cache_map_path,
        cache_path.parent / 'output_manifest.json', saved], {'mode': args.mode, 'pbs_job_id': os.environ['PBS_JOBID']})
    flags = dict(deterministic_algorithms=torch.are_deterministic_algorithms_enabled(),
        cudnn_deterministic=torch.backends.cudnn.deterministic, cudnn_benchmark=torch.backends.cudnn.benchmark,
        cudnn_tf32=torch.backends.cudnn.allow_tf32, matmul_tf32=torch.backends.cuda.matmul.allow_tf32,
        cublas_workspace_config=os.environ.get('CUBLAS_WORKSPACE_CONFIG'), torch_threads=torch.get_num_threads())
    (output / 'runtime.json').write_text(json.dumps({'flags': flags, 'host': platform.node(),
        'python': sys.version, 'torch': torch.__version__, 'cuda': torch.version.cuda,
        'gpu': torch.cuda.get_device_name(0), 'audit_source_sha256': sha(__file__)}, indent=2))
    bundle = load_cache_bundle(cache_path, mmap_mode='r')
    old = np.load(saved)
    replays = []
    for number in (1, 2):
        gate, anchors, _, _ = infer_gates(source, bundle, 'val', torch.device('cuda'))
        np.save(output / f'replay{number}.npy', gate)
        np.save(output / f'anchors{number}.npy', anchors)
        replays.append(gate)
    def compare(a, b):
        if a.shape != b.shape:
            return {'exact': False, 'shapes': [list(a.shape), list(b.shape)]}
        if not np.isfinite(a).all() or not np.isfinite(b).all():
            raise ValueError('Nonfinite replay/saved gates')
        difference = np.abs(a.astype(np.float64) - b.astype(np.float64))
        return {'exact': bool(np.array_equal(a, b)), 'shape': list(a.shape),
            'dtypes': [str(a.dtype), str(b.dtype)], 'changed_values': int(np.count_nonzero(a != b)),
            'max_absolute_difference': float(difference.max()),
            'changed_argmax_cells': int(np.count_nonzero(a.argmax(-1) != b.argmax(-1)))}
    report = {'pbs_job_id': os.environ['PBS_JOBID'], 'mode': args.mode, 'flags': flags,
        'replay1_vs_saved': compare(replays[0], old), 'replay2_vs_saved': compare(replays[1], old),
        'replay1_vs_replay2': compare(*replays), 'source_sha256': sha(__file__),
        'scientific_completion': False, 'interpretation': 'numeric execution observation only; no relaxed tolerance, original runtime flags not retroactively inferred'}
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    finalize(output)
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
