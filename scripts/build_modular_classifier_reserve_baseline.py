from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from windfarm_moe.decision import (  # noqa: E402
    DEFAULT_QUANTILES,
    _assign_bins,
    _boundary_selector,
    _calibrate_scalar,
    _cost_metrics,
    _filter_panel,
    _load_cache_meta,
    _load_panel,
    _risk_thresholds,
    select_default_wtb_runs,
)


RUN_TABLE = ROOT / "artifacts" / "strictmask_combined_reviewer_stats" / "reviewer_stat_pack_run_table.csv"
CACHE_DIR = ROOT / "artifacts" / "cache_strictmask" / "wtb_245d"
RESERVE_RAW = ROOT / "artifacts" / "decision_reserve_wtb_operational_windows" / "reserve_decision_raw_runs.csv"
OUT_DIR = ROOT / "artifacts" / "modular_classifier_reserve_control"
MAIN_RATIO = 10.0
BOUNDARY_BAND = 1.0
MAX_CLASSIFIER_ROWS = 200_000


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cache_meta = _load_cache_meta(CACHE_DIR, boundary_band=BOUNDARY_BAND)
    dt = 1.0 / float(cache_meta["steps_per_hour"])
    runs = [run for run in select_default_wtb_runs(RUN_TABLE, root_dir=ROOT) if run.model == "Graph WaveNet"]
    rows = [_rows_for_run(run, cache_meta, dt) for run in runs]
    classifier_raw = pd.DataFrame(rows)
    reserve_raw = pd.read_csv(RESERVE_RAW)
    summary = _summary_rows(classifier_raw, reserve_raw)
    paired = _paired_rows(classifier_raw, reserve_raw)

    classifier_raw.to_csv(OUT_DIR / "modular_classifier_reserve_raw.csv", index=False)
    summary.to_csv(OUT_DIR / "modular_classifier_reserve_summary.csv", index=False)
    paired.to_csv(OUT_DIR / "modular_classifier_reserve_paired.csv", index=False)
    _write_latex(summary, paired, OUT_DIR / "table_modular_classifier_reserve_control.tex")

    payload = {
        "status": "complete_modular_classifier_reserve_control",
        "claim_use": (
            "Reviewer-facing modular-control baseline. A Graph WaveNet predictor is paired with "
            "a validation-fit live-anchor logistic classifier and the same validation-frozen "
            "boundary-window reserve protocol. Use this to show the modular alternative is tested "
            "directly; it remains a control for reserve slicing, not an in-model route-responsibility "
            "mechanism."
        ),
        "inputs": {
            "run_table": str(RUN_TABLE),
            "cache_dir": str(CACHE_DIR),
            "reserve_raw": str(RESERVE_RAW),
        },
        "outputs": {
            "raw": str(OUT_DIR / "modular_classifier_reserve_raw.csv"),
            "summary": str(OUT_DIR / "modular_classifier_reserve_summary.csv"),
            "paired": str(OUT_DIR / "modular_classifier_reserve_paired.csv"),
            "tex": str(OUT_DIR / "table_modular_classifier_reserve_control.tex"),
        },
    }
    (OUT_DIR / "modular_classifier_reserve_control.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )
    print(f"Wrote {OUT_DIR / 'modular_classifier_reserve_summary.csv'}")


def _rows_for_run(run: Any, cache_meta: dict[str, Any], dt: float) -> dict[str, Any]:
    val_full = _load_panel(run.run_dir / "val_metrics", cache_meta)
    test_full = _load_panel(run.run_dir / "test_metrics", cache_meta)
    val = _filter_panel(val_full, _boundary_selector(val_full, want_boundary=True))
    test = _filter_panel(test_full, _boundary_selector(test_full, want_boundary=True))
    clf = _fit_classifier(run.run_dir / "val_metrics", seed=int(run.seed))
    val_score = _classifier_pitch_score(clf, run.run_dir / "val_metrics")[_boundary_selector(val_full, want_boundary=True)]
    test_score = _classifier_pitch_score(clf, run.run_dir / "test_metrics")[_boundary_selector(test_full, want_boundary=True)]

    global_reserve, global_quantile = _calibrate_scalar(
        val.shortfall,
        val.valid,
        MAIN_RATIO,
        dt,
        DEFAULT_QUANTILES,
    )
    thresholds = _risk_thresholds(val_score)
    val_labels = _assign_bins(val_score, thresholds)
    test_labels = _assign_bins(test_score, thresholds)
    reserves: dict[str, float] = {}
    quantiles: dict[str, float] = {}
    for idx, name in enumerate(["low", "mid", "high"]):
        mask = val.valid & (val_labels[:, None] == idx)
        if mask.any():
            reserve, quantile = _calibrate_scalar(val.shortfall, mask, MAIN_RATIO, dt, DEFAULT_QUANTILES)
        else:
            reserve, quantile = global_reserve, global_quantile
        reserves[name] = float(reserve)
        quantiles[name] = float(quantile)

    reserve_by_window = np.zeros(test_labels.shape[0], dtype=np.float64)
    for idx, name in enumerate(["low", "mid", "high"]):
        reserve_by_window[test_labels == idx] = reserves[name]
    reserve_matrix = np.repeat(reserve_by_window[:, None], test.shortfall.shape[1], axis=1)
    metrics = _cost_metrics(test.shortfall, test.valid, reserve_matrix, MAIN_RATIO, dt)
    return {
        "model": "Graph WaveNet + live-anchor classifier",
        "source_model": run.model,
        "seed": int(run.seed),
        "run_dir": str(run.run_dir),
        "policy": "classifier-bin",
        "subset": "boundary",
        "cost_ratio": MAIN_RATIO,
        "threshold_low": float(thresholds[0]),
        "threshold_high": float(thresholds[1]),
        "best_quantile": _fmt_mapping(quantiles, digits=3),
        "reserve": _fmt_mapping(reserves, digits=6),
        **metrics,
    }


def _fit_classifier(metrics_dir: Path, *, seed: int) -> LogisticRegression:
    physics = np.asarray(np.load(metrics_dir / "anchor_physics.npy", mmap_mode="r"), dtype=np.float64)
    regime = np.asarray(np.load(metrics_dir / "regime_primary.npy", mmap_mode="r"), dtype=np.int64)
    valid = np.asarray(np.load(metrics_dir / "regime_primary_valid.npy", mmap_mode="r"), dtype=np.float64) > 0.5
    x = physics.reshape(-1, physics.shape[-1])[valid.reshape(-1)]
    y = regime.reshape(-1)[valid.reshape(-1)]
    if x.shape[0] > MAX_CLASSIFIER_ROWS:
        rng = np.random.default_rng(20260702 + int(seed))
        chosen = rng.choice(x.shape[0], size=MAX_CLASSIFIER_ROWS, replace=False)
        x = x[chosen]
        y = y[chosen]
    return LogisticRegression(max_iter=3000, C=1.0).fit(x, y)


def _classifier_pitch_score(clf: LogisticRegression, metrics_dir: Path) -> np.ndarray:
    physics = np.asarray(np.load(metrics_dir / "anchor_physics.npy", mmap_mode="r"), dtype=np.float64)
    flat = physics.reshape(-1, physics.shape[-1])
    if 2 not in clf.classes_:
        probs = np.zeros(flat.shape[0], dtype=np.float64)
    else:
        pitch_idx = list(clf.classes_).index(2)
        probs = clf.predict_proba(flat)[:, pitch_idx]
    return probs.reshape(physics.shape[:2]).mean(axis=1).astype(np.float64)


def _summary_rows(classifier_raw: pd.DataFrame, reserve_raw: pd.DataFrame) -> pd.DataFrame:
    rows: list[pd.DataFrame] = [classifier_raw]
    for model, policy in [
        ("Graph WaveNet", "global"),
        ("Graph WaveNet", "physical-bin"),
        ("Boundary-forced router", "gate-bin"),
    ]:
        subset = reserve_raw[
            reserve_raw["model"].astype(str).eq(model)
            & reserve_raw["policy"].astype(str).eq(policy)
            & reserve_raw["subset"].astype(str).eq("boundary")
            & np.isclose(pd.to_numeric(reserve_raw["cost_ratio"], errors="coerce"), MAIN_RATIO)
        ].copy()
        subset["model"] = model
        subset["policy"] = policy
        rows.append(subset[classifier_raw.columns.intersection(subset.columns).tolist() + [
            column for column in subset.columns if column not in classifier_raw.columns
        ]])
    frame = pd.concat(rows, ignore_index=True, sort=False)
    metrics = ["total_cost", "violation_rate", "reserve_energy", "shortage_energy"]
    out = (
        frame.groupby(["model", "policy", "subset", "cost_ratio"], sort=False)[metrics]
        .agg(["mean", "std"])
        .reset_index()
    )
    out.columns = ["_".join([part for part in col if part]) if isinstance(col, tuple) else str(col) for col in out.columns]
    return out


def _paired_rows(classifier_raw: pd.DataFrame, reserve_raw: pd.DataFrame) -> pd.DataFrame:
    candidates = {
        "classifier-bin minus GWN physical-bin": _reserve_subset(reserve_raw, "Graph WaveNet", "physical-bin"),
        "classifier-bin minus Boundary gate-bin": _reserve_subset(reserve_raw, "Boundary-forced router", "gate-bin"),
        "classifier-bin minus GWN global": _reserve_subset(reserve_raw, "Graph WaveNet", "global"),
    }
    base = classifier_raw.set_index("seed")
    rows = []
    for label, reference in candidates.items():
        ref = reference.set_index("seed")
        for metric in ["total_cost", "violation_rate", "reserve_energy", "shortage_energy"]:
            diffs = (base[metric] - ref[metric]).dropna().astype(float).to_numpy()
            boot = _bootstrap_mean(diffs, seed=20260702 + len(label) + len(metric))
            rows.append(
                {
                    "comparison": label,
                    "metric": metric,
                    "mean_delta": float(diffs.mean()),
                    "ci_low": float(boot.quantile(0.025)),
                    "ci_high": float(boot.quantile(0.975)),
                    "n_pairs": int(diffs.size),
                }
            )
    return pd.DataFrame(rows)


def _reserve_subset(reserve_raw: pd.DataFrame, model: str, policy: str) -> pd.DataFrame:
    return reserve_raw[
        reserve_raw["model"].astype(str).eq(model)
        & reserve_raw["policy"].astype(str).eq(policy)
        & reserve_raw["subset"].astype(str).eq("boundary")
        & np.isclose(pd.to_numeric(reserve_raw["cost_ratio"], errors="coerce"), MAIN_RATIO)
    ].copy()


def _bootstrap_mean(values: np.ndarray, *, seed: int, n_boot: int = 20_000) -> pd.Series:
    array = np.asarray(values, dtype=float)
    rng = np.random.default_rng(seed)
    samples = rng.choice(array, size=(n_boot, array.size), replace=True)
    return pd.Series(samples.mean(axis=1))


def _write_latex(summary: pd.DataFrame, paired: pd.DataFrame, path: Path) -> None:
    rows = []
    display = summary.copy()
    display["label"] = display["model"].astype(str) + "/" + display["policy"].astype(str)
    for _, row in display.iterrows():
        rows.append(
            " & ".join(
                [
                    _escape(str(row["label"])),
                    _fmt_m(row["total_cost_mean"]),
                    _fmt_float(row["violation_rate_mean"], 4),
                    _fmt_m(row["reserve_energy_mean"]),
                    _fmt_m(row["shortage_energy_mean"]),
                ]
            )
            + r" \\"
        )
    key = paired[
        paired["comparison"].astype(str).eq("classifier-bin minus Boundary gate-bin")
        & paired["metric"].astype(str).isin(["total_cost", "violation_rate", "shortage_energy"])
    ]
    key_text = "; ".join(
        f"{str(row['metric']).replace('_', ' ')} {_fmt_delta(row['mean_delta'], row['metric'])} "
        f"[{_fmt_delta(row['ci_low'], row['metric'])},{_fmt_delta(row['ci_high'], row['metric'])}]"
        for _, row in key.iterrows()
    )
    lines = [
        r"\begin{table}[H]",
        r"\centering",
        r"\scriptsize",
        r"\setlength{\tabcolsep}{2.5pt}",
        r"\renewcommand{\arraystretch}{1.03}",
        r"\caption*{\textbf{Table A10c.} Modular live-anchor classifier reserve control at $\rho=10$ on the WTB boundary slice.}",
        r"\begin{tabularx}{\columnwidth}{>{\raggedright\arraybackslash}X >{\centering\arraybackslash}p{0.14\columnwidth} >{\centering\arraybackslash}p{0.12\columnwidth} >{\centering\arraybackslash}p{0.14\columnwidth} >{\centering\arraybackslash}p{0.14\columnwidth}}",
        r"\toprule",
        r"Policy & Cost & Viol. & Reserve & Shortage \\",
        r"\midrule",
        *rows,
        r"\bottomrule",
        r"\end{tabularx}",
        r"\vspace{1mm}",
        r"\footnotesize Classifier-bin uses Graph WaveNet forecasts plus a validation-fit live-anchor logistic classifier. Paired deltas vs Boundary/gate-bin: "
        + _escape(key_text)
        + r". It is a modular reserve-slicing control, not an in-model route-responsibility mechanism.",
        r"\end{table}",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def _fmt_mapping(values: dict[str, float], *, digits: int) -> str:
    return ";".join(f"{key}={value:.{digits}f}" for key, value in values.items())


def _fmt_m(value: Any) -> str:
    return f"{float(value) / 1_000_000.0:.2f}M"


def _fmt_float(value: Any, digits: int) -> str:
    return f"{float(value):.{digits}f}"


def _fmt_delta(value: Any, metric: str) -> str:
    number = float(value)
    if "cost" in metric or "energy" in metric:
        return f"{number / 1_000_000.0:+.2f}M"
    return f"{number:+.4f}"


def _escape(text: str) -> str:
    return (
        text.replace("\\", r"\textbackslash{}")
        .replace("&", r"\&")
        .replace("%", r"\%")
        .replace("_", r"\_")
    )


if __name__ == "__main__":
    main()
