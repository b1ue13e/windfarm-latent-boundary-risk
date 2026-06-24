from __future__ import annotations

from pathlib import Path
from typing import Any
import shutil

import numpy as np
import pandas as pd

from .config import EvalConfig, ModelConfig, TrainConfig
from .data import load_cache_bundle
from .train import train_model
from .utils import ensure_dir, load_json, save_json


ANCHOR_STRESS_VARIANTS = ("no_patv", "lagged_patv", "no_pab_mean", "lagged_pab_wspd")


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
) -> Path:
    suite = Path(suite_root)
    cache = Path(cache_root)
    out_dir = ensure_dir(output_dir)
    variant_list = _parse_variants(variants)
    seed_list = _parse_seeds(seeds)

    rows: list[dict[str, Any]] = []
    for variant in variant_list:
        for seed in seed_list:
            run_dir = suite / variant / f"wtb_bal_align_force_seed{seed}"
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
    limit_train_batches: int | None = None,
    limit_val_batches: int | None = None,
    skip_visuals: bool = True,
    resume: bool = True,
) -> Path:
    cache_root = Path(cache_root)
    out_root = ensure_dir(output_root)
    variant_list = _parse_variants(variants)
    seed_list = _parse_seeds(seeds)

    rows: list[dict[str, Any]] = []
    for variant in variant_list:
        cache_dir = _resolve_variant_cache(cache_root, variant)
        bundle = load_cache_bundle(cache_dir, mmap_mode=None)
        for seed in seed_list:
            run_dir = out_root / variant / f"wtb_bal_align_force_seed{seed}"
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
                mode="moe_full_no_aux",
                epochs=int(epochs),
                batch_size=int(batch_size),
                learning_rate=float(learning_rate),
                weight_decay=float(weight_decay),
                patience=int(patience),
                seed=int(seed),
                align_weight=5000.0,
                aux_weight=0.0,
                smooth_weight=0.0,
                balance_weight=1000.0,
                physics_force_weight=10000.0,
                limit_train_batches=limit_train_batches,
                limit_val_batches=limit_val_batches,
                label=f"anchor_stress_{variant}_seed{seed}",
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
                    "variant_key": "bal_align_force",
                    "experiment_group": "anchor_stress",
                    "anchor_stress_variant": variant,
                    "cache_dir": str(cache_dir),
                    "model_mode": "moe_full_no_aux",
                    "label": "MoE + L_bal + L_align + L_force",
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
            "policy": (
                "Train the boundary-forced WTB router on derived issue-time anchor-observability caches. "
                "Runs are written under <output_root>/<variant>/wtb_bal_align_force_seed<seed> for guard reuse."
            ),
        },
    )
    return out_root


def _copy_cache(source: Path, target: Path) -> None:
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target)


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
