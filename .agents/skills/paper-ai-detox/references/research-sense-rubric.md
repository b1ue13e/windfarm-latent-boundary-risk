# Research-Sense Rubric

Use this rubric when the manuscript problem goes beyond style. The goal is to restore the labor a real paper must perform: ask a real question, support it with hard evidence, and make visible author judgment.

## 1. Surface Language

Red flags:

- Excessive hedging: "可能", "或许", "一定程度上", "似乎", "往往", "may", "might", "to some extent" when the evidence already supports a bounded claim.
- Defensive transitions: "值得注意的是", "需要指出的是", "不可否认的是", "必须强调的是", "it is worth noting" used as padding.
- Fake dialectics: "不是 A，而是 B", "not merely X but Y", "rather than A, it is B" when A is a straw target.
- Syntactic overload: one sentence carries the claim, caveat, method, implication, and background.
- Report tone: encyclopedic listing instead of a problem-driven argument.
- Paragraph homogeneity: every paragraph is the same length and weight.
- Mechanical ordering: "first, second, third" or "宏观/微观/理论/实践" used to create format rather than logic.
- Empty endings: "具有重要理论意义和实践价值", "provides new insights", "offers reference" without a specific claim.

What good revision does:

- State the claim directly.
- Keep only necessary qualifiers.
- Vary paragraph length according to emphasis.
- Let transitions express a real logical turn: contradiction, narrowing, consequence, limitation, or evidence shift.

## 2. Argument Architecture

Red flags:

- The research question is a topic, not a puzzle.
- The introduction lacks a concrete contradiction, anomaly, or unresolved dispute.
- The literature review lists authors without showing what they fought over.
- Foundational theories and marginal comments receive the same weight.
- The paper balances weak counterarguments long after the evidence has settled them.
- The theory framework and empirical material run in parallel: concepts never land on cases, variables, or observations.
- The conclusion repeats the structure instead of stating what has been learned.
- The author never judges: no claim is preferred, rejected, narrowed, or revised.

What good revision does:

- Reframe the opening around a live tension: inconsistent findings, failed measurement, neglected sample, anomalous case, or method gap.
- Turn literature review into a battlefield: origin, dispute, methodological shift, unresolved weakness, and this paper's position.
- Make the central claim risky but bounded: it should be clear what evidence would weaken it.
- Let evidence change the theory, not merely illustrate it.

## 3. Research Design And Evidence

Red flags:

- Topic is large, method is weak, conclusion is full.
- Research question and method do not match.
- Concepts are directly equated with variables: "innovation capability" becomes "patent count" without justification.
- Mechanisms are decorative stories, not testable pathways.
- Causal verbs appear without a credible identification strategy.
- Correlational results are written as "promotes", "causes", "leads to", "drives", or "determines".
- Non-significant results are spun as support because the coefficient direction "meets expectations".
- Results are too smooth: every robustness test, heterogeneity result, and mechanism aligns perfectly.
- Data source, cleaning, winsorization, matching, missingness, and sample attrition are vague.
- Policy suggestions are detached from the actual findings.
- Reproducibility details are absent: code, random seed, split, hyperparameters, feature processing, leakage checks, baselines, metrics.

What good revision does:

- Match claim strength to design strength.
- Specify variables, proxies, known biases, alternatives, and why the chosen operationalization fits the concept.
- Attach every mechanism to a measurable intermediate or concrete qualitative trace.
- Treat non-significance honestly: evidence is insufficient unless additional analysis supports interpretation.
- Report messy evidence with discipline: weakened coefficients, failed mechanisms, subgroup differences, and plausible alternative explanations.
- Make recommendations traceable to findings.

## 4. Epistemology And Discipline Norms

Red flags:

- Citation hallucination: invented papers, wrong years, wrong journals, wrong conclusions, or real authors attached to unsupported claims.
- Knowledge is flattened: core disputes and side notes receive equal attention.
- Historical sense is missing: theories are listed without the controversy that produced them.
- Importance judgment fails: the paper cannot tell readers which sources must be answered and which can be footnotes.
- The tone is eternally calm, even when a method is flawed, a puzzle is surprising, or a finding matters.
- The paper ignores discipline-specific rules:
  - Economics: identification, endogeneity, mechanisms, robustness, and scope.
  - Management: theory contribution, construct validity, mechanisms, boundary conditions.
  - Sociology: problem consciousness, empirical texture, positionality where relevant, alternative explanations.
  - History: source criticism, chronology, archive limits, historiographical dispute.
  - Psychology: validity threats, measurement, power, preregistration where relevant.
  - Computer science: task definition, baselines, ablations, reproducibility, leakage, metric fit.
- Advanced methods are used as decoration: DID without a policy shock, IV without exogeneity, ML without task logic, PSM without selection reasoning.
- Failure costs are invisible: every method choice is described only by its advantages.

What good revision does:

- Verify every citation before relying on it.
- Name the discipline's hidden rule and evaluate the draft against it.
- Make tradeoffs explicit: sample representativeness, proxy limits, identification limits, interpretability, external validity, and data quality.
- Restore author judgment: say which claim is stronger, which measure is flawed, which result should not be overread, and what remains unresolved.

## Severity Guide

- Critical: fabricated or unverified citations presented as facts; causal claims unsupported by design; theory and evidence disconnected; methods cannot answer the research question.
- High: vague variables, decorative mechanisms, hollow contribution, missing data provenance, mishandled non-significance, flattened literature dispute.
- Medium: hedging overload, defensive cliches, report tone, long overloaded sentences, paragraph homogeneity, mechanical lists.
- Low: local phrasing, minor repetition, transition cleanup, rhythm polish.
