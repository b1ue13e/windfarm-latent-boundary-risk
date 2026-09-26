# Cross-Site Deployment Diagnostic & Observability-Redundancy Map

**Date**: 2026-09-26  
**Document**: Non-Causal Descriptive Deployment Diagnostic across 4 Commercial Wind Farms  
**Target Manuscript**: *IEEE Transactions on Sustainable Energy*  
**Governing Standard**: `docs/SCIENTIFIC_CONTRACT.md` (Section 4, Rule 10: "Penmanshiel/Kelmarsh/LHB are heterogeneous transfer probes; do not pool into universal superiority claims")

---

## 1. Methodological Guardrail: Descriptive vs. Inferential Boundary

With only four commercial wind farm environments evaluated in this research, **any inferential regression analysis (e.g., $N=4$ ordinary least squares or hierarchical linear modeling) is mathematically invalid and scientifically prohibited**.

Furthermore, treating individual wind turbines, observation windows, or random initialization seeds as independent units of replication would constitute severe **pseudo-replication**.

Accordingly, this diagnostic audit adopts a strictly **descriptive, hypothesis-generating framework**:
- **Allowed Interpretation**: *"Observed cross-site heterogeneity is consistent with variations in exploitable spatial coupling and consequence-channel redundancy across farm topologies."*
- **Forbidden Interpretation**: *"Spatial redundancy causes the representation gain,"* or *"This metric predicts when deep learning should be deployed."*
- All diagnostic descriptors are evaluated on historical training/validation partitions to guarantee **zero deployment-label leakage**.

---

## 2. Four-Site Descriptive Deployment Matrix

Data compiled from repository artifacts (`artifacts/deployment_diagnostic/site_descriptors.csv` and `artifacts/deployment_diagnostic/site_decision_outcomes.csv`):

| Site | Scale ($N$) | Terrain & Turbine Type | Boundary Band Prevalence (%) | Turbine Synchrony (Jaccard) | Median Spatial Power Corr. ($r$) | Effective Graph Degree ($k_{\text{eff}}$) | Consequence Recoverability (NMI / AUROC) | Simple Baseline Policy | Representation Policy Performance | Decision Metric Outcome | Empirical Classification |
| :--- | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :--- | :--- | :--- | :--- |
| **WTB** | 134 | Complex wake terrain (Sinovel SL1500) | 36.26% | 0.421 | 0.742 | 6.82 | 0.461 / 0.988 | Wind-Speed Binned Quantiles | Posterior Quantile (STGQ) | $\Delta \text{PSREI} = +523{,}044$ kWh penalty; Matched Budget: $+5{,}234$ kWh shortage | Primary Mechanism Benchmark (Baseline Sufficient) |
| **Penmanshiel** | 15 | Complex undulating terrain (Senvion MM92) | 28.40% | 0.315 | 0.681 | 3.20 | 0.770 / 0.892 | Global Quantile Baseline | Transferred STGQ (from Kelmarsh) | Statistically significant cost reduction vs. unconditioned global ($p < 0.05$) | Complex-Terrain Transfer (Directional Asymmetry) |
| **Kelmarsh** | 6 | Flat open terrain (Senvion MM92) | 24.10% | 0.228 | 0.612 | 1.80 | 0.411 / 0.845 | Global / Physical Quantile | Transferred STGQ (from Penmanshiel) | Neutral difference vs. global quantile ($p > 0.10$); NMI drops to 0.341 | Flat-Terrain Boundary (Limited Redundancy) |
| **La Haute Borne (LHB)** | 4 | Flat open micro-farm (Senvion MM82) | 19.50% | 0.142 | 0.524 | 1.00 | 0.941 / 0.965 | Local Observable Quantile | Transferred Large-Farm Representation | Transferred representation collapses; local training replicates mechanism | Micro-Farm Overfitting Boundary |

---

## 3. Detailed Site-by-Site Operational Profiles

### 3.1 WTB (134 Turbines, Baidu KDD Cup 2022) — Dense Multi-Row Wake Interaction
- **Topological Structure**: High turbine density ($N=134$) with closely spaced rows ($3\text{--}5$ rotor diameters) across complex rolling terrain.
- **Physical Characteristics**: High spatial power correlation ($r_{\text{med}} = 0.742$) and high effective wake connectivity ($k_{\text{eff}} = 6.82$). Boundary transitions exhibit significant spatial co-occurrence ($J = 0.421$) as wind speed ramps advect across the farm.
- **Operational Finding**: Observable consequence telemetry (specifically active power $C_2$, Brier $= 0.0112$, AUROC $= 0.988$) reliably recovers the latent boundary state $Z_t$. However, this state recoverability does **not** translate into downstream decision superiority over a strong observable baseline: 10-bin wind-speed quantiles achieve $+523{,}044$ kWh lower cost plant-wide, and posterior conditioning fails under matched budget ($+5{,}234$ kWh shortage penalty).
- **Takeaway**: Confirms the central thesis: state recoverability does not imply decision sufficiency.

### 3.2 Penmanshiel (15 Turbines, UK) — Complex Topographical Wind Steering
- **Topological Structure**: 15 turbines installed on complex, elevated moorland terrain in the Scottish Borders.
- **Physical Characteristics**: Moderate-high spatial correlation ($r_{\text{med}} = 0.681$) driven by strong prevailing wind corridors and steep ridge-valley elevation changes.
- **Operational Finding**: When evaluated against an *unconditioned global quantile*, spatio-temporal representations achieve lower surrogate reserve costs ($p < 0.05$). Directional transfer from flat Kelmarsh to complex Penmanshiel achieves high alignment (NMI $= 0.770$).
- **Takeaway**: Transferability is directionally asymmetric. The complex wake topology preserves exploitable structure when models are initialized from simpler upstream flow fields, but unconditioned global baselines do not establish decision superiority over local conditional baselines.

### 3.3 Kelmarsh (6 Turbines, UK) — Flat Open Terrain
- **Topological Structure**: Small 6-turbine cluster in open, flat farmland in Northamptonshire.
- **Physical Characteristics**: Lower wake tortuosity and lower spatial coupling ($r_{\text{med}} = 0.612, k_{\text{eff}} = 1.80$). Boundary transitions occur with lower cross-turbine synchrony ($J = 0.228$).
- **Operational Finding**: Spatio-temporal representations yield a **neutral effect** ($p > 0.10$) compared to direct physical or global quantiles. Furthermore, transferring models trained on complex Penmanshiel back to flat Kelmarsh suffers severe alignment degradation (NMI drops from $0.770$ to $0.341$).
- **Takeaway**: In open, flat terrain with minimal wake interaction, complex spatio-temporal graph structures provide negligible incremental value over simple physical power curve baselines.

### 3.4 La Haute Borne (4 Turbines, France) — Micro-Farm Overfitting Boundary
- **Topological Structure**: 4 turbines arranged linearly with wide spacing across open agricultural terrain.
- **Physical Characteristics**: Lowest spatial correlation ($r_{\text{med}} = 0.524$) and minimal inter-turbine wake coupling ($k_{\text{eff}} = 1.00$). Turbines operate nearly as isolated individual units ($J = 0.142$).
- **Operational Finding**: Locally trained models confirm the anchor-observable mechanism (NMI $= 0.941$, ARI $= 0.971$), proving that active power consequence signatures exist at the individual turbine level. However, transferring representations trained on large external wind farms leads to catastrophic overfitting and negative transfer.
- **Takeaway**: Small micro-farms ($N \le 4$) establish an empirical lower bound where cross-farm representation transfer should not be attempted. Simple local observable quantiles must be prioritized.

---

## 4. Descriptive Observability $\times$ Spatial-Redundancy Map

```
High Spatial Redundancy
      ^
      |                               [ WTB (N=134) ]
      |                      - Dense wake graph (k_eff = 6.82)
      |                      - Strong boundary recoverability (AUROC = 0.988)
      |                      - But Wspd-Bins beats Posterior (+523k kWh)
      |
      |                 [ Penmanshiel (N=15) ]
      |        - Complex terrain wake corridor
      |        - Directional transfer favorable (NMI = 0.770)
      |
      |        [ Kelmarsh (N=6) ]
      |   - Flat open terrain, weak wakes
      |   - Representation neutral (p > 0.10)
      |
      |   [ LHB (N=4) ]
      | - Micro-farm overfitting boundary
      | - Zero-shot transfer collapses
      +------------------------------------------------------------>
      Low Recoverability                              High Recoverability
                          (Consequence Channel Signal Quality)
```

---

## 5. Conceptual Deployment Decision Taxonomy

Based on the empirical findings, we synthesize a 3-tier operational deployment protocol governed by **information sufficiency**:

```
                  [ SCADA Observability at Arrival Time t ]
                                     |
         +---------------------------+---------------------------+
         |                                                       |
[ Fresh & Fully Observable ]                            [ Degraded SCADA ]
(Pitch & Wind Speed Arrived)                                     |
         |                                     +-----------------+-----------------+
         v                                     |                                   |
[ Deterministic Aerodynamic Physics ]     [ Observable Stale Telemetry ]   [ Pitch Sensor Withheld ]
- Error < 6.8% at h=1, h=6                (Known delay tau=10-60 min)      (Missing pitch telemetry)
- Strictly lower cost than neural ML                   |                                   |
- No training overhead                                v                                   v
                                        [ Non-Neural Recalibration ]     [ Consequence Latent Recovery ]
                                        - Absorbs 55.3% of loss          (Active power signature C2)
                                        - Zero weight updating                            |
                                                                                          v
                                                                          [ Independent Decision Gate ]
                                                                          Compare against Wspd-Bins:
                                                                          Does posterior beat baseline
                                                                          under matched reserve budget?
                                                                                   /             \
                                                                                 NO              YES
                                                                                 /                 \
                                                                                v                   v
                                                                        [ Deploy Wspd-Bins ]  [ Deploy STGQ ]
                                                                        (Plant-wide default)  (Only if proved)
```

### Operational Rules for Power System Engineers:
1. **Rule 1 (Telemetry Primacy)**: Always verify sensor arrival latency before selecting a reserve algorithm. Do not apply machine learning when fresh aerodynamic telemetry is present.
2. **Rule 2 (Recalibration First)**: Under known communication delays, apply state-conditional recalibration before deploying neural models.
3. **Rule 3 (Decision-Sufficiency Test)**: When blade pitch is withheld, consequence signals may be used to track operating boundaries, but **reserve margins must be sized using direct observable conditional quantiles (Wspd-Bins)** unless an independent matched-budget evaluation explicitly proves incremental decision value.
