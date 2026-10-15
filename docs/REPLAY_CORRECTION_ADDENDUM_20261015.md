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
