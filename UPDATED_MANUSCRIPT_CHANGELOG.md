# Updated Manuscript Changelog: IEEE Transactions on Sustainable Energy

**Date**: 2026-09-18  
**Target Manuscript**: `paper_tste_ieee.md` $\to$ `build/paper_tste_ieee.pdf` (10.0 Pages)  
**Supplementary Material**: `paper_tste_supplementary.md` $\to$ `build/paper_tste_supplementary.pdf` (17.0 Pages)

---

## 1. Summary of Structural Refactoring

The paper was fundamentally restructured from an incremental engineering paper ("Mixture-of-Experts improves wind power forecasting") into a rigorous, falsifiable scientific paper addressing **latent operating-boundary recovery under degraded SCADA telemetry**:

```
BEFORE REFACTORING:
  - Framed around "MoE routing superiority" (falsified: MoE has no benefit, p=0.380).
  - Unbounded claims of machine learning replacing aerodynamic power curves (falsified: physics beats ML by 8.1% in boundary band when telemetry is fresh).
  - Wholesale market cashflow and revenue claims without clearing model (invalidated: removed in favor of Level-1 PSREI engineering units).

AFTER REFACTORING:
  - Centered on the Central Scientific Question of boundary recoverability and asymmetric reserve decision value.
  - Formally bounded by four failure/fallback boundaries where simple physics or empirical recalibration dominates.
  - Rigorously audited against 5 direct conditional quantile baselines, negative controls, and paired daily cluster bootstrap CIs over 35 observed days (1,000 resamples).
  - Strict 10.0-page IEEE Transactions on Sustainable Energy budget.
```

---

## 2. Page-by-Page Itemized Manuscript Changelog

| Page / Section | Original Narrative / Defect | Updated Evidence-Grounded Implementation | Scientific Grounding |
| :--- | :--- | :--- | :--- |
| **Page 1: Title, Abstract, Keywords** | Promoted MoE routing and generic deep learning forecasting gains. | Retitled: *"When Aerodynamic States Become Latent: Reserve-Risk Screening under Degraded Wind-Turbine SCADA Telemetry"*. Abstract declares that physical rules beat ML when telemetry is clean ($881\text{k vs } 15.06\text{M kWh}$); state recalibration absorbs $55.3\%$; MoE provides zero routing benefit ($p=0.380$). | Phase 0, 1, 9 audit |
| **Page 2: Section I (Introduction)** | Claimed universal superiority of spatio-temporal AI over engineering models. | Formulated three bounded Research Questions (RQ1: Physical Breakdown Boundary, RQ2: Recalibration vs Latent Recovery, RQ3: Falsification of MoE Routing). | Phase 1 Canonical Research Question |
| **Page 3: Section II & III (Problem Formulation)** | Ambiguous market cashflow claims; mixed point forecast and reserve stages. | Established two-level grid hierarchy: strictly bounded to Level-1 Pre-Dispatch Screening (PSREI energy proxy, $\rho=10$, $q^*=0.90$, kWh/MWh) and disclaiming Level-2 AC-OPF clearing. Formalized fixed point-forecast stage separation. | Phase 2 & 3 Contracts |
| **Page 4: Section IV (Methodology)** | Overemphasized dynamic MoE routing gates. | Demoted MoE to an ablation comparator. Formalized spatio-temporal encoder, latent boundary classification head, and two-stage residual quantile sizing. | Phase 5 Factorial Design |
| **Page 5: Section V (Direct Baselines & Telemetry Breakdown)** | Lacked direct simple baseline challenge. | Embedded Table I: Direct simple baselines (B0 to B5). Showed B3 GBDT excels at $h=1$ but breaches the nominal 10% Newsvendor violation target at $h=6$ ($16.23\%$ clean, $14.98\%$ pitch-withheld violation). | Phase 4 Empirical Results |
| **Page 6: Section V (Failure of Physical Rules)** | Only reported aggregate metrics. | Dissected the cubic sensitivity cliff transition: unadapted physical rules surge violation to $24.0\%$ under 60-min latency, leaving $127.6\text{ MWh}$ unhedged shortfall. | Phase 0 Provenance Audit |
| **Page 7: Section VI (Factorial Latent-Boundary Ablation)** | Did not separate representation, boundary labels, and routing. | Embedded Table II: Factorial ablation (Variants A to J). Proved negative controls fail ($11.41\%$ violation) and Dense multitask head matches or beats Routed MoE ($15.47\text{M}$ vs $15.77\text{M kWh}$, $p=0.380$). | Phase 5 Summary CSV |
| **Page 8: Section VI (Consequence Mechanism & Calibration)** | Asserted boundary recovery without channel breakdown or calibration audit. | Embedded Table III: C1--C10 channel ablation proving Active Power ($C2$) drives recovery (Brier $0.0112$, NMI $0.461$, recall $62.9\%$), while thermal/direction fail. Referenced Figure 2 reliability diagrams (ECE $\le 3.46\%$). | Phase 6 & 7 Evidence |
| **Page 9: Section VII (Mediation & Operational Decision Matrix)** | Claimed uniform value across all operating regimes. | Embedded Table IV: Mediation analysis proving $48.38\%$ of savings ($+892\text{k kWh}$) is concentrated in transition windows ($\pm 3$ steps), while direct bins are sufficient for steady MPPT. Provided 4-rule operator decision matrix. | Phase 8 & 9 Audits |
| **Page 10: Section VIII (Conclusion & References)** | Overclaimed future expansion to commercial markets. | Restrained conclusion affirming conditional utility of latent boundary recovery, disclaiming steady MPPT superiority, and listing exact failure boundaries. Clean references fitting exactly on page 10. | Phase 10 & 15 Gate Verification |

---

## 3. Verification & Compliance Confirmation

- **IEEE Page Budget**: Exactly 10.0 pages (verified via `pypdf`).
- **Number Consistency**: Verified via `python scripts/verify_tste_number_consistency.py` (complete consistency, zero mismatches).
- **Decisive Gate Suite**: Verified via `python scripts/verify_decisive_gate.py` (exit code 0).
