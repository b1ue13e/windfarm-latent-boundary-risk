# 检索与排除记录

检索日期：2026-10-19，按Asia/Shanghai客户端日期。目的为对照R1固定参照确认及R2有限族最小性，不是扩充一般风电预测综述。

## 三轮检索

|轮次|实际采用的代表查询|用途及结果|
|---|---|---|
|问题词|`"wind" "telemetry" "minimal" "reserve" information`；`"wind power" "minimal" "risk" "feature selection" reserve telemetry sufficiency`|搜索同一任务接口；大量结果与本问题不匹配，不将未命中完全相同标题作为新颖性证明|
|方法词|`"risk" "feature selection" "newsvendor" noninferiority`；`"minimum acceptable" "subset" "risk" model confidence set`；`"The Model Confidence Set" Hansen Lunde Nason pdf 2011`|定位按决策选输入、近优子集与集合推断；核对Serrano、Kowal和MCS|
|方法补充|`"Post-selection confidence bounds for prediction performance" authors`|新增Rink与Brannath近邻，核实固定模型条件性能、bootstrap tilting与maxT校正；与R2事后选择责任比较|
|反证词|`"risk-constrained" "feature selection" "nearly optimal" subset`；`"telemetry" "reserve" "minimum sufficient" wind`；`"minimal" "noninferiority" "model selection" confidence set`；`"wind" "information value" "current power" reserve quantile`|主动检索已有同类解答；非劣临床文献、通用网页等命中不作为风电最近邻证据|
|近期先行核验|`"Feature-based profitability evaluation for newsvendor-type products" 2026`及`site:sciencedirect.com`限定查询|接受出版社摘要／导论索引，核对2026期刊卷年与含2025的DOI不是冲突|
|领域简单基线核验|`"Short-term variations in wind power" "pdf" Pritchard Auckland`|本轮未取得可读作者全文；仅按出版社摘要限制比较，不照搬旧审查的全文细节为新核验|

检索同时复用既有13篇新颖性矩阵作为线索，但重新打开一手来源核对关键原理。既有审查不是替代原文的引文证据；旧矩阵和原审查均未修改。弃用的历史`literature/literature_matrix.csv`与合成brief未作为证据。

## 来源层级与访问限制

- Serrano：机构托管发表版PDF，核查§3.2双层目标及约束，不能将求解优化最优性等同统计认证最小性。
- Kowal：JMLR发表版PDF，核查§2.4式(18)–(20)、§2.5与讨论，不能将其默认后验概率接受门槛当作本项目的95%联合事件。
- MCS：期刊元数据与出版社摘要；方法阅读使用[Aarhus官方作者版2010-76](https://pure.au.dk/ws/files/34269366/rp10_76.pdf)，对应作者版§2–3及假设2，不伪称读取2011期刊每一页。
- LTT：Crossref核实期刊2025，正文阅读作者arXiv v5的§1.1、§2.1–2.4；不采用HTML动态显示的2026日期作为发表年。
- Rink与Brannath：Springer发表版HTML，重点§1.1–1.2、式(1)–(2)及方法相关段。预印本为2022，期刊发表为2025，不作两篇独立文献。
- Zhao：IEEE直接页面出现JavaScript／机器人验证；接受检索工具返回的IEEE出版社摘要及元数据，不使用第三方摘要替代。Crossref首取失败、后续小写DOI重试成功，两个记录均保留。
- Pritchard：Wiley直接打开有失败，出版社摘要可由检索返回；仅使用摘要明确的当前功率概率持续性及预测性质，不推断全文未做的内容。
- Zhang等：ScienceDirect直接访问403，使用检索工具返回的出版社摘要、高亮及导论。逐点置信区间来自出版社导论表述；未读全文，未断言其所有附加分析均不覆盖本项目。

7篇有DOI者均有Crossref记录；MCS的Crossref作者字段缺失，由出版社／作者机构记录补核。Kowal采用JMLR的23(108):1–38元数据，不补造DOI。

## 排除规则与停止规则

1. 一般SCADA点预测特征选择、Graph/MoE、故障检测不是两项结果的最接近方法，作为背景线索，不取代决策选择文献。
2. 未验证的二手下载站、自动生成研究网页、主题不符材料不用于结论。
3. 不强填`failing`角色，不声称先行算法已在当前任务失败。
4. 8篇已足以识别原理重合和关键不同推断对象；本轮到此给定位判断，不通过无限追加论文推迟交付。
5. 停止不代表检索穷尽。全球优先权、未读全文和相邻未检索术语仍UNKNOWN，不写“首次解决领域长期空白”。
