# Metis raw-data replay —2026-10-15

Status: PARTIAL / WTB RAW PREPARATION VERIFIED; GPU TRAINING QUEUED. First attempt failed and is preserved below. This document is an execution record, not a scientific certificate.
The full user requirement and all46 historical artifact rows remain in force. Coverage is
not satisfied by scheduler submission, software tests, or an interrupted fit.

## Execution and immutable inputs

- SSH alias: `metis`, configured key authentication; no embedded credentials.
- Cloud workspace: `/lstr/sahara/minlpml/junyu/paper3_raw_replay_20261015`.
- Interpreter: workspace `.venv/bin/python`, isolated venv using the existing grokking
  Python/PyTorch installation as its base. Exact installed packages are archived in
  `artifacts/metis_deployment_20261015_v3/environment.txt`; this is not a fully vendored runtime.
- Upstream source commit: `3c0e4e2`. Runtime subset commit on Metis:
  `3ec80337b95a32831ad32f4b217b63a9606fc3a5`. They intentionally differ; deployment.json
  maps the source revision and per-file hashes. No original Git HEAD is impersonated.
- Package: `artifacts/metis_deployment_20261015_v3/source.zip`, SHA256 `22fa91ea1da47e045108f46ce73cd9f692105a8850fae3a1c6cc8913ba71d14f`.
  Runtime entry points/tests/frozen protocols/configs and historical target identity arrays
  are included. Local trained weights, outputs and credentials are excluded.
- All36 raw source inputs have expected hashes originating in prior recorded raw-read
  receipts. Metis independently hashes actual bytes before relevant stages. The four
  original receipts are provided separately in `raw_hash_origin_receipts_attempt3.zip`;
  first/second companion attempts failed and remain preserved.
- Existing Metis WTB334304460-byte CSV and3310-byte location file independently matched
  SHA2566cf7613a82c61bb5cf9fcbbf22e3f6c48165fa32021eb6f1905cb2b7af4d7667 and
  15c19ceca43171dfda06e8de487d4d55eb116112904d77958aed7260c2f0d9fe respectively.
- External files are staged from authenticated local transfer or exact filenames/sizes
  on official Zenodo records16807551 (Kelmarsh) and16807304 (Penmanshiel), then checked
  against the frozen SHA256 values. Partial transfer files are retained separately.
  `metis_execution/external_raw_hash_verification.json` must exist with
  ALL_EXTERNAL_RAW_SHA256_PASS before any external PBS submission. Until then NOT_RUN.

## Local interruption and actual preflight outcomes

Five verified owned local replay processes were stopped after the user's Metis instruction.
Completed local fits remain intact; RUNNING receipts become INTERRUPTED_BY_USER_HOST_CHANGE,
not completed training or a negative scientific outcome. See
`artifacts/raw_replay_20261015_v2/METIS_MIGRATION_NOTICE.json`. Cloud fits restart from scratch,
with the same frozen configurations/seeds; no optimizer-resume or mixed-host pooled result.

v2 cloud preflight FAILED during pytest import with missing seaborn. requirements.txt
now declares seaborn (and scikit-learn). IMPORTANT preservation gap: the original pytest
failure file was overwritten by the v3 retry; its inspected error survives in tool/chat
output, not as a preserved byte-for-byte original log. `preflight_attempts.json` records
this gap. v2 source archive and deployment log remain. Do not claim every original
failure log is intact. Later attempts must use distinct files.

v3 independent source/WTB hashes, real snapshot Git HEAD, compileall, pip check and
79 software tests passed (`79 passed in87.10s`). Software fixtures are not scientific
experiments or new empirical results.

## Submitted PBS graph and reproduction commands

Actual WTB submission receipt: `artifacts/metis_deployment_20261015_v3/pbs_jobs_wtb.json`.
-242589.cm: wtb-prepare, CPU route rqdf→short,4CPUs64GB,30min; observed RUNNING on cn14.
-242590[].cm: wtb-fit, array0..29%1, qllm,1GPU4CPUs64GB,12h/subjob; dependency on prepare.
-242591.cm: wtb-core, dependency on the complete fit array.
-242592.cm: diagnostics, dependency on core.
At first post-submission check, all GPU jobs were HELD by their dependencies. No cloud
model fit or scientific result is claimed. Existing unrelated Metis jobs remain untouched.

For a fresh, verified workspace (do not resubmit into existing receipts):
```bash
ssh metis
cd /lstr/sahara/minlpml/junyu/paper3_raw_replay_20261015
.venv/bin/python metis_execution/submit_wtb.py
qstat -u junyu
```
The exact qsub argv for every stage is saved in the submission JSON. Array index selects
one frozen config; no hyperparameter, seed, primary comparator or numeric scientific gate
is changed for hardware migration. Stage runtime files record actual hostname/GPU/PBS ID.
Per-fit training logs, source snapshots, inputs, weights, predictions and output manifests
are produced under the cloud artifacts roots, not manufactured from the local partial fits.

`submit_external_when_ready.py` is a one-shot stage dispatcher that waits at most6h for
actual raw hash verification, then submits external-prepare,15 fits and matched transfer
with afterok dependencies on external and WTB fit arrays. Until submission JSON exists,
these tasks are only pending staging. This process does not certify any experimental result.

## Remaining scope

The currently implemented corrected factorial covers zero-delay pitch-withheld inference.
The other three historical conditions remain NOT_RUN and must be implemented/executed
under matched arrival information before the factorial family can be called reproduced.
Every other pending row in coverage.json, complete raw training/evaluation, claim reconciliation,
final PDF rebuild and independent raw-to-manuscript review remain required. The overall
verification gate currently FAILS for open tasks and the incomplete raw replay gate.
Never weaken those gates or infer scientific PASS from this deployment.

## PBS preparation attempt1 failure and explicit retry

Supersedes earlier first-submission R/H snapshot as current status. Job242589.cm
finished exit1: compute node could not execute git, before raw preprocessing was
launched. PBS canceled afterok dependents242590/242591/242592; no model fit is
attributed to them. Original stdout and qstat history are retained as
wtb_prepare_attempt1_stdout.txt and pbs_prepare_attempt1_history.txt. Failed frozen
output root remains intact at artifacts/raw_replay_20261015_failed_prepare_attempt1.
No fitted weights or empirical outputs were overwritten.

The actual Metis login host git2.43.7 binary is provided at shared
metis_execution/bin/git, SHA2564712661e824361c85d1c8f9dc231d45a79f853b393745a86b7ded95937bcbd38.
Dependencies are recorded; qsub explicitly exports that directory in PATH.
This repairs a runtime dependency, not a scientific threshold or protocol change.
Fresh retry graph: prepare242593.cm → array242594[].cm → core242595.cm
→ diagnostics242596.cm. Current pbs_jobs_wtb.json is the retry receipt; original
is preserved as pbs_jobs_wtb_attempt1.json. Submission is not execution.
Use submit_wtb_retry1.py in a fresh workspace after validating this runtime;
never rerun either helper over an existing submission receipt.
External staging dispatcher was restarted with the same explicit PATH;
logs/external_submit_retry1.log still waits for complete raw SHA256 validation.

## Verified retry preparation result

Actual job242593.cm exited0. Its independent PBS stdout reports79 tests passed in9.66s,
FROZEN_CONFIGS30, preprocess_wtb EXECUTED exit0, train_only_weights EXECUTED exit0,
and TARGET_MASK_LABEL_EXACT. Source data preprocessing and train-only weighting both
ran on Metis. preprocessing_comparison.json records exact frozen target/mask/label/time
identity; non-bitwise feature differences remain reported rather than fitted away.
The current training array242594[].cm is QUEUED; no training completion, test metric,
scientific significance or final manuscript reproduction is claimed. External raw
staging is still incomplete. The result-neutral verification gate still exits1 for
open TRR02–TRR08 and unfinished raw replay, as required.

## Continuing follow-up —2026-10-15

The current-thread automation `metis` is ACTIVE every30 minutes. It checks actual PBS
history/exits and execution/output lineage, preserves negative/null results and failed
attempts, fixes diagnosed runtime/implementation defects in new attempts, and continues
through all experiment/claim reconciliation and final independent gates. Unchanged
queue states do not count as progress or reproduction. Do not run training locally or
on the Metis login node. No scientific threshold or frozen experiment endpoint changed.

All34 external source files now passed complete SHA256 validation on Metis.
Job242598.cm ran external preprocessing on cn09 and exited0; stdout reports
raw_la_haute_borne, raw_kelmarsh and raw_penmanshiel EXECUTED exit0. GPU training
arrays242594[].cm(30 WTB) and242599[].cm(15 external) remain queued because the
single-GPU queue has no available allocation. Core242595/diagnostics242596/transfer242600
are held by afterok dependencies. No cloud fit/result is certified by those submissions.

`collect_metis_evidence.py` is a read-only collector, deployed outside the frozen
experiment source tree at metis_execution/collect_metis_evidence.py. Run:
```bash
.venv/bin/python metis_execution/collect_metis_evidence.py --root "$PWD"
```
Every call creates metis_execution/monitor_snapshots/<UTC>_<UUID> and never overwrites
older snapshots. Full PBS JSON/stdout/stderr and visible log/receipt bytes are retained,
with SHA256 and source stability metadata. Missing history/logs remain UNKNOWN; copied
running logs are explicitly incomplete snapshots. Exit0 on a stage is not a certificate
of scientific correctness or complete experiment reproduction.

First snapshot20261015T102903Z_3bbcd9a1 archived44 files and11 full scheduler command
outputs/errors. Returned archive and all file hashes were independently checked locally.
Collector correction: its first index mistakenly categorized train_only_weights as a fit
because of a train_ prefix. This is preprocessing, not model training. The first snapshot
is preserved but that fit classification is withdrawn; corrected collector requires an
actual registered model-family-plus-seed name. It cannot turn weighting or queue states
into trained model counts. Later snapshots carry the corrected source hash.

Existing disclosed v2 pytest raw-log loss remains a historical preservation gap; it
is not repaired by claiming a reconstructed original. The new immutable snapshot policy
applies going forward. Full46-artifact/claim coverage, pending factorial conditions,
all fits/decisions and final paper checks remain DOING, and final verification remains FAIL.
