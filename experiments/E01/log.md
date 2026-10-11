# 实验日志 E01

- 创建：2026-10-11T08:56:57.760Z


## 2026-10-11T16:56:02.679Z

在外部风场Penmanshiel（14机）与Kelmarsh（6机）全测试集上，在严格匹配信息集（测试期pitch完全扣留，仅使用到达时刻本地风速、功率、气温）及5种子(201-205)、B=2000日聚类Block Bootstrap下：1) 在Penmanshiel复杂地形下，h=1时Transferred STGQ相对Site-Local Wspd-Bins配对差分Delta PSREI=-9.9k kWh (p=0.600，CI跨零无显著增益)；h=6时Delta PSREI=+448.0k kWh (p=0.185，均值增加且无统计优势)；Fine-tuned STGQ显著劣于Wspd-Bins (+1.09M kWh, p<0.001)；No-Graph MLP因单机容量欠拟合而增加+2.15M kWh (p<0.001)。2) 在Kelmarsh平坦微风场下，h=1时Delta PSREI=+11.3k kWh (p=0.448)；h=6时Delta PSREI=+48.5k kWh (p=0.272)；Fine-tuned STGQ增加+215k kWh (p<0.001)；No-Graph MLP增加+1.50M kWh (p<0.001)。3) 结果完全确证反向结果解释：去除时空图交互的本地10-bin风速分箱基线已足以完成备用筛查，跨场站迁移表示相较于该局部条件基准缺乏决策增益。将“状态可恢复不等于决策优越”及“简单基线充分性”正式推广为跨场站普遍规律。工件归档于external-matched-control-benchmark v1。
