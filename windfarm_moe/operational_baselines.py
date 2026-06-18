from __future__ import annotations

from pathlib import Path
from typing import Any
import time

import numpy as np
import pandas as pd

from .data import CacheBundle, load_cache_bundle
from .evaluate import _masked_numpy_metrics
from .utils import ensure_dir, save_json


DEFAULT_BASELINES = ("persistence", "power_curve", "xgboost_lag", "lightgbm_lag", "dlinear")
MODEL_NAMES = {
    "persistence": "Persistence",
    "power_curve": "Physical power curve",
    "xgboost_lag": "XGBoost lag-feature",
    "lightgbm_lag": "LightGBM lag-feature",
    "dlinear": "DLinear-style LTSF",
}


def run_operational_baselines(
    *,
    cache_dir: Path | str,
    output_dir: Path | str,
    baselines: str | list[str] | tuple[str, ...] | None = None,
    max_train_samples: int = 120_000,
    max_dlinear_samples: int = 80_000,
    random_seed: int = 42,
    tree_estimators: int = 80,
    split: str = "test",
) -> Path:
    bundle = load_cache_bundle(cache_dir, mmap_mode="r")
    if bundle.metadata.get("dataset") != "wtb":
        raise ValueError("operational-baselines currently supports the WTB cache.")
    selected = _parse_baselines(baselines)
    out_dir = ensure_dir(output_dir)
    target, mask, regime, regime_valid, aux, aux_valid, anchors, anchor_physics = _future_arrays(bundle, split)
    rows: list[dict[str, Any]] = []

    for key in selected:
        start = time.perf_counter()
        run_dir = ensure_dir(out_dir / key)
        if key == "persistence":
            pred = _persistence_prediction(bundle, anchors)
            fit_summary = {"fit": "none"}
        elif key == "power_curve":
            pred, fit_summary = _power_curve_prediction(bundle, anchors)
        elif key in {"xgboost_lag", "lightgbm_lag"}:
            pred, fit_summary = _tree_lag_prediction(
                bundle,
                anchors,
                model_key=key,
                max_train_samples=max_train_samples,
                random_seed=random_seed,
                n_estimators=tree_estimators,
            )
        elif key == "dlinear":
            pred, fit_summary = _dlinear_prediction(
                bundle,
                anchors,
                max_train_samples=max_dlinear_samples,
                random_seed=random_seed,
            )
        else:
            raise ValueError(f"Unsupported operational baseline: {key}")

        eval_seconds = time.perf_counter() - start
        metrics = _metrics_for_prediction(bundle, pred, target, mask, regime, eval_seconds=eval_seconds)
        _write_eval_artifacts(
            run_dir,
            pred=pred,
            target=target,
            mask=mask,
            regime=regime,
            regime_valid=regime_valid,
            regime_aux=aux,
            regime_aux_valid=aux_valid,
            anchor_index=anchors,
            anchor_physics=anchor_physics,
            metrics=metrics,
        )
        row = _summary_row(bundle, key, run_dir, metrics, fit_summary, split)
        rows.append(row)

    summary = pd.DataFrame(rows)
    summary.to_csv(out_dir / "wtb_operational_baselines.csv", index=False)
    _write_latex_table(summary, out_dir / "table_wtb_operational_baselines.tex")
    save_json(
        out_dir / "operational_baseline_config.json",
        {
            "cache_dir": str(cache_dir),
            "split": split,
            "baselines": selected,
            "max_train_samples": int(max_train_samples),
            "max_dlinear_samples": int(max_dlinear_samples),
            "random_seed": int(random_seed),
            "tree_estimators": int(tree_estimators),
        },
    )
    return out_dir


def _parse_baselines(values: str | list[str] | tuple[str, ...] | None) -> list[str]:
    if values is None:
        return list(DEFAULT_BASELINES)
    if isinstance(values, str):
        parsed = [token.strip() for token in values.split(",") if token.strip()]
    else:
        parsed = [str(value).strip() for value in values if str(value).strip()]
    unknown = sorted(set(parsed).difference(DEFAULT_BASELINES))
    if unknown:
        raise ValueError(f"Unsupported operational baseline(s): {unknown}. Available: {list(DEFAULT_BASELINES)}")
    return parsed


def _split_anchors(bundle: CacheBundle, split: str) -> np.ndarray:
    hist_len = int(bundle.metadata["hist_len"])
    pred_len = int(bundle.metadata["pred_len"])
    start, end = bundle.metadata["split_bounds"][split]
    anchor_start = int(start) + hist_len - 1
    anchor_end = int(end) - pred_len - 1
    if anchor_end < anchor_start:
        return np.empty((0,), dtype=np.int64)
    return np.arange(anchor_start, anchor_end + 1, dtype=np.int64)


def _future_arrays(
    bundle: CacheBundle,
    split: str,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    anchors = _split_anchors(bundle, split)
    pred_len = int(bundle.metadata["pred_len"])
    if anchors.size == 0:
        raise ValueError(f"Split {split!r} is too short for operational baseline evaluation.")
    target = np.stack([np.asarray(bundle.target[a + 1 : a + 1 + pred_len], dtype=np.float32) for a in anchors], axis=0)
    mask = np.stack([np.asarray(bundle.target_mask[a + 1 : a + 1 + pred_len], dtype=np.float32) for a in anchors], axis=0)
    regime = np.asarray(bundle.regime_primary[anchors], dtype=np.int16)
    regime_valid = np.asarray(bundle.regime_primary_valid[anchors], dtype=np.float32)
    if bundle.regime_aux is None:
        aux = np.full_like(regime, -1, dtype=np.int16)
        aux_valid = np.zeros_like(regime, dtype=np.float32)
    else:
        aux = np.asarray(bundle.regime_aux[anchors], dtype=np.int16)
        aux_valid = (
            np.asarray(bundle.regime_aux_valid[anchors], dtype=np.float32)
            if bundle.regime_aux_valid is not None
            else np.zeros_like(regime, dtype=np.float32)
        )
    anchor_physics = np.asarray(bundle.physics[anchors], dtype=np.float32)
    return target, mask, regime, regime_valid, aux, aux_valid, anchors, anchor_physics


def _persistence_prediction(bundle: CacheBundle, anchors: np.ndarray) -> np.ndarray:
    pred_len = int(bundle.metadata["pred_len"])
    last = np.asarray(bundle.target[anchors], dtype=np.float32)
    return np.repeat(last[:, None, :], pred_len, axis=1)


def _feature_index(bundle: CacheBundle, name: str) -> int | None:
    names = [str(value) for value in bundle.metadata.get("feature_names", [])]
    try:
        return names.index(name)
    except ValueError:
        return None


def _physics_index(bundle: CacheBundle, name: str) -> int | None:
    names = [str(value) for value in bundle.metadata.get("physics_names", [])]
    try:
        return names.index(name)
    except ValueError:
        return None


def _power_curve_prediction(bundle: CacheBundle, anchors: np.ndarray) -> tuple[np.ndarray, dict[str, Any]]:
    train_start, train_end = bundle.metadata["split_bounds"]["train"]
    wspd_idx = _physics_index(bundle, "Wspd")
    if wspd_idx is None:
        wspd_idx = 0
    train_wind = np.asarray(bundle.physics[int(train_start) : int(train_end), :, wspd_idx], dtype=np.float64)
    train_power = np.asarray(bundle.target[int(train_start) : int(train_end)], dtype=np.float64)
    train_mask = np.asarray(bundle.target_mask[int(train_start) : int(train_end)], dtype=bool)
    rated_power = float(np.nanquantile(train_power[train_mask], 0.995)) if train_mask.any() else 1.0
    bin_edges = np.linspace(0.0, 30.0, 61)
    global_curve = _fit_binned_curve(train_wind, train_power, train_mask, bin_edges, rated_power)
    node_curves = []
    for node in range(train_power.shape[1]):
        curve = _fit_binned_curve(train_wind[:, node], train_power[:, node], train_mask[:, node], bin_edges, rated_power)
        node_curves.append(curve)
    node_curves_arr = np.stack(node_curves, axis=0)

    anchor_wind = np.asarray(bundle.physics[anchors, :, wspd_idx], dtype=np.float64)
    bin_ids = _curve_bin_ids(anchor_wind, bin_edges)
    node_idx = np.arange(anchor_wind.shape[1])
    pred_anchor = node_curves_arr[node_idx[None, :], bin_ids]
    missing = ~np.isfinite(pred_anchor)
    if missing.any():
        pred_anchor[missing] = global_curve[bin_ids[missing]]
    pred_anchor = np.nan_to_num(pred_anchor, nan=0.0, posinf=rated_power, neginf=0.0)
    pred_anchor = np.clip(pred_anchor, 0.0, rated_power).astype(np.float32)
    pred = np.repeat(pred_anchor[:, None, :], int(bundle.metadata["pred_len"]), axis=1)
    return pred, {"rated_power_proxy": rated_power, "wind_bins": len(bin_edges) - 1}


def _fit_binned_curve(
    wind: np.ndarray,
    power: np.ndarray,
    mask: np.ndarray,
    bin_edges: np.ndarray,
    fallback: float,
) -> np.ndarray:
    wind_flat = np.asarray(wind, dtype=np.float64).reshape(-1)
    power_flat = np.asarray(power, dtype=np.float64).reshape(-1)
    mask_flat = np.asarray(mask, dtype=bool).reshape(-1) & np.isfinite(wind_flat) & np.isfinite(power_flat)
    bins = _curve_bin_ids(wind_flat[mask_flat], bin_edges)
    curve = np.full(len(bin_edges) - 1, np.nan, dtype=np.float64)
    for bin_id in range(curve.size):
        values = power_flat[mask_flat][bins == bin_id]
        if values.size >= 20:
            curve[bin_id] = float(np.nanmedian(values))
    if np.isnan(curve).all():
        return np.full(curve.size, fallback, dtype=np.float64)
    series = pd.Series(curve).interpolate(limit_direction="both").fillna(float(np.nanmedian(power_flat[mask_flat])) if mask_flat.any() else fallback)
    return series.to_numpy(dtype=np.float64)


def _curve_bin_ids(wind: np.ndarray, bin_edges: np.ndarray) -> np.ndarray:
    return np.clip(np.digitize(np.asarray(wind, dtype=np.float64), bin_edges) - 1, 0, len(bin_edges) - 2)


def _tree_lag_prediction(
    bundle: CacheBundle,
    anchors: np.ndarray,
    *,
    model_key: str,
    max_train_samples: int,
    random_seed: int,
    n_estimators: int,
) -> tuple[np.ndarray, dict[str, Any]]:
    if model_key == "xgboost_lag":
        from xgboost import XGBRegressor

        model = XGBRegressor(
            n_estimators=int(n_estimators),
            max_depth=4,
            learning_rate=0.05,
            subsample=0.9,
            colsample_bytree=0.9,
            objective="reg:squarederror",
            tree_method="hist",
            random_state=int(random_seed),
            n_jobs=2,
        )
    elif model_key == "lightgbm_lag":
        from lightgbm import LGBMRegressor

        model = LGBMRegressor(
            n_estimators=int(n_estimators),
            learning_rate=0.05,
            num_leaves=31,
            subsample=0.9,
            colsample_bytree=0.9,
            random_state=int(random_seed),
            n_jobs=2,
            verbosity=-1,
        )
    else:
        raise ValueError(model_key)

    x_train, y_train = _sample_lag_training_rows(bundle, max_train_samples, random_seed)
    model.fit(x_train, y_train)
    pred = _predict_lag_model(bundle, anchors, model)
    return pred, {"train_samples": int(x_train.shape[0]), "n_estimators": int(n_estimators)}


def _sample_lag_training_rows(bundle: CacheBundle, max_samples: int, random_seed: int) -> tuple[np.ndarray, np.ndarray]:
    anchors = _split_anchors(bundle, "train")
    pred_len = int(bundle.metadata["pred_len"])
    num_nodes = int(bundle.target.shape[1])
    total = int(anchors.size * num_nodes * pred_len)
    rng = np.random.default_rng(random_seed)
    take = min(int(max_samples), total)
    flat = rng.choice(total, size=take, replace=False) if take < total else np.arange(total)
    anchor_pos = flat // (num_nodes * pred_len)
    rem = flat % (num_nodes * pred_len)
    node = rem // pred_len
    horizon = rem % pred_len + 1
    anchor = anchors[anchor_pos]
    x = _lag_features(bundle, anchor, node, horizon)
    y = np.asarray(bundle.target[anchor + horizon, node], dtype=np.float32)
    valid = np.asarray(bundle.target_mask[anchor + horizon, node], dtype=bool) & np.isfinite(y)
    return x[valid], y[valid]


def _lag_features(bundle: CacheBundle, anchor: np.ndarray, node: np.ndarray, horizon: np.ndarray) -> np.ndarray:
    anchor = np.asarray(anchor, dtype=np.int64)
    node = np.asarray(node, dtype=np.int64)
    horizon = np.asarray(horizon, dtype=np.float32)
    target = np.asarray(bundle.target)
    last = np.asarray(target[anchor, node], dtype=np.float32)
    lag1 = np.asarray(target[np.maximum(anchor - 1, 0), node], dtype=np.float32)
    lag6 = np.asarray(target[np.maximum(anchor - 6, 0), node], dtype=np.float32)
    lag18 = np.asarray(target[np.maximum(anchor - 18, 0), node], dtype=np.float32)
    lag36 = np.asarray(target[np.maximum(anchor - 36, 0), node], dtype=np.float32)
    wspd_idx = _feature_index(bundle, "Wspd")
    pitch_idx = _feature_index(bundle, "Pab_mean")
    prtv_idx = _feature_index(bundle, "Prtv")
    wind = _feature_at(bundle, anchor, node, wspd_idx)
    pitch = _feature_at(bundle, anchor, node, pitch_idx)
    prtv = _feature_at(bundle, anchor, node, prtv_idx)
    regime = np.asarray(bundle.regime_primary[anchor, node], dtype=np.float32)
    node_norm = node.astype(np.float32) / max(float(bundle.target.shape[1] - 1), 1.0)
    pred_len = float(bundle.metadata["pred_len"])
    features = np.stack(
        [
            horizon / pred_len,
            node_norm,
            last,
            lag1,
            lag6,
            lag18,
            lag36,
            last - lag6,
            wind,
            pitch,
            prtv,
            regime,
        ],
        axis=1,
    )
    return np.nan_to_num(features.astype(np.float32), nan=0.0, posinf=0.0, neginf=0.0)


def _feature_at(bundle: CacheBundle, anchor: np.ndarray, node: np.ndarray, index: int | None) -> np.ndarray:
    if index is None:
        return np.zeros(anchor.shape[0], dtype=np.float32)
    return np.asarray(bundle.features[anchor, node, index], dtype=np.float32)


def _predict_lag_model(bundle: CacheBundle, anchors: np.ndarray, model: Any, chunk_anchors: int = 128) -> np.ndarray:
    pred_len = int(bundle.metadata["pred_len"])
    num_nodes = int(bundle.target.shape[1])
    pred = np.empty((anchors.size, pred_len, num_nodes), dtype=np.float32)
    nodes = np.arange(num_nodes, dtype=np.int64)
    horizons = np.arange(1, pred_len + 1, dtype=np.int64)
    for start in range(0, anchors.size, chunk_anchors):
        chunk = anchors[start : start + chunk_anchors]
        anchor_flat = np.repeat(chunk, num_nodes * pred_len)
        node_flat = np.tile(np.repeat(nodes, pred_len), chunk.size)
        horizon_flat = np.tile(horizons, chunk.size * num_nodes)
        x = _lag_features(bundle, anchor_flat, node_flat, horizon_flat)
        y_hat = np.asarray(model.predict(x), dtype=np.float32)
        pred[start : start + chunk.size] = y_hat.reshape(chunk.size, num_nodes, pred_len).transpose(0, 2, 1)
    return np.clip(np.nan_to_num(pred, nan=0.0), 0.0, None)


def _dlinear_prediction(
    bundle: CacheBundle,
    anchors: np.ndarray,
    *,
    max_train_samples: int,
    random_seed: int,
) -> tuple[np.ndarray, dict[str, Any]]:
    from sklearn.linear_model import Ridge
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    x_train, y_train = _sample_dlinear_rows(bundle, max_train_samples, random_seed)
    model = make_pipeline(StandardScaler(), Ridge(alpha=1.0))
    model.fit(x_train, y_train)
    pred = _predict_dlinear(bundle, anchors, model)
    return pred, {"train_samples": int(x_train.shape[0]), "alpha": 1.0}


def _sample_dlinear_rows(bundle: CacheBundle, max_samples: int, random_seed: int) -> tuple[np.ndarray, np.ndarray]:
    anchors = _split_anchors(bundle, "train")
    pred_len = int(bundle.metadata["pred_len"])
    num_nodes = int(bundle.target.shape[1])
    total = int(anchors.size * num_nodes)
    rng = np.random.default_rng(random_seed)
    take = min(int(max_samples), total)
    flat = rng.choice(total, size=take, replace=False) if take < total else np.arange(total)
    anchor = anchors[flat // num_nodes]
    node = flat % num_nodes
    x = _dlinear_features(bundle, anchor, node)
    y = np.stack([np.asarray(bundle.target[a + 1 : a + 1 + pred_len, n], dtype=np.float32) for a, n in zip(anchor, node)], axis=0)
    m = np.stack(
        [np.asarray(bundle.target_mask[a + 1 : a + 1 + pred_len, n], dtype=bool) for a, n in zip(anchor, node)],
        axis=0,
    )
    valid = m.all(axis=1) & np.isfinite(y).all(axis=1)
    return x[valid], y[valid]


def _dlinear_features(bundle: CacheBundle, anchor: np.ndarray, node: np.ndarray) -> np.ndarray:
    hist_len = int(bundle.metadata["hist_len"])
    anchor = np.asarray(anchor, dtype=np.int64)
    node = np.asarray(node, dtype=np.int64)
    histories = np.stack(
        [np.asarray(bundle.target[a - hist_len + 1 : a + 1, n], dtype=np.float32) for a, n in zip(anchor, node)],
        axis=0,
    )
    histories = np.nan_to_num(histories, nan=0.0)
    kernel = min(6, hist_len)
    cumsum = np.cumsum(np.pad(histories, ((0, 0), (1, 0)), mode="edge"), axis=1)
    trend_core = (cumsum[:, kernel:] - cumsum[:, :-kernel]) / float(kernel)
    pad = np.repeat(trend_core[:, :1], hist_len - trend_core.shape[1], axis=1)
    trend = np.concatenate([pad, trend_core], axis=1)
    residual = histories - trend
    node_norm = (node.astype(np.float32) / max(float(bundle.target.shape[1] - 1), 1.0))[:, None]
    return np.concatenate([trend, residual, node_norm], axis=1).astype(np.float32)


def _predict_dlinear(bundle: CacheBundle, anchors: np.ndarray, model: Any, chunk_rows: int = 40_000) -> np.ndarray:
    pred_len = int(bundle.metadata["pred_len"])
    num_nodes = int(bundle.target.shape[1])
    total = anchors.size * num_nodes
    pred_flat = np.empty((total, pred_len), dtype=np.float32)
    all_anchor = np.repeat(anchors, num_nodes)
    all_node = np.tile(np.arange(num_nodes, dtype=np.int64), anchors.size)
    for start in range(0, total, chunk_rows):
        end = min(start + chunk_rows, total)
        x = _dlinear_features(bundle, all_anchor[start:end], all_node[start:end])
        pred_flat[start:end] = np.asarray(model.predict(x), dtype=np.float32)
    return np.clip(pred_flat.reshape(anchors.size, num_nodes, pred_len).transpose(0, 2, 1), 0.0, None)


def _metrics_for_prediction(
    bundle: CacheBundle,
    pred: np.ndarray,
    target: np.ndarray,
    mask: np.ndarray,
    regime: np.ndarray,
    *,
    eval_seconds: float,
) -> dict[str, Any]:
    metrics: dict[str, Any] = {
        "overall": _masked_numpy_metrics(pred, target, mask),
        "efficiency": {
            "eval_seconds": float(eval_seconds),
            "num_windows": int(pred.shape[0]),
            "num_batches": 0,
            "windows_per_second": float(pred.shape[0] / eval_seconds) if eval_seconds > 0.0 else float("nan"),
        },
        "by_regime": {},
    }
    names = list(bundle.metadata["primary_regime_names"])
    for regime_id, name in enumerate(names):
        selector = regime == regime_id
        metrics["by_regime"][name] = _masked_numpy_metrics(pred, target, mask * selector[:, None, :])
    switch_selector = _switch_selector(regime, int(bundle.metadata.get("steps_per_hour", 6)))
    metrics["switch_window"] = _masked_numpy_metrics(pred, target, mask * switch_selector[:, None, :])
    return metrics


def _switch_selector(regime: np.ndarray, steps_per_hour: int) -> np.ndarray:
    switch_window = 3 * int(steps_per_hour)
    selector = np.zeros_like(regime, dtype=bool)
    if regime.shape[0] > 1:
        changes = regime[1:] != regime[:-1]
        rows, nodes = np.where(changes)
        for row, node in zip(rows, nodes):
            lo = max(0, row + 1 - switch_window)
            hi = min(regime.shape[0], row + 2 + switch_window)
            selector[lo:hi, node] = True
    return selector


def _write_eval_artifacts(
    output_dir: Path,
    *,
    pred: np.ndarray,
    target: np.ndarray,
    mask: np.ndarray,
    regime: np.ndarray,
    regime_valid: np.ndarray,
    regime_aux: np.ndarray,
    regime_aux_valid: np.ndarray,
    anchor_index: np.ndarray,
    anchor_physics: np.ndarray,
    metrics: dict[str, Any],
) -> None:
    save_json(output_dir / "metrics.json", metrics)
    rows = [{"slice": "overall", **metrics["overall"]}, {"slice": "switch_window", **metrics["switch_window"]}]
    for name, values in metrics["by_regime"].items():
        rows.append({"slice": f"regime::{name}", **values})
    pd.DataFrame(rows).to_csv(output_dir / "regime_wise_metrics.csv", index=False)
    np.save(output_dir / "pred.npy", pred.astype(np.float32))
    np.save(output_dir / "target.npy", target.astype(np.float32))
    np.save(output_dir / "mask.npy", mask.astype(np.float32))
    np.save(output_dir / "regime_primary.npy", regime.astype(np.int16))
    np.save(output_dir / "regime_primary_valid.npy", regime_valid.astype(np.float32))
    np.save(output_dir / "regime_aux.npy", regime_aux.astype(np.int16))
    np.save(output_dir / "regime_aux_valid.npy", regime_aux_valid.astype(np.float32))
    np.save(output_dir / "anchor_index.npy", anchor_index.astype(np.int64))
    np.save(output_dir / "anchor_physics.npy", anchor_physics.astype(np.float32))
    save_json(output_dir / "training_summary.json", {"best_epoch": 0, "best_val_rmse": None, "test_summary": metrics})


def _summary_row(
    bundle: CacheBundle,
    key: str,
    run_dir: Path,
    metrics: dict[str, Any],
    fit_summary: dict[str, Any],
    split: str,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "dataset": "wtb",
        "model": MODEL_NAMES[key],
        "run_dir": str(run_dir),
        "seed": "",
        "variant_key": key,
        "experiment_group": "operational_baseline",
        "setting_label": "engineering baseline",
        "model_mode": key,
        "parameter_count": 0,
        "split": split,
        "overall_mae": metrics["overall"]["mae"],
        "overall_rmse": metrics["overall"]["rmse"],
        "switch_mae": metrics["switch_window"]["mae"],
        "switch_rmse": metrics["switch_window"]["rmse"],
        **{f"fit_{name}": value for name, value in fit_summary.items()},
    }
    for regime_name, values in metrics["by_regime"].items():
        row[f"{regime_name}_mae"] = values["mae"]
        row[f"{regime_name}_rmse"] = values["rmse"]
    return row


def _write_latex_table(summary: pd.DataFrame, output_path: Path) -> None:
    lines = [
        r"\begin{table}[t]",
        r"\centering",
        r"\footnotesize",
        r"\setlength{\tabcolsep}{5pt}",
        r"\renewcommand{\arraystretch}{1.08}",
        r"\caption*{\textbf{Table.} WTB engineering forecasting baselines evaluated on the strict cache.}",
        r"\begin{tabular}{lrrr}",
        r"\toprule",
        r"Baseline & Overall RMSE & Switch RMSE & Pitch-control RMSE \\",
        r"\midrule",
    ]
    for _, row in summary.iterrows():
        name = str(row["model"]).replace("_", r"\_")
        lines.append(
            f"{name} & {float(row['overall_rmse']):.2f} & {float(row['switch_rmse']):.2f} & {float(row.get('pitch_control_rmse', np.nan)):.2f} \\\\"
        )
    lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}", ""])
    output_path.write_text("\n".join(lines), encoding="utf-8")
