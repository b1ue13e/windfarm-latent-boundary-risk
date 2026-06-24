from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .decision import (
    DEFAULT_COST_RATIOS,
    DEFAULT_MAIN_RATIO,
    DEFAULT_QUANTILES,
    _aggregate_metric_rows,
    _calibrate_policy,
    _cost_metrics,
    _iter_subsets,
    _load_cache_meta,
    _load_run_decision_data,
    _reserve_matrix_for_calibration,
    _validate_anchor_alignment,
    select_default_wtb_runs,
)
from .utils import ensure_dir, save_json


DEFAULT_PROBABILISTIC_STRATA = ("boundary", "non_boundary", "high_ramp")


def run_reserve_probabilistic_baseline(
    *,
    run_table: Path | str,
    cache_dir: Path | str,
    output_dir: Path | str,
    root_dir: Path | str = ".",
    cost_ratios: list[float] | None = None,
    main_ratio: float = DEFAULT_MAIN_RATIO,
    quantiles: list[float] | None = None,
    boundary_band: float = 1.0,
    bootstrap_samples: int = 1000,
    seed: int = 42,
) -> Path:
    """Compare gate-conditioned reserves with validation-frozen quantile baselines.

    The baseline is intentionally narrow: it is a held-out residual reserve audit,
    not a full probabilistic dispatch model. This keeps the evidence citable even
    when the standard quantile baseline outperforms the gate-conditioned rule.
    """

    out_dir = ensure_dir(output_dir)
    ratios = cost_ratios or list(DEFAULT_COST_RATIOS)
    candidate_quantiles = quantiles or list(DEFAULT_QUANTILES)
    cache_meta = _load_cache_meta(cache_dir, boundary_band=boundary_band)
    dt = 1.0 / float(cache_meta["steps_per_hour"])

    runs = select_default_wtb_runs(run_table, root_dir=root_dir)
    run_data = [_load_run_decision_data(run, cache_meta) for run in runs]
    _validate_anchor_alignment(run_data)

    raw_rows: list[dict[str, Any]] = []
    for data in run_data:
        for subset_name, val_subset, test_subset in _iter_subsets(
            data.val,
            data.test,
            int(cache_meta["pred_len"]),
            strata=list(DEFAULT_PROBABILISTIC_STRATA),
        ):
            for ratio in ratios:
                raw_rows.extend(
                    _probabilistic_rows_for_run(
                        data=data,
                        val_panel=val_subset,
                        test_panel=test_subset,
                        subset_name=subset_name,
                        ratio=float(ratio),
                        dt=dt,
                        quantiles=candidate_quantiles,
                    )
                )

    raw_df = pd.DataFrame(raw_rows)
    summary = _aggregate_probabilistic_rows(raw_df)
    main = summary[np.isclose(pd.to_numeric(summary["cost_ratio"], errors="coerce"), float(main_ratio))].copy()
    comparison = _comparison_rows(main)
    bootstrap = _bootstrap_comparisons(raw_df, main_ratio=float(main_ratio), samples=bootstrap_samples, seed=seed)

    raw_df.to_csv(out_dir / "reserve_quantile_baseline_raw.csv", index=False)
    summary.to_csv(out_dir / "reserve_quantile_baseline.csv", index=False)
    comparison.to_csv(out_dir / "reserve_quantile_baseline_comparison.csv", index=False)
    bootstrap.to_csv(out_dir / "reserve_quantile_baseline_bootstrap.csv", index=False)
    _write_latex_table(main, out_dir / "reserve_quantile_baseline.tex", main_ratio=float(main_ratio))
    save_json(
        out_dir / "reserve_quantile_baseline.json",
        {
            "dataset": "wtb",
            "run_table": str(run_table),
            "cache_dir": str(cache_dir),
            "cost_ratios": [float(value) for value in ratios],
            "main_ratio": float(main_ratio),
            "quantiles": [float(value) for value in candidate_quantiles],
            "boundary_band": float(boundary_band),
            "bootstrap_samples": int(bootstrap_samples),
            "seed": int(seed),
            "claim_use": (
                "Validation-frozen empirical quantile/conformal reserve baseline. "
                "If it dominates gate-bin reserves, downgrade the reserve claim to "
                "transition-window attribution diagnostic."
            ),
            "selected_runs": [
                {
                    "model": run.model,
                    "seed": int(run.seed),
                    "run_dir": str(run.run_dir),
                    "variant_key": run.variant_key,
                    "experiment_group": run.experiment_group,
                }
                for run in runs
            ],
            "outputs": {
                "summary_csv": str(out_dir / "reserve_quantile_baseline.csv"),
                "comparison_csv": str(out_dir / "reserve_quantile_baseline_comparison.csv"),
                "bootstrap_csv": str(out_dir / "reserve_quantile_baseline_bootstrap.csv"),
                "tex": str(out_dir / "reserve_quantile_baseline.tex"),
            },
        },
    )
    return out_dir


def _probabilistic_rows_for_run(
    *,
    data: Any,
    val_panel: Any,
    test_panel: Any,
    subset_name: str,
    ratio: float,
    dt: float,
    quantiles: list[float],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    policies = [
        ("global_quantile", "global"),
        ("physical_bin_quantile", "physical-bin"),
    ]
    if data.has_gate:
        policies.append(("gate_bin_quantile", "gate-bin"))

    for baseline, policy in policies:
        calibration = _calibrate_policy(
            policy=policy,
            panel=val_panel,
            ratio=ratio,
            dt=dt,
            quantiles=quantiles,
        )
        base = _base_row(data, baseline, policy, subset_name, ratio, calibration)
        if calibration.status != "applicable":
            rows.append({**base, **_empty_metrics()})
            continue
        reserve, _ = _reserve_matrix_for_calibration(calibration, test_panel)
        metrics = _cost_metrics(test_panel.shortfall, test_panel.valid, reserve, ratio, dt)
        rows.append({**base, **metrics})
    return rows


def _base_row(data: Any, baseline: str, policy: str, subset_name: str, ratio: float, calibration: Any) -> dict[str, Any]:
    return {
        "model": data.info.model,
        "source_model": data.info.source_model,
        "seed": int(data.info.seed),
        "run_dir": str(data.info.run_dir),
        "variant_key": data.info.variant_key,
        "experiment_group": data.info.experiment_group,
        "overall_rmse": data.info.overall_rmse,
        "baseline": baseline,
        "policy": policy,
        "subset": subset_name,
        "cost_ratio": float(ratio),
        "status": calibration.status,
        "score_source": calibration.score_source,
        "best_quantile": ";".join(f"{key}={value:.3f}" for key, value in calibration.quantiles.items()),
        "reserve": ";".join(f"{key}={value:.6g}" for key, value in calibration.reserves.items()),
    }


def _empty_metrics() -> dict[str, float]:
    return {
        "total_cost": np.nan,
        "mean_cost": np.nan,
        "violation_rate": np.nan,
        "mean_reserve": np.nan,
        "reserve_energy": np.nan,
        "shortage_energy": np.nan,
        "valid_cells": 0,
    }


def _aggregate_probabilistic_rows(raw_df: pd.DataFrame) -> pd.DataFrame:
    if raw_df.empty:
        return pd.DataFrame()
    renamed = raw_df.rename(columns={"baseline": "model_baseline"}).copy()
    renamed["model"] = renamed["model"] + "/" + renamed["model_baseline"]
    aggregated = _aggregate_metric_rows(renamed)
    if aggregated.empty:
        return aggregated
    split = aggregated["model"].astype(str).str.rsplit("/", n=1, expand=True)
    aggregated["model"] = split[0]
    aggregated["baseline"] = split[1]
    columns = ["subset", "cost_ratio", "model", "baseline", "policy", "status", "n_runs"]
    rest = [column for column in aggregated.columns if column not in columns]
    return aggregated[columns + rest]


def _comparison_rows(summary: pd.DataFrame) -> pd.DataFrame:
    if summary.empty:
        return pd.DataFrame()
    rows: list[dict[str, Any]] = []
    for subset in sorted(summary["subset"].astype(str).unique()):
        subset_df = summary[summary["subset"].astype(str).eq(subset)]
        gate = _pick(subset_df, model="Boundary-forced router", baseline="gate_bin_quantile")
        for model, baseline in [
            ("Boundary-forced router", "global_quantile"),
            ("Boundary-forced router", "physical_bin_quantile"),
            ("Graph WaveNet", "global_quantile"),
            ("Graph WaveNet", "physical_bin_quantile"),
        ]:
            candidate = _pick(subset_df, model=model, baseline=baseline)
            if gate is None or candidate is None:
                continue
            row = {
                "subset": subset,
                "cost_ratio": float(gate["cost_ratio"]),
                "candidate": f"{model}/{baseline}",
                "reference": "Boundary-forced router/gate_bin_quantile",
            }
            for metric in ["total_cost", "violation_rate", "reserve_energy", "shortage_energy"]:
                row[f"candidate_{metric}"] = candidate.get(f"{metric}_mean", np.nan)
                row[f"reference_{metric}"] = gate.get(f"{metric}_mean", np.nan)
                row[f"delta_{metric}_candidate_minus_reference"] = (
                    _num(candidate.get(f"{metric}_mean")) - _num(gate.get(f"{metric}_mean"))
                )
            row["interpretation"] = _comparison_interpretation(row)
            rows.append(row)
    return pd.DataFrame(rows)


def _pick(frame: pd.DataFrame, *, model: str, baseline: str) -> pd.Series | None:
    subset = frame[frame["model"].astype(str).eq(model) & frame["baseline"].astype(str).eq(baseline)]
    if subset.empty:
        return None
    return subset.iloc[0]


def _num(value: Any) -> float:
    out = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    return float(out) if pd.notna(out) else float("nan")


def _comparison_interpretation(row: dict[str, Any]) -> str:
    total = _num(row.get("delta_total_cost_candidate_minus_reference"))
    violation = _num(row.get("delta_violation_rate_candidate_minus_reference"))
    shortage = _num(row.get("delta_shortage_energy_candidate_minus_reference"))
    if np.isfinite(total) and np.isfinite(violation) and np.isfinite(shortage):
        if total < 0 and violation <= 0 and shortage <= 0:
            return "probabilistic_baseline_dominates_gate_bin"
        if total > 0 and violation >= 0 and shortage >= 0:
            return "gate_bin_dominates_candidate"
    return "mixed_tradeoff"


def _bootstrap_comparisons(raw_df: pd.DataFrame, *, main_ratio: float, samples: int, seed: int) -> pd.DataFrame:
    if raw_df.empty or samples <= 0:
        return pd.DataFrame()
    main = raw_df[np.isclose(pd.to_numeric(raw_df["cost_ratio"], errors="coerce"), float(main_ratio))].copy()
    gate = main[
        main["model"].astype(str).eq("Boundary-forced router")
        & main["baseline"].astype(str).eq("gate_bin_quantile")
        & main["status"].astype(str).eq("applicable")
    ].copy()
    if gate.empty:
        return pd.DataFrame()
    rng = np.random.default_rng(seed)
    rows: list[dict[str, Any]] = []
    metrics = ["total_cost", "violation_rate", "reserve_energy", "shortage_energy"]
    for subset in sorted(gate["subset"].astype(str).unique()):
        gate_subset = gate[gate["subset"].astype(str).eq(subset)]
        for baseline in ["global_quantile", "physical_bin_quantile"]:
            cand = main[
                main["subset"].astype(str).eq(subset)
                & main["model"].astype(str).eq("Graph WaveNet")
                & main["baseline"].astype(str).eq(baseline)
                & main["status"].astype(str).eq("applicable")
            ].copy()
            merged = cand.merge(
                gate_subset,
                on="seed",
                suffixes=("_candidate", "_gate"),
            )
            if merged.empty:
                continue
            for metric in metrics:
                diffs = (
                    pd.to_numeric(merged[f"{metric}_candidate"], errors="coerce")
                    - pd.to_numeric(merged[f"{metric}_gate"], errors="coerce")
                ).dropna()
                if diffs.empty:
                    continue
                draws = [float(rng.choice(diffs.to_numpy(), size=len(diffs), replace=True).mean()) for _ in range(samples)]
                rows.append(
                    {
                        "subset": subset,
                        "candidate": f"Graph WaveNet/{baseline}",
                        "reference": "Boundary-forced router/gate_bin_quantile",
                        "metric": metric,
                        "n_seed_pairs": int(len(diffs)),
                        "observed_delta_candidate_minus_gate": float(diffs.mean()),
                        "ci_low": float(np.quantile(draws, 0.025)),
                        "ci_high": float(np.quantile(draws, 0.975)),
                    }
                )
    return pd.DataFrame(rows)


def _write_latex_table(frame: pd.DataFrame, path: Path, *, main_ratio: float) -> None:
    lines = [
        r"\begin{table}[H]",
        r"\centering",
        r"\footnotesize",
        r"\setlength{\tabcolsep}{4pt}",
        r"\renewcommand{\arraystretch}{1.08}",
        rf"\caption{{Validation-frozen probabilistic reserve baselines at $\rho={main_ratio:g}$.}}",
        r"\begin{tabular}{llrrrr}",
        r"\toprule",
        r"Subset & Model / baseline & Cost & Violation & Reserve & Shortage \\",
        r"\midrule",
    ]
    if not frame.empty:
        display = frame[
            frame["subset"].astype(str).isin(["full", "boundary"])
            & frame["model"].astype(str).isin(["Graph WaveNet", "Boundary-forced router"])
            & frame["baseline"].astype(str).isin(["global_quantile", "physical_bin_quantile", "gate_bin_quantile"])
        ].copy()
        display = display.sort_values(["subset", "model", "baseline"])
        for _, row in display.iterrows():
            label = f"{row['model']}/{row['baseline']}".replace("_", r"\_")
            lines.append(
                " & ".join(
                    [
                        str(row["subset"]).replace("_", r"\_"),
                        label,
                        _fmt_m(row.get("total_cost_mean")),
                        _fmt(row.get("violation_rate_mean"), 4),
                        _fmt_m(row.get("reserve_energy_mean")),
                        _fmt_m(row.get("shortage_energy_mean")),
                    ]
                )
                + r" \\"
            )
    lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}", ""])
    path.write_text("\n".join(lines), encoding="utf-8")


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
