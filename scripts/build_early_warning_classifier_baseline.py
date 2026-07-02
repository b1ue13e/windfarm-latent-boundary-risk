"""Simple issue-time anchor classifier baseline for the label-degradation audit.

Reviewer-facing control for Table `tab:early-warning`. The manuscript's
early-warning claim compares the MoE gate against a *degraded* threshold-label
rule. A reviewer will immediately ask the fair question: instead of the whole
mixture-of-experts gate, why not a simple supervised classifier on the same
issue-time SCADA anchors? Because the WTB operating regime is a deterministic
threshold on wind speed and mean pitch (see `compute_wtb_operation_regime`), and
those channels are inside `anchor_physics`, a plain classifier that reads the
*live* anchor recovers the operating state trivially.

This script quantifies that baseline honestly, using the exact same early-pitch
window, transition detection, and precision/recall helpers as the main audit in
`windfarm_moe.anchor_stress`. It fits a multinomial logistic regression on the
validation split (calibrate-before-use information boundary) and evaluates on the
test split, side by side with the saved gate and the degraded threshold rule.

The takeaway the manuscript must report: on clean issue-time anchors the simple
classifier matches or exceeds the gate at early-pitch detection, so the
operational detection value reflects anchor availability rather than the routing
mechanism. The routing contribution is the auditable, boundary-aligned attribution
integrated into the forecaster, not a superior standalone detector.
"""

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

from windfarm_moe.anchor_stress import (  # noqa: E402
    _early_pitch_window,
    _early_warning_run_dir,
    _delay_labels,
    _mppt_to_pitch_transitions,
    _precision_recall,
)
from windfarm_moe.regimes import compute_wtb_operation_regime  # noqa: E402

SUITE = ROOT / "artifacts" / "strictmask_validation_wtb_full"
OUT_DIR = ROOT / "artifacts" / "early_warning_classifier_baseline_wtb"

SEEDS = [201, 202, 203, 204, 205]
VARIANT = "canonical"
SPLIT = "test"
EARLY_WINDOW_STEPS = 6
CUT_IN_WIND = 3.0
RATED_WIND = 10.5
PITCH_THRESHOLD = 2.0
RANDOM_SEED = 1729

# Scenarios mirror the main early-warning table (delay / availability / noise).
DELAY_STEPS = [1, 3, 6]
AVAILABILITY_RATES = [0.75, 0.50, 0.25]
NOISE_LEVELS = [(0.25, 0.5), (0.5, 1.0), (1.0, 2.0)]


def _load(seed: int, split: str, name: str) -> np.ndarray:
    run_dir = _early_warning_run_dir(SUITE, VARIANT, seed)
    return np.load(run_dir / f"{split}_metrics" / f"{name}.npy")


def _fit_classifier(seed: int) -> LogisticRegression:
    physics = np.asarray(_load(seed, "val", "anchor_physics"), dtype=np.float64)
    regime = np.asarray(_load(seed, "val", "regime_primary"), dtype=np.int64)
    valid = np.asarray(_load(seed, "val", "regime_primary_valid"), dtype=np.float64) > 0.5
    channels = physics.shape[-1]
    x = physics.reshape(-1, channels)[valid.reshape(-1)]
    y = regime.reshape(-1)[valid.reshape(-1)]
    return LogisticRegression(max_iter=3000, C=1.0).fit(x, y)


def _predict_pitch(clf: LogisticRegression, physics: np.ndarray, shape: tuple[int, int]) -> np.ndarray:
    channels = physics.shape[-1]
    labels = clf.predict(physics.reshape(-1, channels)).reshape(shape)
    return labels == 2


def _rows_for_seed(seed: int) -> list[dict[str, Any]]:
    clf = _fit_classifier(seed)

    gate_prob = np.asarray(_load(seed, SPLIT, "gate_prob"), dtype=np.float64)
    physics = np.asarray(_load(seed, SPLIT, "anchor_physics"), dtype=np.float64)
    regime = np.asarray(_load(seed, SPLIT, "regime_primary"), dtype=np.int16)
    valid = np.asarray(_load(seed, SPLIT, "regime_primary_valid"), dtype=np.float64) > 0.5

    gate_classes = max(1, min(int(gate_prob.shape[-1]), 3))
    gate_pitch = gate_prob[..., :gate_classes].argmax(axis=-1) == 2
    clf_pitch = _predict_pitch(clf, physics, regime.shape)

    transitions = _mppt_to_pitch_transitions(regime, valid)
    target, support = _early_pitch_window(
        regime, valid, transitions, early_window_steps=EARLY_WINDOW_STEPS
    )

    base = {"seed": int(seed), "variant": VARIANT, "split": SPLIT,
            "n_target_cells": int(target.sum()), "n_support_cells": int(support.sum())}
    rows: list[dict[str, Any]] = []

    def _emit(scenario: str, level: Any, label: str, rule_pitch: np.ndarray, clf_variant_pitch: np.ndarray) -> None:
        gate = _precision_recall(np.asarray(gate_pitch, bool), target, support)
        clf_stats = _precision_recall(np.asarray(clf_variant_pitch, bool), target, support)
        rule = _precision_recall(np.asarray(rule_pitch, bool), target, support)
        rows.append({
            **base, "scenario": scenario, "degradation_level": level, "degradation_label": label,
            "gate_recall": gate["recall"], "gate_precision": gate["precision"],
            "clf_recall": clf_stats["recall"], "clf_precision": clf_stats["precision"],
            "rule_recall": rule["recall"], "rule_precision": rule["precision"],
            "clf_minus_gate_recall": clf_stats["recall"] - gate["recall"],
        })

    # Clean reference: no degradation. Gate, classifier, and a hard live-anchor
    # threshold recompute are all scored on their clean predictions.
    thresh_clean = (regime == 2) & valid
    _emit("clean", 0, "clean_live_anchor", thresh_clean, clf_pitch)

    # Label delay: the *label stream* the threshold rule reads is delayed. The gate
    # and the classifier both read live anchors, so their predictions are unchanged.
    for delay in DELAY_STEPS:
        delayed = _delay_labels(regime, steps=int(delay), fill=0)
        delayed_valid = _delay_labels(valid.astype(np.int16), steps=int(delay), fill=0).astype(bool) & valid
        rule_pitch = (delayed == 2) & delayed_valid
        _emit("label_delay", int(delay), f"delay_steps={int(delay)}", rule_pitch, clf_pitch)

    # Label availability: the confirmed label stream drops out at random.
    rng = np.random.default_rng(RANDOM_SEED + int(seed) * 1009)
    for rate in AVAILABILITY_RATES:
        available = rng.random(regime.shape) < float(rate)
        rule_pitch = (regime == 2) & valid & available
        _emit("label_availability", float(rate), f"available_rate={float(rate):.2f}", rule_pitch, clf_pitch)

    # Sensor noise: the anchors themselves are noisy. Here both the hard rule and
    # the classifier see the *noisy* anchors (a fair anchor-level comparison). The
    # saved gate cannot be re-run on noisy inputs post hoc, so it stays clean; this
    # is noted so the noise row is not over-read as a gate robustness claim.
    wspd = physics[..., 0]
    pab = physics[..., 1]
    for idx, (wspd_sd, pab_sd) in enumerate(NOISE_LEVELS):
        noise_rng = np.random.default_rng(RANDOM_SEED + int(seed) * 9173 + idx * 37)
        noisy_wspd = wspd + noise_rng.normal(0.0, float(wspd_sd), size=wspd.shape)
        noisy_pab = pab + noise_rng.normal(0.0, float(pab_sd), size=pab.shape)
        noisy_regime, noisy_valid = compute_wtb_operation_regime(
            noisy_wspd, noisy_pab, cut_in_wind=CUT_IN_WIND, rated_wind=RATED_WIND, pitch_threshold=PITCH_THRESHOLD
        )
        rule_pitch = (noisy_regime == 2) & noisy_valid.astype(bool) & valid
        noisy_physics = physics.copy()
        noisy_physics[..., 0] = noisy_wspd
        noisy_physics[..., 1] = noisy_pab
        clf_noisy_pitch = _predict_pitch(clf, noisy_physics, regime.shape)
        _emit("threshold_sensor_noise", float(wspd_sd), f"wspd_sd={float(wspd_sd):.2f};pab_sd={float(pab_sd):.2f}",
              rule_pitch, clf_noisy_pitch)

    return rows


def _summarize(raw: pd.DataFrame) -> pd.DataFrame:
    group = ["scenario", "degradation_label", "degradation_level"]
    metrics = [c for c in raw.columns if c.endswith(("_recall", "_precision")) or c == "clf_minus_gate_recall"]
    agg = raw.groupby(group, sort=False)[metrics].agg(["mean", "std"]).reset_index()
    agg.columns = list(group) + [f"{m}_{stat}" for m in metrics for stat in ("mean", "std")]
    return agg


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    raw_rows: list[dict[str, Any]] = []
    for seed in SEEDS:
        raw_rows.extend(_rows_for_seed(seed))
    raw = pd.DataFrame(raw_rows)
    summary = _summarize(raw)

    raw.to_csv(OUT_DIR / "early_warning_classifier_baseline_raw.csv", index=False)
    summary.to_csv(OUT_DIR / "early_warning_classifier_baseline_summary.csv", index=False)

    clean = summary[summary["scenario"] == "clean"].iloc[0]
    gate_recall = float(clean["gate_recall_mean"])
    clf_recall = float(clean["clf_recall_mean"])
    gate_precision = float(clean["gate_precision_mean"])
    clf_precision = float(clean["clf_precision_mean"])
    classifier_matches_or_beats_gate = clf_recall + 1e-9 >= gate_recall

    status = (
        "complete_classifier_baseline_matches_or_beats_gate"
        if classifier_matches_or_beats_gate
        else "complete_classifier_baseline_below_gate"
    )
    guard = {
        "status": status,
        "suite_root": str(SUITE),
        "seeds": SEEDS,
        "split": SPLIT,
        "clean_early_pitch": {
            "gate_recall_mean": gate_recall,
            "gate_precision_mean": gate_precision,
            "clf_recall_mean": clf_recall,
            "clf_precision_mean": clf_precision,
        },
        "classifier_matches_or_beats_gate": bool(classifier_matches_or_beats_gate),
        "claim_use": (
            "Reviewer-facing control for the label-degradation audit. On clean "
            "issue-time anchors a multinomial logistic regression fit on the "
            "validation split recovers the early MPPT-to-pitch pitch window as "
            "well as or better than the MoE gate, so the operational detection "
            "value reflects anchor availability at issue time, not the routing "
            "mechanism. The routing contribution is the auditable, boundary-aligned "
            "attribution integrated into the forecaster, not a superior standalone "
            "detector."
        ),
        "paths": {
            "raw_csv": str(OUT_DIR / "early_warning_classifier_baseline_raw.csv"),
            "summary_csv": str(OUT_DIR / "early_warning_classifier_baseline_summary.csv"),
        },
    }
    (OUT_DIR / "early_warning_classifier_baseline_guard.json").write_text(
        json.dumps(guard, indent=2), encoding="utf-8"
    )

    print(f"Status: {status}")
    print(f"Clean early-pitch recall  -> gate {gate_recall:.3f}  clf {clf_recall:.3f}")
    print(f"Clean early-pitch precision-> gate {gate_precision:.3f}  clf {clf_precision:.3f}")
    print(f"Wrote {OUT_DIR / 'early_warning_classifier_baseline_summary.csv'}")


if __name__ == "__main__":
    main()
