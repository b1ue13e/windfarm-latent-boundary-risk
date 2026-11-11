# Reviewer N：风电领域反向先行工作审查

审计日：2026-10-19。对象严格为08_claim_inventory.md冻结的C1–C8；没有重定义任务、q、资源或比较对象。只读项目，不用旧矩阵/伪造brief，不读取本轮其他reviewer输出。采用research-skill的反证检索流程。

## 结论与判级尺度

VERIFIED：当前功率驱动的短期条件分位数、在现有点预测之外估计误差分位数、执行时信息约束、缺失输入的直接决策损失评估，均有风电先行工作。尚未核实一篇文献完整覆盖“固定共同预测+增量遥测资源字典序+事前选定q.95独立年确认+另列q.925有限族严格更小者排除”。因此不得宣布整个项目被直接做过，也不能以精确组合未搜到为C8创新证明。

- DIRECT：同一原子贡献的实质内容已被直接覆盖；本轮未给出任何“全项目DIRECT”。
- STRONG：正文定位直接支持关键概念/接口的强覆盖；不代表相同数据、全部协议或相同经验结果。
- ADJACENT：邻域启发或相关问题，核心目标不同。
- CANDIDATE：只有摘要/目录，未取得足够正文；绝不据此作STRONG/DIRECT判决。

fetch_level区分全文文件取得、实际阅读范围与最终发表版。未取得全文并不等于未存在重叠。

## 威胁最高的正文对照

|工作、primary来源|确切正文定位及核实内容|冻结Claim重叠|级别、重要差异及限制|
|---|---|---|---|
|Geoffrey Pritchard (2011), Short-term variations in wind power: Some quantile-type models for probabilistic forecasting, Wind Energy14:255–269, DOI10.1002/we.416；[出版社](https://onlinelibrary.wiley.com/doi/10.1002/we.416)|§3、HTML行117–155：只以当前功率建分位数样条，留一日历年验证；§4、行185–190：额外输入与当前功率交互，使效应随功率工况变化；§4.3、行236–248：功率变化量作为不确定性预测输入。|C2、C3、C6、C8的概念层|STRONG概念覆盖：当前功率有信息、直接条件分位数、跨年评估均已有。没有核实其进行备用层非劣、资源最小性排除；不能覆盖C1/C4实质协议。只读到§4.3及§4.4标题；后半页抓取超时、PDF403，因此不是完整全文核验。PDF页码未取得；章节+HTML行定位可复查。|
|Yuchi Sun et al. (2022), Machine learning derived dynamic operating reserve requirements in high-renewable power systems, JRSE14:036303, DOI10.1063/5.0087144；[作者机构全文](https://www.ethree.com/wp-content/uploads/2023/03/Machine-learning-derived-dynamic-operating-reserve-requirements-in-high-renewable-power-systems.pdf)|PDF2/印刷-1 §I：不改进点预测，估计其误差；PDF3/-2 §II末：遵守实时可用数据与既有误差定义；PDF4/-3 §III、Fig1：T0可用输入、34数据点、pinball MLP；PDF9–10 §VI及PDF15–16 AppA2–3：成本/高价事件代理、coverage/exceedance。|C1、C2、C7、C8的接口/评价层|STRONG概念覆盖：共同现成预测+后续误差分位数备用层已有。其对象是CAISO净负荷，目标含15分钟与5分钟预测差，非本项目机组未来实际短缺；10折而非封存独立年。未见增量遥测最小集合、字典序及严格更小者排除。故不能称C1或C4已被完整复现。|
|Honglin Wen (2024), Probabilistic wind power forecasting resilient to missing values: An adaptive quantile regression approach, Energy300:131544, DOI10.1016/j.energy.2024.131544；[作者v3全文](https://arxiv.org/pdf/2305.14662v3)，[出版社](https://www.sciencedirect.com/science/article/pii/S0360544224013173)|v3 PDF9–13 §§3–4：按缺失模式条件分位数、掩码适应特征提取及non-crossing MLP；PDF13–16 §5、PDF17–20 §6：历史功率6lags、时间切分、模拟缺失与CRPS/reliability/sharpness；PDF20–22 §7及AppA配置。|C2、C6、C8相关问题/方法|STRONG限于“剩余观测可直接支持概率预测”；没有备用损失、预设风险/成本非劣或资源最小性结论。不能拿CRPS优胜推翻本项目C1，亦不能把缺失鲁棒预测当成其未做过的决策充分性。v3是作者Energy修订稿，不冒称出版社最终PDF逐字一致。|
|Miguel Á. Muñoz, Juan M. Morales, Salvador Pineda (2020), Feature-Driven Improvement of Renewable Energy Forecasting and Trading, TPWRS35(5):3753–3763, DOI10.1109/TPWRS.2020.2975246；[作者全文](https://arxiv.org/pdf/1907.07580)，[作者机构元数据](https://portaldelainvestigacion.uma.es/documentos/63df0adc6fdec82c4e7dff43)|作者PDF4–5 §II-B、Eq26–30：较丰富直接决策规则可能过拟合，改为仅输入改进后forecast的低自由度bid校正；PDF6 §III-A：共同上游WindFor预测及信息时序限制；PDF7 §III-C：标签未成熟的gap；PDF8 §IV-A：更多输入不必改善，选较简单模型。|C2、C5、C6、C8的两层接口/负结果|STRONG概念先行：预测层消费较多信息、下游简单决策及未获增益已有。其上游主动改进、rolling refit、test-informed simplicity选择和市场bid不同于本项目历史冻结选择；无固定短缺目标和UCB最小性证书。公开数据迟报/缺timestamp限制被作者明说，不能升级为严格到达时钟认证。|
|Akylas Stratigakos et al. (2024), Towards Resilient Energy Forecasting: A Robust Optimization Approach, TSG15(1):874–885, DOI10.1109/TSG.2023.3272379；[作者机构全文](https://backend.orbit.dtu.dk/ws/portalfiles/portal/320707182/BERAT_Towards_Resilient_Energy_Forecasting_A_Robust_Optimization_Approach.pdf)|接受稿PDF3–7/正文2–6 §§II–III：feature-deletion robust regression、Γ预算与LP；PDF8–9/正文7–8 §IV：QR/QRF、RETRAIN、缺失分组，wind数据及不能删除的calendar项。|C2、C8相关问题/约束|ADJACENT：Γ是缺失鲁棒预算，不是找到满足非劣界的最小新增遥测；预测目标不同。实际13页含机构封面，核读方法/设置，未逐项审计全部结果。|
|Matias Kühnau et al. (2023), Resilient Feature-driven Trading of Renewable Energy with Missing Data, ISGT Europe, DOI10.1109/ISGTEUROPE56780.2023.10408186；[作者机构全文](https://discovery.ucl.ac.uk/id/eprint/10212754/1/FeatDriven_Trading_with_Missing_Data%20%281%29.pdf)|5页全文：p2 §II Eq1–5 newsvendor与可用features；p3 §III Eq6–9缺失组鲁棒决策；p4–5 §IV、TablesI–II缺失输入下实际imbalance cost；p5 References[8]引Stratigakos。|C6、C7、C8相关问题|STRONG概念覆盖“缺失输入→下游损失评估”；不是forecast后独立备用接口或最小性识别。其输入格不作本项目实测节省证据。|
|Dariush Wahdany, Carlo Schmitt, Jochen L. Cremer (2023), More than accuracy: end-to-end wind power forecasting that optimises the energy system, EPSR221:109384, DOI10.1016/j.epsr.2023.109384；[最终版机构全文](https://pure.tudelft.nl/ws/portalfiles/portal/150812483/1_s2.0_S0378779623002730_main.pdf)|PDF3/文章p2 §1、Fig1：预测目标与系统目标可能不匹配；PDF11/文章p10 §4.4、Table3，PDF12/p11 §4.6：成本与curtailment不同目标、效果非普遍更好。|C6、C8的洞见层|STRONG限于accuracy≠value及效应边界；无状态恢复/固定预测遥测最小性。不能据此认定本项目具体C6负结果早已测过。|

## 核心指定但全文未获的风险

Zhao/Wan/Song2021，Operating Reserve Quantification Using Prediction Intervals of Wind Power: An Integrated Probabilistic Forecasting and Decision Methodology，TPWRS36(4):3701–3714，DOI10.1109/TPWRS.2021.3053847。[IEEE原始记录](https://ieeexplore.ieee.org/abstract/document/9334448)核实其题名、作者、日期、摘要及§II–IV目录。摘要包含reserve provision payment、deficit penalty、coverage约束、joint confidence/quantile tuning。其与C1/C4/C8相邻程度高，但本轮IEEE HTML/PDF下载418；没有正文公式/实验/附录可读，故标CANDIDATE，不作正文STRONG，不能声称其证明了信息约简或完整先行。Sun2022是其真实forward citation，不是替代Zhao原文。

Nielsen/Madsen/Nielsen2006，Using quantile regression to extend an existing wind power forecasting system with probabilistic forecasts，Wind Energy9:95–108，DOI10.1002/we.180。[DTU元数据](https://orbit.dtu.dk/en/publications/using-quantile-regression-to-extend-an-existing-wind-power-foreca/)、[出版社](https://onlinelibrary.wiley.com/doi/10.1002/we.180)只提供摘要及参考文献。摘要明确现有forecast系统的误差条件分位数，支持必须对照此经典，但缺正文，仅CANDIDATE概念线索。Pritchard References[4]实际引它，backward边成立。

## 七类反向检索覆盖

|类别|实际找到的最接近证据|对冻结主张的判决|
|---|---|---|
|same problem|Sun2022 §I/III；Zhao2021仅摘要|固定预测后备用误差层并非新问题；资源最小族问题完整先行UNKNOWN。|
|same phenomenon|Pritchard2011 §3；Muñoz2020 §IV-A；Rutyna2025 §§4/6|少输入可保留性能已有；C1的具体预设2%+风险界独立年结果仍是新的本地实证。|
|same mechanism|Pritchard2011 §4：功率工况交互|当前功率携带工况相关条件风险不新；未测得本项目隐状态必要性，也不倒推C6。|
|same method|Wen2024 §§3–4；Sun2022 §III/AppA；Muñoz2020 §II|直接pinball/条件分位数与简单下游策略已有。NC1–NC3本就不主张方法首创；不攻击不存在的声称。|
|same insight|Muñoz2020 §II-B/IV-A；Wahdany2023 §1/4.4|更多输入、预测提升与经济提升不等同已有；C5的具体分离可以是教学性实例，但不是新选择理论。|
|adjacent framing|Stratigakos2024；Kühnau2023；Bouche2023；Rutyna2025|缺失鲁棒、变量/lag选择、市场损失相邻，不能宣称全任务覆盖。|
|negative/null|Muñoz2020 §II-B负结论、Wahdany2023 §4.6；Pritchard摘要的resolution/sharpness分离|复杂模型/更多输入未必增益不是新普遍洞见；本项目具体有界负结果仍需保留。|

近五年实际覆盖：2021 Zhao、2022 Sun、2023 Bouche/Kühnau/Wahdany、2024 Wen/Stratigakos、2025 Rutyna；2026检索查到候选但未以低深度2026文献主张完整覆盖。经典覆盖2006与2011，另有Muñoz2020主文（不混同另一篇2023 online-trading工作）。Rutyna2025（DOI10.3390/wind5040028）和Bouche2023（DOI10.1016/j.renene.2023.05.005）只作变量约简邻域，非C1/C4先行；原始来源及fetch_level见CSV。

## 逐Claim剩余内容

|Claim|删去已知思想后的残余判断|
|---|---|
|C1|数值与冻结独立确认可以保留；先行检索不否定此结果，但其科学意外性有限：当前P条件风险有强经典基础。|
|C2|限定备用接口的input reduction有本地证据；“少单变量足够”概念已强覆盖，且不能转成端到端单传感器/实测成本节约。|
|C3|仍UNKNOWN。一次独立年增加可靠性，不能被写成稳定跨期规律的新发现；Pritchard已做跨年可靠性讨论。|
|C4|本轮未找到风电完全相同的有限族排除证据；这不证明方法首创。225族、资源字典序及q.925决定证书的范围。|
|C5|分离责任是正确且有用的报告，但答案不同在逻辑上受不同目标/候选族驱动；应说明哪一项新经验改变了判断。|
|C6|特定反证有应用价值，普遍洞见已先行；“状态恢复无额外稳定决策增益”的本地实验不能升级到所有状态。|
|C7|UNPROVEN保持。文献没有替本项目测量真实传输/维护/延迟与成本溢价。|
|C8|目前可支持“严谨的限定接口应用证据+诚实的有限族识别边界”；可竞争的发现创新仍不足以由文献未检出直接确认。|

## 审计边界

没有训练、推理、重采样或远端；未改原结果/稿件/门槛。全文取得与选择性深读记录不等于系统综述穷尽。保存的PDF为作者/机构primary来源，元数据经Crossref记录；没有用聚合站摘要推导内容评价。下载失败、版本差异与真实引文方向见SEARCH_LOG.md。
