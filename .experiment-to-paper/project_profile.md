# 项目证据画像（2026-09-05）

## 科学问题

风机从最大功率点跟踪（MPPT）进入变桨控制的边界附近，确认运行状态的风速/桨距通道可能延迟、受噪声影响或覆盖不完整。本文研究的不是新的低 RMSE 预测器，而是：能否让功率预测器同时产生一个可审计的边界风险后验，并在确认流退化时仍支持边界识别和备用筛查。

## 建议锁定的研究对象

**与功率预测联合学习的软边界风险后验（jointly learned boundary-risk posterior）**。

MoE 路由只是该后验的一种实现。现有对照显示：

- 定价信息主要来自联合学习/共享表征，而不是路由本身；
- 确认流退化下的识别鲁棒性主要来自路由结构；
- 物理连续量在干净、完整观测下仍是更强定价基线；
- 低 RMSE 预测器仍应作为生产预测骨干。

## 实验契约

- 主数据：KDD Cup 2022 / SDWPF WTB，134 台风机，245 天，10 分钟粒度。
- 外部场站：ENGIE La Haute Borne、Kelmarsh、Penmanshiel。
- 对照数据：ERA5，仅作为可观测性对照，不参与备用或跨场部署主张。
- 时间划分：WTB 180/30/35 天 chronological split；历史长 36、预测长 24。
- 主重复策略：WTB 关键神经模型和核心诊断使用 seeds 201--205；部分窗口扫描为 3 seeds。
- 主指标：RMSE/MAE、NMI/ARI、early-window recall/precision、validation-frozen reserve proxy cost、violation、reserve、shortage。
- 信息边界：输入最晚到 issue time t，目标从 t+1 开始；当前 Patv 可作状态输入，未来 Patv 仅作目标。
- 关键来源边界：headline 应使用 train-only class-weight rerun；legacy strict-cache 仅保留历史对照。

## 证据状态

- **Observed**：仓库表格、JSON、主稿和补充材料中可直接定位的数值。
- **Inferred**：从多个 observed 对照共同得到的机制解释，必须使用“支持/一致于”，不能写成因果定论。
- **Proposed**：尚未完成的外部运营后果、匹配模块化对照和语义修复，不得写入已完成结果。

## 当前成熟度

**Submission-oriented draft（面向投稿的完整稿），但不是无条件 submission-ready。** 构建、页数和 token 数字 guard 已通过；仍有自动 guard 未捕获的语义矛盾与证据口径问题，详见 `docs/paper_result_synthesis_20260905.md`。
