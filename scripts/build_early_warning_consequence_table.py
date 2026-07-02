from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW = (
    ROOT
    / "artifacts"
    / "anchor_stress_early_warning_wtb_strictmask"
    / "anchor_stress_early_warning_raw.csv"
)
CLASSIFIER = (
    ROOT
    / "artifacts"
    / "early_warning_classifier_baseline_wtb"
    / "early_warning_classifier_baseline_summary.csv"
)
OUT_TABLES = ROOT / "artifacts" / "final_evidence_package" / "export" / "tables"

CONDITIONS = [
    ("Clean live anchors", "label_availability", "available_rate=1.00", "clean", "clean_live_anchor"),
    ("Delay, 6 steps", "label_delay", "delay_steps=6"),
    ("50% label availability", "label_availability", "available_rate=0.50"),
    ("Sensor noise, strongest", "threshold_sensor_noise", "wspd_sd=1.00;pab_sd=2.00"),
]


def main() -> None:
    OUT_TABLES.mkdir(parents=True, exist_ok=True)
    raw = pd.read_csv(RAW)
    classifier = pd.read_csv(CLASSIFIER)
    rows = [
        _condition_summary(raw, classifier, label, scenario, degradation, clf_scenario, clf_degradation)
        for label, scenario, degradation, clf_scenario, clf_degradation in _conditions()
    ]

    out_csv = OUT_TABLES / "early_warning_consequence_audit.csv"
    out_tex = OUT_TABLES / "table_early_warning_consequence_audit.tex"
    out_json = OUT_TABLES / "early_warning_consequence_audit_summary.json"

    pd.DataFrame(rows).to_csv(out_csv, index=False)
    _write_latex(rows, out_tex)
    payload: dict[str, Any] = {
        "inputs": {"raw_csv": str(RAW)},
        "outputs": {"csv": str(out_csv), "tex": str(out_tex)},
        "claim_use": (
            "Detection-control audit for the label-degradation result. The table compares "
            "the audited gate, a simple issue-time anchor classifier, and the degraded "
            "threshold-label rule. Counts are test-set turbine-time cells per seed inside "
            "the six-step MPPT-to-pitch window; they are not MWh, currency, or dispatch-cost "
            "estimates. In sensor-noise rows, gate values are the saved clean-route audit "
            "while classifier/rule values are recomputed from noisy issue-time anchors."
        ),
    }
    out_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {out_csv}")


def _conditions() -> list[tuple[str, str, str, str, str]]:
    out: list[tuple[str, str, str, str, str]] = []
    for condition in CONDITIONS:
        if len(condition) == 5:
            out.append(condition)  # type: ignore[arg-type]
        else:
            label, scenario, degradation = condition
            out.append((label, scenario, degradation, scenario, degradation))
    return out


def _condition_summary(
    raw: pd.DataFrame,
    classifier: pd.DataFrame,
    label: str,
    scenario: str,
    degradation: str,
    clf_scenario: str,
    clf_degradation: str,
) -> dict[str, Any]:
    subset = raw[
        (raw["scenario"].astype(str) == scenario)
        & (raw["degradation_label"].astype(str) == degradation)
    ].copy()
    if subset.empty:
        raise ValueError(f"Missing early-warning condition: {scenario} / {degradation}")

    subset["gate_detected_cells"] = subset["n_target_cells"] * subset["gate_recall"]
    subset["rule_detected_cells"] = subset["n_target_cells"] * subset["threshold_recall"]
    subset["gate_missed_cells"] = subset["n_target_cells"] - subset["gate_detected_cells"]
    subset["rule_missed_cells"] = subset["n_target_cells"] - subset["rule_detected_cells"]
    subset["recovered_cells_vs_rule"] = subset["gate_detected_cells"] - subset["rule_detected_cells"]
    clf_row = classifier[
        (classifier["scenario"].astype(str) == clf_scenario)
        & (classifier["degradation_label"].astype(str) == clf_degradation)
    ]
    if clf_row.empty:
        raise ValueError(f"Missing classifier condition: {clf_scenario} / {clf_degradation}")
    clf = clf_row.iloc[0]

    row: dict[str, Any] = {
        "condition": label,
        "scenario": scenario,
        "degradation_label": degradation,
        "n_runs": int(subset[["variant", "seed"]].drop_duplicates().shape[0]),
    }
    for column in [
        "n_target_cells",
        "gate_detected_cells",
        "rule_detected_cells",
        "gate_missed_cells",
        "rule_missed_cells",
        "recovered_cells_vs_rule",
    ]:
        values = pd.to_numeric(subset[column], errors="coerce")
        row[f"{column}_mean"] = _mean(values)
        row[f"{column}_std"] = _std(values)
    for source, prefix in [
        (subset, "gate"),
        (subset.rename(columns={"threshold_recall": "rule_recall", "threshold_precision": "rule_precision"}), "rule"),
    ]:
        for metric in ["recall", "precision"]:
            values = pd.to_numeric(source[f"{prefix}_{metric}"], errors="coerce")
            row[f"{prefix}_{metric}_mean"] = _mean(values)
            row[f"{prefix}_{metric}_std"] = _std(values)
    for metric in ["recall", "precision"]:
        row[f"classifier_{metric}_mean"] = float(clf[f"clf_{metric}_mean"])
        row[f"classifier_{metric}_std"] = float(clf[f"clf_{metric}_std"])
    return row


def _write_latex(rows: list[dict[str, Any]], path: Path) -> None:
    lines = [
        r"\begin{table}[H]",
        r"\centering",
        r"\scriptsize",
        r"\setlength{\tabcolsep}{2pt}",
        r"\renewcommand{\arraystretch}{1.05}",
        r"\caption*{\textbf{Table A10.} Early-warning detector control under degraded threshold labels.}",
        r"\resizebox{\columnwidth}{!}{%",
        r"\begin{tabular}{lrrrrrrr}",
        r"\toprule",
        r"Condition & Gate R & Gate P & Classifier R & Classifier P & Rule R & Rule P & Recovered cells \\",
        r"\midrule",
    ]
    for row in rows:
        recovered = (
            "--"
            if str(row["condition"]) == "Clean live anchors"
            else _pm(row["recovered_cells_vs_rule_mean"], row["recovered_cells_vs_rule_std"])
        )
        lines.append(
            " & ".join(
                [
                    _escape(str(row["condition"])),
                    _fmt(row["gate_recall_mean"]),
                    _fmt(row["gate_precision_mean"]),
                    _fmt(row["classifier_recall_mean"]),
                    _fmt(row["classifier_precision_mean"]),
                    _fmt(row["rule_recall_mean"]),
                    _fmt(row["rule_precision_mean"]),
                    recovered,
                ]
            )
            + r" \\"
        )
    lines.extend(
        [
            r"\bottomrule",
            r"\end{tabular}%",
            r"}",
            r"\vspace{1mm}",
            r"\footnotesize R/P denote recall and precision on early pitch-window cells. The simple classifier is a validation-fit logistic model on the same issue-time anchors; it is a detector control, not a routed forecaster. In sensor-noise rows, gate values are the saved clean-route audit; classifier/rule values are recomputed from noisy anchors.",
            r"\end{table}",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def _mean(values: Any) -> float:
    return float(np.nanmean(np.asarray(values, dtype=np.float64)))


def _std(values: Any) -> float:
    arr = np.asarray(values, dtype=np.float64)
    if arr.size <= 1:
        return 0.0
    return float(np.nanstd(arr, ddof=1))


def _pm(mean: Any, std: Any) -> str:
    return f"{float(mean):.1f} $\\pm$ {float(std):.1f}"


def _fmt(value: Any) -> str:
    return f"{float(value):.3f}"


def _escape(text: str) -> str:
    return (
        text.replace("\\", r"\textbackslash{}")
        .replace("&", r"\&")
        .replace("%", r"\%")
        .replace("_", r"\_")
    )


if __name__ == "__main__":
    main()
