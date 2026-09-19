---
name: science-skill
description: >-
  Use for Science main-journal AI/ML experiment hardening: experimental design,
  disruptive claim audit, mechanistic evidence, strong baselines, ablations,
  orthogonal validation, statistical audit, reproducibility, data/code/model
  openness, ethics/compliance, and reviewer attack mapping. Use when the user
  wants to make computational, benchmark, AI-for-science, or machine-learning
  experiments strong enough for Science core-journal review rather than merely
  top-conference or incremental publication.
---

# Science Skill

## Core Rule

Treat Science main-journal readiness as an evidence-chain problem, not a writing or packaging problem.

For AI/ML projects, do not reward benchmark theater. A Science-level computational paper must use experiments to support a broad scientific claim, mechanism, or field-level revision. If the current evidence only shows a model is slightly better on selected benchmarks, say so plainly and mark it as `No-Go` for Science main journal.

Never invent experiments, datasets, ethics approvals, accession numbers, citations, code repositories, raw-data availability, model weights, or robustness checks. Missing evidence is not a prose problem; mark it as a gap and propose the smallest decisive experiment that would close it.

## Required Intake

Before a full audit, gather or infer these items:

- Core claim and the old belief, limitation, or field debate it challenges.
- Current experiment table: datasets, splits, baselines, metrics, seeds, ablations, external validations, negative results.
- Data provenance, access terms, privacy/ethics constraints, and third-party data limitations.
- Model, training, hyperparameter, compute, and randomness protocol.
- Code/data/model/figure reproducibility state.
- Target narrative: Science main journal, Science family journal, or a different high-impact venue.

If key items are missing, still produce a provisional audit, but label all judgments as provisional.

## Output Contract

For experiment-audit tasks, output these four sections:

1. **Go / No-Go verdict**
   - `Go`: claim is broad, evidence is orthogonal, main alternatives are addressed, and reproducibility is credible.
   - `Conditional Go`: the idea has Science-level shape but decisive experiments are missing.
   - `No-Go`: evidence supports only an incremental, venue-specific, or benchmark-level claim.

2. **Evidence-chain matrix**
   - Map each major claim to current evidence, missing evidence, orthogonal validation, and likely reviewer objection.

3. **Must-do experiments**
   - Rank as `fatal`, `high-priority`, and `strengthening`.
   - Prefer decisive controls, external validation, mechanism tests, and leakage/overfitting audits over extra minor benchmarks.

4. **Reproducibility and compliance checklist**
   - Cover data, code, model weights, raw outputs, figure source data, environment, random seeds, licenses, privacy, ethics, and materials/data availability statements.

## Routing

Read only the reference files needed for the task:

- For Science main-journal threshold, broad impact, and mechanism versus incremental performance, read `references/science-main-journal-gate.md`.
- For AI/ML experiment hardening, baselines, data leakage, seed stability, OOD, ablations, and negative controls, read `references/ml-experiment-hardening.md`.
- For claim-to-evidence matrices and three-way orthogonal validation, read `references/orthogonal-evidence-chain.md`.
- For statistics, uncertainty, power-style planning, reproducibility packages, and official policy anchors, read `references/statistics-and-reproducibility.md`.
- For reviewer-risk triage and prioritized supplement experiments, read `references/reviewer-attack-map.md`.

## Science Main-Journal Defaults For AI/ML

Use these defaults unless the user provides a different venue or discipline:

- Reject single-run best-score claims.
- Reject weak or outdated baselines.
- Reject leaderboard-only narratives.
- Reject causal or mechanistic claims supported only by correlation or attention maps.
- Require train/validation/test isolation, time or domain holdouts when relevant, leakage checks, seed stability, and uncertainty intervals.
- Require at least one external validation setting for broad claims.
- Require mechanism, theory, intervention, or counterfactual evidence when the paper claims to change scientific understanding.
- Treat open reproducibility as part of the experiment, not an afterthought.

## Policy Discipline

Separate:

- **Official policy requirements**: Science/AAAS author instructions, editorial policies, data/material/code availability, ethics, and reproducibility language.
- **Science-level best practice**: hostile-reviewer controls, orthogonal validation, mechanism depth, negative controls, and external stress tests.

Do not describe a best-practice recommendation as an official Science rule unless it is verified from an official source.

## Relationship To Other Skills

- Use this skill for experiment design and evidence hardening.
- Use `paper-ai-detox` later for prose, research-thin diagnosis, and reviewer-facing tone.
- Use `academic-research-suite` for broad literature, citation, venue, and manuscript workflow.
- Use project-specific skills, such as `nature-skill`, for domain framing; this skill should not overwrite project-specific policy logic.
