# Raw-data replay and audit repair protocol — 2026-10-15

Status: REGISTERED BEFORE REPLAY; no replay result is known at registration.
This is a reproducibility/correction campaign, not a new positive discovery trial.
The scientific contract, primary baseline and decision thresholds are unchanged.

## Frozen scope and acceptance

Reconcile every entry in artifacts/ARTIFACT_MANIFEST.json and the current main/supplementary manuscript with a source run. Families: WTB raw preprocessing and strict masks/train-only weights; original forecast and regime-supervision variants (five seeds 201–205); dense/routed controls; frozen residual generation; channel probes; strong conditional-quantile comparison; matched-budget/rho sensitivity; EXP01 external transfer; EXP02 no-privileged supervision; EXP03 asynchronous arrival; calibration/observability diagnostics and manuscript figures/tables. External raw sites: Kelmarsh, Penmanshiel and La Haute Borne. Ancillary evidence whose raw reconstruction is unavailable must be marked unresolved/withdrawn, not omitted from coverage.

Historical outputs are immutable. New outputs live under artifacts/raw_replay_20261015. Never silently redirect a missing input to an old cache/checkpoint. Each executed command records argv, UTC start/end, exit, code revision/hash, input and output hashes, environment, seed/config, stdout/stderr. All neural runs require weights, per-epoch losses and predictions; decisions require target/mask/population and paired day-block arrays. Failed runs remain archived. A saved CSV/hash is not evidence of raw-data retraining.

Full replay acceptance requires every scoped artifact to be regenerated or explicitly withdrawn with a reason. Comparison reports distinguish exact data/mask matches, deterministic re-evaluation, and stochastic retraining variation. Neither a favorable sign nor matching an old number is an acceptance criterion. No post-result tolerance fitting. Data split/label arrays must be exactly equal when replaying the same preprocessing protocol; if not, stop that branch and diagnose. Statistical results must be recomputable from archived predictions/blocks. Cross-device bitwise neural training equality is not asserted.

## Fixed scientific specification

- Primary reserve baseline: site-local 10-bin wind-speed conditional 0.90 quantile; frozen forecast and shortfall s=max(yhat_fixed-y,0) shared by all policies.
- Primary h=6, secondary h=1; rho=10, dt=1/6 hour. Existing rho sensitivity grid, seeds, chronological splits, masks and bootstrap definitions retained per registered family.
- WTB: 134 turbines, 245 days, 180/30/35 chronological split, H=36, P=24; train-only normalization/class weighting, strict anchor-validity masks. Historical privileged training disclosed separately from pitch-withheld deployment.
- Historical model configurations are copied as data from checkpoint model_config/train_config BEFORE training (weights are not reused). No architecture/hyperparameter tuning to reproduce favorable outcomes.
- Full/steady/transition results retained; transition windows remain ex-post diagnostic. NMI/ARI/Brier/recall do not establish decision superiority.
- EXP01 v4 is retrospective; v2 preserved as superseded history. No graph causality from unmatched No-Graph controls.
- EXP02 epsilon=50 primary; 20/100 sensitivity; registered verdict threshold unchanged. Native seed/day blocks must be saved.
- EXP03 synthetic only; full arrival/missing/stale provenance must be replayable. No unarrived packet may initialize a causal state. Missing initial observation is represented by a predetermined constant (standardized zero), shared by methods, until a packet arrives; no future backfill.

## Newly identified protocol defects and version separation

CH-HORIZON: run_channel_consequence_ablations.py enumerates [h1,h6] but indexes residuals by enumerate index [0,1] rather than horizon [0,5]. The archived h6 channel decision values are withdrawn from confirmatory use. New version uses actual horizon indices and exact anchor alignment assertions. Representation outputs are separately scoped; no inference about the full STGNN follows from an MLP probe.

CH-REFERENCE: hardcoded historical direct-cost references are not matched baselines. New version calculates the wind-bin comparator from identical residual arrays/masks; uses Delta=challenger-baseline and records per-seed outputs. Historical deltas remain archived, not relabeled.

ASYNC-INIT: simulator initializes LOCF with v[0] even if that packet is not yet available. Corrected version starts at fixed standardized zero until a causal packet arrives. All packet delays, selected source indices, missing/stale masks, and resulting features must be archived and checked; old asynchronous claims cannot inherit new provenance retroactively.

## Withdrawal policy

Unsupported hidden-state necessity, universal transfer, graph causality, field latency prevalence and blanket FULLY_REPRODUCIBLE certification are withdrawn now. Unexecuted replay is PENDING, not failed. Executed protocol/data failures are FAILED with raw logs; a numerical claim that cannot be reconstructed is withdrawn from current conclusions while its historical record remains accessible. Final independent scientific falsification is mandatory before any scientific completion statement.


## Additional correction registration (before training; v2 campaign)

CH-TRANSITION: invalid adjacent labels can create false transition edges. New recall
requires both adjacent labels valid, dilates only those edges, and scores valid positive
targets. Archive legacy and corrected recalls and denominators side by side. The historical
62.9% is withdrawn as a valid-transition recall claim pending corrected evaluation; NMI and
ARI have separate masks and must not inherit this invalidation without evidence.

ASYNC-REPLICATION: keep simulator seed 20261012+100*delay (one trace per delay shared
by five model seeds); do not claim five independent simulator replications. Tau-star is first
upper CI bound >=0 (loss of demonstrated advantage), not demonstrated inferiority. Per-model
RNGs are explicitly seeded; this is a new corrected run, not recovery of an unknown old RNG state.

A withdrawn claim is a completed claim disposition, never a successfully reproduced
experiment. Keep NOT_RUN/FAILED/BLOCKED separate from WITHDRAWN.

The initial freeze/raw-only probe directory is retained as artifacts/raw_replay_20261015.
No model was trained there. Corrected registered execution uses artifacts/raw_replay_20261015_v2.
Raw-only probe showed exact targets, masks, labels, coordinates, graph and time indices, but
small floating-point feature/normalization discrepancies from the historical cache. These
are recorded as non-exact, without retrofitting an acceptance tolerance. New raw-derived
training is evaluated as a current-code rerun; it cannot certify bitwise historical replay.
