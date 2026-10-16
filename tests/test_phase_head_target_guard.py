"""Regression for the real matching-invalid-NaN failure and non-equivalent targets."""
import ast
import os
from pathlib import Path
import numpy as np
import pytest


source = Path(os.environ.get('PHASE_GUARD_SOURCE', Path(__file__).resolve().parents[1] / 'scripts/eval_single_task_dense_phase_scan.py'))
tree = ast.parse(source.read_text(encoding='utf-8'))
node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'assert_matched_head_training')
namespace = {'np': np}
exec(compile(ast.Module(body=[node], type_ignores=[]), str(source), 'exec'), namespace)
check = namespace['assert_matched_head_training']


def pair():
    a = dict(anchor_indices=np.array([40, 41]), mask=np.array([[1., 0.], [1., 1.]]),
             shortfall=np.array([[0., np.nan], [2., 3.]]))
    return a, {k: v.copy() for k, v in a.items()}


def test_real_failure_semantics():
    a, b = pair()
    assert not np.array_equal(a['shortfall'], b['shortfall'])
    assert check(a, b)['valid_cells'] == 3


@pytest.mark.parametrize('kind', ['valid_value', 'valid_nan', 'valid_inf', 'invalid_value', 'mask', 'anchor', 'empty'])
def test_mismatches_still_stop(kind):
    a, b = pair()
    if kind == 'valid_value':
        b['shortfall'][1, 0] = np.nextafter(2., 3.)
    elif kind in ('valid_nan', 'valid_inf'):
        a['shortfall'][1, 0] = b['shortfall'][1, 0] = np.nan if kind == 'valid_nan' else np.inf
    elif kind == 'invalid_value':
        b['shortfall'][0, 1] = 0.
    elif kind == 'mask':
        b['mask'][0, 1] = 1.
    elif kind == 'anchor':
        b['anchor_indices'][0] += 1
    else:
        a['mask'].fill(0); b['mask'].fill(0)
    with pytest.raises(ValueError):
        check(a, b)
