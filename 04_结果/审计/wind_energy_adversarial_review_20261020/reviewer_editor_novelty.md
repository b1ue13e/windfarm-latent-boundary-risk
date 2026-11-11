# Wind Energy 编辑与新颖性对抗审查

日期：2026-10-20。角色：严格的期刊编辑／新知识审查；模拟意见，不代表 Wiley、编委或真实投稿裁决。

**裁决：当前版本不建议直接作为 Research Article 投稿；本角色给出 desk-reject recommendation，允许实质补强后重新判断。** 原因是可核实的新结果存在，但“跨年确认＋有限族最小性”主要增加了本项目结论的可信度和精确范围，尚未充分说明它解决了哪个有实际约束的风电信息接口问题。不是发现了相同论文，也不是因为没有新网络、OPF、新年份或第二个阳性站点。

## 审查依据与阅读边界

- 已先读 `AGENTS.md`、`docs/SCIENTIFIC_CONTRACT.md` 第8–9节、`PROJECT.md` 末节；完整读本轮 `manuscripts/wind_energy/manuscript.md`（250行）及 `supplementary.md`（245行）。
- 本报告形成前未读该稿 `qa/`、验收记录或 `FOUR_QUESTIONS_CN.md`。四问问句由主代理单独提供，未提供既有答案。
- 技能：`paper-review`，以 `academic-writing-skills` 为完整性基础；加载 computational 和 overlay-contract 模块。本角色只负责编辑意义、实际方法近邻和新知识边界；没有独立复现统计覆盖率、重新验算模型输出或审核全部远端资产。
- **VERIFIED**＝直接稿件／原始论文／官方指南可核；**INFERRED**＝本角色判断或推论；**UNKNOWN**＝本轮无足够材料。下文 S0–S4 是问题严重性，不是证据可信度；S3阻断所指定阶段，S4为已证实的根本性失效。本角色没有发现S4。
- 本轮仅新增本报告；未改稿、阈值、原结果、科学契约、PROJECT或既有矩阵；未训练、推理、校准、重采样、仿真、读取新测量、访问Metis或联系编辑。未执行任何科研里程碑门禁，不以本报告宣称新实证里程碑通过。

## 官方期刊依据

**VERIFIED：研究主题在范围内。** [Wind Energy 官方范围](https://onlinelibrary.wiley.com/page/journal/10991824/homepage/productinformation.html) 的 Principal Topics 包括预测、控制与传感器、电气集成、运行与性能优化。一个清楚界定的风电信息接口实证研究可以属于这些范围；新网络、AC-OPF及新增独立年份都不是该页面规定的普遍硬门。

**VERIFIED：范围吻合不等于达到文章意义要求。** [官方作者指南](https://onlinelibrary.wiley.com/page/journal/10991824/homepage/forauthors.html) Article Types 要求 Research Article 对知识有显著贡献；Peer Review 部分规定先由主编判断质量和相关性。该指南另规定8000词上限、摘要至多250词、至多6关键词；允许Free Format和已有方法评价。Data Sharing 部分明确期待公开归档支撑结果的数据与其他资产，并在声明中给出仓库链接。

**INFERRED：本稿是“范围可过、意义仍弱”的稿。** Phipps的已发表评价研究说明没有新预测器本身不构成否决理由；Dantas的73场／多年设计也不能变成所有稿的统一样本门槛。真正的问题是本稿尚未像这两篇那样，把比较结果转换为一个足够具体、可复用的风电技术认识。

## 六篇指定近邻：实际方法、结果与剩余差异

以下均使用原始论文或官方正文核查，不把文献矩阵的评价当作原论文事实。`gap_role`只表示与本稿的关系，不暗示该文在本任务失效。

| 先行与角色 | 本轮实际核到的方法／结果锚点 | 对本稿新颖性的约束；仍然不同之处 |
|---|---|---|
| Dantas & Browell, *Wind Energy* 29(2), e70079，DOI [10.1002/we.70079](https://onlinelibrary.wiley.com/doi/full/10.1002/we.70079)；`adjacent` | **VERIFIED**：§2.1以quantile GBT建weather-to-power模型；§2.2以分位距决定核宽并作beta-transformed pooling；§3.3／§4使用2021–2023的不同测试年，区分两种不确定性及其随预测时距的变化。 | 已有分阶段信息来源比较与跨年研究，不能把“分层＋跨年”本身当新知识。本稿没有同一方法；它固定承诺、比较后续输入并计入短缺损失，不研究6–162小时NWP不确定性组合。该文带来可解释的时距规律，本稿尚无对应的一般性规律。 |
| Pritchard, *Wind Energy* 14(2):255–269，DOI [10.1002/we.416](https://onlinelibrary.wiley.com/doi/10.1002/we.416)；`mainstream` | **VERIFIED**：§3当前P的spline quantiles；2005–2008各完整年轮流holdout；§4–5比较更多输入和交互。Table IV及§5报告小大模型IQR均值接近，但resolution改变；§6指出额外变量可能重复其他输入的信息。官方reader L151–155、L287–306、L318–322可定位。 | 直接击穿“当前P已足够／多输入增益小／跨年稳定性是新发现”的宽泛说法。不同处是本稿共同F条件下的特定损失、绝对事件率限制及有限族排除；Pritchard未给这套确认对象。其holdout并非本稿严格前向封存，不能抹去本稿冻结时序的可信度增量。 |
| Phipps et al., *Wind Energy* 25(8):1379–1405，DOI [10.1002/we.2736](https://onlinelibrary.wiley.com/doi/10.1002/we.2736)；`adjacent` | **VERIFIED**：§3的Raw、One-Step-W、One-Step-P、Two-Step-WP；固定简单预测器比较EMOS位置，§4瑞典2015–2017训练、2018–2019评价。§5–6认为最终P后处理一遍与天气＋P两遍表现相似，前者步骤少；本地PDF文字§5约L608–620。 | “同一上游过程后减少下游处理而保持近似表现”已有很具体的本刊先例。本稿的比较单位是reserve层输入而非EMOS位置，且有明确非劣与排除规则；该先例不能认证本稿统计覆盖或实际节省，但要求本稿给出同样清楚的工程选择含义。 |
| Sun et al., *JRSE* 14:036303，DOI [10.1063/5.0087144](https://www.ethree.com/wp-content/uploads/2023/03/Machine-learning-derived-dynamic-operating-reserve-requirements-in-high-renewable-power-systems.pdf)；`mainstream` | **VERIFIED**：printed036303-3的§III用MLP/pinball、既有预测及已到达的日历／天气／误差lag，预测误差分位；2019十折。Table II同时报需求量、coverage、平均／最大exceedance；§V另用PLEXOS评价系统后果。 | 不是首次在点预测之后建立分位备用层，也不是首次指出事件频率不足以替代缺额严重度。本稿的跨年冻结比其同年CV职责不同，且专门问增量通道及族内最小性；Sun没有回答这个窄问题。不能借本稿冻结更严而声称其既有结论不可信。 |
| Serrano et al., *EJOR* 315(2):703–714，DOI [10.1016/j.ejor.2024.01.025](https://publications.polymtl.ca/57338/1/2024_Serrano_Bilevel_optimization_feature_selection_data.pdf)；`adjacent` | **VERIFIED**：§3.2式21–25在validation以newsvendor成本选子集、training拟线性决策；MILP化并比较CV及正则化。§4和§6明确其本论文实验是**合成数据**；低几百样本可恢复相关输入，成本改进或持平。 | “按下游非对称决策成本选输入”是直接先行。不同处在本稿的已拟合有限族、每实例事件率约束与同时界／更小者排除，而非双层选特征算法。既有`closest_literature_audit_20261019/literature_matrix.csv` L4写“合成及实际数据”过宽，本轮不沿用；未改原矩阵。 |
| Kowal, *JMLR* 23(108):1–38，[官方发表版](https://www.jmlr.org/papers/volume23/21-0403/21-0403.pdf)；`foundational` | **VERIFIED**：§2.4式17定义相对样本外损失，式19定义容限与预测概率下的acceptable family，式20取smallest acceptable subset；§4有教育数据及众多近优子集。 | 直接击穿“容限内可接受集合＋最小成员”概念首创。不同处是其Bayesian predictive判据与本稿同时事件／成本上下界；本稿明确排除所有较小者比单纯列出已合格最小者更谨慎，但没有建立新的覆盖定理，也不能仅凭逻辑更严格推成新统计方法。 |

**VERIFIED：当前正文已正确承认主要先行。** `manuscript.md:49–55`、`:227`明确说当前P、分位数和选子集原则既有。因此上述重叠是“剩余增量够不够”的编辑问题，不是本稿偷换或抄袭的证据。

**UNKNOWN：没有核到完全相同的先行，也没有完成全领域穷尽查新。** 不能用六篇各回答一部分，推导已有一篇完整完成了本稿全部任务；同样不能因暂未发现同构论文就宣布组合首次。

## 有界2024–2026查新

查新日期同上。检索围绕wind power probabilistic forecasting／feature selection、decision feature selection／reserve、minimal subset及telemetry noninferiority；仅将原始论文、出版社和作者代码／机构版作为事实来源。检索不以“recent”替代发表身份，不下载任何测量数据。

1. **Rutyna, 2025, *Wind*（MDPI）5(4):28，DOI [10.3390/wind5040028](https://www.mdpi.com/2674-032X/5/4/28)，`adjacent`。** 官方检索正文显示§3.1的lag–feature sigmoid gate、top-M/top-k预算，§5.2预测比较；作者[代码仓库](https://github.com/InajaraRutyna/lag-feature-selection-gate)确认身份。官方摘要称降低输入维度与训练时间、保持／改善预测，正文目标写≥96%。**阅读限制：**官方HTML/PDF直接取回本轮403／429，只有官方索引正文片段，未逐页读完整全文。故仅作“输入裁剪不是新主题”的新查新线索，**不**据其认定完全覆盖本稿；尚不能认证其数据泄漏控制、统计界或工程节省。它与Wiley的**Wind Energy不是同一刊**。
2. **Regional Wind Power Forecasting Based on Bayesian Feature Selection**, *IEEE TPWRS* 40(1):113–124，DOI [10.1109/TPWRS.2024.3388011](https://ieeexplore.ieee.org/document/10497893/)，`adjacent`。官方摘要核到2024在线／2025卷期、NWP子区域裁剪和Bayesian sequential optimization，三国区域出力；未取得全文，不用于完全排重。预测误差目标有别于本稿固定F的风险／成本资格。
3. **Zhang, Deng & Wang, *Omega* 141:103508，DOI [10.1016/j.omega.2025.103508](https://www.sciencedirect.com/science/article/pii/S0305048325002348)，`adjacent`。** 官方摘要／导论核到2026卷期，decision-based feature selection、nonparametric weighted SAA及保守bootstrap盈利评价；正文方法完整性尚未知，不能称其联合界等于本稿。但进一步收窄了“决策选输入＋保守统计评价”组合的概念新意。
4. **von Zuben & Schell, [Minimum Open Data Subset for Wind Power Prediction](https://wes.copernicus.org/preprints/wes-2025-29/)，`adjacent`。** 官方页面明确是2025 discussion preprint，讨论后未获继续评审。只把它作为题目易触发“已有人做最小输入”的阅读风险；不当作已发表接受先例，也不从其未接受推断本稿会被拒。其预测／资源评估任务不等于本稿reserve层损失。

这轮查新未形成一个“已核全文且完全击穿本稿窄主张”的新增论文。指定近邻已足以判断概念增量很小；新查新限制须原样保留，不能写成“最新文献排重闭合”。

## 四问独立判断

| 问题 | 判断及认识论状态 | 对应稿件锚点 |
|---|---|---|
| **Why care? 为什么重要？** | **部分成立。VERIFIED**：非对称短缺后果与输入重复确是可研究问题。**INFERRED**：若有人必须在既有预测之后单独维持一个受限输入接口，则量化112→5的损失代价有用。**UNKNOWN**：谁受这个约束、为何不能取得已有W/P、为何需要独立reserve learner；稿件没有真实服务契约、技术文档或受限接口实例。一般的风电波动动机不足以证明这个特定实验接口重要。 | `manuscript.md:47`、`:61`、`:97`、`:219–221` |
| **What's new? 贡献什么新知识？** | **窄经验增量成立，概念／方法新意不成立。VERIFIED**：在该历史程序和2025人口下，当前P附加策略以成本+0.5641%、U+2.1843%满足一个固定参照要求；不同offset在有限族内排除了15个更小者，WTB没有识别最小性。**INFERRED**：这是可复核的条件化案例，最有用的认识是“预选策略达标”与“事后族内最小”可能分离。单凭跨年、联合界和有限族计数，尚不足把它提升为显著新风电技术知识。 | `:55`、`:168–195`、`:207`、`:225–227` |
| **Why believe it? 为什么证据够？** | **对窄陈述较可信，对外推不够。VERIFIED**：稿件与契约8–9一致地区分主q=.95／次q=.925；共同目标、正溢价、严重度增加和负结果没有被隐藏。**UNKNOWN（本角色）**：未独立核远端全部字节、所有统计坐标或bootstrap覆盖。**INFERRED**：前向冻结增强可信度，但不会增加独立气候年数；共同老F＋新P的结构仍限制结果适用接口，当前P本身有先验预测价值。不能由族内排除推出物理通道必要性。 | `:83–119`、`:146–160`、补充`:141–155`、`:219–245` |
| **Why this venue? 为何Wind Energy读者关注？** | **范围成立，意义尚未过关。VERIFIED**：预测、传感器、控制及运行属于官方范围，且已有Pritchard／Phipps的输入／流程评价文章。**INFERRED**：若能证明一个重复出现的信息接口约束，并给出当前案例可传递的判断原则，风电读者会受益。当前更多读到项目如何封存、如何排除和如何不越界，少看到自己何时该改变输入设计。因此本角色不给直接送审建议。 | `:217–235`及官方Scope／Article Types |

## 可击穿“跨年＋有限族”的具体攻击

**E1｜S3，意义／应用问题；INFERRED，open；阻断：当前Research Article编辑初筛。**

短锚点：“functional order”与“builds the common 148-column feature matrix”（`:97`、`:221`）。已核实的减少是所选函数输入宽度，当前实现不因此少建feature matrix，上游W/P仍保留；实际节省为UNKNOWN。又因为成本和短缺严重度都变差，论文现在没有量化一个能与这些代价交换的工程收益。无实测节省并不使结果为假，但使“为何值得做这个简化”没有完成闭环。最低修复不是再加免责声明，而是指出一个有依据的接口／集成约束和可接受的收益对象。若没有这类依据，应收缩为有边界的任务评价；不能把名义原始列宽当作替代收益。

**E2｜S2，概念新意／文献定位；VERIFIED重叠＋INFERRED编辑意义，open；阻断：以方法创新或组合首次为卖点的叙事。**

短锚点：“observed trade-off across years and evidence excluding smaller candidates”（`:55`）。Pritchard已有多完整年小大输入比较，Phipps已有简化下游处理，Sun已有预测后reserve与severity，Serrano已有下游成本选输入，Kowal已有近优族与最小成员。该稿的诚实写法已避开首创；仍需解释本任务的新经验事实为什么改变认识，而非仅把已有原则运行得更审慎。多重比较、封存和完整负结果是优点，不能独自承担新颖性。

**E3｜S3，应用对象；VERIFIED设定＋INFERRED重要性，open；阻断：telemetry requirement的运行解释。**

短锚点：“synthetic two-feed information interface”（`:61`）。共同F来自截至t−6的W/P，目标t+6，决策层可取新P；此时试验自然带有“用新观察更新旧预测”的强结构。P1与WPQ36仍是公平的同条件比较；这不是泄漏指控。缺口在于没有材料说明该两feed及固定F为何是实际相关边界，而不是主要制造当前P增量的受控选择。可保持此任务作为明确的受控研究，但无法只改几句文字就把其存在频率／业务必要性核实。

**E4｜S2，识别对象；VERIFIED，open；阻断：把minimumness当作一般输入必要性。**

短锚点：“15 smaller candidates”（`:195`；补充`:155–179`）。这15个是Common两估计器×五offset及persistence×五offset；不是十五种独立物理信息来源，也不含所有不用新通道的函数或更强Common拟合。不同单通道／实现可在resource tuple上并列；排除15个的逻辑任务已经清楚。故当前族内陈述可保留，不能以“排除全部更小者”反向宣称同等规模的信息必要性理论。若要扩成一般必要性，必须新增相应方法或证据，不能在本轮偷偷扩族。

**E5｜S3，正式发布资产；VERIFIED缺少链接＋UNKNOWN公开可得性，open；阻断：投稿包完成。**

短锚点：“accompanying reproducibility materials”（`:245`；补充`:233–243`）。当前材料大量链接本机项目相对路径，未给长期公共仓库地址；指南明确期待结果支撑资产的公共归档与链接。缺失权重是否必须全部公开须按最终再现责任说明，不可冒称全包已有。应先把现有足够复核主张的代码／配置／聚合统计／排除记录准备成具体可检查发布包，补声明及作者所需信息；是否正式发布由主任务授权范围决定。此项不需要新模型或新年份。

## 投稿前最小动作，按证据负担区分

### A. 写作即可修

1. 把新增认识集中为一个明确的风电接口取舍：固定老F之后，新P能达到何种明确资格、以什么成本和severity代价。保留“主预选达标／次要族内最小不同”的核心，不再用封存数量或病例计数承担贡献。
2. 用一小段实际方法对照交代Pritchard、Phipps、Sun、Serrano、Kowal分别已做什么，本稿究竟增加哪个判断对象。当前已有承认，不必扩成防御性长清单。
3. 让“requirements”和“resource”始终落在增量函数输入及注册序；不把人工margin写成业务可接受性，不把positive premium写成代价可忽略。当前稿大体做到，需在任何投稿信／摘要后续版本继续保持。

### B. 现有资产可核，无须新研究计算

1. 将freeze／protocol、主结果、15个排除记录及WTB负结果形成可长期定位的最小公开复核包；核验真实链接和相对路径可用性。原始SCADA不入Git，合法数据入口及版本可替代再分发。
2. 只读核查已有工程／协议文档是否已存在两feed边界、独立reserve接口或输入访问限制的外部依据；区分“本实验这样设定”与“真实系统这样运行”。如没有，明确记录缺失，不从论文设定自证应用需求。
3. 固定本稿primary／secondary及claims对应证据，准备与近邻差异的简表。既有运行时间和文件大小只能按记录实际含义披露，不能变成受控online节省测量。
4. 阅读范围记录纠正Serrano实验类型；Rutyna及其他新增近邻若仍用来支持具体方法差异，需取得合法完整正文后补核。本轮访问失败不能被写成完成。

### C. 必须新增证据，才可增加相应强主张

1. **要声称该输入缩减具有实际工程收益：**需有具体接口约束的证据，并对相关收益作匹配的测量或分析；例如真实集成条件或受控子集实现的开销。无需预设一定要传感器拆除、OPF或再训练新网络。当前资产声明不能替代这种证据。
2. **要声称该minimality超越冻结程序／族：**需进一步的函数族覆盖、理论识别或独立方法资格；注册15个小候选的排除本身不够。若只保留有限族陈述，则这项新增证据不是必做。
3. **要把资格提升为业务可靠性／短缺安全：**需有相应服务指标、severity或交付证据。现有10%事件率和2%平均proxy容限不认证这些对象。若不作该主张，则无需为迎合期刊虚构新实验。

**最小投入建议（INFERRED）：**先做A与B，检查能否找到一个已有依据的、足够重要的信息接口问题；若找不到，不建议仅凭进一步润色就把当前稿当作稳妥Wind Energy Research Article。C类动作必须围绕最终实际主张另行授权，不能自动恢复已停止实验。没有要求补新年份，也不把新数据采集作为默认出路。

## 完整性回看

已覆盖当前正文与补充全文、官方范围／作者指南、指定六篇实际方法结果以及一轮有界新查新。没有读旧qa、验收或四问答案；没有完成视觉排版复审、远端字节审计、统计覆盖认证或全领域系统性排重。新查新的全文可得性限制已明确。论文事实与契约8–9未发现越级冲突；主要开放问题是S3的编辑意义／接口应用依据／发布资产，而非已经证实的造假、泄漏或数值错误。**准备状态：可用于主代理综合裁决；不构成投稿放行。**
