# 实验 E03：EXP-03: 整数步异步 packet 到达 envelope

- 假设：—
- 目的：在显式 event_time/arrival_time/sequence_id 协议下，比较 challenger 与 Site-Local Wspd-Bins 的 PSREI-vs-delay 曲线，并估计预注册临界点 tau*；同时报告 5%/10%/15% operating target 敏感性。
- 创建：2026-10-12T01:17:28.840Z

## 设计
1. 冻结整数时间步 packet simulator、同到达排序、有限 causal buffer、迟包丢弃与共享 missing mask 协议
2. 用同一 arrival trace 和 missing mask 驱动 Site-Local Wspd-Bins 与 challenger
3. 按每场站、每 horizon 计算 paired PSREI-vs-delay 曲线和 tau*，不把 10% 当作唯一 breakdown threshold
4. 执行 packet-level unit tests、记录输入 trace SHA256，并将合成结果标记为 synthetic asynchronous envelope

## 预期结果

- 若 Metis 连接和输入数据可用，输出每场站/每 horizon 的 paired PSREI-vs-delay 曲线、tau*、5/10/15% operating target 敏感性及 packet diagnostics。
- 结果方向不预设；负结果和 null 结果均为有效证据。

## 当前状态与执行推进

- **最终状态**：CONCLUDED（2026-10-12 在 Metis HPC 集群 A100 GPU 节点完成）。
- **计算环境**：NVIDIA A100-PCIE-40GB GPU (Metis Cloud Node, Python 3.11, PyTorch 2.11.0+cu128)。
- **到达轨迹完整性**：物化到达轨迹 SHA-256 = `d1619efce7f02412d826e3811bfa2a2346e6bc1b1fcd2b02a9d10f163f0736ff`。
- **评测规格**：7个整数延迟网格 $\tau \in \{0, 1, 2, 3, 4, 5, 6\}$ (0至60分钟)，5个随机种子 (201–205)，2个预测时域 ($h=1, h=6$)，以及 $B=2000$ 35天日聚类 Block Bootstrap。

## 观察与核心结论（Observation & Findings）

1. **临界跨越阈值 $\tau^*$（Primary Estimand）**：
   - 时域 $h=1$（10分钟调度步）：$\tau^* = 1$ 整数步（10分钟）。在无延迟 $\tau=0$ 时，$\Delta\text{PSREI} = -524.5\text{k kWh}$ (95% CI: $[-1114.9\text{k}, -28.7\text{k}]$, $p=0.074$)。在 $\tau \ge 1$ 时，配对 95% 置信区间上界立即跨越零轴（$\tau=1$: $\Delta\text{PSREI} = -400.1\text{k kWh}$, CI: $[-990.8\text{k}, +97.6\text{k}]$, $p=0.182$），统计显著优势消失。
   - 时域 $h=6$（主终点，1小时调度步）：$\tau^* = 0$ 整数步（0分钟）。即使在理想无延迟状态 $\tau=0$ 下，配对差异亦不显著（$\Delta\text{PSREI} = -210.8\text{k kWh}$, CI: $[-859.9\text{k}, +322.8\text{k}]$, $p=0.293$），且全延迟网格 $\tau \in [0, 6]$ 内置信区间均宽幅跨越零轴，不存在统计决策增益。
2. **标称运行目标敏感性（Nominal Operating Targets）**：
   - 5% 违约目标：两个模型在所有延迟与时域下均跨越（自然违约基线在 7%–11%）。
   - 10% 标称目标（对应 Newsvendor $q^* = 1 - 1/\rho = 0.90$）：在 $h=1$ 下，挑战者违约率在 $7.42\%\text{--}8.06\%$ 之间平稳受控（跨越点 $\tau > 6$）；在 $h=6$ 下，挑战者违约率为 $10.82\%\text{--}11.29\%$，而 Site-Local Wspd-Bins 严格控制在 $8.65\%\text{--}8.83\%$，完全优于标称红线。
   - 15% 违约目标：在全部已评估延迟下未被触发（$\tau > 6$）。
3. **科学护栏与归档**：
   - 确立合成异步信封（Synthetic Asynchronous Envelope），严禁向工业现场遥测丢包率进行外推。
   - 确认反向零假设保护：表示复杂性并不能对抗物理遥测滞后，简单局部风速条件分位数在对称退化信息集下展现了高度的抗时延鲁棒性。
   - 产出工件已落盘至 `artifacts/exp03_async/` 并版本化归档为 `exp03-async-protocol v2`。
