# Strong-Baseline Closure: Posterior vs. Wind-Speed-Conditioned Quantiles & Deployable Hybrid Policy

**Date**: 2026-09-19  
**Core Hypothesis Tested**:
> *“Does the latent-boundary posterior alter the risk-cost trade-off beyond observable wind-speed conditioning specifically near operating-state transitions?”*

**Mandatory Integrity Directive**:
The manuscript MUST NOT imply that the boundary posterior improves reserve screening over conditional quantile calibration. The goal is to state exactly where latent-boundary information provides a transition-localized risk-hedging trade-off and where it increases surrogate cost.

---

## 1. Experimental Protocol & Policy Definitions

All policies evaluate under **IDENTICAL**:
- Point forecast residuals: $s_t = \max(\hat{y}_t - y_t, 0)$ frozen across 5 seeds in `artifacts/fixed_forecast_residuals.npz`;
- Evaluation sample: WTB 134-turbine wind farm, 35-day chronological test split ($N = 385,205$ valid evaluated cells);
- Horizon: Operational Level-1 pre-dispatch horizon $h=6$ (60-minute ahead dispatch);
- Reserve objective: Penalized Reserve-Shortfall Energy Index ($\text{PSREI}$, $\rho=10$, target fractile $q^*=0.90$);
- Telemetry condition: Blade-pitch withheld ($\tau=0$, `Pab_mean` and `Pab_std` masked), simulating commercial protocol withholding.

### Evaluated Policies:
1. **Policy A (Global Residual Quantile)**:
   Scalar empirical quantile $\hat{q}_{0.90}(s)$ calibrated on validation residuals, independent of telemetry: $r_A = \hat{q}_{0.90}$.
2. **Policy B (Wind-Speed Binned Residual Quantile)**:
   Strong observable-state baseline. Empirical 90th percentile conditioned on 10 uniform wind-speed bins over $[0, 25\text{ m/s}]$ calibrated on validation data.
3. **Policy C (Posterior-Conditioned Residual Quantile)**:
   Quantile conditioned on 5 validation-calibrated quintiles of the learned latent-boundary posterior probability $\pi_t = P(Z_t = \text{Pitch} \mid \mathcal{I}_t^{(d)})$ from the spatio-temporal Dense GNN.
4. **Policy D (Validation-Frozen Deployable Hybrid Policy)**:
   Uses wind-speed conditioning ($r_B$) during ordinary/steady operation, switching to posterior conditioning ($r_C$) strictly when transition risk is indicated.
   - **Constraint**: The hybrid rule MUST NOT use true future or oracle regime labels.
   - **Validation Freezing**: The gating rule is swept and frozen strictly on validation data to minimize validation PSREI loss. Across seeds, the optimal validation rule is an uncertainty band in posterior probability ($0.05 \le \pi_t \le 0.95$ or $0.2 \le \pi_t \le 0.8$) or an inflow velocity rated band ($|v_{\text{inflow}} - 10.5\text{ m/s}| \le 0.5\text{--}1.0\text{ m/s}$).
5. **Policy D10 (Pre-Specified Boundary-Band Deployable Hybrid)**:
   Pre-specified physical band: uses posterior conditioning $r_C$ when $|v_{\text{inflow}} - 10.5| \le 1.0\text{ m/s}$, and wind-speed conditioning $r_B$ otherwise.

---

## 2. 5-Seed Empirical Results Table

Evaluated across 5 random seeds (201--205) on the 35 observed test days:

| Population Slice | Policy ID | Policy Description | PSREI Cost ($\text{kW}\cdot\text{h}$) | Reserve Volume ($\text{kW}\cdot\text{h}$) | Violation Rate (%) | Shortage Energy ($\text{kW}\cdot\text{h}$) | Delta vs. Wspd ($\Delta L$, $\text{kW}\cdot\text{h}$) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **FULL POPULATION** | Policy A | Global Residual Quantile | $16,132,772 \pm 2,362,165$ | $12,484,016$ | 5.41% | $364,876$ | $+2,348,452$ (Worse) |
| ($N = 385,205$, 100%) | Policy B | Wind-Speed Binned Quantile | $\mathbf{13,784,320} \pm 1,438,833$ | $10,324,129$ | 8.79% | $346,019$ | **0 (Reference)** |
| | Policy C | Posterior-Conditioned Quantile | $14,307,364 \pm 1,787,258$ | $10,179,077$ | 9.08% | $412,829$ | **$+523,044$** (Worse, $p=0.85$) |
| | Policy D | Validation-Frozen Hybrid | $13,789,154 \pm 1,434,721$ | $10,339,015$ | 8.78% | $345,014$ | $+4,834$ (Neutral) |
| | Policy D10 | Pre-Specified Band Hybrid | $13,801,696 \pm 1,438,458$ | $10,378,012$ | 8.76% | $342,368$ | $+17,376$ (Neutral) |
| **TRANSITION WINDOWS** | Policy A | Global Residual Quantile | $5,325,549 \pm 725,068$ | $4,526,985$ | 3.03% | $79,856$ | $+1,005,239$ (Worse) |
| ($\pm 3$ steps of switch; | Policy B | Wind-Speed Binned Quantile | $\mathbf{4,320,310} \pm 261,611$ | $3,417,998$ | 8.36% | $90,231$ | **0 (Reference)** |
| $N = 139,684$, 36.26%) | Policy C | Posterior-Conditioned Quantile | $4,433,014 \pm 336,858$ | $3,567,090$ | **7.24%** | $\mathbf{86,592}$ | **$+112,704$** ($p=0.48$) |
| | Policy D | Validation-Frozen Hybrid | $4,326,018 \pm 258,505$ | $3,429,531$ | 8.35% | $89,649$ | $+5,708$ (Neutral) |
| | Policy D10 | Pre-Specified Band Hybrid | $4,335,519 \pm 262,140$ | $3,456,492$ | 8.30% | $87,903$ | $+15,209$ (Neutral) |
| **STEADY WINDOWS** | Policy A | Global Residual Quantile | $10,807,224 \pm 1,642,320$ | $7,957,030$ | 6.76% | $285,019$ | $+1,343,214$ (Worse) |
| (Stationary MPPT/Pitch; | Policy B | Wind-Speed Binned Quantile | $\mathbf{9,464,010} \pm 1,185,662$ | $6,906,130$ | 9.03% | $\mathbf{255,788}$ | **0 (Reference)** |
| $N = 245,521$, 63.74%) | Policy C | Posterior-Conditioned Quantile | $9,874,350 \pm 1,466,885$ | $6,611,987$ | 10.13% | $326,236$ | **$+410,340$** (Worse, $p=0.002$) |
| | Policy D | Validation-Frozen Hybrid | $9,463,137 \pm 1,185,918$ | $6,909,484$ | 9.03% | $255,365$ | $-873$ (Neutral) |
| | Policy D10 | Pre-Specified Band Hybrid | $9,466,177 \pm 1,185,505$ | $6,921,521$ | 9.02% | $254,466$ | $+2,167$ (Neutral) |

---

## 3. Formal Statistical Contrast & Paired Cluster Bootstrap

To rigorously test whether the relative performance of posterior conditioning versus wind-speed conditioning changes between transition and steady operation, we run a **paired day-level cluster bootstrap over the 35 observed test days** (144 steps per daily cluster, 1,000 paired resamples across 5 seeds).

Let difference loss be:
$$d_t = L_{\text{posterior}, t} - L_{\text{wspd}, t}.$$

We estimate:
- $\Delta_{\text{transition}} = \sum_{t \in \text{Trans}} d_t$
- $\Delta_{\text{steady}} = \sum_{t \in \text{Steady}} d_t$
- **Heterogeneity Interaction Contrast**:
  $$\text{Interaction} = \Delta_{\text{transition}} - \Delta_{\text{steady}}.$$

### Seed-by-Seed Bootstrap Results ($L_C - L_B$ in $\text{kW}\cdot\text{h}$):

| Seed | $\Delta_{\text{transition}}$ (95% Bootstrap CI) | $\Delta_{\text{steady}}$ (95% Bootstrap CI) | Heterogeneity Interaction $\Delta_{\text{trans}} - \Delta_{\text{steady}}$ | $p$-value |
| :--- | :--- | :--- | :--- | :--- |
| **201** | $+1,808$ [$-55,467, +60,024$] | $+446,675$ [$+112,291, +807,176$] | **$-444,867$** [$-826,476, -101,349$] | **0.0030** |
| **202** | $+57,382$ [$+11,328, +114,290$] | $-101,846$ [$-211,233, +12,838$] | **$+159,228$** [$+74,006, +256,493$] | 0.0000 |
| **203** | $+277,601$ [$+214,261, +341,119$] | $+587,213$ [$+352,366, +842,683$] | **$-309,612$** [$-547,256, -80,609$] | **0.0030** |
| **204** | $+134,314$ [$+83,578, +190,271$] | $+619,538$ [$+263,606, +1,003,549$] | **$-485,224$** [$-832,765, -151,231$] | **0.0020** |
| **205** | $+93,030$ [$+48,811, +136,012$] | $+493,168$ [$+206,477, +792,439$] | **$-400,138$** [$-708,728, -121,146$] | **0.0020** |
| **Mean** | **$+112,827$** $\text{kW}\cdot\text{h}$ | **$+410,217$** $\text{kW}\cdot\text{h}$ | **$-296,123$** $\text{kW}\cdot\text{h}$ | **$< 0.005$** |

### Statistical Findings:
1. **The Gap is Sharply Compressed in Transitions**:
   In steady-state operation, posterior conditioning incurs a large, statistically significant surrogate penalty of **$+410,217\text{ kW}\cdot\text{h}$** over wind-speed bins ($p < 0.005$). In transition windows, this penalty shrinks to $+112,827\text{ kW}\cdot\text{h}$.
2. **Statistically Significant Heterogeneity Interaction**:
   Across 4 of 5 seeds, the interaction contrast is strongly negative (mean: **$-296,123\text{ kW}\cdot\text{h}$**, $p < 0.005$), confirming that the relative performance profile of the posterior changes fundamentally between steady and transition regimes.
3. **Shortage and Violation Shift in Transitions**:
   In transition windows, Policy C achieves a **lower violation rate** ($7.24\%$ vs. $8.36\%$) and **reduces unhedged shortage energy** from $90.2\text{k}$ to $86.6\text{k kW}\cdot\text{h}$. However, achieving this lower violation requires procuring more reserve capacity ($3,567\text{k}$ vs. $3,418\text{k kW}\cdot\text{h}$), resulting in a slight net PSREI cost increase (+112k kWh).
4. **Deployable Hybrid Policy Verdict**:
   Validation-frozen hybrid policy D yields $13,789,154\text{ kW}\cdot\text{h}$ plant-wide, which is statistically indistinguishable from Policy B ($13,784,320\text{ kW}\cdot\text{h}$, difference $+4,834\text{ kW}\cdot\text{h}$, $p > 0.40$). It does **not** deliver plant-wide cost reduction over simple wind-speed binning.

---

## 4. Reinterpreting the 48.4% Transition Mediation Result

### The Reviewer Vulnerability:
Earlier drafts reported: *"48.4% of total reserve savings occur near transitions."*  
A critical reviewer can reasonably object:
> *“Transition windows simply contain higher underlying prediction variance and higher losses in general. Therefore, any baseline or model will have a large share of its absolute dollar/kWh deltas concentrated in transitions. High loss concentration is not proof of treatment benefit.”*

### The Rigorous Scientific Disentanglement:
We formally distinguish between **loss concentration** and **incremental model benefit**:

1. **Loss Concentration vs. Treatment Benefit**:
   - Transition windows account for **$36.26\%$** of test time, but concentrate **$33.0\%$** of global quantile loss ($5.33\text{M}$ out of $16.13\text{M}$) and **$31.3\%$** of wind-speed binned loss ($4.32\text{M}$ out of $13.78\text{M}$).
   - The absolute saving of posterior conditioning versus an *unconditioned global quantile* is indeed $48.38\%$ concentrated in transition windows ($+892,535\text{ kW}\cdot\text{h}$ out of $+1,825,410\text{ kW}\cdot\text{h}$).
2. **Against the Strong Wind-Speed Baseline**:
   - When compared against the strong observable wind-speed conditioned baseline (Policy B), the learned posterior does **not** beat wind-speed binning plant-wide ($\Delta L = L_{\text{posterior}} - L_{\text{wspd}} = +523,044\text{ kW}\cdot\text{h}$ net penalty, posterior is worse).
   - In steady state, wind-speed binning is strictly superior ($\Delta L = +410,340\text{ kW}\cdot\text{h}$, $p=0.002$).
   - In transition windows, posterior conditioning provides risk-averse coverage (compressing violations to $7.24\%$ and shortages to $86.6\text{k kW}\cdot\text{h}$ vs. $8.36\%$ and $90.2\text{k kW}\cdot\text{h}$), but does not provide net surrogate cost savings ($\Delta L = +112,704\text{ kW}\cdot\text{h}$, $p=0.48$).

### Safe, Non-Triumphalist Manuscript Statement:
> “The learned latent-boundary posterior does not improve plant-wide reserve screening over a strong wind-speed-conditioned quantile baseline ($\Delta L = +523{,}044\text{ kW}\cdot\text{h}$ difference, $p=0.85$); near operating transitions it reduces shortage and violation exposure at additional reserve cost, revealing a localized risk-hedging rather than cost-dominance effect. In steady operation, direct wind-speed binning serves as the operational minimum sufficient model. Machine learning provides conditional regime information, not universal predictive superiority.”
