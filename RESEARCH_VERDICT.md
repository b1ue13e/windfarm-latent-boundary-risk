# Final Research Verdict: SCADA Latent-Boundary Recovery & Asymmetric Reserve Sizing

**Date**: 2026-09-18  
**Audit Directorate**: Independent Adversarial Review Panel & Experimental Reliability Auditor  
**Repository**: `e:\论文3`  
**Target Venue**: *IEEE Transactions on Sustainable Energy* (Strict 10.0-Page Constraint)  
**Primary Artifact**: `build/paper_tste_ieee.pdf` (10 pages) & `build/paper_tste_supplementary.pdf` (17 pages)

---

## 1. Central Scientific Question: Formal Resolution

> **CENTRAL QUESTION**:  
> *Under exactly the same arrival-time information constraints, when a critical wind-turbine control boundary becomes partially unobservable, can secondary SCADA consequence signals recover useful information about that hidden operating boundary, and does that recovered boundary information provide independent value for asymmetric shortfall-risk / reserve quantile decisions?*

### FINAL VERDICT: PASS_WITH_LIMITATIONS

The paper's central scientific claim **SURVIVES** under a strict, falsifiable formulation, bounded by four negative-result operational limits:

```
                            CENTRAL SCIENTIFIC VERDICT
                                        │
           ┌────────────────────────────┴────────────────────────────┐
           ▼                                                         ▼
     WHAT SURVIVED                                              WHAT DIED
(Defensible Scientific Claims)                             (Refuted Overclaims)
           │                                                         │
1. Secondary Consequence Recovery                         1. MoE Routing Superiority
   (Active power identifies latent pitch                     (Statistically indistinguishable from
    boundary: NMI=0.461, ECE=2.54%)                           dense multitask heads, p=0.380)
           │                                                         │
2. Transition Decision Value                              2. Universal ML Superiority
   (Saves +1.83M kWh vs global quantile;                     (Clean physical rules beat ML by 8.1%
    48.4% concentrated in boundary transitions)               in boundary band when pitch is observable)
           │                                                         │
3. Nominal Target Preservation                           3. Steady-State MPPT Dominance
   (Maintains target-satisfying violation, whereas GBDT      (Direct wind-speed bins sufficient in
    breaches nominal 10% target at 14.98% / 16.23%)           steady Region 2 operation)
           │                                                         │
4. State-Conditional Recalibration                        4. Selective Abstention Benefit
   (Absorbs 55.3% of shortage loss without                   (Abstaining on low confidence produces
    neural backpropagation)                                   negative value; +1.77M kWh waste)
```

---

## 2. Core Empirical Evidence Matrix

| Research Dimension | Empirical Evidence & Key Numbers | Evidence Artifact |
| :--- | :--- | :--- |
| **Information Symmetry** | Audited feature-lag manifest (819 entries); exact synchronous degradation $\mathcal{I}_t^{(d)}$. | `docs/INFORMATION_SET_CONTRACT.md` |
| **Point Forecast Anchor** | Canonical frozen point forecast across 5 seeds; residuals frozen into fixed target array. | `artifacts/fixed_forecast_residuals.npz` |
| **Direct Baseline Challenge** | B3 Quantile GBDT excels at $h=1$ ($6.49\text{M}$ clean / $6.41\text{M}$ withheld) but **surges to $16.23\%$ (clean) and $14.98\%$ (pitch-withheld) violation at $h=6$** (exceeding nominal 10% target); B1 Wspd-Bins is robust in steady state. | `artifacts/direct_quantile_baselines_summary.csv` |
| **MoE Dynamic Routing** | STGQ-Dense ($15,471,506 \text{ kWh}$) matches or outperforms STGQ-Routed ($15,768,203 \text{ kWh}$, $p=0.380$). | `artifacts/factorial_boundary_ablation_summary.csv` |
| **Negative Controls** | Permuted labels inflate cost to $17.93\text{M}$; random posterior exceeds nominal 10% Newsvendor violation target at **$11.41\%$ violation**. | `artifacts/factorial_boundary_ablation_summary.csv` |
| **Posterior Calibration** | Test ECE strictly $\le 3.46\%$ across all conditions (Dense: $0.89\%$ clean, $2.54\%$ withheld); passes $\le 0.05$ gate. | `artifacts/posterior_calibration.csv` |
| **Consequence Mechanism** | Active Power ($C2$) achieves Brier $0.0112$, NMI $0.461$, recovering $62.9\%$ of transitions; thermal fails ($0.0\%$). | `artifacts/channel_consequence_ablations.csv` |
| **Decision Mediation** | Boundary representation saves **$+1.83\text{M kWh}$** vs unconditioned global quantile ($48.4\%$ concentrated in transition windows); vs strong wind-speed bins, it acts as a localized risk hedge (reducing violation from $8.36\%$ to $7.24\%$ at $+112\text{k kWh}$ reserve cost; $\Delta_{\text{trans}} - \Delta_{\text{steady}} = -296\text{k kW}\cdot\text{h}$ establishes cost gap heterogeneity). | `artifacts/mediation_analysis.csv` |
| **Physical Dominance** | Deterministic physical rule achieves **$881,367 \text{ kWh}$** in the boundary band at $h=6$ under $\tau=0$, beating neural models by 8.1%. | `docs/FAILURE_FALLBACK_BOUNDARY.md` |
| **Page Budget Compliance** | `build/paper_tste_ieee.pdf` compiles cleanly to **exactly 10.0 pages** in two-column IEEEtran format. | `build/paper_tste_ieee.pdf` |

---

## 3. The 4 Operational Conditions Governing Deployment

1. **Rule 1 (Pristine Telemetry $\to$ Deterministic Physics)**:
   Whenever blade pitch telemetry is available and fresh ($\tau < 10\text{ min}$), operators must deploy physical aerodynamic quantile curves. Machine learning is strictly inferior under full observability.
2. **Rule 2 (Telemetry Latency $\to$ Empirical Recalibration First)**:
   When communication latency occurs but channels are observable, state-conditional recalibration absorbs $55.3\%$ of shortage risk without training neural networks.
3. **Rule 3 (Pitch Withheld $\to$ Latent-Boundary Spatio-Temporal GNN)**:
   When blade pitch registers are unobservable across commercial boundaries, the spatio-temporal boundary representation should be deployed on utility-scale wind farms to infer the latent boundary from active power and wake context.
4. **Rule 4 (Steady MPPT $\to$ Localized Physical Bins)**:
   In benign, steady-state Region 2 conditions, simple wind-speed bins are optimal and sufficient. Latent boundary conditioning provides a localized risk hedge (lower violation/shortage at higher reserve procurement cost) near dynamic transition windows, not a plant-wide cost reduction.
