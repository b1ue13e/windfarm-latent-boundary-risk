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

**P2 stop rule:** Do not add another graph, MoE, or hidden-state architecture merely to improve recoverability metrics. The project distinguishes three non-equivalent propositions:

```text
state recoverability -> risk-shape change -> decision value
```

Each arrow requires separate evidence. NMI, ARI, AUROC, Brier, calibration, or regime recall can support recoverability only; lower violation/shortage at higher reserve can support a risk-shape trade-off only; deployment necessity requires an independent matched-information decision result under the formal selector in `docs/MINIMUM_SUFFICIENT_DECISION_CRITERION.md`. Until E04 freezes and tests that selector, complex representations are implementation comparators or probes, not a justification for further model expansion.

### Q2 — Incremental decision value

**Question:** With the same deployment information set, frozen point forecast, and frozen shortfall target, does explicit boundary conditioning outperform strong direct conditional-quantile policies?

**Current answer:** **NO plant-wide PSREI superiority is established. A transition risk-shape trade-off is present in the latest imported snapshot, but current transition-localized heterogeneity is not claim-ready because its joint interval crosses zero and the deep audit is pending.**

The original h = 6 strong-baseline closure (historical; superseded for current numerical reporting) was:

| Population | Wind-speed bins PSREI | Posterior PSREI | Posterior delta |
|---|---:|---:|---:|
| Full | 13,784,320 | 14,307,364 | **+523,044 kWh** |
| Transition | 4,320,310 | 4,433,014 | **+112,704 kWh** |
| Steady | 9,464,010 | 9,874,350 | **+410,340 kWh** |

**2026-10-17 evidence-freeze addendum:** The values above remain immutable historical evidence and must not be reported as the current replay result. The latest imported candidate snapshot is `+445,639 kWh` (Full), `+71,204 kWh` (Transition), and `+374,436 kWh` (Steady); its joint interaction interval crosses zero. Receipt/output hashes were checked, but deep action/block/statistical audit is still pending. Until it closes, the contract-level current answer is limited to **no plant-wide PSREI superiority established**; the exact current effect size and transition heterogeneity are pending. See `docs/EVIDENCE_FREEZE_20261017.md`.

The historical transition slice showed a lower violation/shortage rate only with higher reserve procurement and higher PSREI. Those values remain historical provenance. In the latest imported candidate snapshot, the transition delta is `+71,204 kWh` and the joint transition-vs-steady interaction is `-303,232 kWh` with 95% interval `[-597,953, +19,013] kWh`, crossing zero. Thus the current allowed interpretation is a **possible transition risk-shape trade-off at higher reserve/PSREI cost**, not established heterogeneity, cost optimality, or a deployable policy gain.

**Claim ceiling:** Never turn improvement over an unconditioned global quantile into superiority over the strongest matched-information baseline.

### Q3 — Minimum-sufficient deployment boundary

**Question:** Which method is sufficient under each information condition?

**Current answer:** **SUPPORTED as a conditional deployment map, not as a universal model ranking.**

1. Fresh wind + fresh pitch/state information → deterministic physical rule first.
2. State remains observable but distribution/latency condition changes → non-neural state-conditional recalibration first.
3. Pitch is unavailable and transition risk matters → consequence-based latent-state representation is conditionally useful.
4. Steady-state operation, sparse farms, or cross-site zero-shot settings → prefer simple local baselines or local recalibration unless matched evidence establishes otherwise.

The target is the **minimum sufficient decision function**, not maximum model complexity.

### Q3 formal selection criterion

For an arrived information set $\mathcal{I}$, admissible policy class $\mathcal{M}(\mathcal{I})$, strong same-information baseline $b_{\mathcal{I}}$, fixed-target PSREI $C_P$, violation rate $V_P$, and a pre-registered complexity preorder, the conditional selector is:

\begin{equation}
\begin{aligned}
m^*(\mathcal{I},\rho,\epsilon_C,\epsilon_V)
&=\arg\min_{m\in\mathcal{M}(\mathcal{I})}\operatorname{Complexity}(m)\\
\text{s.t.}\quad
U_{1-\alpha}[C_P(m)-C_P(b_{\mathcal{I}})]&\le\epsilon_C,\\
U_{1-\alpha}[V_P(m)-V_P(b_{\mathcal{I}})]&\le\epsilon_V,\\
U_{1-\alpha}[V_P(m)]&\le v_{\max}.
\end{aligned}
\label{eq:contract-minimum-sufficient}
\end{equation}

This is a conditional, falsifiable model-selection protocol, not a universal optimality theorem. The complexity preorder and $(\alpha,\epsilon_C,\epsilon_V,v_{\max})$ were frozen before the E04 test. The E04 selector returned ``no feasible policy'' on the WTB Full population because the baseline itself exceeded the absolute violation upper bound and every complex candidate also failed at least one constraint. This is an inconclusive feasibility result, not evidence that a complex model is deployment-necessary. Independent review returned `NEEDS-WORK / NOT SCIENTIFICALLY CERTIFIED` because temporal precedence, remote output receipt/hash binding, and selector stability remain unresolved. The full specification and execution evidence are in `docs/MINIMUM_SUFFICIENT_DECISION_CRITERION.md` and artifact `e04-minimum-sufficient-selector-20261017 v3`.

---

## 3. Claim-status ledger

| Claim | Status | Allowed interpretation |
|---|---|---|
| Fresh telemetry: physical rule is strongest in the evaluated boundary band | VERIFIED | Conditional to the evaluated boundary band and protocol |
| Observable latency can be partly absorbed by non-neural recalibration | VERIFIED | Shortage-loss absorption rises monotonically with delay: 36.3% / 53.9% / 61.7% at $\tau=10/20/30$ min and 66.5% at the $\tau=60$ min contingency endpoint ($127.552 \to 42.787$ MWh, channel_mode=all, matched delay). The deprecated 55.3% token was a cross-channel_mode pitch-withholding contrast (Regime 3), not a recalibration absorption rate; it must not be used. |
| Pitch-withheld consequence signals retain boundary information | VERIFIED, bounded | Dominated by active-power signature; privileged training setting |
| Active power is a major mediator of recoverability | VERIFIED | Do not upgrade to “complex STGNN discovers mechanism” |
| Posterior conditioning reduces plant-wide PSREI vs wind-speed bins | REFUTED by current closure | Must not be claimed |
| Posterior conditioning is transition-localized risk hedging | PARTIALLY SUPPORTED | Lower violation/shortage, higher reserve and PSREI |
| Regime supervision improves representation alignment | VERIFIED | NMI/ARI improvement does not imply downstream decision gain |
| Regime supervision itself improves downstream PSREI | NOT ESTABLISHED | Existing paired CIs cross zero |
| MoE routing is a key mechanism | NOT SUPPORTED | Dense/routed parity; p = 0.380 in current manuscript evidence |
| External farms prove universal generalization | NOT ESTABLISHED | Treat as heterogeneous boundary probes |
| Synthetic 60-min latency represents observed industrial latency distribution | NOT ESTABLISHED | Treat as a stress envelope |
| Field prevalence of 10–60 min SCADA delay / pitch withholding | UNKNOWN / NOT ESTABLISHED | Evaluated strictly as synthetic stress envelope; cannot extrapolate to commercial field rates |
| Causal necessity of external spatial graph structure in EXP-01 | UNPROVEN / NOT ESTABLISHED | Parameter capacity (4,865 vs 110,012) and training asymmetries preclude causal attribution |
| Ex-ante deployability of transition policy | DIAGNOSTIC ONLY / UNPROVEN | Transition slice requires ex-post oracle knowledge of future state changes; online selector without an ex-ante detector is unsupported |
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

11. **Architectural-control non-equivalence rule**  
    The 4,865-parameter No-Graph MLP trained on validation data is an architectural probe, not a capacity-matched control for the 110,012-parameter STGQ model. The performance gap must not be causally attributed to graph structure alone.

12. **Transition-slice diagnostic boundary rule**  
    The transition window slice ($\pm 3$ steps of operating switch) is strictly a post-hoc diagnostic partition conditioned on realized future transitions. It must not be presented as an ex-ante deployable operating policy without a causal online transition detector.

13. **Synthetic telemetry envelope rule**  
    Simulated 10–60 min SCADA latencies, packet drops, and pitch withholding represent synthetic stress bounds. Their industrial frequency and commercial field prevalence are UNKNOWN and must not be asserted as factual fleet-wide reality.

14. **Literature evidence layer integrity rule (Issue F7)**  
    Historical `literature/literature_matrix.csv` (at least 18 rows with DOI-title mismatches or 404 errors) and 40 repository-synthesized `Literature Benchmark Brief` PDFs in `literature/top_journal_papers/` are DEPRECATED and strictly prohibited as scientific evidence. The authoritative literature evidence layer consists exclusively of verified peer-reviewed records in `docs/REVERSE_AUDIT_LITERATURE_MATRIX_20261012.csv` and the 4-role complete literature matrix in `research-manifest.json`. Hallucinated/fabricated literature identifiers (such as falsely attributing pure algebra paper arXiv:2405.01234 to wind power) are strictly barred.

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
- “No-Graph MLP underperforms” → “spatial graph connectivity is causally necessary”
- “post-hoc transition slice hedges risk” → “deployable online policy selector is established”
- “evaluated under pitch withholding” → “commercial wind operators routinely withhold pitch telemetry”

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
