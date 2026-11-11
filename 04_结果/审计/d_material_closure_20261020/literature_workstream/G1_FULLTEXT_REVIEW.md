# G1 两篇最近先例的全文核查

日期：2026-10-20（Asia/Shanghai）。范围：公开论文与文献元数据；没有读取新运行数据、运行科研实验、联系作者或修改旧审计/论文。遵循 research-skill。本文是材料核查，不是新颖性全范围认证。

## 材料门决定

**G1_NOT_PASSED。** PMAPS 2024全文核验已完成，并能明确与D的差异；Next Energy 2026正文仍未合法取得，不能排除其方法/验证重合。按照本轮“继续或放弃、不再HOLD”的投资要求，G1不能为D提供继续立项依据，建议**本轮不继续投资D**。这是材料资格否决，不是认定D已被完整做过，也不是认定Next Energy没有经验校准。

## 1. Glista & Watson（PMAPS 2024）

- 题名：Electricity Grid Capacity Expansion Planning Considering Interconnection Queue Uncertainty。
- DOI：10.1109/PMAPS61648.2024.10667148。角色：mainstream。
- 来源：https://www.osti.gov/servlets/purl/2377899 。本轮通过标准Windows HTTPS请求取得官方作者稿；没有绕过登录或验证。
- 本地PDF：`glista_watson_pmaps2024.pdf`，988693 bytes，SHA256 `55a5ab61d1270c072d1f667feee9c39e19072f40751afb4e33817b0e440ff14d`。
- 全文8个PDF页，前2页为封面/免责声明。以下“正文页”=PDF页减2。8页全部提取并阅读，PDF第6页的公式7–8另外视觉核对。全文转录和页面图仅是本地阅读副本，不应加入交付正文或Git提交。

|核查项|直接证据与位置|与D的对应关系|
|---|---|---|
|结果对象|正文pp2–3（PDF4–5），§III：success为完成接入并最终commercial operation，failure为此前withdrawal/suspension|不是在固定H期限内完成的MW比例；也未联合估计既有机组退出|
|概率假设|正文p3（PDF5），Assumption 1：Bernoulli且参数已知；不随其他项目决策而更新|没有经验识别时间变化的项目间条件依赖；作者明确保留互补/替代可能性|
|经验拟合|正文pp4–5（PDF6–7），§IV-A、Eq9、Table I：California数据来自Queued Up end-2022；以1999–2017入队的终态项目按类型估计operational/(operational+suspended+withdrawn)，active排除|是单一终态数据层的类型频率，不是逐公开origin冻结的时间到事件预测校验|
|组合处理|正文p4（PDF6），§III-B、Assumption 2、Eqs7–8：同类型项目成功数用Binomial；以成功数的高分位b限制可投资项目数|不能解读为“至少交付b项目/容量”的下尾保证。Binomial是模型假设，不是经验依赖验证|
|决策候选|正文p5（PDF7），§IV-A：尚未把真实active项目映射进CATS；候选在既有相同类型bus上扩建，2022年末active数量用于计数约束|不是一份历史真实项目组合在未来的兑现验证|
|优化任务|正文pp2、4–5（PDF4、6–7）：投资+运行CEP；CATS、2045代表天气、RPS；transportation power-flow relaxation，忽略ramping/start-up/shutdown|是模型内规划结果，不是实际过渡期补购/退出安排的历史后悔|
|验证责任|正文pp4–6（PDF6–8），§IV–V：三种CEP模型的成本、投资、RPS及求解比较；参数敏感性留待进一步验证|全文没有报告跨历史origin的未来投运组合覆盖、概率校准或实际采购后悔；不能把代表天气场景当该类样本外验证|

**有界判断：**PMAPS已经占据“历史项目完成率进入规划”的贡献；D若能完成真实origin、期限内MW组合下尾及独立行动接口，责任确有差别。但这个差别需要D自身材料支撑，不能由先例未做自动推出重要性。

## 2. Al Hasibi et al.（Next Energy 2026）

- 题名：Mitigating firm-capacity delay risk through stochastic planning of flexible generation and battery storage。
- 作者：Rahmat Adiprasetya Al Hasibi；Eko Hariyostanto；Zahid Ahmad Faiz。
- DOI：10.1016/j.nxener.2026.100888；PII S2949821X26003789；角色：adjacent。
- 出版社入口：https://www.sciencedirect.com/science/article/pii/S2949821X26003789 。题录/摘要与Crossref核验一致；出版社标为Open Access，Crossref记录CC-BY 4.0许可。
- 仅摘要层可核：Jawa–Bali 2025–2034的firm-capacity delay mitigation、灵活机组和储能等投资/运行。**不凭这些摘要用语推断其情景是任意设定，更不据此断言没有历史验证。**

### 本轮合法访问与阻断

|路径|结果|可得证据|
|---|---|---|
|出版社原始article入口，web工具|403 Forbidden|没有正文|
|同一入口，标准Invoke-WebRequest|403 Forbidden|没有正文；未绕过验证|
|Crossref公开works元数据|成功|作者、DOI、许可和两个出版社TDM全文链接|
|Crossref所列Elsevier text/xml链接，无凭据标准请求|429 Too Many Requests|没有正文；未继续高频重试、未尝试绕过限制|
|OpenAlex W7202258952公开元数据|成功|仅列出版社location，pdf_url为空，has_fulltext=false，any_repository_has_fulltext=false；不证明其他仓储绝不存在|
|精确题名/DOI/作者与UMY机构仓储定向检索|未找到独立公开作者稿或完整正文|搜索负结果仅限已查范围；不把摘要转录站当全文|

前轮已记录出版社验证页面和API FULL=401。本轮不把先前状态冒充本次结果，也没有尝试登录、使用机构凭据或联系作者。

### 不能排除的重合

以下均为UNKNOWN：概率与情景的校准来源；是否使用历史版本/起点冻结；项目cohort和取消/迟报处理；新增与退出的相关性；独立未来验证；是否存在真实采购/退役接口及决策后悔。没有正文就不能逐项把它们判为“不存在”。

## 3. 对D当前题面的限制

1. PMAPS差异明确，但不足以通过要求“两篇完整方法比较”的G1。
2. Next Energy取得困难是信息不足，不是科学反证。当前投资不继续，是因为必须排除的最近重合尚未排除，而非声称这篇论文否定了D。
3. 即使以后取得正文，G2真实公开版本和G3真实行动接口仍须独立通过；本核查不授权采集项目表、实验或自动恢复D。

## 研究状态卡

- 当前结论：G1本轮关闭为NOT_PASSED；不支持D立项。
- 证据：官方PMAPS全文与哈希/页码；Next Energy出版社、Crossref、OpenAlex及访问状态。
- 未解决：Next Energy完整方法/验证；D自身的版本身份和决策材料另由其他工作流核查。
- 下一步：交主智能体合并三个门，作继续/放弃决定；不创建实验或联系作者队列。
- Kill条件：本轮必须排除的近邻责任仍不可审查；不以摘要差异填补。
