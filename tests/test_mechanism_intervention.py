from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd
import torch

from main import build_parser
from windfarm_moe.config import ModelConfig
from windfarm_moe.mechanism_intervention import (
    _apply_intervention,
    build_wtb_intervention_specs,
    build_run_table_from_suite,
    run_checkpoint_replay_audit,
    run_mechanism_evidence_gate,
    run_mechanism_intervention_audit,
)
from windfarm_moe.utils import load_json, save_json
from windfarm_moe.model import RegimeAwareForecaster

class MechanismInterventionAuditTests(unittest.TestCase):
    def test_parser_accepts_mechanism_intervention_command(self) -> None:
        args = build_parser().parse_args(["mechanism-intervention", "--output-dir", "out"])

        self.assertEqual(args.command, "mechanism-intervention")
        self.assertEqual(args.cache_dir, "artifacts/cache/wtb_245d")

    def test_parser_accepts_checkpoint_replay_command(self) -> None:
        args = build_parser().parse_args(["checkpoint-replay", "--output-dir", "out"])

        self.assertEqual(args.command, "checkpoint-replay")
        self.assertEqual(args.batch_size, 512)

    def test_parser_accepts_mechanism_gate_command(self) -> None:
        args = build_parser().parse_args(["mechanism-gate", "--suite-dir", "suite", "--output-dir", "out"])

        self.assertEqual(args.command, "mechanism-gate")
        self.assertEqual(args.variant_keys, "bal_align_force")
        self.assertFalse(args.skip_intervention)

    def test_anchor_negative_controls_mutate_expected_physics_channels(self) -> None:
        specs = {
            spec.name: spec
            for spec in build_wtb_intervention_specs(
                feature_names=["Wspd", "Pab_mean", "Etmp", "Itmp"],
                physics_names=["Wspd", "Pab_mean", "wake_score", "Patv"],
                selected="anchor_boundary_wrong_threshold_shift,anchor_random_physics,anchor_wspd_only,anchor_pab_only,anchor_boundary_node_shuffle,anchor_boundary_global_shuffle",
            )
        }
        anchor = torch.arange(2 * 3 * 4, dtype=torch.float32).reshape(2, 3, 4)
        batch = {"anchor_physics": anchor}

        wrong_threshold = _apply_intervention(batch, specs["anchor_boundary_wrong_threshold_shift"])["anchor_physics"]
        self.assertTrue(torch.equal(wrong_threshold[..., :2], anchor[..., :2] + 1.0))
        self.assertTrue(torch.equal(wrong_threshold[..., 2:], anchor[..., 2:]))

        random_physics = _apply_intervention(batch, specs["anchor_random_physics"])["anchor_physics"]
        self.assertFalse(torch.equal(random_physics, anchor))
        self.assertTrue(torch.equal(torch.sort(random_physics.reshape(-1)).values, torch.sort(anchor.reshape(-1)).values))

        wspd_only = _apply_intervention(batch, specs["anchor_wspd_only"])["anchor_physics"]
        self.assertTrue(torch.equal(wspd_only[..., 0], anchor[..., 0]))
        self.assertTrue(torch.equal(wspd_only[..., 1:], torch.zeros_like(wspd_only[..., 1:])))

        pab_only = _apply_intervention(batch, specs["anchor_pab_only"])["anchor_physics"]
        self.assertTrue(torch.equal(pab_only[..., 1], anchor[..., 1]))
        self.assertTrue(torch.equal(pab_only[..., [0, 2, 3]], torch.zeros_like(pab_only[..., [0, 2, 3]])))

        node_shuffle = _apply_intervention(batch, specs["anchor_boundary_node_shuffle"])["anchor_physics"]
        self.assertFalse(torch.equal(node_shuffle[..., :2], anchor[..., :2]))
        self.assertTrue(torch.equal(torch.sort(node_shuffle[..., :2].reshape(-1)).values, torch.sort(anchor[..., :2].reshape(-1)).values))

        global_shuffle = _apply_intervention(batch, specs["anchor_boundary_global_shuffle"])["anchor_physics"]
        self.assertFalse(torch.equal(global_shuffle[..., :2], anchor[..., :2]))
        self.assertTrue(
            torch.equal(torch.sort(global_shuffle[..., :2].reshape(-1)).values, torch.sort(anchor[..., :2].reshape(-1)).values)
        )

    def test_build_run_table_from_suite_uses_requested_split_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            run_dir = root / "suite" / "wtb_bal_align_force_seed301"
            run_dir.mkdir(parents=True)
            self._write_min_training_summary(run_dir)
            self._write_min_metrics(run_dir / "test_metrics", rmse=111.0)
            self._write_min_metrics(run_dir / "holdout_metrics", rmse=222.0)

            output_path = build_run_table_from_suite(
                suite_dir=root / "suite",
                output_path=root / "run_table.csv",
                dataset="wtb",
                split="holdout",
                models="MoE + L_bal + L_align + L_force",
                variant_keys="bal_align_force",
                experiment_groups="ablation",
            )
            df = pd.read_csv(output_path)

            self.assertEqual(float(df.iloc[0]["overall_rmse"]), 222.0)

    def test_mechanism_intervention_replays_checkpoint(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            cache_dir = self._build_cache(root / "cache")
            run_dir = root / "runs" / "moe_seed1"
            self._write_checkpoint(run_dir, feature_dim=11, pred_len=2)
            table = root / "runs.csv"
            pd.DataFrame(
                [
                    {
                        "dataset": "wtb",
                        "model": "Physics-Aligned MoE",
                        "seed": 1,
                        "variant_key": "full",
                        "experiment_group": "main",
                        "run_dir": run_dir.relative_to(root),
                    }
                ]
            ).to_csv(table, index=False)

            output_dir = run_mechanism_intervention_audit(
                run_table=table,
                cache_dir=cache_dir,
                output_dir=root / "intervention",
                root_dir=root,
                models="Physics-Aligned MoE",
                interventions="actual,anchor_boundary_zero,history_boundary_zero",
                batch_size=4,
                bootstrap_samples=20,
                device="cpu",
            )

            raw = pd.read_csv(output_dir / "mechanism_intervention_raw.csv")
            summary = pd.read_csv(output_dir / "mechanism_intervention_summary.csv")
            effects = pd.read_csv(output_dir / "mechanism_intervention_effects.csv")

            self.assertEqual(set(raw["intervention"]), {"actual", "anchor_boundary_zero", "history_boundary_zero"})
            actual = raw[raw["intervention"] == "actual"].iloc[0]
            self.assertEqual(actual["replay_status"], "checkpoint_mismatch")
            self.assertFalse(summary.empty)
            self.assertFalse(effects.empty)
            self.assertIn("delta_pitch_control_rmse_mean", effects.columns)
            self.assertTrue((output_dir / "mechanism_intervention_report.md").exists())

    def test_checkpoint_replay_audit_outputs_gate_table(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            cache_dir = self._build_cache(root / "cache")
            run_dir = root / "runs" / "moe_seed1"
            self._write_checkpoint(run_dir, feature_dim=11, pred_len=2)
            table = root / "runs.csv"
            pd.DataFrame(
                [
                    {
                        "dataset": "wtb",
                        "model": "Physics-Aligned MoE",
                        "seed": 1,
                        "variant_key": "full",
                        "experiment_group": "main",
                        "run_dir": run_dir.relative_to(root),
                    }
                ]
            ).to_csv(table, index=False)

            output_dir = run_checkpoint_replay_audit(
                run_table=table,
                cache_dir=cache_dir,
                output_dir=root / "replay",
                root_dir=root,
                models="Physics-Aligned MoE",
                batch_size=4,
                device="cpu",
            )

            audit = pd.read_csv(output_dir / "checkpoint_replay_audit.csv")
            config_path = output_dir / "checkpoint_replay_config.json"

            self.assertEqual(audit.iloc[0]["replay_status"], "checkpoint_mismatch")
            self.assertTrue(config_path.exists())

    def test_checkpoint_replay_marks_missing_reference_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            cache_dir = self._build_cache(root / "cache")
            run_dir = root / "runs" / "moe_seed1"
            self._write_checkpoint(run_dir, feature_dim=11, pred_len=2, with_reference_metrics=False)
            table = root / "runs.csv"
            pd.DataFrame(
                [
                    {
                        "dataset": "wtb",
                        "model": "Physics-Aligned MoE",
                        "seed": 1,
                        "variant_key": "full",
                        "experiment_group": "main",
                        "run_dir": run_dir.relative_to(root),
                    }
                ]
            ).to_csv(table, index=False)

            output_dir = run_checkpoint_replay_audit(
                run_table=table,
                cache_dir=cache_dir,
                output_dir=root / "replay",
                root_dir=root,
                models="Physics-Aligned MoE",
                batch_size=4,
                device="cpu",
            )

            audit = pd.read_csv(output_dir / "checkpoint_replay_audit.csv")
            config = pd.read_json(output_dir / "checkpoint_replay_config.json", typ="series")
            report = (output_dir / "checkpoint_replay_report.md").read_text(encoding="utf-8")

            self.assertEqual(audit.iloc[0]["replay_status"], "missing_reference")
            self.assertEqual(int(config["n_mismatches"]), 0)
            self.assertEqual(int(config["n_missing_references"]), 1)
            self.assertIn("Missing reference metrics: 1", report)

    def test_mechanism_evidence_gate_blocks_on_checkpoint_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            cache_dir = self._build_cache(root / "cache")
            run_dir = root / "suite" / "wtb_bal_align_force_seed1"
            self._write_checkpoint(
                run_dir,
                feature_dim=11,
                pred_len=2,
                label="MoE + L_bal + L_align + L_force",
                variant_key="bal_align_force",
                experiment_group="ablation",
            )

            output_dir = run_mechanism_evidence_gate(
                suite_dir=root / "suite",
                cache_dir=cache_dir,
                output_dir=root / "gate",
                root_dir=root,
                models="MoE + L_bal + L_align + L_force",
                variant_keys="bal_align_force",
                experiment_groups="ablation",
                batch_size=4,
                bootstrap_samples=0,
                device="cpu",
            )

            config = load_json(output_dir / "mechanism_evidence_gate_config.json")
            report = (output_dir / "mechanism_evidence_gate_report.md").read_text(encoding="utf-8")

            self.assertEqual(config["gate_status"], "checkpoint_mismatch")
            self.assertEqual(config["n_mismatches"], 1)
            self.assertIsNone(config["mechanism_intervention_dir"])
            self.assertFalse((output_dir / "mechanism_intervention").exists())
            self.assertIn("was not generated", report)

    def test_mechanism_evidence_gate_handles_empty_suite(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            cache_dir = self._build_cache(root / "cache")
            (root / "suite").mkdir()

            output_dir = run_mechanism_evidence_gate(
                suite_dir=root / "suite",
                cache_dir=cache_dir,
                output_dir=root / "gate",
                root_dir=root,
                batch_size=4,
                bootstrap_samples=0,
                device="cpu",
            )

            config = load_json(output_dir / "mechanism_evidence_gate_config.json")
            run_table = pd.read_csv(output_dir / "mechanism_gate_run_table.csv")
            replay_audit = pd.read_csv(output_dir / "checkpoint_replay" / "checkpoint_replay_audit.csv")

            self.assertEqual(config["gate_status"], "no_audited_runs")
            self.assertEqual(config["n_audited_runs"], 0)
            self.assertTrue(run_table.empty)
            self.assertTrue(replay_audit.empty)
            self.assertFalse((output_dir / "mechanism_intervention").exists())

    def test_mechanism_evidence_gate_runs_intervention_after_replay_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            cache_dir = self._build_cache(root / "cache")
            run_dir = root / "suite" / "wtb_bal_align_force_seed1"
            self._write_checkpoint(
                run_dir,
                feature_dim=11,
                pred_len=2,
                with_reference_metrics=False,
                label="MoE + L_bal + L_align + L_force",
                variant_key="bal_align_force",
                experiment_group="ablation",
            )
            table = root / "runs.csv"
            pd.DataFrame(
                [
                    {
                        "dataset": "wtb",
                        "model": "MoE + L_bal + L_align + L_force",
                        "seed": 1,
                        "variant_key": "bal_align_force",
                        "experiment_group": "ablation",
                        "run_dir": run_dir.relative_to(root),
                    }
                ]
            ).to_csv(table, index=False)
            replay_source = run_mechanism_intervention_audit(
                run_table=table,
                cache_dir=cache_dir,
                output_dir=root / "reference_replay",
                root_dir=root,
                models="MoE + L_bal + L_align + L_force",
                interventions="actual",
                batch_size=4,
                bootstrap_samples=0,
                device="cpu",
            )
            actual = pd.read_csv(replay_source / "mechanism_intervention_raw.csv").iloc[0]
            self._write_reference_metrics_from_row(run_dir, actual)

            output_dir = run_mechanism_evidence_gate(
                suite_dir=root / "suite",
                cache_dir=cache_dir,
                output_dir=root / "gate",
                root_dir=root,
                models="MoE + L_bal + L_align + L_force",
                variant_keys="bal_align_force",
                experiment_groups="ablation",
                interventions="actual,anchor_boundary_zero",
                batch_size=4,
                bootstrap_samples=0,
                device="cpu",
            )

            config = load_json(output_dir / "mechanism_evidence_gate_config.json")
            intervention_raw = output_dir / "mechanism_intervention" / "mechanism_intervention_raw.csv"

            self.assertEqual(config["gate_status"], "passed")
            self.assertEqual(config["n_matches"], 1)
            self.assertTrue(intervention_raw.exists())
            self.assertEqual(set(pd.read_csv(intervention_raw)["intervention"]), {"actual", "anchor_boundary_zero"})

    def _build_cache(self, cache_dir: Path) -> Path:
        cache_dir.mkdir(parents=True)
        rng = np.random.default_rng(1)
        total_steps = 32
        num_nodes = 3
        feature_dim = 11
        features = rng.normal(size=(total_steps, num_nodes, feature_dim)).astype(np.float32)
        feature_mask = np.ones_like(features, dtype=np.float32)
        target = rng.normal(size=(total_steps, num_nodes)).astype(np.float32)
        target_mask = np.ones_like(target, dtype=np.float32)
        regime = np.tile(np.array([[0, 1, 2]], dtype=np.int16), (total_steps, 1))
        regime_valid = np.ones_like(regime, dtype=np.float32)
        aux = np.zeros_like(regime, dtype=np.int16)
        aux_valid = np.zeros_like(regime, dtype=np.float32)
        physics = rng.normal(size=(total_steps, num_nodes, 4)).astype(np.float32)
        edge_index = np.full((total_steps, num_nodes, 1), -1, dtype=np.int16)
        edge_weight = np.zeros((total_steps, num_nodes, 1), dtype=np.float32)
        coords = rng.normal(size=(num_nodes, 2)).astype(np.float32)
        time_index = np.stack([np.arange(total_steps), np.zeros(total_steps)], axis=-1).astype(np.int64)
        node_ids = np.arange(1, num_nodes + 1, dtype=np.int32)
        arrays = {
            "features": features,
            "feature_mask": feature_mask,
            "target": target,
            "target_mask": target_mask,
            "regime_primary": regime,
            "regime_primary_valid": regime_valid,
            "regime_aux": aux,
            "regime_aux_valid": aux_valid,
            "physics": physics,
            "physics_model": physics,
            "edge_index": edge_index,
            "edge_weight": edge_weight,
            "coords": coords,
            "time_index": time_index,
            "node_ids": node_ids,
        }
        for name, value in arrays.items():
            np.save(cache_dir / f"{name}.npy", value)
        save_json(
            cache_dir / "metadata.json",
            {
                "dataset": "wtb",
                "feature_names": [
                    "Wspd",
                    "Wdir_sin",
                    "Wdir_cos",
                    "Ndir_sin",
                    "Ndir_cos",
                    "Etmp",
                    "Itmp",
                    "Pab_mean",
                    "Pab_std",
                    "Prtv",
                    "Patv_hist",
                ],
                "physics_names": ["Wspd", "Pab_mean", "wake_score", "Patv"],
                "primary_regime_names": ["idle", "mppt", "pitch_control"],
                "primary_num_classes": 3,
                "primary_class_weights": [1.0, 1.0, 1.0],
                "split_bounds": {"train": [0, 18], "val": [18, 24], "test": [24, 32]},
                "hist_len": 3,
                "pred_len": 2,
                "steps_per_hour": 1,
            },
        )
        return cache_dir

    def _write_checkpoint(
        self,
        run_dir: Path,
        feature_dim: int,
        pred_len: int,
        with_reference_metrics: bool = True,
        label: str = "Physics-Aligned MoE",
        variant_key: str = "full",
        experiment_group: str = "main",
    ) -> None:
        run_dir.mkdir(parents=True)
        if with_reference_metrics:
            metrics_dir = run_dir / "test_metrics"
            metrics_dir.mkdir(parents=True)
            save_json(
                metrics_dir / "metrics.json",
                {
                    "overall": {"mae": -1.0, "rmse": -1.0},
                    "switch_window": {"mae": -1.0, "rmse": -1.0},
                    "by_regime": {
                        "idle": {"mae": 0.0, "rmse": 0.0},
                        "mppt": {"mae": 0.0, "rmse": 0.0},
                        "pitch_control": {"mae": 0.0, "rmse": 0.0},
                    },
                    "gate_alignment": {"nmi": -1.0, "ari": -1.0},
                },
            )
        model_config = ModelConfig(hidden_dim=8, num_experts=4, dropout=0.0, tau=0.7, primary_num_classes=3, gate_physics_dim=4)
        model = RegimeAwareForecaster(feature_dim=feature_dim, pred_len=pred_len, mode="moe_phys_full", config=model_config)
        torch.save(
            {
                "model_state": model.state_dict(),
                "model_config": model_config.__dict__,
                "train_config": {"mode": "moe_phys_full"},
                "metadata": {},
            },
            run_dir / "best_model.pt",
        )
        save_json(
            run_dir / "training_summary.json",
            {
                "best_epoch": 1,
                "best_val_rmse": 1.0,
                "history": [{"epoch": 1, "epoch_seconds": 0.1}],
                "model_mode": "moe_phys_full",
                "parameter_count": 1,
                "label": label,
                "seed": 1,
                "variant_key": variant_key,
                "experiment_group": experiment_group,
            },
        )

    def _write_reference_metrics_from_row(self, run_dir: Path, row: pd.Series) -> None:
        metrics_dir = run_dir / "test_metrics"
        metrics_dir.mkdir(parents=True, exist_ok=True)
        save_json(
            metrics_dir / "metrics.json",
            {
                "overall": {"mae": float(row["overall_mae"]), "rmse": float(row["overall_rmse"])},
                "switch_window": {"mae": float(row["switch_mae"]), "rmse": float(row["switch_rmse"])},
                "by_regime": {
                    "idle": {"mae": 0.0, "rmse": 0.0},
                    "mppt": {"mae": 0.0, "rmse": 0.0},
                    "pitch_control": {"mae": 0.0, "rmse": 0.0},
                },
                "gate_alignment": {"nmi": float(row["nmi"]), "ari": float(row["ari"])},
            },
        )

    def _write_min_training_summary(self, run_dir: Path) -> None:
        save_json(
            run_dir / "training_summary.json",
            {
                "best_epoch": 1,
                "best_val_rmse": 10.0,
                "history": [],
                "total_train_seconds": 1.0,
                "model_mode": "moe_full_no_aux",
                "parameter_count": 1,
                "label": "MoE + L_bal + L_align + L_force",
                "seed": 301,
                "variant_key": "bal_align_force",
                "experiment_group": "ablation",
            },
        )

    def _write_min_metrics(self, metrics_dir: Path, rmse: float) -> None:
        metrics_dir.mkdir(parents=True)
        save_json(
            metrics_dir / "metrics.json",
            {
                "overall": {"mae": rmse / 2.0, "rmse": rmse},
                "switch_window": {"mae": rmse / 3.0, "rmse": rmse + 1.0},
                "by_regime": {
                    "idle": {"mae": 1.0, "rmse": 2.0},
                    "mppt": {"mae": 1.0, "rmse": 2.0},
                    "pitch_control": {"mae": 1.0, "rmse": 2.0},
                    "transition": {"mae": 1.0, "rmse": 2.0},
                },
                "gate_alignment": {"nmi": 0.5, "ari": 0.6},
                "efficiency": {"eval_seconds": 1.0, "num_windows": 2, "windows_per_second": 2.0},
            },
        )


if __name__ == "__main__":
    unittest.main()
