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

## Queue selection error corrected —2026-10-15

The user correctly identified idle GPUs. Earlier wording that treated qllm's GPU
shortage as a cluster-wide shortage is withdrawn. Actual PBS node/queue snapshots
showed18 unassigned GPUs on general cn nodes (17 nodes also had >=4 free CPUs),
whereas qllm binds only llm1 and its single GPU was assigned to another project.
Our explicit qllm submission unnecessarily excluded those general GPUs.

Before moving any job, monitor snapshot20261015T104014Z_b7bb7adc preserved its
original state. Actual successful queue changes, with the same IDs/dependencies:
```bash
qmove rqdf '242594[].cm'
qmove rqdf '242599[].cm'
qmove rqdf 242595.cm
qmove rqdf 242596.cm
qmove rqdf 242600.cm
qalter -W max_run_subjobs=4 '242594[].cm'
qalter -W max_run_subjobs=4 '242599[].cm'
```
All commands exited0. The router selected qmed16cpus for the fit arrays; downstream
held jobs remain in rqdf pending their unchanged afterok dependencies. Array concurrency
was originally1 each and is now4 each, allowing8 independent fits in parallel. Per-fit
1GPU/4CPU/64GB/12h requests, seeds, training parameters, data, metric thresholds and
uncertainty procedures are unchanged. No checkpoint was restarted or overwritten.

At10:42:49UTC qstat showed242594[0..3].cm and242599[0..3].cm RUNNING. Subsequent
inspection found all8 actual runtime JSONs and RUNNING fit receipts. This is actual
job execution, not scientific completion; finished test results remain pending.
Source changes are limited to the LOCAL PBS template default qllm→rqdf for future
deployments. Existing deployed source archives and frozen input hashes were not edited.
For a new submission using the older frozen template, explicitly pass qsub -q rqdf;
do not repeat its qllm default. Scheduler environment PBS_O_QUEUE records the original
submission queue and is not the authoritative current queue after qmove; qstat is.

Evidence: artifacts/metis_queue_fix_20261015 contains full before/after queue/node
metadata, successful command receipt and the subsequent immutable monitor snapshot.
The normal30-minute evidence follow-up remains active. No experiment threshold changed.

## Four-condition factorial closure scheduled —2026-10-15

Protocol RAW-FACTORIAL-FOUR-CONDITIONS-V2 was registered before execution in
EXPERIMENT_REGISTRY and FACTORIAL_FOUR_CONDITIONS_PROTOCOL_20261015.md.
Source/tests are committed at381ee85b. The isolated extension is deployed under
metis_execution/extensions/factorial_four_conditions_v2_attempt1, outside frozen
scripts/windfarm_moe. Its archive SHA256 is
8faa118f48cc40627c997d848de37f373629cba7fc9a5e6bf93b2e644c6c3fa7.
Manifest contains9 extension files and88 frozen base dependencies; actual tests
checked both sets. Current source/protocol snapshot includes the new registration;
the base runtime's old frozen registry/source files remain untouched.

Falsifier§17 gave bounded source PASS_WITH_LIMITATIONS after closing strict physical
wind scaling, successful canonical residual receipt/hash, exact residual formula,
and nonfinite forecast/target/shortfall guards. No source-review verdict is treated
as an experiment result. All variants use the same canonical targets/populations,
K reads actual arrived physical wind, and diagnostic fresh wind never enters its
late-arrival decisions. Five-seed descriptive summaries cannot imply significance
or superiority over a fresh-pitch strongest comparator.

Actual Metis PBS CPU test242601.cm ran on cn32, exited0 and printed:
EXTENSION_AND_FROZEN_DEPENDENCY_HASHES_PASS;11 passed in48.84s.
Software fixtures are not research data. Raw stdout is preserved in the extension
folder and returned to artifacts/metis_factorial_extension_20261015_v2_attempt1.
Array242602[].cm covers4conditions×5seeds, cap4, with afterok dependencies on
242601 and actual WTB core242595. Aggregate242603.cm waits for that complete array,
requires20 successful receipts,44 unique cells per seed and fixed cross-condition
populations, then emits only descriptive means/SD and its own output receipt.
These20 diagnostics have NOT_RUN at submission; dependency hold is not completion.

New predictions include actual shuffle permutations, head weights/losses/sample IDs,
arrived input/source indices, targets/masks/time/node and paired issue-day
cost/reserve/shortage/cell-count arrays. Every sign and failure must be retained.
The collector now recursively archives nested execution directories so future
factorial/aggregate failures are covered along with primary training logs.
All pending coverage and final manuscript/falsification/evidence gates remain in force.

## First completed cloud fit — bounded check only

LHBseed202 completed actual training/evaluation with exit0 and6epochs. Independent
read-only audit verified receipt/source/input/output hashes, deep output manifest,
raw source/cache provenance and full evaluation anchors/physical target/mask/time/
node/window identity. Predictions have shapes4261×24×4(val) and4981×24×4(test),
with all valid forecasts finite. Audit report is
artifacts/metis_heartbeat_20261015/LHB_seed202_20261015T111934Z.json.
This is a single-fit artifact/population verification, never a five-seed experiment,
matched decision-value result, historical numerical replication or whole-paper PASS.
The11 software tests and20 pending factorial diagnostics likewise do not certify
scientific completion. All open task/coverage/final gates remain unchanged.

## Parallel training and exact-input readiness gate —2026-10-15

After observing9 additional general nodes with unassigned GPU and >=4 freeCPUs,
qalter increased independent WTB array242594 cap4→8 and external242599 cap4→6.
Subsequent actual PBS counts were8WTB+6external RUNNING; per-fit resource request,
configuration, seeds, data and every scientific endpoint remain unchanged.

A separate registered scheduling addendum,
FACTORIAL_READINESS_SCHEDULING_20261015.md, permits overlapping the factorial with
unrelated core analyses only after its actual inputs are independently verified.
The existing20-job array242602 has NOT been released by this note. Its current
original dependency is afterok242595 plus beforeok242603, with system hold.

Audit/controller code a96f96ed was source-reviewed in falsifier§18 as bounded
PASS_WITH_LIMITATIONS after adding exact architecture/train-config checks,
unique family×seed coverage, actual exit0/nonempty evidence, and strict current
PBS dependency/hold preservation. A new prerequisite or human hold blocks any
replacement. Source review does not certify actual software/audit/job execution.
Draft tools attempt1 were never PBS-executed and remain retained. Tools attempt2
live outside frozen scripts/windfarm_moe and pin all audit/controller/test sources.
An exclusive controller lock prevents duplicate submissions; probe creates no lock.

Actual PBS CPU audit242604 exited0: audit tool hashes PASS,3 negative-guard software
fixtures passed in2.04s, and8 completed model artifacts passed full checks. These
are forecast201–204 and LHB201–204. Checks cover frozen training/architecture
configs, finite checkpoint tensors, input/source/output hashes, complete epoch
history, and full val/test target/mask/time/node/window identity and finite predictions.
The report explicitly says completed-mode,37pending,0failures, readinessNOT_CERTIFIED,
scientific_completionfalse. It cannot release factorial or certify a5-seed experiment.
Returned report/stdout: artifacts/metis_fit_audit_20261015_attempt2. Future audit
attempts must use new output/log directories; do not rerun the fixed attempt2 script
against its existing report or overwrite it.

The one-shot watcher is active, polling receipt metadata only. Once all20 required
models and the shared canonical residual have actually exited0, it submits a PBS
CPU readiness audit (no login-node model computation). That audit verifies the
same artifacts plus residual provenance/target/formula/finiteness. Only matching
INPUTS_VERIFIED report+actual audit exit0+software-test dependency+unchanged original
PBS dependency/hold permit qalter. It saves full before/after qstat and qalter logs;
no qrun, no forced hold removal, no new canonical target, no numerical gate changes.
Until then the original dependency remains. Watcher state/lock/logs are under
metis_execution/factorial_readiness_control.* and fit_audit_tools/attempt2.
All logs and nested audit reports are included in subsequent immutable snapshots.
Final paper/claim reconciliation and all experiment evidence gates remain pending.

##19:50follow-up: thirteen model artifact audits, not research completion

NewCPUaudit242605 used the same pinned audit tool with a fresh output/log path.
It exited0 and verified13closedmodels: WTBforecast201–205,LHB201–205 and
Kelmarsh201/202/204;32models remained pending in that audit. The report retains
readinessNOT_CERTIFIED/scientific_completionfalse. Nonewtrainingfailurewasfound.
Returned logs/report and independently verified227-file/16-PBS-command snapshot:
artifacts/metis_heartbeat_20261015_1951. The four-condition controller still awaited
16requiredreceipts and made no dependency change. Whole experiment, decision
statistics and paper claim reconciliation remain unfinished; no threshold changed.

## 20:03–20:15 follow-up: seventeen model artifacts verified

The external array had only five remaining fits. After checking actual free GPU,
CPU and memory resources, WTB array concurrency was increased from 8 to 9 using
`qalter -W max_run_subjobs=9 '242594[].cm'`. Subsequent PBS evidence showed nine
WTB and five external fits running. Per-fit resources, configurations, seeds and
scientific thresholds were unchanged; other projects were not modified.

Fresh CPU audit 242606.cm exited 0, with pinned tool hashes passing and three
software guard tests passing in 1.50 seconds. Its report verified 17 model
artifacts: forecast201–205, aligned_force203/205, Kelmarsh201–205 and LHB201–205.
It left 28 pending and found no failures among the inspected completed models.
The checks cover input/source/output hashes, raw/cache provenance, exact model
and training configurations, finite weights, complete epoch histories and full
validation/test anchor, target, mask, physical time, node and prediction identity.
This is completed-model artifact verification, not decision-experiment or paper
reproduction. The report remains NOT_CERTIFIED / scientific_completion=false.

Evidence: `artifacts/metis_followup_20261015_2003/report.json`,
`completed_20261015T1203.stdout`, `concurrency_change.stdout`, and immutable
snapshot `20261015T121447Z_2c1a8337`. Independent verification checked 259 copied
files and 17 full PBS command stdout/stderr pairs against their SHA256 records;
the returned report bytes and pinned audit source matched the snapshot.
Running-file copies represent only bytes visible when collected, not final logs.

At 12:12:31 UTC the factorial controller still awaited 16 required execution
receipts. All four conditions remain held; no readiness audit or dependency
release is inferred from this completed-mode audit. The actual final verification
gate returned exit 1 for unfinished TRR02–TRR11 and raw replay coverage. All
experiment coverage, manuscript reconciliation and final independent reviews
remain open. No scientific gate or negative-result retention rule was changed.

## 20:23 follow-up: twenty-five model artifacts verified

Fresh CPU audit242607.cm exited0; pinned tool hashes passed, and three software
guard tests passed in2.20s. Its completed-mode report verified25 model artifacts:
forecast201-205, aligned_force201-205, unaligned201, Kelmarsh201-205,
Penmanshiel201-204 and LHB201-205. Twenty fits remained pending in that audit;
no completed-model artifact failure was found. Exact checkpoint configurations,
finite tensors, complete histories, source/input/output/raw/cache hashes and full
validation/test target/mask/anchor/time/node/window identity were checked.
Readiness remains NOT_CERTIFIED and scientific_completion=false.

With external14expired/1running and seven compatible general GPU nodes free,
only WTB concurrency was raised9->13. Subsequent actual PBS state was13WTB plus
1external running. Scientific settings, seeds, thresholds and per-fit resources
were unchanged. Four-condition controller still awaited15 required execution
receipts at12:25:31UTC; its existing hold was not released.

Evidence: artifacts/metis_heartbeat_20261015_2023/report.json and
completed_20261015T1223.stdout; immutable snapshot20261015T122608Z_fd54cc64.
Independent verification rehashed297 copied files and18 full PBS command
stdout/stderr pairs; returned report bytes and pinned audit program hash match
the snapshot. Running-file copies are available-byte snapshots, not final logs.
The actual final verification gate remains exit1 for unfinished raw coverage
and TRR02-TRR11. Model artifact verification is not decision-experiment or
whole-paper reproduction; final statistics, claims and independent reviews
remain pending. All previous failures and negative-result requirements remain.

## 20:53 follow-up: all external model fits artifact-verified

Actual CPU audit242608.cm exited0; pinned hashes passed and three software guard
tests passed in1.54s. It verified31 completed model artifacts: forecast201-205,
aligned_force201-205, unaligned201-205, aligned204, and all15 external fits across
Kelmarsh, Penmanshiel and LHB. Fourteen fits remained pending at audit time;
no completed-model artifact failure was found. This verifies exact configurations,
finite weights, complete epoch histories, source/input/output/raw/cache provenance
and full validation/test anchor/target/mask/time/node/window identity. It does not
certify external transfer decisions or whole-paper reproduction: NOT_CERTIFIED,
scientific_completion=false.

External array242599 reached F/exit0. With WTB13running/1queued and four eligible
free GPU nodes, only WTB concurrency was raised13->14; actual subsequent qstat
showed14running/0queued. All per-fit resources, settings, seeds and scientific
gates remain unchanged. The factorial controller still waits10 required receipts
at12:55:32UTC, so all four conditions remain held.

Evidence: artifacts/metis_heartbeat_20261015_2053/report.json and
completed_20261015T1253.stdout; immutable snapshot20261015T125528Z_bbf9850e.
Independent verification rehashed342 files and19 full PBS command output/error
pairs and matched the report bytes and pinned auditor hash. Running logs remain
available-byte snapshots; later exit0 receipts outside this audit are recorded
separately as awaiting verification. Final verification gate still exits1 for
unfinished tasks/raw coverage. Paper conclusions, decision statistics and final
independent reviews remain open; no reproduction success is claimed.

## 21:23 follow-up: forty-three model artifacts verified

Actual CPU audit242610.cm exited0. Pinned tool hashes passed and three software
guard tests passed in1.57s. Forty-three model artifacts passed the completed-mode
config/checkpoint/history/hash/provenance/full val-test identity checks; dense204
and dense205 were still running, with no completed-model artifact failures.
Readiness remains NOT_CERTIFIED/scientific_completion=false. Model artifact
verification does not certify reserve/statistical experiments or paper claims.

All20 model execution receipts needed by the four-condition extension were
available. The shared canonical residual execution receipt was still absent;
the controller remained WAITING_FOR_REQUIRED_EXECUTION_RECEIPTS with pending1
at13:26:32UTC. Core242595 remains dependent on allWTB fits. No factorial release,
new canonical generation, source change or numerical threshold change occurred.

Evidence: artifacts/metis_heartbeat_20261015_2123/report.json and
completed_20261015T1323.stdout; immutable snapshot20261015T132639Z_65519edd.
Independent verification rehashed370files and20 full PBS stdout/stderr pairs,
matched returned audit report bytes and checked the pinned auditor source hash.
Running-file copies remain snapshots of visible bytes, not complete final logs.
A read-only planning inventory groups all46 original coverage entries by source;
source existence alone does not establish replay coverage. Actual final gate
still exits1 for unfinished tasks/raw replay. All20 factorial runs, decision
statistics, manuscript claims and final independent reviews remain pending.
