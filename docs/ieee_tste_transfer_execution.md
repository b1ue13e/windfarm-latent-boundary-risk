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

Decision rule:

- `complete_anchor_stress_supports_partial_anchor_robustness`: cite partial anchor robustness.
- `complete_anchor_stress_requires_claim_downgrade`: keep declared-anchor-constrained routing language.
- `ready_to_execute_anchor_stress_training`: do not cite training-level anchor robustness.
- `blocked_anchor_stress_leakage_guard_failed`: do not submit until the leakage issue is resolved.

## Minimum Evidence Tables

The TSTE paper should retain only these table-level claims in the main text:

- WTB forecasting tradeoff: Graph WaveNet lower RMSE versus boundary-forced router higher NMI/ARI.
- Ablation table: unconstrained MoE, alignment, boundary force, and anchor-only/router controls.
- Anchor stress summary after the new three-step protocol.
- External wind deployment-gate table with Kelmarsh/Penmanshiel failure metrics.
- Compact reserve-risk vignette showing same-model gate-bin value and physical-bin lower-cost bound.

## Acceptance Checklist

- The abstract leads with SCADA-anchored routing audit, not reserve procurement.
- The contribution statement says `auditability`, `responsibility assignment`, and `control-boundary diagnosis`.
- The limitations explicitly say the method is not anchor-free physical discovery.
- The final package provenance lists `anchor-stress-cache / anchor-stress-train / anchor-stress-guard`.
- All code changes are covered by targeted tests before manuscript conversion starts.
