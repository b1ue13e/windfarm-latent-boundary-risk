# SCIENTIFIC_CONTRACT.md

**Status:** AUTHORITATIVE  
**Effective date:** 2026-09-21  
**Scope:** Scientific claims, experiment interpretation, agent behavior, manuscript revision, reviewer-response drafting.

> This file is the claim ceiling for the repository. If any older report, summary, README, agent note, or manuscript sentence conflicts with this contract, this contract controls until it is explicitly revised with new evidence.

## 1. Central scientific question

Under the **same arrival-time deployment information set**, when the MPPT-to-active-pitch control boundary is no longer directly observable because pitch is delayed or withheld, can already-arrived SCADA consequence signals recover useful boundary information, and does that recovered information provide **incremental decision value** for asymmetric reserve-risk allocation beyond strong direct conditional-quantile baselines?

The paper is not primarily about whether a GNN, STGNN, or MoE architecture wins a forecasting benchmark.

The causal chain under study is:

```text
control-boundary transition Z_t
        ↓
fresh pitch / state information unavailable
        ↓
available consequence signals retain some information about Z_t
        ↓
latent-state recoverability
        ↓
conditional shortfall distribution changes
        ↓
reserve decision may or may not improve
```

The three inferential stages are distinct:

```text
Observability → Recoverability → Decision Sufficiency
```

No arrow may be assumed merely because the previous stage is supported.

---

## 2. Three research questions

### Q1 — Recoverability

**Question:** When pitch is unavailable at deployment, which already-arrived consequence signals retain information about the MPPT/pitch boundary?

**Current answer:** **SUPPORTED, within the privileged-training deployment setting.**

Current mechanism evidence shows that active power is the dominant source of recoverable information:

- C2 Active-Power-Only: Brier = 0.0112, NMI = 0.461, ARI = 0.647, transition recall = 62.9%.
- C9 Active Power + Wake is essentially similar (NMI = 0.463, ARI = 0.648), so current evidence does **not** establish a necessary incremental wake mechanism.
- The full consequence suite has lower NMI than C2, so “more channels” is not itself the mechanism.

**Claim ceiling:** The defensible statement is that an **active-power consequence signature retains substantial boundary information** when pitch is withheld. Do not describe this as anchor-free discovery of a hidden physical mechanism or as proof that complex spatio-temporal structure is necessary.

### Q2 — Incremental decision value

**Question:** With the same deployment information set, frozen point forecast, and frozen shortfall target, does explicit boundary conditioning outperform strong direct conditional-quantile policies?

**Current answer:** **NO plant-wide PSREI superiority is established. Transition-localized risk hedging is supported.**

At h = 6 in the strong-baseline closure:

| Population | Wind-speed bins PSREI | Posterior PSREI | Posterior delta |
|---|---:|---:|---:|
| Full | 13,784,320 | 14,307,364 | **+523,044 kWh** |
| Transition | 4,320,310 | 4,433,014 | **+112,704 kWh** |
| Steady | 9,464,010 | 9,874,350 | **+410,340 kWh** |

In the **transition** slice, posterior conditioning changes the risk shape:

- violation: 8.36% → **7.24%**
- shortage exposure: 90,231 → **86,592 kWh**
- reserve procurement: 3,417,998 → **3,567,090 kWh**
- PSREI: 4,320,310 → **4,433,014 kWh**

Thus the supported interpretation is **localized tail-risk hedging at higher reserve/PSREI cost**, not cost optimality.

The transition-vs-steady contrast is heterogeneous (mean interaction about -296,123 kWh; bootstrap CI excludes zero in the current closure artifact), but this does not convert the posterior into a plant-wide winner.

**Claim ceiling:** Never turn improvement over an unconditioned global quantile into superiority over the strongest matched-information baseline.

### Q3 — Minimum-sufficient deployment boundary

**Question:** Which method is sufficient under each information condition?

**Current answer:** **SUPPORTED as a conditional deployment map, not as a universal model ranking.**

1. Fresh wind + fresh pitch/state information → deterministic physical rule first.
2. State remains observable but distribution/latency condition changes → non-neural state-conditional recalibration first.
3. Pitch is unavailable and transition risk matters → consequence-based latent-state representation is conditionally useful.
4. Steady-state operation, sparse farms, or cross-site zero-shot settings → prefer simple local baselines or local recalibration unless matched evidence establishes otherwise.

The target is the **minimum sufficient decision function**, not maximum model complexity.

---

## 3. Claim-status ledger

| Claim | Status | Allowed interpretation |
|---|---|---|
| Fresh telemetry: physical rule is strongest in the evaluated boundary band | VERIFIED | Conditional to the evaluated boundary band and protocol |
| Observable latency can be partly absorbed by non-neural recalibration | VERIFIED | 55.3% shortage-loss absorption under the evaluated matched-delay setting |
| Pitch-withheld consequence signals retain boundary information | VERIFIED, bounded | Dominated by active-power signature; privileged training setting |
| Active power is a major mediator of recoverability | VERIFIED | Do not upgrade to “complex STGNN discovers mechanism” |
| Posterior conditioning reduces plant-wide PSREI vs wind-speed bins | REFUTED by current closure | Must not be claimed |
| Posterior conditioning is transition-localized risk hedging | PARTIALLY SUPPORTED | Lower violation/shortage, higher reserve and PSREI |
| Regime supervision improves representation alignment | VERIFIED | NMI/ARI improvement does not imply downstream decision gain |
| Regime supervision itself improves downstream PSREI | NOT ESTABLISHED | Existing paired CIs cross zero |
| MoE routing is a key mechanism | NOT SUPPORTED | Dense/routed parity; p = 0.380 in current manuscript evidence |
| External farms prove universal generalization | NOT ESTABLISHED | Treat as heterogeneous boundary probes |
| Synthetic 60-min latency represents observed industrial latency distribution | NOT ESTABLISHED | Treat as a stress envelope |
| Pitch-never-recorded training scenario is solved | UNKNOWN | Current privileged-supervision setting does not establish it |
| End-to-end market/AC-OPF economic value is established | OUT OF SCOPE / BLOCKED | Current Level-1 PSREI does not establish this |

---

## 4. Non-negotiable interpretation rules

1. **Same-information rule**  
   Any decision-value claim must compare methods under the same arrival-time information set.

2. **Frozen-target rule**  
   Point forecast and residual-risk target must be frozen before comparing reserve policies unless the experiment is explicitly registered as a different question.

3. **Strong-baseline rule**  
   Global quantiles are not sufficient evidence for incremental value. The relevant challenge is the strongest matched-information direct conditional quantile, including wind-speed-binned policies where applicable.

4. **Slice-separation rule**  
   Always distinguish:
   - Full population
   - Steady-state
   - Transition window

5. **Representation ≠ decision rule**  
   Better NMI, ARI, AUROC, Brier, or regime recall does not by itself establish lower PSREI or better reserve decisions.

6. **Risk hedging ≠ cost optimality**  
   Lower violation/shortage at higher reserve procurement or higher PSREI must be described as a risk trade-off, not a cost win.

7. **Privileged-supervision rule**  
   Training-time pitch availability and deployment-time pitch withholding must be stated explicitly. No inference may silently extend to sites where pitch was never historically recorded.

8. **Complexity fallback rule**  
   If a simple matched baseline solves the decision problem, the complex representation must be treated as unnecessary for that regime.

9. **Negative-result preservation rule**  
   An experiment passes scientifically when it resolves the registered question, even if the result is negative. “Desired direction” is never an acceptance criterion.

10. **External-validity rule**  
    Penmanshiel/Kelmarsh/LHB are heterogeneous transfer probes. Do not pool them into a universal superiority claim without a pre-registered pooled estimand and matched controls.

---

## 5. Forbidden claim transformations

Agents and manuscript edits must not make any of the following transformations:

- “beats global quantile” → “has independent decision value”
- “high NMI/ARI” → “improves reserve decisions”
- “active-power signature works” → “complex spatio-temporal model discovers a hidden mechanism”
- “transition violation is lower” → “transition policy is cheaper”
- “MoE is implemented” → “routing is mechanistically important”
- “three external farms were tested” → “generalizes across farms”
- “synthetic 60-min stress test” → “real industrial 60-min latency is common”
- “historical pitch available in training” → “works when pitch has never been recorded”

---

## 6. Evidence authority hierarchy

For scientific interpretation, use this order:

1. **This file: `docs/SCIENTIFIC_CONTRACT.md`**
2. Raw/current experiment artifacts and registered statistical outputs
3. `docs/FIRST_PRINCIPLES_ADVERSARIAL_AUDIT_20260921.md`
4. Current manuscript and supplementary manuscript
5. Older reports such as `RESEARCH_VERDICT.md`, `DECISIVE_EXPERIMENT_REPORT.md`, earlier audit summaries

Older reports remain provenance records but are **non-authoritative for claim wording** when they conflict with this contract.

---

## 7. Conditions for changing this contract

A claim status may be upgraded only when all of the following exist:

- a pre-registered experiment entry;
- a matched information-set definition;
- a frozen target/baseline definition;
- direct artifact evidence;
- uncertainty analysis appropriate to the unit of replication;
- an adversarial falsification review;
- an updated scientific claim gate that encodes the new interpretation.

No agent may modify this contract merely to make a result “pass.”
