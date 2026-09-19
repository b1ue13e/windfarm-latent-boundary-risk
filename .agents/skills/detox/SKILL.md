---
name: detox
description: Diagnose and rewrite academic prose to remove AI flavor and restore research depth (学术论文去AI味与学术质感重构).
---

# Paper AI Detox

## Core Rule

Treat "AI flavor" as a research-quality problem, not a synonym problem. Revise only after identifying whether the weakness sits in surface prose, argument architecture, research design, evidence integrity, citation reliability, or discipline norms.

Never invent citations, datasets, results, fieldwork details, quotes, model diagnostics, or robustness checks. If a literature claim or empirical detail is not supplied or verified, mark it as needing verification instead of fabricating support.

## Workflow

1. **Triage the task**
   - If the user asks for diagnosis, produce a compact risk report before rewriting.
   - If the user asks for polishing, still run a brief internal diagnosis and target the highest-risk patterns.
   - If the user gives a full manuscript or long section, scan the local file when available with `scripts/scan_ai_style.py`, then combine the scan with substantive judgment.

2. **Diagnose in four layers**
   - Surface: hedging overload, defensive transitions, "not A but B" templates, long overloaded sentences, report tone, uniform paragraphs, mechanical lists, hollow conclusions.
   - Argument: weak problem consciousness, fake balance, no literature battlefield, no authorial judgment, theory and evidence not touching.
   - Research design: question-method mismatch, vague variable operationization, causal verbs without identification, mechanisms without measurable intermediates, over-smooth result interpretation, mishandled non-significance.
   - Epistemology: citation hallucination risk, discipline-specific norm violations, flattened importance judgments, missing failure-cost awareness, lack of reproducibility detail.

   Load `references/research-sense-rubric.md` when performing a manuscript critique, reviewer-risk audit, research-design detox, literature-review repair, or claim-support assessment.

3. **Revise in passes**
   - Pass 1: cut empty AI prose without weakening valid caution.
   - Pass 2: replace templates with direct claims and concrete logical movement.
   - Pass 3: sharpen the research question, dispute, mechanism, contribution, and boundary conditions.
   - Pass 4: reconnect theory, evidence, variables, methods, results, and conclusion.
   - Pass 5: produce a reviewer-facing risk checklist when the revision touches claims, methods, citations, data, or contribution.

   Load `references/rewrite-playbook.md` for paragraph-level rewriting, anti-template edits, Chinese or English academic prose repair, and before/after examples.

4. **Output usefully**
   - For diagnosis: group findings by severity, cite paragraph or line references when available, and separate surface issues from research-design risks.
   - For rewrites: provide the revised passage first, then a short explanation of high-impact edits.
   - For full-paper repair: include a revision roadmap with concrete tasks, not generic advice.
   - For citations: say which claims require source verification; do not supply made-up author-year support.

## Scanner

Use the scanner for quick pattern detection:

```bash
python C:\Users\lidong\.gemini\config\skills\paper-ai-detox\scripts\scan_ai_style.py path\to\paper.md
```

It supports `.txt`, `.md`, `.tex`, and `-` for standard input. Treat the output as a signal, not a verdict; the final judgment must consider discipline, genre, and evidence.

## Revision Standards

- Preserve necessary epistemic caution when evidence is correlational, exploratory, qualitative, preliminary, or contested.
- Remove hedging when the manuscript has direct evidence and the claim scope is already bounded.
- Use causal language only when the design supports it; otherwise use association language.
- Replace empty "theoretical and practical significance" with the exact assumption revised, audience affected, mechanism clarified, or boundary established.
- Make literature reviews stage a dispute: who changed the question, who changed the method, who was later challenged, and where the current paper stands.
- Add empirical texture only from supplied material: dataset construction, sample changes, field notes, interview fragments, anomalies, diagnostics, robustness failures, or concrete case anchors.
