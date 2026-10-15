# Additional pre-execution corrections — 2026-10-15

This addendum registers newly discovered defects before the affected experiment is
replayed. It does not change outcome thresholds, primary comparators, seed counts,
epsilon values or significance gates. WTB forecast training is already running;
the changes below affect later EXP02 and external stages, not that forecast fit.

## EXP02 physical proxy and diagnostic integrity

Historical code loaded physics_model.npy but inverted power using Patv_hist feature
statistics. The physical power channel has different scaler statistics. Direct checks
found 189 validation and 24 test proxy labels differ at epsilon=50 (historical cache).
Corrected replay reads Wspd and Patv directly from physics.npy, retaining thresholds
10.5 m/s and 1500-epsilon kW, epsilon50 primary and20/100 secondary. The historical
correct-physical-protocol interpretation is withdrawn; old numbers remain archived.
Held-out transition diagnostics now require adjacent valid labels; report generators
must not hardcode result direction, instability or a particular seed explanation.

## External raw-window correction

The legacy rebuild_obs_windows.py slices all arrays (including static coords),
computes feature statistics from already standardized features, and writes new
physics-model statistics without re-transforming physics_model. It cannot certify
the stated raw-window/train-only normalization method. Corrected raw replay selects
the historically fixed windows before fitting preprocessing: Kelmarsh offset120 days,
Penmanshiel offset720 days, La Haute Borne offset0; window245 days; split180/30/35.
No outcome-dependent window search is performed. Real coordinate coverage and expected
node counts 6/14/4 are hard checks, not replaced with fabricated topology. All original
data files and their hashes are recorded before execution. New caches and retrained
models are a corrected protocol version; exact legacy equivalence is not asserted.
Any conflicting legacy result remains unverified/withdrawn for current interpretation
until the relevant source chain is independently reconstructed.

## Execution-chain transparency

WTB first training launched before the deeper cache_manifest link was implemented.
Array hashes were already recorded in preprocessing_comparison.json; a subsequent
explicit check confirmed no changes and wrote cache_manifest_late_link_notice.json.
Do not describe the new linking receipt as having existed at first launch. Later
training children record complete cache hashes before model fitting. Withdrawn,
FAILED, NOT_RUN and successfully reproduced are distinct coverage states.

## External coordinate integrity correction (before Kelmarsh/Penmanshiel replay)

The legacy reader could silently replace missing/unmatched node coordinates with a
500m regular synthetic layout. Kelmarsh raw node IDs T01..T06 and static aliases KWF1..KWF6
require explicit bijective normalization; the static Title and Alternative Title columns
identify these same numbered turbines. Corrected code resolves those aliases, rejects
missing schemas/unmatched nodes and never fills invented coordinates. Historical graph
interpretations cannot be certified from the synthetic fallback. Real raw coordinates,
label thresholds and fixed windows are frozen; this is not a model-performance threshold.

## Engineered physical feature correction (before EXP02/03 replay)

EXP02 and EXP03 previously divided standardized power by1500 and described it as
physical rated-power ratio. Corrected EXP02 constructs wind, power, wind squared and
clipped power/1500 from physical physics.npy channels before its training-only scaler.
Corrected EXP03 retains standardized base SCADA features but constructs wind squared/100
and clipped power/1500 after explicitly inverting the appropriate feature scaler.
The model architectures, loss weights, primary epsilon and decision thresholds do not
change; this is an explicitly versioned feature-definition correction before execution.
Oracle gate arrays are now hashed and checked against the frozen anchors, targets and masks.

EXP01 v4 is INVALID, not current authoritative evidence: see EXP01_INVALIDATION_20261015.md.
No valid external direction or confidence interval is inferred from a wrong-window result.

## RAW-PHASE-FROZEN-V1 (registered before phase replay)

The old phase scan compared model-specific shortfalls and selected boundary cells using
arrived/degraded wind. Its cross-model fixed-target and cross-delay fixed-population
interpretations are withdrawn. New version fixes canonical shortfall arrays for every
model/condition, checks anchor identity, and freezes the diagnostic boundary population
to valid target cells with |physical issue-time wind-10.5|<=1 m/s in each split/horizon.
Primary comparator is the existing ten fixed wind bins (0..25 m/s with infinite endpoints),
validation 0.90 shortfall quantiles, >20 observations per bin or global fallback. Primary
h=6; h=1/3 secondary; delays0/1/2/3/6 and all/no_pitch conditions unchanged. This remains
an ex-post boundary diagnostic, not a deployable oracle selector.

Both frozen quantile heads learn the same clean reference forecaster's shortfall and
valid-target mask, with matched shuffled window indices. Retain five head epochs and
150 cached training batches (64 windows each) from the original procedure; disclose this
sample budget rather than claiming every training window was used for the auxiliary head.
Save weights, losses, training anchors, frozen targets/populations and all per-condition
reserve predictions. Chance target10%, rho10, per-seed201–205 and all negative/null results
remain unchanged. Legacy artifacts remain archived; new values are not substituted into
old tables before independent verification.

Clean physical calibration in the corrected phase scan is keyed by both horizon and
channel mode. Pitch-withheld wind conditioning must not reuse pitch-angle bin edges.
At zero delay the same-channel clean/recalibrated reserves must coincide exactly;
a hard assertion enforces this. This is a units/conditioning repair, not threshold tuning.

## Gate strengthening (result-neutral)

A new required verify_raw_replay check prevents cached-artifact PASS from certifying
raw-data replay. It checks the unchanged minimum experiment scope, actual execution
receipts and file hashes, recorded failures/withdrawals, and a final independent review
bound to the current coverage manifest. This adds evidence requirements; it changes no
scientific baseline, seed, effect/significance threshold or decision rule. It currently
returns FAIL, as expected while work remains unfinished.

## RAW-SUPERVISION-MASKED-V1 (before corrected evaluation)

Ordinary training gate caches do not prove pitch-withheld evaluation. Corrected
supervision ablation explicitly runs both checkpoints under double pitch-feature
withholding, rejects missing seeds/truncation, and verifies frozen targets/times/nodes.
Pairs must have identical model configs and identical effective loss weights except
alignment0 vs5000. Both retain historical pitch inputs in training. Report all five
paired seeds and actual seed-level Student-t statistics; zero-variance t tests remain
undefined, never replaced with invented p-values. Historical claimed-withholding results
are suspended until this fresh masked evaluation exists.

EXP02 zero-privilege refers to the conditional reserve learner. Its common scheduled
forecast is supplied by the separately trained fixed reference forecaster, which uses
historical privileged data. This does not demonstrate an entirely pitch-never-recorded
end-to-end forecasting system. This scope restriction changes no numerical gate.

## RAW-FACTORIAL-MASKED-V1 / RAW-ACTIVE-POWER-V2 / Metis execution

Before corrected execution, factorial A/B are constrained to identical backbone configs
and effective losses except alignment0 vs5000, both historically using pitch in training.
Both deployment pitch features/masks are withheld. Linear quantile heads retain five
epochs, Adam0.01, batch2048, up to20000 validation cells; save all indices/weights/losses.
Common canonical forecasts/targets/masks/anchors govern all arms. Randomized posterior
control permutes both validation and test scores; shuffled oracle permutes both splits.
Unknown oracle label3 uses global quantile fallback, not zero reserve. J is explicitly
the same array as C. Primary K wind baseline, fixed full/boundary populations and all
five seeds remain; summaries are descriptive, not fabricated significance evidence.

The currently implemented corrected factorial entry point evaluates pitch-withheld,
zero-delay deployment only. Its CSV is a versioned diagnostic and must not certify the
old four-condition factorial family. Clean, delay6 and delay6-plus-pitch-withheld
conditions remain NOT_RUN in the full replay scope until their corrected execution.
This records unfinished requirements, not a reduction of the user's full replay task.

Active-power audit now saves selected training indices, model/scaler/history, scores,
reserve vectors and masks. Original three-epoch /200000-cell budget is disclosed.
Its decision cohort requires valid regime labels and is not called full-population.
Transition edges require both endpoint labels valid. Remove hardcoded causal, numerical
direction and safe-thermal-omission prose; read directions from executed tables only.

User requires execution on Metis. Completed local artifacts and interrupted fits remain
immutable provenance; no local partial checkpoint substitutes for cloud from-scratch
fits. Cloud raw inputs must match frozen source hashes. New PBS stages retain all
registered model configs/seeds and fail closed on missing/hash-mismatched dependencies.
Actual host/Python/PyTorch/CUDA/GPU and pip environment are recorded. Cross-host bitwise
identity is not assumed or manufactured. Compare actual regenerated outputs and disclose
differences; do not tune thresholds or remove seeds to reproduce an old headline.
