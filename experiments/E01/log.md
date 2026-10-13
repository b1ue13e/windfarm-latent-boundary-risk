# 实验日志 E01

- 创建�?026-10-11T08:56:57.760Z

> **日志状态说明（2026-10-13，F6 修复�?*
> 本文件下方的 `2026-10-11T16:56:02.679Z` 条目记录的是 **v1 协议**，该协议已在 corrected v2 中作废�?> v1 �?transferred challenger 自身预测推导 shortfall target，违反冻结点预测分离要求，故其数�?> （Penmanshiel h=6 `+448.0k kWh`、Kelmarsh h=6 `+48.5k kWh`�?*不得再被引用**，其“跨场站普遍规律�?> 表述已被 EXP-01 corrected v2 �?`docs/SCIENTIFIC_CONTRACT.md` �?claim ceiling 推翻�?> 当前生效结果见下�?v2 条目�?`docs/EXPERIMENT_REGISTRY.md`（EXP-01）�?
## 2026-10-11T16:56:02.679Z �?【已作废 v1，保留为溯源�?
在外部风场Penmanshiel�?4机）与Kelmarsh�?机）全测试集上，在严格匹配信息集（测试期pitch完全扣留，仅使用到达时刻本地风速、功率、气温）�?种子(201-205)、B=2000日聚类Block Bootstrap下：1) 在Penmanshiel复杂地形下，h=1时Transferred STGQ相对Site-Local Wspd-Bins配对差分Delta PSREI=-9.9k kWh (p=0.600，CI跨零无显著增�?；h=6时Delta PSREI=+448.0k kWh (p=0.185，均值增加且无统计优�?；Fine-tuned STGQ显著劣于Wspd-Bins (+1.09M kWh, p<0.001)；No-Graph MLP因单机容量欠拟合而增�?2.15M kWh (p<0.001)�?) 在Kelmarsh平坦微风场下，h=1时Delta PSREI=+11.3k kWh (p=0.448)；h=6时Delta PSREI=+48.5k kWh (p=0.272)；Fine-tuned STGQ增加+215k kWh (p<0.001)；No-Graph MLP增加+1.50M kWh (p<0.001)�?) 结果完全确证反向结果解释：去除时空图交互的本�?0-bin风速分箱基线已足以完成备用筛查，跨场站迁移表示相较于该局部条件基准缺乏决策增益。将“状态可恢复不等于决策优越”及“简单基线充分性”正式推广为跨场站普遍规律。工件归档于external-matched-control-benchmark v1�?
**作废理由（VERIFIED）：** 该条目仅具历史溯源价值，存在两处不可复用的问题：
1. **协议缺陷�?* v1 �?shortfall target �?transferred challenger 自身预测导出，未满足冻结点预测分离；
2. **越界结论�?* “正式推广为跨场站普遍规律”被 `docs/SCIENTIFIC_CONTRACT.md` �?claim ceiling 明确禁止
   （外场只�?external-validity boundary probe，两场站异质，不得合并为普遍因果规律）�?
## 2026-10-13 �?EXP-01 corrected v2（当前生效结果）

在独�?site-specific frozen point forecast、相同到达时刻信息集（本地风速、功率、气温；测试�?pitch 完全扣留）�?目标与掩码由 canonical external cache �?anchor index 重建�?种子 (201�?05)、B=2000 日聚�?Block Bootstrap 下：

1. **Penmanshiel�?4机）**：h=6 主终�?Site-Local Wspd-Bins 13,742,849 kWh�?种子均值，16.59% viol）；
   Transferred STGQ-Modular ΔPSREI = **+5,321,915 kWh**�?种子均值，p=0.003�?*显著成本惩罚**）；
   Fine-tuned ΔPSREI = �?,527,228 kWh（探索性）；No-Graph Architectural Control ΔPSREI = +16,880,326 kWh（p<0.001）�?   h=1 次终点：Transferred ΔPSREI = +6,571,777 kWh（p<0.001）�?2. **Kelmarsh�?机）**：h=6 主终�?Site-Local Wspd-Bins 3,131,041 kWh�?1.80% viol）；
   Transferred STGQ-Modular ΔPSREI = **+435,684 kWh**（p=0.196�?*无显著增�?*）；
   Fine-tuned ΔPSREI = �?,001 kWh（探索性）；No-Graph Architectural Control ΔPSREI = +3,403,611 kWh（p<0.001）�?3. **联合不确定性（两层�?hierarchical bootstrap，替代逐种子算术平均）**：见
   `artifacts/joint_uncertainty_summary.json` �?`docs/JOINT_UNCERTAINTY_AUDIT_REPORT.md`�?   Penmanshiel h=6 Transferred �?joint 95% CI �?[+2,333.9k, +8,309.9k] kWh，P(Δ�?)=0.000�?   Kelmarsh h=6 Transferred �?joint 95% CI �?[+124.5k, +713.5k] kWh，P(Δ�?)=0.0052�?
**科学结论（场站异质，禁止普遍化）�?* 两个场站均未显示 Transferred STGQ 相对本地 10-bin 风速条件分位数基线�?显著正向决策改善；Penmanshiel 在主终点显著劣于该局部基线，Kelmarsh 差异为正但未达显著�?可保留的负结果表述是“在本协议下，运行状态的可恢复性不推出备用决策优越性，强局部条件分位数是更小、更稳的
充分决策函数”�?*严禁**升级为“所有外部风场都不需要图结构”或“已证明跨场站普遍因果规律”�?
**架构对照的因果边界：** No-Graph Architectural Control�?,865 参数，从 validation 子集训练）与
STGQ-Modular�?10,012 参数�?34 机源域预训练后迁移）在参数量与训练协议上均不等价�?故“空间图结构对外场备用决策质量具有因果必要性”锁定为 `UNPROVEN / NOT ESTABLISHED`
（见 `docs/NO_GRAPH_CONTROL_AUDIT.md` �?4 节与 `docs/SCIENTIFIC_CONTRACT.md`）�?
**工件�?* `artifacts/external_matched_control_benchmark.csv`（corrected v2�?0 行；工件
`external-matched-control-benchmark v2`，SHA256 `596f46e0be8d71ab7a9965dbe4c481cc717b31c083fe288441a9ca9a39c3966e`�?v1 作废但保留为溯源）�?