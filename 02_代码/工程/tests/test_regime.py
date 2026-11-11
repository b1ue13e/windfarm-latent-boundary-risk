from __future__ import annotations

import unittest

import numpy as np

from windfarm_moe.regimes import (
    compute_era5_regime_from_sshf,
    compute_wtb_operation_regime,
    compute_wtb_wake_flag,
)


class RegimeRuleTests(unittest.TestCase):
    def test_wtb_primary_regime_boundaries(self) -> None:
        wspd = np.array([[2.9, 3.0, 10.5, 11.0, 8.0]], dtype=np.float32)
        pab_avg = np.array([[1.0, 1.0, 1.5, 2.0, 3.0]], dtype=np.float32)
        regime, valid = compute_wtb_operation_regime(wspd, pab_avg)
        self.assertEqual(regime[0, 0], 0)
        self.assertEqual(regime[0, 1], 1)
        self.assertEqual(regime[0, 2], 1)
        self.assertEqual(regime[0, 3], 2)
        self.assertEqual(regime[0, 4], 3)
        self.assertEqual(valid[0, 4], 0.0)

    def test_wtb_primary_regime_custom_thresholds(self) -> None:
        wspd = np.array([[10.2, 10.7, 11.1]], dtype=np.float32)
        pab_avg = np.array([[1.8, 1.8, 2.1]], dtype=np.float32)
        regime, _ = compute_wtb_operation_regime(wspd, pab_avg, rated_wind=11.0, pitch_threshold=2.0)
        self.assertEqual(regime[0, 0], 1)
        self.assertEqual(regime[0, 1], 1)
        self.assertEqual(regime[0, 2], 2)

    def test_wtb_primary_regime_marks_missing_anchor_invalid(self) -> None:
        wspd = np.array([[np.nan, 11.0]], dtype=np.float32)
        pab_avg = np.array([[3.0, np.nan]], dtype=np.float32)

        regime, valid = compute_wtb_operation_regime(wspd, pab_avg)

        self.assertEqual(regime[0, 0], 3)
        self.assertEqual(regime[0, 1], 3)
        self.assertEqual(valid[0, 0], 0.0)
        self.assertEqual(valid[0, 1], 0.0)

    def test_wtb_wake_flag_does_not_override_primary(self) -> None:
        wake_score = np.array([[0.1, 0.4], [0.8, 0.9], [0.2, 0.3]], dtype=np.float32)
        op_regime = np.array([[1, 2], [1, 2], [0, 3]], dtype=np.int16)
        wake_flag, wake_valid, threshold = compute_wtb_wake_flag(wake_score, op_regime, train_stop=2)
        self.assertGreaterEqual(threshold, 0.0)
        self.assertEqual(op_regime[1, 0], 1)
        self.assertEqual(op_regime[1, 1], 2)
        self.assertEqual(wake_valid[2, 0], 0.0)
        self.assertEqual(wake_valid[2, 1], 0.0)

    def test_wtb_wake_flag_quantile_is_configurable(self) -> None:
        wake_score = np.array([[0.1, 0.2], [0.7, 0.8], [0.9, 1.0]], dtype=np.float32)
        op_regime = np.array([[1, 1], [1, 1], [1, 1]], dtype=np.int16)
        _, _, q70 = compute_wtb_wake_flag(wake_score, op_regime, train_stop=3, quantile=0.70)
        _, _, q90 = compute_wtb_wake_flag(wake_score, op_regime, train_stop=3, quantile=0.90)
        self.assertLess(q70, q90)

    def test_era5_regime_from_sshf(self) -> None:
        sshf = np.array(
            [
                [[50.0], [-60.0]],
                [[45.0], [-55.0]],
                [[0.1], [-0.1]],
                [[80.0], [-100.0]],
            ],
            dtype=np.float32,
        )
        regime, meta = compute_era5_regime_from_sshf(sshf.reshape(4, 2), train_stop=3)
        self.assertIn("eps", meta)
        self.assertIn("shock_quantile", meta)
        self.assertEqual(regime[0, 0], 0)
        self.assertEqual(regime[0, 1], 1)
        self.assertEqual(regime[2, 0], 2)
        self.assertEqual(regime[2, 1], 2)


if __name__ == "__main__":
    unittest.main()
