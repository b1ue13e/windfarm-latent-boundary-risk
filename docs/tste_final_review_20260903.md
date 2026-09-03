# 🏛️ 终审 Reviewer 模拟（2026-09-03 终态：证据切换 + 软边界风险主线完成）

> 评审对象：`paper_tste_ieee.md` + `paper_tste_supplementary.md` + `cover_letter_tste.md`（2026-09-03 全部修改后）
> 与 09-01 harsh review、09-02 压力测试的关系：两轮的 P0 与新增攻击面均已处置或显式遗留，本轮只评终态。
> 终态证据链：signature-gate（WTB/LHB/Kelmarsh/Penmanshiel + 5 个 shuffled 负对照）、公平退化（实验 A）、不确定度 reserve（实验 B）、E1 软后验（官方化）、E3 soft-gate-bin（官方化）、全基线表、控制文献、ERA5 节、算力披露。

---

## 📊 Executive Summary 与录用概率校准

| 情形 | TSTE 概率 | 风险 | 说明 |
| :--- | :--- | :--- | :--- |
| 当前稿（本轮终态，图未重生成） | **~55-65%** | Medium | 稿证已一致、主线已迁移；残留 3 个机械/防守项 |
| 投稿前完成图重生成 + 窗口稳健性扫描 + 历史窗口延迟变体 | **~65-75%** | Low-Medium | 把最后三个可攻击面全部封死 |
| 转投 Applied Energy / Wind Energy | ~75-85% | Low | 现有完成度对二区刊已经充分 |

**一句话裁决**：从 09-01 的"仓库翻案、稿件未签收"到今天的终态，稿件的**创新性质疑、循环性质疑、场景语义质疑全部有正面证据回应**。剩余风险不再是"这篇论文没有贡献"，而是三个具体的、低成本的防守实验和资产更新。这不是 desk-reject 形态，是正常 Major Revision 前的自修清单。

---

## 👤 Reviewer #1（Theory & Novelty Hawk）

**评分：Soundness 3/4 ｜ Novelty 3/4 ｜ Overall 6.5/10 ｜ Confidence 4/5**

**已被正面证据化解的攻击**：
1. 循环性/阈值重放 → signature-gate 0.561（去定义通道）+ 5 个 shuffled 负对照全随机。**失效**。
2. "贡献只是工程叙事" → 三大贡献全部有"规则/物理箱给不出"的证据：(a) 公平退化下 rule 崩 80%、gate 掉 3.9%；(b) 纯不确定度分箱 vs global CI 显著、无需物理箱；(c) 55% pitch 农场恢复边界。**失效**。
3. 谱系非单调（Penmanshiel 78% < Kelmarsh 55%）→ 已在正文/Table A9d 主动解释（后果通道质量调制）+ 方差披露。**转为正面披露**。

**残余火点（2 个）**：
1. **Pab_std 作为后果通道的辩护只有一句**："blade-pitch dispersion is itself a control consequence that may correlate with the boundary"（Limitations）。审稿人仍可追问"signature_core 的 0.367/0.575 有多少来自 Pab_std？"→ 建议补一个 `signature_core_no_pab_std` 变体（代码现成，~2h）或至少在补充材料加 Pab_std 遮蔽行。
2. **实验 A 的历史窗口延迟边界**：正文已形式化"confirming-stream delay vs archived history"场景，但审稿人可能要求 upper bound（历史窗口也延迟）。→ 补延迟也作用于历史窗口的变体（replay 改一行）。

---

## 👤 Reviewer #2（Empirical & Baseline Nitpicker）

**评分：Soundness 3.5/4 ｜ Rigor 3/4 ｜ Overall 6/10 ｜ Confidence 5/5**

**已解决的**：A6 符号翻转（-0.109/0.352 上稿）、Table III clean 口径 + Full-MoE 复现行、全基线表 A13、单位 MWh（A12）、算力披露、双包合并、median/IQR 与坍缩披露（farms 表）、负对照完备（5 个 shuffled）。

**残余火点（按严重度）**：
1. **[中] 窗口稳健性扫描缺失**（旧 P0-R3-4 原样留存）：Penmanshiel day 720 / Kelmarsh day 120 的窗口规则是预注册的、无结果依赖的，但审稿人仍可攻击"挑窗口"。补 top-K 可观测窗口 + 随机窗口对照的 NMI 分布（纯分析，已有缓存，~2-4h GPU）。
2. **[低] 实验 B 未并入官方 reserve strata**：A11b 已注明口径不可与 Table III 互换。审稿人可能要求同管线并排；或接受明确口径分离。最低成本方案：在 A11b 脚注加"边界带口径与 Table III 全样本口径的差异说明"（已有）+ 提交时声明两套管线。
3. **[低] Table A13 的 MoE train-only 行 MAE 缺失**（footnote 已说明在 archived run tables）——可接受，但最好补上。
4. **[低] 图年代**（见 P0 清单）：figure2/4/5/6 仍是 legacy 产物，正文数字已更新 → 图内数字与正文会不一致，投稿前必须重生成。

---

## 👤 Reviewer #3（Impact & Pragmatist Critic）

**评分：Soundness 3.5/4 ｜ Significance 3/4 ｜ Overall 6.5/10 ｜ Confidence 4/5**

**已解决的**：动机落地（55% pitch 农场仍可恢复 = 公开数据缺控制字段的审计缺口坐实）、代价披露（RMSE +11.9/+72.2、violation +0.001、precision 0.630 vs classifier 0.879）、诚实边界五条（cover letter）。

**残余火点（1 个）**：
1. **Kelmarsh 限电归因流仍未用**（93.7% 覆盖的 `Lost Production to Curtailment` 真实工业标签）：这是把"标签延迟"动机落到真实工业 grounding 的现成素材。不堵死也行（公平退化已修场景语义），但加上会是 R3 的强加分项。成本：数据在本地，需人工核对字段语义（中）。

---

## 📋 终态 Checklist

- [✅] 稿证一致性（A6/Table III/摘要/部署门/cover letter 已全部切换，grep 无 legacy 残留）
- [✅] 负对照完备性（5 个 shuffled）
- [✅] 场景语义（公平退化 + 形式化定义）
- [✅] 贡献-证据对齐（三大贡献 = 摘要/贡献段/结论/reserve/软后验段）
- [✅] 统计呈现（5 seeds、CI、median/IQR、坍缩/方差披露）
- [✅] 全基线表 / 单位 / 算力 / 控制文献 / ERA5 节 / cover letter
- [⚠️] 图年代（figure2/4/5/6 legacy，未重生成）
- [⚠️] 窗口稳健性扫描（未跑）
- [⚠️] Pab_std 遮蔽变体与历史窗口延迟变体（未跑）

---

## 🚨 剩余 P0（投稿前必须，全部低成本）

1. **[P0] 图重生成**：figure2/4/5/6 用 train-only 产物重出（routing evidence、reserve 曲线、机制面板）。这是投稿前唯一不可省略的资产更新。
2. **[P0] 窗口稳健性扫描**：Penmanshiel/Kelmarsh 的 top-K 可观测窗口 + 随机窗口对照 NMI 分布，把"挑窗口"攻击封死（脚本可从 `scripts/rebuild_obs_windows.py` 扩展）。
3. **[P0] 两个低成本消融**：(a) `signature_core_no_pab_std`（Pab_std 遮蔽）；(b) 实验 A 的"历史窗口也延迟"upper-bound 变体。都是现成代码改参数，各 ~2h。

## 🧪 可选加分（不进 P0）

- Kelmarsh 限电归因流 grounding（R3 强加分）。
- 实验 B 并入官方 reserve strata（或提交时声明口径分离）。
- Table A13 MoE 行补 MAE。

## 🛡️ Rebuttal 弹药（终态版，已就绪）

- 循环性 → signature-gate + 5 shuffled 对照。
- 创新性 → "rule degrades 80%, route 3.9%; uncertainty-only bins beat global without physical bins; boundary recoverable at 55% pitch coverage"。
- 构造偏袒 → 公平退化形式化定义 + 噪声作用于全窗口。
- 挑窗口 → 预注册窗口规则（输入掩码 only）+ 稳健性扫描（P0-2 完成后）。
- 挑数据 → 负对照全部随机水平。
- 统计 → 5 seeds + bootstrap CI + BH 家族声明 + median/IQR。

## ⚠️ Kill / Pivot 条件（终态）

- 窗口稳健性扫描若显示仅单窗口过门 → 谱系叙事退回单窗口描述，仍不致命。
- `signature_core_no_pab_std` 若崩塌到 chance → Pab_std 成为 core 信号的主载体，Limitations 的披露句必须升级为正式消融披露。
- 历史窗口延迟变体若 gate 优势消失 → 延迟鲁棒性贡献缩窄为噪声部分（0.951 vs 0.680 仍成立）。
