Dear Editor-in-Chief,

We are pleased to submit our manuscript, **"SCADA-Anchored Regime-Aware Routing for Auditable Wind-Turbine Control-Boundary Forecasting,"** for consideration as a Regular Paper in *IEEE Transactions on Sustainable Energy*.

**What the paper does.**
The manuscript targets a specific wind-farm operating failure mode: near the MPPT-to-pitch transition, the threshold label that identifies the active control law may be delayed, incomplete, or noisy exactly when reserve screening needs an operating-state signal. We introduce a SCADA-anchored routing framework that makes this control-boundary assignment auditable. A node-level mixture-of-experts gate is constrained by operating anchors so that each turbine-time routing assignment can be compared against a declared MPPT-to-pitch partition and then used as an issue-time diagnostic when the corresponding threshold-label stream degrades. The contribution is an accountability layer that reports which operating state generated a local forecast, quantifies the degraded-label value of that assignment, prices the resulting RMSE cost, and states the deployment checks required before cross-farm use.

**Why it fits TSTE.**
The paper is written for a sustainable-energy audience because the technical question is tied to wind-farm operation: can a forecaster expose the control-boundary state that concentrates reserve risk, even when the lowest-RMSE backbone does not provide an auditable operating-state assignment? On the KDD Cup 2022 WTB benchmark, the boundary-forced router recovers the declared MPPT-to-pitch partition (NMI about 0.87, ARI about 0.92) while paying a measured 11.79-RMSE accuracy price: RMSE 236.13 versus 224.34 for iTransformer, the lowest-RMSE strict-cache forecasting baseline. Under a six-step label delay, however, the gate retains 0.960 early pitch-window recall while the delayed threshold rule falls to 0.196; with only 50% label availability, the gate remains at 0.960 versus 0.508 for the available-label rule. This degraded-label reserve-screening value is the primary contribution we ask reviewers to assess.

**Evidence package and claim controls.**
The submission package deliberately separates supported operating-boundary claims from stronger claims the evidence does not support. Supplementary Table A6 records the statistical claim boundary; Table A7 reports an outcome-channel sanity audit for the shared-anchor concern; Table A8 turns the Kelmarsh/Penmanshiel external-site failures into deployment gates; Table A9 converts label-degradation recall into detected and missed turbine-time cells; Table A10 records the reserve-policy claim boundary; and Supplementary Table A11 translates the main reserve deltas into MWh-equivalent forecast-cell accounting and scenario EUR values. The IEEE main paper remains 10 pages, and the supplementary material contains these reviewer-facing audit tables rather than using the main text to over-argue them.

**Honest boundaries we foreground.**
We explicitly state the following boundaries so that reviewers can evaluate the manuscript on its intended contribution.

1. **Not SOTA forecasting.** iTransformer, Graph WaveNet, and other strong baselines remain better whole-sample forecasters. The router is used when an operator needs an accountable operating-state assignment, not when the sole target is minimum average error.
2. **Not universal reserve-policy superiority.** Gate-conditioned binning improves a same-model boundary-window global reserve rule at moderate cost ratios, but physical-bin quantile policies are competitive and can be lower-cost. Supplementary Tables A10-A11 record the claim boundary and the bounded MWh-equivalent/EUR scenario translation.
3. **Not automatic cross-farm generalization.** Kelmarsh/Penmanshiel testing does not pass the held-out routing criterion. The manuscript reports this as a deployment protocol requiring sensor coverage, pitch or proxy observability, local boundary re-estimation, and a held-out routing pass before reserve use.
4. **Not anchor-free physical discovery.** The label-degradation audit shows operational value when an already defined threshold-label stream degrades; it is not an unsupervised discovery claim. The anchor-stress and outcome-channel audits support partial anchor robustness, not anchor-free regime recovery.
5. **Not market or security-constrained dispatch.** The reserve audit uses validation-frozen shortfall quantiles and rolling forecast-cell MWh-equivalent accounting. The EUR values are scenario translations under declared reserve-carrying prices; they exclude optimal power flow, unit commitment, market clearing, delivery constraints, and settlement-price claims.

**Reproducibility.**
All code, configuration files, releasable derived tables, figure data, and model checkpoints will be made available with the article. The reproduction package includes the WTB routing analysis, reserve audit, anchor-stress cache/train/guard protocol, early-warning label-degradation audit, external boundary diagnostics, supplementary claim-boundary table generation, and an evidence-freeze guard. The current IEEE manuscript and supplementary PDF compile cleanly, with the main paper at 10 pages.

We confirm that this manuscript has not been published previously and is not under consideration elsewhere. We thank the reviewers in advance for their time and constructive feedback.

Sincerely,
Junyu Li and Juntao Du
