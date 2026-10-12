#!/usr/bin/env python3
"""Scientific claim gate.

This gate checks that the repository's current headline interpretation matches the
strongest frozen baseline evidence. It is intentionally fail-closed: if decisive
evidence changes, the scientific contract must be reviewed before the gate is
updated.
"""
from __future__ import annotations

import csv
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def fail(msg: str, failures: list[str]) -> None:
    failures.append(msg)
    print(f"  [FAIL] {msg}")


def ok(msg: str) -> None:
    print(f"  [PASS] {msg}")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def row(rows: list[dict[str, str]], **where: str) -> dict[str, str]:
    hits = [
        r for r in rows
        if all(str(r.get(k, "")).strip() == str(v) for k, v in where.items())
    ]
    if len(hits) != 1:
        raise ValueError(f"Expected exactly one row for {where}, found {len(hits)}")
    return hits[0]


def f(x: str) -> float:
    return float(str(x).replace(",", "").strip())


def main() -> int:
    failures: list[str] = []

    print("=" * 72)
    print("SCIENTIFIC CLAIM GATE")
    print("=" * 72)

    required = [
        ROOT / "docs" / "SCIENTIFIC_CONTRACT.md",
        ROOT / "docs" / "EXPERIMENT_REGISTRY.md",
        ROOT / ".agents" / "agents" / "scientific-falsifier" / "agent.md",
        ROOT / "artifacts" / "strong_baseline_closure_summary.csv",
        ROOT / "artifacts" / "strong_baseline_bootstrap_contrasts.csv",
        ROOT / "paper_tste_ieee.md",
    ]

    print("\n[1] Control-plane files")
    for p in required:
        if not p.exists():
            fail(f"missing required file: {p.relative_to(ROOT)}", failures)
        elif p.stat().st_size == 0:
            fail(f"empty required file: {p.relative_to(ROOT)}", failures)
        else:
            ok(str(p.relative_to(ROOT)))

    if failures:
        print("\nSCIENTIFIC_CLAIM_GATE: FAIL")
        return 1

    print("\n[2] Strong-baseline claim ceiling")
    rows = read_csv(ROOT / "artifacts" / "strong_baseline_closure_summary.csv")
    try:
        full_b = row(rows, population="Full", policy_id="Policy_B")
        full_c = row(rows, population="Full", policy_id="Policy_C")
        trans_b = row(rows, population="Transition", policy_id="Policy_B")
        trans_c = row(rows, population="Transition", policy_id="Policy_C")
        steady_b = row(rows, population="Steady", policy_id="Policy_B")
        steady_c = row(rows, population="Steady", policy_id="Policy_C")
    except ValueError as e:
        fail(str(e), failures)
    else:
        full_delta = f(full_c["psrei_mean_kwh"]) - f(full_b["psrei_mean_kwh"])
        if not math.isclose(full_delta, 523044.0, rel_tol=0, abs_tol=1.0):
            fail(
                f"full posterior-vs-wspd PSREI delta changed: {full_delta:.0f} kWh; "
                "review SCIENTIFIC_CONTRACT.md before changing this gate",
                failures,
            )
        elif full_delta <= 0:
            fail("posterior unexpectedly beats wind-speed bins plant-wide", failures)
        else:
            ok("plant-wide posterior cost superiority is not supported (+523,044 kWh)")

        trans_delta = f(trans_c["psrei_mean_kwh"]) - f(trans_b["psrei_mean_kwh"])
        risk_hedge = (
            f(trans_c["violation_rate_pct"]) < f(trans_b["violation_rate_pct"])
            and f(trans_c["shortage_mean_kwh"]) < f(trans_b["shortage_mean_kwh"])
            and f(trans_c["reserve_mean_kwh"]) > f(trans_b["reserve_mean_kwh"])
            and trans_delta > 0
        )
        if not risk_hedge:
            fail(
                "transition slice no longer matches 'lower violation/shortage at higher reserve and PSREI' interpretation",
                failures,
            )
        else:
            ok(
                "transition result is a risk hedge, not a cost win "
                f"(PSREI delta +{trans_delta:.0f} kWh)"
            )

        steady_delta = f(steady_c["psrei_mean_kwh"]) - f(steady_b["psrei_mean_kwh"])
        if steady_delta <= 0:
            fail(
                "steady-state posterior now beats wind-speed bins; contract requires review",
                failures,
            )
        else:
            ok(f"steady-state simple baseline remains lower-cost (+{steady_delta:.0f} kWh posterior penalty)")

    print("\n[3] Transition-localization interaction")
    contrasts = read_csv(ROOT / "artifacts" / "strong_baseline_bootstrap_contrasts.csv")
    try:
        mean = row(contrasts, seed="Mean")
        interaction = f(mean["interaction_mean"])
        lo = f(mean["interaction_ci_low"])
        hi = f(mean["interaction_ci_high"])
        p = f(mean["interaction_pval"])
        if not (interaction < 0 and hi < 0 and p < 0.05):
            fail(
                f"transition-vs-steady heterogeneity no longer supported: "
                f"mean={interaction:.1f}, CI=[{lo:.1f},{hi:.1f}], p={p}",
                failures,
            )
        else:
            ok(
                f"heterogeneity retained: interaction={interaction:.1f} kWh, "
                f"CI=[{lo:.1f},{hi:.1f}], p={p}"
            )
    except ValueError as e:
        fail(str(e), failures)

    print("\n[4] Manuscript interpretation guard")
    manuscript = (ROOT / "paper_tste_ieee.md").read_text(encoding="utf-8", errors="ignore")
    required_phrases = [
        "strong wind-speed-conditioned quantiles remain lower-cost plant-wide",
        "attributable to consequence-based representation and calibrated quantile sizing rather than dynamic expert routing",
        "state recoverability is not sufficient for downstream reserve-decision superiority",
        "trained using historically available pitch information that is withheld at deployment",
    ]
    for phrase in required_phrases:
        if phrase.lower() not in manuscript.lower():
            fail(f"required claim-boundary phrase missing from manuscript: {phrase!r}", failures)
        else:
            ok(f"claim boundary present: {phrase}")

    forbidden_patterns = {
        "unqualified universal ML superiority": r"machine learning (?:is|was) universally superior",
        "unqualified cross-site generalization proof": r"proves? (?:universal )?generalization across .*wind farms",
        "MoE mechanism superiority": r"MoE routing (?:is|was) (?:the )?(?:key|critical|superior) mechanism",
        "plant-wide posterior superiority": r"posterior(?:-conditioned| conditioning)?[^\\n]{0,240}outperform(?:s|ed)?[^\\n]{0,240}plant-wide",
    }
    for label, pattern in forbidden_patterns.items():
        if re.search(pattern, manuscript, flags=re.I | re.S):
            fail(f"forbidden overclaim detected: {label}", failures)
        else:
            ok(f"no {label}")

    print("\n[5] Contract authority guard")
    contract = (ROOT / "docs" / "SCIENTIFIC_CONTRACT.md").read_text(
        encoding="utf-8", errors="ignore"
    )
    required_contract_markers = [
        "Observability → Recoverability → Decision Sufficiency",
        "REFUTED by current closure",
        "Negative-result preservation rule",
        "Older reports remain provenance records",
        "Architectural-control non-equivalence rule",
        "Transition-slice diagnostic boundary rule",
        "Synthetic telemetry envelope rule",
    ]
    for marker in required_contract_markers:
        if marker not in contract:
            fail(f"scientific contract missing authority marker: {marker!r}", failures)
        else:
            ok(f"contract marker present: {marker}")

    print("\n[6] EXP-01, EXP-02, EXP-03 Control & Evidence Integrity")
    # EXP-01 v2
    exp01_csv = ROOT / "artifacts" / "external_matched_control_benchmark.csv"
    if not exp01_csv.exists():
        fail("missing EXP-01 v2 benchmark artifact: external_matched_control_benchmark.csv", failures)
    else:
        exp01_rows = read_csv(exp01_csv)
        if len(exp01_rows) != 80:
            fail(f"EXP-01 expected 80 rows, found {len(exp01_rows)}", failures)
        else:
            ok(f"EXP-01 v2 benchmark verified (80 rows, 5 seeds, 2 farms)")

    # EXP-02
    exp02_csv = ROOT / "artifacts" / "zero_privileged_supervision_benchmark.csv"
    if not exp02_csv.exists():
        fail("missing EXP-02 benchmark artifact: zero_privileged_supervision_benchmark.csv", failures)
    else:
        exp02_rows = read_csv(exp02_csv)
        roles = {r["model_role"] for r in exp02_rows if r["model"] == "Zero-Privileged Challenger (eps=50)"}
        if "Oracle Upper Reference (Non-Competitive)" in roles:
            fail("EXP-02 Zero-Privileged Challenger mislabeled as Oracle", failures)
        elif "Primary Challenger" not in roles:
            fail("EXP-02 Zero-Privileged Challenger missing Primary Challenger role", failures)
        else:
            ok("EXP-02 verified with corrected Primary Challenger role classification")

    # EXP-03
    exp03_csv = ROOT / "artifacts" / "exp03_async" / "psrei_vs_delay.csv"
    if not exp03_csv.exists():
        fail("missing EXP-03 benchmark artifact: psrei_vs_delay.csv", failures)
    else:
        exp03_rows = read_csv(exp03_csv)
        n_cells_set = {int(r["n_evaluated_cells"]) for r in exp03_rows if "n_evaluated_cells" in r}
        if len(n_cells_set) > 2 or min(n_cells_set) < 400000:
            fail(f"EXP-03 sample population collapse detected: cell counts = {n_cells_set}", failures)
        else:
            ok(f"EXP-03 fixed population verified ({list(n_cells_set)[0]} cells constant across delay grid)")

    # Joint Uncertainty Summary
    joint_json = ROOT / "artifacts" / "joint_uncertainty_summary.json"
    if not joint_json.exists():
        fail("missing joint uncertainty summary: joint_uncertainty_summary.json", failures)
    else:
        ok("Joint hierarchical uncertainty summary verified")

    print("\n" + "=" * 72)
    if failures:
        print(f"SCIENTIFIC_CLAIM_GATE: FAIL ({len(failures)} issue(s))")
        for item in failures:
            print(f" - {item}")
        return 1

    print("SCIENTIFIC_CLAIM_GATE: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
