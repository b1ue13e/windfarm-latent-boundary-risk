from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from main import build_parser
from windfarm_moe.reviewer_stats import REVIEWER_STAT_REQUIRED_FILES, run_reviewer_stat_pack, run_reviewer_stat_pack_guard
from windfarm_moe.utils import load_json
from windfarm_moe.utils import save_json


class ReviewerStatPackTests(unittest.TestCase):
    def test_parser_accepts_reviewer_stat_pack_command(self) -> None:
        args = build_parser().parse_args(
            [
                "reviewer-stat-pack",
                "--output-dir",
                "out",
                "--run-table",
                "runs.csv",
                "--reference-model",
                "Aligned",
            ]
        )

        self.assertEqual(args.command, "reviewer-stat-pack")
        self.assertEqual(args.reference_model, "Aligned")

    def test_parser_accepts_reviewer_stat_pack_guard_command(self) -> None:
        args = build_parser().parse_args(
            [
                "reviewer-stat-pack-guard",
                "--pack-dir",
                "pack",
                "--output-dir",
                "guard",
                "--min-runs",
                "20",
                "--required-models",
                "A,B",
                "--required-seeds",
                "201,202",
            ]
        )

        self.assertEqual(args.command, "reviewer-stat-pack-guard")
        self.assertEqual(args.pack_dir, "pack")
        self.assertEqual(args.required_models, "A,B")
        self.assertEqual(args.required_seeds, "201,202")

    def test_reviewer_stat_pack_outputs_paired_and_failure_tables(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            cache = root / "cache"
            cache.mkdir()
            np.save(cache / "node_ids.npy", np.array([101, 102], dtype=np.int64))

            ref_run = root / "runs" / "ref_seed1"
            cmp_run = root / "runs" / "cmp_seed1"
            self._write_run(ref_run, pred_value=1.0, spike_value=5.0, include_gate=True)
            self._write_run(cmp_run, pred_value=3.0, spike_value=3.0, include_gate=False)

            run_table = root / "runs.csv"
            pd.DataFrame(
                [
                    {
                        "dataset": "wtb",
                        "model": "MoE + L_bal + L_align + L_force",
                        "seed": 1,
                        "variant_key": "bal_align_force",
                        "experiment_group": "ablation",
                        "run_dir": ref_run.relative_to(root),
                    },
                    {
                        "dataset": "wtb",
                        "model": "Graph WaveNet",
                        "seed": 1,
                        "variant_key": "graph_wavenet",
                        "experiment_group": "strong_baselines",
                        "run_dir": cmp_run.relative_to(root),
                    },
                ]
            ).to_csv(run_table, index=False)

            output_dir = run_reviewer_stat_pack(
                dataset="wtb",
                output_dir=root / "reviewer",
                root_dir=root,
                run_table=run_table,
                cache_dir=cache,
                bootstrap_samples=5,
                permutation_samples=5,
                max_paired_examples=100,
                top_k_failures=2,
                steps_per_hour=1,
                seed=3,
            )

            self.assertTrue((output_dir / "per_example_predictions.csv.gz").exists())
            manifest = pd.read_csv(output_dir / "per_example_manifest.csv")
            paired = pd.read_csv(output_dir / "paired_effects_summary.csv")
            multiplicity = pd.read_csv(output_dir / "paired_multiplicity_table.csv")
            failures = pd.read_csv(output_dir / "failure_cases_gate_correct_bad.csv")
            boundary_failures = pd.read_csv(output_dir / "failure_cases_boundary_gate_correct_bad.csv")
            efficiency = pd.read_csv(output_dir / "efficiency_fairness_table.csv")

            self.assertEqual(len(manifest), 2)
            self.assertFalse(paired.empty)
            self.assertIn("Graph WaveNet", paired["comparator_model"].tolist())
            self.assertIn("boundary_band", paired["slice"].tolist())
            self.assertIn("nmi", paired["metric"].tolist())
            self.assertIn("ari", paired["metric"].tolist())
            gate_rows = paired[paired["metric"].isin(["nmi", "ari"])]
            self.assertTrue((gate_rows["status"] == "not_applicable_missing_gate_metric").all())
            self.assertTrue(gate_rows["missing_gate_metric_side"].astype(str).str.contains("comparator").all())
            self.assertFalse(multiplicity.empty)
            self.assertIn("p_value_bh", multiplicity.columns)
            self.assertIn("Benjamini-Hochberg FDR", multiplicity["correction"].tolist())
            self.assertTrue(multiplicity["p_value_bh"].dropna().between(0.0, 1.0).all())
            self.assertFalse(failures.empty)
            self.assertTrue((failures["gate_correct"] == 1).all())
            self.assertFalse(boundary_failures.empty)
            self.assertTrue((boundary_failures["gate_correct"] == 1).all())
            self.assertTrue((boundary_failures["wspd_anchor"].sub(10.5).abs() <= 1.0).all())
            self.assertTrue((output_dir / "failure_cases_boundary_gate_correct_bad.png").exists())
            self.assertEqual(set(efficiency["model"]), {"MoE + L_bal + L_align + L_force", "Graph WaveNet"})
            self.assertTrue((output_dir / "reviewer_stat_pack_report.md").exists())
            report = (output_dir / "reviewer_stat_pack_report.md").read_text(encoding="utf-8")
            self.assertIn("Multiple comparisons", report)

    def test_reviewer_stat_pack_guard_marks_complete_pack_preliminary_until_min_runs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            pack = root / "pack"
            self._write_guard_pack(pack, n_runs=15)

            output_dir = run_reviewer_stat_pack_guard(pack_dir=pack, output_dir=root / "guard", min_runs=20)
            guard = load_json(output_dir / "reviewer_stat_pack_guard.json")

            self.assertEqual(guard["status"], "preliminary_available")
            self.assertTrue(guard["checks"]["required_files_exist"])
            self.assertTrue(guard["checks"]["paired_multiplicity_table_nonempty"])
            self.assertFalse(guard["checks"]["n_runs_at_least_min_runs"])

    def test_reviewer_stat_pack_guard_completes_when_min_runs_met(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            pack = root / "pack"
            self._write_guard_pack(pack, n_runs=20)

            output_dir = run_reviewer_stat_pack_guard(pack_dir=pack, output_dir=root / "guard", min_runs=20)
            guard = load_json(output_dir / "reviewer_stat_pack_guard.json")

            self.assertEqual(guard["status"], "complete_ready_for_reviewer_statistics")
            self.assertTrue(guard["checks"]["multiplicity_rows_at_least_min"])
            self.assertTrue((output_dir / "reviewer_stat_pack_file_status.csv").exists())

    def test_reviewer_stat_pack_guard_allows_empty_failure_case_tables(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            pack = root / "pack"
            self._write_guard_pack(pack, n_runs=20, n_failure_cases=0, n_boundary_failure_cases=0)

            output_dir = run_reviewer_stat_pack_guard(pack_dir=pack, output_dir=root / "guard", min_runs=20)
            guard = load_json(output_dir / "reviewer_stat_pack_guard.json")

            self.assertEqual(guard["status"], "complete_ready_for_reviewer_statistics")
            self.assertTrue(guard["checks"]["failure_cases_file_present"])
            self.assertTrue(guard["checks"]["boundary_failure_cases_file_present"])
            self.assertFalse(guard["checks"]["failure_cases_nonempty"])
            self.assertFalse(guard["checks"]["boundary_failure_cases_nonempty"])
            self.assertEqual(guard["n_failure_cases"], 0)

    def test_reviewer_stat_pack_guard_blocks_missing_required_model_seed_matrix(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            pack = root / "pack"
            self._write_guard_pack(pack, n_runs=20)

            output_dir = run_reviewer_stat_pack_guard(
                pack_dir=pack,
                output_dir=root / "guard",
                min_runs=20,
                required_models="A,B",
                required_seeds="201,202",
            )
            guard = load_json(output_dir / "reviewer_stat_pack_guard.json")

            self.assertEqual(guard["status"], "blocked_incomplete_reviewer_stat_pack")
            self.assertFalse(guard["checks"]["required_models_present"])
            self.assertFalse(guard["checks"]["required_seeds_present"])
            self.assertFalse(guard["checks"]["required_model_seed_matrix_complete"])
            self.assertIn("B", guard["missing_required_models"])

    def test_reviewer_stat_pack_guard_blocks_missing_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            pack = root / "pack"
            pack.mkdir()
            save_json(pack / "reviewer_stat_pack_config.json", {"n_runs": 20})

            output_dir = run_reviewer_stat_pack_guard(pack_dir=pack, output_dir=root / "guard", min_runs=20)
            guard = load_json(output_dir / "reviewer_stat_pack_guard.json")

            self.assertEqual(guard["status"], "blocked_missing_reviewer_stat_pack_files")
            self.assertFalse(guard["checks"]["required_files_exist"])

    def _write_run(self, run_dir: Path, pred_value: float, spike_value: float, include_gate: bool = True) -> None:
        metrics_dir = run_dir / "test_metrics"
        metrics_dir.mkdir(parents=True)
        windows = 4
        horizon = 2
        nodes = 2
        target = np.zeros((windows, horizon, nodes), dtype=np.float32)
        pred = np.full_like(target, pred_value)
        pred[1, :, 0] = spike_value
        mask = np.ones_like(target, dtype=np.float32)
        regime = np.array([[0, 1], [1, 2], [2, 1], [1, 0]], dtype=np.int16)
        valid = np.ones_like(regime, dtype=np.float32)
        anchor_physics = np.zeros((windows, nodes, 4), dtype=np.float32)
        anchor_physics[..., 0] = 10.5
        anchor_physics[..., 1] = 3.0
        gate = np.zeros((windows, nodes, 3), dtype=np.float32)
        for row in range(windows):
            for node in range(nodes):
                gate[row, node, regime[row, node]] = 1.0
        anchor_index = np.arange(10, 10 + windows, dtype=np.int64)

        np.save(metrics_dir / "pred.npy", pred)
        np.save(metrics_dir / "target.npy", target)
        np.save(metrics_dir / "mask.npy", mask)
        np.save(metrics_dir / "regime_primary.npy", regime)
        np.save(metrics_dir / "regime_primary_valid.npy", valid)
        np.save(metrics_dir / "anchor_physics.npy", anchor_physics)
        if include_gate:
            np.save(metrics_dir / "gate_prob.npy", gate)
        np.save(metrics_dir / "anchor_index.npy", anchor_index)
        metrics_payload = {
            "overall": {"mae": float(pred_value), "rmse": float(pred_value)},
            "switch_window": {"mae": float(pred_value), "rmse": float(pred_value)},
            "by_regime": {},
            "efficiency": {"eval_seconds": 2.0, "num_windows": windows, "windows_per_second": 2.0},
        }
        if include_gate:
            metrics_payload["gate_alignment"] = {
                "nmi": 0.8 if pred_value <= 1.0 else 0.2,
                "ari": 0.7 if pred_value <= 1.0 else 0.1,
            }
        save_json(
            metrics_dir / "metrics.json",
            metrics_payload,
        )
        save_json(
            run_dir / "training_summary.json",
            {
                "best_epoch": 1,
                "best_val_rmse": float(pred_value),
                "total_train_seconds": 10.0,
                "parameter_count": 123,
            },
        )

    def _write_guard_pack(
        self,
        pack: Path,
        n_runs: int,
        n_failure_cases: int = 1,
        n_boundary_failure_cases: int = 1,
    ) -> None:
        pack.mkdir(parents=True)
        save_json(
            pack / "reviewer_stat_pack_config.json",
            {
                "n_runs": n_runs,
                "n_per_example_run_summaries": 1,
                "n_paired_rows": 2,
                "n_paired_multiplicity_rows": 2,
                "n_failure_cases": n_failure_cases,
                "n_boundary_failure_cases": n_boundary_failure_cases,
            },
        )
        failure_cases = (
            pd.DataFrame([{"model": "A", "gate_correct": 1}])
            if n_failure_cases
            else pd.DataFrame(columns=["model", "gate_correct"])
        )
        boundary_failure_cases = (
            pd.DataFrame([{"model": "A", "gate_correct": 1}])
            if n_boundary_failure_cases
            else pd.DataFrame(columns=["model", "gate_correct"])
        )
        csv_payloads = {
            "reviewer_stat_pack_run_table.csv": pd.DataFrame([{"model": "A"}]),
            "per_example_manifest.csv": pd.DataFrame([{"model": "A", "rows": 10}]),
            "paired_effects_raw.csv": pd.DataFrame([{"slice": "overall"}]),
            "paired_effects_summary.csv": pd.DataFrame([{"slice": "overall"}]),
            "paired_multiplicity_table.csv": pd.DataFrame(
                [{"family": "test:overall:rmse", "raw_p_value": 0.1, "p_value_bh": 0.1}]
            ),
            "efficiency_fairness_table.csv": pd.DataFrame([{"model": "A", "parameter_count_mean": 1}]),
            "failure_cases_gate_correct_bad.csv": failure_cases,
            "failure_cases_boundary_gate_correct_bad.csv": boundary_failure_cases,
        }
        for name, frame in csv_payloads.items():
            frame.to_csv(pack / name, index=False)
        for name in REVIEWER_STAT_REQUIRED_FILES:
            path = pack / name
            if path.exists():
                continue
            if name.endswith(".gz"):
                path.write_bytes(b"not really gz but nonempty")
            elif name.endswith(".png"):
                path.write_bytes(b"png")
            elif name.endswith(".md"):
                path.write_text("# report\n", encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
