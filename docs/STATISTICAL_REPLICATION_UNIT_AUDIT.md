# Statistical Claim and Replication Unit Audit Report

**Date:** 2026-09-19  
**Status:** ALL STATISTICAL CLAIMS AUDITED & BOUNDED  
**Scope:** Complete manuscript (`paper_tste_ieee.md`), supplementary (`paper_tste_supplementary.md`), and compiled artifacts.

---

## 1. Executive Summary

This audit establishes rigorous statistical boundaries for every quantitative claim and hypothesis test in the manuscript. It enforces the fundamental scientific distinction between:
1. **Training Stochasticity ($n=5$ model random seeds):** Evaluates parameter initialization and optimization variance across seeds 201--205. This measures algorithmic stability, *not* population-level physical replication across wind farms or weather epochs.
2. **Operational Sampling Uncertainty (35 Observed Daily Clusters, $B=1{,}000$ Paired Bootstrap Resamples):** Evaluates operational risk variation across the 35 observed non-overlapping daily clusters in the test split (144 continuous ten-minute dispatch steps per daily cluster across all 134 turbines simultaneously). The 1,000 bootstrap replicates are Monte Carlo resamples drawn with replacement from those 35 observed daily clusters, *not* 1,000 independent observational units. Paired model comparisons are evaluated within each resampled cluster.

---

## 2. Statistical Replication Hierarchy & Anti-Pseudoreplication Protocol

| Study Component | Unit of Replication | Sample Size | Resampling / Test Protocol | What it Identifies | What it CANNOT Claim |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Privileged-Supervision Latent Alignment Ablation** | Model random seed | $n=5$ seeds (201--205) | Matched-seed paired difference ($\lambda_{\mathrm{align}}=5000$ vs $0$). Paired Student-$t$ ($df=4$) & Exact Wilcoxon signed-rank. | Training stochasticity; representation separation gain in latent space. | Does *not* isolate training-time pitch telemetry itself; does *not* prove necessity. |
| **Operational Reserve Screening (Table I & Table II)** | Daily cluster (35 observed days) | 35 observed daily clusters ($B=1{,}000$ paired resamples) | Paired daily cluster bootstrap (144 steps/cluster, 134 turbines clustered simultaneously). Paired differences evaluated within each resampled day. | Operational dispatch cost distribution under real weather variability across observed diurnal clusters. | Does *not* treat 1,000 bootstrap resamples as independent observations (effective sample size is 35 observed days); does *not* assume i.i.d. turbine-time samples (avoids $N=408{,}939$ pseudoreplication). |
| **MoE Routing vs. Dense Parity** | Daily cluster (35 observed days) | 35 observed daily clusters ($B=1{,}000$ paired resamples) | Paired daily cluster bootstrap ($p=0.380$) across 35 observed days. | High-capacity capacity-matched routing parity in reserve screening. | Does *not* prove universal equivalence; establishes lack of detected difference across observed days. |
| **Transition Window Mediation** | Turbine event window | $N=13{,}883$ boundary events | Stratified bootstrap across 134 turbines ($p < 0.0001$). | Fraction of cost reduction localized to aerodynamic transitions (48.4%). | Does *not* claim cashflow profit or revenue creation. |
| **Cross-Farm Robustness (Table IV & Table A11g--h)** | Farm-year / turbine-year | Kelmarsh (9 yr), Penmanshiel (8.6 yr), LHB (1 yr) | Multi-year walk-forward rolling quarterly/annual folds. | Generalization boundary (sparse vs dense arrays, PCC smoothing). | Rejects turbine-count scaling laws ($N<20, N\ge 50$); identifies site physics. |

---

## 3. Comprehensive Inventory of Headline $p$-Values and Statistical Claims

### 3.1 Privileged Supervision & Latent Representation Alignment ($n=5$ Model Seeds)

- **Claimed Metrics:**
  - Normalized Mutual Information (NMI): $\Delta\mathrm{NMI} = +0.134 \pm 0.039$ (from $0.076 \pm 0.038$ to $0.210 \pm 0.015$).
  - Adjusted Rand Index (ARI): $\Delta\mathrm{ARI} = +0.075 \pm 0.017$ (from $0.021 \pm 0.014$ to $0.096 \pm 0.010$).
- **Test Statistics ($n=5, df=4$):**
  - Paired Student-$t$ test:
    - NMI: $t = 7.74, p = 0.0015$ (rejects null of zero representation shift).
    - ARI: $t = 10.10, p = 0.0005$ (rejects null of zero partition recovery).
  - Exact Wilcoxon Signed-Rank Test:
    - Under $n=5$, the exact test statistic with all positive signs ($W=0$) achieves $p = 2 \times (1/2)^5 = 1/2^4 = 0.0625$.
    - *Reporting Boundary:* The manuscript explicitly discloses that the non-parametric Wilcoxon test has a theoretical minimum two-sided $p$-value of $0.0625$ at $n=5$. Parametric $p$-values ($p=0.0015$ and $p=0.0005$) are reported alongside this exact sample-size boundary, acknowledging that $n=5$ measures optimization stochasticity.
- **Decision-Consequence Attribution Boundary:**
  - Net plant-wide PSREI difference is $-311{,}957\text{ kWh}$ with $95\%$ bootstrap CI $[-871{,}439, +247{,}525]$ (crossing zero).
  - *Anti-Overclaim Notice:* The manuscript strictly refrains from asserting that privileged supervision provides a confirmed decision benefit or that it is a "strictly necessary mechanism". It discloses that latent alignment sharpens operating-state representations without statistically separating decision costs under clean telemetry.

### 3.2 MoE vs. Dense Parity ($p=0.380$)

- **Location:** Abstract, Section IV-B (Result 2), Table II, Conclusion.
- **Claimed Finding:** Dynamic Mixture-of-Experts (MoE) routing confers no statistically significant advantage over unrouted dense architectures in reserve screening ($p=0.380$).
- **Test Methodology:**
  - Paired daily cluster bootstrap test over 35 observed test days ($B=1{,}000$ Monte Carlo resamples, 144 steps/cluster) comparing STGQ-Routed ($1{,}163{,}593\text{ kW}\cdot\text{h}$) vs STGQ-Dense ($1{,}179{,}859\text{ kW}\cdot\text{h}$) under Delay-6.
  - Paired cost difference: $-16{,}266\text{ kW}\cdot\text{h}$ ($95\%$ CI $[-52{,}401, +20{,}069]$, two-sided bootstrap $p = 0.380$).
  - *Effective Sample Size Note:* The 1,000 bootstrap resamples are Monte Carlo iterations used to approximate the empirical sampling distribution under paired resampling, not 1,000 independent day-block observations; the effective cluster count is $n=35$ observed days.
- **Interpretation Notice:** The failure to reject the null hypothesis ($p=0.380$) is properly interpreted as lack of detected difference under capacity matching, *not* formal equivalence (since no equivalence margin was prespecified for Two One-Sided Tests, TOST).

### 3.3 Active-Power Consequence Signal Mediation ($p < 0.0001$)

- **Location:** Section IV-D (Result 4), Table II, Table A11e.
- **Claimed Finding:** When blade pitch telemetry is withheld, latent operating states are inferred primarily from secondary consequence channels: active power transients ($\texttt{Patv}$) provide dominant discriminative power (Brier score $0.0112$, NMI $0.461$), whereas thermal channels fail to track fast aerodynamic transitions (recall $0.0\%$).
- **Mediation Analysis:**
  - Decision-value mediation confirms that dynamic transition windows account for $48.4\%$ of total reserve cost reductions ($p = 0.0000$ under 10,000 bootstrap resamples).
- **Statistical Integrity:** Sample size is based on $N=13{,}883$ boundary-active events clustered across 134 turbines over 35 days.

### 3.4 Multiplicity Control across Mechanism Controls ($m=13$)

- **Location:** Supplementary Table A11e.
- **Procedure:** Family-wise Bonferroni correction over $m=13$ pre-planned mechanism comparisons ($\alpha_{\mathrm{adjusted}} = 0.05 / 13 = 0.00385$, corresponding to $99.62\%$ simultaneous confidence intervals).
- **Results:**
  - Soft-physical vs Global: 99.62% CI $[-1.38\text{M}, -0.82\text{M}]$ (excludes zero).
  - Soft-physical vs Physical-bin: 99.62% CI $[-0.85\text{M}, -0.45\text{M}]$ (excludes zero).
  - Joint Gate vs Global: 99.62% CI $[-0.78\text{M}, -0.36\text{M}]$ (excludes zero).
  - Joint Gate vs Physical-bin: 99.62% CI $[-0.35\text{M}, +0.08\text{M}]$ (crosses zero; no difference detected).
  - Independent GBDT vs Joint Gate: 99.62% CI $[+1.35\text{M}, +1.81\text{M}]$ (excludes zero).
  - Joint Non-routed vs Joint Gate: 99.62% CI $[-0.21\text{M}, +0.24\text{M}]$ (crosses zero; parity).

### 3.5 Modular Classifier Reserve Control (Result 5, Supplementary Table A10c)

- **Location:** Main manuscript Section IV-C (Result 5), Supplementary Table A10c, artifacts in `artifacts/modular_classifier_reserve_control/`.
- **Evaluated Policy:** Independent sequence classifier (Graph WaveNet coupled to live-anchor classifier) vs. physical-bin baseline ($84{,}314{,}353\text{ kW}\cdot\text{h}$) and joint boundary router ($84{,}577{,}217\text{ kW}\cdot\text{h}$) at $\rho=10$ on the WTB boundary slice across 5 seeds (201--205).
- **Comparator 1 (vs. Physical-Bin):**
  - Paired difference: $\Delta\text{Cost} = +2{,}221{,}968\text{ kW}\cdot\text{h}$ ($+2.22\text{M kW}\cdot\text{h}$).
  - All 5 seed differences are positive: Seed 201 ($+2.66\text{M}$), 202 ($+2.57\text{M}$), 203 ($+2.64\text{M}$), 204 ($+2.04\text{M}$), 205 ($+1.20\text{M}$).
  - 95% Bootstrap CI: $[+1{,}662{,}670, +2{,}632{,}979]$ (strictly excludes zero).
  - Paired Student-$t$ test ($df=4$): $t = 7.9712$, $p = 0.00134 < 0.01$.
  - Exact Wilcoxon signed-rank test: $W=0$, $p = 0.0625$ (theoretical minimum permutation floor at $n=5$).
  - **Verdict:** Headline $p < 0.01$ is fully supported for the comparison against physical-bin.
- **Comparator 2 (vs. Joint Boundary Router):**
  - Paired difference: $\Delta\text{Cost} = +1{,}959{,}104\text{ kW}\cdot\text{h}$ ($+1.96\text{M kW}\cdot\text{h}$).
  - Seed differences: Seed 201 ($+1.39\text{M}$), 202 ($-5.37\text{M}$), 203 ($-14.56\text{M}$), 204 ($+8.05\text{M}$), 205 ($+20.29\text{M}$).
  - 95% Bootstrap CI: $[-8{,}178{,}424, +12{,}707{,}359]$ (strictly crosses zero).
  - Paired Student-$t$ test ($df=4$): $t = 0.3312$, $p = 0.757$.
  - Exact Wilcoxon signed-rank test: $W=6$, $p = 0.8125$.
  - **Disambiguation Notice:** Manuscript explicitly distinguishes the two comparators: the independent classifier significantly trails physical-bin by $+2.22\text{M}$ ($p=0.0013 < 0.01$), but its difference against the joint boundary router crosses zero ($p=0.757$).

---

## 4. Audit Checklist & Verification Statements

1. **Replication Unit Transparency:** All text reporting seed-level standard deviations explicitly notes that $n=5$ reflects training initialization variance across seeds 201--205, while operational decision intervals reflect paired cluster bootstrap resampling over 35 observed daily clusters (with 1,000 Monte Carlo draws).
2. **Pseudoreplication Elimination:** No $p$-value or standard error is calculated by treating $N=408{,}939$ 10-minute cell measurements as independent and identically distributed observations.
3. **Boundary Population Specification:** All headline numbers ($589{,}535$ and $881{,}367\text{ kW}\cdot\text{h}$) are explicitly qualified with the boundary-active operating condition ($|v_{\text{phys}}-10.5|\le 1.0\text{ m/s}$, $N=13{,}883$ events) across Abstract, Intro, Results, Discussion, Conclusion, and Table captions.
4. **Non-Parametric Floor Disclosure:** The $p=0.0625$ theoretical minimum for $n=5$ two-sided Wilcoxon tests is explicitly documented in the supplementary material and method registry.

---

## 5. Final Statistical Integrity Verdict

**STATISTICAL CLAIM INTEGRITY: PASS**  
Every statistical claim is grounded in verifiable replication units, free of pseudoreplication, bounded by exact confidence intervals, and guarded against overstatement.
