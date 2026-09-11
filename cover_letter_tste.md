# IEEE Transactions on Sustainable Energy
## Submission Cover Letter & Executive Summary

**Date:** March 2026  
**To:** Editor-in-Chief, *IEEE Transactions on Sustainable Energy*  
**From:** Juntao Du (Corresponding Author), on behalf of the authors  
**Affiliation:** School of Statistics and Applied Mathematics, Anhui University of Finance and Economics, Bengbu 233030, China  
**Contact:** `dujuntao@aufe.edu.cn`  

**Manuscript Title:**  
*Operational Boundaries of Aerodynamic Power Rules, Recalibration, and Learned Representations under SCADA Telemetry Degradation*

**Authors:**  
Junyu Li and Juntao Du

---

### Part I: Formal Submission Statement

Dear Editor-in-Chief and Editorial Board,

We submit our original research manuscript entitled **"Operational Boundaries of Aerodynamic Power Rules, Recalibration, and Learned Representations under SCADA Telemetry Degradation"** for consideration as a Regular Paper in *IEEE Transactions on Sustainable Energy* (TSTE).

The manuscript complies with the strict IEEE double-column 10-page length requirement (the main paper is exactly 10.0 pages including all text, equations, tables, figures, and 38 references). A comprehensive 16.0-page Supplementary Material is provided to support reproducible verification, extended multi-regime phase scans, and mathematical derivations without burdening the main text.

#### Compliance & Declarations:
1. **Originality & Sole Submission:** This manuscript represents original work that has not been published previously and is not currently under peer review elsewhere.
2. **Author Approval:** All listed authors have reviewed, contributed to, and approved the final manuscript.
3. **Data Availability & Ethics:** The study evaluates publicly available commercial SCADA archives (134-turbine WTB benchmark, ENGIE La Haute Borne, Kelmarsh, and Penmanshiel). No human or animal subjects were involved. Full reproduction scripts, configuration files, and frozen validation checkpoints are documented in the manuscript.
4. **AI Disclosure:** The authors utilized AI-based language editing tools strictly for prose polishing and grammatical consistency check; all conceptual derivations, numerical analyses, figure/table data, and conclusions were independently conducted and verified by the authors.

---

### Part II: Executive Summary for the Associate Editor & Reviewers

#### 1. Core Motivation & Problem Articulation
In bulk power system balancing operations, real-time generation deficits incur severe asymmetric shortage penalties relative to surplus energy. Traditional $L_2$ forecasting metrics like Root-Mean-Square Error (RMSE) mask catastrophic tail shortfall events that govern operating reserve adequacy. This vulnerability is most acute near the demarcation boundary between Maximum Power Point Tracking (MPPT, Region 2) and active blade-pitch regulation (Region 3), where the governing aerodynamic sensitivity abruptly transitions from cubic growth ($\partial P / \partial v \propto 3v^2$) to zero. 

In operational utility networks, Supervisory Control and Data Acquisition (SCADA) telemetry regularly suffers communication queuing delays, packet serialization dropouts, and OEM protocol firewalls that conceal primary blade-pitch registers from third-party aggregators and Transmission System Operators (TSOs). Feeding stale or incomplete telemetry into deterministic physical power curves causes severe over-extrapolation near rated wind speed, leaving bulk power systems exposed to unhedged reserve shortfalls.

#### 2. Intellectual Stance: Rejecting AI Hype in Favor of Empirical Division of Labor
Rather than claiming that "deep learning unconditionally surpasses physical laws," this paper establishes an **Empirical Operational Boundary and Value-of-Information Framework under Information Freshness Constraints**. Across five random seeds on utility-scale wind plants, we delineate a transparent, evidence-grounded division of labor:

* **Regime I: Physical Aerodynamic Curves and Recalibration are Superior ($\tau \le 30\text{ min}$, Full Observability):**  
  Under intact SCADA telemetry, continuous physical quantiles achieve the lowest reserve-screening surrogate cost ($589{,}535\text{ kW}\cdot\text{h}$ at $h=1$ and $881{,}367\text{ kW}\cdot\text{h}$ at $h=6$, with $\sim 6.8\%$ violation). When communication latency increases to $10\text{--}30\text{ min}$ under full channel observability, simple state-conditional recalibration absorbs $55.3\%$ of shortage loss ($127.6 \to 57.0\text{ MWh}$, restoring violation to $10.7\%$) at negligible computational cost. **Here, complex deep learning models are unnecessary.**

* **Regime II: Learned Representations Deliver Decisive Value under Withheld Pitch Telemetry:**  
  When proprietary OEM boundaries conceal blade-pitch registers (\texttt{no\_pitch}), physical curves lose direct rotor state awareness. In this regime, learned spatio-temporal representations reconstruct aerodynamic operating states purely from secondary electromechanical transients (active/reactive power, wake geometry), consistently outperforming recalibrated physics by **$46.7\text{k}\text{--}68.6\text{k}\text{ kW}\cdot\text{h}$ across all latencies** and more than doubling boundary recall ($0.416$ vs. $0.196$ under Delay-6).

* **Regime III: Physical Collapse under Severe Outage Envelopes ($60\text{ min}$, Delay-6):**  
  Under severe communication contingency stress (simulating gateway crashes or cyber-physical storms), static physical curves experience systematic reliability collapse, surging violation rates to $24.0\% \pm 1.7\%$ at $h=1$ and $12.20\% \pm 1.25\%$ at $h=6$, severely breaching the nominal 10% target. Modular neural representations provide verified defense-in-depth, curtailing tail shortage exposure by $31\%\text{--}35\%$ ($78.3\text{--}82.5\text{ MWh} \to 53.9\text{ MWh}$).

#### 3. Statistical Rigor & Demystification of Mixture-of-Experts (MoE)
To ensure absolute academic accountability, the paper actively challenges popular machine learning narratives:
- **Statistical Parity:** Capacity-matched Dense networks and dynamic MoE architectures achieve statistical parity under Clean telemetry ($p=0.380$). Under 60-minute latency, MoE’s modest nominal advantage ($+79{,}637\text{ kW}\cdot\text{h}$, uncorrected $p=0.038$) is non-significant after Bonferroni correction ($\alpha=0.0125$).
- **Decoupled Edge Deployment:** A decoupled modular architecture (*Frozen Backbone + Residual Quantile*) achieves $1.284\text{M kW}\cdot\text{h}$ and $9.68\%$ violation ($60\%$ seed compliance rate), matching end-to-end MoE without incurring dynamic gating complexity. This provides utility operators with a single-checkpoint, lightweight deployment solution (110k parameters, $<5\text{ ms}$ inference).

#### 4. Scope Demarcation: Level-1 Operational Pre-Dispatch Triage
The analytical scope is explicitly circumscribed to an **upstream Level-1 local pre-dispatch risk screening proxy (PSREI at $\rho=10$, Newsvendor critical fractile $q^*=0.90$)**. The formulation abstracts away downstream Level-2 AC-OPF power-flow constraints and locational marginal pricing (LMP), functioning as an upstream operational filter to ensure that corrupt wind injections do not propagate into global grid dispatchers.

#### 5. Key Audited Empirical Benchmarks and Evidence Pillars
- **Benchmark Trajectory Accuracy & Physical Alignment:** On the 134-turbine WTB benchmark, training-split class-weight models achieve boundary alignment of NMI 0.721 and RMSE 229.93, within 5.59 units of the best strict-cache baseline iTransformer (224.34).
- **Point of Common Coupling (PCC) Fleet Smoothing:** Fleet-wide aggregation at the PCC bus yields significant risk mitigation: joint posterior aggregate quantile pricing saves -2.32M kWh (95% bootstrap CI [-6.07M, 1.73M]) against Global PCC Quantile and -1.37M kWh against Gaussian parametric reserve sizing; in transitional regimes, it delivers -1.33M kWh savings over continuous physical pitch rules.
- **Industrial Markov-Gilbert Telemetry Burst Losses:** Under realistic two-state Markov burst packet loss, the stale physical rule's recall drops to 0.840, while learned posteriors sustain 0.962 recall (seed-paired F1 gain +0.021).

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
