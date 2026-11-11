# 四条件 V2 执行与数值证据核验

范围：当前登记的 RAW-FACTORIAL-FOUR-CONDITIONS-V2。本文不认证旧版错误结果、
全部46项产物或整篇论文的科学结论。

## 已直接核验

- clean、delay6、pitch_withheld、delay6_pitch_withheld，各种子201–205：20份真实
  EXECUTED/exit0收据，另有1份成功汇总收据。
- 880条逐种子结果、176组五种子描述汇总；h6主终点、h1次终点，Full与固定
  raw-wind边界诊断总体，11个变体（J是C的别名，不是独立方法）。
- PBS数值审计242732.cm实际F/exit0。保存动作→储备、短缺、PSREI、违约率及全部
  原生日块均精确重算；共同目标、掩码、时刻、节点、总体及控制代数检查通过。
- A/B保存的context和实际训练head权重，按原4096批次CPU推理和原裁剪精确复推动作；
  五轮训练历史、种子及相同抽样索引均检查。本审计只读已训练权重和产物。
- 不引入显著性、收益优越性、架构必要性或实际部署效果结论。K读同一退化批次的
  到达风速，但它是wind-only诊断基线，并非fresh-pitch条件下的最强基线。

审计源码：[audit_metis_factorial_results.py](../scripts/audit_metis_factorial_results.py)，
提交24a2de4，SHA256
`b687825d4c5169a317994cf2577888b6c233bdccf773ac9b6640ca9c85ac2e52`。
来源：[完整审计报告](../artifacts/metis_factorial_numeric_audit_20261015_attempt2/report.json)、
[完整审计输出](../artifacts/metis_factorial_numeric_audit_20261015_attempt2/audit.stdout)。

## 数值表示与核验边界

逐run CSV按round-trip解析，与保存动作计算值精确比较；汇总阶段单独重放原汇总器
实际使用的默认pandas CSV解析器再groupby。报告记录846个数值格的解析表示差异。
没有修改这些文件或拟合容差；两种实际实现阶段分别精确核验。

审计复用冻结的分箱、分类和日块函数，证明的是独立执行及产物一致性，不能表述为
完全独立的算法实现。独立角色证据审查给出限域PASS；未认证整篇科学完成。

最终快照20261015T142324Z_4d5e7b85的533个文件、28对完整PBS输出流逐项SHA通过；
报告、审计源码、20份收据、汇总导出的全部文件均与其清单绑定。
[核验清单](../artifacts/metis_heartbeat_20261015_2153/numeric_verification.json)。
[逐种子结果](../artifacts/metis_core_recovery_20261015_attempt1/factorial_result_export/aggregate/all_seed_results.csv)、
[完整汇总](../artifacts/metis_core_recovery_20261015_attempt1/factorial_result_export/aggregate/summary.csv)
保留全部结果，不按方向筛选。

## 失败与恢复记录

原核心242595因缺少json导入在序列化时失败。原强基线完整合并stdout/stderr、代码、
环境、配置和部分输出已保留；11文件失败归档独立SHA通过。修复仅增加import json，
部署在metis_execution/recovery工具目录，未改冻结scripts/windfarm_moe。
真实PBS预检242627通过后，强基线新收据strong_baseline_retry_import_v1退出0，
原失败目录不变。核心恢复242628继续执行channels、EXP02、EXP03；其他实验仍未结束。

原四条件数组242602的终态缺少Exit_status，调度终止原因仍UNKNOWN。其真实完成的
clean201–204四项保留；仅16个从未执行的索引4–19续排到242630，实际退出0。
原未执行汇总242603在保存调度元数据后取消，新汇总242631退出0。
不把原未知调度状态补写为成功，不把新成功覆盖到原失败收据。

第一批45个主干/外部预测模型的产物已由PBS242626核验通过；这不替代剩余诊断、
外部决策、统计、46项coverage、论文逐项核对和最终scientific-falsifier/证据门控。
科学合同、种子、基线、指标、总体、数值门槛和不确定性程序均未为结果改动。
