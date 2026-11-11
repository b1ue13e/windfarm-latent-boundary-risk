# Decisive Matched-Reserve-Budget Preregistration

**Document Status:** PREREGISTERED & FROZEN  
**Date:** 2026-09-22  
**Repository:** `https://github.com/b1ue13e/windfarm-latent-boundary-risk.git`  
**Base Commit:** `621bb8b5817483f54bfb7a51fcd0f9a0751fc542`  
**Target Venue:** *IEEE Transactions on Sustainable Energy* (TSTE)  

---

## 1. Scientific Context and Central Question

The paper investigates reserve-risk screening under degraded SCADA telemetry where blade pitch is withheld or delayed at dispatch time. The governing inferential chain is:
$$\text{Observability} \longrightarrow \text{Recoverability} \longrightarrow \text{Decision Sufficiency}.$$

The manuscript already establishes that:
1. Consequence signals (primarily active power) can partially recover the latent MPPT-to-pitch operating boundary ($\text{Brier}=0.0112$, $\text{NMI}=0.461$).
2. Recoverability does **not** imply universal decision superiority: a strong observable wind-speed-conditioned quantile baseline achieves lower total $\text{PSREI}$ cost plant-wide ($\Delta L = +523{,}044\text{ kW}\cdot\text{h}$ penalty for posterior).
3. The current manuscript characterizes posterior conditioning as a **localized transition-window risk hedge**, noting lower violation rates ($7.24\%$ vs. $8.36\%$) and lower uncovered shortage ($86{,}592$ vs. $90{,}231\text{ kW}\cdot\text{h}$), but accompanied by higher reserve procurement ($3{,}567{,}090$ vs. $3{,}417{,}998\text{ kW}\cdot\text{h}$, $+149{,}092\text{ kW}\cdot\text{h}$) and higher $\text{PSREI}$ ($+112{,}704\text{ kW}\cdot\text{h}$).

### The Single Decisive Question:
> **At the SAME reserve-procurement budget, does posterior-conditioned reserve allocation provide genuinely better reliability during the pre-defined operating-transition window than the strongest direct wind-speed-conditioned quantile baseline?**
>
> In other words: Is the lower transition-window violation rate of posterior conditioning caused by **superior allocation efficiency of a fixed reserve budget**, OR is it explained **almost entirely by buying more reserve**?

---

## 2. Frozen Scientific Definitions

### 2.1 Evaluated Methods
- **$M_{\text{base}}$ (Policy B - Wind-Speed-Conditioned Quantile Baseline)**:
  Empirical quantile $\hat{q}_{0.90}(s \mid v)$ conditioned on 10 uniform wind-speed bins over $[0, 25\text{ m/s}]$ calibrated on validation data.
- **$M_{\text{post}}$ (Policy C - Spatio-Temporal Boundary Posterior Quantile)**:
  Empirical quantile $\hat{q}_{0.90}(s \mid \pi)$ conditioned on 5 validation-calibrated quintiles of the learned latent-boundary posterior probability $\pi_t = P(Z_t = \text{Pitch} \mid \mathcal{I}_t^{(d)})$ from the spatio-temporal Dense GNN.

### 2.2 Data Split and Telemetry Degradation
- **Dataset**: WTB 134-turbine wind farm, 245-day corpus.
- **Split**: 35-day chronological test split ($N = 385{,}205$ valid evaluated turbine-time cells), identical validation set ($N = 142{,}235$ cells).
- **Seeds**: 5 frozen random seeds (`201`, `202`, `203`, `204`, `205`).
- **Telemetry Condition**: Blade-pitch withheld ($\tau=0$, `Pab_mean` and `Pab_std` masked).
- **Dispatch Horizon**: Operational Level-1 pre-dispatch horizon $h=6$ (60-minute ahead dispatch).
- **Point Forecast Residuals**: $s_t = \max(\hat{y}_t - y_t, 0)$ frozen in `artifacts/fixed_forecast_residuals.npz`.

### 2.3 Evaluated Population Slices
1. **Transition Window ($\text{Trans}$, Primary Slice)**:
   Observations within $\pm 3$ time-steps (10-minute steps) of an operating regime change ($Z_t \ne Z_{t-1}$).
   Represents $N = 139{,}684$ cells ($36.26\%$ of valid test sample).
2. **Stationary Window ($\text{Steady}$, Negative Control)**:
   Observations strictly outside the transition window (stationary MPPT or pitch).
   Represents $N = 245{,}521$ cells ($63.74\%$ of valid test sample).
3. **Full Plant ($\text{Full}$, Global Control)**:
   All valid evaluated cells ($N = 385{,}205$, $100\%$).

---

## 3. Matched-Reserve-Budget Frontier Protocol

### 3.1 Policy Scaling Formulation (Phase 3A)
For each method $m \in \{\text{base}, \text{post}\}$, let $r_m(i,t)$ denote the frozen reserve recommendation at nominal $q^*=0.90$.
The scaled policy family is defined by proportional scaling:
$$r_m^{(\alpha)}(i,t) = \max(0, \alpha \cdot r_m(i,t)),$$
swept over a dense grid $\alpha \in [0.50, 1.50]$ with step $\Delta \alpha \le 0.02$.
This formulation preserves the spatial-temporal allocation geometry and relative turbine ranking while monotonically adjusting aggregate procurement volume.

### 3.2 Common Budget Support and Budget Grid (Phase 3B)
For each method on the target evaluation slice, total reserve procurement energy is:
$$R_m(\alpha) = \sum_{i,t \in \text{Slice}} r_m^{(\alpha)}(i,t) \cdot \Delta t,$$
where $\Delta t = 1/6\text{ h}$.
The common budget support is defined as:
$$\mathcal{B}_{\text{common}} = \left[ \max(\min R_{\text{base}}, \min R_{\text{post}}), \; \min(\max R_{\text{base}}, \max R_{\text{post}}) \right].$$
Across $\mathcal{B}_{\text{common}}$, a uniform grid of $K = 30$ budget points $\{B_k\}_{k=1}^K$ is established.
For each target budget $B_k$, the exact multiplier $\alpha_m(B_k)$ is solved via monotonic numerical interpolation such that:
$$\frac{|R_m(\alpha_m(B_k)) - B_k|}{B_k} \le 0.001 \quad (0.1\% \text{ tolerance}).$$

### 3.3 Two Frontier Variants (Phase 3C)
1. **Frontier A — Ex-Post Matched-Budget Diagnostic**:
   Multipliers $\alpha_{\text{base}}(B)$ and $\alpha_{\text{post}}(B)$ are matched directly on the test set observations. This isolates pure allocation efficiency from calibration drift.
2. **Frontier B — Validation-Calibrated Deployable Frontier**:
   Target budgets $B_{\text{val}}$ are declared on validation data; multipliers $\alpha_{\text{base}}^{\text{val}}(B)$ and $\alpha_{\text{post}}^{\text{val}}(B)$ are solved on the validation set, frozen, and applied to test observations. Realized test budgets and reliability metrics are reported.

---

## 4. Primary Decision Metrics and Accounting Identity

At each budget point $B$:
- Total Reserve Procurement: $R_m(B) = \sum r_m(i,t) \Delta t$
- Uncovered Shortfall Energy: $U_m(B) = \sum \max(s(i,t) - r_m(i,t), 0) \Delta t$
- Violation Probability: $V_m(B) = \frac{1}{N} \sum \mathbb{I}(s(i,t) > r_m(i,t))$
- Penalized Reserve-Shortfall Energy Index ($\rho=10$):
  $$\text{PSREI}_{10}(B) = R(B) + 10 \cdot U(B)$$

### Paired Contrast at Matched Budget $B$:
$$\Delta U(B) = U_{\text{post}}(B) - U_{\text{base}}(B)$$
$$\Delta V(B) = V_{\text{post}}(B) - V_{\text{base}}(B)$$
$$\Delta \text{PSREI}_{10}(B) = \text{PSREI}_{\text{post}}(B) - \text{PSREI}_{\text{base}}(B) \equiv 10 \cdot \Delta U(B) \quad (\text{since } \Delta R \equiv 0).$$

---

## 5. Dependence-Aware Uncertainty (Phase 5 & 6)

### 5.1 Paired Day-Cluster Bootstrap Specification
- **Clustering Unit**: Calendar day ($144$ consecutive 10-minute dispatch steps across all 134 turbines).
- **Cluster Count**: 35 non-overlapping clusters in the test set.
- **Replicates**: $B_{\text{boot}} = 5{,}000$ Monte Carlo resamples drawn with replacement.
- **Paired Sampling**: Identical clusters sampled for both methods in each bootstrap replicate.
- **Strict Within-Bootstrap Budget Matching**:
  In each bootstrap replicate $b$, multipliers $\alpha_{\text{base}}^{(b)}(B_k)$ and $\alpha_{\text{post}}^{(b)}(B_k)$ are independently re-solved on the resampled data so that:
  $$R_{\text{post}}^{(b)}(B_k) = R_{\text{base}}^{(b)}(B_k) = B_k \quad (\Delta R^{(b)} \equiv 0).$$
  This guarantees that the bootstrap distribution reflects pure allocation efficiency without confounding procurement differences.

### 5.2 Frontier-Level Summary Metrics
1. **Integrated Shortfall Energy Difference**:
   $$\Delta \text{AUC}_{\text{shortfall}} = \int_{\min \mathcal{B}}^{\max \mathcal{B}} [U_{\text{post}}(B) - U_{\text{base}}(B)] \, \mathrm{d}B.$$
   Estimated via trapezoidal quadrature across the 30 grid points, with $95\%$ bootstrap confidence interval.
2. **Favorable Support Fraction**:
   $$f_{\text{fav}} = \frac{1}{K} \sum_{k=1}^K \mathbb{I}(\Delta U(B_k) < 0).$$

---

## 6. Economic $\rho$-Sensitivity Analysis (Phase 2 & Phase 8)

1. **Frozen-Policy Algebraic Break-Even (Phase 2)**:
   $$\rho_{\text{break}} = -\frac{\Delta R}{\Delta U} = -\frac{R_{\text{post}} - R_{\text{base}}}{U_{\text{post}} - U_{\text{base}}}.$$
   Evaluated at frozen nominal $q^*=0.90$ across $\rho \in [1, 100]$.
2. **Validation Re-Optimized Policy Sensitivity (Phase 8)**:
   For $\rho \in [2, 5, 10, 15, 20, 30, 40, 50, 75, 100]$, Newsvendor optimal quantile is $q^*(\rho) = 1 - 1/\rho$.
   Each policy re-calibrates its bin/quintile quantiles on validation data for $q^*(\rho)$, freezes parameters, and evaluates realized test PSREI to identify the dynamic economic crossover.

---

## 7. Falsification Hypothesis and Pre-Committed Decision Rules

| Outcome Case | Quantitative Condition | Scientific Interpretation | Manuscript Action |
| :--- | :--- | :--- | :--- |
| **Case A: Strong Support** | $\Delta U(B) < 0$ and $95\%$ bootstrap CI excludes zero over $\ge 50\%$ of $\mathcal{B}_{\text{common}}$ in transitions; stationary control shows no gain. | Posterior provides genuine superior allocation efficiency for fixed reserve during transitions. | Upgrade manuscript to state that posterior reallocates fixed budget to higher-risk events during transitions. |
| **Case B: Weak / Local Support** | $\Delta U(B) < 0$ only over narrow budget band ($< 30\%$), or $95\%$ bootstrap CIs cross zero. | Benefit is borderline / noise-sensitive; cannot conclusively claim allocation superiority. | Retain "localized risk-hedging behavior" with explicit caveat that equal-budget efficiency is not statistically established. |
| **Case C: Null Result** | $\Delta U(B) \approx 0$ across the common budget support ($|\Delta U / U_{\text{base}}| < 2\%$). | Lower raw violation was driven almost entirely by purchasing more reserve volume, not smarter allocation. | Conclude that posterior changes operating point but does not improve allocation efficiency at matched procurement. |
| **Case D: Negative Result** | $\Delta U(B) > 0$ across common budget support in transitions. | Posterior is inferior to wind-speed conditioning even at matched budget during transitions. | Strike all claims of transition decision advantage; retain latent boundary only as representation recovery. |

**Pre-Commitment Clause:**  
The experiment is successful when it cleanly discriminates among Cases A, B, C, and D. A negative or null result (Case C or D) is fully acceptable and will be reported with complete scientific candor.
