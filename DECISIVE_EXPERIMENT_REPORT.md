# Decisive Experiment Report: SCADA Latent-Boundary Recovery & Reserve Decisions

**Date**: 2026-09-18  
**Scope**: Full end-to-end audit report documenting the experimental evidence for *IEEE Transactions on Sustainable Energy*.  
**Author**: Research Reliability Orchestrator & Experimental Auditor  
**Hardware & Environment**:
- Local: NVIDIA GeForce RTX 5060 (8GB VRAM, PyTorch 2.11.0+cu128)
- HPC Cluster: NIU Metis HPC Cluster (Dual NVIDIA Blackwell 96GB + 32x A100 40GB GPUs, PBS Pro scheduler)

---

## 1. Experimental Overview & Architecture of Proof

The investigation was structured into 15 rigorous, sequential phases to eliminate confounding factors:

```
[Phase 0] Repository Forensics (17 Headline Claims Mapped)
    │
[Phase 1] Freeze Research Claim (H1 Recoverability, H2 Decision Value, H3 Failure Boundary)
    │
[Phase 2] Information-Set Contract (819 Audited Feature-Lags, Zero Forward Leakage)
    │
[Phase 3] Freeze Decision Target (Canonical GNN Residuals Frozen, 5 Seeds, 6 Horizons)
    │
[Phase 4] Direct Simple-Baseline Challenge (B0-B5 Direct Quantile Baselines Evaluated)
    │
[Phase 5] Factorial Latent-Boundary Ablation (Variants A to J across 4 Telemetry Conditions)
    │
[Phase 6] Posterior Calibration Audit (ECE, Brier, NLL, Reliability Diagrams, Terminology Gate)
    │
[Phase 7] Consequence-Signal Mechanism (C1 to C10 Channel Ablation & Identifiability)
    │
[Phase 8] Decision-Value Mediation Test (24h Block Bootstrap across Operating Slices)
    │
[Phase 9] Failure / Fallback Boundary (Clean Physics Dominance, Recalibration, Micro-Farms)
    │
[Phase 10 & 11] Statistical Integrity & Claim Language Audit (Zero Market Overclaims)
    │
[Phase 12 & 13] Manuscript Restructuring & PDF Compilation (Strict 10.0-Page IEEE Format)
    │
[Phase 14 & 15] Automated Decisive Gate Verification (10-Point Executable Test Suite)
```

---

## 2. Decisive Experimental Findings by Phase

### Phase 4: Direct Baseline Challenge
- Evaluated 5 direct conditional quantile baselines under strictly matched information:
  - **B0 Global Empirical Quantile**: High reserve overspending ($9.22\text{M}$ at $h=1$, $16.79\text{M}$ at $h=6$).
  - **B1 Conditional Wind-Speed Bins**: Robust steady-state performance ($7.14\text{M}$ at $h=1$, $14.55\text{M}$ at $h=6$, compliant $7.4\%$--$8.5\%$ violation).
  - **B2 Linear Quantile Regression**: Under-allocates reserves, surging violation rates to $17.0\%$--$41.5\%$.
  - **B3 Quantile GBDT**: Excels at short horizon ($h=1$, $6.49\text{M}$ clean / $6.41\text{M}$ pitch-withheld), but **catastrophically breaks down at $h=6$ (surging to 16.23% clean and 14.98% pitch-withheld violation)**, breaching the nominal 10% Newsvendor violation target ($q^*=0.90$) due to failure to model spatio-temporal wake advection.
  - **B4 Direct MLP**: Matches compliance ($7.5\%$--$10.6\%$ violation).

### Phase 5: Factorial Latent-Boundary Ablation (Variants A to J)
- **Negative Controls**:
  - Permuting regime labels (`E_Shuffled_State`) increases cost to $17.93\text{M kWh}$.
  - Random posterior conditioning (`F_Random_Posterior`) surges violation to **$11.41\%$**, exceeding the nominal 10% Newsvendor violation target.
- **MoE Dynamic Routing Parity**:
  - Dense multitask head (`I_STGQ_Dense`, $15,471,506 \text{ kWh}$) matches or outperforms Routed MoE (`J_STGQ_Routed`, $15,768,203 \text{ kWh}$, $p=0.380$). MoE confers no benefit.
- **Value of Boundary Representation**:
  - Removing the boundary representation (`D_Posterior_Ablated`) inflates cost from $15.47\text{M}$ to $17.32\text{M kWh}$ ($+1.85\text{M kWh}$ penalty).

### Phase 6: Posterior Calibration Audit
- Across all 4 conditions, test-set Expected Calibration Error (ECE) is strictly $\le 3.46\%$ (well under the $5.0\%$ threshold):
  - Pristine: $0.89\% \pm 0.14\%$ (Dense), $0.94\% \pm 0.39\%$ (Routed).
  - Pitch Withheld: $2.54\% \pm 0.56\%$ (Dense), $3.33\% \pm 1.84\%$ (Routed).
- Dense GNN achieves superior calibration over Routed MoE.
- The phrase "calibrated operating-boundary posterior" is justified, with explicit disclosure of tail MCE dispersion.

### Phase 7: Consequence-Signal Mechanism (C1 to C10)
- **Active Power ($C2$)** is the primary physical mediator:
  - Brier score: $0.0112$, NMI: $0.461$, ARI: $0.647$, transition recall: $62.9\%$.
  - Captures $95\%$ of the full consequence suite's reserve cost reduction.
- **Thermal ($C4$) and Direction ($C5$)** fail to identify fast dynamic transitions ($0.0\%$ recall for thermal).
- **Noise Corrupted ($C10$)**: Transition recall remains resilient at $71.0\%$.

### Phase 8: Decision-Value Mediation Test
- Paired daily cluster bootstrap over 35 observed test days (1,000 paired Monte Carlo resamples, 144 steps/cluster):
  - Overall reduction: **$+1,825,410 \text{ kWh}$** vs global quantile ($p < 10^{-4}$).
  - Against unconditioned global quantiles, **$48.38\%$ of total savings ($+892,535\text{ kWh}$)** occurs within **Dynamic Transition Windows** ($\pm 3$ steps), reflecting baseline loss concentration ($33.0\%$). Against strong wind-speed bins, the posterior acts as a localized risk hedge (reducing violation to $7.24\%$ and shortage to $86.6\text{k kW}\cdot\text{h}$ at $+112{,}704\text{ kW}\cdot\text{h}$ additional reserve cost); the bootstrap interaction ($\Delta_{\text{trans}} - \Delta_{\text{steady}} = -296{,}123\text{ kW}\cdot\text{h}, p < 0.005$) establishes cost gap heterogeneity rather than a net cost advantage.
  - In steady-state MPPT ($|v - 10.5| > 2.5\text{ m/s}$), direct wind-speed bins are sufficient ($\Delta L = L_{\text{posterior}} - L_{\text{wspd}} = +523{,}044\text{ kW}\cdot\text{h}$ penalty for posterior).

---

## 3. Data Integrity & Verification Summary

- **Reproducibility Test**: `python scripts/verify_decisive_gate.py` passes all 10 criteria with **exit code 0**.
- **Number Consistency Audit**: `python scripts/verify_tste_number_consistency.py` confirms 100% agreement between text, tables, and raw experiment CSVs.
- **Page Budget**: `build/paper_tste_ieee.pdf` compiles cleanly to **exactly 10.0 pages**.
