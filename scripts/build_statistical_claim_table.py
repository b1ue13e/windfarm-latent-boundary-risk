from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT_TABLES = ROOT / "artifacts" / "final_evidence_package" / "export" / "tables"
PAIRED = ROOT / "artifacts" / "strictmask_combined_reviewer_stats" / "paired_effects_summary.csv"
MULTIPLICITY = ROOT / "artifacts" / "strictmask_combined_reviewer_stats" / "paired_multiplicity_table.csv"
RESERVE = ROOT / "artifacts" / "reserve_quantile_baseline" / "reserve_quantile_baseline_bootstrap.csv"

REFERENCE = "MoE + L_bal + L_align + L_force"


def main() -> None:
    OUT_TABLES.mkdir(parents=True, exist_ok=True)
    paired = pd.read_csv(PAIRED)
    multiplicity = pd.read_csv(MULTIPLICITY)
    reserve = pd.read_csv(RESERVE)

    rows = [
        _rmse_row(
            paired,
            multiplicity,
            comparator="Graph WaveNet",
            slice_name="overall",
            label="Accuracy price vs Graph WaveNet",
            interpretation="Boundary router is significantly worse on headline RMSE",
        ),
        _rmse_row(
            paired,
            multiplicity,
            comparator="Graph WaveNet",
            slice_name="boundary_band",
            label="Boundary-band accuracy price",
            interpretation="The price also appears in the boundary window",
        ),
        _gate_row(
            paired,
            multiplicity,
            metric="nmi",
            label="Gate NMI vs full physics-aligned MoE",
            interpretation="Positive but not FDR-significant; cite as bounded mechanism contrast",
        ),
        _gate_row(
            paired,
            multiplicity,
            metric="ari",
            label="Gate ARI vs full physics-aligned MoE",
            interpretation="Positive but not FDR-significant; avoid superiority wording",
        ),
        _reserve_row(
            reserve,
            candidate="Graph WaveNet/physical_bin_quantile",
            reference="Boundary-forced router/gate_bin_quantile",
            metric="total_cost",
            label="Boundary quantile cost vs GWN physical bin",
            interpretation="CI crosses zero; reserve cost should remain a diagnostic claim",
        ),
        _reserve_row(
            reserve,
            candidate="Graph WaveNet/physical_bin_quantile",
            reference="Boundary-forced router/gate_bin_quantile",
            metric="violation_rate",
            label="Boundary quantile violation vs GWN physical bin",
            interpretation="CI crosses zero; no universal reserve-policy optimality claim",
        ),
    ]

    table = pd.DataFrame(rows)
    table.to_csv(OUT_TABLES / "statistical_claim_boundaries.csv", index=False)
    _write_latex(table, OUT_TABLES / "table_statistical_claim_boundaries.tex")
    summary = {
        "inputs": {
            "paired_effects_summary": str(PAIRED),
            "paired_multiplicity_table": str(MULTIPLICITY),
            "reserve_quantile_bootstrap": str(RESERVE),
        },
        "outputs": {
            "csv": str(OUT_TABLES / "statistical_claim_boundaries.csv"),
            "tex": str(OUT_TABLES / "table_statistical_claim_boundaries.tex"),
        },
        "claim_use": (
            "Reviewer-facing statistical boundary table. It documents significant RMSE price, "
            "non-significant gate-alignment superiority versus the full MoE comparator, and reserve "
            "bootstrap intervals that cross zero."
        ),
    }
    (OUT_TABLES / "statistical_claim_boundaries_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(f"Wrote {OUT_TABLES / 'statistical_claim_boundaries.csv'}")


def _rmse_row(
    paired: pd.DataFrame,
    multiplicity: pd.DataFrame,
    *,
    comparator: str,
    slice_name: str,
    label: str,
    interpretation: str,
) -> dict[str, Any]:
    row = _lookup(
        paired,
        reference_model=REFERENCE,
        comparator_model=comparator,
        split="test",
        slice=slice_name,
        metric="rmse",
    )
    mult = _lookup(
        multiplicity,
        reference_model=REFERENCE,
        comparator_model=comparator,
        split="test",
        slice=slice_name,
        metric="rmse",
    )
    return {
        "claim": label,
        "statistic": "Delta RMSE",
        "estimate": _num(row.get("delta_rmse_reference_minus_comparator_mean")),
        "ci_low": math.nan,
        "ci_high": math.nan,
        "p_value": _num(mult.get("p_value_bh")),
        "n": int(_num(row.get("n_tested_seed_pairs"))),
        "result": "FDR significant" if bool(int(_num(mult.get("reject_fdr_0p05")))) else "not significant",
        "interpretation": interpretation,
    }


def _gate_row(
    paired: pd.DataFrame,
    multiplicity: pd.DataFrame,
    *,
    metric: str,
    label: str,
    interpretation: str,
) -> dict[str, Any]:
    row = _lookup(
        paired,
        reference_model=REFERENCE,
        comparator_model="Physics-Aligned MoE",
        split="test",
        slice="gate_alignment",
        metric=metric,
    )
    mult = _lookup(
        multiplicity,
        reference_model=REFERENCE,
        comparator_model="Physics-Aligned MoE",
        split="test",
        slice="gate_alignment",
        metric=metric,
    )
    return {
        "claim": label,
        "statistic": f"Delta {metric.upper()}",
        "estimate": _num(row.get("delta_reference_minus_comparator_mean")),
        "ci_low": _num(row.get("delta_reference_minus_comparator_ci_low")),
        "ci_high": _num(row.get("delta_reference_minus_comparator_ci_high")),
        "p_value": _num(mult.get("p_value_bh")),
        "n": int(_num(row.get("n_tested_seed_pairs"))),
        "result": "FDR significant" if bool(int(_num(mult.get("reject_fdr_0p05")))) else "not significant",
        "interpretation": interpretation,
    }


def _reserve_row(
    reserve: pd.DataFrame,
    *,
    candidate: str,
    reference: str,
    metric: str,
    label: str,
    interpretation: str,
) -> dict[str, Any]:
    row = _lookup(
        reserve,
        subset="boundary",
        candidate=candidate,
        reference=reference,
        metric=metric,
    )
    low = _num(row.get("ci_low"))
    high = _num(row.get("ci_high"))
    crosses = low <= 0.0 <= high
    return {
        "claim": label,
        "statistic": "Delta " + metric.replace("_", " "),
        "estimate": _num(row.get("observed_delta_candidate_minus_gate")),
        "ci_low": low,
        "ci_high": high,
        "p_value": math.nan,
        "n": int(_num(row.get("n_seed_pairs"))),
        "result": "CI crosses zero" if crosses else "CI excludes zero",
        "interpretation": interpretation,
    }


def _lookup(frame: pd.DataFrame, **equals: str) -> pd.Series:
    mask = pd.Series(True, index=frame.index)
    for column, value in equals.items():
        mask &= frame[column].astype(str).eq(str(value))
    rows = frame[mask]
    if rows.empty:
        raise ValueError(f"No row matches {equals}")
    return rows.iloc[0]


def _num(value: Any) -> float:
    out = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    return float(out) if pd.notna(out) else math.nan


def _fmt(value: Any, digits: int = 3) -> str:
    value_float = _num(value)
    if not math.isfinite(value_float):
        return "--"
    return f"{value_float:.{digits}f}"


def _fmt_ci(row: pd.Series) -> str:
    low = _num(row.get("ci_low"))
    high = _num(row.get("ci_high"))
    if not math.isfinite(low) or not math.isfinite(high):
        return "--"
    return f"[{_fmt(low)}, {_fmt(high)}]"


def _fmt_p(value: Any) -> str:
    value_float = _num(value)
    if not math.isfinite(value_float):
        return "--"
    if value_float < 0.001:
        return "<0.001"
    return f"{value_float:.3f}"


def _write_latex(frame: pd.DataFrame, path: Path) -> None:
    lines = [
        r"\begin{table}[H]",
        r"\centering",
        r"\scriptsize",
        r"\setlength{\tabcolsep}{2.5pt}",
        r"\renewcommand{\arraystretch}{1.08}",
        r"\caption*{\textbf{Table A6.} Statistical claim boundaries used for reviewer-facing wording.}",
        r"\begin{tabularx}{\columnwidth}{>{\raggedright\arraybackslash}p{0.25\columnwidth} >{\centering\arraybackslash}p{0.13\columnwidth} >{\centering\arraybackslash}p{0.15\columnwidth} >{\centering\arraybackslash}p{0.11\columnwidth} >{\raggedright\arraybackslash}X}",
        r"\toprule",
        r"Claim & Estimate & 95\% CI & $p_{\mathrm{BH}}$ & Wording consequence \\",
        r"\midrule",
    ]
    for _, row in frame.iterrows():
        lines.append(
            " & ".join(
                [
                    _escape(str(row["claim"])),
                    _fmt_table_estimate(row),
                    _fmt_table_ci(row),
                    _fmt_p(row.get("p_value")),
                    _escape(str(row["interpretation"])),
                ]
            )
            + r" \\"
        )
    lines.extend([r"\bottomrule", r"\end{tabularx}", r"\end{table}", ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def _fmt_table_estimate(row: pd.Series) -> str:
    statistic = str(row.get("statistic", ""))
    value = _num(row.get("estimate"))
    if not math.isfinite(value):
        return "--"
    if "total cost" in statistic:
        return f"{value / 1_000_000:.3f}M"
    return _fmt(value)


def _fmt_table_ci(row: pd.Series) -> str:
    statistic = str(row.get("statistic", ""))
    low = _num(row.get("ci_low"))
    high = _num(row.get("ci_high"))
    if not math.isfinite(low) or not math.isfinite(high):
        return "--"
    if "total cost" in statistic:
        return f"[{low / 1_000_000:.3f}M, {high / 1_000_000:.3f}M]"
    return _fmt_ci(row)


def _escape(text: str) -> str:
    return (
        text.replace("\\", r"\textbackslash{}")
        .replace("&", r"\&")
        .replace("%", r"\%")
        .replace("_", r"\_")
    )


if __name__ == "__main__":
    main()
