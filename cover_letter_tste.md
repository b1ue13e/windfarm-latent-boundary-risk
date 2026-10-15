> AUDIT HOLD (2026-10-15): Not submission-ready. Historical claims below are subject to the current correction/withdrawal register and full raw-data replay.

# IEEE Transactions on Sustainable Energy
## Submission Cover Letter & Executive Summary

**Date:** March 2026  
**To:** Editor-in-Chief, *IEEE Transactions on Sustainable Energy*  
**From:** Juntao Du (Corresponding Author), on behalf of the authors  
**Affiliation:** School of Statistics and Applied Mathematics, Anhui University of Finance and Economics, Bengbu 233030, China  
**Contact:** `dujuntao@aufe.edu.cn`  

**Manuscript Title:**  
*When Aerodynamic States Become Latent: Reserve-Risk Screening under Degraded Wind-Turbine SCADA Telemetry*

**Authors:**  
Junyu Li and Juntao Du

---

### Part I: Formal Submission Statement

Dear Editor-in-Chief and Editorial Board,

We submit our original research manuscript entitled **"When Aerodynamic States Become Latent: Reserve-Risk Screening under Degraded Wind-Turbine SCADA Telemetry"** for consideration as a Regular Paper in *IEEE Transactions on Sustainable Energy* (TSTE).

The manuscript complies with the strict IEEE double-column 10-page length requirement (the main paper is exactly 10.0 pages including all text, equations, tables, figures, and 38 references). A comprehensive 44-page Supplementary Material is provided to support reproducible verification, extended multi-regime phase scans, and mathematical derivations without burdening the main text.

#### Compliance & Declarations:
1. **Originality & Sole Submission:** This manuscript represents original work that has not been published previously and is not currently under peer review elsewhere.
2. **Author Approval:** All listed authors have reviewed, contributed to, and approved the final manuscript.
3. **Data Availability & Ethics:** The study evaluates publicly available commercial SCADA archives (134-turbine WTB benchmark, ENGIE La Haute Borne, Kelmarsh, and Penmanshiel). No human or animal subjects were involved. Full reproduction scripts, configuration files, and frozen validation checkpoints are documented in the manuscript.
4. **AI Disclosure:** The authors utilized AI-based language editing tools strictly for prose polishing and grammatical consistency check; all conceptual derivations, numerical analyses, figure/table data, and conclusions were independently conducted and verified by the authors.

---

### Part II: Executive Summary for the Associate Editor & Reviewers

#### 1. Core Motivation & Problem Articulation
In bulk power system balancing operations, real-time generation deficits incur severe asymmetric shortage penalties relative to surplus energy. Traditional $L_2$ forecasting metrics like Root-Mean-Square Error (RMSE) mask catastrophic tail shortfall events that govern operating reserve adequacy. This vulnerability is most acute near the demarcation boundary between Maximum Power Point Tracking (MPPT, Region 2) and active blade-pitch regulation (Region 3), where the governing aerodynamic sensitivity abruptly transitions from cubic growth ($\partial P / \partial v \propto 3v^2$) to zero. 

In operational utility networks, Supervisory Control and Data Acquisition (SCADA) telemetry regularly encounters communication queuing delays, packet serialization dropouts, or commercial access boundaries and proprietary OEM protocol restrictions that may conceal primary blade-pitch registers from third-party aggregators and Transmission System Operators (TSOs). Feeding stale or incomplete telemetry into deterministic physical power curves causes severe over-extrapolation near rated wind speed, leaving bulk power systems exposed to unhedged reserve shortfalls.

#### 2. Intellectual Stance: Rejecting AI Hype in Favor of Empirical Division of Labor
Rather than claiming that "deep learning unconditionally surpasses physical laws," this paper establishes an **Empirical Operational Boundary and Value-of-Information Framework under Information Freshness Constraints**. Across five random seeds on utility-scale wind plants, we delineate a transparent, evidence-grounded division of labor:

* **Regime I: Physical Aerodynamic Curves and Recalibration are Superior ($\tau \le 30\text{ min}$, Full Observability):**  
  Under intact SCADA telemetry, continuous physical quantiles achieve the lowest reserve-screening surrogate cost ($589{,}535\text{ kW}\cdot\text{h}$ at $h=1$ and $881{,}367\text{ kW}\cdot\text{h}$ at $h=6$, with $\sim 6.8\%$ violation). When communication latency grows to $10\text{--}30\text{ min}$ under full channel observability, simple state-conditional recalibration absorbs $36.3\%$--$61.7\%$ of the delay-induced shortage loss ($37.7 \to 24.0\text{ MWh}$ at $\tau=10$; $69.1 \to 26.4\text{ MWh}$ at $\tau=30$), holding violation at $7.1\%$--$7.5\%$ below the nominal $10\%$ target at negligible computational cost; at the $60$-min contingency endpoint absorption reaches $66.5\%$ ($127.552 \to 42.787\text{ MWh}$, $9.5\%$ violation). Delay conclusions represent a synthetic stress evaluation and remain provisional pending full field packet latency validation (Exp-A). **Here, complex deep learning models provide no additional operational benefit over calibrated physical rules.**

* **Regime II: Transition-Window Localized Risk Hedge under Withheld Pitch Telemetry:**  
  When commercial boundaries or proprietary OEM protocol restrictions withhold blade-pitch registers (\texttt{no\_pitch}), incoming wind-speed anchors already separate valid operating regimes deterministically ($100\%$ precision/recall on valid test cells), demonstrating that discrete regime identification is not an unobservable bottleneck. Secondary electromechanical consequences (dominated by active power, $\text{NMI}=0.461$, $\text{AUROC}=0.988$) preserve substantial boundary information ($62.9\%$ transition event recovery), enabling a **localized tail-risk hedge for reserve shortfall concentrated in dynamic transition windows** ($\Delta_{\text{trans}} - \Delta_{\text{steady}} = -296\text{k}\text{ kW}\cdot\text{h}$, $p=0.002$; $48.4\%$ of savings concentrated in transition slices). However, this hedge is strictly localized: it does not cover steady-state MPPT regimes, does not reduce plant-wide reserve screening costs relative to strong observable wind-speed-binned quantiles ($+523{,}044\text{ kW}\cdot\text{h}$ posterior penalty, $p=0.85$), and does not generalize as a universal cross-site transfer law.

* **Regime III: Physical Collapse under Severe Outage Envelopes ($60\text{ min}$, Delay-6):**  
  Under severe communication contingency stress (simulating gateway crashes or cyber-physical storms), static physical curves experience systematic reliability collapse, surging violation rates to $24.0\% \pm 1.7\%$ at $h=1$ and $12.20\% \pm 1.25\%$ at $h=6$, severely breaching the nominal 10% target. Modular neural representations provide verified defense-in-depth, curtailing tail shortage exposure by $31\%\text{--}35\%$ ($78.3\text{--}82.5\text{ MWh} \to 53.9\text{ MWh}$).

#### 3. Statistical Rigor & Demystification of Mixture-of-Experts (MoE) as an Implementation Comparator
To ensure absolute academic accountability, the paper explicitly treats Mixture-of-Experts (MoE) as an **implementation comparator rather than a primary innovation**:
- **Statistical Parity:** Capacity-matched Dense networks and dynamic MoE architectures achieve statistical parity under Clean telemetry ($p=0.380$). Consequence-based state recovery and calibrated quantile sizing do not depend on dynamic gating complexity. Under 60-minute latency, MoE’s modest nominal advantage ($+79{,}637\text{ kW}\cdot\text{h}$, uncorrected $p=0.038$) is non-significant after Bonferroni correction ($\alpha=0.0125$).
- **Decoupled Modular Deployment:** A decoupled modular architecture (*Frozen Backbone + Residual Quantile*) achieves $1.284\text{M kW}\cdot\text{h}$ and $9.68\%$ violation ($60\%$ seed target satisfaction rate), matching end-to-end MoE without incurring dynamic gating complexity. It demonstrates lightweight execution profile (110k parameters, estimated $<5\text{ ms}$ desktop benchmark runtime; physical RTU deployment remains unvalidated).

#### 4. Scope Demarcation: Level-1 Operational Pre-Dispatch Triage
The analytical scope is explicitly circumscribed to an **upstream Level-1 local pre-dispatch risk screening proxy (PSREI at $\rho=10$, Newsvendor critical fractile $q^*=0.90$)**. The formulation abstracts away downstream Level-2 AC-OPF power-flow constraints and locational marginal pricing (LMP), functioning as an upstream operational filter to ensure that corrupt wind injections do not propagate into global grid dispatchers. Downstream Battery Energy Storage System (BESS) rolling dispatch linear program (LP) formulations and storage sensitivities are fully isolated in Supplementary Material Section S4 and Supplementary Table A11-BESS to prevent conflating storage asset sizing with wind telemetry degradation.

#### 5. Key Audited Empirical Benchmarks and Evidence Pillars
- **Benchmark Trajectory Accuracy & Physical Alignment:** On the 134-turbine WTB benchmark, training-split class-weight models achieve boundary alignment of NMI 0.721 and RMSE 229.93, within 5.59 units of the best strict-cache baseline iTransformer (224.34).
- **Physical Dimension Translation:** Supplementary Table A12 translates dimensionless screening metrics into physical energy system values (e.g., MWh of unserved energy and monetary penalty equivalents across differing shortage cost ratios $\rho \in [2, 20]$).
- **Point of Common Coupling (PCC) Fleet Smoothing:** Fleet-wide aggregation at the PCC bus yields significant risk mitigation: joint posterior aggregate quantile pricing saves -2.32M kWh (95% bootstrap CI [-6.07M, 1.73M]) against Global PCC Quantile and -1.37M kWh against Gaussian parametric reserve sizing; in transitional regimes, it delivers -1.33M kWh savings over continuous physical pitch rules.
- **Industrial Markov-Gilbert Telemetry Burst Losses:** Under realistic two-state Markov burst packet loss, the stale physical rule's recall drops to 0.840, while learned posteriors sustain 0.962 recall (seed-paired F1 gain +0.021).
- **Heterogeneous External Transferability (Within Evaluated Sites Only):** Multi-year evaluations across European commercial wind plants (Kelmarsh and Penmanshiel) establish that transferred representations do not beat strong site-local 10-bin wind-speed quantiles (Penmanshiel exhibits a significant $+5.32\text{M kW}\cdot\text{h}$ penalty at $h=6$, $p=0.003$; Kelmarsh $+436\text{k kW}\cdot\text{h}$, $p=0.196$). This decisively bounds cross-site performance strictly within evaluated sites, refuting any universal zero-shot transferability law and demonstrating that external deployment requires site-local conditioning.

---

### Part III: Suggested Reviewer Expertise & Relevant Topic Areas

The manuscript intersects power system operations, wind energy engineering, and industrial data analytics. We suggest the Associate Editor consider reviewers with expertise in:
1. **Wind Power Forecasting & Operating Reserve Scheduling:** Probabilistic forecasting, quantile regression, and reserve sizing under renewable uncertainty.
2. **Wind Turbine Aerodynamics & SCADA Analytics:** IEC 61400-25 communication architectures, pitch/MPPT transition dynamics, and condition monitoring.
3. **Physics-Informed Machine Learning & Edge Diagnostics:** Applied spatio-temporal graph modeling and robust dispatch under sensor/communication degradation.

#### Suggested Peer Reviewers:
- **Prof. Pierre Pinson** (Imperial College London / Technical University of Denmark)  
  *Expertise:* Probabilistic wind power forecasting, decision-making under uncertainty, asymmetric reserve penalties.
- **Dr. Jethro Dowell** (University of Strathclyde, UK)  
  *Expertise:* Wind energy SCADA analytics, spatio-temporal wind forecasting, vector autoregression.
- **Prof. Manimaran Govindarasu / Dr. Gelli Ravikumar** (Iowa State University, USA)  
  *Expertise:* Wide-area telemetry anomaly mitigation, cyber-physical grid security, machine learning for power systems.
- **Prof. S. J. Watson** (TU Delft, Netherlands)  
  *Expertise:* Wind turbine condition monitoring using SCADA data, wake dynamics, sensor reliability.

---

### Part IV: Concluding Remarks

We believe this paper will be of high interest to the readers of *IEEE Transactions on Sustainable Energy*. By openly documenting both the failure envelopes of physical rules and the statistical boundaries of deep neural representations, the work bridges the gap between academic machine learning and utility-grade grid reliability standards.

Thank you for your time and editorial consideration.

Sincerely,

**Juntao Du, Ph.D.**  
Corresponding Author  
Associate Professor, School of Statistics and Applied Mathematics  
Anhui University of Finance and Economics, Bengbu 233030, China  
Email: `dujuntao@aufe.edu.cn`  

**Junyu Li**  
School of Statistics and Applied Mathematics  
Anhui University of Finance and Economics, Bengbu 233030, China  
