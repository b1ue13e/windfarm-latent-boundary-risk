# 方向 1：软边界风险主线 — 论文重构大纲

> 日期：2026-09-03 ｜ 定位：把主贡献从"硬路由外延"迁移为"软边界风险仪表"，方向 2（pitch 稀疏农场 signature）并入部署谱系叙事。
> 实验进行中：`25979:artifacts/signature_gate_farms_runs_20260903/`（Penmanshiel 4 变体 + Kelmarsh 3 变体 × 5 seeds）

## 0. 一句话新故事

> 确定性阈值规则只能说"这台风机现在是 MPPT"；我们的路由后验能说"它现在是 MPPT，但离 pitch 边界还有多远、这个判断有多不确定、由此带来的备用金风险溢价是多少"——而且这一切在定义通道（风速/桨距）缺失或延迟时依然可算。

规则 → 标签（1 bit）；路由 → **风险后验（连续 + 不确定度）**。这就是规则原理上给不出的增量，也是全篇唯一的进攻性创新点。

## 1. 标题与摘要重构

**Title 候选**（三选一，待定）：
1. `Graded Operating-Boundary Risk from SCADA-Anchored Routing for Wind-Turbine Reserve Diagnosis`
2. `Soft Boundary-Risk Routing: Identifying the MPPT-to-Pitch Transition Without Its Defining Channels`
3. 保守版：保留原题，加副标题 `...: From Hard Regime Labels to Graded Boundary Risk`

**摘要骨架**（按新故事重写）：
1. 问题：确认标签流延迟/缺失时，MPPT-to-pitch 边界风险不可见。
2. 发现一（signature）：边界指纹存在于后果通道——遮蔽 Wspd/Pab_mean 后 NMI 仍 0.561（WTB）/0.674（LHB），打乱标签崩塌到 4e-6/1.9e-4；pitch 稀疏农场（Penmanshiel 68%）的结果待回填。
3. 发现二（soft risk）：规则类内，路由后验与结果残差 Spearman ρ=0.183（5/5 同号）；路由不确定度与预测误差 ρ=0.391。
4. 发现三（reserve）：软分箱备用金在 ρ=10 下较 global 省 ~6%（CI 显著），与 physical-bin 打平但不需要预先定义物理箱。
5. 边界声明：不是 forecaster 替代品、不是 detector 替代品、不是 dispatch 优化器；是"规则之外的类内风险仪表 + 跨可观测性谱系的部署分级"。

## 2. 贡献三条（重写）

1. **Soft boundary-risk routing**：SCADA-anchored 路由后验作为规则类内的分级边界风险信号（含不确定度定价），在定义通道缺失时仍可计算（signature-gate 证据）。
2. **Deployment spectrum, not go/no-go**：把"pitch 不可观测 → 直接 no-go"升级为"signature 强度随 pitch 覆盖率分级的部署谱系"（LHB 0.674 / Kelmarsh ? / Penmanshiel ? / WTB 0.561）。
3. **Validation-frozen reserve consequence**：软分箱 reserve 诊断（-617k CI 显著），物理箱对照 + 同模型 global 对照 + 跨骨架对照三重边界。

## 3. 章节映射（改动清单）

| 章节 | 现状 | 改为 |
| :--- | :--- | :--- |
| Abstract | "auditable assignment... declared operating boundary" | 软风险主线 + signature 数字 |
| Introduction L47-53 | 三贡献以硬路由为中心 | 按上节重写；引用 E1/E3 数字 |
| "Withheld-channel signature recovery" | 已有 | 加 Penmanshiel/Kelmarsh 结果；改为"boundary signature across the observability spectrum" |
| 新增小节 "Soft boundary-risk stratification" | 无 | 放 E1（类内 ρ=0.183 + 分歧细胞）、E3 不确定度定价 ρ=0.391 |
| Reserve 节 | gate-bin vs global/physical-bin | 补充软分箱结果、说明"不需要物理箱先验"的部署含义 |
| Discussion 部署门表 | 0.4877 不过门（旧） | 改：windowfix 0.5574 过门 + 分方向表 + signature 强度分级行 |
| Limitations | 循环性防御段 | 改为：软后验在规则类内有效、类外不声称；signature 谱系未含无 pitch 农场 |
| Conclusion | traceable route-to-reserve diagnostic | 软边界风险仪表 + 部署谱系 |

## 4. 关键措辞红线（避免被审稿人抓）

- 不写 "discovers the boundary without anchors"——写 "recovers a graded boundary-risk signal when the defining channels are unavailable or delayed"。
- 不写 "soft binning beats physical bins"——写 "matches physical-bin cost without requiring pre-defined physical bins, and dominates global"。
- 不写 "transfer"——写 "mechanism replication under a shared threshold definition"。
- E1/E3 数字必须带 CI 和 5/5 同号披露；软分箱必须带 CI 不跨零声明。
- signature_core 的坍缩（WTB 3/5）照实披露，LHB 0/5 作为对照证据。

## 5. 等实验回填的位置

- 主文 Table（signature-gate）：加 Penmanshiel/Kelmarsh 行。
- 补充材料：Table A9d（pitch-sparse farm signature probe）。
- Discussion 部署谱系表：NMI 强度列 LHB 0.975/0.674/0.575、Kelmarsh ?/?/?、Penmanshiel ?/?/?。
- 判据：Penmanshiel signature_core NMI ≥ 0.20 即支持"pitch 稀疏农场边界可恢复"；< 0.05 则退回 honest negative。

## 6. 执行顺序

1. 等 farms 实验（25979，~6-9h）→ 回填数字。
2. E1/E3 数字从 `docs/tste_trainonly_rerun_results_20260830.md` 追加三取出，官方化进主稿（先核对 CI 表述）。
3. 按本大纲逐章改写 `paper_tste_ieee.md` + 补充材料。
4. 同步更新 cover letter 标题与贡献。
5. 重跑 topconf-reviewer 校验。
