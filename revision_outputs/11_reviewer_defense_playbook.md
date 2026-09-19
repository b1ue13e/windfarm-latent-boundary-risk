# IEEE Transactions on Sustainable Energy
## Senior Reviewer & Editorial Defense Playbook (审稿人应对预案)

**Manuscript Title:** *Operational Boundaries of Aerodynamic Power Rules, Recalibration, and Learned Representations under SCADA Telemetry Degradation*  
**Authors:** Junyu Li and Juntao Du  
**Venue:** *IEEE Transactions on Sustainable Energy* (TSTE)  
**Document ID:** `11_reviewer_defense_playbook.md`  
**Target Roles:** Associate Editor (AE), Reviewer #1 (Power Systems Operations), Reviewer #2 (Skeptical Aerodynamics/SCADA Expert), Reviewer #3 (Machine Learning Specialist)

---

### Executive Summary for Authors

This playbook provides a structured, point-by-point defense strategy anticipating the sharpest, most adversarial inquiries from IEEE TSTE reviewers. By shifting the manuscript narrative from a machine learning architectural claim ("our MoE model is superior") to an empirical boundary-science framework ("when physical rules, recalibration, and learned representations are each operational necessities"), every potential attack surface has been fortified with concrete mathematical derivations, audited CSV artifacts, and multi-farm empirical benchmarks.

---

### Defense Matrix: Anticipated Reviewer Challenges & Rebuttal Strategies

```
+-------------------------------------------------------------------------------------------------------------+
| Reviewer Concern / Attack Vector          | Vulnerability Level | Primary Defense Pillar & Evidence Anchor  |
+-------------------------------------------------------------------------------------------------------------+
| 1. Why local Newsvendor (PSREI) instead   | Moderate            | Upstream Level-1 risk triage defense;     |
|    of full grid AC-OPF with LMPs?         |                     | computational viability; Table A12 MWh.   |
+-------------------------------------------------------------------------------------------------------------+
| 2. Are 10-60 min SCADA latencies and      | High                | Communication queuing & gateway crashes;  |
|    withheld pitch registers realistic?    |                     | commercial OEM interface boundaries; IEC. |
+-------------------------------------------------------------------------------------------------------------+
| 3. If MoE routing is statistically        | Low (Turn into      | Core paper contribution: DATA DECIDES     |
|    equivalent to Dense, why neural nets?  | central finding)    | STORY; value emerges under missing pitch. |
+-------------------------------------------------------------------------------------------------------------+
| 4. Why does model underperform physics    | Moderate (Turn into | Validated operational boundary: micro-    |
|    on La Haute Borne (4-turbine site)?    | boundary condition) | scale arrays lack wake spatial diversity. |
+-------------------------------------------------------------------------------------------------------------+
| 5. Why was BESS rolling MPC moved from    | Low                 | Scope isolation: prevents conflating      |
|    main text to Supplementary Material?   |                     | storage asset sizing with wind telemetry. |
+-------------------------------------------------------------------------------------------------------------+
```

---

### Point-by-Point Rebuttal Templates

#### Challenge 1: Scope of Economic Metric — Level-1 PSREI vs. Level-2 Full Grid AC-OPF

> **Reviewer #1 / Reviewer #2:**  
> *"The paper evaluates an operational cost proxy (Penalized Shortfall Energy Proxy, PSREI) based on an asymmetric Newsvendor loss with $\rho=10$. In bulk power systems, reserve procurement and generation balancing depend on transmission line congestion, locational marginal prices (LMPs), and AC optimal power flow (AC-OPF). Why did the authors not simulate a full IEEE benchmark grid with power flow constraints?"*

**Airtight Rebuttal Strategy:**
1. **Upstream Pre-Dispatch Triage Demarcation:** Clarify that bulk power grid reliability relies on a two-level defense architecture:
   - *Level-1 (Local Wind Plant Pre-Dispatch Triage):* Filters, screens, and risk-calibrates individual plant injections before submitting bids/schedules to the market operator.
   - *Level-2 (Global Transmission AC-OPF / Market Clearing):* Clears system-wide power flows, line thermal limits, and voltage constraints.
   If corrupt, stale, or over-optimistic wind forecasts from Region 2/3 transitions enter Level-2 dispatchers, they create unhedged physical deficiencies during real-time 10-minute balancing that force expensive spinning reserve deployment.
2. **Computational Viability at Operational Cadence:** Screening 134 individual wind turbines across five-minute or ten-minute intervals within an AC-OPF formulation introduces severe non-convexity and computational latency that obscures the specific telemetry degradation causal boundary.
3. **Physical Translation Provided:** Refer Reviewer #1 to **Supplementary Table A12** (*Engineering-Unit Value Translation*), which explicitly translates the dimensionless proxy into physical MWh of unserved energy ($127.6\text{ MWh} \to 57.0\text{ MWh}$) and monetary equivalents under varying shortage penalty ladders ($\rho \in [2, 20]$).
4. **Literature Grounding:** Cite classic foundational energy economics literature:
   - P. Pinson et al., "Trading wind energy in electricity markets: An asymmetric loss approach," *IEEE Trans. Power Syst.*, 2007.
   - R. Bessa et al., "Reserve requirements for wind power integration: An empirical risk approach," *IEEE Trans. Sustain. Energy*, 2017.

---

#### Challenge 2: Operational Realism of Telemetry Degradation & OEM Withheld Pitch

> **Reviewer #2 (Skeptical Industrial Reviewer):**  
> *"Modern wind farm SCADA protocols operate at sub-second or 1-minute intervals. How can the authors justify communication delays of 10 to 60 minutes? Furthermore, why would blade-pitch angle registers be inaccessible to plant operators or grid aggregators?"*

**Airtight Rebuttal Strategy:**
1. **Routine Latency vs. Severe Outage Contingencies:**
   - Explicitly distinguish routine latency ($\tau = 10\text{--}30\text{ min}$) from the 60-minute stress envelope. As documented in IEEE PES reports, utility telemetry often encounters gateway serialization bottlenecks, substation polling cycle delays, and wide-area network queuing when aggregated across hundreds of remote geographically dispersed turbines.
   - Clarify that the 60-minute latency condition ($\text{Delay-6}$) is explicitly declared throughout the paper as a **severe contingency / communication outage-envelope stress test** (simulating fiber cuts, microwave repeater power failures, or cyber-physical storms), rather than steady-state nominal latency.
2. **Commercial Access Boundaries and OEM Proprietary Protocols:**
   - In commercial wind energy operations, wind turbine OEMs (e.g., Vestas, Siemens Gamesa, Goldwind, GE) frequently treat internal blade-pitch control loops and high-frequency pitch sensor registers as proprietary intellectual property.
   - Third-party virtual power plant (VPP) aggregators, independent power producers (IPPs), and Transmission System Operators (TSOs) communicating via standard IEC 61400-25 or Modbus TCP interfaces often receive only gross active power ($\texttt{Patv}$), reactive power, and nacelle anemometer wind speed ($\texttt{Wspd}$), while individual blade pitch registers ($\texttt{Pab}$) are withheld or non-contractual.
   - Our counterfactual `no_pitch` ablation directly addresses this widespread commercial reality.

---

#### Challenge 3: Scientific Finding on Mixture-of-Experts (MoE) vs. Dense Architectures

> **Reviewer #3 (Machine Learning Specialist):**  
> *"Table 1 and Section IV-D show that the dynamic MoE architecture achieves almost identical performance to the capacity-matched Dense baseline under Clean telemetry ($p=0.380$) and shows only a marginal nominal gain under Delay-6 that is not statistically significant after Bonferroni correction. Does this invalidate the novelty of the proposed model?"*

**Airtight Rebuttal Strategy:**
1. **The Principle: 'Data Decides the Story, Architecture Does Not':**
   - Thank the reviewer for underscoring this exact observation, which represents one of the primary scientific contributions of the reconstructed paper.
   - Contrast this with typical machine learning papers that over-claim architecture superiority through cherry-picked seeds. We openly report negative results and provide full Bonferroni-corrected statistics ($\alpha = 0.0125$).
2. **Mechanistic Explanation of Statistical Parity:**
   - Explain *why* MoE does not outperform Dense: The shared directed-diffusion spatio-temporal graph backbone captures the dominant wake advection dynamics across the wind plant. Once this rich spatio-temporal representation is learned, downstream regime specialization does not require dynamic gating; a simple decoupled residual quantile head suffices ($1.284\text{M kW}\cdot\text{h}$ and $9.68\%$ violation).
3. **Operational Implication for Utilities:**
   - This finding is of tremendous practical importance to power grid operators: utilities do **not** need to deploy fragile, complex dynamic MoE routing gates in substation control centers. A single-checkpoint, modular neural representation provides equivalent tail risk defense without routing instability.

---

#### Challenge 4: Micro-Farm Operational Boundary on ENGIE La Haute Borne (LHB)

> **Reviewer #2:**  
> *"On the 4-turbine La Haute Borne site, the learned model incurs a positive cost penalty of $+1.01\text{M kW}\cdot\text{h}$ compared to the global quantile baseline. Why does your method fail on this real-world site?"*

**Airtight Rebuttal Strategy:**
1. **Embrace as a Fundamental Physical Boundary Condition:**
   - Reiterate that this result is deliberately highlighted in Section IV-F, Section V, and Supplementary Table A11h as a validated **operational boundary condition**.
2. **Physical Aerodynamic Rationale:**
   - *Array Scale & Spatial Redundancy:* WTB has 134 turbines spanning multiple rows where wake propagation exhibits strong multi-path physical redundancy. LHB consists of only 4 turbines arranged linearly along a localized ridge in complex terrain.
   - *Spatial Overfitting:* In a 4-turbine linear array, spatial graph convolutions overfit local topographic wind distortions rather than learning generalizable wake advection. Seasonal regime shifts (such as Autumn wake transitions in Q3, $+968.1\text{k kW}\cdot\text{h}$) amplify representation variance.
3. **Formal Deployment Gate Definition (Table A14):**
   - Rather than making ad-hoc excuses, we formalized this finding into an engineering deployment protocol: learned spatio-temporal graph models are operationally bounded to utility-scale plants with multi-row spatial array redundancy under telemetry degradation; on micro-scale 4-turbine sites with pristine sensors, calibrated physical rules or pooled quantile estimators should remain the default utility standard.

---

#### Challenge 5: Excision of Battery Energy Storage System (BESS) Dispatch from Main Text

> **Reviewer #1 / AE:**  
> *"Earlier drafts or similar energy papers often include battery energy storage system (BESS) sizing and rolling dispatch simulations. Why is BESS excluded from the main text of this paper?"*

**Airtight Rebuttal Strategy:**
1. **Methodological Purity & Attack Surface Elimination:**
   - The central research question of this study is: *What are the empirical operational boundaries of physical rules, recalibration, and learned representations under SCADA telemetry degradation?*
   - Introducing co-located battery storage in the main text convolves wind forecasting reliability with arbitrary battery engineering assumptions (e.g., C-rate sizing, depth of discharge, battery chemistry, initial State of Charge, throughput degradation cost $c_{\mathrm{deg}}$, and arbitrage strategies).
2. **Complete LP Formulation Retained in Supplementary Material:**
   - Note that full receding-horizon LP dispatch formulations via the HiGHS solver, continuous 35-day SoC trajectories (Figure A11-BESS1), and capacity sensitivity scans (5 to 40 MWh, Table A11-BESSb) are preserved in **Supplementary Material Section S4** as an illustrative downstream proof-of-concept.
   - In Supplementary Table A11-BESS, we show that 20 MWh storage mitigates $45.7\%$ of unhedged shortage energy under 60-minute latency, with exact mathematical equivalence between rolling LP and step heuristics. Keeping this in the supplement preserves main-text narrative focus while satisfying curious readers.

---

#### Challenge 6: Role of Offline Privileged Supervision ? Representation Discrimination vs. Reserve Decision Value

> **Reviewer #3 (Machine Learning Specialist) / Reviewer #2:**  
> *"The authors claim offline privileged supervision ($\mathcal{L}_{\mathrm{align}}$ with training-only blade pitch) enables the model to recover hidden aerodynamic states when pitch is withheld at deployment. Does privileged supervision also prove statistically necessary for downstream reserve decision cost savings?"*

**Airtight Rebuttal Strategy:**
1. **Preserve the Three-Layer Evidence Hierarchy:**
   - Clearly delineate what offline privileged supervision *does* and *does not* establish across three distinct, uncompressed layers:
     - **LAYER A ? Latent Representation & Calibration (SUPPORTED):** Offline regime supervision ($\lambda_{\mathrm{align}} = 5000$ vs. $\lambda_{\mathrm{align}} = 0$ on matched backbones across $n=5$ independent random seeds 201--205) substantially improves latent-state organization and reduces the observed susceptibility to representation collapse within the evaluated architecture:
       - $\Delta\text{NMI} = +0.579 \pm 0.167$ ($t(4) = 7.74, p = 0.0015$, 95% Student-$t$ CI $[+0.371, +0.787]$; $0.819$ vs. $0.240$);
       - $\Delta\text{ARI} = +0.692 \pm 0.153$ ($t(4) = 10.10, p = 0.0005$, 95% Student-$t$ CI $[+0.502, +0.882]$; $0.889$ vs. $0.198$).
       - *Posterior Calibration*: Regime supervision improves average calibration ($\Delta\text{Brier} = -0.2208 \pm 0.4183$, $0.020$ vs. $0.241$), but the estimated magnitude is sensitive to an observed representation collapse in a single unaligned run (Seed 204, where unaligned Brier degraded to $0.9812$). Excluding Seed 204, the remaining four seeds yield $\Delta\text{Brier} = -0.0359 \pm 0.0728$, with the 5-seed paired confidence interval including zero (95% CI $[-0.7402, +0.2986]$, $t(4)=-1.18, p=0.3033$).
     - **LAYER B ? Reserve Decision Information (INDEPENDENTLY SUPPORTED):** Downstream reserve decision value is established through posterior-conditioned residual quantile sizing vs unconditioned state-blind baselines (saving $568\text{k kW}\cdot\text{h}$, $p < 0.001$, 95% CI $[-726\text{k}, -406\text{k}]$). In contrast, raw $\lambda_{\mathrm{align}}$ alone yields an unestablished reserve cost difference: full-population $\Delta\text{PSREI} = -311{,}957 \pm 1{,}085{,}873\text{ kW}\cdot\text{h}$ (95% Student-$t$ CI $[-1{,}660{,}247, +1{,}036{,}332]\text{ kW}\cdot\text{h}$, $t(4)=-0.64, p=0.5556$, crossing zero; 3 of 5 seeds exhibit higher point costs with alignment); boundary slice $\Delta\text{PSREI} = +15{,}261 \pm 27{,}504\text{ kW}\cdot\text{h}$ (95% CI $[-18{,}890, +49{,}412]\text{ kW}\cdot\text{h}$, $t(4)=1.24, p=0.2825$, crossing zero).
     - **LAYER C ? Transition-Window Localization (INDEPENDENTLY SUPPORTED):** Reserve-screening savings concentrate mechanistically within dynamic transition windows ($\pm 3$ steps around Region 2/3 boundary crossings), which account for $48.4\%$ of total reserve cost reduction ($p < 0.001$).
     - *Anti-Conflation Rule*: We never compress A + B + C into a claim that "privileged supervision causes reserve savings."
2. **Scope of the Matched Ablation:**
   - The matched $\lambda_{\mathrm{align}}$ ablation isolates the contribution of regime-label supervision conditional on the same privileged training inputs; it does not isolate the full value of training-time pitch access. Both variants received pitch in historical training sequences ($x_{\text{hist}}$) and had pitch strictly zero-masked at validation/test deployment.
3. **Honest Reporting of Null/Cross-Zero Findings:**
   - We explicitly state in Section IV-E, Table III, and Supplementary Table A6c that the reserve cost difference includes zero at 95% confidence. We never claim that offline privileged supervision is "the necessary mechanism" or that $-311{,}957\text{ kW}\cdot\text{h}$ is a confirmed operational benefit.
4. **Transparent Deployment Setting:**
   - The present study assumes historical blade-pitch availability during offline training, followed by pitch withholding at deployment. Performance in settings where pitch was never historically recorded remains untested.

---

---

### Section 4: Final Adversarial Reviewer Attack Defense (Q1--Q8 Matrix)

For each anticipated challenge, we provide: **CLAIM**, **EVIDENCE**, **LIMITATION**, and **SAFE MANUSCRIPT WORDING**.

#### Q1: Is the paper fundamentally dependent on one site?
- **CLAIM**: Yes, the empirical discovery and mechanistic identification of consequence-driven latent operating-boundary recovery are fundamentally established on the 134-turbine WTB complex. Five random training seeds (201--205) quantify training stochasticity, not independent physical replications.
- **EVIDENCE**: WTB 245-day 10-minute SCADA archive ($T=35{,}280, N=134, F=11$, KDD Cup 2022 benchmark) under 180/30/35-day chronological splits (`artifacts/cache_strictmask_trainweights/wtb_245d`, `artifacts/fixed_forecast_residuals.npz`).
- **LIMITATION**: The learned neural parameters are site-specific and cannot be transferred zero-shot to external wind plants with different turbine models, power curves, or layouts.
- **SAFE MANUSCRIPT WORDING**: *“The primary aerodynamic mechanism is identified on the 134-turbine WTB benchmark complex, where five random seeds evaluate training stochasticity rather than independent physical environments. External sites probe transferability and delineate site-dependent boundary conditions rather than serving as uniform replications.”*

#### Q2: Do external sites reproduce the mechanism or merely bound transferability?
- **CLAIM**: External sites do not provide uniform replication evidence; their observed effects are heterogeneous and primarily serve as external-validity boundary probes that establish where spatial graph modeling adds value and where it fails.
- **EVIDENCE**: `docs/SITE_MECHANISM_BOUNDARY_TABLE.md` and `artifacts/clean_evidence_v2/risk_layer_benchmark/cross_farm_generalization_table.csv`:
  - *Penmanshiel (14 operational turbines, WT01--WT15 excluding WT03)*: POSITIVE. STGQ saves $-2.14\text{M kW}\cdot\text{h}$ over global quantiles (95% CI $[-3.25\text{M}, -1.36\text{M}]$, $p < 0.05$). Table IV compares STGQ against an unconditioned global baseline rather than matched external no-graph ablations, so external gains are not causally attributed to wake modeling alone.
  - *Kelmarsh (6 turbines)*: NEUTRAL. Minimal spatial wake redundancy across a 6-turbine micro-array yields a neutral difference of $-40\text{k kW}\cdot\text{h}$ (95% CI $[-204\text{k}, +172\text{k}]$, $p=0.85$).
  - *La Haute Borne (4 turbines)*: NEGATIVE. Micro-farm graph convolutions overfit local terrain noise, incurring a $+43\text{k kW}\cdot\text{h}$ penalty (annual) and $+1.01\text{M kW}\cdot\text{h}$ (quarterly rolling).
  - *Directional Asymmetry*: Kelmarsh $\to$ Penmanshiel NMI $0.77$ vs. Penmanshiel $\to$ Kelmarsh NMI $0.34$.
- **LIMITATION**: External farm tests do not demonstrate automatic cross-site generalization. Cross-site STGQ effects relative to the global quantile baseline are heterogeneous; the observed pattern is consistent with exploitable spatial redundancy as a possible moderator, while turbine count alone does not explain the variation.
- **SAFE MANUSCRIPT WORDING**: *“Cross-site STGQ effects relative to the global quantile baseline are heterogeneous (Penmanshiel: positive; Kelmarsh: statistically neutral; La Haute Borne: negative overfitting boundary). The observed pattern is consistent with exploitable spatial redundancy as a possible moderator, while turbine count alone does not explain the variation. Because Table IV lacks matched external no-graph ablations, wake modeling is not causally isolated as the sole mechanism for external gains.”*

#### Q3: Are 14.98% and 16.23% genuinely different experimental scopes?
- **CLAIM**: Yes. Both numbers are mathematically exact, reproducible values computed from the canonical baseline artifact (`artifacts/direct_quantile_baselines_summary.csv`), but represent two distinct operational degradation scenarios for `B3_Quantile_GBDT` at $h=6$.
- **EVIDENCE**: Forensic trace in `docs/GBDT_METRIC_PROVENANCE.md` from `scripts/run_direct_quantile_baselines.py`:
  - `clean` scenario ($\tau=0$, all 11 SCADA channels observed): $\text{Violation Rate} = 0.162345 \to \mathbf{16.23\%}$ ($\text{PSREI} = 15,665,275\text{ kW}\cdot\text{h}$).
  - `pitch_withheld` scenario ($\tau=0$, blade pitch channels $P_{\text{ab}}$ masked): $\text{Violation Rate} = 0.149771 \to \mathbf{14.98\%}$ ($\text{PSREI} = 14,965,626\text{ kW}\cdot\text{h}$).
  - Both values breach the nominal 10% Newsvendor violation target ($q^* = 0.90$ induced by $\rho=10$; $16.23\% > 10.0\%$ and $14.98\% > 10.0\%$).
- **LIMITATION**: Earlier textual summaries quoted $16.23\%$ while discussing the pitch-withheld regime; this was a typographical scenario conflation in draft narrative, now reconciled everywhere.
- **SAFE MANUSCRIPT WORDING**: *“Shallow quantile tree baselines (B3 GBDT) breach the nominal 10% Newsvendor violation target ($q^* = 0.90$) at $h=6$, surging to a $16.23\%$ violation rate under clean telemetry and $14.98\%$ when blade pitch is withheld (exceeding the nominal 10% target in both conditions).”*

#### Q4: Does posterior conditioning beat a strong wind-speed-conditioned quantile baseline overall?
- **CLAIM**: No. On the full operational test population, posterior conditioning does NOT outperform a strong empirical wind-speed-binned quantile baseline; it performs approximately $523\text{k kW}\cdot\text{h}$ worse (canonically defined as $\Delta L = L_{\text{posterior}} - L_{\text{wspd}} = +523{,}044\text{ kW}\cdot\text{h}$ penalty, $p=0.85$).
- **EVIDENCE**: Evaluated across 5 seeds on 385,205 valid test cells in `artifacts/strong_baseline_closure_summary.csv`:
  - Policy B (Wind-Speed Bins): $\text{PSREI} = \mathbf{13,784,320} \pm 1,438,833\text{ kW}\cdot\text{h}$ (8.79% violation).
  - Policy C (Posterior-Conditioned): $\text{PSREI} = 14,307,364 \pm 1,787,258\text{ kW}\cdot\text{h}$ (9.08% violation).
  - Paired difference: $\Delta L = L_{\text{posterior}} - L_{\text{wspd}} = \mathbf{+523,044\text{ kW}\cdot\text{h}}$ ($p=0.85$, 95% CI $[+233\text{k}, +830\text{k}]$).
- **LIMITATION**: Machine learning models cannot beat direct observable physical wind-speed conditioning across the broad plant-wide envelope. In Region 2 (MPPT) where power obeys $P \propto v^3$, direct wind-speed binning is the minimum sufficient operational policy.
- **SAFE MANUSCRIPT WORDING**: *“The learned latent-boundary posterior does not improve plant-wide reserve screening over a strong wind-speed-conditioned quantile baseline (canonically defined as $\Delta L = L_{\text{posterior}} - L_{\text{wspd}} = +523{,}044\text{ kW}\cdot\text{h}$ penalty, $p=0.85$). The relative risk-cost trade-off becomes materially more favorable near operating transitions.”*

#### Q5: If not, exactly where does posterior information add value?
- **CLAIM**: The relative risk-cost trade-off becomes materially more favorable near operating transitions ($\pm 3$ steps of boundary switching): posterior conditioning selectively reduces violation and shortage exposure near transitions, but this hedge remains more expensive under $\rho=10$ than wind-speed-binned quantile calibration ($\Delta = +112{,}704\text{ kW}\cdot\text{h}$, due to $+149{,}092\text{ kW}\cdot\text{h}$ higher reserve procurement).
- **EVIDENCE**: Slicing analysis in `docs/STRONG_BASELINE_CLOSURE.md`:
  - In Steady Windows ($63.74\%$ of test time): Posterior incurs a significant surrogate cost penalty of $+410,217\text{ kW}\cdot\text{h}$ ($p = 0.002$) over wind-speed bins.
  - In Transition Windows ($36.26\%$ of test time): The posterior penalty is compressed by nearly 75% to $+112,827\text{ kW}\cdot\text{h}$. Posterior achieves a lower violation rate ($7.24\%$ vs. $8.36\%$) and reduces unhedged shortage energy ($86,592\text{ kW}\cdot\text{h}$ vs. $90,231\text{ kW}\cdot\text{h}$) compared to wind-speed bins.
  - Paired day-level cluster bootstrap over 35 observed test days confirms a statistically significant heterogeneity interaction: $\Delta_{\text{trans}} - \Delta_{\text{steady}} = \mathbf{-296,123\text{ kW}\cdot\text{h}}$ ($p < 0.005$).
- **LIMITATION**: While the posterior provides superior risk hedging in transition windows (cutting shortage by $3.6\text{k kWh}$ and violations to $7.24\%$), doing so requires procuring more reserve headroom ($3.57\text{M}$ vs. $3.42\text{M kWh}$), so it does not yield net PSREI cost reduction under $\rho=10$.
- **SAFE MANUSCRIPT WORDING**: *“The relative risk-cost trade-off becomes materially more favorable near operating transitions: posterior conditioning selectively reduces violation ($7.24\%$ vs. $8.36\%$) and shortage exposure ($86.6\text{k}$ vs. $90.2\text{k kW}\cdot\text{h}$) near transitions, but this hedge remains more expensive under $\rho=10$ than wind-speed-binned quantile calibration. The significant interaction ($\Delta_{\text{trans}} - \Delta_{\text{steady}} = -296{,}123\text{ kW}\cdot\text{h}, p < 0.005$) establishes heterogeneity of the relative cost gap rather than a positive posterior cost advantage.”*

#### Q6: Could the 48.4% transition result merely reflect higher underlying losses?
- **CLAIM**: Yes, if evaluated uncritically. Transition windows naturally exhibit larger point forecast errors and higher baseline losses. However, formal interaction testing proves that the posterior's performance profile shifts specifically in transition windows beyond mere proportional loss scaling.
- **EVIDENCE**: Transition windows account for $36.26\%$ of observations, $33.0\%$ of global quantile loss ($5.33\text{M} / 16.13\text{M}$), and capture $48.38\%$ of savings vs unconditioned global quantiles ($+892,535\text{ kW}\cdot\text{h}$ of $+1,825,410\text{ kW}\cdot\text{h}$). Against wind-speed bins, the interaction contrast $\Delta_{\text{trans}} - \Delta_{\text{steady}} = -296,123\text{ kW}\cdot\text{h}$ ($p < 0.005$) demonstrates a structural model performance shift that cannot be explained by uniform error inflation.
- **LIMITATION**: We explicitly concede that the raw "$48.4\%$ of total savings" metric is computed relative to an unconditioned global quantile, and does not prove that posterior conditioning outperforms wind-speed conditioning in transition windows.
- **SAFE MANUSCRIPT WORDING**: *“Transition windows are not merely high-loss regions; formal interaction contrasts confirm they are the regions where secondary consequence signals alter tail risk allocations. However, we caution that raw transition savings percentages ($48.4\%$) reflect both underlying loss concentration and model sensitivity; relative to strong wind-speed binning, the posterior acts as a risk-hedging mechanism rather than a cost-reducing mechanism.”*

#### Q7: Does a deployable hybrid policy improve the full-population objective?
- **CLAIM**: No. A deployable hybrid policy achieves parity with wind-speed binning, but does not achieve a statistically significant improvement on the plant-wide objective ($+4,834\text{ kW}\cdot\text{h}$ difference, $p > 0.40$). The deployable hybrid policy remains statistically equivalent to wind-speed binning and must NOT be presented as an improvement.
- **EVIDENCE**: Tested in `scripts/test_strong_baseline_closure.py` across 5 seeds:
  - Policy B (Wind-Speed Bins): $\text{PSREI} = \mathbf{13,784,320} \pm 1,438,833\text{ kW}\cdot\text{h}$.
  - Policy D (Validation-Frozen Deployable Hybrid): $\text{PSREI} = 13,789,154 \pm 1,434,721\text{ kW}\cdot\text{h}$.
  - Policy D10 (Pre-specified Band $|v-10.5| \le 1.0\text{ m/s}$): $\text{PSREI} = 13,801,696 \pm 1,438,458\text{ kW}\cdot\text{h}$.
- **LIMITATION**: Because transition events comprise only $36.3\%$ of the time series and wind-speed binning is already well-calibrated, the switching overhead and conservative tail margin of the posterior prevent the hybrid policy from beating pure wind-speed binning plant-wide.
- **SAFE MANUSCRIPT WORDING**: *“A deployable hybrid policy that switches between wind-speed binning in steady states and posterior conditioning near boundary transitions matches wind-speed binning plant-wide ($13.79\text{M}$ vs. $13.78\text{M kW}\cdot\text{h}$, $p > 0.40$), but does not improve the overall objective. Wind-speed-binned quantile calibration therefore remains the operational minimum sufficient model for plant-wide reserve sizing.”*

#### Q8: What remains novel after Zhao et al. 2026 already introduced physics-aware dynamic-graph MoE forecasting?
- **CLAIM**: Our contribution does not lie in architectural novelty (graph MoE or physics-guided neural networks). Zhao et al. (IJEPES 2026) already explore this architectural family for symmetric point forecasting. Our contribution lies in an information-theoretic and operational decision question: establishing reliability boundaries under telemetry degradation, proving when recalibration suffices, diagnosing latent operating states from consequence SCADA channels, and testing whether recovered states alter asymmetric reserve-risk screening.
- **EVIDENCE**: Concession of architectural neighborhood: Chenkai Zhao et al., *Int. J. Electr. Power Energy Syst.*, Vol. 176, 111769, 2026. Falsification of MoE necessity: In our factorial ablations (Table~\ref{tab:h6-benchmark}), unrouted Dense GNNs achieve statistical parity with Routed MoE ($991\text{k}$ vs. $959\text{k kW}\cdot\text{h}$ on boundary slice, $p = 0.380$; $15.47\text{M}$ vs. $15.77\text{M kW}\cdot\text{h}$ full population). MoE routing is explicitly shown to be non-essential. Consequence mechanism identification: Proving that active power curvature and variance ($C2$), rather than thermal ($C4$) or wake-only ($C3$) signals, recover the latent boundary under pitch withholding (`artifacts/channel_consequence_ablations.csv`).
- **LIMITATION**: We explicitly disclaim proposing a novel neural network architecture, novel graph convolution, or novel mixture-of-experts routing layer.
- **SAFE MANUSCRIPT WORDING**: *“Recent physics-aware dynamic-graph MoE models, such as Zhao et al. (2026), investigate whether architectural coupling of spatial graphs, physical guidance, and expert routing improves wind-power forecasting accuracy. We instead treat these components as diagnostic comparators and ask an information-and-decision question: when critical aerodynamic states become unobservable due to telemetry degradation, what information remains recoverable from secondary consequence channels, when is simple conditional recalibration sufficient without neural learning, and whether the recovered latent state alters asymmetric reserve-shortfall decisions.”*

---

### Suggested Author Response Checklist for Rebuttal Stage

- [x] Maintain objective, polite, and restrained IEEE PES technical tone.
- [x] Directly acknowledge reviewer validity before providing data-backed clarification.
- [x] Quote exact line numbers, table labels, and equations from the reconstructed manuscript.
- [x] Provide exact numerical delta and 95% bootstrap confidence intervals for all empirical claims.
- [x] Cross-reference Supplementary Material tables (A1--A14) for extended proofs and ablations.
- [x] Rely on `docs/GBDT_METRIC_PROVENANCE.md` for exact GBDT scenario separation (clean 16.23% vs withheld 14.98%).
- [x] Rely on `docs/STRONG_BASELINE_CLOSURE.md` for exact wind-speed binned vs posterior contrasts.
- [x] Rely on `docs/SITE_MECHANISM_BOUNDARY_TABLE.md` for site-specific external validity probes.
