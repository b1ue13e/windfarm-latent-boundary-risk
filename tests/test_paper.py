from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

from main import build_parser
from windfarm_moe.config import EvalConfig, ModelConfig, TrainConfig
from windfarm_moe.data import load_cache_bundle
from windfarm_moe.paper import (
    WTB_ABLATION_ORDER,
    aggregate_runs,
    build_main_benchmark_table,
    build_routing_quality_table,
    build_wtb_sentinel_review,
    collect_suite_run_dirs,
    find_capacity_matched_dense_hidden_dim,
    run_paper_suite,
    run_paper_suite_parallel,
)
from windfarm_moe.utils import load_json, save_json


PAPER_PATH = Path(__file__).resolve().parents[1] / "paper_draft.md"


class PaperUtilityTests(unittest.TestCase):
    def _write_fake_wtb_run(self, run_dir: Path, seed: int, overall_rmse: float, switch_rmse: float, nmi: float) -> None:
        metrics_dir = run_dir / "test_metrics"
        metrics_dir.mkdir(parents=True, exist_ok=True)
        save_json(
            run_dir / "training_summary.json",
            {
                "variant_key": "bal_align_force",
                "seed": seed,
                "label": "MoE + L_bal + L_align + L_force",
                "best_epoch": 1,
                "best_val_rmse": overall_rmse,
                "history": [],
                "model_mode": "moe_balance_align",
            },
        )
        save_json(
            metrics_dir / "metrics.json",
            {
                "overall": {"mae": overall_rmse / 2.0, "rmse": overall_rmse},
                "switch_window": {"mae": switch_rmse / 2.0, "rmse": switch_rmse},
                "by_regime": {
                    "idle": {"mae": 1.0, "rmse": 2.0},
                    "mppt": {"mae": 1.0, "rmse": 2.0},
                    "pitch_control": {"mae": 1.0, "rmse": 2.0},
                    "transition": {"mae": 1.0, "rmse": 2.0},
                },
                "gate_alignment": {"nmi": nmi, "ari": nmi},
                "efficiency": {},
            },
        )

    def test_capacity_match_dense_hidden_dim(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir) / "wtb"
            cache_dir.mkdir(parents=True, exist_ok=True)
            features = np.random.randn(64, 4, 11).astype(np.float32)
            feature_mask = np.ones_like(features, dtype=np.float32)
            target = np.random.randn(64, 4).astype(np.float32)
            target_mask = np.ones_like(target, dtype=np.float32)
            regime_primary = np.zeros((64, 4), dtype=np.int16)
            regime_primary_valid = np.ones((64, 4), dtype=np.float32)
            regime_aux = np.zeros((64, 4), dtype=np.int16)
            regime_aux_valid = np.zeros((64, 4), dtype=np.float32)
            edge_index = np.zeros((64, 4, 2), dtype=np.int16)
            edge_weight = np.ones((64, 4, 2), dtype=np.float32)
            physics = np.random.randn(64, 4, 4).astype(np.float32)
            coords = np.random.randn(4, 2).astype(np.float32)
            time_index = np.arange(64, dtype=np.int64)
            node_ids = np.arange(1, 5, dtype=np.int32)
            for name, value in {
                "features": features,
                "feature_mask": feature_mask,
                "target": target,
                "target_mask": target_mask,
                "regime_primary": regime_primary,
                "regime_primary_valid": regime_primary_valid,
                "regime_aux": regime_aux,
                "regime_aux_valid": regime_aux_valid,
                "physics": physics,
                "physics_model": physics,
                "edge_index": edge_index,
                "edge_weight": edge_weight,
                "coords": coords,
                "time_index": time_index,
                "node_ids": node_ids,
            }.items():
                np.save(cache_dir / f"{name}.npy", value)
            save_json(
                cache_dir / "metadata.json",
                {
                    "dataset": "wtb",
                    "feature_names": [f"f{i}" for i in range(11)],
                    "physics_names": [f"p{i}" for i in range(4)],
                    "primary_regime_names": ["idle", "mppt", "pitch_control", "transition"],
                    "aux_regime_names": ["non_wake", "wake"],
                    "primary_num_classes": 3,
                    "primary_class_weights": [1.0, 1.0, 1.0],
                    "split_bounds": {"train": [0, 40], "val": [40, 52], "test": [52, 64]},
                    "hist_len": 12,
                    "pred_len": 6,
                },
            )
            bundle = load_cache_bundle(cache_dir, mmap_mode=None)
            match = find_capacity_matched_dense_hidden_dim(bundle, moe_hidden_dim=64, num_experts=4)
            self.assertLessEqual(match["relative_gap"], 0.05)

    def test_result_table_builders(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            wtb_df = pd.DataFrame(
                [
                    {
                        "model": "Capacity-Matched Dense Diffusion-GRU",
                        "overall_rmse": 10.0,
                        "overall_mae": 8.0,
                        "switch_rmse": 12.0,
                        "switch_mae": 9.0,
                        "nmi": np.nan,
                        "ari": np.nan,
                        "expert_usage_entropy": np.nan,
                        "expert_usage_variance": np.nan,
                    },
                    {
                        "model": "Unconstrained MoE",
                        "overall_rmse": 9.5,
                        "overall_mae": 7.5,
                        "switch_rmse": 11.5,
                        "switch_mae": 8.5,
                        "nmi": 0.0,
                        "ari": 0.0,
                        "expert_usage_entropy": 0.0,
                        "expert_usage_variance": 0.25,
                    },
                    {
                        "model": "Physics-Aligned MoE",
                        "overall_rmse": 8.5,
                        "overall_mae": 7.0,
                        "switch_rmse": 10.0,
                        "switch_mae": 8.0,
                        "nmi": 0.8,
                        "ari": 0.9,
                        "expert_usage_entropy": 1.1,
                        "expert_usage_variance": 0.03,
                    },
                ]
            )
            era5_df = pd.DataFrame(
                [
                    {
                        "model": "Capacity-Matched Dense Diffusion-GRU",
                        "overall_rmse": 1.0,
                        "overall_mae": 0.8,
                        "switch_rmse": 1.1,
                        "switch_mae": 0.9,
                        "nmi": np.nan,
                        "ari": np.nan,
                        "expert_usage_entropy": np.nan,
                        "expert_usage_variance": np.nan,
                    },
                    {
                        "model": "Unconstrained MoE",
                        "overall_rmse": 0.9,
                        "overall_mae": 0.7,
                        "switch_rmse": 1.0,
                        "switch_mae": 0.8,
                        "nmi": 0.05,
                        "ari": 0.02,
                        "expert_usage_entropy": 0.7,
                        "expert_usage_variance": 0.08,
                    },
                    {
                        "model": "Physics-Aligned MoE",
                        "overall_rmse": 0.8,
                        "overall_mae": 0.6,
                        "switch_rmse": 0.9,
                        "switch_mae": 0.7,
                        "nmi": 0.5,
                        "ari": 0.7,
                        "expert_usage_entropy": 0.6,
                        "expert_usage_variance": 0.09,
                    },
                ]
            )
            benchmark_path = build_main_benchmark_table(wtb_df, era5_df, output_dir / "table_main_benchmark.csv")
            routing_path = build_routing_quality_table(wtb_df, era5_df, output_dir / "table_routing_quality.csv")
            self.assertTrue(benchmark_path.exists())
            self.assertTrue(routing_path.exists())
            benchmark = pd.read_csv(benchmark_path)
            routing = pd.read_csv(routing_path)
            self.assertEqual(len(benchmark), 7)
            self.assertIn("WTB", benchmark["Panel"].tolist())
            self.assertIn("Boundary-forced router", benchmark["Model"].tolist())
            self.assertIn("Physics-Aligned MoE", routing["Model"].tolist())

    def test_wtb_main_benchmark_includes_strong_baselines(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            wtb_df = pd.DataFrame(
                [
                    {
                        "model": "Capacity-Matched Dense Diffusion-GRU",
                        "experiment_group": "main",
                        "overall_rmse": 260.0,
                        "overall_mae": 180.0,
                        "switch_rmse": 265.0,
                        "switch_mae": 185.0,
                    },
                    {
                        "model": "Unconstrained MoE",
                        "experiment_group": "main",
                        "overall_rmse": 258.0,
                        "overall_mae": 181.0,
                        "switch_rmse": 261.0,
                        "switch_mae": 183.0,
                    },
                    {
                        "model": "Physics-Aligned MoE",
                        "experiment_group": "ablation",
                        "overall_rmse": 256.0,
                        "overall_mae": 178.0,
                        "switch_rmse": 260.0,
                        "switch_mae": 179.0,
                    },
                    {
                        "model": "Graph WaveNet",
                        "experiment_group": "strong_baselines",
                        "overall_rmse": 231.0,
                        "overall_mae": 168.0,
                        "switch_rmse": 236.0,
                        "switch_mae": 170.0,
                    },
                    {
                        "model": "GAT-GRU",
                        "experiment_group": "strong_baselines",
                        "overall_rmse": 245.0,
                        "overall_mae": 172.0,
                        "switch_rmse": 250.0,
                        "switch_mae": 175.0,
                    },
                    {
                        "model": "Graph Transformer",
                        "experiment_group": "strong_baselines",
                        "overall_rmse": 249.0,
                        "overall_mae": 176.0,
                        "switch_rmse": 253.0,
                        "switch_mae": 178.0,
                    },
                    {
                        "model": "PatchTST",
                        "experiment_group": "strong_baselines",
                        "overall_rmse": 264.0,
                        "overall_mae": 186.0,
                        "switch_rmse": 268.0,
                        "switch_mae": 186.0,
                    },
                    {
                        "model": "iTransformer",
                        "experiment_group": "strong_baselines",
                        "overall_rmse": 229.0,
                        "overall_mae": 166.0,
                        "switch_rmse": 233.0,
                        "switch_mae": 167.0,
                    },
                    {
                        "model": "TiDE",
                        "experiment_group": "strong_baselines",
                        "overall_rmse": 238.0,
                        "overall_mae": 171.0,
                        "switch_rmse": 242.0,
                        "switch_mae": 172.0,
                    },
                    {
                        "model": "MoE + L_bal + L_align + L_force",
                        "experiment_group": "ablation",
                        "overall_rmse": 270.0,
                        "overall_mae": 190.0,
                        "switch_rmse": 274.0,
                        "switch_mae": 190.0,
                    },
                ]
            )
            era5_df = pd.DataFrame(
                [
                    {
                        "model": "Capacity-Matched Dense Diffusion-GRU",
                        "experiment_group": "main",
                        "overall_rmse": 1.0,
                        "overall_mae": 0.8,
                        "switch_rmse": 1.1,
                        "switch_mae": 0.9,
                    }
                ]
            )

            benchmark_path = build_main_benchmark_table(wtb_df, era5_df, output_dir / "table_main_benchmark.csv")
            benchmark = pd.read_csv(benchmark_path)
            wtb_models = benchmark.loc[benchmark["Panel"] == "WTB", "Model"].tolist()

            self.assertEqual(
                wtb_models,
                [
                    "Graph WaveNet",
                    "Graph Transformer",
                    "GAT-GRU",
                    "Physics-Aligned MoE",
                    "PatchTST",
                    "iTransformer",
                    "TiDE",
                    "Capacity-Matched Dense Diffusion-GRU",
                    "Unconstrained MoE",
                    "Boundary-forced router",
                ],
            )

    def test_align_ablation_modes_do_not_enable_force(self) -> None:
        align_only = TrainConfig(mode="moe_align_only", align_weight=1.0, physics_force_weight=9.0)
        balance_align = TrainConfig(mode="moe_balance_align", align_weight=1.0, balance_weight=1.0, physics_force_weight=9.0)
        self.assertEqual(align_only.effective_loss_weights()["physics_force"], 0.0)
        self.assertEqual(balance_align.effective_loss_weights()["physics_force"], 0.0)

    def test_simple_router_controls_enable_force_without_aux_or_smooth(self) -> None:
        for mode in ["moe_context_align", "moe_anchor_only"]:
            weights = TrainConfig(
                mode=mode,
                align_weight=1.0,
                balance_weight=2.0,
                physics_force_weight=3.0,
                aux_weight=4.0,
                smooth_weight=5.0,
            ).effective_loss_weights()
            self.assertEqual(weights["align"], 1.0)
            self.assertEqual(weights["balance"], 2.0)
            self.assertEqual(weights["physics_force"], 3.0)
            self.assertEqual(weights["aux"], 0.0)
            self.assertEqual(weights["smooth"], 0.0)

    def test_bal_align_force_spec_enables_force_without_aux_or_smooth(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("windfarm_moe.paper._run_spec_sequence", return_value=[]) as run_sequence:
                run_paper_suite(
                    bundle=object(),
                    output_root=Path(temp_dir),
                    dataset="wtb",
                    seeds=[204],
                    base_model_config=ModelConfig(num_experts=4),
                    base_train_config=TrainConfig(),
                    eval_config=EvalConfig(),
                    groups=["ablation"],
                    variant_keys=["bal_align_force"],
                )

        specs = run_sequence.call_args.kwargs["specs"]
        self.assertEqual([spec["key"] for spec in specs], ["bal_align_force"])
        self.assertEqual(specs[0]["mode"], "moe_full_no_aux")
        self.assertGreater(specs[0]["train_overrides"]["physics_force_weight"], 0.0)
        self.assertEqual(specs[0]["train_overrides"]["aux_weight"], 0.0)
        self.assertEqual(specs[0]["train_overrides"]["smooth_weight"], 0.0)

    def test_suite_collection_maps_new_ablation_labels(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            suite_root = Path(temp_dir) / "wtb_suite"
            run_dir = suite_root / "ablation" / "wtb_align_seed201"
            run_dir.mkdir(parents=True, exist_ok=True)
            save_json(
                run_dir / "training_summary.json",
                {
                    "variant_key": "align",
                    "seed": 201,
                    "label": "MoE + L_align",
                },
            )
            collected = collect_suite_run_dirs(suite_root, "wtb")
            self.assertIn(("MoE + L_align", run_dir), collected)
            self.assertIn("MoE + L_align", WTB_ABLATION_ORDER)

    def test_suite_collection_maps_strong_baseline_labels(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            suite_root = Path(temp_dir) / "wtb_suite"
            run_dir = suite_root / "strong_baselines" / "wtb_stgcn_seed101"
            run_dir.mkdir(parents=True, exist_ok=True)
            save_json(
                run_dir / "training_summary.json",
                {
                    "variant_key": "stgcn",
                    "seed": 101,
                    "label": "STGCN",
                },
            )
            collected = collect_suite_run_dirs(suite_root, "wtb")
            self.assertIn(("STGCN", run_dir), collected)

    def test_aggregate_runs_prefers_path_group_for_main_runs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            suite_root = Path(temp_dir) / "wtb_suite"
            run_dir = suite_root / "main" / "wtb_dense_seed101"
            metrics_dir = run_dir / "test_metrics"
            metrics_dir.mkdir(parents=True, exist_ok=True)
            save_json(
                run_dir / "training_summary.json",
                {
                    "seed": 101,
                    "best_epoch": 1,
                    "best_val_rmse": 1.0,
                    "history": [{"epoch_seconds": 1.0}],
                    "model_mode": "baseline_dense",
                },
            )
            save_json(
                metrics_dir / "metrics.json",
                {
                    "overall": {"mae": 1.0, "rmse": 2.0},
                    "switch_window": {"mae": 1.1, "rmse": 2.1},
                    "by_regime": {
                        "idle": {"mae": 0.5, "rmse": 1.5},
                        "mppt": {"mae": 0.6, "rmse": 1.6},
                        "pitch_control": {"mae": 0.7, "rmse": 1.7},
                        "transition": {"mae": 0.8, "rmse": 1.8},
                    },
                    "efficiency": {},
                },
            )
            np.save(metrics_dir / "regime_primary.npy", np.zeros((4, 2), dtype=np.int16))
            np.save(metrics_dir / "mask.npy", np.ones((4, 2), dtype=np.float32))
            np.save(metrics_dir / "pred.npy", np.zeros((4, 2), dtype=np.float32))
            np.save(metrics_dir / "target.npy", np.zeros((4, 2), dtype=np.float32))

            aggregated = aggregate_runs(
                "wtb",
                [("Capacity-Matched Dense Diffusion-GRU", run_dir)],
                Path(temp_dir) / "tables",
            )
            self.assertEqual(str(aggregated.iloc[0]["experiment_group"]), "main")
            self.assertEqual(str(aggregated.iloc[0]["variant_key"]), "dense")

    def test_paper_batch_parser_accepts_variant_keys(self) -> None:
        args = build_parser().parse_args(
            [
                "paper-batch",
                "--output-dir",
                "out",
                "--variant-keys",
                "bal_align_force",
            ]
        )

        self.assertEqual(args.variant_keys, "bal_align_force")

    def test_manuscript_structure(self) -> None:
        text = PAPER_PATH.read_text(encoding="utf-8")

        self.assertIn(
            "SCADA-Anchored Regime-Aware Routing for Operational Reserve Diagnosis "
            "in Wind-Turbine Control-Boundary Forecasting",
            text,
        )
        self.assertIn("# Highlights {.unnumbered}", text)
        self.assertLess(text.index("# Nomenclature {.unnumbered}"), text.index("# Introduction"))
        self.assertLess(
            text.index("# AI Use Statement"),
            text.index("# References {.unnumbered}"),
        )
        self.assertLess(text.index("# Code and data availability"), text.index("# References {.unnumbered}"))
        for heading in [
            "# Physics-Informed Framework for Operational Boundary Identification",
            "## Integration of Physical Constraints into Model Optimization",
            "# Case Study Configuration and Operational Constraints",
            "## Techno-Economic Validation and Benchmarking Framework",
            "# Evidence and Operational Boundary Diagnosis",
        ]:
            self.assertIn(heading, text)

    def test_highlights_meet_length_limit(self) -> None:
        text = PAPER_PATH.read_text(encoding="utf-8")
        start = text.index("# Highlights {.unnumbered}")
        end = text.index("# Nomenclature {.unnumbered}")
        highlights = [
            line.removeprefix("- ").strip()
            for line in text[start:end].splitlines()
            if line.startswith("- ")
        ]

        self.assertEqual(len(highlights), 5)
        for highlight in highlights:
            self.assertLessEqual(len(highlight), 85, highlight)

    def test_paper_export_parser_accepts_multiple_suite_dirs(self) -> None:
        args = build_parser().parse_args(
            [
                "paper-export",
                "--output-dir",
                "out",
                "--wtb-suite-dir",
                "old_wtb",
                "--wtb-suite-dir",
                "new_wtb",
                "--era5-suite-dir",
                "era5_main",
            ]
        )

        self.assertEqual(args.wtb_suite_dir, ["old_wtb", "new_wtb"])
        self.assertEqual(args.era5_suite_dir, ["era5_main"])

    def test_summary_metrics_use_sample_standard_deviation(self) -> None:
        from windfarm_moe.paper import _summarize_metrics

        summary = _summarize_metrics(
            pd.DataFrame(
                [
                    {"model": "Boundary-forced router", "rmse": 228.6109},
                    {"model": "Boundary-forced router", "rmse": 243.6501},
                ]
            ),
            ["model"],
            ["rmse"],
        )

        self.assertAlmostEqual(float(summary.iloc[0]["rmse_std"]), 10.6343, places=3)
        self.assertIn("+/- 10.63", str(summary.iloc[0]["rmse_display"]))

    def test_run_paper_suite_default_keeps_all_ablation_variants(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("windfarm_moe.paper._run_spec_sequence", return_value=[]) as run_sequence:
                run_paper_suite(
                    bundle=object(),
                    output_root=Path(temp_dir),
                    dataset="wtb",
                    seeds=[201],
                    base_model_config=ModelConfig(num_experts=4),
                    base_train_config=TrainConfig(),
                    eval_config=EvalConfig(),
                    groups=["ablation"],
                )

        specs = run_sequence.call_args.kwargs["specs"]
        self.assertEqual(
            [spec["key"] for spec in specs],
            [
                "dense",
                "unconstrained",
                "bal",
                "align",
                "bal_align",
                "bal_align_force",
                "bal_align_force_smooth",
                "context_align_force",
                "anchor_only",
                "full",
            ],
        )

    def test_run_paper_suite_filters_single_ablation_variant(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("windfarm_moe.paper._run_spec_sequence", return_value=[]) as run_sequence:
                run_paper_suite(
                    bundle=object(),
                    output_root=Path(temp_dir),
                    dataset="wtb",
                    seeds=[201],
                    base_model_config=ModelConfig(num_experts=4),
                    base_train_config=TrainConfig(),
                    eval_config=EvalConfig(),
                    groups=["ablation"],
                    variant_keys=["bal_align_force"],
                )

        specs = run_sequence.call_args.kwargs["specs"]
        self.assertEqual([spec["key"] for spec in specs], ["bal_align_force"])

    def test_run_paper_suite_filters_multiple_ablation_variants(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("windfarm_moe.paper._run_spec_sequence", return_value=[]) as run_sequence:
                run_paper_suite(
                    bundle=object(),
                    output_root=Path(temp_dir),
                    dataset="wtb",
                    seeds=[201],
                    base_model_config=ModelConfig(num_experts=4),
                    base_train_config=TrainConfig(),
                    eval_config=EvalConfig(),
                    groups=["ablation"],
                    variant_keys=["align", "bal_align_force"],
                )

        specs = run_sequence.call_args.kwargs["specs"]
        self.assertEqual([spec["key"] for spec in specs], ["align", "bal_align_force"])

    def test_run_paper_suite_dispatches_strong_baselines(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("windfarm_moe.paper._run_spec_sequence", return_value=[]) as run_sequence:
                run_paper_suite(
                    bundle=object(),
                    output_root=Path(temp_dir),
                    dataset="wtb",
                    seeds=[101],
                    strong_baseline_seeds=[301],
                    base_model_config=ModelConfig(num_experts=4),
                    base_train_config=TrainConfig(),
                    eval_config=EvalConfig(),
                    groups=["strong_baselines"],
                    variant_keys=["graph_wavenet", "patchtst"],
                )

        self.assertEqual(run_sequence.call_args.kwargs["experiment_group"], "strong_baselines")
        self.assertEqual(run_sequence.call_args.kwargs["seeds"], [301])
        specs = run_sequence.call_args.kwargs["specs"]
        self.assertEqual([spec["key"] for spec in specs], ["graph_wavenet", "patchtst"])
        self.assertEqual([spec["mode"] for spec in specs], ["baseline_graph_wavenet", "baseline_patchtst"])

    def test_run_paper_suite_dispatches_additional_graph_baselines(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("windfarm_moe.paper._run_spec_sequence", return_value=[]) as run_sequence:
                run_paper_suite(
                    bundle=object(),
                    output_root=Path(temp_dir),
                    dataset="wtb",
                    seeds=[101],
                    strong_baseline_seeds=[301],
                    base_model_config=ModelConfig(num_experts=4),
                    base_train_config=TrainConfig(),
                    eval_config=EvalConfig(),
                    groups=["strong_baselines"],
                    variant_keys=["gat_gru", "graph_transformer"],
                )

        self.assertEqual(run_sequence.call_args.kwargs["experiment_group"], "strong_baselines")
        specs = run_sequence.call_args.kwargs["specs"]
        self.assertEqual([spec["key"] for spec in specs], ["graph_transformer", "gat_gru"])
        self.assertEqual([spec["mode"] for spec in specs], ["baseline_graph_transformer", "baseline_gat_gru"])

    def test_run_paper_suite_dispatches_recent_time_series_baselines(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("windfarm_moe.paper._run_spec_sequence", return_value=[]) as run_sequence:
                run_paper_suite(
                    bundle=object(),
                    output_root=Path(temp_dir),
                    dataset="wtb",
                    seeds=[101],
                    strong_baseline_seeds=[301],
                    base_model_config=ModelConfig(num_experts=4),
                    base_train_config=TrainConfig(),
                    eval_config=EvalConfig(),
                    groups=["strong_baselines"],
                    variant_keys=["itransformer", "tide"],
                )

        self.assertEqual(run_sequence.call_args.kwargs["experiment_group"], "strong_baselines")
        specs = run_sequence.call_args.kwargs["specs"]
        self.assertEqual([spec["key"] for spec in specs], ["itransformer", "tide"])
        self.assertEqual([spec["mode"] for spec in specs], ["baseline_itransformer", "baseline_tide"])

    def test_run_paper_suite_rejects_unknown_variant_key(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("windfarm_moe.paper._run_spec_sequence", return_value=[]) as run_sequence:
                with self.assertRaisesRegex(ValueError, "Unknown variant key\\(s\\) for ablation: missing_key"):
                    run_paper_suite(
                        bundle=object(),
                        output_root=Path(temp_dir),
                        dataset="wtb",
                        seeds=[201],
                        base_model_config=ModelConfig(num_experts=4),
                        base_train_config=TrainConfig(),
                        eval_config=EvalConfig(),
                        groups=["ablation"],
                        variant_keys=["missing_key"],
                    )

        run_sequence.assert_not_called()

    def test_run_paper_suite_parallel_rejects_unknown_variant_key_before_dispatch(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaisesRegex(ValueError, "Unknown variant key\\(s\\) for ablation: missing_key"):
                run_paper_suite_parallel(
                    cache_dir=Path(temp_dir),
                    output_root=Path(temp_dir) / "out",
                    dataset="wtb",
                    seeds=[201],
                    base_model_config=ModelConfig(num_experts=4),
                    base_train_config=TrainConfig(),
                    eval_config=EvalConfig(),
                    groups=["ablation"],
                    variant_keys=["missing_key"],
                    device_ids=[0, 1],
                    max_parallel=2,
                )

    def test_wtb_sentinel_review_marks_matching_reruns_passed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            reference_dir = root / "reference"
            sentinel_dir = root / "sentinel"
            self._write_fake_wtb_run(reference_dir / "ablation" / "wtb_bal_align_force_seed201", 201, 100.0, 110.0, 0.90)
            self._write_fake_wtb_run(sentinel_dir / "wtb_bal_align_force_seed201", 201, 102.0, 112.0, 0.87)

            output_path = build_wtb_sentinel_review(
                reference_suite_dir=reference_dir,
                sentinel_suite_dir=sentinel_dir,
                output_path=root / "review.json",
            )

            review = load_json(output_path)
            self.assertEqual(review["status"], "PASSED")
            self.assertTrue((root / "review.csv").exists())

    def test_wtb_sentinel_review_marks_large_drift_anomaly(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            reference_dir = root / "reference"
            sentinel_dir = root / "sentinel"
            self._write_fake_wtb_run(reference_dir / "ablation" / "wtb_bal_align_force_seed201", 201, 100.0, 110.0, 0.90)
            self._write_fake_wtb_run(sentinel_dir / "wtb_bal_align_force_seed201", 201, 110.0, 130.0, 0.80)

            output_path = build_wtb_sentinel_review(
                reference_suite_dir=reference_dir,
                sentinel_suite_dir=sentinel_dir,
                output_path=root / "review.json",
            )

            review = load_json(output_path)
            self.assertEqual(review["status"], "ANOMALY")
            self.assertIn("overall_rmse_delta", review["rows"][0]["reason"])


if __name__ == "__main__":
    unittest.main()
