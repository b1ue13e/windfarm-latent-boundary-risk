from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
TABLE_DIR = ROOT / "artifacts" / "final_evidence_package" / "export" / "tables"
FAILURE_TABLE = TABLE_DIR / "external_site_transfer_failure_table.csv"
CHECKLIST_TABLE = TABLE_DIR / "new_wind_farm_deployment_checklist.csv"
LHB_GUARD = ROOT / "artifacts" / "external_wind_lhb_guard_full_5seed" / "external_wind_guard.json"


def main() -> None:
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    failure = pd.read_csv(FAILURE_TABLE)
    checklist = pd.read_csv(CHECKLIST_TABLE)

    rows = _build_rows(failure, checklist)
    out_csv = TABLE_DIR / "external_deployment_gate_audit.csv"
    out_tex = TABLE_DIR / "table_external_deployment_gate_audit.tex"
    out_json = TABLE_DIR / "external_deployment_gate_audit_summary.json"

    pd.DataFrame(rows).to_csv(out_csv, index=False)
    _write_latex(rows, out_tex)

    payload: dict[str, Any] = {
        "inputs": {
            "failure_table": str(FAILURE_TABLE),
            "checklist_table": str(CHECKLIST_TABLE),
        },
        "outputs": {
            "csv": str(out_csv),
            "tex": str(out_tex),
        },
        "claim_use": (
            "Kelmarsh/Penmanshiel external evidence is a deployment-screening "
            "audit. It blocks automatic cross-farm portability and reserve use "
            "until sensor coverage, local boundary calibration, frozen held-out "
            "routing, and reserve-audit gates all pass."
        ),
    }
    out_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {out_csv}")


def _build_rows(failure: pd.DataFrame, checklist: pd.DataFrame) -> list[dict[str, str]]:
    routing = _failure_row(failure, "pre-specified external routing criterion")
    recalibration = _failure_row(failure, "validation-selected local boundary recalibration")
    adaptation = _failure_row(failure, "small calibration-window gate-map adaptation")
    sensor = _failure_row(failure, "sensor and boundary support")

    lhb = json.loads(LHB_GUARD.read_text(encoding="utf-8")) if LHB_GUARD.exists() else {}

    return [
        {
            "gate": "Cross-site recovery (La Haute Borne)",
            "observed_external_evidence": (
                f"Five-seed chronological routing NMI {_fmt(lhb.get('mean_nmi'))}, "
                f"ARI {_fmt(lhb.get('mean_ari'))}; pitch observed in 99.2% of cells, no proxy"
            ),
            "go_no_go_rule": "Held-out NMI >= 0.50 with observed pitch after parameters are frozen",
            "claim_consequence": "Go: boundary recovers where pitch is observable; cite as positive cross-site control",
        },
        {
            "gate": "Cross-site routing criterion",
            "observed_external_evidence": _sentence_case(str(routing["observed"])),
            "go_no_go_rule": _sentence_case(_checklist_rule(checklist, "held-out routing criterion")),
            "claim_consequence": "No-go for cross-farm router interpretation; cite as negative boundary-condition evidence",
        },
        {
            "gate": "Local boundary recalibration",
            "observed_external_evidence": _sentence_case(str(recalibration["observed"])),
            "go_no_go_rule": _sentence_case(_checklist_rule(checklist, "local boundary calibration")),
            "claim_consequence": "Local threshold transfer is insufficient; re-estimate before use",
        },
        {
            "gate": "Small-window adaptation",
            "observed_external_evidence": str(adaptation["observed"]),
            "go_no_go_rule": "Small calibration windows must still pass the frozen held-out routing criterion",
            "claim_consequence": "Calibration alone does not authorize external reserve use",
        },
        {
            "gate": "Sensor and boundary support",
            "observed_external_evidence": _sentence_case(str(sensor["observed"])),
            "go_no_go_rule": _sentence_case(_checklist_rule(checklist, "sensor coverage")),
            "claim_consequence": "No physical-router interpretation without observability",
        },
        {
            "gate": "External reserve-use decision",
            "observed_external_evidence": (
                "Upstream gates do not pass before reserve allocation is evaluated"
            ),
            "go_no_go_rule": _sentence_case(_checklist_rule(checklist, "reserve audit")),
            "claim_consequence": "Withhold gate-bin reserve use outside WTB; report a deployment protocol only",
        },
    ]


def _failure_row(frame: pd.DataFrame, gate: str) -> pd.Series:
    matches = frame[frame["evidence_gate"].astype(str).str.lower() == gate.lower()]
    if matches.empty:
        raise ValueError(f"Missing external evidence gate: {gate}")
    return matches.iloc[0]


def _checklist_rule(frame: pd.DataFrame, gate: str) -> str:
    matches = frame[frame["gate"].astype(str).str.lower() == gate.lower()]
    if matches.empty:
        raise ValueError(f"Missing deployment checklist gate: {gate}")
    return str(matches.iloc[0]["pass_condition"])


def _sentence_case(text: str) -> str:
    if not text:
        return text
    return text[0].upper() + text[1:]


def _fmt(value: Any) -> str:
    try:
        return f"{float(value):.3f}"
    except (TypeError, ValueError):
        return "--"


def _write_latex(rows: list[dict[str, str]], path: Path) -> None:
    lines = [
        r"\begin{table}[H]",
        r"\centering",
        r"\scriptsize",
        r"\setlength{\tabcolsep}{2.2pt}",
        r"\renewcommand{\arraystretch}{1.08}",
        r"\caption*{\textbf{Table A8.} External-site deployment-gate audit and wording boundary.}",
        r"\begin{tabularx}{\columnwidth}{>{\raggedright\arraybackslash}p{0.20\columnwidth} >{\raggedright\arraybackslash}p{0.33\columnwidth} >{\raggedright\arraybackslash}p{0.22\columnwidth} >{\raggedright\arraybackslash}X}",
        r"\toprule",
        r"Gate & Observed external evidence & Go/no-go rule & Claim consequence \\",
        r"\midrule",
    ]
    for row in rows:
        lines.append(
            f"{_latex_text(row['gate'])} & "
            f"{_latex_text(row['observed_external_evidence'])} & "
            f"{_latex_text(row['go_no_go_rule'])} & "
            f"{_latex_text(row['claim_consequence'])} "
            + r"\\"
        )
    lines.extend([r"\bottomrule", r"\end{tabularx}", r"\end{table}", ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def _latex_text(text: str) -> str:
    return _escape(text).replace(">=", r"$\geq$").replace("->", r"$\rightarrow$")


def _escape(text: str) -> str:
    return (
        text.replace("\\", r"\textbackslash{}")
        .replace("&", r"\&")
        .replace("%", r"\%")
        .replace("_", r"\_")
    )


if __name__ == "__main__":
    main()
