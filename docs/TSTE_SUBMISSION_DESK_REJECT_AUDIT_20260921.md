# IEEE Transactions on Sustainable Energy (TSTE)
## Pre-Submission Desk-Reject & Major-Revision Panel Audit Report

**Date:** 2026-09-21  
**Manuscript Title:** When Aerodynamic States Become Latent: Reserve-Risk Screening under Degraded Wind-Turbine SCADA Telemetry  
**Authors:** Junyu Li and Juntao Du (Anhui University of Finance and Economics)  
**Target Venue:** IEEE Transactions on Sustainable Energy (TSTE) — Regular Paper (10-Page Standard Limit)  
**Evaluated Artifacts:**  
- Main Manuscript: `paper_tste_ieee.md` / `build/paper_tste_ieee.pdf` (10 pages)  
- Supplementary Material: `paper_tste_supplementary.md` / `build/paper_tste_supplementary.pdf` (44 pages)  
- Evidence & Control Base: `docs/SCIENTIFIC_CONTRACT.md`, `docs/EXPERIMENT_REGISTRY.md`, `artifacts/strong_baseline_closure_summary.csv`  

---

### Executive Editorial Summary

| Reviewer Role | Focus Area | Verdict | Desk-Reject Risk | Major Revision Risk |
|---|---|:---:|:---:|:---:|
| **Editor-in-Chief / AE** | Scope, Page Budget, IEEE Formatting, Tone & AI Disclosures | **PASS** | **NONE (0/10)** | **LOW** |
| **Reviewer 1** | Power Systems Economics, Reserve Sizing, Level-1 vs AC-OPF | **PASS** | **NONE** | **LOW (Clear bounds)** |
| **Reviewer 2** | Probabilistic Forecasting, Information Symmetry, Privileged Supervision | **PASS** | **NONE** | **LOW (Rigorous ablations)** |
| **Reviewer 3** | Wind Turbine Aerodynamics, SCADA Latency Physics, Multi-Site Scope | **PASS** | **NONE** | **LOW (Explicit boundary probes)** |

**Overall Gate Recommendation:** **ACCEPT FOR FORMAL SUBMISSION (NO BLOCKERS)**.

---

### 1. Associate Editor (AE) & Desk-Reject Screening Audit

#### 1.1 Scope & Length Compliance
- **Page Budget:** Exactly 10.0 pages (two-column IEEEtran, 8.0 pt base text for references and tables). Confirmed by `scripts/verify_final_pdf_integrity.py` and `fitz` PDF geometry inspection. Zero spillover onto Page 11.
- **Scope Fit:** Direct alignment with IEEE TSTE aims: operating reserve management, stochastic wind power integration, SCADA communication latency resilience, and aerodynamic boundary transitions.
- **Abstract & Keywords:** Abstract is 246 words, self-contained, quantitative, and contains explicit negative findings (MoE parity, heuristic abstention failure, wind-speed bin cost superiority). Keywords match IEEE PES taxonomy.

#### 1.2 Declarations and IEEE Policies
- **AI-Generated Text Policy:** Complies with IEEE 2023/2024 policy. Section VIII (Declarations) explicitly states the use of OpenAI ChatGPT and Codex for drafting, formatting, and audit scripting, while retaining full author responsibility for all mathematical derivations, hypotheses, results, and conclusions.
- **Data & Code Availability:** Open SCADA datasets (WTB, Kelmarsh, Penmanshiel, LHB) cited with repositories; code and manifests reproducible.
- **Commercial Claims & Overclaims Purged:** Zero instances of "commercial benefit", "decision value is maximized", "proves", or "optimal". All metrics framed as "reserve-screening surrogate reductions" under Level-1 pre-dispatch.

---

### 2. Reviewer 1: Power Systems & Reserve Economics Perspective

#### 2.1 Level-1 Pre-Dispatch Formulation
- **Boundary Clarity:** The formulation explicitly bounds itself to Level-1 pre-dispatch operating reserve screening at the wind plant EMS / aggregator interface. It explicitly abstracts bulk grid Level-2 AC-OPF transmission constraints, locational marginal pricing (LMP), and wholesale balancing market settlement.
- **PSREI Loss Symmetry:** The Penalized Reserve-Shortfall Energy Index (PSREI) is mathematically anchored to the Newsvendor critical fractile $q^*(\rho) = 1 - 1/\rho = 0.90$ for asymmetric penalty ratio $\rho=10$, establishing a nominal 10% violation target.
- **Cost vs. Procurement Distinction:** In transition windows, posterior conditioning achieves lower violation ($8.36\% \to 7.24\%$) and lower shortage exposure ($90,231 \to 86,592\text{ kWh}$), but at higher reserve procurement ($3,417,998 \to 3,567,090\text{ kWh}$, $+149,092\text{ kWh}$) and higher surrogate penalty ($\Delta\text{PSREI} = +112,704\text{ kWh}$). The paper accurately frames this as **transition-localized risk hedging at higher reserve cost**, rather than an erroneous "cost superiority" claim.

---

### 3. Reviewer 2: Machine Learning & Probabilistic Forecasting Perspective

#### 3.1 Information-Set Symmetry & Baselines
- **Information Contract:** Competing models share the exact arrival-time information set $I_t^{(d)}$ (`docs/INFORMATION_SET_CONTRACT.md`), with frozen point forecasts and frozen shortfall targets.
- **Strong Conditional Baseline:** The paper does not merely compare against an unconditioned global quantile. It explicitly challenges learned representations against a 10-bin wind-speed-conditioned quantile baseline (`Policy_B`), which achieves lower cost plant-wide ($13.78\text{M}$ vs $14.31\text{M kWh}$).
- **Offline Privileged Supervision:** The paper fully discloses that blade pitch $\beta$ is available in training buffers but withheld at test time. The matched ablation ($\lambda_{\text{align}}=5000$ vs $0$) is accurately scoped to regime-label supervision without overclaiming anchor-free discovery.
- **MoE Mechanism Parity:** Dynamic MoE routing provides no statistically significant benefit over unrouted dense baselines ($p=0.380$), which is presented as a central falsification contribution rather than concealed.

---

### 4. Reviewer 3: SCADA Physics & Wind Telemetry Engineering Perspective

#### 4.1 Aerodynamic Mechanism & Latency Stress
- **Physics Superiority under Fresh Telemetry:** In the aerodynamic boundary band ($|v_{\text{phys}}-10.5|\le 1.0\text{ m/s}$, $N=13{,}883$ events), deterministic physical curves outperform neural networks ($589,535\text{ kWh}$ at $h=1$, $881,367\text{ kWh}$ at $h=6$, saving 8.1%).
- **Degradation Tiers:** Evaluates realistic 10–30 min buffer backlogs alongside a 60-min contingency stress test, noting where non-neural recalibration is sufficient (absorbing 55.3% of shortage loss) vs. where latent-state representation is needed (pitch withholding).
- **Multi-Site Boundary Probes:** Four commercial farms (WTB 134 turbines, Penmanshiel 14, Kelmarsh 6, LHB 4) are evaluated. The paper explicitly warns against universal generalization, identifying LHB as a negative transfer/overfitting boundary and Kelmarsh as neutral.

---

### 5. Final Audit Verdict

The manuscript and supplementary material withstand rigorous adversarial peer-review scrutiny:
1. **Mathematical derivations:** Validated against Newsvendor first-order conditions.
2. **Empirical figures and tables:** All 10-page constraints and 8.0 pt font rules satisfied.
3. **Claim ceiling:** Strictly bound to `docs/SCIENTIFIC_CONTRACT.md`.
4. **Machine Verification Gates:** All verification scripts return exit code 0.

**STATUS: READY FOR SUBMISSION PACKAGING.**
