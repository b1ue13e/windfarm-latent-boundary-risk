# Fixed-Target Decision-Isolation Contract (Phase 3)

**Date**: 2026-09-18  
**Status**: FROZEN & VERIFIED  
**Artifact**: `artifacts/fixed_forecast_residuals.npz` (165.38 MB), `artifacts/fixed_forecast_residuals_meta.json`

---

## 1. Principle of Decision Isolation

In prior iterations, comparative benchmarks risked conflating three conceptually distinct stages:
1. **Point Forecasting Quality**: Minimizing symmetric $L_2$ error $\mathbb{E}[(\hat{y} - y)^2]$;
2. **Latent-State Inference**: Inferring discrete operating regimes $Z_t \in \{0, 1, 2\}$;
3. **Reserve-Tail Estimation**: Estimating asymmetric upper quantiles $Q_{0.90}(s_t \mid \mathcal{I}_t)$ of shortfall $s_t = \max(\hat{y}_t - y_t, 0)$.

If competing reserve estimation methods use different point forecasters, any observed difference in reserve shortfall cost (PSREI) could simply be an artifact of a better point prediction rather than genuine decision value from latent boundary awareness.

To enforce strict causal interpretability, this contract **freezes one canonical point forecast** $\hat{y}_{\text{fixed}}$ across all competing reserve-sizing models.

---

## 2. Mathematical Definition of Fixed Residuals

For turbine $i$, dispatch issue time $t$, and forward horizon $h \in \{1, 2, 3, 4, 5, 6\}$ (corresponding to 10, 20, 30, 40, 50, and 60 minutes ahead):
1. **Canonical Scheduled Point Forecast**:
   $$\hat{y}_{i, t+h}^{\text{fixed}} \quad \text{generated strictly by the frozen clean-trained spatio-temporal GNN backbone (Seeds 201--205).}$$
2. **Realized Generation**:
   $$y_{i, t+h} \quad \text{actual metered electrical power generation.}$$
3. **Canonical Shortfall Residual Target**:
   $$s_{i, t, h} = \max\left( \hat{y}_{i, t+h}^{\text{fixed}} - y_{i, t+h}, \; 0 \right) \cdot m_{i, t+h},$$
   where $m_{i, t+h} \in \{0, 1\}$ is the validity mask (filtering non-positive or corrupted targets).

**Universal Reserve Optimization Objective**:
All competing models (Global empirical quantile, Binned empirical quantile, Quantile GBDT, Direct MLP, Modular Res-Head, and Joint Boundary models) are tasked with estimating the EXACT same target:
$$\hat{r}_{i, t, h}^* = Q_{0.90}\left( s_{i, t, h} \;\middle|\; \mathcal{I}_t^{(d)} \right).$$

No model may obtain a different residual target.

---

## 3. Canonical Point Forecast Performance (Stage A Audit)

Performance of the canonical frozen point forecaster across the 134-turbine WTB plant (mean $\pm$ standard deviation across 5 random seeds 201--205):

| Dispatch Horizon ($h$) | Lead Time (min) | Validation Split RMSE (kW) | Validation Split MAE (kW) | Test Split RMSE (kW) | Test Split MAE (kW) | Test Mean Shortfall (kW) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| $h=1$ | 10 min | $142.34 \pm 17.80$ | $85.39 \pm 10.96$ | $\mathbf{111.60 \pm 19.78}$ | $71.60 \pm 11.23$ | $35.80 \pm 5.61$ |
| $h=2$ | 20 min | $172.69 \pm 11.96$ | $105.74 \pm 8.21$ | $\mathbf{136.21 \pm 13.91}$ | $88.54 \pm 8.78$ | $44.27 \pm 4.39$ |
| $h=3$ | 30 min | $193.36 \pm 8.52$ | $119.86 \pm 6.32$ | $\mathbf{152.92 \pm 10.97}$ | $100.32 \pm 7.42$ | $50.16 \pm 3.71$ |
| $h=4$ | 40 min | $206.56 \pm 6.88$ | $129.24 \pm 5.34$ | $\mathbf{164.71 \pm 9.61}$ | $109.11 \pm 6.69$ | $54.56 \pm 3.35$ |
| $h=5$ | 50 min | $215.17 \pm 5.96$ | $135.53 \pm 4.79$ | $\mathbf{173.30 \pm 8.84}$ | $115.82 \pm 6.27$ | $57.91 \pm 3.14$ |
| $h=6$ | 60 min | $222.38 \pm 6.20$ | $140.75 \pm 4.67$ | $\mathbf{180.26 \pm 9.47}$ | $121.26 \pm 6.09$ | $60.63 \pm 3.05$ |

*Observation*: Forecast error expands smoothly with look-ahead horizon, from $111.6\text{ kW}$ at $h=1$ to $180.3\text{ kW}$ at $h=6$. This frozen trajectory establishes the exact background dispersion against which all reserve quantiles must be sized.

---

## 4. Separation Protocol

In all subsequent reports, manuscripts, and tables:
1. **Stage A (Point Forecasting)**: Reported solely as background operational anchoring;
2. **Stage B (State Recovery)**: Reported via NMI, ARI, Brier score, ECE, and transition recall;
3. **Stage C (Reserve Decision)**: Evaluated strictly through PSREI ($C(r)$ at $\rho=10$), empirical violation rate ($\% \le 10\%$), reserve capacity (kW), and unhedged shortage (kWh).

The three stages are mathematically decoupled.
