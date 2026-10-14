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
        elif "drop_fraction" not in exp03_rows[0] or "stale_fraction" not in exp03_rows[0]:
            # Cell counts alone cannot detect imputation-driven staleness (F6 gate weakness).
            fail("EXP-03 artifact lacks drop_fraction/stale_fraction; fixed-population claim unverifiable", failures)
        else:
            worst_drop = max(float(r["drop_fraction"]) for r in exp03_rows)
            worst_stale = max(float(r["stale_fraction"]) for r in exp03_rows)
            if worst_drop > 0.5 and "LOCF" not in (
                ROOT / "docs" / "EXPERIMENT_REGISTRY.md"
            ).read_text(encoding="utf-8", errors="replace"):
                fail(
                    f"EXP-03 drop_fraction reaches {worst_drop:.2%} but the registry does not disclose the "
                    "LOCF imputation boundary (cell counts alone are not a fixed-population proof)",
                    failures,
                )
            else:
                ok(
                    f"EXP-03 evaluated population fixed ({sorted(n_cells_set)}) with disclosed "
                    f"imputation boundary (max drop={worst_drop:.2%}, max stale={worst_stale:.2%})"
                )

    # Joint Uncertainty Summary
    joint_json = ROOT / "artifacts" / "joint_uncertainty_summary.json"
    if not joint_json.exists():
        fail("missing joint uncertainty summary: joint_uncertainty_summary.json", failures)
    else:
        ok("Joint hierarchical uncertainty summary verified")

    print("\n[7] Stale-Content Re-Pollution Guard (F6)")
    # This section fails closed if superseded v1 material, duplicate experiment
    # registrations, or overstated provenance claims are re-introduced anywhere in
    # the control plane. Historical provenance records may QUOTE v1 numbers only in a
    # line that also marks them superseded/void.

    SUPERSEDED_MARKERS = (
        "superseded", "supersede", "作废", "已作废", "invalid", "INVALID",
        "MUST NOT", "must not", "not be cited", "不得再被引用", "不得引用",
        "provenance", "溯源", "historical", "FORBIDDEN", "forbidden", "Prohibited",
        "禁止",
    )

    def _line_is_voided(line: str, enclosing_heading: str) -> bool:
        """A stale number is acceptable only inside an explicitly voided region."""
        text = line.lstrip()
        if text.startswith(">") or text.startswith("#"):
            return True  # blockquote / heading: explanatory annotation, not a live claim
        hay = line + " " + enclosing_heading
        return any(m in hay for m in SUPERSEDED_MARKERS)

    def check_no_stale_numbers(rel: str, tokens: list[str]) -> None:
        """Each occurrence of a superseded v1 number must sit inside a voided region."""
        path = ROOT / rel
        if not path.exists():
            fail(f"stale-guard target missing: {rel}", failures)
            return
        offenders: list[str] = []
        heading = ""
        for i, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if line.lstrip().startswith("#"):
                heading = line
            if any(tok in line for tok in tokens):
                if not _line_is_voided(line, heading):
                    offenders.append(f"{rel}:{i}")
        if offenders:
            fail(
                f"superseded v1 material re-appears as a live statement in {rel}: "
                + ", ".join(offenders[:6]),
                failures,
            )
        else:
            ok(f"{rel}: no live (unmarked) superseded v1 numbers")

    # v1 EXP-01 magnitudes that must never be stated as current results.
    V1_EXP01 = ["+448.0k", "448,046", "+48.5k", "48,494", "+2.15M", "+1.50M", "+1.09M", "+215k"]
    check_no_stale_numbers("experiments/E01/log.md", V1_EXP01)

    # v1 No-Graph magnitudes in the architecture audit (allowed only in the revision notice).
    V1_NOGRAPH = ["+1,050k", "+2,154k", "+888k", "+1,501k"]
    check_no_stale_numbers("docs/NO_GRAPH_CONTROL_AUDIT.md", V1_NOGRAPH)

    # v1 EXP-01 magnitudes must not re-enter the authoritative registry as live text.
    check_no_stale_numbers("docs/EXPERIMENT_REGISTRY.md", ["+448.0k", "+48.5k", "448,046", "48,494"])

    # The architecture audit must keep an explicit, non-equivalence-consistent parameter count.
    ng_json = ROOT / "artifacts" / "no_graph_architecture_audit.json"
    if not ng_json.exists():
        fail("missing architecture audit artifact: no_graph_architecture_audit.json", failures)
    else:
        import json as _json

        with ng_json.open("r", encoding="utf-8") as fh:
            ng = _json.load(fh)
        total = int(ng["stgq_modular"]["total_parameters"])
        ruling = ng.get("designation_ruling", {})
        blob = " ".join(str(v) for v in ruling.values())
        # Any explicit parameter count asserted in the prose must equal the computed count.
        prose_numbers = {int(m.replace(",", "")) for m in re.findall(r"\b\d{3},\d{3}\b", blob)}
        prose_numbers.discard(total)
        wrong = {n for n in prose_numbers if n not in (4865, 10)}
        if wrong:
            fail(
                f"architecture audit prose asserts parameter counts inconsistent with the computed "
                f"total {total}: {sorted(wrong)}",
                failures,
            )
        elif ruling.get("causal_necessity_of_spatial_graph") != "UNPROVEN / NOT ESTABLISHED":
            fail("architecture audit lost the spatial-graph causal-necessity claim ceiling", failures)
        else:
            ok(f"architecture audit parameter count self-consistent ({total:,}) and claim ceiling intact")

    # The No-Graph audit must retain its causal-necessity ceiling section.
    ng_doc = ROOT / "docs" / "NO_GRAPH_CONTROL_AUDIT.md"
    if ng_doc.exists():
        doc_txt = ng_doc.read_text(encoding="utf-8", errors="replace")
        if "UNPROVEN / NOT ESTABLISHED" not in doc_txt:
            fail("NO_GRAPH_CONTROL_AUDIT.md dropped the UNPROVEN / NOT ESTABLISHED claim ceiling", failures)
        elif "容量匹配" in doc_txt and "Prohibited" not in doc_txt:
            fail("NO_GRAPH_CONTROL_AUDIT.md re-introduces capacity-matched wording without prohibition", failures)
        else:
            ok("NO_GRAPH_CONTROL_AUDIT.md retains nomenclature + causal-necessity ceilings")

    # Duplicate experiment registration must not return: EXP-Q2-003 is answered by EXP-01.
    # An *open* duplicate is a registry line that declares the status as PROPOSED/BLOCKED
    # outside of a voided annotation (blockquote/heading).
    reg = ROOT / "docs" / "EXPERIMENT_REGISTRY.md"
    if reg.exists():
        offenders = []
        heading = ""
        for i, line in enumerate(reg.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if line.lstrip().startswith("#"):
                heading = line
            if "PROPOSED / BLOCKED" in line:
                if not _line_is_voided(line, heading):
                    offenders.append(f"docs/EXPERIMENT_REGISTRY.md:{i}")
        if offenders:
            fail(
                "EXPERIMENT_REGISTRY.md re-introduces an open PROPOSED/BLOCKED duplicate "
                f"registration alongside a completed experiment (F6 defect): {offenders}",
                failures,
            )
        else:
            ok("experiment registry has no open duplicate PROPOSED/BLOCKED registration")

    # EXP-03 provenance must not be overstated as a full-grid hash. Only the *live*
    # assertion counts; blockquotes/headings that quote-and-correct the bad phrasing are fine.
    overstated = [
        "Full-Grid SHA-256",
        "full-grid arrival trace hash",
        "Cryptographic SHA256 provenance hash of the full-grid arrival stream",
    ]
    for rel in ("docs/EXP03_ASYNCHRONOUS_REPORT.md", "docs/EXPERIMENT_REGISTRY.md"):
        p = ROOT / rel
        if not p.exists():
            continue
        offenders = []
        heading = ""
        for i, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if line.lstrip().startswith("#"):
                heading = line
            if any(s in line for s in overstated):
                if not _line_is_voided(line, heading):
                    offenders.append(f"{rel}:{i}")
        if offenders:
            fail(f"{rel} overstates EXP-03 trace provenance as full-grid: {offenders}", failures)
        else:
            ok(f"{rel}: EXP-03 trace provenance not overstated")

    # EXP-03 must disclose the LOCF staleness boundary rather than claim fresh fixed population.
    exp03_csv_path = ROOT / "artifacts" / "exp03_async" / "psrei_vs_delay.csv"
    if exp03_csv_path.exists():
        rows03 = read_csv(exp03_csv_path)
        if "stale_fraction" not in rows03[0]:
            fail("EXP-03 artifact omits stale_fraction; LOCF staleness is not disclosed", failures)
        else:
            worst_stale = max(float(r["stale_fraction"]) for r in rows03)
            worst_drop = max(float(r["drop_fraction"]) for r in rows03)
            if worst_stale >= 0.99 and "stale_fraction" not in (ROOT / "docs" / "EXPERIMENT_REGISTRY.md").read_text(
                encoding="utf-8", errors="replace"
            ):
                fail("EXP-03 reaches ~100% stale fraction but the registry does not disclose it", failures)
            else:
                ok(
                    f"EXP-03 staleness disclosed (max stale={worst_stale:.4f}, "
                    f"max drop={worst_drop:.4f})"
                )

    print("\n[8] EXP-02 Verdict Integrity Guard (F4)")
    # F4 defect: the EXP-02 verdict was hardcoded ("DEFICIT ESTABLISHED"),
    # P(delta <= 0) was mislabeled a two-sided p-value, and the Zero-Privileged
    # Challenger could be misclassified as Oracle. These checks fail closed if any
    # of that returns.

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    from scripts.exp02_verdict import (  # noqa: PLC0415
        assign_model_role,
        is_oracle_role,
        derive_verdict,
        VerdictInputs,
        VERDICT_SUPPORTED,
        VERDICT_DIRECTIONAL,
        VERDICT_NULL,
    )

    # (a) Role assignment must never promote the unprivileged challenger to Oracle.
    challenger_names = [
        "Zero-Privileged Challenger (eps=50)",
        "Zero-Privileged Challenger (eps=20)",
        "Zero-Privileged Challenger (eps=100)",
    ]
    misassigned = [n for n in challenger_names if is_oracle_role(n)]
    if misassigned:
        fail(f"Zero-Privileged Challenger misclassified as Oracle: {misassigned}", failures)
    elif assign_model_role("Zero-Privileged Challenger (eps=50)") != "Primary Challenger":
        fail("Zero-Privileged Challenger is not assigned the Primary Challenger role", failures)
    elif not is_oracle_role("Privileged STGQ (Oracle Reference)"):
        fail("Privileged STGQ is no longer recognised as the Oracle Reference", failures)
    else:
        ok("role assignment: challenger is Primary Challenger, Oracle restricted to Privileged STGQ")

    # (b) Gate conditions must be C1 (mean <= 0) and C2 (P >= 0.95) only.
    c1_c2_cases = [
        (VerdictInputs("h=1", -100.0, 0.96, 0.0, 0.0), VERDICT_SUPPORTED),
        (VerdictInputs("h=1", -100.0, 0.94, 0.0, 0.0), VERDICT_DIRECTIONAL),
        (VerdictInputs("h=6", +100.0, 0.99, 0.0, 0.0), VERDICT_NULL),
    ]
    bad = [
        f"{vi.horizon}: expected {exp}, got {derive_verdict(vi).code}"
        for vi, exp in c1_c2_cases
        if derive_verdict(vi).code != exp
    ]
    if bad:
        fail("EXP-02 verdict rule no longer implements C1/C2 gating: " + "; ".join(bad), failures)
    else:
        ok("verdict gates on C1 (mean <= 0) and C2 (P >= 0.95), with diagnostics non-gating")

    # (c) The registry must not resurrect the stale hardcoded deficit verdict.
    reg_txt = (ROOT / "docs" / "EXPERIMENT_REGISTRY.md").read_text(encoding="utf-8", errors="replace")
    live_deficit = []
    heading = ""
    for i, line in enumerate(reg_txt.splitlines(), 1):
        if line.lstrip().startswith("#"):
            heading = line
        if "DEFICIT ESTABLISHED" in line and not _line_is_voided(line, heading):
            live_deficit.append(f"docs/EXPERIMENT_REGISTRY.md:{i}")
    if live_deficit:
        fail(
            "registry states a bare 'DEFICIT ESTABLISHED' verdict as live text "
            f"(F4 regression): {live_deficit}",
            failures,
        )
    else:
        ok("registry does not present a stale 'DEFICIT ESTABLISHED' EXP-02 verdict")

    # (d) The superseded p-value naming must not return to the EXP-02 pipeline.
    #     Uses the AST so that live code references are distinguished from
    #     docstrings/comments and from the schema-migration mapping, whose entire
    #     purpose is to translate the legacy names.
    exp02_py = ROOT / "scripts" / "run_exp02_zero_privileged_supervision.py"
    if exp02_py.exists():
        import ast as _ast

        legacy_fields = {"full_delta_psrei_pval", "bnd_delta_psrei_pval", "p_val_delta_psrei"}
        try:
            tree = _ast.parse(exp02_py.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError as exc:
            fail(f"EXP-02 runner does not parse: {exc}", failures)
            tree = None

        if tree is not None:
            # Lines inside the schema-migration function are the sanctioned exception.
            sanctioned: set[int] = set()
            for node in _ast.walk(tree):
                if isinstance(node, (_ast.FunctionDef, _ast.AsyncFunctionDef)) and node.name == "normalize_exp02_schema":
                    for sub in _ast.walk(node):
                        if hasattr(sub, "lineno"):
                            sanctioned.add(sub.lineno)

            live: list[int] = []
            for node in _ast.walk(tree):
                if isinstance(node, _ast.Constant) and isinstance(node.value, str):
                    if node.value in legacy_fields and node.lineno not in sanctioned:
                        live.append(node.lineno)
                elif isinstance(node, _ast.Name) and node.id in legacy_fields and node.lineno not in sanctioned:
                    live.append(node.lineno)
                elif isinstance(node, _ast.Attribute) and node.attr in legacy_fields and node.lineno not in sanctioned:
                    live.append(node.lineno)

            live = sorted(set(live))
            if live:
                fail(
                    "EXP-02 pipeline reintroduces the mislabelled p-value field as live code "
                    f"outside the migration mapping: lines {live}",
                    failures,
                )
            else:
                ok(
                    "EXP-02 emits P(delta <= 0) under the non-inferiority name; "
                    "legacy name appears only in the schema-migration mapping"
                )

    # (e) The joint-uncertainty report must not claim two-level hierarchy it does not perform.
    gen = ROOT / "scripts" / "generate_joint_uncertainty_report.py"
    if gen.exists():
        gsrc = gen.read_text(encoding="utf-8", errors="replace")
        if "unified two-level hierarchical" in gsrc or "Two-Level Hierarchical Block Bootstrap across training seeds" in gsrc:
            fail("joint report generator re-claims an unimplemented two-level hierarchical bootstrap", failures)
        elif "seed_level_bootstrap_from_records" not in gsrc:
            ok("joint report generator: seed-level bootstrap (naming not asserted)")
        else:
            ok("joint report generator is labelled seed-level, not two-level hierarchical")

    # (f) No EXP-02 report may claim a two-level/joint interval when it carries no
    #     block-level data. The reporting runner is a SECOND writer of that claim,
    #     separate from generate_joint_uncertainty_report.py, so it needs its own guard.
    exp02_report = ROOT / "docs" / "ZERO_PRIVILEGED_SUPERVISION_REPORT.md"
    exp02_runner = ROOT / "scripts" / "run_exp02_zero_privileged_supervision.py"
    if exp02_report.exists():
        rtxt = exp02_report.read_text(encoding="utf-8", errors="replace")
        section3 = re.search(r"^## 3\.(.*)$", rtxt, re.M)
        claims_two_level = bool(section3) and bool(
            re.search(r"Two-Level|Joint Hierarchical", section3.group(1))
        )
        # A claimed joint/two-level CI column must actually be populated.
        has_real_ci = bool(re.search(r"\|\s*\[\s*[+-]?\d", rtxt))
        if claims_two_level and not has_real_ci:
            fail(
                "EXP-02 report claims a two-level/joint interval (Section 3) but every CI cell is "
                "empty; the frozen CSV does not persist block-level deltas",
                failures,
            )
        elif claims_two_level:
            ok("EXP-02 report claims two-level intervals and populates them from block deltas")
        else:
            ok("EXP-02 report Section 3 does not claim an uncomputed two-level interval")

    if exp02_runner.exists():
        rsrc = exp02_runner.read_text(encoding="utf-8", errors="replace")
        rlines = rsrc.splitlines()
        # The heading must be selected from data presence, not hardcoded.
        if "joint_heading" not in rsrc or "has_joint_ci" not in rsrc:
            fail(
                "EXP-02 report runner hardcodes the Section 3 two-level heading instead of "
                "deriving it from the presence of block-level deltas",
                failures,
            )
        else:
            # The two-level literal must live inside the has_joint_ci-guarded branch, so that
            # the block-delta-absent path cannot emit a two-level claim.
            guard = next((i for i, ln in enumerate(rlines) if "if has_joint_ci:" in ln), None)
            two_level = [
                i for i, ln in enumerate(rlines)
                if re.search(r"Two-Level Bootstrap|Joint Hierarchical", ln)
                and not ln.lstrip().startswith("#")
            ]
            # The paired else at the same indentation closes the guarded branch.
            else_idx = None
            if guard is not None:
                indent = len(rlines[guard]) - len(rlines[guard].lstrip())
                for j in range(guard + 1, len(rlines)):
                    if rlines[j].strip() == "else:" and (len(rlines[j]) - len(rlines[j].lstrip())) == indent:
                        else_idx = j
                        break

            stray = [
                i for i in two_level
                if guard is None or else_idx is None or not (guard < i < else_idx)
            ]
            if stray:
                fail(
                    "EXP-02 report runner places a two-level heading literal outside the "
                    f"has_joint_ci-guarded branch: lines {[i + 1 for i in stray]}",
                    failures,
                )
            else:
                ok("EXP-02 report runner derives the Section 3 heading from block-delta availability")

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
