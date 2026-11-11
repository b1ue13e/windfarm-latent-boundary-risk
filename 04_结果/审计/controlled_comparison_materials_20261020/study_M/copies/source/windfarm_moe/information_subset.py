"""Finite information lattice and a direct pinball neural comparator.

All choices are development choices; this module does not certify sufficiency.
"""
from __future__ import annotations

from itertools import combinations
import numpy as np


def subset_grid() -> dict[str, tuple[tuple[int, ...], int]]:
    result = {"Common": ((), 0)}
    for size in (1, 2, 3):
        for channels in combinations(range(3), size):
            for lookback in (1, 6, 36):
                result["".join("WPQ"[c] for c in channels) + str(lookback)] = (channels, lookback)
    return result


def telemetry_columns(channels: tuple[int, ...], lookback: int, delay: int,
                      pitch_available: bool) -> np.ndarray:
    """Columns in common4 + W36 + P36 + Q36 + pitch36, oldest first.

    Lookback counts last-arrived observations, truncated at issue minus 35;
    no condition obtains observations outside the common event-time window.
    """
    if delay not in range(36) or lookback not in (0, 1, 6, 36):
        raise ValueError("Unsupported delay or lookback")
    if len(set(channels)) != len(channels) or any(c not in range(3) for c in channels):
        raise ValueError("Invalid channels")
    if bool(channels) != bool(lookback):
        raise ValueError("Empty information must have zero lookback")
    columns = list(range(4))
    for c in channels:
        columns.extend(4 + c * 36 + t for t in range(max(0, 36 - delay - lookback), 36 - delay))
    if pitch_available:
        columns.extend(4 + 3 * 36 + t for t in range(36 - delay))
    return np.asarray(columns, dtype=np.int64)


def nested_samples(mask: np.ndarray, budgets: list[int], seed: int) -> dict[int, np.ndarray]:
    valid = np.flatnonzero(np.asarray(mask).reshape(-1))
    if not budgets or min(budgets) < 1 or len(set(budgets)) != len(budgets) or max(budgets) > len(valid):
        raise ValueError("Budgets must be distinct positive and available")
    order = np.random.default_rng(seed).permutation(valid)
    return {n: order[:n].copy() for n in budgets}


def fit_standardizer(x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    a = np.asarray(x, dtype=np.float64)
    count = np.isfinite(a).sum(axis=0)
    mean = np.where(np.isfinite(a), a, 0).sum(axis=0) / np.maximum(count, 1)
    centered = np.where(np.isfinite(a), a - mean, 0)
    scale = np.sqrt((centered * centered).sum(axis=0) / np.maximum(count, 1))
    scale = np.where(scale > 1e-8, scale, 1)
    return mean.astype(np.float32), scale.astype(np.float32)


def standardize(x: np.ndarray, mean: np.ndarray, scale: np.ndarray) -> np.ndarray:
    a = np.asarray(x, dtype=np.float32)
    missing = ~np.isfinite(a)
    z = np.where(missing, 0, (a - mean) / scale)
    return np.column_stack((z, missing.astype(np.float32))).astype(np.float32)


class PinballMLP:
    """CPU deterministic quantile network; fixed epochs, no validation tuning."""

    def __init__(self, seed: int, settings: dict):
        self.seed, self.settings = seed, settings

    def _network(self, width: int):
        import torch
        hidden = self.settings["hidden"]
        return torch.nn.Sequential(torch.nn.Linear(width, hidden[0]), torch.nn.ReLU(),
                                   torch.nn.Linear(hidden[0], hidden[1]), torch.nn.ReLU(),
                                   torch.nn.Linear(hidden[1], 1))

    def fit(self, x: np.ndarray, y: np.ndarray):
        import torch
        torch.set_num_threads(2)
        torch.use_deterministic_algorithms(True)
        torch.manual_seed(self.seed)
        self.mean_, self.scale_ = fit_standardizer(x)
        xx = torch.from_numpy(standardize(x, self.mean_, self.scale_))
        self.target_scale_ = max(float(np.std(y)), 1.0)
        yy = torch.as_tensor(y / self.target_scale_, dtype=torch.float32)
        if not torch.isfinite(yy).all():
            raise ValueError("Invalid training targets")
        self.model_ = self._network(xx.shape[1])
        with torch.no_grad():
            self.model_[-1].bias.fill_(float(np.quantile(y, .9)) / self.target_scale_)
        optimizer = torch.optim.AdamW(self.model_.parameters(), lr=self.settings["learning_rate"],
                                     weight_decay=self.settings["weight_decay"])
        generator = torch.Generator().manual_seed(self.seed + 91000)
        self.training_trace_ = []
        batch = self.settings["batch_size"]
        for epoch in range(self.settings["epochs"]):
            order = torch.randperm(len(xx), generator=generator)
            total = 0.0
            for start in range(0, len(xx), batch):
                indices = order[start:start + batch]
                residual = yy[indices] - self.model_(xx[indices]).flatten()
                loss = torch.maximum(.9 * residual, -.1 * residual).mean()
                optimizer.zero_grad(set_to_none=True)
                loss.backward()
                optimizer.step()
                total += float(loss.detach()) * len(indices)
            self.training_trace_.append(total / len(xx))
        return self

    def predict(self, x: np.ndarray) -> np.ndarray:
        import torch
        values = []
        self.model_.eval()
        with torch.no_grad():
            for start in range(0, len(x), 8192):
                xx = torch.from_numpy(standardize(x[start:start + 8192], self.mean_, self.scale_))
                values.append(self.model_(xx).flatten().numpy().astype(np.float64) * self.target_scale_)
        return np.concatenate(values)
