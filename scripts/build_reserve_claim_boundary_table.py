from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT_TABLES = ROOT / "artifacts" / "final_evidence_package" / "export" / "tables"
SUMMARY = OUT_TABLES / "reserve_decision_summary.csv"
SYSTEM_ENVELOPE = OUT_TABLES / "system_value_envelope.csv"
PAIRED_STATS = OUT_TABLES / "reserve_paired_statistics.csv"
RAW_RUNS = ROOT / "artifacts" / "decision_reserve_wtb_operational_windows" / "reserve_decision_raw_runs.csv"


def main() -> None:
    OUT_TABLES.mkdir(parents=True, exist_ok=True)
    summary = pd.read_csv(SUMMARY)
    envelope = pd.read_csv(SYSTEM_ENVELOPE)
    paired = pd.read_csv(PAIRED_STATS)
    raw_runs = pd.read_csv(RAW_RUNS)
    same_model = _same_model_paired_stats(raw_runs)

    rows = [
        _same_model_boundary_row(envelope, same_model),
        _physical_bin_row(summary),
        _cost_ratio_row(envelope),
        _full_sample_row(summary),
        _paired_uncertainty_row(paired),
        _scope_row(),
    ]
    frame = pd.DataFrame(rows)

    out_csv = OUT_TABLES / "reserve_claim_boundary_audit.csv"
    out_tex = OUT_TABLES / "table_reserve_claim_boundary_audit.tex"
    out_json = OUT_TABLES / "reserve_claim_boundary_audit_summary.json"

    frame.to_csv(out_csv, index=False)
    _write_latex(frame, out_tex)
    payload: dict[str, Any] = {
        "inputs": {
            "reserve_decision_summary": str(SUMMARY),
            "system_value_envelope": str(SYSTEM_ENVELOPE),
            "reserve_paired_statistics": str(PAIRED_STATS),
            "reserve_decision_raw_runs": str(RAW_RUNS),
        },
        "outputs": {"csv": str(out_csv), "tex": str(out_tex)},
        "claim_use": (
            "Reserve-policy claim-boundary audit. It separates same-model "
            "boundary-window diagnostic evidence from unsupported reserve-policy, "
            "backbone-superiority, full-sample dispatch, and market-price claims."
        ),
    }
    out_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {out_csv}")


def _same_model_boundary_row(envelope: pd.DataFrame, same_model: dict[str, dict[str, float]]) -> dict[str, str]:
    row = _lookup(envelope, cost_ratio=10.0)
    cost = same_model["total_cost"]
    violation = same_model["violation_rate"]
    shortage = same_model["shortage_energy"]
    evidence = (
        "At rho=10, gate-bin vs same-router global: "
        f"Delta cost {_fmt_m(row['boundary_total_cost_delta'])} "
        f"(seed-paired 95% CI [{_fmt_m(cost['ci_low'])}, {_fmt_m(cost['ci_high'])}]), "
        f"Delta viol. {_fmt_float(row['violation_delta'], 4)} "
        f"(CI [{_fmt_float(violation['ci_low'], 4)}, {_fmt_float(violation['ci_high'], 4)}]), "
        f"reserve {_fmt_m(row['additional_reserve_energy'], signed=True)}, "
        f"shortage {_fmt_m(row['shortage_energy_delta'], signed=True)} "
        f"(CI [{_fmt_m(shortage['ci_low'])}, {_fmt_m(shortage['ci_high'])}])."
    )
    return {
        "boundary": "Same-model boundary reserve effect",
        "evidence": evidence,
        "wording_rule": (
            "Claim a statistically supported same-predictor transition-window diagnostic; "
            "do not present this as a cross-backbone reserve win."
        ),
    }


def _physical_bin_row(summary: pd.DataFrame) -> dict[str, str]:
    b_phys = _reserve_row(summary, "boundary", "Boundary-forced router", "physical-bin")
    g_phys = _reserve_row(summary, "boundary", "Graph WaveNet", "physical-bin")
    b_gate = _reserve_row(summary, "boundary", "Boundary-forced router", "gate-bin")
    evidence = (
        "Boundary/physical-bin "
        f"{_fmt_m(b_phys['total_cost_mean'])}, viol. {_fmt_float(b_phys['violation_rate_mean'], 4)}; "
        "GWN/physical-bin "
        f"{_fmt_m(g_phys['total_cost_mean'])}, viol. {_fmt_float(g_phys['violation_rate_mean'], 4)}; "
        "Boundary/gate-bin "
        f"{_fmt_m(b_gate['total_cost_mean'])}, viol. {_fmt_float(b_gate['violation_rate_mean'], 4)}."
    )
    return {
        "boundary": "Physical-bin quantile comparator",
        "evidence": evidence,
        "wording_rule": (
            "Say physical-bin baselines are competitive and sometimes lower-cost; "
            "avoid gate-bin optimality wording."
        ),
    }


def _cost_ratio_row(envelope: pd.DataFrame) -> dict[str, str]:
    ratio50 = _lookup(envelope, cost_ratio=50.0)
    evidence = (
        "rho=2 inactive; rho=5 to 10 lowers boundary cost and violation; "
        "rho=20 narrows; rho=50 favors global "
        f"({_fmt_m(ratio50['boundary_total_cost_delta'], signed=True)}, "
        f"viol. {_fmt_float(ratio50['violation_delta'], 4, signed=True)})."
    )
    return {
        "boundary": "Cost-ratio applicability",
        "evidence": evidence,
        "wording_rule": (
            "Claim moderate-cost transition-window value only; do not assert a "
            "universal shortage-penalty policy."
        ),
    }


def _full_sample_row(summary: pd.DataFrame) -> dict[str, str]:
    gwn = _reserve_row(summary, "full", "Graph WaveNet", "global")
    gate = _reserve_row(summary, "full", "Boundary-forced router", "gate-bin")
    evidence = (
        "Full sample at rho=10: GWN/global "
        f"{_fmt_m(gwn['total_cost_mean'])}, viol. {_fmt_float(gwn['violation_rate_mean'], 4)}; "
        "Boundary/gate-bin "
        f"{_fmt_m(gate['total_cost_mean'])}, viol. {_fmt_float(gate['violation_rate_mean'], 4)}."
    )
    return {
        "boundary": "Full-sample system value",
        "evidence": evidence,
        "wording_rule": (
            "Do not claim system-wide dispatch value or reserve superiority; keep "
            "the consequence bounded to the boundary slice."
        ),
    }


def _paired_uncertainty_row(paired: pd.DataFrame) -> dict[str, str]:
    row = _lookup(
        paired,
        candidate="Boundary-forced router/gate-bin",
        baseline="Graph WaveNet/global",
        metric="total_cost",
    )
    evidence = (
        "Full-sample paired total-cost delta "
        f"{_fmt_m(row['observed_delta'], signed=True)}, "
        f"95% CI [{_fmt_m(row['ci_low'], signed=True)}, "
        f"{_fmt_m(row['ci_high'], signed=True)}], "
        f"perm. p={_fmt_float(row['paired_sign_permutation_p'], 3)}."
    )
    return {
        "boundary": "Cross-backbone/full-sample uncertainty",
        "evidence": evidence,
        "wording_rule": (
            "Use bounded diagnostic language; do not cite the reserve audit as a "
            "system-wide or cross-backbone improvement."
        ),
    }


def _scope_row() -> dict[str, str]:
    return {
        "boundary": "Operational scope",
        "evidence": (
            "Costs are normalized reserve-energy proxy units from validation-frozen "
            "shortfall quantiles; OPF, unit commitment, delivery constraints, "
            "market clearing, and prices are excluded."
        ),
        "wording_rule": (
            "Use as a screening audit for reserve exposure, not as a market or "
            "security-constrained dispatch study."
        ),
    }


def _same_model_paired_stats(raw_runs: pd.DataFrame) -> dict[str, dict[str, float]]:
    frame = raw_runs[
        raw_runs["model"].astype(str).eq("Boundary-forced router")
        & raw_runs["subset"].astype(str).eq("boundary")
        & pd.to_numeric(raw_runs["cost_ratio"], errors="coerce").eq(10.0)
        & raw_runs["policy"].astype(str).isin(["global", "gate-bin"])
    ].copy()
    if frame.empty:
        raise ValueError("No boundary same-model reserve rows found for cost ratio 10.")

    metrics = ["total_cost", "violation_rate", "reserve_energy", "shortage_energy"]
    wide = frame.pivot(index="seed", columns="policy", values=metrics)
    out: dict[str, dict[str, float]] = {}
    for metric in metrics:
        diffs = (wide[(metric, "gate-bin")] - wide[(metric, "global")]).dropna().astype(float)
        if diffs.empty:
            raise ValueError(f"No paired differences available for {metric}.")
        values = diffs.to_numpy()
        boot = _bootstrap_mean(values, n_boot=20000, seed=20260702 + len(metric))
        out[metric] = {
            "mean": float(values.mean()),
            "ci_low": float(boot.quantile(0.025)),
            "ci_high": float(boot.quantile(0.975)),
            "n_pairs": float(len(values)),
        }
    return out


def _bootstrap_mean(values: Any, *, n_boot: int, seed: int) -> pd.Series:
    import numpy as np

    array = np.asarray(values, dtype=float)
    rng = np.random.default_rng(seed)
    samples = rng.choice(array, size=(n_boot, array.size), replace=True)
    return pd.Series(samples.mean(axis=1))


def _reserve_row(summary: pd.DataFrame, subset: str, model: str, policy: str) -> pd.Series:
    return _lookup(
        summary,
        subset=subset,
        cost_ratio=10.0,
        model=model,
        policy=policy,
    )


def _lookup(frame: pd.DataFrame, **equals: Any) -> pd.Series:
    mask = pd.Series(True, index=frame.index)
    for column, value in equals.items():
        if isinstance(value, float):
            values = pd.to_numeric(frame[column], errors="coerce")
            mask &= values.sub(value).abs().le(1e-9)
        else:
            mask &= frame[column].astype(str).eq(str(value))
    rows = frame[mask]
    if rows.empty:
        raise ValueError(f"No row matches {equals}")
    return rows.iloc[0]


def _num(value: Any) -> float:
    out = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    return float(out) if pd.notna(out) else math.nan


def _fmt_m(value: Any, *, signed: bool = False) -> str:
    value_float = _num(value)
    if not math.isfinite(value_float):
        return "--"
    prefix = "+" if signed and value_float >= 0 else ""
    return f"{prefix}{value_float / 1_000_000:.2f}M"


def _fmt_float(value: Any, digits: int, *, signed: bool = False) -> str:
    value_float = _num(value)
    if not math.isfinite(value_float):
        return "--"
    prefix = "+" if signed and value_float >= 0 else ""
    return f"{prefix}{value_float:.{digits}f}"


def _write_latex(frame: pd.DataFrame, path: Path) -> None:
    lines = [
        r"\begin{table}[H]",
        r"\centering",
        r"\scriptsize",
        r"\setlength{\tabcolsep}{2.4pt}",
        r"\renewcommand{\arraystretch}{1.03}",
        r"\caption*{\textbf{Table A11.} Reserve-policy claim-boundary audit.}",
        r"\begin{tabularx}{\columnwidth}{>{\raggedright\arraybackslash}p{0.25\columnwidth} >{\raggedright\arraybackslash}X >{\raggedright\arraybackslash}p{0.22\columnwidth}}",
        r"\toprule",
        r"Boundary & Key evidence & Limit \\",
        r"\midrule",
    ]
    display_evidence = [
        r"$\rho=10$: $\Delta$cost -3.55M [CI -4.65M,-2.45M]; $\Delta$viol. -0.0138 [CI -0.0203,-0.0072]; shortage -0.54M [CI -0.78M,-0.30M]",
        r"Boundary phys. 83.78M/0.0880; GWN phys. 84.31M/0.0931; gate 84.58M/0.0900",
        r"Active at $\rho=5$--10; narrows at 20; $\rho=50$ favors global (+5.93M, +0.0035)",
        r"GWN/global 464.07M/0.0901; gate-bin 481.36M/0.1214",
        r"$\Delta$cost +17.28M; 95\% CI [-52.09M,+87.95M]; p=0.752",
        r"Validation-frozen shortfall quantiles; no OPF, unit commitment, market clearing, or prices",
    ]
    display_limits = [
        "Same-model diagnostic; not cross-model optimal",
        "Physical bins remain competitive",
        "Moderate-cost window only",
        "No system-wide dispatch claim",
        "Not system-wide or cross-backbone",
        "Screening audit only",
    ]
    for (_, row), evidence, limit in zip(frame.iterrows(), display_evidence, display_limits):
        lines.append(
            " & ".join(
                [
                    _escape(str(row["boundary"])),
                    evidence,
                    _escape(limit),
                ]
            )
            + r" \\"
        )
    lines.extend(
        [
            r"\bottomrule",
            r"\end{tabularx}",
            r"\vspace{1mm}",
            r"\footnotesize Same-model intervals are $n=5$ seed-paired bootstrap mean CIs for gate-bin minus same-router global at $\rho=10$.",
            r"\end{table}",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def _escape(text: str) -> str:
    return (
        text.replace("\\", r"\textbackslash{}")
        .replace("&", r"\&")
        .replace("%", r"\%")
        .replace("_", r"\_")
    )


if __name__ == "__main__":
    main()
