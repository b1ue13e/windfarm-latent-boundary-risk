# Canonical Research Question & Nested Hypotheses (Phase 1 Freeze)

**Date**: 2026-09-18  
**Status**: FROZEN / IMMUTABLE

---

## 1. The Central Scientific Question

The core scientific inquiry governing this investigation is strictly formulated as:

> **Under exactly the same arrival-time information constraints, when a critical wind-turbine control boundary becomes partially unobservable, can secondary SCADA consequence signals recover useful information about that hidden operating boundary, and does that recovered boundary information provide independent decision value for asymmetric shortfall-risk / reserve quantile decisions?**

### The Operational Triad
1. **State ($Z_t$)**: Which aerodynamic and control regime is the turbine actually operating in (e.g., MPPT Region 2 vs. active blade-pitch regulation Region 3)?
2. **Information ($\mathcal{I}_t^{(d)}$)**: What physical and electromechanical sensor measurements have genuinely arrived at the dispatch terminal by decision time $t$ under telemetry degradation condition $d$?
3. **Decision ($r_t^*$)**: Given the causal information set $\mathcal{I}_t^{(d)}$, what upward spinning reserve margin is required to reliably control the upper-tail generation shortfall risk at the Newsvendor critical fractile $q^* = 1 - 1/\rho = 0.90$?

---

## 2. Non-Negotiable Framing Boundaries

1. **NO MoE Marketing**: The research question is NOT "Does Mixture-of-Experts improve wind power forecasting?". Dynamic MoE routing is strictly an implementation comparator and mechanism ablation, not a prerequisite for scientific validity.
2. **NO Neural Supremacy Assumption**: Machine learning is NOT assumed to be universally superior to physics.
   - When inflow wind speed and blade pitch are fresh and directly observable: deterministic aerodynamics should remain sufficient or superior.
   - When pitch registers are withheld but secondary electromechanical consequences retain identifiable information: learned latent-boundary representations may improve residual-tail decisions.
   - When the hidden boundary is not identifiable: the system must not invent false confidence; a conservative regime-blind/global fallback is preferred.
3. **The Decisive Falsification Test**:
   > *"If every competing method receives exactly the same delayed/missing history and predicts exactly the same residual-risk target, can a simple direct conditional quantile model obtain the same decision performance without explicitly recovering the latent operating boundary?"*
   - If **YES**: the latent-boundary claim is falsified and must be weakened or rejected.
   - If **NO**: quantify the exact incremental decision value of boundary awareness.

---

## 3. Three Nested Scientific Hypotheses

### Hypothesis H1: Boundary Recoverability (Information Preservation)
*Statement*: After definitionally revealing primary control channels (specifically collective blade pitch angle $\bar{p}_{i,t}$) are removed from the deployable observation set, the remaining causal SCADA consequence channels (active power divergence, electrical/reactive dynamics, and spatio-temporal wake interactions) retain statistically identifiable mutual information regarding the latent operating boundary between MPPT and blade-pitch regulation.
*Formal Criterion*:
$$\mathrm{NMI}\left(Z_t, \, \hat{Z}(I_t^{\text{no\_pitch}})\right) \gg \mathrm{NMI}\left(Z_t, \, \hat{Z}_{\text{permuted}}\right), \quad \text{with } p < 0.001.$$

### Hypothesis H2: Incremental Decision Value (Tail Risk Mitigation)
*Statement*: Embedding boundary-aware information (either via a calibrated latent-state posterior or boundary-aligned representation) into residual quantile estimation yields a statistically significant reduction in the asymmetric shortfall screening metric (PSREI at $\rho=10$) relative to direct conditional quantile models that observe the identical information set $\mathcal{I}_t^{(d)}$ and anchor on the identical fixed point forecast $\hat{y}_{\text{fixed}, t}$.
*Formal Criterion*:
$$\Delta\text{PSREI} = \text{PSREI}(\text{Direct Baseline} \mid \mathcal{I}_t) - \text{PSREI}(\text{Boundary-Aware} \mid \mathcal{I}_t) > 0,$$
where the paired 95% daily cluster bootstrap confidence interval (1,000 resamples over 35 observed days) strictly excludes zero.

### Hypothesis H3: Operational Failure Boundary (Conditional Validity)
*Statement*: The independent decision value of learned boundary recovery is strictly bounded and disappears under any of the following four operational regimes:
1. **Full Fresh Observability ($\tau=0$, complete channels)**: Deterministic aerodynamic power curves achieve lower surrogate cost and target-satisfying reliability without neural variance;
2. **Observable Transmission Latency ($\tau \in [10, 30]\text{ min}$, complete channels)**: Non-neural state-conditional quantile recalibration absorbs the vast majority ($>50\%$) of shortfall loss, rendering complex representation learning redundant;
3. **Minimal Spatial Redundancy Boundary**: On micro-arrays or sparse configurations where exploitable upstream wake redundancy is absent, LHB exhibits a negative transfer/overfitting boundary, consistent with limited exploitable spatial redundancy and site-specific heterogeneity, failing to outperform local or global quantiles;
4. **Severe Unidentifiability / Latency Horizon ($\tau \ge 60\text{ min}$)**: Extreme information decay degrades both point forecasts and boundary classification; here, heuristic selective abstention fails, and a conservative uniform reserve margin expansion dominates.
