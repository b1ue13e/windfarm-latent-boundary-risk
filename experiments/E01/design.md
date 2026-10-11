# 实验 E01：EXP-01: 外部场站相同信息集配对直接条件分位数对照

- 假设：H1
- 目的：在外部风场（Penmanshiel与Kelmarsh）上，检验去除时空图交互的局部风速分箱基线是否足以完成备用筛查，以及跨场站迁移表示相较于局部条件基准是否缺乏决策增益。
- 创建：2026-10-11T08:56:57.758Z

## 设计
1. 数据审计：检查Penmanshiel与Kelmarsh本地风速缺失率（<=20%硬性停止检查）并锁定信息集（风速、功率、气温，pitch扣留）
2. 基线实现：校准本地10-bin风速条件分位数基线与容量匹配单机No-Graph MLP基线
3. 模型评估：在Penmanshiel与Kelmarsh全测试集上分别评估跨场站迁移STGQ-Modular、本地微调STGQ-Modular、Site-Local Wspd-Bins与No-Graph MLP在5种子(201-205)及h=1,h=6下的PSREI与违约率
4. 统计推断：执行场站级日聚类Block Bootstrap (B=2000)，计算ΔPSREI与ΔV的配对估计量及95%置信区间
5. 工件沉淀：生成目标工件artifacts/external_matched_control_benchmark.csv并完成证据归档

## 预期结果

## 观察（Observation）
