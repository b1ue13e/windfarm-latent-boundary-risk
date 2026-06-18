# Science readiness dashboard

Generated at: `2026-06-18T19:16:03`
Overall status: `within_wtb_submission_ready_external_nonportable`

Refresh command:

```powershell
artifacts\science_readiness_dashboard_20260611\refresh_readiness.ps1
```

## Items

- fatal | complete | Strict-cache strong baselines: Graph WaveNet, Graph Transformer, GAT-GRU, PatchTST (20/20 complete)
  Next: Wait for remaining GAT-GRU/PatchTST runs and rerun strict-baseline-guard.
- fatal | complete | WTB east-cluster spatial turbine-group holdout (15/15 complete)
  Next: Execute spatial holdout training, mechanism gate, and reviewer-stat pack.
- high-priority | complete | Pre-specified future-period holdout (5/5 complete)
  Next: Execute queued future holdout runs and holdout audits.
- high-priority | complete | Strict-cache full ablation including simple routing controls (50/50 complete)
  Next: Run strict ablation suite and mechanism-gate routing controls.
- high-priority | complete | Strict-cache wrong-threshold mechanism negative controls (20/20 complete)
  Next: Run strict threshold-control sensitivity suite and reviewer-stat pack.
- strengthening | available | Reviewer statistics pack: per-example rows, paired tests, efficiency, failure cases
  Next: Regenerate final combined reviewer-stat pack after all strict baselines and ablations finish.
- fatal | complete_but_within_wtb_only | External Kelmarsh/Penmanshiel portability guard (80/80 complete)
  Next: Keep the manuscript at WTB-only mechanism evidence; do not cite cross-farm portability.
- high-priority | complete | External wind source-data guard (31/31 complete)
  Next: Keep Kelmarsh/Penmanshiel source files, checksums, and CC-BY-4.0 manifest in the release bundle.
- high-priority | diagnostic_only | Kelmarsh/Penmanshiel site-specific small-calibration adaptation (40/40 complete)
  Next: Report as a site-specific adaptation diagnostic; do not claim usable external routing unless the guard allows it.
- fatal | within_wtb_ready | Final evidence manifest claim gate
  Next: Submission tables are ready for the downgraded WTB-only claim; external portability remains uncited.
- strengthening | available | Reproducibility and compliance manifest (53/53 complete)
  Next: Keep the manifest refreshed after each guard or evidence-package update.
- strengthening | pass | ERA5 claim narrowed away from forecasting advantage
  Next: Keep ERA5 framed as visible-regime routing calibration, not prediction superiority.
