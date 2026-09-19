# Manuscript Reconstruction Structural Change Log
## Target: IEEE Transactions on Sustainable Energy (TSTE)
**Artifact ID**: `06_structural_change_log.md`  
**Date**: September 2026  

---

## 1. Structural Architecture Overview

The manuscript underwent a comprehensive structural transformation from a technology-promotional narrative to a rigorous, boundary-science diagnostic investigation. The table below contrasts the legacy structure against the reconstructed IEEE TSTE architecture:

| Manuscript Component | Legacy Structure | Reconstructed IEEE TSTE Structure | Primary Rationale |
|:---|:---|:---|:---|
| **Title** | Focused on physics-aligned MoE routing and early warning | *Operational Boundaries of Aerodynamic Power Rules, Recalibration, and Learned Representations under SCADA Telemetry Degradation* | Reframes work around empirical boundary science, information freshness, and grid reliability |
| **Abstract** | Lengthy (>280 words), promoted MoE gating, claimed edge deployment | Bounded 220-word executive summary: Problem $\to$ Gap $\to$ Approach $\to$ 3 Core Findings $\to$ Grid Balancing Implication | Adheres strictly to IEEE 200–250 word limit; highlights empirical division of labor |
| **Introduction** | Generic AI motivation, diffuse claims, combative tone toward physics | Strict 5-paragraph IEEE TSTE architecture culminating in 4 bounded, verifiable contributions | Connects SCADA degradation to power balancing; establishes empirical division of labor |
| **Section II: Methodology** | Heavily centered on multi-expert MoE routing and auxiliary gating losses | **Spatio-Temporal Graph Quantile (STGQ)** framework: $C_p$ control cliff, state-conditional recalibration, directed wake diffusion, residual quantile loss; MoE condensed to ablation comparator | Focuses on core operational mechanisms; decouples representation learning from quantile calibration |
| **Section III: Experimental Setup** | Focused primarily on WTB KDD Cup benchmark with diffuse protocol | Standardized protocol across four wind plants (WTB, Penmanshiel, Kelmarsh, LHB); explicit definition of telemetry latency and missingness stress tests | Establishes industrial realism and cross-farm empirical rigor |
| **Section IV: Empirical Results** | Organized by model architectures with promotional bolding | Strictly organized by **Research Questions (RQ1–RQ6)** with objective neutral formatting | Converts narrative into systematic, falsifiable hypothesis testing |
| **Section V: Discussion** | Defensive explanations of model discrepancies and post-hoc excuses | Transparent analysis of MoE statistical parity, LHB micro-farm operational boundary, and SCADA watchdog guidelines | Fortifies manuscript against Reviewer #2 objections; embraces negative findings |
| **BESS Dispatch Model** | Embedded in main text as a primary contribution | Relegated entirely to **Supplementary Material**; single illustrative paragraph retained in Section II-D/Discussion | Immunizes paper against battery degradation and AC power-flow reviewer critiques |
| **Terminology & Metrics** | Inconsistent units, historical remnants (95M, 15.5M), AGC blunder | Standardized single dispatch interval delivery cost (kW·h per interval); AGC replaced with Real-Time Economic Dispatch (RTED) | Conforms to IEEE PES electric power systems standards |

---

## 2. Section-by-Section Transformation Log

### Abstract & Keywords
- **Word Count**: Reduced and tightly budgeted to exactly ~220 words.
- **De-marketing**: Replaced all promotional terms ("fundamentally superior", "revolutionary gating") with quantitative performance metrics ($589{,}535\text{ kW}\cdot\text{h}$ clean, $24.0\%$ collapse, $55.3\%$ recalibration absorption, $46.7\text{k}\text{--}68.6\text{k}\text{ kW}\cdot\text{h}$ withheld-channel gain).
- **Keywords**: Updated to standard IEEE PES indexing terms.

### Section I: Introduction
- **Paragraph 1**: Established the asymmetric shortage penalty of grid balancing ($\rho=10$) and the non-linear aerodynamic control cliff at rated wind speed ($u_{\mathrm{rated}}$).
- **Paragraph 2**: Grounded SCADA telemetry vulnerabilities in IEC 61400-25 standards and commercial Kelmarsh operational data (99.6% sub-interval transitions).
- **Paragraph 3**: Formulated the operational dilemma between fragile static physical curves and unconstrained neural networks.
- **Paragraph 4**: Introduced the *Empirical Operational Boundary and Value-of-Information Framework under Information Freshness Constraints*.
- **Paragraph 5**: Articulated four bounded contributions with explicit empirical numbers.

### Section II: Methodology (STGQ Framework)
- **Mathematical Formalism**: Derived variable-speed turbine aerodynamics $P_{\mathrm{mech}} = \frac{1}{2}\rho \pi R^2 C_p(\lambda, \beta) v^3$ and proved the derivative jump $\partial P/\partial v$ collapsing from cubic growth to zero at $u_{\mathrm{rated}}$.
- **State-Conditional Recalibration**: Added formal mathematical formulation of conditional quantile mapping:
  $$\hat{r}^{\mathrm{recal}}_{i,t}(k) = \hat{Q}_{q^*}\left( s_{i,t} \mid \mathbf{s}_{i,t-\tau} \in \mathcal{B}_k \right)$$
- **Directed Wake Diffusion**: Formulated time-varying asymmetric wake graph $\mathcal{A}_t$ based on local wind direction and wake cone decay.
- **Decoupled Residual Quantile Head**: Formulated asymmetric pinball loss at Newsvendor critical fractile $q^* = 1 - 1/\rho = 0.90$ acting on point-forecast residuals.
- **MoE Condensation**: Condensed dynamic MoE routing to a concise paragraph and designated it as an architectural ablation comparator.
- **Terminology Fix**: Replaced "Automatic Generation Control (AGC)" on line 256 with "Real-Time Economic Dispatch (RTED)" to match the 10-minute dispatch timescale.

### Section III: Experimental Setup & Datasets
- **Multi-Farm Demarcation**: Cataloged the four empirical wind plant environments (WTB 134-turbine, Penmanshiel 14-turbine [WT01--WT15 excluding WT03], Kelmarsh 6-turbine, and LHB 4-turbine).
- **Telemetry Degradation Protocols**: Detailed controlled latency steps ($\tau \in \{10, \dots, 60\}\text{ min}$), two-state Markov-Gilbert burst dropouts ($p_{GB}=0.08, p_{BB}=0.75$), and withheld blade-pitch channels (`no_pab`).

### Section IV: Results Organized by RQ1–RQ6
- **RQ1 (Physical Primacy)**: Clean telemetry performance established ($589{,}535\text{ kW}\cdot\text{h}$ at $h=1$; $881{,}367\text{ kW}\cdot\text{h}$ at $h=6$, $6.8\%$ violation).
- **RQ2 (Physical Collapse)**: 60-min latency breakdown documented ($24.0\%$ at $h=1$, $12.20\%$ at $h=6$, $127.6\text{ MWh}$ shortage).
- **RQ3 (Recalibration Role)**: Recalibration absorbs $55.3\%$ of shortage ($57.0\text{ MWh}$, $10.7\%$ violation), proving sufficiency under full observability.
- **RQ4 (Learned Value under Withheld Pitch)**: STGQ delivers $46.7\text{k}\text{--}68.6\text{k}\text{ kW}\cdot\text{h}$ savings and doubles recall ($0.416$ vs $0.196$).
- **RQ5 (MoE Demystification)**: Proved statistical parity between Dense and MoE ($p=0.380$); validated decoupled modular pipeline ($1.284\text{M kW}\cdot\text{h}$, $9.68\%$ violation).
- **RQ6 (Multi-Farm & PCC Aggregation)**: PCC portfolio smoothing saves $-2.32\text{M kW}\cdot\text{h}$; LHB negative case framed as operational boundary.

### Section V: Discussion & Operational Guidelines
- Detailed interpretation of MoE parity and decoupled modular deployment.
- Formalized the LHB micro-farm operational boundary condition.
- Provided practical telemetry watchdog guidelines for utility operators.
- Retained one illustrative paragraph on downstream BESS dispatchability.

### Section VI: Conclusion
- Synthesized the empirical division of labor across telemetry freshness states.
