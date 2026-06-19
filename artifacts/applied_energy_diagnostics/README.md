# Applied Energy diagnostics

This package is generated from saved strict-cache artifacts and does not retrain models.

## Main outputs

- `dispatch_reserve_main_table.csv` and `table_dispatch_reserve_main.tex`: same-table dispatch/reserve comparison at cost ratio 10.
- `operational_decision_curve.png`: RMSE penalty, reserve energy, and shortage tradeoff on the boundary window.
- `reserve_paired_statistics.csv`: paired bootstrap/permutation-style uncertainty summaries for reserve cost and risk metrics.
- `anchor_only_rule_router_main_table.csv`: formal anchor-only/router-rule comparison.
- `external_negative_evidence_table.csv`: external Kelmarsh/Penmanshiel negative evidence and allowed claims.
- `new_wind_farm_deployment_checklist.png`: deployment gate from sensor coverage to allowed/forbidden claims.

## Claim summary

Gate-bin reserve is a conditional transition-window diagnostic. It wins when moderate shortage penalties make boundary shortage and violations worth extra reserve; it loses when high-ramp or very high-penalty settings make the same-model global policy safer.
