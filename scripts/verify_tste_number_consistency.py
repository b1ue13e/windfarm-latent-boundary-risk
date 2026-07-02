from __future__ import annotations

import argparse
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = ROOT / "artifacts" / "tste_number_consistency_audit"


@dataclass(frozen=True)
class NumberCheck:
    claim_id: str
    source_file: str
    source_value: float
    display_token: str
    required_documents: tuple[str, ...]


def run_number_consistency_audit(
    root: Path | str = ROOT,
    output_dir: Path | str = DEFAULT_OUTPUT_DIR,
) -> Path:
    root = Path(root)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    checks = build_number_checks(root)
    documents = {
        "main": root / "paper_tste_ieee.md",
        "supplementary": root / "paper_tste_supplementary.md",
        "cover": root / "cover_letter_tste.md",
    }
    document_text = {
        name: path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""
        for name, path in documents.items()
    }

    rows: list[dict[str, object]] = []
    for check in checks:
        source_present = Path(root / check.source_file).exists()
        docs_with_token = sorted(
            name for name, text in document_text.items() if check.display_token in text
        )
        missing_documents = [
            name for name in check.required_documents if name not in docs_with_token
        ]
        passed = source_present and not missing_documents and math.isfinite(check.source_value)
        rows.append(
            {
                "claim_id": check.claim_id,
                "source_file": check.source_file,
                "source_value": check.source_value,
                "display_token": check.display_token,
                "required_documents": ";".join(check.required_documents),
                "documents_with_token": ";".join(docs_with_token),
                "missing_documents": ";".join(missing_documents),
                "source_present": bool(source_present),
                "passed": bool(passed),
            }
        )

    frame = pd.DataFrame(rows)
    frame.to_csv(output_dir / "tste_number_consistency_audit.csv", index=False)
    _write_latex(frame, output_dir / "table_tste_number_consistency_audit.tex")

    failed = frame[~frame["passed"].astype(bool)].copy()
    status = "complete_tste_number_consistency" if failed.empty else "blocked_tste_number_mismatch"
    summary = {
        "status": status,
        "n_checks": int(len(frame)),
        "n_failed": int(len(failed)),
        "failed_claims": failed["claim_id"].astype(str).tolist(),
        "documents": {name: str(path) for name, path in documents.items()},
        "outputs": {
            "csv": str(output_dir / "tste_number_consistency_audit.csv"),
            "tex": str(output_dir / "table_tste_number_consistency_audit.tex"),
            "json": str(output_dir / "tste_number_consistency_audit.json"),
        },
        "claim_use": (
            "Submission-facing number consistency audit. Each display token is derived "
            "from a source artifact and required to appear in declared final-facing documents."
        ),
    }
    (output_dir / "tste_number_consistency_audit.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    return output_dir


def build_number_checks(root: Path) -> list[NumberCheck]:
    benchmark = pd.read_csv(root / "artifacts" / "paper_assets" / "tables" / "table_main_benchmark.csv")
    ablation = pd.read_csv(root / "artifacts" / "paper_assets" / "tables" / "table_wtb_ablation.csv")
    early = pd.read_csv(
        root
        / "artifacts"
        / "anchor_stress_early_warning_wtb_strictmask"
        / "anchor_stress_early_warning_summary.csv"
    )
    classifier = pd.read_csv(
        root
        / "artifacts"
        / "early_warning_classifier_baseline_wtb"
        / "early_warning_classifier_baseline_summary.csv"
    )
    consequence = pd.read_csv(
        root
        / "artifacts"
        / "final_evidence_package"
        / "export"
        / "tables"
        / "early_warning_consequence_audit.csv"
    )
    accountability = pd.read_csv(
        root
        / "artifacts"
        / "final_evidence_package"
        / "export"
        / "tables"
        / "accountability_tradeoff.csv"
    )
    reserve = pd.read_csv(
        root
        / "artifacts"
        / "final_evidence_package"
        / "export"
        / "tables"
        / "dispatch_reserve_main_table.csv"
    )
    engineering = pd.read_csv(
        root
        / "artifacts"
        / "final_evidence_package"
        / "export"
        / "tables"
        / "engineering_unit_value_translation.csv"
    )
    anchor_stress = pd.read_csv(root / "artifacts" / "anchor_stress_guard" / "anchor_stress_summary.csv")
    lhb_guard = json.loads(
        (root / "artifacts" / "external_wind_lhb_guard_full_5seed" / "external_wind_guard.json").read_text(
            encoding="utf-8"
        )
    )
    lhb_anchor_guard = json.loads(
        (
            root
            / "artifacts"
            / "external_wind_lhb_anchor_intervention_full"
            / "lhb_anchor_observability_guard.json"
        ).read_text(encoding="utf-8")
    )

    graph = _lookup(benchmark, Panel="WTB", Model="Graph WaveNet")
    best_strict = _best_wtb_strict_cache_baseline(benchmark)
    boundary = _lookup(benchmark, Panel="WTB", Model="Boundary-forced router")
    boundary_ablation = _lookup(ablation, Model="MoE + L_bal + L_align + L_force")
    delay_6 = _lookup(early, variant="canonical", scenario="label_delay", degradation_label="delay_steps=6")
    availability_50 = _lookup(
        early,
        variant="canonical",
        scenario="label_availability",
        degradation_label="available_rate=0.50",
    )
    classifier_clean = _lookup(classifier, scenario="clean", degradation_label="clean_live_anchor")
    consequence_delay_6 = _lookup(consequence, scenario="label_delay", degradation_label="delay_steps=6")
    accountability_boundary = _lookup(accountability, model="Boundary-forced router")
    reserve_boundary_gate = _lookup(
        reserve,
        subset="boundary",
        cost_ratio="10.0",
        policy="Boundary router/gate-bin",
    )
    reserve_boundary_global = _lookup(
        reserve,
        subset="boundary",
        cost_ratio="10.0",
        policy="Boundary router/global",
    )
    reserve_gwn_physical = _lookup(
        reserve,
        subset="boundary",
        cost_ratio="10.0",
        policy="Graph WaveNet/physical-bin",
    )
    engineering_same = _lookup(
        engineering,
        comparison="Boundary gate-bin vs same-router global",
    )
    anchor_no_patv = _lookup(anchor_stress, variant="no_patv")
    anchor_no_pab = _lookup(anchor_stress, variant="no_pab_mean")
    anchor_lag_patv = _lookup(anchor_stress, variant="lagged_patv")
    anchor_lag_pab_wspd = _lookup(anchor_stress, variant="lagged_pab_wspd")

    return [
        _check("graph_wavenet_overall_rmse", "artifacts/paper_assets/tables/table_main_benchmark.csv", _metric_mean(graph["Overall RMSE"]), "{:.2f}", ("main",)),
        _check("best_strict_cache_baseline_overall_rmse", "artifacts/paper_assets/tables/table_main_benchmark.csv", _metric_mean(best_strict["Overall RMSE"]), "{:.2f}", ("main", "cover")),
        _check("boundary_router_overall_rmse", "artifacts/paper_assets/tables/table_main_benchmark.csv", _metric_mean(boundary["Overall RMSE"]), "{:.2f}", ("main", "cover")),
        _check("boundary_router_nmi", "artifacts/paper_assets/tables/table_wtb_ablation.csv", _metric_mean(boundary_ablation["NMI"]), "{:.4f}", ("main",)),
        _check("boundary_router_ari", "artifacts/paper_assets/tables/table_wtb_ablation.csv", _metric_mean(boundary_ablation["ARI"]), "{:.4f}", ("main",)),
        _check("six_step_gate_recall", "artifacts/anchor_stress_early_warning_wtb_strictmask/anchor_stress_early_warning_summary.csv", _num(delay_6["gate_recall_mean"]), "{:.3f}", ("main", "cover")),
        _check("six_step_threshold_recall", "artifacts/anchor_stress_early_warning_wtb_strictmask/anchor_stress_early_warning_summary.csv", _num(delay_6["threshold_recall_mean"]), "{:.3f}", ("main", "cover")),
        _check("fifty_percent_availability_rule_recall", "artifacts/anchor_stress_early_warning_wtb_strictmask/anchor_stress_early_warning_summary.csv", _num(availability_50["threshold_recall_mean"]), "{:.3f}", ("main", "cover")),
        _check("classifier_clean_recall", "artifacts/early_warning_classifier_baseline_wtb/early_warning_classifier_baseline_summary.csv", _num(classifier_clean["clf_recall_mean"]), "{:.3f}", ("main", "cover", "supplementary")),
        _check("classifier_clean_precision", "artifacts/early_warning_classifier_baseline_wtb/early_warning_classifier_baseline_summary.csv", _num(classifier_clean["clf_precision_mean"]), "{:.3f}", ("main", "cover", "supplementary")),
        _check("gate_clean_precision", "artifacts/early_warning_classifier_baseline_wtb/early_warning_classifier_baseline_summary.csv", _num(classifier_clean["gate_precision_mean"]), "{:.3f}", ("main", "supplementary")),
        _check("six_step_recall_gain", "artifacts/final_evidence_package/export/tables/accountability_tradeoff.csv", _num(accountability_boundary["citable_recall_gain"]), "{:+.3f}", ("main",)),
        _check("early_pitch_cells_recovered", "artifacts/final_evidence_package/export/tables/early_warning_consequence_audit.csv", _num(consequence_delay_6["recovered_cells_vs_rule_mean"]), lambda value: f"{int(round(value))}", ("main",)),
        _check("rmse_price_vs_best_strict_cache_baseline", "artifacts/final_evidence_package/export/tables/accountability_tradeoff.csv", _num(accountability_boundary["rmse_penalty_vs_best_strict_cache_baseline"]), "{:.2f}", ("main", "cover")),
        _check("boundary_gate_bin_cost", "artifacts/final_evidence_package/export/tables/dispatch_reserve_main_table.csv", _num(reserve_boundary_gate["total_cost"]), _fmt_millions, ("main",)),
        _check("boundary_global_cost", "artifacts/final_evidence_package/export/tables/dispatch_reserve_main_table.csv", _num(reserve_boundary_global["total_cost"]), _fmt_millions, ("main",)),
        _check("gwn_physical_bin_cost", "artifacts/final_evidence_package/export/tables/dispatch_reserve_main_table.csv", _num(reserve_gwn_physical["total_cost"]), _fmt_millions, ("main", "supplementary")),
        _check("engineering_delta_reserve_mwh", "artifacts/final_evidence_package/export/tables/engineering_unit_value_translation.csv", _num(engineering_same["delta_reserve_mwh_equiv"]), "{:.1f}", ("supplementary",)),
        _check("engineering_avoided_shortage_mwh", "artifacts/final_evidence_package/export/tables/engineering_unit_value_translation.csv", _num(engineering_same["avoided_shortage_mwh_equiv"]), "{:.1f}", ("supplementary",)),
        _check("engineering_delta_cost_mwh", "artifacts/final_evidence_package/export/tables/engineering_unit_value_translation.csv", abs(_num(engineering_same["delta_total_cost_mwh_equiv"])), "{:.1f}", ("supplementary",)),
        _check("engineering_delta_eur_100", "artifacts/final_evidence_package/export/tables/engineering_unit_value_translation.csv", abs(_num(engineering_same["delta_eur_at_100_per_mwh"])), lambda value: f"{int(round(value / 1000.0))}k", ("main", "supplementary")),
        _check("anchor_stress_no_patv_nmi", "artifacts/anchor_stress_guard/anchor_stress_summary.csv", _num(anchor_no_patv["nmi_mean"]), "{:.3f}", ("main",)),
        _check("anchor_stress_no_pab_mean_nmi", "artifacts/anchor_stress_guard/anchor_stress_summary.csv", _num(anchor_no_pab["nmi_mean"]), "{:.3f}", ("main",)),
        _check("anchor_stress_lagged_patv_nmi", "artifacts/anchor_stress_guard/anchor_stress_summary.csv", _num(anchor_lag_patv["nmi_mean"]), "{:.3f}", ("main",)),
        _check("anchor_stress_lagged_pab_wspd_nmi", "artifacts/anchor_stress_guard/anchor_stress_summary.csv", _num(anchor_lag_pab_wspd["nmi_mean"]), "{:.3f}", ("main",)),
        _check("la_haute_borne_routing_nmi", "artifacts/external_wind_lhb_guard_full_5seed/external_wind_guard.json", _num(lhb_guard["mean_nmi"]), "{:.3f}", ("main", "cover")),
        _check("lhb_anchor_patv_zero_nmi", "artifacts/external_wind_lhb_anchor_intervention_full/lhb_anchor_observability_guard.json", _num(lhb_anchor_guard["patv_zero_nmi_mean"]), "{:.3f}", ("main", "supplementary")),
        _check("lhb_anchor_boundary_zero_nmi", "artifacts/external_wind_lhb_anchor_intervention_full/lhb_anchor_observability_guard.json", _num(lhb_anchor_guard["boundary_zero_nmi_mean"]), "{:.3f}", ("main", "supplementary")),
        _check("lhb_anchor_random_physics_nmi", "artifacts/external_wind_lhb_anchor_intervention_full/lhb_anchor_observability_guard.json", _num(lhb_anchor_guard["random_physics_nmi_mean"]), "{:.3f}", ("supplementary",)),
    ]


def _check(
    claim_id: str,
    source_file: str,
    source_value: float,
    formatter: str | Callable[[float], str],
    required_documents: tuple[str, ...],
) -> NumberCheck:
    token = formatter(source_value) if callable(formatter) else formatter.format(source_value)
    return NumberCheck(claim_id, source_file, float(source_value), token, required_documents)


def _lookup(frame: pd.DataFrame, **equals: str) -> pd.Series:
    mask = pd.Series(True, index=frame.index)
    for column, value in equals.items():
        mask &= frame[column].astype(str).eq(str(value))
    rows = frame[mask]
    if rows.empty:
        raise ValueError(f"No row matches {equals}")
    return rows.iloc[0]


def _best_wtb_strict_cache_baseline(frame: pd.DataFrame) -> pd.Series:
    candidates = [
        "Graph WaveNet",
        "Graph Transformer",
        "GAT-GRU",
        "PatchTST",
        "iTransformer",
        "TiDE",
    ]
    rows = []
    for model in candidates:
        try:
            row = _lookup(frame, Panel="WTB", Model=model)
        except ValueError:
            continue
        rmse = _metric_mean(row["Overall RMSE"])
        if math.isfinite(rmse):
            rows.append((rmse, row))
    if not rows:
        raise ValueError("No WTB strict-cache forecasting baseline row found.")
    return min(rows, key=lambda item: item[0])[1]


def _metric_mean(value: object) -> float:
    match = re.search(r"[-+]?\d+(?:\.\d+)?", str(value))
    return float(match.group(0)) if match else math.nan


def _num(value: object) -> float:
    out = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    return float(out) if pd.notna(out) else math.nan


def _fmt_millions(value: float) -> str:
    return f"{value / 1_000_000.0:.2f}M"


def _write_latex(frame: pd.DataFrame, path: Path) -> None:
    lines = [
        r"\begin{table}[H]",
        r"\centering",
        r"\scriptsize",
        r"\setlength{\tabcolsep}{3pt}",
        r"\renewcommand{\arraystretch}{1.05}",
        r"\caption*{\textbf{TSTE number consistency audit.}}",
        r"\begin{tabular}{lll}",
        r"\toprule",
        r"Claim & Display token & Required documents \\",
        r"\midrule",
    ]
    for _, row in frame.iterrows():
        mark = "pass" if bool(row["passed"]) else "fail"
        lines.append(
            " & ".join(
                [
                    _escape(str(row["claim_id"])),
                    _escape(str(row["display_token"])),
                    _escape(str(row["required_documents"])) + f" ({mark})",
                ]
            )
            + r" \\"
        )
    lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}", ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def _escape(text: str) -> str:
    return (
        text.replace("\\", r"\textbackslash{}")
        .replace("&", r"\&")
        .replace("%", r"\%")
        .replace("_", r"\_")
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify TSTE submission-facing numbers.")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    out = run_number_consistency_audit(args.root, args.output_dir)
    summary = json.loads((out / "tste_number_consistency_audit.json").read_text(encoding="utf-8"))
    print(f"TSTE number consistency audit: {summary['status']}")
    print(f"Wrote {out / 'tste_number_consistency_audit.csv'}")
    if summary["status"] != "complete_tste_number_consistency":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
