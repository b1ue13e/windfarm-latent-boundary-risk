# EXP-01 Experiment Audit Report

**Date:** 2026-10-12
**Project:** 跨风电场备用筛查的时空图迁移与局部条件基线决策增益评估
**Experiment:** EXP-01 / E01
**Auditor:** Local evidence audit; external cross-model reviewer unavailable (request timeout)

## Overall Verdict: WARN -> corrected v2 executed

## Integrity Status: corrected execution verified; independent cross-model review unavailable

The original v1 benchmark violated the frozen-point-forecast separation in its implementation: shortfall was derived from the transferred challenger prediction. The protocol was repaired and EXP-01 was rerun. The corrected v2 uses independent external-site `external_wind_full_seed{201..205}` point forecasts and reconstructs realized targets/masks from the canonical external cache by anchor index. The corrected CSV was archived as artifact v2 and verified. The independent cross-model reviewer request still timed out, so the audit is not an independent PASS.

## Checks

### A. Ground Truth Provenance: WARN

**Evidence:** `scripts/run_exp01_matched_control_benchmark.py:464-475`.

The realized target is loaded from `trans_test["target"]`, which is dataset/cache-derived. However, the evaluated shortfall is constructed as `np.maximum(pred_test_h - target_test_h, 0.0)`, where `pred_test_h` is taken from the transferred model's test prediction. The code comment calls this a canonical frozen point forecast, but no independent frozen forecast artifact or loader is used in this function. The same transferred prediction is therefore used to define the evaluation target for all methods. This is a protocol risk under the frozen-target and same-information rules and must be resolved or explicitly reclassified as a transferred-model-proxy evaluation.

### B. Score Normalization: PASS with scope note

**Evidence:** `scripts/run_exp01_matched_control_benchmark.py:293-311`, `:338-385`.

PSREI is computed directly as `(reserve + RHO * shortage) * DT`; violation rate is the direct fraction of target cells exceeding reserve. The block bootstrap uses paired block-level sums and ratios. No denominator is taken from a model's own maximum, mean, or minimum output. The reported p-value is an empirical bootstrap probability `mean(delta_c <= 0)`, not a conventional independent-sample p-value; this naming should be made explicit in tables and manuscript text.

### C. Result File Existence and Reproducibility: WARN

**Evidence:** `artifacts/external_matched_control_benchmark.csv`, `docs/EXPERIMENT_REGISTRY.md:253-337`, `.agent_state/EVIDENCE_LEDGER.md:1062-1078`, artifact metadata for `external-matched-control-benchmark v1`.

The current CSV exists, has 80 rows, 23 columns, no missing cells, five seeds (201-205), two horizons, two farms, four model labels, and no duplicate `(farm, seed, horizon, model)` keys. The current file hash is `b042ce934a9edd01f6fceaca21df57bca6cf4899fcddd09f26df3a59dd197ce7`, whereas the saved artifact v1 records hash prefix `4b7e77f4d1c901fb`. The CSV was regenerated after artifact v1 was saved; a new artifact version must be saved before treating the current CSV as the archived result.

### D. Dead Code Detection: WARN

**Evidence:** `scripts/run_exp01_matched_control_benchmark.py:421-441`, `:188-290`.

`features_all`, `anc_tr`, `target_tr`, `mask_tr`, and `s_tr` are loaded or constructed but are not used by the evaluation loop. The No-Graph MLP is trained from validation data only (`:490-498` and `:210-245`), with an internal chronological 70/30 split, so the nominal train-split preparation is dead code. This does not prove numerical invalidity, but it creates a mismatch between the registry's stated train/validation protocol and the executed control training path.

### E. Scope Assessment: PASS with claim boundary

**Evidence:** `artifacts/external_matched_control_benchmark.csv`; `scripts/run_exp01_matched_control_benchmark.py:48-59`; `docs/EXPERIMENT_REGISTRY.md:309-337`.

The executed scope is two external farms evaluated separately, five seeds, two horizons, four models, and 2,000 bootstrap resamples with 144 ten-minute steps per block. This is adequate for the registered two-site boundary probe, but not for claims about all external farms, universal spatial redundancy, or a universal causal law. The registry now contains the appropriate restriction; the README does not itself present EXP-01 as a universal result.

### F. Evaluation Type: real_gt with proxy-target risk

The realized target is dataset/cache-provided SCADA target data (`:95-96`, `:464-469`). The reserve policy target, however, is a shortfall derived from the transferred model's point prediction rather than an independently loaded frozen point forecast. Therefore the evaluation is `real_gt` for realized power but has a model-derived proxy component for the shortfall target until the frozen forecast source is verified.

## Verified Execution Facts

- Penmanshiel: 14 operational turbines in the current cache; wind-speed missingness 0.63% in the executed run.
- Kelmarsh: 6 turbines; wind-speed missingness 2.10% in the executed run.
- Seeds: 201, 202, 203, 204, 205.
- Horizons: h=1 and h=6.
- Current CSV rows: 80.
- Current primary-endpoint rows: 10 (two farms x five seeds at h=6 for Transferred STGQ).
- Current mean primary deltas: Penmanshiel +448,045.54 kWh, mean bootstrap probability 0.1854; Kelmarsh +48,493.73 kWh, mean bootstrap probability 0.2725.
- Architecture audit artifact integrity: `no-graph-architecture-audit-v1` verifies OK; STGQ 110,012 parameters, No-Graph Architectural Control 4,865 parameters.

## Required Actions Before Scientific Completion

1. Identify and load the independent frozen point forecast specified by `docs/FIXED_TARGET_CONTRACT.md`, or explicitly downgrade EXP-01 to a transferred-prediction proxy experiment and remove frozen-target claims.
2. Re-run all 2 farms x 5 seeds x 2 horizons after freezing the corrected target source.
3. Save the regenerated CSV as a new versioned artifact and verify its SHA256 against the artifact metadata.
4. Rename `p_val_delta_psrei` to an unambiguous bootstrap-probability field or document the exact interpretation everywhere it is reported.
5. Remove or use the dead train-split preparation code and reconcile the No-Graph training protocol with the registry.
6. Obtain an independent cross-model integrity review; the attempted reviewer request timed out and is not evidence of PASS.

## Claim Impact

- Claim 1, execution coverage: **supported**.
- Claim 2, two-site descriptive result under the current script: **supported with protocol warning**.
- Claim 3, absence of decision gain under the frozen-target contract: **pending until independent frozen forecast is verified or the estimand is reclassified**.
- Claim 4, universal redundancy of spatial graphs: **unsupported and forbidden by the scientific contract**.
