"""Synthetic tests for mainline 2026 adapter without accessing real 2026 data."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import sys
import zipfile

import numpy as np
import pytest

C_LEGACY = Path(r"C:\Users\lidong\AppData\Local\Temp\paper3_mainline_legacy_20261026")
if C_LEGACY.exists() and str(C_LEGACY) not in sys.path:
    sys.path.insert(0, str(C_LEGACY))
REPO_ROOT = Path(r"E:\论文3")
if REPO_ROOT.exists() and str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

ADAPTER_PATH = Path(__file__).resolve().parent / 'adapter.py'
spec = importlib.util.spec_from_file_location("mainline_2026_adapter", ADAPTER_PATH)
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)


def make_fake_2026_zip(zip_path: Path, months=(1, 2, 3, 4), corrupt_schema=False, conflict=False, pitch_same_mean=False):
    turb_fields = ["wtc_AcWindSp_mean", "wtc_PitcPosA_mean", "wtc_PitcPosB_mean", "wtc_PitcPosC_mean"]
    grid_fields = ["wtc_ActPower_mean", "wtc_ReactPwr_mean"]
    if corrupt_schema:
        turb_fields[0] = "corrupt_column"

    with zipfile.ZipFile(zip_path, "w") as z:
        for m in months:
            t_hdr = "TimeStamp,StationId," + ",".join(turb_fields) + "\n"
            t_rows = []
            for st in range(2304510, 2304531):
                t_rows.append(f"2026-{m:02d}-01T00:10:00Z,{st},10.5,1.0,2.0,3.0")
                if conflict and m == 1 and st == 2304510:
                    t_rows.append(f"2026-{m:02d}-01T00:10:00Z,{st},15.0,1.0,2.0,3.0")
                elif pitch_same_mean and m == 1 and st == 2304510:
                    t_rows.append(f"2026-{m:02d}-01T00:10:00Z,{st},10.5,2.0,2.0,2.0")
                else:
                    t_rows.append(f"2026-{m:02d}-01T00:10:00Z,{st},10.5,1.0,2.0,3.0")
            z.writestr(f"tblSCTurbine_2026_{m:02d}.csv", t_hdr + "\n".join(t_rows) + "\n")

            g_hdr = "TimeStamp,StationId," + ",".join(grid_fields) + "\n"
            g_rows = []
            for st in range(2304510, 2304531):
                g_rows.append(f"2026-{m:02d}-01T00:10:00Z,{st},500.0,50.0")
            z.writestr(f"tblSCTurGrid_2026_{m:02d}.csv", g_hdr + "\n".join(g_rows) + "\n")


def test_cli_rejects_numeric_without_pbs_jobid(tmp_path, monkeypatch):
    monkeypatch.delenv("PBS_JOBID", raising=False)
    proto_file = tmp_path / "protocol.json"
    proto_file.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["adapter.py", "--protocol", str(proto_file), "--output", str(tmp_path), "--stage", "preflight"])
    with pytest.raises(ValueError, match="PBS_JOBID missing"):
        adapter.main()


def test_preflight_verifies_archive_without_opening_zip(tmp_path, monkeypatch):
    archive_path = tmp_path / "fake_2026.zip"
    archive_path.write_bytes(b"opaque_archive_bytes_not_zip")

    protocol_path = tmp_path / "protocol.json"
    proto = {
        "legacy_root": str(tmp_path),
        "source_sha256": {"file1": adapter.sha(tmp_path/'file1') if (tmp_path/'file1').write_text('test') else ''},
        "new_archive": {
            "path": str(archive_path),
            "bytes": len(b"opaque_archive_bytes_not_zip"),
            "md5": adapter.md5_file(archive_path),
            "sha256": adapter.sha(archive_path),
        },
        "selected_tasks": [{"task_index": i, "task": {"subset": "P1" if i < 5 else "WPQ36", "seed": 201 + (i % 5)}} for i in range(10)],
        "verified_inputs": {str(tmp_path / "file1"): {"bytes": 4, "sha256": adapter.sha(tmp_path / "file1" if (tmp_path / "file1").write_text("test") else tmp_path / "file1")}},
        "seeds": [201, 202, 203, 204, 205],
        "primary_q": 0.95,
        "offset_index": 2,
        "cost_epsilon": 0.02,
        "v_max": 0.10,
        "window": {"start": "2026-01-01T00:00:00Z", "end": "2026-05-01T00:00:00Z"},
    }
    freeze_dir = tmp_path / "results/chosen"
    freeze_dir.mkdir(parents=True)
    freeze_file = freeze_dir / "freeze.json"
    freeze_file.write_text("{}", encoding="utf-8")
    proto["legacy_freeze_sha256"] = adapter.sha(freeze_file)
    protocol_path.write_text(json.dumps(proto), encoding="utf-8")

    def forbidden_zip(*args, **kwargs):
        raise AssertionError("zipfile.ZipFile called during preflight!")
    monkeypatch.setattr(zipfile, "ZipFile", forbidden_zip)

    args = argparse.Namespace(protocol=protocol_path, output=tmp_path / "out", stage="preflight")
    adapter.preflight(args, proto)

    receipt = json.loads((tmp_path / "out/preflight/preflight_receipt.json").read_text(encoding="utf-8"))
    assert receipt["status"] == "PREFLIGHT_PASS_NO_TEST_READ"
    assert receipt["archive_never_opened"] is True


def test_setup_legacy_runtime_missing_source_fails(tmp_path):
    proto = {"source_sha256": {"nonexistent.py": "dummy"}}
    with pytest.raises(FileNotFoundError, match="Required legacy source missing"):
        adapter.setup_legacy_runtime(proto, tmp_path)


def test_partial_output_is_preserved_and_inputs_cannot_be_silently_missing(tmp_path):
    p=tmp_path/'partial'; p.mkdir(); (p/'receipt.json').write_text('{"status":"FAILED_PRESERVED"}')
    args=argparse.Namespace(protocol=tmp_path/'p.json')
    with pytest.raises(FileExistsError,match='refuse overwrite'):
        adapter.begin(p,args,{},[],'evaluate')
    assert json.loads((p/'receipt.json').read_text())['status']=='FAILED_PRESERVED'
    with pytest.raises(FileNotFoundError):
        adapter.require_legacy_inputs(dict(verified_inputs={str(tmp_path/'missing'):{'bytes':1,'sha256':'x'}}))


def test_freeze_rejects_changed_executable_before_any_raw_read(tmp_path):
    out=tmp_path/'out'; (out/'chosen').mkdir(parents=True)
    proto=tmp_path/'p.json'; proto.write_text('{}')
    (out/'chosen/freeze.json').write_text(json.dumps(dict(protocol_sha256=adapter.sha(proto),
        adapter_sha256='changed',legacy_freeze_sha256='old',review_status='PASS_BEFORE_UNLOCK')))
    args=argparse.Namespace(output=out,protocol=proto)
    with pytest.raises(ValueError,match='identity mismatch'):
        adapter.validate_freeze(args,dict(legacy_freeze_sha256='old'))


def test_evaluate_refuses_without_freeze(tmp_path):
    leg_root = C_LEGACY if C_LEGACY.exists() else REPO_ROOT
    dummy_source = leg_root / "dummy_source.py"
    if not dummy_source.exists():
        dummy_source = tmp_path / "dummy_source.py"
        dummy_source.write_text("# dummy")

    protocol_path = tmp_path / "protocol.json"
    proto = {
        "legacy_root": str(dummy_source.parent),
        "source_sha256": {dummy_source.name: adapter.sha(dummy_source)},
        "new_archive": {"path": str(tmp_path / "2026.zip")},
    }
    protocol_path.write_text(json.dumps(proto), encoding="utf-8")
    args = argparse.Namespace(protocol=protocol_path, output=tmp_path / "out", stage="evaluate")
    with pytest.raises(FileNotFoundError, match="Frozen historical package missing"):
        adapter.evaluate(args, proto)


def test_missing_months_and_corrupt_schema_fail_evaluation(tmp_path):
    class FakeQualifier:
        @staticmethod
        def read_header(handle, table):
            return {
                "encoding": "utf-8-sig", "delimiter": ",", "station": "StationId",
                "fields": ["wtc_AcWindSp_mean", "wtc_PitcPosA_mean", "wtc_PitcPosB_mean", "wtc_PitcPosC_mean"]
            }

    class FakeCorruptQualifier:
        @staticmethod
        def read_header(handle, table):
            return {
                "encoding": "utf-8-sig", "delimiter": ",", "station": "StationId",
                "fields": ["corrupt_col", "wtc_PitcPosA_mean", "wtc_PitcPosB_mean", "wtc_PitcPosC_mean"]
            }

    storage = np.zeros((120 * 144 + 1) * 21 * 4, dtype=float).reshape(-1, 4)
    seen = np.zeros(len(storage), bool)
    schema = {"encoding": "utf-8-sig", "delimiter": ",", "station": "StationId", "fields": ["wtc_AcWindSp_mean", "wtc_PitcPosA_mean", "wtc_PitcPosB_mean", "wtc_PitcPosC_mean"]}

    # Missing month 4
    zip_missing = tmp_path / "missing.zip"
    make_fake_2026_zip(zip_missing, months=[1, 2, 3])
    with pytest.raises(ValueError, match="Missing or ambiguous table"):
        adapter.read_table_2026(zip_missing, 2026, "tblSCTurbine", storage, seen, [1, 2, 3, 4], schema, FakeQualifier())

    # Corrupt schema
    zip_corrupt = tmp_path / "corrupt.zip"
    make_fake_2026_zip(zip_corrupt, months=[1, 2, 3, 4], corrupt_schema=True)
    with pytest.raises(ValueError, match="Consumed schema differs"):
        adapter.read_table_2026(zip_corrupt, 2026, "tblSCTurbine", storage, seen, [1, 2, 3, 4], schema, FakeCorruptQualifier())


def test_raw_pitch_difference_rejected_even_if_mean_identical(tmp_path):
    class FakeQualifier:
        @staticmethod
        def read_header(handle, table):
            return {
                "encoding": "utf-8-sig", "delimiter": ",", "station": "StationId",
                "fields": ["wtc_AcWindSp_mean", "wtc_PitcPosA_mean", "wtc_PitcPosB_mean", "wtc_PitcPosC_mean"]
            }

    qualifier = FakeQualifier()
    schema = {"encoding": "utf-8-sig", "delimiter": ",", "station": "StationId", "fields": qualifier.read_header(None, None)["fields"]}
    storage = np.zeros((120 * 144 + 1) * 21 * 4, dtype=float).reshape(-1, 4)
    seen = np.zeros(len(storage), bool)

    zip_pitch_conflict = tmp_path / "pitch_conflict.zip"
    make_fake_2026_zip(zip_pitch_conflict, months=[1], pitch_same_mean=True)
    with pytest.raises(ValueError, match="Conflicting consumed observations"):
        adapter.read_table_2026(zip_pitch_conflict, 2026, "tblSCTurbine", storage, seen, [1], schema, qualifier)


def test_conflicting_raw_rows_rejected_equal_duplicates_accepted(tmp_path):
    class FakeQualifier:
        @staticmethod
        def read_header(handle, table):
            return {
                "encoding": "utf-8-sig", "delimiter": ",", "station": "StationId",
                "fields": ["wtc_AcWindSp_mean", "wtc_PitcPosA_mean", "wtc_PitcPosB_mean", "wtc_PitcPosC_mean"]
            }

    qualifier = FakeQualifier()
    schema = {"encoding": "utf-8-sig", "delimiter": ",", "station": "StationId", "fields": qualifier.read_header(None, None)["fields"]}
    storage = np.zeros((120 * 144 + 1) * 21 * 4, dtype=float).reshape(-1, 4)
    seen = np.zeros(len(storage), bool)

    zip_conflict = tmp_path / "conflict.zip"
    make_fake_2026_zip(zip_conflict, months=[1], conflict=True)
    with pytest.raises(ValueError, match="Conflicting consumed observations"):
        adapter.read_table_2026(zip_conflict, 2026, "tblSCTurbine", storage, seen, [1], schema, qualifier)

    zip_clean = tmp_path / "clean.zip"
    make_fake_2026_zip(zip_clean, months=[1], conflict=False)
    storage.fill(np.nan)
    seen.fill(False)
    rep = adapter.read_table_2026(zip_clean, 2026, "tblSCTurbine", storage, seen, [1], schema, qualifier)
    assert rep["redundant_equal_copies"] == 21


def test_aggregate_14_coordinates_and_h_not_gating(tmp_path):
    out = tmp_path / "out"
    eval_dir = out / "evaluate"
    eval_dir.mkdir(parents=True)

    leg_root = C_LEGACY if C_LEGACY.exists() else REPO_ROOT
    dummy_src = tmp_path / "source.py"
    dummy_src.write_text("# dummy")

    tasks = []
    seeds = [201, 202, 203, 204, 205]
    for s_idx, subset in enumerate(["P1", "WPQ36"]):
        for seed_idx, seed in enumerate(seeds):
            t_idx = s_idx * 5 + seed_idx
            tasks.append({"task_index": t_idx, "task": {"subset": subset, "seed": seed}})

    proto = {
        "legacy_root": str(tmp_path),
        "source_sha256": {"source.py": adapter.sha(dummy_src)},
        "selected_tasks": tasks,
        "offset_index": 2,
        "cost_epsilon": 0.02,
        "v_max": 0.10,
        "n_boot": 400,
        "bootstrap_seed": 20261029,
        "primary_span": 3,
        "sensitivity_spans": [1, 7],
    }
    proto_file = tmp_path / "protocol.json"
    proto_file.write_text(json.dumps(proto), encoding="utf-8")
    proto_sha = adapter.sha(proto_file)

    # 1. Non-zero variance daily weather blocks with reasonable risk (< 10%)
    rng = np.random.default_rng(2026)
    n_days = 20
    counts = np.full(n_days, 144.0 * 21)
    base_cost = np.linspace(60.0, 70.0, n_days)

    for item in tasks:
        t_idx = item["task_index"]
        t_dir = eval_dir / str(t_idx)
        t_dir.mkdir()
        # Seed variation: vary violation counts around 5% of total day counts
        v_daily = rng.binomial(n=counts.astype(int), p=0.045)
        c_mult = 1.005 + .001*np.sin(np.arange(n_days)) if item["task"]["subset"] == "P1" else np.ones(n_days)
        c_daily = (base_cost * c_mult) * counts

        np.savez(t_dir / "blocks.npz", **{
            "2__count": counts,
            "2__block_ids": np.arange(n_days),
            "2__loss_sum": c_daily,
            "2__violation_sum": v_daily.astype(float),
            "2__reserve_sum": c_daily-10*.2*counts,
            "2__shortage_sum": .2*counts,
        })
        manifest = {"blocks.npz": {"bytes": (t_dir / "blocks.npz").stat().st_size, "sha256": adapter.sha(t_dir / "blocks.npz")}}
        (t_dir / "receipt.json").write_text(json.dumps({"status": "COMPLETE", "protocol_sha256": proto_sha}), encoding="utf-8")
        manifest["receipt.json"] = {"bytes": (t_dir / "receipt.json").stat().st_size, "sha256": adapter.sha(t_dir / "receipt.json")}
        (t_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    args = argparse.Namespace(protocol=proto_file, output=out, stage="aggregate")
    adapter.aggregate(args, proto)

    summary = json.loads((out / "aggregate/summary.json").read_text(encoding="utf-8"))
    assert summary["confirmed"] is True
    assert summary["coordinate_count"] == 14  # exactly 14 joint coordinates
    assert summary["H_threshold_applied"] is False
    assert "descriptive only" in summary["U_R_H_role"]
    assert "risk_point" in summary and "relative_ratio_point" in summary


def test_zero_variance_risk_is_unknown_and_fails_confirmation(tmp_path):
    out = tmp_path / "out_zero_var"
    eval_dir = out / "evaluate"
    eval_dir.mkdir(parents=True)

    dummy_src = tmp_path / "source.py"
    dummy_src.write_text("# dummy")

    tasks = []
    seeds = [201, 202, 203, 204, 205]
    for s_idx, subset in enumerate(["P1", "WPQ36"]):
        for seed_idx, seed in enumerate(seeds):
            t_idx = s_idx * 5 + seed_idx
            tasks.append({"task_index": t_idx, "task": {"subset": subset, "seed": seed}})

    proto = {
        "legacy_root": str(tmp_path),
        "source_sha256": {"source.py": adapter.sha(dummy_src)},
        "selected_tasks": tasks,
        "offset_index": 2,
        "cost_epsilon": 0.02,
        "v_max": 0.10,
        "n_boot": 100,
        "bootstrap_seed": 20261029,
        "primary_span": 3,
        "sensitivity_spans": [1, 7],
    }
    proto_file = tmp_path / "protocol_zero.json"
    proto_file.write_text(json.dumps(proto), encoding="utf-8")
    proto_sha = adapter.sha(proto_file)

    # Identical 0 violations everywhere -> zero bootstrap variance -> UNKNOWN risk upper bound = 1.0 -> must fail!
    for item in tasks:
        t_idx = item["task_index"]
        t_dir = eval_dir / str(t_idx)
        t_dir.mkdir()
        np.savez(t_dir / "blocks.npz", **{
            "2__count": np.full(10, 100.0),
            "2__block_ids": np.arange(10),
            "2__loss_sum": np.full(10, 60.0),
            "2__violation_sum": np.zeros(10),
            "2__reserve_sum": np.full(10, 60.0),
            "2__shortage_sum": np.zeros(10),
        })
        manifest = {"blocks.npz": {"bytes": (t_dir / "blocks.npz").stat().st_size, "sha256": adapter.sha(t_dir / "blocks.npz")}}
        (t_dir / "receipt.json").write_text(json.dumps({"status": "COMPLETE", "protocol_sha256": proto_sha}), encoding="utf-8")
        manifest["receipt.json"] = {"bytes": (t_dir / "receipt.json").stat().st_size, "sha256": adapter.sha(t_dir / "receipt.json")}
        (t_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    args = argparse.Namespace(protocol=proto_file, output=out, stage="aggregate")
    adapter.aggregate(args, proto)

    summary = json.loads((out / "aggregate/summary.json").read_text(encoding="utf-8"))
    assert summary["confirmed"] is False
    assert summary["primary_status"] == "CONFIRMATION_NOT_ESTABLISHED"
    # Zero variance forces risk upper to 1.0 (100%)
    assert summary["candidate_max_risk_upper_percent"] == 100.0
