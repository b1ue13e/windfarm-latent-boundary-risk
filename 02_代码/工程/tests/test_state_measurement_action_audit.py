import numpy as np
import pytest

from scripts.audit_state_measurement_pilot import audit_actions
from windfarm_moe.state_measurement import account


def test_serialized_action_tampering_and_mismatched_totals_are_detected(tmp_path):
    a = np.array([143, 144, 145])
    s = np.array([[12., np.nan], [0., 3.], [2., 4.]])
    raw = np.array([[6., 500.], [1., 5.], [2., 1.]])
    r = np.maximum(raw + .5, 0)
    m = np.isfinite(s)
    np.savez(tmp_path / "actions.npz", raw=raw, calibrated=r)
    b = account(s, r, m, a)
    with np.load(tmp_path / "actions.npz") as z:
        assert audit_actions(s, a, m, z["raw"], z["calibrated"], .5, b)["checks"] == 7
        changed = b | {"C": b["C"] + 1}
        with pytest.raises(ValueError, match="accounting mismatch"):
            audit_actions(s, a, m, z["raw"], z["calibrated"], .5, changed)
        with pytest.raises(ValueError, match="action/offset mismatch"):
            audit_actions(s, a, m, z["raw"], z["calibrated"] + 1, .5, b)
        with pytest.raises(ValueError, match="count mismatch"):
            audit_actions(s, a, m, z["raw"], z["calibrated"], .5, b | {"V": b["V"] + 1})
