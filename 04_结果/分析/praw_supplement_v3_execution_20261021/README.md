# V3已执行结果

先读[结果报告](REPORT.md)。本轮已完成10个Praw拟合及固定评价、旧动作工况／134机组组合记账、预定区间；没有改论文、原结果或阈值。

- [主分析端点](primary_comparisons.csv)与[全部端点](all_endpoints.csv)
- [五实例点值](mean_metrics.csv)与[组合点值](group_metrics.csv)
- [主张证据表](CLAIM_EVIDENCE.csv)与[执行状态](STATUS.json)
- [独立数值复核](verification/numeric_reconciliation.json)；复核脚本只消费已存draw与权重，没有生成新抽样
- [取回与哈希核验](verification/retrieval_verified.json)
- [保护记录](verification/protected_final.json)

`metis_results/results/`含完整封存产物。`metis_results.tar.gz`是334MB的完整取回包，属于新生成的派生结果，不含新下载测量；不提交大二进制到Git。

实际执行代码固定于`87fde9b057806c13617a30aeb111b68dea6b4cd1`。提交记录、执行receipt、环境、原索引、新模型、自身offset、动作与推断分母均保留。后续摘要和复核文件不替换这些原输出。
