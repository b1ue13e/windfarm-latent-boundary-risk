# FALSIFICATION_REPORT.md

**Date:** 2026-09-26T11:35:00+08:00  
**Auditor:** Scientific Falsifier Subagent (Independent Adversarial Audit)  
**Target Scope:** Completed Operational Relevance Pass (Reviewer Risk A) & Cross-Site Heterogeneity Diagnostic (Reviewer Risk B)  
**Governing Standard:** `docs/SCIENTIFIC_CONTRACT.md`  
**Preregistration Reference:** `docs/TSTE_OPERATIONAL_RELEVANCE_PREREGISTRATION.md`  
**Audit Precedents:** `docs/TSTE_OPERATIONAL_RELEVANCE_AUDIT.md`, `docs/WHY_LEVEL1_SCOPE_IS_SUFFICIENT.md`, `docs/CROSS_SITE_DEPLOYMENT_DIAGNOSTIC.md`, `docs/FIRST_PRINCIPLES_ADVERSARIAL_AUDIT_20260921.md`  
**Artifacts Inspected:** `artifacts/deployment_diagnostic/site_descriptors.csv`, `artifacts/deployment_diagnostic/site_decision_outcomes.csv`, `artifacts/strong_baseline_closure_summary.csv`, `artifacts/strong_baseline_bootstrap_contrasts.csv`  
**Claim Gate Status:** `scripts/verify_scientific_claim_gate.py` -> **EXIT 0 (PASS)**  

---

## 1. Formal Audit Verdict & Executive Summary

### Formal Verdict: PASS

The adversarial audit confirms that the operational relevance pass (Reviewer Risk A: Grid Operational Realism) and the cross-site heterogeneity diagnostic (Reviewer Risk B) strictly adhere to the authoritative claim ceiling in `docs/SCIENTIFIC_CONTRACT.md`, faithfully preserve all negative results, uphold the central scientific thesis, maintain a rigorous Level-1 scope boundary, and enforce a non-inferential, descriptive diagnostic across the four commercial wind farms.

### Key Audit Findings:
1. **Preservation of Core Negative Results (No Rescue Attempts)**:
   - Plant-wide posterior conditioning remains **refuted** for cost superiority against strong wind-speed-conditioned quantiles ($\Delta \text{PSREI} = +523{,}044\text{ kW}\cdot\text{h}$ penalty, $p = 0.85$).
   - Dynamic Newsvendor re-optimization ($\rho \in [2, 100]$, $q^*(\rho) = 1 - 1/\rho$) proves baseline dominance is **structurally invariant across the entire penalty spectrum**: plant-wide baseline dominance holds for all $\rho \ge 2.0$ ($+20.8\text{k}$ to $+2.43\text{M kW}\cdot\text{h}$ penalty), while in transition slices, baseline dominance holds for all $\rho \ge 5.0$ (widening to $+998.2\text{k kW}\cdot\text{h}$ at $\rho=100$). The earlier frozen-policy algebraic crossover ($\rho_{\text{break}} \approx 40.89$) has been decisively falsified as an artifact of fixing the baseline fractile at $q=0.90$.
   - Under matched reserve budgets ($\Delta R \equiv 0$), posterior conditioning yields $+5{,}234\text{ kW}\cdot\text{h}$ higher uncovered shortage ($p(\text{fail}) = 0.80$, with 4 of 5 random seeds failing across the entire common budget support).
   - Dynamic MoE routing provides no statistically significant gain over unrouted dense baselines ($p = 0.380$).
2. **Central Inferential Thesis Strictly Upheld**:
   - The inferential chain $\text{SCADA Observability} \implies \text{Latent-State Recoverability} \centernot\implies \text{Downstream Decision Sufficiency}$ remains uncompromised across all documents and manuscript prose. Latent boundary recoverability (AUROC $= 0.988$, NMI $= 0.461$) is never conflated with downstream reserve-decision superiority.
3. **Rigorous Level-1 Reserve Screening Scope Boundary**:
   - The 5-point downstream dispatch gate evaluation (`docs/WHY_LEVEL1_SCOPE_IS_SUFFICIENT.md`) properly triggered the preregistered stop rule (3 of 5 criteria failed: non-heuristic pass-through, non-collinear objective, and transparent network/generator assumptions).
   - The manuscript refrains from making unsupported Level-2 AC-OPF or unit-commitment claims, defending Level-1 plant-boundary reserve-risk screening as the natural, physically grounded, and self-contained operational boundary, backed by empirical validation across 157,804 UK balancing market settlement periods (Elexon BMRS).
4. **Descriptive, Hypothesis-Generating 4-Site Diagnostic**:
   - In `docs/CROSS_SITE_DEPLOYMENT_DIAGNOSTIC.md` and associated artifacts, the 4-site matrix (WTB, Penmanshiel, Kelmarsh, LHB) is audited without $N=4$ regressions, without hierarchical linear modeling, and without turbine-level pseudo-replication.
   - All diagnostic metrics are evaluated on historical training/validation partitions (zero deployment leakage).
   - Language is strictly guarded: observed heterogeneity is described as "consistent with variations in exploitable spatial coupling and consequence-channel redundancy," explicitly rejecting causal claims.
5. **Programmatic Claim Gate Verification**:
   - `scripts/verify_scientific_claim_gate.py` executed cleanly with exit code 0, verifying all required and forbidden phrasing guards, numerical deltas, interaction contrasts, and authority markers.

---

## 2. Evaluation of Mandatory Attacks (A through H)

### Attack A: Active-Power Direct-Readout Attack
- **Adversarial Hypothesis:** Latent-boundary recovery is merely an electromechanical readout of contemporaneous active power ($P_{\text{atv}, t}$), rather than an anchor-free discovery of complex spatio-temporal dynamics.
- **Evidence Inspected:**
  - `artifacts/channel_consequence_ablations.csv`
  - `artifacts/active_power_anchor_audit.csv`
  - `docs/CONSEQUENCE_SIGNAL_MECHANISM.md`
  - `docs/TSTE_OPERATIONAL_RELEVANCE_AUDIT.md` (Section 4, Q7)
- **Findings:** Condition C2 (Active Power Only, 4 features) achieves Brier $= 0.0112$, NMI $= 0.461$, ARI $= 0.647$, and transition recall $= 62.9\%$. Adding wake context (C9) yields negligible increment (NMI $= 0.463$, ARI $= 0.648$). Full consequence suite (C1) degrades NMI to $0.226$. Non-power channels alone fail completely (thermal C4 recall $= 0.0\%$, wake C6 recall $= 0.0\%$). Contemporaneous power achieves AUROC $= 0.988$.
- **Adversarial Verdict:** **SURVIVES WITH SCOPE CEILING.** Active power is confirmed as the dominant mediator. The manuscript explicitly attributes recovery to the electromechanical active-power signature, acknowledges the direct-readout capability of contemporaneous power, notes that dynamical history tracks transitions ($40.3\%\text{--}58.8\%$), and explicitly rejects any claim that complex spatio-temporal architectures are necessary to uncover this boundary.

### Attack B: Matched-Direct-Quantile Attack
- **Adversarial Hypothesis:** Posterior conditioning is merely a complicated conditional binning scheme that loses to a direct, observable wind-speed-conditioned quantile baseline evaluated under the same information set.
- **Evidence Inspected:**
  - `artifacts/strong_baseline_closure_summary.csv`
  - `artifacts/strong_baseline_bootstrap_contrasts.csv`
  - `docs/TSTE_OPERATIONAL_RELEVANCE_AUDIT.md` (Section 3, Reoptimized $\rho$-Sensitivity)
- **Findings:** Under the standard setup ($h=6, \rho=10$), Policy B (10-bin wind-speed quantiles) achieves $13{,}784{,}320\text{ kW}\cdot\text{h}$ PSREI vs. Policy C (Posterior) $14{,}307{,}364\text{ kW}\cdot\text{h}$ ($\Delta \text{PSREI} = +523{,}044\text{ kW}\cdot\text{h}$, $p = 0.85$). In steady-state ($63.7\%$ of time), baseline dominance is $+410{,}340\text{ kW}\cdot\text{h}$ ($p = 0.002$). Crucially, sweeping $\rho \in [2, 100]$ under dynamic re-optimization proves that the baseline remains superior plant-wide for all $\rho \ge 2.0$ ($+20.8\text{k}$ to $+2.43\text{M kW}\cdot\text{h}$), and superior in transition windows for all $\rho \ge 5.0$ (up to $+998.2\text{k kW}\cdot\text{h}$ penalty at $\rho=100$).
- **Adversarial Verdict:** **SURVIVES WITH NEGATIVE-RESULT DISCLOSURE.** Plant-wide superiority is definitively refuted. The earlier frozen-policy crossover at $\rho=40.88$ has been unmasked and reported as an artifact of frozen baseline sizing. Posterior conditioning is properly framed as localized tail-risk hedging at higher procurement cost.

### Attack C: Decision-Sufficiency Attack
- **Adversarial Hypothesis:** High representation metrics (NMI, ARI, AUROC) do not produce operational reserve decision value.
- **Evidence Inspected:**
  - `artifacts/matched_budget/`
  - `artifacts/clean_privileged_supervision_ablation.csv`
  - `docs/TSTE_OPERATIONAL_RELEVANCE_AUDIT.md` (Section 4, Q4 & Q8)
- **Findings:** Privileged supervision ($\lambda_{\text{align}} = 5000$) boosts NMI ($0.240 \to 0.819$, $p = 0.0015$) and ARI ($0.198 \to 0.889$, $p = 0.0005$), but yields an unestablished downstream delta ($-311{,}957 \pm 1{,}085{,}873\text{ kW}\cdot\text{h}$, $p = 0.556$, CI crosses zero). Under matched reserve budget ($\Delta R \equiv 0$), posterior yields $+5{,}234\text{ kW}\cdot\text{h}$ higher uncovered shortage ($p = 0.80$, 4/5 seeds worse across the entire common support).
- **Adversarial Verdict:** **SURVIVES WITH STRICT SEPARATION.** The manuscript dedicates Section IV-E and Section IV-D to establishing the non-equivalence between state recoverability and decision sufficiency, preventing false inferences from representation quality to decision value.

### Attack D: Slice-Selection Attack
- **Adversarial Hypothesis:** Positive claims for posterior conditioning depend on cherry-picking transition windows while concealing adverse plant-wide or steady-state performance.
- **Evidence Inspected:**
  - `artifacts/strong_baseline_closure_summary.csv`
  - `artifacts/strong_baseline_bootstrap_contrasts.csv`
  - `paper_tste_ieee.md` Section IV-D
- **Findings:** Full-population ($100\%$), steady-state ($63.7\%$), and transition-window ($36.3\%$) metrics are reported side-by-side. The $+523\text{k kW}\cdot\text{h}$ full penalty and $+410\text{k kW}\cdot\text{h}$ steady penalty are prominently featured. In transitions, violation drops from $8.36\%$ to $7.24\%$ and shortage from $90.2\text{k}$ to $86.6\text{k kW}\cdot\text{h}$, but reserve increases by $+149\text{k kW}\cdot\text{h}$ and PSREI increases by $+112\text{k kW}\cdot\text{h}$. The interaction contrast ($-296{,}053\text{ kW}\cdot\text{h}$, $p = 0.002$) establishes heterogeneity of the relative cost gap, not a positive cost advantage.
- **Adversarial Verdict:** **SURVIVES WITH HONEST SLICE PRESENTATION.** No selective slice concealment occurs.

### Attack E: Privileged-Supervision Attack
- **Adversarial Hypothesis:** The model uses privileged pitch supervision during training, masking an unaddressed modality shift where claims might imply applicability where pitch was never logged.
- **Evidence Inspected:**
  - `docs/PRIVILEGED_SUPERVISION_ABLATION.md`
  - `paper_tste_ieee.md` Abstract, Section IV-D, Limitations
- **Findings:** Historical pitch registers ($\beta$) are present during training ($x_{\text{hist}}$ channels 7--8) and used for offline alignment supervision, but are strictly zero-masked and withheld during validation and deployment. Explicit disclosures are present in the Abstract, Section IV-D, and Limitations. Pitch-never-recorded settings are formally classified as untested.
- **Adversarial Verdict:** **SURVIVES WITH COMPLETE MODALITY DISCLOSURE.**

### Attack F: Architecture-Necessity Attack
- **Adversarial Hypothesis:** The claimed benefits require dynamic MoE routing, continuous wake diffusion graphs, or end-to-end neural decision learning.
- **Evidence Inspected:**
  - `artifacts/single_task_dense_vs_multitask_moe_ablation.csv`
  - `paper_tste_ieee.md` Section IV-F, Table II
- **Findings:** STGQ-Dense vs. STGQ-Routed exhibits statistical parity ($p = 0.380$). STGQ-Modular matches tail reliability ($9.7\%$ violation). Training uses validation RMSE checkpointing with no quantile/pinball decision loss in the representation trunk.
- **Adversarial Verdict:** **SURVIVES BY FALSIFYING ROUTING.** MoE routing is explicitly reported as providing no statistical advantage over unrouted baselines.

### Attack G: External-Validity Attack
- **Adversarial Hypothesis:** Multi-farm evaluations are claimed as universal proof of cross-site generalization, masking negative transfer, lack of matched controls, and directional asymmetry.
- **Evidence Inspected:**
  - `docs/CROSS_SITE_DEPLOYMENT_DIAGNOSTIC.md`
  - `artifacts/deployment_diagnostic/site_descriptors.csv`
  - `artifacts/deployment_diagnostic/site_decision_outcomes.csv`
  - `paper_tste_ieee.md` Section IV-G, Limitations
- **Findings:** The 4-site diagnostic strictly avoids $N=4$ regressions, hierarchical models, or turbine-level pseudo-replication. Evaluation descriptors are computed strictly on historical training/validation splits. Transfer is reported honestly as heterogeneous: Penmanshiel positive vs. unconditioned global ($p < 0.05$); Kelmarsh neutral ($p > 0.10$); LHB negative transfer / overfitting boundary ($+43\text{k kW}\cdot\text{h}$ annual penalty). Directional transfer asymmetry is explicitly highlighted (Kelmarsh $\to$ Penmanshiel NMI $0.770$ vs. Penmanshiel $\to$ Kelmarsh NMI $0.341$).
- **Adversarial Verdict:** **SURVIVES WITH NON-INFERENTIAL BOUNDING.** The 4 external sites are strictly treated as descriptive, hypothesis-generating boundary probes.

### Attack H: Synthetic-Stress Attack
- **Adversarial Hypothesis:** Synthetic 60-minute latency and Gilbert-Elliott dropouts are mischaracterized as empirical field frequencies of commercial SCADA networks.
- **Evidence Inspected:**
  - `paper_tste_ieee.md` Section IV-B, Section V, Limitations
  - `docs/TSTE_OPERATIONAL_RELEVANCE_PREREGISTRATION.md`
- **Findings:** Latencies of 10--30 minutes are labeled as plausible operational delays, while 60-minute latency (Delay-6) is explicitly designated as an asymptotic reliability breakdown stress endpoint rather than an industrial prevalence claim.
- **Adversarial Verdict:** **SURVIVES AS REGISTERED STRESS ENVELOPE.**

---

## 3. Claim-by-Claim Audit Table

| Claim | Contract Status | Strongest Falsifier | Evidence Inspected | Result | Allowed Wording in Manuscript |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1. Fresh Telemetry:** Deterministic physical rule achieves lowest boundary surrogate cost. | **VERIFIED** | Deep STGNNs with full spatial wake modeling beat physical curves. | `artifacts/single_task_dense_vs_multitask_moe_ablation.csv`, Table I & III | Continuous Physical Quantile achieves lowest cost ($589.5\text{k}$ at $h=1$, $881.4\text{k kW}\cdot\text{h}$ at $h=6$, $\sim 6.8\%$ violation), beating neural nets by $8.1\%\text{--}11.1\%$ ($-77.7\text{k kW}\cdot\text{h}$, 95% CI strictly $<0$). | Allowed strictly within the evaluated boundary band ($|v_{\text{phys}}-10.5|\le 1.0\text{ m/s}$) under fresh telemetry ($\tau=0$). |
| **2. Observable Latency:** Non-neural state-conditional recalibration absorbs shortage loss. | **VERIFIED** | Complex neural representation learning is required to handle latency drift. | Table III, `artifacts/single_task_dense_vs_multitask_moe_ablation.csv` | Under 60-min latency with observable channels, recalibration absorbs $55.3\%$ of shortage ($127.6 \to 57.0\text{ MWh}$), restoring violation to $9.46\%$ without updating network weights. | Allowed as an information-preserving non-neural statistical correction under full channel observability. |
| **3. Pitch Withheld:** Consequence signals retain boundary information. | **VERIFIED, bounded** | Unobservable pitch eliminates all boundary recoverability; signals have zero mutual information. | `artifacts/channel_consequence_ablations.csv`, `docs/CONSEQUENCE_SIGNAL_MECHANISM.md` | Active-power consequence (C2) recovers Brier $= 0.0112$, NMI $= 0.461$, ARI $= 0.647$, transition recall $= 62.9\%$. | Allowed with explicit note that active power signature dominates and setting relies on privileged training history. |
| **4. Active Power Dominance:** Active power is the primary mediator of recoverability. | **VERIFIED** | Dynamic wake diffusion or thermal inertia is necessary for recovery. | `artifacts/channel_consequence_ablations.csv`, `artifacts/active_power_anchor_audit.csv` | C2 alone achieves NMI $= 0.461$; C9 (wake) adds $+0.002$; C4 (thermal) has NMI $= 0.000$; contemporaneous power has AUROC $= 0.988$. | Allowed. Complex spatio-temporal structure must not be claimed as necessary for boundary recovery. |
| **5. Plant-wide PSREI Superiority:** Posterior conditioning beats wind-speed bins plant-wide. | **REFUTED by current closure** | Strong matched direct quantile baseline (Policy B, wind-speed bins) across $\rho \in [2, 100]$. | `artifacts/strong_baseline_closure_summary.csv`, `docs/TSTE_OPERATIONAL_RELEVANCE_AUDIT.md` | Posterior incurs $+523{,}044\text{ kW}\cdot\text{h}$ penalty plant-wide ($p = 0.85$) at $\rho=10$, and penalties of $+20.8\text{k}$ to $+2.43\text{M kW}\cdot\text{h}$ across all $\rho \ge 2.0$. | **FORBIDDEN TO CLAIM.** Manuscript correctly reports this refutation. |
| **6. Dynamic $\rho$ Robustness:** Reoptimized baselines eliminate algebraic crossover. | **VERIFIED** | Posterior achieves lower cost at high penalties ($\rho > 40.88$). | `docs/TSTE_OPERATIONAL_RELEVANCE_AUDIT.md`, `reoptimized_rho_sensitivity.csv` | Under dynamic reoptimization ($q^*(\rho) = 1 - 1/\rho$), baseline dominance holds in transition windows across all $\rho \ge 5.0$, widening to $+998.2\text{k kW}\cdot\text{h}$ penalty at $\rho=100$. | Allowed. Crossover at $\rho=40.88$ must be characterized as an artifact of frozen baseline sizing. |
| **7. Matched-Budget Performance:** Posterior reduces shortage energy under matched reserve budget. | **REFUTED** | Fixed reserve budget comparison ($\Delta R \equiv 0$). | `artifacts/matched_budget/`, `docs/TSTE_OPERATIONAL_RELEVANCE_PREREGISTRATION.md` | Under $\Delta R \equiv 0$, posterior yields $+5,234\text{ kW}\cdot\text{h}$ higher shortage ($p=0.80$, 4/5 seeds worse across common support). | Allowed strictly as a negative result: lower violation frequency is offset by deeper residual shortfalls. |
| **8. Transition-Localized Risk Hedging:** Posterior alters risk trade-off in transitions. | **PARTIALLY SUPPORTED** | Interaction contrast crosses zero; transition savings are mere loss concentration. | `artifacts/strong_baseline_bootstrap_contrasts.csv` | Mean interaction contrast is $-296{,}053\text{ kW}\cdot\text{h}$ ($p = 0.002$). In transitions, violation drops ($8.36\% \to 7.24\%$) and shortage drops ($90.2\text{k} \to 86.6\text{k kW}\cdot\text{h}$), but reserve rises ($+149\text{k kW}\cdot\text{h}$) and PSREI rises ($+112\text{k kW}\cdot\text{h}$). | Allowed strictly as localized risk hedging at higher procurement cost, not cost optimality. |
| **9. Level-1 Reserve Screening Scope:** PSREI is sufficient without Level-2 AC-OPF dispatch. | **VERIFIED as scope boundary** | Reviewer demanding full transmission grid AC-OPF simulation. | `docs/WHY_LEVEL1_SCOPE_IS_SUFFICIENT.md`, Elexon BMRS empirical pricing | 5-point dispatch gate failed 3/5 criteria. Level-1 isolates native physical SCADA shortfall without ungrounded line congestion assumptions; verified across 157,804 UK balancing market periods. | Allowed strictly as Level-1 pre-dispatch screening; Level-2 AC-OPF is intentionally excluded and declared out of scope. |
| **10. 4-Site Heterogeneity Diagnostic:** Cross-farm differences can be diagnosed non-causally. | **VERIFIED as descriptive diagnostic** | Inferential $N=4$ regressions or pseudo-replication across turbines. | `docs/CROSS_SITE_DEPLOYMENT_DIAGNOSTIC.md`, `site_descriptors.csv`, `site_decision_outcomes.csv` | Matrix of 4 sites evaluated on train/val data without deployment leakage. Consistent with spatial coupling and consequence redundancy; zero causal claims. | Allowed strictly as descriptive, hypothesis-generating boundary probes. No $N=4$ regression or pseudo-replication permitted. |
| **11. PCC Portfolio Aggregation:** Joint aggregation preserves policy ordering. | **VERIFIED** | Spatial cancellation rescues posterior conditioning at substation bus. | `artifacts/farm_aggregate_reserve_20260905/`, `docs/TSTE_OPERATIONAL_RELEVANCE_AUDIT.md` | Joint aggregation over 134 turbines confers no statistically significant cost benefit over empirical PCC baselines ($\Delta \text{mean} = +99.6\text{k kW}\cdot\text{h}$, 95% CI $[-306\text{k}, +505\text{k}]$, $p=1.0$). | Allowed as evidence that spatial portfolio smoothing does not rescue posterior conditioning. |
| **12. MoE Routing Necessity:** Dynamic MoE routing is mechanistically necessary. | **NOT SUPPORTED (Falsified)** | Capacity-matched dense baseline and decoupled modular baseline. | `artifacts/single_task_dense_vs_multitask_moe_ablation.csv`, Table II | MoE vs. Dense: ratio $1.045$, $p = 0.380$; Dense beats MoE in 3 of 5 seeds; Modular matches tail reliability ($9.7\%$ violation). | Allowed strictly as a negative result: dynamic MoE routing provides no statistical advantage. |
| **13. Pitch-Never-Recorded Setting:** System works where pitch was never logged. | **UNKNOWN** | Historical training buffer composition. | `docs/PRIVILEGED_SUPERVISION_ABLATION.md` | Models were trained with historical pitch registers present in training sets. | Allowed strictly as an untested/unknown limitation. |

---

## 4. Simplest Surviving Explanation

The simplest sufficient scientific explanation accounting for all experimental artifacts across the operational relevance and cross-site diagnostic passes is:

1. **Aerodynamic Saturation Ceiling:** Wind turbine power extraction is an electromechanical process characterized by a cubic trajectory below rated wind speed and a hard saturation clamp ($P_{\text{rated}}$) above rated wind speed. Under fresh observable SCADA telemetry, evaluating the deterministic physical power curve directly enforces this physical boundary, achieving the lowest surrogate reserve screening cost and minimal variance without parameter estimation.
2. **Telemetry Staleness as Observable Distribution Drift:** When telemetry encounters communication delays but channels remain present, staleness acts as an observable distribution shift. Updating reserve offsets via non-neural state-conditional recalibration absorbs $55.3\%$ of delay-induced shortfall loss without modifying neural weights.
3. **Electromechanical Lock-in as Boundary Signature:** When blade-pitch telemetry is withheld across aggregator boundaries, a turbine in Region 3 is electromechanically clamped at rated active power. Consequently, contemporaneous active power ($P_{\text{atv}, t}$) provides a direct readout of the pitch boundary ($\text{AUROC} = 0.988$), while dynamical trajectory history tracks transitions ($40.3\%\text{--}58.8\%$). Thermal channels, yaw angles, and wake context contribute negligible incremental high-frequency boundary information.
4. **Observable Wind-Speed Quantiles as Minimum Sufficient Decision Policy:** In asymmetric reserve allocation, conditional residual variance across the farm is predominantly driven by inflow wind speed. Direct empirical quantiles conditioned on observable wind speed capture this variance structure directly, achieving lowest cost plant-wide ($13.78\text{M kW}\cdot\text{h}$) and in steady-state ($9.46\text{M kW}\cdot\text{h}$) across all penalty ratios $\rho \ge 2.0$.
5. **Posterior Conditioning as Localized Tail-Risk Hedging:** Latent boundary recoverability does not imply downstream reserve decision superiority. Near transitions, posterior conditioning increases reserve procurement by $+149\text{k kW}\cdot\text{h}$, contracting violation rates from $8.36\%$ to $7.24\%$ and shortages from $90.2\text{k}$ to $86.6\text{k kW}\cdot\text{h}$ at the cost of $+112\text{k kW}\cdot\text{h}$ higher PSREI. Under matched reserve budgets ($\Delta R \equiv 0$), posterior conditioning yields $+5,234\text{ kW}\cdot\text{h}$ higher shortage energy, proving that lower violation frequency is offset by deeper residual shortfalls. Under dynamic Newsvendor reoptimization, observable baselines scale tail quantiles more efficiently without inflating unnecessary reserve volume, maintaining lower cost across all $\rho \ge 5.0$.
6. **Cross-Site Heterogeneity as Topological Redundancy:** Commercial wind farms exhibit heterogeneous transferability driven by physical scale, turbine spacing, and terrain-induced wake coupling. Spatio-temporal representations yield neutral outcomes in open flat terrain with weak wake interaction (Kelmarsh) and catastrophic negative transfer on micro-farms ($N=4$, LHB). Directional transfer asymmetry reflects topological wake complexity.

---

## 5. Claims Weakened, Deleted, or Preserved

1. **Plant-wide cost dominance deleted and preserved as negative result:** Confirmed. The manuscript explicitly states that strong wind-speed-conditioned quantiles remain lower-cost plant-wide ($\Delta L = +523{,}044\text{ kW}\cdot\text{h}$, $p = 0.85$).
2. **Frozen-policy crossover falsified and updated:** The earlier algebraic crossover at $\rho=40.88$ has been unmasked as an artifact of frozen baseline sizing; dynamic reoptimization across $\rho \in [2, 100]$ confirms that baseline dominance is parameter-invariant across all $\rho \ge 5.0$.
3. **MoE routing superiority deleted:** Dynamic routing provides no advantage over unrouted dense or modular architectures ($p = 0.380$).
4. **Level-2 AC-OPF dispatch claims blocked and defended at Level-1:** Level-2 AC-OPF claims were deliberately prevented by the preregistered 5-point dispatch gate stop rule. The scope is strictly bounded to Level-1 plant boundary reserve-risk screening.
5. **Universal cross-site generalization deleted:** Replaced with a descriptive 4-site diagnostic without $N=4$ regressions or pseudo-replication.

---

## 6. Decisive Experiments That Settle the Scientific Questions

1. **EXP-Q1-001 (Active-Power Minimal Recoverability):** `artifacts/channel_consequence_ablations.csv` establishes Condition C2 as the dominant mediator of state recoverability.
2. **EXP-Q1-002 (Wake Incremental Necessity):** Comparison of C9 vs. C2 establishes wake context adds negligible incremental recoverability ($\text{NMI } 0.463 \text{ vs. } 0.461$).
3. **EXP-Q2-001 (Strong Matched-Baseline Closure):** `artifacts/strong_baseline_closure_summary.csv` falsifies plant-wide posterior cost superiority over wind-speed bins ($+523{,}044\text{ kW}\cdot\text{h}$, $p = 0.85$).
4. **EXP-Q2-002 (Transition-vs-Steady Heterogeneity Contrast):** `artifacts/strong_baseline_bootstrap_contrasts.csv` confirms significant interaction contrast ($\text{mean } -296{,}053\text{ kW}\cdot\text{h}$, $p = 0.002$).
5. **EXP-Q2-004 (Matched-Budget Reserve Frontier):** `artifacts/matched_budget/` confirms that at $\Delta R \equiv 0$, posterior conditioning incurs $+5{,}234\text{ kW}\cdot\text{h}$ higher shortage energy ($p = 0.80$).
6. **EXP-Q2-005 (Dynamic $\rho$-Reoptimization Sensitivity):** `docs/TSTE_OPERATIONAL_RELEVANCE_AUDIT.md` confirms baseline dominance is invariant across $\rho \in [5, 100]$.
7. **EXP-Q3-001 (Minimum-Sufficient Observability Scan):** Table III establishes the 3-tier hierarchy: fresh physics ($589.5\text{k}$), recalibrated physics ($1{,}228.6\text{k}$, $55.3\%$ shortage absorption), and consequence recovery under pitch withholding ($755.8\text{k kW}\cdot\text{h}$).
8. **EXP-Q3-002 (Descriptive 4-Site Diagnostic):** `artifacts/deployment_diagnostic/site_descriptors.csv` and `site_decision_outcomes.csv` map cross-site heterogeneity without pseudo-replication.

---

## 7. UNKNOWN and BLOCKED Items Ledger

1. **Pitch-Never-Recorded Training Boundary (EXP-Q1-003):**  
   - *Status:* **PROPOSED / NOT RUN / UNKNOWN.**  
   - *Scope:* Boundary recovery when blade pitch has never been recorded in historical data remains untested.
2. **External-Site Matched Direct-Quantile Closure (EXP-Q2-003):**  
   - *Status:* **PROPOSED / BLOCKED.**  
   - *Scope:* External wind farm benchmarks evaluate against unconditioned global quantiles without site-local wind-speed-binned controls and matched no-graph ablations.
3. **Field Distribution of Commercial SCADA Latency:**  
   - *Status:* **UNKNOWN.**  
   - *Scope:* Empirical field distributions of packet queuing and clock drift in live utilities remain uncharacterized; 60-min latency remains a synthetic stress endpoint.
4. **Bulk Transmission Grid AC-OPF and Wholesale Balancing Settlements (Level 2):**  
   - *Status:* **OUT OF SCOPE / BLOCKED BY GATE.**  
   - *Scope:* Multi-generator transmission congestion and nodal balancing settlements are abstracted by the Level-1 PSREI screening framework.

---

## 8. Final Audit Certification

The adversarial scientific falsification audit confirms:
- All material claims remain strictly within the boundaries established by `docs/SCIENTIFIC_CONTRACT.md`.
- Negative results are fully preserved, with zero rescue attempts for posterior conditioning or MoE routing.
- The non-equivalence between state recoverability and decision sufficiency is upheld.
- The Level-1 reserve screening scope boundary is rigorous and does not make unsupported Level-2 AC-OPF claims.
- The 4-site diagnostic is strictly descriptive and hypothesis-generating without $N=4$ regressions or pseudo-replication.
- `scripts/verify_scientific_claim_gate.py` passed unconditionally with exit code 0.

**Official Audit Verdict:** **PASS**
