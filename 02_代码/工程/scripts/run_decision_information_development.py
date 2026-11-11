"""Run a new raw-data development study; never rewrite historical results."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from repo_paths import Path, repository_root
import platform
import shutil
import subprocess
import sys
import time
from typing import Any

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from threadpoolctl import threadpool_limits

ROOT = Path(repository_root())
sys.path.insert(0, str(ROOT))
from windfarm_moe.decision_information import arrived_history, block_totals, paired_interval, validate_temporal_stages


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")


def verify_bundle(path: Path, protocol_hash: str, stage: str, seed: int | None = None,
                  condition: str | None = None) -> dict[str, Any]:
    """Verify bytes and producer identity before consuming an archived stage."""
    manifest = json.loads((path / "output_manifest.json").read_text(encoding="utf-8"))
    for name, record in manifest.items():
        member = (path / name).resolve()
        if not member.is_relative_to(path.resolve()) or not member.is_file():
            raise ValueError("Invalid archived member: " + name)
        if member.stat().st_size != record["bytes"] or digest(member) != record["sha256"]:
            raise ValueError("Archived output mismatch: " + str(member))
    info = json.loads((path / "execution_receipt.json").read_text(encoding="utf-8"))
    if info["status"] != "COMPLETED_DEVELOPMENT_NOT_CERTIFIED":
        raise ValueError("Upstream execution not complete")
    if info.get("protocol_sha256") != protocol_hash or info["arguments"]["stage"] != stage:
        raise ValueError("Upstream protocol/stage identity mismatch")
    current_sources = {Path(__file__).name: digest(Path(__file__)),
                       "decision_information.py": digest(ROOT / "windfarm_moe/decision_information.py")}
    archived_sources = {Path(name).name: value for name, value in info.get("source_sha256", {}).items()}
    if any(archived_sources.get(name) != value for name, value in current_sources.items()):
        raise ValueError("Upstream implementation differs from the consuming implementation")
    for key, expected in (("seed", seed), ("condition", condition)):
        if expected is not None and info["arguments"].get(key) != expected:
            raise ValueError("Upstream " + key + " mismatch")
    return info


def receipt(output: Path, protocol: Path, inputs: list[Path], arguments: dict[str, Any]) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=False)
    sources = [Path(__file__).resolve(), ROOT / "windfarm_moe/decision_information.py", protocol]
    snapshot = output / "source"
    snapshot.mkdir()
    for source in sources:
        shutil.copyfile(source, snapshot / source.name)
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, stderr=subprocess.DEVNULL).strip()
    except (subprocess.SubprocessError, FileNotFoundError):
        commit = "not-a-git-checkout; exact source hashes archived"
    info = {
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "status": "RUNNING_DEVELOPMENT",
        "argv": sys.argv,
        "arguments": arguments,
        "git_commit": commit,
        "python": sys.version,
        "executable": sys.executable,
        "numpy": np.__version__, "pandas": pd.__version__, "sklearn": sklearn.__version__,
        "torch_installed": importlib.metadata.version("torch"),
        "compute_backend": "CPU sklearn histogram boosting; CUDA not used",
        "protocol_sha256": digest(protocol),
        "platform": platform.platform(), "host": platform.node(), "cpu": platform.processor(),
        "pbs_job_id": os.environ.get("PBS_JOBID"),
        "allocated_cpus": os.environ.get("NCPUS", os.environ.get("OMP_NUM_THREADS")),
        "source_sha256": {str(p): digest(p) for p in sources},
        "input_sha256": {str(p): digest(p) for p in inputs},
        "scope": "development; no historical claim upgrade or E07 activation",
    }
    write_json(output / "execution_receipt.json", info)
    return info


def finish(output: Path, info: dict[str, Any]) -> None:
    for path, expected in info["input_sha256"].items():
        if digest(Path(path)) != expected:
            raise ValueError("Protected input changed: " + path)
    info["finished_utc"] = datetime.now(timezone.utc).isoformat()
    info["status"] = "COMPLETED_DEVELOPMENT_NOT_CERTIFIED"
    write_json(output / "execution_receipt.json", info)
    manifest = {str(p.relative_to(output)): {"bytes": p.stat().st_size, "sha256": digest(p)}
                for p in sorted(output.rglob("*")) if p.is_file() and p.name != "output_manifest.json"}
    write_json(output / "output_manifest.json", manifest)


def load_raw_csv(path: Path) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    """Reconstruct physical, unimputed time/node channels from the original CSV."""
    columns = ["TurbID", "Day", "Tmstamp", "Wspd", "Patv", "Prtv", "Pab1", "Pab2", "Pab3"]
    frame = pd.read_csv(path, usecols=columns, dtype={
        "TurbID": "int16", "Day": "int16", "Tmstamp": "category",
        **{k: "float32" for k in columns[3:]},
    })
    clock = {f"{hour:02d}:{minute:02d}": hour * 6 + minute // 10
             for hour in range(24) for minute in range(0, 60, 10)}
    time_of_day = frame["Tmstamp"].astype(str).map(clock)
    if time_of_day.isna().any() or frame["Day"].min() != 1:
        raise ValueError("Non-10-minute timestamp or unexpected starting day")
    nodes = np.sort(frame["TurbID"].unique()).astype(np.int64)
    node_index = np.searchsorted(nodes, frame["TurbID"].to_numpy())
    time_index = (frame["Day"].to_numpy(dtype=np.int64) - 1) * 144 + time_of_day.to_numpy(dtype=np.int64)
    n_times = int(time_index.max()) + 1
    identity = time_index * len(nodes) + node_index
    if len(identity) != n_times * len(nodes) or len(np.unique(identity)) != len(identity):
        raise ValueError("Duplicate or missing time/node coordinates")
    data = np.full((n_times, len(nodes), 4), np.nan, dtype=np.float32)
    for column, feature in (("Wspd", 0), ("Patv", 1), ("Prtv", 2)):
        values = frame[column].to_numpy()
        values = np.where(np.isfinite(values), values, np.nan)
        if column == "Wspd":
            values = np.where(values >= 0, values, np.nan)
        data[time_index, node_index, feature] = values
    pitch = frame[["Pab1", "Pab2", "Pab3"]].to_numpy(dtype=np.float64)
    valid_pitch = np.isfinite(pitch).all(axis=1)
    pitch_mean = np.full(len(frame), np.nan, dtype=np.float64)
    pitch_mean[valid_pitch] = pitch[valid_pitch].mean(axis=1)
    data[time_index, node_index, 3] = pitch_mean
    metadata = {
        "num_steps": n_times, "num_nodes": len(nodes), "node_ids": nodes.tolist(),
        "channels": ["wind", "power", "reactive", "pitch"],
        "day_start": 1, "day_end": int(frame["Day"].max()),
        "negative_power_cells_preserved": int(np.sum(data[..., 1] < 0)),
        "zero_power_cells_preserved": int(np.sum(data[..., 1] == 0)),
        "missing_counts": {name: int(np.sum(~np.isfinite(data[..., k])))
                           for k, name in enumerate(("wind", "power", "reactive", "pitch"))},
        "clock_status": "WTB event grid reconstructed; synthetic availability clock, not field arrival logs",
    }
    return data, nodes, metadata


def stages_for(protocol: dict[str, Any], n_times: int) -> dict[str, tuple[int, int]]:
    task = protocol["task"]
    horizon, release = task["horizon_steps"], task["target_release_delay_steps"]
    age, history = task["commitment_age_steps"], task["history_steps"]
    stages = {}
    for name, (first, last) in protocol["stage_days"].items():
        start = max((first - 1) * 144, history - 1)
        future = horizon + age if name == "point_fit" else horizon
        end = min(last * 144 - future - release, n_times - future)
        stages[name] = (start, end)
    validate_temporal_stages(stages, horizon=horizon, label_delay=release)
    if stages["point_fit"][1] - 1 + horizon + age + release >= stages["state_fit"][0]:
        raise ValueError("Point-forecast labels overlap state training")
    return stages


def history_matrix(data: np.ndarray, anchors: np.ndarray, channels: list[int], history: int, delay: int) -> np.ndarray:
    observed = arrived_history(data[..., channels], anchors, history, delay)
    return observed.transpose(0, 1, 3, 2).reshape(len(anchors) * data.shape[1], -1)


def common_matrix(forecast: np.ndarray, anchors: np.ndarray, n_nodes: int) -> np.ndarray:
    if forecast.shape != (len(anchors), n_nodes) or not np.isfinite(forecast).all():
        raise ValueError("Missing common published forecast")
    phase = 2 * np.pi * (anchors % 144) / 144
    result = np.column_stack((
        forecast.reshape(-1), np.repeat(np.sin(phase), n_nodes),
        np.repeat(np.cos(phase), n_nodes), np.tile(np.arange(n_nodes) / max(n_nodes - 1, 1), len(anchors)),
    ))
    return result.astype(np.float32)


def feature_groups(
    data: np.ndarray, anchors: np.ndarray, forecast: np.ndarray, history: int, delay: int, pitch_available: bool
) -> dict[str, np.ndarray]:
    common = common_matrix(forecast, anchors, data.shape[1])
    a_channels = [0, 3] if pitch_available else [0]
    a = np.column_stack((common, history_matrix(data, anchors, a_channels, history, delay)))
    b = np.column_stack((a, history_matrix(data, anchors, [1, 2], history, delay)))
    return {"A": a, "B": b}


def learner(settings: dict[str, Any], seed: int, quantile: bool) -> Pipeline:
    regressor = HistGradientBoostingRegressor(
        loss="quantile" if quantile else "squared_error", quantile=0.9 if quantile else None,
        max_iter=settings["max_iter"], max_leaf_nodes=settings["max_leaf_nodes"],
        min_samples_leaf=settings["min_samples_leaf"], learning_rate=settings["learning_rate"],
        l2_regularization=settings["l2_regularization"], early_stopping=False, random_state=seed,
    )
    # A constant uses no future observations. Indicators preserve arrival status;
    # keeping empty features supports structurally unavailable delayed channels.
    return Pipeline([("missing", SimpleImputer(strategy="constant", fill_value=0.0,
                       add_indicator=True, keep_empty_features=True)), ("regressor", regressor)])


def validate_protocol(protocol: dict[str, Any]) -> None:
    """Reject unsupported scientific settings instead of silently ignoring them."""
    task = protocol["task"]
    if task["rho"] != 10.0 or task["dt_hours"] != 1 / 6 or task["horizon_steps"] != 6:
        raise ValueError("This implementation supports only rho=10, dt=1/6 and h=6")
    if max(c["delay_steps"] for c in protocol["conditions"].values()) > task["commitment_age_steps"]:
        raise ValueError("Common commitment would be newer than the oldest information condition")
    if protocol["inference"]["certifies_minimum_sufficiency"] or protocol["confirmation"]["E07_activated"]:
        raise ValueError("Development implementation cannot certify or activate E07")


def subsample(mask: np.ndarray, maximum: int, seed: int) -> np.ndarray:
    indices = np.flatnonzero(mask)
    if not len(indices):
        raise ValueError("No fit observations")
    if len(indices) > maximum:
        indices = np.sort(np.random.default_rng(seed).choice(indices, maximum, replace=False))
    return indices


def prepare(args: argparse.Namespace, protocol: dict[str, Any]) -> None:
    out, raw = args.output, args.raw_csv
    info = receipt(out, args.protocol, [raw], {"stage": "prepare", "seed": protocol["task"]["point_forecaster_seed"]})
    if digest(raw) != protocol["data"]["raw_sha256"]:
        raise ValueError("Raw WTB bytes differ from the registered source")
    data, nodes, metadata = load_raw_csv(raw)
    if metadata["num_nodes"] != 134 or metadata["day_end"] != 245:
        raise ValueError("Protocol requires the specified WTB134 Day1-245 source")
    stages = stages_for(protocol, len(data))
    task, settings = protocol["task"], protocol["learner"]
    horizon, age, history = task["horizon_steps"], task["commitment_age_steps"], task["history_steps"]
    train_anchors = np.arange(*stages["point_fit"], dtype=np.int64)
    x = history_matrix(data, train_anchors, [0, 1], history, 0)
    y = data[train_anchors + horizon + age, :, 1].reshape(-1).astype(np.float64)
    indices = subsample(np.isfinite(y), settings["max_fit_rows"], task["point_forecaster_seed"])
    model = learner(settings, task["point_forecaster_seed"], False)
    model.fit(x[indices], y[indices])
    joblib.dump(model, out / "point_forecaster.joblib")
    np.save(out / "point_fit_sample_indices.npy", indices)
    np.save(out / "physical_channels.npy", data)
    np.save(out / "node_ids.npy", nodes)
    del x, y
    all_anchors = []
    all_forecasts = []
    for name in ("state_fit", "policy_fit", "calibration", "development_evaluation"):
        anchors = np.arange(*stages[name], dtype=np.int64)
        predictions = []
        for offset in range(0, len(anchors), 256):
            issues = anchors[offset:offset + 256]
            publication = issues - age
            if np.any(publication < history - 1):
                raise ValueError("Insufficient lawful commitment history")
            xx = history_matrix(data, publication, [0, 1], history, 0)
            predictions.append(np.maximum(model.predict(xx), 0).reshape(len(issues), len(nodes)))
        forecast = np.concatenate(predictions).astype(np.float32)
        np.savez_compressed(out / f"{name}_forecast.npz", anchors=anchors, forecast=forecast,
                            publication_indices=anchors - age, target_indices=anchors + horizon)
        all_anchors.append(anchors)
        all_forecasts.append(forecast)
    metadata["stages"] = stages
    metadata["protocol_sha256"] = digest(args.protocol)
    metadata["forecast_scope"] = "new historical-only commitment task; not old E04 canonical forecast"
    write_json(out / "data_manifest.json", metadata)
    finish(out, info)
    print("PREPARED", metadata["num_steps"], metadata["num_nodes"], flush=True)


def load_stage(prepared: Path, data: np.ndarray, name: str, condition: dict[str, Any], history: int, horizon: int) -> dict[str, Any]:
    with np.load(prepared / f"{name}_forecast.npz") as archive:
        anchors, forecast = archive["anchors"], archive["forecast"]
        if not np.array_equal(archive["target_indices"], anchors + horizon):
            raise ValueError("Frozen target coordinates changed")
    true = data[anchors + horizon, :, 1].astype(np.float64)
    mask = np.isfinite(true)
    shortfall = np.full(true.shape, np.nan, dtype=np.float64)
    shortfall[mask] = np.maximum(forecast.astype(np.float64)[mask] - true[mask], 0)
    groups = feature_groups(data, anchors, forecast, history, condition["delay_steps"], condition["pitch_available"])
    return {"anchors": anchors, "forecast": forecast, "true": true, "mask": mask, "shortfall": shortfall, **groups}


def fit_pitch_probes(
    data: np.ndarray, stage: dict[str, Any], settings: dict[str, Any], seed: int, out: Path
) -> dict[str, HistGradientBoostingRegressor]:
    target = data[stage["anchors"], :, 3].reshape(-1).astype(np.float64)
    indices = subsample(np.isfinite(target), settings["state_max_fit_rows"], seed)
    np.save(out / "state_fit_sample_indices.npy", indices)
    permutation = np.random.default_rng(seed + 10000).permutation(len(indices))
    np.save(out / "state_label_control_permutation.npy", permutation)
    result = {}
    for name, group, y in (("pitch", "B", target[indices]), ("wind", "A", target[indices]),
                           ("shuffle", "B", target[indices][permutation])):
        model = learner(settings, seed, False)
        model.fit(stage[group][indices], y)
        joblib.dump(model, out / f"state_{name}.joblib")
        result[name] = model
    return result


def augment(stage: dict[str, Any], probes: dict[str, Any], data: np.ndarray) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray]]:
    scores = {name: model.predict(stage["A" if name == "wind" else "B"]).astype(np.float32)
              for name, model in probes.items()}
    true_pitch = data[stage["anchors"], :, 3].reshape(-1)
    matrices = {
        "A_Wind": stage["A"], "B_Consequences": stage["B"],
        "C_PitchScore": np.column_stack((stage["B"], scores["pitch"])),
        "C_WindScore": np.column_stack((stage["B"], scores["wind"])),
        "C_ShuffledScore": np.column_stack((stage["B"], scores["shuffle"])),
        "E_Compressed": np.column_stack((stage["A"], scores["pitch"])),
        "D_TruePitch_Diagnostic": np.column_stack((stage["B"], true_pitch)),
    }
    return matrices, scores


def bin_policy(fit_wind: np.ndarray, fit_s: np.ndarray, valid: np.ndarray, winds: dict[str, np.ndarray]) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    usable = valid & np.isfinite(fit_wind)
    global_q = float(np.quantile(fit_s[valid], 0.9, method="higher"))
    edges = np.unique(np.quantile(fit_wind[usable], np.linspace(0, 1, 11)[1:-1])) if usable.any() else np.array([])
    memberships = np.searchsorted(edges, fit_wind, side="right")
    quantiles = []
    for index in range(len(edges) + 1):
        selected = usable & (memberships == index)
        quantiles.append(float(np.quantile(fit_s[selected], 0.9, method="higher")) if selected.sum() >= 50 else global_q)
    predictions = {}
    for name, wind in winds.items():
        values = np.full(len(wind), global_q)
        available = np.isfinite(wind)
        values[available] = np.asarray(quantiles)[np.searchsorted(edges, wind[available], side="right")]
        predictions[name] = values
    return predictions, {"edges": edges.tolist(), "quantiles": quantiles, "missing_fallback": global_q}


def run_seed(args: argparse.Namespace, protocol: dict[str, Any]) -> None:
    prepared, out = args.prepared, args.output
    if args.seed not in protocol["seeds"] or args.condition not in protocol["conditions"]:
        raise ValueError("Unregistered seed or information condition")
    producer = verify_bundle(prepared, digest(args.protocol), "prepare")
    inputs = [prepared / "physical_channels.npy", prepared / "data_manifest.json",
              *[prepared / f"{s}_forecast.npz" for s in ("state_fit", "policy_fit", "calibration", "development_evaluation")]]
    info = receipt(out, args.protocol, inputs, {"stage": "run", "seed": args.seed, "condition": args.condition})
    info["prepared_manifest_sha256"] = digest(prepared / "output_manifest.json")
    info["raw_input_sha256"] = producer["input_sha256"]
    manifest = json.loads((prepared / "data_manifest.json").read_text())
    if manifest["protocol_sha256"] != digest(args.protocol):
        raise ValueError("Prepared data belongs to another protocol")
    data = np.load(prepared / "physical_channels.npy", mmap_mode="r")
    condition, settings, task = protocol["conditions"][args.condition], protocol["learner"], protocol["task"]
    start = time.monotonic()
    state_stage = load_stage(prepared, data, "state_fit", condition, task["history_steps"], task["horizon_steps"])
    probes = fit_pitch_probes(data, state_stage, settings, args.seed, out)
    del state_stage
    stages = {name: load_stage(prepared, data, name, condition, task["history_steps"], task["horizon_steps"])
              for name in ("policy_fit", "calibration", "development_evaluation")}
    matrices = {}
    scores = {}
    for name, stage in stages.items():
        matrices[name], scores[name] = augment(stage, probes, data)
    fit, calibration, evaluation = (stages[name] for name in ("policy_fit", "calibration", "development_evaluation"))
    indices = subsample(fit["mask"].reshape(-1), settings["max_fit_rows"], args.seed)
    np.save(out / "policy_fit_sample_indices.npy", indices)
    np.savez_compressed(out / "evaluation_coordinates.npz", anchors=evaluation["anchors"],
                        node_ids=np.asarray(manifest["node_ids"]), target_indices=evaluation["anchors"] + task["horizon_steps"],
                        publication_indices=evaluation["anchors"] - task["commitment_age_steps"],
                        forecast=evaluation["forecast"], realized=evaluation["true"],
                        shortfall=evaluation["shortfall"], mask=evaluation["mask"],
                        true_pitch=data[evaluation["anchors"], :, 3], **scores["development_evaluation"])
    raw_predictions, cal_predictions = {}, {}
    wind_position = 4 + task["history_steps"] - 1 - condition["delay_steps"]
    winds = {name: stage["A"][:, wind_position] for name, stage in stages.items()}
    binned, bin_info = bin_policy(winds["policy_fit"], fit["shortfall"].reshape(-1), fit["mask"].reshape(-1), winds)
    cal_predictions["WindBins"] = binned["calibration"]
    raw_predictions["WindBins"] = binned["development_evaluation"]
    write_json(out / "wind_bins.json", bin_info)
    model_records = {}
    for variant in protocol["variants"]:
        if variant == "WindBins":
            continue
        timer = time.monotonic()
        model = learner(settings, args.seed, True)
        model.fit(matrices["policy_fit"][variant][indices], fit["shortfall"].reshape(-1)[indices])
        joblib.dump(model, out / f"policy_{variant}.joblib")
        cal_predictions[variant] = np.maximum(model.predict(matrices["calibration"][variant]), 0)
        raw_predictions[variant] = np.maximum(model.predict(matrices["development_evaluation"][variant]), 0)
        model_records[variant] = {"fit_seconds": time.monotonic() - timer,
                                  "n_features": int(model.n_features_in_), "n_iter": int(model.named_steps["regressor"].n_iter_)}
        print(args.seed, args.condition, variant, model_records[variant], flush=True)
    block_output = {}
    actions = {}
    rows = []
    offsets = {}
    valid_cal = calibration["mask"].reshape(-1)
    for variant in protocol["variants"]:
        correction = float(np.quantile(calibration["shortfall"].reshape(-1)[valid_cal] - cal_predictions[variant][valid_cal], 0.9, method="higher"))
        offsets[variant] = correction
        raw = raw_predictions[variant].reshape(evaluation["shortfall"].shape)
        reserve = np.maximum(raw + correction, 0)
        actions[variant + "_raw"] = raw.astype(np.float64)
        actions[variant] = reserve.astype(np.float64)
        for version, values in (("raw", raw), ("calibrated", reserve)):
            totals = block_totals(evaluation["shortfall"], values, evaluation["mask"], evaluation["anchors"])
            for key, value in totals.items():
                block_output[f"{variant}__{version}__{key}"] = value
            count = float(totals["count"].sum())
            rows.append({"seed": args.seed, "condition": args.condition, "variant": variant, "version": version,
                         "n_cells": int(count), "psrei_kwh": float(totals["loss_sum"].sum()),
                         "mean_loss_kwh_per_cell": float(totals["loss_sum"].sum() / count),
                         "violation_rate": float(totals["violation_sum"].sum() / count),
                         "reserve_kwh": float(totals["reserve_sum"].sum()),
                         "shortage_kwh": float(totals["shortage_sum"].sum())})
    np.savez_compressed(out / "evaluation_actions.npz", **actions)
    np.savez_compressed(out / "block_totals.npz", **block_output)
    pd.DataFrame(rows).to_csv(out / "metrics.csv", index=False)
    write_json(out / "calibration_offsets.json", offsets)
    model_records["total_seconds"] = time.monotonic() - start
    state_y = data[evaluation["anchors"], :, 3].reshape(-1).astype(np.float64)
    state_valid = np.isfinite(state_y)
    model_records["continuous_pitch_mse_degrees_squared"] = {
        key: float(np.mean((prediction[state_valid] - state_y[state_valid]) ** 2))
        for key, prediction in scores["development_evaluation"].items()}
    model_records["state_diagnostic_cells"] = int(state_valid.sum())
    model_records["probe_input_scope"] = "Base-information probe includes available pitch in fresh/delayed conditions; wind history only plus commitment metadata under pitch withholding"
    write_json(out / "models_and_diagnostics.json", model_records)
    finish(out, info)
    print("COMPLETED", args.seed, args.condition, time.monotonic() - start, flush=True)


def aggregate(args: argparse.Namespace, protocol: dict[str, Any]) -> None:
    expected = [args.runs / f"seed{seed}" / name for seed in protocol["seeds"] for name in protocol["conditions"]]
    missing = [str(path) for path in expected if not (path / "output_manifest.json").exists()]
    if missing:
        raise ValueError("Incomplete registered seed/condition grid: " + json.dumps(missing))
    inputs = [path / "block_totals.npz" for path in expected] + [path / "metrics.csv" for path in expected]
    info = receipt(args.output, args.protocol, inputs, {"stage": "aggregate", "n_boot": protocol["inference"]["n_boot"]})
    frames = []
    prepared_hashes = set()
    common_coordinates = None
    for path in expected:
        producer = verify_bundle(path, digest(args.protocol), "run", int(path.parent.name[4:]), path.name)
        prepared_hashes.add(producer["prepared_manifest_sha256"])
        with np.load(path / "evaluation_coordinates.npz") as coords:
            identity = {key: hashlib.sha256(np.ascontiguousarray(coords[key]).tobytes()).hexdigest()
                        for key in ("anchors", "node_ids", "target_indices", "publication_indices", "forecast", "realized", "shortfall", "mask")}
        if common_coordinates is None:
            common_coordinates = identity
        elif identity != common_coordinates:
            raise ValueError("Cross-run target/coordinate/forecast/mask identity mismatch")
        frames.append(pd.read_csv(path / "metrics.csv"))
    if len(prepared_hashes) != 1:
        raise ValueError("Runs used different prepared bundles")
    all_metrics = pd.concat(frames, ignore_index=True)
    all_metrics.to_csv(args.output / "all_metrics.csv", index=False)
    comparisons = protocol["inference"]["comparisons_per_condition"]
    family = len(comparisons) * len(protocol["conditions"])
    intervals = []
    indices_hashes = set()
    for condition in protocol["conditions"]:
        loaded = [np.load(args.runs / f"seed{seed}" / condition / "block_totals.npz") for seed in protocol["seeds"]]
        count = loaded[0]["A_Wind__calibrated__count"]
        block_ids = loaded[0]["A_Wind__calibrated__block_ids"]
        if np.any(np.diff(block_ids) != 1):
            raise ValueError("Temporal blocks are not contiguous")
        for archive in loaded:
            for variant in protocol["variants"]:
                if not np.array_equal(archive[f"{variant}__calibrated__count"], count):
                    raise ValueError("Candidate mask/count mismatch")
                if not np.array_equal(archive[f"{variant}__calibrated__block_ids"], block_ids):
                    raise ValueError("Candidate time-block mismatch")
        for metric in ("loss_sum", "violation_sum", "reserve_sum", "shortage_sum"):
            matrix = np.asarray([[archive[f"{variant}__calibrated__{metric}"] for variant in protocol["variants"]]
                                 for archive in loaded])
            for left, right in comparisons:
                for span in [protocol["inference"]["moving_block_span_days"], *protocol["inference"]["sensitivity_spans_days"]]:
                    result = paired_interval(matrix, count, protocol["variants"].index(left), protocol["variants"].index(right),
                                             n_boot=protocol["inference"]["n_boot"], block_span=span,
                                             seed=protocol["inference"]["resampling_seed"], family_size=family)
                    result.update(condition=condition, metric=metric, left=left, right=right)
                    result["inference_role"] = "primary_loss_family" if metric == "loss_sum" and span == protocol["inference"]["moving_block_span_days"] else "descriptive_sensitivity_only"
                    intervals.append(result)
                    if span == protocol["inference"]["moving_block_span_days"]:
                        indices_hashes.add(result["bootstrap_indices_sha256"])
        for archive in loaded:
            archive.close()
    if len(indices_hashes) != 1:
        raise ValueError("Conditions do not share the registered temporal resampling")
    write_json(args.output / "paired_intervals.json", intervals)
    summary = all_metrics.groupby(["condition", "variant", "version"], as_index=False).agg(
        mean_loss=("mean_loss_kwh_per_cell", "mean"), seed_sd=("mean_loss_kwh_per_cell", "std"),
        violation_rate=("violation_rate", "mean"), reserve_kwh=("reserve_kwh", "mean"),
        shortage_kwh=("shortage_kwh", "mean"), n_seeds=("seed", "nunique"))
    summary.to_csv(args.output / "summary.csv", index=False)
    write_json(args.output / "verdict.json", {
        "status": "COMPLETED_DEVELOPMENT_NOT_CONFIRMATORY", "n_seeds": len(protocol["seeds"]),
        "n_conditions": len(protocol["conditions"]), "family_size": family,
        "minimum_sufficiency_certified": False, "E07_activated": False,
        "practical_effect_delta": protocol["inference"]["practical_effect_delta"],
        "claim_limit": "Realizable flow comparisons for a new historical-commitment task; no pure information-value, hidden-state causality or deployment certification",
    })
    finish(args.output, info)
    print(summary.to_string(index=False), flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("prepare", "run", "aggregate"))
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--raw-csv", type=Path)
    parser.add_argument("--prepared", type=Path)
    parser.add_argument("--runs", type=Path)
    parser.add_argument("--seed", type=int, default=201)
    parser.add_argument("--condition", default="pitch_withheld")
    parser.add_argument("--threads", type=int, default=2)
    args = parser.parse_args()
    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    validate_protocol(protocol)
    with threadpool_limits(limits=args.threads):
        if args.stage == "prepare":
            if args.raw_csv is None:
                raise ValueError("prepare requires --raw-csv")
            prepare(args, protocol)
        elif args.stage == "run":
            if args.prepared is None:
                raise ValueError("run requires --prepared")
            run_seed(args, protocol)
        else:
            if args.runs is None:
                raise ValueError("aggregate requires --runs")
            aggregate(args, protocol)


if __name__ == "__main__":
    main()
