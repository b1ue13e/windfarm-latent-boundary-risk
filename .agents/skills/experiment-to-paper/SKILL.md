---
name: experiment-to-paper
description: Turn real experiment artifacts in a research repository into evidence-grounded analysis, figures/tables, and a publication-ready paper draft. Use when asked to analyze completed experiments, write an Experiments or Results section, build a claim-evidence map, diagnose missing experiments, or draft/revise an ML/AI/empirical paper from project results. Triggers include experiment to paper, write paper from results, analyze experiments, 实验写论文, 根据实验结果写论文, 从项目生成论文.
---

# Experiment to Paper

Convert completed research experiments into a defensible paper without inventing evidence.

## Non-negotiable contract

1. Treat repository artifacts as the source of truth for experimental claims.
2. Never invent runs, metrics, seeds, confidence intervals, p-values, baselines, citations, or implementation details.
3. Separate three epistemic states:
   - **Observed**: directly present in artifacts.
   - **Inferred**: computed or cautiously interpreted from observed artifacts.
   - **Proposed**: not yet executed; belongs in a gap list or future experiment plan, never in Results as completed work.
4. Every quantitative claim must trace to one or more concrete source files and, when practical, an exact row/key/run identifier.
5. Do not compare numbers that use incompatible datasets, splits, metrics, preprocessing, checkpoints, or evaluation protocols unless the incompatibility is explicitly disclosed.
6. Do not claim statistical significance unless repeated measurements support the test and the test is actually performed.
7. If evidence is missing or contradictory, stop that claim and record the gap. Do not repair the story by guessing.

Read `references/evidence-contract.md` before making substantive claims.

## Modes

Infer the lightest mode that satisfies the request.

- **audit** — inventory experiments, validate comparability, build evidence ledger, identify gaps; no full paper draft.
- **plan** — audit plus paper story, section plan, figure/table storyboard, and missing-experiment priorities.
- **write** — write requested sections from an existing or newly built evidence ledger.
- **review** — attack an existing draft for unsupported claims, weak comparisons, missing controls, inconsistency, and reviewer risk.
- **full** — audit → plan → figures/tables → draft → review → compile/check.

If the user names a mode, use it. Otherwise choose based on the requested outcome.

## Working directory

Resolve the research repository root from the user request or current workspace. Create `.experiment-to-paper/` only when persistent intermediate artifacts are useful.

Preferred working artifacts:

```text
.experiment-to-paper/
  project_profile.md
  experiment_inventory.json
  experiment_matrix.md
  evidence.jsonl
  claims_evidence.md
  paper_plan.md
  review_audit.md
  generated/
```

Do not overwrite original experiment outputs. Do not mutate training/evaluation code unless the user explicitly asks.

## Workflow

### 1. Inventory the repository

Locate, in priority order:

- README / project docs / experiment notes
- configs, launch scripts, seeds, data split definitions
- result tables: CSV/TSV/JSON/JSONL/XLSX
- logs and tracker exports
- checkpoints only when needed to identify runs
- plotting scripts and generated figures
- manuscript source: `.tex`, `.bib`, Markdown, DOCX source notes

If shell execution is available, run:

```bash
python <skill-dir>/scripts/scan_experiments.py <project-root> \
  --output <project-root>/.experiment-to-paper/experiment_inventory.json
```

Use the inventory as a map, not as evidence by itself. Open the actual relevant files.

### 2. Establish the experiment contract

Before interpreting results, determine:

- scientific question and claimed contribution
- task type and target variable
- datasets/domains and train/validation/test split
- baselines and variants
- metrics and whether higher/lower is better
- seed/repetition policy
- preprocessing and evaluation protocol
- primary versus diagnostic/secondary experiments

Write uncertainties into `project_profile.md`; do not silently infer them.

Read `references/experiment-analysis.md` for comparability and statistics rules.

### 3. Build the experiment matrix

Create `experiment_matrix.md` using `templates/experiment-matrix.md`.

One row should correspond to one scientifically comparable experiment family. Record:

- source artifact(s)
- dataset/split
- model/variant
- seed count
- metrics
- protocol/config hash or config path when available
- status: complete / partial / failed / ambiguous

Mark any apples-to-oranges comparison before calculating improvements.

### 4. Normalize evidence

For every candidate paper claim, create an entry in:

- `.experiment-to-paper/evidence.jsonl` using `templates/evidence-schema.md`
- `.experiment-to-paper/claims_evidence.md` using `templates/claims-evidence.md`

The machine-readable ledger is preferred for quantitative claims because it can be checked against CSV/TSV/JSON/JSONL sources.

When possible, validate it:

```bash
python <skill-dir>/scripts/validate_evidence.py \
  <project-root>/.experiment-to-paper/evidence.jsonl \
  --root <project-root>
```

A passing structural check does not prove a scientific claim; it only proves traceability and selected numeric consistency.

### 5. Analyze results conservatively

Compute only analyses justified by the artifacts:

- absolute and relative improvement
- ranking by dataset/condition
- robustness degradation curves
- efficiency/accuracy trade-offs
- mean, standard deviation, confidence intervals only when repeated runs exist
- effect sizes or hypothesis tests only when assumptions and sample structure support them

Always state the denominator for percentages. Prefer absolute differences when relative change is unstable or misleading.

Do not turn a single best seed into a general superiority claim.

### 6. Find the strongest defensible story

Rank claims by evidence strength, not novelty rhetoric.

A strong central story usually has:

1. a concrete problem/failure mode;
2. a method or intervention aimed at it;
3. a primary result under a fair comparison;
4. an ablation/mechanism result showing why the gain occurs;
5. a stress test, OOD test, efficiency test, or generalization result showing scope;
6. explicit limitations.

If the current experiments cannot support the intended story, produce a prioritized missing-experiment list instead of forcing the narrative.

### 7. Design tables and figures from questions

Every table/figure must answer one question.

Preferred roles:

- Main table: Does the method outperform credible baselines under the primary protocol?
- Ablation: Which component causes the gain?
- Robustness/OOD: Does the advantage persist under stress or distribution shift?
- Mechanism/diagnostic: Does the proposed explanation match measured behavior?
- Efficiency: What accuracy/latency/memory/energy trade-off is achieved?

Use existing plotting code when trustworthy. Otherwise create reproducible scripts in `.experiment-to-paper/generated/` and cite the underlying data artifact in captions or notes.

Read `references/paper-writing.md` before drafting.

### 8. Build the paper plan before prose

Create `paper_plan.md` from `templates/paper-plan.md`.

For each section specify:

- question answered;
- claims allowed;
- evidence IDs supporting those claims;
- figure/table dependencies;
- known limitations.

Draft in an evidence-first order:

1. Experimental setup
2. Results
3. Ablations / diagnostics
4. Method
5. Discussion / limitations
6. Introduction / contributions
7. Abstract
8. Conclusion

This ordering prevents the introduction from promising results the experiments do not support.

### 9. Write with claim locks

While drafting:

- attach each quantitative sentence to an evidence ID in working notes;
- use calibrated language: "improves", "is associated with", "suggests", "supports", not causal language unless design supports causality;
- distinguish benchmark performance from real-world utility;
- distinguish interpolation from extrapolation/OOD evidence;
- keep metric precision consistent with artifact precision;
- never add literature citations that have not been verified from an available bibliography or an explicitly permitted literature search.

After each section, compare every number and major claim back to the evidence ledger.

### 10. Reviewer attack

Run the checklist in `references/review-gates.md` and write `review_audit.md` using `templates/reviewer-audit.md`.

At minimum test:

- unsupported or overstated claims
- unfair baseline comparison
- missing strongest baseline
- split leakage / test-set tuning
- inconsistent preprocessing
- seed instability
- metric cherry-picking
- missing ablations
- mismatch between abstract, tables, and conclusion
- causality overclaim
- novelty overclaim
- hidden failed/negative results relevant to the conclusion

Classify issues as **Blocker**, **Major**, **Minor**, or **Style**.

### 11. Compile and verify when applicable

For LaTeX projects:

- preserve venue template and macros;
- compile with the project's existing command if documented;
- resolve missing refs/citations and obvious table overflow;
- do not rewrite working bibliography entries merely for style;
- verify that final PDF numbers match source tables.

If compilation tools are unavailable, report that limitation and still run textual consistency checks.

## Completion criteria

A `full` run is complete only when:

- experiment inventory exists or equivalent manual inventory was performed;
- experiment matrix distinguishes comparable from non-comparable runs;
- every major quantitative paper claim has traceable evidence;
- missing evidence is explicitly listed;
- paper plan maps claims to evidence;
- drafted sections do not exceed the evidence;
- reviewer audit has no unresolved Blocker caused by fabricated or untraceable evidence;
- generated tables/figures have identifiable source data.

## Output to the user

Report, concisely:

- strongest supported paper story;
- 3–7 major evidence-backed findings;
- critical missing experiments or integrity risks;
- files created/updated;
- whether the manuscript is **not ready**, **draft-ready**, or **submission-oriented draft**.

Never describe a draft as submission-ready solely because the prose is polished.
