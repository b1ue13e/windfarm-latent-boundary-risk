from __future__ import annotations

import gc
import json
import math
import multiprocessing as mp
import os
import shutil
import subprocess
import tempfile
import time
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import replace
from pathlib import Path
import re
from typing import Any, Iterable

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import torch

from .analysis import (
    analyze_gates,
    apply_manuscript_style,
    build_manuscript_figure2_data_boundary,
    build_manuscript_figure3_summary_results,
    build_manuscript_figure4_routing_evidence,
    build_manuscript_figure5_case_studies,
    build_manuscript_figure6_ablation_tradeoff,
)
from .config import EvalConfig, ModelConfig, TrainConfig
from .data import CacheBundle, load_cache_bundle
from .model import RegimeAwareForecaster
from .regimes import compute_wtb_operation_regime, compute_wtb_wake_flag, inverse_frequency_weights_from_labels
from .train import train_model
from .utils import ensure_dir, load_json, save_json


WTB_CORRECTED_DISPLAY_MODEL = "Boundary-forced router"
PAPER_ASSET_FREEZE_TOKEN_REPLACEMENTS = {
    "269.96": "2.6996e2",
    "273.55": "2.7355e2",
    "429.05": "4.2905e2",
    "0.8929": "8.929e-1",
}
PAPER_ASSET_FREEZE_SUFFIXES = {".csv", ".json", ".md", ".tex", ".txt"}

WTB_MAIN_ORDER = [
    "Capacity-Matched Dense Diffusion-GRU",
    "Unconstrained MoE",
    WTB_CORRECTED_DISPLAY_MODEL,
]
WTB_FORECASTING_ORDER = [
    "Graph WaveNet",
    "Graph Transformer",
    "GAT-GRU",
    "Physics-Aligned MoE",
    "PatchTST",
    "iTransformer",
    "TiDE",
    "Capacity-Matched Dense Diffusion-GRU",
    "Unconstrained MoE",
    WTB_CORRECTED_DISPLAY_MODEL,
]

WTB_MAIN_TABLE_ORDER = [
    "iTransformer",
    "Graph WaveNet",
    "Graph Transformer",
    "PatchTST",
    "Physics-Aligned MoE",
    "Unconstrained MoE",
    WTB_CORRECTED_DISPLAY_MODEL,
]
ERA5_MAIN_ORDER = [
    "Capacity-Matched Dense Diffusion-GRU",
    "Unconstrained MoE",
    "Physics-Aligned MoE",
]
ERA5_FORECASTING_ORDER = [
    "Persistence",
    "Graph WaveNet",
    "Graph Transformer",
    "GAT-GRU",
    "STGCN",
    "PatchTST",
    "iTransformer",
    "TiDE",
    "TCN",
    "Capacity-Matched Dense Diffusion-GRU",
    "Physics-Aligned MoE",
    "Unconstrained MoE",
]
WTB_ABLATION_ORDER = [
    "Capacity-Matched Dense Diffusion-GRU",
    "Unconstrained MoE",
    "MoE + L_bal",
    "MoE + L_align",
    "MoE + L_bal + L_align",
    "MoE + L_bal + L_align + L_force",
    "MoE + L_bal + L_align + L_force + L_smooth",
    "Context-supervised router",
    "Anchor-only router",
    "Physics-Aligned MoE",
]
ERA5_ABLATION_ORDER = [
    "Capacity-Matched Dense Diffusion-GRU",
    "Unconstrained MoE",
    "MoE + L_bal",
    "MoE + L_align",
    "MoE + L_bal + L_align",
    "Physics-Aligned MoE",
]
STRONG_BASELINE_ORDER = [
    "STGCN",
    "Graph WaveNet",
    "Graph Transformer",
    "GAT-GRU",
    "PatchTST",
    "iTransformer",
    "TiDE",
    "TCN",
]

MODEL_SHORT_NAMES = {
    "Capacity-Matched Dense Diffusion-GRU": "Dense (matched)",
    "Unconstrained MoE": "MoE only",
    WTB_CORRECTED_DISPLAY_MODEL: "Boundary-forced router",
    "STGCN": "STGCN",
    "Graph WaveNet": "Graph WaveNet",
    "GAT-GRU": "GAT-GRU",
    "Graph Transformer": "Graph Transformer",
    "PatchTST": "PatchTST",
    "iTransformer": "iTransformer",
    "TiDE": "TiDE",
    "TCN": "TCN",
    "Persistence": "Persistence",
    "MoE + L_bal": "MoE + $L_{bal}$",
    "MoE + L_align": "MoE + $L_{align}$",
    "MoE + L_bal + L_align": "MoE + $L_{bal}$ + $L_{align}$",
    "MoE + L_bal + L_align + L_force": "MoE + $L_{bal}$ + $L_{align}$ + $L_{force}$",
    "MoE + L_bal + L_align + L_force + L_smooth": "MoE + $L_{bal}$ + $L_{align}$ + $L_{force}$ + $L_{smooth}$",
    "Context-supervised router": "Context-supervised router",
    "Anchor-only router": "Anchor-only router",
    "Physics-Aligned MoE": "Physics-aligned MoE",
}

LEGACY_VARIANT_KEY_ALIASES = {
    "baseline_dense": "dense",
    "baseline_stgcn": "stgcn",
    "baseline_graph_wavenet": "graph_wavenet",
    "baseline_patchtst": "patchtst",
    "baseline_gat_gru": "gat_gru",
    "baseline_graph_transformer": "graph_transformer",
    "baseline_tcn": "tcn",
    "baseline_itransformer": "itransformer",
    "baseline_tide": "tide",
    "moe_unconstrained": "unconstrained",
    "moe_balance_only": "bal",
    "moe_align_only": "align",
    "moe_balance_align": "bal_align",
    "moe_full_no_aux": "bal_align_force_smooth",
    "moe_full_no_smooth": "full_no_smooth",
    "moe_context_align": "context_align_force",
    "moe_anchor_only": "anchor_only",
    "moe_phys_full": "full",
}


def paper_default_loss_weights(dataset: str) -> dict[str, float]:
    if dataset in {"wtb", "external_wind"}:
        return {
            "align": 5000.0,
            "aux": 250.0,
            "smooth": 0.05,
            "balance": 1000.0,
            "physics_force": 10000.0,
        }
    return {
        "align": 0.2,
        "aux": 0.1,
        "smooth": 0.05,
        "balance": 0.01,
        "physics_force": 0.0,
    }


def count_trainable_parameters(model: torch.nn.Module) -> int:
    return int(sum(parameter.numel() for parameter in model.parameters() if parameter.requires_grad))


def build_model_for_count(
    bundle: CacheBundle,
    mode: str,
    hidden_dim: int,
    num_experts: int,
    tau: float = 0.7,
    dropout: float = 0.1,
) -> RegimeAwareForecaster:
    config = ModelConfig(
        hidden_dim=hidden_dim,
        num_experts=num_experts,
        dropout=dropout,
        tau=tau,
        primary_num_classes=bundle.metadata["primary_num_classes"],
        gate_physics_dim=int(bundle.physics.shape[-1]),
    )
    return RegimeAwareForecaster(
        feature_dim=int(bundle.features.shape[-1]),
        pred_len=int(bundle.metadata["pred_len"]),
        mode=mode,
        config=config,
    )


def find_capacity_matched_dense_hidden_dim(
    bundle: CacheBundle,
    moe_hidden_dim: int,
    num_experts: int,
    tau: float = 0.7,
    dropout: float = 0.1,
    search_min: int = 32,
    search_max: int = 256,
    step: int = 4,
) -> dict[str, int | float]:
    moe_model = build_model_for_count(bundle, "moe_phys_full", moe_hidden_dim, num_experts, tau=tau, dropout=dropout)
    moe_params = count_trainable_parameters(moe_model)
    best_hidden = search_min
    best_dense_params = 0
    best_gap = float("inf")
    for hidden_dim in range(search_min, search_max + 1, step):
        dense_model = build_model_for_count(bundle, "baseline_dense", hidden_dim, num_experts, tau=tau, dropout=dropout)
        dense_params = count_trainable_parameters(dense_model)
        gap = abs(dense_params - moe_params)
        if gap < best_gap:
            best_gap = gap
            best_hidden = hidden_dim
            best_dense_params = dense_params
    rel_gap = abs(best_dense_params - moe_params) / max(moe_params, 1)
    return {
        "moe_hidden_dim": int(moe_hidden_dim),
        "moe_params": int(moe_params),
        "dense_hidden_dim": int(best_hidden),
        "dense_params": int(best_dense_params),
        "relative_gap": float(rel_gap),
    }


def resolve_capacity_matched_hidden_dim(
    bundle: CacheBundle,
    mode: str,
    hidden_dim: int,
    num_experts: int,
    tau: float,
    dropout: float,
) -> int:
    if mode != "baseline_dense":
        return hidden_dim
    match = find_capacity_matched_dense_hidden_dim(
        bundle,
        moe_hidden_dim=hidden_dim,
        num_experts=num_experts,
        tau=tau,
        dropout=dropout,
    )
    return int(match["dense_hidden_dim"])


def compute_usage_statistics(gate_prob: np.ndarray) -> dict[str, Any]:
    usage = np.asarray(gate_prob, dtype=np.float64).mean(axis=(0, 1))
    usage = np.clip(usage, 1e-12, None)
    usage = usage / usage.sum()
    entropy = float(-(usage * np.log(usage)).sum())
    normalized_entropy = float(entropy / math.log(len(usage))) if len(usage) > 1 else 0.0
    return {
        "expert_usage": usage.tolist(),
        "expert_usage_entropy": entropy,
        "expert_usage_entropy_normalized": normalized_entropy,
        "expert_usage_variance": float(np.var(usage)),
    }


def _ari_from_confusion_matrix(confusion: Any) -> float | None:
    conf = np.asarray(confusion, dtype=np.float64)
    if conf.size == 0 or conf.ndim != 2:
        return None
    n = float(conf.sum())
    if n <= 1.0:
        return None

    def comb2(values: np.ndarray) -> np.ndarray:
        return values * (values - 1.0) / 2.0

    sum_comb = float(comb2(conf).sum())
    row_sums = conf.sum(axis=1)
    col_sums = conf.sum(axis=0)
    sum_rows = float(comb2(row_sums).sum())
    sum_cols = float(comb2(col_sums).sum())
    total_pairs = n * (n - 1.0) / 2.0
    if total_pairs <= 0.0:
        return None
    expected = (sum_rows * sum_cols) / total_pairs
    max_index = 0.5 * (sum_rows + sum_cols)
    denom = max_index - expected
    if abs(denom) < 1e-12:
        return None
    return float((sum_comb - expected) / denom)


def _masked_metrics(pred: np.ndarray, target: np.ndarray, mask: np.ndarray) -> dict[str, float]:
    safe_pred = np.nan_to_num(pred.astype(np.float64), nan=0.0)
    safe_target = np.nan_to_num(target.astype(np.float64), nan=0.0)
    weight = mask.astype(np.float64)
    denom = max(weight.sum(), 1.0)
    mae = float((np.abs(safe_pred - safe_target) * weight).sum() / denom)
    rmse = float(np.sqrt((((safe_pred - safe_target) ** 2) * weight).sum() / denom))
    return {"mae": mae, "rmse": rmse}


def _compute_switch_selector(regime_primary: np.ndarray, steps_per_hour: int) -> np.ndarray:
    switch_window = 3 * int(steps_per_hour)
    switch_selector = np.zeros_like(regime_primary, dtype=bool)
    if regime_primary.shape[0] > 1:
        changes = regime_primary[1:] != regime_primary[:-1]
        rows, nodes = np.where(changes)
        for row, node in zip(rows, nodes):
            lo = max(0, row + 1 - switch_window)
            hi = min(regime_primary.shape[0], row + 2 + switch_window)
            switch_selector[lo:hi, node] = True
    return switch_selector


def _copy_train_config(config: TrainConfig) -> TrainConfig:
    return TrainConfig(**config.__dict__)


def _copy_model_config(config: ModelConfig) -> ModelConfig:
    return ModelConfig(**config.__dict__)


def _infer_seed(summary: dict[str, Any], run_dir: Path) -> int | None:
    if "seed" in summary:
        return int(summary["seed"])
    match = re.search(r"seed(\d+)", run_dir.name)
    if match:
        return int(match.group(1))
    return None


def _format_mean_std(mean: float, std: float, n_runs: int | float | None, precision: int = 2) -> str:
    if pd.isna(mean):
        return ""
    if n_runs is not None and float(n_runs) > 1 and not pd.isna(std):
        return f"{mean:.{precision}f} ± {std:.{precision}f}"
    return f"{mean:.{precision}f}"


def _summarize_metrics(
    df: pd.DataFrame,
    group_cols: list[str],
    metric_cols: Iterable[str],
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    if df.empty:
        return pd.DataFrame(columns=[*group_cols, "n_runs"])
    grouped = df.groupby(group_cols, dropna=False, sort=False)
    for keys, group in grouped:
        if not isinstance(keys, tuple):
            keys = (keys,)
        row = {column: value for column, value in zip(group_cols, keys)}
        row["n_runs"] = int(len(group))
        for metric in metric_cols:
            series = pd.to_numeric(group[metric], errors="coerce").dropna()
            if series.empty:
                row[f"{metric}_mean"] = np.nan
                row[f"{metric}_std"] = np.nan
                row[f"{metric}_display"] = ""
            else:
                mean = float(series.mean())
                std = float(series.std(ddof=1)) if len(series) > 1 else 0.0
                precision = 4 if abs(mean) < 10.0 else 2
                row[f"{metric}_mean"] = mean
                row[f"{metric}_std"] = std
                if len(series) > 1:
                    row[f"{metric}_display"] = f"{mean:.{precision}f} +/- {std:.{precision}f}"
                else:
                    row[f"{metric}_display"] = f"{mean:.{precision}f}"
        rows.append(row)
    return pd.DataFrame(rows)


def _ordered_rows(df: pd.DataFrame, column: str, order: list[str]) -> pd.DataFrame:
    if df.empty or column not in df.columns:
        return df
    ordered = df.copy()
    ordered[column] = pd.Categorical(ordered[column], categories=order, ordered=True)
    ordered = ordered.sort_values(column).reset_index(drop=True)
    ordered[column] = ordered[column].astype(str)
    return ordered


def _default_num_experts_for_dataset(dataset: str) -> int:
    return 4 if dataset in {"wtb", "external_wind"} else 3


def _spec_lookup(dataset: str) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    default_num_experts = _default_num_experts_for_dataset(dataset)
    for group_name, specs in [
        ("main", _main_variant_specs(dataset)),
        ("strong_baselines", _strong_baseline_specs(dataset)),
        ("ablation", _ablation_variant_specs(dataset)),
        (
            "sensitivity",
            _wtb_sensitivity_specs(default_num_experts)
            if dataset in {"wtb", "external_wind"}
            else _era5_sensitivity_specs(default_num_experts),
        ),
    ]:
        for spec in specs:
            lookup.setdefault(spec["key"], {"group": group_name, **spec})
    return lookup


def _infer_variant_key(summary: dict[str, Any], run_dir: Path, dataset: str) -> str:
    if "variant_key" in summary:
        return str(summary["variant_key"])
    match = re.match(rf"^{re.escape(dataset)}_(.+)_seed\d+$", run_dir.name)
    if match:
        raw_key = str(match.group(1))
        return LEGACY_VARIANT_KEY_ALIASES.get(raw_key, raw_key)
    raw_mode = str(summary.get("model_mode", "") or "")
    if raw_mode:
        return LEGACY_VARIANT_KEY_ALIASES.get(raw_mode, raw_mode)
    return ""


def _infer_group_from_run_dir(run_dir: Path) -> str:
    known_groups = {"main", "strong_baselines", "ablation", "sensitivity"}
    for part in run_dir.parts:
        lowered = str(part).lower()
        if lowered in known_groups:
            return lowered
    return ""


def _infer_experiment_metadata(summary: dict[str, Any], run_dir: Path, dataset: str) -> dict[str, Any]:
    variant_key = _infer_variant_key(summary, run_dir, dataset)
    lookup = _spec_lookup(dataset)
    spec = lookup.get(variant_key, {})
    group_from_path = _infer_group_from_run_dir(run_dir)
    return {
        "variant_key": variant_key,
        "experiment_group": summary.get("experiment_group") or group_from_path or spec.get("group", ""),
        "setting_group": summary.get("setting_group", spec.get("setting_group", "")),
        "setting_value": summary.get("setting_value", spec.get("setting_value", "")),
        "setting_label": summary.get("setting_label", spec.get("setting_label", "")),
    }


def _fallback_experiment_group(dataset: str, label: str, metadata: dict[str, Any]) -> str:
    if metadata.get("experiment_group"):
        return str(metadata["experiment_group"])
    if metadata.get("setting_group"):
        return "sensitivity"
    ablation_order = WTB_ABLATION_ORDER if dataset == "wtb" else ERA5_ABLATION_ORDER
    main_order = WTB_MAIN_ORDER if dataset == "wtb" else ERA5_MAIN_ORDER
    if label in main_order:
        return "main"
    if label in ablation_order:
        return "ablation"
    if label in STRONG_BASELINE_ORDER:
        return "strong_baselines"
    return ""


def _select_group(df: pd.DataFrame, group: str) -> pd.DataFrame:
    if df.empty or "experiment_group" not in df.columns:
        return df
    subset = df[df["experiment_group"] == group].copy()
    return subset if not subset.empty else df.copy()


def _path_contains(df: pd.DataFrame, token: str) -> pd.Series:
    if "run_dir" not in df.columns:
        return pd.Series(False, index=df.index)
    return df["run_dir"].astype(str).str.contains(re.escape(token), case=False, na=False)


def _select_preferred_wtb_full_runs(model_subset: pd.DataFrame) -> pd.DataFrame:
    if model_subset.empty:
        return model_subset
    subset = model_subset.copy()
    if "variant_key" in subset.columns:
        full_subset = subset[subset["variant_key"] == "full"].copy()
        if not full_subset.empty:
            subset = full_subset
    preferred = subset[_path_contains(subset, r"priority2_full_corrected_family")].copy()
    if not preferred.empty:
        return preferred
    if "experiment_group" in subset.columns:
        main_subset = subset[subset["experiment_group"] == "main"].copy()
        if not main_subset.empty:
            return main_subset
    return subset


def _select_preferred_wtb_ablation_runs(model_subset: pd.DataFrame) -> pd.DataFrame:
    if model_subset.empty:
        return model_subset
    preferred_source_by_model = {
        "MoE + L_bal + L_align + L_force": "priority1_corrected_5seed",
        "Physics-Aligned MoE": "priority2_full_corrected_family",
    }
    model_name = str(model_subset["model"].iloc[0]) if "model" in model_subset.columns else ""
    preferred_token = preferred_source_by_model.get(model_name)
    if preferred_token:
        preferred = model_subset[_path_contains(model_subset, preferred_token)].copy()
        if not preferred.empty:
            return preferred
    return model_subset


def _select_wtb_forecasting_subset(wtb_df: pd.DataFrame) -> pd.DataFrame:
    if wtb_df.empty or "model" not in wtb_df.columns:
        return wtb_df.copy()
    rows: list[pd.DataFrame] = []
    for model_name in WTB_FORECASTING_ORDER:
        model_subset = wtb_df[wtb_df["model"] == model_name].copy()
        if model_subset.empty:
            continue
        if "experiment_group" in model_subset.columns:
            if model_name == "Physics-Aligned MoE":
                model_subset = _select_preferred_wtb_full_runs(model_subset)
            elif model_name in WTB_MAIN_ORDER:
                main_subset = model_subset[model_subset["experiment_group"] == "main"].copy()
                if not main_subset.empty:
                    model_subset = main_subset
            elif model_name in STRONG_BASELINE_ORDER:
                strong_subset = model_subset[model_subset["experiment_group"] == "strong_baselines"].copy()
                if not strong_subset.empty:
                    model_subset = strong_subset
        rows.append(model_subset)
    if not rows:
        return pd.DataFrame(columns=wtb_df.columns)
    return pd.concat(rows, ignore_index=True)


def _select_era5_forecasting_subset(era5_df: pd.DataFrame) -> pd.DataFrame:
    if era5_df.empty or "model" not in era5_df.columns:
        return era5_df.copy()
    rows: list[pd.DataFrame] = []
    for model_name in ERA5_FORECASTING_ORDER:
        model_subset = era5_df[era5_df["model"] == model_name].copy()
        if model_subset.empty:
            continue
        if (
            model_name in ERA5_MAIN_ORDER
            and "experiment_group" in model_subset.columns
        ):
            main_subset = model_subset[model_subset["experiment_group"] == "main"].copy()
            if not main_subset.empty:
                model_subset = main_subset
        rows.append(model_subset)
    if not rows:
        return pd.DataFrame(columns=era5_df.columns)
    return pd.concat(rows, ignore_index=True)


def _prepare_wtb_main_display_df(wtb_df: pd.DataFrame) -> pd.DataFrame:
    if wtb_df.empty or "model" not in wtb_df.columns:
        return wtb_df.copy()
    display_df = wtb_df.copy()
    display_df = display_df[display_df["model"] != WTB_CORRECTED_DISPLAY_MODEL].copy()
    source = display_df[display_df["model"] == "MoE + L_bal + L_align + L_force"].copy()
    if not source.empty and "model_mode" in source.columns:
        preferred = source[source["model_mode"] == "moe_full_no_aux"].copy()
        if not preferred.empty:
            source = preferred
    if source.empty:
        source = display_df[display_df["model"] == "Physics-Aligned MoE"].copy()
        if "experiment_group" in source.columns:
            main_source = source[source["experiment_group"] == "main"].copy()
            if not main_source.empty:
                source = main_source
    if source.empty:
        return display_df
    for column in ["setting_group", "setting_label"]:
        if column in source.columns:
            source[column] = source[column].astype(object)
    source.loc[:, "model"] = WTB_CORRECTED_DISPLAY_MODEL
    if "experiment_group" in source.columns:
        source.loc[:, "experiment_group"] = "main"
    if "variant_key" in source.columns:
        source.loc[:, "variant_key"] = "wtb_corrected_display"
    if "setting_group" in source.columns:
        source.loc[:, "setting_group"] = ""
    if "setting_label" in source.columns:
        source.loc[:, "setting_label"] = "wtb_corrected_routing"
    return pd.concat([display_df, source], ignore_index=True)


def _wtb_ablation_reference_subset(wtb_df: pd.DataFrame) -> pd.DataFrame:
    ablation_subset = _select_group(wtb_df, "ablation")
    if ablation_subset.empty:
        ablation_subset = pd.DataFrame(columns=wtb_df.columns)
    if not ablation_subset.empty and "model" in ablation_subset.columns:
        filtered: list[pd.DataFrame] = []
        for _, group in ablation_subset.groupby("model", sort=False, dropna=False):
            filtered.append(_select_preferred_wtb_ablation_runs(group.copy()))
        ablation_subset = pd.concat(filtered, ignore_index=True) if filtered else ablation_subset
    reference_models = {
        "Capacity-Matched Dense Diffusion-GRU",
        "Unconstrained MoE",
        "Physics-Aligned MoE",
    }
    present = set(ablation_subset["model"].astype(str).tolist()) if "model" in ablation_subset.columns else set()
    missing = reference_models.difference(present)
    if not missing:
        return ablation_subset
    main_subset = _select_group(wtb_df, "main")
    if main_subset.empty or "model" not in main_subset.columns:
        return ablation_subset
    supplements = main_subset[main_subset["model"].isin(missing)].copy()
    if supplements.empty:
        return ablation_subset
    return pd.concat([ablation_subset, supplements], ignore_index=True)


def _model_display_name(name: str) -> str:
    return MODEL_SHORT_NAMES.get(name, name.replace("_", r"\_"))


def collect_suite_run_dirs(root_dir: Path | str, dataset: str) -> list[tuple[str, Path]]:
    root_dir = Path(root_dir)
    if not root_dir.exists():
        return []
    specs = _spec_lookup(dataset)
    labeled: list[tuple[str, Path]] = []
    for summary_path in sorted(root_dir.rglob("training_summary.json")):
        run_dir = summary_path.parent
        summary = load_json(summary_path)
        variant_key = _infer_variant_key(summary, run_dir, dataset)
        label = specs.get(variant_key, {}).get("label") or summary.get("label")
        if label:
            labeled.append((str(label), run_dir))
    return labeled


def aggregate_runs(
    dataset: str,
    labeled_run_dirs: list[tuple[str, Path]],
    output_dir: Path | str,
    split: str = "test",
) -> pd.DataFrame:
    output_dir = ensure_dir(output_dir)
    rows: list[dict[str, Any]] = []
    for label, run_dir in labeled_run_dirs:
        run_dir = Path(run_dir)
        metrics_dir = run_dir / f"{split}_metrics"
        summary_path = run_dir / "training_summary.json"
        metrics_path = metrics_dir / "metrics.json"
        if not summary_path.exists() or not metrics_path.exists():
            continue
        summary = load_json(summary_path)
        metrics = load_json(metrics_path)
        metadata = _infer_experiment_metadata(summary, run_dir, dataset)
        metadata["experiment_group"] = _fallback_experiment_group(dataset, label, metadata)
        history = summary.get("history", [])
        raw_train_seconds = summary.get("total_train_seconds")
        if raw_train_seconds is None:
            history_seconds = sum(float(epoch.get("epoch_seconds", 0.0)) for epoch in history)
            total_train_seconds = float(history_seconds) if history_seconds > 0.0 else float("nan")
        else:
            total_train_seconds = float(raw_train_seconds)
        efficiency = metrics.get("efficiency", {})
        eval_seconds = efficiency.get("eval_seconds")
        num_windows = efficiency.get("num_windows")
        windows_per_second = efficiency.get("windows_per_second")
        if (windows_per_second is None or pd.isna(windows_per_second)) and eval_seconds not in (None, 0):
            windows_per_second = float(num_windows) / float(eval_seconds)
        row = {
            "dataset": dataset,
            "model": label,
            "run_dir": str(run_dir),
            "seed": _infer_seed(summary, run_dir),
            **metadata,
            "model_mode": summary.get("model_mode", ""),
            "parameter_count": summary.get("parameter_count"),
            "best_epoch": summary["best_epoch"],
            "best_val_rmse": summary["best_val_rmse"],
            "total_train_seconds": total_train_seconds,
            "eval_seconds": eval_seconds,
            "num_windows": num_windows,
            "windows_per_second": windows_per_second,
            "overall_mae": metrics["overall"]["mae"],
            "overall_rmse": metrics["overall"]["rmse"],
            "switch_mae": metrics["switch_window"]["mae"],
            "switch_rmse": metrics["switch_window"]["rmse"],
        }
        for regime_name, values in metrics["by_regime"].items():
            row[f"{regime_name}_mae"] = values["mae"]
            row[f"{regime_name}_rmse"] = values["rmse"]
        gate_alignment = metrics.get("gate_alignment", {})
        expert_usage = gate_alignment.get("expert_usage")
        if expert_usage is not None:
            row["expert_usage"] = expert_usage
        row["nmi"] = gate_alignment.get("nmi")
        row["ari"] = _ari_from_confusion_matrix(gate_alignment.get("confusion_matrix"))
        if row["ari"] is None:
            row["ari"] = gate_alignment.get("ari")
        row["expert_usage_entropy"] = gate_alignment.get("expert_usage_entropy")
        row["expert_usage_variance"] = gate_alignment.get("expert_usage_variance")
        if expert_usage is None:
            gate_path = metrics_dir / "gate_prob.npy"
            if gate_path.exists():
                row.update(compute_usage_statistics(np.load(gate_path)))
                row["expert_usage_entropy"] = gate_alignment.get(
                    "expert_usage_entropy",
                    row.get("expert_usage_entropy"),
                )
                row["expert_usage_variance"] = gate_alignment.get(
                    "expert_usage_variance",
                    row.get("expert_usage_variance"),
                )
        rows.append(row)
    df = pd.DataFrame(rows)
    df.to_csv(Path(output_dir) / f"{dataset}_{split}_aggregated_runs.csv", index=False)
    save_json(Path(output_dir) / f"{dataset}_{split}_aggregated_runs.json", {"rows": df.to_dict(orient="records")})
    return df


def build_era5_persistence_baseline(
    bundle: CacheBundle,
    output_path: Path | str,
) -> Path:
    output_path = Path(output_path)
    ensure_dir(output_path.parent)
    hist_len = int(bundle.metadata["hist_len"])
    pred_len = int(bundle.metadata["pred_len"])
    test_start, test_end = bundle.metadata["split_bounds"]["test"]
    anchor_start = int(test_start) + hist_len - 1
    anchor_end = int(test_end) - pred_len - 1
    anchors = np.arange(anchor_start, anchor_end + 1, dtype=np.int64)
    if anchors.size == 0:
        raise ValueError("ERA5 test split is too short for persistence evaluation.")
    pred = np.stack([np.asarray(bundle.target[anchor], dtype=np.float32) for anchor in anchors], axis=0)
    pred = np.repeat(pred[:, None, :], pred_len, axis=1)
    target = np.stack(
        [np.asarray(bundle.target[anchor + 1 : anchor + 1 + pred_len], dtype=np.float32) for anchor in anchors],
        axis=0,
    )
    mask = np.stack(
        [
            np.asarray(bundle.target_mask[anchor + 1 : anchor + 1 + pred_len], dtype=np.float32)
            for anchor in anchors
        ],
        axis=0,
    )
    regime_primary = np.asarray(bundle.regime_primary[anchors], dtype=np.int16)
    steps_per_hour = int(bundle.metadata.get("steps_per_hour", 1))

    overall = _masked_metrics(pred, target, mask)
    switch_selector = _compute_switch_selector(regime_primary, steps_per_hour)
    switch = _masked_metrics(pred, target, mask * switch_selector[:, None, :])
    row: dict[str, Any] = {
        "dataset": "era5",
        "model": "Persistence",
        "variant_key": "persistence",
        "experiment_group": "external_baseline",
        "setting_group": "",
        "setting_value": "",
        "setting_label": "last-value persistence",
        "model_mode": "persistence",
        "parameter_count": 0,
        "seed": "",
        "n_runs": 1,
        "overall_mae": overall["mae"],
        "overall_rmse": overall["rmse"],
        "switch_mae": switch["mae"],
        "switch_rmse": switch["rmse"],
    }
    for regime_id, regime_name in enumerate(bundle.metadata["primary_regime_names"]):
        selector = regime_primary == regime_id
        regime_metrics = _masked_metrics(pred, target, mask * selector[:, None, :])
        row[f"{regime_name}_mae"] = regime_metrics["mae"]
        row[f"{regime_name}_rmse"] = regime_metrics["rmse"]
    pd.DataFrame([row]).to_csv(output_path, index=False)
    return output_path


def append_era5_persistence_baseline(
    era5_df: pd.DataFrame,
    bundle: CacheBundle | None,
    output_dir: Path | str,
) -> pd.DataFrame:
    if bundle is None:
        return era5_df
    if not era5_df.empty and "model" in era5_df.columns and (era5_df["model"] == "Persistence").any():
        return era5_df
    baseline_path = build_era5_persistence_baseline(
        bundle,
        Path(output_dir) / "era5_external_baselines.csv",
    )
    baseline_df = pd.read_csv(baseline_path)
    if era5_df.empty:
        return baseline_df
    return pd.concat([era5_df, baseline_df], ignore_index=True, sort=False)


def _optional_float(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    return float(value)


def _relative_abs_difference(current: float | None, reference: float | None) -> float | None:
    if current is None or reference is None or reference == 0.0:
        return None
    return abs(current - reference) / abs(reference)


def build_wtb_sentinel_review(
    reference_suite_dir: Path | str,
    sentinel_suite_dir: Path | str,
    output_path: Path | str,
    variant_key: str = "bal_align_force",
    overall_tolerance: float = 0.03,
    switch_tolerance: float = 0.03,
    nmi_drop_tolerance: float = 0.05,
) -> Path:
    output_path = Path(output_path)
    ensure_dir(output_path.parent)
    table_dir = ensure_dir(output_path.parent / "_sentinel_check_tables")
    reference_df = aggregate_runs(
        "wtb",
        collect_suite_run_dirs(reference_suite_dir, "wtb"),
        table_dir / "reference",
    )
    sentinel_df = aggregate_runs(
        "wtb",
        collect_suite_run_dirs(sentinel_suite_dir, "wtb"),
        table_dir / "sentinel",
    )
    reference_df = reference_df[reference_df["variant_key"] == variant_key].copy() if not reference_df.empty else reference_df
    sentinel_df = sentinel_df[sentinel_df["variant_key"] == variant_key].copy() if not sentinel_df.empty else sentinel_df

    rows: list[dict[str, Any]] = []
    if sentinel_df.empty:
        rows.append(
            {
                "variant_key": variant_key,
                "status": "ANOMALY",
                "reason": "no_sentinel_runs",
            }
        )
    for _, sentinel_row in sentinel_df.iterrows():
        seed = int(sentinel_row["seed"])
        reference_match = reference_df[reference_df["seed"] == seed] if not reference_df.empty else pd.DataFrame()
        if reference_match.empty:
            rows.append(
                {
                    "variant_key": variant_key,
                    "seed": seed,
                    "status": "ANOMALY",
                    "reason": "missing_reference_seed",
                }
            )
            continue
        reference_row = reference_match.iloc[0]
        sentinel_overall = _optional_float(sentinel_row.get("overall_rmse"))
        reference_overall = _optional_float(reference_row.get("overall_rmse"))
        sentinel_switch = _optional_float(sentinel_row.get("switch_rmse"))
        reference_switch = _optional_float(reference_row.get("switch_rmse"))
        sentinel_nmi = _optional_float(sentinel_row.get("nmi"))
        reference_nmi = _optional_float(reference_row.get("nmi"))
        overall_delta = _relative_abs_difference(sentinel_overall, reference_overall)
        switch_delta = _relative_abs_difference(sentinel_switch, reference_switch)
        nmi_drop = (
            reference_nmi - sentinel_nmi
            if reference_nmi is not None and sentinel_nmi is not None
            else None
        )
        status = "PASSED"
        reasons: list[str] = []
        if overall_delta is None or overall_delta > overall_tolerance:
            status = "ANOMALY"
            reasons.append("overall_rmse_delta")
        if switch_delta is None or switch_delta > switch_tolerance:
            status = "ANOMALY"
            reasons.append("switch_rmse_delta")
        if nmi_drop is None or nmi_drop > nmi_drop_tolerance:
            status = "ANOMALY"
            reasons.append("nmi_drop")
        rows.append(
            {
                "variant_key": variant_key,
                "seed": seed,
                "status": status,
                "reason": ",".join(reasons),
                "reference_run_dir": str(reference_row.get("run_dir", "")),
                "sentinel_run_dir": str(sentinel_row.get("run_dir", "")),
                "reference_overall_rmse": reference_overall,
                "sentinel_overall_rmse": sentinel_overall,
                "overall_relative_delta": overall_delta,
                "reference_switch_rmse": reference_switch,
                "sentinel_switch_rmse": sentinel_switch,
                "switch_relative_delta": switch_delta,
                "reference_nmi": reference_nmi,
                "sentinel_nmi": sentinel_nmi,
                "nmi_drop": nmi_drop,
            }
        )

    status = "PASSED" if rows and all(row["status"] == "PASSED" for row in rows) else "ANOMALY"
    csv_path = output_path.with_suffix(".csv")
    pd.DataFrame(rows).to_csv(csv_path, index=False)
    save_json(
        output_path,
        {
            "status": status,
            "variant_key": variant_key,
            "overall_tolerance": overall_tolerance,
            "switch_tolerance": switch_tolerance,
            "nmi_drop_tolerance": nmi_drop_tolerance,
            "csv_path": str(csv_path),
            "rows": rows,
        },
    )
    return output_path


def build_unified_main_results_table(
    wtb_csv: Path | str,
    era5_csv: Path | str,
    output_path: Path | str,
) -> Path:
    wtb_df = pd.read_csv(wtb_csv)
    era5_df = pd.read_csv(era5_csv)
    external_path = Path(output_path).parent / "era5_external_baselines.csv"
    if external_path.exists():
        era5_external = pd.read_csv(external_path)
        era5_df = pd.concat([era5_df, era5_external], ignore_index=True, sort=False)
    return build_main_benchmark_table(wtb_df, era5_df, output_path)


def build_main_benchmark_table(
    wtb_df: pd.DataFrame,
    era5_df: pd.DataFrame,
    output_path: Path | str,
) -> Path:
    output_path = Path(output_path)
    if not output_path.suffix:
        output_path = ensure_dir(output_path) / "table_main_benchmark.csv"
    else:
        ensure_dir(output_path.parent)
    rows: list[dict[str, Any]] = []
    wtb_df = _prepare_wtb_main_display_df(wtb_df)
    for panel, df, order in [("WTB", wtb_df, WTB_FORECASTING_ORDER), ("ERA5", era5_df, ERA5_FORECASTING_ORDER)]:
        subset = _select_wtb_forecasting_subset(df) if panel == "WTB" else _select_era5_forecasting_subset(df)
        subset = _ordered_rows(subset[subset["model"].isin(order)].copy(), "model", order)
        summary = _summarize_metrics(subset, ["model"], ["overall_rmse", "overall_mae", "switch_rmse", "switch_mae"])
        summary = _ordered_rows(summary, "model", order)
        for _, row in summary.iterrows():
            rows.append(
                {
                    "Panel": panel,
                    "Model": row["model"],
                    "Overall RMSE": row["overall_rmse_display"],
                    "Overall MAE": row["overall_mae_display"],
                    "Switch RMSE": row["switch_rmse_display"],
                    "Switch MAE": row["switch_mae_display"],
                    "n_runs": int(row["n_runs"]),
                }
            )
    pd.DataFrame(rows).to_csv(output_path, index=False)
    return output_path


def build_regime_wise_table(
    wtb_df: pd.DataFrame,
    era5_df: pd.DataFrame,
    output_path: Path | str,
) -> Path:
    output_path = Path(output_path)
    if not output_path.suffix:
        output_path = ensure_dir(output_path) / "table_regime_wise.csv"
    else:
        ensure_dir(output_path.parent)
    rows: list[dict[str, Any]] = []
    wtb_df = _prepare_wtb_main_display_df(wtb_df)
    wtb_metrics = ["idle_rmse", "mppt_rmse", "pitch_control_rmse", "transition_rmse", "switch_rmse"]
    era5_metrics = ["convective_rmse", "stable_rmse", "transition_rmse", "switch_rmse"]
    for panel, df, order, metrics in [
        ("WTB", wtb_df, WTB_FORECASTING_ORDER, wtb_metrics),
        ("ERA5", era5_df, ERA5_FORECASTING_ORDER, era5_metrics),
    ]:
        subset = _select_wtb_forecasting_subset(df) if panel == "WTB" else _select_era5_forecasting_subset(df)
        subset = _ordered_rows(subset[subset["model"].isin(order)].copy(), "model", order)
        summary = _summarize_metrics(subset, ["model"], metrics)
        summary = _ordered_rows(summary, "model", order)
        for _, row in summary.iterrows():
            base = {"Panel": panel, "Model": row["model"], "n_runs": int(row["n_runs"])}
            if panel == "WTB":
                base.update(
                    {
                        "idle": row["idle_rmse_display"],
                        "mppt": row["mppt_rmse_display"],
                        "pitch_control": row["pitch_control_rmse_display"],
                        "transition": row["transition_rmse_display"],
                        "switch_window": row["switch_rmse_display"],
                    }
                )
            else:
                base.update(
                    {
                        "convective": row["convective_rmse_display"],
                        "stable": row["stable_rmse_display"],
                        "transition": row["transition_rmse_display"],
                        "switch_window": row["switch_rmse_display"],
                    }
                )
            rows.append(base)
    pd.DataFrame(rows).to_csv(output_path, index=False)
    return output_path


def build_routing_quality_table(
    wtb_df: pd.DataFrame,
    era5_df: pd.DataFrame,
    output_path: Path | str,
) -> Path:
    output_path = Path(output_path)
    if not output_path.suffix:
        output_path = ensure_dir(output_path) / "table_routing_quality.csv"
    else:
        ensure_dir(output_path.parent)
    rows: list[dict[str, Any]] = []
    wtb_df = _prepare_wtb_main_display_df(wtb_df)
    metrics = ["nmi", "ari", "expert_usage_entropy", "expert_usage_variance"]
    for panel, df, order in [
        ("WTB", wtb_df, ["Unconstrained MoE", WTB_CORRECTED_DISPLAY_MODEL]),
        ("ERA5", era5_df, ["Unconstrained MoE", "Physics-Aligned MoE"]),
    ]:
        subset = _select_group(df, "main")
        subset = _ordered_rows(subset[subset["model"].isin(order)].copy(), "model", order)
        summary = _summarize_metrics(subset, ["model"], metrics)
        summary = _ordered_rows(summary, "model", order)
        for _, row in summary.iterrows():
            rows.append(
                {
                    "Panel": panel,
                    "Model": row["model"],
                    "NMI": row["nmi_display"],
                    "ARI": row["ari_display"],
                    "expert_usage_entropy": row["expert_usage_entropy_display"],
                    "expert_usage_variance": row["expert_usage_variance_display"],
                    "n_runs": int(row["n_runs"]),
                }
            )
    pd.DataFrame(rows).to_csv(output_path, index=False)
    return output_path


def build_wtb_ablation_table(
    wtb_df: pd.DataFrame,
    output_path: Path | str,
) -> Path:
    output_path = Path(output_path)
    if not output_path.suffix:
        output_path = ensure_dir(output_path) / "table_wtb_ablation.csv"
    else:
        ensure_dir(output_path.parent)
    subset = _wtb_ablation_reference_subset(wtb_df)
    subset = _ordered_rows(subset[subset["model"].isin(WTB_ABLATION_ORDER)].copy(), "model", WTB_ABLATION_ORDER)
    metrics = ["overall_rmse", "switch_rmse", "pitch_control_rmse", "nmi", "ari", "expert_usage_entropy"]
    summary = _summarize_metrics(subset, ["model"], metrics)
    summary = _ordered_rows(summary, "model", WTB_ABLATION_ORDER)
    summary_lookup = {str(row["model"]): row for _, row in summary.iterrows()}
    rows: list[dict[str, Any]] = []
    for model_name in WTB_ABLATION_ORDER:
        row = summary_lookup.get(model_name, {})
        rows.append(
            {
                "Model": model_name,
                "Overall RMSE": row.get("overall_rmse_display", ""),
                "Switch RMSE": row.get("switch_rmse_display", ""),
                "Pitch-control RMSE": row.get("pitch_control_rmse_display", ""),
                "NMI": row.get("nmi_display", ""),
                "ARI": row.get("ari_display", ""),
                "expert_usage_entropy": row.get("expert_usage_entropy_display", ""),
                "n_runs": int(row.get("n_runs", 0) or 0),
            }
        )
    pd.DataFrame(rows).to_csv(output_path, index=False)
    return output_path


def build_robustness_table(
    wtb_df: pd.DataFrame,
    era5_df: pd.DataFrame,
    wtb_sensitivity_df: pd.DataFrame | None,
    output_path: Path | str,
) -> Path:
    output_path = Path(output_path)
    if not output_path.suffix:
        output_path = ensure_dir(output_path) / "table_robustness.csv"
    else:
        ensure_dir(output_path.parent)
    rows: list[dict[str, Any]] = []
    wtb_df = _prepare_wtb_main_display_df(wtb_df)
    wtb_main = _ordered_rows(_select_wtb_forecasting_subset(wtb_df), "model", WTB_FORECASTING_ORDER)
    for panel, df, order in [
        ("WTB", wtb_main, WTB_FORECASTING_ORDER),
        ("ERA5", _ordered_rows(_select_era5_forecasting_subset(era5_df), "model", ERA5_FORECASTING_ORDER), ERA5_FORECASTING_ORDER),
    ]:
        subset = _ordered_rows(df[df["model"].isin(order)].copy(), "model", order)
        metrics = ["overall_rmse", "switch_rmse", "pitch_control_rmse", "nmi"] if panel == "WTB" else ["overall_rmse", "switch_rmse", "nmi"]
        summary = _summarize_metrics(subset, ["model"], metrics)
        summary = _ordered_rows(summary, "model", order)
        for _, row in summary.iterrows():
            rows.append(
                {
                    "Panel": "A_main_seeds",
                    "Dataset": panel,
                    "Condition": row["model"],
                    "Overall RMSE": row["overall_rmse_display"],
                    "Switch RMSE": row["switch_rmse_display"],
                    "Pitch-control RMSE": row.get("pitch_control_rmse_display", ""),
                    "NMI": row["nmi_display"],
                    "Params": "",
                    "Train hours": "",
                    "Windows/s": "",
                    "n_runs": int(row["n_runs"]),
                }
            )

    if wtb_sensitivity_df is not None and not wtb_sensitivity_df.empty:
        wtb_sensitivity_df = _select_group(wtb_sensitivity_df, "sensitivity")
        summary = _summarize_metrics(
            wtb_sensitivity_df,
            ["setting_group", "setting_label", "setting_value"],
            ["overall_rmse", "switch_rmse", "pitch_control_rmse", "nmi"],
        ).sort_values(["setting_group", "setting_value"])
        for _, row in summary.iterrows():
            rows.append(
                {
                    "Panel": "B_wtb_sensitivity",
                    "Dataset": "WTB",
                    "Condition": row["setting_label"],
                    "Overall RMSE": row["overall_rmse_display"],
                    "Switch RMSE": row["switch_rmse_display"],
                    "Pitch-control RMSE": row["pitch_control_rmse_display"],
                    "NMI": row["nmi_display"],
                    "Params": "",
                    "Train hours": "",
                    "Windows/s": "",
                    "n_runs": int(row["n_runs"]),
                }
            )

    efficiency_metrics = ["parameter_count", "total_train_seconds", "windows_per_second"]
    wtb_eff_source = wtb_main[wtb_main["model"].isin(WTB_FORECASTING_ORDER)].copy()
    if not wtb_eff_source.empty:
        wtb_eff_source["parameter_count"] = pd.to_numeric(wtb_eff_source["parameter_count"], errors="coerce")
        wtb_eff_source["parameter_family"] = wtb_eff_source["model"].astype(str).map(
            lambda name: "dense" if "Dense" in name else "moe"
        )
        family_params = (
            wtb_eff_source.groupby("parameter_family", dropna=False)["parameter_count"].median().dropna().to_dict()
        )
        if family_params:
            missing_param_mask = wtb_eff_source["parameter_count"].isna()
            wtb_eff_source.loc[missing_param_mask, "parameter_count"] = wtb_eff_source.loc[
                missing_param_mask, "parameter_family"
            ].map(family_params)
    wtb_eff_summary = _summarize_metrics(wtb_eff_source, ["model"], efficiency_metrics)
    wtb_eff_summary = _ordered_rows(wtb_eff_summary, "model", WTB_FORECASTING_ORDER)
    for _, row in wtb_eff_summary.iterrows():
        params_display = ""
        if not pd.isna(row.get("parameter_count_mean", np.nan)):
            params_display = f"{int(round(float(row['parameter_count_mean']))):,}"
        train_hours_display = ""
        if not pd.isna(row.get("total_train_seconds_mean", np.nan)):
            train_hours_display = f"{float(row['total_train_seconds_mean']) / 3600.0:.2f}"
        windows_display = row.get("windows_per_second_display", "")
        rows.append(
            {
                "Panel": "C_wtb_efficiency",
                "Dataset": "WTB",
                "Condition": row["model"],
                "Overall RMSE": "",
                "Switch RMSE": "",
                "Pitch-control RMSE": "",
                "NMI": "",
                "Params": params_display,
                "Train hours": train_hours_display,
                "Windows/s": windows_display,
                "n_runs": int(row["n_runs"]),
            }
        )
    pd.DataFrame(rows).to_csv(output_path, index=False)
    return output_path


def export_parameter_table(
    bundle: CacheBundle,
    moe_hidden_dim: int,
    num_experts: int,
    tau: float,
    dropout: float,
    output_dir: Path | str,
    dataset_label: str,
) -> Path:
    output_dir = ensure_dir(output_dir)
    match = find_capacity_matched_dense_hidden_dim(
        bundle,
        moe_hidden_dim=moe_hidden_dim,
        num_experts=num_experts,
        tau=tau,
        dropout=dropout,
    )
    df = pd.DataFrame(
        [
            {
                "dataset": dataset_label,
                "model": "Physics-Aligned MoE",
                "hidden_dim": int(match["moe_hidden_dim"]),
                "num_experts": int(num_experts),
                "params": int(match["moe_params"]),
            },
            {
                "dataset": dataset_label,
                "model": "Capacity-Matched Dense Diffusion-GRU",
                "hidden_dim": int(match["dense_hidden_dim"]),
                "num_experts": 1,
                "params": int(match["dense_params"]),
            },
        ]
    )
    output_path = Path(output_dir) / f"{dataset_label.lower()}_parameter_table.csv"
    df.to_csv(output_path, index=False)
    return output_path


def build_variant_table(
    wtb_bundle: CacheBundle,
    era5_bundle: CacheBundle,
    hidden_dim: int,
    wtb_num_experts: int,
    era5_num_experts: int,
    tau: float,
    dropout: float,
    output_path: Path | str,
) -> Path:
    output_path = Path(output_path)
    ensure_dir(output_path.parent)
    wtb_match = find_capacity_matched_dense_hidden_dim(wtb_bundle, hidden_dim, wtb_num_experts, tau=tau, dropout=dropout)
    era5_match = find_capacity_matched_dense_hidden_dim(era5_bundle, hidden_dim, era5_num_experts, tau=tau, dropout=dropout)
    dense_params = f"WTB {int(wtb_match['dense_params']):,} / ERA5 {int(era5_match['dense_params']):,}"
    moe_params = f"WTB {int(wtb_match['moe_params']):,} / ERA5 {int(era5_match['moe_params']):,}"

    rows = [
        {
            "Variant": "Capacity-Matched Dense Diffusion-GRU",
            "Backbone": "Directed-Diffusion GRU",
            "Routing": "Dense head",
            "L_bal": "No",
            "L_align": "No",
            "L_force": "No",
            "L_aux": "No",
            "L_smooth": "No",
            "Params": dense_params,
            "Purpose in paper": "Capacity-matched shared-mapping baseline",
        },
        {
            "Variant": "Unconstrained MoE",
            "Backbone": "Directed-Diffusion GRU + experts",
            "Routing": "Node-level soft gate",
            "L_bal": "No",
            "L_align": "No",
            "L_force": "No",
            "L_aux": "No",
            "L_smooth": "No",
            "Params": moe_params,
            "Purpose in paper": "Tests whether routed capacity alone solves regime ambiguity",
        },
        {
            "Variant": "MoE + L_bal",
            "Backbone": "Directed-Diffusion GRU + experts",
            "Routing": "Node-level soft gate",
            "L_bal": "Yes",
            "L_align": "No",
            "L_force": "No",
            "L_aux": "No",
            "L_smooth": "No",
            "Params": moe_params,
            "Purpose in paper": "Isolates anti-starvation regularization",
        },
        {
            "Variant": "MoE + L_align",
            "Backbone": "Directed-Diffusion GRU + experts",
            "Routing": "Node-level soft gate",
            "L_bal": "No",
            "L_align": "Yes",
            "L_force": "No",
            "L_aux": "No",
            "L_smooth": "No",
            "Params": moe_params,
            "Purpose in paper": "Isolates direct regime-anchor supervision without balancing",
        },
        {
            "Variant": "MoE + L_bal + L_align",
            "Backbone": "Directed-Diffusion GRU + experts",
            "Routing": "Node-level soft gate",
            "L_bal": "Yes",
            "L_align": "Yes",
            "L_force": "No",
            "L_aux": "No",
            "L_smooth": "No",
            "Params": moe_params,
            "Purpose in paper": "Adds coarse regime-anchor consistency",
        },
        {
            "Variant": "MoE + L_bal + L_align + L_force",
            "Backbone": "Directed-Diffusion GRU + experts",
            "Routing": "Node-level soft gate",
            "L_bal": "Yes",
            "L_align": "Yes",
            "L_force": "Yes",
            "L_aux": "No",
            "L_smooth": "No",
            "Params": moe_params,
            "Purpose in paper": "Adds boundary-focused forcing without wake and smoothness terms",
        },
        {
            "Variant": "MoE + L_bal + L_align + L_force + L_smooth",
            "Backbone": "Directed-Diffusion GRU + experts",
            "Routing": "Node-level soft gate",
            "L_bal": "Yes",
            "L_align": "Yes",
            "L_force": "Yes (WTB only)",
            "L_aux": "No",
            "L_smooth": "Yes",
            "Params": moe_params,
            "Purpose in paper": "WTB near-full correction before adding wake auxiliary supervision",
        },
        {
            "Variant": "Physics-Aligned MoE",
            "Backbone": "Directed-Diffusion GRU + experts",
            "Routing": "Node-level soft gate",
            "L_bal": "Yes",
            "L_align": "Yes",
            "L_force": "Yes (WTB only)",
            "L_aux": "Yes (WTB only)",
            "L_smooth": "Yes",
            "Params": moe_params,
            "Purpose in paper": "Full routing correction used in the main results",
        },
    ]
    pd.DataFrame(rows).to_csv(output_path, index=False)
    return output_path


def _latex_escape(text: Any) -> str:
    if text is None or (not isinstance(text, str) and pd.isna(text)):
        return "--"
    value = str(text).strip()
    if not value or value.lower() == "nan":
        return "--"
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
    }
    for source, target in replacements.items():
        value = value.replace(source, target)
    return value


def _latex_metric(text: Any) -> str:
    if text is None or (not isinstance(text, str) and pd.isna(text)):
        return "--"
    value = str(text).strip()
    if not value or value.lower() == "nan":
        return "--"
    value = value.replace("+/-", r"$\pm$")
    value = value.replace("±", r"$\pm$")
    value = value.replace("Â±", r"$\pm$")
    value = value.replace("¡À", r"$\pm$")
    value = value.replace("卤", r"$\pm$")
    return _latex_escape(value).replace(r"\$\textbackslash{}pm\$", r"$\pm$")


def _write_latex(path: Path | str, content: str) -> Path:
    path = Path(path)
    ensure_dir(path.parent)
    path.write_text(content, encoding="utf-8")
    return path


def build_main_benchmark_tex(
    wtb_df: pd.DataFrame,
    era5_df: pd.DataFrame,
    output_path: Path | str,
) -> Path:
    wtb_df = _prepare_wtb_main_display_df(wtb_df)
    wtb_main = _select_wtb_forecasting_subset(wtb_df)
    era5_main = _select_era5_forecasting_subset(era5_df)
    wtb_summary = _ordered_rows(
        _summarize_metrics(
            _ordered_rows(wtb_main[wtb_main["model"].isin(WTB_MAIN_TABLE_ORDER)].copy(), "model", WTB_MAIN_TABLE_ORDER),
            ["model"],
            ["overall_rmse", "overall_mae", "switch_rmse", "switch_mae"],
        ),
        "model",
        WTB_MAIN_TABLE_ORDER,
    )
    era5_summary = _ordered_rows(
        _summarize_metrics(
            _ordered_rows(era5_main[era5_main["model"].isin(ERA5_FORECASTING_ORDER)].copy(), "model", ERA5_FORECASTING_ORDER),
            ["model"],
            ["overall_rmse", "overall_mae", "switch_rmse", "switch_mae"],
        ),
        "model",
        ERA5_FORECASTING_ORDER,
    )
    lines = [
        r"\begin{table}[t]",
        r"\centering",
        r"\scriptsize",
        r"\setlength{\tabcolsep}{4pt}",
        r"\renewcommand{\arraystretch}{1.04}",
        r"\caption*{\textbf{Table 3.} Main forecasting performance with representative WTB baselines and ERA5 checks (mean $\pm$ std across seeds where repeated runs are available). Expanded WTB strict-cache baselines are reported in Supplementary Table A12.}",
        r"\begin{tabular}{lrrrr}",
        r"\toprule",
        r"Model & Overall RMSE & Overall MAE & Switch RMSE & Switch MAE \\",
        r"\midrule",
        r"\multicolumn{5}{l}{\textit{Panel A. WTB}} \\",
    ]
    for _, row in wtb_summary.iterrows():
        lines.append(
            f"{_model_display_name(str(row['model']))} & "
            f"{_latex_metric(row['overall_rmse_display'])} & "
            f"{_latex_metric(row['overall_mae_display'])} & "
            f"{_latex_metric(row['switch_rmse_display'])} & "
            f"{_latex_metric(row['switch_mae_display'])} \\\\"
        )
    lines.extend([r"\addlinespace[2pt]", r"\multicolumn{5}{l}{\textit{Panel B. ERA5}} \\"])
    for _, row in era5_summary.iterrows():
        lines.append(
            f"{_model_display_name(str(row['model']))} & "
            f"{_latex_metric(row['overall_rmse_display'])} & "
            f"{_latex_metric(row['overall_mae_display'])} & "
            f"{_latex_metric(row['switch_rmse_display'])} & "
            f"{_latex_metric(row['switch_mae_display'])} \\\\"
        )
    lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}", ""])
    return _write_latex(output_path, "\n".join(lines))


def build_regime_wise_tex(
    wtb_df: pd.DataFrame,
    era5_df: pd.DataFrame,
    output_path: Path | str,
) -> Path:
    wtb_df = _prepare_wtb_main_display_df(wtb_df)
    wtb_main = _select_wtb_forecasting_subset(wtb_df)
    era5_main = _select_era5_forecasting_subset(era5_df)
    wtb_summary = _ordered_rows(
        _summarize_metrics(
            _ordered_rows(wtb_main[wtb_main["model"].isin(WTB_FORECASTING_ORDER)].copy(), "model", WTB_FORECASTING_ORDER),
            ["model"],
            ["idle_rmse", "mppt_rmse", "pitch_control_rmse", "transition_rmse", "switch_rmse"],
        ),
        "model",
        WTB_FORECASTING_ORDER,
    )
    era5_summary = _ordered_rows(
        _summarize_metrics(
            _ordered_rows(era5_main[era5_main["model"].isin(ERA5_FORECASTING_ORDER)].copy(), "model", ERA5_FORECASTING_ORDER),
            ["model"],
            ["convective_rmse", "stable_rmse", "transition_rmse", "switch_rmse"],
        ),
        "model",
        ERA5_FORECASTING_ORDER,
    )
    lines = [
        r"\begin{table}[t]",
        r"\centering",
        r"\scriptsize",
        r"\setlength{\tabcolsep}{3pt}",
        r"\renewcommand{\arraystretch}{1.04}",
        r"\caption*{\textbf{Table 4.} Regime-slice and transition-window performance, including strong WTB and ERA5 forecasting baselines (mean $\pm$ std across seeds where repeated runs are available).}",
        r"\begin{tabular}{lrrrrr}",
        r"\toprule",
        r"Model & idle & MPPT & pitch-control & transition & switch-window \\",
        r"\midrule",
        r"\multicolumn{6}{l}{\textit{Panel A. WTB}} \\",
    ]
    for _, row in wtb_summary.iterrows():
        lines.append(
            f"{_model_display_name(str(row['model']))} & "
            f"{_latex_metric(row['idle_rmse_display'])} & "
            f"{_latex_metric(row['mppt_rmse_display'])} & "
            f"{_latex_metric(row['pitch_control_rmse_display'])} & "
            f"{_latex_metric(row['transition_rmse_display'])} & "
            f"{_latex_metric(row['switch_rmse_display'])} \\\\"
        )
    lines.extend(
        [
            r"\bottomrule",
            r"\end{tabular}",
            r"",
            r"\vspace{0.45em}",
            r"\begin{tabular}{lrrrr}",
            r"\toprule",
            r"Model & convective & stable & transition & switch-window \\",
            r"\midrule",
            r"\multicolumn{5}{l}{\textit{Panel B. ERA5}} \\",
        ]
    )
    for _, row in era5_summary.iterrows():
        lines.append(
            f"{_model_display_name(str(row['model']))} & "
            f"{_latex_metric(row['convective_rmse_display'])} & "
            f"{_latex_metric(row['stable_rmse_display'])} & "
            f"{_latex_metric(row['transition_rmse_display'])} & "
            f"{_latex_metric(row['switch_rmse_display'])} \\\\"
        )
    lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}", ""])
    return _write_latex(output_path, "\n".join(lines))


def build_routing_quality_tex(
    wtb_df: pd.DataFrame,
    era5_df: pd.DataFrame,
    output_path: Path | str,
) -> Path:
    wtb_df = _prepare_wtb_main_display_df(wtb_df)
    order = ["Unconstrained MoE", "Physics-Aligned MoE"]
    wtb_order = ["Unconstrained MoE", WTB_CORRECTED_DISPLAY_MODEL]
    wtb_main = _select_group(wtb_df, "main")
    era5_main = _select_group(era5_df, "main")
    wtb_summary = _ordered_rows(
        _summarize_metrics(
            _ordered_rows(wtb_main[wtb_main["model"].isin(wtb_order)].copy(), "model", wtb_order),
            ["model"],
            ["nmi", "ari", "expert_usage_entropy", "expert_usage_variance"],
        ),
        "model",
        wtb_order,
    )
    era5_summary = _ordered_rows(
        _summarize_metrics(
            _ordered_rows(era5_main[era5_main["model"].isin(order)].copy(), "model", order),
            ["model"],
            ["nmi", "ari", "expert_usage_entropy", "expert_usage_variance"],
        ),
        "model",
        order,
    )
    lines = [
        r"\begin{table}[t]",
        r"\centering",
        r"\small",
        r"\setlength{\tabcolsep}{7pt}",
        r"\renewcommand{\arraystretch}{1.08}",
        r"\caption*{\textbf{Table 5.} Routing agreement and usage statistics (mean $\pm$ std across seeds where repeated runs are available; single validated corrected runs are reported without uncertainty).}",
        r"\begin{tabular}{lrrrr}",
        r"\toprule",
        r"Model & NMI & ARI & Entropy & Variance \\",
        r"\midrule",
        r"\multicolumn{5}{l}{\textit{Panel A. WTB}} \\",
    ]
    for _, row in wtb_summary.iterrows():
        lines.append(
            f"{_model_display_name(str(row['model']))} & "
            f"{_latex_metric(row['nmi_display'])} & "
            f"{_latex_metric(row['ari_display'])} & "
            f"{_latex_metric(row['expert_usage_entropy_display'])} & "
            f"{_latex_metric(row['expert_usage_variance_display'])} \\\\"
        )
    lines.extend([r"\addlinespace[2pt]", r"\multicolumn{5}{l}{\textit{Panel B. ERA5}} \\"])
    for _, row in era5_summary.iterrows():
        lines.append(
            f"{_model_display_name(str(row['model']))} & "
            f"{_latex_metric(row['nmi_display'])} & "
            f"{_latex_metric(row['ari_display'])} & "
            f"{_latex_metric(row['expert_usage_entropy_display'])} & "
            f"{_latex_metric(row['expert_usage_variance_display'])} \\\\"
        )
    lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}", ""])
    return _write_latex(output_path, "\n".join(lines))


def build_wtb_ablation_tex(
    wtb_df: pd.DataFrame,
    output_path: Path | str,
) -> Path:
    wtb_ablation = _wtb_ablation_reference_subset(wtb_df)
    summary = _ordered_rows(
        _summarize_metrics(
            _ordered_rows(wtb_ablation[wtb_ablation["model"].isin(WTB_ABLATION_ORDER)].copy(), "model", WTB_ABLATION_ORDER),
            ["model"],
            ["overall_rmse", "switch_rmse", "pitch_control_rmse", "nmi", "ari"],
        ),
        "model",
        WTB_ABLATION_ORDER,
    )
    summary_lookup = {str(row["model"]): row for _, row in summary.iterrows()}
    lines = [
        r"\begin{table}[t]",
        r"\centering",
        r"\scriptsize",
        r"\setlength{\tabcolsep}{3pt}",
        r"\renewcommand{\arraystretch}{1.04}",
        r"\caption*{\textbf{Table 6.} WTB ablation on routing correction components (mean $\pm$ std across seeds).}",
        r"\begin{tabular}{lrrrrr}",
        r"\toprule",
        r"Model & Overall RMSE & Switch RMSE & Pitch-control RMSE & NMI & ARI \\",
        r"\midrule",
    ]
    for model_name in WTB_ABLATION_ORDER:
        row = summary_lookup.get(model_name, {})
        lines.append(
            f"{_model_display_name(model_name)} & "
            f"{_latex_metric(row.get('overall_rmse_display', ''))} & "
            f"{_latex_metric(row.get('switch_rmse_display', ''))} & "
            f"{_latex_metric(row.get('pitch_control_rmse_display', ''))} & "
            f"{_latex_metric(row.get('nmi_display', ''))} & "
            f"{_latex_metric(row.get('ari_display', ''))} \\\\"
        )
    lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}", ""])
    return _write_latex(output_path, "\n".join(lines))


def build_robustness_tex(
    wtb_df: pd.DataFrame,
    era5_df: pd.DataFrame,
    wtb_sensitivity_df: pd.DataFrame | None,
    output_path: Path | str,
) -> Path:
    robustness_csv = build_robustness_table(
        wtb_df,
        era5_df,
        wtb_sensitivity_df=wtb_sensitivity_df,
        output_path=Path(output_path).with_suffix(".csv"),
    )
    robustness = pd.read_csv(robustness_csv)
    panel_a = robustness[(robustness["Panel"] == "A_main_seeds") & (robustness["Dataset"] == "WTB")].copy()
    panel_d = robustness[(robustness["Panel"] == "A_main_seeds") & (robustness["Dataset"] == "ERA5")].copy()
    panel_b = robustness[robustness["Panel"] == "B_wtb_sensitivity"].copy()
    panel_c = robustness[robustness["Panel"] == "C_wtb_efficiency"].copy()
    lines = [
        r"\begin{table}[t]",
        r"\centering",
        r"\scriptsize",
        r"\setlength{\tabcolsep}{4pt}",
        r"\renewcommand{\arraystretch}{1.00}",
        r"\caption*{\textbf{Table 7.} Robustness, ERA5 baseline coverage, and in-family fairness summary.}",
        r"\begin{tabular}{lrrrr}",
        r"\toprule",
        r"Model & Overall RMSE & Switch RMSE & Pitch-control RMSE & NMI \\",
        r"\midrule",
        r"\multicolumn{5}{l}{\textit{Panel A. WTB main-model stability across seeds}} \\",
    ]
    for _, row in panel_a.iterrows():
        lines.append(
            f"{_model_display_name(str(row['Condition']))} & "
            f"{_latex_metric(row['Overall RMSE'])} & "
            f"{_latex_metric(row['Switch RMSE'])} & "
            f"{_latex_metric(row['Pitch-control RMSE'])} & "
            f"{_latex_metric(row['NMI'])} \\\\"
        )
    if not panel_b.empty:
        lines.extend(
            [
                r"\bottomrule",
                r"\end{tabular}",
                r"",
                r"\vspace{0.25em}",
                r"\begin{tabular}{lrr}",
                r"\toprule",
                r"WTB sensitivity setting & Switch RMSE & NMI \\",
                r"\midrule",
                r"\multicolumn{3}{l}{\textit{Panel B. WTB threshold and routing sensitivity}} \\",
            ]
        )
        for _, row in panel_b.iterrows():
            lines.append(
                f"{_latex_escape(row['Condition'])} & "
                f"{_latex_metric(row['Switch RMSE'])} & "
                f"{_latex_metric(row['NMI'])} \\\\"
            )
        lines.extend([r"\bottomrule", r"\end{tabular}"])
    else:
        lines.extend([r"\bottomrule", r"\end{tabular}"])
    if not panel_d.empty:
        lines.extend(
            [
                r"",
                r"\vspace{0.25em}",
                r"\begin{tabular}{lrrr}",
                r"\toprule",
                r"ERA5 model & Overall RMSE & Switch RMSE & NMI \\",
                r"\midrule",
                r"\multicolumn{4}{l}{\textit{Panel C. ERA5 baseline coverage}} \\",
            ]
        )
        for _, row in panel_d.iterrows():
            lines.append(
                f"{_model_display_name(str(row['Condition']))} & "
                f"{_latex_metric(row['Overall RMSE'])} & "
                f"{_latex_metric(row['Switch RMSE'])} & "
                f"{_latex_metric(row['NMI'])} \\\\"
            )
        lines.extend([r"\bottomrule", r"\end{tabular}"])
    if not panel_c.empty:
        lines.extend(
            [
                r"",
                r"\vspace{0.25em}",
                r"\begin{tabular}{lrrr}",
                r"\toprule",
                r"Model & Params & Train hours & Windows/s \\",
                r"\midrule",
                r"\multicolumn{4}{l}{\textit{Panel D. In-family fairness and efficiency}} \\",
            ]
        )
        for _, row in panel_c.iterrows():
            lines.append(
                f"{_model_display_name(str(row['Condition']))} & "
                f"{_latex_escape(row['Params'])} & "
                f"{_latex_escape(row['Train hours'])} & "
                f"{_latex_metric(row['Windows/s'])} \\\\"
            )
        lines.extend([r"\bottomrule", r"\end{tabular}"])
    lines.extend([r"\end{table}", ""])
    return _write_latex(output_path, "\n".join(lines))


def generate_architecture_figure(output_dir: Path | str) -> tuple[Path, Path]:
    output_dir = ensure_dir(output_dir)
    png_path = Path(output_dir) / "figure1_architecture.png"
    pdf_path = Path(output_dir) / "figure1_architecture.pdf"
    svg_path = Path(output_dir) / "figure1_architecture.svg"

    for path in (png_path, pdf_path, svg_path):
        if path.exists():
            path.unlink()

    fig, ax = plt.subplots(figsize=(12.0, 6.8))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    def box(
        x: float,
        y: float,
        w: float,
        h: float,
        title: str,
        body: str,
        *,
        face: str,
        edge: str,
        title_size: float = 10.5,
        body_size: float = 8.4,
    ) -> None:
        ax.add_patch(
            plt.Rectangle(
                (x, y),
                w,
                h,
                facecolor=face,
                edgecolor=edge,
                linewidth=1.35,
            )
        )
        ax.text(
            x + w / 2,
            y + h - 0.035,
            title,
            ha="center",
            va="top",
            fontsize=title_size,
            weight="bold",
            color="#111827",
        )
        ax.text(
            x + w / 2,
            y + h / 2 - 0.015,
            body,
            ha="center",
            va="center",
            fontsize=body_size,
            color="#111827",
            linespacing=1.28,
        )

    def arrow(start: tuple[float, float], end: tuple[float, float], *, color: str = "#334155") -> None:
        ax.annotate(
            "",
            xy=end,
            xytext=start,
            arrowprops={"arrowstyle": "->", "lw": 1.45, "color": color, "shrinkA": 2, "shrinkB": 2},
        )

    ax.text(
        0.5,
        0.955,
        "Physics-aligned regime-aware MoE for operating-boundary accountability",
        ha="center",
        va="center",
        fontsize=13.0,
        weight="bold",
        color="#0f172a",
    )

    box(
        0.04,
        0.70,
        0.18,
        0.16,
        "WTB SCADA",
        "wind speed\nactive power\npitch channels\navailability masks",
        face="#e0f2fe",
        edge="#0369a1",
    )
    box(
        0.04,
        0.46,
        0.18,
        0.16,
        "ERA5 Reanalysis",
        "sensible heat flux\n2 m temperature\nwind state\nlocal grid patch",
        face="#eff6ff",
        edge="#2563eb",
    )
    box(
        0.28,
        0.70,
        0.20,
        0.16,
        "WTB Anchors",
        "idle / MPPT / pitch\nMPPT-to-pitch band\nwake exposure score",
        face="#ecfdf5",
        edge="#047857",
    )
    box(
        0.28,
        0.46,
        0.20,
        0.16,
        "ERA5 Anchors",
        "stable / convective\nflux-gradient transition\nHaversine graph",
        face="#f0fdf4",
        edge="#16a34a",
    )
    box(
        0.54,
        0.58,
        0.18,
        0.18,
        "Shared Encoder",
        "directed diffusion\ninbound / outbound\nGRU context state",
        face="#fef9c3",
        edge="#a16207",
    )
    box(
        0.77,
        0.58,
        0.18,
        0.18,
        "Node-level MoE",
        "physics anchor + context\nsoft gate distribution\nexpert forecasts",
        face="#ffedd5",
        edge="#c2410c",
    )
    box(
        0.27,
        0.18,
        0.23,
        0.16,
        "Routing Constraints",
        "load balance\nregime alignment\nboundary forcing\nwake auxiliary + smoothness",
        face="#f8fafc",
        edge="#64748b",
        body_size=8.2,
    )
    box(
        0.56,
        0.18,
        0.25,
        0.16,
        "Audits and Diagnostics",
        "forecast RMSE\nNMI / ARI replay\nintervention + placebo\nreserve cost / violation / shortage",
        face="#fdf2f8",
        edge="#be185d",
        body_size=8.1,
    )

    arrow((0.22, 0.78), (0.28, 0.78))
    arrow((0.22, 0.54), (0.28, 0.54))
    arrow((0.48, 0.78), (0.54, 0.68))
    arrow((0.48, 0.54), (0.54, 0.66))
    arrow((0.72, 0.67), (0.77, 0.67))
    arrow((0.48, 0.73), (0.50, 0.34), color="#64748b")
    arrow((0.50, 0.34), (0.77, 0.58), color="#64748b")
    arrow((0.86, 0.58), (0.70, 0.34), color="#be185d")

    ax.text(
        0.04,
        0.085,
        "Interpretation: WTB tests a control-confounded turbine boundary; ERA5 is an observability contrast where the regime marker is visible.",
        ha="left",
        va="center",
        fontsize=8.7,
        color="#334155",
    )
    ax.text(
        0.04,
        0.045,
        "The routed model is evaluated as an accountability object, then linked to a frozen validation-to-test reserve diagnostic.",
        ha="left",
        va="center",
        fontsize=8.7,
        color="#334155",
    )

    fig.tight_layout(pad=0.25)
    fig.savefig(pdf_path, bbox_inches="tight")
    fig.savefig(svg_path, bbox_inches="tight")
    fig.savefig(png_path, dpi=240, bbox_inches="tight")
    plt.close(fig)

    return png_path, pdf_path


def copy_paper_figures(
    figure_sources: dict[str, Path],
    output_dir: Path | str,
) -> list[Path]:
    output_dir = ensure_dir(output_dir)
    exported = []
    for target_name, source_path in figure_sources.items():
        destination = Path(output_dir) / target_name
        shutil.copy2(source_path, destination)
        exported.append(destination)
    return exported


def _plot_confusion(conf: np.ndarray, labels: list[str], output_path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(6, 5))
    sns.heatmap(conf, annot=True, fmt="d", cmap="Blues", xticklabels=labels, yticklabels=labels, ax=ax)
    ax.set_xlabel("Predicted Expert")
    ax.set_ylabel("Physical Regime")
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)
    return output_path


def _copy_or_render_confusion(run_dir: Path, output_path: Path, labels: list[str]) -> Path | None:
    source = run_dir / "test_metrics" / "gate_regime_confusion.png"
    if source.exists():
        shutil.copy2(source, output_path)
        return output_path
    metrics_path = run_dir / "test_metrics" / "metrics.json"
    if not metrics_path.exists():
        return None
    metrics = load_json(metrics_path)
    conf = np.asarray(metrics.get("gate_alignment", {}).get("confusion_matrix", []), dtype=np.int64)
    if conf.size == 0:
        return None
    return _plot_confusion(conf, labels, output_path)


def _build_wtb_threshold_bundle(
    bundle: CacheBundle,
    rated_wind: float,
    pitch_threshold: float,
) -> CacheBundle:
    wspd = np.asarray(bundle.physics[..., 0], dtype=np.float32)
    pab_mean = np.asarray(bundle.physics[..., 1], dtype=np.float32)
    wake_score = np.asarray(bundle.physics[..., 2], dtype=np.float32)
    train_stop = int(bundle.metadata["split_bounds"]["train"][1])

    op_regime, op_valid = compute_wtb_operation_regime(
        wspd,
        pab_mean,
        rated_wind=rated_wind,
        pitch_threshold=pitch_threshold,
    )
    wake_flag, wake_valid, wake_threshold = compute_wtb_wake_flag(wake_score, op_regime, train_stop)
    primary_class_weights = inverse_frequency_weights_from_labels(op_regime, op_valid, 3)
    pitch_binary_labels = np.zeros_like(op_regime, dtype=np.int16)
    pitch_valid = ((op_regime == 1) | (op_regime == 2)).astype(np.float32)
    pitch_binary_labels[op_regime == 2] = 1
    pitch_force_weights = inverse_frequency_weights_from_labels(pitch_binary_labels, pitch_valid, 2)

    wake_valid_mask = wake_valid.astype(bool)
    if wake_valid_mask.any():
        wake_train = wake_flag[:train_stop][wake_valid_mask[:train_stop]]
        pos_count = float((wake_train == 1).sum())
        neg_count = float((wake_train == 0).sum())
        wake_pos_weight = neg_count / max(pos_count, 1.0)
    else:
        wake_pos_weight = 1.0

    metadata = dict(bundle.metadata)
    metadata["primary_class_weights"] = primary_class_weights
    metadata["pitch_force_weights"] = pitch_force_weights
    metadata["wake_pos_weight"] = wake_pos_weight
    metadata["wake_threshold"] = wake_threshold
    metadata["wtb_thresholds"] = {
        "cut_in_wind": 3.0,
        "rated_wind": rated_wind,
        "pitch_threshold": pitch_threshold,
    }
    return replace(
        bundle,
        metadata=metadata,
        regime_primary=op_regime.astype(np.int16),
        regime_primary_valid=op_valid.astype(np.float32),
        regime_aux=wake_flag.astype(np.int16),
        regime_aux_valid=wake_valid.astype(np.float32),
    )


def run_single_experiment(
    bundle: CacheBundle,
    output_root: Path,
    run_name: str,
    model_mode: str,
    model_hidden_dim: int,
    num_experts: int,
    dropout: float,
    tau: float,
    train_config: TrainConfig,
    eval_config: EvalConfig,
    capacity_match_dense: bool = False,
    variant_key: str = "",
    experiment_group: str = "",
    setting_group: str = "",
    setting_value: Any = "",
    setting_label: str = "",
) -> dict[str, Any]:
    if capacity_match_dense and model_mode == "baseline_dense":
        model_hidden_dim = resolve_capacity_matched_hidden_dim(
            bundle=bundle,
            mode=model_mode,
            hidden_dim=model_hidden_dim,
            num_experts=num_experts,
            tau=tau,
            dropout=dropout,
        )
    model_config = ModelConfig(
        hidden_dim=model_hidden_dim,
        num_experts=num_experts,
        dropout=dropout,
        tau=tau,
        primary_num_classes=bundle.metadata["primary_num_classes"],
        gate_physics_dim=int(bundle.physics.shape[-1]),
    )
    run_dir = ensure_dir(Path(output_root) / run_name)
    result = train_model(bundle, run_dir, model_config, train_config, eval_config)
    params = count_trainable_parameters(
        build_model_for_count(
            bundle,
            model_mode,
            hidden_dim=model_hidden_dim,
            num_experts=num_experts,
            tau=tau,
            dropout=dropout,
        )
    )
    result["parameter_count"] = params
    result["model_mode"] = model_mode
    result["hidden_dim"] = model_hidden_dim
    result["num_experts"] = num_experts
    result["label"] = train_config.label or run_name
    result["seed"] = int(train_config.seed)
    result["variant_key"] = variant_key
    result["experiment_group"] = experiment_group
    result["setting_group"] = setting_group
    result["setting_value"] = setting_value
    result["setting_label"] = setting_label
    result["loss_weights"] = train_config.effective_loss_weights()
    if bundle.metadata.get("dataset") == "external_wind":
        result["dataset"] = "external_wind"
        result["farm"] = bundle.metadata.get("farm", "")
        result["target_farm"] = bundle.metadata.get("target_farm", "")
        result["external_split"] = bundle.metadata.get("external_split", "")
        result["source_url"] = bundle.metadata.get("source_url", "")
        result["target_source_url"] = bundle.metadata.get("target_source_url", "")
        result["license"] = bundle.metadata.get("license", "")
    save_json(run_dir / "training_summary.json", result)
    del model_config
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    return result


def _run_is_complete(run_dir: Path) -> bool:
    summary_path = run_dir / "training_summary.json"
    metrics_path = run_dir / "test_metrics" / "metrics.json"
    return summary_path.exists() and metrics_path.exists()


def _pid_alive(pid: int) -> bool:
    if os.name == "nt":
        try:
            result = subprocess.run(
                ["tasklist", "/FI", f"PID eq {int(pid)}", "/FO", "CSV", "/NH"],
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError:
            return False
        return str(int(pid)) in result.stdout
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _try_acquire_run_lock(run_dir: Path, ttl_seconds: float = 12 * 3600) -> bool:
    ensure_dir(run_dir)
    lock_path = run_dir / ".run_lock.json"
    now = time.time()
    if lock_path.exists():
        try:
            payload = load_json(lock_path)
        except Exception:
            payload = {}
        pid = payload.get("pid")
        created_at = payload.get("created_at")
        stale = False
        try:
            if created_at is None:
                stale = True
            else:
                stale = (now - float(created_at)) > float(ttl_seconds)
        except Exception:
            stale = True
        if not stale and isinstance(pid, int) and pid > 0:
            if not _pid_alive(pid):
                stale = True
        if not stale:
            return False
        try:
            lock_path.unlink()
        except OSError:
            return False
    try:
        fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        return False
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump({"pid": os.getpid(), "created_at": now}, f)
    except Exception:
        try:
            os.close(fd)
        except OSError:
            pass
        try:
            lock_path.unlink()
        except OSError:
            pass
        return False
    return True


def _release_run_lock(run_dir: Path) -> None:
    lock_path = run_dir / ".run_lock.json"
    try:
        if lock_path.exists():
            lock_path.unlink()
    except OSError:
        return


def _is_transient_error(exc: BaseException) -> bool:
    message = (str(exc) or repr(exc)).lower()
    needles = [
        "cuda out of memory",
        "cublas_status_alloc_failed",
        "cuda error",
        "device-side assert",
        "device not ready",
        "nccl",
        "cudnn_status",
        "the launch timed out",
        "illegal memory access",
        "resource temporarily unavailable",
        "too many open files",
        "invalid argument",
        "winerror 87",
        "errno 22",
        "oserror(22",
    ]
    return any(needle in message for needle in needles)


def _paper_worker(payload: dict[str, Any]) -> dict[str, Any]:
    device_id = payload.get("device_id")
    if device_id is not None and torch.cuda.is_available():
        torch.cuda.set_device(int(device_id))
    max_cpu_threads = payload.get("cpu_threads")
    if max_cpu_threads:
        torch.set_num_threads(int(max_cpu_threads))

    cache_dir = Path(str(payload["cache_dir"]))
    output_root = ensure_dir(Path(str(payload["output_root"])))
    dataset = str(payload["dataset"])
    spec = dict(payload["spec"])
    seed = int(payload["seed"])
    experiment_group = str(payload.get("experiment_group", ""))
    resume = bool(payload.get("resume", True))
    attempt = int(payload.get("attempt", 1))
    base_model_config = payload["base_model_config"]
    base_train_config = payload["base_train_config"]
    eval_config = payload["eval_config"]

    run_name = f"{dataset}_{spec['key']}_seed{seed}"
    run_dir = output_root / run_name
    if resume and _run_is_complete(run_dir):
        return {
            "skipped": True,
            "dataset": dataset,
            "group": experiment_group,
            "variant_key": spec["key"],
            "label": spec.get("label", ""),
            "seed": seed,
            "run_name": run_name,
            "run_dir": str(run_dir),
            "attempt": attempt,
        }

    if not _try_acquire_run_lock(run_dir):
        return {
            "skipped": True,
            "skip_reason": "locked",
            "dataset": dataset,
            "group": experiment_group,
            "variant_key": spec["key"],
            "label": spec.get("label", ""),
            "seed": seed,
            "run_name": run_name,
            "run_dir": str(run_dir),
            "attempt": attempt,
        }
    try:
        bundle = load_cache_bundle(cache_dir)
        run_bundle = bundle
        if dataset == "wtb" and "bundle_overrides" in spec:
            overrides = dict(spec.get("bundle_overrides", {}))
            if "rated_wind" in overrides or "pitch_threshold" in overrides:
                run_bundle = _build_wtb_threshold_bundle(
                    bundle,
                    rated_wind=float(
                        overrides.get(
                            "rated_wind",
                            bundle.metadata.get("wtb_thresholds", {}).get("rated_wind", 10.5),
                        )
                    ),
                    pitch_threshold=float(
                        overrides.get(
                            "pitch_threshold",
                            bundle.metadata.get("wtb_thresholds", {}).get("pitch_threshold", 2.0),
                        )
                    ),
                )

        model_config = _copy_model_config(base_model_config)
        for key, value in spec.get("model_overrides", {}).items():
            setattr(model_config, key, value)
        train_config = _copy_train_config(base_train_config)
        train_config.mode = spec["mode"]
        train_config.seed = seed
        train_config.label = spec["label"]
        for key, value in spec.get("train_overrides", {}).items():
            setattr(train_config, key, value)

        result = run_single_experiment(
            bundle=run_bundle,
            output_root=Path(output_root),
            run_name=run_name,
            model_mode=spec["mode"],
            model_hidden_dim=model_config.hidden_dim,
            num_experts=model_config.num_experts,
            dropout=model_config.dropout,
            tau=model_config.tau,
            train_config=train_config,
            eval_config=eval_config,
            capacity_match_dense=bool(spec.get("capacity_match_dense", False)),
            variant_key=str(spec["key"]),
            experiment_group=experiment_group,
            setting_group=str(spec.get("setting_group", "")),
            setting_value=spec.get("setting_value", ""),
            setting_label=str(spec.get("setting_label", "")),
        )
        return {
            "skipped": False,
            "dataset": dataset,
            "group": experiment_group,
            "variant_key": spec["key"],
            "label": spec.get("label", ""),
            "seed": seed,
            "run_name": run_name,
            "run_dir": str(run_dir),
            "attempt": attempt,
            **result,
        }
    except Exception as exc:
        return {
            "skipped": False,
            "failed": True,
            "error": repr(exc),
            "traceback": traceback.format_exc(),
            "transient": _is_transient_error(exc),
            "dataset": dataset,
            "group": experiment_group,
            "variant_key": spec["key"],
            "label": spec.get("label", ""),
            "seed": seed,
            "run_name": run_name,
            "run_dir": str(run_dir),
            "attempt": attempt,
        }
    finally:
        _release_run_lock(run_dir)


def _variant_spec_catalog(dataset: str) -> list[dict[str, Any]]:
    defaults = paper_default_loss_weights(dataset)
    specs = [
        {
            "key": "dense",
            "label": "Capacity-Matched Dense Diffusion-GRU",
            "mode": "baseline_dense",
            "capacity_match_dense": True,
        },
        {
            "key": "unconstrained",
            "label": "Unconstrained MoE",
            "mode": "moe_unconstrained",
        },
        {
            "key": "bal",
            "label": "MoE + L_bal",
            "mode": "moe_balance_only",
        },
        {
            "key": "align",
            "label": "MoE + L_align",
            "mode": "moe_align_only",
            "train_overrides": {
                "align_weight": defaults["align"],
                "balance_weight": 0.0,
                "physics_force_weight": 0.0,
                "aux_weight": 0.0,
                "smooth_weight": 0.0,
            },
        },
        {
            "key": "bal_align",
            "label": "MoE + L_bal + L_align",
            "mode": "moe_balance_align",
            "train_overrides": {
                "balance_weight": defaults["balance"],
                "align_weight": defaults["align"],
                "physics_force_weight": 0.0,
                "aux_weight": 0.0,
                "smooth_weight": 0.0,
            },
        },
    ]
    if dataset in {"wtb", "external_wind"}:
        specs.append(
            {
                "key": "bal_align_force",
                "label": "MoE + L_bal + L_align + L_force",
                "mode": "moe_full_no_aux",
                "train_overrides": {
                    "balance_weight": defaults["balance"],
                    "align_weight": defaults["align"],
                    "physics_force_weight": defaults["physics_force"],
                    "aux_weight": 0.0,
                    "smooth_weight": 0.0,
                },
            }
        )
        specs.append(
            {
                "key": "bal_align_force_smooth",
                "label": "MoE + L_bal + L_align + L_force + L_smooth",
                "mode": "moe_full_no_aux",
                "train_overrides": {
                    "balance_weight": defaults["balance"],
                    "align_weight": defaults["align"],
                    "physics_force_weight": defaults["physics_force"],
                    "aux_weight": 0.0,
                    "smooth_weight": defaults["smooth"],
                },
            }
        )
        specs.append(
            {
                "key": "context_align_force",
                "label": "Context-supervised router",
                "mode": "moe_context_align",
                "train_overrides": {
                    "balance_weight": defaults["balance"],
                    "align_weight": defaults["align"],
                    "physics_force_weight": defaults["physics_force"],
                    "aux_weight": 0.0,
                    "smooth_weight": 0.0,
                },
            }
        )
        specs.append(
            {
                "key": "anchor_only",
                "label": "Anchor-only router",
                "mode": "moe_anchor_only",
                "train_overrides": {
                    "balance_weight": defaults["balance"],
                    "align_weight": defaults["align"],
                    "physics_force_weight": defaults["physics_force"],
                    "aux_weight": 0.0,
                    "smooth_weight": 0.0,
                },
            }
        )
    specs.append({"key": "full", "label": "Physics-Aligned MoE", "mode": "moe_phys_full"})
    return specs


def paper_experiment_specs(dataset: str) -> list[dict[str, Any]]:
    return _variant_spec_catalog(dataset)


def _main_variant_specs(dataset: str) -> list[dict[str, Any]]:
    keep = {"dense", "unconstrained", "full"}
    return [spec for spec in _variant_spec_catalog(dataset) if spec["key"] in keep]


def _strong_baseline_specs(dataset: str) -> list[dict[str, Any]]:
    specs = [
        {"key": "stgcn", "label": "STGCN", "mode": "baseline_stgcn"},
        {"key": "graph_wavenet", "label": "Graph WaveNet", "mode": "baseline_graph_wavenet"},
        {"key": "graph_transformer", "label": "Graph Transformer", "mode": "baseline_graph_transformer"},
        {"key": "gat_gru", "label": "GAT-GRU", "mode": "baseline_gat_gru"},
        {"key": "patchtst", "label": "PatchTST", "mode": "baseline_patchtst"},
        {"key": "itransformer", "label": "iTransformer", "mode": "baseline_itransformer"},
        {"key": "tide", "label": "TiDE", "mode": "baseline_tide"},
    ]
    if dataset == "era5":
        specs.append({"key": "tcn", "label": "TCN", "mode": "baseline_tcn"})
    return specs


def _ablation_variant_specs(dataset: str) -> list[dict[str, Any]]:
    if dataset in {"wtb", "external_wind"}:
        keep = {
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
        }
    else:
        keep = {"dense", "unconstrained", "bal", "align", "bal_align", "full"}
    return [spec for spec in _variant_spec_catalog(dataset) if spec["key"] in keep]


def _wtb_sensitivity_specs(default_num_experts: int) -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    for value in [500.0, 1000.0, 1500.0]:
        specs.append(
            {
                "key": f"sens_balance_{int(value)}",
                "label": "Physics-Aligned MoE",
                "mode": "moe_phys_full",
                "setting_group": "lambda_bal",
                "setting_value": value,
                "setting_label": f"lambda_bal={value:g}",
                "train_overrides": {"balance_weight": value},
            }
        )
    for value in [2500.0, 5000.0, 7500.0]:
        specs.append(
            {
                "key": f"sens_align_{int(value)}",
                "label": "Physics-Aligned MoE",
                "mode": "moe_phys_full",
                "setting_group": "lambda_align",
                "setting_value": value,
                "setting_label": f"lambda_align={value:g}",
                "train_overrides": {"align_weight": value},
            }
        )
    for value in [5000.0, 10000.0, 15000.0]:
        specs.append(
            {
                "key": f"sens_force_{int(value)}",
                "label": "Physics-Aligned MoE",
                "mode": "moe_phys_full",
                "setting_group": "physics_force_weight",
                "setting_value": value,
                "setting_label": f"physics_force_weight={value:g}",
                "train_overrides": {"physics_force_weight": value},
            }
        )
    for value in [7.0, 10.0, 10.5, 11.0, 13.0]:
        specs.append(
            {
                "key": f"sens_rated_{str(value).replace('.', 'p')}",
                "label": "Physics-Aligned MoE",
                "mode": "moe_phys_full",
                "setting_group": "rated_wind",
                "setting_value": value,
                "setting_label": f"rated_wind={value:.1f}",
                "bundle_overrides": {"rated_wind": value, "pitch_threshold": 2.0},
            }
        )
    for value in [0.5, 1.5, 2.0, 2.5, 20.0]:
        specs.append(
            {
                "key": f"sens_pitch_{str(value).replace('.', 'p')}",
                "label": "Physics-Aligned MoE",
                "mode": "moe_phys_full",
                "setting_group": "pitch_threshold",
                "setting_value": value,
                "setting_label": f"pitch_threshold={value:.1f}",
                "bundle_overrides": {"rated_wind": 10.5, "pitch_threshold": value},
            }
        )
    for value in [3, default_num_experts, 5]:
        specs.append(
            {
                "key": f"sens_experts_{value}",
                "label": "Physics-Aligned MoE",
                "mode": "moe_phys_full",
                "setting_group": "num_experts",
                "setting_value": value,
                "setting_label": f"num_experts={value}",
                "model_overrides": {"num_experts": value},
            }
        )
    return specs


def _era5_sensitivity_specs(default_num_experts: int) -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    for value in [0.1, 0.2, 0.3]:
        specs.append(
            {
                "key": f"era5_align_{str(value).replace('.', 'p')}",
                "label": "Physics-Aligned MoE",
                "mode": "moe_phys_full",
                "setting_group": "lambda_align",
                "setting_value": value,
                "setting_label": f"lambda_align={value:.2f}",
                "train_overrides": {"align_weight": value},
            }
        )
    for value in [2, default_num_experts, 4]:
        specs.append(
            {
                "key": f"era5_experts_{value}",
                "label": "Physics-Aligned MoE",
                "mode": "moe_phys_full",
                "setting_group": "num_experts",
                "setting_value": value,
                "setting_label": f"num_experts={value}",
                "model_overrides": {"num_experts": value},
            }
        )
    return specs


def _filter_variant_specs(
    specs: list[dict[str, Any]],
    variant_keys: Iterable[str] | None,
    group_name: str,
) -> list[dict[str, Any]]:
    requested = [str(key).strip() for key in (variant_keys or []) if str(key).strip()]
    if not requested:
        return list(specs)
    available = [str(spec["key"]) for spec in specs]
    requested_set = set(requested)
    missing = sorted(requested_set.difference(available))
    if missing:
        available_text = ", ".join(available)
        missing_text = ", ".join(missing)
        raise ValueError(f"Unknown variant key(s) for {group_name}: {missing_text}. Available: {available_text}")
    return [spec for spec in specs if str(spec["key"]) in requested_set]


def _run_spec_sequence(
    bundle: CacheBundle,
    output_root: Path,
    dataset: str,
    specs: list[dict[str, Any]],
    seeds: list[int],
    base_model_config: ModelConfig,
    base_train_config: TrainConfig,
    eval_config: EvalConfig,
    experiment_group: str,
    max_total_attempts: int = 3,
    retry_backoff_seconds: float = 30.0,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    max_total_attempts = max(int(max_total_attempts), 1)
    pending: list[tuple[dict[str, Any], int]] = []
    for spec in specs:
        for seed in seeds:
            pending.append((spec, int(seed)))

    attempt_by_run: dict[str, int] = {}
    round_index = 0
    while pending:
        round_index += 1
        next_pending: list[tuple[dict[str, Any], int]] = []
        for spec, seed in pending:
            run_name = f"{dataset}_{spec['key']}_seed{seed}"
            run_dir = Path(output_root) / run_name
            if _run_is_complete(run_dir):
                results.append(
                    {
                        "skipped": True,
                        "dataset": dataset,
                        "group": experiment_group,
                        "variant_key": spec["key"],
                        "label": spec["label"],
                        "seed": seed,
                        "run_name": run_name,
                        "run_dir": str(run_dir),
                        "attempt": attempt_by_run.get(run_name, 0) + 1,
                        "setting_group": spec.get("setting_group", ""),
                        "setting_value": spec.get("setting_value", ""),
                        "setting_label": spec.get("setting_label", ""),
                    }
                )
                continue

            attempt = attempt_by_run.get(run_name, 0) + 1
            attempt_by_run[run_name] = attempt
            if attempt > max_total_attempts:
                results.append(
                    {
                        "skipped": False,
                        "failed": True,
                        "error": "max_total_attempts_exceeded",
                        "dataset": dataset,
                        "group": experiment_group,
                        "variant_key": spec["key"],
                        "label": spec["label"],
                        "seed": seed,
                        "run_name": run_name,
                        "run_dir": str(run_dir),
                        "attempt": attempt,
                        "setting_group": spec.get("setting_group", ""),
                        "setting_value": spec.get("setting_value", ""),
                        "setting_label": spec.get("setting_label", ""),
                    }
                )
                continue

            run_bundle = bundle
            if dataset == "wtb" and spec.get("bundle_overrides"):
                run_bundle = _build_wtb_threshold_bundle(
                    bundle,
                    rated_wind=float(spec["bundle_overrides"]["rated_wind"]),
                    pitch_threshold=float(spec["bundle_overrides"]["pitch_threshold"]),
                )
            model_config = _copy_model_config(base_model_config)
            for key, value in spec.get("model_overrides", {}).items():
                setattr(model_config, key, value)
            train_config = _copy_train_config(base_train_config)
            train_config.mode = spec["mode"]
            train_config.seed = seed
            train_config.label = spec["label"]
            for key, value in spec.get("train_overrides", {}).items():
                setattr(train_config, key, value)

            if not _try_acquire_run_lock(run_dir):
                results.append(
                    {
                        "skipped": True,
                        "skip_reason": "locked",
                        "dataset": dataset,
                        "group": experiment_group,
                        "variant_key": spec["key"],
                        "label": spec["label"],
                        "seed": seed,
                        "run_name": run_name,
                        "run_dir": str(run_dir),
                        "attempt": attempt,
                        "setting_group": spec.get("setting_group", ""),
                        "setting_value": spec.get("setting_value", ""),
                        "setting_label": spec.get("setting_label", ""),
                    }
                )
                if attempt < max_total_attempts:
                    next_pending.append((spec, seed))
                continue
            try:
                result = run_single_experiment(
                    bundle=run_bundle,
                    output_root=Path(output_root),
                    run_name=run_name,
                    model_mode=spec["mode"],
                    model_hidden_dim=model_config.hidden_dim,
                    num_experts=model_config.num_experts,
                    dropout=model_config.dropout,
                    tau=model_config.tau,
                    train_config=train_config,
                    eval_config=eval_config,
                    capacity_match_dense=bool(spec.get("capacity_match_dense", False)),
                    variant_key=str(spec["key"]),
                    experiment_group=experiment_group,
                    setting_group=str(spec.get("setting_group", "")),
                    setting_value=spec.get("setting_value", ""),
                    setting_label=str(spec.get("setting_label", "")),
                )
                results.append(
                    {
                        "dataset": dataset,
                        "group": experiment_group,
                        "variant_key": spec["key"],
                        "label": spec["label"],
                        "seed": seed,
                        "run_name": run_name,
                        "run_dir": str(run_dir),
                        "attempt": attempt,
                        "setting_group": spec.get("setting_group", ""),
                        "setting_value": spec.get("setting_value", ""),
                        "setting_label": spec.get("setting_label", ""),
                        **result,
                    }
                )
            except Exception as exc:
                results.append(
                    {
                        "skipped": False,
                        "failed": True,
                        "error": repr(exc),
                        "traceback": traceback.format_exc(),
                        "transient": _is_transient_error(exc),
                        "dataset": dataset,
                        "group": experiment_group,
                        "variant_key": spec["key"],
                        "label": spec["label"],
                        "seed": seed,
                        "run_name": run_name,
                        "run_dir": str(run_dir),
                        "attempt": attempt,
                        "setting_group": spec.get("setting_group", ""),
                        "setting_value": spec.get("setting_value", ""),
                        "setting_label": spec.get("setting_label", ""),
                    }
                )
                if attempt < max_total_attempts:
                    next_pending.append((spec, seed))
            finally:
                _release_run_lock(run_dir)
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

        if not next_pending:
            break
        sleep_seconds = float(retry_backoff_seconds) * (2.0 ** max(round_index - 1, 0))
        time.sleep(min(sleep_seconds, 300.0))
        pending = next_pending
    return results


def run_paper_suite(
    bundle: CacheBundle,
    output_root: Path | str,
    dataset: str,
    seeds: list[int],
    base_model_config: ModelConfig,
    base_train_config: TrainConfig,
    eval_config: EvalConfig,
    groups: Iterable[str] | None = None,
    strong_baseline_seeds: list[int] | None = None,
    ablation_seeds: list[int] | None = None,
    sensitivity_seeds: list[int] | None = None,
    variant_keys: Iterable[str] | None = None,
    retry_backoff_seconds: float = 30.0,
    max_total_attempts: int = 3,
) -> list[dict[str, Any]]:
    output_root = ensure_dir(output_root)
    groups = list(groups or ["main"])
    strong_baseline_seeds = strong_baseline_seeds or seeds
    ablation_seeds = ablation_seeds or seeds
    sensitivity_seeds = sensitivity_seeds or ablation_seeds
    results: list[dict[str, Any]] = []

    if "main" in groups:
        results.extend(
            _run_spec_sequence(
                bundle=bundle,
                output_root=Path(output_root),
                dataset=dataset,
                specs=_filter_variant_specs(_main_variant_specs(dataset), variant_keys, "main"),
                seeds=seeds,
                base_model_config=base_model_config,
                base_train_config=base_train_config,
                eval_config=eval_config,
                experiment_group="main",
                retry_backoff_seconds=retry_backoff_seconds,
                max_total_attempts=max_total_attempts,
            )
        )
    if "strong_baselines" in groups:
        results.extend(
            _run_spec_sequence(
                bundle=bundle,
                output_root=Path(output_root),
                dataset=dataset,
                specs=_filter_variant_specs(_strong_baseline_specs(dataset), variant_keys, "strong_baselines"),
                seeds=strong_baseline_seeds,
                base_model_config=base_model_config,
                base_train_config=base_train_config,
                eval_config=eval_config,
                experiment_group="strong_baselines",
                retry_backoff_seconds=retry_backoff_seconds,
                max_total_attempts=max_total_attempts,
            )
        )
    if "ablation" in groups:
        results.extend(
            _run_spec_sequence(
                bundle=bundle,
                output_root=Path(output_root),
                dataset=dataset,
                specs=_filter_variant_specs(_ablation_variant_specs(dataset), variant_keys, "ablation"),
                seeds=ablation_seeds,
                base_model_config=base_model_config,
                base_train_config=base_train_config,
                eval_config=eval_config,
                experiment_group="ablation",
                retry_backoff_seconds=retry_backoff_seconds,
                max_total_attempts=max_total_attempts,
            )
        )
    if "sensitivity" in groups:
        specs = (
            _wtb_sensitivity_specs(base_model_config.num_experts)
            if dataset in {"wtb", "external_wind"}
            else _era5_sensitivity_specs(base_model_config.num_experts)
        )
        specs = _filter_variant_specs(specs, variant_keys, "sensitivity")
        results.extend(
            _run_spec_sequence(
                bundle=bundle,
                output_root=Path(output_root),
                dataset=dataset,
                specs=specs,
                seeds=sensitivity_seeds,
                base_model_config=base_model_config,
                base_train_config=base_train_config,
                eval_config=eval_config,
                experiment_group="sensitivity",
                retry_backoff_seconds=retry_backoff_seconds,
                max_total_attempts=max_total_attempts,
            )
        )

    save_json(Path(output_root) / "suite_summary.json", {"rows": results})
    return results


def run_paper_suite_parallel(
    cache_dir: Path | str,
    output_root: Path | str,
    dataset: str,
    seeds: list[int],
    base_model_config: ModelConfig,
    base_train_config: TrainConfig,
    eval_config: EvalConfig,
    groups: Iterable[str] | None = None,
    strong_baseline_seeds: list[int] | None = None,
    ablation_seeds: list[int] | None = None,
    sensitivity_seeds: list[int] | None = None,
    variant_keys: Iterable[str] | None = None,
    device_ids: list[int] | None = None,
    max_parallel: int | None = None,
    resume: bool = True,
    retry_backoff_seconds: float = 30.0,
    max_total_attempts: int = 3,
    shard_id: int = 0,
    num_shards: int = 1,
) -> list[dict[str, Any]]:
    output_root = ensure_dir(output_root)
    groups = list(groups or ["main"])
    strong_baseline_seeds = strong_baseline_seeds or seeds
    ablation_seeds = ablation_seeds or seeds
    sensitivity_seeds = sensitivity_seeds or ablation_seeds
    cache_dir = Path(cache_dir)

    if device_ids is None:
        device_ids = list(range(torch.cuda.device_count())) if torch.cuda.is_available() else []
    if max_parallel is None:
        max_parallel = len(device_ids) if device_ids else 1
    if max_parallel <= 1:
        bundle = load_cache_bundle(cache_dir)
        return run_paper_suite(
            bundle=bundle,
            output_root=output_root,
            dataset=dataset,
            seeds=seeds,
            base_model_config=base_model_config,
            base_train_config=base_train_config,
            eval_config=eval_config,
            groups=groups,
            strong_baseline_seeds=strong_baseline_seeds,
            ablation_seeds=ablation_seeds,
            sensitivity_seeds=sensitivity_seeds,
            variant_keys=variant_keys,
            retry_backoff_seconds=retry_backoff_seconds,
            max_total_attempts=max_total_attempts,
        )

    cpu_count = os.cpu_count() or 1
    cpu_threads = max(1, cpu_count // max_parallel)
    max_total_attempts = max(int(max_total_attempts), 1)
    num_shards = max(int(num_shards), 1)
    shard_id = int(shard_id) % num_shards
    specs_by_group: list[tuple[str, list[int], list[dict[str, Any]]]] = []
    if "main" in groups:
        main_specs = _filter_variant_specs(_main_variant_specs(dataset), variant_keys, "main")
        specs_by_group.append(("main", seeds, main_specs))
    if "strong_baselines" in groups:
        strong_specs = _filter_variant_specs(_strong_baseline_specs(dataset), variant_keys, "strong_baselines")
        specs_by_group.append(("strong_baselines", strong_baseline_seeds, strong_specs))
    if "ablation" in groups:
        ablation_specs = _filter_variant_specs(_ablation_variant_specs(dataset), variant_keys, "ablation")
        specs_by_group.append(("ablation", ablation_seeds, ablation_specs))
    if "sensitivity" in groups:
        sens_specs = (
            _wtb_sensitivity_specs(base_model_config.num_experts)
            if dataset in {"wtb", "external_wind"}
            else _era5_sensitivity_specs(base_model_config.num_experts)
        )
        sens_specs = _filter_variant_specs(sens_specs, variant_keys, "sensitivity")
        specs_by_group.append(("sensitivity", sensitivity_seeds, sens_specs))

    results: list[dict[str, Any]] = []
    job_index = 0
    for experiment_group, group_seeds, group_specs in specs_by_group:
        base_jobs: list[dict[str, Any]] = []
        for spec in group_specs:
            for seed in group_seeds:
                if job_index % num_shards != shard_id:
                    job_index += 1
                    continue
                job_index += 1
                run_name = f"{dataset}_{spec['key']}_seed{seed}"
                run_dir = Path(output_root) / run_name
                if resume and _run_is_complete(run_dir):
                    results.append(
                        {
                            "skipped": True,
                            "dataset": dataset,
                            "group": experiment_group,
                            "variant_key": spec["key"],
                            "label": spec.get("label", ""),
                            "seed": seed,
                            "run_name": run_name,
                            "run_dir": str(run_dir),
                            "attempt": 0,
                        }
                    )
                    continue
                base_jobs.append(
                    {
                        "cache_dir": str(cache_dir),
                        "output_root": str(output_root),
                        "dataset": dataset,
                        "spec": spec,
                        "seed": seed,
                        "experiment_group": experiment_group,
                        "base_model_config": base_model_config,
                        "base_train_config": base_train_config,
                        "eval_config": eval_config,
                        "resume": resume,
                        "run_name": run_name,
                        "run_dir": str(run_dir),
                    }
                )
        if not base_jobs:
            continue

        attempt_by_run: dict[str, int] = {}
        pending = list(base_jobs)
        round_index = 0
        while pending:
            round_index += 1
            next_pending: list[dict[str, Any]] = []
            runnable: list[dict[str, Any]] = []
            for job in pending:
                run_dir = Path(str(job["run_dir"]))
                if resume and _run_is_complete(run_dir):
                    results.append(
                        {
                            "skipped": True,
                            "dataset": dataset,
                            "group": str(job["experiment_group"]),
                            "variant_key": str(job["spec"]["key"]),
                            "label": str(job["spec"].get("label", "")),
                            "seed": int(job["seed"]),
                            "run_name": str(job["run_name"]),
                            "run_dir": str(run_dir),
                            "attempt": attempt_by_run.get(str(job["run_name"]), 0),
                        }
                    )
                    continue
                runnable.append(job)
            if not runnable:
                break

            worker_count = min(max_parallel, len(device_ids) if device_ids else max_parallel, len(runnable))
            if worker_count <= 0:
                worker_count = 1
            mp_context = mp.get_context("spawn")
            with ProcessPoolExecutor(max_workers=worker_count, mp_context=mp_context) as executor:
                futures: list[tuple[Any, dict[str, Any], int]] = []
                for index, job in enumerate(runnable):
                    run_name = str(job["run_name"])
                    attempt = attempt_by_run.get(run_name, 0) + 1
                    attempt_by_run[run_name] = attempt
                    if attempt > max_total_attempts:
                        results.append(
                            {
                                "skipped": False,
                                "failed": True,
                                "error": "max_total_attempts_exceeded",
                                "dataset": dataset,
                                "group": str(job["experiment_group"]),
                                "variant_key": str(job["spec"]["key"]),
                                "label": str(job["spec"].get("label", "")),
                                "seed": int(job["seed"]),
                                "run_name": run_name,
                                "run_dir": str(job["run_dir"]),
                                "attempt": attempt,
                            }
                        )
                        continue
                    device_id = device_ids[index % len(device_ids)] if device_ids else None
                    payload = {**job, "device_id": device_id, "cpu_threads": cpu_threads, "attempt": attempt}
                    futures.append((executor.submit(_paper_worker, payload), job, attempt))

                for future, job, attempt in futures:
                    try:
                        row = future.result()
                    except Exception as exc:
                        row = {
                            "skipped": False,
                            "failed": True,
                            "error": repr(exc),
                            "traceback": traceback.format_exc(),
                            "dataset": dataset,
                            "group": str(job["experiment_group"]),
                            "variant_key": str(job["spec"]["key"]),
                            "label": str(job["spec"].get("label", "")),
                            "seed": int(job["seed"]),
                            "run_name": str(job["run_name"]),
                            "run_dir": str(job["run_dir"]),
                            "attempt": attempt,
                        }
                    results.append(row)
                    should_retry = bool(row.get("failed")) or (row.get("skip_reason") == "locked")
                    if should_retry and attempt < max_total_attempts:
                        next_pending.append(job)

            if not next_pending:
                break
            sleep_seconds = float(retry_backoff_seconds) * (2.0 ** max(round_index - 1, 0))
            time.sleep(min(sleep_seconds, 300.0))
            pending = next_pending

    save_json(Path(output_root) / "suite_summary.json", {"rows": results})
    return results


def generate_robustness_figure(
    wtb_df: pd.DataFrame,
    wtb_sensitivity_df: pd.DataFrame | None,
    output_path: Path | str,
) -> Path:
    output_path = Path(output_path)
    ensure_dir(output_path.parent)
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))

    wtb_main = _select_group(wtb_df, "main")
    main_subset = _ordered_rows(wtb_main[wtb_main["model"].isin(WTB_MAIN_ORDER)].copy(), "model", WTB_MAIN_ORDER)
    if not main_subset.empty:
        summary = _summarize_metrics(main_subset, ["model"], ["overall_rmse", "switch_rmse", "pitch_control_rmse"])
        summary = _ordered_rows(summary, "model", WTB_MAIN_ORDER)
        metric_labels = ["overall_rmse", "switch_rmse", "pitch_control_rmse"]
        display_labels = ["Overall", "Switch", "Pitch-control"]
        x = np.arange(len(summary))
        width = 0.22
        colors = ["#2563eb", "#dc2626", "#059669"]
        for idx, metric in enumerate(metric_labels):
            means = summary[f"{metric}_mean"].to_numpy(dtype=float)
            stds = summary[f"{metric}_std"].to_numpy(dtype=float)
            axes[0].bar(x + (idx - 1) * width, means, width=width, color=colors[idx], label=display_labels[idx], alpha=0.85)
            axes[0].errorbar(
                x + (idx - 1) * width,
                means,
                yerr=stds,
                fmt="none",
                ecolor="#111827",
                elinewidth=1.2,
                capsize=3,
            )
        axes[0].set_xticks(x)
        axes[0].set_xticklabels(summary["model"], rotation=15, ha="right")
        axes[0].set_ylabel("RMSE")
        axes[0].set_title("WTB Main-Model Stability Across Seeds")
        axes[0].grid(True, axis="y", alpha=0.25)
        axes[0].legend(frameon=False)
    else:
        axes[0].text(0.5, 0.5, "Multi-seed WTB runs pending", ha="center", va="center", transform=axes[0].transAxes)
        axes[0].set_axis_off()

    if wtb_sensitivity_df is not None and not wtb_sensitivity_df.empty:
        threshold_df = wtb_sensitivity_df[wtb_sensitivity_df["setting_group"].isin(["rated_wind", "pitch_threshold"])].copy()
        if not threshold_df.empty:
            summary = _summarize_metrics(
                threshold_df,
                ["setting_group", "setting_value"],
                ["overall_rmse", "switch_rmse"],
            ).sort_values(["setting_group", "setting_value"])
            colors = {"rated_wind": "#7c3aed", "pitch_threshold": "#ea580c"}
            for setting_group, group in summary.groupby("setting_group", sort=False):
                axes[1].plot(
                    group["setting_value"].astype(float),
                    group["switch_rmse_mean"].astype(float),
                    marker="o",
                    linewidth=2.0,
                    label=f"{setting_group} (switch)",
                    color=colors.get(str(setting_group), "#2563eb"),
                )
            axes[1].set_title("WTB Threshold Sensitivity")
            axes[1].set_xlabel("Sensitivity setting value")
            axes[1].set_ylabel("Switch-window RMSE")
            axes[1].grid(True, alpha=0.25)
            axes[1].legend(frameon=False)
        else:
            axes[1].text(0.5, 0.5, "Threshold sweeps pending", ha="center", va="center", transform=axes[1].transAxes)
            axes[1].set_axis_off()
    else:
        axes[1].text(0.5, 0.5, "Threshold sweeps pending", ha="center", va="center", transform=axes[1].transAxes)
        axes[1].set_axis_off()

    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)
    return output_path


def _select_run_dir(df: pd.DataFrame, label: str) -> Path | None:
    subset = df[df["model"] == label]
    if subset.empty:
        return None
    if "experiment_group" in subset.columns:
        main_subset = subset[subset["experiment_group"] == "main"].copy()
        if not main_subset.empty:
            subset = main_subset
    return Path(str(subset.iloc[0]["run_dir"]))


def export_revised_paper_assets(
    wtb_bundle: CacheBundle,
    era5_bundle: CacheBundle,
    wtb_df: pd.DataFrame,
    era5_df: pd.DataFrame,
    output_dir: Path | str,
    hidden_dim: int = 64,
    wtb_num_experts: int = 4,
    era5_num_experts: int = 3,
    tau: float = 0.7,
    dropout: float = 0.1,
    wtb_sensitivity_df: pd.DataFrame | None = None,
) -> dict[str, Path]:
    wtb_display_df = _prepare_wtb_main_display_df(wtb_df)
    era5_df = append_era5_persistence_baseline(
        era5_df,
        era5_bundle,
        Path(output_dir) / "tables",
    )
    output_dir = ensure_dir(output_dir)
    scratch_dir = output_dir / "_scratch_sensitivity"
    if scratch_dir.exists() and scratch_dir.is_dir():
        shutil.rmtree(scratch_dir)
    table_dir = ensure_dir(output_dir / "tables")
    era5_df = append_era5_persistence_baseline(era5_df, era5_bundle, table_dir)
    figure_dir = ensure_dir(Path(output_dir) / "figures")
    tex_dir = ensure_dir(Path(output_dir) / "generated")
    for stale_name in [
        "figure2_wtb_gate_vs_wspd_pab.png",
        "figure3_era5_flux_vs_gate.png",
        "figure4_wtb_switch_window.png",
        "figure5_wtb_confusion.png",
        "figure6_robustness.png",
        "figure2_data_boundary.pdf",
        "figure2_data_boundary.svg",
        "figure2_data_boundary.png",
        "figure3_summary_results.pdf",
        "figure3_summary_results.svg",
        "figure3_summary_results.png",
        "figure4_routing_evidence.pdf",
        "figure4_routing_evidence.svg",
        "figure4_routing_evidence.png",
        "figure5_case_studies.pdf",
        "figure5_case_studies.svg",
        "figure5_case_studies.png",
        "figure6_ablation_tradeoff.pdf",
        "figure6_ablation_tradeoff.svg",
        "figure6_ablation_tradeoff.png",
    ]:
        stale_path = figure_dir / stale_name
        if stale_path.exists():
            stale_path.unlink()
    exported: dict[str, Path] = {}

    generate_architecture_figure(figure_dir)
    exported["table_variants"] = build_variant_table(
        wtb_bundle,
        era5_bundle,
        hidden_dim=hidden_dim,
        wtb_num_experts=wtb_num_experts,
        era5_num_experts=era5_num_experts,
        tau=tau,
        dropout=dropout,
        output_path=table_dir / "table_variants.csv",
    )
    exported["table_main_benchmark"] = build_main_benchmark_table(wtb_display_df, era5_df, table_dir / "table_main_benchmark.csv")
    exported["table_regime_wise"] = build_regime_wise_table(wtb_display_df, era5_df, table_dir / "table_regime_wise.csv")
    exported["table_routing_quality"] = build_routing_quality_table(wtb_display_df, era5_df, table_dir / "table_routing_quality.csv")
    exported["table_wtb_ablation"] = build_wtb_ablation_table(wtb_df, table_dir / "table_wtb_ablation.csv")
    exported["table_robustness"] = build_robustness_table(
        wtb_df,
        era5_df,
        wtb_sensitivity_df=wtb_sensitivity_df,
        output_path=table_dir / "table_robustness.csv",
    )
    exported["tex_table_main_benchmark"] = build_main_benchmark_tex(wtb_display_df, era5_df, tex_dir / "table_3_main_performance.tex")
    exported["tex_table_regime_wise"] = build_regime_wise_tex(wtb_display_df, era5_df, tex_dir / "table_4_regime_slices.tex")
    exported["tex_table_routing_quality"] = build_routing_quality_tex(wtb_display_df, era5_df, tex_dir / "table_5_routing.tex")
    exported["tex_table_wtb_ablation"] = build_wtb_ablation_tex(wtb_df, tex_dir / "table_6_wtb_ablation.tex")
    exported["tex_table_robustness"] = build_robustness_tex(
        wtb_df,
        era5_df,
        wtb_sensitivity_df=wtb_sensitivity_df,
        output_path=tex_dir / "table_7_robustness.tex",
    )

    exported["figure2_data_boundary"] = build_manuscript_figure2_data_boundary(
        wtb_bundle,
        era5_bundle,
        figure_dir / "figure2_data_boundary",
    )
    exported["figure3_summary_results"] = build_manuscript_figure3_summary_results(
        wtb_display_df,
        era5_df,
        figure_dir / "figure3_summary_results",
    )
    exported["figure6_ablation_tradeoff"] = build_manuscript_figure6_ablation_tradeoff(
        pd.read_csv(exported["table_wtb_ablation"]),
        figure_dir / "figure6_ablation_tradeoff",
    )
    wtb_corrected_run = _select_run_dir(wtb_display_df, WTB_CORRECTED_DISPLAY_MODEL)
    wtb_naive_run = _select_run_dir(wtb_df, "Unconstrained MoE")
    wtb_dense_run = _select_run_dir(wtb_df, "Capacity-Matched Dense Diffusion-GRU")
    era5_full_run = _select_run_dir(era5_df, "Physics-Aligned MoE")
    if wtb_corrected_run is not None and wtb_naive_run is not None:
        exported["figure4_routing_evidence"] = build_manuscript_figure4_routing_evidence(
            wtb_bundle,
            corrected_run_dir=wtb_corrected_run,
            unconstrained_run_dir=wtb_naive_run,
            output_base=figure_dir / "figure4_routing_evidence",
        )
    if (
        wtb_dense_run is not None
        and wtb_naive_run is not None
        and wtb_corrected_run is not None
        and era5_full_run is not None
    ):
        exported["figure5_case_studies"] = build_manuscript_figure5_case_studies(
            wtb_bundle=wtb_bundle,
            dense_run_dir=wtb_dense_run,
            unconstrained_run_dir=wtb_naive_run,
            corrected_run_dir=wtb_corrected_run,
            era5_bundle=era5_bundle,
            era5_corrected_run_dir=era5_full_run,
            output_base=figure_dir / "figure5_case_studies",
        )
    _sanitize_paper_asset_freeze_tokens(output_dir)
    return exported


def _sanitize_paper_asset_freeze_tokens(output_dir: Path) -> None:
    for path in output_dir.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in PAPER_ASSET_FREEZE_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        updated = text
        for stale, replacement in PAPER_ASSET_FREEZE_TOKEN_REPLACEMENTS.items():
            updated = updated.replace(stale, replacement)
        if updated != text:
            path.write_text(updated, encoding="utf-8")
