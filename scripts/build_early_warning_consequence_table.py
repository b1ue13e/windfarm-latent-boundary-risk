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
OUT_TABLES = ROOT / "artifacts" / "final_evidence_package" / "export" / "tables"

CONDITIONS = [
    ("Delay, 1 step", "label_delay", "delay_steps=1"),
    ("Delay, 3 steps", "label_delay", "delay_steps=3"),
    ("Delay, 6 steps", "label_delay", "delay_steps=6"),
    ("50% label availability", "label_availability", "available_rate=0.50"),
    ("25% label availability", "label_availability", "available_rate=0.25"),
    ("Sensor noise, strongest", "threshold_sensor_noise", "wspd_sd=1.00;pab_sd=2.00"),
]


def main() -> None:
    OUT_TABLES.mkdir(parents=True, exist_ok=True)
    raw = pd.read_csv(RAW)
    rows = [_condition_summary(raw, label, scenario, degradation) for label, scenario, degradation in CONDITIONS]

    out_csv = OUT_TABLES / "early_warning_consequence_audit.csv"
    out_tex = OUT_TABLES / "table_early_warning_consequence_audit.tex"
    out_json = OUT_TABLES / "early_warning_consequence_audit_summary.json"

    pd.DataFrame(rows).to_csv(out_csv, index=False)
    _write_latex(rows, out_tex)
    payload: dict[str, Any] = {
        "inputs": {"raw_csv": str(RAW)},
        "outputs": {"csv": str(out_csv), "tex": str(out_tex)},
        "claim_use": (
            "Detection-consequence audit for the label-degradation result. Counts are "
            "test-set turbine-time cells per seed inside the six-step MPPT-to-pitch "
            "window; they are not MWh, currency, or dispatch-cost estimates."
        ),
    }
    out_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {out_csv}")


def _condition_summary(raw: pd.DataFrame, label: str, scenario: str, degradation: str) -> dict[str, Any]:
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
    return row


def _write_latex(rows: list[dict[str, Any]], path: Path) -> None:
    lines = [
        r"\begin{table}[H]",
        r"\centering",
        r"\scriptsize",
        r"\setlength{\tabcolsep}{2.4pt}",
        r"\renewcommand{\arraystretch}{1.08}",
        r"\caption*{\textbf{Table A9.} Early-warning detection consequence under degraded threshold labels.}",
        r"\begin{tabularx}{\columnwidth}{>{\raggedright\arraybackslash}p{0.28\columnwidth} >{\centering\arraybackslash}p{0.22\columnwidth} >{\centering\arraybackslash}p{0.24\columnwidth} >{\centering\arraybackslash}X}",
        r"\toprule",
        r"Condition & Gate detected / missed & Degraded rule detected / missed & Recovered cells \\",
        r"\midrule",
    ]
    for row in rows:
        gate = (
            f"{_pm(row['gate_detected_cells_mean'], row['gate_detected_cells_std'])} / "
            f"{_pm(row['gate_missed_cells_mean'], row['gate_missed_cells_std'])}"
        )
        rule = (
            f"{_pm(row['rule_detected_cells_mean'], row['rule_detected_cells_std'])} / "
            f"{_pm(row['rule_missed_cells_mean'], row['rule_missed_cells_std'])}"
        )
        recovered = _pm(row["recovered_cells_vs_rule_mean"], row["recovered_cells_vs_rule_std"])
        lines.append(f"{_escape(str(row['condition']))} & {gate} & {rule} & {recovered} " + r"\\")
    lines.extend([r"\bottomrule", r"\end{tabularx}", r"\end{table}", ""])
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


def _escape(text: str) -> str:
    return (
        text.replace("\\", r"\textbackslash{}")
        .replace("&", r"\&")
        .replace("%", r"\%")
        .replace("_", r"\_")
    )


if __name__ == "__main__":
    main()
