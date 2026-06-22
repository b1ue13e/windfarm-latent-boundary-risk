# AE Major Revision Fail-Safe Strengthening Plan

## 1. Core Position

本项目按 Applied Energy 大修风险来准备，而不是按小修稿来包装。目标不是证明模型在所有指标上赢，而是把证据链补到一个可审稿、可回击、可降级的状态。

核心问题固定为：

> 牺牲一部分预测精度换来的 gate accountability 和 transition-window reserve diagnostic，是否足以构成能源系统贡献？

因此所有新增实验必须服务于三个可审稿问题：

- gate 是否只是读取 `Patv`、`Wspd`、`Pab_mean` 等标签相关锚点。
- reserve diagnostic 是否经得起标准概率或分位数 reserve baseline 的比较。
- boundary diagnostic 是否能转化为一个简单但明确的 operational consequence。

## 2. Non-Negotiable Guardrails

- 不把 routed model 写成 forecasting SOTA。
- 不把外部 Kelmarsh/Penmanshiel 结果写成泛化成功。
- 不把 empirical shortfall quantile 写成 calibrated probabilistic forecast。
- 不隐藏失败实验。失败结果必须转化为 claim boundary。
- 不在没有证据时写 deployment-ready、generalizable physical router 或 reserve policy superiority。
- 所有补强实验先做小规模 smoke/stress test，再决定是否扩到完整表。

## 3. Execution Order

### Phase A: Probability Reserve Baseline, Lowest Risk

先补 reserve baseline，因为它最容易变成可写证据，即使结果不利也不会毁稿。

最低实现：

- LightGBM quantile 或 conformal residual quantile baseline。
- 使用 validation split 冻结分位数或 conformal margin，只在 test split 报告。
- 报告 full sample、boundary anchors、high-ramp 或 late-horizon slice。
- 指标固定为 cost、violation rate、reserve energy、shortage energy。

写作规则：

- 如果 probability baseline 更强，写成 gate-bin reserve 主要是 attribution diagnostic，不是 policy superiority。
- 如果 gate-bin 在 boundary slice 仍有优势，写成 transition-window diagnostic value。
- 如果两者各有 tradeoff，主张放在 cost-violation-reserve-energy frontier，不写单点胜利。

### Phase B: Toy Operational Cost, Medium Risk

第二步把 normalized reserve diagnostic 接到一个简洁 operational toy case。目标是让 AE 审稿人看到能源系统后果，而不是只看到 ML 指标。

最低实现：

- 单风场 imbalance 或 reserve procurement toy model。
- 输入使用已有 point forecast、reserve schedule、actual generation。
- 成本项至少包含 reserve procurement cost 与 shortage/imbalance penalty。
- 不引入完整 OPF、unit commitment 或 market clearing，除非后续明确需要。

写作规则：

- 只说 toy operational consequence，不说真实市场调度结论。
- 重点展示 boundary window 的 cost exposure。
- 如果收益只在 boundary slice 出现，正好支持本文的 bounded diagnostic claim。

### Phase C: Anchor Stress Test, Highest Risk

最后做 anchor stress，因为它最可能暴露 gate 对可观测锚点的依赖，但也是最能消除审稿人攻击的证据。

先做小规模 stress test，不直接开全量 5-seed。

第一批优先级：

- `no-Patv`
- `lagged-Patv`
- `no-Pab_mean`
- `lagged-Pab_mean/Wspd`

最小执行：

- 先 1 seed smoke run。
- 若结果没有完全崩，再扩到 3 seeds。
- 只有当 3 seeds 仍能支持主张时，才扩成 5 seeds 正文表。

写作规则：

- 如果 gate 崩溃，写成 declared-anchor constrained routing，不写 learned physical discovery。
- 如果 gate 部分保持，写成 other SCADA channels provide partial proxy evidence。
- 如果 gate 稳定，才可加强为 learned structure beyond direct anchor observability，但仍不能写成无监督发现。

## 4. Stop And Downgrade Gates

以下结果不视为项目失败，只触发 claim 降级：

- Probability reserve baseline 全面优于 gate-bin：reserve claim 降级为 transition-window attribution diagnostic。
- no/lagged anchor 后 NMI/ARI 大幅下降：routing claim 降级为 anchor-constrained responsibility audit。
- toy cost 只在 boundary slice 有效：贡献限定为 MPPT-to-pitch transition-window risk diagnosis。
- 外部风场仍失败：保留 negative boundary-condition evidence，强调 local calibration gate。

真正需要暂停的情况只有三类：

- 新实验与已有 strict-mask 数据切分不兼容，导致旧证据不可比较。
- reserve baseline 需要重新定义目标或 mask，破坏现有证据表 schema。
- anchor stress test 暗示现有主文存在 target leakage，而不是 issue-time observability。

## 5. Manuscript Rewrite Target

完成补强后，主文应从防守型长稿压缩成 AE 读者能快速判断的结构：

- Problem: MPPT-to-pitch transition creates reserve risk.
- Method: anchor-constrained MoE routing audits operating-boundary responsibility.
- Evidence: routing recovery, anchor stress, probability reserve comparison, toy operational cost, external negative diagnostics.
- Claim: within-WTB boundary auditability and transition-window reserve-risk diagnosis.
- Boundary: not forecasting SOTA, not external deployment generality, not full probabilistic reserve policy.

最终稿的语气应是：

> The router is not a better general forecaster. It is an accountable operating-boundary diagnostic whose value appears in transition-window reserve risk, and whose portability must be re-established under local sensor and control conditions.

## 6. Default Deliverables

若继续执行补强，默认新增以下产物：

- `anchor_stress_smoke.{csv,tex}`
- `reserve_quantile_baseline.{csv,tex}`
- `reserve_toy_operational_cost.{csv,tex}`
- 对应单元测试和 reproduction manifest 条目。
- `paper_draft.md` 中的 Results、Discussion、Limitations 重构。

每一批完成后必须单独提交 git commit，避免实验、正文和编译产物混在一起。
