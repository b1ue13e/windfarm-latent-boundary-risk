# 实验 E01：EXP-01: 外部场站相同信息集配对直接条件分位数对照

- 假设：H1
- 目的：在外部风场（Penmanshiel与Kelmarsh）上，检验去除时空图交互的局部风速分箱基线是否足以完成备用筛查，以及跨场站迁移表示相较于局部条件基准是否缺乏决策增益。
- 创建：2026-10-11T08:56:57.758Z

## 设计
1. 数据审计：检查Penmanshiel与Kelmarsh本地风速缺失率（<=20%硬性停止检查）并锁定信息集（风速、功率、气温，pitch扣留）
2. 基线实现：校准本地10-bin风速条件分位数基线，以及**No-Graph Architectural Control**（单机MLP，4,865 参数；非容量等价对照，仅切断风机间空间图交互的架构对照）
3. 模型评估：在Penmanshiel与Kelmarsh全测试集上分别评估跨场站迁移STGQ-Modular、本地微调STGQ-Modular、Site-Local Wspd-Bins与No-Graph Architectural Control在5种子(201-205)及h=1,h=6下的PSREI与违约率
4. 统计推断：执行场站级日聚类Block Bootstrap (B=2000)，计算ΔPSREI与ΔV的配对估计量及95%置信区间；跨种子联合推断使用两层级 hierarchical bootstrap
5. 工件沉淀：生成目标工件artifacts/external_matched_control_benchmark.csv并完成证据归档

## 协议修订说明（2026-10-13）
原始 v1 协议以 transferred challenger 自身预测推导 shortfall target，违反冻结点预测分离，已作废。
Corrected v2 改用独立 site-specific frozen point forecast，并由 canonical external cache 按 anchor index
重建目标与掩码。v1 数值不得引用；“跨场站普遍规律”的表述被 `docs/SCIENTIFIC_CONTRACT.md` 禁止。
本实验不得用于主张“空间图结构具有因果必要性”（参数量与训练协议均不等价，锁定为 UNPROVEN / NOT ESTABLISHED）。

## 预期结果

## 观察（Observation）
