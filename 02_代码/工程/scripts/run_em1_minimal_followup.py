"""Two bounded diagnostics on the immutable matched-endpoint campaign.

This module appends to the complete parent family, never screens fixed fits,
and never fits an upstream or release model. Original results remain read-only.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import numbers
import os
from repo_paths import Path, repository_root
import platform
import shutil
import sys
import time
import traceback
from typing import Any, Mapping

ROOT = Path(repository_root())
sys.path.insert(0, str(ROOT))
import numpy as np
from threadpoolctl import threadpool_limits
from windfarm_moe.stable_contrast_inference import (
    CSTAR, SEED_IDS, THRESHOLDS, infer_stable_campaign,
)

DIRECT_PAIRS = (('EM1_008_Z', 'EM1_003_P'), ('EM1_008_Z', 'EM1_004_P'))
CONTROL = 'NV_MAJOR_Z'
PARENT_SIZE = dict(policies=1400, pairs=7257, aliases=152, coordinates=87970)
DIRECT_SIZE = dict(policies=1400, pairs=7259, aliases=152, coordinates=87990)
AGGREGATE_SIZE = dict(policies=1401, pairs=7260, aliases=152, coordinates=88011)


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def array_sha(value: np.ndarray, dtype: str | None = '<f8') -> str:
    return hashlib.sha256(np.ascontiguousarray(value, dtype=dtype).tobytes()).hexdigest()


def read(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding='utf-8'))


def save_new(path: Path, value: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False,
                  default=lambda x: x.tolist() if isinstance(x, np.ndarray) else str(x))
        stream.write('\n')


def bind(path: Path) -> dict:
    return dict(sha256=sha(path), bytes=Path(path).stat().st_size)


def environment() -> dict:
    import joblib, scipy, sklearn
    return dict(host=platform.node(), python=sys.version, numpy=np.__version__,
                scipy=scipy.__version__, sklearn=sklearn.__version__, joblib=joblib.__version__,
                job_id=os.environ.get('PBS_JOBID'), release=os.environ.get('CAMPAIGN_RELEASE'),
                utc=datetime.now(timezone.utc).isoformat(), threads=1,
                command=sys.argv, device='CPU')


def deadline_check(deadline: float) -> None:
    if time.monotonic() >= deadline:
        raise TimeoutError('Frozen stage wall-time allocation exhausted')


def config_check(cfg: Mapping[str, Any]) -> None:
    expected = dict(direct=600, replay=180, aggregate=600, audit=300, reserve=600)
    if (cfg.get('stage_limits') != expected or cfg.get('max_cpu_seconds') != 3000
            or cfg.get('max_new_candidates') != 1
            or cfg.get('seeds') != list(SEED_IDS) or cfg.get('spans') != [1, 3, 7]
            or cfg.get('n_boot') != 20000 or cfg.get('resampling_seed') != 20261022
            or cfg.get('thresholds') != THRESHOLDS or cfg.get('cstar_report_only') != CSTAR
            or cfg.get('rho') != 10 or cfg.get('dt_hours') != 1 / 6
            or cfg.get('gate') != 'EM1_008_Z' or cfg.get('controls') != ['EM1_003_P', 'EM1_004_P']
            or cfg.get('new_control') != CONTROL or cfg.get('expected_direct') != DIRECT_SIZE
            or cfg.get('expected_aggregate') != AGGREGATE_SIZE):
        raise ValueError('Frozen follow-up specification changed')
    if 600 + 5 * 180 + 600 + 300 + 600 != cfg['max_cpu_seconds']:
        raise ValueError('Stage CPU reservations do not total 3000 seconds')


def verify_sources(cfg: Mapping[str, Any]) -> None:
    if not cfg.get('source_hashes'):
        raise ValueError('Unsealed source release')
    for rel, digest in cfg['source_hashes'].items():
        p = ROOT / rel
        if not p.resolve().is_relative_to(ROOT.resolve()) or sha(p) != digest:
            raise ValueError('Source release mismatch: ' + rel)


def _pair_names(pair: Any, names: list[str]) -> tuple[str, str]:
    if not isinstance(pair, (list, tuple)) or len(pair) != 2:
        raise ValueError('Pair must contain two frozen references')
    result = []
    for item in pair:
        if isinstance(item, str) and item in names:
            result.append(item)
        elif isinstance(item, numbers.Integral) and not isinstance(item, (bool, np.bool_)) and 0 <= item < len(names):
            result.append(names[int(item)])
        else:
            raise ValueError('Unknown frozen policy reference')
    return result[0], result[1]


def family_size(names, pairs, aliases) -> dict:
    return dict(policies=len(names), pairs=len(pairs), aliases=len(aliases),
                coordinates=11 * len(names) + 10 * len(pairs))


def extend_family(parent_inf: Mapping[str, Any], additions=DIRECT_PAIRS, *,
                  new_role: str | None = None, expected_parent=PARENT_SIZE,
                  expected=DIRECT_SIZE) -> tuple[list, list, list, list]:
    """Preserve every parent role, pair, alias and availability entry in order."""
    fd = parent_inf['family_definition']
    names = list(parent_inf['policy_names'])
    available = list(parent_inf['available'])
    if not names or names[0] != 'REF' or len(set(names)) != len(names):
        raise ValueError('Incomplete/duplicate frozen names')
    if len(available) != len(names) or any(type(x) is not bool for x in available):
        raise ValueError('Frozen availability must be complete booleans')
    if fd['policy_names'] != names:
        raise ValueError('Parent family names disagree')
    pairs = [_pair_names(p, names) for p in fd['comparisons']]
    aliases = [_pair_names(p, names) for p in fd['frozen_aliases']]
    if family_size(names, pairs, aliases) != expected_parent:
        raise ValueError('Unexpected parent family dimensions')
    if new_role is not None:
        if new_role in names:
            raise ValueError('New role already exists')
        names.append(new_role)
        available.append(True)
    pairs += [_pair_names(p, names) for p in additions]
    if len(set(pairs)) != len(pairs) or len(set(aliases)) != len(aliases):
        raise ValueError('Duplicate frozen comparison or alias')
    if family_size(names, pairs, aliases) != expected:
        raise ValueError('Expanded family dimensions changed')
    return names, available, pairs, aliases


def verify_parent(cfg: Mapping[str, Any]):
    from windfarm_moe.release_bank import verify_parent_campaign_freeze
    parent, freeze, pcfg = verify_parent_campaign_freeze(
        cfg['parent_results'], cfg['parent_freeze_sha256'], label='EM parent')
    if pcfg != cfg['parent_protocol']:
        raise ValueError('Frozen parent protocol differs')
    for name, field in [('all_daily_ledger.npz', 'parent_ledger_sha256'),
                        ('all_policy_names.json', 'parent_names_sha256'),
                        ('inference_span3.json', 'parent_span3_sha256')]:
        if sha(parent / name) != cfg[field]:
            raise ValueError('Parent input changed: ' + name)
    inf, info = read(parent / 'inference_span3.json'), read(parent / 'all_policy_names.json')
    names, avail = inf['policy_names'], inf['available']
    if info['names'] != names or info['available'] != avail:
        raise ValueError('Names/availability bridge differs')
    for field, infkey in [('comparisons', 'comparisons'), ('aliases', 'frozen_aliases')]:
        if ([_pair_names(p, names) for p in info[field]] !=
                [_pair_names(p, names) for p in inf['family_definition'][infkey]]):
            raise ValueError('Parent family file differs')
    with np.load(parent / 'all_daily_ledger.npz', allow_pickle=False) as z:
        ledger, counts, days = z['ledger'].copy(), z['counts'].copy(), z['day_ids'].copy()
    if ledger.shape != (5, 1400, 35, 4) or counts.shape != (35,) or days.shape != (35,):
        raise ValueError('Frozen parent ledger shape changed')
    if not np.array_equal(days, np.arange(210, 245)) or int(counts.sum()) != 672939:
        raise ValueError('Frozen evaluation population changed')
    return parent, freeze, inf, ledger, counts, days


def run_inference(cfg, folder, ledger, counts, names, available, pairs, aliases, deadline):
    for span in cfg['spans']:
        deadline_check(deadline)
        result = infer_stable_campaign(ledger, counts, names, pairs, span=span,
            n_boot=cfg['n_boot'], seed=cfg['resampling_seed'], available=available, aliases=aliases)
        if result['family_size'] != 11 * len(names) + 10 * len(pairs) or result['thresholds'] != cfg['thresholds']:
            raise ValueError('Original inference specification changed')
        save_new(folder / f'inference_span{span}.json', result)
        print(json.dumps(dict(stage=str(folder.name), span=span, family_size=result['family_size'],
                              critical_value=result['critical_value'])), flush=True)


def finish_stage(folder: Path, cfg, details):
    files = ['all_daily_ledger.npz', 'all_policy_names.json'] + [f'inference_span{s}.json' for s in cfg['spans']]
    save_new(folder / 'completion.json', dict(status='COMPLETED', environment=environment(),
        source_hashes=cfg['source_hashes'], files={n: bind(folder / n) for n in files},
        new_fits=0, new_measurements=0, thresholds_changed=False, selection_filters_evaluation=False,
        independent_confirmation=False, post_selection_exploratory=True, **details))


def direct(cfg, out: Path, deadline):
    parent, _, inf, ledger, counts, _ = verify_parent(cfg)
    names, available, pairs, aliases = extend_family(inf)
    folder = out / 'step1'; folder.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(parent / 'all_daily_ledger.npz', folder / 'all_daily_ledger.npz')
    if sha(folder / 'all_daily_ledger.npz') != cfg['parent_ledger_sha256']:
        raise ValueError('Parent ledger byte copy differs')
    save_new(folder / 'all_policy_names.json', dict(names=names, available=available,
        comparisons=pairs, aliases=aliases, nominal_family_size=DIRECT_SIZE['coordinates']))
    run_inference(cfg, folder, ledger, counts, names, available, pairs, aliases, deadline)
    finish_stage(folder, cfg, dict(family_size=DIRECT_SIZE, parent_ledger_sha256=cfg['parent_ledger_sha256'],
                                  parent_prefix_exact=True, comparisons_appended=list(DIRECT_PAIRS)))


def action_view(bank):
    """Only arrived arrays enter either action constructor."""
    return {k: bank[k] for k in ('anchors', 'safe', 'cost', 'current_features', 'feedback_features')}


def _model_identity(obj, seed, snap):
    from windfarm_moe.matched_release_design import SNAPSHOTS
    cut, enabled = SNAPSHOTS['outer'][snap]
    if (obj.get('vintage'), obj.get('arm'), obj.get('seed'), obj.get('recipe_id'),
        obj.get('snapshot'), obj.get('cut_anchor'), obj.get('enabled_anchor'), obj.get('episode_start')) != (
            'outer', 'Z', seed, 8, snap, cut, enabled, enabled):
        raise ValueError('Frozen EM008 model timing/identity differs')
    if obj.get('kind') != 'GATE':
        raise ValueError('EM008 must remain the frozen GATE recipe')


def replay(cfg, out: Path, seed: int, deadline):
    from scripts.run_matched_release import read_phase, check_bank, bankpath
    from scripts.run_prospective_release import verify_prefix, _window_cell_metrics
    from scripts.run_mixture_closed_loop import score_actions, PHASES
    from windfarm_moe.matched_endpoint_bank import build_matched_bank
    from windfarm_moe.matched_release_design import scheduled_actions, VALIDATION_WINDOWS
    from windfarm_moe.release_bank import load_release_bank
    from windfarm_moe.release_gate import load_release_gate_model
    from windfarm_moe.no_veto_release import no_veto_actions
    from scripts.audit_no_veto_replay import independent_no_veto, independent_daily

    if seed not in SEED_IDS or isinstance(seed, bool):
        raise ValueError('Exactly the five registered fixed fits are required')
    folder = out / 'replay' / f'seed{seed}'
    if folder.exists():
        raise FileExistsError('Refusing to overwrite replay output')
    accepted = ROOT / 'experiments/em1_minimal_followup_20261025/KERNEL_ACCEPTED.json'
    if not accepted.exists():
        raise ValueError('Independent kernel acceptance signal absent')
    if read(accepted)['source_sha256'] != sha(ROOT / 'windfarm_moe/no_veto_release.py'):
        raise ValueError('Independently accepted kernel source changed')
    parent, freeze, _, _, _, _ = verify_parent(cfg)
    shard = (seed - 201) * 3 + 2
    frozen_history = freeze['histories'][shard]
    hp = parent / frozen_history['path']
    if sha(hp) != frozen_history['sha256']:
        raise ValueError('Frozen history receipt changed')
    history_receipt = read(hp)
    if (history_receipt['seed'], history_receipt['arm'], history_receipt['status']) != (seed, 'Z', 'COMPLETED'):
        raise ValueError('Frozen historical Z instance differs')
    version = frozen_history['versions']['outer']
    if version != history_receipt['versions']['outer']:
        raise ValueError('Frozen outer history version differs')
    bp = bankpath(parent, 'outer', 'Z', seed)
    hist = load_release_bank(bp, expected_sha256=version['bank_manifest']['npz_sha256'],
        expected_metadata_sha256=version['bank_manifest']['metadata_sha256'])
    model_rows = [m for m in version['models'] if m['recipe_id'] == 8]
    if len(model_rows) != 3 or {m['snapshot'] for m in model_rows} != {'C', 'E', 'D'}:
        raise ValueError('Incomplete C/E/D EM008 model set')
    models, receipts, bindings = {}, {}, {}
    for row in model_rows:
        mp, rp = parent / row['path'], parent / row['receipt_path']
        if sha(mp) != row['sha256'] or sha(rp) != row['receipt_sha256']:
            raise ValueError('Frozen model/receipt SHA changed')
        snap = row['snapshot']; model = load_release_gate_model(mp); receipt = read(rp)
        _model_identity(model, seed, snap); _model_identity(receipt, seed, snap)
        models[snap] = model
        receipts[snap] = receipt
        bindings[snap] = dict(model=bind(mp), receipt=bind(rp), path=row['path'],
                              receipt_path=row['receipt_path'], leaf_alphas=receipt.get('leaf_alphas'))
    deadline_check(deadline)
    bank = build_matched_bank(cfg['parent_protocol'], seed, 'Z', 'outer', True, root=ROOT)
    check_bank(bank, 'outer', True)
    if verify_prefix(hist, bank) != 1289:
        raise ValueError('Historical prefix is not the frozen 1289 issues')
    erp = parent / 'shards/evaluate' / f'{shard:02d}.json'
    er = read(erp)
    if er['status'] != 'COMPLETED' or er['freeze_sha256'] != cfg['parent_freeze_sha256'] or er['qualification_filter']:
        raise ValueError('Frozen evaluation binding invalid')
    eb = er['versions']['outer']; meta_path = parent / eb['metadata_path']
    if sha(meta_path) != eb['metadata_sha256'] or read(meta_path) != bank['metadata']:
        raise ValueError('Rebuilt full bank metadata differs from frozen parent')
    endpoint_hashes = {k: array_sha(bank[k], '<i8' if k == 'anchors' else None if k == 'mask' else '<f8')
        for k in ('anchors', 'shortfall', 'mask', 'reference', 'safe', 'cost', 'current_features', 'feedback_features')}
    view = action_view(bank)
    original, original_diag = scheduled_actions(view, {(k, 8): m for k, m in models.items()}, 'outer', 8)
    actions, kernel_receipt = no_veto_actions(view, models)
    independent, independent_choices = independent_no_veto(view, receipts)
    if actions.dtype != independent.dtype or actions.tobytes() != independent.tobytes():
        raise ValueError('Independent receipt-based action reconstruction differs')
    folder.mkdir(parents=True, exist_ok=False)
    phases = {}
    for phase in ('outer', 'evaluate'):
        deadline_check(deadline)
        binding = version['phases'][phase] if phase == 'outer' else eb['phase']
        oldrec, oldz = read_phase(parent, 'outer', phase, seed, 'Z', binding)
        lo, hi, _ = PHASES[phase]; sel = (bank['anchors'] >= lo) & (bank['anchors'] < hi)
        y, mask, anchors = bank['shortfall'][sel], bank['mask'][sel], bank['anchors'][sel]
        for rid, candidate in [('0', bank['safe'][sel]), ('8', original[sel])]:
            if array_sha(candidate) != oldrec['policies'][rid]['action_sha256']:
                raise ValueError('Frozen action replay SHA differs: ' + phase + '/' + rid)
        # COST recipe is a direct copy in the original endpoint design.
        if array_sha(bank['cost'][sel]) != oldrec['policies']['1']['action_sha256']:
            raise ValueError('Frozen COST endpoint action SHA differs')
        if array_sha(y) != oldrec['target_sha256'] or array_sha(mask, None) != oldrec['mask_sha256']:
            raise ValueError('Frozen target/mask SHA differs')
        daily, counts, days = score_actions(actions[sel], y, mask, anchors)
        independent_ledger, independent_counts, independent_days = independent_daily(actions[sel], y, mask, anchors)
        if (not np.array_equal(counts, independent_counts) or not np.array_equal(days, independent_days)
                or not np.allclose(daily, independent_ledger, atol=1e-8, rtol=0)):
            raise ValueError('Independent daily loss reconstruction differs')
        original_daily, on, od = score_actions(original[sel], y, mask, anchors)
        reference, rn, rd = score_actions(bank['reference'][sel], y, mask, anchors)
        if (not np.array_equal(on, oldz['counts']) or not np.array_equal(od, oldz['days'])
                or not np.array_equal(original_daily, oldz['ledger'][8])
                or not np.array_equal(reference, oldz['reference'])
                or not np.array_equal(counts, rn) or not np.array_equal(days, rd)):
            raise ValueError('Frozen GATE ledger/population reconstruction differs')
        np.savez_compressed(folder / f'{phase}_daily.npz', ledger=daily, counts=counts, days=days, reference=reference)
        np.savez_compressed(folder / f'{phase}_actions.npz', actions=actions[sel], gate=original[sel], anchors=anchors)
        delta = actions[sel] - original[sel]
        phases[phase] = dict(daily_file=f'{phase}_daily.npz', daily=bind(folder / f'{phase}_daily.npz'),
            action_file=f'{phase}_actions.npz', action_file_binding=bind(folder / f'{phase}_actions.npz'),
            action_sha256=array_sha(actions[sel]), gate_action_sha256=array_sha(original[sel]),
            frozen_gate_action_sha256=oldrec['policies']['8']['action_sha256'],
            safe_action_sha256=array_sha(bank['safe'][sel]), cost_action_sha256=array_sha(bank['cost'][sel]),
            target_sha256=array_sha(y), mask_sha256=array_sha(mask, None), issues=int(sel.sum()),
            scored_cells=int(counts.sum()), metrics=(daily.sum(0) / counts.sum()).tolist(),
            gate_metrics=(original_daily.sum(0) / counts.sum()).tolist(),
            no_veto_minus_gate_metrics=((daily-original_daily).sum(0) / counts.sum()).tolist(),
            grid_no_veto_ge_gate=bool(np.all(delta >= 0)), scored_no_veto_ge_gate=bool(np.all(delta[mask] >= 0)),
            grid_action_delta_min=float(delta.min()), grid_action_delta_max=float(delta.max()),
            grid_action_delta_negative_cells=int(np.count_nonzero(delta < 0)),
            qualification_filter=False, frozen_parent_receipt=binding)
    windows = {}
    for key, (lo, hi) in VALIDATION_WINDOWS['outer'].items():
        use = (bank['anchors'] >= lo) & (bank['anchors'] < hi)
        windows[key] = dict(no_veto=_window_cell_metrics(actions[use], bank['shortfall'][use], bank['mask'][use]),
                            gate=_window_cell_metrics(original[use], bank['shortfall'][use], bank['mask'][use]))
    save_new(folder / 'receipt.json', dict(status='COMPLETED', seed=seed, arm='Z', vintage='outer',
        control=CONTROL, source_hashes=cfg['source_hashes'], freeze_sha256=cfg['parent_freeze_sha256'],
        history_receipt=bind(hp), history_bank=version['bank_manifest'], history_prefix_issues=1289,
        parent_full_metadata=bind(meta_path), full_metadata_exact=True, rebuilt_array_sha256=endpoint_hashes,
        full_feature_hashes_were_not_stored_by_parent=True,
        identity_evidence='Exact historical bank prefix; full metadata/trace equality; original SAFE/COST/GATE action SHA and target/mask SHA in both scoring phases',
        kernel_acceptance_sha256=sha(accepted), model_bindings=bindings, kernel=kernel_receipt,
        independent_action_bytes_exact=True, independent_daily_tolerance=1e-8,
        independent_snapshot_choices=independent_choices,
        original_gate_diagnostics=original_diag, phases=phases, validation_windows=windows,
        new_fits=0, qualification_filter=False, all_alpha_zero_instances_retained=True, environment=environment()))


def load_stage(folder: Path):
    completion = read(folder / 'completion.json')
    if completion['status'] != 'COMPLETED':
        raise ValueError('Incomplete statistics stage')
    for rel, binding in completion['files'].items():
        if bind(folder / rel) != binding:
            raise ValueError('Statistics stage binding changed: ' + rel)
    info = read(folder / 'all_policy_names.json')
    with np.load(folder / 'all_daily_ledger.npz', allow_pickle=False) as z:
        ledger, counts, days = z['ledger'].copy(), z['counts'].copy(), z['day_ids'].copy()
    return completion, info, ledger, counts, days


def collect_replays(out: Path, cfg, counts, days, reference):
    rows, bindings = [], {}
    for si, seed in enumerate(SEED_IDS):
        folder = out / 'replay' / f'seed{seed}'; path = folder / 'receipt.json'
        if not path.exists():
            raise ValueError('Missing mandatory fixed fit: ' + str(seed))
        receipt = read(path)
        if (receipt.get('status'), receipt.get('seed'), receipt.get('vintage'), receipt.get('control'),
                receipt.get('qualification_filter'), receipt.get('freeze_sha256')) != (
                    'COMPLETED', seed, 'outer', CONTROL, False, cfg['parent_freeze_sha256']):
            raise ValueError('Replay identity/filter differs')
        if receipt['source_hashes'] != cfg['source_hashes']:
            raise ValueError('Replay source release changed')
        for phase, issues in [('outer', 1289), ('evaluate', 5033)]:
            phase_rec = receipt['phases'].get(phase)
            if not phase_rec or phase_rec['issues'] != issues or phase_rec['qualification_filter']:
                raise ValueError('Missing/filtered scoring phase')
            if bind(folder / phase_rec['daily_file']) != phase_rec['daily']:
                raise ValueError('Replay daily SHA differs')
            ap = folder / phase_rec['action_file']
            if bind(ap) != phase_rec['action_file_binding']:
                raise ValueError('Replay action archive SHA differs')
            with np.load(ap, allow_pickle=False) as az:
                if (az['actions'].shape != az['gate'].shape or len(az['anchors']) != issues
                        or az['actions'].shape[0] != issues
                        or array_sha(az['actions']) != phase_rec['action_sha256']
                        or array_sha(az['gate']) != phase_rec['frozen_gate_action_sha256']):
                    raise ValueError('Replay action/phase identity differs')
        rec = receipt['phases']['evaluate']; daily_path = folder / rec['daily_file']
        if bind(daily_path) != rec['daily']:
            raise ValueError('Replay daily SHA differs')
        with np.load(daily_path, allow_pickle=False) as z:
            if (not np.array_equal(z['counts'], counts) or not np.array_equal(z['days'], days)
                    or not np.allclose(z['reference'], reference[si], rtol=0, atol=1e-8)):
                raise ValueError('Replay population/reference differs')
            bridge_error = float(np.max(np.abs(z['reference'] - reference[si])))
            row = z['ledger'].copy()
        if row.shape != (35, 4) or not np.isfinite(row).all() or np.any(row < 0):
            raise ValueError('Invalid new control ledger')
        rows.append(row); bindings[str(seed)] = dict(**bind(path),
            reference_bridge_max_abs_error=bridge_error, reference_bridge_original_atol=1e-8)
    return np.stack(rows), bindings


def aggregate(cfg, out: Path, deadline):
    _, _, parent_inf, parent, parent_counts, parent_days = verify_parent(cfg)
    completion, info, old, counts, days = load_stage(out / 'step1')
    if (completion['source_hashes'] != cfg['source_hashes'] or not np.array_equal(old, parent, equal_nan=True)
            or not np.array_equal(counts, parent_counts) or not np.array_equal(days, parent_days)):
        raise ValueError('Step A immutable parent bridge differs')
    ainf = read(out / 'step1/inference_span3.json')
    # Rebuild the direct family independently from the immutable parent.
    dn, da, dp, dx = extend_family(parent_inf)
    if info != dict(names=dn, available=da, comparisons=[list(p) for p in dp],
                    aliases=[list(p) for p in dx], nominal_family_size=DIRECT_SIZE['coordinates']):
        raise ValueError('Step A complete family changed')
    names, available, pairs, aliases = extend_family(ainf, [('EM1_008_Z', CONTROL)],
        new_role=CONTROL, expected_parent=DIRECT_SIZE, expected=AGGREGATE_SIZE)
    new, bindings = collect_replays(out, cfg, counts, days, old[:, 0])
    ledger = np.concatenate([old, new[:, None]], axis=1)
    folder = out / 'step2'; folder.mkdir(parents=True, exist_ok=False)
    np.savez_compressed(folder / 'all_daily_ledger.npz', ledger=ledger, counts=counts, day_ids=days)
    save_new(folder / 'all_policy_names.json', dict(names=names, available=available,
        comparisons=pairs, aliases=aliases, nominal_family_size=AGGREGATE_SIZE['coordinates']))
    run_inference(cfg, folder, ledger, counts, names, available, pairs, aliases, deadline)
    finish_stage(folder, cfg, dict(family_size=AGGREGATE_SIZE, mandatory_fixed_fits=list(SEED_IDS),
        scored_new_instances=10, parent_prefix_exact=True, step1_completion=bind(out / 'step1/completion.json'),
        replay_receipts=bindings, seed205_certificate_sidecar_only=True))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--protocol', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--stage', choices=('direct', 'replay', 'aggregate'), required=True)
    parser.add_argument('--seed', type=int, default=201)
    args = parser.parse_args()
    if not os.environ.get('PBS_JOBID') or not os.environ.get('CAMPAIGN_RELEASE'):
        raise ValueError('Bounded PBS allocation and sealed source-release identity required')
    if sha(ROOT / 'source_payload.zip') != os.environ['CAMPAIGN_RELEASE']:
        raise ValueError('PBS source identity does not bind the deployed source archive')
    cfg = read(args.protocol); config_check(cfg); verify_sources(cfg)
    out = args.output
    out.mkdir(parents=True, exist_ok=True)
    protocol_copy = out / 'protocol_original.json'
    if protocol_copy.exists():
        if protocol_copy.read_bytes() != args.protocol.read_bytes():
            raise ValueError('Campaign protocol changed')
    else:
        # Concurrent replay jobs only run after the direct stage creates this copy.
        with protocol_copy.open('xb') as stream:
            stream.write(args.protocol.read_bytes())
    start = time.process_time(); deadline = time.monotonic() + cfg['stage_limits'][args.stage]
    try:
        with threadpool_limits(limits=1):
            if args.stage == 'replay':
                replay(cfg, out, args.seed, deadline)
            else:
                globals()[args.stage](cfg, out, deadline)
        print(json.dumps(dict(status='COMPLETED', stage=args.stage, seed=args.seed,
                              process_cpu_seconds=time.process_time()-start)), flush=True)
    except BaseException as exc:
        dst = out / 'failures' / f'{args.stage}_seed{args.seed}_{os.environ["PBS_JOBID"].replace("/", "_")}.json'
        save_new(dst, dict(status='FAILED', error=repr(exc), traceback=traceback.format_exc(),
                          process_cpu_seconds=time.process_time()-start, environment=environment()))
        raise


if __name__ == '__main__':
    main()
