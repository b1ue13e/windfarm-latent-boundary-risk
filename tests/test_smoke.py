from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader

from windfarm_moe.config import DataConfig, ModelConfig
from windfarm_moe.data import RegimeWindowDataset, load_cache_bundle
from windfarm_moe.model import RegimeAwareForecaster
from windfarm_moe.train import snapshot_model_state
from windfarm_moe.utils import save_json
from main import build_parser


class SmokeTests(unittest.TestCase):
    def test_common_data_args_accept_cache_root(self) -> None:
        args = build_parser().parse_args(["preprocess", "--cache-root", "artifacts/cache_strictmask"])

        self.assertEqual(args.cache_root, "artifacts/cache_strictmask")

    def test_data_config_supports_explicit_holdout_split(self) -> None:
        config = DataConfig(train_days=4, val_days=2, test_days=2, holdout_days=2, slots_per_day=10, hist_len=3, pred_len=2)

        self.assertEqual(config.effective_day_split(), (4, 2, 2, 2))
        self.assertEqual(config.split_bounds()["holdout"], (80, 100))

    def test_snapshot_model_state_is_immutable_after_parameter_update(self) -> None:
        model = torch.nn.Linear(2, 1)
        snapshot = snapshot_model_state(model)
        original_weight = snapshot["weight"].clone()
        with torch.no_grad():
            model.weight.add_(10.0)

        self.assertTrue(torch.equal(snapshot["weight"], original_weight))
        self.assertFalse(torch.equal(snapshot["weight"], model.state_dict()["weight"]))

    def _build_synthetic_cache(self, root: Path, dataset: str, num_features: int, num_nodes: int, num_experts: int) -> Path:
        cache_dir = root / dataset
        cache_dir.mkdir(parents=True, exist_ok=True)
        total_steps = 80
        features = np.random.randn(total_steps, num_nodes, num_features).astype(np.float32)
        feature_mask = np.ones_like(features, dtype=np.float32)
        target = np.random.rand(total_steps, num_nodes).astype(np.float32) * 1000.0
        target_mask = np.ones_like(target, dtype=np.float32)
        regime_primary = np.random.randint(0, min(num_experts, 3), size=(total_steps, num_nodes), dtype=np.int16)
        regime_primary_valid = np.ones_like(target_mask, dtype=np.float32)
        regime_aux = np.random.randint(0, 2, size=(total_steps, num_nodes), dtype=np.int16)
        regime_aux_valid = np.ones_like(target_mask, dtype=np.float32) if dataset == "wtb" else np.zeros_like(target_mask, dtype=np.float32)
        edge_index = np.full((total_steps, num_nodes, 3), -1, dtype=np.int16)
        edge_weight = np.zeros((total_steps, num_nodes, 3), dtype=np.float32)
        for t in range(total_steps):
            edge_index[t, :, 0] = np.roll(np.arange(num_nodes, dtype=np.int16), -1)
            edge_weight[t, :, 0] = 1.0
        physics = np.random.rand(total_steps, num_nodes, 4).astype(np.float32)
        coords = np.random.rand(num_nodes, 2).astype(np.float32)
        time_index = np.arange(total_steps, dtype=np.int64)
        node_ids = np.arange(1, num_nodes + 1, dtype=np.int32)

        np.save(cache_dir / "features.npy", features)
        np.save(cache_dir / "feature_mask.npy", feature_mask)
        np.save(cache_dir / "target.npy", target)
        np.save(cache_dir / "target_mask.npy", target_mask)
        np.save(cache_dir / "regime_primary.npy", regime_primary)
        np.save(cache_dir / "regime_primary_valid.npy", regime_primary_valid)
        np.save(cache_dir / "regime_aux.npy", regime_aux)
        np.save(cache_dir / "regime_aux_valid.npy", regime_aux_valid)
        np.save(cache_dir / "edge_index.npy", edge_index)
        np.save(cache_dir / "edge_weight.npy", edge_weight)
        np.save(cache_dir / "physics.npy", physics)
        np.save(cache_dir / "coords.npy", coords)
        np.save(cache_dir / "time_index.npy", time_index)
        np.save(cache_dir / "node_ids.npy", node_ids)
        save_json(
            cache_dir / "metadata.json",
            {
                "dataset": dataset,
                "feature_names": [f"f{i}" for i in range(num_features)],
                "physics_names": [f"p{i}" for i in range(4)],
                "primary_regime_names": ["r0", "r1", "r2", "transition"] if dataset == "wtb" else ["c", "s", "t"],
                "aux_regime_names": ["non_wake", "wake"] if dataset == "wtb" else [],
                "primary_num_classes": 3,
                "primary_class_weights": [1.0, 1.0, 1.0],
                "wake_expert_index": 3 if dataset == "wtb" else None,
                "wake_pos_weight": 1.0,
                "split_bounds": {"train": [0, 50], "val": [50, 65], "test": [65, 80]},
                "hist_len": 12,
                "pred_len": 6,
            },
        )
        return cache_dir

    def test_dataset_shapes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = self._build_synthetic_cache(Path(temp_dir), "wtb", num_features=11, num_nodes=4, num_experts=4)
            bundle = load_cache_bundle(cache_dir, mmap_mode=None)
            dataset = RegimeWindowDataset(bundle, "train", hist_len=12, pred_len=6)
            sample = dataset[0]
            self.assertEqual(sample["x_hist"].shape, (12, 4, 11))
            self.assertEqual(sample["target"].shape, (6, 4))
            self.assertEqual(sample["anchor_physics"].shape, (4, 4))

    def test_dataset_accepts_metadata_holdout_split(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = self._build_synthetic_cache(Path(temp_dir), "wtb", num_features=11, num_nodes=4, num_experts=4)
            metadata = {
                "dataset": "wtb",
                "feature_names": [f"f{i}" for i in range(11)],
                "physics_names": [f"p{i}" for i in range(4)],
                "primary_regime_names": ["r0", "r1", "r2", "transition"],
                "aux_regime_names": ["non_wake", "wake"],
                "primary_num_classes": 3,
                "primary_class_weights": [1.0, 1.0, 1.0],
                "wake_expert_index": 3,
                "wake_pos_weight": 1.0,
                "split_bounds": {"train": [0, 50], "val": [50, 65], "test": [65, 72], "holdout": [72, 80]},
                "hist_len": 3,
                "pred_len": 2,
            }
            save_json(cache_dir / "metadata.json", metadata)
            bundle = load_cache_bundle(cache_dir, mmap_mode=None)
            dataset = RegimeWindowDataset(bundle, "holdout", hist_len=3, pred_len=2)

            self.assertGreater(len(dataset), 0)

    def test_model_forward_and_backward_wtb(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = self._build_synthetic_cache(Path(temp_dir), "wtb", num_features=11, num_nodes=4, num_experts=4)
            bundle = load_cache_bundle(cache_dir, mmap_mode=None)
            dataset = RegimeWindowDataset(bundle, "train", hist_len=12, pred_len=6)
            batch = next(iter(DataLoader(dataset, batch_size=2)))
            for mode in [
                "moe_phys_full",
                "baseline_stgcn",
                "baseline_graph_wavenet",
                "baseline_patchtst",
                "baseline_gat_gru",
                "baseline_graph_transformer",
                "baseline_tcn",
                "moe_context_align",
                "moe_anchor_only",
            ]:
                model = RegimeAwareForecaster(
                    feature_dim=11,
                    pred_len=6,
                    mode=mode,
                    config=ModelConfig(hidden_dim=16, num_experts=4, primary_num_classes=3, gate_physics_dim=4),
                )
                pred, gate_prob, _ = model(
                    batch["x_hist"],
                    batch["edge_index_hist"],
                    batch["edge_weight_hist"],
                    batch["feature_mask_hist"],
                    batch["anchor_physics"],
                )
                loss = ((pred - batch["target"]) ** 2 * batch["target_mask"]).mean()
                loss.backward()
                self.assertEqual(pred.shape, (2, 6, 4))
                if mode in {"moe_phys_full", "moe_context_align", "moe_anchor_only"}:
                    self.assertEqual(gate_prob.shape[-1], 4)
                else:
                    self.assertIsNone(gate_prob)

    def test_model_forward_and_backward_era5(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = self._build_synthetic_cache(Path(temp_dir), "era5", num_features=8, num_nodes=9, num_experts=3)
            bundle = load_cache_bundle(cache_dir, mmap_mode=None)
            dataset = RegimeWindowDataset(bundle, "train", hist_len=12, pred_len=6)
            batch = next(iter(DataLoader(dataset, batch_size=2)))
            model = RegimeAwareForecaster(
                feature_dim=8,
                pred_len=6,
                mode="moe_phys_full",
                config=ModelConfig(hidden_dim=16, num_experts=3, primary_num_classes=3, gate_physics_dim=4),
            )
            pred, gate_prob, _ = model(
                batch["x_hist"],
                batch["edge_index_hist"],
                batch["edge_weight_hist"],
                batch["feature_mask_hist"],
                batch["anchor_physics"],
            )
            loss = ((pred - batch["target"]) ** 2 * batch["target_mask"]).mean()
            loss.backward()
            self.assertEqual(pred.shape, (2, 6, 9))
            self.assertEqual(gate_prob.shape[-1], 3)


if __name__ == "__main__":
    unittest.main()
