> 日期：2026-10-19（Asia/Shanghai）。C1—C8按08冻结，未重定义；原数据、原结果、稿件、契约和门槛未改。VERIFIED为直接事实，SUPPORTED为有界支持，INFERRED为审稿判断，UNKNOWN为未检验。

# 先行工作威胁：完整任务不同，不等于主要思想新颖

**结论：没有核实一篇完整复现C1/C4全部协议和数值的先行；但当前P条件分位数、既有预测后的实时备用误差层、决策导向输入选择、近优集合选小者均已有直接正文先行。** 因而“没有完全相同组合”不能支持C8竞争性创新。排他性原创认证为 **NOVELTY NOT VERIFIED**；下列已核概念先行本身是VERIFIED。

## 五篇最有威胁的工作

|工作|被覆盖的内容与正文定位|冻结主张/威胁|尚未覆盖的部分|
|---|---|---|---|
|[Pritchard2011](https://onlinelibrary.wiley.com/doi/10.1002/we.416)|§3、§4–4.3：当前P单变量条件分位数、额外输入和跨年验证|C2/C3/C6/C8：STRONG概念覆盖|未核其做相同备用非劣/最小性；后半正文/PDF缺失|
|[Sun等2022 RESERVE](https://www.ethree.com/wp-content/uploads/2023/03/Machine-learning-derived-dynamic-operating-reserve-requirements-in-high-renewable-power-systems.pdf)|印刷036303-1 §I、-3 §III/Fig1：保留既有point forecast，执行时可用输入估计误差分位数；§VI/AppA评价成本/超限|C1/C2/C7/C8：STRONG接口先行|净负荷预测差目标、十折/PLEXOS；未见增量输入最小性和封存年选择|
|[Serrano等2024](https://publications.polymtl.ca/57338/1/2024_Serrano_Bilevel_optimization_feature_selection_data.pdf)|§3.2 p707 Eq21起：按留出newsvendor成本选变量；§§4–5；作者版AppA|C2/C4/C8：STRONG问题/方法思想覆盖|线性规则及双层MILP，不是本项目依赖风险cap/有限族证书|
|[Kowal2022](https://www.jmlr.org/papers/volume23/21-0403/21-0403.pdf)|§2.4 p12 Eq19–20：近优可接受族与最小成员；§2.5/Algorithm1|C4/C5/C8：STRONG概念覆盖|Bayesian可接受概率与本项目UCB/严格较小者排除不等价|
|[Muñoz等2020](https://arxiv.org/html/1907.07580v3)|§II-B Eq25–30：较丰富直接bid可过拟合，采用上游多输入、下游单forecast校正；§III/IV检验|C2/C6/C8：STRONG两层信息/负结果先行|其上游预测可变、市场bid、滚动拟合且披露时序限制，非固定短缺备用选择器|

STRONG均定位到特定概念/接口，**不表示C1的2025数值已被他人测过**。本轮不把“新数据点”与“新科学发现”划等号。未作任何“全项目DIRECT OVERLAP”判决；NC1—NC5不是作者当前主张，不能建立稻草人。

## 七维对照与其他威胁

`13_prior_art_comparison.csv`有17篇×7维=119行；每行包含Prior Work、Current Project、Overlap、Claim IDs、正文定位、内容读取层级、DOI/URL与四角色。完整注册见本轮`prior_art_registry.json`。

- MCS作者稿§4.1（2010-76 PDFp19）明确固定benchmark比较与集合选择的不同责任；LTT arXivv5 §2.4处理多风险资格。它们限制“新联合选择原则”的包装，不提供本项目依赖日块覆盖证明。[MCS](https://pure.au.dk/ws/files/34269366/rp10_76.pdf)、[LTT](https://arxiv.org/html/2110.01052v5)
- Yuan/Wang2026的稀疏newsvendor预印本§2、§5、§6.4/7提供最新邻域先行；其iid/稀疏线性假设和理论目标不同，不当作项目已被完整解决。[原文](https://arxiv.org/html/2609.01544v1)
- 缺失输入到下游交易损失、预测质量不等于系统目标已有风电原文；相关文献不能替代本项目自身的C7实测。[Kühnau2023](https://discovery.ucl.ac.uk/id/eprint/10212754/1/FeatDriven_Trading_with_Missing_Data%20%281%29.pdf)、[Wahdany2023](https://pure.tudelft.nl/ws/portalfiles/portal/150812483/1_s2.0_S0378779623002730_main.pdf)
- Zhao2021及Zhang2026仅获得出版摘要/目录，属于高相关但正文未闭合的UNCERTAIN；没有将其未取得全文当“没有重叠”。

## 搜索、引文追踪与不足

N角色执行43条查询；主代理另有15条问题/机制/反证/近邻查询，可能重复，不是58个独立数据库或系统综述。七类目标均有对应命中。实际检索和失败见`novelty_impact_20261019/reviewer_n/SEARCH_LOG.md`、根检索日志与原始返回；不使用弃用矩阵/合成brief。

已核真实边包括：Pritchard→Nielsen2006（backward，后者仅摘要）；Wen→Stratigakos（backward）；Zhao2021→Sun2022、Stratigakos→Kühnau、Muñoz2020→Kühnau（forward）。根另核Serrano2024→Ban/Rudin2019（journal pp713 References）及Serrano2024→Yuan/Wang2026（后者§1.1、Ref32）的forward边。概念搜索与真实引文边分开，未穷举任何论文全部被引文献。

威胁大的文献实际读取了方法、实验及可得附录；Pritchard只到§4.3，Zhao正文418，Zhang全文未得；MCS最终supplement打开失败，使用明确标注的作者工作稿；Serrano作者38页版本补核计算附录，未冒称与12页出版版字节相同。两个PDF截图调用失败，未宣称图表视觉核验成功。所有访问层级写在矩阵。

## 数学等价边界

本项目`L=(r+10(S-r)+)/6`可写成`[9(S-r)+ +(r-S)+ +S]/6`。因此其优化与标准9:1 newsvendor仅差一个对策略无关项，直接分位数原则不是新损失原理。**但相对成本比不对加性常数不变**，所以不能把这里2%容限机械等同另一pinball/newsvendor损失表示的2%；当前C1固定原损失仍有效。没有更换损失/容限或用该恒等式重判原实验。[标准目标定位](https://publications.polymtl.ca/57338/1/2024_Serrano_Bilevel_optimization_feature_selection_data.pdf) §2。
