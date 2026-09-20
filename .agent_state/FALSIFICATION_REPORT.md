# FALSIFICATION_REPORT.md

**Date:** 2026-09-21T05:38:00+08:00  
**Auditor:** Scientific Falsifier Subagent (Independent Adversarial Audit)  
**Target Manuscript:** `paper_tste_ieee.md`  
**Authoritative Standard:** `docs/SCIENTIFIC_CONTRACT.md`  
**Registry Reference:** `docs/EXPERIMENT_REGISTRY.md`  
**Audit Precedent:** `docs/FIRST_PRINCIPLES_ADVERSARIAL_AUDIT_20260921.md`  
**Claim Gate Status:** `scripts/verify_scientific_claim_gate.py` -> **EXIT 0 (PASS)**  

---

## 1. Executive Summary & Verdict

### Verdict: PASS

Every material scientific claim in `paper_tste_ieee.md` strictly honors the claim ceiling defined in `docs/SCIENTIFIC_CONTRACT.md` and survives the strongest available simpler explanation.

The repository and manuscript have successfully executed a first-principles adversarial closure:
1. The paper does **not** claim that machine learning, graph neural networks, or Mixture-of-Experts (MoE) architectures universally outperform aerodynamic equations or direct statistical baselines.
2. The paper explicitly publishes its core **negative results**:
   - Plant-wide posterior conditioning is **refuted** for cost superiority against strong wind-speed-conditioned quantiles ($\Delta L = +523{,}044\text{ kW}\cdot\text{h}$ penalty, $p = 0.85$);
   - In steady-state operation ($63.7\%$ of time), wind-speed binning strictly dominates the posterior ($\Delta L = +410{,}340\text{ kW}\cdot\text{h}$, $p = 0.002$);
   - In transition windows ($36.3\%$ of time), posterior conditioning functions as a **localized risk hedge** (lowering violations from $8.36\%$ to $7.24\%$ and shortages from $90.2\text{k}$ to $86.6\text{k kW}\cdot\text{h}$ at the expense of $+149\text{k kW}\cdot\text{h}$ greater reserve procurement and $+112{,}704\text{ kW}\cdot\text{h}$ higher PSREI);
   - Dynamic MoE routing provides **no statistical advantage** over unrouted dense or modular baselines ($p = 0.380$);
   - Privileged regime supervision ($\lambda_{\text{align}}$) improves latent representation clustering ($p < 0.002$), but yields an unestablished downstream decision delta whose confidence interval crosses zero ($p = 0.556$);
   - Cross-site evaluations are heterogeneous boundary probes (Penmanshiel positive, Kelmarsh neutral, LHB negative overfitting boundary) rather than proof of universal generalization.
3. The programmatic claim gate (`scripts/verify_scientific_claim_gate.py`) verified all control-plane files, numerical bounds, interaction contrasts, and required/forbidden manuscript patterns with zero failures.

---

## 2. Evaluation of Mandatory Attacks (A through H)

### Attack A: Active-Power Direct-Readout Attack
- **Hypothesis:** The claimed latent-boundary recovery is merely an electromechanical readout of contemporaneous active power ($P_{\text{atv}, t}$), rather than an anchor-free discovery of complex spatio-temporal structure.
- **Evidence Inspected:**
  - `artifacts/channel_consequence_ablations.csv`
  - `artifacts/active_power_anchor_audit.csv`
  - `docs/CONSEQUENCE_SIGNAL_MECHANISM.md`
- **Audit Findings:**
  - In `artifacts/channel_consequence_ablations.csv`, Condition C2 (Active Power Only, 4 features) achieves Brier $= 0.0112$, $\text{NMI} = 0.461$, $\text{ARI} = 0.647$, and transition recall $= 62.9\%$.
  - Adding wake context (Condition C9, 8 features) yields virtually identical metrics: Brier $= 0.0114$, $\text{NMI} = 0.463$, $\text{ARI} = 0.648$, and transition recall $= 61.3\%$. The wake increment is negligible.
  - The Full Consequence Suite (Condition C1, 36 features) degrades metrics: Brier $= 0.0218$, $\text{NMI} = 0.226$, $\text{ARI} = 0.397$.
  - Non-power channels alone completely fail to identify fast transitions: Thermal-only (C4) has $\text{NMI} = 0.000$, $\text{ARI} = 0.000$, recall $= 0.0\%$; Direction-only (C5) has $\text{NMI} = 0.006$, recall $= 3.5\%$; Wake-only (C6) has $\text{NMI} = 0.000$, recall $= 0.0\%$.
  - In `artifacts/active_power_anchor_audit.csv`, Condition A (Contemporaneous $P_{\text{atv}, t} + \text{History}$) achieves $\text{AUROC} = 0.988$, Precision $= 59.7\%$, Recall $= 63.1\%$, and $\text{F1} = 0.613$. Withholding contemporaneous $P_{\text{atv}, t}$ (Condition B) causes recall to drop to $40.3\%$.
- **Adversarial Verdict:** **SURVIVES WITH SCOPE CEILING.** Active power is indeed the dominant mediator. The manuscript strictly complies: it explicitly attributes recovery to the active-power signature, acknowledges the direct-readout capability of contemporaneous power, notes that dynamical history tracks transitions ($40.3\%\text{--}58.8\%$), and explicitly rejects any claim that complex spatio-temporal neural networks are necessary to discover this boundary.

### Attack B: Matched-Direct-Quantile Attack
- **Hypothesis:** Posterior conditioning is merely a complicated conditional binning scheme that loses to a direct, observable wind-speed-conditioned quantile baseline evaluated under the same information set.
- **Evidence Inspected:**
  - `artifacts/strong_baseline_closure_summary.csv`
  - `artifacts/strong_baseline_bootstrap_contrasts.csv`
  - `docs/STRONG_BASELINE_CLOSURE.md`
- **Audit Findings:**
  - Across the full 35-day test split ($N = 385{,}205$ valid cells, $h=6$, $\rho=10$), Policy B (Wind-Speed Binned Quantile, 10 bins) incurs a PSREI cost of $13{,}784{,}320\text{ kW}\cdot\text{h}$.
  - Policy C (Posterior-Conditioned Quantile) incurs $14{,}307{,}364\text{ kW}\cdot\text{h}$, representing a net penalty of **$+523{,}044\text{ kW}\cdot\text{h}$** ($p = 0.85$).
  - In steady-state operation ($N = 245{,}521$, $63.74\%$ of test split), Policy B incurs $9{,}464{,}010\text{ kW}\cdot\text{h}$ vs. Policy C's $9{,}874{,}350\text{ kW}\cdot\text{h}$ ($\Delta = \mathbf{+410{,}340\text{ kW}\cdot\text{h}}$, $p = 0.002$).
  - Policy C only outperforms the unconditioned Global Quantile Policy A ($16{,}132{,}772\text{ kW}\cdot\text{h}$); it loses plant-wide to the strong matched direct baseline Policy B.
- **Adversarial Verdict:** **SURVIVES WITH NEGATIVE-RESULT DISCLOSURE.** The manuscript completely refrains from claiming cost dominance over Policy B. It explicitly states in the Abstract, Results, and Discussion that wind-speed-conditioned quantiles remain lower-cost plant-wide and in steady state, framing the posterior solely as a localized risk-hedging mechanism.

### Attack C: Decision-Sufficiency Attack
- **Hypothesis:** High representation alignment (NMI, ARI) and state classification accuracy do not produce operational reserve decision improvements.
- **Evidence Inspected:**
  - `artifacts/clean_privileged_supervision_ablation.csv`
  - `artifacts/modular_classifier_reserve_control/`
  - `docs/PRIVILEGED_SUPERVISION_ABLATION.md`
- **Audit Findings:**
  - In `clean_privileged_supervision_ablation.csv`, privileged alignment ($\lambda_{\text{align}} = 5000$) increases NMI from $0.240 \pm 0.150$ to $0.819 \pm 0.088$ ($p = 0.0015$) and ARI from $0.198 \pm 0.139$ to $0.889 \pm 0.057$ ($p = 0.0005$).
  - However, the paired downstream PSREI delta is $-311{,}957 \pm 1{,}085{,}873\text{ kW}\cdot\text{h}$ with a 95% Student-$t$ CI of $[-1{,}660{,}247, +1{,}036{,}332]\text{ kW}\cdot\text{h}$ ($p = 0.5556$, crossing zero). In 3 out of 5 seeds (201, 202, 205), alignment actually increased costs.
  - Furthermore, an independent classifier achieving perfect transition recall ($1.000$) incurs a surrogate cost of $86.54\text{M kW}\cdot\text{h}$ ($9.54\%$ violation), which is significantly worse than the simple physical-bin baseline ($84.31\text{M kW}\cdot\text{h}$, paired $t$-test $p = 0.0013$).
- **Adversarial Verdict:** **SURVIVES WITH STRICT SEPARATION.** The manuscript dedicates Section IV-E (Result 5) to the explicit thesis "Classification Accuracy Does Not Equal Reserve Value", strictly separating representation quality from decision value.

### Attack D: Slice-Selection Attack
- **Hypothesis:** Positive claims for posterior conditioning depend on cherry-picking transition windows or boundary bands while concealing adverse plant-wide or steady-state performance.
- **Evidence Inspected:**
  - `artifacts/mediation_analysis.csv`
  - `artifacts/strong_baseline_closure_summary.csv`
  - `paper_tste_ieee.md` Section IV-D
- **Audit Findings:**
  - `artifacts/mediation_analysis.csv` details all slices: Full (100%), Boundary band (2.03%), Far field (93.00%), True Regime Pitch (3.08%), True Regime MPPT (70.95%), Dynamic Transitions (36.26%), Stationary Steady (63.74%), High Confidence (4.66%), Moderate Confidence (1.03%), Low Confidence (94.32%).
  - Across every single slice, Policy C incurs higher PSREI than Policy B (e.g., Boundary band: $+17{,}375\text{ kW}\cdot\text{h}$, $p = 0.8868$; High confidence: $+29{,}717\text{ kW}\cdot\text{h}$, $p = 0.8918$; Steady: $+410{,}340\text{ kW}\cdot\text{h}$, $p = 0.002$; Transitions: $+112{,}704\text{ kW}\cdot\text{h}$, $p = 0.48$).
  - In transition windows, Policy C contracts violations ($7.24\%$ vs. $8.36\%$) and shortages ($86.6\text{k}$ vs. $90.2\text{k kW}\cdot\text{h}$), but requires $+149{,}092\text{ kW}\cdot\text{h}$ additional reserve capacity.
- **Adversarial Verdict:** **SURVIVES WITH HONEST SLICE PRESENTATION.** The manuscript presents full-population, steady-state, and transition results side-by-side, explicitly documenting the $+523\text{k kW}\cdot\text{h}$ full-population penalty and $+410\text{k kW}\cdot\text{h}$ steady penalty, and characterizing the transition window result strictly as risk hedging at higher procurement cost.

### Attack E: Privileged-Supervision Attack
- **Hypothesis:** The model utilizes privileged blade-pitch supervision during training, masking an unaddressed modality shift where claims might silently imply applicability to wind farms where pitch was never recorded.
- **Evidence Inspected:**
  - `docs/PRIVILEGED_SUPERVISION_ABLATION.md`
  - `artifacts/clean_privileged_supervision_ablation.csv`
  - `paper_tste_ieee.md` Section IV-D & Limitations
- **Audit Findings:**
  - Historical pitch registers ($\beta$) are present during training ($x_{\text{hist}}$ channels 7--8) and used for offline cross-entropy supervision ($\mathcal{L}_{\text{align}}$), but are strictly zero-masked/withheld during validation and testing.
  - The manuscript contains explicit disclosures in the Abstract, Section IV-D, and Limitations:
    > *"trained using historically available pitch information that is withheld at deployment"*
    > *"This matched ablation isolates regime-label supervision conditional on privileged training inputs, without isolating training-time pitch access itself."*
    > *"The study assumes historical blade-pitch availability during offline training, followed by pitch withholding at deployment. Performance in settings where pitch was never recorded remains untested."*
- **Adversarial Verdict:** **SURVIVES WITH COMPLETE MODALITY DISCLOSURE.** The boundary between privileged training and pitch-withheld deployment is explicitly stated, and pitch-never-recorded deployment is formally bounded as untested.

### Attack F: Architecture-Necessity Attack
- **Hypothesis:** The claimed benefits require dynamic MoE routing, continuous wake diffusion graphs, or joint multi-task neural architectures.
- **Evidence Inspected:**
  - `artifacts/single_task_dense_vs_multitask_moe_ablation.csv`
  - `artifacts/capacity_matched_dense_wtb/`
  - `paper_tste_ieee.md` Section IV-F
- **Audit Findings:**
  - In `artifacts/single_task_dense_vs_multitask_moe_ablation.csv`, comparing STGQ-Dense to STGQ-Routed yields statistical parity: at $h=1$ clean, costs are $596{,}753\text{ kW}\cdot\text{h}$ (Dense) vs. $663{,}915\text{ kW}\cdot\text{h}$ (MoE Routed), cost ratio $0.898 \pm 0.235$.
  - Paired difference is $+29{,}624\text{ kW}\cdot\text{h}$ (95% CI $[-53{,}774, +113{,}023]$, $p = 0.380$). At $h=6$, paired difference $+32{,}154\text{ kW}\cdot\text{h}$ crosses zero (95% CI $[-1{,}148, +65{,}456]$).
  - STGQ-Modular (decoupled architecture with frozen embeddings and a dedicated residual head) matches tail reliability ($9.7\%$ violation, $1{,}284{,}098\text{ kW}\cdot\text{h}$) vs. STGQ-Routed ($10.6\%$ violation, $1{,}412{,}321\text{ kW}\cdot\text{h}$).
- **Adversarial Verdict:** **SURVIVES BY FALSIFYING ROUTING.** The manuscript explicitly entitles Section IV-F "MoE Mechanism Falsification (RQ3)", highlighting that dynamic MoE routing provides no measurable advantage over unrouted dense baselines ($p = 0.380$) or modular architectures.

### Attack G: External-Validity Attack
- **Hypothesis:** Multi-farm evaluations are claimed as universal proof of cross-site generalization, while masking negative transfer, lack of matched controls, and directional asymmetry.
- **Evidence Inspected:**
  - `artifacts/external_wind_runs/`
  - `docs/SITE_MECHANISM_BOUNDARY_TABLE.md`
  - `paper_tste_ieee.md` Section IV-G & Table IV
- **Audit Findings:**
  - In Table IV, STGQ relative to the unconditioned global quantile baseline exhibits severe cross-site heterogeneity:
    - WTB ($N=134$): $-38\text{k kW}\cdot\text{h}$ (boundary band, $p < 0.05$);
    - Penmanshiel ($N=14$): $-2.14\text{M kW}\cdot\text{h}$ ($p < 0.05$);
    - Kelmarsh ($N=6$): $-40\text{k kW}\cdot\text{h}$ (95% CI $[-204\text{k}, +172\text{k}]$, statistically neutral);
    - ENGIE La Haute Borne ($N=4$): $+43\text{k kW}\cdot\text{h}$ annual ($+1.01\text{M kW}\cdot\text{h}$ quarterly walk-forward, statistically negative overfitting boundary).
  - Continuous physical quantiles match or edge STGQ across all sites (WTB: 842k vs 855k; Kelmarsh: 1,025k vs 1,025k; Penmanshiel: 2,029k vs 2,029k).
  - Zero-shot transfer exhibits severe directional asymmetry: Kelmarsh $\to$ Penmanshiel NMI $= 0.77$ vs. Penmanshiel $\to$ Kelmarsh NMI $= 0.34$.
- **Adversarial Verdict:** **SURVIVES WITH SITE-HETEROGENEITY BOUNDING.** The manuscript explicitly states:
  > *"The three external European facilities must not be presented as uniform replication evidence: their observed effects are heterogeneous (Penmanshiel: positive; Kelmarsh: statistically neutral; LHB: negative overfitting boundary)... Because Table IV compares STGQ against an unconditioned global baseline rather than a matched external no-graph ablation, these comparisons do not by themselves establish that spatial wake modeling causally drives external-site improvements."*

### Attack H: Synthetic-Stress Attack
- **Hypothesis:** Synthetic 60-minute latency and Gilbert-Elliott packet dropouts are mischaracterized as empirical field frequencies of commercial SCADA networks.
- **Evidence Inspected:**
  - `paper_tste_ieee.md` Section IV-B, Section V, Section VI
  - `docs/SCIENTIFIC_CONTRACT.md`
- **Audit Findings:**
  - The manuscript explicitly labels Delay-6 as a *"60-minute synthetic latency contingency stress test"* designed to test asymptotic reliability breakdown.
  - The Limitations section explicitly notes:
    > *"Impairments are evaluated under synthetic stress (10--30 min backlogs, 60-min latency, Gilbert-Elliott dropouts); field units may exhibit sensor icing or individual pitch actions outside supervisory records."*
- **Adversarial Verdict:** **SURVIVES AS REGISTERED STRESS ENVELOPE.** No claims are made that 60-minute delays reflect normal operational frequency.

---

## 3. Claim-by-Claim Audit Table

| Claim | Contract Status | Strongest Falsifier | Evidence Inspected | Result | Allowed Wording in Manuscript |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1. Fresh Telemetry:** Deterministic physical rule achieves lowest boundary surrogate cost. | **VERIFIED** | Deep STGNNs with full spatial wake modeling beat physical curves. | `artifacts/single_task_dense_vs_multitask_moe_ablation.csv`, Table I ($h=6$) & Table III ($h=1$) | Continuous Physical Quantile achieves lowest cost ($589.5\text{k kW}\cdot\text{h}$ at $h=1$, $881.4\text{k kW}\cdot\text{h}$ at $h=6$, $\sim 6.8\%$ violation), beating neural nets by $8.1\%\text{--}11.1\%$ ($-77.7\text{k kW}\cdot\text{h}$, 95% CI strictly $<0$). | Allowed strictly within the evaluated boundary band ($|v_{\text{phys}}-10.5|\le 1.0\text{ m/s}$) under fresh telemetry ($\tau=0$). |
| **2. Observable Latency:** Non-neural state-conditional recalibration absorbs shortage loss. | **VERIFIED** | Complex neural representation learning is required to handle latency drift. | Table III, `artifacts/single_task_dense_vs_multitask_moe_ablation.csv` | Under 60-min latency with observable channels, recalibration absorbs $55.3\%$ of shortage ($127.6 \to 57.0\text{ MWh}$), restoring violation to $9.46\%$ without updating network weights. | Allowed as an information-preserving non-neural statistical correction under full channel observability. |
| **3. Pitch Withheld:** Consequence signals retain boundary information. | **VERIFIED, bounded** | Unobservable pitch eliminates all boundary recoverability; signals have zero mutual information. | `artifacts/channel_consequence_ablations.csv`, `docs/CONSEQUENCE_SIGNAL_MECHANISM.md` | Active-power consequence (C2) recovers Brier $= 0.0112$, $\text{NMI} = 0.461$, $\text{ARI} = 0.647$, transition recall $= 62.9\%$. | Allowed with explicit note that active power signature dominates and setting relies on privileged training history. |
| **4. Active Power Dominance:** Active power is the primary mediator of recoverability. | **VERIFIED** | Dynamic wake diffusion or thermal inertia is necessary for recovery. | `artifacts/channel_consequence_ablations.csv`, `artifacts/active_power_anchor_audit.csv` | C2 alone achieves $\text{NMI} = 0.461$; C9 (wake) adds $+0.002$; C4 (thermal) has $\text{NMI} = 0.000$; contemporaneous power has $\text{AUROC} = 0.988$. | Allowed. Must not claim that complex spatio-temporal structure is necessary. |
| **5. Plant-wide PSREI Superiority:** Posterior conditioning beats wind-speed bins plant-wide. | **REFUTED by current closure** | Strong matched direct quantile baseline (Policy B, wind-speed bins). | `artifacts/strong_baseline_closure_summary.csv` | Posterior incurs $+523{,}044\text{ kW}\cdot\text{h}$ penalty plant-wide ($p = 0.85$) and $+410{,}340\text{ kW}\cdot\text{h}$ penalty in steady state ($p = 0.002$). | **FORBIDDEN TO CLAIM.** Manuscript correctly reports this refutation. |
| **6. Transition-Localized Risk Hedging:** Posterior alters risk trade-off in transitions. | **PARTIALLY SUPPORTED** | Interaction contrast crosses zero; transition savings are mere loss concentration. | `artifacts/strong_baseline_bootstrap_contrasts.csv` | Mean interaction contrast is $-296{,}123\text{ kW}\cdot\text{h}$ ($p = 0.002$). In transitions, violation drops ($8.36\% \to 7.24\%$) and shortage drops ($90.2\text{k} \to 86.6\text{k kW}\cdot\text{h}$), but reserve rises ($+149\text{k kW}\cdot\text{h}$) and PSREI rises ($+112\text{k kW}\cdot\text{h}$). | Allowed strictly as localized risk hedging at higher procurement cost, not cost optimality. |
| **7. Regime Alignment:** Regime supervision improves representation structure. | **VERIFIED** | Alignment loss produces representation collapse or zero NMI change. | `artifacts/clean_privileged_supervision_ablation.csv` | $\lambda_{\text{align}}=5000$ improves NMI ($+0.579$, $p=0.0015$) and ARI ($+0.692$, $p=0.0005$) on matched backbones. | Allowed for representation clustering and state organization; must not imply downstream decision gains. |
| **8. Downstream Gain from Supervision:** Regime supervision improves downstream PSREI. | **NOT ESTABLISHED** | Matched $\lambda_{\text{align}}$ downstream PSREI evaluation across seeds. | `artifacts/clean_privileged_supervision_ablation.csv` | Downstream delta is $-311{,}957 \pm 1{,}085{,}873\text{ kW}\cdot\text{h}$ ($p = 0.556$, 95% CI crosses zero); 3 of 5 seeds show cost increases. | Allowed only as an unestablished null/neutral downstream cost result. |
| **9. MoE Routing Necessity:** MoE routing is a critical mechanism. | **NOT SUPPORTED (Falsified)** | Capacity-matched dense baseline and decoupled modular baseline. | `artifacts/single_task_dense_vs_multitask_moe_ablation.csv`, Table II | MoE vs. Dense: ratio $1.045$, $p = 0.380$; Dense beats MoE in 3 of 5 seeds; Modular matches tail reliability ($9.7\%$ violation). | Allowed strictly as a negative result: dynamic MoE routing provides no statistical advantage. |
| **10. Cross-Farm Generalization:** External farms prove universal model generalization. | **NOT ESTABLISHED** | Independent external wind farm evaluations (Kelmarsh, Penmanshiel, LHB). | `docs/SITE_MECHANISM_BOUNDARY_TABLE.md`, Table IV | Heterogeneous: Penmanshiel positive ($-2.14\text{M}$ vs. global), Kelmarsh neutral ($-40\text{k}$, CI crosses zero), LHB negative ($+43\text{k}$ annual penalty). | Allowed strictly as heterogeneous boundary probes; zero-shot transfer fails; local retraining recommended. |
| **11. Industrial Latency Representation:** 60-min delay reflects real-world SCADA latency. | **NOT ESTABLISHED** | SCADA communication protocol timing literature. | `docs/SCIENTIFIC_CONTRACT.md`, Section IV-B | Delays $>30\text{ min}$ are rare contingencies, not steady polling states. | Allowed strictly as a synthetic stress test / contingency envelope. |
| **12. Pitch-Never-Recorded Setting:** System works where pitch was never logged. | **UNKNOWN** | Historical training buffer composition. | `docs/PRIVILEGED_SUPERVISION_ABLATION.md` | Models were trained with historical pitch registers present in training sets. | Allowed strictly as an untested/unknown limitation. |
| **13. End-to-End Market / AC-OPF Value:** Economic cash flows in wholesale markets. | **OUT OF SCOPE / BLOCKED** | Level-1 pre-dispatch proxy vs. Level-2 AC-OPF settlement. | `docs/FIXED_TARGET_CONTRACT.md`, Section III-A | Level-1 PSREI newsvendor surrogate abstracts transmission constraints and balancing cash settlement. | Allowed strictly as a Level-1 pre-dispatch operational screening proxy. |

---

## 4. Simplest Surviving Explanation

The simplest sufficient explanation that accounts for all verified experimental findings in this repository is:

1. **Aerodynamics under pristine conditions:** Wind turbine power generation is an electromechanical physical process with a hard saturation ceiling ($P_{\text{rated}}$) and cubic aerodynamic power conversion. When telemetry is fresh, evaluating the physical power curve evaluates the true bounding physics directly, producing the lowest surrogate risk and minimal variance without neural parameter estimation.
2. **Telemetry staleness as an observable distribution shift:** When telemetry experiences transmission latency but registers remain present, the error manifests as a known distribution shift. Conditioning quantile margins on held-out delayed residuals via non-neural state-conditional recalibration absorbs $55.3\%$ of the shortfall without modifying neural weights.
3. **Electromechanical lock-in as the recovery mechanism:** When pitch telemetry is withheld at deployment, a turbine in Region 3 is electromechanically clamped at rated active power. Consequently, contemporaneous active power ($P_{\text{atv}, t}$) provides a direct readout of the pitch boundary ($\text{AUROC} = 0.988$). Historical active power trajectories provide dynamical tracking of boundary transitions ($40.3\%\text{--}58.8\%$). Slower thermal registers, yaw angles, and wake context provide negligible incremental high-frequency boundary information.
4. **Observable wind-speed binning as the minimum sufficient decision baseline:** In asymmetric reserve allocation, conditional residual variance across the farm is predominantly driven by inflow wind velocity. Binned empirical quantiles conditioned on wind speed ($Policy\_B$) capture this structure directly and achieve the lowest surrogate cost plant-wide ($13.78\text{M kW}\cdot\text{h}$) and in steady state ($9.46\text{M kW}\cdot\text{h}$).
5. **Posterior conditioning as localized tail-risk hedging:** Recovering the latent boundary posterior ($Policy\_C$) does not reduce plant-wide cost ($14.31\text{M kW}\cdot\text{h}$, a $+523\text{k kW}\cdot\text{h}$ penalty). Near operating transitions, posterior conditioning acts as a conservative risk buffer: it procures $+149\text{k kW}\cdot\text{h}$ more reserve capacity, contracting violation rates from $8.36\%$ to $7.24\%$ and shortages from $90.2\text{k}$ to $86.6\text{k kW}\cdot\text{h}$, resulting in a net PSREI cost increase of $+112\text{k kW}\cdot\text{h}$. This represents a localized risk-hedging trade-off, not cost dominance.
6. **Architectural simplicity:** Dynamic MoE routing, dynamic graph advection, and joint multi-task routing are superfluous. Decoupled modular and dense architectures achieve statistical parity ($p = 0.380$).

---

## 5. Status of Manuscript Claims: Weakened, Deleted, and Preserved Boundaries

All necessary claim adjustments have been successfully integrated into `paper_tste_ieee.md`. No further manuscript text deletions or weakenings are required for the paper to satisfy `docs/SCIENTIFIC_CONTRACT.md`.

Specific guardrails confirmed in the text:
1. **Plant-wide cost superiority rejected:** The manuscript explicitly declares that wind-speed-conditioned quantiles remain lower-cost plant-wide ($\Delta L = +523{,}044\text{ kW}\cdot\text{h}$, $p = 0.85$).
2. **Transition mediation re-framed:** The manuscript explicitly decouples loss concentration ($33\%$ baseline loss in transitions) from model behavior, framing the transition effect as risk hedging with higher procurement costs.
3. **MoE routing falsified:** The manuscript explicitly labels MoE routing as yielding no advantage ($p = 0.380$).
4. **Privileged supervision disclosed:** The manuscript explicitly discloses that pitch was available during offline training but withheld at deployment, and notes that downstream decision gains from supervision are not established ($p = 0.556$).
5. **External validity localized:** The manuscript explicitly presents external sites as heterogeneous boundary probes, acknowledges LHB as a negative overfitting boundary, and highlights that external gains cannot be causally attributed to wake modeling alone.

---

## 6. Decisive Experiments That Settle the Scientific Questions

The following six registered experiments constitute the authoritative, decisive evidentiary core:

1. **EXP-Q1-001 (Active-Power Minimal Recoverability):** `artifacts/channel_consequence_ablations.csv` establishes that Condition C2 (Active Power Only) captures over 95% of state recoverability, proving that active power is the dominant mediator.
2. **EXP-Q1-002 (Incremental Wake Necessity):** Comparison of C9 vs. C2 establishes that wake context contributes negligible incremental recoverability ($\text{NMI } 0.463 \text{ vs. } 0.461$), falsifying wake necessity for state recovery.
3. **EXP-Q2-001 (Strong Matched-Baseline Closure):** `artifacts/strong_baseline_closure_summary.csv` falsifies plant-wide posterior cost superiority over wind-speed bins ($+523{,}044\text{ kW}\cdot\text{h}$, $p = 0.85$), proving that direct wind-speed binning is the minimum sufficient model plant-wide.
4. **EXP-Q2-002 (Transition-vs-Steady Heterogeneity Contrast):** `artifacts/strong_baseline_bootstrap_contrasts.csv` establishes a statistically significant interaction ($\text{mean } -296{,}123\text{ kW}\cdot\text{h}$, $p = 0.002$), confirming regime heterogeneity and risk hedging in transitions.
5. **EXP-Q3-001 (Minimum-Sufficient Observability Scan):** Table III (`artifacts/single_task_dense_vs_multitask_moe_ablation.csv`) establishes the 3-tier operational hierarchy: fresh physics ($589.5\text{k kW}\cdot\text{h}$), recalibrated physics ($1{,}228.6\text{k kW}\cdot\text{h}$, $55.3\%$ shortage absorption), and learned recovery under pitch withholding ($755.8\text{k kW}\cdot\text{h}$).
6. **Architecture Ablation (Dense vs. MoE Parity):** Table II confirms that dynamic MoE routing provides no statistically significant gain over unrouted dense models ($p = 0.380$).

---

## 7. UNKNOWN and BLOCKED Items Ledger

The following items are officially documented as unresolved and remain strictly outside the verified claims of the study:

1. **Pitch-Never-Recorded Training Boundary (EXP-Q1-003):**  
   - *Status:* **PROPOSED / NOT RUN / UNKNOWN.**  
   - *Scope:* Whether boundary-relevant latent representations can be learned when blade pitch has never been recorded historically remains untested.
2. **External-Site Matched Direct-Quantile Closure (EXP-Q2-003):**  
   - *Status:* **PROPOSED / BLOCKED.**  
   - *Scope:* External wind farm benchmarks compare against unconditioned global quantiles, lacking site-local wind-speed-binned controls and matched no-graph ablations. External wake modeling cannot be claimed as a causal mechanism.
3. **Industrial SCADA Latency Distribution:**  
   - *Status:* **UNKNOWN.**  
   - *Scope:* Field distributions of asynchronous packet arrival, clock drift, serialization jitter, and non-stationary packet loss in operational utilities remain uncharacterized.
4. **Wholesale Market Settlement and AC-OPF (Level 2):**  
   - *Status:* **OUT OF SCOPE / BLOCKED.**  
   - *Scope:* Actual financial cash flows, transmission congestion, nodal balancing settlements, and spinning reserve deployment are abstracted by the Level-1 PSREI newsvendor surrogate.

---

## 8. Final Audit Certification

The adversarial scientific audit confirms that:
- Every claim in `paper_tste_ieee.md` stays strictly within the boundaries of `docs/SCIENTIFIC_CONTRACT.md`.
- No claim exceeds the evidence of the strongest matched direct baselines.
- The repository enforces negative-result preservation and structural reproducibility.
- `scripts/verify_scientific_claim_gate.py` passed unconditionally with zero errors.

**Official Audit Verdict:** **PASS**
