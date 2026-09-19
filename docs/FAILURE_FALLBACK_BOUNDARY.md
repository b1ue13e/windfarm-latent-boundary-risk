# Failure and Fallback Boundary Analysis

**Date**: 2026-09-18  
**Scope**: Empirical identification of operational regimes where latent-boundary representation learning fails, provides zero value, or is strictly dominated by simpler physical or tabular rules.  
**Audited Artifacts**:
- Repository Evidence Map: `docs/REPOSITORY_EVIDENCE_MAP.md`
- Factorial Ablation Summary: `artifacts/factorial_boundary_ablation_summary.csv`
- Direct Baselines Summary: `artifacts/direct_quantile_baselines_summary.csv`
- Mediation Analysis: `artifacts/mediation_analysis.csv`

---

## 1. Executive Summary

A critical requirement of rigorous scientific publication in *IEEE Transactions on Sustainable Energy* is establishing **falsifiability and negative-result boundaries**. Rather than claiming universal superiority, this paper establishes four precise operational boundaries where neural latent-boundary estimation should be bypassed in favor of simpler, deterministic fallbacks.

```
                    OPERATIONAL TELEMETRY STATE
                                 │
         ┌───────────────────────┴───────────────────────┐
         ▼                                               ▼
Fresh Pitch Telemetry                           Blade Pitch Withheld /
Observable (τ = 0)                              Unobservable Actuator
         │                                               │
         ▼                                               ▼
┌─────────────────────────────┐                 ┌─────────────────────────────┐
│ FALLBACK: Physical Rule     │                 │ Latent Boundary Recov. GNN  │
│ Cost: 881,367 kWh (h=6)     │                 │ Cost: 15,471,506 kWh (h=6)  │
│ Violation: 6.81%            │                 │ Saves 1.83M kWh vs Global   │
│ (Beats ALL Neural Models)   │                 │ (Maintains 8.84% Viol Rate) │
└─────────────────────────────┘                 └─────────────────────────────┘
```

---

## 2. The Four Decisive Failure and Fallback Boundaries

### Boundary 1: Clean Aerodynamic Telemetry within Boundary-Active Regimes (τ = 0)
- **Finding**: When blade pitch angle ($\beta / P_{\text{ab}}$) is directly and freshly transmitted, **deterministic continuous physical quantile estimation strictly dominates all neural representations within the active boundary band**.
- **Empirical Evidence**:
  - In the boundary band ($|v_{\text{phys}} - 10.5|\le 1.0\text{ m/s}$, $N=13{,}883$ events) at $h=6$, clean physical quantile achieves **$881{,}367 \pm 95{,}741\text{ kW}\cdot\text{h}$** ($6.81\%$ violation), outperforming STGQ-Routed ($959{,}027\text{ kW}\cdot\text{h}$) and STGQ-Dense ($991{,}181\text{ kW}\cdot\text{h}$) by $8.1\%$ ($-77{,}659\text{ kW}\cdot\text{h}$, $p < 0.01$).
  - Across the full plant-wide population ($N=408{,}939$ valid test cells), direct quantile baselines achieve $14.0\text{M}$ to $16.5\text{M kW}\cdot\text{h}$. (Note: comparing $881\text{k}$ against $15\text{M}$ is mathematically invalid due to evaluating different cell populations; see `docs/METRIC_SCOPE_REGISTRY.md`).
- **Prescribed Fallback Policy**: If pitch telemetry is available and fresh ($\tau < 10\text{ min}$), operators must deploy deterministic aerodynamic power curves rather than neural state estimators.

---

### Boundary 2: Telemetry Observable Recalibration Sufficiency
- **Finding**: When SCADA telemetry channels are observable but experience moderate communication lag ($\tau \le 3$), simple state-conditional empirical recalibration absorbs **$55.3\%$** of the shortage loss without training any deep neural network or Mixture-of-Experts architecture.
- **Empirical Evidence**: State-conditional quantile adjustment reduces shortage loss from $127.6\text{ MWh}$ to $57.0\text{ MWh}$ without backpropagation.
- **Prescribed Fallback Policy**: For utilities with low computational budgets, state-conditioned empirical lookup tables provide an 80/20 cost-effective alternative to deep learning.

---

### Boundary 3: Spatial Redundancy Boundary vs. Wake-Coupled Array Benefit
- **Finding**: The utility of spatial neural networks is consistent with **exploitable spatial redundancy and site-specific heterogeneity**, rather than an arbitrary turbine headcount threshold.
- **Empirical Evidence**:
  - On compact micro-farms with isolated turbines and weak wake coupling (e.g., LHB with 4 turbines), LHB exhibits a negative transfer/overfitting boundary, consistent with limited exploitable spatial redundancy and site-specific heterogeneity, resulting in a $+43\text{k kW}\cdot\text{h}$ penalty (95% CI $[-28.7\text{k}, +141.2\text{k}]$), where local tabular models suffice.
  - On Kelmarsh (6 turbines), graph modeling is neutral ($-40\text{k kW}\cdot\text{h}$, CI crossing zero).
  - Crucially, on wake-coupled arrays (e.g., Penmanshiel with 14 turbines and WTB with 134 turbines), spatial graph modeling delivers massive, statistically significant reserve cost savings ($-2.14\text{M kW}\cdot\text{h}$ on Penmanshiel, $p < 0.05$; $-38\text{k kW}\cdot\text{h}$ on WTB).
- **Prescribed Fallback Policy**: Spatial-representation value is site-dependent and appears related to exploitable spatial redundancy, not turbine count alone. Graph neural architectures should only be deployed on wind facilities exhibiting demonstrable wake interactions and exploitable spatial redundancy; compact micro-arrays or sparse configurations lacking spatial wake coupling should fall back to single-turbine tabular or tree-based quantile models.

---

### Boundary 4: Selective Abstention Failure
- **Finding**: Bypassing reserve decisions or defaulting to conservative global quantiles when boundary confidence is low ($\pi_t < 0.20$) produces negative economic value.
- **Empirical Evidence**:
  - Over $94.3\%$ of operational windows exhibit $\pi_t < 0.20$ (corresponding to benign Region 2 MPPT operation).
  - Forcing conservative global quantiles in this regime inflates reserve overspending by **$+1,771,801 \text{ kWh}$**.
- **Prescribed Fallback Policy**: When $\pi_t < 0.20$, the system must seamlessly fall back to local empirical wind-speed binned quantiles, rather than triggering global alarm reserves.

---

## 3. Summary Decision Matrix for System Operators

| Telemetry Status | Wind Fleet Spatial Coupling | Operating Regime | Recommended Decision Policy | Expected Violation Rate |
| :--- | :--- | :--- | :--- | :--- |
| **Fresh Pitch Observable** | Any | Boundary-Active ($|v-v_{\text{rated}}| \le 1.0$) | **Continuous Physical Quantile** | $6.8\% \pm 0.4\%$ |
| **Pitch Withheld / Failed** | Wake-Coupled (Pronounced spatial redundancy) | Dynamic Boundary | **Latent-Boundary GNN Quantile** | $8.8\% \pm 0.6\%$ |
| **Pitch Withheld / Failed** | Micro-Array / Sparse (Minimal spatial redundancy) | Any | **Direct Quantile GBDT / Bins** | $8.5\% \pm 0.9\%$ |
| **Telemetry Severely Stalled** | Any | Unknown | **Validation-Calibrated Conservative** | $5.5\% \pm 0.3\%$ |
