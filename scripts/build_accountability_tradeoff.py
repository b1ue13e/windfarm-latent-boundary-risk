from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT_TABLES = ROOT / "artifacts" / "final_evidence_package" / "export" / "tables"
OUT_FIGURES = ROOT / "artifacts" / "final_evidence_package" / "export" / "figures"

MAIN_BENCHMARK = ROOT / "artifacts" / "paper_assets" / "tables" / "table_main_benchmark.csv"
WTB_ABLATION = ROOT / "artifacts" / "paper_assets" / "tables" / "table_wtb_ablation.csv"
EARLY_WARNING = (
    ROOT
    / "artifacts"
    / "anchor_stress_early_warning_wtb_strictmask"
    / "anchor_stress_early_warning_summary.csv"
)
TOY_COST = ROOT / "artifacts" / "reserve_toy_operational_cost" / "reserve_toy_operational_cost.csv"

ROUTING_NMI_PASS = 0.65


def main() -> None:
    OUT_TABLES.mkdir(parents=True, exist_ok=True)
    OUT_FIGURES.mkdir(parents=True, exist_ok=True)

    benchmark = pd.read_csv(MAIN_BENCHMARK)
    ablation = pd.read_csv(WTB_ABLATION)
    early = pd.read_csv(EARLY_WARNING)
    cost = pd.read_csv(TOY_COST)

    graph_rmse = _metric_mean(
        _lookup(benchmark, Panel="WTB", Model="Graph WaveNet").get("Overall RMSE")
    )
    boundary_rmse = _metric_mean(
        _lookup(benchmark, Panel="WTB", Model="Boundary-forced router").get("Overall RMSE")
    )
    unconstrained = _lookup(ablation, Model="Unconstrained MoE")
    boundary_ablation = _lookup(ablation, Model="MoE + L_bal + L_align + L_force")

    six_step = _lookup(
        early,
        variant="canonical",
        scenario="label_delay",
        degradation_label="delay_steps=6",
    )
    gate_recall = _num(six_step.get("gate_recall_mean"))
    rule_recall = _num(six_step.get("threshold_recall_mean"))
    recall_gain = _num(six_step.get("recall_gain_mean"))
    target_cells = _num(six_step.get("n_target_cells_mean"))
    gate_missed_cells = target_cells * (1.0 - gate_recall)
    rule_missed_cells = target_cells * (1.0 - rule_recall)
    recovered_cells = rule_missed_cells - gate_missed_cells

    gate_cost = _lookup(
        cost,
        subset="boundary",
        policy_label="Boundary-forced router/gate-bin",
        source="reserve_decision",
    )

    rows = [
        {
            "model": "Graph WaveNet",
            "role": "accuracy reference",
            "overall_rmse": graph_rmse,
            "rmse_penalty_vs_graph_wavenet": 0.0,
            "route_nmi": math.nan,
            "route_ari": math.nan,
            "routing_gate_status": "no audited operating-state gate",
            "six_step_gate_recall": math.nan,
            "six_step_threshold_rule_recall": rule_recall,
            "raw_recall_gain": math.nan,
            "citable_recall_gain": 0.0,
            "citable_gate_recall": 0.0,
            "early_pitch_cells_recovered_vs_delay_rule": math.nan,
            "toy_total_cost_delta_vs_same_model_global": math.nan,
            "shortage_penalty_delta_vs_same_model_global": math.nan,
            "violation_rate_delta_vs_same_model_global": math.nan,
            "pareto_status": "frontier_anchor",
            "claim_boundary": "forecasting baseline; no degraded-label accountability claim",
        },
        {
            "model": "Unconstrained MoE",
            "role": "routed-capacity control",
            "overall_rmse": _metric_mean(unconstrained.get("Overall RMSE")),
            "rmse_penalty_vs_graph_wavenet": _metric_mean(unconstrained.get("Overall RMSE"))
            - graph_rmse,
            "route_nmi": _metric_mean(unconstrained.get("NMI")),
            "route_ari": _metric_mean(unconstrained.get("ARI")),
            "routing_gate_status": "fails physical-route audit",
            "six_step_gate_recall": math.nan,
            "six_step_threshold_rule_recall": rule_recall,
            "raw_recall_gain": math.nan,
            "citable_recall_gain": 0.0,
            "citable_gate_recall": 0.0,
            "early_pitch_cells_recovered_vs_delay_rule": math.nan,
            "toy_total_cost_delta_vs_same_model_global": math.nan,
            "shortage_penalty_delta_vs_same_model_global": math.nan,
            "violation_rate_delta_vs_same_model_global": math.nan,
            "pareto_status": "dominated_by_accuracy_reference",
            "claim_boundary": "routed capacity alone is not an auditable operating-state signal",
        },
        {
            "model": "Boundary-forced router",
            "role": "auditable boundary route",
            "overall_rmse": boundary_rmse,
            "rmse_penalty_vs_graph_wavenet": boundary_rmse - graph_rmse,
            "route_nmi": _metric_mean(boundary_ablation.get("NMI")),
            "route_ari": _metric_mean(boundary_ablation.get("ARI")),
            "routing_gate_status": "passes physical-route audit",
            "six_step_gate_recall": gate_recall,
            "six_step_threshold_rule_recall": rule_recall,
            "raw_recall_gain": recall_gain,
            "citable_recall_gain": recall_gain,
            "citable_gate_recall": gate_recall,
            "early_pitch_cells_recovered_vs_delay_rule": recovered_cells,
            "toy_total_cost_delta_vs_same_model_global": _num(
                gate_cost.get("delta_toy_total_cost_vs_boundary_router_global")
            ),
            "shortage_penalty_delta_vs_same_model_global": _num(
                gate_cost.get("delta_shortage_penalty_vs_boundary_router_global")
            ),
            "violation_rate_delta_vs_same_model_global": _num(
                gate_cost.get("delta_violation_rate_vs_boundary_router_global")
            ),
            "pareto_status": "frontier_accountability",
            "claim_boundary": (
                "only audited point with a citable degraded-label early-warning signal"
            ),
        },
    ]

    table = pd.DataFrame(rows)
    table.to_csv(OUT_TABLES / "accountability_tradeoff.csv", index=False)
    _write_latex(table, OUT_TABLES / "table_accountability_tradeoff.tex")
    _plot_tradeoff(table, OUT_FIGURES / "accountability_tradeoff_curve.pdf")
    _plot_tradeoff(table, OUT_FIGURES / "accountability_tradeoff_curve.png")

    summary = {
        "inputs": {
            "main_benchmark": str(MAIN_BENCHMARK),
            "wtb_ablation": str(WTB_ABLATION),
            "early_warning": str(EARLY_WARNING),
            "toy_cost": str(TOY_COST),
        },
        "routing_nmi_pass": ROUTING_NMI_PASS,
        "six_step_label_delay": {
            "gate_recall": gate_recall,
            "threshold_rule_recall": rule_recall,
            "recall_gain": recall_gain,
            "target_cells_mean": target_cells,
            "gate_missed_cells_mean": gate_missed_cells,
            "rule_missed_cells_mean": rule_missed_cells,
            "early_pitch_cells_recovered_vs_delay_rule_mean": recovered_cells,
        },
        "boundary_gate_bin_cost_proxy": {
            "delta_toy_total_cost_vs_same_model_global": _num(
                gate_cost.get("delta_toy_total_cost_vs_boundary_router_global")
            ),
            "delta_shortage_penalty_vs_same_model_global": _num(
                gate_cost.get("delta_shortage_penalty_vs_boundary_router_global")
            ),
            "delta_violation_rate_vs_same_model_global": _num(
                gate_cost.get("delta_violation_rate_vs_boundary_router_global")
            ),
            "scope": "normalized reserve-energy cost units, not currency",
        },
        "outputs": {
            "csv": str(OUT_TABLES / "accountability_tradeoff.csv"),
            "tex": str(OUT_TABLES / "table_accountability_tradeoff.tex"),
            "pdf": str(OUT_FIGURES / "accountability_tradeoff_curve.pdf"),
            "png": str(OUT_FIGURES / "accountability_tradeoff_curve.png"),
        },
    }
    (OUT_TABLES / "accountability_tradeoff_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(f"Wrote {OUT_TABLES / 'accountability_tradeoff.csv'}")
    print(f"Wrote {OUT_FIGURES / 'accountability_tradeoff_curve.pdf'}")


def _lookup(frame: pd.DataFrame, **equals: str) -> pd.Series:
    mask = pd.Series(True, index=frame.index)
    for column, value in equals.items():
        mask &= frame[column].astype(str).eq(str(value))
    rows = frame[mask]
    if rows.empty:
        raise ValueError(f"No row matches {equals}")
    return rows.iloc[0]


def _metric_mean(value: Any) -> float:
    if value is None:
        return math.nan
    text = str(value)
    match = re.search(r"[-+]?\d+(?:\.\d+)?", text)
    if not match:
        return math.nan
    return float(match.group(0))


def _num(value: Any) -> float:
    out = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    return float(out) if pd.notna(out) else math.nan


def _fmt(value: Any, digits: int = 2) -> str:
    value_float = _num(value)
    if not math.isfinite(value_float):
        return "--"
    return f"{value_float:.{digits}f}"


def _fmt3(value: Any) -> str:
    return _fmt(value, 3)


def _fmt_m(value: Any) -> str:
    value_float = _num(value)
    if not math.isfinite(value_float):
        return "--"
    return f"{value_float / 1_000_000.0:.2f}M"


def _write_latex(frame: pd.DataFrame, path: Path) -> None:
    lines = [
        r"\begin{table}[H]",
        r"\centering",
        r"\scriptsize",
        r"\setlength{\tabcolsep}{3pt}",
        r"\renewcommand{\arraystretch}{1.08}",
        r"\caption{Accountability value versus forecasting RMSE price.}",
        r"\begin{tabular}{lrrrrl}",
        r"\toprule",
        r"Model & RMSE & RMSE price & NMI & Delay gain & Status \\",
        r"\midrule",
    ]
    for _, row in frame.iterrows():
        lines.append(
            " & ".join(
                [
                    str(row["model"]).replace("_", r"\_"),
                    _fmt(row.get("overall_rmse"), 2),
                    _fmt(row.get("rmse_penalty_vs_graph_wavenet"), 2),
                    _fmt3(row.get("route_nmi")),
                    _fmt3(row.get("citable_recall_gain")),
                    str(row["routing_gate_status"]).replace("_", r"\_"),
                ]
            )
            + r" \\"
        )
    lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}", ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def _plot_tradeoff(frame: pd.DataFrame, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(6.9, 2.75))
    colors = {
        "Graph WaveNet": "#2563eb",
        "Unconstrained MoE": "#6b7280",
        "Boundary-forced router": "#dc2626",
    }
    markers = {
        "Graph WaveNet": "o",
        "Unconstrained MoE": "X",
        "Boundary-forced router": "s",
    }
    for _, row in frame.iterrows():
        model = str(row["model"])
        x = _num(row["rmse_penalty_vs_graph_wavenet"])
        y = _num(row["citable_recall_gain"])
        ax.scatter(
            [x],
            [y],
            s=95,
            marker=markers.get(model, "o"),
            color=colors.get(model, "#374151"),
            edgecolor="white",
            linewidth=0.9,
            zorder=3,
        )
        label = {
            "Graph WaveNet": "Graph WaveNet",
            "Unconstrained MoE": "Unconstrained MoE\n(no route)",
            "Boundary-forced router": "Boundary router\n(+0.764)",
        }[model]
        dx = 0.16 if model != "Boundary-forced router" else -2.85
        dy = 0.045 if model == "Graph WaveNet" else 0.035
        ax.annotate(label, (x, y), xytext=(x + dx, y + dy), fontsize=8)

    frontier = frame[frame["pareto_status"].astype(str).str.startswith("frontier")].copy()
    frontier = frontier.sort_values("rmse_penalty_vs_graph_wavenet")
    ax.plot(
        frontier["rmse_penalty_vs_graph_wavenet"],
        frontier["citable_recall_gain"],
        color="#111827",
        linewidth=1.5,
        linestyle="--",
        label="auditability frontier",
        zorder=2,
    )

    boundary = frame[frame["model"].eq("Boundary-forced router")].iloc[0]
    ax.annotate(
        "gate 0.960 vs rule 0.196",
        xy=(
            _num(boundary["rmse_penalty_vs_graph_wavenet"]),
            _num(boundary["citable_recall_gain"]),
        ),
        xytext=(1.5, 0.60),
        fontsize=8,
        arrowprops={"arrowstyle": "->", "lw": 1.0, "color": "#991b1b"},
        color="#991b1b",
    )
    ax.text(
        0.03,
        0.95,
        "Citable gain requires a passed physical-routing audit.",
        transform=ax.transAxes,
        fontsize=7.5,
        va="top",
        color="#374151",
    )
    ax.set_xlabel("WTB RMSE penalty vs Graph WaveNet")
    ax.set_ylabel("Citable recall gain")
    ax.set_xlim(-0.8, 12.1)
    ax.set_ylim(-0.05, 0.86)
    ax.grid(True, alpha=0.25)
    ax.legend(loc="lower right", fontsize=7, frameon=True)
    fig.tight_layout()
    fig.savefig(path, dpi=240)
    plt.close(fig)


if __name__ == "__main__":
    main()
