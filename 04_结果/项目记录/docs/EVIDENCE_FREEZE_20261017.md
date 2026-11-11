# Evidence Freeze: Strong Baseline and EXP-01

**Freeze date:** 2026-10-17
**Freeze scope:** current evidence versioning only; no retraining, no favorable-result selection, and no manuscript certification.
**Governing documents:** `docs/SCIENTIFIC_CONTRACT.md`, `docs/EXPERIMENT_REGISTRY.md`, `docs/REPLAY_CLAIM_DISPOSITION_20261015.md`, `docs/EXP01_INVALIDATION_20261015.md`, `docs/EXTERNAL_DETERMINISTIC_EVIDENCE_20261015.md`, and `.agent_state/CURRENT_RESEARCH_ASSESSMENT_20261017.md`.

## Status vocabulary

- **canonical-candidate:** the single newest result snapshot selected for current reconciliation; it is not claim-ready until the stated audit is complete.
- **canonical-limited:** the newest bounded evidence branch for a defined protocol scope; it does not certify the whole experiment or manuscript.
- **superseded:** retained historical evidence that must not be used as the current number.
- **withdrawn:** numerical or interpretive evidence that failed a declared validity condition; files remain immutable for provenance.
- **pending:** execution or audit evidence exists, but the scientific claim is not certified.

## 1. Strong-baseline closure

### Current canonical candidate: `strong_baseline_retry_import_v1`

**Status:** `canonical-candidate / pending deep numerical and statistical audit`.

**Frozen primary snapshot (h=6, WTB full test population):**

| Population | Wind-speed bins PSREI | Posterior PSREI | Delta (posterior - bins) |
|---|---:|---:|---:|
| Full | 14,979,310 kWh | 15,424,949 kWh | **+445,639 kWh** |
| Transition diagnostic | 4,572,112 kWh | 4,643,315 kWh | **+71,204 kWh** |
| Steady diagnostic | 10,407,198 kWh | 10,781,634 kWh | **+374,436 kWh** |

**Frozen joint interaction snapshot:** mean `-303,232.337659 kWh`; 95% interval `[-597,952.520900, +19,013.037805] kWh`; empirical `P(interaction <= 0) = 0.967`. The interval crosses zero. This is a current output snapshot, not a completed independent statistical certification.

**Source files and hashes:**

- `artifacts/raw_replay_20261015_v2/strong_baseline_retry_import_v1/strong_baseline_closure_summary.csv` — SHA-256 `8360D4BCF131FA09FD513D7E3EBA3E59C2F931F2463F08EAAA472A45F01FB562`
- `artifacts/raw_replay_20261015_v2/strong_baseline_retry_import_v1/strong_baseline_joint_interaction_v2.json` — SHA-256 `A75EFA63418F011D5F3963359E209842E8992C6CBAAEC6F59EC36E2CAA125970`
- Execution receipt: `artifacts/current_research_assessment_20261017/returned/artifacts/raw_replay_20261015_v2/execution/strong_baseline_retry_import_v1/record.json`
- Independent bounded review: `artifacts/current_research_assessment_20261017/independent_evidence_review.md`

**Allowed interpretation while pending:** the current snapshot does not establish posterior cost superiority over the local wind-speed baseline; the transition contrast is a risk-shape trade-off with a confidence interval crossing zero. Do not report the snapshot as a final claim until the audit closes.

### Superseded historical closure

- `artifacts/strong_baseline_closure_summary.csv` — SHA-256 `2596EB5FBD4C16AC92EDBC57A9E57F21764135864F597761D33EE4096BF59953`; old full delta `+523,044 kWh`.
- `artifacts/strong_baseline_joint_v2/strong_baseline_joint_interaction_v2.json` — SHA-256 `592B22B579370FC7F931F9D9C3691E9A2F65E4A16316ACF4DC8820F793007381`; old interaction `-297,565.353 kWh`, with a non-crossing historical interval.

These files remain immutable provenance records. They are **superseded for current numerical reporting** and must not be used as the current replay outcome, significance evidence, or manuscript headline.

## 2. EXP-01 external evidence

### Current bounded branch: `deterministic_matched_transfer_v1`

**Status:** `canonical-limited / pending full EXP-01 certification`.

This is the only current external branch allowed for bounded reporting. It uses existing complete weights, local frozen forecasts/calibration, the declared current raw windows, deterministic execution settings, and the evaluated site/horizon scope. It does not certify raw retraining, complete zero-shot transfer, or the whole paper.

**Primary h=6 snapshot:**

| Site | Delta PSREI (kWh) | 95% interval (kWh) | Interpretation |
|---|---:|---:|---|
| Kelmarsh | +6,322.697575 | [-31,417.261401, +46,732.590610] | no established cost improvement |
| Penmanshiel | +356,014.397853 | [+162,798.520598, +566,245.720865] | cost penalty in this bounded protocol |

**Source:** `artifacts/metis_external_deterministic_20261015_attempt1/audit_report.json` — SHA-256 `0455763AC369188D682C4EC54C8BA8AC0A5213692E78E012AE1B7F295AF1E3D0`.

**Allowed interpretation:** within this bounded external branch, no positive decision gain over the local wind-speed baseline is established. Do not call this universal cross-site evidence or a complete raw-data reproduction.

### Superseded / not reinstated: corrected v2

- Artifact: `external-matched-control-benchmark v2`, source `artifacts/external_matched_control_benchmark.csv`, SHA-256 `596F46E0BE8D71AB7A9965DBE4C481CC717B31C083FE288441A9CA9A39C3966E`.
- Status: **superseded and not reinstated as the current matched-decision result**. It remains historical evidence because the later raw-window reconciliation did not certify it as the current external decision branch.
- Do not quote its Penmanshiel `+5,321,915 kWh` or Kelmarsh `+435,684 kWh` as the current canonical external result without a new registered adjudication.

### Withdrawn / invalid: v4 and pitch-masked retrospective branch

- `docs/EXP01_INVALIDATION_20261015.md` formally invalidates EXP-01 v4 as matched decision evidence because saved forecasts and evaluated targets came from different physical windows.
- `artifacts/exp01-pitchmasked-retrospective-v3/v2` and its reported v4 decision deltas are **withdrawn for current interpretation**. The files remain immutable historical calculation records.
- Withdrawn values include the v4 `-315,399.62 kWh` Penmanshiel and `+352,433.95 kWh` Kelmarsh directions and intervals.

## 3. Project state after freeze

- Project phase: **analysis / evidence reconciliation**, not `concluded`.
- E01/H1: **pending adjudication**; the prior supported conclusion is not current until the external version is certified.
- Strong-baseline claim: **negative direction retained**, current numeric snapshot pending audit.
- EXP-01 claim: **bounded deterministic evidence retained**, full external decision claim pending.
- Historical negative, null, failed, superseded, and withdrawn files are preserved; no gate threshold or scientific contract ceiling is weakened.
- The current manuscript and submission package are not synchronized by this freeze and remain **not submission-ready**.

## 4. Required next action

Complete one registered adjudication that audits the current strong-baseline snapshot and the bounded deterministic EXP-01 branch against the same information set, target, population, native blocks, and uncertainty procedure. Only that adjudication may promote a pending snapshot to claim-ready or change the scientific contract.
