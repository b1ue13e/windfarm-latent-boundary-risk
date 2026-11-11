# RAW-FACTORIAL-FOUR-CONDITIONS-V2

Registered before execution. All results NOT_RUN at registration. This repairs
coverage and information alignment, with no favorable-result acceptance criterion.

The four original conditions are clean (delay0, all channels); delay6 (all channels,
stalled history); pitch_withheld (delay0, both pitch features/masks and anchor pitch
zeroed); and delay6_pitch_withheld (both operations). Five model seeds201–205 each,
h6 primary/h1 secondary, same canonical scheduled forecast/shortfall/mask/time/node,
rho10, dt1/6h and validation quantile0.90. No simulator seed is introduced: fixed
delay6 is deterministic. This is not the asynchronous packet experiment.

The common full population is the canonical target-valid test set. Boundary is a
fixed ex-post diagnostic |raw issue-time wind−10.5|<=1m/s, not a deployable selector.
It never changes with degradation. K uses ten fixed physical wind bins from0..25
with infinite endpoints, >20 calibration cells or global fallback, identical to
the already registered comparator. Its wind comes from exactly the model's degraded
anchor_physics batch and is inverted with that channel's training-only scaler.
Fresh physical wind may define the diagnostic slice, never delayed-arm decisions.
All families must produce identical observed wind/source anchors. K is wind-only;
in clean/fresh-pitch arms it is not claimed to exploit all available pitch information
or be the strongest physical comparator. No scientific-superiority claim is licensed
by this diagnostic without the separately registered matched strong-baseline evidence.

A/B use the same unaligned/aligned architecture and effective losses except
alignment0 vs5000; optimizer/schedule/seed/config fields must match apart from
mode/label and inactive loss weights. Both retain historical pitch in training.
Auxiliary heads retain five epochs, Adam0.01, batch2048, up to20000 validation cells,
same selected anchors and initialization/SGD seed in A/B. Save weights, losses and
selected indices. Other variants retain C posterior bins, D global, E both-split
shuffled-label oracle diagnostic, F both-split randomized posterior, G oracle
diagnostic, H0.95C+0.05global, I dense classifier posterior, J alias C, K wind bins.
Unknown oracle states use global reserve, never silent zero. E/G are non-deployable;
J is not an independent control. Keep the existing reserve clipping1.5×max valid
validation shortfall for heads; do not tune any limit after seeing outcomes.

Archive checkpoint/config/input hashes, actual source and environment/PBS identity,
all latent/gate/arrived-wind arrays, deterministic history/anchor source indices,
per-condition/per-seed reserve vectors, targets/masks/anchors/node identity and paired
day-block costs/reserves/shortages/cell counts relative to K. Use raw issue-time day
IDs for all methods. Summaries require all5 seeds, use descriptive mean/SD only,
and do not invent significance tests or turn representation into decision value.

Execute in a separately hashed Metis extension outside scripts/windfarm_moe, after
actual WTB core completion. Never edit the running frozen tree or overwrite any
earlier output. The existing masked-only factorial run remains a separate version.
Any missing checkpoint, mismatched time/node/target, unmatched observed inputs,
failed withholding/stalling, nonfinite reserve or missing receipt stops that run.
Preserve every sign/null/failure, fix implementation defects in new attempts, and
keep overall coverage incomplete until all required experiment families and final
paper/independent scientific/evidence gates have actually been checked.

Pre-execution fail-closed requirements: physical wind scaler must explicitly contain finite mean and positive finite std; missing metadata cannot imply identity scaling. Verify the successful fixed_residuals execution receipt/output SHA and exact s=max(yhat−y,0)×mask formula. The separate aggregate receipt requires all20 actual successful runs, exact44 cells per seed and matching canonical populations across all conditions; report only after these checks, never from partial rows.
