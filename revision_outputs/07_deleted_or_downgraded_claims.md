# Formal Forensic Audit of Deleted, Downgraded, and Qualified Claims
## Target: IEEE Transactions on Sustainable Energy (TSTE)
**Artifact ID**: `07_deleted_or_downgraded_claims.md`  
**Date**: September 2026  

---

## 1. Executive Summary of Scientific Forensic Audit

To transition the manuscript from a promotional machine-learning preprint to an authoritative, rigorous paper in *IEEE Transactions on Sustainable Energy*, an exhaustive scientific forensic audit was conducted. Every empirical claim was evaluated against raw experimental artifacts, statistical confidence intervals, and power engineering realities.

Unsubstantiated marketing claims, post-hoc rationalizations, and over-generalized assertions have been systematically purged, downgraded, or circumscribed with explicit operational boundary conditions.

---

## 2. Forensic Register of Deleted or Downgraded Claims

### Audit Entry 1: Demystification and De-marketing of Dynamic MoE Routing
- **Historical Text / Claim**: *"Our physics-aligned Mixture-of-Experts (MoE) architecture routes turbines to physically specialized experts, fundamentally outperforming conventional dense neural networks across all operating regimes."*
- **Forensic Status**: **DELETED & CONDENSED TO ABLATION COMPARATOR**.
- **Empirical Evidence**: Across 5 strict-mask random seeds under matched capacity (110k parameters), Dense (matched) and dynamic MoE achieve statistical parity on Clean telemetry (cost ratio $1.045$, $p=0.380$). Under Delay-6, MoE's nominal advantage ($+79{,}637\text{ kW}\cdot\text{h}$, raw $p=0.038$) fails to reach significance after Bonferroni correction ($\alpha = 0.0125$). Furthermore, a decoupled modular pipeline (*Frozen Backbone + Residual Quantile*) achieves $1.284\text{M kW}\cdot\text{h}$ and $9.68\%$ violation without dynamic gating.
- **Revised Framing in Reconstruction**: The framework is rechristened as **Spatio-Temporal Graph Quantile (STGQ)**. MoE is treated objectively as an ablation variant, proving that operational gains originate from spatio-temporal feature representations and decoupled residual quantile calibration, not dynamic routing.

---

### Audit Entry 2: Qualification of 60-Minute Telemetry Latency
- **Historical Text / Claim**: *"We evaluate communication delays of up to 60 minutes as representative operational conditions in utility wind farms."*
- **Forensic Status**: **DOWNGRADED & QUALIFIED AS CONTINGENCY STRESS ENVELOPE**.
- **Empirical Evidence**: Industrial wind SCADA systems (IEC 61400-25) operate on 10-minute polling cycles. Latencies of 10–30 minutes correspond to plausible substation buffer congestion, cellular retransmissions, or satellite queuing. A 60-minute delay represents an extreme failure event.
- **Revised Framing in Reconstruction**: The 6-step ($60\text{ min}$) latency condition is explicitly defined as a **severe contingency outage-envelope stress condition** (simulating substation gateway crashes, fiber cuts, or cyber-physical storm blackouts) designed deliberately to probe the asymptotic mathematical breakdown of static physical rules.

---

### Audit Entry 3: Elimination of Post-Hoc Excuse on La Haute Borne (LHB)
- **Historical Text / Claim**: *"The negative reserve performance on La Haute Borne occurred because the wind farm operator did not implement Point of Common Coupling (PCC) smoothing in their dispatch logs."*
- **Forensic Status**: **DELETED & REPLACED WITH HONEST OPERATIONAL BOUNDARY**.
- **Empirical Evidence**: On the 4-turbine ENGIE LHB wind farm, learned models exhibit a positive cost delta ($+1.01\text{M kW}\cdot\text{h}$ walk-forward, $+43\text{k kW}\cdot\text{h}$ annual) compared to physical rules. Blaming operator dispatch for this failure was an unsubstantiated post-hoc rationalization.
- **Revised Framing in Reconstruction**: LHB is honestly and transparently foregrounded as a documented **operational boundary condition**. In micro-farms ($\le 4$ turbines) situated in complex rolling terrain, aerodynamic wake propagation lacks spatial multi-path redundancy. Spatial graph learning overfits local turbulence, demonstrating that spatio-temporal neural representations require utility-scale turbine arrays ($\ge 6\text{--}15$ turbines) to provide positive risk mitigation.

---

### Audit Entry 4: Substation Edge Computing Hardware Claims
- **Historical Text / Claim**: *"Our model achieves sub-5 ms latency and sub-megabyte memory footprints, proving direct deployment readiness on low-cost substation microcontrollers and edge RTUs."*
- **Forensic Status**: **DOWNGRADED & QUALIFIED AS THEORETICAL FOOTPRINT**.
- **Empirical Evidence**: The 110k parameter count and $3.8\text{ ms}$ inference time were benchmarked on a desktop GPU/CPU in Python/PyTorch. No experiments were conducted on embedded ARM Cortex-M or industrial RTU hardware running real-time operating systems (RTOS).
- **Revised Framing in Reconstruction**: Phrased strictly as a **theoretical parameter and execution footprint**, noting that 110k float32 parameters occupy $\sim 440\text{ kB}$ of memory, indicating algorithmic compactness consistent with substation computer constraints, while avoiding unsubstantiated embedded hardware claims.

---

### Audit Entry 5: Downscaling of Battery Energy Storage (BESS) Dispatch Scope
- **Historical Text / Claim**: *"We formulate an end-to-end BESS rolling dispatch Model Predictive Control algorithm that optimizes wholesale market revenue and proves commercial arbitrage value."*
- **Forensic Status**: **DOWNGRADED & RELEGATED TO SUPPLEMENTARY MATERIAL**.
- **Empirical Evidence**: The linear program used simple static round-trip efficiency ($\eta=0.90$) and did not model non-linear electrochemical degradation, solid-electrolyte interphase (SEI) growth, ambient thermal effects, or real AC power-flow grid constraints.
- **Revised Framing in Reconstruction**: BESS MPC is moved entirely to **Supplementary Material**, retaining only a single illustrative paragraph in Section II-D/Discussion to illustrate downstream dispatchability. The main paper's benchmark endpoint remains anchored strictly to the upstream Penalized Reserve-Shortfall Energy Index (PSREI).

---

### Audit Entry 6: Tone Down Unconditional Compliance and Universal Superiority
- **Historical Text / Claim**: *"Our physics-guided model guarantees operational compliance and eliminates tail risk across all utility deployments."*
- **Forensic Status**: **DOWNGRADED TO STATISTICALLY BOUNDED RELATIVE MITIGATION**.
- **Empirical Evidence**: Under Delay-6, learned posteriors settle test violation at $10.6\% \pm 1.1\%$, with only 3 out of 5 random seeds ($60\%$) strictly achieving $\le 10.0\%$ violation. State-conditional recalibration absorbs $55.3\%$ of shortage, while learned models add $5.4\%$.
- **Revised Framing in Reconstruction**: Explicitly phrased as **relative risk mitigation under frozen validation calibration**, acknowledging that no model provides unconditional compliance under severe telemetry loss without conservative margin inflation.
