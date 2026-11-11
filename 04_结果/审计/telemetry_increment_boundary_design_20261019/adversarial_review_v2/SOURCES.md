# 只读证据入口与核验边界

本轮未引入新文献结论；数学反例为自查推导，未运行模拟。以下均是现有文件，不把历史状态替代现行停止决定。

|编号|已读取来源|支持的具体事实|
|S-A|[V2](../PLAN_V2.md)、[主张表](../CLAIM_EVIDENCE_V2.csv)、[矩阵](../CONTROL_MATRIX_V2.csv)、[23项](../OPEN_ITEMS_V2.json)|审查对象、检验职责及缺项，不是实验结果|
|S-B|[科学契约](../../../docs/SCIENTIFIC_CONTRACT.md)、[PROJECT](../../../PROJECT.md)|旧结果范围、停止状态、新主张未确认|
|S-C|[实际独立确认协议](../../../experiments/independent_confirmation_execution_20261019/protocol.json)|旧窗口、seed、point_seed、HGB/MLP超参数、q网格、历史选择和冻结范围|
|S-D|[原来源与目标协议](../../../experiments/independent_confirmation_20261019/decision_protocol.json)|旧UTC十分钟period-END、单位、目标与共同上游时钟；文件旧sealed状态由后续完成记录取代|
|S-E|[子集及MLP源码](../../../windfarm_moe/information_subset.py)|nested_samples按seed抽样；MLP标准化/缺失指示及固定.9 pinball；不能由确定性算法名推断同输入|
|S-F|[开发入口](../../../scripts/run_decision_information_development.py)|learner中的HGB缺失处理、early_stopping=False、quantile=.9|
|S-G|[风险工具](../../../windfarm_moe/risk_frontier.py)|offset_grid对clipped raw取残差higher分位；旧共享块法只是近似|
|S-H|[独立确认模块](../../../windfarm_moe/independent_confirmation.py)、[执行入口](../../../scripts/run_independent_confirmation.py)|特征及point时钟、抽样索引、offset、历史选择、原确认职责|
|S-I|[独立确认报告](../../../analyses/independent_confirmation_execution_20261019/REPORT.md)|旧原结果与五实例/天气推断范围；无新边界结果|
|S-J|[文献矩阵](../literature_matrix.csv)、[检索日志](../search_log.md)|已有foundational/mainstream/adjacent标签；没有核实failing文献；非穷尽新颖性证书|
|S-K|[资源—损失评审](../../14_resource_loss_break_even_review.md)|真实接口价值未建立，不能由旧2%研究容限推出业务验收|

OPEN_ITEM_TRIAGE.csv的evidence栏使用这些文件名及章节/函数作紧凑定位。参数引用仅为已存在的历史设置；本轮没有把它们填入新冻结协议。来源和方案身份由protected_before.json与validation.json记录。
