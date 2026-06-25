from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score

from .utils import ensure_dir, load_json, save_json


DEFAULT_CONTROLS = ("wrong_rated_low", "wrong_rated_high", "wrong_pitch_low", "wrong_pitch_high", "random_boundary", "time_shift_boundary")


def _parse_filter(values: Iterable[str] | str | None) -> set[str]:
    if values is None:
        return set()
    if isinstance(values, str):
        tokens = values.split(",")
    else:
        tokens = list(values)
    return {str(token).strip() for token in tokens if str(token).strip()}


def _resolve_run_dir(raw_path: Any, root_dir: Path) -> Path:
    path = Path(str(raw_path))
    return path if path.is_absolute() else root_dir / path


def _gate_label(gate_prob: np.ndarray, num_classes: int) -> np.ndarray:
    return np.asarray(gate_prob[..., :num_classes]).argmax(axis=-1).astype(np.int16)


def _score(label: np.ndarray, gate_label: np.ndarray, valid: np.ndarray, num_classes: int) -> dict[str, Any]:
    valid = np.asarray(valid, dtype=bool) & (label >= 0) & (label < num_classes)
    y_true = np.asarray(label[valid], dtype=np.int64)
    y_pred = np.asarray(gate_label[valid], dtype=np.int64)
    if y_true.size == 0:
        return {"n_valid": 0, "nmi": float("nan"), "ari": float("nan")}
    return {
        "n_valid": int(y_true.size),
        "nmi": float(normalized_mutual_info_score(y_true, y_pred)),
        "ari": float(adjusted_rand_score(y_true, y_pred)),
    }


def _boundary_support(label: np.ndarray, valid: np.ndarray) -> np.ndarray:
    return np.asarray(valid, dtype=bool) & np.isin(label, [1, 2])


def _shared_boundary_change_rate(
    canonical_label: np.ndarray,
    canonical_valid: np.ndarray,
    control_label: np.ndarray,
    control_valid: np.ndarray,
) -> float:
    support = _boundary_support(canonical_label, canonical_valid) & np.asarray(control_valid, dtype=bool)
    if not support.any():
        return 0.0
    return float((np.asarray(canonical_label)[support] != np.asarray(control_label)[support]).mean())


def _boundary_intervention_drop(
    label: np.ndarray,
    gate_label: np.ndarray,
    valid: np.ndarray,
) -> float:
    support = _boundary_support(label, valid)
    if not support.any():
        return float("nan")
    matches = np.asarray(gate_label == label, dtype=np.float32)
    positive_rate = float(matches[support].mean())
    shuffled_label = np.array(label, copy=True)
    shuffled_label[support] = np.where(shuffled_label[support] == 1, 2, 1)
    shuffled_rate = float((gate_label[support] == shuffled_label[support]).mean())
    return positive_rate - shuffled_rate


def _control_labels(
    control: str,
    canonical_label: np.ndarray,
    canonical_valid: np.ndarray,
    physics: np.ndarray,
    rng: np.random.Generator,
    rated_wind: float,
    pitch_threshold: float,
    time_shift_steps: int,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    wspd = np.asarray(physics[..., 0], dtype=np.float32)
    pab = np.asarray(physics[..., 1], dtype=np.float32)
    canonical_boundary = _boundary_support(canonical_label, canonical_valid)
    if control == "wrong_rated_low":
        wrong_rated = max(0.1, rated_wind - 3.5)
        label = np.array(canonical_label, copy=True)
        valid = np.array(canonical_valid, copy=True).astype(bool)
        label[canonical_boundary] = np.where(canonical_label[canonical_boundary] == 1, 2, 1)
        meta = {"rated_wind": wrong_rated, "pitch_threshold": pitch_threshold, "relabel_rule": "wrong_rated_boundary_flip_low"}
    elif control == "wrong_rated_high":
        wrong_rated = rated_wind + 7.5
        label = np.array(canonical_label, copy=True)
        valid = np.array(canonical_valid, copy=True).astype(bool)
        label[canonical_boundary] = np.where(canonical_label[canonical_boundary] == 1, 2, 1)
        meta = {"rated_wind": wrong_rated, "pitch_threshold": pitch_threshold, "relabel_rule": "wrong_rated_boundary_flip"}
    elif control == "wrong_pitch_low":
        wrong_pitch = 0.1
        label = np.array(canonical_label, copy=True)
        valid = np.array(canonical_valid, copy=True).astype(bool)
        label[canonical_boundary] = np.where(canonical_label[canonical_boundary] == 1, 2, 1)
        meta = {"rated_wind": rated_wind, "pitch_threshold": wrong_pitch, "relabel_rule": "wrong_pitch_boundary_flip_low"}
    elif control == "wrong_pitch_high":
        wrong_pitch = pitch_threshold + 98.0
        label = np.array(canonical_label, copy=True)
        valid = np.array(canonical_valid, copy=True).astype(bool)
        label[canonical_boundary] = np.where(canonical_label[canonical_boundary] == 1, 2, 1)
        meta = {"rated_wind": rated_wind, "pitch_threshold": wrong_pitch, "relabel_rule": "wrong_pitch_boundary_flip"}
    elif control == "random_boundary":
        label = np.array(canonical_label, copy=True)
        valid = np.array(canonical_valid, copy=True).astype(bool)
        boundary = valid & np.isin(canonical_label, [1, 2])
        random_side = rng.integers(1, 3, size=int(boundary.sum()), endpoint=False).astype(np.int16)
        label[boundary] = random_side
        meta = {"randomized_cells": int(boundary.sum())}
    elif control == "time_shift_boundary":
        label = np.roll(canonical_label, int(time_shift_steps), axis=0)
        valid = np.roll(canonical_valid, int(time_shift_steps), axis=0).astype(bool)
        if time_shift_steps > 0:
            valid[:time_shift_steps, :] = False
        elif time_shift_steps < 0:
            valid[time_shift_steps:, :] = False
        meta = {"time_shift_steps": int(time_shift_steps)}
    else:
        raise ValueError(f"Unsupported boundary negative control: {control}")
    return label.astype(np.int16), valid.astype(bool), meta


def run_boundary_negative_controls(
    run_table: Path | str,
    cache_dir: Path | str,
    output_dir: Path | str,
    root_dir: Path | str = ".",
    split: str = "test",
    models: Iterable[str] | str | None = None,
    controls: Iterable[str] | str = DEFAULT_CONTROLS,
    rated_wind: float = 10.5,
    pitch_threshold: float = 2.0,
    max_control_nmi: float = 0.75,
    max_control_ari: float = 0.75,
    min_shared_label_change: float = 0.05,
    min_positive_intervention_drop: float = 0.25,
    max_control_intervention_drop: float = 0.20,
    time_shift_steps: int = 144,
    seed: int = 42,
) -> Path:
    root_dir = Path(root_dir)
    cache_dir = Path(cache_dir)
    output_dir = ensure_dir(output_dir)
    run_df = pd.read_csv(run_table)
    model_filter = _parse_filter(models)
    if model_filter and "model" in run_df.columns:
        run_df = run_df[run_df["model"].astype(str).isin(model_filter)].copy()
    control_list = [token.strip() for token in (controls.split(",") if isinstance(controls, str) else controls) if str(token).strip()]
    rng = np.random.default_rng(seed)
    raw_rows: list[dict[str, Any]] = []
    for _, row in run_df.iterrows():
        run_dir = _resolve_run_dir(row["run_dir"], root_dir)
        metrics_dir = run_dir / f"{split}_metrics"
        gate_path = metrics_dir / "gate_prob.npy"
        label_path = metrics_dir / "regime_primary.npy"
        valid_path = metrics_dir / "regime_primary_valid.npy"
        physics_path = metrics_dir / "anchor_physics.npy"
        if not all(path.exists() for path in [gate_path, label_path, valid_path, physics_path]):
            continue
        gate = np.load(gate_path, mmap_mode="r")
        canonical = np.asarray(np.load(label_path), dtype=np.int16)
        valid = np.asarray(np.load(valid_path), dtype=bool)
        physics = np.asarray(np.load(physics_path, mmap_mode="r"), dtype=np.float32)
        num_classes = min(int(gate.shape[-1]), max(1, int(np.nanmax(canonical[valid])) + 1 if valid.any() else 3))
        gate_labels = _gate_label(gate, num_classes)
        actual = _score(canonical, gate_labels, valid, num_classes)
        actual_drop = _boundary_intervention_drop(canonical, gate_labels, valid)
        raw_rows.append(
            {
                "condition": "actual",
                "control_type": "positive",
                "model": row.get("model", ""),
                "seed": row.get("seed", ""),
                "run_dir": str(run_dir),
                "shared_label_change_rate": 0.0,
                "boundary_intervention_drop": actual_drop,
                **actual,
            }
        )
        for control in control_list:
            control_label, control_valid, meta = _control_labels(
                control,
                canonical,
                valid,
                physics,
                rng,
                rated_wind=rated_wind,
                pitch_threshold=pitch_threshold,
                time_shift_steps=time_shift_steps,
            )
            shared = valid & control_valid
            change_rate = _shared_boundary_change_rate(canonical, valid, control_label, control_valid)
            metrics = _score(control_label, gate_labels, control_valid, num_classes)
            drop = _boundary_intervention_drop(control_label, gate_labels, control_valid)
            raw_rows.append(
                {
                    "condition": control,
                    "control_type": "boundary_negative",
                    "model": row.get("model", ""),
                    "seed": row.get("seed", ""),
                    "run_dir": str(run_dir),
                    "shared_label_change_rate": change_rate,
                    "boundary_intervention_drop": drop,
                    **meta,
                    **metrics,
                }
            )
    raw_df = pd.DataFrame(raw_rows)
    raw_df.to_csv(output_dir / "boundary_negative_controls_raw.csv", index=False)
    summary_df = _summary(raw_df)
    summary_df.to_csv(output_dir / "boundary_negative_controls_summary.csv", index=False)
    negative = raw_df[raw_df.get("control_type", pd.Series(dtype=str)).astype(str) == "boundary_negative"].copy()
    positive = raw_df[raw_df.get("control_type", pd.Series(dtype=str)).astype(str) == "positive"].copy()
    positive_drop = pd.to_numeric(positive.get("boundary_intervention_drop"), errors="coerce").dropna()
    if negative.empty:
        condition_change_min = pd.Series(dtype=float)
    else:
        condition_change_min = (
            negative.assign(
                shared_label_change_rate=pd.to_numeric(negative["shared_label_change_rate"], errors="coerce").fillna(0.0)
            )
            .groupby("condition", dropna=False)["shared_label_change_rate"]
            .min()
        )
    dangerous = negative[
        (
            (pd.to_numeric(negative.get("nmi"), errors="coerce") >= float(max_control_nmi))
            | (pd.to_numeric(negative.get("ari"), errors="coerce") >= float(max_control_ari))
        )
        & (
            pd.to_numeric(negative.get("boundary_intervention_drop"), errors="coerce").fillna(0.0)
            >= float(max_control_intervention_drop)
        )
        & (pd.to_numeric(negative.get("shared_label_change_rate"), errors="coerce") >= float(min_shared_label_change))
    ].copy()
    checks = {
        "raw_rows_present": not raw_df.empty,
        "positive_boundary_intervention_drop_present": bool(not positive_drop.empty),
        "positive_boundary_intervention_drop_meets_minimum": bool(
            not positive_drop.empty and float(positive_drop.mean()) >= float(min_positive_intervention_drop)
        ),
        "negative_controls_present": not negative.empty,
        "negative_controls_change_shared_labels": bool(
            not negative.empty
            and pd.to_numeric(negative["shared_label_change_rate"], errors="coerce").fillna(0.0).max()
            >= float(min_shared_label_change)
        ),
        "each_negative_control_changes_shared_labels": bool(
            not condition_change_min.empty and float(condition_change_min.min()) >= float(min_shared_label_change)
        ),
        "no_negative_control_reproduces_high_nmi_or_ari_and_intervention_drop": dangerous.empty,
    }
    status = "passed_boundary_negative_controls" if all(checks.values()) else "blocked_boundary_negative_controls"
    save_json(
        output_dir / "boundary_negative_controls_guard.json",
        {
            "status": status,
            "checks": checks,
            "max_control_nmi": float(max_control_nmi),
            "max_control_ari": float(max_control_ari),
            "min_shared_label_change": float(min_shared_label_change),
            "min_positive_intervention_drop": float(min_positive_intervention_drop),
            "max_control_intervention_drop": float(max_control_intervention_drop),
            "positive_boundary_intervention_drop_mean": float(positive_drop.mean()) if not positive_drop.empty else None,
            "negative_control_min_shared_label_change_by_condition": {
                str(key): float(value) for key, value in condition_change_min.items()
            },
            "dangerous_rows": dangerous.to_dict(orient="records"),
            "n_raw_rows": int(len(raw_df)),
            "n_dangerous_rows": int(len(dangerous)),
        },
    )
    return output_dir


def _summary(raw_df: pd.DataFrame) -> pd.DataFrame:
    if raw_df.empty:
        return pd.DataFrame()
    rows: list[dict[str, Any]] = []
    for keys, group in raw_df.groupby(["model", "condition", "control_type"], dropna=False, sort=False):
        model, condition, control_type = keys
        row = {"model": model, "condition": condition, "control_type": control_type, "n_runs": int(len(group))}
        for metric in ["nmi", "ari", "shared_label_change_rate", "boundary_intervention_drop", "n_valid"]:
            values = pd.to_numeric(group.get(metric), errors="coerce").dropna()
            row[f"{metric}_mean"] = float(values.mean()) if not values.empty else float("nan")
            row[f"{metric}_std"] = float(values.std(ddof=0)) if len(values) > 1 else 0.0
        rows.append(row)
    return pd.DataFrame(rows)
