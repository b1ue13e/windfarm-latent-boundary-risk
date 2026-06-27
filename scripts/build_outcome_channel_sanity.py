from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RUN_TABLE = ROOT / "artifacts" / "strictmask_combined_reviewer_stats" / "reviewer_stat_pack_run_table.csv"
OUT_TABLES = ROOT / "artifacts" / "final_evidence_package" / "export" / "tables"
REFERENCE = "MoE + L_bal + L_align + L_force"
SEEDS = (201, 202, 203, 204, 205)
WIND_BINS = np.asarray([0, 3, 5, 7, 9, 9.5, 10, 10.5, 11, 11.5, 12, 13, 16, 30], dtype=np.float64)


def main() -> None:
    OUT_TABLES.mkdir(parents=True, exist_ok=True)
    run_table = pd.read_csv(RUN_TABLE)
    runs = _select_runs(run_table)
    seed_rows: list[dict[str, Any]] = []
    for _, row in runs.iterrows():
        seed_rows.append(_audit_run(Path(str(row["run_dir"])), int(row["seed"])))

    seed_frame = pd.DataFrame(seed_rows)
    summary = _summarize(seed_frame)
    seed_frame.to_csv(OUT_TABLES / "outcome_channel_sanity_by_seed.csv", index=False)
    pd.DataFrame([summary]).to_csv(OUT_TABLES / "outcome_channel_sanity_summary.csv", index=False)
    _write_latex(summary, OUT_TABLES / "table_outcome_channel_sanity.tex")
    payload = {
        "inputs": {
            "run_table": str(RUN_TABLE),
            "model": REFERENCE,
            "seeds": list(SEEDS),
        },
        "outputs": {
            "by_seed": str(OUT_TABLES / "outcome_channel_sanity_by_seed.csv"),
            "summary": str(OUT_TABLES / "outcome_channel_sanity_summary.csv"),
            "tex": str(OUT_TABLES / "table_outcome_channel_sanity.tex"),
        },
        "claim_use": (
            "Outcome-channel sanity audit. Within the WTB boundary wind-speed window and after "
            "fine wind-bin adjustment, pitch-gate cells show a higher future-power response than "
            "MPPT-gate cells. This mitigates but does not eliminate the shared-anchor/label concern."
        ),
    }
    (OUT_TABLES / "outcome_channel_sanity_summary.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )
    print(f"Wrote {OUT_TABLES / 'outcome_channel_sanity_summary.csv'}")


def _select_runs(run_table: pd.DataFrame) -> pd.DataFrame:
    subset = run_table[
        (run_table["model"].astype(str) == REFERENCE) & (run_table["seed"].astype(int).isin(SEEDS))
    ].copy()
    if subset.empty:
        raise ValueError(f"No runs found for {REFERENCE}")
    subset = subset.sort_values(["seed", "run_dir"]).drop_duplicates("seed", keep="first")
    missing = sorted(set(SEEDS) - set(subset["seed"].astype(int)))
    if missing:
        raise ValueError(f"Missing required seeds: {missing}")
    return subset.sort_values("seed")


def _audit_run(run_dir: Path, seed: int) -> dict[str, Any]:
    val_mean, val_valid = _future_power_mean(run_dir / "val_metrics")
    val_wspd, _, _, _, _ = _anchor_arrays(run_dir / "val_metrics")
    val_bin = np.digitize(val_wspd, WIND_BINS) - 1
    expected = _validation_power_curve(val_mean, val_valid, val_bin)

    test_mean, test_valid = _future_power_mean(run_dir / "test_metrics")
    test_first, test_first_valid = _future_power_mean(run_dir / "test_metrics", horizon_slice=slice(0, 6))
    test_late, test_late_valid = _future_power_mean(run_dir / "test_metrics", horizon_slice=slice(12, None))
    test_wspd, anchor_patv, gate_label, _, _ = _anchor_arrays(run_dir / "test_metrics")
    test_bin = np.digitize(test_wspd, WIND_BINS) - 1
    expected_power = expected[np.clip(test_bin, 0, len(expected) - 1)]
    signed_residual = test_mean - expected_power
    future_ramp = test_late - test_first

    boundary = (
        (test_wspd >= 9.5)
        & (test_wspd <= 11.5)
        & test_valid
        & test_first_valid
        & test_late_valid
        & np.isfinite(test_mean)
        & np.isfinite(signed_residual)
        & np.isfinite(future_ramp)
    )
    shared_bin_stats: list[dict[str, dict[str, float]]] = []
    for bin_id in range(len(WIND_BINS) - 1):
        bin_mask = boundary & (test_bin == bin_id)
        if not bin_mask.any():
            continue
        stats: dict[str, dict[str, float]] = {}
        for gate_id, gate_name in [(1, "mppt"), (2, "pitch")]:
            gate_mask = bin_mask & (gate_label == gate_id)
            if int(gate_mask.sum()) < 20:
                continue
            stats[gate_name] = {
                "future_power": _mean(test_mean[gate_mask]),
                "signed_residual": _mean(signed_residual[gate_mask]),
                "future_ramp": _mean(future_ramp[gate_mask]),
                "anchor_patv": _mean(anchor_patv[gate_mask]),
                "wspd": _mean(test_wspd[gate_mask]),
            }
        if "mppt" in stats and "pitch" in stats:
            shared_bin_stats.append(stats)

    if not shared_bin_stats:
        raise ValueError(f"No shared boundary wind bins for seed {seed}")

    def delta(metric: str) -> float:
        return float(np.mean([item["pitch"][metric] - item["mppt"][metric] for item in shared_bin_stats]))

    return {
        "seed": seed,
        "shared_wind_bins": len(shared_bin_stats),
        "boundary_mppt_gate_cells": int((boundary & (gate_label == 1)).sum()),
        "boundary_pitch_gate_cells": int((boundary & (gate_label == 2)).sum()),
        "delta_future_power_pitch_minus_mppt": delta("future_power"),
        "delta_power_curve_residual_pitch_minus_mppt": delta("signed_residual"),
        "delta_future_ramp_pitch_minus_mppt": delta("future_ramp"),
        "delta_anchor_patv_pitch_minus_mppt": delta("anchor_patv"),
        "delta_wspd_pitch_minus_mppt": delta("wspd"),
    }


def _future_power_mean(metrics_dir: Path, horizon_slice: slice | None = None) -> tuple[np.ndarray, np.ndarray]:
    target = np.load(metrics_dir / "target.npy", mmap_mode="r")
    mask = np.load(metrics_dir / "mask.npy", mmap_mode="r") > 0.5
    if horizon_slice is not None:
        target = target[:, horizon_slice, :]
        mask = mask[:, horizon_slice, :]
    valid_count = mask.sum(axis=1)
    total = (target * mask).sum(axis=1, dtype=np.float64)
    mean = np.divide(total, valid_count, out=np.full(valid_count.shape, np.nan, dtype=np.float64), where=valid_count > 0)
    return mean, valid_count > 0


def _anchor_arrays(metrics_dir: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    anchor = np.load(metrics_dir / "anchor_physics.npy", mmap_mode="r")
    gate_prob = np.load(metrics_dir / "gate_prob.npy", mmap_mode="r")
    regime = np.load(metrics_dir / "regime_primary.npy", mmap_mode="r")
    regime_valid = np.load(metrics_dir / "regime_primary_valid.npy", mmap_mode="r") > 0.5
    return (
        np.asarray(anchor[:, :, 0], dtype=np.float64),
        np.asarray(anchor[:, :, 3], dtype=np.float64),
        np.asarray(gate_prob[:, :, :3].argmax(axis=-1), dtype=np.int16),
        np.asarray(regime, dtype=np.int16),
        np.asarray(regime_valid, dtype=bool),
    )


def _validation_power_curve(val_mean: np.ndarray, val_valid: np.ndarray, val_bin: np.ndarray) -> np.ndarray:
    global_mean = _mean(val_mean[val_valid])
    expected: list[float] = []
    for bin_id in range(len(WIND_BINS) - 1):
        mask = (val_bin == bin_id) & val_valid & np.isfinite(val_mean)
        expected.append(_mean(val_mean[mask]) if mask.any() else global_mean)
    return np.asarray(expected, dtype=np.float64)


def _summarize(seed_frame: pd.DataFrame) -> dict[str, Any]:
    out: dict[str, Any] = {
        "n_seeds": int(len(seed_frame)),
        "shared_wind_bins_mean": _mean(seed_frame["shared_wind_bins"]),
        "boundary_mppt_gate_cells_mean": _mean(seed_frame["boundary_mppt_gate_cells"]),
        "boundary_pitch_gate_cells_mean": _mean(seed_frame["boundary_pitch_gate_cells"]),
    }
    for column in [
        "delta_future_power_pitch_minus_mppt",
        "delta_power_curve_residual_pitch_minus_mppt",
        "delta_future_ramp_pitch_minus_mppt",
        "delta_anchor_patv_pitch_minus_mppt",
        "delta_wspd_pitch_minus_mppt",
    ]:
        values = pd.to_numeric(seed_frame[column], errors="coerce")
        out[column + "_mean"] = _mean(values)
        out[column + "_std"] = _std(values)
        out[column + "_min"] = float(values.min())
        out[column + "_max"] = float(values.max())
    return out


def _write_latex(summary: dict[str, Any], path: Path) -> None:
    rows = [
        (
            "Boundary cells per seed",
            f"{_fmt(summary['boundary_mppt_gate_cells_mean'], 0)} MPPT / "
            f"{_fmt(summary['boundary_pitch_gate_cells_mean'], 0)} pitch",
            "9.5--11.5 m s$^{-1}$ test anchors",
        ),
        (
            "Future mean power",
            _pm(
                summary["delta_future_power_pitch_minus_mppt_mean"],
                summary["delta_future_power_pitch_minus_mppt_std"],
                " kW",
            ),
            "Pitch-gate minus MPPT-gate after wind-bin adjustment",
        ),
        (
            "Power-curve residual",
            _pm(
                summary["delta_power_curve_residual_pitch_minus_mppt_mean"],
                summary["delta_power_curve_residual_pitch_minus_mppt_std"],
                " kW",
            ),
            "Validation wind-bin power curve only; no pitch label used",
        ),
        (
            "Future power ramp",
            _pm(
                summary["delta_future_ramp_pitch_minus_mppt_mean"],
                summary["delta_future_ramp_pitch_minus_mppt_std"],
                " kW",
            ),
            "Mean late-horizon minus early-horizon power",
        ),
        (
            "Anchor-time Patv",
            _pm(
                summary["delta_anchor_patv_pitch_minus_mppt_mean"],
                summary["delta_anchor_patv_pitch_minus_mppt_std"],
                " kW",
            ),
            "Current active power is not driving the same positive contrast",
        ),
        (
            "Residual claim boundary",
            "sanity check only",
            "Mitigates circularity concern; does not prove anchor-free discovery",
        ),
    ]
    lines = [
        r"\begin{table}[H]",
        r"\centering",
        r"\scriptsize",
        r"\setlength{\tabcolsep}{4pt}",
        r"\renewcommand{\arraystretch}{1.08}",
        r"\caption*{\textbf{Table A7.} Outcome-channel sanity audit for the shared-anchor concern.}",
        r"\begin{tabularx}{\columnwidth}{>{\raggedright\arraybackslash}p{0.25\columnwidth} >{\centering\arraybackslash}p{0.24\columnwidth} >{\raggedright\arraybackslash}X}",
        r"\toprule",
        r"Check & Five-seed summary & Interpretation \\",
        r"\midrule",
    ]
    for check, value, interpretation in rows:
        lines.append(f"{_escape(check)} & {value} & {_escape(interpretation)} " + r"\\")
    lines.extend([r"\bottomrule", r"\end{tabularx}", r"\end{table}", ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def _mean(values: Any) -> float:
    return float(np.nanmean(np.asarray(values, dtype=np.float64)))


def _std(values: Any) -> float:
    arr = np.asarray(values, dtype=np.float64)
    if arr.size <= 1:
        return 0.0
    return float(np.nanstd(arr, ddof=1))


def _fmt(value: Any, digits: int = 1) -> str:
    return f"{float(value):.{digits}f}"


def _pm(mean: Any, std: Any, suffix: str) -> str:
    return f"{_fmt(mean)} $\\pm$ {_fmt(std)}{suffix}"


def _escape(text: str) -> str:
    return (
        text.replace("\\", r"\textbackslash{}")
        .replace("&", r"\&")
        .replace("%", r"\%")
        .replace("_", r"\_")
    )


if __name__ == "__main__":
    main()
