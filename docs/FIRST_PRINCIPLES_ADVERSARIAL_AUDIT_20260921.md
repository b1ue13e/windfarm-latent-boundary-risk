# 论文核心问题的对抗性审查与第一性原理收束

日期：2026-09-21  
审查对象：`paper_tste_ieee.md` 及其补充材料、核心证据与决定性实验文档  
审查方式：第一性原理因果链 + 最强反例审查 + claim-evidence 对齐

## 1. 先给结论

这篇论文真正解决的不是“MoE 是否改善风电预测”，也不是“深度模型是否普遍优于物理模型”。最稳固的主线是：

> 当 MPPT 到主动变桨的关键控制边界因延迟或通道缺失而不可直接观测时，可部署的 SCADA 后果信号能否恢复足够的边界信息，并在边界跃迁期间改善尾部备用风险分配？

这条主线有一半得到强证据支持，另一半只能得到条件性支持：

- **边界信息可恢复：SUPPORTED。** 在 pitch withholding 下，active-power consequence 是最有信息量的通道；C2 的 Brier=0.0112、NMI=0.461、ARI=0.647、跃迁召回率=62.9%（`docs/CONSEQUENCE_SIGNAL_MECHANISM.md`）。
- **恢复信息具有普遍独立决策优势：NOT SUPPORTED。** 后验策略相对强 wind-speed-binned quantile 在全厂 PSREI 上高出 523,044 kWh（p=0.85）；稳态窗口反而由 wind-speed bins 占优。现有证据只支持跃迁窗口的风险重分配：违约率 7.24% 对 8.36%、短缺暴露 86.6k 对 90.2k kWh，但需额外备用，成本仍高 112,704 kWh（`docs/DECISION_VALUE_MEDIATION.md`）。
- **最小充分机制比“联合复杂表示”更简单：INFERRED/部分 VERIFIED。** C2 active-power-only 已达到最佳状态识别，C9（active power+wake）几乎相同，而全 consequence suite 的 NMI 反而为 0.226。当前证据支持“功率后果签名是主要媒介”，不支持“必须联合动态图、热通道和多专家路由”。

因此，论文的最严谨结论应是：**学习表示在关键状态不可观测、且风险集中于控制边界跃迁时，提供一种条件性的尾部风险对冲；它不是全厂成本最优器，也不是物理规则的通用替代。**

## 2. 第一性原理：问题到底是什么

把所有模型、网络结构和术语暂时去掉，只保留决策因果链：

```text
控制边界 Z_t 发生跃迁
        ↓
pitch / 新鲜状态信息延迟或缺失
        ↓
物理规则使用过时状态，或直接 quantile 无法区分边界条件
        ↓
预测残差的上尾被低估
        ↓
在非对称短缺损失下，备用配置出现尾部风险
```

所以本论文的基本对象不是预测均值，而是条件尾部分布：

\[
q^*(I_t)=Q_{0.90}\bigl(s_t\mid I_t\bigr),\qquad
s_t=\max(\hat y_{\mathrm{fixed},t}-y_t,0),
\]

其中 `I_t` 是真正已经到达调度端的信息集。理想方法不是“模型越复杂越好”，而是找到给定 `I_t` 下的**最小充分决策函数**：在名义 10% 违约目标下，PSREI 尽可能低；只有当显式边界信息相对于同信息集的直接 quantile 确实改变决策，才值得把它作为独立科学对象。

## 3. 最凝练的三个问题

### Q1：边界是否可观测

**问题：** 在 pitch 延迟或被 withholding 时，哪些已经到达的 SCADA 后果信号仍包含 MPPT/主动变桨边界的信息？这种可识别性在多大延迟、噪声和通道缺失下仍存在？

**为什么过去解决不了：**

1. 物理曲线默认 `Wspd` 和 pitch 同时新鲜可见，边界跃迁时会沿 cubic 曲线外推。
2. 传统预测按平均误差优化，把离散控制边界和尾部短缺混在一起。
3. 直接分类的准确率没有约束其错误是否发生在残差最大的跃迁时刻。

**现在的思路：**

- 先冻结到达时间和输入掩码，所有方法接受同一 `I_t`；
- 用历史可得的 regime label 做离线辅助监督，把不可观测边界变成可检验的 latent representation；
- 用 channel ablation 判断信息来源，而不是把效果归因于网络名字。

**证据结论：** Q1 在限定条件下回答“是”。Active power 是主导通道；热通道和 wake-only 通道不能独立恢复快速跃迁。Condition A 的当前 active power 达到 AUROC=0.988，说明它是强直接读出；因此论文不能把结果写成“复杂时空模型从弱信号中发现了边界”。更准确的说法是：**功率后果签名保留了部分边界可识别性，时序和空间信息只提供附加的防御层。**

### Q2：边界恢复是否有独立决策价值

**问题：** 在完全相同的到达信息、冻结点预测和残差目标下，显式恢复边界后验是否比直接 conditional quantile 更能降低非对称备用风险？

**为什么过去解决不了：**

1. “识别得准”不等于“备用配得好”；独立分类器已出现高 recall 但更高 PSREI。
2. 如果没有同信息集的 strong direct baseline，就无法知道后验是否只是复杂的条件分箱。
3. 全厂平均成本会掩盖边界跃迁的局部风险，单一 aggregate 指标也无法说明价值发生在哪里。

**现在的思路：**

- 以同一 frozen residual target 比较 posterior、wind-speed bins、global quantile 和 direct GBDT/quantile baselines；
- 把全厂、steady-state、transition-window 三个区域拆开；
- 用 paired day-cluster bootstrap 检验 `transition gap - steady gap`，而不是只比较一个总均值。

**证据结论：** 广义的“独立决策价值”没有被证明。posterior 全厂没有击败 wind-speed bins，且在稳态更贵；它的证据是**局部风险对冲**而非成本最优。现有最强表述应为：

> 边界后验在跃迁窗口降低短缺与违约暴露，但以额外备用采购为代价；其价值是风险形状重分配，不是全厂 PSREI 改善。

### Q3：什么时候值得用学习模型

**问题：** 在什么信息条件下，物理规则、非神经重校准和学习表示分别是最小充分的方案？

**为什么过去解决不了：** 以“模型能力”作为起点，会把 fresh telemetry、observable delay 和 pitch missing 混成一个任务，无法知道复杂模型究竟填补了哪一个信息缺口。

**现在的思路：** 通过信息可观测性分层建立回退边界：

1. fresh pitch/wind：确定性物理规则；
2. 状态仍可观测但分布发生漂移：state-conditional recalibration；
3. pitch 不可观测且跃迁风险重要：consequence-based learned representation；
4. 小型稀疏场或跨场 zero-shot：回退或本地重校准。

**证据结论：** 这是论文最有实际解释力的产物，但它是**条件决策图**，不是一个单一新模型。理想结果是证明每一层都只在自己的信息边界内承担任务，并且简单方案在能解决问题时优先。

## 4. 最终理想情况应该怎样定义

理想情况不应写成“学习模型在所有场景赢”。可证伪、也符合现有证据的理想目标是：

1. 给定任意部署信息集 `I_t`，先判断关键边界是否仍可由新鲜物理量直接确定；
2. 若可确定，物理规则达到最低 PSREI；若仅有分布漂移，重校准恢复名义违约率；
3. 若边界不可观测，后果信号提供经过校准的边界风险，并在跃迁窗口相对 direct quantile 减少短缺/违约；
4. 若后验不能降低同一决策损失，系统应回退到 wind-speed bins 或统一 margin，而不是保留复杂模型；
5. 训练依赖历史 pitch 的 privileged setting 必须显式写入适用域；pitch 从未记录的场景仍是 UNKNOWN。

一句话：**理想系统选择的是“在当前可观测性下足以解决尾部风险的最简单模型”，而不是固定选择神经网络。**

## 5. 对抗性审查：最强反例与当前回答

| 反例问题 | 当前证据能否回答 | 严格回答 |
|---|---|---|
| 这只是 active power 的直接读出，不是 latent-boundary recovery 吗？ | 部分能 | 是强反例。C2 最好、Condition A 当前功率 AUROC=0.988；应把“复杂时空发现边界”降为“功率签名保留边界信息”，并承认复杂结构的增量尚未建立。 |
| 后验是否真的优于同信息 direct quantile？ | 能 | 全厂不优于；transition 只显示风险对冲和 violation/shortage 改善，成本仍更高。不能写 universal decision gain。 |
| privileged pitch supervision 是否改变了问题？ | 能 | 改变了适用域：结论仅适用于“历史训练可见、部署时不可见”。匹配 ablation 只隔离 regime-label supervision，未隔离训练期 pitch 本身。 |
| 多场结果是否证明泛化？ | 只能部分回答 | 只能作为 external-validity boundary probes。外部表没有 matched no-graph controls，不能把收益归因于 wake modeling。 |
| 60 分钟延迟是否是真实工业故障？ | 不能完全回答 | 当前是 synthetic stress envelope；不能宣称现场延迟分布或真实现金流效果。 |
| MoE 是否是关键机制？ | 能 | 不是。Dense/MoE parity 和 modular result 已经把 MoE 降为实现细节。 |
| 训练/测试信息是否对称？ | 已有强证据 | `docs/INFORMATION_SET_CONTRACT.md` 和 arrival-feed 审计支持 parity；这是可信度底座，但不等于证明机制本身。 |

## 6. 主线证据链的最终评级

| 主张 | 评级 | 原因 |
|---|---|---|
| 新鲜 telemetry 下物理规则在边界带最好 | VERIFIED | 五 seed、固定目标、证据表和 gate 均有来源。 |
| 可观测延迟可由非神经重校准吸收一部分风险 | VERIFIED | 55.3% shortage absorption，且有明确条件。 |
| pitch withholding 下 consequence signals 保留边界信息 | VERIFIED（限定域） | C2 ablation、transition recall、active-power audit 支持；但主要信息来自 active power。 |
| latent posterior 在全厂降低 PSREI | REFUTED / 不成立 | 相对 wind-speed bins 为 +523,044 kWh，p=0.85。 |
| latent posterior 在跃迁期间提供独立风险价值 | PARTIALLY SUPPORTED | 违约和短缺暴露下降，但额外 reserve cost；交互项显著说明异质性，不说明总成本优越。 |
| regime supervision 本身带来 downstream cost gain | NOT ESTABLISHED | NMI/ARI 支持，PSREI 配对差异 CI 跨零。 |
| 外部场站证明模型普适 | NOT ESTABLISHED | 结果异质，LHB 负迁移，且外部因果对照不完整。 |

## 7. 建议采用的核心表述

**研究问题：**

> 在相同的到达时间信息下，当 MPPT—主动变桨边界不可直接观测时，后果信号能否恢复足够的边界信息，使备用分配在跃迁窗口比直接条件分位数更稳健？

**核心答案：**

> 可以恢复部分边界信息，主导来源是 active-power signature；但它没有带来全厂成本优势，只在动态跃迁期间表现为以额外备用为代价的尾部风险对冲。新鲜状态用物理规则，仍可观测的漂移用重校准，只有关键状态不可观测时才需要学习表示。

**不应再作为主线的表述：** “learned boundary recovery provides independent decision value” 若不加 transition-localized、risk-hedging 和 same-information direct-baseline 限定，会超过现有证据。

## 8. 剩余 UNKNOWN / BLOCKED

- 真实工业现场的异步延迟、乱序、时钟漂移和非平稳 dropout 是否产生同样效果：UNKNOWN。
- pitch 从未被历史记录时，privileged supervision 是否仍有效：UNKNOWN。
- 在 external farms 上，后验相对 matched direct quantile 的独立增益：当前证据不足，BLOCKED。
- 端到端市场现金流、AC-OPF 和真实 reserve activation 的经济价值：本研究的 Level-1 PSREI 不覆盖，BLOCKED。

本报告的结论只对上述证据边界负责，不把 UNKNOWN 推断为 VERIFIED。
