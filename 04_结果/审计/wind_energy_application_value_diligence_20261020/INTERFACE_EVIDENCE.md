# 固定单 F 接口真实用途尽调

日期：2026-10-20。REVIEW PROFILE：general scientific，application-interface evidence audit。MODE：只读审查；不修改 Wind Energy V2。模块：paper-review、其 academic-writing-skills 基座、methods-and-assumptions、ai-llm-computational。旧审查只提供检索线索，不充当新增现场证据。

**结论：现有材料不足以把本研究精确的固定单 F 接口确认为真实运行需求；本次没有发现可绑定该接口的真实 owner、服务规范、接收记录或验收责任。官方原文支持预测后量化误差和备用需求的一般用途，但提供的实际接口与本稿有重要差异。此次原文复核不能补齐 Wind Energy 应用重要性所需的具体用途桥。保留受控评价研究价值；不把查无材料解释为全行业不存在需求，也不宣布当前受控单 F 设计存在技术错误。**

## 1. 范围与查找责任

已读本项目 AGENTS.md、SCIENTIFIC_CONTRACT.md（特别是第8—9节）、PROJECT.md 末段、V2 正文接口/目标/资源/应用段、补充接口定义和 interface_review/sources.csv。额外检索现有仓库，而非只重述 GAPS：

- 本地 `rg --files` 清单覆盖910份 md/txt/py/yaml/yml/toml，排除 snapshots、public_review_package、source_static、verification 等重复来源；这是索引规模，不是逐页通读910文件的声明。
- 对现有文字/源码查 `service agreement`、`service.level.agreement`、`SLA`、`forecast feed/API`、`single F`、`gate closure`、`packet`、`接口`、`服务协议`、`运营规格`、`业务/客户需求`、`承诺/发布` 等。严格需求词组检索有30个文件命中；另做原有 docs、规划、理论、文献、源码及稿件的广义运营检索，逐项核读相关命中。
- 原始职责材料包括冻结 decision_protocol、实际输入/目标源码、场站原始 README/数据字典、原 Level-1 与104转发表述。既存14号资源审查和承诺职责审查仅作线索及回归核对；没有把它们的“未找到”再次计为独立证据。
- 公开复核对象仅为现有来源链上的 AEMO、RES、Zenodo、Sun2022，以及既存 CAISO 官方入口的原始监测文件；下表给版本与已读范围。未做新题目/新场站筛选，未访问私有邮件/合同系统，未联系任何人。

没有打开或解析原始大型测量、模型、动作数组；没有运行训练、推理、校准、统计重算、重采样、模拟、测量下载或远端作业。公开 README 的自动下载说明只阅读、未执行。仅新增本报告，不改阈值、论文、原始结果、协议或旧报告，不 commit。

`VERIFIED` 指可定位原文/代码支持；`INFERRED` 指有条件推论；`UNKNOWN` 指无足够材料。限定搜索中的未命中，不证明行业或私人系统中的不存在。

## 2. 直接任务材料：究竟固定了什么

| 核项 | 直接依据（仓库相对路径及行号） | 核实与不能推出的内容 |
|---|---|---|
| 精确时钟 | `experiments/independent_confirmation_20261019/decision_protocol.json:31`；`scripts/run_independent_confirmation.py:240`起，特别243—244、257—260 | **VERIFIED 实验定义**：决策issue为t；共同forecast以t−6为上游历史末端，预测t+6；短缺目标为max(F−P[t+6],0)。名义publication=t−6是研究定义。不是实测发送/接收时刻。 |
| 一条 F 而非全部已到达消息 | `windfarm_moe/independent_confirmation.py:21`起25—29；V2 `manuscript.md:61`与`63`；`supplementary.md:26` | **VERIFIED 受控限制**：common为同issue的一条forecast、时钟两列、ID，再加选定遥测。现稿已说明不是完整真实消息集。不能称截至t全部合法可用forecast/error/update的完整控制器。 |
| “新鲜P”的含义 | `windfarm_moe/information_subset.py:20`起33—38；`windfarm_moe/decision_information.py:25`起25—30；decision_protocol第32行；原始数据字典 `experiments/independent_confirmation_20261019/metadata/Hill_of_Towie_data_dictionary.md:15`起、130、143 | **VERIFIED 实验定义**：delay=0时允许事件时间t的十分钟平均P；P1使用其最后一个值。数据字典证明区间末端UTC及字段单位，不能证明均值在该时刻已被reserve服务生成、传输与接收。“当前”不能静默等同秒级瞬时出力。 |
| 真实用户和决策责任 | decision_protocol第49—69行；`manuscript.md:65`起与79、113、245 | **VERIFIED**：研究定义单机单十分钟短缺代理、rho=10、2%容限和10%事件率。**UNKNOWN**：谁实际采购/激活R，承诺对谁有效，谁接受U严重度、如何映射PCC/备用提供方与fallback。冻结研究阈值不等于运营SLA。 |
| 现场用途的原始来源 | 场站官方README本地副本 `experiments/independent_confirmation_20261019/metadata/github_README.md:5`起、18—28；官方Zenodo说明 | **VERIFIED**：来源具有真实商业场站测量与公开分析用途。该README实际描述升级效益/控制分析及下载/缓存，不提供本项目reserve endpoint、P1-only客户要求或固定单F合同。 |

这是原型任务定义的充分溯源，尚不是其制度需求的外部验证。科学契约第247行明确没有观测到的现场arrival/publication log；第258行也只准许增量输入与合成双feed解释。

## 3. 公开原文复核：支持、反向限定与未知

下列版本均按所读文件本身标识；不把2022/2023文件当成已核2026全套运营规则。各条只列本次实际核读的部分，不声称全文逐页审查。

| ID、角色、读取层级 | 来源、精确版本及范围 | 对本任务的证据方向 |
|---|---|---|
| A01，adjacent，官方原文选段 | [AEMO AWEFS/ASEFS overview](https://aemo.com.au/-/media/files/electricity/nem/security_and_reliability/dispatch/policy_and_process/australian-wind-energy-forecasting-solar-energy-forecasting-system.pdf)，v4，2023-08-07；Table1 p7、§4.2.1 pp8—10、§6.1—6.2 p13、§7.1 p15 | **支持一般分层，反对直接等同精确接口**：五分钟更新；当前MW及其他SCADA参与预测；UIGF与MaxAvail等进入NEMDE。不能据此推成本研究固定旧F、单机目标或P1-only约束。 |
| A02，adjacent，新增核官方原文选段 | [AEMO Guide to Data Requirements](https://aemo.com.au/-/media/files/electricity/nem/security_and_reliability/dispatch/policy_and_process/guide-to-data-requirements-for-awefs-and-asefs.pdf)，v5，2022-09-19；§1.2 p5、Tables1—2 p6 | **支持新鲜P在实际系统有用途，反向限定本研究的测量类比**：瞬时SCADA更新4—10秒，平均值更新最长15秒；dispatch point的P、setpoint、local limit及多项W/状态要求同时存在。它既不证明十分钟P均值即时可得，也不授权删除其余业务信号。 |
| A03，mainstream，作者机构正式版选段 | [Sun等2022正式版，DOI10.1063/5.0087144](https://www.ethree.com/wp-content/uploads/2023/03/Machine-learning-derived-dynamic-operating-reserve-requirements-in-high-renewable-power-systems.pdf)，§III printed036303-3、TableII -5、§V -6/-7 | **强支持预测后备用问题，反向限定single-F类比**：其模型使用在决策时可得的近过去5分钟与近过去/近未来15分钟预测，共34点；目标是不同调度时间层预测差，系统成本另经PLEXOS评估。不是本稿一个冻结F与实测P[t+6]的接口，也不是遥测选列用途证明。 |
| A04，adjacent，官方原始文件选段 | [CAISO DMM Review of mosaic quantile regression](https://www.caiso.com/Documents/Review-of-the-Mosaic-Quantile-Regression-Nov-20-2023.pdf)，2023-11-20；§1 p1、§3.1—3.3 pp6—10、§8 p57 | **支持明确用途与责任的重要性，非本稿业务背书**：实际用于FRP及WEIM充足性；binding/advisory预测差及应用时刻有具体定义，按当前load/solar/wind forecast估计。不同产品定义不能互换。所读定义不等于本稿单机短缺。 |
| A05，adjacent，官方网页 | [CAISO Flexible ramping product](https://www.caiso.com/library/flexible-ramping-product)，历史项目完成页Outcome；[DMM notice](https://www.caiso.com/Documents/dmm-review-of-the-mosaic-quantile-regression-for-estimating-net-load-uncertainty-call-on-12123.html)，2023-11-22全文 | **支持一般真实需求**：存在具名运营者的上/下调节不确定性采购及监测。不是Hill of Towie客户、单F服务或2%/10%接受证据。A04从该notice的正式报告链接取得，不是新测量。 |
| A06，foundational，官方record元数据与Description | [Hill of Towie record22662930](https://zenodo.org/records/22662930)，v2.1.0，2026-09-08；Description关于年度SCADA、Siemens Backup、UTC与period-end | **支持测量来源**：商业场站历史十分钟统计。**UNKNOWN**：端到端消息到达、reserve订阅、单F权限与使用者。未点击或预览年包/fastlog。 |
| A07，foundational，运营者所属仓库README | [RES open analysis repository](https://github.com/resgroup/hill-of-towie-open-source-analysis)，公开main于2026-10-20读取；开篇、Quickstart、DynamicYaw说明、Configuration | **支持已有公开分析用途**：升级/控制效益及本地缓存流程。未出现本研究reserve服务的身份依据；不能由仓库属于RES推导作者方案被RES采用。 |
| A08，adjacent，本次读取失败 | [IEA Task36 recommended practices](https://iea-wind.org/task36/task36-publications/task36-recommended-practices/)；V2 S02旧记录为官方HTML已读，S15 Part4旧记录仅索引 | 本轮直接页面失败；保持其旧读取层级，不升级为本轮新核全文。即使一般应用适配建议成立，也无法单独证明精确单F需求，因此不让结论依赖该入口。 |

V2 sources.csv 的S06—S10属于方法/近邻职责，不能补为真实owner或现场接口材料；本报告不对其做新的全面查新。S11—S12本次已回溯实际源码；S13—S14回溯了其所引用的原字段、代码及旧作者论证。S15未取得全文的身份保持。

## 4. 固定被计分承诺与单 F 可访问信息不是同一命题

**VERIFIED**：当前V2把共同F与目标固定，是为了在同一短缺责任下比较下游策略；代码与论文一致明确受控访问只含该F。没有证据表明这项明示设计是遗漏bug，本报告不重开它。

**INFERRED（条件解释）**：真实系统可以要求对已接受的某版承诺负责，即使后来得到新预测，也仍然用原承诺计算短缺。可是“承诺不改”不自动推出“不能把已到达的新预测、其历史或已成熟误差用于选择备用动作”。前者是目标/责任规则，后者是信息访问/服务边界规则，必须分别有依据。Sun的实际输入安排正说明，在既定误差问题中使用多个已可得forecast是可以定义的另一类接口；不是本研究需要修改为该接口的命令。

要把本研究具体制度写成真实用途，现有材料至少应同时绑定：谁拥有该承诺、为什么在t−6锁定t+6目标、为何t时reserve服务只可见相应一条F、t时十分钟P均值是否已经收到、以及R和U由谁承担。当前这五项没有同一真实场景的证据闭环。不能用一般market gate closure的理论可能性或一条“独立服务可能存在”的作者解释填空。

## 5. 原有强表述不能代替用途证据

- `manuscript/REBUTTAL_PREPARATION.md:62`把104转发屏蔽pitch称为普遍规则，属于作者答辩自述；没有本场站接口/收据/合同绑定。科学契约第131、181行仍将现场发生率列为未知。即便某系统不传pitch，也不能顺带证明不传多版forecast或需要以raw列数为目标。
- `docs/WHY_LEVEL1_SCOPE_IS_SUFFICIENT.md:59`起的代数在作者指定可分假设下成立，不是具体grid-code、采购合同或本项目业务损失验证；第63行的实际合规等同表述不能当外部证据。现稿已经保留代理边界，本报告不建议恢复旧表述。
- 历史协议与自动门禁证明研究规则/结果的一致性职责，不证明运营者接受额外缺额严重度或实收服务。本次不重开图3、统计覆盖或复核包问题，也不将未运行新门禁误记成通过。

## 6. 闭合判断与 Wind Energy 重要性

| 要求 | 现有材料判断 | 对重要性的实际贡献 |
|---|---|---|
| 风/光预测误差需要备用/不确定性评估 | **VERIFIED**，具名官方产品及Sun方法 | 已有背景依据，值得研究；不属于本稿新增业务发现。 |
| 新鲜P是有实际用途的运行输入 | **VERIFIED，在AEMO的不同接口** | 支持选取P作为测量的合理性；不验证本研究P1作用位置、十分钟新鲜度或额外收益。 |
| 本稿精确t−6/t/t+6与单F限制确有真实owner要求 | **UNKNOWN／未闭合** | 此次没有找到可以填补的直接材料。 |
| 真实业务需要112→5且接受相应后果 | **UNKNOWN／未闭合** | 除代码选列事实外，没有owner接受、可避免负担或代理到业务的绑定。 |
| 当前受控比较是否因此自动失效 | **否，不能如此推出** | 它仍可报告预声明有限程序在明确共同目标下的跨年取舍；其重要性只能建立在这一窄的实证知识上。 |

**最终用途判断：EXACT_OPERATIONAL_INTERFACE_NOT_ESTABLISHED。** 此次有界尽调已经得到明确答案，毋须以等待一般文献或重开旧技术议题延长判定。现有官方来源只能补强一般运行背景与接口差异的准确说明，不能把当前V2提升为已证明具有具体运行需求或已兑现遥测价值的应用研究。若要继续论证Wind Energy的重要性，应由现有跨年结果本身承担科学增量；不能声称这轮材料已解决真实用途。以后若出现合法可披露的owner/接口材料，可以改变这个认识论状态，本报告没有证明现实需求不可能存在。

FUNCTIONAL-COMPLETENESS RETROSPECTIVE：已覆盖用途/责任/时钟/信息访问及来源层级；原稿、冻结结果和阈值锁定；直接代码与官方材料交叉核对。未进行现场部署、私有合同调查、全行业系统综述或新数值检验。没有修改需要传播的论文内容，没有图形或运行软件需要视觉/执行测试。本报告足以回答本次“现有材料能否闭合精确接口用途”，不构成整稿投稿认证或新实证里程碑。
