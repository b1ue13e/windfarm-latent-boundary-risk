# Nature Skill Reference: Eco-Yangtze-Env Final Goal

## One-Sentence Goal

Use multi-agent counterfactual learning to redefine watershed ecological compensation: move from paying by observed section-water-quality outcomes to pricing cross-period, cross-region marginal ecological contributions.

## Policy Anchor

The 2025 Chinese policy window matters because central ministries proposed a unified horizontal ecological protection compensation mechanism for the Yangtze and Yellow River mainstems by 2027 and broader coverage by 2035. The Yangtze mainstem province set is Qinghai, Tibet, Sichuan, Yunnan, Chongqing, Hubei, Hunan, Jiangxi, Anhui, Jiangsu, and Shanghai. Current water-quality accounting uses CODMn, NH3N, and TP with weights 30%, 30%, and 40%.

Use official citations when writing formal text:

- Ministry of Finance et al., `关于进一步健全横向生态保护补偿机制的意见`, 财资环〔2025〕49 号, 2025-05-30.
- Ministry of Finance et al., `关于深入推进大江大河干流横向生态保护补偿机制建设的实施方案`, 财资环〔2025〕50 号, 2025-05-30.

## Core Formula Sketches

Counterfactual ecological contribution:

```text
C_i,t^cf =
Q_phi(S_t, a_i,t, a_-i,t)
- E_{a'_i,t ~ pi_i}[Q_phi(S_t, a'_i,t, a_-i,t)]
```

Watershed state:

```text
S_t = {o_1,t, o_2,t, ..., o_N,t, B_t, G_t, W_t}
```

Local observation:

```text
o_i,t = [
  GDP_i,t,
  Ind_i,t,
  Fiscal_i,t,
  CODMn_i,t,
  NH3N_i,t,
  TP_i,t,
  Carbon_i,t,
  Wastewater_i,t,
  EcoInv_i,t,
  Pop_i,t,
  UpstreamFlow_i,t
]
```

Policy action:

```text
a_i,t = [e_i,t, c_i,t, p_i,t, q_i,t, z_i,t]
```

Environment transition:

```text
S_t+1 = f_theta(S_t, A_t, X_t) + epsilon_t
```

Water-quality reward:

```text
WQ_t = -[0.3 * CODMn_t + 0.3 * NH3N_t + 0.4 * TP_t]
```

Global reward:

```text
R_t^global =
alpha * WQ_t
+ beta * GDP_t
- gamma * Inequality_t
- eta * FiscalRisk_t
- mu * ManipulationRisk_t
```

Compensation score:

```text
Score_i,t =
lambda_1 * C_i,t^eco
+ lambda_2 * C_i,t^cost
+ lambda_3 * Risk_i,t
- lambda_4 * ManipulationRisk_i,t
```

Transfer:

```text
T_i,t =
B_t * exp(Score_i,t / tau) / sum_j exp(Score_j,t / tau)
```

Constraints:

```text
sum_i T_i,t <= B_t
Welfare_i,t^with_compensation >= Welfare_i,t^without_participation
```

## Experiments

Historical backtest:

- Train 2011-2018.
- Validate 2019-2021.
- Test 2022-2025.
- Prefer monthly or quarterly water quality if available.

Mechanism comparison:

- no compensation
- fixed compensation
- current section-water-quality rule
- system dynamics or evolutionary game
- basic MARL
- COMA-style MARL
- full CEC-MARL

Delayed ecological benefit:

- Compare short-term GDP-preserving policy versus long-term investment policy.
- Show DEBR reduces short-sighted governance.

Upstream-downstream credit assignment:

- Build a scenario where upstream A reduces pollution and downstream B's section improves.
- Show `C_A^cf > 0` and `T_A^CEC-MARL > T_A^CurrentRule` without claiming all upstream provinces deserve more.

Stress tests:

- drought
- industrial demand shock
- fiscal budget decline
- upstream pollution accident
- downstream recession
- monitoring noise
- strategic manipulation

Reward hacking:

- pollution transfer to non-assessed tributaries
- temporary pre-assessment treatment
- baseline suppression
- selective reporting
- pollution transfer downstream or outside the target region

Transfer validation:

- Yangtze train, Yellow River test
- Yangtze main experiment, Yellow River or Xin'an River external validation
- Synthetic basin benchmark calibrated with Yangtze data

## Ablation Table

| Model | Counterfactual | DEBR | Risk critic | Adaptive target | Purpose |
|---|---|---|---|---|---|
| Current Rule | No | No | No | No | Policy baseline |
| MARL-basic | No | No | No | No | Plain RL |
| CEC-only | Yes | No | No | No | Credit assignment |
| CEC+DEBR | Yes | Yes | No | No | Long-term benefit |
| CEC+Risk | Yes | No | Yes | No | Tail risk |
| Full CEC-MARL | Yes | Yes | Yes | Yes | Full mechanism |

## Contribution Language

Use this four-part contribution set:

1. Formulate watershed ecological compensation as a decentralized partially observable Markov game linking upstream-downstream hydrological externalities with fiscal transfer design.
2. Develop a counterfactual compensation mechanism that prices each jurisdiction's marginal contribution to basin-wide ecological welfare rather than relying only on observed water-quality accounting.
3. Introduce delayed ecological benefit replay and distributional risk evaluation to address long-horizon conservation costs and policy tail risks.
4. Apply the framework to the Yangtze River Basin and show improved water quality, fiscal efficiency, and interregional fairness under historical and stress-test scenarios.

Do not add a fifth contribution unless the user explicitly requests a broader paper.
