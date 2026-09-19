# Rewrite Playbook

Use this playbook for paragraph-level repair. Do not make prose merely "more polished"; make it more accountable.

## Default Revision Moves

- Replace vague caution with bounded assertion.
  - Weak: "这一结果在一定程度上可能说明数字金融对创新具有促进作用。"
  - Stronger: "在控制企业和年份固定效应后，数字金融指数与专利申请量正相关。该结果支持融资可得性路径，但还不足以证明因果效应。"

- Replace fake dialectics with direct claims.
  - Weak: "这并非简单的技术问题，而是复杂的治理问题。"
  - Stronger: "平台治理的核心困难在于激励结构，而不是技术部署。"

- Replace defensive transitions with logical turns.
  - Weak: "值得注意的是，现有研究已经取得丰富成果，但仍存在不足。"
  - Stronger: "现有研究的分歧集中在识别策略：横截面研究发现正相关，准实验研究则显示效果依赖政策窗口。"

- Replace hollow contribution with a specific contribution.
  - Weak: "本文丰富了相关研究，并具有重要的理论意义和实践价值。"
  - Stronger: "本文将数字金融的作用边界缩小到融资约束较强的民营企业，说明既有全样本结论高估了政策的普遍性。"

- Replace list logic with argumentative sequence.
  - Weak: "这一现象可以从三个维度理解。首先...其次...最后..."
  - Stronger: "最先变化的不是企业创新投入，而是融资约束。只有当现金流压力下降后，研发投入才开始增加。"

## Chinese Academic Prose Rules

- Cut default-suspect phrases unless they perform real work: "值得注意的是", "需要指出的是", "不可否认的是", "必须强调的是", "基于此", "有鉴于此", "综上所述", "从宏观层面看", "从微观层面看".
- Do not open every paragraph with "关于 X", "现有研究主要从", "本文试图回答".
- Avoid "何以可能" unless the draft first proves why the phenomenon is theoretically difficult.
- Avoid "不是...而是..." unless the rejected view is real, plausible, and worth refuting.
- Keep most Chinese sentences under 35 characters when revising dense prose. Longer sentences are acceptable only when syntax remains transparent.
- Use short paragraphs for sharp claims, longer paragraphs for evidence and reasoning.
- Keep terms only when they earn their place. If "场域", "话语", "范式", "机制", or "表征" can be replaced by a concrete actor, variable, process, or evidence trace, replace it.

## English Academic Prose Rules

- Cut default-suspect phrases: "it is worth noting", "it should be emphasized", "to some extent", "in a certain sense", "arguably", "not merely X but Y", "provides new insights".
- Prefer claim-first sentences.
  - Weak: "This study may, to some extent, contribute to the literature on..."
  - Stronger: "This study revises the literature on X by showing that Y holds only under Z."
- Use "associated with" or "correlates with" for observational evidence unless identification supports causality.
- Keep sentences under 25 words when the passage is conceptually dense.
- Replace broad contribution verbs with exact actions: revises, tests, rejects, narrows, extends, measures, identifies, falsifies, bounds.

## Evidence Texture

Add concrete texture only from supplied material:

- Quantitative: data vendor, period, sample filters, final sample size, matching method, winsorization, missingness, attrition, model specification, fixed effects, standard errors, robustness tests, failed checks.
- Qualitative: field site, date, actor, interview role, observation detail, document source, quote, coding choice, negative case.
- Computational: dataset split, preprocessing, feature construction, baseline, random seed, hyperparameters, ablation, leakage check, metric rationale.

Do not invent texture. If the needed detail is absent, write a placeholder such as "[补充数据清洗口径]" or state that the claim requires source verification.

## Claim Strength Ladder

Use claim strength that matches evidence:

- Descriptive evidence: "shows", "documents", "reveals", "indicates".
- Correlational evidence: "is associated with", "correlates with", "has a positive relationship with".
- Quasi-experimental evidence: "supports a causal interpretation", "is consistent with an effect", then name assumptions.
- Strong identification or experiment: "causes", "increases", "reduces", but still state scope and assumptions.

## Literature Review Repair

Convert author lists into disputes:

- Who opened the question?
- Who changed the method or measurement?
- Which conclusion was later challenged?
- Which proxy, sample, or identification strategy remains weak?
- Where does this paper stand in that dispute?

Bad: "Zhang (2020) argues..., Li (2021) finds..., Wang (2022) notes..."

Better: "The dispute is not whether digital finance matters, but where its effect enters the innovation process. Cross-sectional studies treat financing constraints as the channel, while later panel designs show that the channel disappears after firm fixed effects. This paper tests that unresolved step directly."

## Reviewer-Risk Checklist

After revising a substantial section, check:

- Is the question a real puzzle rather than a broad topic?
- Does the method answer the question?
- Are variables justified as proxies, with known limits?
- Are causal verbs licensed by the design?
- Are mechanisms empirically testable?
- Are non-significant or messy results handled honestly?
- Are all citations real and accurately represented?
- Does the conclusion say something specific that follows from the evidence?
- Does the prose sound like an author making judgments, not a system arranging information?
