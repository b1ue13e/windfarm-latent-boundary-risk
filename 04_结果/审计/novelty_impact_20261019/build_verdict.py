"""Assemble a frozen-claim novelty/value audit; never modify original science."""
from pathlib import Path
import csv
import hashlib
import json

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'research_audit'
WORK=Path(__file__).resolve().parent

def paper(pid,authors,year,title,venue,doi,url,role,threat,claims,locator,level,prior,difference):
    return dict(id=pid,authors=authors,year=year,title=title,venue=venue,doi=doi,url=url,
        gap_role=role,threat=threat,claim_ids=claims,locator=locator,read_level=level,
        prior=prior,difference=difference)

# Each paper's prior entry has seven dimensions, not an assertion of identical tasks.
PAPERS=[
paper('R01','Geoffrey Pritchard',2011,'Short-term variations in wind power: Some quantile-type models for probabilistic forecasting','Wind Energy 14(2):255-269','10.1002/we.416','https://onlinelibrary.wiley.com/doi/10.1002/we.416','mainstream','STRONG OVERLAP','C2;C3;C6;C8','Publisher body §§3,4,4.3; HTML lines117-248','PARTIAL_PRIMARY_BODY; later body/PDF unavailable',
['短期功率条件分位数与额外输入','当前P可观测；特定零功率排除/输入条件','当前P单变量分位数样条和扩展输入','当前P条件化未来不确定性','低维功率基线及额外输入的差异','跨日历年留出；正文已核部分','非本项目短缺备用非劣与最小性'],
'概念先行强；C1的2025数值与C4排除协议未被此文完整覆盖。'),
paper('R02','Yuchi Sun; James H. Nelson; John C. Stevens; Adrian H. Au; Vignesh Venugopal; Charles Gulian; Saamrat Kasina; Patrick O’Neill; Mengyao Yuan; Arne Olson',2022,'Machine learning derived dynamic operating reserve requirements in high-renewable power systems','Journal of Renewable and Sustainable Energy 14:036303','10.1063/5.0087144','https://www.ethree.com/wp-content/uploads/2023/03/Machine-learning-derived-dynamic-operating-reserve-requirements-in-high-renewable-power-systems.pdf','mainstream','STRONG OVERLAP','C1;C2;C7;C8','Printed036303-1 §I; -2 §II; -3 §III/Fig1; -8–9 §VI; -13–15 AppA','AUTHOR_INSTITUTION_PDF; methods/experiments/appendix selectively read',
['既有点预测误差的动态备用需求','执行时可用信息；CAISO净负荷/子小时市场','pinball MLP误差分位数；34输入','已有预测后的误差风险层','成本、覆盖和超限严重度权衡','2019十折与PLEXOS运行模拟','不同预测差目标；未见增量子集最小性/封存年选择'],
'冻结/既有forecast后备用接口已有；本项目主要新增候选是输入格及一次独立年测量，非新接口原则。'),
paper('R03','Breno Serrano; Stefan Minner; Maximilian Schiffer; Thibaut Vidal',2024,'Bilevel optimization for feature selection in the data-driven newsvendor problem','European Journal of Operational Research 315(2):703-714','10.1016/j.ejor.2024.01.025','https://publications.polymtl.ca/57338/1/2024_Serrano_Bilevel_optimization_feature_selection_data.pdf','adjacent','STRONG OVERLAP','C2;C4;C8','Journal§2 p705–706, §3.2 p707, §§4–5 pp708–711; author arXiv2209.05093 AppA pp31–38','JOURNAL_BODY_AND_AUTHOR_APPENDIX; no proof certification',
['按下游newsvendor成本选稀疏输入','训练/验证分开；线性决策规则','双层特征选择及MILP重构','由留出决策代价而非预测指标选变量','稀疏规则的成本与支持恢复','合成线性/非线性；参数变化；计算附录','非依赖天气风险cap/独立年有限族排除'],
'决策导向选输入被直接先行覆盖；其算法不是本项目算法，不将任务差异抹掉。'),
paper('R04','Daniel R. Kowal',2022,'Bayesian subset selection and variable importance for interpretable prediction and classification','Journal of Machine Learning Research 23(108):1-38','','https://www.jmlr.org/papers/volume23/21-0403/21-0403.pdf','foundational','STRONG OVERLAP','C4;C5;C8','§2.4 pp11–12 Eq17–20; §2.5; §§3–4; Algorithm1 p25; AppA–C','PUBLISHER_PDF; methods/experiments and selected appendix',
['近优变量子集族及最小可接受者','Bayesian预测分布；容限/后验概率定义','subset filtering、可接受族与最小成员','在不确定性下保留竞争解释','小子集可近优，成员不唯一','模拟、教育数据、敏感性','非本项目共同绝对风险cap与频率界认证'],
'最小近优子集概念强覆盖；其可接受概率条件与本项目UCB/严格较小者排除并不等价。'),
paper('R05','M. A. Muñoz; J. M. Morales; S. Pineda',2020,'Feature-Driven Improvement of Renewable Energy Forecasting and Trading','IEEE Transactions on Power Systems 35(5):3753-3763','10.1109/TPWRS.2020.2975246','https://arxiv.org/html/1907.07580v3','failing','STRONG OVERLAP','C2;C6;C8','§II-B Eq25–30; §III-A/C; §IV-A/B; author PDF pp4–8','AUTHOR_FULLTEXT; focal methods and experiments read',
['利用特征改进风电预测与交易','DK1市场；上游forecast可改进；成本可预测性有限','上游多输入、下游单forecast低自由度校正','复杂直接bid可能拟合成本噪声','更多输入/自由度不保证更高经济回报','滚动训练与真实市场成本','非固定shortfall备用；作者披露时间一致性限制'],
'failing仅指其特定直接交易规则的负结果；不是宣称所有决策学习失败。低维下游经济规则已有。'),
paper('R06','Anastasios N. Angelopoulos; Stephen Bates; Emmanuel J. Candès; Michael I. Jordan; Lihua Lei',2025,'Learn then test: Calibrating predictive algorithms to achieve risk control','Annals of Applied Statistics 19(2):1641-1662','10.1214/24-AOAS1998','https://arxiv.org/html/2110.01052v5','foundational','PARTIAL OVERLAP','C4;C5;C8','arXivv5 §1.1; §§2.1–2.4; Proposition6','AUTHOR_FULLTEXT_SELECTIVE; journal metadata verified',
['校准后的多风险资格与参数选择','需有效检验；文中校准样本iid','Learn-then-Test、多重检验','风险资格转假设检验','可返回风险合格集合/空集','多任务风险校准实例','不自动适用于本项目季节依赖日块'],
'联合资格思想已有；未把其iid保证借给项目，也不将本项目误称LTT原算法。'),
paper('R07','Peter R. Hansen; Asger Lunde; James M. Nason',2011,'The Model Confidence Set','Econometrica 79(2):453-497','10.3982/ECTA5771','https://pure.au.dk/ws/files/34269366/rp10_76.pdf','foundational','PARTIAL OVERLAP','C4;C5;C8','Author2010-76 §§1–4; §4.1 PDFp19; publisher metadata2011','AUTHOR_WORKING_VERSION; publisher supplement unavailable',
['多模型相对性能的集合推断','候选族固定；期望损失差满足统计条件','顺序排除与bootstrap MCS','信息不足时保留更大的集合','固定benchmark比较与集合选择责任不同','理论、模拟与经济时间序列','MCS未拒绝不等于证明epsilon非劣/风险合格'],
'集合与不识别责任有先行；不是本项目绝对cap加最小资源证书的等价实现。'),
paper('R08','Honglin Wen',2024,'Probabilistic wind power forecasting resilient to missing values: An adaptive quantile regression approach','Energy 300:131544','10.1016/j.energy.2024.131544','https://arxiv.org/pdf/2305.14662v3','mainstream','PARTIAL OVERLAP','C2;C6;C8','Authorv3 §§3–4 pp9–13; §§5–7 pp13–22; AppA','AUTHOR_FULLTEXT_SELECTIVE; final publisher bytes not compared',
['缺失遥测下概率风电预测','人工缺失情形及历史功率滞后','缺失模式自适应条件分位数','按实际可观测输入适配预测','剩余输入可用于鲁棒概率预测','CRPS、可靠性、sharpness实验','未核实同一备用成本非劣/资源最小性'],
'缺失遥测直接分位数不是空白；预测分数不可替代本项目风险成本判断。'),
paper('R09','Changfei Zhao; Can Wan; Yonghua Song',2021,'Operating Reserve Quantification Using Prediction Intervals of Wind Power: An Integrated Probabilistic Forecasting and Decision Methodology','IEEE Transactions on Power Systems 36(4):3701-3714','10.1109/TPWRS.2021.3053847','https://ieeexplore.ieee.org/abstract/document/9334448','mainstream','UNCERTAIN','C1;C4;C8','Publisher abstract and contents; full HTML/PDF418','PRIMARY_ABSTRACT_TOC_ONLY',
['预测区间与备用成本联合决策','摘要提coverage及采购/缺额成本','联合区间/备用方案，正文未读','摘要关联经济风险与分位数','原文摘要报告经济备用改进','全文实验未核实','不能据摘要断言完整同问题或不存在子集分析'],
'重要候选；全文缺口禁止DIRECT/STRONG正文覆盖判决。'),
paper('R10','Zhaoliang Yuan; Jie Wang',2026,'Variable Selection for Feature-Based Newsvendor','arXiv:2609.01544v1 (preprint)','','https://arxiv.org/html/2609.01544v1','adjacent','PARTIAL OVERLAP','C2;C4;C8','§2 Eq1–3; §5 assumptions/theorems; §6.4; §7; Ref32','PREPRINT_PRIMARY_BODY; proof correctness not independently audited',
['硬基数限制的决策变量选择','iid、稀疏线性及密度/特征等条件','MISOCP、rounding/greedy、稀疏分位数','少变量成本与支持恢复','报告较少变量的成本表现','合成与零售实例','非本项目相关天气/冻结参照/绝对cap/次要排除'],
'最新邻域先行，预印本身份单列，不把作者的统计保证直接转授项目。'),
paper('R11','Dariush Wahdany; Carlo Schmitt; Jochen L. Cremer',2023,'More than accuracy: end-to-end wind power forecasting that optimises the energy system','Electric Power Systems Research 221:109384','10.1016/j.epsr.2023.109384','https://pure.tudelft.nl/ws/portalfiles/portal/150812483/1_s2.0_S0378779623002730_main.pdf','adjacent','PARTIAL OVERLAP','C6;C8','§1 Fig1; §4.4 Table3; §§4.3–4.6','FINAL_INSTITUTION_PDF; focal body read',
['风电预测与系统决策目标差异','端到端系统优化目标','决策导向预测训练','预测误差与下游成本不等同','不同目标下效果存在边界','能源系统成本/curtailment对照','非状态恢复、固定forecast或遥测最小性'],
'accuracy不等于value已有直接领域讨论；本项目具体状态负结果仍局部。'),
paper('R12','Matias Kühnau et al.',2023,'Resilient Feature-driven Trading of Renewable Energy with Missing Data','IEEE ISGT Europe','10.1109/ISGTEUROPE56780.2023.10408186','https://discovery.ucl.ac.uk/id/eprint/10212754/1/FeatDriven_Trading_with_Missing_Data%20%281%29.pdf','adjacent','STRONG OVERLAP','C6;C7;C8','pp2–3 §§II–III Eq1–9; pp4–5 §IV TablesI–II','AUTHOR_INSTITUTION_5PAGE_FULLTEXT',
['缺失输入下可再生能源交易损失','缺失组及可用features','feature-driven鲁棒决策','输入不可用直接作用于经济损失','缺失鲁棒决策需评估实际损失','市场imbalance cost对照','非共同forecast后的最小备用输入认证'],
'缺失输入—决策成本问题已有；其市场价值不替项目测量C7。'),
paper('R13','Lesia Semenova; Cynthia Rudin; Ronald Parr',2022,'On the Existence of Simpler Machine Learning Models','ACM FAccT','10.1145/3531146.3533232','https://arxiv.org/html/1908.01755v4','adjacent','PARTIAL OVERLAP','C4;C5;C8','§3 Definition1; §5; accompanying reference-vs-ERM distinction','AUTHOR_FULLTEXT_FOCAL_DEFINITIONS',
['近优集合与简单模型存在','模型类、损失及统计假设明确','Rashomon set/ratio','不同近优模型可有不同复杂度','简单且准确的模型存在条件','理论与多数据集研究','非本项目风险cap/有限输入格的覆盖验证'],
'近优集合中存在简单者的思想已有；不证明本项目处于其假设。'),
paper('R14','Akylas Stratigakos et al.',2024,'Towards Resilient Energy Forecasting: A Robust Optimization Approach','IEEE Transactions on Smart Grid 15(1):874-885','10.1109/TSG.2023.3272379','https://backend.orbit.dtu.dk/ws/portalfiles/portal/320707182/BERAT_Towards_Resilient_Energy_Forecasting_A_Robust_Optimization_Approach.pdf','adjacent','RELATED','C2;C8','Accepted version §§II–IV; 13 actual PDF pages','INSTITUTION_ACCEPTED_TEXT; 2023 online/2024 volume',
['feature deletion下鲁棒能源预测','缺失预算Gamma及不可删日历项','feature-deletion robust regression/LP','对缺失输入作鲁棒优化','风电缺失情形预测性能','QR/QRF/RETRAIN比较','Gamma非最小新增遥测或非劣证书'],
'相关鲁棒输入问题，不能与最小资源选择等同；没有任务外扩展建议。'),
paper('R15','Yuying Zhang; Shiming Deng; Wanpeng Wang',2026,'Feature-based profitability evaluation for newsvendor-type products','Omega 141:103508','10.1016/j.omega.2025.103508','https://www.sciencedirect.com/science/article/pii/S0305048325002348','adjacent','UNCERTAIN','C2;C4;C8','Publisher indexed abstract/highlights; full paper unavailable','ABSTRACT_ONLY; not a full-overlap adjudication',
['feature-based newsvendor盈利概率','目标盈利概率，细节未审','摘要称决策选变量+保守bootstrap','上下文与保守性能评估结合','摘要报告数值效益','全文方法/附录未核实','不得声称未做本项目类似辅助验证'],
'最新重要候选，全文未核实，不能以标题或摘要作强排他判断。'),
paper('R16','Gah-Yi Ban; Cynthia Rudin',2019,'The Big Data Newsvendor: Practical Insights from Machine Learning','Operations Research 67(1):90-108','10.1287/opre.2018.1757','https://pubsonline.informs.org/doi/abs/10.1287/opre.2018.1757','foundational','RELATED','C2;C8','Publisher abstract; Serrano2024 §1.1 and References pp713 verified citation','PRIMARY_ABSTRACT; no full-theorem audit',
['上下文newsvendor直接决策','预设非对称损失','feature-based ERM等','从特征到决策','上下文决策有成熟先行','出版社摘要及书目','不据未读正文判同风险门/封存年'],
'作真实backward引用与基础定位，不以二手引用替代正文覆盖。'),
paper('R17','Utsav Sadana; Abhilash Chenreddy; Erick Delage; Alexandre Forel; Emma Frejinger; Thibaut Vidal',2025,'A survey of contextual optimization methods for decision-making under uncertainty','European Journal of Operational Research 320(2):271-289','10.1016/j.ejor.2024.03.020','https://www.sciencedirect.com/science/article/pii/S0377221724002200','foundational','RELATED','C8','Publisher abstract/taxonomy; Yuan2026 Ref31 verified citation','PRIMARY_SURVEY_TAXONOMY_ONLY',
['contextual optimization命名和框架统一','任务与可用covariates','三个方法范式分类','预测与优化结合已有成熟领域','给出统一分类而非本项目实验','survey自身摘要/分类','不用综述替代各原论文的技术结论'],
'只支持问题范式已成熟，不作任何本项目数值有效性先行。')
]

CURRENT=[
'固定共同预测后，备用层增量遥测能否满足风险/成本要求',
'同forecast/shortfall/finite-target；五冻结实例；合成双馈送；依赖天气',
'固定HGB/MLP/持续性+历史offset/选择+近似联合界+有限族排除',
'假设当前P保留下游相关信息；原因尚未识别',
'q.95主非劣；q.925次要最小；WTB不识别；无普遍规律',
'一次封存2025、550确认任务；全族/失败透明；块后算术可核',
'覆盖/实际净收益/端到端资源/真实到达/PCC未知；非全函数最小'
]
DIMS=['Research Question','Assumptions','Core Method','Mechanism','Findings','Evidence','Limitations']
S='STRONG OVERLAP';P='PARTIAL OVERLAP';R='RELATED';U='UNCERTAIN'
DIM_OVERLAP={
    'R01':[P,P,S,P,P,P,R], 'R02':[S,P,S,P,P,P,R], 'R03':[S,P,P,P,P,P,R],
    'R04':[S,P,P,P,P,R,R], 'R05':[P,P,P,S,S,P,R], 'R06':[P,P,P,S,P,R,P],
    'R07':[P,P,P,S,P,R,P], 'R08':[P,P,P,P,P,R,R], 'R09':[U]*7,
    'R10':[S,P,P,P,P,R,R], 'R11':[P,R,R,P,S,R,R], 'R12':[S,P,P,P,P,P,R],
    'R13':[P,P,R,P,P,R,P], 'R14':[P,P,R,R,R,R,R], 'R15':[U]*7,
    'R16':[R]*7, 'R17':[R]*7}

HEADER='> 日期：2026-10-19（Asia/Shanghai）。C1—C8按08冻结，未重定义；原数据、原结果、稿件、契约和门槛未改。VERIFIED为直接事实，SUPPORTED为有界支持，INFERRED为审稿判断，UNKNOWN为未检验。\n\n'

DOCS={
'09_prior_art_threats.md':r'''# 先行工作威胁：完整任务不同，不等于主要思想新颖

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
''',
'10_novelty_audit.md':r'''# 新颖性裁决

**当前可确认的是一个新的具体应用测量，不是新算法、新理论或已经成立的新规律。** 08的C1/C4数值与协议范围保留；C8“足以构成竞争性创新”未获证明。确切完整组合的原创性为 **NOVELTY NOT VERIFIED**，不以检索未命中认证“首次”。

## 五类新颖性分别判断

分值0=无新增证据，1=局部设置/实例增量，2=有界任务经验增量，3=明确可复用的新解释/方法，4—5=广泛/基础性推进；属于INFERRED辅助评价，不是录用概率。

|维度|分数|明确判决|证据/置信边界|
|---|---:|---|---|
|Problem novelty|1.5/5|通用问题成熟；当前精确双馈送接口是特定化，尚未证明它改变了领域瓶颈|Pritchard/Sun/Serrano正文先行；高置信否定宽泛首创，精确组合排他性UNKNOWN|
|Method novelty|0/5|未识别新增算法机制；现有recipe和选择/界工具的任务组合|当前实现、LTT/MCS/Kowal；高置信。NC1/NC2本就不是作者主张|
|Discovery novelty|1.5/5|C1、C4是本地新数值；尚非可预测的稳定新现象|一场站一封存年；C3未知，WTB异同多因素变化；中高置信|
|Theoretical novelty|0/5|没有新定理、已验证新机制或依赖覆盖保证|原代码/报告只声明近似；没有将先行定理借来；高置信|
|Empirical novelty|2/5|冻结确认、有限格和失败边界提供可复用案例；未证明现有领域结论被系统推翻|C1/C4真实局部数据，C5一般差别由量词/定义不同；中置信价值判断|

## 删除已有思想之后剩下什么

剩下的是：在明确共同W/P预测、未来目标、五个固定实例和近似日块推断下，P1/q.95于2025以0.5641%成本溢价通过固定参照要求；另一个q.925于预声明次要族排除15个更小者；同时存在WTB不识别和其他条件失败。这些具体测量不是定义能算出来的，所以不能说项目“零新信息”。但当前没有给出超越该场站/年份/recipe的机制、必要条件或外部预测，剩余增量不足以支撑强方法/发现定位。

## 什么不能再作为创新

当前P能用于短期条件分位数；在既有预测后估计误差备用；直接按非对称损失选输入；在近优集合中找小者；信息不足时保留集合；预测/表征分数不等于决策价值。正文先行定位见09及13矩阵。它们仍是正确研究原则，但遵守原则与提出原则是两回事。新paper数值、拟合数量、哈希闭合和不隐瞒负结果，也不能单独换算创新强度。

## 对最弱贡献的裁决

最容易被推翻的是把C4/C5称为“新的最小充分选择原则/新统计洞见”，或把C2称为“首次发现少遥测足够”。这些升级并非冻结的实际贡献，故当前应阻止升级，而不是反复攻击作者未作的NC主张。实际贡献候选中，**第二项C4+C5的科学新颖性弱于第一项C1+C2的应用测量**：它的普遍内容主要是已知集合选择及不同比较责任，局部证书又依赖有限族。

## 仍可能改变裁决的证据

直接先行若完整覆盖精确任务，C8进一步收缩；真实接口及可兑现资源代价可提升应用贡献重要性，但不创造方法首创；第二未查看窗口可提升C3可靠性，但不自动提高问题/方法新颖性；新机制/理论需要独立可检验内容，当前没有，本轮也不扩展。不能通过改q/容限、重命名“充分性”回避已核先行。
''',
'11_scientific_significance.md':r'''# 科学意义裁决

**INFERRED：当前整体科学意义2/5，定位为限定接口的应用实证。** 它回答一个具体实例能否用更少备用输入维持声明要求；尚未解释领域未知机制、解决普遍瓶颈或形成可迁移规律。数值真实性与重要性分别成立，不因前者通过而自动提高后者。

|维度|辅助评分|实际改变了什么|没有改变什么|
|---|---:|---|---|
|Fundamental understanding|1.5/5|知道该2025接口里P1可以以约0.56%代价通过固定要求|不知道为何、何时失效；没有证明状态冗余/物理机制；C5一般差别来自定义量词|
|Research utility|2.5/5|提供固定目标、历史选择、失败/排除见证和独立年份的可复核案例|尚无相对已有集合工具的新能力证明；工程纪律不是新科学原理|
|Generality|1/5|两来源和压力结果提供局部正负边界|种子共享天气；WTB/Hill多因素不同；没有受控迁移条件；C3仍未知|

## 反事实：若不发表，学界失去什么

会失去一份风电具体接口的定量记录：少新增P相对固定参照的0.5641%代价、另一q的有限族证书和全部不识别/失败。不会因此失去“当前P有预测力”“决策导向选变量”“简单模型可近优”“固定参照与全族不同”的一般认识，因为09列先行已提供这些思想。也没有证据表明运营者会失去已证明的净收益。故当前是局部可复核知识，尚非影响领域理解的强发现。

## 可靠结果为何未自动成为强发现

C1不是人为定义：实际成本/风险必须测量，值得保留。C5的具体同年反例也帮助读者避免误读，但主要差别来自q、参照、候选族和检验责任改变，不能写成新物理现象。C6负结果仍容许状态冗余、优化不足、校准/标签/版本等解释；不支持唯一机制。WTB不识别和Hill识别不能单因于样本量或风场物理，也不能把420/90相关案例当独立复制。

## 最强三类科学意义异议与裁决

- S1（confirmed缺口）：定义区分未形成解释。现有证据未给出能够预先预测何时少输入有效的新边界。最低补救是在当前应用定位中承认其为既有原则的任务实例，不需要新训练。
- S2（confirmed缺口、真实场景UNKNOWN）：资源字典序尚无实际使用者瓶颈支撑。若完整遥测已在同一进程，去掉若干learner列未必解决重要问题。最低补救是核实一个真实备用接口的新增数据责任与代价。
- S3（confirmed范围）：一场站一独立年和不匹配开发来源不足以建立迁移规律。最低补救是删去泛化暗示；新确认只增加可靠性，若要声称新条件规律还需另证，本轮不启动。

完整角色报告见`novelty_impact_20261019/reviewer_s/`。这些异议没有证明工作完全无用，但足以阻止强机制/理论/普遍模型地图的定位。

## 纠正上一轮关于“唯一实验失败”的过强表述

上一轮将“第二窗口失败则整篇不成立”用于所选稳定性主线，仍容易混淆C1与C3。准确边界是：**第二窗口未确认只削弱C3及该窗口结论，不能逆向撤销2025的窄C1或已存C4算术；UCB未过也不等于真实总体被证明违规。** 若新证据发现共有实现/来源/推断错误，才可能同时影响旧结果。新确认通过亦不能消除新颖性和实际价值缺口。保留窄事实，并不意味着其贡献足以支撑强论文。
''',
'12_practical_impact.md':r'''# 实际价值裁决

**Practical Impact：UNPROVEN。** 当前证据显示一个特定接口可用较少learner输入满足代理要求，不能显示真实净收益。谁实际使用该接口、原方案是什么、可避免的数据成本和业务可接受溢价均未绑定。条件性使用者只能写为已有预测服务且单独维护备用输入的EMS/聚合软件团队，不当作已观测部署。

## 真实数字与其含义

|量|P1与冻结全量参照|可支持/不可支持|
|---|---|---|
|原始learner列|5 vs112，减少95.5357%|接口宽度，不是同幅端到端内存/报文/传感器节约|
|MLP标准化后列|10 vs224|源码拼接缺失指示；当前HGB确切宽度因未导出模型UNKNOWN|
|共享上游|W/P各36历史，两者共用|不能从系统成本账抹掉；不是只用一个传感器|
|实际特征构建|各recipe先建148列X；2025 X本体653,338,896B（约623MiB）|不是峰值RSS；当前路径未兑现5/112同幅构建内存下降|
|训练索引首拷贝|360k×148 float32=213,120,000B|选择子列之前已产生，P1仍承担此路径|
|HGB fit存档均值|2.500s vs34.679s，差约32.179s|只显示所存固定recipe的fit差，不是同节点受控benchmark或线上SLA|
|完整年度evaluate存档均值|5.347s vs6.797s|包含加载、全特征、五q记账/校核和写出；纯predict延迟未记录|
|每有效格成本|67.020403 vs66.644430，差+0.375973|成本上升0.5641%；非成本改善|
|观测年代理总溢价|五实例均值+398,248.517 kWh-equivalent|不是实际额外能量、货币或PCC账单，不能乘未绑定电价|

源：本轮`reviewer_p/recompute_practical.py`从700份受保护输入只读计算；receipt前后哈希一致。Metis receipt为CPU only，Python3.11.16、sklearn1.9.1、Torch2.11.0+cu128；CUDA build不等于用了GPU。每worker请求2CPU/16GB，不等于实际利用率/占用；每recipe CPU型号、cput、峰值RSS和纯predict时间缺失。

## 收益能否抵偿代价

当前可证的方向是：较少learner列及较短存档fit，对应**更高**代理运行损失。数据输入/维护/访问限制可能值得这个代价，但尚无现实成本或业务容限证据，不能以“0.56%小”直接判定值得。单次离线fit约32秒差也不足以在缺少单位转换和实际调用频率时计算财务摊销。真实净收益的必要条件是存在可避免的接口负担，并能与决策损失在业务认可尺度上比较；当前两端未连接。

## 现实基线与失败成本

同一目标已测Common、Persistence、HGB/MLP全信息，不能说只有弱基线：次要225族3日界下Common/HGB/q.95成本78.272922、风险U6.9941%；Persistence/q.925成本86.969480、U9.2874%；全量HGB/q.95成本66.644430、U6.6934%。这些U来自次要族，与主要14坐标U不能混抄。P1比Common/Persistence便宜，支持新鲜P对这些比较器有增量价值；不能以它们取代更便宜的冻结全量参照。

实际运营fallback、经验margin、报警回退或采购流程未观测；没有“已验证安全回退”。原物理/分箱支线目标不同，不能拼来补真实fallback。无功/风速数据是否本来已有、能否停止转发、是否存在授权费，均UNKNOWN。

只读事后日块还显示：2025-10-31 seed204的P1日风险21.1019%（参照20.9286%）；2025-12-13 seed201日成本溢价6.4938%。它们**不违反已注册全期判据**，却阻止每日安全/每时段非劣解释。没有真实arrival/publication、PCC净额、容量/爬坡/SoC/网络可交付性，不能把统计cap认证等同可用备用已供足。新增严重度/现场价值仍UNKNOWN。

## 指标适用性

Objective quality适用，但只有机组级代理；风险约束只在声明总体/近似界内检验。Optimality gap/primal-dual bound、time-to-first-feasible、solver compatibility不适用当前直接政策学习，不能填0或宣称最优求解。46/90等是相关案例判定，不是独立solve rate。当前无同硬件规模曲线，不声称scalability已证明。

## 最低成本的单项下一步

**真实备用接口的资源—代理损失盈亏台账评审。** 固定当前两策略，证明哪个真实使用者能取消哪些增量读取/缓存/传输/维护；共用forecast成本保留，与+0.375973/有效格的代理溢价并列。无法货币化时就报告二维权衡，不虚构净收益。预计已有材料可得时0.5—2人日，无新训练；实际接口权限/日志不可得则时间和结果UNKNOWN。若没有可取消负担或被接受的业务容限，不再为当前主线增加训练支出，不包装部署节约。这仍在原问题内，不是新方向。
''',
'FINAL_NOVELTY_AND_IMPACT_VERDICT.md':r'''# 独立科研价值判决

## 1. Novelty Verdict

**当前剩余新知识是一个具体预测接口和封存年份的定量应用结果；方法、理论和稳定新规律均未建立。** Pritchard2011、Sun2022、Serrano2024、Kowal2022、Muñoz2020已分别覆盖当前P分位数、既有预测后备用误差层、决策选输入、近优最小子集及简化下游经济决策。没有核实一篇完整复现C1/C4全部数值/协议的论文，因此不判“全项目已被做过”；也不将这个精确组合未检出当原创证明。排他性原创认证 **NOVELTY NOT VERIFIED**；已核概念先行置信高。

## 2. Scientific Value Verdict

**INFERRED：整体2/5，限定应用实证。** 具体新增的是2025独立年中少新增P的代价约0.56%及另一q的有限族识别，并保留不识别/失败。它没有回答何时这种约简应当成功、为何状态恢复不转化、哪种现实瓶颈因此被解决。若不发表，学界少一份可复核案例及账本，不会因此缺失已知的条件分位数/集合选择原则。可靠记录可保留，强科学贡献仍缺证据。

## 3. Practical Value Verdict

**UNPROVEN，置信高的是“缺口存在”，不是“真实收益一定为负”。** 成本实际上升0.5641%，每格+0.375973代理单位。5原列vs112只反映learner接口；当前实现先生成148列X，共同上游仍消费W/P72历史值。存档fit2.500s vs34.679s有差，但纯推理、峰值RSS、实际带宽/维护成本、真实使用者与PCC经济映射未测。不能将接口宽度下降当端到端节约，更不能把代理kWh乘未绑定电价变成净收益。

## 4. Strongest Prior Work

|优先对照|具体重叠及证据|不能据此声称什么|
|---|---|---|
|[Sun等2022](https://www.ethree.com/wp-content/uploads/2023/03/Machine-learning-derived-dynamic-operating-reserve-requirements-in-high-renewable-power-systems.pdf)|§I/III、AppA：既有预测后的执行时信息误差分位数与备用评价，STRONG接口先行|没有完成本项目增量输入最小性或同封存年结果|
|[Pritchard2011](https://onlinelibrary.wiley.com/doi/10.1002/we.416)|§3–4.3：当前功率条件分位数、额外输入、跨年检验，STRONG现象先行|后半正文未取得，不能宣称全文已核/同风险成本证书|
|[Serrano等2024](https://publications.polymtl.ca/57338/1/2024_Serrano_Bilevel_optimization_feature_selection_data.pdf)|§3.2及§§4–5：按留出newsvendor代价选变量，STRONG问题思想先行|双层MILP不是本项目算法，绝对风险/依赖界不同|
|[Kowal2022](https://www.jmlr.org/papers/volume23/21-0403/21-0403.pdf)|§2.4 Eq19–20：近优可接受族/最小者，STRONG概念先行|Bayesian接受与本项目UCB/严格较小者排除非等价|
|[Muñoz等2020](https://arxiv.org/html/1907.07580v3)|§II-B Eq25–30：上游多特征、下游单forecast低自由度规则，STRONG信息接口/负结果先行|其forecast可改、市场bid而非本项目shortfall，作者亦有时序限制|

逐论文七维对照、其他风险校准/缺失输入/最新预印本和内容读取层级见09与13。Zhao2021及Zhang2026正文未获，保持UNCERTAIN；检索不是穷尽系统综述。

## 5. Defensible Contributions

只保留两项**经验贡献候选**，不称新算法原理：

1. **C1+C2：**在共同预测已用W/P的前提下，事前选定P1/HGB/q.95于2025对冻结WPQ36/HGB/q.95，以0.5641%溢价满足2%成本容限与10%全期风险要求。点成本67.020403/66.644430；近似区间[0.3575%,0.7708%]，最大实例风险U6.2025%/6.2004%。其用途和代表性仍须说明。
2. **C4及局部C5：**同年预声明次要全q族识别q.925、排除15更小者；WTB420例零最小性和Hill失败/未解保留。这提供有限族证据边界，不把已知集合逻辑当新理论。q.925不能授予q.95主要选择。

实际贡献候选不等于竞争力已建立。C3跨窗口稳定、C7净收益、机制解释、全函数最小性均不在已成立贡献中。

## 6. Weakest Claim

若将C8建立在“冻结预测后研究备用”或“发现P低维足够”上，Sun/Pritchard会直接击中其理由；若建立在C4/C5概念首创上，Serrano/Kowal/MCS/LTT会击中。**两项实际候选中，C4+C5作为强科学创新最脆弱**：一般责任差别已有先行，局部证书又依赖q/有限recipes/字典序/近似界。这里不攻击作者明确排除的NC1—NC5。

## 7. Decisive Evidence

最能改变本轮价值判断的是：现实中存在该增量馈送约束，并能兑现可测的资源/接口收益，足以使使用者接受已观察代理溢价。没有这项证据，再确认一年主要提高C3可靠性，不解决新颖性/重要性。依赖覆盖核验影响C1/C4推断强度；正文未获的强近邻可能进一步缩小剩余贡献。这些分别是价值、有效性与新颖性的门槛，不互相替代。

**纠正上一轮边界：**第二窗口未确认只削弱C3和该窗口结论，不自动撤销窄2025 C1。界未过也未必证明真实总体不合格；只有共同实现/来源/推断错误才可能逆向影响原证据。不能刻意扩大已证Claim以制造“一个实验失败就整篇归零”的可证伪外观。

## 8. Recommended Positioning

**应用实证/透明评价研究。** 不支持当前理论研究、方法创新或机制发现定位。可报告严谨的单接口代价、风险与有限族识别；不得用更多模型、年份数量、哈希或自我纠错工作量代替贡献。当前也不据此承诺TSTE或任何期刊的竞争力，没有作者绑定的官方期刊标准或校准录用概率。

## 9. Research Decision

**REPOSITION。选择F：保留当前有限贡献，降低定位；不扩展新方向。** A/C/D/E暂不启动；B只有已有问题内出现可检验条件预测才值得另议，但本轮不设计新机制；G作为停止新增投入的规则：若F的最低现实接口价值核验无法成立，就封存现有结果/工具，不继续为同一卖点追加模型或训练。不是因为过去投入大就CONTINUE，也不因方法非首创就删除真实局部结果。

## 10. Next Action（只一项）

**安排一次真实备用接口的资源—代理损失盈亏台账评审。** 固定P1/q.95与现有参照，不新训练；列出一位实际使用者、现行fallback、共同forecast已消费的信息、可取消的新增接口负担及可测代价，与+0.375973/有效格并列。已有接口/日志可得时预估0.5—2人日；访问不可得时明确UNKNOWN，不发明部署场景。完成标准是得出“存在且值得约简的真实接口”或“没有足够用途证据”的可审查结论。没有币值/交付映射就不计算财务回本。

## 三角色与Meta-Reviewer裁决

三角色均fresh fork、继承同一模型路由，先提交后综合，未互读本轮输出。角色分离不等于错误统计独立；无审稿准确率校准。三席均未修改原项目。

|意见|裁决|最低应对/是否根本定位问题|
|---|---|---|
|N1 概念链成熟|已核正文先行；不是整个C1被重复|直接承认先行；宽泛首创定位不成立|
|N2 有限recipe最小性未自动成为新发现|范围已证；精确同任务先行仍UNKNOWN|保留15见证，不升新理论；强方法定位有根本缺口|
|N3 接口约简未证用户收益|C7缺口确认，真实是否省钱UNKNOWN|与P1/P2互相印证，统一归资源价值核验|
|S1 定义差别尚无解释机制|已确认未识别机制，不证明永无机制|以局部测量定位，无须为投稿加模块|
|S2 现实瓶颈可能不存在|缺现实证据已证，瓶颈不存在仍UNKNOWN|唯一next-action验证；否则应用影响定位受阻|
|S3 没有迁移条件/新预测|C3未知、两来源非受控比较|删除外推；再一年属可靠性补证|
|P1 5/112未兑现同幅系统资源下降|源码148列物化已证；在线收益UNKNOWN|严格区分learner和完整pipeline|
|P2 更高proxy成本的净收益未闭合|正溢价已证，净收益方向UNKNOWN|保留正值，不假币值兑换|
|P3 全期cap不是每日/现场安全|最差日和未绑定交付已证|不重判原门槛，不宣称部署安全|

最低成本可化解的是表述范围、比较对象和现有实现资源账；不能仅靠润色化解的是现实需求、推断覆盖和缺乏新解释。所有未解决批评保留，没有以多席一致等同科学认证。

## 300字内科研价值摘要

当前新知识限于：固定共同预测后，少新增有功策略在一个封存年份以0.5641%成本溢价满足预设要求。当前功率条件分位数、预测后的备用误差建模、决策选变量及近优最小子集均有先行，尚无新算法、理论或稳定规律。它值得保留为可复核的应用案例；竞争力取决于真实备用接口是否需要这种约简，以及可兑现资源收益是否足以接受该代价。先核实这项价值，再决定追加验证；再通过一年不会自动创造创新。
'''
}

def main():
    freeze=json.loads((WORK/'claim_freeze.json').read_text(encoding='utf-8'))
    for name,value in freeze['sources_sha256'].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==value,name
    for name,body in DOCS.items():
        (OUT/name).write_text(HEADER+body,encoding='utf-8')
    for p in PAPERS:p['dimension_overlaps']=dict(zip(DIMS,DIM_OVERLAP[p['id']]))
    (WORK/'prior_art_registry.json').write_text(json.dumps(PAPERS,ensure_ascii=False,indent=2),encoding='utf-8')
    records=[]
    for p in PAPERS:
        for dim,prior,current in zip(DIMS,p['prior'],CURRENT):
            records.append(dict(Paper_ID=p['id'],Authors=p['authors'],Year=p['year'],Title=p['title'],Venue=p['venue'],
                DOI=p['doi'] or 'NO_VERIFIED_DOI',URL=p['url'],Gap_Role=p['gap_role'],Claim_IDs=p['claim_ids'],
                Dimension=dim,Prior_Work=prior,Current_Project=current,Overlap=p['dimension_overlaps'][dim],Overall_Threat=p['threat'],
                Evidence_Locator=p['locator'],Read_Level=p['read_level'],Scope_Difference=p['difference'],
                Whole_C1_C4_Direct_Overlap='NOT_ESTABLISHED'))
    with (OUT/'13_prior_art_comparison.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=records[0]);w.writeheader();w.writerows(records)
    assert len(records)==119
    print('Wrote',len(DOCS),'reports and',len(records),'comparison rows for',len(PAPERS),'papers.')

if __name__=='__main__':main()
