"""Two predeclared static controls; never alter the completed main campaign."""
from __future__ import annotations
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import os
from repo_paths import Path, repository_root
import platform
import sys
import time

ROOT = Path(repository_root())
sys.path.insert(0, str(ROOT))
import numpy as np
import scipy
from windfarm_moe.static_convex_reserve import fit_static_convex, predict_static, _highs_version
from windfarm_moe.static_convex_bundle import fit_bundle
from windfarm_moe.autonomous_campaign_inference import infer_campaign


def sha(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda: f.read(2**20), b''):
            h.update(b)
    return h.hexdigest()


def save(p, value):
    Path(p).write_text(json.dumps(value, indent=2, allow_nan=False,
        default=lambda x: x.tolist() if isinstance(x, np.ndarray) else str(x))+'\n')


def verified_cache(p):
    info = json.loads((p/'manifest.json').read_text())
    for name, item in info['files'].items():
        f = p/name
        if f.stat().st_size != item['bytes'] or sha(f) != item['sha256']:
            raise ValueError('Cache identity mismatch: '+str(f))
    return info


def training_rows(a, y, mask):
    use = (a >= 27648) & (a < 28937)
    if not np.array_equal(a[use], np.arange(27648, 28937)):
        raise ValueError('Historical inner window differs')
    if y.shape != mask.shape or y.shape != (len(a), 134):
        raise ValueError('Common population differs')
    return use


def daily_ledger(r, y, mask, anchors):
    days = np.unique(anchors//144)
    if len(days) != 35 or int(mask.sum()) != 672939:
        raise ValueError('Original scoring population differs')
    result = []
    for day in days:
        ix = anchors//144 == day
        valid = mask[ix]
        action, target = r[ix][valid], y[ix][valid]
        u = np.maximum(target-action, 0)/6
        reserve = action/6
        result.append([np.sum(reserve+10*u), np.sum(reserve), np.sum(u),
                       np.sum(target > action)])
    return np.asarray(result)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--main', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--declaration', type=Path, required=True)
    parser.add_argument('--backend', choices=['full_lp','bundle'],default='full_lp')
    args = parser.parse_args()
    if not os.environ.get('PBS_JOBID'):
        raise RuntimeError('A separate bounded PBS allocation is required')
    start = time.monotonic()
    state = json.loads((args.main/'campaign_state.json').read_text())
    declaration = json.loads(args.declaration.read_text())
    opened = json.loads((args.main/'evaluation_open.json').read_text())
    if (state['attempted'] > 1998 or state['allocated_cpu_hours']*3600+1200+480 > 86400
        or datetime.fromisoformat(declaration['declared_utc']) >= datetime.fromisoformat(opened['time_utc'])
        or not state['status'].startswith('COMPLETED')):
        raise ValueError('Shared budget, precedence, or main completion gate failed')
    out = args.output
    out.mkdir(parents=True, exist_ok=False)
    save(out/'run_environment.json', dict(pbs_job_id=os.environ['PBS_JOBID'],
        started_utc=datetime.now(timezone.utc).isoformat(), host=platform.node(),
        python=sys.version, max_wall_seconds=480, max_paired_recipes=2,
        numpy_version=np.__version__,scipy_version=scipy.__version__,highs_version=_highs_version(),
        platform=platform.platform(),allocated_cpus=1,blas_threads=1,
        scipy_solver_limit_seconds=10 if args.backend=='full_lp' else 12,
        numerical_backend=args.backend, declaration_sha256=sha(args.declaration),
        main_freeze_sha256=sha(args.main/'FINAL_FREEZE.json'),
        source_sha256={p:sha(ROOT/p) for p in ['scripts/run_static_convex_control.py',
            'windfarm_moe/static_convex_reserve.py','windfarm_moe/static_convex_bundle.py',
            'windfarm_moe/autonomous_campaign_inference.py']}))
    hist = args.main/'expert_cache/historical_extended'
    verified_cache(hist)
    a, y, m = [np.load(hist/(s+'.npy')) for s in ['anchors','shortfall','mask']]
    ix = training_rows(a, y, m)
    fits = {}
    # Both controls and both arms are fitted before opening final scoring arrays.
    for seed in range(201, 206):
        for arm in ['P', 'Z']:
            x = np.load(hist/f'{arm}_seed{seed}.npy')[ix][m[ix]]
            target = y[ix][m[ix]]
            cap = float(np.maximum(target-x[:,0], 0).mean())
            for variant, limit in [('COST', None), ('CAP', cap)]:
                if time.monotonic()-start > 330:
                    raise TimeoutError('Preserve all fits; leave time for inference')
                fitter = fit_static_convex if args.backend=='full_lp' else fit_bundle
                result = fitter(x, target, time_limit=10 if args.backend=='full_lp' else 12,
                                uncovered_cap=limit)
                name = f'{variant}_{arm}_seed{seed}'
                save(out/(name+'.json'), dict(**asdict(result),
                    historical_binding=dict(cache_manifest_sha256=sha(hist/'manifest.json'),
                        window=[27648,28937],valid_cells=len(target),n_experts=x.shape[1],
                        full_population_no_subsampling=True)))
                fits[name] = result
    save(out/'CONTROL_FREEZE.json', dict(time_utc=datetime.now(timezone.utc).isoformat(),
        fits={k:sha(out/(k+'.json')) for k in fits}, rule='Score all feasible incumbents; no selection on evaluation; nonoptimal status retained'))
    final = args.main/'expert_cache/evaluate'
    verified_cache(final)
    a, y, m = [np.load(final/(s+'.npy')) for s in ['anchors','shortfall','mask']]
    base = np.load(args.main/'final_daily_ledger.npz')
    programs = json.loads((args.main/'final_programs.json').read_text())
    names = programs['policy_names']+['LP_COST_P','LP_COST_Z','LP_CAP_P','LP_CAP_Z']
    ledger = np.concatenate([base['ledger'], np.full((5,4,35,4), np.nan)], axis=1)
    available = list(programs['available'])+[True]*4
    for si, seed in enumerate(range(201,206)):
        for j, (variant, arm) in enumerate([('COST','P'),('COST','Z'),('CAP','P'),('CAP','Z')]):
            result = fits[f'{variant}_{arm}_seed{seed}']
            if result.weights is None:
                available[len(programs['policy_names'])+j] = False
                continue
            r = predict_static(np.load(final/f'{arm}_seed{seed}.npy'), result.weights)
            np.save(out/f'LP_{variant}_{arm}_seed{seed}.npy', r, allow_pickle=False)
            ledger[si,len(programs['policy_names'])+j] = daily_ledger(r,y,m,a)
    comparisons = [*map(tuple,programs['comparisons']),
        ('LP_COST_Z','LP_COST_P'),('LP_CAP_Z','LP_CAP_P'),
        ('EW_P','LP_COST_P'),('DUAL_P','LP_COST_P'),
        ('PROTECTED_P','LP_CAP_P'),('PROTECTED_Z','LP_CAP_Z')]
    np.savez_compressed(out/'expanded_daily_ledger.npz', ledger=ledger, counts=base['counts'], day_ids=base['day_ids'])
    for span in [3,1,7]:
        if time.monotonic()-start > 430:
            raise TimeoutError('Inference left incomplete; do not claim full closure')
        value = infer_campaign(ledger,base['counts'],names,comparisons,span=span,
            available=available,aliases=programs['aliases'])
        save(out/f'expanded_inference_span{span}.json',value)
    save(out/'completion.json',dict(status='COMPLETED_EXPLORATORY_CONTROL',
        elapsed_seconds=time.monotonic()-start,available=available,policy_names=names,
        all_fits_optimal=all(r.optimal for r in fits.values()),
        joint_selection_adjusted=False,original_main_outputs_unchanged=True))


if __name__ == '__main__':
    main()
