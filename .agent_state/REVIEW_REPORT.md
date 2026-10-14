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
