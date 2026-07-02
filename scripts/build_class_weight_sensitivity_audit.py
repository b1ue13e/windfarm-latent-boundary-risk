from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
LEGACY_SUITE = ROOT / "artifacts" / "strictmask_validation_wtb_full"
TRAIN_WEIGHT_SUITE = ROOT / "artifacts" / "trainweight_class_weight_rerun_20260702"
OUT = ROOT / "artifacts" / "class_weight_boundary_audit"
FINAL_TABLES = ROOT / "artifacts" / "final_evidence_package" / "export" / "tables"
SEEDS = [201, 202, 203, 204, 205]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    FINAL_TABLES.mkdir(parents=True, exist_ok=True)
    rows = []
    for suite_label, suite_dir, weight_source in [
        ("legacy_strict_cache", LEGACY_SUITE, "full-period metadata"),
        ("train_only_weight_rerun", TRAIN_WEIGHT_SUITE, "train split"),
    ]:
        for seed in SEEDS:
            run_dir = suite_dir / f"wtb_bal_align_force_seed{seed}"
            if not (run_dir / "training_summary.json").exists():
                rows.append(_missing_row(suite_label, weight_source, seed, run_dir))
                continue
            rows.append(_metric_row(suite_label, weight_source, seed, run_dir))

    frame = pd.DataFrame(rows)
    csv_path = OUT / "class_weight_sensitivity_audit.csv"
    tex_path = OUT / "table_class_weight_sensitivity_audit.tex"
    json_path = OUT / "class_weight_sensitivity_audit.json"
    frame.to_csv(csv_path, index=False)

    summary = _summary(frame)
    summary.to_csv(OUT / "class_weight_sensitivity_summary.csv", index=False)
    _write_latex(summary, tex_path)
    (FINAL_TABLES / csv_path.name).write_text(csv_path.read_text(encoding="utf-8"), encoding="utf-8")
    (FINAL_TABLES / tex_path.name).write_text(tex_path.read_text(encoding="utf-8"), encoding="utf-8")

    complete = bool(frame["complete"].astype(bool).all()) if not frame.empty else False
    train = summary[summary["suite"] == "train_only_weight_rerun"]
    nmi_pass = bool(not train.empty and float(train.iloc[0]["nmi_mean"]) >= 0.65)
    status = (
        "complete_train_only_class_weight_rerun_supports_boundary_claim"
        if complete and nmi_pass
        else "pending_train_only_class_weight_rerun"
    )
    payload = {
        "status": status,
        "seeds": SEEDS,
        "legacy_suite": str(LEGACY_SUITE),
        "train_weight_suite": str(TRAIN_WEIGHT_SUITE),
        "claim_use": (
            "Sensitivity audit for alignment/forcing class-weight provenance. "
            "The train-only rerun isolates the loss-weight boundary while keeping "
            "the strict-cache arrays and protocol fixed."
        ),
        "csv": str(csv_path),
        "tex": str(tex_path),
        "summary": summary.to_dict(orient="records"),
    }
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    (FINAL_TABLES / json_path.name).write_text(json_path.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"Wrote {csv_path}")
    print(status)


def _missing_row(suite: str, weight_source: str, seed: int, run_dir: Path) -> dict[str, Any]:
    return {
        "suite": suite,
        "weight_source": weight_source,
        "seed": seed,
        "run_dir": str(run_dir.relative_to(ROOT)),
        "complete": False,
    }


def _metric_row(suite: str, weight_source: str, seed: int, run_dir: Path) -> dict[str, Any]:
    metrics = json.loads((run_dir / "test_metrics" / "metrics.json").read_text(encoding="utf-8"))
    return {
        "suite": suite,
        "weight_source": weight_source,
        "seed": seed,
        "run_dir": str(run_dir.relative_to(ROOT)),
        "complete": True,
        "overall_rmse": _get(metrics, "overall", "rmse"),
        "switch_rmse": _get(metrics, "switch_window", "rmse"),
        "pitch_control_rmse": _get(metrics, "by_regime", "pitch_control", "rmse"),
        "nmi": _get(metrics, "gate_alignment", "nmi"),
        "ari": _get(metrics, "gate_alignment", "ari"),
    }


def _summary(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    metrics = ["overall_rmse", "switch_rmse", "pitch_control_rmse", "nmi", "ari"]
    for suite, group in frame.groupby("suite", sort=False):
        row: dict[str, Any] = {
            "suite": suite,
            "weight_source": str(group["weight_source"].dropna().iloc[0]) if "weight_source" in group else "",
            "complete_runs": int(group["complete"].astype(bool).sum()),
        }
        for metric in metrics:
            values = pd.to_numeric(group.get(metric), errors="coerce").dropna()
            row[f"{metric}_mean"] = float(values.mean()) if not values.empty else np.nan
            row[f"{metric}_std"] = float(values.std(ddof=1)) if len(values) > 1 else 0.0
        rows.append(row)
    summary = pd.DataFrame(rows)
    if {"legacy_strict_cache", "train_only_weight_rerun"}.issubset(set(summary["suite"])):
        legacy = summary[summary["suite"] == "legacy_strict_cache"].iloc[0]
        train = summary[summary["suite"] == "train_only_weight_rerun"].iloc[0]
        delta: dict[str, Any] = {
            "suite": "train_only_minus_legacy",
            "weight_source": "delta",
            "complete_runs": int(train["complete_runs"]),
        }
        for metric in metrics:
            delta[f"{metric}_mean"] = float(train[f"{metric}_mean"] - legacy[f"{metric}_mean"])
            delta[f"{metric}_std"] = np.nan
        summary = pd.concat([summary, pd.DataFrame([delta])], ignore_index=True)
    return summary


def _write_latex(summary: pd.DataFrame, path: Path) -> None:
    display = summary.copy()
    labels = {
        "legacy_strict_cache": "Legacy strict-cache weights",
        "train_only_weight_rerun": "Train-only weight rerun",
        "train_only_minus_legacy": "Delta",
    }
    lines = [
        r"\begin{table}[H]",
        r"\centering",
        r"\scriptsize",
        r"\setlength{\tabcolsep}{3pt}",
        r"\renewcommand{\arraystretch}{1.05}",
        r"\caption*{\textbf{Class-weight sensitivity audit.} Boundary-router rerun after recomputing alignment and pitch-forcing loss weights from the training split only.}",
        r"\resizebox{\columnwidth}{!}{%",
        r"\begin{tabular}{lrrrrr}",
        r"\toprule",
        r"Condition & Overall RMSE & Switch RMSE & Pitch RMSE & NMI & ARI \\",
        r"\midrule",
    ]
    for _, row in display.iterrows():
        lines.append(
            " & ".join(
                [
                    labels.get(str(row["suite"]), str(row["suite"])).replace("_", r"\_"),
                    _fmt(row["overall_rmse_mean"], 2),
                    _fmt(row["switch_rmse_mean"], 2),
                    _fmt(row["pitch_control_rmse_mean"], 2),
                    _fmt(row["nmi_mean"], 4),
                    _fmt(row["ari_mean"], 4),
                ]
            )
            + r" \\"
        )
    lines.extend(
        [
            r"\bottomrule",
            r"\end{tabular}%",
            r"}",
            r"\end{table}",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def _get(obj: dict[str, Any], *keys: str) -> float:
    current: Any = obj
    for key in keys:
        current = current[key]
    return float(current)


def _fmt(value: Any, digits: int) -> str:
    try:
        if np.isnan(float(value)):
            return "--"
    except (TypeError, ValueError):
        return "--"
    return f"{float(value):.{digits}f}"


if __name__ == "__main__":
    main()
