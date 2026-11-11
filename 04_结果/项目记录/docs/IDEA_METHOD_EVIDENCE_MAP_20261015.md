# Idea — implemented method — evidence map (2026-10-15)

This is a mapping of actual implementation, not certification that all rows have
finished raw replay. Execution statuses remain in the campaign receipts and coverage.

| Question | Actual implementation | Evidence / reproducibility obligation |
|---|---|---|
| Does state posterior improve reserve decisions over wind bins? | Dense-classifier mode, SpatioTemporalEncoder (directed diffusion + GRU),87,067 nominal parameters; posterior5-bin vs wind10-bin0.90 quantiles | test_strong_baseline_closure.py; same fixed residual NPZ, target/mask/anchors; native day blocks and all slices |
| Are consequence channels informative? | Separate binary ConsequenceMLP, not full-STGNN module deletion; latest/mean/std/max features | run_channel_consequence_ablations.py; per-group/seed weights, training losses, probabilities, labels and both legacy/valid transition denominators |
| Does privileged label supervision matter? | modes moe_balance_only / moe_balance_align on identical110,012-parameter backbone; effective loss weights depend on mode, not merely stored config values | clean supervision ablation; training inputs still privileged in both variants; do not equate removal of alignment with removal of historical pitch |
| Is routing necessary for decisions? | MoE backbone110,012 vs unrouted dense115,240 parameters; explicit shared-reference quantile heads in corrected phase scan | Legacy mixed-target cost interpretation withdrawn. Corrected frozen targets/populations/head training data archived; approximately matched capacity only |
| Does a representation transfer across farms? | WTB MoE mode moe_full_no_aux; locally frozen point predictor rebuilt on each corrected raw window; wind10-bin and posterior5-bin comparison | repair_exp01_pitch_withheld_v3.py now checks target/mask/time/node identity. Historical v4 is INVALID; raw replacement pending |
| Can zero-privileged inputs support reserve decisions? | Separate weak-supervised MLP with pinball head and auxiliary physical proxy; epsilon50 primary20/100 secondary | EXP02 corrected physical units, per-model snapshots, all reserve arrays and paired day blocks. Oracle is unfair reference only; explicit gate-array hashes and alignment |
| What happens under asynchronous arrivals? | Explicit causal event/arrival simulation with shared trace per delay, fixed initial standardized zero and LOCF | EXP03 full grid archive, selected source indices, masks, models and decisions. One simulator realization per delay, five model seeds; no claim of five simulator replications |
| Does lower violation reflect better allocation? | Exact/validation-calibrated matched-budget fronts and rho sensitivity | Same frozen targets, paired day-block uncertainty; distinguish raw-sample and bootstrap means; preserve every budget/seed |

Runtime construction from the frozen model configurations confirms the six WTB
families use SpatioTemporalEncoder. Graph WaveNet is a separate benchmark option,
not the encoder class of the principal MoE runs. Counts are nominal instantiated
parameters, not a claim that every module receives gradients in every mode.
Source: artifacts/raw_replay_20261015_v2/architecture_config_audit.json and
windfarm_moe/model.py / config.py.

The original method story is not one monolithic network. The manuscript must name
which model/policy generated each experiment, give the input/supervision lifecycle,
and avoid inferring architecture necessity from representation metrics or invalid
cost comparisons. Source archives, failed attempts and withdrawn claims are retained.
