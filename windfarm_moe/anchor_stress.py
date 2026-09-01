from __future__ import annotations

from pathlib import Path
from typing import Any
import shutil

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score

from .config import EvalConfig, ModelConfig, TrainConfig
from .data import load_cache_bundle
from .regimes import compute_wtb_operation_regime
from .train import train_model
from .utils import ensure_dir, load_json, save_json


ANCHOR_STRESS_VARIANTS = (
    "no_patv",
    "lagged_patv",
    "no_pab_mean",
    "lagged_pab_wspd",
    "signature_full",
    "signature_core",
)
DEFAULT_ANCHOR_STRESS_RUN_PREFIX = "wtb_bal_align_force_seed"


def build_anchor_stress_caches(
    *,
    source_cache_dir: Path | str,
    output_cache_root: Path | str,
    variants: list[str] | tuple[str, ...] | str | None = None,
) -> Path:
    source = Path(source_cache_dir)
    output_root = ensure_dir(output_cache_root)
    variant_list = _parse_variants(variants)
    metadata = load_json(source / "metadata.json")
    for variant in variant_list:
        target = output_root / f"{source.name}_{variant}"
        if _cache_variant_ready(target, variant):
            continue
        _copy_cache(source, target)
        _apply_variant(target, variant, metadata)
    save_json(
        output_root / "anchor_stress_cache_manifest.json",
        {
            "source_cache_dir": str(source),
            "variants": variant_list,
            "policy": (
                "Derived caches alter only issue-time anchor observability channels. "
                "Future target arrays are not changed."
            ),
            "variant_dirs": {variant: str(output_root / f"{source.name}_{variant}") for variant in variant_list},
        },
    )
    return output_root


def run_anchor_stress_guard(
    *,
    suite_root: Path | str,
    cache_root: Path | str,
    output_dir: Path | str,
    variants: list[str] | tuple[str, ...] | str | None = None,
    seeds: list[int] | tuple[int, ...] | str | None = None,
    min_nmi: float = 0.65,
    run_prefix: str = DEFAULT_ANCHOR_STRESS_RUN_PREFIX,
) -> Path:
    suite = Path(suite_root)
    cache = Path(cache_root)
    out_dir = ensure_dir(output_dir)
    variant_list = _parse_variants(variants)
    seed_list = _parse_seeds(seeds)

    rows: list[dict[str, Any]] = []
    for variant in variant_list:
        for seed in seed_list:
            run_dir = suite / variant / f"{run_prefix}{seed}"
            rows.append(_run_status_row(run_dir, variant, seed))
    status_df = pd.DataFrame(rows)
    status_df.to_csv(out_dir / "anchor_stress_run_status.csv", index=False)

    summary = _summary_rows(status_df, min_nmi=float(min_nmi))
    summary.to_csv(out_dir / "anchor_stress_summary.csv", index=False)
    _write_latex_table(summary, out_dir / "anchor_stress_summary.tex")

    cache_rows = _cache_status_rows(cache, variant_list)
    pd.DataFrame(cache_rows).to_csv(out_dir / "anchor_stress_cache_status.csv", index=False)

    complete = bool(not summary.empty and summary["all_requested_runs_complete"].astype(bool).all())
    leakage_pass = bool(not summary.empty and summary["leakage_guard_pass"].astype(bool).all())
    nmi_pass = bool(not summary.empty and summary["nmi_gate_pass"].astype(bool).all())
    if not complete:
        status = "ready_to_execute_anchor_stress_training"
    elif not leakage_pass:
        status = "blocked_anchor_stress_leakage_guard_failed"
    elif nmi_pass:
        status = "complete_anchor_stress_supports_partial_anchor_robustness"
    else:
        status = "complete_anchor_stress_requires_claim_downgrade"

    save_json(
        out_dir / "anchor_stress_guard.json",
        {
            "status": status,
            "variants": variant_list,
            "seeds": [int(seed) for seed in seed_list],
            "min_nmi": float(min_nmi),
            "run_prefix": str(run_prefix),
            "checks": {
                "all_requested_runs_complete": complete,
                "leakage_guard_pass": leakage_pass,
                "nmi_gate_pass": nmi_pass,
            },
            "claim_use": (
                "Training-level anchor-observability stress guard. If NMI drops below "
                "threshold or runs are incomplete, manuscript must use declared-anchor "
                "constrained routing language rather than learned physical discovery."
            ),
            "paths": {
                "run_status_csv": str(out_dir / "anchor_stress_run_status.csv"),
                "summary_csv": str(out_dir / "anchor_stress_summary.csv"),
                "cache_status_csv": str(out_dir / "anchor_stress_cache_status.csv"),
                "tex": str(out_dir / "anchor_stress_summary.tex"),
            },
        },
    )
    return out_dir


def run_anchor_stress_early_warning(
    *,
    suite_root: Path | str,
    output_dir: Path | str,
    variants: list[str] | tuple[str, ...] | str | None = None,
    seeds: list[int] | tuple[int, ...] | str | None = None,
    split: str = "test",
    early_window_steps: int = 6,
    pretrigger_steps: list[int] | tuple[int, ...] | str | None = None,
    delay_steps: list[int] | tuple[int, ...] | str | None = None,
    availability_rates: list[float] | tuple[float, ...] | str | None = None,
    noise_levels: list[tuple[float, float]] | tuple[tuple[float, float], ...] | str | None = None,
    random_seed: int = 1729,
    cut_in_wind: float = 3.0,
    rated_wind: float = 10.5,
    pitch_threshold: float = 2.0,
    min_delay_recall_gain: float = 0.15,
    min_low_availability_recall_gain: float = 0.20,
    max_availability_for_gain: float = 0.50,
    min_pretrigger_auc: float = 0.80,
) -> Path:
    suite = Path(suite_root)
    out_dir = ensure_dir(output_dir)
    variant_list = _parse_early_warning_variants(variants)
    seed_list = _parse_seeds(seeds)
    pre_steps = _parse_int_grid(pretrigger_steps, [1, 3, 6, 12])
    delay_grid = _parse_int_grid(delay_steps, [1, 3, 6])
    availability_grid = _parse_float_grid(availability_rates, [1.0, 0.75, 0.5, 0.25])
    noise_grid = _parse_noise_grid(noise_levels, [(0.25, 0.5), (0.5, 1.0), (1.0, 2.0)])

    raw_rows: list[dict[str, Any]] = []
    status_rows: list[dict[str, Any]] = []
    for variant in variant_list:
        for seed in seed_list:
            run_dir = _early_warning_run_dir(suite, variant, seed)
            metrics_dir = run_dir / f"{split}_metrics"
            required = ["gate_prob.npy", "regime_primary.npy", "regime_primary_valid.npy", "anchor_physics.npy"]
            missing = [name for name in required if not (metrics_dir / name).exists()]
            status_rows.append(
                {
                    "variant": variant,
                    "seed": int(seed),
                    "run_dir": str(run_dir),
                    "metrics_dir": str(metrics_dir),
                    "complete": not missing,
                    "missing_files": ",".join(missing),
                }
            )
            if missing:
                continue
            raw_rows.extend(
                _early_warning_rows_for_run(
                    variant=variant,
                    seed=int(seed),
                    run_dir=run_dir,
                    metrics_dir=metrics_dir,
                    split=split,
                    early_window_steps=int(early_window_steps),
                    pretrigger_steps=pre_steps,
                    delay_steps=delay_grid,
                    availability_rates=availability_grid,
                    noise_levels=noise_grid,
                    random_seed=int(random_seed),
                    cut_in_wind=float(cut_in_wind),
                    rated_wind=float(rated_wind),
                    pitch_threshold=float(pitch_threshold),
                )
            )

    status_df = pd.DataFrame(status_rows)
    raw_df = pd.DataFrame(raw_rows)
    summary_df = _summarize_early_warning(raw_df)

    status_df.to_csv(out_dir / "anchor_stress_early_warning_run_status.csv", index=False)
    raw_df.to_csv(out_dir / "anchor_stress_early_warning_raw.csv", index=False)
    summary_df.to_csv(out_dir / "anchor_stress_early_warning_summary.csv", index=False)
    _write_early_warning_latex(summary_df, out_dir / "anchor_stress_early_warning_summary.tex")

    expected_runs = int(len(variant_list) * len(seed_list))
    complete_runs = int(status_df["complete"].astype(bool).sum()) if not status_df.empty else 0
    delay_pass = _scenario_gain_pass(
        summary_df,
        scenario="label_delay",
        gain_col="recall_gain_mean",
        min_gain=float(min_delay_recall_gain),
    )
    availability_pass = _low_availability_gain_pass(
        summary_df,
        max_availability=float(max_availability_for_gain),
        min_gain=float(min_low_availability_recall_gain),
    )
    pretrigger_pass = _scenario_gain_pass(
        summary_df,
        scenario="pretrigger_ranking",
        gain_col="gate_roc_auc_mean",
        min_gain=float(min_pretrigger_auc),
    )
    noise_present = bool(not summary_df.empty and summary_df["scenario"].astype(str).eq("threshold_sensor_noise").any())
    checks = {
        "all_requested_runs_complete": complete_runs == expected_runs and expected_runs > 0,
        "delay_degradation_curve_nonempty": bool(
            not raw_df.empty and raw_df["scenario"].astype(str).eq("label_delay").any()
        ),
        "label_availability_curve_nonempty": bool(
            not raw_df.empty and raw_df["scenario"].astype(str).eq("label_availability").any()
        ),
        "gate_beats_delayed_threshold_labels": delay_pass,
        "gate_beats_low_availability_threshold_labels": availability_pass,
        "pretrigger_ranking_auc_passes": pretrigger_pass,
        "threshold_sensor_noise_curve_present": noise_present,
    }
    if not checks["all_requested_runs_complete"]:
        status = "ready_to_execute_anchor_stress_early_warning"
    elif checks["gate_beats_delayed_threshold_labels"] and checks["gate_beats_low_availability_threshold_labels"]:
        status = "complete_anchor_stress_supports_label_degradation_value"
    else:
        status = "complete_anchor_stress_needs_early_warning_claim_downgrade"

    save_json(
        out_dir / "anchor_stress_early_warning_guard.json",
        {
            "status": status,
            "variants": variant_list,
            "seeds": [int(seed) for seed in seed_list],
            "split": split,
            "early_window_steps": int(early_window_steps),
            "pretrigger_steps": pre_steps,
            "delay_steps": delay_grid,
            "availability_rates": availability_grid,
            "noise_levels": [[float(wspd), float(pab)] for wspd, pab in noise_grid],
            "thresholds": {
                "cut_in_wind": float(cut_in_wind),
                "rated_wind": float(rated_wind),
                "pitch_threshold": float(pitch_threshold),
                "min_delay_recall_gain": float(min_delay_recall_gain),
                "min_low_availability_recall_gain": float(min_low_availability_recall_gain),
                "max_availability_for_gain": float(max_availability_for_gain),
                "min_pretrigger_auc": float(min_pretrigger_auc),
            },
            "expected_runs": expected_runs,
            "complete_runs": complete_runs,
            "checks": checks,
            "claim_use": (
                "Post-hoc label-degradation audit for MPPT-to-pitch transition value. "
                "The citable claim is operational detection under delayed, missing, or noisy threshold labels, "
                "not a future-label predictor unless the pre-trigger ranking slice is cited separately."
            ),
            "paths": {
                "run_status_csv": str(out_dir / "anchor_stress_early_warning_run_status.csv"),
                "raw_csv": str(out_dir / "anchor_stress_early_warning_raw.csv"),
                "summary_csv": str(out_dir / "anchor_stress_early_warning_summary.csv"),
                "tex": str(out_dir / "anchor_stress_early_warning_summary.tex"),
                "guard_json": str(out_dir / "anchor_stress_early_warning_guard.json"),
            },
        },
    )
    _write_early_warning_readme(
        out_dir / "README.md",
        status=status,
        checks=checks,
        summary=summary_df,
    )
    return out_dir


def run_anchor_stress_training(
    *,
    cache_root: Path | str,
    output_root: Path | str,
    variants: list[str] | tuple[str, ...] | str | None = None,
    seeds: list[int] | tuple[int, ...] | str | None = None,
    epochs: int = 20,
    batch_size: int = 16,
    hidden_dim: int = 64,
    num_experts: int = 4,
    dropout: float = 0.1,
    tau: float = 0.7,
    learning_rate: float = 2e-3,
    weight_decay: float = 1e-4,
    patience: int = 5,
    num_workers: int = 0,
    limit_train_batches: int | None = None,
    limit_val_batches: int | None = None,
    skip_visuals: bool = True,
    resume: bool = True,
    model_mode: str = "moe_full_no_aux",
    run_prefix: str = DEFAULT_ANCHOR_STRESS_RUN_PREFIX,
    label: str = "",
    align_weight: float = 5000.0,
    aux_weight: float | None = None,
    smooth_weight: float | None = None,
    balance_weight: float = 1000.0,
    physics_force_weight: float = 10000.0,
) -> Path:
    cache_root = Path(cache_root)
    out_root = ensure_dir(output_root)
    variant_list = _parse_variants(variants)
    seed_list = _parse_seeds(seeds)

    rows: list[dict[str, Any]] = []
    for variant in variant_list:
        cache_dir = _resolve_variant_cache(cache_root, variant)
        bundle = load_cache_bundle(cache_dir, mmap_mode=None)
        resolved_aux_weight = _default_anchor_aux_weight(model_mode, aux_weight)
        resolved_smooth_weight = _default_anchor_smooth_weight(model_mode, smooth_weight)
        resolved_label = label or _default_anchor_label(model_mode)
        resolved_variant_key = _default_anchor_variant_key(model_mode)
        for seed in seed_list:
            run_dir = out_root / variant / f"{run_prefix}{seed}"
            if resume and _run_status_row(run_dir, variant, seed)["complete"]:
                row = _run_status_row(run_dir, variant, seed)
                row["training_action"] = "skipped_existing_complete_run"
                rows.append(row)
                continue

            model_config = ModelConfig(
                hidden_dim=int(hidden_dim),
                num_experts=int(num_experts),
                dropout=float(dropout),
                tau=float(tau),
                primary_num_classes=int(bundle.metadata.get("primary_num_classes", 3)),
                gate_physics_dim=int(bundle.physics.shape[-1]),
            )
            train_config = TrainConfig(
                mode=str(model_mode),
                epochs=int(epochs),
                batch_size=int(batch_size),
                learning_rate=float(learning_rate),
                weight_decay=float(weight_decay),
                patience=int(patience),
                num_workers=int(num_workers),
                seed=int(seed),
                align_weight=float(align_weight),
                aux_weight=float(resolved_aux_weight),
                smooth_weight=float(resolved_smooth_weight),
                balance_weight=float(balance_weight),
                physics_force_weight=float(physics_force_weight),
                limit_train_batches=limit_train_batches,
                limit_val_batches=limit_val_batches,
                label=resolved_label,
            )
            eval_config = EvalConfig(
                skip_visuals=bool(skip_visuals),
                save_predictions=True,
                switch_window=3 * int(bundle.metadata.get("steps_per_hour", 6)),
            )
            result = train_model(bundle, run_dir, model_config, train_config, eval_config)
            result.update(
                {
                    "seed": int(seed),
                    "variant_key": resolved_variant_key,
                    "experiment_group": "anchor_stress",
                    "anchor_stress_variant": variant,
                    "cache_dir": str(cache_dir),
                    "model_mode": str(model_mode),
                    "label": resolved_label,
                    "loss_weights": train_config.effective_loss_weights(),
                }
            )
            save_json(run_dir / "training_summary.json", result)
            row = _run_status_row(run_dir, variant, seed)
            row["training_action"] = "trained"
            rows.append(row)

    manifest = pd.DataFrame(rows)
    manifest.to_csv(out_root / "anchor_stress_training_manifest.csv", index=False)
    save_json(
        out_root / "anchor_stress_training_manifest.json",
        {
            "cache_root": str(cache_root),
            "output_root": str(out_root),
            "variants": variant_list,
            "seeds": [int(seed) for seed in seed_list],
            "model_mode": str(model_mode),
            "run_prefix": str(run_prefix),
            "label": resolved_label if variant_list else str(label),
            "policy": (
                "Train the requested router on derived issue-time anchor-observability caches. "
                "Runs are written under <output_root>/<variant>/<run_prefix><seed> for guard reuse."
            ),
        },
    )
    return out_root


def _default_anchor_aux_weight(model_mode: str, value: float | None) -> float:
    if value is not None:
        return float(value)
    return 250.0 if str(model_mode) == "moe_phys_full" else 0.0


def _default_anchor_smooth_weight(model_mode: str, value: float | None) -> float:
    if value is not None:
        return float(value)
    return 0.05 if str(model_mode) == "moe_phys_full" else 0.0


def _default_anchor_label(model_mode: str) -> str:
    return "Physics-Aligned MoE" if str(model_mode) == "moe_phys_full" else "MoE + L_bal + L_align + L_force"


def _default_anchor_variant_key(model_mode: str) -> str:
    return "full" if str(model_mode) == "moe_phys_full" else "bal_align_force"


def _copy_cache(source: Path, target: Path) -> None:
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target)


def _early_warning_run_dir(suite: Path, variant: str, seed: int) -> Path:
    if variant == "canonical":
        return suite / f"wtb_bal_align_force_seed{seed}"
    return suite / variant / f"wtb_bal_align_force_seed{seed}"


def _early_warning_rows_for_run(
    *,
    variant: str,
    seed: int,
    run_dir: Path,
    metrics_dir: Path,
    split: str,
    early_window_steps: int,
    pretrigger_steps: list[int],
    delay_steps: list[int],
    availability_rates: list[float],
    noise_levels: list[tuple[float, float]],
    random_seed: int,
    cut_in_wind: float,
    rated_wind: float,
    pitch_threshold: float,
) -> list[dict[str, Any]]:
    gate_prob = np.asarray(np.load(metrics_dir / "gate_prob.npy", mmap_mode="r"), dtype=np.float64)
    regime = np.asarray(np.load(metrics_dir / "regime_primary.npy", mmap_mode="r"), dtype=np.int16)
    valid = np.asarray(np.load(metrics_dir / "regime_primary_valid.npy", mmap_mode="r"), dtype=bool)
    physics = np.asarray(np.load(metrics_dir / "anchor_physics.npy", mmap_mode="r"), dtype=np.float64)
    gate_classes = max(1, min(int(gate_prob.shape[-1]), 3))
    gate_label = np.asarray(gate_prob[..., :gate_classes]).argmax(axis=-1).astype(np.int16)
    pitch_score = gate_prob[..., 2] if gate_prob.shape[-1] > 2 else (gate_label == 2).astype(np.float64)
    transitions = _mppt_to_pitch_transitions(regime, valid)
    early_pitch, transition_support = _early_pitch_window(
        regime,
        valid,
        transitions,
        early_window_steps=int(early_window_steps),
    )
    gate_pitch = gate_label == 2
    rows: list[dict[str, Any]] = []
    base = {
        "variant": variant,
        "seed": int(seed),
        "run_dir": str(run_dir),
        "split": split,
        "early_window_steps": int(early_window_steps),
        "n_mppt_to_pitch_transitions": int(transitions.sum()),
    }

    for delay in delay_steps:
        delayed = _delay_labels(regime, steps=int(delay), fill=0)
        delayed_valid = _delay_labels(valid.astype(np.int16), steps=int(delay), fill=0).astype(bool) & valid
        threshold_pitch = (delayed == 2) & delayed_valid
        rows.append(
            {
                **base,
                "scenario": "label_delay",
                "degradation_level": int(delay),
                "degradation_label": f"delay_steps={int(delay)}",
                **_detection_metrics(gate_pitch, threshold_pitch, early_pitch, transition_support),
            }
        )

    rng = np.random.default_rng(int(random_seed) + int(seed) * 1009 + _stable_variant_offset(variant))
    for rate in availability_rates:
        available = rng.random(regime.shape) < float(rate)
        threshold_pitch = (regime == 2) & valid & available
        rows.append(
            {
                **base,
                "scenario": "label_availability",
                "degradation_level": float(rate),
                "degradation_label": f"available_rate={float(rate):.2f}",
                **_detection_metrics(gate_pitch, threshold_pitch, early_pitch, transition_support),
            }
        )

    if physics.ndim >= 3 and physics.shape[-1] >= 2:
        wspd = np.asarray(physics[..., 0], dtype=np.float64)
        pab = np.asarray(physics[..., 1], dtype=np.float64)
        for idx, (wspd_sigma, pab_sigma) in enumerate(noise_levels):
            noise_rng = np.random.default_rng(
                int(random_seed) + int(seed) * 9173 + _stable_variant_offset(variant) + idx * 37
            )
            noisy_wspd = wspd + noise_rng.normal(0.0, float(wspd_sigma), size=wspd.shape)
            noisy_pab = pab + noise_rng.normal(0.0, float(pab_sigma), size=pab.shape)
            noisy_regime, noisy_valid_float = compute_wtb_operation_regime(
                noisy_wspd,
                noisy_pab,
                cut_in_wind=float(cut_in_wind),
                rated_wind=float(rated_wind),
                pitch_threshold=float(pitch_threshold),
            )
            threshold_pitch = (noisy_regime == 2) & noisy_valid_float.astype(bool) & valid
            rows.append(
                {
                    **base,
                    "scenario": "threshold_sensor_noise",
                    "degradation_level": float(wspd_sigma),
                    "degradation_label": f"wspd_sd={float(wspd_sigma):.2f};pab_sd={float(pab_sigma):.2f}",
                    "wspd_noise_sd": float(wspd_sigma),
                    "pab_noise_sd": float(pab_sigma),
                    **_detection_metrics(gate_pitch, threshold_pitch, early_pitch, transition_support),
                }
            )

    for steps in pretrigger_steps:
        pretrigger = _pretrigger_window(regime, valid, transitions, lead_steps=int(steps))
        mppt_support = valid & (regime == 1)
        y_true = (pretrigger & mppt_support).astype(np.int16)[mppt_support]
        score = np.asarray(pitch_score[mppt_support], dtype=np.float64)
        rows.append(
            {
                **base,
                "scenario": "pretrigger_ranking",
                "degradation_level": int(steps),
                "degradation_label": f"lead_steps={int(steps)}",
                "n_target_cells": int(y_true.sum()),
                "n_support_cells": int(y_true.size),
                "target_rate": float(y_true.mean()) if y_true.size else float("nan"),
                "gate_average_precision": _binary_average_precision(y_true, score),
                "gate_roc_auc": _binary_roc_auc(y_true, score),
                "gate_target_score_mean": _safe_mean_np(score[y_true.astype(bool)]),
                "gate_background_score_mean": _safe_mean_np(score[~y_true.astype(bool)]),
            }
        )
    return rows


def _mppt_to_pitch_transitions(regime: np.ndarray, valid: np.ndarray) -> np.ndarray:
    transitions = np.zeros_like(regime, dtype=bool)
    if regime.shape[0] < 2:
        return transitions
    changes = (regime[:-1] == 1) & (regime[1:] == 2) & valid[:-1] & valid[1:]
    transitions[1:] = changes
    return transitions


def _early_pitch_window(
    regime: np.ndarray,
    valid: np.ndarray,
    transitions: np.ndarray,
    *,
    early_window_steps: int,
) -> tuple[np.ndarray, np.ndarray]:
    target = np.zeros_like(regime, dtype=bool)
    support = np.zeros_like(regime, dtype=bool)
    num_steps = regime.shape[0]
    for row, node in np.argwhere(transitions):
        lo = max(0, int(row) - int(early_window_steps))
        hi = min(num_steps, int(row) + int(early_window_steps) + 1)
        target[int(row) : hi, int(node)] = True
        support[lo:hi, int(node)] = True
    target &= valid & (regime == 2)
    support &= valid & np.isin(regime, [1, 2])
    return target, support


def _pretrigger_window(
    regime: np.ndarray,
    valid: np.ndarray,
    transitions: np.ndarray,
    *,
    lead_steps: int,
) -> np.ndarray:
    target = np.zeros_like(regime, dtype=bool)
    for row, node in np.argwhere(transitions):
        lo = max(0, int(row) - int(lead_steps))
        hi = int(row)
        if lo < hi:
            target[lo:hi, int(node)] = True
    return target & valid & (regime == 1)


def _delay_labels(values: np.ndarray, *, steps: int, fill: int) -> np.ndarray:
    steps = max(0, int(steps))
    out = np.empty_like(values)
    if steps == 0:
        out[...] = values
        return out
    out[:steps] = fill
    out[steps:] = values[:-steps]
    return out


def _detection_metrics(
    gate_pitch: np.ndarray,
    threshold_pitch: np.ndarray,
    target: np.ndarray,
    support: np.ndarray,
) -> dict[str, Any]:
    gate = np.asarray(gate_pitch, dtype=bool)
    threshold = np.asarray(threshold_pitch, dtype=bool)
    target = np.asarray(target, dtype=bool)
    support = np.asarray(support, dtype=bool)
    gate_stats = _precision_recall(gate, target, support)
    threshold_stats = _precision_recall(threshold, target, support)
    return {
        "n_target_cells": int(target.sum()),
        "n_support_cells": int(support.sum()),
        "gate_positive_cells": int((gate & support).sum()),
        "threshold_positive_cells": int((threshold & support).sum()),
        "gate_recall": gate_stats["recall"],
        "threshold_recall": threshold_stats["recall"],
        "recall_gain": gate_stats["recall"] - threshold_stats["recall"],
        "gate_precision": gate_stats["precision"],
        "threshold_precision": threshold_stats["precision"],
        "precision_gain": gate_stats["precision"] - threshold_stats["precision"],
        "gate_f1": gate_stats["f1"],
        "threshold_f1": threshold_stats["f1"],
        "f1_gain": gate_stats["f1"] - threshold_stats["f1"],
    }


def _precision_recall(pred: np.ndarray, target: np.ndarray, support: np.ndarray) -> dict[str, float]:
    pred_support = pred & support
    true_positive = int((pred_support & target).sum())
    target_count = int(target.sum())
    pred_count = int(pred_support.sum())
    recall = float(true_positive / target_count) if target_count else float("nan")
    precision = float(true_positive / pred_count) if pred_count else float("nan")
    if np.isfinite(recall) and np.isfinite(precision) and (recall + precision) > 0:
        f1 = float(2.0 * recall * precision / (recall + precision))
    else:
        f1 = float("nan")
    return {"recall": recall, "precision": precision, "f1": f1}


def _summarize_early_warning(raw_df: pd.DataFrame) -> pd.DataFrame:
    group_cols = ["variant", "scenario", "degradation_label", "degradation_level"]
    metric_cols = [
        "n_mppt_to_pitch_transitions",
        "n_target_cells",
        "n_support_cells",
        "gate_recall",
        "threshold_recall",
        "recall_gain",
        "gate_precision",
        "threshold_precision",
        "precision_gain",
        "gate_f1",
        "threshold_f1",
        "f1_gain",
        "gate_average_precision",
        "gate_roc_auc",
        "target_rate",
        "gate_target_score_mean",
        "gate_background_score_mean",
    ]
    columns = group_cols + ["n_runs"] + [f"{col}_{suffix}" for col in metric_cols for suffix in ["mean", "std"]]
    if raw_df.empty:
        return pd.DataFrame(columns=columns)
    rows: list[dict[str, Any]] = []
    for keys, group in raw_df.groupby(group_cols, dropna=False, sort=False):
        row = {column: value for column, value in zip(group_cols, keys)}
        row["n_runs"] = int(group[["variant", "seed"]].drop_duplicates().shape[0])
        for column in metric_cols:
            if column not in group.columns:
                row[f"{column}_mean"] = float("nan")
                row[f"{column}_std"] = float("nan")
                continue
            values = pd.to_numeric(group[column], errors="coerce")
            row[f"{column}_mean"] = float(values.mean()) if values.notna().any() else float("nan")
            row[f"{column}_std"] = float(values.std(ddof=1)) if values.notna().sum() > 1 else 0.0
        rows.append(row)
    return pd.DataFrame(rows)


def _scenario_gain_pass(summary: pd.DataFrame, *, scenario: str, gain_col: str, min_gain: float) -> bool:
    if summary.empty or gain_col not in summary.columns:
        return False
    rows = summary[summary["scenario"].astype(str).eq(scenario)].copy()
    if rows.empty:
        return False
    values = pd.to_numeric(rows[gain_col], errors="coerce").dropna()
    return bool(not values.empty and float(values.min()) >= float(min_gain))


def _low_availability_gain_pass(
    summary: pd.DataFrame,
    *,
    max_availability: float,
    min_gain: float,
) -> bool:
    if summary.empty or "recall_gain_mean" not in summary.columns:
        return False
    rows = summary[summary["scenario"].astype(str).eq("label_availability")].copy()
    if rows.empty:
        return False
    levels = pd.to_numeric(rows["degradation_level"], errors="coerce")
    rows = rows[levels <= float(max_availability)].copy()
    if rows.empty:
        return False
    values = pd.to_numeric(rows["recall_gain_mean"], errors="coerce").dropna()
    return bool(not values.empty and float(values.min()) >= float(min_gain))


def _write_early_warning_latex(frame: pd.DataFrame, path: Path) -> None:
    lines = [
        r"\begin{table}[H]",
        r"\centering",
        r"\footnotesize",
        r"\setlength{\tabcolsep}{4pt}",
        r"\renewcommand{\arraystretch}{1.08}",
        r"\caption{Anchor-stress label-degradation audit for MPPT-to-pitch transition detection.}",
        r"\begin{tabular}{lllrrrr}",
        r"\toprule",
        r"Variant & Scenario & Degradation & Runs & Gate recall & Rule recall & Gain \\",
        r"\midrule",
    ]
    if not frame.empty:
        keep = frame[frame["scenario"].astype(str).isin(["label_delay", "label_availability", "threshold_sensor_noise"])]
        for _, row in keep.iterrows():
            lines.append(
                " & ".join(
                    [
                        str(row.get("variant", "")).replace("_", r"\_"),
                        str(row.get("scenario", "")).replace("_", r"\_"),
                        str(row.get("degradation_label", "")).replace("_", r"\_"),
                        str(int(row.get("n_runs", 0))),
                        _fmt_pm(row.get("gate_recall_mean"), row.get("gate_recall_std")),
                        _fmt_pm(row.get("threshold_recall_mean"), row.get("threshold_recall_std")),
                        _fmt_pm(row.get("recall_gain_mean"), row.get("recall_gain_std")),
                    ]
                )
                + r" \\"
            )
    lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}", ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_early_warning_readme(
    path: Path,
    *,
    status: str,
    checks: dict[str, Any],
    summary: pd.DataFrame,
) -> None:
    lines = [
        "# Anchor-stress early-warning audit",
        "",
        f"Status: `{status}`",
        "",
        "This audit compares saved gate assignments with degraded threshold-label baselines around MPPT-to-pitch transitions.",
        "It supports a conservative operational claim: gate value under delayed, missing, or noisy labels.",
        "",
        "## Checks",
        "",
    ]
    for key, value in checks.items():
        lines.append(f"- {key}: `{bool(value)}`")
    if not summary.empty:
        lines.extend(["", "## Summary", ""])
        display = summary[
            summary["scenario"].astype(str).isin(["label_delay", "label_availability", "threshold_sensor_noise"])
        ].copy()
        for _, row in display.iterrows():
            lines.append(
                "- "
                f"{row['variant']} / {row['scenario']} / {row['degradation_label']}: "
                f"gate recall {_fmt_float(row.get('gate_recall_mean'))}, "
                f"rule recall {_fmt_float(row.get('threshold_recall_mean'))}, "
                f"gain {_fmt_float(row.get('recall_gain_mean'))}"
            )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _parse_early_warning_variants(values: list[str] | tuple[str, ...] | str | None) -> list[str]:
    if values is None:
        return ["canonical"]
    if isinstance(values, str):
        parsed = [token.strip() for token in values.split(",") if token.strip()]
    else:
        parsed = [str(value).strip() for value in values if str(value).strip()]
    if not parsed:
        return ["canonical"]
    allowed = set(ANCHOR_STRESS_VARIANTS) | {"canonical"}
    unknown = sorted(set(parsed).difference(allowed))
    if unknown:
        raise ValueError(f"Unsupported early-warning variant(s): {unknown}. Available: {sorted(allowed)}")
    return parsed


def _parse_int_grid(values: list[int] | tuple[int, ...] | str | None, default: list[int]) -> list[int]:
    if values is None:
        parsed = list(default)
    elif isinstance(values, str):
        parsed = [int(token.strip()) for token in values.split(",") if token.strip()]
    else:
        parsed = [int(value) for value in values]
    return sorted({int(value) for value in parsed if int(value) >= 0})


def _parse_float_grid(values: list[float] | tuple[float, ...] | str | None, default: list[float]) -> list[float]:
    if values is None:
        parsed = list(default)
    elif isinstance(values, str):
        parsed = [float(token.strip()) for token in values.split(",") if token.strip()]
    else:
        parsed = [float(value) for value in values]
    return sorted({float(value) for value in parsed if 0.0 <= float(value) <= 1.0}, reverse=True)


def _parse_noise_grid(
    values: list[tuple[float, float]] | tuple[tuple[float, float], ...] | str | None,
    default: list[tuple[float, float]],
) -> list[tuple[float, float]]:
    if values is None:
        return list(default)
    if isinstance(values, str):
        parsed: list[tuple[float, float]] = []
        for token in values.split(","):
            token = token.strip()
            if not token:
                continue
            if ":" not in token:
                raise ValueError("Noise levels must use 'wspd_sd:pab_sd' entries separated by commas.")
            wspd, pab = token.split(":", 1)
            parsed.append((float(wspd.strip()), float(pab.strip())))
        return parsed
    return [(float(wspd), float(pab)) for wspd, pab in values]


def _binary_average_precision(y_true: np.ndarray, score: np.ndarray) -> float:
    y = np.asarray(y_true, dtype=np.int16)
    if y.size == 0 or np.unique(y).size < 2:
        return float("nan")
    return float(average_precision_score(y, np.asarray(score, dtype=np.float64)))


def _binary_roc_auc(y_true: np.ndarray, score: np.ndarray) -> float:
    y = np.asarray(y_true, dtype=np.int16)
    if y.size == 0 or np.unique(y).size < 2:
        return float("nan")
    return float(roc_auc_score(y, np.asarray(score, dtype=np.float64)))


def _safe_mean_np(values: np.ndarray) -> float:
    arr = np.asarray(values, dtype=np.float64)
    arr = arr[np.isfinite(arr)]
    return float(arr.mean()) if arr.size else float("nan")


def _stable_variant_offset(variant: str) -> int:
    return int(sum((idx + 1) * ord(char) for idx, char in enumerate(str(variant))))


def _fmt_float(value: Any, digits: int = 3) -> str:
    value_float = _num(value)
    return "NA" if not np.isfinite(value_float) else f"{value_float:.{digits}f}"


def _resolve_variant_cache(cache_root: Path, variant: str) -> Path:
    manifest_path = cache_root / "anchor_stress_cache_manifest.json"
    if manifest_path.exists():
        manifest = load_json(manifest_path)
        variant_dirs = manifest.get("variant_dirs", {})
        path = variant_dirs.get(variant) if isinstance(variant_dirs, dict) else None
        if path and _cache_variant_ready(Path(path), variant):
            return Path(path)
    matches = sorted(cache_root.glob(f"*_{variant}"))
    for match in matches:
        if _cache_variant_ready(match, variant):
            return match
    raise FileNotFoundError(
        f"Missing anchor-stress cache for variant '{variant}' under {cache_root}. "
        "Run `anchor-stress-cache` first."
    )


def _cache_variant_ready(cache_dir: Path, variant: str) -> bool:
    metadata_path = cache_dir / "metadata.json"
    if not metadata_path.exists():
        return False
    try:
        metadata = load_json(metadata_path)
    except Exception:
        return False
    required = ["features.npy", "feature_mask.npy", "physics.npy", "physics_model.npy"]
    return metadata.get("anchor_stress_variant") == variant and all((cache_dir / name).exists() for name in required)


def _apply_variant(cache_dir: Path, variant: str, source_metadata: dict[str, Any]) -> None:
    feature_names = [str(name) for name in source_metadata.get("feature_names", [])]
    physics_names = [str(name) for name in source_metadata.get("physics_names", [])]
    metadata = load_json(cache_dir / "metadata.json")
    metadata["anchor_stress_variant"] = variant
    metadata["anchor_stress_policy"] = _variant_description(variant)

    features = np.load(cache_dir / "features.npy")
    feature_mask = np.load(cache_dir / "feature_mask.npy")
    physics = np.load(cache_dir / "physics.npy")
    physics_model = np.load(cache_dir / "physics_model.npy")

    if variant == "no_patv":
        _zero_feature(features, feature_mask, feature_names, "Patv_hist")
        _zero_physics(physics, physics_model, physics_names, "Patv")
    elif variant == "lagged_patv":
        _lag_feature(features, feature_names, "Patv_hist")
        _lag_physics(physics, physics_model, physics_names, "Patv")
    elif variant == "no_pab_mean":
        _zero_feature(features, feature_mask, feature_names, "Pab_mean")
        _zero_feature(features, feature_mask, feature_names, "Pab_std")
        _zero_physics(physics, physics_model, physics_names, "Pab_mean")
    elif variant == "lagged_pab_wspd":
        _lag_feature(features, feature_names, "Pab_mean")
        _lag_feature(features, feature_names, "Pab_std")
        _lag_feature(features, feature_names, "Wspd")
        _lag_physics(physics, physics_model, physics_names, "Pab_mean")
        _lag_physics(physics, physics_model, physics_names, "Wspd")
    elif variant == "signature_full":
        # Remove the label-defining channels (Wspd, Pab_mean) from every
        # model-visible path: encoder features and the gate anchor. Raw
        # physics.npy is kept intact for evaluation/analysis only; the model
        # consumes physics_model.npy (see windfarm_moe/data.py).
        _zero_feature(features, feature_mask, feature_names, "Wspd")
        _zero_feature(features, feature_mask, feature_names, "Pab_mean")
        _zero_physics_model(physics_model, physics_names, "Wspd")
        _zero_physics_model(physics_model, physics_names, "Pab_mean")
    elif variant == "signature_core":
        # Strictest signature probe: additionally remove the power channel so
        # only non-power consequence channels remain (Pab_std, Prtv, wake,
        # directions, temperatures).
        _zero_feature(features, feature_mask, feature_names, "Wspd")
        _zero_feature(features, feature_mask, feature_names, "Pab_mean")
        _zero_feature(features, feature_mask, feature_names, "Patv_hist")
        _zero_physics_model(physics_model, physics_names, "Wspd")
        _zero_physics_model(physics_model, physics_names, "Pab_mean")
        _zero_physics_model(physics_model, physics_names, "Patv")
    else:
        raise ValueError(f"Unsupported anchor stress variant: {variant}")

    np.save(cache_dir / "features.npy", features.astype(np.float32))
    np.save(cache_dir / "feature_mask.npy", feature_mask.astype(np.float32))
    np.save(cache_dir / "physics.npy", physics.astype(np.float32))
    np.save(cache_dir / "physics_model.npy", physics_model.astype(np.float32))
    save_json(cache_dir / "metadata.json", metadata)


def _zero_feature(features: np.ndarray, mask: np.ndarray, names: list[str], name: str) -> None:
    if name not in names:
        return
    idx = names.index(name)
    features[..., idx] = 0.0
    mask[..., idx] = 0.0


def _zero_physics(physics: np.ndarray, physics_model: np.ndarray, names: list[str], name: str) -> None:
    if name not in names:
        return
    idx = names.index(name)
    physics[..., idx] = 0.0
    physics_model[..., idx] = 0.0


def _zero_physics_model(physics_model: np.ndarray, names: list[str], name: str) -> None:
    """Zero a model-facing gate-anchor channel while keeping raw physics intact.

    Signature variants must block model access to label-defining channels
    without corrupting evaluation artifacts (raw physics.npy is not consumed
    by the model).
    """
    if name not in names:
        return
    idx = names.index(name)
    physics_model[..., idx] = 0.0


def _lag_feature(features: np.ndarray, names: list[str], name: str) -> None:
    if name not in names:
        return
    idx = names.index(name)
    features[1:, :, idx] = features[:-1, :, idx]
    features[0, :, idx] = 0.0


def _lag_physics(physics: np.ndarray, physics_model: np.ndarray, names: list[str], name: str) -> None:
    if name not in names:
        return
    idx = names.index(name)
    physics[1:, :, idx] = physics[:-1, :, idx]
    physics[0, :, idx] = 0.0
    physics_model[1:, :, idx] = physics_model[:-1, :, idx]
    physics_model[0, :, idx] = 0.0


def _run_status_row(run_dir: Path, variant: str, seed: int) -> dict[str, Any]:
    summary_path = run_dir / "training_summary.json"
    metrics_path = run_dir / "test_metrics" / "metrics.json"
    summary = load_json(summary_path) if summary_path.exists() else {}
    metrics = load_json(metrics_path) if metrics_path.exists() else {}
    gate = metrics.get("gate_alignment", {}) if isinstance(metrics, dict) else {}
    leakage = metrics.get("leakage_guard", {}) if isinstance(metrics, dict) else {}
    if not leakage:
        leakage = summary.get("leakage_guard", {}) if isinstance(summary, dict) else {}
    complete = summary_path.exists() and metrics_path.exists() and "overall" in metrics and "gate_alignment" in metrics
    leakage_pass = bool(leakage.get("pass", True))
    return {
        "variant": variant,
        "seed": int(seed),
        "run_dir": str(run_dir),
        "summary_exists": summary_path.exists(),
        "metrics_exists": metrics_path.exists(),
        "complete": bool(complete),
        "leakage_guard_pass": leakage_pass,
        "overall_rmse": metrics.get("overall", {}).get("rmse"),
        "switch_rmse": metrics.get("switch_window", {}).get("rmse"),
        "nmi": gate.get("nmi"),
        "ari": gate.get("ari"),
        "claim_boundary": _claim_boundary(_num(gate.get("nmi")), leakage_pass),
    }


def _summary_rows(status_df: pd.DataFrame, *, min_nmi: float) -> pd.DataFrame:
    if status_df.empty:
        return pd.DataFrame()
    rows: list[dict[str, Any]] = []
    for variant, group in status_df.groupby("variant", dropna=False):
        nmi = pd.to_numeric(group["nmi"], errors="coerce")
        ari = pd.to_numeric(group["ari"], errors="coerce")
        complete = group["complete"].astype(bool)
        leakage = group["leakage_guard_pass"].astype(bool)
        nmi_mean = float(nmi.mean()) if nmi.notna().any() else np.nan
        rows.append(
            {
                "variant": variant,
                "n_requested_runs": int(len(group)),
                "n_complete_runs": int(complete.sum()),
                "all_requested_runs_complete": bool(complete.all() and len(group) > 0),
                "leakage_guard_pass": bool(leakage.all()),
                "nmi_mean": nmi_mean,
                "nmi_std": float(nmi.std(ddof=1)) if nmi.notna().sum() > 1 else 0.0,
                "ari_mean": float(ari.mean()) if ari.notna().any() else np.nan,
                "ari_std": float(ari.std(ddof=1)) if ari.notna().sum() > 1 else 0.0,
                "nmi_gate_pass": bool(np.isfinite(nmi_mean) and nmi_mean >= float(min_nmi)),
                "claim_boundary": _claim_boundary(nmi_mean, bool(leakage.all())),
            }
        )
    return pd.DataFrame(rows)


def _cache_status_rows(cache_root: Path, variants: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for variant in variants:
        matches = sorted(cache_root.glob(f"*_{variant}"))
        path = matches[0] if matches else cache_root / variant
        metadata_path = path / "metadata.json"
        metadata = load_json(metadata_path) if metadata_path.exists() else {}
        rows.append(
            {
                "variant": variant,
                "cache_dir": str(path),
                "metadata_exists": metadata_path.exists(),
                "variant_marker_matches": metadata.get("anchor_stress_variant") == variant,
            }
        )
    return rows


def _claim_boundary(nmi: float, leakage_pass: bool) -> str:
    if not leakage_pass:
        return "blocked_by_leakage_guard"
    if not np.isfinite(nmi):
        return "not_yet_citable"
    if nmi >= 0.65:
        return "partial_anchor_robustness_supported"
    return "downgrade_to_declared_anchor_constrained_routing"


def _variant_description(variant: str) -> str:
    return {
        "no_patv": "Zero Patv issue-time status channel in features and gate physics.",
        "lagged_patv": "Replace Patv issue-time status channel with one-step lag.",
        "no_pab_mean": "Zero pitch-angle issue-time anchor channels.",
        "lagged_pab_wspd": "Replace pitch-angle and wind-speed anchors with one-step lag.",
        "signature_full": (
            "Remove label-defining channels (Wspd, Pab_mean) from features and "
            "model-facing gate anchor; raw physics kept for evaluation only."
        ),
        "signature_core": (
            "signature_full plus removal of the power channel (Patv_hist, Patv "
            "anchor); only non-power consequence channels remain."
        ),
    }[variant]


def _parse_variants(values: list[str] | tuple[str, ...] | str | None) -> list[str]:
    if values is None:
        parsed = list(ANCHOR_STRESS_VARIANTS)
    elif isinstance(values, str):
        parsed = [token.strip() for token in values.split(",") if token.strip()]
    else:
        parsed = [str(value).strip() for value in values if str(value).strip()]
    unknown = sorted(set(parsed).difference(ANCHOR_STRESS_VARIANTS))
    if unknown:
        raise ValueError(f"Unsupported anchor stress variant(s): {unknown}. Available: {list(ANCHOR_STRESS_VARIANTS)}")
    return parsed


def _parse_seeds(values: list[int] | tuple[int, ...] | str | None) -> list[int]:
    if values is None:
        return [201, 202, 203]
    if isinstance(values, str):
        return [int(token.strip()) for token in values.split(",") if token.strip()]
    return [int(value) for value in values]


def _write_latex_table(frame: pd.DataFrame, path: Path) -> None:
    lines = [
        r"\begin{table}[H]",
        r"\centering",
        r"\footnotesize",
        r"\setlength{\tabcolsep}{5pt}",
        r"\renewcommand{\arraystretch}{1.08}",
        r"\caption{Training-level anchor-observability stress summary.}",
        r"\begin{tabular}{lrrrrl}",
        r"\toprule",
        r"Variant & Runs & NMI & ARI & Pass & Claim boundary \\",
        r"\midrule",
    ]
    if not frame.empty:
        for _, row in frame.iterrows():
            lines.append(
                " & ".join(
                    [
                        str(row["variant"]).replace("_", r"\_"),
                        f"{int(row['n_complete_runs'])}/{int(row['n_requested_runs'])}",
                        _fmt_pm(row.get("nmi_mean"), row.get("nmi_std")),
                        _fmt_pm(row.get("ari_mean"), row.get("ari_std")),
                        "yes" if bool(row.get("nmi_gate_pass")) else "no",
                        str(row.get("claim_boundary", "")).replace("_", r"\_"),
                    ]
                )
                + r" \\"
            )
    lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}", ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def _num(value: Any) -> float:
    out = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    return float(out) if pd.notna(out) else float("nan")


def _fmt_pm(mean: Any, std: Any) -> str:
    mean_value = _num(mean)
    std_value = _num(std)
    if not np.isfinite(mean_value):
        return "NA"
    if not np.isfinite(std_value):
        std_value = 0.0
    return f"{mean_value:.3f} $\\pm$ {std_value:.3f}"
