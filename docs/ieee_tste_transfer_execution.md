# IEEE TSTE Transfer Execution

This note turns the Applied Energy major-revision fallback into the active IEEE Transactions on Sustainable Energy route.

## Target Claim

Primary claim:

> SCADA-anchored mixture-of-experts routing can make the MPPT-to-pitch control boundary auditable in wind-power forecasting, exposing where a low-RMSE graph forecaster loses operating-regime accountability.

The manuscript must not claim forecasting SOTA, reserve-policy superiority, external-site generalization, or full dispatch readiness.

## Manuscript Rewrite

- Replace the Applied Energy reserve-diagnostics title with a TSTE-facing title such as `SCADA-Anchored Regime-Aware Routing for Auditable Wind-Turbine Control-Boundary Forecasting`.
- Compress the paper to the IEEE PES Transactions initial-submission budget of 10 double-column pages.
- Remove ERA5 from the main paper unless a page-budget exception is explicitly justified; keep WTB as the main wind-energy case.
- Keep reserve evidence as a short boundary-risk vignette, not as the central contribution.
- Report Graph WaveNet's lower RMSE as the accuracy price of auditability.
- Report physical-bin quantile baselines as honest controls that bound any reserve-policy claim.
- Report Kelmarsh/Penmanshiel as external boundary-condition failure, not as transfer success.

## Anchor-Stress Completion

Run the training-level anchor-observability stress sequence before citing anchor robustness:

```powershell
python main.py anchor-stress-cache --dataset wtb --root-dir . --source-cache-dir artifacts/cache_strictmask/wtb_245d --output-cache-root artifacts/cache_anchor_stress --variants no_patv,lagged_patv,no_pab_mean,lagged_pab_wspd

python main.py anchor-stress-train --cache-root artifacts/cache_anchor_stress --output-root artifacts/anchor_stress_runs --variants no_patv,lagged_patv,no_pab_mean,lagged_pab_wspd --seeds 201,202,203 --skip-visuals

python main.py anchor-stress-guard --suite-root artifacts/anchor_stress_runs --cache-root artifacts/cache_anchor_stress --output-dir artifacts/anchor_stress_guard --variants no_patv,lagged_patv,no_pab_mean,lagged_pab_wspd --seeds 201,202,203 --min-nmi 0.65
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

- WTB forecasting tradeoff: Graph WaveNet lower RMSE versus boundary-forced router higher NMI/ARI.
- Ablation table: unconstrained MoE, alignment, boundary force, and anchor-only/router controls.
- Anchor stress summary after the new three-step protocol.
- Anchor-stress early-warning label-degradation curve if page budget allows; otherwise cite it in supplementary evidence.
- External wind deployment-gate table with Kelmarsh/Penmanshiel failure metrics.
- Compact reserve-risk vignette showing same-model gate-bin value and physical-bin lower-cost bound.

## Acceptance Checklist

- The abstract leads with SCADA-anchored routing audit, not reserve procurement.
- The contribution statement says `auditability`, `responsibility assignment`, and `control-boundary diagnosis`.
- The limitations explicitly say the method is not anchor-free physical discovery.
- The final package provenance lists `anchor-stress-cache / anchor-stress-train / anchor-stress-guard / anchor-stress-early-warning`.
- All code changes are covered by targeted tests before manuscript conversion starts.

## Build And Submission Environment Notes

Two environment conditions can break `scripts/prepare_tste_submission.ps1` even when the manuscript itself is correct. Check both before a fresh build on a new machine or after cleaning disk space.

### 1. `rg` (ripgrep) must be on PATH

The submission script scans the XeLaTeX logs for blocking warnings with `rg`. If `rg` is not on PATH, the call fails as a missing command and `$LASTEXITCODE` carries over the `0` from the preceding `pdfinfo`, so the script throws a false `LaTeX log contains blocking warnings/errors` even when the logs are clean.

Put a `rg.exe` on PATH before running the build, for example:

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

These two arrays are an exact function of the windowed cache (`target` window = `cache_target[t+1 : t+1+P]` from the still-present `anchor_index`). Restore them losslessly before rebuilding:

```powershell
python scripts/restore_run_targets.py            # runs referenced by the reviewer stat-pack run table
python scripts/restore_run_targets.py --scan     # every run dir under artifacts/ missing the arrays
python scripts/restore_run_targets.py --dry-run  # report only, write nothing
```

The utility refuses to write unless the reconstruction reproduces each run's stored `overall.rmse`, so it cannot corrupt evidence. The restored arrays are git-ignored and can be deleted again to reclaim space, then regenerated on demand.
