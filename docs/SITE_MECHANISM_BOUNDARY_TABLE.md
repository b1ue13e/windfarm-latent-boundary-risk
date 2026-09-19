# Site × Mechanism Cross-Farm External Validity Boundary Table

**Date**: 2026-09-19  
**Framing Directive**: The 134-turbine WTB site is the primary mechanism-identification environment. Five random seeds quantify training stochasticity; they are NOT independent farms, climates, or physical replications. The three external European facilities must NOT be presented as uniform replication evidence. Their observed effects are heterogeneous:
- **Penmanshiel**: positive;
- **Kelmarsh**: statistically neutral;
- **ENGIE La Haute Borne (LHB)**: negative / overfitting boundary.

**Canonical Conclusion**:
> “The primary mechanism is identified on WTB; external sites probe transferability and reveal site-dependent boundary conditions. Cross-site heterogeneity is evidence against universal model superiority and supports site-specific assessment of exploitable spatial/state information.”

---

## 1. Site × Mechanism Comprehensive Ledger

| Site Name | Country & Facility Type | Turbine Count ($N$) | Observation Period | Available SCADA Channels | Blade Pitch Available? | Spatial Redundancy / Wake Context | Evaluated Model Comparison | Paired Effect ($\Delta\text{PSREI}$) | Uncertainty Interval (95% Bootstrap CI) | Transfer / Replication Interpretation |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **WTB** | China, Utility-scale onshore complex | 134 turbines | 245 days (8 months, 10-min SCADA, $T=35{,}280$) | 11 channels (Wspd, Wdir, Patv, Pab1..3, Ndir, Itmp, Etmp) | Yes (observed in raw; selectively withheld in experiments) | **High**: Dense multi-row array with pronounced spatial wake advection and terrain diversity | STGQ vs. Global Quantile (also vs. Continuous Physical & B1--B5) | **$-38\text{k kW}\cdot\text{h}$** (boundary band) / **$-1.83\text{M kW}\cdot\text{h}$** (full pop. vs global) | $[-67\text{k}, -12\text{k}]\text{ kW}\cdot\text{h}$ ($p < 0.05$) / $[+1.21\text{M}, +2.41\text{M}]$ | **Primary Mechanism Identification Site**: High spatial redundancy and wake coupling enable consequence-driven latent boundary recovery when pitch is withheld. |
| **Penmanshiel** | UK, Commercial onshore wind farm | 14 operational (MM82, numbered WT01--WT15 excluding WT03) | 8.6 years decadal archive (2016--2021) | Standard SCADA (Wspd, Patv, Pab, nacelle, temperatures) | Yes (99.1% available in modern continuous period) | **Moderate**: Cohesive commercial cluster with measurable inter-turbine wake coupling | STGQ vs. Global Quantile | **$-2.14\text{M kW}\cdot\text{h}$** | $[-3.25\text{M}, -1.36\text{M}]\text{ kW}\cdot\text{h}$ ($p < 0.05$) | **Positive External Boundary Probe**: Cross-site STGQ effects relative to the global quantile baseline are heterogeneous. The observed pattern is consistent with exploitable spatial redundancy as a possible moderator under local retraining, while turbine count alone does not explain the variation. |
| **Kelmarsh** | UK, Commercial onshore micro-array | 6 MM92 turbines | 9.0 years decadal archive (2016--2021) | Standard SCADA (Wspd, Patv, Pab, gen. speed, pitch) | Yes (97.3% available in modern continuous period) | **Minimal**: Linear/sparse 6-turbine micro-array; low spatial wake redundancy | STGQ vs. Global Quantile | **$-40\text{k kW}\cdot\text{h}$** | $[-204\text{k}, +172\text{k}]\text{ kW}\cdot\text{h}$ (**crosses zero**, $p = 0.85$) | **Statistically Neutral Probe**: Minimal spatial redundancy yields no detectable benefit for neural representations; simple quantile baselines match neural models. |
| **ENGIE La Haute Borne (LHB)** | France, Open-access micro-farm | 4 MM82 turbines | 4 years (2013--2016, quarterly walk-forward) | 4 core channels (Wspd, Patv, Pab, Ndir) | Yes (99.2% directly observed) | **Negligible**: 4-turbine micro-farm; high localized micro-topography heterogeneity | STGQ vs. Global Quantile / Continuous Physical | **$+43\text{k kW}\cdot\text{h}$** (annual) / **$+1.01\text{M kW}\cdot\text{h}$** (quarterly walk-forward) | $[-29\text{k}, +141\text{k}]\text{ kW}\cdot\text{h}$ (annual) / $[+0.29\text{M}, +1.76\text{M}]$ (quarterly) | **Negative / Overfitting Boundary Probe**: LHB exhibits a negative transfer/overfitting boundary, consistent with limited exploitable spatial redundancy and site-specific heterogeneity; simple deterministic physical rules or scalar quantiles are strictly superior. |

---

## 2. Key Methodological Lessons

1. **No Uniform Pooling**:
   The three European wind farms cannot and must not be pooled into a single "average transfer effect." Doing so would obscure the cross-site heterogeneity: STGQ effects relative to the global quantile baseline vary substantially across sites, consistent with exploitable spatial redundancy as a possible moderator, while turbine count alone does not explain the variation.
2. **Turbine Count vs. Spatial Redundancy**:
   Array scale is not purely about turbine count, but about physical turbine density and array configuration:
   - WTB (134 units) and Penmanshiel (14 operational units, WT01--WT15 excluding WT03) exhibit rich array depth where spatio-temporal representations show large empirical differences relative to global unconditioned quantiles.
   - Kelmarsh (6 units) and LHB (4 units) show neutral or negative differences, indicating that complex spatio-temporal models gain nothing (Kelmarsh) or reveal that LHB exhibits a negative transfer/overfitting boundary, consistent with limited exploitable spatial redundancy and site-specific heterogeneity.
3. **Directional Transfer Asymmetry**:
   Zero-shot transfer experiments between Kelmarsh and Penmanshiel demonstrate pronounced directional asymmetry (Kelmarsh $\to$ Penmanshiel NMI $0.77$ vs. Penmanshiel $\to$ Kelmarsh NMI $0.34$). This directional transfer asymmetry supports site-specific retraining or recalibration rather than assuming reliable zero-shot transfer.
4. **Absence of Matched External No-Graph Controls**:
   Table IV benchmarks STGQ against an unconditioned global quantile baseline, not matched external no-graph models. Notably, continuous physical curves match or slightly edge STGQ across external sites (WTB: 842k vs. 855k; Kelmarsh: 1,025k vs. 1,025k; Penmanshiel: 2,029k vs. 2,029k). Because matched no-graph ablations do not exist in the repository for external sites, wake modeling is not causally isolated as the driver of external-site gains.
