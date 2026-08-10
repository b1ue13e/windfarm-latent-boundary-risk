# TSTE 论文写作与文献支撑地图

本文档用于约束 `paper_tste_ieee.md` 的语言润色、文献使用和证据叙事。文献只承担“定义问题、说明方法来源、建立比较基线和限定解释边界”的功能，不复制任何论文的原句、段落或图表布局。

## 一、核心参考文献

当前稿件至少有以下五篇可作为主线核心文献。它们分别承担不同的论证任务，不能把五篇文献堆在同一个句子后面。

| 核心文献 | 期刊/会议 | 在本文中的功能 | 适用位置 |
|---|---|---|---|
| Karniadakis et al. (2021), `@karniadakis2021piml` | *Nature Reviews Physics* | 说明 physics-informed machine learning 的约束思想、可解释性与泛化边界 | 引言、物理约束方法、局限性 |
| Zehtabiyan-Rezaie et al. (2023), `@zehtabiyan2023physicsguided` | *PRX Energy* | 支撑风电场 physics-guided prediction 的研究背景，作为领域内高质量方法参照 | Related Work、方法定位、讨论 |
| Pinson (2013), `@pinson2013forecasting` | *Statistical Science* | 说明风电预测的运行管理、爬坡和不确定性问题 | 引言问题动机、reserve 诊断 |
| Hersbach et al. (2020), `@hersbach2020era5` | *QJRMS* | 说明 ERA5 数据与再分析场的来源、物理可观测性背景 | 数据集与 ERA5 对照 |
| Zhou et al. (2024), `@zhou2024sdwpfdata` | *Scientific Data* | 说明 SDWPF/WTB 数据的规模、字段和公开基准地位 | 数据集与复现设置 |

方法比较时再使用 `@wu2019graphwavenet`、`@li2018dcrnn`、`@yu2018stgcn`、`@nie2023patchtst`、`@liu2024itransformer` 和 `@das2023longterm`。它们是基线或模型组件来源，不应替代上述五篇核心论证文献。

## 二、逐节写作任务与引用分配

### Abstract

摘要按“问题 → 缺口 → 方法 → 关键结果 → 含义 → 边界”组织。摘要中的每个数字都必须能在主表或补充表中找到；不在摘要中展开旧 checkpoint 与新 checkpoint 的所有细节，只用一句话明确两者的 provenance boundary。

### Introduction

| 段落 | 句子功能 | 应回答的问题 | 推荐文献 |
|---|---|---|---|
| 1 | 重要性与运行风险 | 为什么平均 RMSE 不足以描述 transition-window 风险？ | `@pinson2013forecasting; @wang2025uncertaintyreview; @doherty2005reserve` |
| 2 | 已知方法与能力边界 | 图模型、SCADA 和 physics-guided 模型已经解决了什么，仍缺什么？ | `@wu2019graphwavenet; @park2019physicsinduced; @kim2024lidarscada; @daenens2025offshore` |
| 3 | 方法缺口 | 为什么 MoE 的 route 需要物理 anchor 和审计？ | `@jacobs1991adaptive; @jordan1994hierarchical; @shazeer2017outrageously; @karniadakis2021piml` |
| 4 | 本文问题与范围 | 本文究竟验证 routing diagnosis，而不是预测 leaderboard 或 dispatch optimality | `@tautzweinert2017scada; @bremnes2004quantile; @zhou2013probabilisticmarkets` |
| 5 | 贡献 | 只列可被结果支持的三项贡献，主动写出 classifier、external transfer 和 RMSE 的边界 | 结果表、A6、A8、A10 |

### Related Work

每个小节只做一件事：先给领域共识，再指出本文的具体差异。避免逐篇罗列文献。图模型小节使用 `@wu2019graphwavenet; @guo2019astgcn; @bai2020agcrn`；physics-guided 小节使用 `@karpatne2017tgds; @karniadakis2021piml; @zehtabiyan2023physicsguided`；决策风险小节使用 `@bremnes2004quantile; @zhang2014probabilisticreview; @zhou2013probabilisticmarkets`。

### Methods

方法段落采用“设计目的 → 数学定义 → 信息边界 → 可复现参数”的顺序。每个公式前先解释它解决哪一个失败模式：

- directed diffusion graph：表示风向依赖的空间传播，引用 `@li2018dcrnn; @wu2019graphwavenet`；
- graph/SCADA physics：说明图结构如何进入风电模型，引用 `@park2019physicsinduced; @zehtabiyan2023physicsguided`；
- MoE gate：说明软路由与 expert collapse 风险，引用 `@shazeer2017outrageously; @fedus2022switch`；
- reserve quantile：说明 validation-frozen empirical shortfall rule 的来源，引用 `@bremnes2004quantile; @nielsen2006quantile`。

### Results

Results 每段使用三句结构：

1. **Question sentence**：明确本段检验什么；
2. **Observation sentence**：给出表/图中的主要数字；
3. **Boundary sentence**：只说明该数字能支持到哪里，解释性推断留给 Discussion。

建议顺序为：数据与信息边界 → 主预测比较 → route alignment 与消融 → boundary stress/early warning → reserve consequence → external deployment gates。该顺序对应“平台有效性 → 性能代价 → 机制证据 → 运行后果 → 可迁移性”的证据阶梯。

### Discussion and Conclusion

Discussion 不重复每个数字，而是解释三件事：

- high NMI/ARI 证明的是 declared-anchor compliance，不是 anchor-free discovery；
- reserve gain 只在 boundary slice 和中等 `rho` 下成立，physical-bin 仍是强对照；
- external evidence 说明 observability 是 deployment gate，而不是自动泛化保证。

结论必须以“贡献 + 决定性证据 + 适用边界”收束，不加入新的实验数字。

## 三、表格为什么这样安排

| 表格 | 表格问题 | 为什么需要该布局 | 读者应得到的结论 |
|---|---|---|---|
| Main benchmark | 路由是否值得付出 RMSE 代价？ | 先放强预测基线，再放 dense/MoE 家族，避免只在弱基线上比较 | 本方法不是 leaderboard winner，RMSE price 必须透明 |
| Main mechanism table | gate 是否恢复声明的 operating boundary？ | 将 NMI/ARI、intervention、holdout 和 external checks 放在同一证据面板 | 高 alignment 代表可审计 routing，不代表无监督发现 |
| Early-warning table | label delay/availability/noise 下，issue-time route 是否仍有用？ | 以 degradation scenario 为行，Gate/Rule/Classifier 为列，直接暴露控制基线 | gate 的价值是 responsibility chain，不是 standalone classifier superiority |
| Reserve table | route 是否改变 boundary-window reserve trade-off？ | 同时列 global、physical-bin、gate-bin 和 GWN reference | 只支持 same-router diagnostic，不支持 universal policy optimality |
| External deployment table | 什么条件允许跨风场使用？ | 将 observed evidence、go/no-go rule、claim consequence 并列 | observability 与 held-out pass 是部署前置条件 |
| A1 model family | 消融比较是否公平？ | routing、extra terms、参数量和实验角色放在同一行 | 读者可以区分容量效应和物理约束效应 |
| A2 information boundary | 是否存在未来信息或共享 anchor 泄漏？ | label、input、target、timing 四列分开 | NMI/ARI 的解释边界被预先声明 |
| A3--A5 constants | 结果能否复现？ | 共享超参数、数据阈值和 loss 权重分表 | 参数来源与作用清楚，避免把调参写成物理定律 |
| A6/A6b statistics | 哪些数字可作显著性结论？ | estimate、CI、p 值和 wording consequence 并列 | 旧 checkpoint、新 rerun 和统计措辞不混用 |
| A7 outcome sanity | gate 是否只是在复述 anchor？ | 用 validation power curve 做 outcome-channel 对照 | 缓解 circularity，但不声称 anchor-free discovery |
| A8/A9 external replay | 外部高 NMI 的负载通道是什么？ | 通过 site gate 与 anchor intervention 分开呈现 | La Haute Borne 是 anchor-observable replication |
| A10/A10b/A10c detector control | gate 是否优于模块化替代方案？ | 同列 Gate、Rule、Classifier 与 route evolution | 主张限定为 in-model attribution |
| A11/A12 reserve boundary | 经济数字能否外推？ | 同时给 CI、cost-ratio sensitivity、单位换算和 excluded operations | 只做 screening audit，不代表市场收入或 OPF 结果 |

## 四、句子级自检规则

1. 每句话只能有一个主要命题；若同时包含方法、结果和意义，拆成三句。
2. Results 用过去时描述观察到的结果；Discussion 用 `suggest`, `may`, `is consistent with` 表示解释。
3. 每个核心 claim 都要有对应的 evidence 和 boundary。没有对应表格的数字不得进入摘要或结论。
4. `best`, `superior`, `robust`, `generalizable`, `physics-discovered` 等词只有在跨基线、跨 seed、跨站点证据都支持时才可使用。当前稿件应避免这些绝对词。
5. 文献引用解释“为什么这样设计”或“前人已经知道什么”，不为本实验的数字背书。实验数字必须引用自己的表格和 source-data artifact。

