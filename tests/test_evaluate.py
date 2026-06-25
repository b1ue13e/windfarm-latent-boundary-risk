from __future__ import annotations

import math
import tempfile
import unittest
from pathlib import Path

import numpy as np
import torch

from windfarm_moe.config import EvalConfig
from windfarm_moe.evaluate import evaluate_model


class _Bundle:
    physics = np.zeros((3, 2, 4), dtype=np.float32)
    metadata = {
        "primary_regime_names": ["idle", "mppt", "pitch_control", "transition"],
        "primary_num_classes": 3,
        "steps_per_hour": 6,
    }


class _Model(torch.nn.Module):
    def forward(self, x_hist, edge_index_hist, edge_weight_hist, feature_mask_hist=None, anchor_physics=None):
        batch = x_hist.shape[0]
        nodes = x_hist.shape[2]
        pred = torch.zeros((batch, 2, nodes), dtype=torch.float32)
        gate = torch.full((batch, nodes, 4), 0.25, dtype=torch.float32)
        return pred, gate, {}


class EvaluateTests(unittest.TestCase):
    def test_gate_alignment_handles_empty_valid_regime_cells(self) -> None:
        batch = {
            "x_hist": torch.zeros((3, 3, 2, 4), dtype=torch.float32),
            "feature_mask_hist": torch.ones((3, 3, 2, 4), dtype=torch.float32),
            "edge_index_hist": torch.zeros((3, 3, 2, 1), dtype=torch.int64),
            "edge_weight_hist": torch.zeros((3, 3, 2, 1), dtype=torch.float32),
            "target": torch.zeros((3, 2, 2), dtype=torch.float32),
            "target_mask": torch.ones((3, 2, 2), dtype=torch.float32),
            "regime_primary": torch.zeros((3, 2), dtype=torch.int64),
            "regime_primary_valid": torch.zeros((3, 2), dtype=torch.float32),
            "regime_aux": torch.zeros((3, 2), dtype=torch.int64),
            "regime_aux_valid": torch.zeros((3, 2), dtype=torch.float32),
            "anchor_index": torch.arange(3, dtype=torch.int64),
            "anchor_physics": torch.zeros((3, 2, 4), dtype=torch.float32),
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            out = Path(temp_dir)
            metrics = evaluate_model(_Model(), [batch], _Bundle(), torch.device("cpu"), EvalConfig(skip_visuals=True), out)

            self.assertIn("gate_alignment", metrics)
            self.assertTrue(math.isnan(metrics["gate_alignment"]["nmi"]))
            self.assertTrue(math.isnan(metrics["gate_alignment"]["ari"]))
            self.assertEqual(metrics["gate_alignment"]["confusion_matrix"], [[0, 0, 0], [0, 0, 0], [0, 0, 0]])
            self.assertTrue((out / "gate_prob.npy").exists())
            self.assertEqual(np.load(out / "gate_prob.npy").shape, (3, 2, 4))


if __name__ == "__main__":
    unittest.main()
