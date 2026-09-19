---
name: nature-skill
description: Use when working on Eco-Yangtze-Env, Yangtze River ecological compensation, CEC-MARL, counterfactual watershed governance, Nature Sustainability/Global Environmental Change/Water Research manuscript strategy, experiment design, data-roadmap planning, literature gaps, paper abstracts, figures, baselines, or implementation choices that must align with the project's final top-journal goal.
---

# Nature Skill

## Core Rule

Align every Eco-Yangtze-Env decision with this final target:

> Use multi-agent counterfactual learning to redefine watershed ecological compensation: move from paying by observed section-water-quality outcomes to pricing cross-period, cross-region marginal ecological contributions.

Do not let the work become an algorithm showcase. Make it a policy mechanism discovery and validation project with real data, interpretable counterfactuals, strong baselines, and stress-tested governance implications.

## Always Reframe The Project

Use this framing before writing code, text, plans, or experiments:

- Main problem: How can long-term, spatially externalized, not directly observable ecological contributions be fairly priced in cross-regional watershed governance?
- Main mechanism: CEC-MARL, Counterfactual Ecological Compensation Multi-Agent Reinforcement Learning.
- Main empirical case: Yangtze River mainstem provinces: Qinghai, Tibet, Sichuan, Yunnan, Chongqing, Hubei, Hunan, Jiangxi, Anhui, Jiangsu, Shanghai.
- Main policy anchor: China's 2025 cross-provincial ecological protection compensation policy window for the Yangtze and Yellow River mainstems.
- Main water-quality policy weights: CODMn, NH3N, TP at 30%, 30%, 40%.

Use `ADDICT-V` only as an internal legacy codename. In outward-facing writing, translate it into sober top-journal language:

- counterfactual credit assignment
- delayed ecological benefit replay
- risk-sensitive distributional evaluation
- adaptive target setting
- spatial-temporal attention over upstream-downstream dependencies

## Decision Priority

When choosing what to do next, use this order:

1. Data.
2. Counterfactual contribution evidence.
3. Current-rule and non-RL baselines.
4. MARL implementation.
5. Top-journal packaging.

If a user asks for MARL before the data and current-rule baseline are credible, keep implementation scoped and remind them that the paper stands or falls on the evidence chain, not algorithmic complexity.

## Core Contributions

Keep the contribution set narrow.

First: counterfactual ecological contribution pricing.

Estimate what basin-level water quality, economic welfare, and distributional equity would be if one province's action changed while other provinces remained fixed. Use this difference as the province's marginal ecological contribution.

Second: delayed ecological benefit replay.

Handle short-term economic costs and delayed water-quality gains by relabeling or prioritizing trajectories where long-run ecological benefits appear after earlier governance investment.

Third: risk-sensitive compensation.

Use distributional evaluation and CVaR-style metrics to test whether compensation mechanisms reduce tail risks under drought, fiscal stress, industrial shocks, monitoring noise, pollution accidents, or manipulation.

Avoid adding extra main contributions unless the user explicitly asks for a broader architecture.

## Required Baselines And Tests

For experiments, push toward these groups:

- Historical backtesting of the watershed simulator.
- Current section-water-quality accounting rule versus counterfactual compensation.
- No compensation, fixed compensation, current-rule compensation, system dynamics or evolutionary game baseline, basic MARL, COMA-style MARL, and full CEC-MARL.
- Delayed benefit replay ablation.
- Upstream-downstream credit assignment scenario.
- Extreme shock pressure tests.
- Reward hacking or monitoring manipulation tests.
- Cross-basin transfer validation, preferably Yangtze to Yellow River, or Yangtze main experiment plus Xin'an River/Yellow River external validation.

Use evaluation metrics that cover:

- water-quality improvement
- GDP loss
- compensation efficiency
- fairness, such as `1 - Gini(NetWelfare)`
- participation rate
- policy stability
- `CVaR_5%(WaterQuality)`
- `CVaR_5%(NetWelfare)`
- worst province loss

## Minimum Manuscript Shape

When drafting paper text, proposals, outlines, or reports, organize around:

1. Study area and policy context.
2. Data.
3. Watershed simulator.
4. Counterfactual ecological compensation.
5. Delayed ecological benefit replay.
6. Distributional risk critic.
7. Baselines.
8. Evaluation.

Recommended title:

> From water-quality accounting to marginal-contribution pricing: counterfactual ecological compensation in the Yangtze River Basin

Acceptable alternative:

> Counterfactual ecological compensation for long-horizon watershed governance through multi-agent reinforcement learning

## Figure Checklist

When designing outputs, steer toward these figures:

- Problem diagram: Yangtze upstream-downstream provinces, sections, ecological externalities, and transfer funds.
- CEC-MARL architecture: decentralized provincial actors, basin-level centralized critic, counterfactual contribution, compensation pool, watershed simulator.
- Compensation difference map: current rule versus counterfactual mechanism.
- Pareto frontier: GDP loss versus water-quality improvement.
- Delayed ecological benefit plot: show DEBR reducing short-sighted policy.
- Stress-test and anti-manipulation plot: show lower tail risk under shocks and gaming.
- Optional open benchmark or simulator interface figure.

## Data Roadmap

Prefer progressively stronger data tiers:

- Minimum: annual province panel for GDP, industry structure, fiscal revenue/spending, environmental spending, wastewater, sewage treatment, carbon emissions, and annual water quality.
- Medium: monthly or quarterly water quality plus annual economic data, using mixed-frequency modeling or careful interpolation.
- Strong: monthly section water quality, hydrology, remote sensing, provincial economy, enterprise pollution sources, and policy text.

For Eco-Yangtze-Env, keep the immediate working target as an auditable `Province x Year` or higher-frequency panel plus section topology and a current-rule proxy. Do not invent missing CODMn, NH3N, TP, GDP, fiscal, or compensation values; preserve missingness and report it.

## Reviewer Defense

Anticipate and preempt these objections:

- "RL is a black box": include interpretable panel simulator, sensitivity analysis, policy constraints, and counterfactual decomposition.
- "Governments are not game agents": use bounded rationality, historical policy calibration, and optionally imitation learning before RL fine-tuning.
- "Counterfactuals cannot be verified": compare with quasi-natural experiments, DID, placebo tests, and synthetic controls where possible.
- "Compensation encourages gaming": include reward-hacking experiments, monitoring noise, anomaly detection, and remote-sensing or third-party proxies.
- "This is China-specific": present Yangtze as a large real-world benchmark and add transfer validation to Yellow River, Xin'an River, or synthetic basins.

## Writing Style

Use Nature Sustainability-level language:

- Prefer policy mechanism, marginal contribution, incentive compatibility, participation constraint, fiscal feasibility, fairness, tail risk, watershed governance.
- Avoid hype around AI, complex architectures, dopamine, gambling, addiction, sunk-cost psychology, blind boxes, or gamified policy language.
- Start abstracts and introductions with policy pain, not model novelty.
- Present MARL as necessary because the problem has multiple actors, partial observability, long feedback, spatial spillovers, non-stationary strategies, and credit assignment difficulty.

## References

Read `references/final-goal-condensed.md` when the task requires detailed formulas, experiment specs, data tiers, or manuscript structure.
