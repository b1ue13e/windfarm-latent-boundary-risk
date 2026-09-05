# 论文结果总整理、主线收束与分区判断（2026-09-05）

## 结论先行

这批结果可以汇聚成一条主线，而且主线已经比“physics-aligned MoE 提升风电预测”更清楚：

> **当 MPPT→变桨边界的确认通道延迟、受噪声影响或不完整时，与功率预测联合学习的软边界风险后验仍可从后果通道恢复 declared boundary；联合学习使后验携带残差/备用风险信息，路由结构则提高退化确认流下的识别鲁棒性，从而为已有低 RMSE 预测器提供一个可审计、边界限定的 reserve-screening layer。**

分区判断：

- **二区：能支撑，而且证据规格明显高于普通二区稿。** 五随机种子、强预测基线、负对照、时间/空间 holdout、跨场复现、matched non-routed head、独立分类器、统计多重校正和诚实负结果已经形成完整证据梯。
- **一区/TSTE：可以冲，但当前不是“稳一”。** 主要限制不是实验数量，而是方法必要性和真实运营闭环：干净观测下物理连续量更优，模块化低 RMSE forecaster + classifier 很有竞争力，外部场站 reserve 增量未检出，真实延迟仅有异步事件 grounding 而没有事件级经济后果。
- **当前交付状态：submission-oriented draft，但建议修完下述语义 P0 后再投。** 2026-09-04 的提交包已通过 10 页、43 项数字 token 和 evidence-freeze guard；这些 guard 没有检查比较方向和跨表语义，因此不能替代人工证据审计。

IEEE TSTE 官方把范围界定为可并入输配电系统的可持续能源系统，以及相关设计、实现、并网与控制研究；当前问题在 scope 内，但 reserve proxy 必须继续保持“诊断/筛查”定位，不能包装成 dispatch 或市场收益。

## 结果应如何归并

### 第一层：问题成立，但预测不是贡献

WTB 边界带 RMSE 约 321.17，比非边界有效样本高约 67，说明该窗口确实是风险集中区。与此同时，iTransformer/GWN 的 RMSE 为 224.34/225.74，train-only router 为 229.93，legacy router 为 236.13。由此只能得出：需要一个边界诊断层，但不能得出 routing 改善整体预测。

论文第一句贡献应主动承认：**accuracy belongs to the backbone; accountability belongs to the posterior.**

### 第二层：边界不是简单阈值重放

最强证据不是 legacy NMI 0.872，而是 withheld-channel + shuffled control：

- WTB 去掉 Wspd/Pab 后 NMI 仍为 0.561，标签置换后约 4e-6；
- LHB signature_full/core 为 0.674/0.575，置换后 1.92e-4；
- 去掉 Pab_std 后 WTB/LHB core 仍为 0.309/0.578；
- Penmanshiel/Kelmarsh 的 signature_full 为 0.302/0.340，四个附加窗口逐 seed 均越过 0.20。

这组结果支持“后果通道中存在可学习的边界 signature”，但不支持 anchor-free discovery 或控制因果识别。WTB signature_core 有 3/5 seeds expert collapse，也必须保留。

### 第三层：联合学习负责风险定价，路由负责退化鲁棒

这是把所有结果串起来的机制核心。

在统一 boundary-band soft-pricing 管线中：

- global：16.632M；
- joint routed posterior：16.065M，对 global 为 -0.568M，CI [-0.726M,-0.406M]；
- joint non-routed posterior：16.076M，与 routed 差 +0.011M，CI [-0.163M,+0.186M]；
- independent GBDT posterior：17.656M，比 joint routed 高 1.59M；
- continuous pitch quantile：15.538M，仍是 clean observation 下最强基线。

因此定价增量不能归给 MoE route。更准确的解释是：**联合训练得到的表征/后验与预测误差共同适配；route 与 non-route 在定价上未检出差异。**

在公平退化中：

- delay6：routed 0.933，joint non-routed 0.286，rule 0.196，GBDT 0.868；
- strongest noise：routed 0.951，rule 0.680，GBDT 0.804；
- stalled-history upper bound：delay6 routed 0.416，rule 0.196。

因此 routing 的独特增量是相对 matched joint non-routed head 的退化保持能力；但 GBDT 0.868 表明它不是唯一可用方案。

### 第四层：跨场结果是部署边界，不是外部价值闭环

LHB 提供较强 replication；Penmanshiel/Kelmarsh 提供 heterogeneous observability 下的弱到中等 signature。结果并不随 pitch coverage 单调：Penmanshiel 78% 的 core 0.195 低于 Kelmarsh 55% 的 0.378。因此宜写成“由多通道 consequence quality 共同决定的 graded recoverability”，不宜把 pitch coverage 当单一解释轴。

Kelmarsh soft-gate reserve 对 global 仅 -0.04M，CI [-0.20M,+0.13M]，未检出外部定价增量。这是目前一区上限最明确的短板。

### 第五层：运营结论必须分成两套口径

主稿现在同时展示 95M 级 hard-route reserve audit 和 16M 级 soft-posterior boundary-band audit。两者目的、聚合方式和比较对象不同：

- 95.13M vs 99.55M 回答“同一 routed forecaster 的硬 gate-bin 是否优于 global”；
- 16.065M vs 16.632M 回答“软 posterior 是否提供类内风险分层，以及价值来自 joint learning 还是 routing”。

主线真正需要的是第二套，因为它直接对应“joint posterior”机制分解。建议主文保留 16M 机制表，把 95M 硬策略表移到补充材料或明确标成独立 legacy-compatible diagnostic。否则读者会把两组数误认为可横向比较。

## Claim 强度排序

| 等级 | 主张 | 判断 |
|---|---|---|
| A | 去定义通道后 boundary signature 仍高于 shuffled chance | 主线核心，证据强 |
| A- | routed posterior 在预定义公平退化下显著优于 rule 和 matched non-routed head | 主线核心；需限定为 controlled stress protocol |
| B+ | joint posterior 对 global reserve proxy 有显著局部增量 | 成立，但 physical continuous baseline 更强 |
| B | 跨场异质可观测条件下可恢复 | 成立；不是单调 coverage 规律，也不是直接 transfer |
| B- | joint learning 是定价价值来源 | 与现有对照一致，但独立 modular posterior 对照仍未穷尽 |
| C | 实际运营/经济价值 | 目前仅为 proxy，外部场站未检出 |
| 不成立 | 预测 SOTA、clean detector superiority、普适 reserve policy、anchor-free discovery | 必须继续明确否认 |

## 投稿前语义 P0

1. **修 Supplementary A10c 的比较方向。** 86.54M 优于 95.13M、劣于 84.31M；当前句子写成同时 “trails physical-bin/gate-bin”，后半错误。主文对应句已经正确。
2. **删除或纠正 ERA5 的 “NMI 0.90+” 句。** `table_routing_quality.csv` 的 Physics-Aligned MoE 为 0.2100 +/- 0.1086，Unconstrained MoE 为 0.0317 +/- 0.0245；补充材料末节的 0.90+ 没有被最终表支持。这是可被直接判为稿证冲突的 blocker。
3. **统一 evidence source of truth。** 最新补充材料 A6 已使用 train-only -0.109/-0.138，但 `final_evidence_package/export/tables/statistical_claim_boundaries.csv` 仍保留 legacy +0.040/+0.035。当前 number guard 只检查 token 是否出现，不能发现两个证据包的语义冲突。
4. **解释 week-block bootstrap 的尺度。** A11d 报告 -4.42M 的 same-model mean difference，A11d 脚注又报告 -22.40M observed mean per seed；两者近似相差 5 倍。即便只是 pooled/sum 与 per-seed mean 的区别，也必须在表头和脚注明确单位，避免被判计算不一致。
5. **收紧“joint learning 负责定价”的措辞。** 与 hard classifier/physical-bin 的 -0.125M CI 跨零；soft logistic control 16.234M 也很接近。可以写“consistent with a joint-learning/shared-representation explanation”，不能写成已经证明 modular pipeline 无法替代。
6. **跨场主张改成 heterogeneous observability，而非 pitch-coverage law。** 78% < 55% 的非单调结果必须与贡献句同时出现。

## 一区增量：只补三件高价值工作

### 1. 决定性外部后果验证

在 LHB、Kelmarsh 或 Penmanshiel 至少一个场站完成 local recalibration + held-out reserve consequence，并报告失败也可以。目标不是一定显著，而是回答：WTB 的后验—残差关系是否能在外部场站复现。

### 2. 匹配的 modular posterior 对照

用同一低 RMSE backbone、同一 consequence-channel 输入、同一参数/调参/校准预算，比较：

- 独立 posterior；
- joint non-routed posterior；
- joint routed posterior。

同时报告 pricing、degraded recall、calibration、latency 和统一日志成本。若 joint non-routed 已足够，论文就应把 route 降为鲁棒实现，而不是核心学习原理。

### 3. 真实延迟/缺失分布或事件级对齐

当前 Kelmarsh 的 99.6% 非网格事件只证明异步，不证明 1--6 step 延迟在真实系统中的频率。最好估计 event-to-periodic-confirmation lag、缺失持续时间与 boundary-event recall；拿不到则把全文统一写成 controlled deployment stress test。

## 建议的主文结构

1. **Problem**：低 RMSE 不提供控制边界责任链；确认流会退化。
2. **Posterior**：定义 jointly learned boundary-risk posterior，MoE 是 routed realization。
3. **Identifiability**：withheld channels + shuffled + Pab_std ablation + LHB replication。
4. **Mechanism decomposition**：joint/non-joint × routed/non-routed × physical/non-physical。
5. **Degradation**：公平 delay/noise/stalled-history，强调协议边界。
6. **Decision consequence**：只用统一 soft-pricing 主表；hard-route 表移补充。
7. **Deployment limits**：多场站异质可观测性、外部 reserve null、真实延迟未闭环。

## 最终判断

**这不是一篇靠“模型精度小幅提升”投稿的论文，而是一篇靠“边界风险后验的可识别性、机制分解、退化鲁棒性和诚实部署边界”投稿的论文。** 按这条线收口，二区具备较高把握；一区/TSTE 有现实机会，但必须先清掉上述六个稿证/尺度 P0，并至少补“外部后果”或“匹配 modular posterior”中的一个决定性闭环。若不补，最合理定位是强二区或一区边缘稿；若补成，才有资格把它称为较稳的一线能源系统方法论文。

## 主要证据入口

- 主稿：`paper_tste_ieee.md`
- 补充材料：`paper_tste_supplementary.md`
- soft posterior：`artifacts/p1_stats_20260904/unified_control_table.csv`
- fair degradation：`artifacts/fair_degradation_replay_20260903/fair_degradation_summary.csv`
- cross-farm：`artifacts/p1_stats_20260904/farm_median_iqr.csv`
- modular/dense controls：`artifacts/breakthrough_20260904/`
- hard reserve audit：`artifacts/decision_reserve_trainweight_allclean_20260830/reserve_decision_summary.csv`
- package verification：`artifacts/tste_submission/20260904_103543/VERIFICATION_REPORT.md`
