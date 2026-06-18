from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from main import build_parser
from windfarm_moe.decision import (
    _calibrate_scalar,
    _cost_metrics,
    _operational_window_rows,
    run_reserve_decision,
    run_reserve_decision_guard,
    select_default_wtb_runs,
)
from windfarm_moe.utils import load_json, save_json


class DecisionUtilityTests(unittest.TestCase):
    def test_calibrated_quantile_does_not_drop_when_shortage_penalty_increases(self) -> None:
        shortfall = np.array([[0.0, 2.0], [5.0, 8.0], [10.0, 20.0]], dtype=np.float64)
        valid = np.ones_like(shortfall, dtype=bool)
        quantiles = [0.5, 0.8, 0.95]

        _, low_penalty_q = _calibrate_scalar(shortfall, valid, ratio=2.0, dt=1.0, quantiles=quantiles)
        _, high_penalty_q = _calibrate_scalar(shortfall, valid, ratio=20.0, dt=1.0, quantiles=quantiles)

        self.assertGreaterEqual(high_penalty_q, low_penalty_q)

    def test_cost_metrics_use_reserve_and_shortage_penalty(self) -> None:
        shortfall = np.array([[5.0, 1.0]], dtype=np.float64)
        reserve = np.array([[3.0, 3.0]], dtype=np.float64)
        valid = np.ones_like(shortfall, dtype=bool)

        metrics = _cost_metrics(shortfall, valid, reserve, ratio=10.0, dt=0.5)

        self.assertAlmostEqual(metrics["total_cost"], 13.0)
        self.assertAlmostEqual(metrics["violation_rate"], 0.5)
        self.assertAlmostEqual(metrics["mean_reserve"], 3.0)

    def test_parser_accepts_reserve_decision_command(self) -> None:
        args = build_parser().parse_args(["reserve-decision", "--output-dir", "out", "--strata", "boundary,non_boundary"])

        self.assertEqual(args.command, "reserve-decision")
        self.assertEqual(args.cost_ratios, "2,5,10,20,50")
        self.assertEqual(args.strata, "boundary,non_boundary")

    def test_parser_accepts_reserve_decision_guard_command(self) -> None:
        args = build_parser().parse_args(["reserve-decision-guard", "--output-dir", "out"])

        self.assertEqual(args.command, "reserve-decision-guard")
        self.assertEqual(args.required_seeds, "201,202,203,204,205")

    def test_parser_accepts_operational_baselines_command(self) -> None:
        args = build_parser().parse_args(["operational-baselines", "--output-dir", "out", "--baselines", "persistence,dlinear"])

        self.assertEqual(args.command, "operational-baselines")
        self.assertEqual(args.baselines, "persistence,dlinear")

    def test_select_default_runs_rejects_missing_required_runs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            table = Path(temp_dir) / "runs.csv"
            pd.DataFrame(
                [
                    {
                        "model": "Graph WaveNet",
                        "seed": 101,
                        "experiment_group": "strong_baselines",
                        "run_dir": "missing",
                        "variant_key": "graph_wavenet",
                    }
                ]
            ).to_csv(table, index=False)

            with self.assertRaisesRegex(ValueError, "Missing default WTB reserve-decision run"):
                select_default_wtb_runs(table, root_dir=temp_dir)

    def test_select_default_runs_supports_strict_cache_run_table(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            table = root / "runs.csv"
            rows = []
            for model, variant in [
                ("Graph WaveNet", "graph_wavenet"),
                ("PatchTST", "patchtst"),
                ("Physics-Aligned MoE", "full"),
                ("MoE + L_bal + L_align + L_force", "bal_align_force"),
            ]:
                for seed in [201, 202, 203, 204, 205]:
                    run_dir = root / "artifacts" / "strictmask_runs" / f"{variant}_seed{seed}"
                    for split in ["val_metrics", "test_metrics"]:
                        metrics = run_dir / split
                        metrics.mkdir(parents=True, exist_ok=True)
                        np.save(metrics / "pred.npy", np.zeros((2, 1, 1), dtype=np.float32))
                        np.save(metrics / "target.npy", np.zeros((2, 1, 1), dtype=np.float32))
                        np.save(metrics / "mask.npy", np.ones((2, 1, 1), dtype=np.float32))
                        np.save(metrics / "regime_primary.npy", np.zeros((2, 1), dtype=np.int16))
                        np.save(metrics / "anchor_index.npy", np.arange(2, dtype=np.int64))
                    rows.append(
                        {
                            "model": model,
                            "seed": seed,
                            "experiment_group": "strong_baselines" if model in {"Graph WaveNet", "PatchTST"} else "ablation",
                            "variant_key": variant,
                            "run_dir": f"artifacts/strictmask_runs/{variant}_seed{seed}",
                            "overall_rmse": 1.0,
                        }
                    )
            pd.DataFrame(rows).to_csv(table, index=False)

            runs = select_default_wtb_runs(table, root_dir=root)

            self.assertEqual(len(runs), 20)
            self.assertEqual(runs[0].model, "Graph WaveNet")
            self.assertEqual(runs[-1].model, "Boundary-forced router")

    def test_run_reserve_decision_outputs_tables_and_marks_gate_policy(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            table = self._build_default_run_fixture(root)
            cache_dir = self._build_cache(root)
            output_dir = root / "decision"

            run_reserve_decision(
                run_table=table,
                output_dir=output_dir,
                root_dir=root,
                cache_dir=cache_dir,
                cost_ratios=[2.0, 10.0],
                main_ratio=10.0,
                quantiles=[0.5, 0.8, 0.95],
                strata=["boundary", "non_boundary", "late_period", "spatial_holdout"],
                bootstrap_samples=20,
                make_plots=False,
            )

            summary = pd.read_csv(output_dir / "reserve_decision_summary.csv")
            by_ratio = pd.read_csv(output_dir / "reserve_decision_by_ratio.csv")
            raw = pd.read_csv(output_dir / "reserve_decision_raw_runs.csv")
            gate_loss = pd.read_csv(output_dir / "reserve_decision_gate_loss.csv")
            bootstrap = pd.read_csv(output_dir / "reserve_decision_bootstrap.csv")
            system_baselines = pd.read_csv(output_dir / "reserve_decision_system_baselines.csv")
            sensitivity = pd.read_csv(output_dir / "reserve_decision_cost_ratio_sensitivity.csv")
            config = load_json(output_dir / "reserve_decision_config.json")

            self.assertTrue((output_dir / "reserve_decision_by_risk_bin.csv").exists())
            self.assertTrue((output_dir / "reserve_decision_bootstrap.csv").exists())
            self.assertTrue((output_dir / "reserve_decision_gate_loss.csv").exists())
            self.assertTrue((output_dir / "reserve_decision_operational_windows.csv").exists())
            self.assertTrue((output_dir / "reserve_decision_system_baselines.tex").exists())
            self.assertTrue((output_dir / "reserve_decision_cost_ratio_sensitivity.tex").exists())
            self.assertIn("Graph WaveNet", summary["model"].tolist())
            self.assertTrue(
                {
                    "Graph WaveNet/global-quantile reserve",
                    "Graph WaveNet/physical-bin reserve",
                    "Boundary-forced router/global",
                    "Boundary-forced router/gate-bin",
                }.issubset(set(system_baselines["baseline"]))
            )
            self.assertTrue({"full", "boundary"}.issubset(set(system_baselines["subset"])))
            self.assertTrue(
                {"Graph WaveNet/global-quantile reserve", "Graph WaveNet/physical-bin reserve"}.issubset(
                    set(sensitivity["baseline"])
                )
            )
            self.assertTrue({2.0, 10.0}.issubset(set(sensitivity["cost_ratio"].astype(float))))
            self.assertTrue({"boundary", "non_boundary", "late_period", "spatial_holdout"}.issubset(set(raw["subset"])))
            self.assertIn("not_applicable", by_ratio.loc[by_ratio["policy"] == "gate-bin", "status"].tolist())
            physics_gate = summary[(summary["model"] == "Physics-Aligned MoE") & (summary["policy"] == "gate-bin")]
            self.assertFalse(physics_gate.empty)
            self.assertEqual(physics_gate.iloc[0]["status"], "applicable")
            for column in ["total_cost", "violation_rate", "reserve_energy", "shortage_energy"]:
                self.assertIn(column, gate_loss.columns)
            self.assertTrue({"gate_correct", "gate_wrong"}.issubset(set(gate_loss["gate_correctness"])))
            self.assertTrue((bootstrap["n_seeds"] == 5).all())
            self.assertTrue((bootstrap["n_seed_day_pairs"] >= 5).all())
            operational = pd.read_csv(output_dir / "reserve_decision_operational_windows.csv")
            self.assertIn("boundary_shortage_energy_mean", operational.columns)
            self.assertIn("boundary_shortage_energy_mean_delta_vs_model_global", operational.columns)
            self.assertIn("subset_operational_value", operational.columns)
            self.assertIn("gate_value_window", operational.columns)
            self.assertIn("gate_operational_value", operational.columns)
            self.assertTrue({"full", "boundary", "non_boundary"}.issubset(set(operational["subset"])))
            self.assertEqual(config["dataset"], "wtb")
            self.assertEqual(config["strata"], ["boundary", "non_boundary", "late_period", "spatial_holdout"])

            guard_dir = run_reserve_decision_guard(
                decision_dir=output_dir,
                output_dir=root / "decision_guard",
                min_bootstrap_rows=9,
                min_seed_day_pairs=5,
            )
            guard = load_json(guard_dir / "reserve_decision_guard.json")
            self.assertEqual(guard["status"], "blocked_reserve_decision_evidence")
            self.assertTrue(guard["checks"]["selected_runs_cover_required_5_seeds"])
            self.assertTrue(guard["checks"]["paired_bootstrap_uses_seed_day_pairs"])
            self.assertTrue(guard["checks"]["summary_has_total_cost_violation_reserve_and_shortage_energy"])
            self.assertTrue(guard["checks"]["gate_correctness_operational_loss_present"])
            self.assertTrue(guard["checks"]["system_reserve_baselines_present"])
            self.assertTrue(guard["checks"]["graph_wavenet_reserve_cost_ratio_sensitivity_present"])
            self.assertFalse(guard["checks"]["operational_window_cost_violation_reserve_and_boundary_shortage_present"])
            self.assertFalse(guard["checks"]["gate_boundary_operational_gain_present"])
            self.assertIn("gate_boundary_operational_gain_present", guard["checks"])

    def test_operational_window_labels_boundary_gain_separately_from_risk_tradeoff(self) -> None:
        by_ratio = pd.DataFrame(
            [
                {
                    "subset": "boundary",
                    "cost_ratio": 10.0,
                    "model": "Boundary-forced router",
                    "policy": "global",
                    "status": "applicable",
                    "total_cost_mean": 100.0,
                    "violation_rate_mean": 0.10,
                    "reserve_energy_mean": 50.0,
                    "shortage_energy_mean": 5.0,
                },
                {
                    "subset": "boundary",
                    "cost_ratio": 10.0,
                    "model": "Boundary-forced router",
                    "policy": "gate-bin",
                    "status": "applicable",
                    "total_cost_mean": 90.0,
                    "violation_rate_mean": 0.08,
                    "reserve_energy_mean": 55.0,
                    "shortage_energy_mean": 4.0,
                },
                {
                    "subset": "non_boundary",
                    "cost_ratio": 10.0,
                    "model": "Boundary-forced router",
                    "policy": "global",
                    "status": "applicable",
                    "total_cost_mean": 200.0,
                    "violation_rate_mean": 0.05,
                    "reserve_energy_mean": 150.0,
                    "shortage_energy_mean": 3.0,
                },
                {
                    "subset": "non_boundary",
                    "cost_ratio": 10.0,
                    "model": "Boundary-forced router",
                    "policy": "gate-bin",
                    "status": "applicable",
                    "total_cost_mean": 190.0,
                    "violation_rate_mean": 0.07,
                    "reserve_energy_mean": 140.0,
                    "shortage_energy_mean": 4.0,
                },
            ]
        )

        operational = _operational_window_rows(by_ratio, main_ratio=10.0)
        boundary_gate = operational[
            operational["subset"].eq("boundary") & operational["policy"].eq("gate-bin")
        ].iloc[0]
        non_boundary_gate = operational[
            operational["subset"].eq("non_boundary") & operational["policy"].eq("gate-bin")
        ].iloc[0]

        self.assertEqual(boundary_gate["gate_operational_value"], "boundary_only_operational_gain")
        self.assertEqual(non_boundary_gate["gate_operational_value"], "boundary_only_operational_gain")
        self.assertEqual(boundary_gate["subset_operational_value"], "operational_gain")
        self.assertEqual(non_boundary_gate["subset_operational_value"], "cost_reduction_with_risk_tradeoff")
        self.assertLess(boundary_gate["total_cost_mean_delta_vs_model_global"], 0.0)
        self.assertLess(boundary_gate["violation_rate_mean_delta_vs_model_global"], 0.0)
        self.assertLess(boundary_gate["boundary_shortage_energy_mean_delta_vs_model_global"], 0.0)
        self.assertLess(non_boundary_gate["total_cost_mean_delta_vs_model_global"], 0.0)
        self.assertGreater(non_boundary_gate["violation_rate_mean_delta_vs_model_global"], 0.0)
        self.assertGreater(non_boundary_gate["shortage_energy_mean_delta_vs_model_global"], 0.0)

    def test_reserve_decision_guard_blocks_missing_seed_day_bootstrap(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            decision = root / "decision"
            decision.mkdir()
            save_json(
                decision / "reserve_decision_config.json",
                {
                    "dataset": "wtb",
                    "main_ratio": 10.0,
                    "selected_runs": [
                        {"model": model, "seed": seed}
                        for model in ["Graph WaveNet", "PatchTST", "Physics-Aligned MoE", "Boundary-forced router"]
                        for seed in [201, 202, 203, 204, 205]
                    ],
                },
            )
            pd.DataFrame(
                [
                    {
                        "model": model,
                        "policy": policy,
                        "status": "applicable" if policy != "gate-bin" or model in {"Physics-Aligned MoE", "Boundary-forced router"} else "not_applicable",
                        "total_cost_mean": 1.0,
                        "violation_rate_mean": 0.1,
                        "reserve_energy_mean": 2.0,
                        "shortage_energy_mean": 3.0,
                    }
                    for model in ["Graph WaveNet", "PatchTST", "Physics-Aligned MoE", "Boundary-forced router"]
                    for policy in ["global", "physical-bin", "gate-bin"]
                ]
            ).to_csv(decision / "reserve_decision_summary.csv", index=False)
            raw_rows = []
            daily_rows = []
            for model in ["Graph WaveNet", "PatchTST", "Physics-Aligned MoE", "Boundary-forced router"]:
                for policy in ["global", "physical-bin", "gate-bin"]:
                    status = "applicable" if policy != "gate-bin" or model in {"Physics-Aligned MoE", "Boundary-forced router"} else "not_applicable"
                    raw_rows.append({"model": model, "policy": policy, "subset": "full", "cost_ratio": 10.0, "status": status})
                    if status == "applicable":
                        for seed in [201, 202, 203, 204, 205]:
                            daily_rows.append({"model": model, "policy": policy, "seed": seed, "day": 1, "cost_ratio": 10.0, "daily_cost": 1.0})
            pd.DataFrame(raw_rows).to_csv(decision / "reserve_decision_raw_runs.csv", index=False)
            pd.DataFrame(raw_rows).to_csv(decision / "reserve_decision_by_ratio.csv", index=False)
            pd.DataFrame(raw_rows).to_csv(decision / "reserve_decision_by_risk_bin.csv", index=False)
            pd.DataFrame(raw_rows).to_csv(decision / "reserve_decision_raw_bins.csv", index=False)
            pd.DataFrame(daily_rows).to_csv(decision / "reserve_decision_daily_costs.csv", index=False)
            pd.DataFrame(
                [
                    {
                        "model": "Physics-Aligned MoE",
                        "policy": "gate-bin",
                        "seed": 201,
                        "subset": "full",
                        "cost_ratio": 10.0,
                        "gate_correctness": label,
                        "status": "applicable",
                        "total_cost": 1.0,
                        "violation_rate": 0.1,
                        "reserve_energy": 2.0,
                        "shortage_energy": 3.0,
                    }
                    for label in ["gate_correct", "gate_wrong"]
                ]
            ).to_csv(decision / "reserve_decision_gate_loss.csv", index=False)
            pd.DataFrame(
                [
                    {
                        "candidate": "Physics-Aligned MoE/gate-bin",
                        "baseline": "Graph WaveNet/global",
                        "status": "ok",
                        "n_seeds": 1,
                        "n_seed_day_pairs": 1,
                        "ci_low": -1.0,
                        "ci_high": 1.0,
                        "prob_candidate_lower": 0.5,
                    }
                ]
            ).to_csv(decision / "reserve_decision_bootstrap.csv", index=False)
            pd.DataFrame(
                [
                    {
                        "subset": subset,
                        "model": "Physics-Aligned MoE",
                        "policy": "gate-bin",
                        "status": "applicable",
                        "total_cost_mean": 1.0,
                        "violation_rate_mean": 0.1,
                        "reserve_energy_mean": 2.0,
                        "shortage_energy_mean": 3.0,
                        "boundary_shortage_energy_mean": 3.0 if subset == "boundary" else np.nan,
                        "total_cost_mean_delta_vs_model_global": -0.1,
                        "gate_value_window": "boundary_only_cost_reduction",
                    }
                    for subset in ["full", "boundary", "non_boundary"]
                ]
            ).to_csv(decision / "reserve_decision_operational_windows.csv", index=False)

            guard_dir = run_reserve_decision_guard(decision_dir=decision, output_dir=root / "guard")
            guard = load_json(guard_dir / "reserve_decision_guard.json")

            self.assertEqual(guard["status"], "blocked_reserve_decision_evidence")
            self.assertFalse(guard["checks"]["paired_bootstrap_required_candidates_present"])
            self.assertFalse(guard["checks"]["paired_bootstrap_uses_seed_day_pairs"])

    def test_run_reserve_decision_rejects_anchor_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            table = self._build_default_run_fixture(root, mismatch_one_run=True)
            cache_dir = self._build_cache(root)

            with self.assertRaisesRegex(ValueError, "anchor_index mismatch"):
                run_reserve_decision(
                    run_table=table,
                    output_dir=root / "decision",
                    root_dir=root,
                    cache_dir=cache_dir,
                    cost_ratios=[10.0],
                    quantiles=[0.5, 0.8],
                    bootstrap_samples=5,
                    make_plots=False,
                )

    def _build_cache(self, root: Path) -> Path:
        cache = root / "cache"
        cache.mkdir(parents=True)
        save_json(
            cache / "metadata.json",
            {
                "dataset": "wtb",
                "steps_per_hour": 6,
                "pred_len": 2,
                "wtb_thresholds": {"rated_wind": 10.5},
                "split_bounds": {"train": [0, 2], "val": [2, 5], "test": [5, 8]},
                "spatial_holdout_patch": {"holdout_node_indices": [1]},
            },
        )
        time_index = np.array([[1, 0], [1, 1], [2, 0], [2, 1], [3, 0], [3, 1], [4, 0], [4, 1]], dtype=np.int16)
        np.save(cache / "time_index.npy", time_index)
        physics = np.zeros((8, 2, 4), dtype=np.float32)
        physics[..., 0] = np.array(
            [[8.0, 10.4], [9.0, 11.0], [10.2, 12.0], [6.0, 8.0], [11.2, 10.6], [4.0, 7.0], [10.1, 10.8], [12.0, 5.0]],
            dtype=np.float32,
        )
        np.save(cache / "physics.npy", physics)
        regime = np.array([[0, 1], [1, 2], [1, 2], [0, 1], [2, 1], [1, 0], [1, 2], [2, 0]], dtype=np.int16)
        np.save(cache / "regime_primary.npy", regime)
        np.save(cache / "regime_primary_valid.npy", np.ones_like(regime, dtype=np.float32))
        return cache

    def _build_default_run_fixture(self, root: Path, mismatch_one_run: bool = False) -> Path:
        specs = [
            ("Graph WaveNet", "Graph WaveNet", "strong_baselines", "graph_wavenet", [201, 202, 203, 204, 205], ""),
            ("PatchTST", "PatchTST", "strong_baselines", "patchtst", [201, 202, 203, 204, 205], ""),
            (
                "Physics-Aligned MoE",
                "Physics-Aligned MoE",
                "ablation",
                "full",
                [201, 202, 203, 204, 205],
                "priority2_full_corrected_family",
            ),
            (
                "Boundary-forced router",
                "MoE + L_bal + L_align + L_force",
                "ablation",
                "bal_align_force",
                [201, 202, 203, 204, 205],
                "priority1_corrected_5seed",
            ),
        ]
        rows = []
        for _display, model, group, variant, seeds, marker in specs:
            for seed in seeds:
                parent = root / (marker or group)
                run_dir = parent / f"{variant}_seed{seed}"
                has_gate = model in {"Unconstrained MoE", "Physics-Aligned MoE", "MoE + L_bal + L_align + L_force"}
                mismatch = mismatch_one_run and model == "PatchTST" and seed == 201
                self._write_run(run_dir, seed=seed, has_gate=has_gate, anchor_offset=1 if mismatch else 0)
                rows.append(
                    {
                        "model": model,
                        "seed": seed,
                        "experiment_group": group,
                        "variant_key": variant,
                        "run_dir": run_dir.relative_to(root),
                        "overall_rmse": 100.0 + seed % 10,
                    }
                )
        table = root / "wtb_test_aggregated_runs.csv"
        pd.DataFrame(rows).to_csv(table, index=False)
        return table

    def _write_run(self, run_dir: Path, *, seed: int, has_gate: bool, anchor_offset: int = 0) -> None:
        for split, base in [("val_metrics", 0.0), ("test_metrics", 1.0)]:
            metrics = run_dir / split
            metrics.mkdir(parents=True, exist_ok=True)
            pred = np.array(
                [
                    [[10.0 + base, 12.0 + base], [11.0 + base, 13.0 + base]],
                    [[20.0 + base, 18.0 + base], [19.0 + base, 17.0 + base]],
                    [[30.0 + base, 32.0 + base], [29.0 + base, 31.0 + base]],
                ],
                dtype=np.float32,
            )
            target = pred - np.array(
                [
                    [[0.0, 2.0], [3.0, 0.0]],
                    [[5.0, 0.0], [0.0, 7.0]],
                    [[1.0, 8.0], [2.0, 9.0]],
                ],
                dtype=np.float32,
            )
            mask = np.ones_like(pred, dtype=np.float32)
            regime = np.array([[0, 1], [2, 1], [3, 2]], dtype=np.int16)
            anchor = np.array([2, 4, 6], dtype=np.int64) + anchor_offset
            np.save(metrics / "pred.npy", pred + (seed % 3) * 0.1)
            np.save(metrics / "target.npy", target)
            np.save(metrics / "mask.npy", mask)
            np.save(metrics / "regime_primary.npy", regime)
            np.save(metrics / "regime_primary_valid.npy", np.ones_like(regime, dtype=np.float32))
            np.save(metrics / "anchor_index.npy", anchor)
            if has_gate:
                gate = np.zeros((3, 2, 4), dtype=np.float32)
                pred_label = np.array([[0, 2], [2, 1], [2, 0]], dtype=np.int64)
                for row in range(pred_label.shape[0]):
                    for node in range(pred_label.shape[1]):
                        gate[row, node, pred_label[row, node]] = 0.9
                        gate[row, node, 3] = 0.1
                np.save(metrics / "gate_prob.npy", gate)


if __name__ == "__main__":
    unittest.main()
