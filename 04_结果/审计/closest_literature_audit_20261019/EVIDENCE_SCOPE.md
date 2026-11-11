# 一手证据读取范围与本项目入口

本文件记录定位判断的可核查位置，不包含新实验或新统计结果。

|ID|元数据来源|实际内容读取位置|允许使用的判断|
|---|---|---|---|
|L01|[Wiley](https://onlinelibrary.wiley.com/doi/abs/10.1002/we.416)；Crossref|出版社摘要|当前功率概率持续性与额外输入比较已有先例；全文其他分析UNKNOWN|
|L02|[IEEE](https://ieeexplore.ieee.org/abstract/document/9334448)；Crossref|出版社摘要、章节目录|成本／覆盖联合备用优化已有先例；不作全文排他判断|
|L03|[机构发表版](https://publications.polymtl.ca/57338/1/2024_Serrano_Bilevel_optimization_feature_selection_data.pdf)；Crossref|§3.2，PDF第5页式(21)–(25)，引言与§4设计相关段|双层训练／验证决策成本选择，不同于冻结候选的联合统计排除|
|L04|[JMLR元数据](https://www.jmlr.org/papers/v23/21-0403.html)及发表版|§2.4，PDF第12页式(18)–(20)；§2.5；讨论|可接受族与最小成员是明确先行；接受概率与项目联合置信事件不等同|
|L05|[出版社](https://onlinelibrary.wiley.com/doi/abs/10.3982/ecta5771)及[Aarhus作者版](https://pure.au.dk/ws/files/34269366/rp10_76.pdf)|作者版引言、§2、§3假设2（PDF第11页）|集合推断及相关损失比较有先行；其假设不能略去|
|L06|Crossref期刊记录；[作者v5正文](https://arxiv.org/html/2110.01052v5)|§1.1；§2.1–2.4，命题6|多风险检验与弃权已有先行；需有效p值和声明校准条件|
|L07|[Springer发表版](https://link.springer.com/article/10.1007/s10994-024-06632-w)；Crossref|§1.1–1.2、式(1)–(2)、方法与讨论相关段|固定模型条件性能及选择后同时界有直接先行；不是风电特定证书|
|L08|[出版社页面](https://www.sciencedirect.com/science/article/pii/S0305048325002348)；Crossref|出版社摘要、高亮及导论第3项|决策特征选择结合保守bootstrap已有先例；仅能按所读逐点界表述比较|

## 本项目实现与归档（只读）

- `windfarm_moe/independent_confirmation.py`：`historical_selection`和`confirmation_verdict`，核对历史选档与固定参照主要确认的对象。
- `windfarm_moe/risk_frontier.py`：`near_optimal_set`，核对可能可行集合、正向风险资格、成本上界与资源排序。
- `windfarm_moe/subset_inference.py`：`streamed_envelopes`，核对共享日块、固定实例与近似最大标准化包络的声明；本轮不调用。
- `scripts/verify_independent_confirmation_gate.py`：`check_primary`和`check_secondary`，核对主要／次要结果的判断逻辑。运行该一致性门禁不重抽样、不重拟合。
- `analyses/independent_confirmation_execution_20261019/REPORT.md`与原归档：R1、R2、全部不识别及失败的依据。
- `research_audit/14_resource_loss_break_even_review.md`：实测／算术资源与未知真实接口边际收益的区分。本轮不重新估计收益。

对R1/R2的最小性条件推论是本报告用这些定义直接重述的逻辑，不冒称新的定理。所有覆盖结论均条件于原联合界适用，旧近似覆盖状态没有升级。
