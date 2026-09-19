# Verification Gate Report

Generated: 2026-09-19T13:12:11+08:00

## Command: verify_final_pdf_integrity
`python scripts/verify_final_pdf_integrity.py`
Exit: 0
```
=== Auditing Main IEEE PDF: build/paper_tste_ieee.pdf ===
Total pages: 10

--- Checking Required Phrases ---
  [PASS] Found required phrase: '13,883'
  [PASS] Found required phrase: 'boundary-active'
  [PASS] Found required phrase: 'site-dependent'
  [PASS] Found required phrase: 'not turbine count alone'
  [PASS] Found required phrase: 'explicit disclosure that pitch is available in training inputs but withheld in validation/test deployment'

--- Checking Banned Phrases ---
  [PASS] Confirmed absent: 'Commercial benefit'
  [PASS] Confirmed absent: 'N < 20'
  [PASS] Confirmed absent: 'N >= 50'
  [PASS] Confirmed absent: 'N <= 6'
  [PASS] Confirmed absent: 'N >= 14'
  [PASS] Confirmed absent: 'decision value is maximized'

--- Checking Headline Number Proximity Qualifiers ---
Number 589,535 found 5 times:
  [PASS] Occurrence #1 at index 1434: qualifier present=True
  [PASS] Occurrence #2 at index 5574: qualifier present=True
  [PASS] Occurrence #3 at index 24726: qualifier present=True
  [PASS] Occurrence #4 at index 37150: qualifier present=True
  [PASS] Occurrence #5 at index 53526: qualifier present=True
Number 881,367 found 6 times:
  [PASS] Occurrence #1 at index 1480: qualifier present=True
  [PASS] Occurrence #2 at index 5601: qualifier present=True
  [PASS] Occurrence #3 at index 24781: qualifier present=True
  [PASS] Occurrence #4 at index 30732: qualifier present=True
  [PASS] Occurrence #5 at index 33368: qualifier present=True
  [PASS] Occurrence #6 at index 53550: qualifier present=True

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
  [PASS] docs/REPOSITORY_EVIDENCE_MAP.md (12,051 bytes)
  [PASS] docs/CANONICAL_RESEARCH_QUESTION.md (5,461 bytes)
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
  [PASS] docs/DECISION_VALUE_MEDIATION.md (5,135 bytes)
  [PASS] artifacts/mediation_analysis.csv (2,979 bytes)
  [PASS] docs/FAILURE_FALLBACK_BOUNDARY.md (7,217 bytes)
  [PASS] docs/CLAIM_LANGUAGE_AUDIT.md (7,594 bytes)
  [PASS] docs/DECISIVE_EVIDENCE_GATE.md (6,695 bytes)
  [PASS] build/paper_tste_ieee.pdf (179,111 bytes)
  [PASS] build/paper_tste_supplementary.pdf (1,011,531 bytes)

[Audit Step 2: Information-Set Symmetry]
  [PASS] Information-set manifest validated (819 rows, zero forward leakage)

[Audit Step 3: Fixed Forecast Residuals]
  [PASS] Fixed residuals validated across 5 seeds and 6 horizons (keys: 28)

[Audit Step 4: Direct Baselines Compliance Audit]
  [PASS] B3 GBDT breaches grid compliance at h=6 (14.98% > 10.0%), confirming tree baseline failure under wake advection

[Audit Step 5: Factorial Latent-Boundary Ablation Audit]
  [PASS] Negative control F_Random_Posterior breaches compliance (11.41% > 10.0%)
  [PASS] MoE vs Dense Parity at h=6 pitch-withheld: Dense=15,471,506 kWh vs Routed=15,768,203 kWh (Dense matches or beats Routed)

[Audit Step 6: Posterior Calibration Gate]
  [PASS] All uncalibrated ECE values pass strict gate: max ECE = 3.46% <= 5.00%

[Audit Step 7: Channel Consequence Mechanism]
  [PASS] C2 Active Power confirmed dominant mechanism (Brier=0.0112, NMI=0.461)
  [PASS] C4 Thermal confirmed unable to detect fast transitions (recall=0.0%)

[Audit Step 8: Decision-Value Mediation Concentration]
  [PASS] Mediation confirmed: Dynamic Transition Windows account for 48.4% of total savings (p=0.0000)

[Audit Step 9: IEEE Paper Page Budget Constraint]
  [PASS] IEEE paper page count = 10 <= 10.0 pages (COMPLIANT)

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

## Verdict
PASS
