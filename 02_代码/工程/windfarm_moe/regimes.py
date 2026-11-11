from __future__ import annotations

import numpy as np


WTB_PRIMARY_NAMES = ("idle", "mppt", "pitch_control", "transition")
WTB_AUX_NAMES = ("non_wake", "wake")
ERA5_PRIMARY_NAMES = ("convective", "stable", "transition")


def compute_wtb_operation_regime(
    wspd: np.ndarray,
    pab_avg: np.ndarray,
    cut_in_wind: float = 3.0,
    rated_wind: float = 10.5,
    pitch_threshold: float = 2.0,
) -> tuple[np.ndarray, np.ndarray]:
    regime = np.full(wspd.shape, 3, dtype=np.int16)
    regime[wspd < cut_in_wind] = 0
    regime[(wspd >= cut_in_wind) & (wspd <= rated_wind) & (pab_avg < pitch_threshold)] = 1
    regime[(wspd > rated_wind) & (pab_avg >= pitch_threshold)] = 2
    valid = regime != 3
    return regime, valid.astype(np.float32)


def compute_wtb_wake_flag(
    wake_score: np.ndarray,
    op_regime: np.ndarray,
    train_stop: int,
    quantile: float = 0.75,
) -> tuple[np.ndarray, np.ndarray, float]:
    valid = np.isin(op_regime, [1, 2])
    train_wake = wake_score[:train_stop][valid[:train_stop]]
    threshold = float(np.quantile(train_wake, quantile)) if train_wake.size else 0.0
    wake_flag = np.zeros_like(op_regime, dtype=np.int16)
    wake_flag[(wake_score >= threshold) & valid] = 1
    return wake_flag, valid.astype(np.float32), threshold


def compute_era5_regime_from_sshf(
    sshf: np.ndarray,
    train_stop: int,
    eps_quantile: float = 0.10,
    shock_quantile: float = 0.95,
) -> tuple[np.ndarray, dict[str, float]]:
    safe = np.nan_to_num(sshf.astype(np.float32), nan=0.0)
    diff = np.zeros_like(safe, dtype=np.float32)
    diff[1:] = safe[1:] - safe[:-1]

    train_abs = np.abs(safe[:train_stop]).reshape(-1)
    train_diff = np.abs(diff[:train_stop]).reshape(-1)
    eps = float(np.quantile(train_abs, eps_quantile)) if train_abs.size else 0.0
    shock_q95 = float(np.quantile(train_diff, shock_quantile)) if train_diff.size else 0.0

    regime = np.full(safe.shape, 2, dtype=np.int16)
    convective = (safe > eps) & (np.abs(diff) <= shock_q95)
    stable = (safe < -eps) & (np.abs(diff) <= shock_q95)
    regime[convective] = 0
    regime[stable] = 1
    return regime, {
        "eps": eps,
        "shock_q95": shock_q95,
        "eps_quantile": float(eps_quantile),
        "shock_quantile": float(shock_quantile),
    }


def compute_era5_regime_from_t2m_gradient(
    t2m: np.ndarray,
    train_stop: int,
    eps_quantile: float = 0.10,
    shock_quantile: float = 0.95,
) -> tuple[np.ndarray, dict[str, float]]:
    safe = np.nan_to_num(t2m.astype(np.float32), nan=0.0)
    grad = np.zeros_like(safe, dtype=np.float32)
    grad[1:] = safe[1:] - safe[:-1]
    train_abs = np.abs(grad[:train_stop]).reshape(-1)
    eps = float(np.quantile(train_abs, eps_quantile)) if train_abs.size else 0.0
    shock_q95 = float(np.quantile(train_abs, shock_quantile)) if train_abs.size else 0.0
    regime = np.full(safe.shape, 2, dtype=np.int16)
    convective = (grad > eps) & (np.abs(grad) <= shock_q95)
    stable = (grad < -eps) & (np.abs(grad) <= shock_q95)
    regime[convective] = 0
    regime[stable] = 1
    return regime, {
        "eps": eps,
        "shock_q95": shock_q95,
        "eps_quantile": float(eps_quantile),
        "shock_quantile": float(shock_quantile),
    }


def inverse_frequency_weights_from_labels(
    labels: np.ndarray,
    valid_mask: np.ndarray,
    num_classes: int,
) -> list[float]:
    valid = valid_mask.astype(bool)
    if valid.any():
        counts = np.bincount(labels[valid].reshape(-1), minlength=num_classes).astype(np.float64)
    else:
        counts = np.ones((num_classes,), dtype=np.float64)
    counts = np.where(counts > 0, counts, 1.0)
    weights = counts.sum() / (num_classes * counts)
    weights = weights / weights.mean()
    return weights.astype(np.float32).tolist()
