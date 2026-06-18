from __future__ import annotations

from pathlib import Path
from typing import Any
import hashlib
import json

import numpy as np
import pandas as pd

from .utils import ensure_dir, load_json, save_json


STRICT_EVIDENCE_INPUTS = {
    "boundary_slice_effects": "boundary_slice_effects.csv",
    "boundary_slice_summary": "boundary_slice_summary.csv",
    "mechanism_effects": "mechanism_intervention/mechanism_intervention_effects.csv",
    "mechanism_raw": "mechanism_intervention/mechanism_intervention_raw.csv",
    "mechanism_replay_summary": "checkpoint_replay/checkpoint_replay_summary.csv",
    "placebo_effects": "routing_placebo_effects.csv",
    "placebo_raw": "routing_placebo_raw.csv",
    "placebo_summary": "routing_placebo_summary.csv",
    "time_forward_effects": "time_forward_effects.csv",
    "time_forward_summary": "time_forward_summary.csv",
    "time_forward_shift_diagnostics": "time_forward_shift_diagnostics.csv",
    "time_forward_shift_effects": "time_forward_shift_effects.csv",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _escape_latex(value: Any) -> str:
    text = "" if value is None else str(value)
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def _fmt(value: Any, digits: int = 4) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "" if value is None else str(value)
    if not np.isfinite(number):
        return ""
    return f"{number:.{digits}f}"


def _fmt_ci(mean: Any, low: Any, high: Any, digits: int = 4) -> str:
    return f"{_fmt(mean, digits)} [{_fmt(low, digits)}, {_fmt(high, digits)}]"


def _write_latex_table(path: Path, headers: list[str], rows: list[list[Any]], caption: str) -> Path:
    lines = [
        r"\begin{table}[t]",
        r"\centering",
        r"\small",
        f"\\caption{{{_escape_latex(caption)}}}",
        r"\resizebox{\linewidth}{!}{%",
        "\\begin{tabular}{" + "l" * len(headers) + "}",
        r"\toprule",
        " & ".join(_escape_latex(header) for header in headers) + r" \\",
        r"\midrule",
    ]
    for row in rows:
        lines.append(" & ".join(_escape_latex(value) for value in row) + r" \\")
    lines.extend([r"\bottomrule", r"\end{tabular}%", r"}", r"\end{table}", ""])
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _seed_from_run_dir(run_dir: Path) -> int | None:
    stem = run_dir.name
    if "seed" not in stem:
        return None
    try:
        return int(stem.rsplit("seed", 1)[-1])
    except ValueError:
        return None


def _collect_seed_metrics(strict_suite_dir: Path, model: str) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for run_dir in sorted(strict_suite_dir.glob("*seed*")):
        metrics_path = run_dir / "test_metrics" / "metrics.json"
        summary_path = run_dir / "training_summary.json"
        if not metrics_path.exists():
            continue
        metrics = load_json(metrics_path)
        training = load_json(summary_path) if summary_path.exists() else {}
        gate = metrics.get("gate_alignment", {})
        by_regime = metrics.get("by_regime", {})
        rows.append(
            {
                "dataset": "wtb",
                "model": model,
                "seed": _seed_from_run_dir(run_dir),
                "run_dir": str(run_dir),
                "best_epoch": training.get("best_epoch"),
                "best_val_rmse": training.get("best_val_rmse"),
                "overall_mae": metrics.get("overall", {}).get("mae"),
                "overall_rmse": metrics.get("overall", {}).get("rmse"),
                "switch_mae": metrics.get("switch_window", {}).get("mae"),
                "switch_rmse": metrics.get("switch_window", {}).get("rmse"),
                "pitch_control_mae": by_regime.get("pitch_control", {}).get("mae"),
                "pitch_control_rmse": by_regime.get("pitch_control", {}).get("rmse"),
                "nmi": gate.get("nmi"),
                "ari": gate.get("ari"),
                "expert_usage_entropy": gate.get("expert_usage_entropy"),
                "expert_usage_variance": gate.get("expert_usage_variance"),
            }
        )
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values("seed", na_position="last").reset_index(drop=True)
    return df


def _summarize_seed_metrics(seed_df: pd.DataFrame) -> pd.DataFrame:
    if seed_df.empty:
        return pd.DataFrame()
    metric_cols = [
        "overall_rmse",
        "switch_rmse",
        "pitch_control_rmse",
        "nmi",
        "ari",
        "expert_usage_entropy",
        "expert_usage_variance",
    ]
    row: dict[str, Any] = {
        "dataset": "wtb",
        "model": seed_df["model"].iloc[0],
        "n_runs": int(len(seed_df)),
        "seeds": ",".join(str(int(seed)) for seed in seed_df["seed"].dropna().astype(int).tolist()),
    }
    for metric in metric_cols:
        values = pd.to_numeric(seed_df.get(metric), errors="coerce").dropna()
        row[f"{metric}_mean"] = float(values.mean()) if not values.empty else float("nan")
        row[f"{metric}_std"] = float(values.std(ddof=1)) if len(values) > 1 else 0.0
    return pd.DataFrame([row])


def _copy_csv(src: Path, dst: Path) -> pd.DataFrame:
    df = pd.read_csv(src) if src.exists() else pd.DataFrame()
    df.to_csv(dst, index=False)
    return df


def _write_seed_tables(seed_df: pd.DataFrame, summary_df: pd.DataFrame, output_dir: Path) -> Path:
    rows: list[list[Any]] = []
    for _, row in seed_df.iterrows():
        rows.append(
            [
                int(row["seed"]),
                _fmt(row["overall_rmse"]),
                _fmt(row["switch_rmse"]),
                _fmt(row["pitch_control_rmse"]),
                _fmt(row["nmi"]),
                _fmt(row["ari"]),
            ]
        )
    if not summary_df.empty:
        s = summary_df.iloc[0]
        rows.append(
            [
                "Mean +/- SD",
                f"{_fmt(s['overall_rmse_mean'])} +/- {_fmt(s['overall_rmse_std'])}",
                f"{_fmt(s['switch_rmse_mean'])} +/- {_fmt(s['switch_rmse_std'])}",
                f"{_fmt(s['pitch_control_rmse_mean'])} +/- {_fmt(s['pitch_control_rmse_std'])}",
                f"{_fmt(s['nmi_mean'])} +/- {_fmt(s['nmi_std'])}",
                f"{_fmt(s['ari_mean'])} +/- {_fmt(s['ari_std'])}",
            ]
        )
    return _write_latex_table(
        output_dir / "table_strict_wtb_seed_metrics.tex",
        ["Seed", "Overall RMSE", "Switch RMSE", "Pitch RMSE", "NMI", "ARI"],
        rows,
        "Strict-anchor-mask WTB five-seed metrics.",
    )


def _write_mechanism_table(effects_df: pd.DataFrame, output_dir: Path) -> Path:
    rows: list[list[Any]] = []
    for _, row in effects_df.iterrows():
        rows.append(
            [
                row.get("intervention", ""),
                _fmt_ci(
                    row.get("delta_overall_rmse_mean"),
                    row.get("delta_overall_rmse_ci_low"),
                    row.get("delta_overall_rmse_ci_high"),
                ),
                _fmt_ci(
                    row.get("delta_switch_rmse_mean"),
                    row.get("delta_switch_rmse_ci_low"),
                    row.get("delta_switch_rmse_ci_high"),
                ),
                _fmt_ci(
                    row.get("drop_nmi_mean"),
                    row.get("drop_nmi_ci_low"),
                    row.get("drop_nmi_ci_high"),
                ),
                _fmt_ci(
                    row.get("drop_ari_mean"),
                    row.get("drop_ari_ci_low"),
                    row.get("drop_ari_ci_high"),
                ),
            ]
        )
    return _write_latex_table(
        output_dir / "table_strict_wtb_mechanism_effects.tex",
        ["Intervention", "Delta RMSE", "Delta switch RMSE", "Drop NMI", "Drop ARI"],
        rows,
        "Replay-safe strict-mask WTB mechanism interventions.",
    )


def _write_placebo_table(effects_df: pd.DataFrame, output_dir: Path) -> Path:
    rows: list[list[Any]] = []
    for _, row in effects_df.iterrows():
        rows.append(
            [
                row.get("control_condition", ""),
                _fmt_ci(row.get("delta_nmi_mean"), row.get("delta_nmi_ci_low"), row.get("delta_nmi_ci_high")),
                _fmt_ci(row.get("delta_ari_mean"), row.get("delta_ari_ci_low"), row.get("delta_ari_ci_high")),
            ]
        )
    return _write_latex_table(
        output_dir / "table_strict_wtb_placebo_effects.tex",
        ["Control", "Delta NMI", "Delta ARI"],
        rows,
        "Strict-mask WTB routing placebo separations.",
    )


def _write_mechanism_per_seed_table(raw_df: pd.DataFrame, output_dir: Path) -> Path:
    rows: list[list[Any]] = []
    if not raw_df.empty:
        actual = raw_df[raw_df["intervention"] == "actual"].copy()
        controls = raw_df[raw_df["intervention"].isin(["anchor_boundary_zero", "anchor_wake_zero"])].copy()
        merged = controls.merge(
            actual[["run_dir", "overall_rmse", "switch_rmse", "nmi", "ari"]],
            on="run_dir",
            how="inner",
            suffixes=("_intervention", "_actual"),
        )
        for _, row in merged.sort_values(["intervention", "seed"]).iterrows():
            rows.append(
                [
                    int(row["seed"]),
                    row.get("intervention", ""),
                    _fmt(float(row["overall_rmse_intervention"]) - float(row["overall_rmse_actual"])),
                    _fmt(float(row["switch_rmse_intervention"]) - float(row["switch_rmse_actual"])),
                    _fmt(float(row["nmi_actual"]) - float(row["nmi_intervention"])),
                    _fmt(float(row["ari_actual"]) - float(row["ari_intervention"])),
                ]
            )
    return _write_latex_table(
        output_dir / "table_strict_wtb_mechanism_per_seed.tex",
        ["Seed", "Intervention", "Delta RMSE", "Delta switch RMSE", "Drop NMI", "Drop ARI"],
        rows,
        "Per-seed strict-mask WTB mechanism intervention effects.",
    )


def _write_placebo_per_seed_table(raw_df: pd.DataFrame, output_dir: Path) -> Path:
    rows: list[list[Any]] = []
    if not raw_df.empty:
        actual = raw_df[raw_df["condition"] == "actual"].copy()
        controls = raw_df[raw_df["condition"].isin(["temporal_shift_144", "node_permutation", "global_shuffle"])].copy()
        merged = controls.merge(
            actual[["run_dir", "nmi", "ari"]],
            on="run_dir",
            how="inner",
            suffixes=("_control", "_actual"),
        )
        for _, row in merged.sort_values(["condition", "seed"]).iterrows():
            rows.append(
                [
                    int(row["seed"]),
                    row.get("condition", ""),
                    _fmt(row.get("nmi_actual")),
                    _fmt(row.get("nmi_control")),
                    _fmt(float(row["nmi_actual"]) - float(row["nmi_control"])),
                    _fmt(float(row["ari_actual"]) - float(row["ari_control"])),
                ]
            )
    return _write_latex_table(
        output_dir / "table_strict_wtb_placebo_per_seed.tex",
        ["Seed", "Control", "Actual NMI", "Control NMI", "Delta NMI", "Delta ARI"],
        rows,
        "Per-seed strict-mask WTB routing placebo separations.",
    )


def _write_time_forward_table(summary_df: pd.DataFrame, output_dir: Path) -> Path:
    rows: list[list[Any]] = []
    for _, row in summary_df.iterrows():
        rows.append(
            [
                f"{int(row['block_id'])} {row['block_label']}",
                f"{int(row['anchor_start_min'])}-{int(row['anchor_end_max'])}",
                f"{_fmt(row['overall_rmse_mean'])} +/- {_fmt(row['overall_rmse_std'])}",
                f"{_fmt(row['switch_rmse_mean'])} +/- {_fmt(row['switch_rmse_std'])}",
                f"{_fmt(row['nmi_mean'])} +/- {_fmt(row['nmi_std'])}",
                f"{_fmt(row['ari_mean'])} +/- {_fmt(row['ari_std'])}",
            ]
        )
    return _write_latex_table(
        output_dir / "table_strict_wtb_time_forward.tex",
        ["Block", "Anchor range", "Overall RMSE", "Switch RMSE", "NMI", "ARI"],
        rows,
        "Strict-mask WTB post-hoc time-forward test-slice audit.",
    )


def _write_late_shift_table(effects_df: pd.DataFrame, output_dir: Path) -> Path:
    rows: list[list[Any]] = []
    for _, row in effects_df.iterrows():
        rows.append(
            [
                row.get("model", ""),
                _fmt_ci(
                    row.get("delta_overall_rmse_mean"),
                    row.get("delta_overall_rmse_ci_low"),
                    row.get("delta_overall_rmse_ci_high"),
                ),
                _fmt_ci(
                    row.get("delta_abs_ramp_mean_mean"),
                    row.get("delta_abs_ramp_mean_ci_low"),
                    row.get("delta_abs_ramp_mean_ci_high"),
                ),
                _fmt(row.get("regime_share_total_variation")),
                _fmt(row.get("regime_share_jensen_shannon")),
                _fmt_ci(row.get("delta_nmi_mean"), row.get("delta_nmi_ci_low"), row.get("delta_nmi_ci_high")),
            ]
        )
    return _write_latex_table(
        output_dir / "table_strict_wtb_late_shift_diagnostics.tex",
        ["Model", "Delta RMSE", "Delta abs ramp", "Regime TV", "Regime JSD", "Delta NMI"],
        rows,
        "Strict-mask WTB late-period distribution-shift diagnostics.",
    )


def _write_boundary_slice_table(summary_df: pd.DataFrame, output_dir: Path) -> Path:
    rows: list[list[Any]] = []
    for _, row in summary_df.iterrows():
        nmi = _fmt(row.get("nmi_mean"))
        ari = _fmt(row.get("ari_mean"))
        rows.append(
            [
                row.get("slice", ""),
                f"{_fmt(row.get('rmse_mean'))} +/- {_fmt(row.get('rmse_std'))}",
                nmi if nmi else "NA",
                ari if ari else "NA",
                _fmt(row.get("n_anchor_cells_mean"), digits=0),
            ]
        )
    return _write_latex_table(
        output_dir / "table_strict_wtb_boundary_slice.tex",
        ["Slice", "RMSE", "NMI", "ARI", "Anchor cells"],
        rows,
        "Strict-mask WTB MPPT-to-pitch boundary-slice audit.",
    )


def _write_boundary_effects_table(effects_df: pd.DataFrame, output_dir: Path) -> Path:
    rows: list[list[Any]] = []
    for _, row in effects_df.iterrows():
        rows.append(
            [
                row.get("comparison", ""),
                _fmt_ci(row.get("delta_rmse_mean"), row.get("delta_rmse_ci_low"), row.get("delta_rmse_ci_high")),
                _fmt_ci(row.get("delta_mae_mean"), row.get("delta_mae_ci_low"), row.get("delta_mae_ci_high")),
            ]
        )
    return _write_latex_table(
        output_dir / "table_strict_wtb_boundary_effects.tex",
        ["Comparison", "Delta RMSE", "Delta MAE"],
        rows,
        "Strict-mask WTB boundary-band difficulty relative to comparator slices.",
    )


def _manifest(
    output_dir: Path,
    input_paths: dict[str, Path],
    output_paths: dict[str, Path],
    summary: dict[str, Any],
) -> dict[str, Any]:
    existing_inputs = {
        name: {"path": str(path), "sha256": _sha256(path)}
        for name, path in sorted(input_paths.items())
        if path.exists()
    }
    existing_outputs = {
        name: {"path": str(path), "sha256": _sha256(path)}
        for name, path in sorted(output_paths.items())
        if path.exists()
    }
    return {
        "kind": "strict_wtb_evidence_source_package",
        "output_dir": str(output_dir),
        "inputs": existing_inputs,
        "outputs": existing_outputs,
        "summary": summary,
    }


def export_strict_wtb_evidence(
    output_dir: Path | str,
    strict_suite_dir: Path | str = "artifacts/strictmask_validation_wtb_full",
    mechanism_dir: Path | str = "artifacts/mechanism_gate_wtb_strictmask_full",
    placebo_dir: Path | str = "artifacts/routing_placebo_wtb_strictmask_full",
    time_forward_dir: Path | str = "artifacts/time_forward_wtb_strictmask_full",
    boundary_slice_dir: Path | str = "artifacts/boundary_slice_wtb_strictmask_full",
    model: str = "MoE + L_bal + L_align + L_force",
) -> Path:
    output_dir = ensure_dir(output_dir)
    strict_suite_dir = Path(strict_suite_dir)
    mechanism_dir = Path(mechanism_dir)
    placebo_dir = Path(placebo_dir)
    time_forward_dir = Path(time_forward_dir)
    boundary_slice_dir = Path(boundary_slice_dir)
    table_dir = ensure_dir(output_dir / "tables")
    tex_dir = ensure_dir(output_dir / "generated")

    seed_df = _collect_seed_metrics(strict_suite_dir, model=model)
    summary_df = _summarize_seed_metrics(seed_df)
    seed_path = table_dir / "strict_wtb_seed_metrics.csv"
    summary_path = table_dir / "strict_wtb_summary.csv"
    seed_df.to_csv(seed_path, index=False)
    summary_df.to_csv(summary_path, index=False)

    input_paths = {
        "strict_suite_summary": strict_suite_dir / "suite_summary.json",
        "boundary_slice_effects": boundary_slice_dir / STRICT_EVIDENCE_INPUTS["boundary_slice_effects"],
        "boundary_slice_summary": boundary_slice_dir / STRICT_EVIDENCE_INPUTS["boundary_slice_summary"],
        "mechanism_effects": mechanism_dir / STRICT_EVIDENCE_INPUTS["mechanism_effects"],
        "mechanism_raw": mechanism_dir / STRICT_EVIDENCE_INPUTS["mechanism_raw"],
        "mechanism_replay_summary": mechanism_dir / STRICT_EVIDENCE_INPUTS["mechanism_replay_summary"],
        "placebo_effects": placebo_dir / STRICT_EVIDENCE_INPUTS["placebo_effects"],
        "placebo_raw": placebo_dir / STRICT_EVIDENCE_INPUTS["placebo_raw"],
        "placebo_summary": placebo_dir / STRICT_EVIDENCE_INPUTS["placebo_summary"],
        "time_forward_effects": time_forward_dir / STRICT_EVIDENCE_INPUTS["time_forward_effects"],
        "time_forward_summary": time_forward_dir / STRICT_EVIDENCE_INPUTS["time_forward_summary"],
        "time_forward_shift_diagnostics": time_forward_dir / STRICT_EVIDENCE_INPUTS["time_forward_shift_diagnostics"],
        "time_forward_shift_effects": time_forward_dir / STRICT_EVIDENCE_INPUTS["time_forward_shift_effects"],
    }
    mechanism_effects = _copy_csv(input_paths["mechanism_effects"], table_dir / "strict_wtb_mechanism_effects.csv")
    mechanism_raw = _copy_csv(input_paths["mechanism_raw"], table_dir / "strict_wtb_mechanism_raw.csv")
    replay_summary = _copy_csv(input_paths["mechanism_replay_summary"], table_dir / "strict_wtb_replay_summary.csv")
    placebo_effects = _copy_csv(input_paths["placebo_effects"], table_dir / "strict_wtb_placebo_effects.csv")
    placebo_raw = _copy_csv(input_paths["placebo_raw"], table_dir / "strict_wtb_placebo_raw.csv")
    placebo_summary = _copy_csv(input_paths["placebo_summary"], table_dir / "strict_wtb_placebo_summary.csv")
    time_effects = _copy_csv(input_paths["time_forward_effects"], table_dir / "strict_wtb_time_forward_effects.csv")
    time_summary = _copy_csv(input_paths["time_forward_summary"], table_dir / "strict_wtb_time_forward_summary.csv")
    time_shift_diagnostics = _copy_csv(
        input_paths["time_forward_shift_diagnostics"], table_dir / "strict_wtb_time_forward_shift_diagnostics.csv"
    )
    time_shift_effects = _copy_csv(
        input_paths["time_forward_shift_effects"], table_dir / "strict_wtb_time_forward_shift_effects.csv"
    )
    boundary_effects = _copy_csv(
        input_paths["boundary_slice_effects"], table_dir / "strict_wtb_boundary_slice_effects.csv"
    )
    boundary_summary = _copy_csv(
        input_paths["boundary_slice_summary"], table_dir / "strict_wtb_boundary_slice_summary.csv"
    )

    tex_paths = {
        "seed_metrics_tex": _write_seed_tables(seed_df, summary_df, tex_dir),
        "mechanism_effects_tex": _write_mechanism_table(mechanism_effects, tex_dir),
        "mechanism_per_seed_tex": _write_mechanism_per_seed_table(mechanism_raw, tex_dir),
        "placebo_effects_tex": _write_placebo_table(placebo_effects, tex_dir),
        "placebo_per_seed_tex": _write_placebo_per_seed_table(placebo_raw, tex_dir),
        "time_forward_tex": _write_time_forward_table(time_summary, tex_dir),
        "late_shift_diagnostics_tex": _write_late_shift_table(time_shift_effects, tex_dir),
        "boundary_slice_tex": _write_boundary_slice_table(boundary_summary, tex_dir),
        "boundary_effects_tex": _write_boundary_effects_table(boundary_effects, tex_dir),
    }
    output_paths = {
        "seed_metrics_csv": seed_path,
        "summary_csv": summary_path,
        "boundary_slice_effects_csv": table_dir / "strict_wtb_boundary_slice_effects.csv",
        "boundary_slice_summary_csv": table_dir / "strict_wtb_boundary_slice_summary.csv",
        "mechanism_effects_csv": table_dir / "strict_wtb_mechanism_effects.csv",
        "mechanism_raw_csv": table_dir / "strict_wtb_mechanism_raw.csv",
        "replay_summary_csv": table_dir / "strict_wtb_replay_summary.csv",
        "placebo_effects_csv": table_dir / "strict_wtb_placebo_effects.csv",
        "placebo_raw_csv": table_dir / "strict_wtb_placebo_raw.csv",
        "placebo_summary_csv": table_dir / "strict_wtb_placebo_summary.csv",
        "time_forward_effects_csv": table_dir / "strict_wtb_time_forward_effects.csv",
        "time_forward_summary_csv": table_dir / "strict_wtb_time_forward_summary.csv",
        "time_forward_shift_diagnostics_csv": table_dir / "strict_wtb_time_forward_shift_diagnostics.csv",
        "time_forward_shift_effects_csv": table_dir / "strict_wtb_time_forward_shift_effects.csv",
        **tex_paths,
    }

    summary: dict[str, Any] = {}
    if not summary_df.empty:
        summary.update(json.loads(summary_df.iloc[0].to_json()))
    if not replay_summary.empty:
        summary["replay_status"] = replay_summary.iloc[0].get("replay_status")
        summary["n_replay_runs"] = int(replay_summary.iloc[0].get("n_runs", 0))
    if not time_effects.empty:
        row = time_effects.iloc[0]
        summary["late_vs_early_delta_overall_rmse_mean"] = float(row.get("delta_overall_rmse_mean"))
        summary["late_vs_early_delta_switch_rmse_mean"] = float(row.get("delta_switch_rmse_mean"))
        summary["late_vs_early_delta_nmi_mean"] = float(row.get("delta_nmi_mean"))
    if not time_shift_effects.empty:
        row = time_shift_effects.iloc[0]
        summary["late_shift_delta_abs_ramp_mean"] = float(row.get("delta_abs_ramp_mean_mean"))
        summary["late_shift_regime_share_total_variation"] = float(row.get("regime_share_total_variation"))
        summary["late_shift_wspd_ks"] = float(row.get("wspd_mean_ks"))
    if not boundary_summary.empty:
        boundary_row = boundary_summary[boundary_summary["slice"] == "boundary_band"]
        if not boundary_row.empty:
            summary["boundary_band_rmse_mean"] = float(boundary_row.iloc[0].get("rmse_mean"))
            summary["boundary_band_nmi_mean"] = float(boundary_row.iloc[0].get("nmi_mean"))
            summary["boundary_band_ari_mean"] = float(boundary_row.iloc[0].get("ari_mean"))
    if not boundary_effects.empty:
        effect_row = boundary_effects[boundary_effects["comparator_slice"] == "nonboundary_valid"]
        if not effect_row.empty:
            summary["boundary_vs_nonboundary_delta_rmse_mean"] = float(effect_row.iloc[0].get("delta_rmse_mean"))

    manifest_path = output_dir / "strict_wtb_evidence_manifest.json"
    save_json(manifest_path, _manifest(output_dir, input_paths, output_paths, summary))
    output_paths["manifest_json"] = manifest_path

    readme_lines = [
        "# Strict WTB Evidence Source Package",
        "",
        "This folder centralizes the strict-anchor-mask WTB evidence stack for manuscript table and supplement regeneration.",
        "",
        "## Contents",
        "",
        "- `tables/strict_wtb_seed_metrics.csv`: per-seed strict-mask metrics.",
        "- `tables/strict_wtb_summary.csv`: five-seed mean and standard deviation.",
        "- `tables/strict_wtb_mechanism_effects.csv`: replay-safe mechanism intervention effects.",
        "- `tables/strict_wtb_mechanism_raw.csv`: per-seed mechanism intervention raw metrics.",
        "- `tables/strict_wtb_placebo_effects.csv`: routing placebo separations.",
        "- `tables/strict_wtb_placebo_raw.csv`: per-seed routing placebo raw metrics.",
        "- `tables/strict_wtb_time_forward_summary.csv`: post-hoc time-forward block metrics.",
        "- `tables/strict_wtb_time_forward_effects.csv`: late-vs-early effects.",
        "- `tables/strict_wtb_time_forward_shift_diagnostics.csv`: block-level late-period distribution-shift diagnostics.",
        "- `tables/strict_wtb_time_forward_shift_effects.csv`: late-minus-early shift distances and paired effects.",
        "- `tables/strict_wtb_boundary_slice_summary.csv`: MPPT-to-pitch boundary-band slice metrics.",
        "- `tables/strict_wtb_boundary_slice_effects.csv`: boundary-band versus comparator-slice effects.",
        "- `generated/*.tex`: LaTeX source tables generated from the CSV files.",
        "- `strict_wtb_evidence_manifest.json`: input/output SHA256 manifest.",
        "",
        "## Science-Level Interpretation",
        "",
        "The package supports a strict-mask mechanism/routing claim, not an accuracy-SOTA or deployment-robustness claim.",
    ]
    if summary:
        readme_lines.extend(
            [
                "",
                "## Key Numbers",
                "",
                f"- Overall RMSE: `{_fmt(summary.get('overall_rmse_mean'))} +/- {_fmt(summary.get('overall_rmse_std'))}`.",
                f"- Switch RMSE: `{_fmt(summary.get('switch_rmse_mean'))} +/- {_fmt(summary.get('switch_rmse_std'))}`.",
                f"- NMI / ARI: `{_fmt(summary.get('nmi_mean'))} +/- {_fmt(summary.get('nmi_std'))}` / `{_fmt(summary.get('ari_mean'))} +/- {_fmt(summary.get('ari_std'))}`.",
                f"- Boundary-band RMSE / NMI / ARI: `{_fmt(summary.get('boundary_band_rmse_mean'))}` / `{_fmt(summary.get('boundary_band_nmi_mean'))}` / `{_fmt(summary.get('boundary_band_ari_mean'))}`.",
                f"- Boundary-vs-nonboundary delta RMSE: `{_fmt(summary.get('boundary_vs_nonboundary_delta_rmse_mean'))}`.",
                f"- Replay status: `{summary.get('replay_status', '')}` over `{summary.get('n_replay_runs', '')}` runs.",
                f"- Late-vs-early overall RMSE delta: `{_fmt(summary.get('late_vs_early_delta_overall_rmse_mean'))}`.",
                f"- Late-shift abs-ramp delta / regime TV: `{_fmt(summary.get('late_shift_delta_abs_ramp_mean'))}` / `{_fmt(summary.get('late_shift_regime_share_total_variation'))}`.",
            ]
        )
    (output_dir / "README.md").write_text("\n".join(readme_lines) + "\n", encoding="utf-8")
    return output_dir
