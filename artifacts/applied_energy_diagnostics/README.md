# Applied Energy diagnostics

This package is generated from saved strict-mask artifacts and does not retrain models.

## Main outputs

- `dispatch_reserve_main_table.csv` and `table_dispatch_reserve_main.tex`: same-table dispatch/reserve comparison at cost ratio 10.
- `system_value_envelope.csv` and `table_system_value_envelope.tex`: boundary-window reserve value envelope across cost ratios.
- `operational_decision_curve.png`: RMSE penalty, reserve energy, and shortage tradeoff on the boundary window.
- `reserve_paired_statistics.csv`: paired bootstrap/permutation-style uncertainty summaries for reserve cost and risk metrics.
- `reserve_coverage_reliability.csv`: held-out coverage check for validation-selected reserve quantiles.
- `reserve_horizon_time_sensitivity.csv`: post-hoc horizon and time-of-day slices using frozen cell-level empirical quantiles.
- `reserve_horizon_quantile_whatif.csv`: horizon-specific empirical-quantile what-if without new probabilistic training.
- `cost_ratio_energy_system_assumptions.csv`: mapping from abstract shortage/reserve cost ratios to energy-system reliability assumptions.
- `anchor_only_rule_router_main_table.csv`: formal anchor-only/router-rule comparison.
- `external_negative_evidence_table.csv`: external Kelmarsh/Penmanshiel negative evidence and bounded claims.
- `quasi_external_deployment_drill_summary.csv`: WTB proxy deployment drill using calibration-only boundary/gate-map selection and held-out testing.
- `boundary_reserve_system_workflow.png`: SCADA to boundary router to reserve-policy audit workflow.
- `new_wind_farm_deployment_checklist.png`: deployment gate from sensor coverage to bounded operating claims.
- `graphical_abstract_applied_energy.png`: standalone Applied Energy graphical abstract (1800 x 840 px, 300 dpi).
- `../reserve_quantile_baseline/reserve_quantile_baseline.{csv,tex,json}`: validation-frozen global, physical-bin, and gate-bin quantile reserve baseline.
- `../reserve_toy_operational_cost/reserve_toy_operational_cost.{csv,tex,json}`: normalized reserve procurement plus shortage-penalty proxy.
- `../anchor_stress_guard/anchor_stress_guard.json`: training-level anchor-stress claim guard; incomplete runs require declared-anchor wording.

## Claim summary

Gate-bin reserve is a conditional transition-window diagnostic. It wins when moderate shortage penalties make boundary shortage and violations worth extra reserve; it loses when high-ramp or very high-penalty settings make the same-model global policy safer.

The quasi-external deployment drill is a WTB proxy workflow only: small calibration window, local boundary/gate-map freeze, and held-out future or held-out east-turbine testing. It does not rescue the negative Kelmarsh/Penmanshiel external-site adaptation result.
