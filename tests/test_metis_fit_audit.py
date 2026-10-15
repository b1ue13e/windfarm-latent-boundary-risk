"""Software regressions for readiness false-positive guards, not experiment data."""
import importlib.util
import os
from pathlib import Path
import pytest

source=Path(os.environ.get('FIT_AUDIT_SOURCE',Path(__file__).resolve().parents[1]/'scripts/audit_metis_fit_outputs.py'))
spec=importlib.util.spec_from_file_location('fit_audit',source)
audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)


def test_completed_label_with_failed_exit_or_missing_outputs_cannot_pass():
    record={'status':'EXECUTED','exit_code':0,'inputs':[{'fixture':True}],'outputs':[{'fixture':True}]}
    audit.require_success(record)
    with pytest.raises(ValueError):audit.require_success(dict(record,exit_code=1))
    with pytest.raises(ValueError):audit.require_success(dict(record,outputs=[]))


def test_twenty_records_cannot_replace_a_missing_seed_with_a_duplicate():
    families=('forecast','unaligned','aligned','dense_classifier')
    rows=[{'family':family,'seed':seed} for family in families for seed in range(201,206)]
    audit.require_matrix(rows,families)
    rows[-1]=rows[0].copy()
    with pytest.raises(ValueError):audit.require_matrix(rows,families)


def test_new_prerequisites_and_human_holds_are_never_discarded():
    source=Path(os.environ.get('FACTORIAL_READINESS_SOURCE',
        Path(__file__).resolve().parents[1]/'scripts/watch_metis_factorial_readiness.py'))
    spec=importlib.util.spec_from_file_location('ready_control',source)
    control=importlib.util.module_from_spec(spec);spec.loader.exec_module(control)
    current={'Hold_Types':'s','depend':'afterok:242595.cm@cm,beforeok:242603.cm@cm'}
    updated=control.replacement_dependency(current,'300000.cm')
    assert updated=='afterok:242601.cm:300000.cm,beforeok:242603.cm@cm'
    extra=dict(current,depend='afterok:242595.cm@cm:999999.cm@cm,beforeok:242603.cm@cm')
    with pytest.raises(ValueError):control.replacement_dependency(extra,'300000.cm')
    with pytest.raises(ValueError):control.replacement_dependency(dict(current,Hold_Types='su'),'300000.cm')
