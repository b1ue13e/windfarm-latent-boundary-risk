# 当前功率之后的状态信息：最近邻文献与可成立问题

日期：2026-10-20。状态：LITERATURE / AUDIT；不是科学里程碑认证、选题通过或实验启动。已读 AGENTS、research-skill、PROJECT、科学契约，以及 `analyses/decision_information_execution_20261018/REPORT.md` 和 `research_audit/14_resource_loss_break_even_review.md`。本次只读文件、公开论文和元数据；未下载运行测量、未实验、未改论文/契约/旧结果。

## 1. 结论先行

**可保留为需要严判的具体问题：在当前有功及既有历史/共同预测已经到达后，新增控制状态线索是否在有用提前量内预示未来短缺，并使同一非对称损失下的备用动作发生有价值的改变；哪些情况下它只是已知后果的重编码？**

当前文献不支持把“预测准确不等于决策价值”“工况决定不确定性”“当前功率是强基线”“按决策成本选择输入”作为新知识。这些均有强先例。上述窄问题有可审查的差异，但**尚不能认证为独占空白或顶刊主线**。实际差异必须是可迁移的提前信息边界，而非另一个模型优劣、当前P有效的再次展示，或给旧非劣结果换标题。

不保留“状态信息主要影响稀有短缺严重度而非违反频率”为预期机制。它既未由项目当前对照识别，也容易把损失定义或分位数校准的已知性质当作新发现。

## 2. 五篇必须面对的最近邻

### L01 — 状态与预测不确定性的直接先例

Ege Kandemir, Trond Kvamsdal, Agus Hasan, Saleh Abdel-Afou Alaliyat. **Explainable uncertainty quantification in probabilistic wind power forecasting.** *Machine Learning with Applications* **25** (September 2026), 100957. DOI [10.1016/j.mlwa.2026.100957](https://doi.org/10.1016/j.mlwa.2026.100957)。作者顺序另由 [NTNU 作者官方主页](https://www.ntnu.edu/employees/ege.kandemir)核验。

- **阅读层级：PRIMARY_BODY_PARTIAL。** 出版社公开索引返回并已读 §1、§2.1、§2.2 部分、§2.3、§3.1/3.2 和 §4；直接 DOI/ScienceDirect 打开失败，没有取得可逐页核对的完整PDF，不称全文完全覆盖。
- **已经解决：** 将运行功率曲线、异方差/分位数预测与局部特征扰动结合，解释不同功率区间的预测不确定性。其独立扰动范围为 ±5%；所读结果中 blade angle 等变量贡献较小，主图未保留。讨论已联系 torque-to-pitch 区间与备用调度。
- **可成立的差异：** 检验额外状态信息在完整后果基线之上的配对动作/损失增量；区分可解释敏感性、提前信息和可实现决策价值。
- **不能这样写：** “首次发现状态依赖不确定性”或“别人只预测均值”。所读部分没有展示本项目式配对备用试验，但全文覆盖不完整，不能据此断言该文绝无相关附加分析。其经济含义讨论也不能替本项目提供实测市场收益。

### L02 — 工况、校准与短缺代理的最接近新论文

Yang Wang, Haiyun Wang. **Reserve-risk-oriented regime-calibrated interval forecasting for wind power integration under extreme fluctuations.** *Sustainable Energy Technologies and Assessments* **94** (October 2026), 105438. DOI [10.1016/j.seta.2026.105438](https://doi.org/10.1016/j.seta.2026.105438)；[出版社记录](https://www.sciencedirect.com/science/article/pii/S2213138826006247)。

- **阅读层级：PUBLISHER_PREVIEW。** 已读摘要、完整可得引言/贡献和方法/数据/讨论章节预览。未找到作者公开全文；出版社和Crossref所指公开API入口均未取得正文，没有登录或绕过限制。
- **日期严格区分：** [Crossref元数据](https://api.crossref.org/works/10.1016%2Fj.seta.2026.105438)给出刊期2026年10月，`published-online`为空，`created=2026-09-27T11:53:31Z`只是记录创建日期。**准确online发表日UNKNOWN**，不得把created或抓取日期当发表日。
- **已经解决：** 将 ramp-up/down、高波动、低/高出力工况用于分位数学习和 horizon/regime 校准，样本少时向统一校准收缩；报告外场检验。引言明确其 downside-boundary violation 是备用相关风险代理，非直接系统运行成本。
- **可成立的差异：** 原生控制状态是否在已知出力后果之后仍有提前量，以及同一冻结承诺下的配对备用动作/损失；不是再做工况校准。
- **UNKNOWN：** 其工况定义、完整时间索引、全部基线和损失分析尚未全文核实。不能凭“预览没看到”宣称它未做相似检验，也不能把该文当作已证失败的 `failing` 文献。

### L03 — 缺失遥测下直接分位数的强先例

Honglin Wen. **Probabilistic wind power forecasting resilient to missing values: An adaptive quantile regression approach.** *Energy* **300** (1 August 2024), 131544. DOI [10.1016/j.energy.2024.131544](https://doi.org/10.1016/j.energy.2024.131544)；[作者稿 v3 正文](https://arxiv.org/html/2305.14662v3)。

- **阅读层级：FULL_TEXT_AVAILABLE / MAIN_BODY_AND_APPENDIX_READ。** 本次读v2/v3正文的定义、方法、实验、结果、讨论、结论及实现附录；最终发表版与作者稿不是逐字节比对。
- **已经解决：** 针对缺失模式设计自适应分位数模型，直接利用剩余观测，避免强制插补。验证覆盖模拟随机、块状和自掩码缺失；指标为校准、区间宽度、CRPS。正文把缺失重建与最终预测目标分开。
- **可成立的差异：** 连续pitch或控制线索在完整后果条件下的提前预警与配对备用价值。缺失鲁棒性本身不能充当本项目新意；重新预测pitch也不是必经步骤。
- **边界：** 作者实验主要使用滞后功率，不能拿它证明本项目某个控制状态无用；更不能从该文合成缺失实验推出本项目存在真实现场延迟率。

### L04 — 当前功率强基线的奠基先例

Geoffrey Pritchard. **Short-term variations in wind power: Some quantile-type models for probabilistic forecasting.** *Wind Energy* **14**(2) (2011), 255–269. DOI [10.1002/we.416](https://onlinelibrary.wiley.com/doi/10.1002/we.416)。

- **阅读层级：PRIOR_PRIMARY_BODY_PARTIAL。** 本轮重新读取旧registry及审计记录；此前直接核过出版社§§3、4–4.3，包含当前功率条件分位数及扩展输入。此次直接访问超时，未重新取得完整原文。采用较窄的§4.3边界，不沿用早期概述中“§§2–5”较宽读法。
- **已经解决：** 仅当前功率的概率持续性、额外输入与分位数建模；已有年度验证/相关性讨论记录。
- **可成立的差异：** 不是证明当前P有用，而是额外状态线索在更完整当前后果信息下是否提供决策相关提前信息。
- **不能这样写：** “近期才提出当前功率对照”“首次低维输入支撑概率预测”“复杂输入一般无用”。旧部分正文不足以判定其所有尾部/决策附加分析均不存在。

### L05 — 按非对称决策损失选择输入的直接方法先例

Breno Serrano, Stefan Minner, Maximilian Schiffer, Thibaut Vidal. **Bilevel optimization for feature selection in the data-driven newsvendor problem.** *European Journal of Operational Research* **315**(2) (2024), 703–714. DOI [10.1016/j.ejor.2024.01.025](https://doi.org/10.1016/j.ejor.2024.01.025)；[机构托管发表版PDF](https://publications.polymtl.ca/57338/1/2024_Serrano_Bilevel_optimization_feature_selection_data.pdf)。发表版首页明确online为2024-01-24。

- **阅读层级：FULL_TEXT_AVAILABLE / TARGETED_BODY_READ。** 12页发表版可访问；本轮核首页、§1–2、§3.2–3.3的目标式和约束；结合此前§4实验阅读记录。没有把章节抽查写成逐页通读。
- **已经解决：** 以留出样本的订货成本选择特征，训练层只使用入选输入；把选择与估计结合为双层问题。非对称成本而非中间预测精度决定特征价值，不是新原则。
- **可成立的差异：** 风电原生状态相对当前输出的领先/滞后信息边界及其决策后果。若只剩逐通道删减+比较pinball/备用成本，它已构成方法先行。

这五篇覆盖领域强基线、缺失输入、状态不确定性、工况风险与决策选输入；没有强行安排 `failing` 条目。文献角色见CSV。

补充背景L06由根代理核验，不作第六个近邻扩展检索：Haipeng Zhang, Ran Li, Qintao Du, Junyi Tao, Salvador Pineda, Georges Kariniotakis, Simon Camal, Claire Bizon Monroc, Mingyang Sun, Can Wan, Wangkun Xu, Fei Teng，**Decision-Focused Learning for Power System Decision-Making Under Uncertainty**，*IEEE Transactions on Power Systems* **41**(1)，307–323，January 2026，DOI [10.1109/TPWRS.2025.3597806](https://doi.org/10.1109/TPWRS.2025.3597806)。IEEE页记录首次发表2025-08-11；正式期刊第一作者为Haipeng Zhang，不得套用 [arXiv:2401.03680v2](https://arxiv.org/abs/2401.03680v2)前身稿的第一作者/版本。本轮层级为根代理核过官方摘要/引言及作者前身稿，未称正式发表全文完整阅读。它进一步排除“把预测和决策连接起来就是新贡献”的宽题。

## 3. 两个必须分开的估计对象

设 I_t 包含共同冻结预测、已到达当前P、允许的W/P/Q历史、时间/机组标识及其他登记输入；Z_t 是在决策前真正额外到达的状态测量。Y是共同短缺目标，r是备用动作。

**新增测量问题：** 比较使用 I_t 与使用 (I_t,Z_t) 的策略。在目标、可行动集合和损失固定后，检验额外状态的可实现损失差及提前量。这个比较能回答增量预测价值，不自动证明改变物理控制状态的因果效应。

**重编码问题：** 若 g_t=g(I_t) 是由同一信息算出的pitch预测/状态分数，且训练信息也同等可用，则 σ(I_t,g_t)=σ(I_t)。它不增加部署时的Bayes信息。有限模型可能因表示、监督或训练差异受益；该收益应叫表示/估计程序收益。不能把 C−B 直接称新增信息价值，也不能由 C−B不显著证明状态本身无用。

“尚未反映在当前P”必须是issue时信息条件下的问题。固定当前P但遗漏其历史斜率、共同预测或W，会把已有后果线索误写成状态提前信息；按未来下行/未来大损失选择样本，再声称在线预警，是另一种对象偷换。

## 4. 什么才算实质差异，什么不能算

**有潜力但未验证的差异：** 给出控制线索相对当前后果信息的条件性领先区间，并证明领先区间内的预测分布变化恰好进入某个明确非对称决策的有效动作区域；在其他区间只改善状态识别或重新解释已有后果。它要能区分先兆、已发生后果和模型容量效应，且允许所有增量为零的结果。

这里的关键不是漂亮的状态分类，而是三项对象必须对应：

1. **先兆证据：** Z_t在相同I_t条件下改善未来短缺的适当预测量；不能只预测当前pitch本身。
2. **动作证据：** 相同承诺和动作约束下，利用Z_t改变了动作；只改变远端尾部却不改变有效分位数/可行动作，不能叫适应信息的决策收益。
3. **价值证据：** 变化在配对损失中成立，且没有用更高采购量换取较少违约后声称全面支配。采购、频率、未覆盖幅度是解释性账目，不是新理论本身。

不可作为创新：当前P有预测性；状态相关异方差；均方误差不等于运营成本；分位数对应非对称损失；特征选择应该按决策目标；g(I)不创造信息；平均未覆盖短缺等于发生概率乘条件平均幅度；模型非劣/有限族最小性的原理。科学新增只能来自这些已知原则下，经证据建立的特定风电提前信息边界。

**本项目还有更强的等价性限制。** 对冻结短缺目标Y、备用r，未乘时间因子前的损失满足 `r+10(Y−r)_+ = Y+10ρ_0.9(Y−r)`。同一Y总体上，比较对应动作的q=0.9 pinball与比较该损失是同一排序；若都乘共同的1/6时间因子，等价性仍在。不能把“这个正确目标的分位数损失改善却未改善备用成本”写成新矛盾。真正不同的中间任务可以是pitch测量MSE、状态分类或其他分位数/全分布评分；这些与备用损失的不同不是新理论。动作cap、约束或风险门改变可行问题时，需要显式列出，不能借此模糊原恒等式。

## 5. 与现有证据的衔接及不能跨越的结论

- `decision_information_execution_20261018/REPORT.md`：B相对A成本下降而违反频率上升，证明本开发流程存在成本—频率不同向；不是状态机制。C相对B变化小且语义控制区间跨零，只支持目前尚未隔离状态语义的稳定特殊收益；不能写为严格零价值或等效。
- 同报告的pitch测量预测MSE下降，目标是pitch测量本身，不是未来shortfall。因此“恢复好但决策小”是研究线索，不是已经识别的物理中介。
- `14_resource_loss_break_even_review.md` 的P1对WPQ36同时移除其他通道及历史。该比较可说明某两策略的频率与幅度结果不同，不能识别pitch状态信息只影响严重度；也没有真实服务边际价值。
- 现有数据已查看，候选问题是结果知情形成。对旧资料的重新解释仍应为探索性，不把2025再命名为新的独立验证。

## 6. 本轮决策与边界

**继续的是问题层面的对照审查，不是恢复模型/算力投入。** 该问题比“信息最小化值得部署”更接近可检验的风电知识，但当前没有证据可宣布其正向结论或顶刊资格。

若新增状态测量没有独立到达语义、所谓领先仅由漏掉功率历史/上游预测导致，或只能展示同信息g(I)的学习便利，则主张必须降为表示分析，不能保留“提前物理状态信息”主线。若最后仅是再现已知频率—严重度恒等式、增加几个条件分组或更换分位数学习器，也不足以支持本轮新科学问题。

本文不启动实验，也没有提供预期结果。SETA全文与准确online日期未核实即按UNKNOWN保留；没有为完美排重继续无限检索。
