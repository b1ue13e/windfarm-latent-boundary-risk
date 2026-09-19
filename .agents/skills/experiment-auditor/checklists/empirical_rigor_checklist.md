# Top-Tier Conference Empirical Rigor Checklist

在使用本 Skill 时，对照以下清单进行打分与逐项排查：

## 1. Baseline 覆盖度 (Baseline Coverage)
- [ ] 是否包含了本领域公认的标准 Benchmark 数据集（至少 3-5 个不同规模与分布的数据集）？
- [ ] 是否对比了 2024-2026 年发表在顶级会议（NeurIPS/ICLR/ICML/KDD/CVPR）上的最新工作？
- [ ] Baseline 是否经过了合理的超参数调优（Fair hyperparameter tuning on validation set）？
- [ ] Baseline 代码来源是否为官方开源实现？

## 2. 统计显著性与复现性 (Statistical Rigor & Reproducibility)
- [ ] 所有表格数据是否为 $\ge 5$ 个独立运行实验的均值与标准差（Mean $\pm$ Std）？
- [ ] 是否在文本中注明了随机种子的设置与划分方式？
- [ ] 关键性能提升是否通过了统计学显著性检验（$p$-value $< 0.05$）？
- [ ] 是否提供了详细的 Hardware 配置（GPU 型号、RAM、CUDA 版本）与运行时间（Wall-clock training/inference time）？

## 3. 消融与鲁棒性分析 (Ablations & Robustness)
- [ ] 是否证明了每一个新提出的组件/Loss项都提供了不可替代的正面贡献？
- [ ] 是否进行了噪声注入、丢包、Out-of-Distribution (OOD) 分布偏移测试？
- [ ] 是否给出了模型在不同数据规模（Data Scaling）下的复杂度曲线？
- [ ] 增益是否来源于参数量增加？（是否与同等参数量的 baseline 进行了对齐对比？）
