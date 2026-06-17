from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .utils import ensure_dir, load_json, save_json


DEFAULT_COST_RATIOS = [2.0, 5.0, 10.0, 20.0, 50.0]
DEFAULT_MAIN_RATIO = 10.0
DEFAULT_QUANTILES = [0.50, 0.60, 0.70, 0.80, 0.85, 0.90, 0.95, 0.975, 0.99]
BIN_NAMES = ["low", "mid", "high"]
POLICIES = ["global", "physical-bin", "gate-bin"]
RESERVE_DECISION_REQUIRED_FILES = (
    "reserve_decision_summary.csv",
    "reserve_decision_by_ratio.csv",
    "reserve_decision_by_risk_bin.csv",
    "reserve_decision_bootstrap.csv",
    "reserve_decision_raw_runs.csv",
    "reserve_decision_raw_bins.csv",
    "reserve_decision_daily_costs.csv",
    "reserve_decision_gate_loss.csv",
    "reserve_decision_config.json",
)
RESERVE_REQUIRED_MODELS = ("Graph WaveNet", "PatchTST", "Physics-Aligned MoE", "Boundary-forced router")
RESERVE_GATED_MODELS = ("Physics-Aligned MoE", "Boundary-forced router")
RESERVE_REQUIRED_SEEDS = (201, 202, 203, 204, 205)
RESERVE_REQUIRED_BOOTSTRAP_CANDIDATES = (
    "Graph WaveNet/physical-bin",
    "PatchTST/global",
    "PatchTST/physical-bin",
    "Physics-Aligned MoE/global",
    "Physics-Aligned MoE/physical-bin",
    "Physics-Aligned MoE/gate-bin",
    "Boundary-forced router/global",
    "Boundary-forced router/physical-bin",
    "Boundary-forced router/gate-bin",
)


@dataclass(frozen=True)
class SelectionRule:
    display_model: str
    source_model: str
    seeds: tuple[int, ...]
    experiment_group: str | None = None
    variant_key: str | None = None
    run_dir_contains: str | None = None


@dataclass(frozen=True)
class RunInfo:
    model: str
    source_model: str
    seed: int
    run_dir: Path
    variant_key: str
    experiment_group: str
    overall_rmse: float | None


@dataclass
class DecisionPanel:
    forecast: np.ndarray
    actual: np.ndarray
    shortfall: np.ndarray
    valid: np.ndarray
    physical_score: np.ndarray
    gate_score: np.ndarray | None
    boundary_score: np.ndarray
    gate_correct_score: np.ndarray | None
    spatial_holdout: np.ndarray
    anchor_index: np.ndarray
    day_index: np.ndarray


@dataclass
class RunDecisionData:
    info: RunInfo
    val: DecisionPanel
    test: DecisionPanel
    has_gate: bool


@dataclass(frozen=True)
class Calibration:
    policy: str
    status: str
    score_source: str
    thresholds: tuple[float, float] | None
    reserves: dict[str, float]
    quantiles: dict[str, float]


DEFAULT_SELECTION_RULES = [
    SelectionRule("Graph WaveNet", "Graph WaveNet", (201, 202, 203, 204, 205), experiment_group="strong_baselines"),
    SelectionRule("PatchTST", "PatchTST", (201, 202, 203, 204, 205), experiment_group="strong_baselines"),
    SelectionRule(
        "Physics-Aligned MoE",
        "Physics-Aligned MoE",
        (201, 202, 203, 204, 205),
        experiment_group="ablation",
        variant_key="full",
        run_dir_contains="priority2_full_corrected_family",
    ),
    SelectionRule(
        "Boundary-forced router",
        "MoE + L_bal + L_align + L_force",
        (201, 202, 203, 204, 205),
        experiment_group="ablation",
        variant_key="bal_align_force",
        run_dir_contains="priority1_corrected_5seed",
    ),
]


def select_default_wtb_runs(run_table: Path | str, root_dir: Path | str = ".") -> list[RunInfo]:
    table_path = Path(run_table)
    root = Path(root_dir)
    df = pd.read_csv(table_path)
    missing: list[str] = []
    selected: list[RunInfo] = []

    for rule in DEFAULT_SELECTION_RULES:
        for seed in rule.seeds:
            base_subset = df[df["model"].astype(str).eq(rule.source_model)].copy()
            subset = base_subset[pd.to_numeric(base_subset["seed"], errors="coerce").astype("Int64").eq(seed)]
            if rule.experiment_group:
                subset = subset[subset["experiment_group"].astype(str).eq(rule.experiment_group)]
            if rule.variant_key:
                subset = subset[subset["variant_key"].astype(str).eq(rule.variant_key)]
            if rule.run_dir_contains and not subset.empty:
                marked_subset = subset[subset["run_dir"].astype(str).str.contains(rule.run_dir_contains, case=False, na=False)]
                if not marked_subset.empty:
                    subset = marked_subset
            if subset.empty:
                missing.append(f"{rule.display_model} seed {seed}")
                continue
            row = subset.sort_values("run_dir").iloc[0]
            run_dir = Path(str(row["run_dir"]))
            if not run_dir.is_absolute():
                run_dir = root / run_dir
            selected.append(
                RunInfo(
                    model=rule.display_model,
                    source_model=rule.source_model,
                    seed=seed,
                    run_dir=run_dir,
                    variant_key=str(row.get("variant_key", "")),
                    experiment_group=str(row.get("experiment_group", "")),
                    overall_rmse=_optional_float(row.get("overall_rmse")),
                )
            )

    if missing:
        raise ValueError("Missing default WTB reserve-decision run(s): " + "; ".join(missing))
    _validate_run_files(selected)
    return selected


def run_reserve_decision(
    *,
    run_table: Path | str,
    output_dir: Path | str,
    root_dir: Path | str = ".",
    cache_dir: Path | str | None = None,
    cost_ratios: list[float] | None = None,
    main_ratio: float = DEFAULT_MAIN_RATIO,
    quantiles: list[float] | None = None,
    strata: list[str] | None = None,
    boundary_band: float = 1.0,
    bootstrap_samples: int = 1000,
    seed: int = 42,
    make_plots: bool = True,
) -> Path:
    ratios = cost_ratios or DEFAULT_COST_RATIOS
    candidate_quantiles = quantiles or DEFAULT_QUANTILES
    stratum_list = _normalize_strata(strata)
    out_dir = ensure_dir(output_dir)
    cache_meta = _load_cache_meta(cache_dir, boundary_band=boundary_band)
    dt = 1.0 / float(cache_meta["steps_per_hour"])

    runs = select_default_wtb_runs(run_table, root_dir=root_dir)
    run_data = [_load_run_decision_data(run, cache_meta) for run in runs]
    _validate_anchor_alignment(run_data)

    raw_rows: list[dict[str, Any]] = []
    bin_rows: list[dict[str, Any]] = []
    daily_rows: list[dict[str, Any]] = []
    gate_loss_rows: list[dict[str, Any]] = []
    for data in run_data:
        for subset_name, val_subset, test_subset in _iter_subsets(
            data.val,
            data.test,
            cache_meta["pred_len"],
            strata=stratum_list,
        ):
            for ratio in ratios:
                for policy in POLICIES:
                    calibration = _calibrate_policy(
                        policy=policy,
                        panel=val_subset,
                        ratio=ratio,
                        dt=dt,
                        quantiles=candidate_quantiles,
                    )
                    raw_row, policy_bin_rows, policy_daily_rows = _evaluate_policy(
                        data=data,
                        calibration=calibration,
                        test_panel=test_subset,
                        subset_name=subset_name,
                        ratio=ratio,
                        dt=dt,
                        main_ratio=main_ratio,
                    )
                    raw_rows.append(raw_row)
                    bin_rows.extend(policy_bin_rows)
                    daily_rows.extend(policy_daily_rows)
                    if calibration.status == "applicable":
                        reserve_matrix, _ = _reserve_matrix_for_calibration(calibration, test_subset)
                        gate_loss_rows.extend(
                            _gate_correctness_loss_rows(raw_row, test_subset, reserve_matrix, ratio, dt)
                        )

    raw_df = pd.DataFrame(raw_rows)
    bin_df = pd.DataFrame(bin_rows)
    daily_df = pd.DataFrame(daily_rows)
    gate_loss_df = pd.DataFrame(gate_loss_rows)
    by_ratio = _aggregate_metric_rows(raw_df)
    summary = by_ratio[np.isclose(by_ratio["cost_ratio"].astype(float), float(main_ratio))].copy()
    by_bin = _aggregate_bin_rows(bin_df)
    bootstrap_df = _bootstrap_pairs(daily_df, samples=bootstrap_samples, seed=seed, main_ratio=main_ratio)

    _write_outputs(
        output_dir=out_dir,
        summary=summary,
        by_ratio=by_ratio,
        by_bin=by_bin,
        bootstrap_df=bootstrap_df,
        raw_df=raw_df,
        bin_df=bin_df,
        daily_df=daily_df,
        gate_loss_df=gate_loss_df,
        config={
            "dataset": "wtb",
            "run_table": str(Path(run_table)),
            "cache_dir": str(cache_dir) if cache_dir else None,
            "cost_ratios": ratios,
            "main_ratio": main_ratio,
            "quantiles": candidate_quantiles,
            "strata": stratum_list,
            "boundary_band": float(boundary_band),
            "reserve_cost": 1.0,
            "dt": dt,
            "bootstrap_samples": bootstrap_samples,
            "seed": seed,
            "selected_runs": [
                {
                    "model": run.model,
                    "source_model": run.source_model,
                    "seed": run.seed,
                    "run_dir": str(run.run_dir),
                    "variant_key": run.variant_key,
                    "experiment_group": run.experiment_group,
                    "overall_rmse": run.overall_rmse,
                }
                for run in runs
            ],
        },
    )
    if make_plots:
        _make_plots(out_dir, by_ratio, by_bin, main_ratio)
    return out_dir


def _optional_float(value: Any) -> float | None:
    try:
        if value is None or (isinstance(value, float) and np.isnan(value)):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _validate_run_files(runs: list[RunInfo]) -> None:
    required = ["pred.npy", "target.npy", "mask.npy", "regime_primary.npy", "anchor_index.npy"]
    missing: list[str] = []
    for run in runs:
        if not run.run_dir.exists():
            missing.append(f"{run.model} seed {run.seed}: missing run dir {run.run_dir}")
            continue
        for split in ["val_metrics", "test_metrics"]:
            split_dir = run.run_dir / split
            for name in required:
                path = split_dir / name
                if not path.exists():
                    missing.append(f"{run.model} seed {run.seed}: missing {split}/{name}")
    if missing:
        raise ValueError("Reserve-decision input file check failed: " + "; ".join(missing))


def _load_cache_meta(cache_dir: Path | str | None, *, boundary_band: float = 1.0) -> dict[str, Any]:
    if cache_dir is None:
        return {
            "steps_per_hour": 6,
            "pred_len": 24,
            "time_index": None,
            "boundary_score": None,
            "gate_true_regime": None,
            "spatial_holdout_patch": {},
        }
    cache_path = Path(cache_dir)
    metadata = load_json(cache_path / "metadata.json")
    time_index_path = cache_path / "time_index.npy"
    time_index = np.load(time_index_path, mmap_mode="r") if time_index_path.exists() else None
    boundary_score = _cache_boundary_score(cache_path, metadata, boundary_band=float(boundary_band))
    gate_true_regime = np.load(cache_path / "regime_primary.npy", mmap_mode="r") if (cache_path / "regime_primary.npy").exists() else None
    return {
        "steps_per_hour": int(metadata.get("steps_per_hour", 6)),
        "pred_len": int(metadata.get("pred_len", 24)),
        "time_index": time_index,
        "boundary_score": boundary_score,
        "gate_true_regime": gate_true_regime,
        "spatial_holdout_patch": metadata.get("spatial_holdout_patch", {}),
        "split_bounds": metadata.get("split_bounds", {}),
    }


def _cache_boundary_score(cache_path: Path, metadata: dict[str, Any], *, boundary_band: float) -> np.ndarray | None:
    physics_path = cache_path / "physics.npy"
    regime_path = cache_path / "regime_primary.npy"
    valid_path = cache_path / "regime_primary_valid.npy"
    if not physics_path.exists() or not regime_path.exists():
        return None
    try:
        physics = np.load(physics_path, mmap_mode="r")
        regime = np.load(regime_path, mmap_mode="r")
        valid = np.load(valid_path, mmap_mode="r") if valid_path.exists() else np.ones_like(regime, dtype=np.float32)
    except (OSError, ValueError):
        return None
    if physics.ndim < 3 or regime.shape != physics.shape[:2]:
        return None
    rated_wind = float(metadata.get("wtb_thresholds", {}).get("rated_wind", 10.5))
    wspd = np.asarray(physics[..., 0], dtype=np.float32)
    boundary = (
        np.isin(np.asarray(regime), [1, 2])
        & (np.asarray(valid) > 0)
        & np.isfinite(wspd)
        & (np.abs(wspd - rated_wind) <= float(boundary_band))
    )
    return boundary.astype(np.float32)


def _load_run_decision_data(run: RunInfo, cache_meta: dict[str, Any]) -> RunDecisionData:
    val = _load_panel(run.run_dir / "val_metrics", cache_meta)
    test = _load_panel(run.run_dir / "test_metrics", cache_meta)
    return RunDecisionData(info=run, val=val, test=test, has_gate=val.gate_score is not None and test.gate_score is not None)


def _load_panel(metrics_dir: Path, cache_meta: dict[str, Any]) -> DecisionPanel:
    pred = np.load(metrics_dir / "pred.npy", mmap_mode="r")
    target = np.load(metrics_dir / "target.npy", mmap_mode="r")
    mask = np.load(metrics_dir / "mask.npy", mmap_mode="r")
    pred_arr = np.nan_to_num(np.asarray(pred, dtype=np.float64), nan=0.0)
    target_arr = np.nan_to_num(np.asarray(target, dtype=np.float64), nan=0.0)
    mask_arr = np.asarray(mask, dtype=np.float64)
    forecast = np.sum(pred_arr * mask_arr, axis=2)
    actual = np.sum(target_arr * mask_arr, axis=2)
    valid = np.sum(mask_arr, axis=2) > 0.0
    shortfall = np.maximum(forecast - actual, 0.0)

    regime = np.load(metrics_dir / "regime_primary.npy", mmap_mode="r")
    regime_arr = np.asarray(regime)
    valid_path = metrics_dir / "regime_primary_valid.npy"
    if valid_path.exists():
        regime_valid = np.asarray(np.load(valid_path, mmap_mode="r"), dtype=np.float64) > 0.0
        denom = np.maximum(regime_valid.sum(axis=1), 1.0)
        physical_score = (((regime_arr == 2) | (regime_arr == 3)) & regime_valid).sum(axis=1) / denom
    else:
        physical_score = ((regime_arr == 2) | (regime_arr == 3)).mean(axis=1)

    gate_score = None
    gate_path = metrics_dir / "gate_prob.npy"
    if gate_path.exists():
        gate = np.load(gate_path, mmap_mode="r")
        if gate.shape[-1] > 2:
            gate_score = np.asarray(gate[..., 2], dtype=np.float64).mean(axis=1)

    anchor_index = np.asarray(np.load(metrics_dir / "anchor_index.npy", mmap_mode="r"), dtype=np.int64)
    boundary_score = _window_cache_score(cache_meta.get("boundary_score"), anchor_index, regime_arr.shape[1])
    gate_correct_score = _window_gate_correctness(metrics_dir, cache_meta, anchor_index)
    spatial_holdout = _spatial_holdout_rows(cache_meta, anchor_index)
    day_index = _day_index_from_anchor(anchor_index, cache_meta)
    return DecisionPanel(
        forecast=forecast,
        actual=actual,
        shortfall=shortfall,
        valid=valid,
        physical_score=np.asarray(physical_score, dtype=np.float64),
        gate_score=gate_score,
        boundary_score=boundary_score,
        gate_correct_score=gate_correct_score,
        spatial_holdout=spatial_holdout,
        anchor_index=anchor_index,
        day_index=day_index,
    )


def _window_cache_score(score: Any, anchor_index: np.ndarray, num_nodes: int) -> np.ndarray:
    if score is None:
        return np.zeros(anchor_index.shape[0], dtype=np.float64)
    try:
        score_arr = np.asarray(score)
        selected = score_arr[anchor_index]
    except (IndexError, ValueError, TypeError):
        return np.zeros(anchor_index.shape[0], dtype=np.float64)
    if selected.ndim == 1:
        return selected.astype(np.float64)
    if selected.ndim >= 2:
        return selected.reshape(selected.shape[0], -1).mean(axis=1).astype(np.float64)
    return np.zeros(anchor_index.shape[0], dtype=np.float64)


def _window_gate_correctness(metrics_dir: Path, cache_meta: dict[str, Any], anchor_index: np.ndarray) -> np.ndarray | None:
    gate_path = metrics_dir / "gate_prob.npy"
    if not gate_path.exists():
        return None
    try:
        gate = np.asarray(np.load(gate_path, mmap_mode="r"))
    except (OSError, ValueError):
        return None
    if gate.ndim < 3:
        return None
    gate_classes = int(min(3, gate.shape[-1]))
    pred = np.asarray(gate[..., :gate_classes]).argmax(axis=-1)
    if (metrics_dir / "regime_primary.npy").exists():
        try:
            regime = np.asarray(np.load(metrics_dir / "regime_primary.npy", mmap_mode="r"))
        except (OSError, ValueError):
            regime = None
    else:
        regime = None
    if regime is None or regime.shape != pred.shape:
        true_cache = cache_meta.get("gate_true_regime")
        if true_cache is None:
            return None
        try:
            regime = np.asarray(true_cache[anchor_index])
        except (IndexError, ValueError, TypeError):
            return None
    valid_path = metrics_dir / "regime_primary_valid.npy"
    if valid_path.exists():
        try:
            valid = np.asarray(np.load(valid_path, mmap_mode="r")) > 0
        except (OSError, ValueError):
            valid = np.ones_like(regime, dtype=bool)
    else:
        valid = np.ones_like(regime, dtype=bool)
    usable = valid & (regime >= 0) & (regime < gate_classes)
    correct = (pred == regime) & usable
    denom = np.maximum(usable.reshape(usable.shape[0], -1).sum(axis=1), 1)
    return (correct.reshape(correct.shape[0], -1).sum(axis=1) / denom).astype(np.float64)


def _spatial_holdout_rows(cache_meta: dict[str, Any], anchor_index: np.ndarray) -> np.ndarray:
    patch = cache_meta.get("spatial_holdout_patch") or {}
    split_bounds = cache_meta.get("split_bounds") or patch.get("split_bounds") or {}
    test_bounds = split_bounds.get("test") or split_bounds.get("holdout")
    if not test_bounds:
        return np.zeros(anchor_index.shape[0], dtype=bool)
    start, end = int(test_bounds[0]), int(test_bounds[1])
    return ((anchor_index >= start) & (anchor_index < end)).astype(bool)


def _day_index_from_anchor(anchor_index: np.ndarray, cache_meta: dict[str, Any]) -> np.ndarray:
    time_index = cache_meta.get("time_index")
    if time_index is not None:
        values = np.asarray(time_index[anchor_index])
        if values.ndim == 2:
            return values[:, 0].astype(np.int64)
        return values.astype(np.int64)
    steps_per_day = int(cache_meta.get("steps_per_hour", 6)) * 24
    return (anchor_index // steps_per_day).astype(np.int64)


def _validate_anchor_alignment(run_data: list[RunDecisionData]) -> None:
    if not run_data:
        return
    base = run_data[0]
    mismatches = []
    for data in run_data[1:]:
        if not np.array_equal(base.val.anchor_index, data.val.anchor_index):
            mismatches.append(f"{data.info.model} seed {data.info.seed}: val anchor_index mismatch")
        if not np.array_equal(base.test.anchor_index, data.test.anchor_index):
            mismatches.append(f"{data.info.model} seed {data.info.seed}: test anchor_index mismatch")
    if mismatches:
        raise ValueError("Reserve-decision run windows are not aligned: " + "; ".join(mismatches))


def _normalize_strata(strata: list[str] | tuple[str, ...] | str | None) -> list[str]:
    if strata is None:
        return []
    if isinstance(strata, str):
        raw = [token.strip() for token in strata.split(",") if token.strip()]
    else:
        raw = [str(token).strip() for token in strata if str(token).strip()]
    valid = {"boundary", "non_boundary", "late_period", "spatial_holdout"}
    unknown = sorted(set(raw).difference(valid))
    if unknown:
        raise ValueError(f"Unsupported reserve-decision strata: {unknown}. Available: {sorted(valid)}")
    return raw


def _iter_subsets(
    val: DecisionPanel,
    test: DecisionPanel,
    pred_len: int,
    strata: list[str] | None = None,
) -> list[tuple[str, DecisionPanel, DecisionPanel]]:
    val_full = np.ones(val.anchor_index.shape[0], dtype=bool)
    test_full = np.ones(test.anchor_index.shape[0], dtype=bool)
    val_mod = int(val.anchor_index[0] % pred_len) if val.anchor_index.size else 0
    test_mod = int(test.anchor_index[0] % pred_len) if test.anchor_index.size else 0
    val_non_overlap = (val.anchor_index % pred_len) == val_mod
    test_non_overlap = (test.anchor_index % pred_len) == test_mod
    subsets = [
        ("full", _filter_panel(val, val_full), _filter_panel(test, test_full)),
        ("non_overlap", _filter_panel(val, val_non_overlap), _filter_panel(test, test_non_overlap)),
    ]
    requested = set(strata or [])
    if "boundary" in requested:
        subsets.append(
            (
                "boundary",
                _filter_panel(val, _boundary_selector(val, want_boundary=True)),
                _filter_panel(test, _boundary_selector(test, want_boundary=True)),
            )
        )
    if "non_boundary" in requested:
        subsets.append(
            (
                "non_boundary",
                _filter_panel(val, _boundary_selector(val, want_boundary=False)),
                _filter_panel(test, _boundary_selector(test, want_boundary=False)),
            )
        )
    if "late_period" in requested:
        subsets.append(
            (
                "late_period",
                _filter_panel(val, _late_period_selector(val)),
                _filter_panel(test, _late_period_selector(test)),
            )
        )
    if "spatial_holdout" in requested:
        subsets.append(
            (
                "spatial_holdout",
                _filter_panel(val, val_full),
                _filter_panel(test, test.spatial_holdout),
            )
        )
    return subsets


def _boundary_selector(panel: DecisionPanel, *, want_boundary: bool) -> np.ndarray:
    score = np.asarray(panel.boundary_score, dtype=np.float64)
    if score.size == 0:
        return np.zeros(panel.anchor_index.shape[0], dtype=bool)
    selector = score > 0.0
    return selector if want_boundary else ~selector


def _late_period_selector(panel: DecisionPanel) -> np.ndarray:
    if panel.anchor_index.size == 0:
        return np.zeros(0, dtype=bool)
    cutoff = np.quantile(panel.anchor_index.astype(np.float64), 0.5)
    return panel.anchor_index.astype(np.float64) >= float(cutoff)


def _filter_panel(panel: DecisionPanel, rows: np.ndarray) -> DecisionPanel:
    rows = np.asarray(rows, dtype=bool)
    return DecisionPanel(
        forecast=panel.forecast[rows],
        actual=panel.actual[rows],
        shortfall=panel.shortfall[rows],
        valid=panel.valid[rows],
        physical_score=panel.physical_score[rows],
        gate_score=panel.gate_score[rows] if panel.gate_score is not None else None,
        boundary_score=panel.boundary_score[rows],
        gate_correct_score=panel.gate_correct_score[rows] if panel.gate_correct_score is not None else None,
        spatial_holdout=panel.spatial_holdout[rows],
        anchor_index=panel.anchor_index[rows],
        day_index=panel.day_index[rows],
    )


def _calibrate_policy(
    *,
    policy: str,
    panel: DecisionPanel,
    ratio: float,
    dt: float,
    quantiles: list[float],
) -> Calibration:
    if policy == "global":
        reserve, quantile = _calibrate_scalar(panel.shortfall, panel.valid, ratio, dt, quantiles)
        return Calibration(policy, "applicable", "global", None, {"all": reserve}, {"all": quantile})

    if policy == "physical-bin":
        scores = panel.physical_score
        score_source = "physical"
    elif policy == "gate-bin":
        if panel.gate_score is None:
            return Calibration(policy, "not_applicable", "gate", None, {}, {})
        scores = panel.gate_score
        score_source = "gate"
    else:
        raise ValueError(f"Unsupported reserve policy: {policy}")

    thresholds = _risk_thresholds(scores)
    labels = _assign_bins(scores, thresholds)
    global_reserve, global_quantile = _calibrate_scalar(panel.shortfall, panel.valid, ratio, dt, quantiles)
    reserves: dict[str, float] = {}
    selected_quantiles: dict[str, float] = {}
    for idx, name in enumerate(BIN_NAMES):
        row_mask = labels == idx
        cell_mask = panel.valid & row_mask[:, None]
        if cell_mask.any():
            reserve, quantile = _calibrate_scalar(panel.shortfall, cell_mask, ratio, dt, quantiles)
        else:
            reserve, quantile = global_reserve, global_quantile
        reserves[name] = reserve
        selected_quantiles[name] = quantile
    return Calibration(policy, "applicable", score_source, thresholds, reserves, selected_quantiles)


def _calibrate_scalar(
    shortfall: np.ndarray,
    valid: np.ndarray,
    ratio: float,
    dt: float,
    quantiles: list[float],
) -> tuple[float, float]:
    values = shortfall[valid]
    if values.size == 0:
        return 0.0, float("nan")
    best_reserve = 0.0
    best_quantile = float(quantiles[0])
    best_cost = float("inf")
    for quantile in quantiles:
        reserve = float(np.quantile(values, quantile))
        metrics = _cost_metrics(shortfall, valid, _reserve_like(shortfall, reserve), ratio, dt)
        if metrics["total_cost"] < best_cost:
            best_cost = metrics["total_cost"]
            best_reserve = reserve
            best_quantile = float(quantile)
    return best_reserve, best_quantile


def _evaluate_policy(
    *,
    data: RunDecisionData,
    calibration: Calibration,
    test_panel: DecisionPanel,
    subset_name: str,
    ratio: float,
    dt: float,
    main_ratio: float,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    base = {
        "model": data.info.model,
        "source_model": data.info.source_model,
        "seed": data.info.seed,
        "run_dir": str(data.info.run_dir),
        "variant_key": data.info.variant_key,
        "experiment_group": data.info.experiment_group,
        "overall_rmse": data.info.overall_rmse,
        "policy": calibration.policy,
        "subset": subset_name,
        "cost_ratio": float(ratio),
        "status": calibration.status,
        "score_source": calibration.score_source,
        "threshold_low": calibration.thresholds[0] if calibration.thresholds else np.nan,
        "threshold_high": calibration.thresholds[1] if calibration.thresholds else np.nan,
        "best_quantile": _format_quantiles(calibration.quantiles),
        "reserve": _format_reserves(calibration.reserves),
    }
    if calibration.status != "applicable":
        return {**base, **_empty_metrics()}, [], []

    reserve_matrix, labels = _reserve_matrix_for_calibration(calibration, test_panel)
    metrics = _cost_metrics(test_panel.shortfall, test_panel.valid, reserve_matrix, ratio, dt)
    row = {**base, **metrics}
    bin_rows = _bin_metric_rows(base, calibration, test_panel, reserve_matrix, labels, ratio, dt)
    daily_rows: list[dict[str, Any]] = []
    if np.isclose(float(ratio), float(main_ratio)) and subset_name == "full":
        daily_rows = _daily_cost_rows(base, test_panel, reserve_matrix, ratio, dt)
    return row, bin_rows, daily_rows


def _reserve_matrix_for_calibration(
    calibration: Calibration,
    panel: DecisionPanel,
) -> tuple[np.ndarray, np.ndarray | None]:
    if calibration.policy == "global":
        return _reserve_like(panel.shortfall, calibration.reserves["all"]), None

    scores = panel.physical_score if calibration.score_source == "physical" else panel.gate_score
    if scores is None or calibration.thresholds is None:
        return _reserve_like(panel.shortfall, 0.0), None
    labels = _assign_bins(scores, calibration.thresholds)
    reserve_by_bin = np.zeros(labels.shape[0], dtype=np.float64)
    for idx, name in enumerate(BIN_NAMES):
        reserve_by_bin[labels == idx] = calibration.reserves[name]
    return np.repeat(reserve_by_bin[:, None], panel.shortfall.shape[1], axis=1), labels


def _cost_metrics(
    shortfall: np.ndarray,
    valid: np.ndarray,
    reserve: np.ndarray,
    ratio: float,
    dt: float,
) -> dict[str, float]:
    if valid.sum() == 0:
        return _empty_metrics()
    shortage_after = np.maximum(shortfall - reserve, 0.0)
    cost = (reserve + ratio * shortage_after) * dt
    valid_cost = cost[valid]
    valid_reserve = reserve[valid]
    valid_shortage = shortage_after[valid]
    return {
        "total_cost": float(valid_cost.sum()),
        "mean_cost": float(valid_cost.mean()),
        "violation_rate": float((valid_shortage > 1e-9).mean()),
        "mean_reserve": float(valid_reserve.mean()),
        "reserve_energy": float(valid_reserve.sum() * dt),
        "shortage_energy": float(valid_shortage.sum() * dt),
        "valid_cells": int(valid.sum()),
    }


def _empty_metrics() -> dict[str, float]:
    return {
        "total_cost": np.nan,
        "mean_cost": np.nan,
        "violation_rate": np.nan,
        "mean_reserve": np.nan,
        "reserve_energy": np.nan,
        "shortage_energy": np.nan,
        "valid_cells": 0,
    }


def _reserve_like(shortfall: np.ndarray, reserve: float) -> np.ndarray:
    return np.full(shortfall.shape, float(reserve), dtype=np.float64)


def _risk_thresholds(scores: np.ndarray) -> tuple[float, float]:
    if scores.size == 0:
        return 0.0, 0.0
    q_low, q_high = np.quantile(scores, [1.0 / 3.0, 2.0 / 3.0])
    return float(q_low), float(q_high)


def _assign_bins(scores: np.ndarray, thresholds: tuple[float, float]) -> np.ndarray:
    low, high = thresholds
    return np.where(scores <= low, 0, np.where(scores <= high, 1, 2)).astype(np.int16)


def _format_quantiles(quantiles: dict[str, float]) -> str:
    return ";".join(f"{key}={value:.3f}" for key, value in quantiles.items())


def _format_reserves(reserves: dict[str, float]) -> str:
    return ";".join(f"{key}={value:.6g}" for key, value in reserves.items())


def _bin_metric_rows(
    base: dict[str, Any],
    calibration: Calibration,
    panel: DecisionPanel,
    reserve_matrix: np.ndarray,
    labels: np.ndarray | None,
    ratio: float,
    dt: float,
) -> list[dict[str, Any]]:
    if labels is None:
        metrics = _cost_metrics(panel.shortfall, panel.valid, reserve_matrix, ratio, dt)
        return [{**base, "risk_bin": "all", **metrics}]
    rows = []
    for idx, name in enumerate(BIN_NAMES):
        row_mask = labels == idx
        cell_mask = panel.valid & row_mask[:, None]
        metrics = _cost_metrics(panel.shortfall, cell_mask, reserve_matrix, ratio, dt)
        rows.append({**base, "risk_bin": name, **metrics})
    return rows


def _daily_cost_rows(
    base: dict[str, Any],
    panel: DecisionPanel,
    reserve_matrix: np.ndarray,
    ratio: float,
    dt: float,
) -> list[dict[str, Any]]:
    shortage_after = np.maximum(panel.shortfall - reserve_matrix, 0.0)
    cost = (reserve_matrix + ratio * shortage_after) * dt
    cost = np.where(panel.valid, cost, 0.0)
    rows = []
    for day in np.unique(panel.day_index):
        selector = panel.day_index == day
        rows.append(
            {
                "model": base["model"],
                "policy": base["policy"],
                "seed": base["seed"],
                "cost_ratio": base["cost_ratio"],
                "day": int(day),
                "daily_cost": float(cost[selector].sum()),
            }
        )
    return rows


def _gate_correctness_loss_rows(
    base: dict[str, Any],
    panel: DecisionPanel,
    reserve_matrix: np.ndarray,
    ratio: float,
    dt: float,
) -> list[dict[str, Any]]:
    common = {
        "model": base["model"],
        "source_model": base["source_model"],
        "seed": base["seed"],
        "run_dir": base["run_dir"],
        "variant_key": base["variant_key"],
        "experiment_group": base["experiment_group"],
        "policy": base["policy"],
        "subset": base["subset"],
        "cost_ratio": base["cost_ratio"],
    }
    if panel.gate_correct_score is None:
        return [
            {
                **common,
                "gate_correctness": label,
                "status": "not_applicable",
                "n_windows": 0,
                **_empty_metrics(),
            }
            for label in ["gate_correct", "gate_wrong"]
        ]
    score = np.asarray(panel.gate_correct_score, dtype=np.float64)
    selectors = {
        "gate_correct": score >= 0.5,
        "gate_wrong": score < 0.5,
    }
    rows = []
    for label, selector in selectors.items():
        selector = np.asarray(selector, dtype=bool)
        cell_mask = panel.valid & selector[:, None]
        metrics = _cost_metrics(panel.shortfall, cell_mask, reserve_matrix, ratio, dt)
        rows.append(
            {
                **common,
                "gate_correctness": label,
                "status": "applicable",
                "n_windows": int(selector.sum()),
                "mean_gate_correct_score": float(score[selector].mean()) if selector.any() else np.nan,
                **metrics,
            }
        )
    return rows


def _aggregate_metric_rows(raw_df: pd.DataFrame) -> pd.DataFrame:
    group_cols = ["subset", "cost_ratio", "model", "policy", "status"]
    metric_cols = ["total_cost", "mean_cost", "violation_rate", "mean_reserve", "reserve_energy", "shortage_energy"]
    rows = []
    for keys, group in raw_df.groupby(group_cols, dropna=False):
        row = dict(zip(group_cols, keys))
        row["n_runs"] = int(group["seed"].nunique())
        row["overall_rmse_mean"] = float(group["overall_rmse"].mean()) if group["overall_rmse"].notna().any() else np.nan
        for col in metric_cols:
            row[f"{col}_mean"] = float(group[col].mean()) if group[col].notna().any() else np.nan
            row[f"{col}_std"] = float(group[col].std(ddof=1)) if group[col].notna().sum() > 1 else 0.0
        row["best_quantile"] = _unique_join(group["best_quantile"])
        row["reserve"] = _unique_join(group["reserve"])
        rows.append(row)
    result = pd.DataFrame(rows)
    if not result.empty:
        result["regret"] = np.nan
        applicable = result["status"].eq("applicable")
        for (_, ratio), idx in result[applicable].groupby(["subset", "cost_ratio"]).groups.items():
            best = result.loc[list(idx), "total_cost_mean"].min()
            result.loc[list(idx), "regret"] = result.loc[list(idx), "total_cost_mean"] - best
        result = result.sort_values(["subset", "cost_ratio", "total_cost_mean", "model", "policy"], na_position="last")
    return result


def _aggregate_bin_rows(bin_df: pd.DataFrame) -> pd.DataFrame:
    if bin_df.empty:
        return pd.DataFrame()
    group_cols = ["subset", "cost_ratio", "model", "policy", "risk_bin", "status"]
    metric_cols = ["total_cost", "mean_cost", "violation_rate", "mean_reserve", "reserve_energy", "shortage_energy"]
    rows = []
    for keys, group in bin_df.groupby(group_cols, dropna=False):
        row = dict(zip(group_cols, keys))
        row["n_runs"] = int(group["seed"].nunique())
        for col in metric_cols:
            row[f"{col}_mean"] = float(group[col].mean()) if group[col].notna().any() else np.nan
            row[f"{col}_std"] = float(group[col].std(ddof=1)) if group[col].notna().sum() > 1 else 0.0
        rows.append(row)
    return pd.DataFrame(rows).sort_values(["subset", "cost_ratio", "risk_bin", "total_cost_mean"], na_position="last")


def _unique_join(values: pd.Series) -> str:
    clean = sorted({str(value) for value in values.dropna().tolist() if str(value)})
    return "|".join(clean)


def _bootstrap_pairs(daily_df: pd.DataFrame, *, samples: int, seed: int, main_ratio: float) -> pd.DataFrame:
    if daily_df.empty:
        return pd.DataFrame()
    grouped = (
        daily_df[daily_df["cost_ratio"].astype(float).round(10).eq(round(float(main_ratio), 10))]
        .groupby(["model", "policy", "seed", "day"], as_index=False)["daily_cost"]
        .mean()
    )
    pairs = [
        ("Graph WaveNet", "physical-bin", "Graph WaveNet", "global"),
        ("PatchTST", "global", "Graph WaveNet", "global"),
        ("PatchTST", "physical-bin", "Graph WaveNet", "global"),
        ("Physics-Aligned MoE", "global", "Graph WaveNet", "global"),
        ("Physics-Aligned MoE", "physical-bin", "Graph WaveNet", "global"),
        ("Physics-Aligned MoE", "gate-bin", "Graph WaveNet", "global"),
        ("Boundary-forced router", "global", "Graph WaveNet", "global"),
        ("Boundary-forced router", "physical-bin", "Graph WaveNet", "global"),
        ("Boundary-forced router", "gate-bin", "Graph WaveNet", "global"),
    ]
    rng = np.random.default_rng(seed)
    rows = []
    for model, policy, baseline_model, baseline_policy in pairs:
        cand = grouped[(grouped["model"] == model) & (grouped["policy"] == policy)]
        base = grouped[(grouped["model"] == baseline_model) & (grouped["policy"] == baseline_policy)]
        merged = cand.merge(base, on=["seed", "day"], suffixes=("_candidate", "_baseline"))
        if merged.empty:
            rows.append(
                {
                    "candidate": f"{model}/{policy}",
                    "baseline": f"{baseline_model}/{baseline_policy}",
                    "status": "missing",
                    "n_days": 0,
                    "n_seeds": 0,
                    "n_seed_day_pairs": 0,
                }
            )
            continue
        diff = (merged["daily_cost_candidate"] - merged["daily_cost_baseline"]).to_numpy(dtype=np.float64)
        boot = np.empty(samples, dtype=np.float64)
        for index in range(samples):
            sampled = rng.integers(0, diff.size, size=diff.size)
            boot[index] = diff[sampled].mean()
        rows.append(
            {
                "candidate": f"{model}/{policy}",
                "baseline": f"{baseline_model}/{baseline_policy}",
                "status": "ok",
                "n_days": int(merged["day"].nunique()),
                "n_seeds": int(merged["seed"].nunique()),
                "n_seed_day_pairs": int(diff.size),
                "observed_delta": float(diff.mean()),
                "ci_low": float(np.quantile(boot, 0.025)),
                "ci_high": float(np.quantile(boot, 0.975)),
                "prob_candidate_lower": float((boot < 0.0).mean()),
            }
        )
    return pd.DataFrame(rows)


def _write_outputs(
    *,
    output_dir: Path,
    summary: pd.DataFrame,
    by_ratio: pd.DataFrame,
    by_bin: pd.DataFrame,
    bootstrap_df: pd.DataFrame,
    raw_df: pd.DataFrame,
    bin_df: pd.DataFrame,
    daily_df: pd.DataFrame,
    gate_loss_df: pd.DataFrame,
    config: dict[str, Any],
) -> None:
    summary.to_csv(output_dir / "reserve_decision_summary.csv", index=False)
    by_ratio.to_csv(output_dir / "reserve_decision_by_ratio.csv", index=False)
    by_bin.to_csv(output_dir / "reserve_decision_by_risk_bin.csv", index=False)
    bootstrap_df.to_csv(output_dir / "reserve_decision_bootstrap.csv", index=False)
    raw_df.to_csv(output_dir / "reserve_decision_raw_runs.csv", index=False)
    bin_df.to_csv(output_dir / "reserve_decision_raw_bins.csv", index=False)
    daily_df.to_csv(output_dir / "reserve_decision_daily_costs.csv", index=False)
    gate_loss_df.to_csv(output_dir / "reserve_decision_gate_loss.csv", index=False)
    save_json(output_dir / "reserve_decision_config.json", config)


def run_reserve_decision_guard(
    *,
    decision_dir: Path | str,
    output_dir: Path | str,
    required_models: str | list[str] | tuple[str, ...] = RESERVE_REQUIRED_MODELS,
    required_seeds: str | list[int] | tuple[int, ...] = RESERVE_REQUIRED_SEEDS,
    gated_models: str | list[str] | tuple[str, ...] = RESERVE_GATED_MODELS,
    required_bootstrap_candidates: str | list[str] | tuple[str, ...] = RESERVE_REQUIRED_BOOTSTRAP_CANDIDATES,
    min_bootstrap_rows: int = len(RESERVE_REQUIRED_BOOTSTRAP_CANDIDATES),
    min_seed_day_pairs: int = 5,
) -> Path:
    decision_path = Path(decision_dir)
    out_dir = ensure_dir(output_dir)
    model_list = _parse_strings(required_models)
    seed_list = _parse_ints(required_seeds)
    gated_set = set(_parse_strings(gated_models))
    candidate_list = _parse_strings(required_bootstrap_candidates)

    file_status = {name: (decision_path / name).exists() for name in RESERVE_DECISION_REQUIRED_FILES}
    summary = _read_csv_if_exists(decision_path / "reserve_decision_summary.csv")
    raw = _read_csv_if_exists(decision_path / "reserve_decision_raw_runs.csv")
    daily = _read_csv_if_exists(decision_path / "reserve_decision_daily_costs.csv")
    gate_loss = _read_csv_if_exists(decision_path / "reserve_decision_gate_loss.csv")
    bootstrap = _read_csv_if_exists(decision_path / "reserve_decision_bootstrap.csv")
    config_path = decision_path / "reserve_decision_config.json"
    config = load_json(config_path) if config_path.exists() else {}
    main_ratio = float(config.get("main_ratio", DEFAULT_MAIN_RATIO)) if config else DEFAULT_MAIN_RATIO

    selected_pairs = {
        (str(row.get("model", "")), int(row.get("seed", -1)))
        for row in config.get("selected_runs", [])
        if _is_int_like(row.get("seed", None))
    }
    required_pairs = {(model, int(seed)) for model in model_list for seed in seed_list}
    missing_pairs = sorted(f"{model} seed {seed}" for model, seed in required_pairs.difference(selected_pairs))

    applicable_policy_requirements: list[tuple[str, str]] = []
    row_policy_requirements: list[tuple[str, str]] = []
    for model in model_list:
        for policy in POLICIES:
            row_policy_requirements.append((model, policy))
            if policy != "gate-bin" or model in gated_set:
                applicable_policy_requirements.append((model, policy))

    raw_main = pd.DataFrame()
    if not raw.empty and {"model", "policy", "subset", "cost_ratio", "status"}.issubset(raw.columns):
        raw_main = raw[
            raw["subset"].astype(str).eq("full")
            & np.isclose(pd.to_numeric(raw["cost_ratio"], errors="coerce").astype(float), main_ratio)
        ].copy()
    missing_policy_rows = _missing_model_policy_pairs(raw_main, row_policy_requirements, require_applicable=False)
    missing_applicable_rows = _missing_model_policy_pairs(raw_main, applicable_policy_requirements, require_applicable=True)

    metric_cols = ["total_cost_mean", "violation_rate_mean", "reserve_energy_mean", "shortage_energy_mean"]
    summary_missing_metrics: list[str] = []
    summary_for_metric_check = summary.copy()
    if not summary_for_metric_check.empty and "subset" in summary_for_metric_check:
        summary_for_metric_check = summary_for_metric_check[summary_for_metric_check["subset"].astype(str).eq("full")].copy()
    if not summary_for_metric_check.empty and "cost_ratio" in summary_for_metric_check:
        summary_for_metric_check = summary_for_metric_check[
            np.isclose(pd.to_numeric(summary_for_metric_check["cost_ratio"], errors="coerce").astype(float), main_ratio)
        ].copy()
    if summary_for_metric_check.empty or not {"model", "policy", "status"}.issubset(summary_for_metric_check.columns):
        summary_missing_metrics = [f"{model}/{policy}" for model, policy in applicable_policy_requirements]
    else:
        for model, policy in applicable_policy_requirements:
            subset = summary_for_metric_check[
                summary_for_metric_check["model"].astype(str).eq(model)
                & summary_for_metric_check["policy"].astype(str).eq(policy)
                & summary_for_metric_check["status"].astype(str).eq("applicable")
            ]
            if subset.empty:
                summary_missing_metrics.append(f"{model}/{policy}")
                continue
            row = subset.iloc[0]
            for metric in metric_cols:
                value = pd.to_numeric(pd.Series([row.get(metric)]), errors="coerce").iloc[0]
                if pd.isna(value):
                    summary_missing_metrics.append(f"{model}/{policy}:{metric}")

    bootstrap_ok = pd.DataFrame()
    missing_bootstrap_candidates: list[str] = []
    if not bootstrap.empty and {"candidate", "status"}.issubset(bootstrap.columns):
        bootstrap_ok = bootstrap[bootstrap["status"].astype(str).eq("ok")].copy()
        for candidate in candidate_list:
            subset = bootstrap_ok[bootstrap_ok["candidate"].astype(str).eq(candidate)]
            if subset.empty:
                missing_bootstrap_candidates.append(candidate)
    else:
        missing_bootstrap_candidates = list(candidate_list)
    seed_day_values = (
        pd.to_numeric(bootstrap_ok.get("n_seed_day_pairs"), errors="coerce").dropna()
        if "n_seed_day_pairs" in bootstrap_ok
        else pd.Series(dtype=float)
    )
    seed_values = (
        pd.to_numeric(bootstrap_ok.get("n_seeds"), errors="coerce").dropna()
        if "n_seeds" in bootstrap_ok
        else pd.Series(dtype=float)
    )
    ci_present = bool(
        not bootstrap_ok.empty
        and {"ci_low", "ci_high", "prob_candidate_lower"}.issubset(bootstrap_ok.columns)
        and bootstrap_ok[["ci_low", "ci_high", "prob_candidate_lower"]].apply(pd.to_numeric, errors="coerce").notna().all().all()
    )
    daily_pairs = set()
    if not daily.empty and {"model", "policy", "seed", "day", "cost_ratio"}.issubset(daily.columns):
        daily_main = daily[np.isclose(pd.to_numeric(daily["cost_ratio"], errors="coerce").astype(float), main_ratio)].copy()
        daily_pairs = set(zip(daily_main["model"].astype(str), daily_main["policy"].astype(str), daily_main["seed"].astype(int)))
    required_daily = {(model, policy, int(seed)) for model, policy in applicable_policy_requirements for seed in seed_list}
    missing_daily_pairs = sorted(f"{model}/{policy} seed {seed}" for model, policy, seed in required_daily.difference(daily_pairs))
    required_strata = set(_normalize_strata(config.get("strata", []))) if config else set()
    raw_subsets = set(raw.get("subset", pd.Series(dtype=str)).dropna().astype(str).tolist()) if not raw.empty else set()
    missing_strata = sorted(stratum for stratum in required_strata if stratum not in raw_subsets)
    gate_loss_missing_metrics: list[str] = []
    if gate_loss.empty or not {"gate_correctness", "total_cost", "violation_rate", "reserve_energy", "shortage_energy"}.issubset(
        gate_loss.columns
    ):
        gate_loss_missing_metrics.append("reserve_decision_gate_loss.csv:required_columns")
    else:
        for label in ["gate_correct", "gate_wrong"]:
            subset = gate_loss[gate_loss["gate_correctness"].astype(str).eq(label)]
            if subset.empty:
                gate_loss_missing_metrics.append(label)
                continue
            for metric in ["total_cost", "violation_rate", "reserve_energy", "shortage_energy"]:
                if pd.to_numeric(subset[metric], errors="coerce").notna().sum() == 0:
                    gate_loss_missing_metrics.append(f"{label}:{metric}")

    checks = {
        "all_required_files_exist": all(file_status.values()),
        "selected_runs_cover_required_5_seeds": not missing_pairs and bool(required_pairs),
        "raw_runs_cover_required_policies": not missing_policy_rows,
        "gated_policies_are_applicable": not missing_applicable_rows,
        "summary_has_total_cost_violation_reserve_and_shortage_energy": not summary_missing_metrics,
        "requested_strata_present": not missing_strata,
        "gate_correctness_operational_loss_present": not gate_loss_missing_metrics,
        "daily_costs_cover_required_seed_policy_pairs": not missing_daily_pairs,
        "paired_bootstrap_rows_at_least_min": int(len(bootstrap_ok)) >= int(min_bootstrap_rows),
        "paired_bootstrap_required_candidates_present": not missing_bootstrap_candidates,
        "paired_bootstrap_ci_present": ci_present,
        "paired_bootstrap_uses_seed_day_pairs": bool(
            not seed_day_values.empty
            and int(seed_day_values.min()) >= int(min_seed_day_pairs)
            and not seed_values.empty
            and int(seed_values.min()) >= min(len(seed_list), 1)
        ),
    }
    status = "complete_ready_for_reserve_decision_evidence" if all(checks.values()) else "blocked_reserve_decision_evidence"
    report = {
        "status": status,
        "checks": checks,
        "decision_dir": str(decision_path),
        "required_models": model_list,
        "required_seeds": seed_list,
        "required_policies": list(POLICIES),
        "gated_models": sorted(gated_set),
        "required_bootstrap_candidates": candidate_list,
        "main_ratio": main_ratio,
        "file_status": file_status,
        "missing_model_seed_pairs": missing_pairs,
        "missing_policy_rows": missing_policy_rows,
        "missing_applicable_policy_rows": missing_applicable_rows,
        "summary_missing_metrics": summary_missing_metrics,
        "missing_strata": missing_strata,
        "gate_loss_missing_metrics": gate_loss_missing_metrics,
        "missing_daily_seed_policy_pairs": missing_daily_pairs,
        "missing_bootstrap_candidates": missing_bootstrap_candidates,
        "n_bootstrap_ok_rows": int(len(bootstrap_ok)),
        "min_seed_day_pairs": int(seed_day_values.min()) if not seed_day_values.empty else 0,
        "min_bootstrap_seeds": int(seed_values.min()) if not seed_values.empty else 0,
    }
    save_json(out_dir / "reserve_decision_guard.json", report)
    pd.DataFrame([{"check": key, "passed": value} for key, value in checks.items()]).to_csv(
        out_dir / "reserve_decision_guard_checks.csv",
        index=False,
    )
    return out_dir


def _read_csv_if_exists(path: Path) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def _is_int_like(value: Any) -> bool:
    try:
        int(value)
        return True
    except (TypeError, ValueError):
        return False


def _parse_strings(values: str | list[str] | tuple[str, ...]) -> list[str]:
    if isinstance(values, str):
        return [token.strip() for token in values.split(",") if token.strip()]
    return [str(value).strip() for value in values if str(value).strip()]


def _parse_ints(values: str | list[int] | tuple[int, ...]) -> list[int]:
    if isinstance(values, str):
        return [int(token.strip()) for token in values.split(",") if token.strip()]
    return [int(value) for value in values]


def _missing_model_policy_pairs(
    frame: pd.DataFrame,
    required_pairs: list[tuple[str, str]],
    *,
    require_applicable: bool,
) -> list[str]:
    if frame.empty or not {"model", "policy", "status"}.issubset(frame.columns):
        return [f"{model}/{policy}" for model, policy in required_pairs]
    missing = []
    for model, policy in required_pairs:
        subset = frame[frame["model"].astype(str).eq(model) & frame["policy"].astype(str).eq(policy)].copy()
        if require_applicable:
            subset = subset[subset["status"].astype(str).eq("applicable")]
        if subset.empty:
            missing.append(f"{model}/{policy}")
    return missing


def _make_plots(output_dir: Path, by_ratio: pd.DataFrame, by_bin: pd.DataFrame, main_ratio: float) -> None:
    import matplotlib.pyplot as plt

    applicable = by_ratio[(by_ratio["status"] == "applicable") & (by_ratio["subset"] == "full")].copy()
    if not applicable.empty:
        fig, ax = plt.subplots(figsize=(8, 5))
        for (model, policy), group in applicable.groupby(["model", "policy"]):
            label = f"{model} / {policy}"
            ax.plot(group["cost_ratio"], group["total_cost_mean"], marker="o", linewidth=1.5, label=label)
        ax.set_xlabel("Shortage penalty / reserve cost")
        ax.set_ylabel("Mean total cost across runs")
        ax.set_title("Reserve-decision cost sensitivity")
        ax.grid(True, alpha=0.25)
        ax.legend(fontsize=7, ncol=2)
        fig.tight_layout()
        fig.savefig(output_dir / "reserve_cost_sensitivity.png", dpi=180)
        plt.close(fig)

        main = applicable[np.isclose(applicable["cost_ratio"].astype(float), float(main_ratio))]
        fig, ax = plt.subplots(figsize=(7, 5))
        ax.scatter(main["mean_reserve_mean"], main["violation_rate_mean"], s=50)
        for _, row in main.iterrows():
            ax.annotate(f"{row['model']}\n{row['policy']}", (row["mean_reserve_mean"], row["violation_rate_mean"]), fontsize=7)
        ax.set_xlabel("Mean reserve")
        ax.set_ylabel("Violation rate")
        ax.set_title("Reserve amount versus shortage risk")
        ax.grid(True, alpha=0.25)
        fig.tight_layout()
        fig.savefig(output_dir / "reserve_tradeoff.png", dpi=180)
        plt.close(fig)

    high = by_bin[
        (by_bin["status"] == "applicable")
        & (by_bin["subset"] == "full")
        & np.isclose(by_bin["cost_ratio"].astype(float), float(main_ratio))
        & (by_bin["risk_bin"] == "high")
    ].copy()
    if not high.empty:
        high["label"] = high["model"] + "\n" + high["policy"]
        high = high.sort_values("total_cost_mean")
        fig, ax = plt.subplots(figsize=(9, 5))
        ax.bar(high["label"], high["total_cost_mean"])
        ax.set_ylabel("High-risk bin total cost")
        ax.set_title("High-risk reserve-decision cost")
        ax.tick_params(axis="x", labelrotation=65, labelsize=7)
        fig.tight_layout()
        fig.savefig(output_dir / "reserve_high_risk_cost.png", dpi=180)
        plt.close(fig)
