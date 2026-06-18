from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


WTB_FEATURE_NAMES = (
    "Wspd",
    "Wdir_sin",
    "Wdir_cos",
    "Ndir_sin",
    "Ndir_cos",
    "Etmp",
    "Itmp",
    "Pab_mean",
    "Pab_std",
    "Prtv",
    "Patv_hist",
)
ERA5_FEATURE_NAMES = (
    "WindSpeed10",
    "u10",
    "v10",
    "t2m",
    "d2m",
    "sshf",
    "ssr",
    "tp",
)

# Backward-compatible aliases for existing imports.
FEATURE_NAMES = WTB_FEATURE_NAMES
FEATURE_INDEX = {name: idx for idx, name in enumerate(WTB_FEATURE_NAMES)}
REGIME_NAMES = (
    "idle",
    "mppt",
    "pitch_control",
    "transition",
)


@dataclass
class DataConfig:
    dataset: str = "wtb"
    root_dir: Path = Path(".")
    cache_root: str = "artifacts/cache"

    # WTB paths and topology.
    location_file: str = "sdwpf_baidukddcup2022_turb_location.CSV"
    dynamic_file: str = "wtbdata_245days.csv"
    max_days: Optional[int] = None
    num_turbines: int = 134
    slots_per_day: int = 144
    train_days: int = 180
    val_days: int = 30
    test_days: int = 35
    holdout_days: int = 0
    candidate_k: int = 8
    max_distance: float = 1500.0
    max_in_edges: int = 5
    cone_half_angle_deg: float = 25.0
    parallel_scale: float = 1200.0
    cross_scale: float = 400.0
    direction_is_from: bool = True
    preprocess_chunk_size: int = 250_000
    graph_chunk_size: int = 1024

    # Sequence lengths shared by both datasets.
    hist_len: int = 36
    pred_len: int = 24

    # ERA5 settings.
    era5_zip_pattern: str = "era5*.zip"
    era5_patch_size: int = 16
    era5_max_archives: Optional[int] = None
    era5_train_ratio: float = 0.6
    era5_val_ratio: float = 0.2
    era5_helper_python: Optional[str] = None
    era5_candidate_k: int = 8

    # External wind-farm SCADA settings.
    external_farm: str = "kelmarsh"
    external_target_farm: str = ""
    external_split: str = "chronological"
    external_source_dir: str = ""
    external_rated_wind: float = 10.5
    external_pitch_threshold: float = 2.0
    external_cut_in_wind: float = 3.0

    def cache_dir(self) -> Path:
        if self.dataset == "wtb":
            suffix = f"wtb_{self.max_days or 245}d"
        elif self.dataset == "era5":
            archives = self.era5_max_archives or 3
            suffix = f"era5_p{self.era5_patch_size}_m{archives}_k{self.era5_candidate_k}"
        elif self.dataset == "external_wind":
            split = self.external_split.replace("-", "_")
            farm = self.external_farm.strip().lower().replace("_", "-")
            target = self.external_target_farm.strip().lower().replace("_", "-")
            if self.external_split in {"leave-one-farm-out", "lofo"}:
                target = target or ("penmanshiel" if farm == "kelmarsh" else "kelmarsh")
                suffix = f"external_wind_{farm}_to_{target}_{split}"
            else:
                suffix = f"external_wind_{farm}_{split}"
        else:
            raise ValueError(f"Unsupported dataset: {self.dataset}")
        return Path(self.root_dir) / self.cache_root / suffix

    def total_days(self) -> int:
        return self.max_days or (self.train_days + self.val_days + self.test_days + self.holdout_days)

    def total_steps(self) -> int:
        return self.total_days() * self.slots_per_day

    def effective_day_split(self) -> tuple[int, int, int, int]:
        total = self.total_days()
        canonical_total = self.train_days + self.val_days + self.test_days + self.holdout_days
        if total >= canonical_total:
            return self.train_days, self.val_days, self.test_days, self.holdout_days
        if self.holdout_days > 0:
            if total <= 3:
                return max(total - 1, 1), 0, 0, 1 if total > 1 else 0
            holdout = max(1, int(round(total * self.holdout_days / max(canonical_total, 1))))
            remaining = max(total - holdout, 1)
            train = max(1, int(round(remaining * self.train_days / max(self.train_days + self.val_days + self.test_days, 1))))
            val = max(1, int(round(remaining * self.val_days / max(self.train_days + self.val_days + self.test_days, 1))))
            if train + val >= remaining:
                val = max(0, remaining - train - 1)
            test = remaining - train - val
            if test < 0:
                test = 0
            return train, val, test, holdout
        if total <= 1:
            return total, 0, 0, 0
        if total == 2:
            return 1, 1, 0, 0
        train = max(1, int(round(total * 0.6)))
        val = max(1, int(round(total * 0.2)))
        if train + val >= total:
            val = max(1, total - train - 1)
        test = total - train - val
        if test <= 0:
            test = 1
            if train >= val and train > 1:
                train -= 1
            elif val > 1:
                val -= 1
        return train, val, test, 0

    def train_steps(self) -> int:
        train_days, _, _, _ = self.effective_day_split()
        return train_days * self.slots_per_day

    def val_steps(self) -> int:
        _, val_days, _, _ = self.effective_day_split()
        return val_days * self.slots_per_day

    def test_steps(self) -> int:
        _, _, test_days, _ = self.effective_day_split()
        return test_days * self.slots_per_day

    def holdout_steps(self) -> int:
        _, _, _, holdout_days = self.effective_day_split()
        return holdout_days * self.slots_per_day

    def split_bounds(self) -> dict[str, tuple[int, int]]:
        train_end = self.train_steps()
        val_end = min(train_end + self.val_steps(), self.total_steps())
        test_end = min(val_end + self.test_steps(), self.total_steps())
        bounds = {
            "train": (0, train_end),
            "val": (train_end, val_end),
            "test": (val_end, test_end),
        }
        holdout_steps = self.holdout_steps()
        if holdout_steps > 0:
            bounds["holdout"] = (test_end, min(test_end + holdout_steps, self.total_steps()))
        return bounds

    def discover_era5_python(self) -> Optional[Path]:
        candidates = []
        if self.era5_helper_python:
            candidates.append(Path(self.era5_helper_python))
        candidates.append(Path(self.root_dir) / ".era5_env" / "python.exe")
        candidates.append(Path.home() / "anaconda3" / "python.exe")
        candidates.append(Path(sys.executable))
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return None


@dataclass
class ModelConfig:
    hidden_dim: int = 64
    num_experts: int = 4
    dropout: float = 0.1
    tau: float = 0.7
    gate_hidden_dim: int = 64
    primary_num_classes: int = 3
    gate_physics_dim: int = 4


@dataclass
class TrainConfig:
    mode: str = "moe_phys_full"
    batch_size: int = 16
    epochs: int = 20
    learning_rate: float = 2e-3
    weight_decay: float = 1e-4
    grad_clip_norm: float = 1.0
    patience: int = 5
    num_workers: int = 0
    seed: int = 42
    log_every: int = 50
    limit_train_batches: Optional[int] = None
    limit_val_batches: Optional[int] = None
    align_weight: float = 0.2
    aux_weight: float = 0.1
    smooth_weight: float = 0.05
    balance_weight: float = 0.01
    physics_force_weight: float = 0.0
    balance_top_k: int = 1
    label: str = ""

    def effective_loss_weights(self) -> dict[str, float]:
        if self.mode == "moe_phys_full":
            return {
                "align": self.align_weight,
                "aux": self.aux_weight,
                "smooth": self.smooth_weight,
                "balance": self.balance_weight,
                "physics_force": self.physics_force_weight,
            }
        if self.mode == "moe_unconstrained":
            return {"align": 0.0, "aux": 0.0, "smooth": 0.0, "balance": 0.0, "physics_force": 0.0}
        if self.mode == "moe_balance_only":
            return {
                "align": 0.0,
                "aux": 0.0,
                "smooth": 0.0,
                "balance": self.balance_weight,
                "physics_force": 0.0,
            }
        if self.mode == "moe_align_only":
            return {
                "align": self.align_weight,
                "aux": 0.0,
                "smooth": 0.0,
                "balance": 0.0,
                "physics_force": 0.0,
            }
        if self.mode == "moe_balance_align":
            return {
                "align": self.align_weight,
                "aux": 0.0,
                "smooth": 0.0,
                "balance": self.balance_weight,
                "physics_force": 0.0,
            }
        if self.mode == "moe_full_no_aux":
            return {
                "align": self.align_weight,
                "aux": 0.0,
                "smooth": self.smooth_weight,
                "balance": self.balance_weight,
                "physics_force": self.physics_force_weight,
            }
        if self.mode == "moe_full_no_smooth":
            return {
                "align": self.align_weight,
                "aux": self.aux_weight,
                "smooth": 0.0,
                "balance": self.balance_weight,
                "physics_force": self.physics_force_weight,
            }
        if self.mode == "moe_no_phys":
            return {
                "align": 0.0,
                "aux": 0.0,
                "smooth": 0.0,
                "balance": self.balance_weight,
                "physics_force": 0.0,
            }
        if self.mode == "moe_context_align":
            return {
                "align": self.align_weight,
                "aux": 0.0,
                "smooth": 0.0,
                "balance": self.balance_weight,
                "physics_force": self.physics_force_weight,
            }
        if self.mode == "moe_anchor_only":
            return {
                "align": self.align_weight,
                "aux": 0.0,
                "smooth": 0.0,
                "balance": self.balance_weight,
                "physics_force": self.physics_force_weight,
            }
        return {"align": 0.0, "aux": 0.0, "smooth": 0.0, "balance": 0.0, "physics_force": 0.0}


@dataclass
class EvalConfig:
    tsne_max_points: int = 6000
    switch_window: int = 18
    skip_visuals: bool = False
    save_predictions: bool = True
    plot_node: Optional[int] = None
