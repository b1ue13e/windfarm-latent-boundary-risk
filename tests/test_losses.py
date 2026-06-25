from __future__ import annotations

import unittest

import torch

from windfarm_moe.losses import moe_load_balancing_loss, physics_force_loss


class LossTests(unittest.TestCase):
    def test_load_balancing_penalizes_collapse(self) -> None:
        uniform_gate = torch.full((2, 3, 3), 1.0 / 3.0)
        collapsed_gate = torch.zeros((2, 3, 3))
        collapsed_gate[..., 0] = 1.0

        uniform_loss = moe_load_balancing_loss(uniform_gate, top_k=1)
        collapsed_loss = moe_load_balancing_loss(collapsed_gate, top_k=1)

        self.assertAlmostEqual(float(uniform_loss.item()), 0.0, places=5)
        self.assertGreater(float(collapsed_loss.item()), 1.5)

    def test_physics_force_prefers_correct_mppt_pitch_switch(self) -> None:
        regime = torch.tensor([[1, 2]], dtype=torch.int64)
        valid = torch.ones((1, 2), dtype=torch.float32)

        correct_logits = torch.tensor(
            [[[0.0, 4.0, -2.0, 0.0], [0.0, -1.5, 3.5, 0.0]]],
            dtype=torch.float32,
        )
        wrong_logits = torch.tensor(
            [[[0.0, -2.0, 4.0, 0.0], [0.0, 3.5, -1.5, 0.0]]],
            dtype=torch.float32,
        )

        good = physics_force_loss(correct_logits, regime, valid)
        bad = physics_force_loss(wrong_logits, regime, valid)
        self.assertLess(float(good.item()), float(bad.item()))


if __name__ == "__main__":
    unittest.main()
