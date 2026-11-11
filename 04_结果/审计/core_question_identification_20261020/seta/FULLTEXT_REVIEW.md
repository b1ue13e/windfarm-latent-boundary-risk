# SETA 2026近邻：全文资格与可识别性审查

审查日期：2026-10-20；收束时钟：2026-10-20 01:29:58 UTC。遵循AGENTS、PROJECT、SCIENTIFIC_CONTRACT与research-skill，已读core_question_reset/MAIN_QUESTION.md。仅公开文献、元数据和本地既有方案审查；未运行实验、模型、测量数据查询，未登录、绕过访问限制或联系作者，未改论文。

## 结论

**文献身份闭合；全文未闭合。当前只能作出版社预览层面的严格比较，不能称完成全文排他性查新。** 本轮确实尝试了出版社、出版社Crossref登记的TDM路径、机构/作者公开稿检索，以及OpenAlex/Semantic Scholar定位；具体成功/失败均见SOURCE_MATRIX.csv。

本支对TSTE继续投入的意见：**当前不支持凭这条差异恢复实验投入。** 原因不是已经证明该文解决了全部拟议问题，而是最接近工作的方法/对照仍有关键未读部分；与此同时，我们尚不能识别理想新增信息价值与两侧估计遗憾。可以保留“真实状态在强后果历史之后何时改变损失相关动作”这个问题，但不能把它写成已证新颖性或已获正面立项认证。最终全项目裁决还须合并另一篇近邻及识别审查。

## 元数据与获取事实

Yang Wang、Haiyun Wang，*Reserve-risk-oriented regime-calibrated interval forecasting for wind power integration under extreme fluctuations*，*Sustainable Energy Technologies and Assessments* 94，105438（2026年10月），DOI [10.1016/j.seta.2026.105438](https://doi.org/10.1016/j.seta.2026.105438)，PII S2213138826006247。Crossref原始JSON与[出版社记录](https://www.sciencedirect.com/science/article/pii/S2213138826006247)一致。

Crossref `created=2026-09-27T11:53:31Z`是登记创建；刊期仅2026-10，未给published-online。OpenAlex给出2026-09-27，但不能用聚合库日期覆盖尚未核实的出版社online日期。Elsevier `coverDate=2026-10-31`是封面日期，也不当首次发表日。

存在重要开放状态冲突：

- Elsevier公开TDM XML请求HTTP200，但只有1885字符的coredata，无正文，`openaccess=0`、`openaccessArticle=false`。
- OpenAlex与Semantic Scholar都标hybrid/CC BY-NC-ND，却只给DOI落地页；OpenAlex `pdf_url=null`、`has_fulltext=false`、`any_repository_has_fulltext=false`。
- ScienceDirect普通HTTP请求403；浏览器仅出现“请稍候”页面，未进行挑战操作。搜索服务可读取出版社索引中的摘要、引言和章节片段，页面同时显示组织访问/购买PDF。

所以不能把聚合库OA标签当作全文可得，也不据一次403断言论文全球不可公开取得。未取得论文PDF，不存在“已读PDF”的文件或页码。

## 已核重叠：严格止于预览

出版社预览明确：冻结作者预训练iTransformer，训练适配器和分位头；使用爬坡、波动及高低出力工况，按工况和时距校准并对稀疏组收缩。源场99/200MW，外场240MW。贡献段称外场不重训或重校准；备用相关指标被界定为下边界违约代理，而非系统运行成本。标准CQR是摘要明确列出的对照，并宣称包含消融等分析。

以上已足以排除“首次将工况纳入分位/校准/备用风险评价”的表述。它不是已证明本项目全部拟议解释问题均被回答。

## 逐项审查：已知、未知与需要的识别条件

| 检查项 | 当前读到的证据及状态 | 不能推断 / 真正需核条件 |
|---|---|---|
| 工况定义与未来泄漏 | VERIFIED：预览列出工况类别，讨论历史滚动指标和因果在线定义的可用性。UNKNOWN：该方法实际公式、窗口、阈值估计和工况索引 | 不能把引言提到因果定义当成实现证明，也不能因此指控泄漏。训练样本可用成熟后的标签构造权重；真正危险的是校准组/测试动作调用尚未到达的未来工况 |
| 输入、current P与history | VERIFIED：数据片段包括有功、风速、风向、温度；框架片段提到多变量历史。UNKNOWN：完整变量列表、最后可用时间、输入长度与pitch是否使用 | 不能说它没有当前功率强对照；也不能认定其全部工况只是I的重编码。必须拿到实际信息集与列消融 |
| 预测时距 | VERIFIED：按时距报告/校准。UNKNOWN：采样间隔、h集合、是否滚动多步、目标对齐 | 不能拿本项目h=6或60分钟直接套用 |
| 分位数与校准 | VERIFIED：工况加权分位学习、条件校准和稀疏收缩。UNKNOWN：分位对、nonconformity score、收缩系数/支持量、校准更新规则 | 90%区间不自动等于本项目单侧q=.90；未读公式不得混同上下界违约概率或非对称损失最优动作 |
| 完整对照 | VERIFIED：标准CQR明确出现。UNKNOWN：全部表格、同信息直接模型、currentP/完整历史参照、额外原生状态对照、随机/语义控制、配方预算 | 不能因预览未列而称不存在这些对照；也不能因宣称消融就视为已覆盖本项目I、(I,Z)、(I,f(I))区分 |
| 消融与统计 | VERIFIED：贡献段宣称有时距/工况/时间/消融/计算分析。UNKNOWN：消融具体操作、seed、时间相关推断、选择与测试分离 | 不把“有ablation”当因果机制识别；不把未读统计当统计失败 |
| reserve终点 | VERIFIED：作者将主要备用相关评价界定为边界违约proxy。UNKNOWN：详细定义、是否另有采购量/短缺量/损失分析 | 当前不能将其收益当真实系统成本下降；我们也不能只给proxy改名为cost就取得机制创新。若新增同一固定承诺的配对动作和损失，必须说明它回答什么新问题 |
| 外场是否重训 | VERIFIED：公开贡献段明确称不在目标场重训或重校准 | 不能继续把它描写成目标场本地重训。UNKNOWN：归一化、预训练暴露、源场校准映射、最终冻结等详细证据；其公开主张尚非我们的独立复验 |
| 状态独立标签 | UNKNOWN：原生控制测量、出力派生工况、未来事件标签是否区分 | 本项目必须分清真实测量Z与重编码f(I)。否则不是对该文增加独立信息问题 |
| 数据/代码公开 | UNKNOWN：完整data/code availability段及补充材料未取得 | 不能称完全可复现或没有数据；本轮不采集测量数据核验 |

## 对当前单一主问题的实质影响

当前主问题是“已有功率等后果历史后，真实状态何时仍提供未来短缺的增量信息并改变动作”。本论文已覆盖条件校准和备用相关风险，故这些组件是必须承认的直接先例。我们的可讨论差异只有：

1. 保持I、共同预测承诺、目标、损失与评估总体相同，把新测量(I,Z)与同信息重编码(I,f(I))明确分开。
2. 将未来分布差异、相应分位动作差异和实际拟合程序收益分开检验；不能从pitch恢复误差直接跳到价值。
3. 对负结果给出有意义幅度边界，允许条件冗余、目标不敏感、估计未有效利用等解释无法区分；不因不同算法结果挑出唯一原因。

这三条是我们应承担的证据责任，不是本次已经证明SETA没有做的内容。**特别不能宣称：该文未来泄漏、没有强基线、没有真正外场、已经解决全部状态价值问题，或我们已经明显超越它。**

## 归档身份与阅读范围

保存的是公开元数据/访问响应，不是论文全文：

| 文件 | SHA256 |
|---|---|
| crossref.json | 1e51cdc97b2b4e713a7265d070259fab1384363950c00721add4e2759aefa332 |
| openalex.txt | 192f2a48b5df4e06433a86a9e2426f03f105d793215c4a5db401588d9627d04b |
| s2.txt | 247db585870cfb5cd84dabbfcf377dea7b9bb776eb6a2b00cd695ae9adc02f66 |
| elsevier_tdm.txt | 153ec85fc2029724a0cda89f69c30ef1c4f14db66e9858629d74ddb6e42e389e |
| linkinghub.txt | 5751c0fff190bec4c78176a760c51306f1f39d33476b15eae29e9ad7da844927 |

文献角色：`mainstream`，不是已核实失效的`failing`。阅读等级：`PUBLISHER_PREVIEW_PLUS_VERIFIED_METADATA`。全文判断：`NOT_CLOSED`。未stage论文或执行git提交。
