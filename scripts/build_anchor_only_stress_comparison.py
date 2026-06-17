from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score
from torch.utils.data import DataLoader, Subset

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from windfarm_moe.config import ModelConfig
from windfarm_moe.data import RegimeWindowDataset, load_cache_bundle
from windfarm_moe.model import RegimeAwareForecaster
from windfarm_moe.utils import ensure_dir, load_json, save_json, to_device


PROPOSED = "MoE + L_bal + L_align + L_force"
ANCHOR_ONLY = "Anchor-only router"
CONTEXT = "Context-supervised router"
DEFAULT_MODELS = (PROPOSED, ANCHOR_ONLY, CONTEXT)
DEFAULT_SCENARIOS = (
    "actual",
    "anchor_boundary_missing",
    "anchor_all_missing",
    "anchor_boundary_noise_0p25std",
    "anchor_boundary_noise_0p5std",
    "anchor_boundary_noise_1p0std",
    "boundary_fuzzy",
    "anchor_boundary_node_shuffle",
    "domain_shift",
    "few_label_10pct",
    "partial_label_pitch_only",
)
ROBUSTNESS_SCENARIOS = {
    "anchor_boundary_missing",
    "anchor_all_missing",
    "anchor_boundary_noise_0p25std",
    "anchor_boundary_noise_0p5std",
    "anchor_boundary_noise_1p0std",
    "anchor_boundary_node_shuffle",
    "domain_shift",
    "few_label_10pct",
    "partial_label_pitch_only",
}


def _finite_float(value: Any) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return float("nan")
    return out if np.isfinite(out) else float("nan")


def _fmt(value: Any, digits: int = 2) -> str:
    out = _finite_float(value)
    if not np.isfinite(out):
        return "NA"
    return f"{out:.{digits}f}"


def _parse_tokens(raw: str | None, default: tuple[str, ...]) -> list[str]:
    if raw is None or not str(raw).strip():
        return list(default)
    return [token.strip() for token in str(raw).split(",") if token.strip()]


def _resolve_run_dir(raw_path: Any, root_dir: Path) -> Path:
    run_dir = Path(str(raw_path))
    return run_dir if run_dir.is_absolute() else root_dir / run_dir


def _load_model(run_dir: Path, bundle: Any, device: torch.device) -> RegimeAwareForecaster:
    checkpoint_path = run_dir / "best_model.pt"
    checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=False)
    model_config = ModelConfig(**checkpoint["model_config"])
    mode = str(checkpoint["train_config"]["mode"])
    model = RegimeAwareForecaster(
        feature_dim=int(bundle.features.shape[-1]),
        pred_len=int(bundle.metadata["pred_len"]),
        mode=mode,
        config=model_config,
    ).to(device)
    model.load_state_dict(checkpoint["model_state"])
    model.eval()
    return model


def _masked_metrics(pred: np.ndarray, target: np.ndarray, mask: np.ndarray) -> dict[str, float]:
    weight = np.asarray(mask, dtype=np.float64)
    safe_pred = np.nan_to_num(np.asarray(pred, dtype=np.float64), nan=0.0)
    safe_target = np.nan_to_num(np.asarray(target, dtype=np.float64), nan=0.0)
    denom = max(float(weight.sum()), 1.0)
    mae = float((np.abs(safe_pred - safe_target) * weight).sum() / denom)
    rmse = float(np.sqrt((((safe_pred - safe_target) ** 2) * weight).sum() / denom))
    return {"mae": mae, "rmse": rmse}


def _switch_selector(regime: np.ndarray, steps_per_hour: int) -> np.ndarray:
    window = max(1, 3 * int(steps_per_hour))
    selector = np.zeros_like(regime, dtype=bool)
    if regime.shape[0] <= 1:
        return selector
    changes = regime[1:] != regime[:-1]
    rows, nodes = np.where(changes)
    for row, node in zip(rows, nodes):
        lo = max(0, row + 1 - window)
        hi = min(regime.shape[0], row + 2 + window)
        selector[lo:hi, node] = True
    return selector


def _gate_metrics(
    gate_prob: np.ndarray | None,
    regime: np.ndarray,
    valid: np.ndarray,
    primary_num_classes: int,
    selector: np.ndarray | None = None,
) -> dict[str, Any]:
    if gate_prob is None:
        return {
            "n_gate_cells": 0,
            "gate_accuracy": float("nan"),
            "nmi": float("nan"),
            "ari": float("nan"),
        }
    usable = np.asarray(valid, dtype=bool)
    if selector is not None:
        usable = usable & np.asarray(selector, dtype=bool)
    usable = usable & (regime >= 0) & (regime < int(primary_num_classes))
    labels = np.asarray(gate_prob[..., : int(primary_num_classes)]).argmax(axis=-1)
    flat_true = np.asarray(regime[usable], dtype=np.int64)
    flat_pred = np.asarray(labels[usable], dtype=np.int64)
    n_classes = int(np.unique(flat_true).size) if flat_true.size else 0
    return {
        "n_gate_cells": int(flat_true.size),
        "gate_accuracy": float(np.mean(flat_true == flat_pred)) if flat_true.size else float("nan"),
        "nmi": float(normalized_mutual_info_score(flat_true, flat_pred)) if n_classes >= 2 else float("nan"),
        "ari": float(adjusted_rand_score(flat_true, flat_pred)) if n_classes >= 2 else float("nan"),
    }


def _physics_stats(bundle: Any, names: list[str]) -> dict[str, Any]:
    physics = np.asarray(bundle.physics)
    out: dict[str, Any] = {"names": names}
    for name in ["Wspd", "Pab_mean"]:
        idx = names.index(name) if name in names else None
        if idx is None:
            continue
        values = physics[..., idx]
        finite = values[np.isfinite(values)]
        out[f"{name}_std"] = float(np.std(finite)) if finite.size else 1.0
    return out


def _deterministic_noise_like(values: torch.Tensor) -> torch.Tensor:
    order = torch.arange(values.numel(), device=values.device, dtype=values.dtype).reshape_as(values)
    return torch.sin(order * 12.9898 + 78.233)


def _scenario_noise_scale(scenario: str) -> float | None:
    match = re.search(r"anchor_boundary_noise_([0-9]+)p([0-9]+)std", scenario)
    if not match:
        return None
    return float(f"{match.group(1)}.{match.group(2)}")


def _deterministic_keep_mask(anchor: torch.Tensor, keep_fraction: float) -> torch.Tensor:
    order = torch.arange(anchor.shape[0] * anchor.shape[1], device=anchor.device, dtype=anchor.dtype).reshape(
        anchor.shape[0],
        anchor.shape[1],
    )
    score = torch.frac(torch.sin(order * 12.9898 + 78.233) * 43758.5453).abs()
    return score < float(keep_fraction)


def _mutate_anchor(
    batch: dict[str, torch.Tensor],
    scenario: str,
    *,
    wspd_idx: int,
    pab_idx: int,
    rated_wind: float,
    pitch_threshold: float,
    boundary_band: float,
    wspd_std: float,
    pab_std: float,
) -> dict[str, torch.Tensor]:
    if scenario == "actual":
        return batch
    mutated = dict(batch)
    anchor = mutated["anchor_physics"].clone()
    boundary_indices = [int(wspd_idx), int(pab_idx)]
    if scenario == "anchor_boundary_missing":
        anchor[..., boundary_indices] = 0.0
    elif scenario == "anchor_all_missing":
        anchor[...] = 0.0
    elif _scenario_noise_scale(scenario) is not None:
        noise_scale = float(_scenario_noise_scale(scenario))
        values = anchor[..., boundary_indices]
        scale = torch.tensor([wspd_std, pab_std], dtype=values.dtype, device=values.device).view(1, 1, 2)
        anchor[..., boundary_indices] = values + noise_scale * scale * _deterministic_noise_like(values)
    elif scenario == "boundary_fuzzy":
        wspd = anchor[..., int(wspd_idx)]
        pab = anchor[..., int(pab_idx)]
        regime = mutated["regime_primary"]
        valid = mutated["regime_primary_valid"].bool()
        boundary = valid & ((regime == 1) | (regime == 2)) & (torch.abs(wspd - float(rated_wind)) <= float(boundary_band))
        anchor[..., int(wspd_idx)] = torch.where(
            boundary,
            torch.full_like(wspd, float(rated_wind)),
            wspd,
        )
        anchor[..., int(pab_idx)] = torch.where(
            boundary,
            torch.full_like(pab, float(pitch_threshold)),
            pab,
        )
    elif scenario == "anchor_boundary_node_shuffle":
        anchor[..., boundary_indices] = torch.roll(anchor[..., boundary_indices], shifts=1, dims=1)
    elif scenario == "domain_shift":
        anchor[..., int(wspd_idx)] = anchor[..., int(wspd_idx)] * 1.15 + 0.5
        anchor[..., int(pab_idx)] = anchor[..., int(pab_idx)] + 0.5 * float(pab_std)
    elif scenario == "few_label_10pct":
        keep = _deterministic_keep_mask(anchor, 0.10)
        anchor[..., boundary_indices] = torch.where(
            keep.unsqueeze(-1),
            anchor[..., boundary_indices],
            torch.zeros_like(anchor[..., boundary_indices]),
        )
    elif scenario == "partial_label_pitch_only":
        anchor[..., int(wspd_idx)] = 0.0
    else:
        raise ValueError(f"Unsupported scenario: {scenario}")
    mutated["anchor_physics"] = anchor
    return mutated


def _evaluate_scenario(
    model: RegimeAwareForecaster,
    loader: DataLoader,
    bundle: Any,
    device: torch.device,
    scenario: str,
    *,
    wspd_idx: int,
    pab_idx: int,
    rated_wind: float,
    pitch_threshold: float,
    boundary_band: float,
    physics_stats: dict[str, Any],
) -> dict[str, Any]:
    pred_batches: list[np.ndarray] = []
    target_batches: list[np.ndarray] = []
    mask_batches: list[np.ndarray] = []
    regime_batches: list[np.ndarray] = []
    valid_batches: list[np.ndarray] = []
    anchor_batches: list[np.ndarray] = []
    gate_batches: list[np.ndarray] = []

    with torch.no_grad():
        for batch in loader:
            batch = to_device(batch, device)
            anchor_batches.append(batch["anchor_physics"].detach().cpu().numpy())
            batch = _mutate_anchor(
                batch,
                scenario,
                wspd_idx=wspd_idx,
                pab_idx=pab_idx,
                rated_wind=rated_wind,
                pitch_threshold=pitch_threshold,
                boundary_band=boundary_band,
                wspd_std=float(physics_stats.get("Wspd_std", 1.0) or 1.0),
                pab_std=float(physics_stats.get("Pab_mean_std", 1.0) or 1.0),
            )
            pred, gate_prob, _ = model(
                batch["x_hist"],
                batch["edge_index_hist"],
                batch["edge_weight_hist"],
                batch["feature_mask_hist"],
                batch["anchor_physics"],
            )
            pred_batches.append(pred.detach().cpu().numpy())
            target_batches.append(batch["target"].detach().cpu().numpy())
            mask_batches.append(batch["target_mask"].detach().cpu().numpy())
            regime_batches.append(batch["regime_primary"].detach().cpu().numpy())
            valid_batches.append(batch["regime_primary_valid"].detach().cpu().numpy())
            if gate_prob is not None:
                gate_batches.append(gate_prob.detach().cpu().numpy())

    pred = np.concatenate(pred_batches, axis=0)
    target = np.concatenate(target_batches, axis=0)
    mask = np.concatenate(mask_batches, axis=0)
    regime = np.concatenate(regime_batches, axis=0)
    valid = np.concatenate(valid_batches, axis=0).astype(bool)
    anchor_physics = np.concatenate(anchor_batches, axis=0)
    gate_prob = np.concatenate(gate_batches, axis=0) if gate_batches else None

    primary_num_classes = int(bundle.metadata["primary_num_classes"])
    switch = _switch_selector(regime, int(bundle.metadata.get("steps_per_hour", 6)))
    pitch_id = list(bundle.metadata.get("primary_regime_names", [])).index("pitch_control")
    pitch = valid & (regime == int(pitch_id))
    wspd = anchor_physics[..., int(wspd_idx)]
    boundary = valid & ((regime == 1) | (regime == 2)) & (np.abs(wspd - float(rated_wind)) <= float(boundary_band))

    overall = _masked_metrics(pred, target, mask)
    switch_metrics = _masked_metrics(pred, target, mask * switch[:, None, :])
    pitch_metrics = _masked_metrics(pred, target, mask * pitch[:, None, :])
    boundary_metrics = _masked_metrics(pred, target, mask * boundary[:, None, :])
    gate = _gate_metrics(gate_prob, regime, valid, primary_num_classes)
    boundary_gate = _gate_metrics(gate_prob, regime, valid, primary_num_classes, boundary)
    pitch_gate = _gate_metrics(gate_prob, regime, valid, primary_num_classes, pitch)

    gate_label = None
    if gate_prob is not None:
        gate_label = np.asarray(gate_prob[..., :primary_num_classes]).argmax(axis=-1)

    return {
        "overall_mae": overall["mae"],
        "overall_rmse": overall["rmse"],
        "switch_mae": switch_metrics["mae"],
        "switch_rmse": switch_metrics["rmse"],
        "pitch_control_mae": pitch_metrics["mae"],
        "pitch_control_rmse": pitch_metrics["rmse"],
        "boundary_mae": boundary_metrics["mae"],
        "boundary_rmse": boundary_metrics["rmse"],
        "nmi": gate["nmi"],
        "ari": gate["ari"],
        "gate_accuracy": gate["gate_accuracy"],
        "boundary_nmi": boundary_gate["nmi"],
        "boundary_ari": boundary_gate["ari"],
        "boundary_gate_accuracy": boundary_gate["gate_accuracy"],
        "pitch_control_gate_accuracy": pitch_gate["gate_accuracy"],
        "n_gate_cells": gate["n_gate_cells"],
        "n_boundary_cells": int(boundary.sum()),
        "n_pitch_cells": int(pitch.sum()),
        "gate_prob": gate_prob,
        "gate_label": gate_label,
        "valid": valid,
    }


def _drop_arrays(row: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if key not in {"gate_prob", "gate_label", "valid"}}


def _summary(raw_df: pd.DataFrame) -> pd.DataFrame:
    if raw_df.empty:
        return pd.DataFrame()
    metric_cols = [
        "overall_rmse",
        "switch_rmse",
        "pitch_control_rmse",
        "boundary_rmse",
        "nmi",
        "ari",
        "gate_accuracy",
        "boundary_nmi",
        "boundary_ari",
        "boundary_gate_accuracy",
        "pitch_control_gate_accuracy",
        "dominant_flip_rate",
        "mean_gate_l1",
        "n_boundary_cells",
        "n_pitch_cells",
    ]
    rows: list[dict[str, Any]] = []
    for keys, group in raw_df.groupby(["scenario", "model"], sort=False):
        scenario, model = keys
        out: dict[str, Any] = {"scenario": scenario, "model": model, "n_runs": int(len(group))}
        for metric in metric_cols:
            values = pd.to_numeric(group.get(metric), errors="coerce").dropna()
            out[f"{metric}_mean"] = float(values.mean()) if not values.empty else float("nan")
            out[f"{metric}_std"] = float(values.std(ddof=0)) if len(values) > 1 else 0.0
        rows.append(out)
    return pd.DataFrame(rows)


def _attach_degradation(raw_df: pd.DataFrame) -> pd.DataFrame:
    if raw_df.empty:
        return raw_df
    actual = raw_df[raw_df["scenario"] == "actual"].copy()
    controls = raw_df[raw_df["scenario"] != "actual"].copy()
    if actual.empty or controls.empty:
        return raw_df
    metric_cols = ["overall_rmse", "switch_rmse", "pitch_control_rmse", "boundary_rmse", "nmi", "ari"]
    actual_cols = ["model", "seed", "run_dir"] + metric_cols
    merged = controls.merge(actual[actual_cols], on=["model", "seed", "run_dir"], suffixes=("", "_actual"))
    for metric in ["overall_rmse", "switch_rmse", "pitch_control_rmse", "boundary_rmse"]:
        merged[f"delta_{metric}"] = merged[metric] - merged[f"{metric}_actual"]
    for metric in ["nmi", "ari"]:
        merged[f"drop_{metric}"] = merged[f"{metric}_actual"] - merged[metric]
    return merged


def _degradation_summary(degradation: pd.DataFrame) -> pd.DataFrame:
    if degradation.empty:
        return pd.DataFrame()
    metric_cols = [
        "delta_overall_rmse",
        "delta_switch_rmse",
        "delta_pitch_control_rmse",
        "delta_boundary_rmse",
        "drop_nmi",
        "drop_ari",
    ]
    rows: list[dict[str, Any]] = []
    for keys, group in degradation.groupby(["scenario", "model"], sort=False):
        scenario, model = keys
        out: dict[str, Any] = {"scenario": scenario, "model": model, "n_runs": int(len(group))}
        for metric in metric_cols:
            values = pd.to_numeric(group.get(metric), errors="coerce").dropna()
            out[f"{metric}_mean"] = float(values.mean()) if not values.empty else float("nan")
            out[f"{metric}_std"] = float(values.std(ddof=0)) if len(values) > 1 else 0.0
        rows.append(out)
    return pd.DataFrame(rows)


def _paired_model_effects(summary: pd.DataFrame) -> pd.DataFrame:
    if summary.empty:
        return pd.DataFrame()
    rows: list[dict[str, Any]] = []
    for scenario in summary["scenario"].dropna().astype(str).unique():
        proposed = summary[(summary["scenario"].astype(str) == scenario) & (summary["model"].astype(str) == PROPOSED)]
        anchor = summary[(summary["scenario"].astype(str) == scenario) & (summary["model"].astype(str) == ANCHOR_ONLY)]
        if proposed.empty or anchor.empty:
            continue
        p = proposed.iloc[0]
        a = anchor.iloc[0]
        for metric in [
            "overall_rmse",
            "switch_rmse",
            "pitch_control_rmse",
            "boundary_rmse",
            "nmi",
            "ari",
            "gate_accuracy",
            "boundary_nmi",
            "boundary_ari",
            "boundary_gate_accuracy",
            "pitch_control_gate_accuracy",
        ]:
            col = f"{metric}_mean"
            if col not in summary.columns:
                continue
            rows.append(
                {
                    "scenario": scenario,
                    "metric": metric,
                    "proposed_mean": _finite_float(p.get(col)),
                    "anchor_only_mean": _finite_float(a.get(col)),
                    "proposed_minus_anchor_only": _finite_float(p.get(col)) - _finite_float(a.get(col)),
                }
            )
    return pd.DataFrame(rows)


def _paired_degradation_effects(degradation: pd.DataFrame) -> pd.DataFrame:
    if degradation.empty:
        return pd.DataFrame()
    proposed = degradation[degradation["model"].astype(str) == PROPOSED].copy()
    anchor = degradation[degradation["model"].astype(str) == ANCHOR_ONLY].copy()
    if proposed.empty or anchor.empty:
        return pd.DataFrame()
    metric_cols = [
        "delta_overall_rmse",
        "delta_switch_rmse",
        "delta_pitch_control_rmse",
        "delta_boundary_rmse",
        "drop_nmi",
        "drop_ari",
    ]
    merged = proposed.merge(
        anchor[["scenario", "seed"] + metric_cols],
        on=["scenario", "seed"],
        suffixes=("_proposed", "_anchor_only"),
    )
    rows: list[dict[str, Any]] = []
    for scenario, group in merged.groupby("scenario", sort=False):
        out: dict[str, Any] = {"scenario": scenario, "n_seed_pairs": int(len(group))}
        for metric in metric_cols:
            delta = pd.to_numeric(group[f"{metric}_proposed"], errors="coerce") - pd.to_numeric(
                group[f"{metric}_anchor_only"], errors="coerce"
            )
            delta = delta.dropna()
            out[f"proposed_minus_anchor_only_{metric}_mean"] = float(delta.mean()) if not delta.empty else float("nan")
            out[f"proposed_minus_anchor_only_{metric}_std"] = float(delta.std(ddof=0)) if len(delta) > 1 else 0.0
            if metric.startswith("delta_"):
                out[f"proposed_less_degraded_rate_{metric}"] = float((delta < 0.0).mean()) if not delta.empty else float("nan")
            else:
                out[f"proposed_smaller_drop_rate_{metric}"] = float((delta < 0.0).mean()) if not delta.empty else float("nan")
        rows.append(out)
    return pd.DataFrame(rows)


def _necessity_summary(
    summary: pd.DataFrame,
    degradation_summary: pd.DataFrame,
    degradation_effects: pd.DataFrame,
    scenarios: list[str],
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for scenario in scenarios:
        proposed = summary[(summary["scenario"].astype(str) == scenario) & (summary["model"].astype(str) == PROPOSED)]
        anchor = summary[(summary["scenario"].astype(str) == scenario) & (summary["model"].astype(str) == ANCHOR_ONLY)]
        if proposed.empty or anchor.empty:
            continue
        p = proposed.iloc[0]
        a = anchor.iloc[0]
        effect = degradation_effects[degradation_effects["scenario"].astype(str).eq(scenario)]
        deg_p = degradation_summary[
            (degradation_summary["scenario"].astype(str) == scenario)
            & (degradation_summary["model"].astype(str) == PROPOSED)
        ]
        deg_a = degradation_summary[
            (degradation_summary["scenario"].astype(str) == scenario)
            & (degradation_summary["model"].astype(str) == ANCHOR_ONLY)
        ]
        rmse_delta = _finite_float(p.get("overall_rmse_mean")) - _finite_float(a.get("overall_rmse_mean"))
        pitch_delta = _finite_float(p.get("pitch_control_rmse_mean")) - _finite_float(a.get("pitch_control_rmse_mean"))
        boundary_delta = _finite_float(p.get("boundary_rmse_mean")) - _finite_float(a.get("boundary_rmse_mean"))
        nmi_delta = _finite_float(p.get("nmi_mean")) - _finite_float(a.get("nmi_mean"))
        ari_delta = _finite_float(p.get("ari_mean")) - _finite_float(a.get("ari_mean"))
        effect_row: Any = effect.iloc[0] if not effect.empty else {}
        paired_overall = _finite_float(effect_row.get("proposed_minus_anchor_only_delta_overall_rmse_mean"))
        paired_pitch = _finite_float(effect_row.get("proposed_minus_anchor_only_delta_pitch_control_rmse_mean"))
        paired_boundary = _finite_float(effect_row.get("proposed_minus_anchor_only_delta_boundary_rmse_mean"))
        paired_nmi_drop = _finite_float(effect_row.get("proposed_minus_anchor_only_drop_nmi_mean"))
        robust = scenario in ROBUSTNESS_SCENARIOS
        trainable_needed = bool(
            robust
            and (
                (np.isfinite(paired_overall) and paired_overall < 0.0)
                or (np.isfinite(paired_pitch) and paired_pitch < 0.0)
                or (np.isfinite(paired_boundary) and paired_boundary < 0.0)
                or (np.isfinite(paired_nmi_drop) and paired_nmi_drop < 0.0)
                or (np.isfinite(rmse_delta) and rmse_delta < 0.0)
                or (np.isfinite(pitch_delta) and pitch_delta < 0.0)
                or (np.isfinite(boundary_delta) and boundary_delta < 0.0)
            )
        )
        clean_anchor_semantic_win = bool(
            scenario == "actual"
            and np.isfinite(nmi_delta)
            and np.isfinite(ari_delta)
            and nmi_delta < 0.0
            and ari_delta < 0.0
        )
        if trainable_needed:
            claim_label = "trainable_router_necessary_under_stress"
        elif clean_anchor_semantic_win:
            claim_label = "anchor_only_clean_semantic_control_wins"
        elif rmse_delta < 0.0 or pitch_delta < 0.0 or boundary_delta < 0.0:
            claim_label = "trainable_router_forecast_advantage"
        else:
            claim_label = "anchor_only_not_dominated"
        rows.append(
            {
                "scenario": scenario,
                "claim_label": claim_label,
                "claim_scope": "robustness_only" if robust else "clean_anchor_control",
                "anchor_only_wins_clean_semantic_nmi_ari": clean_anchor_semantic_win,
                "trainable_router_necessary": trainable_needed,
                "proposed_overall_rmse_mean": _finite_float(p.get("overall_rmse_mean")),
                "anchor_only_overall_rmse_mean": _finite_float(a.get("overall_rmse_mean")),
                "proposed_minus_anchor_only_overall_rmse": rmse_delta,
                "proposed_pitch_rmse_mean": _finite_float(p.get("pitch_control_rmse_mean")),
                "anchor_only_pitch_rmse_mean": _finite_float(a.get("pitch_control_rmse_mean")),
                "proposed_minus_anchor_only_pitch_rmse": pitch_delta,
                "proposed_boundary_rmse_mean": _finite_float(p.get("boundary_rmse_mean")),
                "anchor_only_boundary_rmse_mean": _finite_float(a.get("boundary_rmse_mean")),
                "proposed_minus_anchor_only_boundary_rmse": boundary_delta,
                "proposed_nmi_mean": _finite_float(p.get("nmi_mean")),
                "anchor_only_nmi_mean": _finite_float(a.get("nmi_mean")),
                "proposed_minus_anchor_only_nmi": nmi_delta,
                "proposed_ari_mean": _finite_float(p.get("ari_mean")),
                "anchor_only_ari_mean": _finite_float(a.get("ari_mean")),
                "proposed_minus_anchor_only_ari": ari_delta,
                "proposed_gate_flip_rate_mean": _finite_float(p.get("dominant_flip_rate_mean")),
                "anchor_only_gate_flip_rate_mean": _finite_float(a.get("dominant_flip_rate_mean")),
                "proposed_minus_anchor_only_seed_paired_delta_overall_rmse": paired_overall,
                "proposed_minus_anchor_only_seed_paired_delta_pitch_rmse": paired_pitch,
                "proposed_minus_anchor_only_seed_paired_delta_boundary_rmse": paired_boundary,
                "proposed_minus_anchor_only_seed_paired_drop_nmi": paired_nmi_drop,
                "proposed_delta_overall_rmse_mean": _finite_float(deg_p.iloc[0].get("delta_overall_rmse_mean"))
                if not deg_p.empty
                else float("nan"),
                "anchor_only_delta_overall_rmse_mean": _finite_float(deg_a.iloc[0].get("delta_overall_rmse_mean"))
                if not deg_a.empty
                else float("nan"),
                "n_seed_pairs": int(effect_row.get("n_seed_pairs", 0)),
            }
        )
    return pd.DataFrame(rows)


def _write_necessity_json(output_dir: Path, necessity: pd.DataFrame) -> None:
    trainable = (
        necessity.loc[necessity.get("trainable_router_necessary", pd.Series(dtype=bool)).astype(bool), "scenario"]
        .dropna()
        .astype(str)
        .tolist()
        if not necessity.empty and "scenario" in necessity
        else []
    )
    anchor_wins = (
        necessity.loc[
            necessity.get("anchor_only_wins_clean_semantic_nmi_ari", pd.Series(dtype=bool)).astype(bool),
            "scenario",
        ]
        .dropna()
        .astype(str)
        .tolist()
        if not necessity.empty and "scenario" in necessity
        else []
    )
    save_json(
        output_dir / "anchor_router_necessity_summary.json",
        {
            "artifact": "anchor_router_necessity",
            "claim_gate": "robustness_or_partial_supervision_only",
            "allowed_claim": "Trainable/context-aware routing may be claimed as necessary only under noisy, missing, domain-shift, few-label, or partial-label anchor conditions.",
            "forbidden_claim": "Do not claim clean-anchor semantic NMI/ARI is universally better than anchor-only.",
            "trainable_router_necessary_scenarios": trainable,
            "anchor_only_clean_semantic_win_scenarios": anchor_wins,
            "n_scenarios": int(len(necessity)),
        },
    )


def _read_value(df: pd.DataFrame, scenario: str, model: str, column: str) -> float:
    if df.empty:
        return float("nan")
    subset = df[(df["scenario"].astype(str) == scenario) & (df["model"].astype(str) == model)]
    if subset.empty or column not in subset.columns:
        return float("nan")
    return _finite_float(subset.iloc[0][column])


def _write_report(
    output_dir: Path,
    summary: pd.DataFrame,
    degradation_summary: pd.DataFrame,
    degradation_effects: pd.DataFrame,
    necessity: pd.DataFrame,
    scenarios: list[str],
) -> None:
    lines = [
        "# Anchor-only stress comparison",
        "",
        "This audit replays the same strict-cache checkpoints under anchor perturbations. It asks whether a router that only sees anchor physics remains sufficient when anchor cues are missing, noisy, or ambiguous.",
        "",
        "## Actual-test baseline",
        "",
        f"- Overall RMSE proposed/anchor-only: {_fmt(_read_value(summary, 'actual', PROPOSED, 'overall_rmse_mean'))}/{_fmt(_read_value(summary, 'actual', ANCHOR_ONLY, 'overall_rmse_mean'))}.",
        f"- Pitch-control RMSE proposed/anchor-only: {_fmt(_read_value(summary, 'actual', PROPOSED, 'pitch_control_rmse_mean'))}/{_fmt(_read_value(summary, 'actual', ANCHOR_ONLY, 'pitch_control_rmse_mean'))}.",
        f"- Semantic NMI/ARI proposed: {_fmt(_read_value(summary, 'actual', PROPOSED, 'nmi_mean'), 4)}/{_fmt(_read_value(summary, 'actual', PROPOSED, 'ari_mean'), 4)}; anchor-only: {_fmt(_read_value(summary, 'actual', ANCHOR_ONLY, 'nmi_mean'), 4)}/{_fmt(_read_value(summary, 'actual', ANCHOR_ONLY, 'ari_mean'), 4)}.",
        "",
        "## Stress degradation",
        "",
    ]
    if degradation_summary.empty:
        lines.append("No stress degradation rows were available.")
    else:
        for scenario in scenarios:
            if scenario == "actual":
                continue
            p_rmse = _read_value(degradation_summary, scenario, PROPOSED, "delta_overall_rmse_mean")
            a_rmse = _read_value(degradation_summary, scenario, ANCHOR_ONLY, "delta_overall_rmse_mean")
            p_nmi = _read_value(degradation_summary, scenario, PROPOSED, "drop_nmi_mean")
            a_nmi = _read_value(degradation_summary, scenario, ANCHOR_ONLY, "drop_nmi_mean")
            lines.append(
                f"- {scenario}: overall RMSE degradation proposed/anchor-only = {_fmt(p_rmse)}/{_fmt(a_rmse)}; "
                f"NMI drop = {_fmt(p_nmi, 4)}/{_fmt(a_nmi, 4)}."
            )
    if not degradation_effects.empty:
        lines.extend(["", "## Seed-paired proposed-vs-anchor-only degradation", ""])
        for _, row in degradation_effects.iterrows():
            lines.append(
                f"- {row['scenario']}: proposed-minus-anchor degradation "
                f"overall RMSE {_fmt(row.get('proposed_minus_anchor_only_delta_overall_rmse_mean'))}, "
                f"pitch RMSE {_fmt(row.get('proposed_minus_anchor_only_delta_pitch_control_rmse_mean'))}, "
                f"NMI drop {_fmt(row.get('proposed_minus_anchor_only_drop_nmi_mean'), 4)}; "
                f"seed pairs {int(row.get('n_seed_pairs', 0))}."
            )
    if not necessity.empty:
        needed = necessity[necessity["trainable_router_necessary"].astype(bool)]["scenario"].astype(str).tolist()
        clean_anchor = necessity[necessity["anchor_only_wins_clean_semantic_nmi_ari"].astype(bool)]["scenario"].astype(str).tolist()
        lines.extend(["", "## Necessity claim gate", ""])
        lines.append(
            "Trainable-router necessity is scoped to noisy, missing, shifted, few-label, or partial-label anchor conditions; clean-anchor semantic NMI/ARI is treated as an anchor-only control."
        )
        lines.append(f"- Trainable-router necessary scenarios: {', '.join(needed) if needed else 'none'}")
        lines.append(f"- Anchor-only clean semantic wins: {', '.join(clean_anchor) if clean_anchor else 'none'}")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "Anchor-only remains the stronger direct semantic label copier under clean anchors. The learned router is only justified where clean hand anchors are not the operating condition: pitch-control forecasting, held-out spatial forecasting, and perturbation settings where context can compensate for unreliable anchor channels.",
            "",
            "## Output files",
            "",
            "- anchor_stress_raw.csv",
            "- anchor_stress_summary.csv",
            "- anchor_stress_degradation.csv",
            "- anchor_stress_degradation_summary.csv",
            "- anchor_stress_model_effects.csv",
            "- anchor_stress_degradation_effects.csv",
            "- anchor_router_necessity_summary.csv",
            "- anchor_router_necessity_summary.json",
            "",
        ]
    )
    (output_dir / "anchor_stress_report.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-table", default="artifacts/strictmask_ablation_export_20260613/tables/wtb_test_aggregated_runs.csv")
    parser.add_argument("--cache-dir", default="artifacts/cache_strictmask/wtb_245d")
    parser.add_argument("--output-dir", default="artifacts/anchor_only_decisive_comparison_20260613")
    parser.add_argument("--root-dir", default=".")
    parser.add_argument("--models", default=",".join(DEFAULT_MODELS))
    parser.add_argument("--scenarios", default=",".join(DEFAULT_SCENARIOS))
    parser.add_argument("--seeds", default="")
    parser.add_argument("--max-windows", type=int, default=0)
    parser.add_argument("--split", default="test")
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--rated-wind", type=float, default=10.5)
    parser.add_argument("--pitch-threshold", type=float, default=2.0)
    parser.add_argument("--boundary-band", type=float, default=1.0)
    args = parser.parse_args()

    root_dir = Path(args.root_dir)
    output_dir = ensure_dir(root_dir / Path(args.output_dir))
    run_table = pd.read_csv(root_dir / Path(args.run_table))
    models = set(_parse_tokens(args.models, DEFAULT_MODELS))
    scenarios = _parse_tokens(args.scenarios, DEFAULT_SCENARIOS)
    run_table = run_table[run_table["model"].astype(str).isin(models)].copy()
    seed_filter = {int(token) for token in _parse_tokens(args.seeds, ())}
    if seed_filter and "seed" in run_table.columns:
        run_table = run_table[pd.to_numeric(run_table["seed"], errors="coerce").astype("Int64").isin(seed_filter)].copy()
    if run_table.empty:
        raise ValueError("No matching runs in run table.")

    bundle = load_cache_bundle(root_dir / Path(args.cache_dir), mmap_mode="r")
    physics_names = [str(name) for name in bundle.metadata.get("physics_names", [])]
    wspd_idx = physics_names.index("Wspd") if "Wspd" in physics_names else 0
    pab_idx = physics_names.index("Pab_mean") if "Pab_mean" in physics_names else 1
    stats = _physics_stats(bundle, physics_names)
    device = torch.device("cuda" if args.device == "auto" and torch.cuda.is_available() else ("cpu" if args.device == "auto" else args.device))
    base_dataset = RegimeWindowDataset(bundle, args.split, int(bundle.metadata["hist_len"]), int(bundle.metadata["pred_len"]))
    if int(args.max_windows) > 0:
        dataset = Subset(base_dataset, list(range(min(int(args.max_windows), len(base_dataset)))))
    else:
        dataset = base_dataset
    loader = DataLoader(dataset, batch_size=int(args.batch_size), shuffle=False, num_workers=0, pin_memory=device.type == "cuda")

    rows: list[dict[str, Any]] = []
    for _, run_row in run_table.sort_values(["model", "seed"]).iterrows():
        run_dir = _resolve_run_dir(run_row["run_dir"], root_dir)
        if not (run_dir / "best_model.pt").exists():
            continue
        print(f"Loading {run_row.get('model', '')} seed {run_row.get('seed', '')}: {run_dir}", flush=True)
        model = _load_model(run_dir, bundle, device)
        actual_for_run: dict[str, Any] | None = None
        for scenario in scenarios:
            print(f"  scenario={scenario}", flush=True)
            metrics = _evaluate_scenario(
                model,
                loader,
                bundle,
                device,
                scenario,
                wspd_idx=wspd_idx,
                pab_idx=pab_idx,
                rated_wind=float(args.rated_wind),
                pitch_threshold=float(args.pitch_threshold),
                boundary_band=float(args.boundary_band),
                physics_stats=stats,
            )
            if scenario == "actual":
                actual_for_run = metrics
                flip_rate = 0.0
                mean_gate_l1 = 0.0
            elif actual_for_run is not None and metrics.get("gate_label") is not None and actual_for_run.get("gate_label") is not None:
                valid = np.asarray(actual_for_run["valid"], dtype=bool)
                flip_rate = float(np.mean(metrics["gate_label"][valid] != actual_for_run["gate_label"][valid])) if valid.any() else float("nan")
                mean_gate_l1 = float(np.abs(metrics["gate_prob"] - actual_for_run["gate_prob"]).mean())
            else:
                flip_rate = float("nan")
                mean_gate_l1 = float("nan")
            rows.append(
                {
                    "dataset": run_row.get("dataset", bundle.metadata.get("dataset", "")),
                    "model": run_row.get("model", ""),
                    "seed": run_row.get("seed", ""),
                    "variant_key": run_row.get("variant_key", ""),
                    "experiment_group": run_row.get("experiment_group", ""),
                    "run_dir": str(run_dir),
                    "split": args.split,
                    "scenario": scenario,
                    "dominant_flip_rate": flip_rate,
                    "mean_gate_l1": mean_gate_l1,
                    **_drop_arrays(metrics),
                }
            )
        model.to("cpu")
        del model
        if device.type == "cuda":
            torch.cuda.empty_cache()

    raw_df = pd.DataFrame(rows)
    raw_df.to_csv(output_dir / "anchor_stress_raw.csv", index=False)
    summary = _summary(raw_df)
    summary.to_csv(output_dir / "anchor_stress_summary.csv", index=False)
    degradation = _attach_degradation(raw_df)
    degradation.to_csv(output_dir / "anchor_stress_degradation.csv", index=False)
    degradation_summary = _degradation_summary(degradation)
    degradation_summary.to_csv(output_dir / "anchor_stress_degradation_summary.csv", index=False)
    model_effects = _paired_model_effects(summary)
    model_effects.to_csv(output_dir / "anchor_stress_model_effects.csv", index=False)
    degradation_effects = _paired_degradation_effects(degradation)
    degradation_effects.to_csv(output_dir / "anchor_stress_degradation_effects.csv", index=False)
    necessity = _necessity_summary(summary, degradation_summary, degradation_effects, scenarios)
    necessity.to_csv(output_dir / "anchor_router_necessity_summary.csv", index=False)
    _write_necessity_json(output_dir, necessity)
    save_json(
        output_dir / "anchor_stress_config.json",
        {
            "run_table": str(root_dir / Path(args.run_table)),
            "cache_dir": str(root_dir / Path(args.cache_dir)),
            "models": sorted(models),
            "scenarios": scenarios,
            "seeds": sorted(seed_filter),
            "max_windows": int(args.max_windows),
            "split": args.split,
            "batch_size": int(args.batch_size),
            "device": str(device),
            "rated_wind": float(args.rated_wind),
            "pitch_threshold": float(args.pitch_threshold),
            "boundary_band": float(args.boundary_band),
            "n_rows": int(len(raw_df)),
            "claim_guard": {
                "clean_anchor_semantic_nmi_ari": "anchor-only is a strong control; do not claim universal clean semantic dominance",
                "trainable_router_necessity": "only noisy/missing/domain-shift/few-label/partial-label robustness",
            },
        },
    )
    _write_report(output_dir, summary, degradation_summary, degradation_effects, necessity, scenarios)
    print(f"Wrote anchor stress comparison to {output_dir}")


if __name__ == "__main__":
    main()
