from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from main import build_parser
from windfarm_moe.strict_baseline import run_strict_baseline_guard, write_strict_baseline_protocol
from windfarm_moe.utils import load_json, save_json


class StrictBaselineProtocolTests(unittest.TestCase):
    def _write_strict_cache(self, root: Path, cache_root: str = "cache") -> Path:
        cache_dir = root / cache_root / "wtb_245d"
        cache_dir.mkdir(parents=True, exist_ok=True)
        feature_mask = np.ones((12, 2, 2), dtype=np.float32)
        regime_valid = np.ones((12, 2), dtype=np.float32)
        np.save(cache_dir / "feature_mask.npy", feature_mask)
        np.save(cache_dir / "regime_primary_valid.npy", regime_valid)
        save_json(
            cache_dir / "metadata.json",
            {
                "dataset": "wtb",
                "feature_names": ["Wspd", "Pab_mean"],
                "split_bounds": {"train": [0, 144], "val": [144, 288], "test": [288, 432]},
                "train_days": 1,
                "val_days": 1,
                "test_days": 1,
                "hist_len": 3,
                "pred_len": 2,
                "strict_anchor_mask_patch": {"removed_regime_valid": 7},
            },
        )
        return cache_dir

    def _write_complete_run(self, run_dir: Path, variant_key: str, seed: int) -> None:
        run_dir.mkdir(parents=True, exist_ok=True)
        mode = {
            "graph_wavenet": "baseline_graph_wavenet",
            "patchtst": "baseline_patchtst",
            "itransformer": "baseline_itransformer",
            "tide": "baseline_tide",
        }[variant_key]
        save_json(
            run_dir / "training_summary.json",
            {
                "seed": seed,
                "variant_key": variant_key,
                "experiment_group": "strong_baselines",
                "model_mode": mode,
            },
        )
        metrics_dir = run_dir / "test_metrics"
        metrics_dir.mkdir(parents=True, exist_ok=True)
        save_json(metrics_dir / "metrics.json", {"overall": {"rmse": 1.2}, "switch_window": {"rmse": 1.4}})

    def test_parser_accepts_strict_baseline_protocol_command(self) -> None:
        args = build_parser().parse_args(
            [
                "strict-baseline-protocol",
                "--output-dir",
                "out",
                "--variant-keys",
                "graph_wavenet,patchtst,itransformer,tide",
                "--seeds",
                "201,202",
            ]
        )

        self.assertEqual(args.command, "strict-baseline-protocol")
        self.assertEqual(args.variant_keys, "graph_wavenet,patchtst,itransformer,tide")
        self.assertEqual(args.seeds, "201,202")

    def test_write_strict_baseline_protocol_outputs_jobs_and_commands(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = write_strict_baseline_protocol(
                output_dir=Path(temp_dir) / "protocol",
                root_dir=Path(temp_dir),
                cache_root="cache",
                suite_dir=Path(temp_dir) / "suite",
                train_days=1,
                val_days=1,
                test_days=1,
                hist_len=3,
                pred_len=2,
                variant_keys="graph_wavenet,patchtst,itransformer,tide",
                seeds="201,202",
            )

            protocol = load_json(output_dir / "strict_baseline_protocol.json")
            jobs = pd.read_csv(output_dir / "strict_baseline_jobs.csv")
            commands = (output_dir / "strict_baseline_commands.ps1").read_text(encoding="utf-8")

            self.assertEqual(protocol["status"], "protocol_only_not_executed")
            self.assertEqual(len(jobs), 8)
            self.assertIn("--groups strong_baselines", commands)
            self.assertIn("--variant-keys graph_wavenet,patchtst,itransformer,tide", commands)
            self.assertIn("--strong-baseline-seeds 201,202", commands)

    def test_strict_baseline_guard_is_ready_when_runs_are_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_strict_cache(root)
            protocol_dir = write_strict_baseline_protocol(
                output_dir=root / "protocol",
                root_dir=root,
                cache_root="cache",
                suite_dir=root / "suite",
                train_days=1,
                val_days=1,
                test_days=1,
                hist_len=3,
                pred_len=2,
                variant_keys="graph_wavenet",
                seeds="201",
            )

            guard_dir = run_strict_baseline_guard(
                protocol_dir=protocol_dir,
                output_dir=root / "guard",
                root_dir=root,
                cache_root="cache",
                suite_dir=root / "suite",
                train_days=1,
                val_days=1,
                test_days=1,
                hist_len=3,
                pred_len=2,
            )
            guard = load_json(guard_dir / "strict_baseline_guard.json")

            self.assertEqual(guard["status"], "ready_to_execute_training")
            self.assertEqual(guard["missing_runs"], 1)
            self.assertTrue(guard["checks"]["cache_strict_anchor_violations_zero"])

    def test_strict_baseline_guard_completes_when_all_runs_exist(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_strict_cache(root)
            protocol_dir = write_strict_baseline_protocol(
                output_dir=root / "protocol",
                root_dir=root,
                cache_root="cache",
                suite_dir=root / "suite",
                train_days=1,
                val_days=1,
                test_days=1,
                hist_len=3,
                pred_len=2,
                variant_keys="graph_wavenet,patchtst,itransformer,tide",
                seeds="201",
            )
            self._write_complete_run(root / "suite" / "wtb_graph_wavenet_seed201", "graph_wavenet", 201)
            self._write_complete_run(root / "suite" / "wtb_patchtst_seed201", "patchtst", 201)
            self._write_complete_run(root / "suite" / "wtb_itransformer_seed201", "itransformer", 201)
            self._write_complete_run(root / "suite" / "wtb_tide_seed201", "tide", 201)

            guard_dir = run_strict_baseline_guard(
                protocol_dir=protocol_dir,
                output_dir=root / "guard",
                root_dir=root,
                cache_root="cache",
                suite_dir=root / "suite",
                train_days=1,
                val_days=1,
                test_days=1,
                hist_len=3,
                pred_len=2,
            )
            guard = load_json(guard_dir / "strict_baseline_guard.json")

            self.assertEqual(guard["status"], "complete_ready_for_strict_baseline_comparison")
            self.assertEqual(guard["complete_runs"], 4)


if __name__ == "__main__":
    unittest.main()
