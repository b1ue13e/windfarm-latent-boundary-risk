# IEEE TSTE Transfer Execution

This note turns the Applied Energy major-revision fallback into the active IEEE Transactions on Sustainable Energy route.

## Target Claim

Primary claim:

> SCADA-anchored mixture-of-experts routing can make the MPPT-to-pitch control boundary auditable in wind-power forecasting, exposing where a low-RMSE graph forecaster loses operating-regime accountability.

The manuscript must not claim forecasting SOTA, reserve-policy superiority, automatic cross-site reserve transfer, or full dispatch readiness. It may claim bounded anchor-observable cross-site mechanism replication on La Haute Borne after local retraining and held-out routing checks.

## Manuscript Rewrite

- Replace the Applied Energy reserve-diagnostics title with a TSTE-facing title such as `SCADA-Anchored Regime-Aware Routing for Auditable Wind-Turbine Control-Boundary Forecasting`.
- Compress the paper to the IEEE PES Transactions initial-submission budget of 10 double-column pages.
- Remove ERA5 from the main paper unless a page-budget exception is explicitly justified; keep WTB as the main wind-energy case.
- Keep reserve evidence as a short boundary-risk vignette, not as the central contribution.
- Report the train-only class-weight rerun as the RMSE guardrail (229.93 versus 224.34 for iTransformer) and the legacy boundary-forced checkpoint as the fully archived operational-audit run.
- Report physical-bin quantile baselines as honest controls that bound any reserve-policy claim.
- Report La Haute Borne as cross-site mechanism replication and Kelmarsh/Penmanshiel as external boundary-condition failure, not as automatic transfer success.

## Anchor-Stress Completion

Run the training-level anchor-observability stress sequence before citing anchor robustness:

```powershell
python main.py anchor-stress-cache --dataset wtb --root-dir . --source-cache-dir artifacts/cache_strictmask/wtb_245d --output-cache-root artifacts/cache_anchor_stress --variants no_patv,lagged_patv,no_pab_mean,lagged_pab_wspd

python main.py anchor-stress-train --cache-root artifacts/cache_anchor_stress --output-root artifacts/anchor_stress_runs --variants no_patv,lagged_patv,no_pab_mean,lagged_pab_wspd --seeds 201,202,203,204,205 --skip-visuals

python main.py anchor-stress-guard --suite-root artifacts/anchor_stress_runs --cache-root artifacts/cache_anchor_stress --output-dir artifacts/anchor_stress_guard --variants no_patv,lagged_patv,no_pab_mean,lagged_pab_wspd --seeds 201,202,203,204,205 --min-nmi 0.65
```

Run the post-hoc label-degradation audit before citing operational early-warning value:

```powershell
python main.py anchor-stress-early-warning --suite-root artifacts/strictmask_validation_wtb_full --output-dir artifacts/anchor_stress_early_warning_wtb_strictmask --variants canonical --seeds 201,202,203,204,205
```

Decision rule:

- `complete_anchor_stress_supports_partial_anchor_robustness`: cite partial anchor robustness.
- `complete_anchor_stress_requires_claim_downgrade`: keep declared-anchor-constrained routing language.
- `ready_to_execute_anchor_stress_training`: do not cite training-level anchor robustness.
- `blocked_anchor_stress_leakage_guard_failed`: do not submit until the leakage issue is resolved.
- `complete_anchor_stress_supports_label_degradation_value`: cite operational gate value under delayed, missing, or noisy threshold labels. Do not call it a future-label predictor unless the pre-trigger ranking slice is explicitly separated.

Current five-seed strictmask readout: with a six-step label delay, gate recall on early MPPT-to-pitch pitch cells is 0.960 +- 0.028 versus 0.196 for the delayed threshold rule; with 50% label availability, gate recall remains 0.960 versus 0.508 for the available-label rule.

## Minimum Evidence Tables

The TSTE paper should retain only these table-level claims in the main text:

- WTB forecasting tradeoff: train-only RMSE guardrail versus iTransformer, plus legacy full-audit route alignment.
- Ablation table: unconstrained MoE, alignment, boundary force, and anchor-only/router controls.
- Anchor stress summary after the new three-step protocol.
- Anchor-stress early-warning label-degradation curve if page budget allows; otherwise cite it in supplementary evidence.
- External wind deployment-gate table with La Haute Borne replication and Kelmarsh/Penmanshiel failure metrics.
- Compact reserve-risk vignette showing same-model gate-bin value and physical-bin lower-cost bound.

## Acceptance Checklist

- The abstract leads with SCADA-anchored routing audit, not reserve procurement.
- The contribution statement says `auditability`, `responsibility assignment`, and `control-boundary diagnosis`.
- The limitations explicitly say the method is not anchor-free physical discovery.
- The final package provenance lists `anchor-stress-cache / anchor-stress-train / anchor-stress-guard / anchor-stress-early-warning`.
- All code changes are covered by targeted tests before manuscript conversion starts.

## Build And Submission Environment Notes

Two environment conditions used to break `scripts/prepare_tste_submission.ps1` on a new machine or after disk cleanup. The current scripts now run these checks automatically, but the notes below remain useful for diagnosis.

### 1. `rg` (ripgrep) must be on PATH

The submission script scans the XeLaTeX logs for blocking warnings. It uses `rg` when available and falls back to PowerShell `Select-String` when `rg` is missing, so a clean build no longer depends on ripgrep being installed.

If you still want the faster scanner, put `rg.exe` on PATH before running the build, for example:

```powershell
$env:PATH = "C:\Users\<user>\AppData\Local\OpenAI\Codex\bin\<hash>;" + $env:PATH
```

To sanity-check the logs independently of `rg`:

```powershell
$logPattern = "Font Warning|No file TUptm|undefined citation|Citation .* undefined|Overfull|Undefined control sequence|Some font shapes|TU/ptm|LaTeX Warning: Reference.*undefined|undefined references|LaTeX Error"
Get-Content build/paper_tste_ieee.log, build/paper_tste_supplementary.log | Select-String -Pattern $logPattern
```

### 2. Restore run `target.npy` / `mask.npy` after cleanup

Space-saving cleanup may strip the bulky `target.npy` and `mask.npy` from the run metrics dirs (each `*_metrics` folder), keeping `pred.npy` and `anchor_index.npy`. The evidence step `scripts/build_outcome_channel_sanity.py` then fails with `FileNotFoundError: ...val_metrics/target.npy`, which aborts `build_paper_ieee.ps1` and the package build.

The build and submission scripts now run `scripts/restore_run_targets.py` before generating evidence tables. These two arrays are an exact function of the windowed cache (`target` window = `cache_target[t+1 : t+1+P]` from the still-present `anchor_index`). To diagnose or run the step manually:

```powershell
python scripts/restore_run_targets.py            # runs referenced by the reviewer stat-pack run table
python scripts/restore_run_targets.py --scan     # every run dir under artifacts/ missing the arrays
python scripts/restore_run_targets.py --dry-run  # report only, write nothing
```

The utility refuses to write unless the reconstruction reproduces each run's stored `overall.rmse`, so it cannot corrupt evidence. The restored arrays are git-ignored and can be deleted again to reclaim space, then regenerated on demand.
