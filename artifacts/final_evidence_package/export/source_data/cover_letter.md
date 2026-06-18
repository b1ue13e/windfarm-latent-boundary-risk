Dear Editors,

We submit the manuscript "Boundary-Aware Routing for Wind-Power Operating Transitions with an ERA5 Observability Contrast" for consideration in Applied Energy.

This manuscript is not positioned as a state-of-the-art point predictor. In the completed WTB strict-cache evidence, Graph WaveNet and lag-feature engineering baselines achieve lower RMSE than the boundary-forced routed model. We state this directly in the abstract, results, conclusion, and claim-boundary table. The contribution is instead a boundary-aware operational routing method: it makes the MoE gate physically accountable near wind-turbine MPPT-to-pitch transitions, measures the forecasting cost of that accountability, and reports when the gate changes reserve shortage, violation rate, and reserve energy in operating windows where dispatch risk is concentrated.

The paper is written for an energy-systems audience rather than as a pure machine-learning benchmark. We include Graph WaveNet reserve baselines, cost-ratio sensitivity, MPPT-to-pitch and ramp-based operational slices, and concrete failure cases showing when a correct gate is useful and when it can mislead downstream reserve decisions. The main reserve result is deliberately conditional: gate-bin reserve improves boundary-window shortage and violation at selected cost ratios, but it is not a universal reserve policy.

We also report the external Kelmarsh/Penmanshiel experiments as a failed transfer and boundary-condition diagnostic, not as an external validation success. The completed 80-run external guard falls below the pre-specified site-transfer criterion, and local rated-wind/pitch recalibration recovers only limited test agreement. The manuscript therefore uses the external farms to explain why site-specific sensor fields, pitch observability, turbine geometry, and regime-share shifts require local boundary re-estimation before claiming operating-regime accountability.

We believe the manuscript fits Applied Energy because it focuses on wind-farm operating boundaries, reserve-capacity risk, shortage exposure, and explainable responsibility assignment under turbine-control transitions. The work asks when physical routing accountability is worth its measured cost, and it reports both the positive evidence and the failure boundaries needed for operational use.

The manuscript has not been published or submitted elsewhere. All authors have approved the submission. The study uses public turbine and atmospheric data and involves no human-subject data.

Sincerely,

Junyu Li and Juntao Du
