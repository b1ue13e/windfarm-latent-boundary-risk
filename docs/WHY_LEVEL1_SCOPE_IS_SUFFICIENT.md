# Why Level-1 Reserve Screening is the Intentional and Sufficient Scope Boundary

**Date**: 2026-09-26  
**Document**: Architectural and Scope Justification  
**Target Venue**: *IEEE Transactions on Sustainable Energy*  
**Governing Standard**: `docs/SCIENTIFIC_CONTRACT.md` (Section 3: "End-to-end market/AC-OPF economic value is out of scope / blocked")

---

## 1. Five-Point Downstream Dispatch Gate Evaluation

In accordance with the preregistered research protocol (`docs/TSTE_OPERATIONAL_RELEVANCE_PREREGISTRATION.md`), the decision to implement a downstream operational grid dispatch layer (e.g., AC-OPF or multi-bus economic dispatch) was subjected to five mandatory criteria:

| Gate Criterion | Evaluation | Verdict |
| :--- | :--- | :---: |
| **1. Established Public Test System** | While standard IEEE test systems (e.g., RTS-96, IEEE 14-bus, IEEE 30-bus) exist, connecting a 134-turbine wind farm to a specific bus requires arbitrary choices of bus location, line capacity scaling, and penetration fraction. | **PARTIALLY MET** |
| **2. Non-Heuristic Reserve Pass-Through** | Passing turbine-level or PCC reserve margins into a centralized dispatch model requires ad-hoc rules for generator slack participation, nodal deliverability, and transmission margin reservation. | **FAILED** |
| **3. Non-Collinear Objective Function** | In standard linear or linearized security-constrained dispatch, system-level reserve costs are mathematically proportional to the plant-level asymmetric loss function $\sum_t [c_r r_t + c_u (\Delta P_t - r_t)^+]$. The system objective is mathematically collinear with aggregated PSREI. | **FAILED** |
| **4. Transparent Network & Generator Assumptions** | Introducing a multi-bus network requires parameterizing thermal generator ramp rates, minimum up/down times, heat-rate curves, start-up costs, and transmission line thermal ratings. None of these parameters originate from wind SCADA physics; they introduce massive ungrounded confounding variance. | **FAILED** |
| **5. Preservation of Stated Scope** | The paper's core scientific question addresses the inferential link between **SCADA observability, latent-boundary recoverability, and reserve-decision sufficiency**. Expanding into transmission congestion management converts the paper into an OPF paper and obscures the physical SCADA mechanism. | **FAILED** |

**Gate Outcome: FAILED (3 of 5 criteria violated)**.  
Under the preregistered stop rule, **a downstream AC-OPF dispatch experiment must NOT be implemented**. Instead, the manuscript must rigorously defend Level-1 reserve screening as the appropriate and sufficient scientific contribution.

---

## 2. Power Systems Engineering Hierarchy: Level-1 vs. Level-2

Modern power system operations partition wind integration into distinct operational layers:

```
[Level 1: Wind Plant Boundary Sizing & Screening]  <-- THIS PAPER'S EXPLICIT SCOPE
  - Direct SCADA telemetry arrival (fresh, delayed, or withheld pitch)
  - Point forecasting and residual distribution estimation
  - Asymmetric reserve requirement sizing: r_t = F^{-1}(q*(rho))
  - Output: Reliable plant-level schedule & reserve envelope passed to TSO/ISO
         |
         v
[Level 2: System-Level Grid Scheduling & Dispatch]  <-- INTENTIONALLY EXCLUDED
  - Transmission network power flow (DC/AC-OPF)
  - Security-constrained unit commitment (SCUC / SCED)
  - Multi-generator re-dispatch, thermal ramping, line congestion
```

### Why Level-1 Screening is Scientifically Necessary
1. **Direct Mechanism Localization**:  
   SCADA telemetry degradation (e.g., pitch sensor latency, packet dropouts, withholding) occurs directly at the wind turbine electromechanical interface. Its physical consequences—aerodynamic transition lag, rotor inertia response, and active power deficit—materialize at the turbine and plant boundary. Level-1 screening isolates these telemetry-driven shortfall mechanisms without confounding them with transmission line congestion elsewhere in the grid.
2. **Model Complexity Audit**:  
   The central scientific inquiry asks: *Does recovering the latent operating state $Z_t$ justify deploying complex neural architectures (e.g., MoE, GNNs) for reserve sizing?* Level-1 screening directly answers this question by showing that a simple observable conditional quantile (wind-speed binning) achieves lower expected cost ($+523{,}044$ kWh posterior penalty) and lower unserved shortage under matched budget (+5,234 kWh penalty). If a complex model fails to provide incremental decision value at Level-1, embedding it inside a Level-2 OPF layer cannot rescue its fundamental information deficit.
3. **Decoupling from Arbitrary Network Topologies**:  
   If a study claims that a wind model improves grid dispatch by evaluating an IEEE 14-bus test case, the conclusion is inevitably sensitive to whether line 1-2 or line 4-5 happens to congest. A paper published on wind SCADA observability should not depend on arbitrary line impedance parameters chosen for a 1960s synthetic test feeder.

---

## 3. Mathematical Equivalence Under Congestion-Free Operations

Consider a transmission-constrained system dispatch problem:
$$\min_{P_g, r_g, r_w} \sum_{g \in \mathcal{G}} C_g(P_g) + \sum_{g \in \mathcal{G}} c_{r, g} r_{g} + c_{r, w} r_w + \mathbb{E}\left[ c_u \left( \sum_{g \in \mathcal{G}} \Delta P_g + \Delta P_w - r_{\text{sys}} \right)^+ \right]$$
When the wind farm is operated as an active participant providing its own reserve margin $r_w$, and transmission lines within the local interconnection are adequately sized (the standard assumption for plant-level grid connection studies), the marginal cost of wind reserve is separable:
$$\frac{\partial \mathcal{L}_{\text{sys}}}{\partial r_w} = c_{r, w} - c_u \cdot \mathbb{P}(\Delta P_w > r_w)$$
Setting this derivative to zero yields the exact Newsvendor critical quantile:
$$q^*(\rho) = 1 - \frac{1}{\rho}, \quad \rho \equiv \frac{c_u}{c_{r, w}}$$
Thus, **PSREI is the exact single-period objective of the wind plant operator under standard grid code compliance**. Evaluating PSREI directly measures the wind farm's ability to fulfill its grid reservation commitments without triggering balancing market penalties.

---

## 4. Multi-Year Empirical Validation via UK Balancing Market (Elexon BMRS)

To ensure that Level-1 screening does not rely solely on theoretical Newsvendor assumptions, the manuscript validated reserve decisions against **157,804 real settlement periods** from the UK electricity market (Elexon BMRS, 2016–2024, Table A12).

Evaluating actual half-hourly System Buy Prices (SBP) and System Sell Prices (SSP):
- Over 9 continuous years, across both flat (Kelmarsh) and complex (Penmanshiel) terrains;
- At realistic balancing market penalty ratios ($\rho \in [5, 20]$);
- The qualitative conclusions remained **100% directionally consistent**:
  - The direct observable baseline remains the cost-effective reserve policy across commercial operations;
  - State recoverability remains distinct from decision superiority;
  - Real market volatility does not overturn the Level-1 screening conclusion.

---

## 5. Scope Boundary Conclusion

The manuscript's deliberate limitation to Level-1 reserve screening is not an empirical gap, but a **rigorous methodological boundary**:
1. It localizes the impact of degraded SCADA observability to its native physical domain.
2. It establishes that latent-boundary representation learning lacks incremental decision sufficiency against strong observable baselines.
3. It avoids confounding wind turbine aerodynamic telemetry with arbitrary transmission network assumptions.
4. It is empirically verified by multi-year commercial market data.
