# 🏛️ 全证据链 Reviewer 压力测试（2026-09-03，方向 1+2 与实验 A/B 完成态）

> 评审对象：`paper_tste_ieee.md` + `paper_tste_supplementary.md` 当前稿 + 2026-09-01~03 全部新证据
> 新证据清单：signature-gate（WTB H1/H2+双负对照）、LHB 跨场（canonical/full/core/shuffled、core_shuffled）、Kelmarsh/Penmanshiel 可观测性谱系（含 shuffled）、实验 A 公平退化、实验 B 不确定度 reserve、E1/E3 pilot
> 立场：三位对抗审稿人 + AC，拒稿优先；**本轮只做压力测试，不手软**。

---

## 📊 Executive Summary 与录用概率校准

| 情形 | TSTE 概率 | 风险 | 说明 |
| :--- | :--- | :--- | :--- |
| 当前稿直接投（未做证据切换与叙事迁移） | ~15-20% | **Critical** | 新证据强，但**旧 P0 依然在稿**：A6 符号反转、部署门旧叙事、Table III legacy 数字、摘要"fail the gates"与谱系证据自相矛盾 |
| 完成证据切换 + 软边界风险主线重写后 | **~60-70%** | Medium | 三大进攻性证据（公平退化鲁棒性 / 不确定度定价 / 跨场谱系）+ 双负对照，创新性基本站住 |
| 再补 E1/E3 官方化 + 全基线表 + 控制文献 | ~70-75% | Low-Medium | 剩余 P0 是机械性修复 |

**一句话裁决**：创新性问题**基本解决**——现在的证据组合给了审稿人一个"只有你的方法能赢"的答案：规则在退化下崩 80%、你的路由只掉 4%；规则给不出类内风险分级、你的不确定度分箱省 0.3-0.6M 且无需物理箱。**但论文本身还没吃到这些证据**：摘要、贡献、A6、Table III、部署门表仍停留在旧叙事，投稿即自爆。

---

## 👤 Reviewer #1（Theory & Novelty Hawk）

**评分：Soundness 3/4 ｜ Novelty 3/4 ｜ Overall 6/10 ｜ Confidence 4/5**

### 强攻点（打得动的）

1. **循环性**（旧致命）：signature-gate 已经把这条打退。若正文按"boundary signature in consequence channels"写，且有 shuffled 对照，R1 只能退到次要位置。**残余火点**：Pab_std 仍保留在 signature_full/core 输入里——桨距分散度是否泄露 pitch 状态？需在正文明说"Pab_std 是控制后果（三个叶片的分散）而非桨距读数本身"，并指出 Kelmarsh core 0.378 是在 Pab_std 覆盖 89% 的输入上得到的。
2. **"贡献是什么"**（新评估）：三大贡献现在可辩护：(a) 公平退化鲁棒性（0.933 vs 0.196，规则给不出）；(b) 不确定度定价（entropy/maxprob 分箱 vs global 显著省 reserve，物理箱给不出）；(c) 跨可观测性谱系（55% pitch 农场仍恢复边界）。**但摘要/贡献段还没写成这三条**——这是最大的自我消耗。
3. **谱系非单调**：Penmanshiel（78%）core 0.195 < Kelmarsh（55%）core 0.378。必须主动给机制解释（后果通道质量调制），否则会被读为"结果噪声大"。E1 的硬分歧不稳定（1.6%-44.6%）也要同段披露。

### 弱攻点（已经挡住）

- 负对照：4 个 shuffled（WTB full/core、LHB full/core）全随机水平，Kelmarsh/Penmanshiel shuffled 亦随机——"输入分布偶然相关"已死。
- 变体选择（A6 符号）：证据存在（-0.109, p=0.352），但**稿内 Table A6 仍是旧 +0.040**——不改就是送给 R1 的免费实锤。

---

## 👤 Reviewer #2（Empirical & Baseline Nitpicker）

**评分：Soundness 3/4 ｜ Rigor 3/4 ｜ Overall 5/10 ｜ Confidence 5/5**

1. **实验 A 的构造问题（本轮唯一实质攻击）**：延迟只作用于 issue-time anchor（历史窗口保留归档流）。审稿人会问"为什么 6 步延迟不影响历史窗口里的 Wspd/Pab？"——回答是"确认流延迟、归档历史可用"的部署语义，必须在正文写成正式定义，否则又被读为构造偏袒。噪声版作用于全窗口（feature+anchor），这一半无懈可击。
2. **实验 B 口径**：边界带 anchor cells（16.6M 规模）与 Table III 全样本（88M 规模）不可互换——已注明，但审稿人可能要求**同一管线内并排**（soft-gate-bin 加入 official reserve-decision 的 strata），而不是两套数字。这是"官方化"未完成的具体表现。
3. **Table III 还是 legacy 数字**（88.13M/84.58M/83.78M）：clean 口径 99.55M/95.13M/93.82M 已存在却未上稿。零借口级别。
4. **E1/E3 仍是 pilot 口径**：追加三/四明确说"正式投稿前并入官方链路"。本轮实验 B 在 train-only runs 上做了 5-seed 配对 bootstrap（比 pilot 强），但缺 reviewer-stat-pack 链路的 BH-FDR 校正。
5. **统计呈现**：Penmanshiel canonical std 0.40、Kelmarsh canonical std 0.24——必须 median/IQR + 方差披露，否则 mean 误导。
6. 旧问题仍在：全基线表未上稿、单位 MWh 未上稿、算力表缺、ERA5 悬空引用、控制文献为零。

---

## 👤 Reviewer #3（Impact & Pragmatist Critic）

**评分：Soundness 3/4 ｜ Significance 3/4 ｜ Overall 6/10 ｜ Confidence 4/5**

1. **动机落地**（大幅改善）：pitch 稀疏农场的谱系证据把"公开数据缺控制字段"的审计缺口坐实——55% pitch 覆盖的 Kelmarsh 仍能恢复边界，运营价值直接。Kelmarsh 的限电归因流（93.7% 覆盖）仍是未用的 grounding 素材，可加分。
2. **代价披露**：signature_full 的 RMSE 代价（+11.9）与 signature_core（+72.2）已披露；但正文应加一句"运营方选择：以 5% 预测精度换退化鲁棒 + 无物理箱 reserve"。
3. **降级路径**：若 TSTE 不收，这套"诚实边界 + 负结果 + 审计协议 + 软风险定价"对 Applied Energy / Wind Energy 是强投稿——不算废稿。
4. **写作自我消耗仍在**：cover letter 标题与稿件不一致、Kelmarsh 误述（旧版"lacks pitch"）需同步修。

---

## 📋 Checklist 审计（基于全证据链）

- [✅] **负对照完备性**：4 个 shuffled + 2 个 farms shuffled，全部随机水平。
- [✅] **场景语义**：实验 A 公平退化修复 Table II 语义。
- [✅] **跨场可复制性**：LHB 同阈值 3 变体 + 负对照；Kelmarsh/Penmanshiel 谱系。
- [❌] **稿证一致性**：A6 旧符号、Table III legacy、摘要"fail the gates"、部署门表 0.4877 旧叙事、two-packages 框架。
- [❌] **贡献-证据对齐**：摘要/贡献段未写三大新贡献；E1/E3 未官方化。
- [⚠️] **统计呈现**：farms canonical 大方差未 median/IQR 化；实验 B 未并入官方 strata。
- [❌] **呈现补齐**：全基线表、单位、算力表、控制文献、ERA5 节、图重生成、cover letter。
- [✅] **数据许可/复现**：窗口重建规则预注册、脚本入库、guard 全绿。

---

## 🚨 P0 清单（按投稿致命度排序）

1. **[P0] 稿证切换**（旧但未修）：A6 两行改 -0.109 [-0.280,+0.084] p=0.352；Table III 换 clean 口径 99.55M/95.13M/93.82M；摘要"Kelmarsh and Penmanshiel fail the observability gates"改为谱系表述；部署门表按 windowfix 0.5574 + 分方向改写；two-packages 框架合并为 train-only 单一证据包。
2. **[P0] 贡献段重写**（方向 1 落地）：摘要+三条贡献改为 (a) 软边界风险后验与公平退化鲁棒（0.933 vs 0.196）；(b) 不确定度定价（无物理箱 reserve -0.3~-0.6M）；(c) 可观测性谱系（55% pitch 仍可恢复）。
3. **[P0] 实验 A 延迟语义形式化**：正文定义"confirming-stream delay vs archived-history"场景，防止构造偏袒质疑。
4. **[P0] E1/E3 官方化**：并入 reviewer-stat-pack 链路 + BH-FDR；实验 B 加 soft-gate-bin/entropy-bin/maxprob-bin 到官方 reserve strata（或明确两套口径并列）。
5. **[P0] 统计呈现**：farms 表 median/IQR + 坍缩/方差披露；Penmanshiel core 0.195 "below criterion, 4400× chance" 措辞照实。
6. **[P0] 呈现补齐**：全基线表（clean MoE 行）、单位 MWh、算力表、4-6 篇控制文献、ERA5 节、重生成图、cover letter 标题与 Kelmarsh 误述。

## 🧪 最小补实验清单

| 优先级 | 实验 | 成本 | 翻转 |
| :--- | :--- | :--- | :--- |
| 1 | 证据切换 + 贡献重写（纯写作） | 低 | P0-1/2 |
| 2 | E1/E3 官方化 + BH-FDR（脚本已有） | 低-中 | P0-4 |
| 3 | 实验 A 补充：延迟也作用于历史窗口的变体（公平性上限） | 低（replay 改一行） | R2-1 |
| 4 | Kelmarsh 限电归因流 grounding | 中 | R3-1 |
| 5 | 1 个 2025+ 风电 SOTA 基线 | 中高 | R2 |

## 🛡️ Rebuttal 弹药库（现成）

- **循环性**："withheld-channel probe: NMI 0.561 with Wspd/Pab removed, 4e-6 under permuted labels; cross-farm replication at 0.674/0.575 with the same controls."
- **创新性**："the threshold rule degrades 80% under six-step delay while the routed posterior degrades 3.9%; uncertainty-only binning beats global reserve by 0.31-0.33M without any physical bin."
- **鲁棒性**："negative controls at chance level at all four farms rule out input-distribution artefacts."
- **诚实性**："we disclose that the clean rule outperforms the gate (1.000 vs 0.971), that Penmanshiel signature_core sits below the 0.20 criterion, and that learned binning raises violation by 0.001."

## ⚠️ Kill / Pivot 条件

- 若实验 A 的"延迟作用于历史窗口"变体显示 gate 优势消失 → 延迟叙事退回"仅确认流延迟"语义，鲁棒性贡献降级为噪声部分（0.951 vs 0.680 仍成立）。
- 若 E1/E3 官方化后软信号不显著 → 贡献退化为"协议性 + 负结果"，转 Applied Energy。
- 若谱系在窗口稳健性扫描（多起始窗口）下不保持 → 谱系叙事改为单窗口描述。
