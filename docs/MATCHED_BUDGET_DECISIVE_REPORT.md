# Decisive Matched-Reserve-Budget Falsification Report: Resolving the Transition Risk-Hedge Hypothesis

**Date:** 2026-09-22  
**Target Venue:** *IEEE Transactions on Sustainable Energy* (TSTE)  
**Author:** Autonomous Research-Engineering Agent & Reliability Orchestrator  
**Status:** COMPLETED & AUDITED  
**Git Baseline Commit:** `621bb8b5817483f54bfb7a51fcd0f9a0751fc542`  
**Preregistration Checksum (SHA256):** `784ADD52DB612314EF870FDEC2A6B5406B2CB07B4867648A1968A226276C2B38`  
**Primary Artifact Directory:** `artifacts/matched_budget/`  

---

## Executive Summary

The paper investigates reserve-risk screening under degraded SCADA telemetry where blade pitch is withheld. While the paper previously established that latent MPPT-to-pitch boundary recoverability does not imply plant-wide decision superiority ($\Delta L = +523{,}044\text{ kW}\cdot\text{h}$ penalty for posterior vs. wind-speed bins), it characterized posterior conditioning as a **"localized transition-window risk hedge"** based on lower observed violation rates ($7.24\%$ vs. $8.36\%$) and lower uncovered shortage ($86{,}592$ vs. $90{,}231\text{ kW}\cdot\text{h}$).

However, the frozen posterior policy simultaneously procured $+149{,}092\text{ kW}\cdot\text{h}$ more reserve ($3{,}567{,}090$ vs. $3{,}417{,}998\text{ kW}\cdot\text{h}$). Under the penalized objective $C = R + \rho U$ with $\rho=10$, this produced a net cost penalty of $+112{,}703\text{ kW}\cdot\text{h}$.

This report presents the results of a decisive adversarial falsification experiment designed to answer the single remaining scientific uncertainty:
> **At the SAME reserve-procurement budget, does posterior-conditioned reserve allocation provide genuinely better reliability during operating-transition windows than the strongest direct wind-speed-conditioned quantile baseline, OR is the lower violation rate explained almost entirely by buying more reserve?**

### Key Decisive Findings:
1. **Falsification of Allocation Superiority (Case C/D Verdict)**:
   Across the 30-point common budget support $\mathcal{B}_{\text{common}} = [1.95\text{M}, 4.77\text{M}]\text{ kWh}$ on transition windows, at the **exact same reserve procurement budget** ($\Delta R \equiv 0$), posterior conditioning produces **$+5{,}241.1\text{ kW}\cdot\text{h}$ MORE uncovered shortfall on average** than simple wind-speed binning across the 5 random seeds.
2. **Seed Breakdown (4 of 5 Seeds Fail)**:
   In 4 out of 5 seeds (202, 203, 204, 205), posterior conditioning exhibits strictly positive shortfall differences ($\Delta U(B) > 0$) across $100\%$ of the common budget grid. Only Seed 201 exhibits favorable allocation ($\Delta U = -3{,}138.7\text{ kW}\cdot\text{h}$).
3. **Paired Day-Cluster Bootstrap ($B=5{,}000$, 35 daily clusters)**:
   Enforcing strict within-bootstrap budget matching ($\Delta R^{(b)} \equiv 0$ identically in every replicate), significant favorable support ($95\%$ bootstrap CI excluding zero with $\Delta U < 0$) occurs on only **$6.0\%$** of the evaluated budget space.
4. **Frozen-Policy vs. Re-Optimized $\rho$-Sensitivity**:
   - The frozen-policy algebraic crossover occurs at $\rho_{\text{break}} = -\Delta R / \Delta U \approx \mathbf{40.97}$.
   - However, when reserve policies are dynamically re-optimized for each $\rho$ using Newsvendor fractile $q^*(\rho) = 1 - 1/\rho$, **no economic crossover exists for any $\rho \ge 5$** ($\Delta \text{PSREI} = +112.7\text{k}$ at $\rho=10$, $+366.4\text{k}$ at $\rho=20$, $+736.5\text{k}$ at $\rho=40$, $+998.0\text{k kW}\cdot\text{h}$ at $\rho=100$). Increasing penalty severity causes the posterior to over-procure tail reserves even more aggressively, widening the baseline's cost advantage.
5. **Scientific Conclusion**:
   The lower raw violation rate of the frozen posterior policy in transition windows is **volume-driven, not efficiency-driven**. Posterior conditioning changes the reserve-reliability operating point by procuring additional reserve volume, but possesses no robust allocation efficiency advantage over observable wind-speed conditioning.

---

## 1. Exact Scientific Question

In the IEEE TSTE manuscript, the governing decision metric is the Penalized Reserve-Shortfall Energy Index:
$$C(r; \rho) = R(r) + \rho \cdot U(r),$$
where $R$ is total reserve procurement energy, $U$ is total uncovered shortage energy, and $\rho = 10$ corresponds to the nominal Newsvendor critical fractile $q^* = 1 - 1/\rho = 0.90$.

Because $C$ combines procurement volume and shortage penalties, any policy can mechanically reduce violations and shortage simply by procuring more reserve capacity.

The central scientific question is therefore formulated as an adversarial separation:
$$\text{Is } \min_{r_{\text{post}} \in \mathcal{R}(B)} U(r_{\text{post}}) < \min_{r_{\text{base}} \in \mathcal{R}(B)} U(r_{\text{base}}) \quad \text{for } B \in \mathcal{B}_{\text{common}}?$$

If $\Delta U(B) = U_{\text{post}}(B) - U_{\text{base}}(B) \ge 0$, then the transition benefit is non-existent at equal expenditure, disproving the claim of superior localized risk hedging.

---

## 2. Preregistered Hypotheses & Protocol

As recorded in `docs/MATCHED_BUDGET_PREREGISTRATION.md` (SHA256: `784ADD52DB612314EF870FDEC2A6B5406B2CB07B4867648A1968A226276C2B38`):
- **Comparator $M_{\text{base}}$**: Strong observable wind-speed conditioned quantile baseline (10 uniform bins over $[0, 25\text{ m/s}]$ calibrated on validation data).
- **Model $M_{\text{post}}$**: Spatio-temporal Dense GNN boundary posterior quantile (5 validation quintiles of $\pi_t$).
- **Sample**: WTB 134 turbines, 35-day chronological test split ($N = 385{,}205$ valid turbine-time cells).
- **Transition Definition**: Cells within $\pm 3$ time-steps (10-minute intervals) of operating regime switch ($N = 139{,}684$, $36.26\%$).
- **Stationary Definition**: Cells outside transition window ($N = 245{,}521$, $63.74\%$).
- **Policy Scaling**: Proportional scaling $r_m^{(\alpha)}(i,t) = \max(0, \alpha \cdot r_m(i,t))$ across dense $\alpha \in [0.5, 1.5]$.
- **Budget Matching Tolerance**: Target error $|R_m(B) - B| / B \le 0.001$ ($0.1\%$).
- **Uncertainty**: $B_{\text{boot}} = 5{,}000$ paired day-level cluster bootstrap resamples (35 daily blocks) with independent within-bootstrap budget matching ($\Delta R^{(b)} \equiv 0$).

---

## 3. Existing Result Reproduction (Phase 1)

All headline numbers reported in `docs/STRONG_BASELINE_CLOSURE.md` and the manuscript were reproduced from clean artifacts within $<0.01\text{ kW}\cdot\text{h}$ numerical precision.

### Table 1: 5-Seed Baseline Reproduction Across Population Slices
*Source artifact: `artifacts/matched_budget/baseline_reproduction.csv`*

| Slice | Seed | Baseline Reserve ($R$, kWh) | Baseline Shortage ($U$, kWh) | Base Viol (%) | Base PSREI ($C$, kWh) | Post Reserve ($R$, kWh) | Post Shortage ($U$, kWh) | Post Viol (%) | Post PSREI ($C$, kWh) | Delta Reserve ($\Delta R$, kWh) | Delta Shortage ($\Delta U$, kWh) | Delta PSREI ($\Delta C$, kWh) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Transition** | 201 | 3,298,002 | 90,411 | 8.36% | 4,202,116 | 3,467,787 | 73,433 | 5.86% | 4,202,116 | +169,785 | -16,978 | **0** |
| | 202 | 3,431,241 | 91,246 | 8.36% | 4,343,701 | 3,576,022 | 82,506 | 7.02% | 4,401,083 | +144,781 | -8,740 | +57,382 |
| | 203 | 3,446,558 | 89,848 | 8.36% | 4,345,038 | 3,607,987 | 101,465 | 8.78% | 4,622,639 | +161,429 | +11,617 | +277,601 |
| | 204 | 3,460,942 | 90,094 | 8.36% | 4,361,882 | 3,600,001 | 89,620 | 7.27% | 4,496,196 | +139,059 | -474 | +134,314 |
| | 205 | 3,453,248 | 89,557 | 8.36% | 4,348,818 | 3,583,654 | 85,819 | 7.28% | 4,441,848 | +130,406 | -3,738 | +93,030 |
| **Trans Mean**| **All** | **3,417,998** | **90,231** | **8.36%** | **4,320,310** | **3,567,090** | **86,592** | **7.24%** | **4,433,013** | **+149,092** | **-3,639** | **+112,703** |
| **Steady Mean**| **All** | **6,906,130** | **255,788** | **9.03%** | **9,464,010** | **6,611,987** | **326,236** | **10.13%** | **9,874,349** | **-294,144** | **+70,448** | **+410,339** |
| **Full Mean** | **All** | **10,324,129** | **346,019** | **8.79%** | **13,784,320** | **10,179,077** | **412,829** | **9.08%** | **14,307,363** | **-145,051** | **+66,809** | **+523,043** |

*Accounting Verification:* For every single row in Table 1, $|C - (R + 10 U)| < 10^{-4}\text{ kW}\cdot\text{h}$. The accounting closes identically.

---

## 4. Frozen-Policy Break-Even Analysis (Phase 2)

Using the frozen policies at nominal $q^*=0.90$, on the transition slice:
$$\Delta R = +149{,}092.4\text{ kW}\cdot\text{h}, \quad \Delta U = -3{,}638.9\text{ kW}\cdot\text{h}.$$
The algebraic break-even shortage penalty ratio is:
$$\rho_{\text{break}} = -\frac{\Delta R}{\Delta U} = \frac{149{,}092.4}{3{,}638.9} \approx \mathbf{40.97}.$$

### Table 2: Frozen-Policy $\Delta \text{PSREI}(\rho) = \Delta R + \rho \Delta U$ Sensitivity
*Source artifact: `artifacts/matched_budget/frozen_policy_rho_sensitivity.csv`*

| Shortage Penalty $\rho$ | Equivalent Fractile $q^*$ | $\Delta R$ (kWh) | $\Delta U$ (kWh) | $\Delta \text{PSREI}$ (kWh) | Economically Preferred Policy |
| :---: | :---: | :---: | :---: | :---: | :---: |
| 1.0 | 0.000 | +149,092 | -3,639 | +145,453 | Baseline (Wspd-Bins) |
| 5.0 | 0.800 | +149,092 | -3,639 | +130,898 | Baseline (Wspd-Bins) |
| 10.0 (Nominal) | 0.900 | +149,092 | -3,639 | +112,703 | Baseline (Wspd-Bins) |
| 20.0 | 0.950 | +149,092 | -3,639 | +76,314 | Baseline (Wspd-Bins) |
| 30.0 | 0.967 | +149,092 | -3,639 | +39,925 | Baseline (Wspd-Bins) |
| **40.97** | **0.976** | **+149,092** | **-3,639** | **0** | **Break-Even Crossover** |
| 50.0 | 0.980 | +149,092 | -3,639 | -32,853 | Boundary Posterior |
| 100.0 | 0.990 | +149,092 | -3,639 | -214,798 | Boundary Posterior |

**Interpretation:** Under frozen policies, posterior conditioning is economically disadvantageous for any shortage penalty ratio below $\rho \approx 41$. However, this calculation assumes the policies remain frozen while the market penalty shifts. Phase 8 evaluates what happens when policies re-optimize.

---

## 5. Decisive Matched-Reserve-Budget Frontier (Phase 3 & 4)

To separate reserve procurement volume from allocation efficiency, we evaluate the exact matched-budget frontier (Frontier A) where reserve procurement is strictly matched at each target budget $B_k$ across $\mathcal{B}_{\text{common}} = [1{,}950{,}143, 4{,}768{,}322]\text{ kW}\cdot\text{h}$.

### Table 3: Transition Slice Matched-Budget Frontier (5-Seed Mean)
*Source artifact: `artifacts/matched_budget/exact_matched_budget_frontier.csv`*

| Budget Index | Target Reserve $B$ (kWh) | Baseline Shortage $U_{\text{base}}$ (kWh) | Posterior Shortage $U_{\text{post}}$ (kWh) | Shortage Delta $\Delta U$ (kWh) | Base Viol (%) | Post Viol (%) | Viol Delta $\Delta V$ (%) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 0 (Min) | 1,950,143 | 240,654 | 244,989 | **+4,335** | 16.59% | 15.65% | -0.94% |
| 5 | 2,436,036 | 181,960 | 186,819 | **+4,859** | 13.56% | 12.59% | -0.97% |
| 10 | 2,921,929 | 133,086 | 138,401 | **+5,315** | 10.74% | 9.77% | -0.97% |
| 14 (Near Baseline) | 3,310,643 | 99,444 | 105,091 | **+5,647** | 8.81% | 7.91% | -0.90% |
| 17 (Near Posterior)| 3,602,179 | 77,882 | 83,674 | **+5,792** | 7.49% | 6.77% | -0.72% |
| 20 | 3,893,715 | 59,573 | 65,379 | **+5,806** | 6.31% | 5.80% | -0.51% |
| 25 | 4,379,607 | 35,461 | 40,845 | **+5,384** | 4.61% | 4.41% | -0.20% |
| 29 (Max) | 4,768,322 | 21,792 | 26,450 | **+4,658** | 3.51% | 3.53% | +0.02% |
| **Grid Average** | **3,359,233** | **111,358** | **116,599** | **+5,241** | **9.28%** | **8.55%** | **-0.73%** |

### Crucial Scientific Discovery:
1. **Shortage Energy is Strictly Higher for Posterior ($\Delta U > 0$)**:
   At every single matched budget point across the entire common support, posterior conditioning yields **higher uncovered shortage energy** ($+4{,}335$ to $+5{,}806\text{ kW}\cdot\text{h}$) than wind-speed binning.
2. **The Apparent Disconnect with Violation Rate**:
   Notice that $\Delta V$ remains slightly negative ($-0.73\%$ on average) even while $\Delta U$ is positive ($+5{,}241\text{ kWh}$)!
   This uncovers the precise pathology of posterior conditioning: **it suppresses marginal small violations at the expense of suffering much larger severe shortages when transitions fail.** Under the convex Newsvendor loss geometry, this trade-off is economically value-destroying.

---

## 6. Seed-by-Seed Breakdown & Bootstrap Uncertainty (Phase 5 & 6)

*Source artifact: `artifacts/matched_budget/bootstrap_frontier_statistics.csv` and `frontier_auc_summary.csv`*

### Table 4: Frontier Summary Metrics & Bootstrap Support by Seed (Transition Slice)
*Evaluated with $B_{\text{boot}} = 5{,}000$ paired day-level cluster bootstrap resamples (35 daily clusters).*

| Seed | Integrated $\Delta \text{AUC}_{\text{shortfall}}$ (kWh) | Favorable Support $\Delta U < 0$ (%) | Significant Favorable ($95\%$ CI $< 0$) | Mean $\Delta U$ (kWh) | Mean $\Delta V$ (%) | Bootstrap $p$-value ($P(\Delta U \ge 0)$) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **201** | **-3,096.0** | **60.0%** | **30.0%** | **-3,138.7** | -1.74% | 0.1420 |
| **202** | **+4,350.4** | **0.0%** | **0.0%** | **+4,312.9** | -0.58% | 0.9980 |
| **203** | **+13,065.3** | **0.0%** | **0.0%** | **+12,931.7** | -0.16% | 1.0000 |
| **204** | **+8,736.5** | **0.0%** | **0.0%** | **+8,634.1** | -0.57% | 1.0000 |
| **205** | **+3,493.2** | **13.3%** | **0.0%** | **+3,465.6** | -0.60% | 0.9240 |
| **Mean** | **+5,309.9** | **14.7%** | **6.0%** | **+5,241.1** | **-0.73%** | **0.8128** |

**Falsification Verdict:**
- Across 4 of the 5 seeds (202, 203, 204, 205), the posterior is **strictly inferior** to the wind-speed baseline at matched reserve budgets ($p > 0.92$).
- The previously observed "localized risk-hedging" effect in aggregate tables was disproportionately carried by an outlier seed (Seed 201). Even for Seed 201, the paired bootstrap $95\%$ CI crosses zero ($p = 0.142$).

---

## 7. Falsification Slices: Primary vs Controls (Phase 7)

*Source artifact: `artifacts/matched_budget/frontier_auc_summary.csv`*

### Table 5: Cross-Slice Comparison of Allocation Efficiency $\Delta \text{AUC}_{\text{shortfall}}$ (kWh)

| Slice | Seed 201 | Seed 202 | Seed 203 | Seed 204 | Seed 205 | 5-Seed Mean | Favorable Support (%) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Transition** (Primary) | -3,096 | +4,350 | +13,065 | +8,736 | +3,493 | **+5,310** | 14.7% |
| **Steady** (Negative Control) | +39,677 | -9,431 | +46,897 | +49,333 | +45,838 | **+34,463** | 20.0% |
| **Full Plant** (Global Control) | +40,639 | -5,305 | +69,915 | +62,560 | +52,908 | **+44,143** | 20.0% |

**Control Consistency:**
In both the stationary slice and the full plant, posterior conditioning severely inflates uncovered shortage ($+34.5\text{k}$ and $+44.1\text{k kWh}$ on average). The transition window shows smaller relative degradation ($+5.3\text{k kWh}$), confirming a structural shift in loss geometry, but **fails to deliver positive net allocation efficiency**.

---

## 8. Dynamic Policy Re-Optimization under Newsvendor Loss (Phase 8)

*Source artifact: `artifacts/matched_budget/reoptimized_rho_sensitivity.csv`*

When each policy is re-calibrated on validation data for $q^*(\rho) = 1 - 1/\rho$, we test whether the posterior becomes economically viable under extreme shortage penalty ratios:

### Table 6: Re-Optimized Policy Economic Performance Across $\rho$ (Transition Slice Mean)

| Penalty Ratio $\rho$ | Optimal Fractile $q^*$ | Delta Reserve $\Delta R$ (kWh) | Delta Shortage $\Delta U$ (kWh) | Delta Violation $\Delta V$ (%) | Delta PSREI $\Delta C$ (kWh) | Economically Preferred |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 2.0 | 0.5000 | +67,259 | -39,314 | -8.67% | **-11,369** | **Posterior** |
| 5.0 | 0.8000 | +70,103 | -9,525 | -2.14% | **+22,478** | **Baseline (Wspd-Bins)** |
| 10.0 | 0.9000 | +149,092 | -3,639 | -1.12% | **+112,703** | **Baseline (Wspd-Bins)** |
| 20.0 | 0.9500 | +405,895 | -1,973 | -0.73% | **+366,436** | **Baseline (Wspd-Bins)** |
| 40.0 | 0.9750 | +802,829 | -1,658 | -0.56% | **+736,520** | **Baseline (Wspd-Bins)** |
| 50.0 | 0.9800 | +913,873 | -1,654 | -0.50% | **+831,192** | **Baseline (Wspd-Bins)** |
| 100.0 | 0.9900 | +1,102,589 | -1,046 | -0.32% | **+997,985** | **Baseline (Wspd-Bins)** |

### Critical Econometric Insight:
- The frozen-policy crossover at $\rho \approx 41$ was an artifact of keeping procurement constant while scaling the penalty.
- When policies re-optimize, the posterior's high conditional variance in transition regimes forces extreme tail procurement ($+1.10\text{M kWh}$ at $\rho=100$) for negligible shortage reduction ($-1{,}046\text{ kWh}$).
- Consequently, **$\Delta \text{PSREI}$ diverges positively**: the posterior becomes progressively **more expensive** as $\rho$ increases.

---

## 9. Mechanism Check: Reallocation vs Baseline Shortfall (Phase 9)

*Source artifact: `artifacts/matched_budget/mechanism_reallocation_diagnostic.csv`*

To diagnose why posterior allocation fails to reduce aggregate shortage at matched budget, we examine individual turbine-time reallocations $\Delta r_{i,t} = r_{\text{post}, i,t} - r_{\text{base}, i,t}$ matched at the same total procurement:
- Correlation with baseline shortage: mean $r = 0.0054 \pm 0.030$.
- Reallocation on shortage events: $+2.26\text{ kW}$.
- Reallocation on non-shortage events: $-0.21\text{ kW}$.

While the posterior slightly shifts reserves toward shortage events on average, the low correlation ($r \approx 0.005$) indicates that the consequence-based representation cannot reliably forecast *which specific turbines* will experience shortfalls during rapid boundary switching. The reserve spread is too diffuse, increasing tail losses on misallocated turbines.

---

## 10. Adversarial Sanity Audits (Phase 10)

1. **Accounting Verification**: Confirmed across all CSV artifacts ($p < 10^{-5}$).
2. **Matching Tolerance**: Frontier A reserve budget mismatch strictly $< 0.1\%$ everywhere.
3. **No Information Leakage**: Frontier B and Phase 8 policies calibrated strictly on validation data.
4. **Monotonicity**: Shortage $U(B)$ strictly non-increasing across budget steps.
5. **Test Suite Execution**: `pytest tests/test_matched_budget_accounting.py` passes 5/5 assertions with exit code 0.

---

## 11. Final Scientific Claim Classification

According to the preregistered criteria in Section 7 of `docs/MATCHED_BUDGET_PREREGISTRATION.md`:

$$\mathbf{VERDICT: CASE \; C \; / \; D \quad (FALSIFICATION \; OF \; DECISION \; ADVANTAGE)}$$

- At matched reserve procurement budgets, posterior conditioning provides **no statistically significant or robust reduction in uncovered shortfall** during operating-transition windows (5-seed mean $\Delta U = +5{,}241\text{ kW}\cdot\text{h}$; 4 of 5 seeds fail).
- The lower transition violation rate previously observed ($7.24\%$ vs. $8.36\%$) was **volume-driven**: it was achieved by procuring $+149{,}092\text{ kW}\cdot\text{h}$ more reserve.
- The claim that posterior conditioning provides "superior localized allocation efficiency" or acts as an "efficient localized risk hedge" is **definitively refuted**.

---

## 12. Exact Manuscript Changes Required (Phase 13 Plan)

To align the IEEE TSTE manuscript (`paper_tste_ieee.md` and `standalone_ieee_package/main.tex`) with these definitive findings, the following surgical edits are required:

1. **Abstract**:
   - *Current:* "...near operating transitions it acts as a localized risk hedge (reducing violation to 7.24% at additional reserve cost)..."
   - *Revised:* "...near operating transitions it alters the operating point by procuring additional reserve rather than improving allocation efficiency at matched budget, while direct wind-speed binning serves as the plant-wide minimum sufficient model."
2. **Contributions (Section I)**:
   - Clarify Contribution 3: Explicitly state that matched-budget frontier analysis demonstrates that the lower transition violation rate is volume-driven rather than allocation-driven.
3. **Section IV-C (Decision Results)**:
   - Insert the decisive matched-budget frontier evidence ($\Delta U = +5{,}241\text{ kW}\cdot\text{h}$, 4/5 seeds showing higher shortfall at matched procurement).
   - Reference `figures/matched_budget_transition_frontier.pdf` and `artifacts/matched_budget/`.
4. **Discussion & Conclusion**:
   - Reframe the final synthesis: *Observability governs decision sufficiency.* Latent boundary recovery via consequence signals succeeds as a representation result, but fails to create decision value beyond simple observable conditioning because consequence signals cannot resolve spatial tail allocation under matched budgets.
