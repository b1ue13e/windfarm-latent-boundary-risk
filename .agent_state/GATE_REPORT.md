# Verification Gate Report

Generated: 2026-09-25T07:39:32+08:00

## Command: verify_final_pdf_integrity
`python scripts/verify_final_pdf_integrity.py`
Exit: 0
```
=== Auditing Main IEEE PDF: build/paper_tste_ieee.pdf ===
Total pages: 9

--- Checking Required Phrases ---
  [PASS] Found required phrase match: '13,883'
  [PASS] Found required phrase match: 'boundary-active'
  [PASS] Found required phrase match: 'site-dependent'
  [PASS] Found required phrase match: 'not turbine count alone / turbine count alone does not explain'
  [PASS] Found required phrase match: 'explicit disclosure that pitch is available in training inputs but withheld in validation/test deployment'

--- Checking Banned Phrases ---
  [PASS] Confirmed absent: 'Commercial benefit'
  [PASS] Confirmed absent: 'N < 20'
  [PASS] Confirmed absent: 'N >= 50'
  [PASS] Confirmed absent: 'N <= 6'
  [PASS] Confirmed absent: 'N >= 14'
  [PASS] Confirmed absent: 'decision value is maximized'

--- Checking Headline Number Proximity Qualifiers ---
Number 589,535 found 6 times:
  [PASS] Occurrence #1 at index 1000: qualifier present=True
  [PASS] Occurrence #2 at index 4865: qualifier present=True
  [PASS] Occurrence #3 at index 7245: qualifier present=True
  [PASS] Occurrence #4 at index 25503: qualifier present=True
  [PASS] Occurrence #5 at index 36251: qualifier present=True
  [PASS] Occurrence #6 at index 48574: qualifier present=True
Number 881,367 found 7 times:
  [PASS] Occurrence #1 at index 1026: qualifier present=True
  [PASS] Occurrence #2 at index 4893: qualifier present=True
  [PASS] Occurrence #3 at index 7271: qualifier present=True
  [PASS] Occurrence #4 at index 25559: qualifier present=True
  [PASS] Occurrence #5 at index 30062: qualifier present=True
  [PASS] Occurrence #6 at index 32688: qualifier present=True
  [PASS] Occurrence #7 at index 48598: qualifier present=True

[ALL IEEE PDF CHECKS PASSED]

=== Auditing Supplementary PDF: build/paper_tste_supplementary.pdf ===
Total pages: 44

--- Checking Banned Phrases in Supplementary ---
  [PASS] Confirmed absent: 'economic reserve benefit'
  [PASS] Confirmed absent: 'economic value'
  [PASS] Confirmed absent: 'reserve pricing'
  [PASS] Confirmed absent: 'Commercial benefit'

[ALL SUPPLEMENTARY PDF CHECKS PASSED]

=======================================================
VERIFICATION SUCCESS: ALL PDF ARTIFACT INTEGRITY CHECKS PASSED
=======================================================

```

## Command: verify_decisive_gate
`python scripts/verify_decisive_gate.py`
Exit: 0
```
======================================================================
      AUTOMATED DECISIVE SCIENTIFIC EVIDENCE GATE VERIFICATION       
======================================================================

[Audit Step 1: Checking Required Artifacts]
  [PASS] docs/REPOSITORY_EVIDENCE_MAP.md (12,110 bytes)
  [PASS] docs/CANONICAL_RESEARCH_QUESTION.md (5,549 bytes)
  [PASS] docs/INFORMATION_SET_CONTRACT.md (7,573 bytes)
  [PASS] artifacts/information_set_manifest.csv (133,318 bytes)
  [PASS] docs/FIXED_TARGET_CONTRACT.md (4,251 bytes)
  [PASS] artifacts/fixed_forecast_residuals.npz (173,410,167 bytes)
  [PASS] artifacts/direct_quantile_baselines_summary.csv (5,922 bytes)
  [PASS] artifacts/factorial_boundary_ablation_summary.csv (12,819 bytes)
  [PASS] docs/POSTERIOR_CALIBRATION_AUDIT.md (5,461 bytes)
  [PASS] artifacts/posterior_calibration.csv (2,985 bytes)
  [PASS] figures/posterior_reliability.pdf (35,234 bytes)
  [PASS] docs/CONSEQUENCE_SIGNAL_MECHANISM.md (4,904 bytes)
  [PASS] artifacts/channel_consequence_ablations.csv (3,608 bytes)
  [PASS] docs/DECISION_VALUE_MEDIATION.md (5,198 bytes)
  [PASS] artifacts/mediation_analysis.csv (2,979 bytes)
  [PASS] docs/FAILURE_FALLBACK_BOUNDARY.md (7,309 bytes)
  [PASS] docs/CLAIM_LANGUAGE_AUDIT.md (8,261 bytes)
  [PASS] docs/DECISIVE_EVIDENCE_GATE.md (6,803 bytes)
  [PASS] build/paper_tste_ieee.pdf (174,226 bytes)
  [PASS] build/paper_tste_supplementary.pdf (1,013,790 bytes)

[Audit Step 2: Information-Set Symmetry]
  [PASS] Information-set manifest validated (819 rows, zero forward leakage)

[Audit Step 3: Fixed Forecast Residuals]
  [PASS] Fixed residuals validated across 5 seeds and 6 horizons (keys: 28)

[Audit Step 4: Direct Baselines Compliance Audit]
  [PASS] B3 GBDT breaches nominal 10% Newsvendor violation target at h=6 (14.98% > 10.0%), confirming tree baseline failure under wake advection

[Audit Step 5: Factorial Latent-Boundary Ablation Audit]
  [PASS] Negative control F_Random_Posterior exceeds nominal 10% Newsvendor target (11.41% > 10.0%)
  [PASS] MoE vs Dense Parity at h=6 pitch-withheld: Dense=15,471,506 kWh vs Routed=15,768,203 kWh (Dense matches or beats Routed)

[Audit Step 6: Posterior Calibration Gate]
  [PASS] All uncalibrated ECE values pass strict gate: max ECE = 3.46% <= 5.00%

[Audit Step 7: Channel Consequence Mechanism]
  [PASS] C2 Active Power confirmed dominant mechanism (Brier=0.0112, NMI=0.461)
  [PASS] C4 Thermal confirmed unable to detect fast transitions (recall=0.0%)

[Audit Step 8: Decision-Value Mediation Concentration]
  [PASS] Mediation confirmed: Dynamic Transition Windows account for 48.4% of total savings (p=0.0000)

[Audit Step 9: IEEE Paper Page Budget Constraint]
  [PASS] IEEE paper page count = 9 <= 10.0 pages (COMPLIANT)

======================================================================
ALL 10 DECISIVE EVIDENCE GATES PASSED (STATUS: VERIFIED)
======================================================================

```

## Command: verify_tste_number_consistency
`python scripts/verify_tste_number_consistency.py`
Exit: 0
```
TSTE number consistency audit: complete_tste_number_consistency
Wrote E:\论文3\artifacts\tste_number_consistency_audit\tste_number_consistency_audit.csv

```

## Command: verify_scientific_claim_gate
`python scripts/verify_scientific_claim_gate.py`
Exit: 0
```
========================================================================
SCIENTIFIC CLAIM GATE
========================================================================

[1] Control-plane files
  [PASS] docs\SCIENTIFIC_CONTRACT.md
  [PASS] docs\EXPERIMENT_REGISTRY.md
  [PASS] .agents\agents\scientific-falsifier\agent.md
  [PASS] artifacts\strong_baseline_closure_summary.csv
  [PASS] artifacts\strong_baseline_bootstrap_contrasts.csv
  [PASS] paper_tste_ieee.md

[2] Strong-baseline claim ceiling
  [PASS] plant-wide posterior cost superiority is not supported (+523,044 kWh)
  [PASS] transition result is a risk hedge, not a cost win (PSREI delta +112739 kWh)
  [PASS] steady-state simple baseline remains lower-cost (+410305 kWh posterior penalty)

[3] Transition-localization interaction
  [PASS] heterogeneity retained: interaction=-296052.9 kWh, CI=[-568265.1,-39428.8], p=0.002

[4] Manuscript interpretation guard
  [PASS] claim boundary present: strong wind-speed-conditioned quantiles remain lower-cost plant-wide
  [PASS] claim boundary present: attributable to consequence-based representation and calibrated quantile sizing rather than dynamic expert routing
  [PASS] claim boundary present: state recoverability is not sufficient for downstream reserve-decision superiority
  [PASS] claim boundary present: trained using historically available pitch information that is withheld at deployment
  [PASS] no unqualified universal ML superiority
  [PASS] no unqualified cross-site generalization proof
  [PASS] no MoE mechanism superiority
  [PASS] no plant-wide posterior superiority

[5] Contract authority guard
  [PASS] contract marker present: Observability → Recoverability → Decision Sufficiency
  [PASS] contract marker present: REFUTED by current closure
  [PASS] contract marker present: Negative-result preservation rule
  [PASS] contract marker present: Older reports remain provenance records

========================================================================
SCIENTIFIC_CLAIM_GATE: PASS

```

## Verdict
PASS
