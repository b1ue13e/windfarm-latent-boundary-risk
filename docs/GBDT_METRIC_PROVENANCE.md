# Forensic Provenance Audit: GBDT $h=6$ Reliability Violation Rates (14.98% vs. 16.23%)

**Date**: 2026-09-19  
**Audit Target**: Programmatic reconciliation of two competing headline violation numbers reported across repository documentation:
1. $\text{Violation Rate} = 14.98\%$
2. $\text{Violation Rate} = 16.23\%$

---

## 1. Executive Summary & Root-Cause Forensic Resolution

A comprehensive forensic audit of all data pipelines, models, feature matrices, and evaluation logs reveals that **both numbers are mathematically exact, reproducible values computed from the canonical baseline artifact**, but they represent **two distinct degradation scenarios**:

| Value | Model ID | Degradation Scenario | Horizon | Target Residual | Sample Population | Source Artifact Row | Script / Code Source |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **16.234%** ($\approx 16.23\%$) | `B3_Quantile_GBDT` | **Clean** ($\tau=0$, all SCADA channels observed) | $h=6$ (60 min) | $s_t = \max(\hat{y}_t - y_t, 0)$ | Full Test Set ($N=408,939$ valid cells) | `artifacts/direct_quantile_baselines_summary.csv` (Row 10) | `scripts/run_direct_quantile_baselines.py:270` |
| **14.977%** ($\approx 14.98\%$) | `B3_Quantile_GBDT` | **Pitch-Withheld** ($\tau=0$, blade pitch $P_{\text{ab}}$ withheld) | $h=6$ (60 min) | $s_t = \max(\hat{y}_t - y_t, 0)$ | Full Test Set ($N=408,939$ valid cells) | `artifacts/direct_quantile_baselines_summary.csv` (Row 30) | `scripts/run_direct_quantile_baselines.py:270` |

### Forensic Diagnosis of the Discrepancy
- **Why both exist**: `scripts/run_direct_quantile_baselines.py` systematically evaluates five direct quantile baselines (`B0` through `B4`) across four operational degradation scenarios:
  1. `clean` ($\tau=0$, complete telemetry)
  2. `delay6` ($\tau=60\text{ min}$, stale telemetry)
  3. `pitch_withheld` ($\tau=0$, missing blade pitch channels)
  4. `delay6_pitch_withheld` ($\tau=60\text{ min}$, stale telemetry and missing blade pitch)
- **Where the labeling error occurred**: In early drafts of summary memos (`docs/DECISIVE_EVIDENCE_GATE.md:35`, `RESEARCH_VERDICT.md:38,53`, and `DECISIVE_EXPERIMENT_REPORT.md:53`), authors discussed the *pitch-withheld* regime but cited the *clean* scenario breach figure ($16.23\%$) rather than the condition-matched figure ($14.98\%$). Conversely, `scripts/verify_decisive_gate.py` explicitly audited the `pitch_withheld` row, verifying $14.98\% > 10.0\%$.
- **Scientific Takeaway**: Both values comfortably exceed the $\le 10.0\%$ grid compliance failure boundary ($16.23\% > 10.0\%$ and $14.98\% > 10.0\%$). However, rigorous scientific provenance requires explicit condition labeling to prevent cross-condition conflation.

---

## 2. Complete Provenance Trace

### 2.1 Model Specification & Checkpoint
- **Framework**: `scikit-learn` `HistGradientBoostingRegressor`
- **Objective**: Direct quantile regression (`loss="quantile"`, target quantile $\alpha = 0.90$)
- **Hyperparameters**:
  - `quantile`: 0.90
  - `max_iter`: 100
  - `max_depth`: 6
  - `min_samples_leaf`: 30
  - `random_state`: 42
- **Training Population**: Sub-sampled sample of 40,000 valid cell observations from the 30-day chronological validation split (`m_v_flat`), calibrated under the exact matching degradation spec.
- **In-Memory Checkpoint**: Trained on-the-fly and evaluated deterministically with seed 42 in `scripts/run_direct_quantile_baselines.py`.

### 2.2 Feature Matrix & Information Set Symmetry
- **Input Channels**: Summary statistics over lookback window $H=36$ (6 hours at 10-min resolution):
  - $\bar{x}_{i,t} = \text{mean}(X_{i, t-H:t})$ (mean of historical telemetry)
  - $\sigma_{i,t} = \text{std}(X_{i, t-H:t})$ (standard deviation of historical telemetry)
  - $x_{i,t}^{\text{last}} = X_{i, t}$ (most recent available historical sample)
  - $anc_{i,t} = \text{anchor\_physics}$ (dispatch-time physical wind speed, direction)
- **Degradation Intervention**:
  - In `clean`: all 11 SCADA features are included.
  - In `pitch_withheld`: pitch angle channels (`Pab_mean`, `Pab_std`) are masked to zero across all history steps $H=36$.

### 2.3 Evaluation Population & Mask
- **Dataset**: WTB 134-turbine wind farm (KDD Cup 2022 benchmark), chronological 35-day test split ($T_{\text{test}} = 4,981$ timestamps).
- **Evaluation Mask**: `m_test[:, 5, :] > 0.5` ($h=6$, index 5), filtering for valid, non-anomalous turbine-interval operations.
- **Evaluated Test Sample Size**: Exactly **408,939 valid turbine-interval cells**.
- **Fixed Residual Target**: $s_t = \max(\hat{y}_{t, \text{seed201}} - y_t, 0)$ frozen in `artifacts/fixed_forecast_residuals.npz`.

### 2.4 Complete 4-Scenario GBDT $h=6$ Metrics from Canonical Artifact
Extracted directly from `artifacts/direct_quantile_baselines_summary.csv`:

| Scenario | Condition ID | Horizon | PSREI Cost (kW·h) | Violation Rate (%) | Reserve Volume (kW·h) | Shortage Energy (kW·h) | Pinball Loss | Grid Compliance ($\le 10\%$) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Pristine Telemetry** | `clean` | $h=6$ (60 min) | 15,665,274.89 | **16.23%** (0.162345) | 7,553,868.14 | 811,140.67 | 18.29 | **FAIL (Surge)** |
| **60-min Delay** | `delay6` | $h=6$ (60 min) | 15,740,668.35 | **15.14%** (0.151372) | 7,770,719.19 | 796,994.92 | 18.41 | **FAIL (Surge)** |
| **Pitch Withheld** | `pitch_withheld` | $h=6$ (60 min) | 14,965,626.30 | **14.98%** (0.149771) | 8,356,190.15 | 660,943.61 | 17.27 | **FAIL (Surge)** |
| **Delay + Pitch Withheld**| `delay6_pitch_withheld`| $h=6$ (60 min) | 14,993,857.49 | **13.73%** (0.137277) | 8,310,173.88 | 668,368.36 | 17.31 | **FAIL (Surge)** |

---

## 3. Canonical Headline Metric Registry Update

All references to GBDT violation rates must explicitly cite their scenario:

| Claim ID | Model | Scenario | Horizon | Population | Metric | Value | Source Artifact | Source Script |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `CLM-GBDT-01` | B3 Quantile GBDT | `clean` | $h=1$ (10 min) | Full Test Set ($N=408,937$) | Violation Rate | **9.16%** | `artifacts/direct_quantile_baselines_summary.csv` | `scripts/run_direct_quantile_baselines.py` |
| `CLM-GBDT-02` | B3 Quantile GBDT | `clean` | $h=6$ (60 min) | Full Test Set ($N=408,939$) | Violation Rate | **16.23%** | `artifacts/direct_quantile_baselines_summary.csv` | `scripts/run_direct_quantile_baselines.py` |
| `CLM-GBDT-03` | B3 Quantile GBDT | `pitch_withheld` | $h=1$ (10 min) | Full Test Set ($N=408,937$) | Violation Rate | **8.42%** | `artifacts/direct_quantile_baselines_summary.csv` | `scripts/run_direct_quantile_baselines.py` |
| `CLM-GBDT-04` | B3 Quantile GBDT | `pitch_withheld` | $h=6$ (60 min) | Full Test Set ($N=408,939$) | Violation Rate | **14.98%** | `artifacts/direct_quantile_baselines_summary.csv` | `scripts/run_direct_quantile_baselines.py` |
| `CLM-GBDT-05` | B3 Quantile GBDT | `delay6` | $h=6$ (60 min) | Full Test Set ($N=408,939$) | Violation Rate | **15.14%** | `artifacts/direct_quantile_baselines_summary.csv` | `scripts/run_direct_quantile_baselines.py` |
| `CLM-GBDT-06` | B3 Quantile GBDT | `delay6_pitch_withheld`| $h=6$ (60 min) | Full Test Set ($N=408,939$) | Violation Rate | **13.73%** | `artifacts/direct_quantile_baselines_summary.csv` | `scripts/run_direct_quantile_baselines.py` |

---

## 4. Repository-Wide Relabeling Directives

1. **When discussing Pristine Telemetry (`clean`, $\tau=0$)**:
   - Explicitly cite **$16.23\%$** violation rate for B3 GBDT at $h=6$.
2. **When discussing Blade Pitch Withholding (`pitch_withheld`)**:
   - Explicitly cite **$14.98\%$** violation rate for B3 GBDT at $h=6$.
3. **When comparing Multi-Horizon Tree Degradation ($h=1 \to h=6$)**:
   - Under Clean: B3 GBDT surges from $9.16\%$ at $h=1$ to $16.23\%$ at $h=6$.
   - Under Pitch-Withheld: B3 GBDT surges from $8.42\%$ at $h=1$ to $14.98\%$ at $h=6$.
4. **General Grid Compliance Finding**:
   - Across all four evaluated telemetry degradation scenarios at $h=6$, shallow tree-based quantile models breach the $10.0\%$ grid compliance threshold ($13.73\%\text{--}16.23\%$), confirming tree baseline failure under multi-step wake advection regardless of telemetry condition.
