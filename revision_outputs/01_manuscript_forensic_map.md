# Forensic Audit Map: Empirical Claims, Models, and Evidence Artifacts
## Target: IEEE Transactions on Sustainable Energy (TSTE)
**Framework**: Spatio-Temporal Graph Quantile (STGQ) & Operational Boundary Analysis  
**Branch**: `revision_topjournal_reconstruction`  
**Date**: September 2026  

---

## 1. Executive Forensic Architecture

This forensic map indexes every empirical assertion, mathematical formulation, and evidence file underpinning the manuscript *"Operational Boundaries of Aerodynamic Power Rules, Recalibration, and Learned Representations under SCADA Telemetry Degradation"*. 

```
                                      [Empirical SCADA Telemetry]
                                                   │
                  ┌────────────────────────────────┴────────────────────────────────┐
                  ▼                                                                 ▼
      【Regime I: Pristine Telemetry】                                【Regimes II & III: Stale / Missing Telemetry】
      (Fresh SCADA, Full Observability)                             (Communication Delay, Burst Drops, Withheld Pitch)
                  │                                                                 │
                  ▼                                                                 ▼
      Deterministic Aerodynamic Quantile                            Telemetry Failure Modes:
      • h=1 Cost: 589,535 kW·h (6.8% viol)                         • Delay-6 (60 min outage contingency)
      • h=6 Cost: 881,367 kW·h (6.8% viol)                         • Withheld Pitch (no_pab across OEM firewalls)
      • Superior to all neural models                              • Markov-Gilbert burst dropouts (p_GB=0.08, p_BB=0.75)
                  │                                                                 │
                  │                                         ┌───────────────────────┴───────────────────────┐
                  │                                         ▼                                               ▼
                  │                            【State-Conditional Recalibration】             【Learned Representations (STGQ)】
                  │                            • Absorbs 55.3% shortage                       • Reconstructs aerodynamic state from
                  │                            • 127.6 -> 57.0 MWh shortage                     electromechanical transients (Patv, Q, V)
                  │                            • Violation: 10.7%                              • Withheld pitch advantage: 46.7k-68.6k kW·h
                  │                            • Zero neural parameter overhead                • Recall doubles: 0.416 vs 0.196
                  │                                                                            • Modular (Frozen + Residual): 1.284M kW·h
                  │                                                                            • Dense vs. MoE Parity (p=0.380)
                  └─────────────────────────────────────────┬───────────────────────────────────────┘
                                                            │
                                                            ▼
                                        【PCC Fleet-Wide Portfolio Aggregation】
                                        • Local aerodynamic errors cancel at 134-turbine bus
                                        • Net plant risk reduction: -2.32M kW·h vs. Global PCC
                                        • -1.33M kW·h in transitional regimes
                                                            │
                                                            ▼
                                        【Downstream Dispatch Interface (BESS MPC)】
                                        • Relegated to Supplementary Material
                                        • Illustrates 32.1% cost cut & 45.7% shortage mitigation
```

---

## 2. Model Inventory & Architectural Taxonomy

| Model Class | Code Designation | Architecture Details | Parameters | Primary Operational Purpose | Evidence Artifact Path |
|:---|:---|:---|:---|:---|:---|
| **Deterministic Physical Quantile** | `continuous_physical_quantile` | $C_p(\lambda, \beta)$ polynomial aerodynamic curve with soft-pitch transition | 0 | Ground-truth baseline under fresh telemetry; reveals reliability collapse under latency | `artifacts/clean_evidence_v2/risk_layer_benchmark/` |
| **State-Conditional Recalibration** | `recal_physical_quantile` | Quantile regression conditional on stale operating bin | 0 (lookup) | Lightweight non-neural adaptation; absorbs primary distribution drift under full observability | `artifacts/clean_evidence_v2/risk_layer_benchmark/` |
| **Tabular Lag Baseline** | `missingness_aware_gbdt` | LightGBM / XGBoost with lag features | ~50k | Tests short-lag autocorrelation vs. spatial wake diffusion across horizons | `artifacts/modular_classifier_reserve_control/` |
| **Spatio-Temporal Graph Backbone** | `Graph WaveNet` | Dilated causal 1D convolution + Adaptive Graph Diffusion | ~310k | Standard STGNN baseline for spatial wake modeling | `artifacts/paper_assets/tables/table_main_benchmark.csv` |
| **Transformer Baselines** | `iTransformer`, `PatchTST` | Channel-inverted Attention / Patch tokenization | ~450k | State-of-the-art long-sequence deep time-series baselines | `artifacts/paper_assets/tables/table_main_benchmark.csv` |
| **Proposed STGQ Backbone** | `Dense (matched)` | Directed wake diffusion + GRU encoder + linear quantile head | 110k | Core learned representation without routing complexity; establishes parity with MoE | `artifacts/trainweight_class_weight_rerun_20260702/` |
| **Ablation Comparator** | `MoE (Boundary-forced)` | Directed wake diffusion + GRU + 3-expert dynamic router + $\mathcal{L}_{\mathrm{force}}$ | 110k (matched) | Evaluates value of dynamic routing over unrouted shared representations | `artifacts/paper_assets/tables/table_wtb_ablation.csv` |
| **Decoupled Modular Architecture** | `Frozen Backbone + Residual Quantile` | Pretrained spatio-temporal embedding + standalone pinball quantile MLP | 110k + 8k | Single-checkpoint utility edge deployment; matches MoE reserve performance | `artifacts/modular_classifier_reserve_control/` |

---

## 3. Empirical Claims Ledger & Quantitative Targets

### Claim Cluster 1: Physical Rule Primacy and Latency Breakdown
- **Pristine Telemetry Performance**: At $h=1$, continuous physical quantile achieves **589,535 kW·h** (6.8% violation). At $h=6$, it achieves **881,367 kW·h** (6.8% violation). Both outperform all deep neural architectures.
  - *Evidence File*: `artifacts/clean_evidence_v2/risk_layer_benchmark/h1_lead1/results_by_seed.csv` and `h6_lead6/results_by_seed.csv`.
- **Latency Reliability Collapse**: Under synthetic 6-step (60-min) latency (outage contingency stress), static physical quantile violation surges to **24.0% ± 1.7%** ($h=1$) and **12.20% ± 1.25%** ($h=6$), resulting in **127.6 MWh** of unhedged shortfall exposure.
  - *Evidence File*: `artifacts/clean_evidence_v2/risk_layer_benchmark/h6_lead6/results_by_seed.csv`.

### Claim Cluster 2: Disentangling Recalibration from Neural Representation
- **Recalibration Dominance under Full Observability**: Condition-matching state-conditional recalibration absorbs **55.3%** of shortage ($127.6 \to 57.0\text{ MWh}$, violation $10.7\%$, delivery cost **1,228,609 kW·h**). Learned neural posteriors achieve **10.6% ± 1.1%** violation and **53.9 MWh** shortage (incremental gain only 5.4%).
  - *Empirical Takeaway*: Under full observability, complex neural networks are not cost-effective.
- **Learned Representation Primacy under Withheld Pitch**: When blade pitch is concealed across OEM boundaries (`no_pab`), learned representations reconstruct operating regimes from electromechanical transients ($\texttt{Patv}, Q, V$), saving **46.7k–68.6k kW·h** over recalibrated physics across all latencies and doubling boundary recall (**0.416 vs. 0.196**).
  - *Evidence File*: `artifacts/fair_degradation_replay_20260903/fair_degradation_summary.csv`.

### Claim Cluster 3: Demystification of Mixture-of-Experts (MoE)
- **Statistical Parity with Dense Backbone**: On pristine telemetry, Dense (matched) and MoE achieve a delivery cost ratio of **1.045** ($p=0.380$, paired two-sided t-test). Under Delay-6, MoE's modest nominal difference (+79,637 kW·h, raw $p=0.038$) is non-significant under Bonferroni correction ($\alpha = 0.0125$).
- **Decoupled Architecture Viability**: A decoupled modular pipeline (*Frozen Backbone + Residual Quantile*) achieves **1.284M kW·h** delivery cost and **9.68%** violation, demonstrating that reserve benefits originate from spatio-temporal feature extraction and decoupled quantile calibration, not dynamic routing.
  - *Evidence File*: `artifacts/modular_classifier_reserve_control/modular_classifier_reserve_summary.csv`.

### Claim Cluster 4: Fleet-Wide PCC Spatial Smoothing
- **Plant-Level Net Risk Reduction**: Aggregating 134 turbines at the Point of Common Coupling (PCC) cancels uncorrelated local turbulence. Joint posterior quantile pricing saves **-2.32M kW·h** (95% CI [-6.07M, +1.73M]) against Global PCC Quantile and **-1.37M kW·h** against Gaussian parametric reserve sizing. In transitional regimes (10%–90% pitching), it saves **-1.33M kW·h** (95% CI [-1.68M, -1.07M], strictly negative).
  - *Evidence File*: `artifacts/farm_aggregate_reserve_20260905/farm_pcc_paired_summary.csv`.

### Claim Cluster 5: Cross-Farm Generalization & Operational Boundary
- **Three Commercial Utility Farms**: Architecture successfully adapts via local chronological retraining on Kelmarsh (6 turbines, MM92) and Penmanshiel (15 turbines, MM82), yielding walk-forward pooled savings of **-6.19M kW·h** and **-4.34M kW·h**.
- **La Haute Borne (LHB) Negative Case as Operational Boundary**: On the 4-turbine LHB site, learned models add **+1.01M kW·h** (walk-forward) and **+43k kW·h** (annual). This is formally documented as an operational boundary condition: in micro-farms with severe terrain distortion and only 4 turbines, spatial wake graph learning overfits and lacks spatial cancellation.
  - *Evidence File*: `artifacts/iec_density_rolling_eval/iec_rolling_guard.json`.

---

## 4. Metric Scale Standard & Conversion Guide

To ensure consistency across the manuscript:
1. **Primary Single Dispatch Horizon Metric**:
   - $h=1$ (10 min) and $h=6$ (1 hour) delivery cost: **kW·h per dispatch interval**.
   - Values: Clean $\approx 589\text{k}\sim 881\text{k}\text{ kW}\cdot\text{h}$; Delay-6 $\approx 1.13\text{M}\sim 1.28\text{M}\text{ kW}\cdot\text{h}$.
2. **Multi-Horizon Accumulated Metric**:
   - 24-step multi-horizon accumulated cost ($\approx 15.5\text{M kW}\cdot\text{h}$) is explicitly marked as a full-horizon envelope and placed in Supplementary Material to prevent reviewer confusion.
3. **Historical 95M Remnant**:
   - The historical $95.13\text{M}$ figure in Section IV-G was calculated over the entire 35-day test set ($5{,}040$ intervals). In the main manuscript, this is standardized to average dispatch interval cost ($1.28\text{M kW}\cdot\text{h}$ per interval) or converted to MWh with explicit temporal duration.
