# Verification Gate Report

Generated: 2026-10-15T10:34:56+08:00

## Command: verify_final_pdf_integrity
`python scripts/verify_final_pdf_integrity.py`
Exit: 0
```
=== Auditing Main IEEE PDF: E:\璁烘枃3\build\paper_tste_ieee.pdf ===
Total pages: 10

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
  [PASS] Occurrence #1 at index 996: qualifier present=True
  [PASS] Occurrence #2 at index 5219: qualifier present=True
  [PASS] Occurrence #3 at index 8493: qualifier present=True
  [PASS] Occurrence #4 at index 27696: qualifier present=True
  [PASS] Occurrence #5 at index 36646: qualifier present=True
  [PASS] Occurrence #6 at index 59267: qualifier present=True
Number 881,367 found 7 times:
  [PASS] Occurrence #1 at index 1021: qualifier present=True
  [PASS] Occurrence #2 at index 5246: qualifier present=True
  [PASS] Occurrence #3 at index 8518: qualifier present=True
  [PASS] Occurrence #4 at index 27751: qualifier present=True
  [PASS] Occurrence #5 at index 30248: qualifier present=True
  [PASS] Occurrence #6 at index 32884: qualifier present=True
  [PASS] Occurrence #7 at index 59291: qualifier present=True

[ALL IEEE PDF CHECKS PASSED]

=== Auditing Supplementary PDF: E:\璁烘枃3\build\paper_tste_supplementary.pdf ===
Total pages: 46

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
  [PASS] docs/REPOSITORY_EVIDENCE_MAP.md (12,327 bytes)
  [PASS] docs/CANONICAL_RESEARCH_QUESTION.md (5,825 bytes)
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
  [PASS] docs/FAILURE_FALLBACK_BOUNDARY.md (8,150 bytes)
  [PASS] docs/CLAIM_LANGUAGE_AUDIT.md (8,571 bytes)
  [PASS] docs/DECISIVE_EVIDENCE_GATE.md (7,010 bytes)
  [PASS] build/paper_tste_ieee.pdf (269,582 bytes)
  [PASS] build/paper_tste_supplementary.pdf (1,017,110 bytes)

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

## Command: verify_replication
`python scripts/verify_replication.py`
Exit: 0
```

--- Step 1: Validating Artifact Manifest & Cryptographic Hashes ---
Loaded manifest with 46 registered artifacts.
  [ALL 46 ARTIFACTS VERIFIED WITH VALID SHA256]

--- Step 2: Auditing Regime 1 Physics Baselines (Table I & II) ---
  [PASS] C01 [Regime 1]: Clean Physics h=1 PSREI (5-seed mean)
         Target: 589,535 kWh | Replicated: 589,535 kWh 
  [PASS] C02 [Regime 1]: Clean Physics h=6 PSREI (5-seed mean)
         Target: 881,367 kWh | Replicated: 881,367 kWh 
  [PASS] C03 [Regime 1]: Clean Physics h=6 Violation Rate
         Target: 6.81% | Replicated: 6.81% 
  [PASS] C04 [Regime 1]: Missingness-Aware GBDT h=6 Breaches 10% Target
         Target: 16.23% (>10.0%) | Replicated: 16.23% 

--- Step 3: Auditing Regime 2 Recalibration (Table III & IV) ---
  [PASS] C05 [Regime 2]: Recalibration shortage absorption at tau=60 min (channel_mode=all)
         Target: 66.5% of 127.552 -> 42.787 MWh | Replicated: 66.46% 
  [PASS] C05b [Regime 2]: Recalibration shortage absorption across the 10-30 min operational grid
         Target: 36.3% / 53.9% / 61.7% at tau=10/20/30 | Replicated: 36.28% / 53.89% / 61.72% 
  [PASS] C06 [Regime 2]: Recalibrated shortage at tau=60 min
         Target: 42.787 MWh | Replicated: 42.787 MWh 
  [PASS] C06b [Regime 2]: Recalibrated Physics tau=60 Cost
         Target: 1,228,609 kWh | Replicated: 1,228,609 kWh 
  [PASS] C07 [Regime 2]: Uncalibrated Posterior Max ECE <= 5.0%
         Target: <= 5.0% | Replicated: 3.46% 

--- Step 4: Auditing Latent Boundary Recovery & Channel Ablations ---
  [PASS] C08 [Regime 3]: Active Power AUROC (5-seed mean)
         Target: 0.988 | Replicated: 0.988 
  [PASS] C09 [Regime 3]: Transition Recall Gain (Model vs Rule)
         Target: 0.417 vs 0.196 | Replicated: 0.417 vs 0.196 
  [PASS] C10 [Ablations]: C2 Active Power Dominant Mechanism (Brier)
         Target: < 0.05 | Replicated: 0.0112 
  [PASS] C11 [Ablations]: C4 Thermal Unable to Detect Fast Transitions (Recall)
         Target: 0.0% | Replicated: 0.0% 

--- Step 5: Auditing Strong Baseline Closure & Statistical Interaction ---
  [PASS] C12 [Strong Baseline]: Plant-Wide Posterior PSREI Penalty (+523,044 kWh)
         Target: +523,044 kWh | Replicated: +523,044 kWh 
  [PASS] C13 [Strong Baseline]: Transition Interaction Delta (p < 0.01)
         Target: -296,053 kWh (p<0.01) | Replicated: -296,053 kWh (p=0.002) 

--- Step 6: Auditing Matched-Budget Frontier & Rho Sensitivity ---
  [PASS] C14 [Matched Budget]: Accounting Identity C = R + 10 U Closes Numerically
         Target: Max Err < 0.05 kWh | Replicated: Max Err = 0.0000 kWh 
  [PASS] C15 [Matched Budget]: Shortage Increases at Matched Budget (Delta U > 0)
         Target: > 0 kWh (4/5 seeds fail) | Replicated: +5,234.0 kWh (4/5 seeds) 
  [PASS] C16 [Rho Sensitivity]: Absence of Economic Crossover for rho >= 5 (Transition Mean)
         Target: Delta PSREI > 0 for all rho in [5, 100] | Replicated: 9 conditions positive (rho=10: +112,739 kWh, rho=100: +998,216 kWh) 

--- Step 7: Auditing External-Site Transferability & Directional Asymmetry ---
  [PASS] C17 [External Sites]: Directional Asymmetry (Kelmarsh->Penm vs reverse)
         Target: 0.770 vs 0.341 | Replicated: 0.770 vs 0.341 
  [PASS] C18 [External Sites]: LHB Micro-Farm Overfitting Boundary Guard
         Target: NMI 0.941, ARI 0.971 | Replicated: NMI 0.941, ARI 0.971 (anchor_observable_replication_passed_not_portability_not_reserve_transfer) 

--- Step 8: Auditing Lightweight Table Regeneration & Submission Numbers ---
  Regenerating lightweight table: artifacts/tste_number_consistency_audit/tste_number_consistency_audit.csv ...
  [PASS] Lightweight table regenerated cleanly with relative paths.
  [PASS] C19 [Submission Audit]: Full Submission Number Consistency (all registered display tokens)
         Target: all 77 checks passed | Replicated: 77/77 passed (0 failed) 

============================================================================
REPLICATION VERIFICATION AUDIT REPORT
============================================================================

Total Headline Claims Evaluated: 21
Passed: 21 | Failed: 0

VERDICT: FULLY_REPRODUCIBLE (ALL 21 CLAIMS VERIFIED WITH EXIT 0)

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
  [PASS] contract marker present: Architectural-control non-equivalence rule
  [PASS] contract marker present: Transition-slice diagnostic boundary rule
  [PASS] contract marker present: Synthetic telemetry envelope rule

[6] EXP-01, EXP-02, EXP-03 Control & Evidence Integrity
  [PASS] EXP-01 v2 benchmark verified (80 rows, 5 seeds, 2 farms)
  [PASS] EXP-02 verified with corrected Primary Challenger role classification
  [PASS] EXP-03 evaluated population fixed ([408937, 408939]) with disclosed imputation boundary (max drop=60.25%, max stale=99.79%)
  [PASS] Joint hierarchical uncertainty summary verified

[7] Stale-Content Re-Pollution Guard (F6)
  [PASS] experiments/E01/log.md: no live (unmarked) superseded v1 numbers
  [PASS] docs/NO_GRAPH_CONTROL_AUDIT.md: no live (unmarked) superseded v1 numbers
  [PASS] docs/EXPERIMENT_REGISTRY.md: no live (unmarked) superseded v1 numbers
  [PASS] architecture audit parameter count self-consistent (110,012) and claim ceiling intact
  [PASS] NO_GRAPH_CONTROL_AUDIT.md retains nomenclature + causal-necessity ceilings
  [PASS] experiment registry has no open duplicate PROPOSED/BLOCKED registration
  [PASS] docs/EXP03_ASYNCHRONOUS_REPORT.md: EXP-03 trace provenance not overstated
  [PASS] docs/EXPERIMENT_REGISTRY.md: EXP-03 trace provenance not overstated
  [PASS] EXP-03 staleness disclosed (max stale=0.9979, max drop=0.6025)

[8] EXP-02 Verdict Integrity Guard (F4)
  [PASS] role assignment: challenger is Primary Challenger, Oracle restricted to Privileged STGQ
  [PASS] verdict gates on C1 (mean <= 0) and C2 (P >= 0.95), with diagnostics non-gating
  [PASS] registry does not present a stale 'DEFICIT ESTABLISHED' EXP-02 verdict
  [PASS] EXP-02 emits P(delta <= 0) under the non-inferiority name; legacy name appears only in the schema-migration mapping
  [PASS] joint report generator is labelled seed-level, not two-level hierarchical
  [PASS] EXP-02 report Section 3 does not claim an uncomputed two-level interval
  [PASS] EXP-02 report runner derives the Section 3 heading from block-delta availability

[9] Phase 2 Retrospective Analysis & Native Blocks Guard
  [PASS] strong baseline native day blocks verified (10 arrays x 35 blocks)
  [PASS] strong baseline hierarchical joint interaction verified: -297565.4 kWh, P=0.9824
  [PASS] strong_baseline_bootstrap_contrasts.csv verified free of arithmetic Mean CI/p-values
  [PASS] EXP-01 v4 native day blocks verified (80 arrays x 35 blocks)
  [PASS] EXP-01 v4 statistics verified: Penmanshiel h=6 delta=-315400 kWh (CI spans zero), Kelmarsh h=6 delta=+352434 kWh (penalty)
  [PASS] Phase 2 retrospective scientific audit report verified: PASS
  [PASS] manuscript updated with retrospective hierarchical numbers

========================================================================
SCIENTIFIC_CLAIM_GATE: PASS

```

## Verdict
PASS
