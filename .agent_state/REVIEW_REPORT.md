# Independent Evidence Review — RA00–RA05

**Date:** 2026-10-12T23:55:00+08:00
**Reviewer:** Independent Evidence Reviewer
**Scope:** `docs/REVERSE_AUDIT_LITERATURE_MATRIX_20261012.csv`, `docs/REVERSE_SCIENTIFIC_AUDIT_20261012.md`, `.agent_state/EVIDENCE_LEDGER.md` RA00–RA05, and `.agent_state/FALSIFICATION_REPORT.md`
**Write boundary:** This report only. No manuscript, scientific contract, experiment output, registry entry, or formal result was modified.

## Verdict

# **PASS_WITH_BLOCKERS**

RA00–RA05 form a materially complete, evidence-linked reverse audit. The two requested deliverables exist, the RA entries in the evidence ledger identify the inspected files and read-only recomputations, and the 2026-10-12 falsifier report is consistent with the current scripts and artifacts. I found no basis to weaken the audit's **REVISE** project decision or its **FAIL / DO NOT SUBMIT** decision for the current manuscript.

`PASS_WITH_BLOCKERS` applies to the **integrity of the audit**, not to the scientific package or manuscript. The scientific and submission blockers listed below remain hard blockers.

## RA00–RA05 Evidence Review

| Task | Review status | Evidence check |
|---|---|---|
| RA00 | VERIFIED | The audit correctly separates the authoritative scientific contract/current artifacts from superseded reports and records that the October experiments postdate the manuscript-facing verification controls. Git history and the current manifests support this finding. |
| RA01 | VERIFIED, source-bounded | The replacement matrix contains 15 literature records with title, DOI/URL, novelty threat, evidence strength, and verification status. Independent primary-source spot checks confirmed the three highest-impact 2026 threats: Bel-Hadj et al. (`10.5194/wes-11-1363-2026`), Wang et al. (`10.1016/j.epsr.2026.113241`), and Wang & Wang (`10.1016/j.seta.2026.105438`). The matrix does not reuse the legacy DOI-title pairings as evidence. |
| RA02 | VERIFIED | The baseline/provenance findings match code and artifacts: EXP-03 does not delay `Patv_hist`; its proxy comparison is performed on standardized features and yields zero positives; its evaluation mask deletes delayed/missing cells; its saved trace/mask do not encode the executed grid. EXP-02 reverses the bootstrap-probability decision logic and misclassifies `Zero-Privileged` models as oracle. |
| RA03 | VERIFIED | The claim-artifact table correctly identifies the 55.3% latency-condition error, omission of EXP-01 corrected v2 from the manuscript, post-hoc transition slicing, averaged per-seed uncertainty summaries, and lack of October-experiment coverage in the existing verification manifest. |
| RA04 | VERIFIED | The synthesis includes reusable assets, missing evidence, fatal defects, exactly three highest-information experiments, explicit falsification conditions, a REVISE decision, and reviewer attack questions. It preserves negative/null results and does not use favorable outcomes as acceptance criteria. |
| RA05 | VERIFIED | `.agent_state/FALSIFICATION_REPORT.md` applies all required adversarial attacks and reaches a defensible `FAIL FOR CURRENT SUBMISSION; REVISE THE PROJECT` verdict. Its claim table, surviving explanation, deletion/correction list, and decisive-experiment recommendations agree with the inspected repository evidence. |

## Direct Consistency Checks

1. **EXP-03 same-information failure — confirmed.** `scripts/run_exp03_async_benchmark.py:132-145` searches for `Patv`, while the consumed feature is `Patv_hist` (`:310,340-348`; cache metadata lines 5–16). Active power therefore remains fresh while Wspd is delayed.
2. **EXP-03 proxy degeneration — confirmed.** `scripts/run_exp03_async_benchmark.py:335-371` compares standardized Wspd/Patv values with physical thresholds. The recorded read-only check (`0 / 570,974` positives) is consistent with the cache ranges and code.
3. **EXP-03 population/provenance failure — confirmed.** `mask_test_h` removes asynchronously invalid cells (`:416-445`); total PSREI collapses with coverage. Only the first delay's packet sample is saved (`:413-414,474-485`), and `missing_mask.json` is generated from the artificial `t % 5 != 0` rule (`:488-493`).
4. **EXP-02 verdict failure — confirmed.** The stored quantity is `P(delta <= 0)` (`scripts/run_exp02_zero_privileged_supervision.py:303-312`), while the winner rule requires a favorable negative delta and a small value of that same quantity (`:785-792`). The substring test at `:717` also labels every `Zero-Privileged` model as privileged/oracle; the CSV and report contain the resulting wrong roles.
5. **EXP-01 supersession — confirmed.** Corrected v2 uses independent site-specific frozen forecasts and gives Penmanshiel h=6 transferred-STGQ deltas positive for all five seeds. The current manuscript still presents the earlier external/global-quantile narrative instead of this strong-comparator result.
6. **55.3% latency attribution — confirmed.** The 127.55 to 57.01 MWh calculation is a Delay-6/60-minute result (`artifacts/ARTIFACT_MANIFEST.json:69-71`; `paper_tste_ieee.md:372-409`), whereas the abstract/introduction/discussion attach it to 10–30 minutes.

## Blockers That Must Remain Open

### Scientific and submission blockers

1. EXP-03 is invalid for scientific inference until all consumed fields, including `Patv_hist`, are delayed under a fixed evaluation population and full trace/mask provenance.
2. EXP-02's formal “deficit established” verdict must be withdrawn or recomputed with correctly oriented, joint seed/time inference; the h=6 result is seed-unstable.
3. The manuscript must correct the 55.3% result to the 60-minute synthetic Delay-6 condition.
4. The manuscript must disclose EXP-01 corrected v2 against Site-Local Wspd-Bins and stop using the weak global-quantile comparison as external incremental-value evidence.
5. Deployable transition claims remain blocked because the current transition slice uses future true-regime information.
6. Graph/wake/MoE necessity, universal cross-site generalization, pitch-never-recorded decision value, and field prevalence of the simulated latency/pitch-suppression conditions remain UNKNOWN or NOT ESTABLISHED.

### Audit/control-plane blockers

1. `docs/REVERSE_SCIENTIFIC_AUDIT_20261012.md:46` describes the falsifier as the pre-RA05 2026-09-26 report. That statement is historically correct for the RA00–RA04 draft state but is now stale because RA05 replaced the file with the 2026-10-12 falsification report. It must not be read as current post-RA05 state.
2. `RUN_STATE.json` still contains superseded EXP-01 v1 and invalid EXP-02/03 completion notes and duplicate `last_verified_task` keys. The audit correctly identifies this contamination, but the read-only phase intentionally did not repair it.
3. `.agents/verification_manifest.json`, `scripts/verify_decisive_gate.py`, and `artifacts/ARTIFACT_MANIFEST.json` do not cover EXP-01 corrected v2, EXP-02, EXP-03, or the reverse-audit deliverables. A subsequent `verify_gate.py` exit 0 is therefore a procedural repository gate only; it cannot convert the scientific/submission FAIL into PASS.
4. The EXP-03 result/trace/mask/protocol files remain ignored or absent from the committed artifact manifest/release, so independent clean-clone reproduction of the claimed envelope is not established.

## Completion Statement

The reverse audit itself is sufficiently complete and internally consistent to guide revision, with the limited synchronization caveats above. The central negative-result thesis survives; the current manuscript and October experiment closures do not.

**FINAL INDEPENDENT REVIEW VERDICT: PASS_WITH_BLOCKERS FOR RA00–RA05 AUDIT INTEGRITY.**
**SCIENTIFIC/SUBMISSION VERDICT RETAINED: FAIL / DO NOT SUBMIT; REVISE THE PROJECT.**

---

## Phase 2 Retrospective Independent Review (2026-10-14)

**Auditor:** Independent Evidence Reviewer  
**Target Scope:** Phase 2 retrospective protocol repairs (EXP-01 v4 native blocks, strong baseline two-stage hierarchical bootstrap, elimination of active arithmetic mean CI/p-values, manuscript & claim-gate synchronization).  
**Verification Verdict:** **PASS_WITH_BLOCKERS (Integrity Verified / Submission NO GO Retained)**.

### Verified Forensic Facts
1. **EXP-01 Lineage & Masking:** PyTorch checkpoints for seeds 201–205 confirmed WTB source (`dataset='wtb'`, `num_nodes=134`). Python AST and tensor guards confirm dual-channel pitch withholding (`Pab_mean` and `Pab_std` masked in history, masks, and anchor physics before model forward).
2. **Native Day Blocks Exported:** `artifacts/exp01_pitchmasked_v4/exp01_native_day_blocks_v4.npz` stores all 80 native day-block arrays ($5\text{ seeds} \times 2\text{ farms} \times 2\text{ horizons} \times [\Delta, N, L_C, L_B]$), exactly replicating aggregate seed summaries with zero error.
3. **Elimination of Arithmetic Averaging of P-values/CIs:** `scripts/test_strong_baseline_closure.py` and active CSV `artifacts/strong_baseline_joint_v2/strong_baseline_bootstrap_contrasts.csv` have eliminated arithmetic averaging across seeds. Active tables now strictly display `Hierarchical_Joint` computed via two-stage hierarchical resampling (sampling seeds with replacement, then 35 daily blocks with replacement).
4. **Interaction Sum vs. Rate Reality:** The joint interaction is $-297,565\text{ kWh}$ ($95\%\text{ CI } [-651,680, -18,021\text{ kWh}]$, empirical $P=0.9824$). However, on a per-cell basis, posterior conditioning is more costly than wind-speed binning across both regimes ($+0.807\text{ kWh/cell}$ in transition, $+1.671\text{ kWh/cell}$ in steady state). Both populations carry positive cost penalties; the negative interaction reflects relative penalty attenuation, not cost superiority.
5. **External Heterogeneity Confirmed:** Penmanshiel $h=6$ $\Delta \approx -315.4\text{k}$ (CI spans zero $[-1,590\text{k}, +970\text{k}]$, $P=0.7084$); Kelmarsh $h=6$ $\Delta \approx +352.4\text{k}$ (statistically significant cost penalty, $P=0.0074$). Zero-shot cross-site transfer superiority is refuted.
6. **Control-Plane & Negative Result Preservation:** Historical v2 benchmark CSV matches SHA256 `596f46e0...` byte-identical; `docs/SCIENTIFIC_CONTRACT.md` matches HEAD and origin/main with 0 modifications. Branch is `revision_topjournal_reconstruction`, zero push to `main`.

### Unresolved Submission Blockers (Mandating Continued REVISE / NO GO)
1. EXP-01 v4 is a post-hoc retrospective repair, not an ex-ante pre-registered trial.
2. Transition slice remains an oracle post-hoc diagnostic filter, not an online deployable policy.
3. Aerodynamic moderators of cross-site transferability remain unresolved and cannot be causally attributed to wake graphs or turbine count.

**AUDIT INTEGRITY VERDICT: PASS.**  
**MANUSCRIPT DISPOSITION: REVISE / NO GO.**


---
## 2026-10-15 — TCA03 independent evidence review (bounded current-status audit)

**REVIEW VERDICT: PASS_WITH_BLOCKERS for the bounded evidence audit; full raw-data retraining reproducibility is NOT ESTABLISHED.**

Scope: independent review of current reproduction entry points, training evidence archives, and the limits of the verification infrastructure. This is not a re-certification of every historical VERIFIED entry, a fresh-clone end-to-end run, a clean-environment retraining, or a guarantee against all fabrication. Main-agent numerical summaries must retain direct artifact citations and the scientific claim ceiling.

### Directly verified findings

1. **Broken documented external preprocessing command.** `docs/DATA_AVAILABILITY_AND_PREPROCESSING.md:75-77` prescribes `python main.py external_cache --root-dir . --site ...`. Executed `python main.py external_cache --help`: **exit 1**, `invalid choice: external_cache`. Executed `python main.py external-wind-preprocess --help`: **exit 0**, with `--farm`, `--external-source-dir`, `--dataset` and `--cache-root`; it has no `--site`. Actual parser registration is `main.py:224-228`.
2. **Documented WTB cache destination does not follow the shown command.** The command at `docs/DATA_AVAILABILITY_AND_PREPROCESSING.md:66` does not set a custom cache root, but line 68 claims `artifacts/cache_signature_trainweight/wtb_245d_canonical/`. The parser default is `main.py:195` (`artifacts/cache`), and `windfarm_moe/config.py:92-109` constructs `wtb_245d`. Default code therefore resolves to `artifacts/cache/wtb_245d`. This was checked by source inspection, not by running preprocessing.
3. **The documented Tier 3 is not an executable full recipe.** `README.md:23` promises all five seeds, baselines and transfers from raw SCADA but points to a document that ends with preprocessing and Category B metadata. It provides no complete current five-seed training/evaluation command chain. `requirements.txt:2-8` uses broad version ranges; this is not a frozen environment specification. A 48-hour estimate is not independently verified here.
4. **Training archives exist for the five sampled source checkpoints.** A read-only Python command loaded `artifacts/strictmask_ablation_rerun_wtb_full/wtb_bal_align_force_seed{201..205}/best_model.pt` and each sibling `training_summary.json` using `torch.load(..., map_location='cpu', weights_only=False)` and JSON parsing: **exit 0**. All checkpoints contain `model_state`, `model_config`, `train_config`, and `metadata`; embedded seeds match 201..205 and `metadata.dataset` is `wtb`. The summary history lengths are respectively 9, 10, 9, 9, 7; best epochs are 4, 5, 4, 4, 2. Nonempty per-epoch train losses exist. The training implementation saves these structures at `windfarm_moe/train.py:286-309,335-340`. These facts establish available archive evidence, not independent proof of historical execution or raw-data replay.
5. **Hash verification is not retraining.** `scripts/verify_replication.py:46-58,103-113` checks SHA256 against a manifest, while line 516 emits `FULLY_REPRODUCIBLE`. No call to training is present in that verifier. `README.md:21-23` distinguishes tiers, but the verifier's verdict must not be represented as proof that every manuscript result has been independently regenerated from raw data. Likewise `scripts/audit_phase2_retrospective.py:54-76` checks checkpoint source metadata rather than re-running the original training.
6. **Channel-ablation reference limitation.** `scripts/run_channel_consequence_ablations.py:181-182` hardcodes `direct_ref_h1=8009040.0` and `direct_ref_h6=16469328.0`; lines 312-313 compute deltas from these fixed references. Line 339 writes aggregate results. The inspected script contains a training loop but no checkpoint-saving operation. Script availability does not prove execution history; this contrast cannot establish incremental value over a freshly matched strong baseline without additional provenance.
7. **Gate scope limitation.** `.agents/scripts/verify_gate.py:15` parses task IDs beginning with `T`, and lines 73-80 only require any `PASS` or `PASS_WITH_BLOCKERS` token anywhere in the review report. Consequently a gate PASS alone is not evidence that all non-T experiment tasks or the latest independent scientific verdict passed. No gate source was changed by this reviewer.

### Blocking requirements for the user's stronger assurance

- An independently executed, current-version raw-data -> preprocessing -> all model/baseline seeds -> predictions -> statistics -> manuscript-table chain remains unverified in this review.
- The exact paper-to-code mapping, raw data versions/hashes, frozen environment, run commands, and expected tolerances must be joined in a usable reproduction manifest. Broken documented commands currently preclude blindly following the supplied recipe.
- Full provenance for all ablations is not established by the five checkpoint sample; aggregation-only artifacts require per-seed traces and/or rerun evidence.
- Existing scientific limits (retrospective protocol repair, ex-post transition slices, unmatched graph controls, and incomplete asynchronous packet provenance) cannot be removed by cached consistency checks.

**Allowed completion wording:** current evidence has been audited within the stated scope and concrete gaps are disclosed. **Disallowed wording:** every result is proven authentic; anyone can reproduce all training results; the full scientific package is fully reproducible.


### 2026-10-15 — Review of the current-status draft

Read `.agent_state/CURRENT_RESEARCH_AUDIT_20261015.md` and directly cross-checked the WTB policy rows in `artifacts/strong_baseline_joint_v2/strong_baseline_closure_summary.csv`, the five transition rows in `artifacts/matched_budget/frontier_auc_summary.csv`, all four current external joint-stat rows in `artifacts/exp01_pitchmasked_v4/exp01_pitchmasked_v3_joint_statistics.csv`, the channel metrics in `artifacts/channel_consequence_ablations.csv`, and the decision-cost CI in `docs/PRIVILEGED_SUPERVISION_ABLATION.md`. The draft correctly distinguishes positive representation evidence, higher posterior decision cost, and inconclusive/negative external transfer findings. Its five-seed mean versus all-budget-support distinction is consistent with the source table. It appropriately does not certify raw-data retraining or worldwide novelty.

The draft should incorporate the verified CLI/cache defects and the limited positive checkpoint-history evidence above. The Exp-C value must remain qualified until the separate scientific-falsifier execution record is available; this reviewer has not independently recomputed Exp-C. The bounded audit verdict remains **PASS_WITH_BLOCKERS**; full scientific reproduction remains **NOT ESTABLISHED**.


## 2026-10-15 — Independent review of raw-replay repair in progress (30b1cd8 plus observed working tree)

Scope: read-first audit requested during the RERUN-20261015 campaign. This is an interim review of implementation and evidence integrity, NOT certification of completed raw-data reproduction. Read RUN_STATE.json, TASK_LEDGER.md, EVIDENCE_LEDGER.md, the evidence-reviewer role, scientific contract, registry and replay protocol. No training/GPU workload was launched by this reviewer; no implementation files were edited.

**Verdict: PASS_WITH_BLOCKERS for the bounded registration/repair evidence currently disclosed; full replay and scientific completion NOT ESTABLISHED.** TRR02–TRR07 are still unchecked/DOING, and that status is appropriate. The word PASS here must not be cited as experiment completion, authentic-history certification, or a submission gate.

### Directly verified progress

- Commit 30b1cd8 adds the registered replay protocol, 30 historical configuration records (6 WTB families × seeds 201–205), fresh training orchestration, version-separated output paths, channel horizon correction, matched channel decision comparator, and new archives. Inspection found no reuse of historical weights for initialization in train_one: configurations instantiate train_model from scratch.
- The channel horizon accessor indexes h−1; h=6 now selects residual index 5. Its transition recall now requires both adjacent labels to be valid, and it stores old/new denominators. Saved weights, training histories, representation probabilities and decision reserve/target/mask arrays are implemented. These are code capabilities; the full replay output has not yet been observed.
- EXP03 starts unobserved channels at standardized zero; full delay matrices, selected source indices, missing/stale masks and consumed features are archived. Prediction/target/mask/day-block files are implemented for each delay/seed/horizon. It explicitly describes one trace per delay shared by five model seeds, and tau-star as loss of demonstrated advantage. Small-array tests validate causal selected-source reconstruction; no complete real-data packet grid was observed in this review.
- Command `python -m pytest tests/test_replay_integrity.py tests/test_exp03_async_arrival.py tests/test_exp02_protocol.py tests/test_f4_verdict_regression.py tests/test_f4_hierarchical_bootstrap.py -q` returned exit 0: 28 passed, one pynvml deprecation warning (9.90 s). These tests do not certify all scientific protocols.
- Independently executed `python main.py external-wind-preprocess --help` and `python scripts/raw_replay.py --help`; both returned exit 0. The corrected CLI exists. This is not evidence that every raw external dataset has been successfully processed.
- Observed execution receipts: preprocess_wtb=EXECUTED, train_only_weights=EXECUTED, train_forecast_201=RUNNING. The forecast log contained actual epoch-1 loss lines through batch 450 at inspection. No finished training claim is warranted. coverage.json has 46 entries, all NOT_RUN at this checkpoint.

### Concrete findings sent immediately to the coordinating agent

1. **EXP02 physical proxy uses the wrong inverse scaler (verified, material scientific defect).** In committed code, load_exp02_cache prefers physics_model.npy, but main converts its active-power channel using feature_stats[Patv_hist]. Actual current raw-derived metadata records physics_model_stats[3] mean/std=(359.9330139160156,426.30133056640625), versus Patv_hist=(379.8779296875,416.43853759765625). Direct comparison against physics.npy on formal val/test anchors found mislabeled proxy cells: epsilon20 314/29; epsilon50 189/24; epsilon100 82/8 (val/test). This is not random retraining variation. The working tree was being repaired to use explicit physical-unit data during review; a new regression test and versioned correction record are required before treating EXP02 reruns as valid. The historical EXP02 numbers must not inherit corrected-protocol validity.
2. **EXP02 invalid-transition recall persisted in the commit.** Its helper and diagnostic call omitted validity, reproducing the defect fixed in channel probes. The latest observed working tree passes v_mask and adds validity handling; targeted verification of the amended version is still required.
3. **EXP02 report generator still contained result-direction hardcoding at inspection.** Text at the then-current lines 1110 onward states h1 is cheaper with less reserve, h6 is dominated by one catastrophic seed, procurement collapses, and no stable gain is established, regardless of new outcomes. The target artifact label also names the historical CSV. Full reports must compute these interpretations or report signed quantities neutrally. A real retraining run could otherwise emit an untrue narrative even with correct CSV values.
4. **Replay receipt completeness and resume validation were insufficient in 30b1cd8.** Cache inputs were mostly metadata-only; residual generation omitted model/cache inputs; downstream receipts recorded only residual inputs and one summary CSV output. Resume originally hashed output_manifest.json but not the predictions/histories it listed, and did not check inputs/source. The coordinating agent added verify_run_receipt during this review. An isolated temporary-directory mutation probe against the changed working tree now rejected a changed cache with ValueError, confirming that particular guard is load-bearing; the probe did NOT demonstrate the old vulnerability after the patch. Outstanding: end-to-end downstream input and directory-output manifests, required archive completeness, inclusion of main.py in source coverage, and linkage between raw/preprocessing/cache/model/decision layers. Source/hash preservation must cover executed code, not merely a Git revision while files are changing.
5. **Running-process/version boundary needs explicit handling.** The active run-wtb parent loaded the original implementation before new cache_manifest requirements were edited. At inspection cache_manifest.json did not yet exist. Future train-one subprocesses will load new files. Any later manifest capture must be labeled as such; it cannot prove a pre-training hash record existed. Source/command receipts must distinguish the actual code version used by each run.
6. **Supplementary text remains internally inconsistent.** At inspection paper_tste_supplementary.md:800 still calls A8c/v2 authoritative, whereas the new caption and final notice mark it historical/superseded by retrospective v4. Fix the live prose as well as the caption. The main-text correction from 4/5 all budgets to 4/5 budget-averaged and 3/5 every budget is present.
7. **Scope coverage remains incomplete and correctly unclaimed.** Current run-wtb orchestrates WTB families, residuals, strong baseline, channels, EXP02 and EXP03. It does not yet execute external raw sites/EXP01, matched-budget/rho analysis, calibration/observability families and all manuscript assets. Forty-six PENDING/NOT_RUN coverage entries are not completed evidence chains. Withdrawals must remain distinct from successfully reproduced experiments.

### Required closing evidence

Before final completion: retain all failed/negative runs; finish and hash every registered dependency; independently recompute summaries and uncertainty from archived predictions/blocks; reconcile all active manuscript/standalone/PDF claims; document historical-vs-corrected differences without fitting success tolerances; run independent scientific falsification and final verification. No raw-training completion, exact historical numerical reproduction, or universal reproduction guarantee is issued by this interim review.


## 2026-10-15 — Bounded Metis deployment evidence review (upstream 3c0e4e2; v3 package)

Scope: read-only implementation/package/status review following the user's instruction to execute on Metis. Read current RUN_STATE.json, TASK_LEDGER.md, EVIDENCE_LEDGER.md, migration notice, scripts/metis_replay.py, package_metis_replay.py, metis_replay.pbs, deployed-source script and returned logs. No training, submission, package mutation or implementation edit was performed by this reviewer. The only reviewer write is this review entry.

**Bounded verdict: PASS_WITH_BLOCKERS for the inspected deployment/status separation. Full scientific reproduction remains FAIL / NOT COMPLETE, with 47 unresolved raw-replay checks.** This verdict is not a scientific PASS and does not close TRR02–TRR08.

### VERIFIED deployment evidence

- Independently recalculated source.zip SHA-256: `22fa91ea1da47e045108f46ce73cd9f692105a8850fae3a1c6cc8913ba71d14f`, matching source_archive_manifest.json. The ZIP has 90 members. Every packaged file listed in the 124-row input manifest matched its recorded byte hash; all packaged Python files parsed without AST errors. The 36 raw files are intentionally external to the source ZIP. Declared WTB/external/diagnostic entry points and main.py are present; the PBS script contains zero CR bytes.
- No .pt/.pth weights or local model/execution output directories are packaged. Historical reference arrays are the five declared target/mask/label/time identity files, not trained checkpoints. Configurations and historical metadata references remain distinct from initialization weights.
- All four expected_raw_hash_origin records match the actual retained local raw-read receipts. All 36 expected raw file hashes/sizes agree with those receipts. This verifies the origin chain of the expected hashes; this reviewer did not rehash all local raw datasets or claim all remote external uploads complete.
- deployment.json records upstream commit `3c0e4e201e269f4410373dfe65734b48777815dc`. Deployment initializes/commits a distinct runtime subset with an explicit message identifying it as such, rather than forging the upstream Git identity. Returned v3 log records actual cloud snapshot `3ec80337b95a32831ad32f4b217b63a9606fc3a5`. The log reports source.zip OK, source/WTB input hash validation, and DEPLOYMENT_PREFLIGHT_PASS.
- Read-only SSH commands returned exit 0 and inspected actual remote metis_execution files. `software_tests.txt` reports **79 passed in 87.10 s**; `pip_check.txt` reports no broken requirements. requirements.txt in the v3 ZIP includes seaborn>=0.13.0; returned setup log records installed seaborn 0.13.2. These are software/deployment checks, not scientific validation.
- Read-only inspection of remote pbs_jobs_wtb.json confirms four submissions: prepare 242589.cm, fit array 242590[].cm, core 242591.cm and diagnostics 242592.cm. Each receipt explicitly says SUBMITTED_NOT_EXECUTED and scientific_completion=false. Dependencies use afterok, and the training array is 0–29%1. Actual qstat snapshot: prepare R in short queue; the other three H in qllm. Thus preprocessing has started, while training has NOT been observed to start or finish. The receipt's submitted state is not falsely promoted to execution.
- METIS_MIGRATION_NOTICE.json explicitly preserves local results without pooling them into cloud results. Both interrupted local receipts (WTB forecast204 and LHB205) now say INTERRUPTED_BY_USER_HOST_CHANGE and NOT_ESTABLISHED_FROM_PARTIAL_FIT. The ZIP independently confirms exclusion of these fits. Earlier completed local fits remain local provenance, not cloud executions.
- `git diff 30b1cd8 HEAD -- docs/SCIENTIFIC_CONTRACT.md` returned no changes. Current gate report still says FAIL, zero validated reproduced manuscript artifacts and 47 unresolved checks. Current task ledger retains TRR02–TRR08 as DOING. No threshold relaxation or scientific completion claim was found within this bounded deployment review.

### BLOCKERS / remaining UNKNOWN at inspection

1. The source ZIP lists four historical raw-read receipt paths/hashes but does not include their original contents. A subsequently created `raw_hash_origin_receipts.zip` was independently inspected: **22 bytes, zero members**, both locally and in remote file listing. This sidecar cannot yet serve as a portable historical-source record. Coordinate a separate versioned sidecar with the four actual receipts and its manifest; do not retroactively change the already-deployed ZIP or pretend the empty archive supplied evidence.
2. The v2 missing-seaborn failure was reported by the coordinator and is consistent with the v3 dependency repair, but the returned deployment_preflight.log ends at the old Git snapshot and contains no pytest traceback. Both deployment scripts redirect pytest to the same software_tests.txt, now containing the successful v3 run. The original failed pytest output has NOT been independently inspected/preserved by this reviewer. Until an immutable failed-output copy is located, mark that original raw log unavailable rather than claiming every failed log was archived. The retained v2 source package remains available for protocol provenance.
3. Complete remote external-data SHA-256 validation is UNKNOWN: the returned staging log only shows the first five Kelmarsh files verified. Do not promote partial file validation to all-site readiness. No external preprocessing/training/PBS receipt was inspected in this review.
4. WTB preprocessing completion, allocated GPU runtime, completed cloud fits, downstream decisions, all-seed coverage, paired bootstrap recomputation and final figures/manuscript reconciliation are UNKNOWN/NOT DONE. qstat R/H and submission IDs do not resolve them.
5. Runtime source manifests and per-run archives exist as implemented checks, but no complete cloud training evidence chain was available to audit. Source-package integrity does not prove future execution will finish or reproduce a scientific result.

Follow-up acceptance: preserve successful and failed deployment logs under unique names; finish/check the raw-receipt sidecar; inspect final remote raw-byte validation and per-stage exit/output receipts; retain every negative/interrupted result; keep the final raw/scientific gates failed until their actual requirements are met. No scientific PASS or complete-reproduction claim is issued.


### Metis deployment review follow-up — receipt sidecar and disclosed failed log

The preceding two packaging/log findings have been reconciled without changing source.zip:

- Independently opened `artifacts/metis_deployment_20261015_v3/raw_hash_origin_receipts_attempt3.zip`: 22,056 bytes, exactly four expected receipt members. Every member SHA-256 matches its expected_raw_hash_origin record in deployment.json. Sidecar SHA-256 is `5038151dbbf6f71433268a130f93c5722e80ce83b9fd9bf0b7be67c3c8d73285`; a read-only remote sha256sum command returned the same digest for metis_execution/raw_hash_origin_receipts_attempt3.zip. The portable raw-hash origin sidecar is therefore VERIFIED. Earlier 22-byte empty ZIPs remain retained failed packaging attempts, not evidence-bearing archives.
- `preflight_attempts.json` now expressly records v2 FAILED, missing-seaborn error as observed in prior tool response, and original pytest file overwritten by the v3 retry/not byte-preserved. This is an honest disclosure; the missing original raw failure log remains unavailable and is not retroactively certified. The same file identifies the two failed sidecar attempts and successful relative-path attempt3.
- Inspected submit_external_when_ready.py: it waits for external_raw_hash_verification.json with ALL_EXTERNAL_RAW_SHA256_PASS, times out as BLOCKED_STAGING_TIMEOUT, submits preparation then fit with afterok dependencies, and requires both external fits and WTB fits before external-transfer. All submission records remain SUBMITTED_NOT_EXECUTED with scientific_completion=false. Actual all-external-byte validation and external submission/execution are still UNKNOWN until their completed receipts are inspected.

The bounded deployment verdict remains PASS_WITH_BLOCKERS. Scientific/raw-replay completion remains FAIL / NOT COMPLETE; no training completion is inferred from the packaging repair or queue state.
