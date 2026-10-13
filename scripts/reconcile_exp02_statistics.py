"""EXP-02 consistency checker: asserts the report agrees with the frozen artifact.

History
-------
This file previously *wrote* ``docs/ZERO_PRIVILEGED_SUPERVISION_REPORT.md``, as a
second writer racing the report embedded in
``scripts/run_exp02_zero_privileged_supervision.py``. Two writers to one path
meant the committed report depended on which script was run last, and this one
carried prose figures that were not recomputed from the CSV -- including the
claim that "individual seed 95% bootstrap CIs span zero across all seeds", which
is false for h=1 seeds 202 and 205.

It is now a read-only checker. Its job is to fail when the published report and
the frozen benchmark CSV disagree, so the contradiction surfaces in CI instead of
in a report a reader has to trust. The single writer is
``run_exp02_zero_privileged_supervision.py``.

Exit code 0 = consistent. Non-zero = at least one contradiction.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from exp02_verdict import (  # noqa: E402
    PRIMARY_BASELINE,
    PRIMARY_CHALLENGER,
    assign_model_role,
    derive_verdict,
    VerdictInputs,
)

CSV_PATH = ROOT / "artifacts" / "zero_privileged_supervision_benchmark.csv"
REPORT_PATH = ROOT / "docs" / "ZERO_PRIVILEGED_SUPERVISION_REPORT.md"


def _k(value: float) -> str:
    """Format a kWh value the way the report does, e.g. '+3,435.5k'."""
    return f"{value/1e3:+,.1f}k"


def check_role_labels(df: pd.DataFrame, failures: list[str]) -> None:
    for model, grp in df.groupby("model"):
        expected = assign_model_role(model)
        actual = set(grp["model_role"])
        if actual != {expected}:
            failures.append(
                f"role mismatch for {model!r}: CSV has {sorted(actual)}, "
                f"expected {{{expected!r}}}"
            )

    challenger_roles = set(
        df.loc[df["model"].str.startswith("Zero-Privileged Challenger"), "model_role"]
    )
    if "Oracle Upper Reference (Non-Competitive)" in challenger_roles:
        failures.append(
            "a Zero-Privileged Challenger variant is labelled as an Oracle reference"
        )


def check_report_numbers(df: pd.DataFrame, report: str, failures: list[str]) -> None:
    """Every headline figure the report states must be re-derivable from the CSV."""
    chal = df[df["model"] == PRIMARY_CHALLENGER]
    base = df[df["model"] == PRIMARY_BASELINE]

    for horizon in ("h=1", "h=6"):
        c = chal[chal["horizon"] == horizon]
        b = base[base["horizon"] == horizon]
        if len(c) == 0 or len(b) == 0:
            failures.append(f"missing challenger/baseline rows for {horizon}")
            continue

        mean_delta = float(c["full_delta_psrei_mean"].mean())
        p_ni = float(c["full_p_non_inferior"].mean())

        for label, literal in (
            ("mean delta PSREI", _k(mean_delta)),
            ("P(non-inferior)", f"{p_ni:.4f}"),
        ):
            if literal not in report:
                failures.append(
                    f"{horizon}: report does not state {label} = {literal} "
                    f"(expected value absent from the text)"
                )

        # The verdict the report declares must equal the verdict the rule derives.
        derived = derive_verdict(
            VerdictInputs(
                horizon=horizon,
                mean_delta_psrei_kwh=mean_delta,
                p_non_inferior=p_ni,
                delta_violation_pp=float(
                    c["full_violation_rate_pct"].mean() - b["full_violation_rate_pct"].mean()
                ),
                delta_shortage_kwh=float(
                    c["full_shortage_kwh"].mean() - b["full_shortage_kwh"].mean()
                ),
            )
        )
        if derived.code not in report:
            failures.append(
                f"{horizon}: report omits the derived verdict code {derived.code}"
            )


def check_no_deficit_verdict(report: str, failures: list[str]) -> None:
    """The withdrawn 'deficit established' verdict must not reappear as a claim.

    The phrase is permissible only inside an explicit negation, which may sit
    before or after it ("CANNOT be concluded that ... deficit is established",
    "DEFICIT NOT ESTABLISHED"). A bare, unnegated assertion is a failure.
    """
    pattern = re.compile(r"(?i)deficit\s+(?:is\s+)?established")
    for m in pattern.finditer(report):
        window = report[max(0, m.start() - 260): m.end() + 260]
        negated = re.search(
            r"(?i)cannot|can not|not\s+be\s+concluded|not\s+established|"
            r"rather\s+than|withdrawn|no\s+longer|instead\s+of",
            window,
        )
        if not negated:
            line_no = report[:m.start()].count("\n") + 1
            failures.append(
                f"report asserts 'deficit established' without an explicit negation "
                f"(line {line_no})"
            )


def check_span_zero_claim(df: pd.DataFrame, report: str, failures: list[str]) -> None:
    """Guards the historical false claim that every seed CI spans zero."""
    if not re.search(r"(?i)span(s|ning)? zero across all seeds", report):
        return
    for horizon in ("h=1", "h=6"):
        c = df[(df["horizon"] == horizon) & (df["model"] == PRIMARY_CHALLENGER)]
        excluding = c[(c["full_delta_psrei_ci95_high"] < 0) | (c["full_delta_psrei_ci95_low"] > 0)]
        if len(excluding) > 0:
            seeds = sorted(int(s) for s in excluding["seed"])
            failures.append(
                f"report claims all seed CIs span zero at {horizon}, but seeds "
                f"{seeds} have CIs excluding zero"
            )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", default=str(CSV_PATH))
    parser.add_argument("--report", default=str(REPORT_PATH))
    args = parser.parse_args()

    csv_path, report_path = Path(args.csv), Path(args.report)
    if not csv_path.exists():
        print(f"CONSISTENCY_CHECK: FAIL\n- missing benchmark artifact: {csv_path}")
        return 2
    if not report_path.exists():
        print(f"CONSISTENCY_CHECK: FAIL\n- missing report: {report_path}")
        return 2

    df = pd.read_csv(csv_path)
    # Tolerate the pre-rename column name so a frozen v1 CSV still checks.
    df = df.rename(columns={
        "full_delta_psrei_pval": "full_p_non_inferior",
        "bnd_delta_psrei_pval": "bnd_p_non_inferior",
    })
    report = report_path.read_text(encoding="utf-8")

    failures: list[str] = []
    check_role_labels(df, failures)
    check_report_numbers(df, report, failures)
    check_no_deficit_verdict(report, failures)
    check_span_zero_claim(df, report, failures)

    if failures:
        print(f"CONSISTENCY_CHECK: FAIL ({len(failures)} contradiction(s))")
        for f in failures:
            print(f" - {f}")
        return 1

    # Summarise the counts the report depends on, as positive evidence.
    chal = df[df["model"] == PRIMARY_CHALLENGER]
    for horizon in ("h=1", "h=6"):
        c = chal[chal["horizon"] == horizon]
        ci_excl = c[(c["full_delta_psrei_ci95_high"] < 0) | (c["full_delta_psrei_ci95_low"] > 0)]
        print(
            f"[ok] {horizon}: mean delta {_k(float(c['full_delta_psrei_mean'].mean()))} kWh, "
            f"P(non-inferior) {float(c['full_p_non_inferior'].mean()):.4f}, "
            f"{len(ci_excl)}/{len(c)} per-seed CIs exclude zero"
        )
    print("CONSISTENCY_CHECK: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
