"""Independent synthetic checks for the frozen campaign inference layer."""
from __future__ import annotations

import hashlib
import json
import math

import numpy as np
import pytest

from windfarm_moe.autonomous_campaign_inference import infer_campaign


def example():
    days = np.arange(35, dtype=float)
    counts = 100 + np.arange(35) % 7
    ledger = np.empty((5, 3, 35, 4), dtype=float)
    for fit in range(5):
        for policy in range(3):
            r = 10 + .3 * np.sin(days / 3 + policy) + fit * .05 + policy * .1
            u = 1 + .1 * np.cos(days / 2 + fit) - policy * .01
            ledger[fit, policy, :, 1] = r * counts
            ledger[fit, policy, :, 2] = u * counts
            ledger[fit, policy, :, 0] = (r + 10 * u) * counts
            ledger[fit, policy, :, 3] = 5 + (np.arange(35) + fit + policy) % 7
    return ledger, counts


def coordinate(result, cid):
    return next(row for row in result['coordinates'] if row['id'] == cid)


def test_complete_nominal_family_missing_policy_is_not_removed():
    ledger, counts = example()
    ledger[:, 2] = np.nan
    r = infer_campaign(ledger, counts, ['REF', 'P', 'MISSING'], [('P', 'MISSING')],
                       span=3, n_boot=101, available=[True, True, False])
    assert len(r['coordinates']) == 3 * 11 + 10
    assert len({x['id'] for x in r['coordinates']}) == 43
    assert coordinate(r, 'Q:2:D')['status'] == 'SOURCE_UNAVAILABLE'
    assert coordinate(r, 'E:0:U')['status'] == 'SOURCE_UNAVAILABLE'
    assert r['qualification']['MISSING']['qualified'] is None
    assert r['comparisons'][0]['joint_gain'] is None


def test_algebraic_alias_requires_explicit_and_complete_ledger_equality():
    ledger, counts = example()
    ledger[:, 2] = ledger[:, 1]
    plain = infer_campaign(ledger, counts, ['REF', 'P', 'IGNORE'], [('IGNORE', 'P')], span=3, n_boot=101)
    explicit = infer_campaign(ledger, counts, ['REF', 'P', 'IGNORE'], [('IGNORE', 'P')],
                              span=3, n_boot=101, aliases=[('IGNORE', 'P')])
    assert coordinate(plain, 'E:0:U')['status'] == 'ZERO_EMPIRICAL_VARIANCE'
    for key in ['D', 'C', 'R', 'U', 'V', 'H:201', 'H:205']:
        row = coordinate(explicit, 'E:0:' + key)
        assert row['status'] == 'EXACT_ALGEBRAIC_ZERO'
        assert row['point'] == row['lower'] == row['upper'] == 0
    ledger[4, 2, 34, 1] += 1e-10
    with pytest.raises(ValueError, match='alias'):
        infer_campaign(ledger, counts, ['REF', 'P', 'IGNORE'], [('IGNORE', 'P')],
                       span=3, n_boot=101, aliases=[('IGNORE', 'P')])


def test_absolute_zero_risk_is_not_structurally_exact():
    ledger, counts = example()
    ledger[..., 3] = 0
    r = infer_campaign(ledger, counts, ['REF', 'P', 'Z'], [], span=1, n_boot=101)
    risk = coordinate(r, 'Q:0:V:201')
    assert risk['point'] == 0
    assert risk['lower'] == 0 and risk['upper'] == 1
    assert risk['status'] == 'ZERO_EMPIRICAL_VARIANCE'
    assert risk['exact'] is False
    assert r['qualification']['REF']['qualified'] is None


def test_zero_observed_n_and_zero_draw_n_keep_all_endpoints():
    ledger = np.zeros((5, 2, 35, 4))
    counts = np.zeros(35)
    r = infer_campaign(ledger, counts, ['REF', 'P'], [('P', 'REF')], span=3, n_boot=101)
    assert len(r['coordinates']) == 32
    assert all(x['status'] == 'ZERO_OBSERVED_DENOMINATOR' for x in r['coordinates'])
    counts[0] = 1
    ledger[:, :, 0, 0] = 2
    r = infer_campaign(ledger, counts, ['REF', 'P'], [('P', 'REF')], span=1, n_boot=101)
    assert all(x['status'] == 'ZERO_DRAW_DENOMINATOR' for x in r['coordinates'])
    assert r['n_boot'] == 101 and r['critical_value'] is None


def test_zero_relative_cost_denominator_only_invalidates_relative_cost():
    ledger, counts = example()
    ledger[:, 0, :, 0] = 0
    ledger[:, 1, :, 2] += (np.arange(35) % 5)[None, :] * counts * .01
    r = infer_campaign(ledger, counts, ['REF', 'P', 'Z'], [('P', 'REF')], span=3, n_boot=101)
    assert coordinate(r, 'Q:1:D')['status'] == 'ZERO_OBSERVED_COST_DENOMINATOR'
    assert coordinate(r, 'E:0:D')['status'] == 'ZERO_OBSERVED_COST_DENOMINATOR'
    assert coordinate(r, 'E:0:U')['status'] == 'ESTIMABLE_APPROX'
    assert r['qualification']['P']['cost_noninferior'] is None


def test_one_zero_draw_cost_denominator_is_not_deleted_or_epsilon_filled():
    ledger, counts = example()
    ledger[:, 0, :, 0] = 0
    ledger[:, 0, 0, 0] = 1
    r = infer_campaign(ledger, counts, ['REF', 'P', 'Z'], [('P', 'REF')], span=1, n_boot=101)
    row = coordinate(r, 'E:0:D')
    assert row['point'] is not None
    assert row['status'] == 'ZERO_DRAW_COST_DENOMINATOR'
    assert row['lower'] is None and row['upper'] is None


def test_shared_natural_day_trace_and_maximum_standardized_envelope_match_scalar_oracle():
    ledger, counts = example()
    n_boot, seed, span = 113, 82, 3
    r = infer_campaign(ledger, counts, ['REF', 'P', 'Z'], [('P', 'REF')],
                       span=span, seed=seed, n_boot=n_boot)
    rng = np.random.default_rng(seed)
    starts = rng.integers(0, 35, size=(n_boot, math.ceil(35 / span)))
    # Reconstruct circular segments without calling a production helper.
    indices = np.asarray([[int((start + j) % 35) for start in row for j in range(span)][:35]
                          for row in starts], dtype=np.int64)
    assert r['bootstrap_indices_sha256'] == hashlib.sha256(indices.astype('<i8').tobytes()).hexdigest()
    bootstrap = []
    point = []
    for row in r['coordinates']:
        desc = row['definition']
        left, right, metric, fit = desc['left'], desc['right'], desc['metric'], desc['fit']
        def statistic(ix):
            den = sum(float(counts[d]) for d in ix)
            values = []
            for k in (range(5) if fit is None else [fit]):
                if metric == 'D':
                    l = sum(float(ledger[k, left, d, 0]) for d in ix)
                    rr = sum(float(ledger[k, right, d, 0]) for d in ix)
                    values.append((l - rr) / den)
                else:
                    col = {'C': 0, 'R': 1, 'U': 2, 'V': 3, 'H': 2}[metric]
                    l = sum(float(ledger[k, left, d, col]) for d in ix)
                    rr = 0 if right is None else sum(float(ledger[k, right, d, col]) for d in ix)
                    values.append((l - rr) / den)
            value = sum(values) / len(values)
            if metric == 'D':
                base = sum(sum(float(ledger[k, right, d, 0]) for d in ix) / den for k in range(5)) / 5
                value /= base
            if metric == 'H':
                value *= 10 / 42.058880543674675
            return value
        point.append(statistic(range(35)))
        bootstrap.append([statistic(ix) for ix in indices])
    bootstrap = np.asarray(bootstrap).T
    point = np.asarray(point)
    eligible = [j for j, row in enumerate(r['coordinates']) if row['status'] == 'ESTIMABLE_APPROX']
    deviations = []
    for j in eligible:
        sd = np.std(bootstrap[:, j], ddof=1)
        deviations.append(np.abs(bootstrap[:, j] - point[j]) / sd)
        assert coordinate(r, r['coordinates'][j]['id'])['standard_error'] == pytest.approx(sd, abs=1e-13)
    maxima = np.max(deviations, axis=0)
    critical = sorted(maxima)[math.ceil(.95 * (n_boot - 1))]
    assert r['critical_value'] == pytest.approx(critical, abs=1e-10)
    for j in eligible:
        sd = np.std(bootstrap[:, j], ddof=1)
        domain = r['coordinates'][j]['domain']
        lower = max(-np.inf if domain[0] is None else domain[0], point[j] - critical * sd)
        upper = min(np.inf if domain[1] is None else domain[1], point[j] + critical * sd)
        assert r['coordinates'][j]['lower'] == pytest.approx(lower, abs=1e-10)
        assert r['coordinates'][j]['upper'] == pytest.approx(upper, abs=1e-10)


def test_fixed_fit_offsets_cancel_before_weather_resampling():
    ledger, counts = example()
    ledger[:, 1, :, 2] = ledger[:, 0, :, 2]
    for fit, shift in enumerate([-2, -1, 0, 1, 2]):
        ledger[fit, 1, :, 2] += shift * .01 * counts
    r = infer_campaign(ledger, counts, ['REF', 'P', 'Z'], [('P', 'REF')], span=3, n_boot=101)
    row = coordinate(r, 'E:0:U')
    assert row['status'] == 'ZERO_EMPIRICAL_VARIANCE'
    assert row['exact'] is False
    assert r['n_fixed_fits'] == 5 and r['resampling_unit'] == 'shared natural weather day'


def test_qualification_and_numerical_protection_labels_are_separate():
    ledger, counts = example()
    ledger[:, 1, :, 1] = ledger[:, 0, :, 1] * 1.02
    ledger[:, 1, :, 2] = ledger[:, 0, :, 2] * .5
    ledger[:, 1, :, 0] = ledger[:, 1, :, 1] + 10 * ledger[:, 1, :, 2]
    ledger[:, 0, :, 3] = 20 + np.arange(35) % 7
    ledger[:, 1, :, 3] = ledger[:, 0, :, 3] - 7
    r = infer_campaign(ledger, counts, ['REF', 'P', 'Z'], [('P', 'REF')], span=3, n_boot=401)
    comp = r['comparisons'][0]
    assert comp['descriptive_conditional_protection'] is True
    assert comp['qualified_joint_protection'] is False
    assert r['selection_adjusted'] is False and r['independent_confirmation'] is False
    assert r['coverage_certified'] is False
    assert 'conditional on the realized update trajectory' in r['inference_target']


def test_family_hash_reproducible_and_sensitive_to_frozen_list():
    ledger, counts = example()
    a = infer_campaign(ledger, counts, ['REF', 'P', 'Z'], [('P', 'REF')], span=3, n_boot=101)
    b = infer_campaign(ledger, counts, ['REF', 'P', 'Z'], [('P', 'REF')], span=7, n_boot=101)
    c = infer_campaign(ledger, counts, ['REF', 'P', 'Z'], [('Z', 'REF')], span=3, n_boot=101)
    assert a['family_sha256'] == b['family_sha256']
    assert a['family_sha256'] != c['family_sha256']
    assert a['source_sha256'] == b['source_sha256']


def test_unavailable_alias_does_not_remove_the_nominal_family():
    ledger, counts = example()
    ledger[:, 2] = np.nan
    r = infer_campaign(ledger, counts, ['REF', 'P', 'IGNORE'], [('IGNORE', 'P')],
                       span=3, n_boot=101, available=[True, True, False], aliases=[('IGNORE', 'P')])
    assert r['alias_verification'][0]['verified'] is False
    assert r['family_size'] == 43
    assert coordinate(r, 'E:0:U')['status'] == 'SOURCE_UNAVAILABLE'


def test_raw_ledger_cannot_replace_strict_events_with_fractional_scores():
    ledger, counts = example()
    ledger[1, 1, 3, 3] += .25
    r = infer_campaign(ledger, counts, ['REF', 'P', 'Z'], [('P', 'REF')], span=3, n_boot=101)
    assert coordinate(r, 'Q:1:V:202')['status'] == 'SOURCE_INVALID'
    assert coordinate(r, 'E:0:V')['status'] == 'SOURCE_INVALID'
    assert coordinate(r, 'E:0:R')['status'] == 'ESTIMABLE_APPROX'


def test_report_only_cstar_is_frozen_not_a_tuning_parameter():
    ledger, counts = example()
    with pytest.raises(ValueError, match='frozen'):
        infer_campaign(ledger, counts, ['REF', 'P', 'Z'], [], span=3, n_boot=101, cstar=42.)


def test_production_defaults_run_the_complete_draw_count_and_are_json_safe():
    ledger, counts = example()
    untouched = ledger.copy()
    r = infer_campaign(ledger, counts, ['REF', 'P', 'Z'], [('P', 'REF')], span=3)
    assert r['n_boot'] == 20000 and r['resampling_seed'] == 20261022
    assert r['production_draw_specification'] is True
    assert r['family_size'] == 43 and r['family_definition']['thresholds']['signed_H'] == .001
    json.dumps(r, allow_nan=False)
    np.testing.assert_array_equal(ledger, untouched)


@pytest.mark.parametrize('change', ['fits', 'counts', 'names', 'span', 'available'])
def test_invalid_schema_is_rejected(change):
    ledger, counts = example()
    kw = dict(span=3, n_boot=11)
    names = ['REF', 'P', 'Z']
    if change == 'fits': ledger = ledger[:4]
    if change == 'counts': counts = counts.astype(float); counts[0] = -1
    if change == 'names': names[2] = 'P'
    if change == 'span': kw['span'] = 2
    if change == 'available': kw['available'] = [True, False]
    with pytest.raises(ValueError):
        infer_campaign(ledger, counts, names, [('P', 'REF')], **kw)
