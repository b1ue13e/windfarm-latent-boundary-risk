# Mimir Import Plan: E:\论文3 SCADA Latent-Boundary Project

**Generated:** 2026-10-12T22:30:00+08:00  
**Target:** DSH Mimir research wiki @ `%DSH_HOME%\storages\research_wiki.json`  
**Existing stub project ID:** `92ef8db3-9dbc-44f7-b900-5b9b888df563`

---

## Phase 0: Pre-Import Forensics (READ ONLY)

### Evidence verified

✅ **research-manifest.json exists** — 3 experiments (E01 external farm, E02 zero-privileged, E03 async), 2 hypotheses, structured loop  
✅ **docs/SCIENTIFIC_CONTRACT.md locked** — claim ceiling defined, Q1/Q2/Q3 boundaries explicit  
✅ **docs/EXPERIMENT_REGISTRY.md** — EXP-01, EXP-02, EXP-03 preregistered with frozen protocols  
✅ **38 versioned artifacts** in `artifacts/ARTIFACT_MANIFEST.json` with SHA256 provenance  
✅ **Git tag `tste-submission-v1.0`** — immutable baseline at 2026-09-23  
✅ **Verification gate passes** — `python scripts/verify_replication.py` exit 0 (19/19 claims)  
✅ **Clean external reproducibility** — confirmed in `docs/EXTERNAL_REPRODUCIBILITY_VERDICT.md`

### Current Mimir state

- **Workspace binding:** `E:\论文3` not in `workspace.json` — needs registration  
- **Stub project:** `92ef8db3-9dbc-44f7-b900-5b9b888df563` exists (title: "风电场备用筛查", stage: idea, 6 figures from standalone_ieee_package/, no research question)  
- **Related projects imported:** `E:\论文1` (fa22474e..., stage: done, outcome: supported) shows the import convention  
- **Import pattern:** other projects use `.agent_state/mimir_import/{RESEARCH_STATE.yaml, IMPORT_MANIFEST.json, IMPORT_LOG.md}`

### Decision: MERGE INTO EXISTING STUB vs CREATE NEW

**MERGE** into `92ef8db3...` because:
1. Same title domain (风电场/SCADA)
2. 6 figures already linked (standalone_ieee_package/figures/)
3. Mimir dedup by title would block a second creation
4. Preserves historical figure references

Action: **UPDATE** existing `92ef8db3-9dbc-44f7-b900-5b9b888df563`.

---

## Phase 1: Project Metadata Reconstruction

### Source documents

| Evidence | Status | Value |
|---|---|---|
| `research-manifest.json:project.title` | VERIFIED | "跨风电场备用筛查的时空图迁移与局部条件基线决策增益评估" |
| `research-manifest.json:question.text` | VERIFIED | "在外部风场上，去除时空图交互的局部风速分箱基线是否同样足以完成备用筛查？跨场站迁移表示相较于该局部条件基准是否依然缺乏决策增益？" |
| `docs/SCIENTIFIC_CONTRACT.md:§1` | VERIFIED | "Under the same arrival-time deployment information set, when the MPPT-to-active-pitch control boundary is no longer directly observable because pitch is delayed or withheld, can already-arrived SCADA consequence signals recover useful boundary information, and does that recovered information provide incremental decision value for asymmetric reserve-risk allocation beyond strong direct conditional-quantile baselines?" |
| `paper_tste_ieee.md` (main manuscript) | VERIFIED | IEEE TSTE 10.0-page submission, 2026-09-23 freeze |
| `README.md` | VERIFIED | Public GitHub repo `b1ue13e/windfarm-latent-boundary-risk` at tag `tste-submission-v1.0` |

### Stage determination

**Source of truth:** `docs/EXPERIMENT_REGISTRY.md` status + `docs/SCIENTIFIC_CONTRACT.md` claim ledger + manuscript state

| Stage | Evidence | Verdict |
|---|---|---|
| Literature Review | `references.bib` (40 entries), `docs/TSTE_SUBMISSION_DESK_REJECT_AUDIT_20260921.md` positioned against Zhao et al. (IJEPES 2026) | ✅ **PASSED** |
| Baseline Selection | `docs/STRONG_BASELINE_CLOSURE.md`, Policy A/B/C/D frozen in `docs/MATCHED_BUDGET_DECISIVE_REPORT.md` | ✅ **PASSED** |
| Baseline Reproduction | `artifacts/baseline_reproduction.csv` (B0-B5 direct quantiles), validation-calibrated frontier | ✅ **PASSED** |
| Idea Exploration | Hypotheses H1/H2 in `research-manifest.json`, both tested | ✅ **PASSED** |
| Research Contract | EXP-01/02/03 preregistered in `docs/EXPERIMENT_REGISTRY.md` with frozen protocols | ✅ **PASSED** |
| Implementation & Experiments | All 3 experiments CONCLUDED, artifacts archived and verified | ✅ **PASSED** |
| Results Analysis | `docs/EXP01_EXTERNAL_MATCHED_CONTROL_REPORT.md`, `docs/ZERO_PRIVILEGED_SUPERVISION_REPORT.md`, `docs/EXP03_ASYNCHRONOUS_REPORT.md` | ✅ **PASSED** |
| Paper Writing | `paper_tste_ieee.pdf` compiled to exact 10.0 pages, ScholarOne freeze package at `artifacts/tste_submission_freeze_20260923.zip` | ✅ **PASSED** |

**Recommended Mimir stage:** `paper-writing` (manuscript complete, under external review preparation)  
**Research outcome:** `supported` (H1 supported: local wspd-bins minimum sufficient; H2 refuted: zero-privileged failed)

---

## Phase 2: Eight-Stage Gate Evidence Map

### Stage 1: Literature Review

**Acceptance:**
- ✅ 40 BibTeX entries in `references.bib`
- ✅ Positioned against Zhao et al. (IJEPES 2026) in Related Work
- ✅ Gap identified: "existing work compares against unconditioned global quantiles, not matched-information local baselines"

**Artifacts to link:**
- `references.bib`
- `docs/FIRST_PRINCIPLES_ADVERSARIAL_AUDIT_20260921.md`
- `docs/TSTE_SUBMISSION_DESK_REJECT_AUDIT_20260921.md`

### Stage 2: Baseline Selection

**Acceptance:**
- ✅ 6 direct quantile baselines (B0-B5) defined in `docs/REPOSITORY_EVIDENCE_MAP.md`
- ✅ Site-Local Wspd-Bins (10-bin) selected as primary challenger
- ✅ No-Graph architectural control registered

**Artifacts:**
- `docs/STRONG_BASELINE_CLOSURE.md`
- `artifacts/direct_quantile_baselines_summary.csv`

### Stage 3: Baseline Reproduction

**Acceptance:**
- ✅ B0-B5 reproduced on WTB primary site
- ✅ Validation-calibrated frontier established in `docs/MATCHED_BUDGET_DECISIVE_REPORT.md`

**Artifacts:**
- `artifacts/baseline_reproduction.csv`
- `artifacts/matched_budget/validation_calibrated_frontier.csv`

### Stage 4: Idea Exploration

**Acceptance:**
- ✅ H1: External-farm matched control (EXP-01)
- ✅ H2: Zero-privileged supervision (EXP-02)

**Artifacts:**
- `research-manifest.json:hypotheses[]`

### Stage 5: Research Contract

**Acceptance:**
- ✅ EXP-01 frozen protocol: dual-farm (Penmanshiel 14-turbine, Kelmarsh 6-turbine), h=1/6, 5 seeds, B=2000 bootstrap
- ✅ EXP-02 frozen protocol: proxy label circularity resolved, 6 protocol corrections, eps sensitivity {20,50,100} kW
- ✅ EXP-03 frozen protocol: 7-delay envelope tau in {0,1,2,3,4,5,6}, causal LOCF buffer

**Artifacts:**
- `docs/EXPERIMENT_REGISTRY.md` (lines 97-270: EXP-01, EXP-02, EXP-03)
- `docs/TSTE_OPERATIONAL_RELEVANCE_PREREGISTRATION.md`

### Stage 6: Implementation & Experiments

**Acceptance:**
- ✅ EXP-01 executed on Metis A100, v2 corrected with independent frozen forecasts
- ✅ EXP-02 executed on Metis A100, falsification guardrail enforced
- ✅ EXP-03 executed on Metis A100, critical crossover tau*=1 (h=1), tau*=0 (h=6)

**Artifacts:**
- `artifacts/external_matched_control_benchmark.csv` (v2, SHA256: `596f46e0...`)
- `artifacts/zero_privileged_supervision_benchmark.csv` (v1, SHA256 in artifact registry)
- `artifacts/exp03_async/psrei_vs_delay.csv` (v2, trace SHA256: `d1619efc...`)

### Stage 7: Results Analysis

**Acceptance:**
- ✅ H1 verdict: Penmanshiel h=6 Delta PSREI = +5.322M kWh (p=0.0025, significant cost penalty); Kelmarsh h=6 Delta PSREI = +435.7k kWh (p=0.1961, non-significant) → **Site-Local Wspd-Bins is minimum sufficient**
- ✅ H2 verdict: h=1 Delta PSREI = -365.9k kWh (p=0.880); h=6 Delta PSREI = +3435.5k kWh (p=0.484) → **Zero-privileged challenger failed**
- ✅ EXP-03 verdict: tau*=1 for h=1, tau*=0 for h=6 → **No hedge against telemetry latency**

**Artifacts:**
- `docs/EXP01_EXTERNAL_MATCHED_CONTROL_REPORT.md`
- `docs/ZERO_PRIVILEGED_SUPERVISION_REPORT.md`
- `docs/EXP03_ASYNCHRONOUS_REPORT.md`
- `docs/MATCHED_BUDGET_DECISIVE_REPORT.md` (falsified reserve allocation advantage, Case C/D)

### Stage 8: Paper Writing

**Acceptance:**
- ✅ Main manuscript: `paper_tste_ieee.pdf` (10.0 pages exactly, 0 overfull hboxes)
- ✅ Supplementary: `paper_tste_supplementary.pdf` (44 pages)
- ✅ ScholarOne freeze: `artifacts/tste_submission_freeze_20260923_pes_compliant.zip`
- ✅ All verification gates pass: `python scripts/verify_gate.py` exit 0

**Artifacts:**
- `paper_tste_ieee.pdf` (build/)
- `paper_tste_supplementary.pdf` (build/)
- `standalone_ieee_package/main.pdf` (independent compile)
- Cover letter, highlights, AI disclosure

---

## Phase 3: Paper & Literature Import

### Papers to ingest (top 12, relevance-ranked)

| arXiv ID / DOI | Title (abbreviated) | Role | Relevance |
|---|---|---|---|
| 2208.04360 | SDWPF Benchmark Dataset | foundational | 10/10 — primary data source |
| (IJEPES 2026) | Zhao et al. spatio-temporal quantiles | mainstream | 9/10 — architecture conceded, scope differentiated |
| (add 10 more from references.bib, roles: foundational / mainstream / failing / adjacent) | ... | ... | ... |

**Action:** Call `wiki_note` `add_paper` for each, with project linkage.

### Failed ideas to preserve

- "MoE routing improves decision value" — REFUTED (p=0.380, dense/routed parity)
- "Posterior conditioning reduces plant-wide PSREI vs wind-speed bins" — REFUTED by matched-budget closure (Case C/D verdict)

---

## Phase 4: Experiment & Claim Import

### Experiments

| ID | Name | Hypothesis | Status | Verdict | Provenance |
|---|---|---|---|---|---|
| E01 | External-farm matched control | H1 | concluded | H1 supported | `artifacts/external_matched_control_benchmark.csv` v2 |
| E02 | Zero-privileged supervision | H2 | concluded | H2 refuted | `artifacts/zero_privileged_supervision_benchmark.csv` v1 |
| E03 | Async telemetry envelope | (exploratory) | concluded | no hedge found | `artifacts/exp03_async/` v2 |

**Action:** Call `wiki_note` `add_experiment` for each, link to hypothesis and artifacts.

### Claims (headline numbers from manuscript)

| Claim | Status | Evidence |
|---|---|---|
| "Site-Local Wspd-Bins minimum sufficient on Penmanshiel" | supported | EXP-01 v2, Penmanshiel h=6 Delta PSREI = +5.322M kWh, p=0.0025 |
| "Posterior is transition-localized risk hedging, not cost optimizer" | supported | `docs/MATCHED_BUDGET_DECISIVE_REPORT.md`, Case C/D, AUC difference CI excludes zero |
| "Active-power signature dominates boundary recovery" | supported | `docs/ACTIVE_POWER_IDENTIFIABILITY_AUDIT.md`, C2 AUROC 0.988 |
| "Zero-privileged challenger failed to beat Wspd-Bins" | supported | EXP-02, h=1 p=0.880, h=6 p=0.484 |

**Action:** Call `wiki_note` `add_claim` for each, link to experiment via `supports` edge.

---

## Phase 5: Figure Import

### 6 figures already linked to stub project

- `standalone_ieee_package/figures/figure1_decision_boundaries.pdf`
- `standalone_ieee_package/figures/figure2_data_boundary.pdf`
- `standalone_ieee_package/figures/figure3_summary_results.pdf`
- `standalone_ieee_package/figures/figure4_routing_evidence.pdf`
- `standalone_ieee_package/figures/figure5_case_studies.pdf`
- `standalone_ieee_package/figures/figure6_ablation_tradeoff.pdf`

**Action:** Verify captions match manuscript, link to experiments via `figure_save` equivalent or manual `evidenceReferences` update.

---

## Phase 6: Stage Progress Update

**For each of 8 stages:**

1. Update `research_stages` table entry with:
   - `acceptanceCriteria[].status` → `passed` where evidence exists
   - `acceptanceCriteria[].evidenceReferences[]` → link to actual artifacts
   - `gateDecision` → `approved` if all criteria passed

2. Update project `currentStageId` → `92ef8db3...:paper-writing`

3. Update project `researchOutcome` → `supported`

---

## Phase 7: Import Log & Manifest

**Create `.agent_state/mimir_import/` directory with:**

1. `RESEARCH_STATE.yaml` — canonical state snapshot (question, gap, hypotheses, experiments, claims, stage verdicts)
2. `IMPORT_MANIFEST.json` — file-by-file import record with timestamps, SHA256, target Mimir IDs
3. `IMPORT_LOG.md` — append-only audit trail

**Example structure (from E:\论文1):**

```yaml
# RESEARCH_STATE.yaml
project:
  id: 92ef8db3-9dbc-44f7-b900-5b9b888df563
  title: "跨风电场备用筛查的时空图迁移与局部条件基线决策增益评估"
  research_question: "..."
  current_stage: paper-writing
  outcome: supported
hypotheses:
  - id: H1
    text: "..."
    status: supported
    tested_by: [E01]
experiments:
  - id: E01
    name: "EXP-01: 外部场站相同信息集配对直接条件分位数对照"
    status: concluded
    verdict: "H1 supported"
    artifacts:
      - path: artifacts/external_matched_control_benchmark.csv
        version: v2
        sha256: 596f46e0be8d71ab7a9965dbe4c481cc717b31c083fe288441a9ca9a39c3966e
claims:
  - text: "Site-Local Wspd-Bins minimum sufficient on Penmanshiel"
    status: supported
    evidence: [E01]
```

---

## Phase 8: Verification & Rollback Plan

### Post-import verification checklist

- [ ] `wiki_note` `list table=projects` returns updated `92ef8db3...` with correct title, question, stage, outcome
- [ ] `wiki_note` `list table=experiments` returns E01, E02, E03 with correct status and links
- [ ] `wiki_note` `list table=claims` returns 4+ headline claims with `supported` status
- [ ] `wiki_note` `list table=papers` includes SDWPF benchmark and Zhao et al.
- [ ] Stage gate `paper-writing` shows all acceptance criteria with `evidenceReferences` populated
- [ ] Refresh Mimir GUI → project appears with 8 stages, correct progress bars, linked figures

### Rollback procedure

If verification fails:
1. Restore `%DSH_HOME%\storages\research_wiki.json` from pre-import backup (Phase 0)
2. Delete `.agent_state/mimir_import/` directory
3. Document failure reason in `.agent_state/IMPORT_FAILURE_LOG.md`

### No-ops (idempotent safety)

- Paper already in wiki → skip ingest (check by arXiv ID / title slug)
- Experiment already exists → update metrics only if `--update-on-exist`
- Claim already exists → add edge only if not already present

---

## Phase 9: Final Report Generation

**Output:** `docs/MIMIR_IMPORT_REPORT_20261012.md` with:

1. **Import summary:** X projects updated, Y papers added, Z experiments linked, W claims registered
2. **Stage progress table:** 8 stages × acceptance criteria pass/fail
3. **Evidence gaps:** list any missing evidence or UNKNOWN status items
4. **Next actions:** top 3 research tasks based on stage blockers
5. **Verification commands:** exact `wiki_note` queries to confirm import

---

## Execution Order (Next Steps)

1. ✅ Backup `research_wiki.json` → `storages/backup_before_scada_import_20261012/`
2. ⏸ READ research-manifest.json, SCIENTIFIC_CONTRACT.md, EXPERIMENT_REGISTRY.md in detail
3. ⏸ Map 8 stages → acceptance criteria → evidence artifacts
4. ⏸ Call `wiki_note` operations to update project, ingest papers, add experiments, add claims
5. ⏸ Update stage gates with evidenceReferences
6. ⏸ Write `.agent_state/mimir_import/` manifest files
7. ⏸ Re-read `research_wiki.json` and verify all updates landed
8. ⏸ Generate final import report
9. ⏸ Present to user with verification commands

---

**STATUS:** Plan complete. Ready for execution approval.
