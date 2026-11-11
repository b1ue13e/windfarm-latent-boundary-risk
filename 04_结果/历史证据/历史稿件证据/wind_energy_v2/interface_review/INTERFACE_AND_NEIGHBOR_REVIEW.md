# V2接口用途与近邻差异核查

日期：2026-10-20。任务：为Wind Energy现有证据闭环修订提供文献与接口材料；不改变原稿、原结果、阈值或科学契约。本报告使用`deep-research`的有界fact-check模式，不是全领域系统综述。

**结论：一般的“既有预测之后评估备用需求”有直接先行，预测、遥测和调度分层也有官方实例；本研究精确的单F、t−6至t+6时钟及112→5增量输入的实际业务用途仍未闭合。V2可以澄清合成任务中的定量取舍，不能把补入一般来源写成现场接口已经得到验证。**

## 1. 核查范围与认识论状态

`VERIFIED`表示正文、源码或官方文件直接支持；`INFERRED`表示由已知事实推得的有条件解释；`UNKNOWN`表示当前没有合格材料。没有找到材料，不表示全行业不存在需求。

本轮只读核：AGENTS、科学契约、PROJECT、上轮审查；当前输入构建及选择源码；14号资源—损失评审及其需求台账；已发布承诺职责评审；旧运行相关性与Level-1论证；Wind Energy阅读笔记、Pritchard reader与Phipps正式版文字；Sun、Serrano和Kowal的公开发表版方法段落；AEMO官方手册、IEA Wind官方推荐实践说明、RES官方仓库README、Zenodo记录说明。未下载、预览或解析任何新运行测量，未运行这些项目的示例脚本。

新增本地关键词检查覆盖`docs/`、`windfarm_moe/`、`scripts/`、`manuscript/`、现有Wind Energy稿与两组既存尽调目录；命中主要为研究协议、源码及作者论证。旧台账曾覆盖438个文本/代码文件、14处命中；这个旧数量不冒称本轮重新完成的全量搜索，也不代表私有合同系统已查。

## 2. 逐项证据闭合

| 待核事实 | 直接证据与定位 | 状态与允许解释 |
|---|---|---|
| 点预测之后另行量化误差／备用 | Sun等2022，printed036303-1引言、-3 §III、-5 Table II；本文明确不以改善点预测为目标，而构造误差分位及备用 | **VERIFIED**：该一般研究问题有直接先行；不是本稿新意或本场站部署证明。[正式版](https://www.ethree.com/wp-content/uploads/2023/03/Machine-learning-derived-dynamic-operating-reserve-requirements-in-high-renewable-power-systems.pdf) |
| 真实系统有遥测→预测→决策的分层 | AEMO2023手册§4.2.1 pp8–10与§7.1 p15说明SCADA输入AWEFS/ASEFS，再供NEMDE使用 | **VERIFIED，不同接口**：存在真实分层；不能替代本研究的单机短缺目标、时钟或两feed制度。[官方手册](https://aemo.com.au/-/media/files/electricity/nem/security_and_reliability/dispatch/policy_and_process/australian-wind-energy-forecasting-solar-energy-forecasting-system.pdf) |
| 新鲜P进入固定旧F下的独立备用器是该真实系统的约束 | 同一AEMO手册§4.2.1规定五分钟周期读取SCADA并更新预测；不是本研究固定旧F的安排 | **UNKNOWN**：AEMO材料不能完成这个用途闭环。它是反对静默等同两制度的对照材料，不是发现本研究信息泄漏 |
| 本研究的共同F、目标及P1输入是什么 | `scripts/run_independent_confirmation.py:240–263`：上游锚点−6；目标+6；`windfarm_moe/independent_confirmation.py:21–35`；`information_subset.py:20–38`：common4与选列 | **VERIFIED，实验定义**：两策略共享同一合成F与未来目标；P1增加当前P；WPQ36增加三个36步历史。源码本身不证明运营需求 |
| 单F是否代表截至t全部已发布承诺 | 既有`COMMITMENT_AND_RAW.md`及上述接口只传同issue的一条F，未登记消息队列或实际接收日志 | **UNKNOWN**：单F是受限实验输入；不能称完整合法到达信息的最强方法。名义publication索引不是接收证明，也不是已证遗漏bug |
| 112→5能兑现什么 | `information_subset.py`及旧资源台账；现实现先构建全宽148列，再切所选列；共同forecast仍用W/P | **VERIFIED**：所选原始learner输入宽度改变。**UNKNOWN**：实际packet、RSS、费用、缓存或传感器可取消性；不能按列宽比推带宽／全系统节约 |
| 场站资料是否证明该备用接口 | Zenodo v2.1.0说明年度十分钟SCADA来源和研究用途；RES README说明下载／缓存／分析 | **VERIFIED**：历史测量与开放研究来源。**UNKNOWN**：独立reserve服务、合同、SLA或P1-only使用者；本轮没有运行其自动下载脚本。[数据说明](https://zenodo.org/records/22662930)，[官方代码说明](https://github.com/resgroup/hill-of-towie-open-source-analysis) |
| 应用评价应按使用者目标设计 | IEA Wind官方推荐实践页面说明选型、试验与评价分别围绕具体应用 | **VERIFIED，一般建议**：支持应用适配的评价动机；它不为本项目2%／10%签署业务容限，也不识别精确两feed需要。[官方说明](https://iea-wind.org/task36/task36-publications/task36-recommended-practices/) |

AEMO文件是2023年版本，本轮不以其证明2026年所有规则及配置仍相同。IEA Part4 PDF直接读取超时／失败；其检索索引中的实时功率建议只作导航线索，不作为已读全文或正文关键引用。未继续搜索额外场站或启动原已终止的CAISO／控制交付主线。

## 3. 六篇近邻：可以新增的判断对象

下表按原文实际方法分工；`gap_role`是与本稿的关系，不是对原文成败的评价。完整机器表见`NEIGHBOR_CLAIM_SUPPORT.csv`。

| 近邻 | 已有知识与原文锚点 | 本稿的实质差异与主张上限 |
|---|---|---|
| Pritchard2011，`mainstream` | §3当前P条件分位数；年度轮换留出；§4额外输入；§5/Table IV与§6比较输入价值及重复 | 不能把当前P有用、复杂输入增益有限或多年度比较称为首创。新增对象是共同F之后、指定短缺损失与绝对事件率条件下，冻结程序的跨年取舍和有限族排除 |
| Phipps等2022，`adjacent` | §3四种后处理位置；§5–6比较最终P一步与天气＋P两步的概率表现 | 不能把分层后简化处理保持表现称为新原则。本稿变动的是备用层原始输入，测的是代理后果及声明资格，不是EMOS位置或CRPS |
| Sun等2022，`mainstream` | §III固定预测后的误差分位；Table II同时列需求量、coverage、exceedance；§V另做系统模拟 | 本稿不首创预测后备用或事件与严重度分开。增量是受控遥测子集及有限族资格；本稿没有同等系统成本／交付证据 |
| Serrano等2024，`adjacent` | §3.2式21–25按留出newsvendor成本选特征并拟合线性决策；§4、§6的实验为合成数据 | 本稿不是决策选特征新算法；采用已拟合有限族、逐fit风险和联合上下界排除。不能把其验证说成只看预测精度，也不沿用旧矩阵“合成及实际”过宽记述 |
| Kowal2022，`foundational` | §2.4式17/19/20定义相对预测损失、可接受集合和最小可接受子集 | 不能把容限集合或最小成员原则作新意。本稿判据／应用不同，没有新的覆盖定理；严格排除声明仍限于登记拟合族 |
| Dantas与Browell2026，`adjacent` | §§2–4分阶段概率不确定性及跨测试年／预测时距比较 | 分层、跨年本身不是创新。本稿固定单F并评价后续输入；不研究同一概率方法或NWP不确定性融合 |

阅读范围：Pritchard、Phipps和Dantas沿用已保存完整正文与既有公式补核，重核上述关键段落；Dantas本轮未重新逐页重读全部19页。Sun、Serrano、Kowal本轮通过公开发表版核对相关方法段落，不声称重新精读全部附录或证明。上轮已核全文的结论与此次抽核一致。没有穷尽所有2024–2026论文，不能据六篇比较声称组合首次。

**INFERRED，可成立的有限经验增量：**在该固定预测接口中，历史选定P1/q=.95以正成本及严重度代价满足固定参照要求；另一历史校准q=.925在次要全族程序中获得不同资格。这个具体实例同时给出可接受输入、代价和识别边界。它不是“越简单越好”，也不证明真实使用者应作这个交换。若期刊要求该取舍对现实接口具有显著技术意义，这项材料缺口仍存在。

## 4. 可供正文采用的有限英文

> Existing work constructs reserve requirements from uncertainty around supplied point forecasts rather than improving the point forecasts themselves. Here, fixing the common forecast isolates a narrower design comparison: which additional inputs a downstream shortfall learner uses, and the associated cost and shortfall trade-off. The specific single-forecast, two-feed clock is a controlled interface; no operator documentation establishes an operational need for its 112-to-5 raw-input reduction.

第一句引用Sun2022；第二句是本稿任务定义，须与本文方法／结果相连；第三句是本轮限定结论，不是外部来源对全行业的否证。若加入AEMO，只能说明不同真实分层实例，不能给本合成接口贴现场标签。

## 5. 仍缺的材料、获取路径与本轮处置

| 缺证ID | 精确缺什么 | 合法获取路径／最小合格形式 | 本轮处置 |
|---|---|---|---|
| I01 | 谁使用固定承诺后的独立reserve learner、为什么不能或不应更新F | 已有系统设计／版本化服务规范／业主需求纪要，明确决策时刻、目标与职责；必要时由作者未来提供合法可披露材料 | 未找到；不联系他人；保持合成评价任务 |
| I02 | 本研究t−6/t/t+6双feed与消息到达集合 | 端点schema及发送、接收、处理时间／时区语义；相同时间下完整承诺访问规则和允许输入清单 | 未找到；不将publication_indices视为到达日志 |
| I03 | 112→5所对应的可避免负担 | 实际订阅／缓存／维护边界或受控实现的资源度量；如果按费用讨论，还需边际价格与可取消条件 | 未找到；不把原列宽／非受控时间升级为净资源收益 |
| I04 | 研究2%／10%容限的业务接受性与缺额严重度要求 | 目标使用者对同一损失／事件单位的书面接受标准；实际采购映射、fallback及PCC责任 | 未找到；阈值保持研究身份，不更改或补写SLA |
| I05 | 任意同信息函数的必要性或族外替代不可行 | 与扩大的主张对应的理论或强比较资格 | 不属于现有证据闭环；V2只谈注册拟合族，不自动加实验 |

这些缺证不使现有配对计算自动失效，也不能靠一般文献或更精美的图补齐。当前可以完成叙述、可见证据桥和复核包；不能据此宣布运行意义已闭合或正式投稿放行。

## 6. 材料身份与不执行声明

`sources.csv`记录准确URL、版本、段落和允许／禁用推论；`metadata/source_status.json`记录本轮读取层级。公开网页只作证据，不执行其脚本或下载测量。未引入任何新实验数字、置信区间、校准档位、阈值、远端作业或新确认窗口；未修改原稿／references、原始结果、PROJECT、科学契约或旧门禁。版权全文仍留在原先不发布的阅读目录，不加入公开复核包。
