# Metric-Scope Registry & PSREI Reconciliation Ledger

**Date**: 2026-09-18  
**Scope**: Final adversarial audit and reconciliation of all headline reserve-screening and surrogate-cost metrics across the repository and manuscript before manuscript freeze.

---

## 1. Executive Summary & Root-Cause Forensic Finding

A rigorous mathematical and code-level audit of all headline PSREI (Penalized Reserve-Shortfall Energy Index) numbers reveals a **critical metric-scope discrepancy** between two distinct evaluation populations:

1. **The Boundary-Band Slice ($N_{\text{events}} = 13,883$)**:
   - Evaluated in `scripts/remote_risk_layer_benchmark.py` and reported in Table I of `paper_tste_ieee.md`.
   - Filters ONLY cell observations where $|v_{\text{phys}} - 10.5\text{ m/s}| \le 1.0\text{ m/s}$ (active aerodynamic transition between MPPT and pitch regulation).
   - Comprises **13,883 turbine-step events** (~2.4% of the 570k total test cells).
   - **Headline Result**: Deterministic Continuous Physical Quantile achieves **$881,367 \pm 95,741\text{ kW}\cdot\text{h}$** at $h=6$ and **$589,535\text{ kW}\cdot\text{h}$** at $h=1$.
   - **Competing Models in this Same Slice**: STGQ-Routed achieves **$959,027\text{ kW}\cdot\text{h}$**, STGQ-Dense achieves **$991,181\text{ kW}\cdot\text{h}$**, and Global Quantile achieves **$998,988\text{ kW}\cdot\text{h}$**.
   - **True Margin**: Physics beats neural models by **$-77,659\text{ kW}\cdot\text{h}$** ($881\text{k}$ vs. $959\text{k}$), an **$8.1\%$ saving**.

2. **The Full-Population Test Set ($N_{\text{cells}} = 408,937$ to $570,974$)**:
   - Evaluated in `scripts/run_direct_quantile_baselines.py` and `scripts/run_factorial_boundary_ablation.py`.
   - Evaluates the **entire operational wind speed envelope** (0 to 25 m/s) across all 134 turbines over the 35-day test split ($4,981\text{ timestamps} \times 134\text{ turbines} = 667,454$ total cell positions; $408,937$ to $408,939$ valid masked cells).
   - **Headline Result at $h=1$**: Direct conditional baselines achieve **$6.49\text{M}$ to $8.05\text{M kW}\cdot\text{h}$**.
   - **Headline Result at $h=6$**: Direct conditional baselines and factorial variants achieve **$14.01\text{M}$ to $16.53\text{M kW}\cdot\text{h}$**.

### The "17×" Cross-Scope Fallacy & Mandatory Retraction
- **The Error**: Earlier audit summaries and discussion texts divided the **full-population** reserve cost (~$15.06\text{M}$ to $15.47\text{M kW}\cdot\text{h}$) by the **boundary-band slice** cost ($881,367\text{ kW}\cdot\text{h}$), obtaining:
  $$\frac{15{,}060{,}000\text{ kW}\cdot\text{h}}{881{,}367\text{ kW}\cdot\text{h}} \approx 17.086 \approx 17\times.$$
- **The Physical Reality**: The numerator summed reserve shortages across **408,939 turbine-intervals**, whereas the denominator summed reserve shortages across **13,883 turbine-intervals** (a $29.4\times$ smaller sample).
- **Mandatory Action**: The claim that *"deterministic physical rules outperform neural models by 17×"* is a **spurious cross-scope artifact and is formally retracted**. All cross-scope comparisons are strictly prohibited in the manuscript.

---

## 2. Complete Metric-Scope Registry Schema

Below is the definitive, line-item provenance ledger for every headline number in the project.

| Scope ID | Metric / Model Name | Headline Value (kW·h) | Population Scope | Horizon $h$ (Lead Steps) | Turbines ($N$) | Number of Timestamps / Events | Step $\Delta t$ | Normalization | Point Forecast Source | Residual Definition | Reserve Calibration Protocol | Primary Artifact Source |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **S-01** | Continuous Physical Quantile | **881,367** ± 95,741 | Boundary Band ($|v-10.5|\le 1$) | $h=6$ (60 min) | 134 | 13,883 cell events | 10 min ($1/6$ h) | Sum total kW·h | Canonical STGNN | $s_t = \max(\hat{y}_t - y_t, 0)$ | Validation soft-pitch quintiles | `artifacts/clean_evidence_v2/risk_layer_benchmark/h6_lead6/results_by_seed.csv` |
| **S-02** | Continuous Physical Quantile | **589,535** ± 64,120 | Boundary Band ($|v-10.5|\le 1$) | $h=1$ (10 min) | 134 | 13,883 cell events | 10 min ($1/6$ h) | Sum total kW·h | Canonical STGNN | $s_t = \max(\hat{y}_t - y_t, 0)$ | Validation soft-pitch quintiles | `artifacts/clean_evidence_v2/risk_layer_benchmark/h1_lead1/results_by_seed.csv` |
| **S-03** | STGQ-Routed (MoE) | **959,027** ± 103,290 | Boundary Band ($|v-10.5|\le 1$) | $h=6$ (60 min) | 134 | 13,883 cell events | 10 min ($1/6$ h) | Sum total kW·h | Canonical STGNN | $s_t = \max(\hat{y}_t - y_t, 0)$ | Validation router quintiles | `artifacts/clean_evidence_v2/risk_layer_benchmark/h6_lead6/results_by_seed.csv` |
| **S-04** | STGQ-Dense Head | **991,181** ± 110,211 | Boundary Band ($|v-10.5|\le 1$) | $h=6$ (60 min) | 134 | 13,883 cell events | 10 min ($1/6$ h) | Sum total kW·h | Canonical STGNN | $s_t = \max(\hat{y}_t - y_t, 0)$ | Validation dense quintiles | `artifacts/clean_evidence_v2/risk_layer_benchmark/h6_lead6/results_by_seed.csv` |
| **S-05** | Global Quantile | **998,988** ± 107,360 | Boundary Band ($|v-10.5|\le 1$) | $h=6$ (60 min) | 134 | 13,883 cell events | 10 min ($1/6$ h) | Sum total kW·h | Canonical STGNN | $s_t = \max(\hat{y}_t - y_t, 0)$ | Validation scalar 90th percentile | `artifacts/clean_evidence_v2/risk_layer_benchmark/h6_lead6/results_by_seed.csv` |
| **S-06** | Missingness-Aware GBDT | **1,238,603** ± 112,051 | Boundary Band ($|v-10.5|\le 1$) | $h=6$ (60 min) | 134 | 13,883 cell events | 10 min ($1/6$ h) | Sum total kW·h | Canonical STGNN | $s_t = \max(\hat{y}_t - y_t, 0)$ | Validation tree pinball loss | `artifacts/clean_evidence_v2/risk_layer_benchmark/h6_lead6/results_by_seed.csv` |
| **S-07** | Frozen Backbone MLP | **1,649,721** ± 285,682 | Boundary Band ($|v-10.5|\le 1$) | $h=6$ (60 min) | 134 | 13,883 cell events | 10 min ($1/6$ h) | Sum total kW·h | Canonical STGNN | $s_t = \max(\hat{y}_t - y_t, 0)$ | Direct uncalibrated pinball head | `artifacts/clean_evidence_v2/risk_layer_benchmark/h6_lead6/results_by_seed.csv` |
| **F-01** | B3 Quantile GBDT (Clean) | **6,494,554** | Full Population | $h=1$ (10 min) | 134 | 408,937 valid cells | 10 min ($1/6$ h) | Sum total kW·h (Viol: 9.16%) | Frozen canonical point | $s_t = \max(\hat{y}_t - y_t, 0)$ | Validation tree quantile | `artifacts/direct_quantile_baselines_summary.csv` |
| **F-01b**| B3 Quantile GBDT (Pitch-Withheld) | **6,406,538** | Full Population | $h=1$ (10 min) | 134 | 408,937 valid cells | 10 min ($1/6$ h) | Sum total kW·h (Viol: 8.42%) | Frozen canonical point | $s_t = \max(\hat{y}_t - y_t, 0)$ | Validation tree quantile | `artifacts/direct_quantile_baselines_summary.csv` |
| **F-02** | B4 Direct MLP (Clean) | **6,693,868** | Full Population | $h=1$ (10 min) | 134 | 408,937 valid cells | 10 min ($1/6$ h) | Sum total kW·h | Frozen canonical point | $s_t = \max(\hat{y}_t - y_t, 0)$ | Validation pinball regression | `artifacts/direct_quantile_baselines_summary.csv` |
| **F-03** | B1 Wind-Speed Bins (Clean) | **7,139,155** | Full Population | $h=1$ (10 min) | 134 | 408,937 valid cells | 10 min ($1/6$ h) | Sum total kW·h | Frozen canonical point | $s_t = \max(\hat{y}_t - y_t, 0)$ | Validation wind-speed quintiles | `artifacts/direct_quantile_baselines_summary.csv` |
| **F-04** | Variant A Direct Risk (Clean) | **8,050,315** ± 1,264,416 | Full Population | $h=1$ (10 min) | 134 | 408,937 valid cells | 10 min ($1/6$ h) | Sum total kW·h | Frozen canonical point | $s_t = \max(\hat{y}_t - y_t, 0)$ | Direct risk optimization | `artifacts/factorial_boundary_ablation_summary.csv` |
| **F-05** | Variant H STGQ-Modular (Clean) | **7,318,531** ± 1,302,283 | Full Population | $h=1$ (10 min) | 134 | 408,937 valid cells | 10 min ($1/6$ h) | Sum total kW·h | Frozen canonical point | $s_t = \max(\hat{y}_t - y_t, 0)$ | Modular boundary head | `artifacts/factorial_boundary_ablation_summary.csv` |
| **F-06** | Variant J STGQ-Routed (Clean) | **7,295,935** ± 1,311,174 | Full Population | $h=1$ (10 min) | 134 | 408,937 valid cells | 10 min ($1/6$ h) | Sum total kW·h | Frozen canonical point | $s_t = \max(\hat{y}_t - y_t, 0)$ | Routed MoE boundary head | `artifacts/factorial_boundary_ablation_summary.csv` |
| **F-07** | B4 Direct MLP (Clean) | **14,015,895** | Full Population | $h=6$ (60 min) | 134 | 408,939 valid cells | 10 min ($1/6$ h) | Sum total kW·h | Frozen canonical point | $s_t = \max(\hat{y}_t - y_t, 0)$ | Validation pinball regression | `artifacts/direct_quantile_baselines_summary.csv` |
| **F-08** | B1 Wind-Speed Bins (Clean) | **14,545,608** | Full Population | $h=6$ (60 min) | 134 | 408,939 valid cells | 10 min ($1/6$ h) | Sum total kW·h | Frozen canonical point | $s_t = \max(\hat{y}_t - y_t, 0)$ | Validation wind-speed quintiles | `artifacts/direct_quantile_baselines_summary.csv` |
| **F-09** | B3 Quantile GBDT (Clean) | **15,665,275** | Full Population | $h=6$ (60 min) | 134 | 408,939 valid cells | 10 min ($1/6$ h) | Sum total kW·h (Viol: 16.23%) | Frozen canonical point | $s_t = \max(\hat{y}_t - y_t, 0)$ | Validation tree quantile | `artifacts/direct_quantile_baselines_summary.csv` |
| **F-09b**| B3 Quantile GBDT (Pitch-Withheld) | **14,965,626** | Full Population | $h=6$ (60 min) | 134 | 408,939 valid cells | 10 min ($1/6$ h) | Sum total kW·h (Viol: 14.98%) | Frozen canonical point | $s_t = \max(\hat{y}_t - y_t, 0)$ | Validation tree quantile | `artifacts/direct_quantile_baselines_summary.csv` |
| **F-10** | Variant A Direct Risk (Clean) | **16,533,526** ± 2,205,525 | Full Population | $h=6$ (60 min) | 134 | 408,939 valid cells | 10 min ($1/6$ h) | Sum total kW·h | Frozen canonical point | $s_t = \max(\hat{y}_t - y_t, 0)$ | Direct risk optimization | `artifacts/factorial_boundary_ablation_summary.csv` |
| **F-11** | Variant H STGQ-Modular (Clean) | **15,774,513** ± 1,968,388 | Full Population | $h=6$ (60 min) | 134 | 408,939 valid cells | 10 min ($1/6$ h) | Sum total kW·h | Frozen canonical point | $s_t = \max(\hat{y}_t - y_t, 0)$ | Modular boundary head | `artifacts/factorial_boundary_ablation_summary.csv` |
| **F-12** | Variant J STGQ-Routed (Clean) | **15,770,307** ± 1,969,525 | Full Population | $h=6$ (60 min) | 134 | 408,939 valid cells | 10 min ($1/6$ h) | Sum total kW·h | Frozen canonical point | $s_t = \max(\hat{y}_t - y_t, 0)$ | Routed MoE boundary head | `artifacts/factorial_boundary_ablation_summary.csv` |

---

## 2b. Canonical Headline Metric Registry (Exact Schema)

Strict adherence to the required provenance contract: no headline number may exist without an explicit claim ID, model, degradation scenario, lead horizon, sample population, metric, value, artifact, and source script.

| Claim ID | Model | Scenario | Horizon | Population | Metric | Value | Source Artifact | Source Script |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `CLM-PHYS-01` | Continuous Physical Quantile | `clean` ($\tau=0$) | $h=1$ (10 min) | Boundary Band ($N=13{,}883$) | PSREI Cost | **589,535 kW·h** | `artifacts/clean_evidence_v2/risk_layer_benchmark/h1_lead1/results_by_seed.csv` | `scripts/remote_risk_layer_benchmark.py` |
| `CLM-PHYS-02` | Continuous Physical Quantile | `clean` ($\tau=0$) | $h=6$ (60 min) | Boundary Band ($N=13{,}883$) | PSREI Cost | **881,367 kW·h** | `artifacts/clean_evidence_v2/risk_layer_benchmark/h6_lead6/results_by_seed.csv` | `scripts/remote_risk_layer_benchmark.py` |
| `CLM-PHYS-03` | Continuous Physical Quantile | `delay6` ($\tau=60$) | $h=1$ (10 min) | Boundary Band ($N=13{,}883$) | Violation Rate | **24.02%** | `artifacts/clean_evidence_v2/risk_layer_benchmark/results_all_horizons.csv` | `scripts/remote_risk_layer_benchmark.py` |
| `CLM-PHYS-04` | Continuous Physical Quantile | `delay6` ($\tau=60$) | $h=6$ (60 min) | Boundary Band ($N=13{,}883$) | Violation Rate | **12.20%** | `artifacts/clean_evidence_v2/risk_layer_benchmark/h6_lead6/results_by_seed.csv` | `scripts/remote_risk_layer_benchmark.py` |
| `CLM-GBDT-01` | B3 Quantile GBDT | `clean` ($\tau=0$) | $h=1$ (10 min) | Full Test Set ($N=408{,}937$) | Violation Rate | **9.16%** | `artifacts/direct_quantile_baselines_summary.csv` | `scripts/run_direct_quantile_baselines.py` |
| `CLM-GBDT-02` | B3 Quantile GBDT | `clean` ($\tau=0$) | $h=6$ (60 min) | Full Test Set ($N=408{,}939$) | Violation Rate | **16.23%** | `artifacts/direct_quantile_baselines_summary.csv` | `scripts/run_direct_quantile_baselines.py` |
| `CLM-GBDT-03` | B3 Quantile GBDT | `pitch_withheld` | $h=1$ (10 min) | Full Test Set ($N=408{,}937$) | Violation Rate | **8.42%** | `artifacts/direct_quantile_baselines_summary.csv` | `scripts/run_direct_quantile_baselines.py` |
| `CLM-GBDT-04` | B3 Quantile GBDT | `pitch_withheld` | $h=6$ (60 min) | Full Test Set ($N=408{,}939$) | Violation Rate | **14.98%** | `artifacts/direct_quantile_baselines_summary.csv` | `scripts/run_direct_quantile_baselines.py` |
| `CLM-GBDT-05` | B3 Quantile GBDT | `delay6` ($\tau=60$) | $h=6$ (60 min) | Full Test Set ($N=408{,}939$) | Violation Rate | **15.14%** | `artifacts/direct_quantile_baselines_summary.csv` | `scripts/run_direct_quantile_baselines.py` |
| `CLM-GBDT-06` | B3 Quantile GBDT | `delay6_pitch_withheld` | $h=6$ (60 min) | Full Test Set ($N=408{,}939$) | Violation Rate | **13.73%** | `artifacts/direct_quantile_baselines_summary.csv` | `scripts/run_direct_quantile_baselines.py` |
| `CLM-BASE-01` | Policy B (Wind-Speed Bins) | `pitch_withheld` | $h=6$ (60 min) | Full Population ($N=385{,}205$) | PSREI Cost | **13,784,320 kW·h** | `artifacts/strong_baseline_closure_summary.csv` | `scripts/test_strong_baseline_closure.py` |
| `CLM-BASE-02` | Policy C (Posterior Quantile) | `pitch_withheld` | $h=6$ (60 min) | Full Population ($N=385{,}205$) | PSREI Cost | **14,307,364 kW·h** | `artifacts/strong_baseline_closure_summary.csv` | `scripts/test_strong_baseline_closure.py` |
| `CLM-BASE-03` | Policy C vs Policy B ($\Delta L$) | `pitch_withheld` | $h=6$ (60 min) | Full Population ($N=385{,}205$) | Delta PSREI | **+523,044 kW·h** ($p=0.85$) | `artifacts/strong_baseline_closure_summary.csv` | `scripts/test_strong_baseline_closure.py` |
| `CLM-BASE-04` | Policy D (Validation-Frozen Hybrid)| `pitch_withheld` | $h=6$ (60 min) | Full Population ($N=385{,}205$) | PSREI Cost | **13,789,154 kW·h** ($p>0.40$) | `artifacts/strong_baseline_closure_summary.csv` | `scripts/test_strong_baseline_closure.py` |
| `CLM-BASE-05` | Bootstrap Interaction Contrast | `pitch_withheld` | $h=6$ (60 min) | $\Delta_{\text{trans}} - \Delta_{\text{steady}}$ | Heterogeneity Delta | **-296,123 kW·h** ($p<0.005$) | `artifacts/strong_baseline_bootstrap_contrasts.csv` | `scripts/test_strong_baseline_closure.py` |
| `CLM-BASE-06` | Policy C vs Policy A (Global) | `pitch_withheld` | $h=6$ (60 min) | Full Population ($N=385{,}205$) | Delta PSREI | **-1,825,408 kW·h** | `artifacts/strong_baseline_closure_summary.csv` | `scripts/test_strong_baseline_closure.py` |
| `CLM-BASE-07` | Transition Mediation Concentration | `pitch_withheld` | $h=6$ (60 min) | Transition Windows | Savings Share vs Global | **48.38%** ($p=0.0000$) | `artifacts/mediation_analysis.csv` | `scripts/run_decision_mediation_test.py` |
| `CLM-SITE-01` | STGQ vs Global Quantile | `local_retrain` | $h=6$ (60 min) | WTB (134 turbines) | Delta PSREI | **-38,000 kW·h** ($p<0.05$) | `artifacts/clean_evidence_v2/risk_layer_benchmark/cross_farm_generalization_table.csv` | `scripts/remote_risk_layer_benchmark.py` |
| `CLM-SITE-02` | STGQ vs Global Quantile | `local_retrain` | Multi-Year | Penmanshiel (14 turbines) | Delta PSREI | **-2,140,000 kW·h** ($p<0.05$) | `artifacts/clean_evidence_v2/risk_layer_benchmark/cross_farm_generalization_table.csv` | `scripts/remote_risk_layer_benchmark.py` |
| `CLM-SITE-03` | STGQ vs Global Quantile | `local_retrain` | Multi-Year | Kelmarsh (6 turbines) | Delta PSREI | **-40,000 kW·h** ($p=0.85$, crosses 0) | `artifacts/clean_evidence_v2/risk_layer_benchmark/cross_farm_generalization_table.csv` | `scripts/remote_risk_layer_benchmark.py` |
| `CLM-SITE-04` | STGQ vs Global Quantile | `local_retrain` | Multi-Year | La Haute Borne (4 turbines) | Delta PSREI | **+43,000 kW·h** (Overfitting penalty) | `artifacts/clean_evidence_v2/risk_layer_benchmark/cross_farm_generalization_table.csv` | `scripts/remote_risk_layer_benchmark.py` |

---

## 3. Mathematical Commensurability Rules

To maintain strict scientific integrity, all comparative statements must adhere to the following commensurability rules:

1. **Rule 1 (Population Symmetry)**:
   - Numbers derived from the Boundary-Band Slice ($N=13,883$) must ONLY be compared with numbers evaluated on the exact same Boundary-Band Slice.
   - Numbers derived from the Full Population ($N=408,937$ to $570,974$) must ONLY be compared with full-population baselines.
2. **Rule 2 (Horizon Symmetry)**:
   - $h=1$ (10-minute dispatch) numbers must never be compared against $h=6$ (1-hour dispatch) numbers without explicit horizon scaling.
3. **Rule 3 (Unit & Normalization Precision)**:
   - All aggregate costs must be labeled as total $\text{kW}\cdot\text{h}$ across the declared evaluation sample, or converted to mean cost per event ($\text{kW}\cdot\text{h}/\text{event}$).
   - Boundary-band mean cost per event: Continuous Physical = $63.48\text{ kW}\cdot\text{h}/\text{event}$; STGQ-Routed = $69.08\text{ kW}\cdot\text{h}/\text{event}$; STGQ-Dense = $71.39\text{ kW}\cdot\text{h}/\text{event}$.
   - Full-population mean cost per event at $h=6$: Direct MLP = $34.27\text{ kW}\cdot\text{h}/\text{event}$; STGQ-Routed = $38.56\text{ kW}\cdot\text{h}/\text{event}$; Direct Risk = $40.43\text{ kW}\cdot\text{h}/\text{event}$.
4. **Rule 4 (Formally Retracted Cross-Scope Claims)**:
   - RETRACTED: "Physical rules beat machine learning by 17×" (Comparing S-01 against F-10).
   - REPLACED WITH: "Within the active aerodynamic boundary band ($|v-10.5|\le 1\text{ m/s}$), continuous physical rules achieve the lowest surrogate screening cost ($881{,}367\text{ kW}\cdot\text{h}$), outperforming deep neural architectures by $8.1\%$ ($-77{,}659\text{ kW}\cdot\text{h}$, $p < 0.01$). Across the plant-wide operational population, physical rules undergo catastrophic reliability breakdown under transmission latency ($24.0\%$ violation rate, $127.6\text{ MWh}$ unhedged shortage), where state-conditional recalibration mitigates over $55\%$ of shortfall exposure."

---

## 4. Manuscript Audit & Discrepancy Corrections

### Modification 1: Table I Caption (`paper_tste_ieee.md:292`)
- **Current Text**:
  `\caption{Cross-Seed Multi-Regime Pre-Dispatch Reserve Screening Benchmark under Clean-Calibrated Protocol ($h=6$, 1-Hour Ahead Dispatch, 5 Seeds 201--205). Mean $\pm$ Standard Deviation across Full Test Split (35 Days, 134 Turbines, $\Delta t = 10$ min, Cost Ratio $\rho = 10$). All quantile bins and multipliers calibrated exclusively on nominal clean validation data.}`
- **Discrepancy**: Caption incorrectly claims the evaluation is across the "Full Test Split", whereas the numbers ($881\text{k}$, $959\text{k}$, $991\text{k}$, etc.) are evaluated strictly on the **Boundary-Band Slice** ($|v-10.5|\le 1.0\text{ m/s}$, $N=13,883$ events).
- **Required Modification**: Change caption to explicitly declare the boundary-active population:
  `\caption{Cross-Seed Multi-Regime Pre-Dispatch Reserve Screening Benchmark on Boundary-Active Operating Regimes under Clean-Calibrated Protocol ($h=6$, 1-Hour Ahead Dispatch, 5 Seeds 201--205). Mean $\pm$ Standard Deviation across Boundary-Band Events ($|v_{\text{phys}}-10.5|\le 1.0\text{ m/s}$, $N=13{,}883$ cells, 35 Test Days, 134 Turbines, $\Delta t = 10$ min, Cost Ratio $\rho = 10$). All quantile bins and multipliers calibrated exclusively on nominal clean validation data.}`

### Modification 2: Abstract & Introduction Clarification (`paper_tste_ieee.md:70, 85`)
- **Current Text**:
  `Under pristine telemetry, deterministic physical rules achieve the lowest reserve-screening surrogate cost among all evaluated approaches ($589{,}535\text{ kW}\cdot\text{h}$ at 10-minute dispatch $h=1$ and $881{,}367\text{ kW}\cdot\text{h}$ at 1-hour dispatch $h=6$, with $\sim 6.8\%$ violation), outperforming deep neural networks.`
- **Clarification**: Add the explicit scope qualification `in the aerodynamic boundary band ($|v-10.5|\le 1\text{ m/s}$, 13,883 events)` so that readers immediately understand that these numbers represent the critical transition slice, preventing any misinterpretation against plant-wide totals.
