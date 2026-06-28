from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable
import json

import pandas as pd

from .config import DataConfig
from .strict_anchor import strict_anchor_mask_report
from .utils import ensure_dir, load_json, save_json


DEFAULT_BASELINE_VARIANTS = ("graph_wavenet", "graph_transformer", "gat_gru", "patchtst", "itransformer", "tide")
DEFAULT_STRICT_BASELINE_SEEDS = (201, 202, 203, 204, 205)

BASELINE_SPECS: dict[str, dict[str, str]] = {
    "stgcn": {"label": "STGCN", "mode": "baseline_stgcn"},
    "graph_wavenet": {"label": "Graph WaveNet", "mode": "baseline_graph_wavenet"},
    "graph_transformer": {"label": "Graph Transformer", "mode": "baseline_graph_transformer"},
    "gat_gru": {"label": "GAT-GRU", "mode": "baseline_gat_gru"},
    "patchtst": {"label": "PatchTST", "mode": "baseline_patchtst"},
    "itransformer": {"label": "iTransformer", "mode": "baseline_itransformer"},
    "tide": {"label": "TiDE", "mode": "baseline_tide"},
}


def _parse_variant_keys(values: Iterable[str] | str | None) -> list[str]:
    if values is None:
        return list(DEFAULT_BASELINE_VARIANTS)
    if isinstance(values, str):
        tokens = [token.strip() for token in values.split(",") if token.strip()]
    else:
        tokens = [str(token).strip() for token in values if str(token).strip()]
    unknown = sorted(set(tokens).difference(BASELINE_SPECS))
    if unknown:
        available = ", ".join(BASELINE_SPECS)
        raise ValueError(f"Unknown strict baseline variant(s): {', '.join(unknown)}. Available: {available}")
    return tokens


def _parse_seeds(values: Iterable[int] | str | None) -> list[int]:
    if values is None:
        return [int(seed) for seed in DEFAULT_STRICT_BASELINE_SEEDS]
    if isinstance(values, str):
        return [int(token.strip()) for token in values.split(",") if token.strip()]
    return [int(seed) for seed in values]


def _jsonable_bounds(bounds: dict[str, tuple[int, int]] | dict[str, list[int]]) -> dict[str, list[int]]:
    return {str(key): [int(value[0]), int(value[1])] for key, value in bounds.items()}


def _split_rows(config: DataConfig) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for split, bounds in config.split_bounds().items():
        start, end = int(bounds[0]), int(bounds[1])
        anchor_start = start + int(config.hist_len) - 1
        anchor_end = end - int(config.pred_len) - 1
        n_anchor_windows = max(anchor_end - anchor_start + 1, 0)
        rows.append(
            {
                "split": split,
                "step_start": start,
                "step_end_exclusive": end,
                "anchor_start": anchor_start if n_anchor_windows else None,
                "anchor_end": anchor_end if n_anchor_windows else None,
                "n_anchor_windows": n_anchor_windows,
            }
        )
    return rows


def _job_rows(suite_dir: Path, variant_keys: list[str], seeds: list[int]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for variant_key in variant_keys:
        spec = BASELINE_SPECS[variant_key]
        for seed in seeds:
            run_name = f"wtb_{variant_key}_seed{seed}"
            rows.append(
                {
                    "variant_key": variant_key,
                    "label": spec["label"],
                    "mode": spec["mode"],
                    "seed": int(seed),
                    "run_name": run_name,
                    "run_dir": str(Path(suite_dir) / run_name),
                    "expected_summary": str(Path(suite_dir) / run_name / "training_summary.json"),
                    "expected_metrics": str(Path(suite_dir) / run_name / "test_metrics" / "metrics.json"),
                }
            )
    return rows


def _command_lines(
    config: DataConfig,
    output_dir: Path,
    suite_dir: Path,
    variant_keys: list[str],
    seeds: list[int],
    epochs: int,
    batch_size: int,
    hidden_dim: int,
) -> list[str]:
    common = (
        f"--dataset wtb --root-dir {config.root_dir} --cache-root {config.cache_root} "
        f"--train-days {config.train_days} --val-days {config.val_days} --test-days {config.test_days} "
        f"--hist-len {config.hist_len} --pred-len {config.pred_len}"
    )
    seed_text = ",".join(str(seed) for seed in seeds)
    variant_text = ",".join(variant_keys)
    return [
        "python main.py strict-baseline-guard "
        f"{common} --protocol-dir {output_dir} --suite-dir {suite_dir} --output-dir {output_dir / 'guard'}",
        "python main.py paper-batch "
        f"{common} --output-dir {suite_dir} --groups strong_baselines --variant-keys {variant_text} "
        f"--seeds {seed_text} --strong-baseline-seeds {seed_text} "
        f"--epochs {int(epochs)} --batch-size {int(batch_size)} --hidden-dim {int(hidden_dim)} --skip-visuals",
        "python main.py strict-baseline-guard "
        f"{common} --protocol-dir {output_dir} --suite-dir {suite_dir} --output-dir {output_dir / 'guard_after_training'}",
    ]


def _run_complete_status(run_dir: Path, variant_key: str, seed: int) -> dict[str, Any]:
    summary_path = run_dir / "training_summary.json"
    metrics_path = run_dir / "test_metrics" / "metrics.json"
    summary = load_json(summary_path) if summary_path.exists() else {}
    metrics = load_json(metrics_path) if metrics_path.exists() else {}
    expected_mode = BASELINE_SPECS[variant_key]["mode"]
    checks = {
        "summary_exists": summary_path.exists(),
        "metrics_exists": metrics_path.exists(),
        "seed_matches": int(summary.get("seed", -1)) == int(seed) if summary else False,
        "variant_key_matches": str(summary.get("variant_key", "")) == variant_key if summary else False,
        "experiment_group_is_strong_baselines": str(summary.get("experiment_group", "")) == "strong_baselines"
        if summary
        else False,
        "model_mode_matches": str(summary.get("model_mode", "")) == expected_mode if summary else False,
        "overall_rmse_present": "overall" in metrics and "rmse" in metrics.get("overall", {}),
    }
    complete = all(checks.values())
    return {
        "variant_key": variant_key,
        "label": BASELINE_SPECS[variant_key]["label"],
        "mode": expected_mode,
        "seed": int(seed),
        "run_dir": str(run_dir),
        "complete": bool(complete),
        "checks": checks,
        "overall_rmse": metrics.get("overall", {}).get("rmse"),
        "switch_rmse": metrics.get("switch_window", {}).get("rmse"),
    }


def write_strict_baseline_protocol(
    output_dir: Path | str,
    root_dir: Path | str = ".",
    cache_root: str = "artifacts/cache_strictmask",
    suite_dir: Path | str = "artifacts/strictmask_baseline_rerun_wtb_full",
    train_days: int = 180,
    val_days: int = 30,
    test_days: int = 35,
    hist_len: int = 36,
    pred_len: int = 24,
    variant_keys: Iterable[str] | str | None = None,
    seeds: Iterable[int] | str | None = None,
    epochs: int = 20,
    batch_size: int = 16,
    hidden_dim: int = 64,
) -> Path:
    output_dir = ensure_dir(output_dir)
    suite_dir = Path(suite_dir)
    variant_key_list = _parse_variant_keys(variant_keys)
    seed_list = _parse_seeds(seeds)
    config = DataConfig(
        dataset="wtb",
        root_dir=Path(root_dir),
        cache_root=cache_root,
        train_days=int(train_days),
        val_days=int(val_days),
        test_days=int(test_days),
        hist_len=int(hist_len),
        pred_len=int(pred_len),
    )
    split_rows = _split_rows(config)
    jobs = _job_rows(suite_dir, variant_key_list, seed_list)
    pd.DataFrame(split_rows).to_csv(output_dir / "strict_baseline_split.csv", index=False)
    pd.DataFrame(jobs).to_csv(output_dir / "strict_baseline_jobs.csv", index=False)
    commands = _command_lines(
        config=config,
        output_dir=output_dir,
        suite_dir=suite_dir,
        variant_keys=variant_key_list,
        seeds=seed_list,
        epochs=epochs,
        batch_size=batch_size,
        hidden_dim=hidden_dim,
    )
    (output_dir / "strict_baseline_commands.ps1").write_text("\n".join(commands) + "\n", encoding="utf-8")
    protocol = {
        "status": "protocol_only_not_executed",
        "dataset": "wtb",
        "purpose": "Fair strict-cache rerun protocol for WTB strong forecasting baselines.",
        "claim_supported_after_execution": "strict-cache cross-family WTB forecasting comparison",
        "claim_not_supported_until_execution": "strict-cache leaderboard or accuracy-dominance claim",
        "cache_policy": {
            "cache_root": cache_root,
            "cache_dir": str(config.cache_dir()),
            "required_metadata_marker": "strict_anchor_mask_patch",
            "required_anchor_violation_count": 0,
        },
        "split_policy": {
            "train_days": int(train_days),
            "val_days": int(val_days),
            "test_days": int(test_days),
            "total_days": int(config.total_days()),
            "hist_len": int(hist_len),
            "pred_len": int(pred_len),
            "bounds": config.split_bounds(),
        },
        "baselines": [
            {"variant_key": key, "label": BASELINE_SPECS[key]["label"], "mode": BASELINE_SPECS[key]["mode"]}
            for key in variant_key_list
        ],
        "seeds": [int(seed) for seed in seed_list],
        "training": {"epochs": int(epochs), "batch_size": int(batch_size), "hidden_dim": int(hidden_dim)},
        "outputs": {
            "suite_dir": str(suite_dir),
            "split_csv": str(output_dir / "strict_baseline_split.csv"),
            "jobs_csv": str(output_dir / "strict_baseline_jobs.csv"),
            "commands_ps1": str(output_dir / "strict_baseline_commands.ps1"),
        },
    }
    save_json(output_dir / "strict_baseline_protocol.json", protocol)
    lines = [
        "# Strict-cache strong-baseline rerun protocol",
        "",
        "Status: `protocol_only_not_executed`.",
        "",
        "This artifact freezes the fair WTB strong-baseline rerun plan. It is not evidence that the rerun has passed.",
        "",
        "## Baselines",
        "",
    ]
    for key in variant_key_list:
        lines.append(f"- {BASELINE_SPECS[key]['label']} (`{key}`), seeds {', '.join(str(seed) for seed in seed_list)}.")
    lines.extend(
        [
            "",
            "## Guard Conditions",
            "",
            "- The cache metadata must match the requested WTB split.",
            "- The cache must carry the `strict_anchor_mask_patch` marker.",
            "- Full-cache anchor-mask verification must report zero strict-anchor violations.",
            "- Every expected baseline run must have matching `training_summary.json` and `test_metrics/metrics.json`.",
            "",
            "## Commands",
            "",
            "```powershell",
            *commands,
            "```",
            "",
        ]
    )
    (output_dir / "README.md").write_text("\n".join(lines), encoding="utf-8")
    return output_dir


def run_strict_baseline_guard(
    protocol_dir: Path | str,
    output_dir: Path | str,
    root_dir: Path | str = ".",
    cache_root: str = "artifacts/cache_strictmask",
    suite_dir: Path | str = "artifacts/strictmask_baseline_rerun_wtb_full",
    train_days: int = 180,
    val_days: int = 30,
    test_days: int = 35,
    hist_len: int = 36,
    pred_len: int = 24,
    variant_keys: Iterable[str] | str | None = None,
    seeds: Iterable[int] | str | None = None,
) -> Path:
    protocol_dir = Path(protocol_dir)
    output_dir = ensure_dir(output_dir)
    suite_dir = Path(suite_dir)
    config = DataConfig(
        dataset="wtb",
        root_dir=Path(root_dir),
        cache_root=cache_root,
        train_days=int(train_days),
        val_days=int(val_days),
        test_days=int(test_days),
        hist_len=int(hist_len),
        pred_len=int(pred_len),
    )
    protocol_path = protocol_dir / "strict_baseline_protocol.json"
    protocol = load_json(protocol_path) if protocol_path.exists() else {}
    protocol_variants = [row.get("variant_key") for row in protocol.get("baselines", [])]
    variant_key_list = _parse_variant_keys(variant_keys if variant_keys is not None else protocol_variants or None)
    seed_list = _parse_seeds(seeds if seeds is not None else protocol.get("seeds") or None)
    expected_bounds = _jsonable_bounds(config.split_bounds())
    protocol_bounds = _jsonable_bounds(protocol.get("split_policy", {}).get("bounds", {})) if protocol else {}
    protocol_cache_root = protocol.get("cache_policy", {}).get("cache_root")
    protocol_cache_dir = protocol.get("cache_policy", {}).get("cache_dir")
    cache_dir = config.cache_dir()
    metadata_path = cache_dir / "metadata.json"
    metadata = load_json(metadata_path) if metadata_path.exists() else {}
    cache_bounds = _jsonable_bounds(metadata.get("split_bounds", {})) if metadata else {}
    anchor_report = strict_anchor_mask_report(cache_dir, metadata) if metadata else {"can_check": False}
    run_status = [
        _run_complete_status(Path(suite_dir) / f"wtb_{variant_key}_seed{seed}", variant_key, seed)
        for variant_key in variant_key_list
        for seed in seed_list
    ]
    complete_runs = int(sum(1 for row in run_status if row["complete"]))
    expected_runs = int(len(run_status))
    missing_runs = expected_runs - complete_runs
    run_df = pd.DataFrame(
        [
            {
                "variant_key": row["variant_key"],
                "label": row["label"],
                "mode": row["mode"],
                "seed": row["seed"],
                "run_dir": row["run_dir"],
                "complete": row["complete"],
                "overall_rmse": row["overall_rmse"],
                "switch_rmse": row["switch_rmse"],
                **{f"check_{key}": value for key, value in row["checks"].items()},
            }
            for row in run_status
        ]
    )
    run_df.to_csv(output_dir / "strict_baseline_run_status.csv", index=False)
    checks = {
        "protocol_json_exists": protocol_path.exists(),
        "protocol_status_is_not_executed": protocol.get("status") == "protocol_only_not_executed",
        "protocol_bounds_match_requested": protocol_bounds == expected_bounds,
        "protocol_cache_root_matches_requested": str(protocol_cache_root) == str(cache_root),
        "protocol_cache_dir_matches_requested": str(protocol_cache_dir) == str(cache_dir),
        "cache_metadata_exists": metadata_path.exists(),
        "cache_bounds_match_requested": cache_bounds == expected_bounds,
        "cache_has_strict_anchor_patch_marker": bool(metadata.get("strict_anchor_mask_patch")),
        "cache_strict_anchor_check_ran": bool(anchor_report.get("can_check")),
        "cache_strict_anchor_violations_zero": anchor_report.get("strict_anchor_violations") == 0,
        "all_expected_runs_complete": missing_runs == 0 and expected_runs > 0,
    }
    if not checks["protocol_json_exists"] or not checks["protocol_bounds_match_requested"]:
        status = "blocked_protocol_mismatch"
    elif not checks["protocol_cache_root_matches_requested"] or not checks["protocol_cache_dir_matches_requested"]:
        status = "blocked_protocol_cache_mismatch"
    elif not checks["cache_metadata_exists"]:
        status = "blocked_cache_missing"
    elif not checks["cache_bounds_match_requested"]:
        status = "blocked_cache_split_mismatch"
    elif not checks["cache_has_strict_anchor_patch_marker"] or not checks["cache_strict_anchor_violations_zero"]:
        status = "blocked_cache_not_strict"
    elif missing_runs > 0:
        status = "ready_to_execute_training"
    else:
        status = "complete_ready_for_strict_baseline_comparison"
    report = {
        "status": status,
        "checks": checks,
        "expected_runs": expected_runs,
        "complete_runs": complete_runs,
        "missing_runs": missing_runs,
        "variants": variant_key_list,
        "seeds": seed_list,
        "expected_bounds": expected_bounds,
        "protocol_bounds": protocol_bounds,
        "cache_bounds": cache_bounds,
        "anchor_mask_report": anchor_report,
        "paths": {
            "protocol_json": str(protocol_path),
            "cache_metadata": str(metadata_path),
            "suite_dir": str(suite_dir),
            "run_status_csv": str(output_dir / "strict_baseline_run_status.csv"),
        },
    }
    save_json(output_dir / "strict_baseline_guard.json", report)
    lines = [
        "# Strict-cache strong-baseline guard",
        "",
        f"Status: `{status}`",
        "",
        "This guard prevents legacy or incomplete baseline runs from being used as strict-cache leaderboard evidence.",
        "",
        "## Checks",
        "",
    ]
    for key, value in checks.items():
        lines.append(f"- {key}: `{bool(value)}`")
    lines.extend(
        [
            "",
            "## Run Completion",
            "",
            f"- Expected runs: `{expected_runs}`",
            f"- Complete runs: `{complete_runs}`",
            f"- Missing or incomplete runs: `{missing_runs}`",
            "",
            "## Anchor-Mask Report",
            "",
            "```json",
            json.dumps(anchor_report, indent=2),
            "```",
            "",
        ]
    )
    (output_dir / "README.md").write_text("\n".join(lines), encoding="utf-8")
    return output_dir
