# 需求灵活性数据路线资格审查

日期：2026-10-20。阶段：文献与公开元数据审查，不是实验结果或新主线科学认证。

执行边界：遵循 AGENTS.md、SCIENTIFIC_CONTRACT.md、PROJECT.md 的停止边界及 research-skill。未获取任何测量数据、ZIP、Parquet 或 API 会话记录；未执行实验、推理、优化求解；未修改论文、旧版本或原始结果。以下只记录公开说明及论文内容。字段存在不等于覆盖率通过。

## 投资意见

**当前不把本支提名为已经闭合的顶刊新主线。保留 ACN 和 KIT 为合格数据资产，不把未发现足够新问题写成数据不可用。**

三条已筛对象：ACN 的声明服务承诺；真实热泵干预；KIT 的充电执行响应。均有具体可用证据，但当前最直观的问题分别与早退/随机控制、温度退出/恢复负荷、暂停失败/动态执行误差的直接先例重合。换预测器、重新计算折减率、叠加网络约束或把几种已知风险合并，不足以构成顶刊知识增量。

最有价值而尚未通过的候选问题是：**同样通过单次阶跃/暂停检验的设备，是否仍因指令序列和执行历史而不能保证声明的持续调节服务；什么测试足以区分这两种资格？** 它要求改变资格测试而不仅是改善拟合误差。然而当前元数据未证明足够的重复序列、同车型多实体/固件重复或独立序列验证；且原 KIT 论文已经处理动态模型。不能把这个问题升格为已推荐主线，更不能推成真实车队共同失效结论。

## 数据资格与可识别对象

| 数据 | VERIFIED：公开资格与关键字段 | 能识别的对象 | UNKNOWN / 主张上限 |
|---|---|---|---|
| [ACN-Data 官方说明](https://ev.caltech.edu/dataset.html) | 公开 API 需注册；`connectionTime`, `disconnectTime`, `doneChargingTime`, `kWhDelivered`, `pilotSignal`, `chargingCurrent`；`userInputs` 可有多次修改，含 `modifiedAt`, `kWhRequested`, `requestedDeparture`；UTC 时间并有站点时区 | 以决策时已提交请求为服务对象的模型内回放；历史实际电流与下达 pilot 的差别 | 未查会话内容，不能声明请求覆盖率；不代表真实出行需要；事后 unplug 只能作标签，不能作预知输入；历史不同调度下的响应不能自动识别新策略因果效果；未闭合完整控制器版本史 |
| [Rigaux 等作者仓库](https://github.com/RigauxBaptiste/The_Proof_of_the_Pudding_is_in_the_Heating) 与 [作者接受稿](https://wps-feb.ugent.be/Papers/wp_24_1101_REV.pdf) | 公开实验文件与代码目录；论文为九户、287 次热泵干预，测量功率、温度并存在停止/覆盖机制；本轮不读取数据包 | 该样本及协议下的控制响应、退出与恢复负荷 | 不是 287 个独立家庭；本轮未证明随机分配，不能称 RCT；小样本总体外推有限；作者已分析舒适约束、天气与恢复负荷 |
| [KIT Zenodo 17866847](https://zenodo.org/records/17866847) / [KIT 官方镜像元数据](https://publikationen.bibliothek.kit.edu/1000190660) | 数据 CC BY 4.0；18 个测量数据集、16 辆车、12 厂商，2025-10-28 至 2025-12-02。`charging_uuid` 联结车型/日期；LF 含 `timestamp_ns`, `setpoint_a`, 三相 U/I/P/Q/S、SoC；HF 含 U/I/setpoint 与 ns 时间。伴随摘要称 LF 50 Hz、HF 5 kHz | 已实施电流指令后的电气响应及该试验支持域内的动态特征 | 不能把 16 辆车等同随机代表车队；同车型实体/固件重复、同步时钟误差、试验序列覆盖、实际公开缺失与有效测量比例未核；不能由单车顺序试验估真实车队共因尾部风险 |
| [2026 JEEM EV tariff RCT](https://www.sciencedirect.com/science/article/pii/S0095069626000744) | 原文明确随机试验，600 余户，静态容量费/分时费/控制组 | 已分配干预的群体效应 | 数据为 reasonable request，不是已核准公开立即可用；已报告分时转移引发新峰，不能重复包装；本轮未联系作者 |

ACN 时间处理必须保留输入版本：每个决策只使用 `modifiedAt <= t` 的最近合法声明。以 `kWhDelivered` 筛选高能量会话是按结果筛样；默认请求与用户主动声明必须分开。官方警告 2019-10-10 之前网页导出曾有 7–8 小时时区偏移，不能直接复用来源不明的旧导出。原始 API 的存在不替代本地数据资格验证。

KIT 文件元数据：`ev-charging_lf.parquet` 422.5 MB，md5 `0327dae2664c79ecde0bd07166bf6b1d`；`ev-charging_hf.parquet` 22.4 GB，md5 `dc692e948cb53e0362553be6a64a972a`。只读目录，未下载或校验实际字节。发布版本 1.0.0，2026-02-09 创建，2026-02-19 修改。

## 最近直接先例与真正差异

阅读等级：FULL = 已读方法、结果与限制；PARTIAL = 官方摘要/部分正文，不能声称方法全审。这里不把 PARTIAL 的内容用于证明一个未读方法不存在。

| 文献及角色 | 阅读等级与已做内容 | 对候选的约束 / 剩余差异 |
|---|---|---|
| Lee, Li & Low, ACN-Data, e-Energy 2019；foundational；[原文](https://ev.caltech.edu/assets/pub/ACN_Data_Analysis_and_Applications.pdf) | FULL。用户请求与非认领默认会话有别，站点存在费用/默认规则变化 | 合法目标是声明服务，不是未经测量的真实需求；不能把全体会话都称有独立需求标签 |
| Puech et al. 2024, [arXiv:2402.13224v1](https://arxiv.org/html/2402.13224v1)；mainstream | FULL。II-A/B 定义请求与结束；IV 建模早退及随机控制；V-A1 使用 ACN，并把无法满足的原请求下调至声明停留时间内可充量 | 早退、声明 deadline、供电上限与费用/服务权衡已经是核心。保留未经下调的请求并报告不可行性是有价值审计，但本身尚不足顶刊新主线 |
| Li & Li, 2024, Distributionally Robust Evaluation for Real-Time Flexibility of EVs；mainstream；[arXiv:2311.11513](https://arxiv.org/abs/2311.11513)，DOI 10.1109/TSG.2024.3397057 | FULL 预印本。早退与 SoC 不确定性进入实时灵活性评价，数值实验有模拟假设 | 不能说现有文献都把声明离开时间当真。模拟边界可批评，但不会自动使同题真实数据回放成为新的系统知识 |
| Brinkel et al., Nature Communications 15,5089 (2024)；failing；[全文](https://www.nature.com/articles/s41467-024-48477-w)，DOI 10.1038/s41467-024-48477-w | FULL。52 车型技术检验；波动、间歇、长短暂停；方法区分实际技术检验与322站历史数据上的模型模拟；讨论早退未纳入的边界 | 暂停不能恢复、最低电流、技术限制改变费用/拥塞/备用价值与资格政策都已经提出。重新发现“实际 EV 不是理想电池”不成立为新贡献 |
| Rigaux, Hamels & Ovaere, Energy Economics148,108565 (2025)；mainstream；[接受稿](https://wps-feb.ugent.be/Papers/wp_24_1101_REV.pdf)，DOI 10.1016/j.eneco.2025.108565 | FULL 早先获取的作者 PDF 正文。舒适停止、手动退出、冷天气、恢复负荷和经济价值已分析 | 不能把热泵服务债、恢复原则或冷天可靠性作为本次新认识；九户数据不能支持广泛资格制度重构 |
| Beichter et al., Open-source data set for characterizing the charging behavior of EVs (2026)；mainstream；[SSRN](https://ssrn.com/abstract=6265089)，DOI 10.2139/ssrn.6265089 | PARTIAL。官方摘要明确已有延迟、上升/下降动态、稳态偏差及逐车型模型比较；SSRN PDF 本轮403，未完成全文方法审查 | 原伴随论文已覆盖最自然的执行误差问题；不能据摘要断言未做序列依赖。其未读全文是推荐新颖性认证的真实缺口 |
| Imanaka & Baba, Measurement of Both Full Activation Time and ICT Response Time for Fast DR of Electric Vehicle Charging（2025在线；Crossref日期2025-09-27）；adjacent；[DOI](https://doi.org/10.1002/tee.70176) | PARTIAL。出版社索引可见同步 ICT 与实际完成响应的实验系统、不同控制路径；全文访问未闭合 | “通信确认不等于实际完成”已有直接工作。没有依据把这个原则当新 |
| Bisha, Winschermann, Secchi & Marinelli, EIA Nordic2026；adjacent；[DTU 官方记录](https://orbit.dtu.dk/en/publications/from-models-to-measurements-a-survey-and-experimental-analysis-of/) | PARTIAL，accepted/in press 官方记录；三个商用 AC 充电器，讨论多厂商观测、时钟和控制限制 | 进一步反对泛泛写“理论聚合与现场不匹配”；未读全文不作更具体归因 |

## 四问判定

| 问题 | 当前可答 | 顶刊缺口 |
|---|---|---|
| Why care? | 真实执行限制或用户声明修订会改变可交付需求响应，关系配网容量与新能源平衡 | 重要性已经由强先例证明，不等于本研究新颖性 |
| What's new? | 暂无已核透且不重复直接先例的核心结论；序列级资格是候选问题而非已知结果 | 不能用更大模型、拼接网络或更保守折减补足 |
| Why believe it? | ACN 支持声明目标回放，KIT 支持已实施指令的电气响应，热泵有真实干预 | 新策略因果收益、跨车共同失败、全市场代表性都没有现成独立标签链 |
| Why this venue? | 若能证实标准检验遗漏了一类可复现的持续服务失效并提出有效的资格修正，才可能触及 TSTE/更广系统读者 | 当前只有已知限制的再量化或不闭合的外推，不能承诺顶刊价值 |

结论是本次投资判断，不是证明这个领域没有开放问题。停止本支进入实验；保留明确可用的数据和文献边界，避免下一轮再从理想电池或完美离开时间的稻草人出发。
