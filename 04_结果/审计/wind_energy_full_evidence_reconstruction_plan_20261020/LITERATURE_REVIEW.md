# Wind Energy 重构前的近邻文献核查

日期：2026-10-20。模式：定向文献核验与证据综合。执行入口为 `deep-research` 的 lit-review/fact-check，PDF仅作阅读。已读项目科学契约与PROJECT现行边界；本轮不运行研究模型、统计重算或外部代码，不下载测量，不访问Metis，不改原结果、阈值、V2、论文或科学契约。

**判断：现有全项目证据仍有可凝练的风电应用实证贡献，但不能落在“首次发现工况相关不确定性”“首次缺失数据概率预测”或“预测质量不等于运行价值”。最近文献已覆盖这些原则。本项目较具体的责任，是在共同预测承诺之后，分开检查后果历史、恢复状态分数和真实pitch测量的程序增量，并报告成本、采购、未覆盖缺额和严格事件率各自的变化。** 这是对已完成比较的定位，未认证全球首创；也不承诺这些比较已共同识别纯信息价值或状态的因果必要性。

## 1. 检索、原文和日期边界

围绕三个指定近邻MLWA2026、SETA2026、SAFER，以及Wind Energy领域先行，定向检索2024—2026的missing-data、连续缺失/旧功率、工况概率预测和备用后果研究；新增核查Wen2024、Meng2026、Stratigakos2026及Wen等2025 v2预印本。不是系统性综述，不声称穷尽或正式PRISMA筛选。来源优先为出版社、Crossref、作者/机构库、arXiv及作者公开方法源码；未用第三方生成摘要作方法证据。

`LITERATURE_MATRIX.csv`逐篇给题名、作者、DOI、卷期日期、版本、四维角色、实际阅读范围、已有知识与本项目差异。角色描述本文引用职责，`failing`不能靠缺全文或本项目表现倒推；本轮没有把任何近邻标为已在本项目任务失效。合法原文与提取文字位于本地忽略的`literature_reading/`，不会随文档意外提交。

- **新增取得：** PolyU的Meng正式录用稿12页，UCL的Stratigakos正式录用稿12页，Wen2024 arXiv v3共26页、Wen等2025 arXiv v2共25页，以及Iversen作者网站的12页正式发表版。只下载论文文件，未下载其数据或执行代码。
- **既有原文重新核读：** 用户提供MLWA正式15页PDF；Pritchard官方reader及既有公式图片；Phipps机构库27页正式PDF；Dantas机构库19页正式PDF。既有“全篇已读”记录与本轮方法/结果抽核分开，不能把抽核写成重新逐页精读全部附录。
- **仍无正式全文：** SETA仅核出版社摘要、引言/贡献/章节预览；SAFER核正式摘要与作者固定commit方法源码，未取得最终文章PDF。SAFER早期SSRN稿的题名、作者次序和结果不同，不能充当最终文章全文。
- **日期：** MLWA首页明确online2026-07-21，正式卷期2026-09；SETA刊期2026-10，SAFER刊期2026-12，其Crossref DOI创建日2026-09-27/09-17均不能冒充online日期。Dantas首次上线2025-12-25、卷期2026-02；Iversenonline2016-05-02、卷期2017-01。Pritchard正式首页online2010-07-19与Crossref的2011-03-14字段不一致，保留冲突并用正式卷年2011，不制造两篇文献。
- 本轮Crossref前三篇请求遇429，未循环请求；沿用本地已核Crossref响应，与现可读出版社身份/MLWA首页复核。`literature_metadata/ACCESS_RECEIPTS.json`保留成功和失败；`PROVENANCE.json`给本地原文、复制元数据与来源hash。日期未知仍记UNKNOWN。

## 2. 最近的三篇状态/工况研究

### MLWA：状态与不确定性的联系已被明确研究

Kandemir等，*Explainable uncertainty quantification in probabilistic wind power forecasting*，DOI [10.1016/j.mlwa.2026.100957](https://doi.org/10.1016/j.mlwa.2026.100957)，`mainstream`。用户正式PDF身份、15页完整阅读记录和本轮pp6—9、13及表2/5/6抽核一致。

**已占据的知识：** 运行功率曲线、残差混合、异方差/分位数预测和局部扰动把概率不确定性联系到控制区间；文章有深度结构消融和概率验证。不能说前人只做点预测或没有强模型。

**可核的差异：** §2.2/2.4为前一分钟七个非有功SCADA输入预测下一分钟P，不含当前P及长P历史；其pp6—9、13没有本项目式固定承诺备用动作的C/R/U/V配对试验。故它没有回答本项目“强后果历史之后额外真实pitch/恢复分数的程序增量”。p13的备用用途讨论不能当已测采购成本，局部pitch敏感度弱也不能当条件冗余或状态无用。[正式文章](https://www.sciencedirect.com/science/article/pii/S2666827026001222)

### SETA：极端工况校准与reserve proxy已有直接近邻

Wang与Wang，*Reserve-risk-oriented regime-calibrated interval forecasting for wind power integration under extreme fluctuations*，DOI [10.1016/j.seta.2026.105438](https://doi.org/10.1016/j.seta.2026.105438)，`mainstream`。

**已知：** 出版社公开预览明确工况/时距分位数及保形再校准、稀疏工况收缩和外场评价；引言把下界违约指标限定为reserve-relevant proxy，而非直接运行成本。其核心并非只追求总体覆盖。

**未知：** 完整输入、pitch、全部消融和额外动作/成本分析未读。可说本项目以冻结承诺后的C/R/U/V及等时P替代承担另一项责任；不可说该文全文“没有pitch/没有历史/没有决策分析”。全文排重仍未闭合，不能用用户摘要或索引片段宣布排他新颖性。[出版社预览](https://www.sciencedirect.com/science/article/pii/S2213138826006247)

### SAFER：已有功率重编码不是新增状态测量

Kometsi、Chinhamu与Chifurira，*State-Adaptive Forecast Error Recalibration for probabilistic wind power forecasting*，DOI [10.1016/j.egyai.2026.100900](https://doi.org/10.1016/j.egyai.2026.100900)，`mainstream`。

**已知：** 正式摘要报告状态条件保形、时序分割、依赖块推断与ACI比较，并保留不同预测时距结果不一致。作者固定commit的source cells2/25/29/31/37显示state由日历与当前出力分档形成，比较包括CQR/ACI。不能说其没有P或只比global。

**差异/限度：** 这个state是已有信息的函数；本项目真实pitch测量与恢复分数必须分开。所读主实现的终点为概率可靠性/宽度/Winkler，未建立本项目测量流增量的C/R/U/V比较；这仅限公开主实现，不代替最终稿全内容判断。未请求作者processed数据、notebook outputs或执行代码。[正式摘要](https://www.sciencedirect.com/science/article/pii/S2666546826002260)；[固定源码身份](https://github.com/VinDW/SAFER-Wind-Forecasting/tree/3b0d501ce63425721c17d45cc76835af2846b24f)

## 3. Missing/stale不能再作为空白问题

| 近邻与阅读范围 | 已有知识与实质差异 |
|---|---|
| **Wen2024**，Energy300:131544，DOI[10.1016/j.energy.2024.131544](https://doi.org/10.1016/j.energy.2024.131544)，`mainstream`；作者arXiv v3 §§2—4、5—6，尤其pp13—16输入/缺失/评分 | 六个P滞后；零散/连续缺失与MNAR；missingness自适应非交叉QR，比较插补和完整数据参考。覆盖/宽度/CRPS是其声明评价。不是缺失数据或强功率历史的新问题；本项目新增职责为固定承诺后的测量/表示与动作后果，而非宣称新缺失预测方法。 |
| **Meng等2026**，TSTE17(2):1202—1213，DOI[10.1109/TSTE.2025.3611370](https://doi.org/10.1109/TSTE.2025.3611370)，`mainstream`；[PolyU录用稿](https://ira.lib.polyu.edu.hk/handle/10397/117725) §§II—IV，pp5—10 | 长P序列及目标日历；训练和在线5%—50% MCAR；联合插补/非参数分位与多步递推，已有AQR等比较。概率可靠性、区间宽度和skill评价明确；其研究不等于本项目真实pitch/等时P替代的风险成本任务。所读录用稿不冒充最终版逐字一致。 |
| **Stratigakos与Andrianesis2026**，TSG17(1):806—817，DOI[10.1109/TSG.2025.3620957](https://doi.org/10.1109/TSG.2025.3620957)，`mainstream`；[UCL录用稿](https://discovery.ucl.ac.uk/id/eprint/10215885/1/Learning_Data-Driven_Uncertainty_Set_Partitions_for_Robust_and_Adaptive_Energy_Forecasting_with_Missing_Data.pdf) §§II—V，pp6—11 | 8场24个P历史+6h旧预测，显式连续不可用与forward-fill；鲁棒/自适应模型和小分区。RMSE为声明终点。它已直接触及强功率历史、旧预测及缺失持续时间，故不能仅凭“stale telemetry”措辞称新；本项目把状态额外测量及固定短缺后果另作评价。 |
| **Wen、Pinson等2025 v2预印本**，*Marginalize, Rather than Impute: Probabilistic Wind Power Forecasting with Incomplete Data*，DOI[10.48550/arXiv.2403.03631](https://doi.org/10.48550/arXiv.2403.03631)，`adjacent`；[作者v2](https://arxiv.org/abs/2403.03631v2) §§2、4—6，pp15—20 | 对已观测特征条件化并边缘化未观测量；有自身/邻场历史比较和覆盖/CRPS评价。v2题名已不同于2024v1；截至本轮所核记录为投稿预印本，不能当正式录用。与本项目的差别仍须落在新增测量和后果，不能笼统称首次潜状态恢复。 |

这些文献能说明缺失机制与时效比较已有基础，不能证明本项目合成延迟/扣留在工业界的发生率。连续缺失、固定延迟、某通道永不记录、训练可见而部署扣留是不同信息条件；不要互相替代。

## 4. Wind Energy先行与备用后果的已有边界

| 文献 | 对重构主张的约束 |
|---|---|
| **Pritchard2011**，DOI[10.1002/we.416](https://doi.org/10.1002/we.416)，`mainstream`；官方reader §§3—6及表III/IV，本轮复核额外输入结论 | 当前P的概率持续性、其他输入与不同预测属性、年度变化早已有研究。不能称首次发现P有用、复杂输入收益有限或首次跨年。本项目需要说明新增历史、真实pitch与冻结后果协议实际改变了什么。 |
| **Iversen等2017**，DOI[10.1002/we.1988](https://doi.org/10.1002/we.1988)，`mainstream`；[作者正式PDF](https://henrikmadsen.org/wp-content/uploads/2017/05/leveraging_stochastic_wind_power.pdf) §§3、4，表VI/VII | 直接比较只观测P与P+风速、动态潜状态及额外测量收益随时距减弱。额外测量/恢复状态/信息作用依条件变化不是新概念。本项目对象为更强后果历史后的pitch和同时间新鲜P，固定承诺后C/R/U/V，不是该SDE新模型。 |
| **Bessa等2011**，DOI[10.1002/we.444](https://doi.org/10.1002/we.444)，`foundational`；根代理核官方摘要、§§1—3部分、4.1/4.2及完整§5 | 已讨论forecast quality、market value/reliability及用户利益冲突。因此“预测/表征质量不等于决策价值”只能作评价前提，不能单列新发现。未逐表/公式审计，不借其结果替本项目数值背书。 |
| **Phipps等2022**，DOI[10.1002/we.2736](https://doi.org/10.1002/we.2736)，`adjacent`；机构正式PDF §§3.2、5—6，本轮抽核四位置设计 | 比较既有预测链中的不同后处理位置已有期刊先例；比较研究可有价值，但模块化/简化本身不是方法创新。它的CRPS结论不自动成为本项目备用收益或正式非劣。 |
| **Dantas与Browell2026**，DOI[10.1002/we.70079](https://doi.org/10.1002/we.70079)，`adjacent`；正式PDF §§2—4、Table1、测试年/时距条款 | 已分离天气与weather-to-power不确定性并比较跨年/时距作用。分阶段、跨年或不确定性来源比较不是首创；本项目评价共同F之后额外SCADA。其测试期选优标为理论参考，不能挪为历史冻结选择。 |
| **Zhao等2021**，DOI[10.1109/TPWRS.2021.3053847](https://doi.org/10.1109/TPWRS.2021.3053847)，`foundational`；IEEE摘要/方法目录，未读全文 | 预测区间、采购/缺额成本与覆盖约束的联合决策已有先行。不能称首创备用成本或从概率走向决策；本项目冻结共同预测而另评增量输入。不能据摘要断言该文没有其他附加分析。 |
| **Sun等2022**，DOI[10.1063/5.0087144](https://doi.org/10.1063/5.0087144)，`mainstream`；已有作者机构PDF选择阅读印刷036303-1—2及原方法核读记录 | 既有点预测后建立误差分布/备用层与系统生产模拟已有先例。固定共同预测是本项目控制条件，不自动构成新接口；其系统模拟效益不能赋予本项目代理成本真实市场意义。 |

## 5. 本项目应保留什么，与什么尚未识别

以下依据`all_experiment_contribution_inventory_20261020/CONTRIBUTION_ATLAS.md`及原文件链接；这里只定位已有结果，不新算数字或把不同协议合成一个共同排名。

1. **可保留的阳性：** 监督提高声明状态表征；增加后果历史具有已观察开发成本改善；恢复pitch分数有小幅且依块长度变化的增量；真实pitch在旧信息背景下与强新鲜P后的表现不同；共同档位下采购、缺额严重度与事件率呈不同变化。不能为了否定某条投入路线而抹去这些结果。
2. **不可越界：** 这些结果分属不同固定程序/总体，不能把跨族百分比当同一随机试验的因果交互。新鲜pitch后的成本区间跨零不证明冗余；状态分数的恢复改善不证明物理语义必要；共同q不等于共同采购预算；旧P-only历史预算控制在开发发生漂移，未完成强P-only排他检验。
3. **独立年份的职责：** Towie2025原冻结q=.95固定参照资格与q=.925有限族最小性是可靠的另一个结果层，不能授予新状态分配问题独立确认身份。WTB不识别、MLP不一致和微缺额事件敏感性保留。它们不把全项目变成“只有负结果”，也不使所有状态测量结论都获认证。

**最小可守的新颖性句子（建议，非全球首次认证）：**

> 本研究针对共同风电预测承诺之后的备用层，利用冻结的SCADA对照分开量化后果历史、恢复状态分数与真实pitch测量的程序增量；结果显示其增量依赖可用信息与新鲜度，并可在成本、采购、缺额严重度和严格事件频率上给出不同判断。

更严的英文定位可写为：

> Under a common wind-power forecast commitment, we evaluate the incremental roles of consequence histories, recovered state scores, and measured pitch in frozen reserve procedures, distinguishing information freshness and the resulting changes in cost, procurement, uncovered shortfall, and event frequency.

“增量依赖”在正文须分别列出原对照及区间，保留描述性与确认性身份；不能写成全局统计交互定理。跨年低输入资格与有限族最小性可以作补充贡献，避免再把全稿压成一项子集证书。

**明确不能主张：** 全球首次状态相关不确定性/工况保形/缺失概率预测；全球首次强当前P或功率历史；首次把预测接备用成本；首次发现quality≠value；pitch/状态一般无用；恢复分数证明额外测量信息；复杂状态或图结构因果必要；同q证明同预算；已识别pitch独有信息价值；端到端传感器/带宽/实际市场成本节省；合成延迟代表现场常态。

## 6. 对当前重构计划的文献结论

**INFERRED：** 最有根据的Wind Energy形态是“对额外遥测价值的条件性实证评价”，问题顺序应围绕完整结果链，而非继续包装V2共同预算方法。应让读者看到：增加后果历史的真实收益、恢复语义与决策结果的不同、新鲜P替代挑战、C/R/U/V不同后果、最后才是受限跨年资格。现有文献并未因为占据通用原则，就自动消除这些特定比较的经验知识。

**UNKNOWN：** 尚无穷尽全文排重；SETA/SAFER最终全文缺口仍在。不能称“最近研究绝未做此组合”，也不能以缺全文断定全项目没有新意。若后续合法取得全文，只需按本矩阵同一责任更新差异；不触发实验、改阈值或恢复V2。

本轮为文献与重构规划材料，不声称新的实证里程碑、科学认证或投稿放行。
