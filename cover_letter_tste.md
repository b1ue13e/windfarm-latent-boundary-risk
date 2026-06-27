Dear Editor-in-Chief,

We are pleased to submit our manuscript, **"SCADA-Anchored Regime-Aware Routing for Auditable Wind-Turbine Control-Boundary Forecasting,"** for consideration as a Regular Paper in *IEEE Transactions on Sustainable Energy*.

**What the paper does.**
The manuscript introduces a framework that makes the wind-turbine MPPT-to-pitch control boundary auditable through SCADA-anchored, regime-aware routing. A node-level mixture-of-experts gate is constrained by SCADA operating anchors so that each sample's routing assignment can be compared against a declared MPPT-to-pitch partition and then used when threshold labels are delayed, incomplete, or noisy. The contribution is not a better forecasting model; it is a framework that exposes which operating state generated each local forecast, quantifies the value of that assignment under degraded label streams, reports the measured RMSE price of accountability, and states explicit deployment conditions for cross-farm use.

**Why it fits TSTE.**
We deliberately submit to *Transactions on Sustainable Energy* rather than to operational-energy journals because our evidence profile is method- and accountability-oriented rather than performance-dominant. The boundary-forced router recovers the declared WTB partition (NMI ≈ 0.87, ARI ≈ 0.92) but pays a measured accuracy cost: overall RMSE 236.13 versus 225.74 for Graph WaveNet. Its operational value appears under label degradation: with a six-step label delay, the gate retains 0.960 early pitch-window recall while the delayed threshold rule falls to 0.196; with only 50% label availability, the gate remains at 0.960 versus 0.508 for the available-label rule. The same gate exposes reserve risk in the transition window, but validation-frozen quantile baselines show that physical-bin policies remain competitive. Kelmarsh/Penmanshiel external tests do not claim automatic generalization; instead they define a deployment protocol—sensor coverage, pitch observability, local boundary re-estimation, and held-out routing checks—that must be satisfied before cross-farm use. TSTE's scope includes forecasting methods, data-driven diagnostics, and operational integration, and our evidence profile aligns with the journal's acceptance of method contribution and interpretability as primary values.

**Honest boundaries we foreground.**
We explicitly state the following boundaries in this cover letter so that reviewers can assess the manuscript on its intended contribution rather than on conventional accuracy metrics:

1. **Not SOTA forecasting.** Graph WaveNet and stronger baselines remain better whole-sample forecasters. The router is used when an operator needs an accountable operating-state assignment, not when the sole target is minimum average error.
2. **Not universal reserve-policy superiority.** Gate-conditioned binning improves same-model boundary-window tradeoffs at a measured reserve-energy cost, but physical-bin quantile policies are competitive. The reserve section is framed as a boundary-risk vignette, not a claim of dispatch optimality.
3. **Not automatic cross-farm generalization.** Kelmarsh/Penmanshiel testing defines explicit deployment conditions rather than promising automatic generalization. Cross-farm use requires local boundary re-estimation and held-out routing verification.
4. **Not anchor-free physical discovery.** The label-degradation audit shows operational value when a threshold stream is delayed, incomplete, or noisy; it is not an unsupervised discovery claim. The five-seed anchor-stress evidence shows that the gate depends on the specific SCADA channel combination present at issue time. The claim is "partial anchor robustness," not "the model discovers the physical boundary without anchors."

**Reproducibility.**
All code, configuration files, releasable derived tables, and model checkpoints are available with the article. The anchor-stress cache derivation, 20 strict-cache training runs (4 variants × 5 seeds), leakage guard, and early-warning label-degradation audit form a mandatory reproducibility protocol. A reproduction package script generates the full pipeline end-to-end.

We confirm that this manuscript has not been published previously and is not under consideration elsewhere. We thank the reviewers in advance for their time and constructive feedback.

Sincerely,
[Author Names]
