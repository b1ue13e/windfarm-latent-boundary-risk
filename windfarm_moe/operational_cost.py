from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .utils import ensure_dir, load_json, save_json

DEFAULT_ENGINEERING_RESERVE_PRICES = (50.0, 100.0, 200.0)


def run_toy_operational_cost(
    *,
    decision_dir: Path | str,
    probabilistic_dir: Path | str,
    output_dir: Path | str,
    main_ratio: float = 10.0,
) -> Path:
    """Build a normalized single-wind-farm operational cost proxy table.

    This is deliberately not a market-clearing or unit-commitment model. It
    combines reserve procurement energy and shortage penalty already measured by
    the frozen reserve audits, so the manuscript can discuss operational
    consequence without overstating dispatch realism.
    """

    decision_path = Path(decision_dir)
    probabilistic_path = Path(probabilistic_dir)
    out_dir = ensure_dir(output_dir)

    decision_rows = _decision_rows(decision_path, main_ratio=float(main_ratio))
    probabilistic_rows = _probabilistic_rows(probabilistic_path, main_ratio=float(main_ratio))
    combined = pd.concat([decision_rows, probabilistic_rows], ignore_index=True, sort=False)
    combined = combined[combined["subset"].astype(str).isin(["full", "boundary"])].copy()
    if not combined.empty:
        combined["reserve_procurement_cost"] = pd.to_numeric(combined["reserve_energy"], errors="coerce")
        combined["shortage_penalty_cost"] = pd.to_numeric(combined["shortage_energy"], errors="coerce") * float(main_ratio)
        combined["toy_total_cost"] = combined["reserve_procurement_cost"] + combined["shortage_penalty_cost"]
        combined["claim_scope"] = "normalized_single_wind_farm_proxy_not_market_dispatch"
        combined = _add_reference_deltas(combined)
    else:
        combined = pd.DataFrame(
            columns=[
                "subset",
                "policy_label",
                "reserve_procurement_cost",
                "shortage_penalty_cost",
                "toy_total_cost",
                "claim_scope",
            ]
        )

    readable = _readable_table(combined)
    combined.to_csv(out_dir / "reserve_toy_operational_cost_raw.csv", index=False)
    readable.to_csv(out_dir / "reserve_toy_operational_cost.csv", index=False)
    _write_latex_table(readable, out_dir / "reserve_toy_operational_cost.tex", main_ratio=float(main_ratio))
    save_json(
        out_dir / "reserve_toy_operational_cost.json",
        {
            "decision_dir": str(decision_dir),
            "probabilistic_dir": str(probabilistic_dir),
            "main_ratio": float(main_ratio),
            "claim_use": (
                "Normalized proxy operational cost: reserve procurement energy plus "
                "rho-weighted shortage energy. Not unit commitment, OPF, market clearing, "
                "or real dispatch integration."
            ),
            "outputs": {
                "summary_csv": str(out_dir / "reserve_toy_operational_cost.csv"),
                "raw_csv": str(out_dir / "reserve_toy_operational_cost_raw.csv"),
                "tex": str(out_dir / "reserve_toy_operational_cost.tex"),
            },
        },
    )
    return out_dir


def run_engineering_unit_value_translation(
    *,
    decision_dir: Path | str,
    toy_cost_dir: Path | str,
    output_dir: Path | str,
    main_ratio: float = 10.0,
    reserve_prices_eur_per_mwh: tuple[float, ...] | list[float] = DEFAULT_ENGINEERING_RESERVE_PRICES,
) -> Path:
    """Translate the normalized reserve audit into bounded engineering units.

    The WTB active-power target is in kW and the reserve audit multiplies each
    valid forecast cell by the configured step length in hours. Dividing these
    kWh-equivalent totals by 1000 gives an engineering-unit accounting view.
    The result is still a rolling forecast-cell accounting table, not delivered
    market energy or a settlement model.
    """

    decision_path = Path(decision_dir)
    toy_path = Path(toy_cost_dir)
    out_dir = ensure_dir(output_dir)
    raw_path = toy_path / "reserve_toy_operational_cost_raw.csv"
    if not raw_path.exists():
        raise FileNotFoundError(f"Missing toy operational-cost raw table: {raw_path}")

    config_path = decision_path / "reserve_decision_config.json"
    config = load_json(config_path) if config_path.exists() else {}
    frame = pd.read_csv(raw_path)
    frame = frame[
        np.isclose(pd.to_numeric(frame["cost_ratio"], errors="coerce"), float(main_ratio))
        & frame["source"].astype(str).eq("reserve_decision")
    ].copy()
    if frame.empty:
        raise ValueError("No reserve-decision rows available for engineering-unit translation.")

    comparisons = [
        {
            "comparison": "Boundary gate-bin vs same-router global",
            "subset": "boundary",
            "candidate": "Boundary-forced router/gate-bin",
            "baseline": "Boundary-forced router/global",
            "claim_scope": "same-model transition-window diagnostic",
            "wording": "Use as bounded boundary-window value, not cross-backbone superiority.",
        },
        {
            "comparison": "Boundary gate-bin vs GWN physical-bin",
            "subset": "boundary",
            "candidate": "Boundary-forced router/gate-bin",
            "baseline": "Graph WaveNet/physical-bin",
            "claim_scope": "competitive physical-bin comparator",
            "wording": "Shows gate-bin is close to a strong physical-bin comparator; not a lower-cost claim.",
        },
        {
            "comparison": "Boundary gate-bin vs GWN global full sample",
            "subset": "full",
            "candidate": "Boundary-forced router/gate-bin",
            "baseline": "Graph WaveNet/global",
            "claim_scope": "full-sample claim boundary",
            "wording": "Blocks system-wide dispatch or full-sample reserve-superiority wording.",
        },
    ]
    rows = [
        row
        for row in (_engineering_comparison_row(frame, spec, reserve_prices_eur_per_mwh) for spec in comparisons)
        if row is not None
    ]
    if not rows:
        raise ValueError("No configured engineering-unit comparisons could be computed.")

    table = pd.DataFrame(rows)
    csv_path = out_dir / "engineering_unit_value_translation.csv"
    tex_path = out_dir / "table_engineering_unit_value_translation.tex"
    json_path = out_dir / "engineering_unit_value_translation_summary.json"
    table.to_csv(csv_path, index=False)
    _write_engineering_value_latex(table, tex_path, main_ratio=float(main_ratio))

    save_json(
        json_path,
        {
            "inputs": {
                "reserve_toy_operational_cost_raw": str(raw_path),
                "reserve_decision_config": str(config_path) if config_path.exists() else None,
            },
            "outputs": {"csv": str(csv_path), "tex": str(tex_path)},
            "assumptions": {
                "target_power_unit": "kW for WTB Patv",
                "step_hours": float(config.get("dt", 1.0 / 6.0)),
                "conversion": "reserve_energy and shortage_energy are kWh-equivalent totals; divide by 1000 for MWh-equivalent",
                "monetary_translation": "Illustrative cost-scale marker = delta reserve-cost-equivalent MWh * assumed reserve carrying cost; not settlement value",
                "reserve_prices_eur_per_mwh": [float(value) for value in reserve_prices_eur_per_mwh],
                "claim_boundary": (
                    "Rolling 24-step forecast-cell accounting only; not delivered MWh, "
                    "market clearing, unit commitment, OPF, or security-constrained dispatch."
                ),
            },
        },
    )
    return out_dir


def _decision_rows(decision_dir: Path, *, main_ratio: float) -> pd.DataFrame:
    path = decision_dir / "reserve_decision_by_ratio.csv"
    if not path.exists():
        return pd.DataFrame()
    frame = pd.read_csv(path)
    frame = frame[np.isclose(pd.to_numeric(frame["cost_ratio"], errors="coerce"), float(main_ratio))].copy()
    rows: list[dict[str, Any]] = []
    for _, row in frame.iterrows():
        model = str(row.get("model", ""))
        policy = str(row.get("policy", ""))
        if model not in {"Graph WaveNet", "Boundary-forced router"}:
            continue
        if policy not in {"global", "physical-bin", "gate-bin"}:
            continue
        if model == "Graph WaveNet" and policy == "gate-bin":
            continue
        rows.append(_normalized_row(row, policy_label=f"{model}/{policy}", source="reserve_decision"))
    return pd.DataFrame(rows)


def _engineering_comparison_row(
    frame: pd.DataFrame,
    spec: dict[str, str],
    reserve_prices: tuple[float, ...] | list[float],
) -> dict[str, Any] | None:
    candidate = _maybe_policy_row(frame, spec["subset"], spec["candidate"])
    baseline = _maybe_policy_row(frame, spec["subset"], spec["baseline"])
    if candidate is None or baseline is None:
        return None

    reserve_delta_kwh = _num(candidate.get("reserve_energy")) - _num(baseline.get("reserve_energy"))
    shortage_delta_kwh = _num(candidate.get("shortage_energy")) - _num(baseline.get("shortage_energy"))
    total_delta_kwh_equiv = _num(candidate.get("toy_total_cost")) - _num(baseline.get("toy_total_cost"))
    row: dict[str, Any] = {
        "comparison": spec["comparison"],
        "subset": spec["subset"],
        "candidate": spec["candidate"],
        "baseline": spec["baseline"],
        "claim_scope": spec["claim_scope"],
        "delta_reserve_mwh_equiv": reserve_delta_kwh / 1000.0,
        "delta_shortage_mwh_equiv": shortage_delta_kwh / 1000.0,
        "avoided_shortage_mwh_equiv": -shortage_delta_kwh / 1000.0,
        "delta_total_cost_mwh_equiv": total_delta_kwh_equiv / 1000.0,
        "delta_violation_rate": _num(candidate.get("violation_rate")) - _num(baseline.get("violation_rate")),
        "wording": spec["wording"],
    }
    for price in reserve_prices:
        label = _price_label(float(price))
        row[f"delta_eur_at_{label}_per_mwh"] = row["delta_total_cost_mwh_equiv"] * float(price)
    return row


def _maybe_policy_row(frame: pd.DataFrame, subset: str, policy_label: str) -> pd.Series | None:
    rows = frame[
        frame["subset"].astype(str).eq(str(subset))
        & frame["policy_label"].astype(str).eq(str(policy_label))
    ]
    if rows.empty:
        return None
    return rows.iloc[0]


def _price_label(value: float) -> str:
    if float(value).is_integer():
        return str(int(value))
    return str(value).replace(".", "p")


def _write_engineering_value_latex(frame: pd.DataFrame, path: Path, *, main_ratio: float) -> None:
    lines = [
        r"\begin{table}[H]",
        r"\centering",
        r"\scriptsize",
        r"\setlength{\tabcolsep}{3.0pt}",
        r"\renewcommand{\arraystretch}{1.03}",
        r"\caption*{\textbf{Table A12.} Engineering-unit reserve-value translation at $\rho="
        + f"{main_ratio:g}"
        + r"$.}",
        r"\begin{tabularx}{\columnwidth}{>{\raggedright\arraybackslash}X >{\centering\arraybackslash}p{0.15\columnwidth} >{\centering\arraybackslash}p{0.16\columnwidth} >{\centering\arraybackslash}p{0.14\columnwidth} >{\centering\arraybackslash}p{0.15\columnwidth}}",
        r"\toprule",
        r"Comparison & $\Delta$ reserve & Avoided shortage & $\Delta$ cost & Cost-scale@100 \\",
        r"\midrule",
    ]
    for _, row in frame.iterrows():
        lines.append(
            " & ".join(
                [
                    _escape(str(row["comparison"])),
                    _fmt_signed(row.get("delta_reserve_mwh_equiv"), 1),
                    _fmt_signed(row.get("avoided_shortage_mwh_equiv"), 1),
                    _fmt_signed(row.get("delta_total_cost_mwh_equiv"), 1),
                    _fmt_signed_m_eur(row.get("delta_eur_at_100_per_mwh")),
                ]
            )
            + r" \\"
        )
    lines.extend(
        [
            r"\bottomrule",
            r"\end{tabularx}",
            r"\vspace{1mm}",
            r"\footnotesize Values are MWh-equivalent forecast-cell accounting with $\Delta t=1/6$ h. Cost-scale@100 is an illustrative reserve-cost scale marker at 100 EUR/MWh, not market revenue, settlement value, OPF, or unit-commitment output. Use same-router/global as the bounded boundary-window diagnostic; physical-bin and full-sample rows block reserve superiority.",
            r"\end{table}",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def _probabilistic_rows(probabilistic_dir: Path, *, main_ratio: float) -> pd.DataFrame:
    path = probabilistic_dir / "reserve_quantile_baseline.csv"
    if not path.exists():
        return pd.DataFrame()
    frame = pd.read_csv(path)
    frame = frame[np.isclose(pd.to_numeric(frame["cost_ratio"], errors="coerce"), float(main_ratio))].copy()
    rows: list[dict[str, Any]] = []
    for _, row in frame.iterrows():
        model = str(row.get("model", ""))
        baseline = str(row.get("baseline", ""))
        if model not in {"Graph WaveNet", "Boundary-forced router"}:
            continue
        if baseline not in {"global_quantile", "physical_bin_quantile", "gate_bin_quantile"}:
            continue
        if model == "Graph WaveNet" and baseline == "gate_bin_quantile":
            continue
        rows.append(_normalized_row(row, policy_label=f"{model}/{baseline}", source="probabilistic_baseline"))
    return pd.DataFrame(rows)


def _normalized_row(row: pd.Series, *, policy_label: str, source: str) -> dict[str, Any]:
    return {
        "subset": row.get("subset", ""),
        "cost_ratio": _num(row.get("cost_ratio")),
        "source": source,
        "policy_label": policy_label,
        "n_runs": int(_num(row.get("n_runs"))) if np.isfinite(_num(row.get("n_runs"))) else 0,
        "total_cost": _num(row.get("total_cost_mean")),
        "violation_rate": _num(row.get("violation_rate_mean")),
        "reserve_energy": _num(row.get("reserve_energy_mean")),
        "shortage_energy": _num(row.get("shortage_energy_mean")),
        "valid_cells": _num(row.get("valid_cells_mean")),
    }


def _add_reference_deltas(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    for column in [
        "delta_toy_total_cost_vs_boundary_router_global",
        "delta_shortage_penalty_vs_boundary_router_global",
        "delta_violation_rate_vs_boundary_router_global",
    ]:
        out[column] = np.nan
    for subset in out["subset"].astype(str).unique():
        selector = out["subset"].astype(str).eq(subset)
        ref = out[selector & out["policy_label"].astype(str).eq("Boundary-forced router/global")]
        if ref.empty:
            continue
        ref_row = ref.iloc[0]
        idx = out[selector].index
        out.loc[idx, "delta_toy_total_cost_vs_boundary_router_global"] = (
            pd.to_numeric(out.loc[idx, "toy_total_cost"], errors="coerce") - _num(ref_row.get("toy_total_cost"))
        )
        out.loc[idx, "delta_shortage_penalty_vs_boundary_router_global"] = (
            pd.to_numeric(out.loc[idx, "shortage_penalty_cost"], errors="coerce")
            - _num(ref_row.get("shortage_penalty_cost"))
        )
        out.loc[idx, "delta_violation_rate_vs_boundary_router_global"] = (
            pd.to_numeric(out.loc[idx, "violation_rate"], errors="coerce") - _num(ref_row.get("violation_rate"))
        )
    return out


def _readable_table(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame
    keep = frame[
        frame["policy_label"].astype(str).isin(
            [
                "Graph WaveNet/global",
                "Graph WaveNet/physical-bin",
                "Graph WaveNet/global_quantile",
                "Graph WaveNet/physical_bin_quantile",
                "Boundary-forced router/global",
                "Boundary-forced router/gate-bin",
                "Boundary-forced router/gate_bin_quantile",
            ]
        )
    ].copy()
    if keep.empty:
        keep = frame.copy()
    keep = keep.sort_values(["subset", "toy_total_cost", "policy_label"], na_position="last")
    return keep[
        [
            "subset",
            "policy_label",
            "source",
            "toy_total_cost",
            "reserve_procurement_cost",
            "shortage_penalty_cost",
            "violation_rate",
            "delta_toy_total_cost_vs_boundary_router_global",
            "delta_shortage_penalty_vs_boundary_router_global",
            "delta_violation_rate_vs_boundary_router_global",
            "claim_scope",
        ]
    ]


def _write_latex_table(frame: pd.DataFrame, path: Path, *, main_ratio: float) -> None:
    lines = [
        r"\begin{table}[H]",
        r"\centering",
        r"\footnotesize",
        r"\setlength{\tabcolsep}{4pt}",
        r"\renewcommand{\arraystretch}{1.08}",
        rf"\caption{{Normalized toy operational cost at $\rho={main_ratio:g}$.}}",
        r"\begin{tabular}{llrrrr}",
        r"\toprule",
        r"Subset & Policy & Toy cost & Reserve cost & Shortage penalty & Violation \\",
        r"\midrule",
    ]
    if not frame.empty:
        for _, row in frame.iterrows():
            lines.append(
                " & ".join(
                    [
                        str(row["subset"]).replace("_", r"\_"),
                        str(row["policy_label"]).replace("_", r"\_"),
                        _fmt_m(row.get("toy_total_cost")),
                        _fmt_m(row.get("reserve_procurement_cost")),
                        _fmt_m(row.get("shortage_penalty_cost")),
                        _fmt(row.get("violation_rate"), 4),
                    ]
                )
                + r" \\"
            )
    lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}", ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def _num(value: Any) -> float:
    out = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    return float(out) if pd.notna(out) else float("nan")


def _fmt(value: Any, digits: int = 2) -> str:
    value_float = _num(value)
    if not np.isfinite(value_float):
        return "NA"
    return f"{value_float:.{digits}f}"


def _fmt_m(value: Any, digits: int = 2) -> str:
    value_float = _num(value)
    if not np.isfinite(value_float):
        return "NA"
    return f"{value_float / 1_000_000.0:.{digits}f}M"


def _fmt_signed(value: Any, digits: int = 1) -> str:
    value_float = _num(value)
    if not np.isfinite(value_float):
        return "NA"
    prefix = "+" if value_float >= 0.0 else ""
    return f"{prefix}{value_float:.{digits}f}"


def _fmt_signed_m_eur(value: Any) -> str:
    value_float = _num(value)
    if not np.isfinite(value_float):
        return "NA"
    prefix = "+" if value_float >= 0.0 else ""
    return f"{prefix}{value_float / 1000.0:.0f}k"


def _escape(text: str) -> str:
    return (
        text.replace("\\", r"\textbackslash{}")
        .replace("&", r"\&")
        .replace("%", r"\%")
        .replace("_", r"\_")
    )
