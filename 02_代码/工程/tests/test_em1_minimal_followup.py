from __future__ import annotations

import copy
import json
from repo_paths import Path, repository_root

import numpy as np
import pytest

from scripts import run_em1_minimal_followup as r


def small_parent():
    return dict(policy_names=['REF', 'G', 'P', 'S'], available=[True, True, False, True],
        family_definition=dict(policy_names=['REF', 'G', 'P', 'S'],
                               comparisons=[[1, 0], [2, 0]], frozen_aliases=[[3, 0]]))


def test_family_preserves_order_unavailable_and_integer_references():
    parent = small_parent(); before = copy.deepcopy(parent)
    n, a, p, x = r.extend_family(parent, [('G', 'P')],
        expected_parent=dict(policies=4, pairs=2, aliases=1, coordinates=64),
        expected=dict(policies=4, pairs=3, aliases=1, coordinates=74))
    assert parent == before
    assert n == ['REF', 'G', 'P', 'S'] and a == [True, True, False, True]
    assert p == [('G', 'REF'), ('P', 'REF'), ('G', 'P')]
    assert x == [('S', 'REF')]
    newer = dict(policy_names=n, available=a,
                 family_definition=dict(policy_names=n, comparisons=p, frozen_aliases=x))
    nn, aa, pp, xx = r.extend_family(newer, [('G', 'NV')], new_role='NV',
        expected_parent=dict(policies=4, pairs=3, aliases=1, coordinates=74),
        expected=dict(policies=5, pairs=4, aliases=1, coordinates=95))
    assert nn[:-1] == n and aa[:-1] == a and aa[-1] is True
    assert pp[:-1] == p and xx == x


@pytest.mark.parametrize('pair', [[True, 0], [99, 0], ['UNKNOWN', 0], [0], [0, None]])
def test_invalid_frozen_references_are_rejected(pair):
    with pytest.raises(ValueError):
        r._pair_names(pair, ['REF', 'G'])


def test_real_family_adds_twenty_then_twenty_one_coordinates():
    root = Path(repository_root())
    info = json.loads((root / 'experiments/endpoint_match_20261025/recovered/results/campaign/all_policy_names.json').read_text())
    parent = dict(policy_names=info['names'], available=info['available'],
        family_definition=dict(policy_names=info['names'], comparisons=info['comparisons'], frozen_aliases=info['aliases']))
    n, a, p, x = r.extend_family(parent)
    assert r.family_size(n, p, x) == r.DIRECT_SIZE
    assert n == info['names'] and a == info['available']
    assert p[-2:] == list(r.DIRECT_PAIRS)
    middle = dict(policy_names=n, available=a,
                  family_definition=dict(policy_names=n, comparisons=p, frozen_aliases=x))
    nn, aa, pp, xx = r.extend_family(middle, [('EM1_008_Z', r.CONTROL)], new_role=r.CONTROL,
        expected_parent=r.DIRECT_SIZE, expected=r.AGGREGATE_SIZE)
    assert r.family_size(nn, pp, xx) == r.AGGREGATE_SIZE
    assert nn[:-1] == n and aa[:-1] == a and pp[:-1] == p and xx == x


def test_added_pairs_are_part_of_complete_inference_family():
    # Scalar hand construction: G costs one fifth less than REF on each day;
    # S is an explicit structural alias. P stays present but unavailable.
    count = np.full(35, 100)
    ledger = np.ones((5, 4, 35, 4))
    ledger[..., 0] = np.arange(35)[None, None, :] + 50
    ledger[:, 1, :, 0] *= .8
    ledger[:, 3] = ledger[:, 0]
    ledger[:, 2] = np.nan
    parent = small_parent()
    names, available, pairs, aliases = r.extend_family(parent, [('G', 'P')],
        expected_parent=dict(policies=4, pairs=2, aliases=1, coordinates=64),
        expected=dict(policies=4, pairs=3, aliases=1, coordinates=74))
    result = r.infer_stable_campaign(ledger, count, names, pairs, aliases=aliases,
                                    available=available, span=3, n_boot=20)
    assert result['family_size'] == 74
    assert len(result['qualification']) == 4
    assert result['coordinates'][44]['point'] == pytest.approx(-.2)
    assert result['coordinates'][-1]['status'] == 'SOURCE_UNAVAILABLE'
    assert result['qualification']['S']['five_instance_H_noninferior'] is True
    assert result['thresholds'] == r.THRESHOLDS


def create_replays(folder, *, source=None):
    source = source or {'x': 'sealed'}
    cfg = dict(source_hashes=source, parent_freeze_sha256='freeze')
    counts = np.arange(35) + 1
    days = np.arange(210, 245)
    reference = np.arange(5 * 35 * 4).reshape(5, 35, 4).astype(float)
    for si, seed in enumerate(r.SEED_IDS):
        p = folder / 'replay' / f'seed{seed}'; p.mkdir(parents=True)
        # Seed 205 is intentionally all-zero and must never be filtered out.
        data = np.full((35, 4), 0. if seed == 205 else si + 1.)
        phases = {}
        for phase, n in [('outer', 1289), ('evaluate', 5033)]:
            np.savez_compressed(p / f'{phase}_daily.npz', ledger=data, counts=counts, days=days, reference=reference[si])
            actions = np.zeros((n, 1)); anchors = np.arange(n)
            np.savez_compressed(p / f'{phase}_actions.npz', actions=actions, gate=actions, anchors=anchors)
            phases[phase] = dict(daily_file=f'{phase}_daily.npz', daily=r.bind(p / f'{phase}_daily.npz'),
                action_file=f'{phase}_actions.npz', action_file_binding=r.bind(p / f'{phase}_actions.npz'),
                issues=n, qualification_filter=False, action_sha256=r.array_sha(actions),
                frozen_gate_action_sha256=r.array_sha(actions))
        r.save_new(p / 'receipt.json', dict(status='COMPLETED', seed=seed, vintage='outer',
            control=r.CONTROL, qualification_filter=False, freeze_sha256='freeze', source_hashes=source,
            phases=phases))
    return cfg, counts, days, reference


def test_all_five_fits_include_alpha_zero_instance(tmp_path):
    cfg, counts, days, ref = create_replays(tmp_path)
    new, bindings = r.collect_replays(tmp_path, cfg, counts, days, ref)
    assert new.shape == (5, 35, 4) and np.array_equal(new[-1], np.zeros((35, 4)))
    assert list(bindings) == [str(s) for s in r.SEED_IDS]


def test_missing_seed_and_tampered_hash_are_rejected(tmp_path):
    cfg, counts, days, ref = create_replays(tmp_path)
    path = tmp_path / 'replay/seed203/receipt.json'; receipt = r.read(path); path.unlink()
    with pytest.raises(ValueError, match='Missing mandatory fixed fit'):
        r.collect_replays(tmp_path, cfg, counts, days, ref)
    # Restore the receipt, then alter an immutable NPZ byte without changing its binding.
    daily = path.with_name('evaluate_daily.npz')
    r.save_new(path, receipt)
    with daily.open('ab') as stream:
        stream.write(b'tamper')
    with pytest.raises(ValueError, match='daily SHA'):
        r.collect_replays(tmp_path, cfg, counts, days, ref)


def test_rebound_wrong_counts_and_source_still_rejected(tmp_path):
    cfg, counts, days, ref = create_replays(tmp_path)
    folder = tmp_path / 'replay/seed201'; receipt = r.read(folder / 'receipt.json')
    np.savez_compressed(folder / 'evaluate_daily.npz', ledger=np.ones((35, 4)),
                        counts=counts+1, days=days, reference=ref[0])
    receipt['phases']['evaluate']['daily'] = r.bind(folder / 'evaluate_daily.npz')
    (folder / 'receipt.json').write_text(json.dumps(receipt))
    with pytest.raises(ValueError, match='population/reference'):
        r.collect_replays(tmp_path, cfg, counts, days, ref)
    receipt['source_hashes'] = {'x': 'different'}
    (folder / 'receipt.json').write_text(json.dumps(receipt))
    with pytest.raises(ValueError, match='source release'):
        r.collect_replays(tmp_path, cfg, counts, days, ref)


def test_prediction_views_do_not_expose_target_mask_or_future_metadata():
    class Guard(dict):
        def __getitem__(self, key):
            if key in ('shortfall', 'mask', 'target', 'metadata'):
                raise AssertionError('Forbidden action-time information')
            return super().__getitem__(key)
    bank = Guard({k: object() for k in ('anchors', 'safe', 'cost', 'current_features', 'feedback_features')})
    assert set(r.action_view(bank)) == {'anchors', 'safe', 'cost', 'current_features', 'feedback_features'}


def test_original_reference_rounding_tolerance_is_preserved(tmp_path):
    cfg, counts, days, ref = create_replays(tmp_path)
    ref = ref.copy(); ref[0, 0, 0] += 5e-9
    _, bindings = r.collect_replays(tmp_path, cfg, counts, days, ref)
    assert bindings['201']['reference_bridge_max_abs_error'] == pytest.approx(5e-9)
    ref[0, 0, 0] += 1e-7
    with pytest.raises(ValueError, match='population/reference'):
        r.collect_replays(tmp_path, cfg, counts, days, ref)


def test_configuration_and_no_overwrite(tmp_path):
    cfg = r.read(Path(repository_root()) / 'experiments/em1_minimal_followup_20261025/protocol.json')
    r.config_check(cfg)
    cfg['thresholds'] = dict(cfg['thresholds'], signed_H=.01)
    with pytest.raises(ValueError, match='specification changed'):
        r.config_check(cfg)
    dst = tmp_path / 'immutable.json'; r.save_new(dst, {'original': True})
    with pytest.raises(FileExistsError):
        r.save_new(dst, {'replacement': True})
    assert r.read(dst) == {'original': True}


def test_stage_binding_detects_mutation(tmp_path):
    payload = tmp_path / 'all_policy_names.json'; payload.write_text('{}')
    r.save_new(tmp_path / 'completion.json', dict(status='COMPLETED', files={payload.name:r.bind(payload)}))
    payload.write_text('{"altered":true}')
    with pytest.raises(ValueError, match='binding changed'):
        r.load_stage(tmp_path)
