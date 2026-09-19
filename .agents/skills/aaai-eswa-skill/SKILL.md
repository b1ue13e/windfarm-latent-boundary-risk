---
name: aaai-eswa-skill
description: Use when working on the E:\论文2 financial stress paper's AAAI versus ESWA venue strategy, including AAAI稳中 gate design, ESWA保底 framing, reviewer-risk audits, claim boundary checks, negative-control planning, cross-market validation, mechanism evidence, reproducibility closure, or rewriting the manuscript from an ESWA application paper into an AAAI method paper.
---

# AAAI / ESWA Skill

Use this skill to keep the financial stress manuscript aligned with two possible venue tracks:

- **ESWA track:** a bounded analyst-facing, expert-system style paper about auditable HGB-anchored rank correction for CSI300 relative-downside review queues.
- **AAAI track:** a general AI method paper about risk-controlled auxiliary representation admission for non-stationary low-label review ranking.

Default to one track at a time. If the user asks whether the paper can reach AAAI, evaluate AAAI gates first, then state the ESWA fallback.

## Core Rule

Do not upgrade the claim faster than the evidence.

- If source controls are incomplete, do not claim source-domain transfer.
- If external markets fail, do not claim broad cross-market generalization.
- If mechanism perturbations are smoke-level or mixed, do not claim temporal-stress mechanism.
- If only CSI300 q=0.45 works, describe relative-review ranking, not tail-risk warning.

## Project Reference

For this workspace, first read the root guide when available:

`E:\论文2\AAAI_ESWA_VENUE_GATE.md`

Use it as the canonical gate document. If the guide and the manuscript conflict, treat the guide as the stricter reviewer-risk policy unless the user explicitly asks to relax it.

## Diagnostic Workflow

1. Identify the requested track:
   - ESWA / journal / applied expert system.
   - AAAI weak submission.
   - AAAI稳中.
   - General venue-fit or reviewer-risk audit.

2. Inspect current evidence before advising:
   - Main manuscript: `01_manuscript/.../main.tex`.
   - Claim decision and review-risk reports under `04_reports`.
   - L0-L3 status under `03_results_and_runs/fatal_experiments_20260602`.
   - Reproducibility package under `07_reproducibility_package`.

3. Classify the current claim level:
   - **L0:** auditable CSI300 rank-fusion workflow.
   - **L1:** source-pretrained auxiliary signal survives negative controls.
   - **L2:** market-conditioned transfer or correct abstention across markets.
   - **L3:** candidate mechanism supported by perturbation/intervention evidence.
   - **L4:** broad transferable mechanism across multiple markets and tasks.

4. Give a gate verdict:
   - `ESWA-ready`, `ESWA-needs-fixes`, `AAAI-weak`, `AAAI-not-yet`, or `AAAI稳中-candidate`.
   - State the smallest blocking gate, not only a long wishlist.

## ESWA Gate

ESWA is plausible when the paper is framed as a bounded applied AI / expert-system workflow.

Require:

- Clear CSI300 relative-downside review-queue task.
- HGB remains the target-domain anchor.
- External representation enters only as low-capacity probe plus rank-level correction.
- Random probe, threshold, fusion sensitivity, rank movement, and external non-confirmation are visible.
- q=0.45 is described as relative review priority, not tail risk.
- Candidate-freezing and validation choices are explicit.
- References and reproducibility materials are clean enough for review.

Recommended ESWA claim:

> The paper contributes an auditable HGB-anchored rank-correction workflow for CSI300 relative-downside review queues, with source-probe evidence treated as bounded and externally non-confirmed.

## AAAI Weak Gate

AAAI weak submission requires a method contribution beyond the ESWA workflow.

Require:

- A named algorithm for auxiliary representation admission.
- Validation-only admission gate.
- No-harm abstention or down-weighting rule.
- Formal audit log for rank movement and admission decisions.
- Completed L1 negative controls or a claim downgrade to generic auxiliary admission.
- Cross-market results reported as improvement or correct rejection, not tuned-away failure.
- Ranking baselines beyond standard classifiers.

If the method is still fixed `0.7/0.3` fusion without gate or abstention, say it is not yet AAAI-level.

## AAAI稳中 Gate

AAAI稳中 requires L1 + L2 + L3 + reproducibility closure.

### L1 Source Validity

Require formal reruns for:

- label-shuffle source encoder.
- time-shifted source encoder.
- shuffled-source control.
- unrelated-source control.
- phase-randomized source control.
- matched random encoder.

Pass only if source fusion beats HGB and shows stable advantage over controls across seeds/protocols. If controls are close, downgrade to interface/gate contribution.

### L2 Market-Conditioned Transfer

Require locked transfer and market-adapted validation to remain separate.

AAAI-stable outcomes:

- External market improves under locked or validation-only adapted test-year protocol, or
- Gate rejects/down-weights weak external auxiliary signals and avoids negative transfer.

Never describe market-adapted validation as locked transfer.

### L3 Mechanism Evidence

Require formal perturbation evidence across seeds:

- At least two perturbation families, such as volatility scale, persistence/autocorrelation, frequency-band masking, drawdown-path counterfactual, or liquidity/trade-value stress.
- Directional response must be pre-registered.
- Response pattern should help explain CSI300 success versus CSI500/SSE50 failure or abstention.

Smoke tests or one-seed mixed results do not pass L3.

### Reproducibility

Require split definitions, configs, seeds, raw predictions, table/figure source data, scripts, checksums, environment files, and availability statements. If market data cannot be redistributed, provide placement instructions and reproducible derived artifacts where legally allowed.

## Writing Rules

Use these phrases for AAAI method framing:

- risk-controlled auxiliary representation admission.
- non-stationary low-label review ranking.
- validation-only admission gate.
- no-harm abstention / down-weighting.
- HGB or target-domain anchor.
- rank-level correction with audit trail.

Avoid these phrases unless all gates pass:

- general transfer to finance.
- broad transferable mechanism.
- tail-risk prediction.
- crash warning.
- source pretraining proves financial semantics.
- external market confirmation.

## Output Format

When asked for an assessment, answer in this structure:

1. **Verdict:** current venue level and whether AAAI稳中 is reachable.
2. **Blocking Gate:** the first failed AAAI gate.
3. **Required Work:** concrete experiments/writing changes, ordered by dependency.
4. **Allowed Claim:** what can be honestly written now.
5. **Downgrade Rule:** when to fall back to ESWA/KBS or rank-fusion-only framing.

Keep the answer direct. Do not turn a summary into paper analysis; inspect claims, evidence, controls, failure cases, and reviewer objections.
