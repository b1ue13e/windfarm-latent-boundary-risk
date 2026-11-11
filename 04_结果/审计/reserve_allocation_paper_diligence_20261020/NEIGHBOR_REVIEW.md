# SETA与SAFER：实际取得的方法证据与差异

2026-10-20。不以摘要代全文，不执行作者代码，不取作者数据文件。SAFER新增的是作者公开方法源码的阅读；SETA仍只有出版社预览/片段。没有据此指控任何论文实验不真实、未来泄漏或基线不公平。

## 1. SAFER：核心公开实现已核，论文PDF仍未取得

文献：Kometsi、Chinhamu、Chifurira，*State-Adaptive Forecast Error Recalibration for probabilistic wind power forecasting*，DOI10.1016/j.egyai.2026.100900。出版社数据可用性链接到[作者仓库](https://github.com/VinDW/SAFER-Wind-Forecasting)。Crossref/出版社身份核对通过；刊期2026Dec不冒充online日期。

固定commit `3b0d501ce63425721c17d45cc76835af2846b24f`。主notebook共60个cell、30个code cell，取source字段阅读；未执行、未审阅/保存outputs/attachments，未请求data/processed、release datasets或results文件。响应与Git blob身份核对通过，见[SAFER_SOURCE_RECEIPT.json](SAFER_SOURCE_RECEIPT.json)。本地method_source副本不提交Git；关键方法锚点按notebook cell编号可公开重查。

| 核查点 | 代码锚点 | 已核内容 |
|---|---|---|
| 对象与分割 | cell2、23、37 | 小时Eskom/ERA5；训练/验证/校准/测试55/10/20/15；实际结果未重算 |
| 信息/状态 | cell2、25、37 | 季节×四时段×当前wind_generation_mw三档构造48格；档界由校准段估计；状态是已有出力/日历重编码，不是测得pitch |
| point/CQR可用上下文 | cell23、27、31 | numeric特征排除target和派生state列；当前generation不是排除项；CQR用同一feature_cols的HGB分位器。未打开加工数据，完整实际列/lag与原始建表时钟未复验 |
| SAFER机制 | cell29 | 绝对预测残差的组内保形分位，最小支持30及层级回退，构造上下预测界 |
| 强比较 | cell27、31、37 | 线性/RF/CatBoost验证选择；global、SAFER、CQR、ACI比较；不再将其简化成仅比global |
| 自适应 | cell31 | ACI顺序更新alpha，gamma=.005，校准分数样本固定；没有本项目式多步标签成熟/消息到达的完整资格证明。底层加工数据索引未读，不据此指控泄漏 |
| 终点 | cell33、35、37、57—58 | 点精度、覆盖/宽度/Winkler、条件指标、DM及移动块bootstrap；主公开实现未定义pitch增量、承诺消息可用格、R/U采购账本或共同预算分配 |
| 运行范围 | 仓库README方法说明 | ERA5是事后再分析，作者明确其回顾方法评价范围；不贬低成未作时间切分或没有新测试 |

这已足以核清**作者公开主实现**的核心职责，没有宣称逐页读完最终文章、复现数值或审过所有补充材料。公开OA标记与实际正文访问分开：本轮普通浏览器停在验证页面，未完成挑战；官方XML HTTP200仅1938B/coredata，无正文。未绕过访问控制。

**与本项目的实质差异：** SAFER的state=f(I)，本问题是增加测量流Z后，对同资源行动后果是否还有程序增量。公开主实现没有完成这一比较；这是一项真实的责任差异。**不能据此说**SAFER缺当前P、没有现代校准基线，或本项目首次做状态自适应校准。完整稿与公开实现是否逐项完全一致未证实，不能把代码读完等同论文全文认证。

## 2. SETA：主贡献范围能区分，完整方法不能冒充闭合

文献：Yang Wang、Haiyun Wang，*Reserve-risk-oriented regime-calibrated interval forecasting for wind power integration under extreme fluctuations*，DOI10.1016/j.seta.2026.105438，PII S2213138826006247。Crossref与[出版社预览](https://www.sciencedirect.com/science/article/pii/S2213138826006247)一致。

本轮核出版社索引可见的摘要、引言、贡献和章节片段；正文仍需机构访问/合法作者稿。直接文章接口一次429后停止，不重复请求。已有作者机构、OA索引与仓库检索未给新全文，本轮精确题名/DOI/公开方法检索亦未找到可核新稿。SSRN搜到的是SAFER早期不同题名/作者顺序/结果的稿，**未拿它替代SETA或SAFER最终文章**。

已确定：冻结预训练iTransformer、轻量适配/分位头、极端工况学习、工况/时距再校准与稀疏支持收缩；99/200MW源场及未见240MW外场。公开引言明确其reserve终点是下侧预测界违约代理，未把它解释成直接系统运行成本。

因此，**固定承诺、真正等资源行动、未覆盖缺额严重度及实际状态测量的替代责任，与其公开主贡献不同**。但完整输入、pitch是否参与、全部消融和可能的附加决策分析未读，不能断言全文绝无这些内容；也不能把“预览没列”记作它失败。

**缺口裁决：** 有可研究的声明责任差异；尚无对SETA全文的排他性新颖性证明。取不到全文不是科学否证，但缺少排重时不能把这个候选当已证顶刊缺口；取得全文本身也不补齐本项目的运行和验证证据。

## 3. 该差异究竟有多大

| 命题 | 本轮结论 |
|---|---|
| 状态/工况相关误差与条件校准是新意 | 否，近邻已明确覆盖 |
| 现代P-only校准没做，只有global可比 | 否，SAFER明确CQR与ACI；本项目必须面对完整合法上下文 |
| 新测量Z与既有I重编码应分开 | 是，SAFER公开源码中的state来源可核，不能把其state效果当新增传感器价值 |
| 共同资源行动后果比区间proxy多一项责任 | 是，公开实现/SETA声明核心的目标有实质差异；不等于首次决策评价或已证TSTE贡献 |
| 当前已经能改变读者的运行判断 | 否，尚无该差异的合格实证/新理论。改变评价责任只是研究设计，不是结果 |

结论不是“前人已经解决全部问题”，也不是“只要加预算就比前人先进”。本项目缺的是重要且可信的新知识，而非再增加一个指标或自建复杂分配器。
