# 独立确认来源的文档筛选

2026-10-18。仅资料核验，不是已激活的确认协议。不替换 E07 的原 WTB 队列；没有下载、查看或评估新场站测量序列。

| 候选 | 已核实的来源事实 | 未解决的资格/适用性 | 当前处置 |
|---|---|---|---|
| Hill of Towie v2.1.0 | RES 发布、CC BY4.0；21机组；公开年度包至2026；字典明确UTC、10分钟区间末端。具备风速、有功、无功、逐叶片pitch和部分年份运行状态，另有风场电表字段 | 实际字段完整性、单位/统计后缀、时钟对应、运行状态代码的物理含义、跨表可对齐性及项目既往使用范围仍需核验；没有数据级资格判定 | 优先候选，仅文档审查。若另立确认研究，应先冻结场站/时段、主对照和转换规则，再接触评估测量值 |
| Aventa AV-7 | 发布方说明有wind/power/pitch/status，单台6kW研究机组，2025年约一个月1Hz记录 | 与商业风场尺度不同；文档列出的通道未提供无功，不能原样完成全部对照；没有原始数据核验 | 可作受限诊断候选，不作为当前全对照默认来源 |

Hill of Towie 的状态字段和独立表计为脱离风速阈值标签、核对聚合任务提供可能性，这是设计推断，不是已验证的决策价值。2026期间有控制升级和周期切换，不能混作平稳基准；是否选2025等时期须在独立协议中事先固定，不能根据拟合效果择期。

本次在 docs/experiments/scripts/manuscript 的文本检索未发现 Hill of Towie 名称或上述记录号；这只是限定范围检索，不证明全项目或任何人从未查看。应保留“此前使用范围待核实”，不能用无日志冒充未查看证明。

## 可核验来源与角色

- **adjacent / 数据来源**：Clerc, A.; Lingkan, E. Hill of Towie wind farm open dataset, v2.1.0, 2026-09-08, DOI 10.5281/zenodo.22662930。[发布记录](https://zenodo.org/records/22662930)。
- **adjacent / 字段和时钟定义**：[发布方数据字典](https://zenodo.org/records/22662930/files/Hill_of_Towie_data_dictionary.md?download=1)。
- **adjacent / 聚合字段定义**：[发布方电表字典](https://zenodo.org/records/22662930/files/Hill_of_Towie_grid_fields_description.csv?download=1)。
- **adjacent / 数据来源**：Barber, S.; Hammer, F.; Marykovskiy, Y. Aventa AV-7 (6kW) IET-OST Research Wind Turbine SCADA with Static Yaw Offset, v2, 2025-08-04, DOI10.5281/zenodo.16738078。[发布记录](https://zenodo.org/records/16738078)。

本文件不把来源文档中的性能描述作本项目证据，不升级科学契约；正式引用须进入指定权威文献/数据矩阵。
