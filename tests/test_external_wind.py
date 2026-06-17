from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import gc
import hashlib
import json
import zipfile
from unittest.mock import patch

import numpy as np
import pandas as pd

from main import _default_num_experts, build_parser
from main import main
from windfarm_moe.data import load_cache_bundle
from windfarm_moe.external_wind import (
    ExternalWindConfig,
    _derive_turbine_id_from_source,
    _download_file,
    _prepare_long_frame,
    _read_external_coords,
    fetch_external_wind_sources,
    inspect_external_wind_sources,
    preprocess_external_wind,
    run_external_wind_guard,
    run_external_wind_portability_rescue,
    run_external_wind_source_guard,
    write_external_wind_protocol,
)
from windfarm_moe.utils import load_json, save_json


class ExternalWindTests(unittest.TestCase):
    def _write_farm(self, root: Path, farm: str, turbines: int = 2, periods: int = 80) -> None:
        farm_dir = root / "data" / "external_wind" / farm
        farm_dir.mkdir(parents=True, exist_ok=True)
        rows = []
        times = pd.date_range("2020-01-01", periods=periods, freq="10min")
        for tid in range(1, turbines + 1):
            for idx, timestamp in enumerate(times):
                wspd = 2.0 + (idx % 20) * 0.7
                pitch = 0.5 if wspd <= 10.5 else 5.0
                rows.append(
                    {
                        "timestamp": timestamp.isoformat(),
                        "turbine_id": f"T{tid}",
                        "wind_speed": wspd,
                        "wind_direction": 180.0,
                        "active_power": max(0.0, wspd * 10.0 - 20.0),
                        "pitch_angle": pitch,
                    }
                )
        pd.DataFrame(rows).to_csv(farm_dir / "scada.csv", index=False)
        pd.DataFrame(
            {
                "turbine_id": [f"T{idx}" for idx in range(1, turbines + 1)],
                "x": np.arange(turbines) * 500.0,
                "y": np.zeros(turbines),
            }
        ).to_csv(farm_dir / "turbine_static.csv", index=False)

    def _write_scada_file(self, farm_dir: Path, filename: str, start: str, periods: int = 20, turbines: int = 2) -> None:
        rows = []
        times = pd.date_range(start, periods=periods, freq="10min")
        for tid in range(1, turbines + 1):
            for idx, timestamp in enumerate(times):
                wspd = 3.0 + (idx % 12) * 0.6
                rows.append(
                    {
                        "timestamp": timestamp.isoformat(),
                        "turbine_id": f"T{tid}",
                        "wind_speed": wspd,
                        "wind_direction": 180.0,
                        "active_power": max(0.0, wspd * 12.0 - 20.0),
                        "pitch_angle": 0.5 if wspd <= 10.5 else 4.0,
                    }
                )
        pd.DataFrame(rows).to_csv(farm_dir / filename, index=False)

    def _write_external_guard_cache(self, root: Path, farm: str, split: str, target: str = "") -> Path:
        cache = root / "cache" / f"{farm}_{split}"
        cache.mkdir(parents=True)
        for name in ["features", "physics", "regime_primary", "regime_primary_valid", "regime_valid", "anchor_index", "node_ids"]:
            np.save(cache / f"{name}.npy", np.zeros((2, 2), dtype=np.float32))
        save_json(
            cache / "metadata.json",
            {
                "dataset": "external_wind",
                "farm": farm,
                "target_farm": target,
                "external_split": split,
                "license": "CC-BY-4.0",
                "source_url": f"https://zenodo.org/{farm}",
                "source_files": f"{farm}/scada.csv",
                "external_source_fingerprint": self._external_guard_fingerprint(farm, split, target),
                "split_farm_roles": {"train": [farm], "val": [farm], "test": [target or farm]},
            },
        )
        return cache

    def _external_guard_fingerprint(self, farm: str, split: str, target: str = "") -> dict:
        farms = [farm]
        if split == "leave-one-farm-out" and target:
            farms.append(target)
        files = [
            {
                "farm": item,
                "role": "test" if item == target and target else "train",
                "kind": "scada_csv",
                "path": f"{item}/scada.csv",
                "size": 128,
                "sha256": hashlib.sha256(item.encode("utf-8")).hexdigest(),
            }
            for item in farms
        ]
        canonical = json.dumps({"version": 1, "files": files}, sort_keys=True, separators=(",", ":"))
        return {
            "version": 1,
            "files": files,
            "signature": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
            "n_files": len(files),
            "n_scada_files": len(files),
            "n_scada_zip_members": 0,
        }

    def _write_external_guard_run(
        self,
        suite: Path,
        model: str,
        seed: int,
        farm: str,
        split: str,
        target: str = "",
        nmi: float = 0.8,
        ari: float = 0.7,
        include_expert_usage: bool = True,
    ) -> Path:
        run = suite / farm / split.replace("-", "_") / f"{model.replace(' ', '_')}_seed{seed}"
        metrics = run / "test_metrics"
        metrics.mkdir(parents=True)
        save_json(
            run / "training_summary.json",
            {
                "label": model,
                "seed": seed,
                "dataset": "external_wind",
                "farm": farm,
                "target_farm": target,
                "external_split": split,
            },
        )
        gate_alignment = {
            "nmi": nmi,
            "ari": ari,
            "expert_usage_entropy": 1.0,
        }
        if include_expert_usage:
            gate_alignment["expert_usage"] = [0.25, 0.50, 0.25]
        save_json(
            metrics / "metrics.json",
            {
                "overall": {"rmse": 1.0},
                "switch_window": {"rmse": 1.0},
                "gate_alignment": gate_alignment,
            },
        )
        np.save(metrics / "pred.npy", np.ones((2, 1, 1), dtype=np.float32))
        np.save(metrics / "target.npy", np.zeros((2, 1, 1), dtype=np.float32))
        np.save(metrics / "mask.npy", np.ones((2, 1, 1), dtype=np.float32))
        np.save(metrics / "regime_primary.npy", np.ones((2, 1), dtype=np.int16))
        np.save(metrics / "regime_primary_valid.npy", np.ones((2, 1), dtype=np.float32))
        np.save(metrics / "anchor_index.npy", np.arange(2, dtype=np.int64))
        physics = np.zeros((2, 1, 4), dtype=np.float32)
        physics[..., 0] = 10.5
        np.save(metrics / "anchor_physics.npy", physics)
        return run

    def test_parser_accepts_external_wind_commands(self) -> None:
        args = build_parser().parse_args(
            [
                "paper-batch",
                "--dataset",
                "external_wind",
                "--farm",
                "kelmarsh",
                "--external-split",
                "leave-one-farm-out",
                "--output-dir",
                "out",
            ]
        )

        self.assertEqual(args.dataset, "external_wind")
        self.assertEqual(args.external_split, "leave-one-farm-out")

    def test_external_wind_default_num_experts_includes_wake_expert(self) -> None:
        self.assertEqual(_default_num_experts("external_wind"), 4)

    def test_parser_accepts_external_wind_fetch(self) -> None:
        args = build_parser().parse_args(
            [
                "external-wind-fetch",
                "--output-dir",
                "out",
                "--farms",
                "kelmarsh",
                "--years",
                "2024",
            ]
        )

        self.assertEqual(args.command, "external-wind-fetch")
        self.assertEqual(args.years, "2024")

    def test_parser_accepts_external_wind_inspect(self) -> None:
        args = build_parser().parse_args(
            [
                "external-wind-inspect",
                "--output-dir",
                "out",
                "--farms",
                "kelmarsh",
                "--max-members-per-zip",
                "1",
            ]
        )

        self.assertEqual(args.command, "external-wind-inspect")
        self.assertEqual(args.max_members_per_zip, 1)

    def test_parser_accepts_external_wind_source_guard(self) -> None:
        args = build_parser().parse_args(
            [
                "external-wind-source-guard",
                "--output-dir",
                "out",
                "--manifest-path",
                "manifest.csv",
                "--min-files",
                "2",
                "--min-total-bytes",
                "100",
            ]
        )

        self.assertEqual(args.command, "external-wind-source-guard")
        self.assertEqual(args.manifest_path, "manifest.csv")
        self.assertEqual(args.min_files, 2)

    def test_parser_accepts_external_wind_portability_rescue(self) -> None:
        args = build_parser().parse_args(
            [
                "external-wind-portability-rescue",
                "--output-dir",
                "out",
                "--rated-wind-grid",
                "9.5,10.5",
                "--pitch-threshold-grid",
                "1.0,2.0",
            ]
        )

        self.assertEqual(args.command, "external-wind-portability-rescue")
        self.assertEqual(args.rated_wind_grid, "9.5,10.5")
        self.assertEqual(args.pitch_threshold_grid, "1.0,2.0")

    def test_external_source_guard_blocks_manifest_only_full_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manifest_dir = root / "manifest"
            manifest_dir.mkdir()
            manifest = manifest_dir / "external_wind_source_manifest.csv"
            pd.DataFrame(
                [
                    {
                        "farm": "kelmarsh",
                        "license": "CC-BY-4.0",
                        "key": "Kelmarsh_SCADA_2016.zip",
                        "size": 60,
                        "local_path": str(root / "data" / "kelmarsh.zip"),
                        "status": "manifest_only",
                        "local_exists": False,
                        "checksum_match": False,
                    },
                    {
                        "farm": "penmanshiel",
                        "license": "CC-BY-4.0",
                        "key": "Penmanshiel_SCADA_2016.zip",
                        "size": 60,
                        "local_path": str(root / "data" / "penmanshiel.zip"),
                        "status": "manifest_only",
                        "local_exists": False,
                        "checksum_match": False,
                    },
                ]
            ).to_csv(manifest, index=False)
            save_json(manifest_dir / "external_wind_source_manifest.json", {"license": "CC-BY-4.0"})

            out = run_external_wind_source_guard(
                output_dir=root / "guard",
                manifest_path=manifest,
                min_files=2,
                min_total_bytes=100,
            )
            guard = load_json(out / "external_wind_source_guard.json")
            status = pd.read_csv(out / "external_wind_source_status.csv")

            self.assertEqual(guard["status"], "blocked_external_source_incomplete")
            self.assertEqual(guard["claim_gate"], "blocked_not_citable")
            self.assertTrue(guard["checks"]["required_farms_present"])
            self.assertTrue(guard["checks"]["total_selected_bytes_meets_minimum"])
            self.assertFalse(guard["checks"]["all_selected_files_local_exists"])
            self.assertFalse(guard["checks"]["all_selected_files_checksum_match"])
            self.assertFalse(guard["checks"]["no_manifest_only_rows"])
            self.assertEqual(guard["n_manifest_only"], 2)
            self.assertEqual(len(status), 2)

    def test_external_source_guard_passes_complete_downloaded_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manifest_dir = root / "manifest"
            manifest_dir.mkdir()
            data_dir = root / "data"
            data_dir.mkdir()
            kelmarsh_file = data_dir / "kelmarsh.zip"
            penmanshiel_file = data_dir / "penmanshiel.zip"
            kelmarsh_file.write_bytes(b"kelmarsh")
            penmanshiel_file.write_bytes(b"penmanshiel")
            manifest = manifest_dir / "external_wind_source_manifest.csv"
            pd.DataFrame(
                [
                    {
                        "farm": "kelmarsh",
                        "license": "CC-BY-4.0",
                        "key": "Kelmarsh_SCADA_2016.zip",
                        "size": 60,
                        "local_path": str(kelmarsh_file),
                        "checksum": "md5:" + hashlib.md5(b"kelmarsh").hexdigest(),
                        "status": "downloaded",
                        "local_exists": True,
                        "checksum_match": True,
                    },
                    {
                        "farm": "penmanshiel",
                        "license": "CC-BY-4.0",
                        "key": "Penmanshiel_SCADA_2016.zip",
                        "size": 60,
                        "local_path": str(penmanshiel_file),
                        "checksum": "md5:" + hashlib.md5(b"penmanshiel").hexdigest(),
                        "status": "exists",
                        "local_exists": True,
                        "checksum_match": True,
                    },
                ]
            ).to_csv(manifest, index=False)
            save_json(manifest_dir / "external_wind_source_manifest.json", {"license": "CC-BY-4.0"})

            out = run_external_wind_source_guard(
                output_dir=root / "guard",
                manifest_path=manifest,
                min_files=2,
                min_total_bytes=100,
            )
            guard = load_json(out / "external_wind_source_guard.json")

            self.assertEqual(guard["status"], "complete_external_source_evidence")
            self.assertEqual(guard["claim_gate"], "within_wtb_only")
            self.assertTrue(all(guard["checks"].values()))
            self.assertEqual(guard["n_files"], 2)
            self.assertEqual(guard["total_selected_bytes"], 120)

    def test_external_source_guard_rechecks_local_files_from_manifest_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manifest_dir = root / "manifest"
            manifest_dir.mkdir()
            data_dir = root / "data"
            data_dir.mkdir()
            kelmarsh_file = data_dir / "kelmarsh.zip"
            penmanshiel_file = data_dir / "penmanshiel.zip"
            kelmarsh_file.write_bytes(b"kelmarsh")
            penmanshiel_file.write_bytes(b"penmanshiel")
            manifest = manifest_dir / "external_wind_source_manifest.csv"
            pd.DataFrame(
                [
                    {
                        "farm": "kelmarsh",
                        "license": "CC-BY-4.0",
                        "key": "Kelmarsh_SCADA_2016.zip",
                        "size": 60,
                        "local_path": str(kelmarsh_file),
                        "checksum": "md5:" + hashlib.md5(b"kelmarsh").hexdigest(),
                        "status": "manifest_only",
                        "local_exists": False,
                        "checksum_match": False,
                    },
                    {
                        "farm": "penmanshiel",
                        "license": "CC-BY-4.0",
                        "key": "Penmanshiel_SCADA_2016.zip",
                        "size": 60,
                        "local_path": str(penmanshiel_file),
                        "checksum": "md5:" + hashlib.md5(b"penmanshiel").hexdigest(),
                        "status": "manifest_only",
                        "local_exists": False,
                        "checksum_match": False,
                    },
                ]
            ).to_csv(manifest, index=False)
            save_json(manifest_dir / "external_wind_source_manifest.json", {"license": "CC-BY-4.0"})

            out = run_external_wind_source_guard(
                output_dir=root / "guard",
                manifest_path=manifest,
                min_files=2,
                min_total_bytes=100,
            )
            guard = load_json(out / "external_wind_source_guard.json")

            self.assertEqual(guard["status"], "complete_external_source_evidence")
            self.assertEqual(guard["n_local_exists"], 2)
            self.assertEqual(guard["n_checksum_match"], 2)
            self.assertEqual(guard["n_manifest_only"], 0)

    def test_external_source_guard_blocks_when_required_farm_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manifest_dir = root / "manifest"
            manifest_dir.mkdir()
            manifest = manifest_dir / "external_wind_source_manifest.csv"
            pd.DataFrame(
                [
                    {
                        "farm": "kelmarsh",
                        "license": "CC-BY-4.0",
                        "key": "Kelmarsh_SCADA_2016.zip",
                        "size": 120,
                        "local_path": str(root / "data" / "kelmarsh.zip"),
                        "status": "downloaded",
                        "local_exists": True,
                        "checksum_match": True,
                    },
                    {
                        "farm": "kelmarsh",
                        "license": "CC-BY-4.0",
                        "key": "Kelmarsh_SCADA_2017.zip",
                        "size": 120,
                        "local_path": str(root / "data" / "kelmarsh_2017.zip"),
                        "status": "downloaded",
                        "local_exists": True,
                        "checksum_match": True,
                    },
                ]
            ).to_csv(manifest, index=False)
            save_json(manifest_dir / "external_wind_source_manifest.json", {"license": "CC-BY-4.0"})

            out = run_external_wind_source_guard(
                output_dir=root / "guard",
                manifest_path=manifest,
                min_files=2,
                min_total_bytes=100,
            )
            guard = load_json(out / "external_wind_source_guard.json")

            self.assertEqual(guard["claim_gate"], "blocked_not_citable")
            self.assertFalse(guard["checks"]["required_farms_present"])

    def test_external_wind_paper_batch_rejects_default_three_seeds(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_farm(root, "kelmarsh")
            with self.assertRaisesRegex(ValueError, "requires explicit --seeds 201,202,203,204,205"):
                with patch(
                    "sys.argv",
                    [
                        "main.py",
                        "paper-batch",
                        "--dataset",
                        "external_wind",
                        "--root-dir",
                        str(root),
                        "--cache-root",
                        "cache",
                        "--external-source-dir",
                        str(root / "data" / "external_wind"),
                        "--output-dir",
                        str(root / "out"),
                        "--epochs",
                        "0",
                    ],
                ):
                    main()

    def test_external_wind_preprocess_writes_cache_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_farm(root, "kelmarsh")
            config = ExternalWindConfig(
                root_dir=root,
                source_dir=root / "data" / "external_wind",
                cache_root="cache",
                farm="kelmarsh",
                train_days=1,
                val_days=1,
                test_days=1,
                hist_len=3,
                pred_len=2,
            )

            cache_dir = preprocess_external_wind(config)
            bundle = load_cache_bundle(cache_dir)
            metadata = load_json(cache_dir / "metadata.json")

            self.assertEqual(metadata["dataset"], "external_wind")
            self.assertEqual(metadata["farm"], "kelmarsh")
            self.assertEqual(bundle.features.shape[-1], 11)
            self.assertEqual(bundle.physics.shape[-1], 4)
            self.assertTrue((bundle.regime_primary_valid >= 0).all())
            anchor_index = np.load(cache_dir / "anchor_index.npy")
            regime_valid = np.load(cache_dir / "regime_valid.npy")
            self.assertEqual(anchor_index.tolist(), list(range(bundle.features.shape[0])))
            self.assertTrue(np.array_equal(regime_valid, np.asarray(bundle.regime_primary_valid)))
            del bundle
            gc.collect()

    def test_external_wind_leave_one_farm_out_metadata_separates_source_and_target(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_farm(root, "kelmarsh", turbines=2, periods=40)
            self._write_farm(root, "penmanshiel", turbines=3, periods=50)
            config = ExternalWindConfig(
                root_dir=root,
                source_dir=root / "data" / "external_wind",
                cache_root="cache",
                farm="kelmarsh",
                target_farm="penmanshiel",
                split="leave-one-farm-out",
                hist_len=3,
                pred_len=2,
            )

            cache_dir = preprocess_external_wind(config)
            metadata = load_json(cache_dir / "metadata.json")
            feature_steps = int(np.load(cache_dir / "features.npy").shape[0])

            self.assertEqual(metadata["external_split"], "leave-one-farm-out")
            self.assertEqual(metadata["target_farm"], "penmanshiel")
            self.assertEqual(metadata["split_farm_roles"], {"train": ["kelmarsh"], "val": ["kelmarsh"], "test": ["penmanshiel"]})
            self.assertTrue(all(label.startswith("kelmarsh:") or label.startswith("penmanshiel:") for label in metadata["node_labels"]))
            self.assertEqual(metadata["split_bounds"]["train"][0], 0)
            self.assertLessEqual(metadata["split_bounds"]["train"][1], metadata["split_bounds"]["val"][0])
            self.assertEqual(metadata["split_bounds"]["val"][1], metadata["split_bounds"]["test"][0])
            self.assertEqual(metadata["split_bounds"]["test"][1], feature_steps)

    def test_external_wind_leave_one_farm_out_reuses_chronological_caches(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_farm(root, "kelmarsh", turbines=2, periods=320)
            self._write_farm(root, "penmanshiel", turbines=3, periods=180)
            common = {
                "root_dir": root,
                "source_dir": root / "data" / "external_wind",
                "cache_root": "cache",
                "hist_len": 3,
                "pred_len": 2,
                "train_days": 1,
                "val_days": 1,
                "test_days": 1,
            }
            preprocess_external_wind(ExternalWindConfig(**common, farm="kelmarsh", split="chronological"))
            preprocess_external_wind(ExternalWindConfig(**common, farm="penmanshiel", split="chronological"))
            cache_dir = preprocess_external_wind(
                ExternalWindConfig(
                    **common,
                    farm="kelmarsh",
                    target_farm="penmanshiel",
                    split="leave-one-farm-out",
                )
            )

            metadata = load_json(cache_dir / "metadata.json")
            features = np.load(cache_dir / "features.npy")

            self.assertEqual(features.shape[:2], (3 * 144, 5))
            self.assertEqual(metadata["split_bounds"], {"train": [0, 144], "val": [144, 288], "test": [288, 432]})
            self.assertEqual(metadata["split_farm_roles"], {"train": ["kelmarsh"], "val": ["kelmarsh"], "test": ["penmanshiel"]})
            self.assertTrue(metadata["external_source_fingerprint"]["signature"])
            self.assertTrue(all(label.startswith("kelmarsh:") for label in metadata["node_labels"][:2]))
            self.assertTrue(all(label.startswith("penmanshiel:") for label in metadata["node_labels"][2:]))

    def test_external_wind_preprocess_rebuilds_cache_when_metadata_schema_is_stale(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_farm(root, "kelmarsh")
            config = ExternalWindConfig(
                root_dir=root,
                source_dir=root / "data" / "external_wind",
                cache_root="cache",
                farm="kelmarsh",
                hist_len=3,
                pred_len=2,
            )
            cache_dir = preprocess_external_wind(config)
            metadata = load_json(cache_dir / "metadata.json")
            metadata.pop("split_farm_roles", None)
            save_json(cache_dir / "metadata.json", metadata)

            cache_dir = preprocess_external_wind(config)
            rebuilt = load_json(cache_dir / "metadata.json")

            self.assertEqual(rebuilt["split_farm_roles"], {"train": ["kelmarsh"], "val": ["kelmarsh"], "test": ["kelmarsh"]})

    def test_external_wind_preprocess_rebuilds_cache_when_source_files_change(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            farm_dir = root / "data" / "external_wind" / "kelmarsh"
            farm_dir.mkdir(parents=True, exist_ok=True)
            self._write_scada_file(farm_dir, "scada_part1.csv", "2020-01-01", periods=20)
            pd.DataFrame(
                {
                    "turbine_id": ["T1", "T2"],
                    "x": [0.0, 500.0],
                    "y": [0.0, 0.0],
                }
            ).to_csv(farm_dir / "turbine_static.csv", index=False)
            config = ExternalWindConfig(
                root_dir=root,
                source_dir=root / "data" / "external_wind",
                cache_root="cache",
                farm="kelmarsh",
                hist_len=3,
                pred_len=2,
            )
            cache_dir = preprocess_external_wind(config)
            first_metadata = load_json(cache_dir / "metadata.json")
            first_steps = int(np.load(cache_dir / "features.npy").shape[0])

            self._write_scada_file(farm_dir, "scada_part2.csv", "2020-01-01 03:20:00", periods=20)
            cache_dir = preprocess_external_wind(config)
            rebuilt_metadata = load_json(cache_dir / "metadata.json")
            rebuilt_steps = int(np.load(cache_dir / "features.npy").shape[0])

            self.assertNotEqual(
                first_metadata["external_source_fingerprint"]["signature"],
                rebuilt_metadata["external_source_fingerprint"]["signature"],
            )
            self.assertEqual(rebuilt_metadata["external_source_fingerprint"]["n_scada_files"], 2)
            self.assertGreater(rebuilt_steps, first_steps)

    def test_external_wind_fetch_writes_zenodo_manifest_without_download(self) -> None:
        fake_records = {
            "16807551": {
                "files": [
                    {
                        "key": "Kelmarsh_WT_static.csv",
                        "size": 10,
                        "checksum": "md5:abc",
                        "links": {"self": "https://example.test/static"},
                    },
                    {
                        "key": "Kelmarsh_SCADA_2024_5962.zip",
                        "size": 20,
                        "checksum": "md5:def",
                        "links": {"self": "https://example.test/scada2024"},
                    },
                    {
                        "key": "Kelmarsh_WT_dataSignalMapping.csv",
                        "size": 5,
                        "checksum": "md5:jkl",
                        "links": {"self": "https://example.test/mapping"},
                    },
                    {
                        "key": "Kelmarsh_PMU_2024.zip",
                        "size": 30,
                        "checksum": "md5:ghi",
                        "links": {"self": "https://example.test/pmu"},
                    },
                ]
            }
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            with patch("windfarm_moe.external_wind._zenodo_record", side_effect=lambda record_id: fake_records[record_id]):
                out = fetch_external_wind_sources(
                    output_dir=root / "sources",
                    source_dir=root / "data" / "external_wind",
                    farms="kelmarsh",
                    years="2024",
                    download=False,
                )

            manifest = pd.read_csv(out / "external_wind_source_manifest.csv")
            meta = load_json(out / "external_wind_source_manifest.json")

            self.assertEqual(set(manifest["key"]), {"Kelmarsh_WT_static.csv", "Kelmarsh_SCADA_2024_5962.zip"})
            self.assertTrue((manifest["status"] == "manifest_only").all())
            self.assertEqual(meta["n_files"], 2)
            self.assertEqual(meta["total_selected_bytes"], 30)
            self.assertEqual(meta["license"], "CC-BY-4.0")

            with patch("windfarm_moe.external_wind._zenodo_record", side_effect=lambda record_id: fake_records[record_id]):
                out_mapping = fetch_external_wind_sources(
                    output_dir=root / "sources_mapping",
                    source_dir=root / "data" / "external_wind",
                    farms="kelmarsh",
                    years="2024",
                    include_mapping=True,
                    download=False,
                )
            manifest_mapping = pd.read_csv(out_mapping / "external_wind_source_manifest.csv")
            self.assertIn("Kelmarsh_WT_dataSignalMapping.csv", manifest_mapping["key"].tolist())

            with patch("windfarm_moe.external_wind._zenodo_record", side_effect=lambda record_id: fake_records[record_id]):
                out_pattern = fetch_external_wind_sources(
                    output_dir=root / "sources_pattern",
                    source_dir=root / "data" / "external_wind",
                    farms="kelmarsh",
                    years="2024",
                    file_pattern="5962",
                    download=False,
                )
            manifest_pattern = pd.read_csv(out_pattern / "external_wind_source_manifest.csv")
            self.assertEqual(manifest_pattern["key"].tolist(), ["Kelmarsh_SCADA_2024_5962.zip"])

    def test_external_download_promotes_complete_part_file_without_network(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "archive.zip"
            target.with_suffix(target.suffix + ".part").write_bytes(b"complete")

            _download_file("https://example.test/archive.zip", target, expected_size=len(b"complete"))

            self.assertTrue(target.exists())
            self.assertEqual(target.read_bytes(), b"complete")
            self.assertFalse(target.with_suffix(target.suffix + ".part").exists())

    def test_external_wind_turbine_id_derivation_uses_zip_member_not_range_archive(self) -> None:
        self.assertEqual(
            _derive_turbine_id_from_source("Penmanshiel_SCADA_2024_WT_11-15_5966.zip"),
            "",
        )
        self.assertEqual(
            _derive_turbine_id_from_source("Penmanshiel_SCADA_2024_WT_11-15_5966.zip!WT12_scada.csv"),
            "WT12",
        )

    def test_external_static_csv_parses_alternative_title_and_latlon_to_meter_coords(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            farm_dir = Path(temp_dir)
            pd.DataFrame(
                [
                    {
                        "Wind Farm": "Kelmarsh",
                        "Title": "Kelmarsh 1",
                        "Alternative Title": "KWF1",
                        "Identity": "SEN 93420",
                        "Latitude": 52.400604,
                        "Longitude": -0.947133,
                    },
                    {
                        "Wind Farm": "Kelmarsh",
                        "Title": "Kelmarsh 2",
                        "Alternative Title": "KWF2",
                        "Identity": "SEN 93421",
                        "Latitude": 52.402551,
                        "Longitude": -0.949527,
                    },
                ]
            ).to_csv(farm_dir / "Kelmarsh_WT_static.csv", index=False)

            coords = _read_external_coords(farm_dir, [])

            self.assertEqual(coords["node_id"].tolist(), ["KWF1", "KWF2"])
            self.assertIn("latitude", coords.columns)
            self.assertIn("longitude", coords.columns)
            self.assertGreater(abs(float(coords.iloc[0]["x"]) - float(coords.iloc[1]["x"])), 100.0)
            self.assertGreater(abs(float(coords.iloc[0]["y"]) - float(coords.iloc[1]["y"])), 100.0)

    def test_external_scada_mapping_signal_names_parse_pitch_and_power(self) -> None:
        raw = pd.DataFrame(
            {
                "Timestamp": ["2024-01-01T00:00:00Z", "2024-01-01T00:10:00Z"],
                "Turbine": ["T01", "T01"],
                "Wind speed": [8.0, 12.0],
                "Wind direction": [180.0, 190.0],
                "Nacelle position": [181.0, 191.0],
                "Power": [1200.0, 1900.0],
                "Reactive power": [10.0, 20.0],
                "Ambient temperature": [5.0, 6.0],
                "Blade angle (pitch position) A": [0.5, 4.0],
                "Blade angle (pitch position) B": [0.7, 4.2],
                "Blade angle (pitch position) C": [0.9, 4.4],
            }
        )

        frame = _prepare_long_frame(raw)

        self.assertEqual(frame["node_id"].tolist(), ["T01", "T01"])
        self.assertAlmostEqual(float(frame.iloc[0]["Pab_mean"]), 0.7)
        self.assertAlmostEqual(float(frame.iloc[1]["Pab_mean"]), 4.2)
        self.assertEqual(frame["Patv"].tolist(), [1200.0, 1900.0])
        self.assertEqual(frame["Prtv"].tolist(), [10.0, 20.0])
        self.assertEqual(frame["Etmp"].tolist(), [5.0, 6.0])

    def test_external_cache_uses_wind_proxy_when_pitch_fully_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            farm_dir = root / "data" / "external_wind" / "penmanshiel"
            farm_dir.mkdir(parents=True)
            times = pd.date_range("2024-01-01", periods=80, freq="10min")
            rows = []
            for timestamp_index, timestamp in enumerate(times):
                for turbine in ["T11", "T12"]:
                    wspd = 4.0 + (timestamp_index % 16) * 0.6
                    rows.append(
                        {
                            "Date and time": timestamp.isoformat(),
                            "Turbine": turbine,
                            "Wind speed (m/s)": wspd,
                            "Wind direction (°)": 180.0,
                            "Nacelle position (°)": 181.0,
                            "Power (kW)": max(0.0, wspd * 100.0),
                            "Reactive power (kvar)": 0.0,
                            "Ambient temperature (converter) (°C)": 5.0,
                            "Blade angle (pitch position) A (°)": np.nan,
                            "Blade angle (pitch position) B (°)": np.nan,
                            "Blade angle (pitch position) C (°)": np.nan,
                        }
                    )
            pd.DataFrame(rows).to_csv(farm_dir / "Turbine_Data_Penmanshiel_11_2024.csv", index=False)
            pd.DataFrame(
                {
                    "Alternative Title": ["T11", "T12"],
                    "Latitude": [55.90, 55.91],
                    "Longitude": [-2.30, -2.31],
                }
            ).to_csv(farm_dir / "Penmanshiel_WT_static.csv", index=False)

            cache = preprocess_external_wind(
                ExternalWindConfig(
                    root_dir=root,
                    source_dir=root / "data" / "external_wind",
                    cache_root="cache",
                    farm="penmanshiel",
                    train_days=1,
                    val_days=1,
                    test_days=1,
                    hist_len=3,
                    pred_len=2,
                )
            )
            metadata = load_json(cache / "metadata.json")
            valid = np.load(cache / "regime_primary_valid.npy")

            self.assertTrue(metadata["pitch_proxy_used_for_regime"])
            self.assertEqual(metadata["pitch_observed_fraction"], 0.0)
            self.assertGreater(float(valid.mean()), 0.0)

    def test_external_portability_rescue_writes_diagnostics_and_downgrades_low_nmi(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            split_specs = [
                ("kelmarsh", "chronological", ""),
                ("penmanshiel", "chronological", ""),
                ("kelmarsh", "leave-one-farm-out", "penmanshiel"),
                ("penmanshiel", "leave-one-farm-out", "kelmarsh"),
            ]
            caches = []
            for farm, split, target in split_specs:
                cache = self._write_external_guard_cache(root, farm, split, target)
                feature_names = ["Wspd", "Patv_hist", "Pab_mean"]
                np.save(cache / "feature_mask.npy", np.ones((4, 2, len(feature_names)), dtype=np.float32))
                physics = np.zeros((4, 2, 4), dtype=np.float32)
                physics[..., 0] = np.array([[4.0, 10.2], [10.8, 12.0], [8.0, 11.2], [2.0, 10.5]], dtype=np.float32)
                physics[..., 1] = np.array([[0.5, 1.0], [4.0, 5.0], [0.5, 4.5], [0.0, 2.5]], dtype=np.float32)
                physics[..., 3] = physics[..., 0] * 100.0
                np.save(cache / "physics.npy", physics)
                regime = np.array([[1, 1], [2, 2], [1, 2], [0, 1]], dtype=np.int16)
                np.save(cache / "regime_primary.npy", regime)
                np.save(cache / "regime_primary_valid.npy", np.ones_like(regime, dtype=np.float32))
                metadata = load_json(cache / "metadata.json")
                metadata.update(
                    {
                        "num_nodes": 2,
                        "num_steps": 4,
                        "feature_names": feature_names,
                        "source_static_note": "6 Senvion MM92 turbines; 10-minute SCADA/static data from 2016 to end-2024.",
                        "target_static_note": "14 Senvion MM82 turbines; 10-minute SCADA/static data from 2016 to end-2024."
                        if target
                        else "",
                        "pitch_proxy_used_for_regime": farm == "penmanshiel",
                        "pitch_observed_fraction": 0.0 if farm == "penmanshiel" else 1.0,
                        "wtb_thresholds": {"cut_in_wind": 3.0, "rated_wind": 10.5, "pitch_threshold": 2.0},
                    }
                )
                save_json(cache / "metadata.json", metadata)
                caches.append(cache)

            suite = root / "runs"
            for farm, split, target in split_specs:
                run = self._write_external_guard_run(
                    suite,
                    model="Physics-Aligned MoE",
                    seed=201,
                    farm=farm,
                    split=split,
                    target=target,
                    nmi=0.2,
                    ari=0.1,
                )
                gate = np.zeros((2, 1, 3), dtype=np.float32)
                gate[..., 1] = 1.0
                np.save(run / "test_metrics" / "gate_prob.npy", gate)
                physics = np.zeros((2, 1, 4), dtype=np.float32)
                physics[..., 0] = [[10.2], [11.2]]
                physics[..., 1] = [[0.5], [4.0]]
                np.save(run / "test_metrics" / "anchor_physics.npy", physics)

            out = run_external_wind_portability_rescue(
                output_dir=root / "rescue",
                cache_dirs=",".join(str(path) for path in caches),
                suite_dir=suite,
                seeds="201",
                required_models="Physics-Aligned MoE",
                rated_wind_grid="10.0,10.5",
                pitch_threshold_grid="1.0,2.0",
            )
            summary = load_json(out / "rescue_summary.json")
            calibration = pd.read_csv(out / "threshold_calibration.csv")
            coverage = pd.read_csv(out / "sensor_field_coverage.csv")
            strata = pd.read_csv(out / "control_strategy_strata.csv")
            domain = pd.read_csv(out / "turbine_domain_alignment.csv")

            self.assertEqual(summary["claim_gate"], "within_wtb_external_diagnostics_only")
            self.assertFalse(summary["portable_wording_allowed"])
            self.assertIn("threshold_calibration.csv", summary["outputs"])
            self.assertEqual(len(calibration), 16)
            self.assertIn("boundary_cells", calibration.columns)
            self.assertIn("synthetic_pitch_proxy_use_rate", coverage.columns)
            self.assertGreater(float(coverage["effective_boundary_cells"].sum()), 0.0)
            self.assertTrue(coverage["pitch_proxy_used_for_regime"].astype(bool).any())
            self.assertIn("control_strategy", strata.columns)
            self.assertIn("target_to_source_rotor_ratio", domain.columns)

    def test_external_wind_inspect_reads_zip_member_headers(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            farm_dir = root / "data" / "external_wind" / "kelmarsh"
            farm_dir.mkdir(parents=True)
            csv_text = (
                "# Greenbyte export metadata\n"
                "# Date and time,Turbine,Wind speed,Power,Blade angle (pitch position) A\n"
                "2024-01-01T00:00:00Z,KWF1,8.0,1200,0.5\n"
            )
            with zipfile.ZipFile(farm_dir / "Kelmarsh_SCADA_2024_5962.zip", "w") as archive:
                archive.writestr("KWF1_scada.csv", csv_text)
                archive.writestr("Status_KWF1.csv", "Timestamp,Status\n2024-01-01T00:00:00Z,OK\n")

            out = inspect_external_wind_sources(
                source_dir=root / "data" / "external_wind",
                output_dir=root / "inspect",
                farms="kelmarsh",
                max_members_per_zip=5,
            )
            inspection = pd.read_csv(out / "external_wind_scada_inspection.csv")
            meta = load_json(out / "external_wind_scada_inspection.json")

            self.assertEqual(len(inspection), 1)
            self.assertEqual(inspection.iloc[0]["derived_turbine_id"], "KWF1")
            self.assertTrue(bool(inspection.iloc[0]["has_timestamp_candidate"]))
            self.assertTrue(bool(inspection.iloc[0]["has_wind_speed_candidate"]))
            self.assertTrue(bool(inspection.iloc[0]["has_power_candidate"]))
            self.assertTrue(bool(inspection.iloc[0]["has_pitch_candidate"]))
            self.assertIn("Wind speed", meta["columns_union"])

    def test_external_wind_protocol_splits_variant_groups_and_boundary_router(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            out = write_external_wind_protocol(
                output_dir=root / "protocol",
                root_dir="E:/paper3",
                source_dir="data/external_wind",
                cache_root="artifacts/cache_external_wind_custom",
                seeds="201,202",
                farms="kelmarsh",
                suite_dir="artifacts/external_wind_runs",
            )
            commands = (out / "external_wind_commands.ps1").read_text(encoding="utf-8")
            reviewer_commands = (out / "external_wind_reviewer_pack_commands.ps1").read_text(encoding="utf-8")
            protocol = load_json(out / "external_wind_protocol.json")

            self.assertIn("--groups main --variant-keys full", commands)
            self.assertNotIn("--groups main --variant-keys dense,unconstrained,full", commands)
            self.assertIn("--groups ablation --variant-keys bal_align_force", commands)
            self.assertIn("--groups strong_baselines --variant-keys graph_wavenet,patchtst", commands)
            self.assertIn("--root-dir E:/paper3", commands)
            self.assertIn("--cache-root artifacts/cache_external_wind_custom", commands)
            self.assertNotIn("--groups main,strong_baselines", commands)
            self.assertNotIn("--external-target-farm --cache-root", commands)
            self.assertIn("reviewer-stat-pack --dataset external_wind", reviewer_commands)
            self.assertIn("--max-per-example-rows 0", reviewer_commands)
            self.assertIn("external_wind_reviewer_stats", reviewer_commands)
            self.assertEqual(protocol["cache_root"], "artifacts/cache_external_wind_custom")
            self.assertIn("external_wind_reviewer_pack_commands.ps1", protocol["reviewer_pack_commands"])
            self.assertIn("MoE + L_bal + L_align + L_force", protocol["protocols"][0]["models"])
            self.assertEqual(protocol["protocols"][0]["main_variants"], ["full"])

    def test_external_guard_blocks_wtb_like_sources(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            cache = root / "cache"
            cache.mkdir()
            for name in ["features", "physics", "regime_primary", "regime_primary_valid", "regime_valid", "anchor_index", "node_ids"]:
                np.save(cache / f"{name}.npy", np.zeros((2, 2), dtype=np.float32))
            save_json(cache / "metadata.json", {"dataset": "external_wind", "farm": "kelmarsh", "source_url": "wtbdata_245days.csv"})

            out = run_external_wind_guard(output_dir=root / "guard", cache_dirs=str(cache), suite_dir=root / "runs", seeds="201")
            guard = load_json(out / "external_wind_guard.json")

            self.assertEqual(guard["claim_gate"], "blocked_not_citable")
            self.assertFalse(guard["checks"]["no_wtb_or_sdwpf_source"])

    def test_external_guard_blocks_cache_missing_required_schema_aliases(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            cache = root / "cache"
            cache.mkdir()
            for name in ["features", "physics", "regime_primary", "regime_primary_valid", "node_ids"]:
                np.save(cache / f"{name}.npy", np.zeros((2, 2), dtype=np.float32))
            save_json(
                cache / "metadata.json",
                {
                    "dataset": "external_wind",
                    "farm": "kelmarsh",
                    "external_split": "chronological",
                    "license": "CC-BY-4.0",
                    "source_url": "https://zenodo.org/records/16807551",
                },
            )

            out = run_external_wind_guard(output_dir=root / "guard", cache_dirs=str(cache), suite_dir=root / "runs", seeds="201")
            guard = load_json(out / "external_wind_guard.json")
            cache_status = pd.read_csv(out / "external_wind_cache_status.csv")

            self.assertEqual(guard["claim_gate"], "blocked_not_citable")
            self.assertFalse(guard["checks"]["all_cache_dirs_exist"])
            self.assertFalse(bool(cache_status.iloc[0]["complete"]))
            self.assertFalse(bool(cache_status.iloc[0]["metadata_schema_complete"]))

    def test_external_guard_blocks_missing_required_seed_matrix(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            caches = []
            for farm, split, target in [
                ("kelmarsh", "chronological", ""),
                ("penmanshiel", "chronological", ""),
                ("kelmarsh", "leave-one-farm-out", "penmanshiel"),
                ("penmanshiel", "leave-one-farm-out", "kelmarsh"),
            ]:
                cache = root / "cache" / f"{farm}_{split}"
                cache.mkdir(parents=True)
                for name in ["features", "physics", "regime_primary", "regime_primary_valid", "regime_valid", "anchor_index", "node_ids"]:
                    np.save(cache / f"{name}.npy", np.zeros((2, 2), dtype=np.float32))
                save_json(
                    cache / "metadata.json",
                    {
                        "dataset": "external_wind",
                        "farm": farm,
                        "target_farm": target,
                        "external_split": split,
                        "license": "CC-BY-4.0",
                        "source_url": f"https://zenodo.org/{farm}",
                        "source_files": f"{farm}/scada.csv",
                        "external_source_fingerprint": self._external_guard_fingerprint(farm, split, target),
                        "split_farm_roles": {"train": [farm], "val": [farm], "test": [target or farm]},
                    },
                )
                caches.append(cache)
            suite = root / "runs"
            for farm, split, target in [
                ("kelmarsh", "chronological", ""),
                ("penmanshiel", "chronological", ""),
                ("kelmarsh", "leave-one-farm-out", "penmanshiel"),
                ("penmanshiel", "leave-one-farm-out", "kelmarsh"),
            ]:
                run = suite / farm / split.replace("-", "_") / "Graph_WaveNet_seed201"
                metrics = run / "test_metrics"
                metrics.mkdir(parents=True)
                save_json(
                    run / "training_summary.json",
                    {
                        "label": "Graph WaveNet",
                        "seed": 201,
                        "dataset": "external_wind",
                        "farm": farm,
                        "target_farm": target,
                        "external_split": split,
                    },
                )
                save_json(
                    metrics / "metrics.json",
                    {
                        "overall": {"rmse": 1.0},
                        "switch_window": {"rmse": 1.0},
                        "gate_alignment": {"nmi": 0.8, "ari": 0.7, "expert_usage_entropy": 1.0},
                    },
                )
                np.save(metrics / "pred.npy", np.ones((2, 1, 1), dtype=np.float32))
                np.save(metrics / "target.npy", np.zeros((2, 1, 1), dtype=np.float32))
                np.save(metrics / "mask.npy", np.ones((2, 1, 1), dtype=np.float32))
                np.save(metrics / "regime_primary.npy", np.ones((2, 1), dtype=np.int16))
                np.save(metrics / "regime_primary_valid.npy", np.ones((2, 1), dtype=np.float32))
                np.save(metrics / "anchor_index.npy", np.arange(2, dtype=np.int64))
                physics = np.zeros((2, 1, 4), dtype=np.float32)
                physics[..., 0] = 10.5
                np.save(metrics / "anchor_physics.npy", physics)

            out = run_external_wind_guard(
                output_dir=root / "guard",
                cache_dirs=",".join(str(path) for path in caches),
                suite_dir=suite,
                seeds="201,202",
                required_models="Graph WaveNet",
            )
            guard = load_json(out / "external_wind_guard.json")
            status = pd.read_csv(out / "external_wind_run_status.csv")

            self.assertEqual(guard["claim_gate"], "blocked_not_citable")
            self.assertFalse(guard["checks"]["all_expected_runs_complete"])
            self.assertEqual(guard["expected_runs"], 8)
            self.assertEqual(guard["complete_runs"], 4)
            self.assertEqual(int((status["seed"] == 202).sum()), 4)
            self.assertFalse(status.loc[status["seed"] == 202, "complete"].any())

    def test_external_guard_blocks_when_required_metric_values_are_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            split_specs = [
                ("kelmarsh", "chronological", ""),
                ("penmanshiel", "chronological", ""),
                ("kelmarsh", "leave-one-farm-out", "penmanshiel"),
                ("penmanshiel", "leave-one-farm-out", "kelmarsh"),
            ]
            caches = [self._write_external_guard_cache(root, farm, split, target) for farm, split, target in split_specs]
            suite = root / "runs"
            for farm, split, target in split_specs:
                self._write_external_guard_run(
                    suite,
                    model="Graph WaveNet",
                    seed=201,
                    farm=farm,
                    split=split,
                    target=target,
                    include_expert_usage=False,
                )

            out = run_external_wind_guard(
                output_dir=root / "guard",
                cache_dirs=",".join(str(path) for path in caches),
                suite_dir=suite,
                seeds="201",
                required_models="Graph WaveNet",
            )
            guard = load_json(out / "external_wind_guard.json")

            self.assertEqual(guard["claim_gate"], "blocked_not_citable")
            self.assertFalse(guard["checks"]["all_required_metric_values_present"])

    def test_external_guard_treats_nan_expert_usage_as_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            split_specs = [
                ("kelmarsh", "chronological", ""),
                ("penmanshiel", "chronological", ""),
                ("kelmarsh", "leave-one-farm-out", "penmanshiel"),
                ("penmanshiel", "leave-one-farm-out", "kelmarsh"),
            ]
            caches = [self._write_external_guard_cache(root, farm, split, target) for farm, split, target in split_specs]
            suite = root / "runs"
            for farm, split, target in split_specs:
                run = self._write_external_guard_run(
                    suite,
                    model="Physics-Aligned MoE",
                    seed=201,
                    farm=farm,
                    split=split,
                    target=target,
                )
                metrics_path = run / "test_metrics" / "metrics.json"
                metrics = load_json(metrics_path)
                metrics["gate_alignment"]["expert_usage"] = float("nan")
                save_json(metrics_path, metrics)

            out = run_external_wind_guard(
                output_dir=root / "guard",
                cache_dirs=",".join(str(path) for path in caches),
                suite_dir=suite,
                seeds="201",
                required_models="Physics-Aligned MoE",
            )
            guard = load_json(out / "external_wind_guard.json")

            self.assertEqual(guard["claim_gate"], "blocked_not_citable")
            self.assertFalse(guard["checks"]["all_required_metric_values_present"])

    def test_external_guard_blocks_protocol_without_routing_models(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            split_specs = [
                ("kelmarsh", "chronological", ""),
                ("penmanshiel", "chronological", ""),
                ("kelmarsh", "leave-one-farm-out", "penmanshiel"),
                ("penmanshiel", "leave-one-farm-out", "kelmarsh"),
            ]
            caches = [self._write_external_guard_cache(root, farm, split, target) for farm, split, target in split_specs]
            suite = root / "runs"
            for farm, split, target in split_specs:
                self._write_external_guard_run(
                    suite,
                    model="Graph WaveNet",
                    seed=201,
                    farm=farm,
                    split=split,
                    target=target,
                    include_expert_usage=False,
                )

            out = run_external_wind_guard(
                output_dir=root / "guard",
                cache_dirs=",".join(str(path) for path in caches),
                suite_dir=suite,
                seeds="201",
                required_models="Graph WaveNet",
            )
            guard = load_json(out / "external_wind_guard.json")

            self.assertEqual(guard["claim_gate"], "blocked_not_citable")
            self.assertTrue(guard["checks"]["forecast_metric_values_present"])
            self.assertFalse(guard["checks"]["routing_metric_values_present"])
            self.assertEqual(guard["expected_routing_runs"], 0)

    def test_external_guard_downgrades_complete_low_alignment_protocol_to_within_wtb(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            split_specs = [
                ("kelmarsh", "chronological", ""),
                ("penmanshiel", "chronological", ""),
                ("kelmarsh", "leave-one-farm-out", "penmanshiel"),
                ("penmanshiel", "leave-one-farm-out", "kelmarsh"),
            ]
            caches = [self._write_external_guard_cache(root, farm, split, target) for farm, split, target in split_specs]
            suite = root / "runs"
            for farm, split, target in split_specs:
                self._write_external_guard_run(
                    suite,
                    model="Physics-Aligned MoE",
                    seed=201,
                    farm=farm,
                    split=split,
                    target=target,
                    nmi=0.1,
                    ari=0.1,
                )

            out = run_external_wind_guard(
                output_dir=root / "guard",
                cache_dirs=",".join(str(path) for path in caches),
                suite_dir=suite,
                seeds="201",
                required_models="Physics-Aligned MoE",
            )
            guard = load_json(out / "external_wind_guard.json")

            self.assertEqual(guard["status"], "complete_but_within_wtb_only")
            self.assertEqual(guard["claim_gate"], "within_wtb_only")
            self.assertTrue(guard["checks"]["all_required_metric_values_present"])
            self.assertFalse(guard["checks"]["routing_nmi_meets_minimum"])
            self.assertFalse(guard["checks"]["routing_ari_meets_minimum"])

    def test_external_guard_downgrades_complete_undefined_alignment_protocol_to_within_wtb(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            split_specs = [
                ("kelmarsh", "chronological", ""),
                ("penmanshiel", "chronological", ""),
                ("kelmarsh", "leave-one-farm-out", "penmanshiel"),
                ("penmanshiel", "leave-one-farm-out", "kelmarsh"),
            ]
            caches = [self._write_external_guard_cache(root, farm, split, target) for farm, split, target in split_specs]
            suite = root / "runs"
            for farm, split, target in split_specs:
                run = self._write_external_guard_run(
                    suite,
                    model="Physics-Aligned MoE",
                    seed=201,
                    farm=farm,
                    split=split,
                    target=target,
                    nmi=float("nan"),
                    ari=float("nan"),
                )
                metrics_path = run / "test_metrics" / "metrics.json"
                metrics = load_json(metrics_path)
                metrics["gate_alignment"]["expert_usage_entropy"] = 0.2
                save_json(metrics_path, metrics)

            out = run_external_wind_guard(
                output_dir=root / "guard",
                cache_dirs=",".join(str(path) for path in caches),
                suite_dir=suite,
                seeds="201",
                required_models="Physics-Aligned MoE",
            )
            guard = load_json(out / "external_wind_guard.json")

            self.assertEqual(guard["status"], "complete_but_within_wtb_only")
            self.assertEqual(guard["claim_gate"], "within_wtb_only")
            self.assertTrue(guard["checks"]["routing_metric_values_present"])
            self.assertFalse(guard["checks"]["routing_nmi_meets_minimum"])
            self.assertFalse(guard["checks"]["routing_ari_meets_minimum"])

    def test_external_guard_passes_only_complete_cross_farm_protocol(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            caches = []
            for farm, split, target in [
                ("kelmarsh", "chronological", ""),
                ("penmanshiel", "chronological", ""),
                ("kelmarsh", "leave-one-farm-out", "penmanshiel"),
                ("penmanshiel", "leave-one-farm-out", "kelmarsh"),
            ]:
                cache = root / "cache" / f"{farm}_{split}"
                cache.mkdir(parents=True)
                for name in ["features", "physics", "regime_primary", "regime_primary_valid", "regime_valid", "anchor_index", "node_ids"]:
                    np.save(cache / f"{name}.npy", np.zeros((2, 2), dtype=np.float32))
                save_json(
                    cache / "metadata.json",
                    {
                        "dataset": "external_wind",
                        "farm": farm,
                        "target_farm": target,
                        "external_split": split,
                        "license": "CC-BY-4.0",
                        "source_url": f"https://zenodo.org/{farm}",
                        "source_files": f"{farm}/scada.csv",
                        "external_source_fingerprint": self._external_guard_fingerprint(farm, split, target),
                        "split_farm_roles": {"train": [farm], "val": [farm], "test": [target or farm]},
                    },
                )
                caches.append(cache)
            suite = root / "runs"
            for model in ["Graph WaveNet", "PatchTST", "Physics-Aligned MoE", "MoE + L_bal + L_align + L_force"]:
                for seed in [201, 202, 203, 204, 205]:
                    for farm, split, target in [
                        ("kelmarsh", "chronological", ""),
                        ("penmanshiel", "chronological", ""),
                        ("kelmarsh", "leave-one-farm-out", "penmanshiel"),
                        ("penmanshiel", "leave-one-farm-out", "kelmarsh"),
                    ]:
                        run = suite / farm / split.replace("-", "_") / f"{model.replace(' ', '_')}_seed{seed}"
                        metrics = run / "test_metrics"
                        metrics.mkdir(parents=True)
                        save_json(
                            run / "training_summary.json",
                            {
                                "label": model,
                                "seed": seed,
                                "dataset": "external_wind",
                                "farm": farm,
                                "target_farm": target,
                                "external_split": split,
                            },
                        )
                        metrics_payload = {
                            "overall": {"rmse": 1.0},
                            "switch_window": {"rmse": 1.0},
                        }
                        if model in {"Physics-Aligned MoE", "MoE + L_bal + L_align + L_force"}:
                            metrics_payload["gate_alignment"] = {
                                "nmi": 0.8,
                                "ari": 0.7,
                                "expert_usage_entropy": 1.0,
                                "expert_usage": [0.25, 0.50, 0.25],
                            }
                        save_json(metrics / "metrics.json", metrics_payload)
                        np.save(metrics / "pred.npy", np.ones((2, 1, 1), dtype=np.float32))
                        np.save(metrics / "target.npy", np.zeros((2, 1, 1), dtype=np.float32))
                        np.save(metrics / "mask.npy", np.ones((2, 1, 1), dtype=np.float32))
                        np.save(metrics / "regime_primary.npy", np.ones((2, 1), dtype=np.int16))
                        np.save(metrics / "regime_primary_valid.npy", np.ones((2, 1), dtype=np.float32))
                        np.save(metrics / "anchor_index.npy", np.arange(2, dtype=np.int64))
                        physics = np.zeros((2, 1, 4), dtype=np.float32)
                        physics[..., 0] = 10.5
                        np.save(metrics / "anchor_physics.npy", physics)

            out = run_external_wind_guard(
                output_dir=root / "guard",
                cache_dirs=",".join(str(path) for path in caches),
                suite_dir=suite,
            )
            guard = load_json(out / "external_wind_guard.json")

            self.assertEqual(guard["claim_gate"], "portable_mechanism_passed")
            self.assertTrue(guard["checks"]["cross_farm_both_directions_complete"])
            self.assertTrue(guard["checks"]["chronological_sanity_complete"])
            self.assertTrue(guard["checks"]["forecast_metric_values_present"])
            self.assertTrue(guard["checks"]["routing_metric_values_present"])
            self.assertAlmostEqual(guard["mean_boundary_rmse"], 1.0)
            self.assertEqual(guard["expected_runs"], 80)
            self.assertEqual(guard["expected_routing_runs"], 40)
            self.assertEqual(guard["complete_runs"], 80)
            status = pd.read_csv(out / "external_wind_run_status.csv")
            self.assertIn("boundary_rmse", status.columns)
            self.assertIn("expert_usage", status.columns)
            self.assertEqual(set(guard["required_models"]), {"Graph WaveNet", "PatchTST", "Physics-Aligned MoE", "MoE + L_bal + L_align + L_force"})
            self.assertEqual(set(guard["routing_required_models"]), {"Physics-Aligned MoE", "MoE + L_bal + L_align + L_force"})


if __name__ == "__main__":
    unittest.main()
