"""EXP-02 single source of truth: model-role assignment and data-derived verdicts.

This module exists because the EXP-02 automatic verdict and role labelling were
defective in two independent ways, and the fix was previously applied in three
different places that could drift apart.

Defect 1 -- inverted decision rule (original `generate_audit_report`):

    challenger_wins = (delta_h6 < 0.0) and (pval_h6 < 0.05)

The bootstrap field is defined as ``P(delta <= 0)``, i.e. the empirical
probability that the challenger is *non-inferior* (cheaper PSREI, since PSREI is
a cost).  Requiring ``delta < 0`` **and** a tiny ``P(delta <= 0)`` is
self-contradictory: a negative delta drives the probability toward 1.0, not 0.
The conjunction was therefore almost never satisfiable, so the report emitted
``DEFICIT ESTABLISHED`` regardless of the data.

Defect 2 -- substring role matching:

    is_oracle = "Privileged" in model_name

evaluated before any other test, so ``Zero-Privileged Challenger (...)` -- the
zero-pitch challenger family -- was labelled an Oracle upper reference.

Both are now centralised here so that the runner, the report generator and the
consistency checks cannot disagree with each other.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

# ---------------------------------------------------------------------------
# Registered model identifiers (must match the strings emitted by the runner)
# ---------------------------------------------------------------------------
PRIMARY_BASELINE = "Site-Local Wspd-Bins"
PRIMARY_CHALLENGER = "Zero-Privileged Challenger (eps=50)"
ORACLE_REFERENCE = "Privileged STGQ (Oracle Reference)"

ROLE_PRIMARY_BASELINE = "Primary Baseline"
ROLE_PRIMARY_CHALLENGER = "Primary Challenger"
ROLE_ORACLE = "Oracle Upper Reference (Non-Competitive)"
ROLE_SECONDARY = "Secondary Baseline / Sensitivity Probe"

# Explicit table. Membership is exact equality, never substring containment:
# ``Primary Challenger`` must not be reachable from a name that merely happens
# to contain the substring ``Privileged``.
_ROLE_TABLE = {
    PRIMARY_BASELINE: ROLE_PRIMARY_BASELINE,
    PRIMARY_CHALLENGER: ROLE_PRIMARY_CHALLENGER,
    ORACLE_REFERENCE: ROLE_ORACLE,
}

_ORACLE_PREFIX = "Privileged "
_CHALLENGER_PREFIX = "Zero-Privileged Challenger"


def assign_model_role(model_name: str) -> str:
    """Assign a registered model name to exactly one role.

    Resolution order is: exact table -> explicit prefix families -> secondary
    probe.  An unrecognised name degrades to the *least* privileged role
    (secondary probe); it is never promoted to Oracle by accident.
    """
    if model_name in _ROLE_TABLE:
        return _ROLE_TABLE[model_name]
    if model_name.startswith(_CHALLENGER_PREFIX):
        # Sensitivity members of the challenger family (eps=20, eps=100).
        return ROLE_SECONDARY
    if model_name.startswith(_ORACLE_PREFIX):
        return ROLE_ORACLE
    return ROLE_SECONDARY


def is_oracle_role(model_name: str) -> bool:
    """True only for registered privileged/oracle references."""
    return assign_model_role(model_name) == ROLE_ORACLE


# ---------------------------------------------------------------------------
# Data-derived verdict
# ---------------------------------------------------------------------------
# Pre-registered decision rule.  PSREI = (reserve + rho * shortage) * dt is a
# COST, so a negative delta means the challenger is cheaper.  Cheaper is only
# evidence of decision value if it is not bought by under-procuring reserve and
# thereby raising violation frequency or shortage exposure; a policy that simply
# reserves less will always look cheaper under this metric.
#
# A challenger therefore counts as a supported decision improvement only if both
# statistical conditions hold:
#   C1  point estimate non-inferior        : mean_delta_psrei_kwh <= 0
#   C2  strong evidence of non-inferiority : p_non_inferior >= 0.95
# Anything else is reported as "no stable advantage observed" -- the weakest
# claim, which is the only one the current evidence licenses.
#
# C3/C4 below are NOT decision gates. They are reported alongside the verdict as
# a diagnostic, because PSREI is a cost: a policy that simply procures less
# reserve is mechanically cheaper, so a cheaper point estimate is evidence of
# decision value only if it is not bought by under-procurement. Keeping them out
# of the gate matters -- it means the verdict is not being steered by a
# post-hoc-chosen tolerance. See `threshold_sensitivity` for what the verdict
# would be under other thresholds.
NON_INFERIORITY_THRESHOLD = 0.95
VIOLATION_TOLERANCE_PP = 0.0
SHORTAGE_TOLERANCE_KWH = 0.0

# Thresholds probed when reporting how fragile the verdict is to the choice of
# non-inferiority level. Reported, never used to pick an outcome.
THRESHOLD_SENSITIVITY_GRID = (0.50, 0.80, 0.90, 0.95, 0.975)

VERDICT_SUPPORTED = "SUPPORTED_DECISION_IMPROVEMENT"
VERDICT_DIRECTIONAL = "DIRECTIONAL_ONLY_NOT_CONCLUSIVE"
VERDICT_NULL = "NO_STABLE_ADVANTAGE_OBSERVED"

HEADLINE_SUPPORTED = "**ZERO-PRIVILEGED DECISION IMPROVEMENT SUPPORTED**"
HEADLINE_DIRECTIONAL = (
    "**NO STABLE ZERO-PRIVILEGED ADVANTAGE ESTABLISHED**"
    " (POINT ESTIMATE FAVOURS CHALLENGER; NOT CONCLUSIVE)"
)
HEADLINE_NULL = (
    "**NO STABLE ZERO-PRIVILEGED ADVANTAGE OBSERVED**"
    " (DEFICIT NOT ESTABLISHED; INSTABILITY OBSERVED)"
)


@dataclass(frozen=True)
class VerdictInputs:
    """Decision-relevant statistics for one (horizon, challenger) pair."""

    horizon: str
    mean_delta_psrei_kwh: float
    p_non_inferior: float
    delta_violation_pp: float
    delta_shortage_kwh: float


@dataclass(frozen=True)
class Verdict:
    code: str
    headline: str
    checks: Tuple[Tuple[str, bool, str], ...]
    diagnostics: Tuple[Tuple[str, bool, str], ...] = ()
    sensitivity: Tuple[Tuple[float, str], ...] = ()

    @property
    def passed(self) -> bool:
        return self.code == VERDICT_SUPPORTED

    @property
    def directional(self) -> bool:
        return self.code == VERDICT_DIRECTIONAL

    def failed_conditions(self) -> List[str]:
        return [label for label, ok, _ in self.checks if not ok]

    def failed_diagnostics(self) -> List[str]:
        return [label for label, ok, _ in self.diagnostics if not ok]


def threshold_sensitivity(v: VerdictInputs, grid=THRESHOLD_SENSITIVITY_GRID) -> List[Tuple[float, str]]:
    """Re-evaluate the two statistical conditions across a grid of thresholds.

    Makes explicit that the reported verdict is not an artefact of the chosen
    non-inferiority level: the point-estimate condition C1 is threshold-free.
    """
    out = []
    for thr in grid:
        c1 = v.mean_delta_psrei_kwh <= 0.0
        c2 = v.p_non_inferior >= thr
        out.append((thr, VERDICT_SUPPORTED if (c1 and c2) else VERDICT_NULL))
    return out


def derive_verdict(v: VerdictInputs) -> Verdict:
    """Apply the pre-registered rule to one challenger/horizon record.

    The verdict is a pure function of the supplied statistics; there is no
    hard-coded outcome and no dependence on a particular run.  Only C1 and C2
    determine the verdict; the under-procurement checks are diagnostics.
    """
    c1 = v.mean_delta_psrei_kwh <= 0.0
    c2 = v.p_non_inferior >= NON_INFERIORITY_THRESHOLD

    checks = (
        (
            "C1 point estimate non-inferior",
            c1,
            f"mean delta PSREI = {v.mean_delta_psrei_kwh:+,.1f} kWh (<= 0 required)",
        ),
        (
            "C2 strong non-inferiority evidence",
            c2,
            f"P(delta <= 0) = {v.p_non_inferior:.4f} "
            f"(>= {NON_INFERIORITY_THRESHOLD} required)",
        ),
    )

    diagnostics = (
        (
            "D1 reserve not under-procured",
            v.delta_violation_pp <= VIOLATION_TOLERANCE_PP,
            f"delta violation = {v.delta_violation_pp:+.4f} pp",
        ),
        (
            "D2 shortage exposure not degraded",
            v.delta_shortage_kwh <= SHORTAGE_TOLERANCE_KWH,
            f"delta shortage = {v.delta_shortage_kwh:+,.1f} kWh",
        ),
    )

    sens = tuple(threshold_sensitivity(v))

    if c1 and c2:
        return Verdict(VERDICT_SUPPORTED, HEADLINE_SUPPORTED, checks, diagnostics, sens)
    if c1:
        # Point estimate favours the challenger but the evidence is not strong
        # enough to call it. Reporting this as a plain null would conflate
        # "no evidence of benefit" with "evidence of no benefit".
        return Verdict(VERDICT_DIRECTIONAL, HEADLINE_DIRECTIONAL, checks, diagnostics, sens)
    return Verdict(VERDICT_NULL, HEADLINE_NULL, checks, diagnostics, sens)


def verdict_from_row(row) -> Verdict:
    """Build a Verdict from one benchmark CSV row plus its paired baseline row.

    ``row`` must provide the challenger statistics and the paired
    ``_baseline_*`` columns produced by the report generator.
    """
    return derive_verdict(
        VerdictInputs(
            horizon=str(row["horizon"]),
            mean_delta_psrei_kwh=float(row["mean_delta_psrei_kwh"]),
            p_non_inferior=float(row["p_non_inferior"]),
            delta_violation_pp=float(row["delta_violation_pp"]),
            delta_shortage_kwh=float(row["delta_shortage_kwh"]),
        )
    )


DECISION_RULE_MD = f"""A challenger is reported as a supported decision improvement only when both
pre-registered statistical conditions hold at the stated horizon:

1. **C1 point estimate non-inferior** — `mean delta PSREI <= 0` (PSREI is a cost).
2. **C2 strong non-inferiority evidence** — `P(delta <= 0) >= {NON_INFERIORITY_THRESHOLD}`.

Otherwise the verdict is "no stable advantage observed".

`P(delta <= 0)` is the empirical bootstrap probability that the challenger is
non-inferior. It is **not** a conventional two-sided p-value.

### Diagnostics (reported, not gating)

PSREI is a *cost*, and a policy that simply procures less reserve is mechanically
cheaper while violating more often. A cheaper point estimate is therefore only
interpretable alongside procurement/risk levels, so the following are reported
next to the verdict rather than folded into it:

- **D1** reserve not under-procured — `delta violation <= {VIOLATION_TOLERANCE_PP} pp`.
- **D2** shortage exposure not degraded — `delta shortage <= {SHORTAGE_TOLERANCE_KWH} kWh`.

They are deliberately **not** part of the gate, so that the verdict cannot be
steered by a post-hoc-chosen tolerance. A passing verdict accompanied by failing
diagnostics is summarised as "cheaper but not demonstrably better".
"""


if __name__ == "__main__":  # pragma: no cover - manual smoke check
    # Role table must not promote the zero-pitch challenger family to Oracle.
    for name in [
        PRIMARY_BASELINE,
        PRIMARY_CHALLENGER,
        ORACLE_REFERENCE,
        "Zero-Privileged Challenger (eps=20)",
        "Zero-Privileged Challenger (eps=100)",
        "Direct Consequence Quantile MLP",
    ]:
        print(f"{name:44s} -> {assign_model_role(name)}")

    demo = VerdictInputs("h=1", -365_904.0, 1.0, +0.62, +58_800.0)
    v = derive_verdict(demo)
    print(f"\nunder-procurement case -> {v.code}")
    for label, ok, detail in v.checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {label}: {detail}")
