# IEEE Transactions on Sustainable Energy (TSTE)
# Comprehensive Adversarial Peer Review Attack Simulation & Defensive Hardening

**Date:** 2026-09-23  
**Target Venue:** *IEEE Transactions on Sustainable Energy* (TSTE) — Regular Paper (10-Page Standard Limit)  
**Manuscript Title:** When Aerodynamic States Become Latent: Reserve-Risk Screening under Degraded Wind-Turbine SCADA Telemetry  
**Authors:** Junyu Li and Juntao Du (Anhui University of Finance and Economics)  
**Governing Thesis:**  
> *"The value of model complexity is governed by information sufficiency, while state recoverability and decision superiority remain fundamentally non-equivalent."*

**Evaluated Artifacts:**  
- Main Manuscript: `paper_tste_ieee.md` (10.0 pages compiled, 0 overfull hboxes)  
- Supplementary Material: `paper_tste_supplementary.md` (44 pages compiled, 0 overfull hboxes, explicit `S3.`, `S4.`, `S5.` navigation)  
- Standalone Submission Package: `standalone_ieee_package/main.tex` and `main.pdf`  
- Evidentiary & Control Base: `docs/SCIENTIFIC_CONTRACT.md`, `docs/MATCHED_BUDGET_DECISIVE_REPORT.md`, `docs/CLAIM_PRECISION_PATCH_REPORT.md`, `artifacts/strong_baseline_closure_summary.csv`, `artifacts/matched_budget/exact_matched_budget_frontier.csv`  

---

## 1. Panel Configuration & Defense Maturity Taxonomy

To provide a realistic and uncompromising pre-submission stress test, we simulate three expert reviewer roles covering Power System Operations, Probabilistic Forecasting, and SCADA Turbine Controls.

Rather than labeling defenses with unreflective confidence, every challenge is categorized under a strict **4-tier defense maturity taxonomy**:
1. **Resolved by evidence**: Supported by direct numerical data, seed-level ablations, bootstrap confidence intervals, or physical artifact traces.
2. **Resolved by scope definition**: Bounded by formal mathematical or operational exclusions (e.g., Level-2 market clearing, intra-plant electrical topology, or uncurtailed aerodynamic equilibrium) clearly documented in the manuscript.
3. **Partially resolved**: Supported by strong empirical or operational justification, but retains residual methodological assumptions that could be debated by specialists.
4. **Residual reviewer risk**: An acknowledged practical limitation or operational domain where empirical field surveys or external validation remain open, requiring defensive author vigilance.

---

## 2. Adversarial Defense Matrix (12 Core Challenges)

| # | Challenge Summary | Primary Reviewer Role | Manuscript Location | Repository Evidence / Artifact | Defense Posture & Maturity Tier |
|:---:|:---|:---:|:---|:---|:---:|
| **1.1** | Level-1 surrogate vs. Level-2 AC-OPF | Rev 1 (Power Systems) | Sec. I, Sec. II-A, Sec. V | `docs/SCIENTIFIC_CONTRACT.md` | **Resolved by scope definition**<br>Strictly bounded to plant EMS local reserve screening; bulk grid AC-OPF/SCUC and LMP clearing explicitly disclaimed. |
| **1.2** | Penalty ratio $\rho=10$ vs. general $\rho \in [1, 100]$ | Rev 1 (Power Systems) | Sec. IV-C, Table A11m | `artifacts/matched_budget/reoptimized_rho_sensitivity.csv` | **Resolved by evidence**<br>Frozen break-even $\rho_{\text{break}} \approx 40.89$; dynamic re-optimization $\rho \in [2, 100]$ shows no economic crossover for $\rho \ge 5$. |
| **1.3** | PCC portfolio smoothing vs. turbine screening | Rev 1 (Power Systems) | Sec. IV-D, Supp. Sec. S5, Table A11f | `artifacts/pcc_bus_level_reserve_allocation.csv` | **Resolved by evidence**<br>134-turbine portfolio cancels high-frequency turbulence, but spatial coherence of ramp fronts preserves transition risk. |
| **1.4** | Intra-plant collector network congestion | Rev 1 (Power Systems) | Sec. II-A, Sec. V | `docs/SCIENTIFIC_CONTRACT.md` | **Resolved by scope definition**<br>Intra-plant electrical topology and cable thermal limits are explicitly scoped to the local SCADA supervisory controller. |
| **2.1** | MoE routing provides no advantage ($p=0.380$) | Rev 2 (Forecasting / ML) | Sec. IV-D, Supp. Sec. S3, Table A1, A3 | `artifacts/factorial_boundary_ablation_summary.csv` | **Resolved by evidence**<br>Unconstrained MoE (zero auxiliary losses) also achieves parity ($p=0.380$); routing entropy collapses to uniform blending. |
| **2.2** | Time-series baseline receptive fields ($H=12$) | Rev 2 (Forecasting / ML) | Sec. II-B, Supp. Sec. S3, Table A11 | `docs/INFORMATION_SET_CONTRACT.md` | **Partially resolved**<br>Strictly matched to operational dispatch horizon; missing state is not solved by long lookback, though Transformer purists may raise windowing choices. |
| **2.3** | Graph neural networks vs. physical wake advection | Rev 2 (Forecasting / ML) | Sec. IV-D, Table VI, Supp. Table A7b, A8 | `artifacts/clean_evidence_v2/.../cross_farm_generalization_table.csv` | **Resolved by evidence**<br>Wake graph ($C3$) has weak identifiability; multi-site tests prove GNN gains require spatial redundancy and fail in small arrays (Kelmarsh $p=0.85$, LHB). |
| **2.4** | Why direct wind-speed binning beats ML plant-wide | Rev 2 (Forecasting / ML) | Sec. IV-A, Sec. IV-C, Sec. V | `artifacts/strong_baseline_closure_summary.csv` | **Resolved by evidence**<br>Empirically proven plant-wide ($13.78\text{M}$ vs $14.31\text{M kWh}$) and in steady state ($p=0.002$); matched-budget analysis proves no allocation advantage. |
| **3.1** | Synthetic latency models (10–30 min vs. 60 min) | Rev 3 (SCADA Physics) | Sec. I, Sec. IV-B, Sec. V | `paper_tste_ieee.md` (lines 411, 442) | **Resolved by scope definition**<br>10–30 min represents realistic buffer stalls (non-neural recalibration absorbs 55.3%); 60 min is strictly framed as a reliability breakdown stress test. |
| **3.2** | Blade pitch withholding operational reality | Rev 3 (SCADA Physics) | Sec. I, Sec. III, Sec. IV-C | `docs/CANONICAL_RESEARCH_QUESTION.md` | **Residual reviewer risk**<br>Supported by industry operational rationale (OEM data barriers, aggregator register limits, encoder failure), but lacks empirical fleet-wide survey data. |
| **3.3** | Active power ($P_t$) consequence contamination | Rev 3 (SCADA Physics) | Sec. II-B, Sec. IV-C, Sec. V | `docs/ACTIVE_POWER_IDENTIFIABILITY_AUDIT.md` | **Resolved by scope definition**<br>Audited on uncurtailed aerodynamic operation ($\text{AUROC} = 0.988$); AGC curtailment and derating are explicitly acknowledged as operational boundaries. |
| **3.4** | Offline privileged training assumption | Rev 3 (SCADA Physics) | Sec. IV-C, Sec. V, Sec. VII, Table A6c | `docs/PRIVILEGED_SUPERVISION_ABLATION.md` | **Partially resolved**<br>Fully disclosed; ablation proves representation gain without downstream decision significance; applicability to zero-historical-pitch fleets remains untested. |

---

## 3. In-Depth Defense Positions by Reviewer

### Reviewer 1: Power System Operations & Reserve Economics

#### 1.1 Level-1 Pre-Dispatch Surrogate vs. Bulk-Grid Level-2 AC-OPF
- **Reviewer Challenge:** *"The paper evaluates an isolated, single-period reserve-screening surrogate ($C = R + \rho U$). In actual power systems, operating reserves are co-optimized with energy in a security-constrained economic dispatch (SCED) with AC/DC power flow constraints and locational marginal pricing (LMP). Why should grid operators care about an unconstrained Level-1 reserve surrogate?"*
- **Hardened Defense (Resolved by scope definition):**
  - The manuscript explicitly positions this work at the **wind plant Energy Management System (EMS) / aggregator interface** (Section I, lines 88–92; Section II-A, lines 130–145).
  - Bulk transmission system operators (ISOs/RTOs) require renewable plants to submit qualified reserve capacities and availability bounds. Sizing local reserves under telemetry latency is an operational task performed locally before market offer submission.
  - Section V (Scope Condition 2, line 452) explicitly disclaims bulk transmission clearing:
    > *"Bulk transmission congestion, locational marginal pricing, and multi-period ramping constraints are governed at Level 2 by the system operator; our formulation targets local reserve qualification at the plant aggregator interface."*

#### 1.2 Penalty Ratio Sensitivity ($\rho=10$ vs. $\rho \in [1, 100]$)
- **Reviewer Challenge:** *"The choice of $\rho=10$ ($q^*=0.90$) is arbitrary. Real balancing market penalties vary from mild imbalance tariffs ($\rho \approx 2\text{--}4$) to Value of Lost Load spikes ($\rho > 100$). Why should conclusions hold outside $\rho=10$?"*
- **Hardened Defense (Resolved by evidence):**
  - Evaluated across the full continuum $\rho \in [1, 100]$ in Supplementary Table A11m and `artifacts/matched_budget/reoptimized_rho_sensitivity.csv`:
    1. *Frozen Policy Break-Even Analysis:* $\rho_{\text{break}} \approx 40.89$ (Section IV-C, line 428). Below 40.89, wind-speed binning is strictly superior; above 40.89, posterior wins only because its massive volume procurement ($+149\text{k kWh}$) offsets high shortage costs.
    2. *Re-Optimized Policy Sweep across $\rho \in [2, 100]$:* When both models re-optimize $q^*(\rho) = 1 - 1/\rho$ on validation data, wind-speed binning is superior for all $\rho \ge 5$ (baseline advantage: $+22\text{k}$ at $\rho=5$, $+112\text{k}$ at $\rho=10$, $+736\text{k}$ at $\rho=40$, and $+998\text{k kW}\cdot\text{h}$ at $\rho=100$).
  - High conditional tail variance under telemetry degradation forces the posterior to over-procure reserve ($+1.10\text{M kWh}$ at $\rho=100$) with negligible shortage reduction ($-1{,}046\text{ kWh}$). **No economic crossover exists for $\rho \ge 5$ under re-optimized policy selection.**

#### 1.3 Fleet-Wide Portfolio Smoothing at PCC vs. Turbine-Level Screening
- **Reviewer Challenge:** *"At the Point of Common Coupling (PCC), turbulence and turbine-level adjustments average out across 134 turbines. Does PCC aggregation wash out the boundary effect?"*
- **Hardened Defense (Resolved by evidence):**
  - Audited in Supplementary Section S5 and Table A11f (`artifacts/pcc_bus_level_reserve_allocation.csv`):
    1. *High-frequency turbulence cancellation:* Across prevailing stationary operation, spatial smoothing reduces aggregate variance.
    2. *Coherent ramp front preservation:* Aerodynamic transition events (mesoscale gust fronts crossing rated speed $v \approx 10.5\text{ m/s}$) are spatially coherent across the array. Turbines transition collectively.
  - In Table A11f, under transitional conditions, PCC-aggregated posterior conditioning achieves $-2.32\text{M kWh}$ relative to unconditioned global quantiles, but matches conditioned physical baselines within bootstrap uncertainty (CI $[-6.07\text{M}, +1.73\text{M}]$, $p=0.312$). Spatial smoothing does not eliminate transition risk, but reinforces that simple conditional models remain sufficient.

#### 1.4 Intra-Plant Collector Network Congestion
- **Reviewer Challenge:** *"Linear reserve aggregation ($\sum r_{i,t}$) ignores thermal MVA limits on 33 kV collector strings. How does local screening account for collector bottlenecks?"*
- **Hardened Defense (Resolved by scope definition):**
  - Section V (Scope Condition 2) explicitly states that intra-plant collector circuit power flow and thermal constraints are adjudicated downstream by the plant supervisory SCADA controller, which uses turbine-level reserve headroom bounds ($r_{i,t} \le P_{i,\text{rated}} - \hat{y}_{i,t}$) to prevent cable overloads.

---

### Reviewer 2: Probabilistic Forecasting & Machine Learning Baselines

#### 2.1 MoE Routing Parity ($p=0.380$)
- **Reviewer Challenge:** *"Did auxiliary alignment losses ($\mathcal{L}_{\text{align}}, \mathcal{L}_{\text{force}}$) over-regularize the Mixture-of-Experts router and artificially suppress its data-driven clustering ability?"*
- **Hardened Defense (Resolved by evidence):**
  - Evaluated in Supplementary Table A1, Table A3, and Table A4:
    1. *Unconstrained MoE (zero auxiliary losses)* also failed to beat the Dense baseline ($15.77\text{M}$ vs. $15.47\text{M kW}\cdot\text{h}$ full population; $991\text{k}$ vs. $959\text{k kW}\cdot\text{h}$ on boundary slice, $p=0.380$).
    2. *Routing Entropy Diagnostics (Table A11e):* Soft gating entropy collapses near continuous aerodynamic boundaries, resulting in uniform blending across experts. The lack of MoE advantage is a structural property of continuous aerodynamic transitions, not a loss-tuning artifact.

#### 2.2 Time-Series Baseline Receptive Fields ($H=12$)
- **Reviewer Challenge:** *"Time-series foundation models (PatchTST, iTransformer) require long lookbacks ($L \ge 96/336$). Was $H=12$ (2 hours) insufficient?"*
- **Hardened Defense (Partially resolved):**
  - Operational buffer limits dictate that SCADA autoregression operates over short dispatch horizons (10–60 min). Beyond 2–4 hours, NWP meteorological updates dominate.
  - In Supplementary Section S3 (Table A11), tuning with expanded lookback ($H=36$) confirmed that missing pitch is an unobservable state problem, not a sequence length deficiency.
  - *Residual consideration:* Transformer purists may argue about standard benchmark defaults, but our information-set contract strictly enforces operational deployment realism.

#### 2.3 Graph Neural Networks vs. Physical Wake Advection
- **Reviewer Challenge:** *"Wake advection is a physical transport process with delay $d/u$. Does the spatial GNN learn physics or merely perform spatial smoothing?"*
- **Hardened Defense (Resolved by evidence):**
  - Channel ablations (Supplementary Table A7b) prove wake graph topology ($C3$) alone provides weak boundary identifiability ($\text{AUROC} \approx 0.62$, recall $0.14$), whereas contemporaneous active power ($C2$) achieves $\text{AUROC} = 0.988$.
  - Multi-site tests (Supplementary Table A8) show GNN gains disappear where spatial wake redundancy is minimal (Kelmarsh 6-turbine array: bootstrap difference $-40\text{k kW}\cdot\text{h}$, $p=0.85$; LHB 4-turbine array: negative transfer penalty). The manuscript explicitly concludes that GNNs act as spatial redundancy aggregators, not universal wake simulators.

#### 2.4 Dominance of Direct Wind-Speed Quantile Binning Plant-Wide
- **Reviewer Challenge:** *"If a simple 10-bin empirical quantile on wind speed beats all complex ML models plant-wide ($13.78\text{M}$ vs. $14.31\text{M kW}\cdot\text{h}$), is machine learning unnecessary for wind power reserve estimation?"*
- **Hardened Defense (Resolved by evidence — Refined Wording):**
  > *"The strong performance of wind-speed-conditioned quantiles is not a failure of the study but an important boundary result. Under sufficiently informative observable telemetry, a simple conditional policy is already decision-sufficient and additional model complexity is unnecessary. When critical control-state telemetry is unavailable, observable consequence signals still retain information about the latent operating regime, and learned representations provide one mechanism for recovering that information. However, our matched-budget analysis shows that improved state recovery does not automatically translate into superior reserve allocation. The contribution is therefore not universal AI superiority, but an empirically identified hierarchy of model sufficiency across telemetry regimes."*
  - The value of model complexity is governed by information sufficiency, while state recoverability and decision superiority remain fundamentally non-equivalent.

---

### Reviewer 3: SCADA Physical Telemetry & Turbine Controls

#### 3.1 SCADA Latency Models (10–30 min vs. 60 min)
- **Reviewer Challenge:** *"Is a 60-minute latency an artificial strawman to manufacture an ML failure case?"*
- **Hardened Defense (Resolved by scope definition):**
  - The paper explicitly separates operational buffer stalls (10–30 min, common in backhaul congestion) from the 60-min contingency stress test (Section I, Section IV-B, Section V).
  - For operational latencies ($\tau \in [10, 30]\text{ min}$), non-neural recalibration absorbs $55.3\%$ of the shortage loss without updating network weights. The 60-min latency is explicitly defined as a reliability breakdown boundary, not standard operation.

#### 3.2 Blade Pitch Withholding Operational Reality
- **Reviewer Challenge:** *"Why would blade pitch ever be withheld in real operations? Isn't this an artificial academic construct?"*
- **Hardened Defense (Residual reviewer risk):**
  - Grounded in well-established operational realities:
    1. *Multi-OEM Aggregator Boundaries:* Turbine OEMs treat high-speed pitch control registers as proprietary trade secrets, exporting only active power, reactive power, and wind speed to third-party aggregators.
    2. *Hardware Failure:* Optical encoders and slip rings experience severe failure and drift in offshore and cold climates.
    3. *Legacy SCADA Protocols:* Modbus RTU / IEC 60870-5-104 bandwidth bottlenecks prioritize revenue metering over auxiliary logs.
  - *Residual reviewer risk:* While operationally sound and widely recognized by field engineers, the paper does not cite an industry-wide empirical survey quantifying pitch omission rates. We maintain an explicit scope definition rather than claiming universal prevalence.

#### 3.3 Active Power ($P_t$) Consequence Contamination
- **Reviewer Challenge:** *"Active power is contaminated by AGC curtailment, wake turbulence, and yaw error. How can $P_t$ recover the boundary under curtailment?"*
- **Hardened Defense (Resolved by scope definition):**
  - SCADA data were filtered for normal operating conditions (`status == 1`).
  - Section V (Scope Condition 3, line 454) explicitly scopes out active power curtailment:
    > *"Consequence-based latent-state recovery assumes normal aerodynamic operating regimes where electromechanical output reflects unconstrained control equilibrium. In operational environments subject to active AGC power curtailment, wake-induced derating, or severe blade icing, active power signals become decoupled from aerodynamic pitch states, requiring explicit curtailment flag conditioning."*

#### 3.4 Offline Privileged Training Assumption
- **Reviewer Challenge:** *"If historical pitch was available during offline training, why not calibrate a physical model? What happens if pitch was never recorded?"*
- **Hardened Defense (Partially resolved):**
  - Matched ablation ($\lambda_{\text{align}}=5000$ vs $0$) shows privileged supervision improves latent clustering ($\Delta\text{NMI} = +0.579$) but yields a downstream decision delta crossing zero ($-311\text{k kW}\cdot\text{h}$, 95% CI $[-1.31\text{M}, +0.34\text{M}]$).
  - The manuscript transparently discloses that settings where pitch was *never* recorded remain untested (Section IV-C, Section VII).

---

## 4. Final Verification Gate Status

```text
========================================================================
[1] python scripts/verify_final_pdf_integrity.py      -> Exit Code: 0 (PASS)
[2] python scripts/verify_decisive_gate.py            -> Exit Code: 0 (PASS)
[3] python scripts/verify_tste_number_consistency.py   -> Exit Code: 0 (PASS)
[4] python scripts/verify_scientific_claim_gate.py     -> Exit Code: 0 (PASS)
[5] pytest tests/test_matched_budget_accounting.py    -> Exit Code: 0 (5/5 PASS)
[6] python .agents/scripts/verify_gate.py             -> Exit Code: 0 (PASS)
========================================================================
```
