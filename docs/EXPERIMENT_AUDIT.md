# EXP-01 Experiment Audit Report

**Date:** 2026-10-12
**Project:** 跨风电场备用筛查的时空图迁移与局部条件基线决策增益评估
**Experiment:** EXP-01 / E01
**Auditor:** Local evidence audit; external cross-model reviewer unavailable (request timeout)

## Overall Verdict: WARN -> corrected v2 executed

## Integrity Status: corrected execution verified; independent cross-model review unavailable

The original v1 benchmark violated the frozen-point-forecast separation in its implementation: shortfall was derived from the transferred challenger prediction. The protocol was repaired and EXP-01 was rerun. The corrected v2 uses independent external-site `external_wind_full_seed{201..205}` point forecasts and reconstructs realized targets/masks from the canonical external cache by anchor index. The corrected CSV was archived as artifact v2 and verified. The independent cross-model reviewer request still timed out, so the audit is not an independent PASS.

## Checks

### A. Ground Truth Provenance: PASS for corrected v2; v1 FAIL retained

**Evidence:** `scripts/run_exp01_matched_control_benchmark.py:105-125`, `:485-517`.

Corrected v2 loads point forecasts from independent `external_wind_full_seed{201..205}` directories and reconstructs realized targets and masks directly from the canonical external cache. The transferred challenger prediction is no longer used to define the shared shortfall target. The original v1 violation is retained in provenance and is superseded, not erased.

### B. Score Normalization: PASS with scope note

**Evidence:** `scripts/run_exp01_matched_control_benchmark.py:293-311`, `:338-385`.

PSREI is computed directly as `(reserve + RHO * shortage) * DT`; violation rate is the direct fraction of target cells exceeding reserve. The block bootstrap uses paired block-level sums and ratios. No denominator is taken from a model's own maximum, mean, or minimum output. The reported p-value is an empirical bootstrap probability `mean(delta_c <= 0)`, not a conventional independent-sample p-value; this naming should be made explicit in tables and manuscript text.

### C. Result File Existence and Reproducibility: PASS for v2

**Evidence:** `artifacts/external_matched_control_benchmark.csv`, artifact `external-matched-control-benchmark v2`, `docs/EXPERIMENT_REGISTRY.md`, `.agent_state/EVIDENCE_LEDGER.md`.

The corrected CSV has 80 rows, 25 columns, no missing cells, five seeds, two horizons, two farms, four model labels, and no duplicate `(farm, seed, horizon, model)` keys. SHA256 is `596f46e0be8d71ab7a9965dbe4c481cc717b31c083fe288441a9ca9a39c3966e`. Artifact v2 verification returns `status=ok`. Artifact v1 remains historical provenance and is superseded.

### D. Dead Code Detection: WARN

**Evidence:** `scripts/run_exp01_matched_control_benchmark.py:421-441`, `:188-290`.

`features_all`, `anc_tr`, `target_tr`, `mask_tr`, and `s_tr` are loaded or constructed but are not used by the evaluation loop. The No-Graph MLP is trained from validation data only (`:490-498` and `:210-245`), with an internal chronological 70/30 split, so the nominal train-split preparation is dead code. This does not prove numerical invalidity, but it creates a mismatch between the registry's stated train/validation protocol and the executed control training path.

### E. Scope Assessment: PASS with claim boundary

**Evidence:** `artifacts/external_matched_control_benchmark.csv`; `scripts/run_exp01_matched_control_benchmark.py:48-59`; `docs/EXPERIMENT_REGISTRY.md:309-337`.

The executed scope is two external farms evaluated separately, five seeds, two horizons, four models, and 2,000 bootstrap resamples with 144 ten-minute steps per block. This is adequate for the registered two-site boundary probe, but not for claims about all external farms, universal spatial redundancy, or a universal causal law. The registry now contains the appropriate restriction; the README does not itself present EXP-01 as a universal result.

### F. Evaluation Type: real_gt with independent site-frozen point forecast

The corrected v2 uses dataset/cache-provided realized SCADA targets and validity masks, while the point forecast is independently loaded from the site-specific `external_wind_full_seed*` run. The reserve target is `max(site_frozen_point_forecast - realized_generation, 0)` under the registered proxy definition. It is not the transferred challenger output.

## Verified Execution Facts

- Penmanshiel: 14 operational turbines in the current cache; wind-speed missingness 0.63% in the executed run.
- Kelmarsh: 6 turbines; wind-speed missingness 2.10% in the executed run.
- Seeds: 201, 202, 203, 204, 205.
- Horizons: h=1 and h=6.
- Current CSV rows: 80.
- Current primary-endpoint rows: 10 (two farms x five seeds at h=6 for Transferred STGQ).
- Corrected v2 mean primary deltas: Penmanshiel +5,321,914.71 kWh, mean bootstrap probability 0.0025; Kelmarsh +435,683.79 kWh, mean bootstrap probability 0.1961.
- Corrected v2 SHA256: `596f46e0be8d71ab7a9965dbe4c481cc717b31c083fe288441a9ca9a39c3966e`.
- Artifact `external-matched-control-benchmark v2` verifies `status=ok`; v1 remains historical and is superseded.
- Architecture audit artifact integrity: `no-graph-architecture-audit-v1` verifies OK; STGQ 110,012 parameters, No-Graph Architectural Control 4,865 parameters.

## Remaining Actions Before Scientific Completion

1. Rename `p_val_delta_psrei` to an unambiguous bootstrap-probability field or document the exact interpretation everywhere it is reported.
2. Remove or use the dead train-split preparation code and reconcile the No-Graph training protocol with the registry.
3. Obtain an independent cross-model integrity review; the attempted reviewer request timed out and is not evidence of PASS.
4. Run the repository's final scientific falsifier and verification gate after the v2 claim update.

## Claim Impact

- Claim 1, execution coverage: **supported**.
- Claim 2, corrected two-site descriptive result: **supported for the registered v2 protocol**.
- Claim 3, original null claim: **superseded**. Corrected v2 shows a significant Penmanshiel cost penalty at h=6 and a non-significant positive delta at Kelmarsh.
- Claim 4, universal redundancy of spatial graphs: **unsupported and forbidden by the scientific contract**.
