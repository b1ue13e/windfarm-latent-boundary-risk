from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

from .utils import ensure_dir, save_json


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


def run_mechanism_behavior_pack(
    run_table: Path | str,
    output_dir: Path | str,
    root_dir: Path | str = ".",
    split: str = "test",
    models: Iterable[str] | str | None = None,
    rated_wind: float = 10.5,
    boundary_band: float = 1.0,
    top_k_failures: int = 20,
) -> Path:
    root_dir = Path(root_dir)
    output_dir = ensure_dir(output_dir)
    run_df = pd.read_csv(run_table)
    model_filter = _parse_filter(models)
    if model_filter and "model" in run_df.columns:
        run_df = run_df[run_df["model"].astype(str).isin(model_filter)].copy()
    expert_rows: list[dict[str, Any]] = []
    boundary_rows: list[dict[str, Any]] = []
    lead_lag_rows: list[dict[str, Any]] = []
    residual_rows: list[dict[str, Any]] = []
    failure_rows: list[dict[str, Any]] = []
    for _, row in run_df.iterrows():
        run_dir = _resolve_run_dir(row["run_dir"], root_dir)
        metrics_dir = run_dir / f"{split}_metrics"
        required = ["pred.npy", "target.npy", "mask.npy", "regime_primary.npy", "regime_primary_valid.npy", "anchor_physics.npy"]
        if any(not (metrics_dir / name).exists() for name in required):
            continue
        pred = np.asarray(np.load(metrics_dir / "pred.npy", mmap_mode="r"), dtype=np.float64)
        target = np.asarray(np.load(metrics_dir / "target.npy", mmap_mode="r"), dtype=np.float64)
        mask = np.asarray(np.load(metrics_dir / "mask.npy", mmap_mode="r"), dtype=np.float64)
        regime = np.asarray(np.load(metrics_dir / "regime_primary.npy"), dtype=np.int16)
        valid = np.asarray(np.load(metrics_dir / "regime_primary_valid.npy"), dtype=bool)
        physics = np.asarray(np.load(metrics_dir / "anchor_physics.npy", mmap_mode="r"), dtype=np.float64)
        gate_path = metrics_dir / "gate_prob.npy"
        if not gate_path.exists():
            continue
        gate = np.asarray(np.load(gate_path, mmap_mode="r"), dtype=np.float64)
        gate_label = gate[..., : max(1, min(gate.shape[-1], 3))].argmax(axis=-1)
        error = np.nan_to_num(pred - target, nan=0.0)
        mse_node = ((error**2) * mask).sum(axis=1) / np.maximum(mask.sum(axis=1), 1.0)
        rmse_node = np.sqrt(mse_node)
        wspd = physics[..., 0]
        power = physics[..., 3] if physics.shape[-1] > 3 else np.nan_to_num(target[:, 0, :], nan=0.0)
        boundary = valid & np.isin(regime, [1, 2]) & (np.abs(wspd - float(rated_wind)) <= float(boundary_band))
        non_boundary = valid & np.isin(regime, [1, 2]) & (np.abs(wspd - float(rated_wind)) > float(boundary_band))
        base = {
            "model": row.get("model", ""),
            "seed": row.get("seed", ""),
            "run_dir": str(run_dir),
            "split": split,
        }
        for selector_name, selector in [("boundary", boundary), ("non_boundary_mppt_pitch", non_boundary)]:
            values = rmse_node[selector]
            boundary_rows.append(
                {
                    **base,
                    "slice": selector_name,
                    "n_cells": int(values.size),
                    "rmse_mean": float(values.mean()) if values.size else float("nan"),
                    "rmse_p90": float(np.quantile(values, 0.90)) if values.size else float("nan"),
                }
            )
        for expert in range(gate.shape[-1]):
            selector = valid & (gate_label == expert)
            for regime_id in [0, 1, 2]:
                regime_selector = selector & (regime == regime_id)
                expert_rows.append(
                    {
                        **base,
                        "expert": int(expert),
                        "regime_id": int(regime_id),
                        "n_cells": int(regime_selector.sum()),
                        "wspd_mean": _safe_mean(wspd[regime_selector]),
                        "power_mean": _safe_mean(power[regime_selector]),
                        "rmse_mean": _safe_mean(rmse_node[regime_selector]),
                    }
                )
        residual_rows.extend(_residual_distribution_rows(base, regime, valid, rmse_node))
        lead_lag_rows.extend(_lead_lag_rows(base, regime, gate_label, valid))
        failure_rows.extend(_failure_rows(base, regime, valid, gate_label, rmse_node, wspd, top_k_failures))
    outputs = {
        "expert_power_curve.csv": pd.DataFrame(expert_rows),
        "boundary_error_decomposition.csv": pd.DataFrame(boundary_rows),
        "gate_transition_lead_lag.csv": pd.DataFrame(lead_lag_rows),
        "regime_residual_distribution.csv": pd.DataFrame(residual_rows),
        "gate_correct_high_error_cases.csv": pd.DataFrame(failure_rows),
    }
    for name, df in outputs.items():
        df.to_csv(output_dir / name, index=False)
    checks = {
        "expert_power_curve_nonempty": not outputs["expert_power_curve.csv"].empty,
        "boundary_error_decomposition_nonempty": not outputs["boundary_error_decomposition.csv"].empty,
        "gate_transition_lead_lag_nonempty": not outputs["gate_transition_lead_lag.csv"].empty,
        "regime_residual_distribution_nonempty": not outputs["regime_residual_distribution.csv"].empty,
        "gate_correct_high_error_cases_nonempty": not outputs["gate_correct_high_error_cases.csv"].empty,
    }
    status = "complete_ready_for_mechanism_behavior_evidence" if all(checks.values()) else "blocked_incomplete_mechanism_behavior_pack"
    save_json(
        output_dir / "mechanism_behavior_pack_config.json",
        {
            "status": status,
            "split": split,
            "rated_wind": float(rated_wind),
            "boundary_band": float(boundary_band),
            "top_k_failures": int(top_k_failures),
            "outputs": {name: int(len(df)) for name, df in outputs.items()},
            "checks": checks,
        },
    )
    save_json(
        output_dir / "mechanism_behavior_pack_guard.json",
        {
            "status": status,
            "checks": checks,
            "outputs": {name: int(len(df)) for name, df in outputs.items()},
        },
    )
    return output_dir


def _safe_mean(values: np.ndarray) -> float:
    values = np.asarray(values, dtype=np.float64)
    values = values[np.isfinite(values)]
    return float(values.mean()) if values.size else float("nan")


def _residual_distribution_rows(base: dict[str, Any], regime: np.ndarray, valid: np.ndarray, rmse_node: np.ndarray) -> list[dict[str, Any]]:
    rows = []
    for regime_id in [0, 1, 2]:
        selector = valid & (regime == regime_id)
        values = rmse_node[selector]
        rows.append(
            {
                **base,
                "regime_id": int(regime_id),
                "n_cells": int(values.size),
                "rmse_mean": float(values.mean()) if values.size else float("nan"),
                "rmse_p50": float(np.quantile(values, 0.50)) if values.size else float("nan"),
                "rmse_p90": float(np.quantile(values, 0.90)) if values.size else float("nan"),
                "rmse_p95": float(np.quantile(values, 0.95)) if values.size else float("nan"),
            }
        )
    return rows


def _lead_lag_rows(base: dict[str, Any], regime: np.ndarray, gate_label: np.ndarray, valid: np.ndarray) -> list[dict[str, Any]]:
    rows = []
    changes = (regime[1:] != regime[:-1]) & valid[1:] & valid[:-1]
    for lag in [-6, -3, 0, 3, 6]:
        matches = []
        rows_idx, nodes_idx = np.where(changes)
        for row, node in zip(rows_idx, nodes_idx):
            gate_row = row + 1 + lag
            if gate_row < 0 or gate_row >= gate_label.shape[0]:
                continue
            matches.append(int(gate_label[gate_row, node] == regime[row + 1, node]))
        rows.append(
            {
                **base,
                "lag_steps": int(lag),
                "n_transitions": int(len(matches)),
                "gate_matches_new_regime_rate": float(np.mean(matches)) if matches else float("nan"),
            }
        )
    return rows


def _failure_rows(
    base: dict[str, Any],
    regime: np.ndarray,
    valid: np.ndarray,
    gate_label: np.ndarray,
    rmse_node: np.ndarray,
    wspd: np.ndarray,
    top_k: int,
) -> list[dict[str, Any]]:
    gate_correct = valid & (gate_label == regime)
    positions = np.argwhere(gate_correct)
    if positions.size == 0 or top_k <= 0:
        return []
    values = rmse_node[gate_correct]
    order = np.argsort(values)[::-1][: int(top_k)]
    rows = []
    for idx in order:
        row_idx, node_idx = positions[idx]
        rows.append(
            {
                **base,
                "window_idx": int(row_idx),
                "node_idx": int(node_idx),
                "regime_id": int(regime[row_idx, node_idx]),
                "gate_label": int(gate_label[row_idx, node_idx]),
                "rmse": float(rmse_node[row_idx, node_idx]),
                "wspd_anchor": float(wspd[row_idx, node_idx]),
            }
        )
    return rows
