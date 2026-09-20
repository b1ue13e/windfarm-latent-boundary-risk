# EXPERIMENT_REGISTRY.md

**Status:** AUTHORITATIVE EXPERIMENT REGISTRY  
**Effective date:** 2026-09-21  
**Scientific contract:** `docs/SCIENTIFIC_CONTRACT.md`

This registry exists to prevent result-seeking experiment drift. An experiment is scientifically complete when it answers its registered question with auditable evidence, **not** when it produces a favorable direction.

## 1. Registration rule

Before running a new decisive experiment, create an entry with all fields below.

### Required fields

- **Experiment ID**
- **Question**
- **Contract claim tested**
- **Status**
- **Information set**
- **Training-only privileged information**
- **Frozen point forecast**
- **Frozen target**
- **Primary baseline**
- **Secondary baselines**
- **Primary estimand**
- **Primary metric**
- **Secondary metrics**
- **Population slices**
- **Unit of replication**
- **Uncertainty procedure**
- **Positive outcome interpretation**
- **Null/negative outcome interpretation**
- **Failure/invalidity conditions**
- **Artifacts to produce**
- **Decision after result**

The following fields are **immutable after first execution** unless the entry is versioned as a new experiment:

- primary estimand;
- primary baseline;
- primary metric;
- population definition;
- unit of replication;
- uncertainty procedure.

Changing any of them after viewing results requires a new Experiment ID.

---

## 2. Frozen experiment entries

### EXP-Q1-001 — Active-power minimal recoverability

**Question:** Can issue-time active-power consequence signals recover meaningful MPPT/pitch boundary information when deployment-time pitch is withheld?

**Contract claim tested:** Q1 Recoverability.

**Status:** COMPLETED / EVIDENCE FROZEN.

**Information set:** Same arrival-time pitch-withheld deployment information set used by the consequence-channel ablation.

**Training-only privileged information:** Historical regime/pitch supervision is allowed and must be disclosed.

**Frozen point forecast:** Not the primary object; decision analyses must reuse the repository frozen forecast contract.

**Frozen target:** Declared MPPT/pitch regime for recoverability; frozen residual shortfall for downstream decision metrics.

**Primary baseline:** Full consequence suite C1.

**Secondary baselines:** C3 reactive-only, C4 thermal-only, C5 direction/yaw-only, C6 wake-only, C9 active-power+wake.

**Primary estimand:** Incremental recoverability of active-power-only representation under pitch withholding.

**Primary metric:** Brier score + NMI jointly interpreted.

**Secondary metrics:** ARI, transition recall, downstream PSREI diagnostics.

**Population slices:** Full pitch-withheld test set and transition windows.

**Unit of replication:** Independent model random seed, n = 5.

**Uncertainty procedure:** Seed-level summary; downstream claims must use the corresponding registered bootstrap/paired procedure.

**Observed result:** C2 Active-Power-Only: Brier 0.0112, NMI 0.461, ARI 0.647, transition recall 62.9%.

**Positive outcome interpretation:** Active-power signature retains usable boundary information.

**Null/negative outcome interpretation:** If active power fails, the latent-boundary recoverability claim must rely on another pre-registered channel or be weakened.

**Failure/invalidity conditions:** Leakage, future Patv use, pitch present at deployment, or label construction entering test-time input.

**Artifacts:** `artifacts/channel_consequence_ablations.csv`, `docs/CONSEQUENCE_SIGNAL_MECHANISM.md`.

**Decision after result:** Treat active power as the dominant mediator. Do not claim complex spatio-temporal structure is necessary.

---

### EXP-Q1-002 — Incremental wake/context necessity

**Question:** Does wake/spatial context add material recoverability beyond active power alone?

**Contract claim tested:** Architecture/mechanism necessity.

**Status:** COMPLETED / NEGATIVE-LEANING.

**Information set:** Same as EXP-Q1-001.

**Primary baseline:** C2 Active-Power-Only.

**Primary challenger:** C9 Active Power + Wake.

**Primary estimand:** C9 minus C2 recoverability improvement.

**Primary metric:** NMI and Brier; ARI/transition recall secondary.

**Observed result:** C2 NMI 0.461/Brier 0.0112 vs C9 NMI 0.463/Brier 0.0114; current evidence does not establish a meaningful necessary wake increment.

**Positive outcome interpretation:** Only if a pre-specified uncertainty test establishes a material increment may wake context be promoted to a mechanism claim.

**Null/negative outcome interpretation:** Active power remains the minimum-sufficient recoverability explanation.

**Decision after result:** Preserve the simpler explanation.

---

### EXP-Q2-001 — Strong matched-baseline closure

**Question:** Does posterior conditioning reduce reserve-screening PSREI relative to the strongest matched-information wind-speed-conditioned quantile policy?

**Contract claim tested:** Q2 Incremental decision value.

**Status:** COMPLETED / NEGATIVE FOR PLANT-WIDE COST SUPERIORITY.

**Information set:** Same arrival-time deployment information.

**Frozen point forecast:** Canonical frozen point forecast from `docs/FIXED_TARGET_CONTRACT.md`.

**Frozen target:** Canonical shortfall residual target.

**Primary baseline:** Policy_B — Wind-Speed Binned Quantile.

**Primary challenger:** Policy_C — Posterior-Conditioned Quantile.

**Primary estimand:** `PSREI(Policy_C) - PSREI(Policy_B)`.

**Primary metric:** PSREI, kWh.

**Secondary metrics:** Reserve procurement, violation rate, shortage exposure.

**Population slices:** Full / Transition / Steady.

**Unit of replication:** Seed-level policy outputs, with the registered block-bootstrap analysis for time dependence.

**Observed result:**

| Slice | Delta PSREI C-B | Interpretation |
|---|---:|---|
| Full | +523,044 kWh | Posterior is more costly |
| Transition | +112,704 kWh | Posterior is more costly |
| Steady | +410,340 kWh | Posterior is more costly |

In transition windows, posterior violation is 7.24% vs 8.36% and shortage is 86,592 vs 90,231 kWh, while reserve procurement rises to 3,567,090 vs 3,417,998 kWh.

**Positive outcome interpretation:** A negative delta with appropriate uncertainty would support cost superiority.

**Null/negative outcome interpretation:** Preserve the negative result; only risk-shape changes may be claimed.

**Failure/invalidity conditions:** Baseline uses weaker information, target differs, point forecast differs, or result is reported only against global quantile.

**Artifacts:** `artifacts/strong_baseline_closure_summary.csv`.

**Decision after result:** Plant-wide decision superiority is not supported. Transition result is risk hedging, not cost optimality.

---

### EXP-Q2-002 — Transition-vs-steady heterogeneity

**Question:** Is the posterior-vs-wind-speed-bin gap different in transition windows than in steady operation?

**Contract claim tested:** Transition-localized risk-hedging interpretation.

**Status:** COMPLETED.

**Primary estimand:** `Delta_transition - Delta_steady`, where Delta is posterior minus wind-speed-bin PSREI.

**Primary metric:** PSREI interaction contrast.

**Uncertainty procedure:** Predefined bootstrap contrast.

**Observed result:** Mean interaction approximately -296,123 kWh; current bootstrap CI excludes zero and reported p = 0.002 in the frozen contrast artifact.

**Positive outcome interpretation:** The decision trade-off is heterogeneous across operating regimes.

**Null/negative outcome interpretation:** Do not claim transition localization.

**Decision after result:** Heterogeneity is supported; this does not imply transition cost superiority.

**Artifacts:** `artifacts/strong_baseline_bootstrap_contrasts.csv`.

---

### EXP-Q3-001 — Minimum-sufficient deployment map

**Question:** Which method is sufficient at each observability tier?

**Contract claim tested:** Q3 Minimum-sufficient deployment boundary.

**Status:** SYNTHESIS OF FROZEN EVIDENCE.

**Primary comparison:**

1. Fresh state → physical rule.
2. Observable delay/drift → state-conditional recalibration.
3. Pitch withheld + transition-sensitive risk → consequence-based representation.
4. Steady/sparse/zero-shot → simple local baseline unless matched evidence supports complexity.

**Primary metric:** No single leaderboard metric. The decision is conditional on observability and the registered decision objective.

**Positive outcome interpretation:** A method is retained only within the information regime where it adds necessary value.

**Null/negative outcome interpretation:** Fall back to the simpler method.

**Decision after result:** This is a conditional decision map, not a model ranking.

---

## 3. Open decisive experiments

### EXP-Q1-003 — No-privileged-pitch training boundary

**Question:** If pitch is never available in historical training data, can boundary-relevant structure still be recovered?

**Contract claim tested:** Current UNKNOWN: pitch-never-recorded setting.

**Status:** PROPOSED / NOT RUN.

**Information set:** No pitch at train, validation, or test; no regime label derived from pitch may enter supervision.

**Primary baseline:** Active-power-only direct classifier/quantile representation without pitch-derived labels.

**Primary challenger:** Self-supervised or weakly supervised temporal representation, if pre-registered.

**Primary estimand:** Recoverability and downstream decision delta under zero privileged pitch access.

**Primary metrics:** Brier/NMI only if a label can be constructed independently for evaluation; otherwise use an independently justified proxy plus downstream matched-baseline PSREI.

**Negative outcome interpretation:** Current privileged-supervision scope remains the maximum supported domain.

**Decision after result:** No claim upgrade unless the evaluation label itself is independent of the training information restriction.

---

### EXP-Q2-003 — External-site matched direct-quantile closure

**Question:** On each external wind farm separately, does latent-state conditioning add value beyond a matched direct conditional quantile under the same information set?

**Contract claim tested:** External validity.

**Status:** PROPOSED / BLOCKED UNTIL MATCHED PROTOCOL IS FIXED.

**Primary baseline:** Site-local matched direct quantile using the same deployment-time features.

**Primary challenger:** Site-local or transferred latent-state posterior policy.

**Population:** Each site separately; no pooled headline estimand unless separately pre-registered.

**Primary metric:** Site-specific PSREI difference.

**Secondary metrics:** Violation, shortage, reserve procurement, calibration.

**Negative outcome interpretation:** Site remains a boundary probe; do not claim generalization.

**Decision after result:** Report positive, neutral, and negative sites separately.

---

## 4. Agent execution rules

For every new experiment:

1. Register first.
2. Freeze comparator and estimand before execution.
3. Run the experiment.
4. Record all outcomes, including negative and null results.
5. Do not change the scientific contract directly from a favorable result.
6. Invoke `scientific-falsifier`.
7. Only after falsification may a contract update be proposed.
8. A contract update must be a separate, reviewable commit.

## 5. Prohibited registry behavior

- no deleting negative experiments;
- no changing the primary baseline after seeing results;
- no replacing full-population results with a favorable slice;
- no using a weaker comparator because the stronger comparator loses;
- no changing significance procedures after inspecting p-values;
- no renaming a failed hypothesis into a “new contribution” without a new registered question.
