# Preregistration: TSTE Operational Relevance & Cross-Site Heterogeneity Pass

**Date**: 2026-09-26  
**Git Baseline Commit**: `a273a05b8a67ccbc24d1b55ee2e0208ae31ff373`  
**Git Branch**: `revision_topjournal_reconstruction`  
**Status**: FROZEN PRIOR TO ANALYSIS  
**Governing Standard**: `docs/SCIENTIFIC_CONTRACT.md`

---

## 1. Scientific Core Freeze

This preregistration establishes an immutable claim ceiling for the final operational relevance and cross-site diagnostic pass for IEEE Transactions on Sustainable Energy.

### Central Thesis
The manuscript does not study whether Mixture-of-Experts (MoE), Graph Neural Networks (GNN), or deep neural networks are universally superior forecasting or control tools. The investigation strictly evaluates the three-stage inferential chain:

$$\text{SCADA Observability} \implies \text{Latent-State Recoverability} \centernot\implies \text{Downstream Decision Sufficiency}$$

Latent operating-boundary transitions remain partly recoverable from already-arrived consequence telemetry (predominantly the active-power signature) when pitch angle is withheld at deployment. However, **latent-state recoverability does not imply downstream reserve-decision superiority**. Strong direct observable baselines (specifically wind-speed-conditioned quantiles) remain the minimum sufficient plant-wide reserve policy in the evaluated industrial setting.

### Locked Empirical Benchmarks (Must NOT be Altered)
1. **Regime 1 (Clean SCADA)**: Deterministic aerodynamic physics dominates at $h=1$ ($589,535$ kWh) and $h=6$ ($881,367$ kWh) with low violation rate ($6.81\%$). GBDT breaches nominal $10\%$ Newsvendor target at $h=6$ ($16.23\%$).
2. **Regime 2 (Observable Latency)**: Non-neural state-conditional recalibration absorbs $55.3\%$ of delay-induced shortage loss at $\tau=60$ min ($1,228,609$ kWh). Uncalibrated posterior ECE passes gate ($\le 3.46\% \le 5.0\%$).
3. **Regime 3 (Withheld Pitch / Boundary Recovery)**: Active power AUROC achieves $0.988$. Transition recall improves from $0.196$ (heuristic rule) to $0.417$ (model). Active-power channel C2 dominates the mechanism (Brier $= 0.0112$, NMI $= 0.461$). Thermal channel C4 fails to detect fast transitions (recall $= 0.0\%$).
4. **Strong-Baseline Closure & Negative Results**:
   - Plant-wide posterior PSREI incurs a net cost penalty of **$+523,044$ kWh** ($p=0.85$) against 10-bin wind-speed quantiles.
   - Steady-state ($63.7\%$ of time) wind-speed binning strictly dominates posterior (+410,340 kWh penalty, $p=0.002$).
   - Transition window ($36.3\%$ of time) posterior acts as a localized tail-risk hedge (violations $8.36\% \to 7.24\%$, shortages $90.2\text{k} \to 86.6\text{k}$ kWh, reserve $+149\text{k}$ kWh, PSREI $+112,704$ kWh).
   - Significant transition interaction delta: $-296,053$ kWh ($p=0.002$).
5. **Matched-Reserve-Budget Frontier**:
   - At matched reserve budget ($\Delta R = 0$), posterior yields **$+5,234.0$ kWh higher shortage** on average; 4 of 5 random seeds fail.
   - No economic crossover exists for reoptimized policies at $\rho \ge 5$.
6. **Cross-Site Transferability**:
   - Directional asymmetry: Kelmarsh $\to$ Penmanshiel ($0.770$) vs Penmanshiel $\to$ Kelmarsh ($0.341$).
   - LHB micro-farm ($N=4$ turbines) establishes an empirical overfitting boundary (NMI $= 0.941$, ARI $= 0.971$).
7. **Number Consistency**: All 73 reported tokens match repository artifacts exactly.

---

## 2. Reviewer Risk Scope & Objectives

The final scientific pass addresses two residual reviewer vulnerabilities without altering frozen conclusions:
- **Risk A (Grid Operational Realism)**: Reviewers questioning whether PSREI is an adequate decision surrogate for Level-1 reserve sizing without running a full AC-OPF or market dispatch simulation.
- **Risk B (Cross-Site Heterogeneity)**: Reviewers demanding why four commercial wind farms exhibit heterogeneous transferability and boundary behavior, and whether this can be diagnosed prior to training.

---

## 3. Preregistered Protocols & Gate Criteria

### Protocol 1: Decision-Realism Gap Audit
- **Objective**: Audit whether the Newsvendor formulation $q^*(\rho) = 1 - 1/\rho$, dynamic $\rho$-reoptimization ($\rho \in [2, 100]$), matched-budget frontiers, and PCC-level aggregation provide sufficient mathematical and empirical grounding for Level-1 reserve screening.
- **Gate / Stop Rule**: If the qualitative policy ordering ($\text{Baseline} \succeq \text{Posterior}$ plant-wide) is robust across $\rho \in [5, 100]$ and across PCC aggregation, **DO NOT add AC-OPF or complex network dispatch merely for appearance**.

### Protocol 2: Economic Interpretation of $\rho$
- Define $\rho \equiv c_u / c_r$ explicitly as a dimensionless ratio between marginal uncovered-shortfall penalty and marginal reserve-procurement cost.
- Compile a compact reference table documenting $\rho \in [2, 100]$, $q^*(\rho)$, $\Delta R$, $\Delta U$, $\Delta \text{PSREI}$, and preferred policy under dynamic reoptimization.
- Do NOT fabricate synthetic spot market prices. Authoritative market data (e.g. Elexon BMRS) may only be used as illustrative scale benchmarks.

### Protocol 3: Downstream Dispatch Experiment Feasibility Gate
A downstream operational dispatch experiment will be implemented **IF AND ONLY IF ALL FIVE** of the following conditions are met:
1. Reuses an established public test system (e.g. IEEE RTS-96 or IEEE 14/30-bus) without ad-hoc parameter tuning;
2. Reserve margins from existing policies pass directly into the dispatch layer without undocumented heuristic transformations;
3. Objective function is not mathematically collinear with PSREI;
4. Network, generator, and cost assumptions are fully transparent;
5. Does not expand the paper's scope beyond Level-1 reserve screening.
*If any condition is violated: create `docs/WHY_LEVEL1_SCOPE_IS_SUFFICIENT.md` and enforce the Level-1 scope boundary.*

### Protocol 4 & 5: Descriptive Cross-Site Deployment Diagnostic ($N=4$ Sites)
- Farms: **WTB** (134 turbines), **Kelmarsh** (6 turbines), **Penmanshiel** (15 turbines), **LHB** (4 turbines).
- Strict non-inferential rule: **NO regression models with $N=4$**. No turbine-level pseudo-replication.
- Compute descriptive diagnostics strictly without deployment label leakage:
  1. Transition prevalence ($\%$ operating time in boundary band);
  2. Transition synchrony across turbines (mean pairwise co-occurrence);
  3. Spatial active-power correlation (mean and robust median);
  4. Nearest-neighbor spatial dependence / correlation distance;
  5. Wake-graph connectivity (effective degree / graph density);
  6. Consequence-channel recoverability (AUROC / NMI);
  7. Fraction of boundary-active observations;
  8. Turbine count / plant scale reference;
  9. Decision outcome ($\Delta \text{PSREI}$ or equivalent reserve delta).
- Language guard: Wording must remain descriptive and hypothesis-generating ("consistent with variation in exploitable spatial redundancy"), never causal ("spatial redundancy causes the gain").

### Protocol 6: Manuscript Claim Surgery
- Audit manuscript text to purge residual claims of universal machine learning superiority, unproved grid compliance, or over-claimed causal mechanisms.
- Retain exact claim boundaries: consequence signals preserve recoverable boundary information, but downstream reserve-decision sufficiency must be tested independently against strong observable baselines.

---

## 4. Acceptance Criteria & Final Verdict Options

Execution must conclude with one of three formal verdicts:
1. `READY_TO_SUBMIT`: All evidence, scope limitations, and reviewer-1 stress tests are closed within Level-1 reserve screening.
2. `READY_WITH_EXPLICIT_SCOPE_LIMITATION`: Reviewer risks are resolved by rigorous scope boundaries and descriptive diagnostics.
3. `ADDITIONAL_OPERATIONAL_VALIDATION_REQUIRED`: Internal contradictions or unresolvable empirical gaps remain.
