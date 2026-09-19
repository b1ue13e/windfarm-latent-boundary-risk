# Experiment Plan Template (科研实验规划模板)

## 1. 核心假设体系
- **主假设 (H1)**：在 [Failure Condition] 下，[新方法] 相比 [主要Baseline] 能将 [主指标] 提升至少 [X%]。
- **次假设 (H2)**：[关键组件 A] 的引入有效降低了 [中间物理量/误差项]。
- **反证假设 (H0)**：性能提升仅源于参数量增加或更长的训练周期。

## 2. 实验矩阵设计
| 实验编号 | 实验类型 | 模型变体 | 测试场景/数据集 | 评测指标 | 目标回答的问题 |
|---|---|---|---|---|---|
| EXP-01 | 主实验对比 | SOTA Baselines vs. Ours | Benchmark A, B | Accuracy, F1, Latency | 本方法是否全面优于主流基线？ |
| EXP-02 | 压力测试 | Baseline vs. Ours | Corrupted / OOD Split | Robustness Drop % | 在极端失效条件下是否稳健？ |
| EXP-03 | 组件消融 | Full, w/o A, w/o B | Benchmark A | Accuracy, Convergence | 每个创新模块是否真正发挥作用？ |
| EXP-04 | 效率与成本 | Baseline vs. Ours | Standard Setup | FLOPs, Memory, Train Time | 性能提升的计算代价是否合理？ |

## 3. 严谨性与防泄漏自查
- [ ] 数据划分（Train/Val/Test）是否严格隔离？时间序列是否依序划分？
- [ ] 归一化均值/方差是否仅由训练集计算？
- [ ] 是否在 5 个以上随机种子下运行并记录 Mean ± Std？
- [ ] 是否执行配对 t 检验或 Wilcoxon 检验以验证显著性（p < 0.05）？
