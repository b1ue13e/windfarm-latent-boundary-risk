# 价格型需求响应随机试验：补充资格审查

审查日期：2026-10-20。范围：文献、官方档案与元数据；没有下载运行数据、运行实验、申请数据或修改论文。

## 决定

**NO-GO：不把这条方向列为本轮可推荐的顶刊主线。** 这不等于判定 CER 数据无价值或无法获得。当前不存在同时满足“当前可取得的微观数据、未被直接先例覆盖的新对象、与原试验设计相符的可识别交付终点”的闭合候选。不能用需要许可的数据加上未经验证的容量解释凑成第四条方向。

## 数据资格

### 爱尔兰 CER Electricity Customer Behaviour Trial

- **VERIFIED**：官方档案 DOI [10.7929/ISSDA/BX59EU](https://doi.org/10.7929/ISSDA/BX59EU) 明确限定非商业研究/教学，研究用途需要提交 ISSDA 申请表；主要 smartmeterFile 文件标记 Restricted / Request Access。20 个文件的目录存在不等于已获微观数据访问权。没有申请或下载。
- **VERIFIED**：官方 [CER/11/080 项目报告](https://www.ucd.ie/issda/t4media/cer11080.pdf) 描述 2009 年基线和 2010 年价格/信息处理，住宅与商业客户分组、用电观测及调查。主试验是长期固定分时电价/信息处理，不是可以任意定义事件时间、长度和连续调用次数的事件调度试验。
- **UNKNOWN**：本团队是否满足申请资格、批准期限、最终到手版本中随机分组/脱落/缺测字段的完整性。不能把申请尚未完成写成“数据不存在”。

### 日本 Ito–Ida–Tanaka 试验

- 一手论文：[Moral Suasion and Economic Incentives: Field Experimental Evidence from Energy Demand](https://www.aeaweb.org/articles?id=10.1257/pol.20160093)，American Economic Journal: Economic Policy，2018，10(1):240–267，DOI 10.1257/pol.20160093。
- [OpenICPSR 114688 V1 复现目录](https://www.openicpsr.org/openicpsr/project/114688/version/V1/view?path=%2Fopenicpsr%2F114688%2Ffcr%3Aversions%2FV1%2FPOL2016-0093_data&type=folder) 的团队目录核查仅见 Readme.txt 与 do_estimation-.do；本支随后打开 README 文件页受到 403 阻断，没有读到正文。
- **UNKNOWN**：是否存在可公开取得的实际微观数据。不得仅据“replication data”题名宣称数据公开，也不得将未读到的 README 概括为明确的 proprietary 声明。
- 原文已经研究干预持续性、习惯化和间隔后的恢复；这些不能重新包装为新机制。本文全文核查由根代理完成，本支未重复全文核查。

## 可识别对象与不能跨越的边界

令 Z 为家庭的随机处理分组，Y_i(z) 为其在指定试验时段、相应处理方案下的用电量。

1. 在随机化有效、处理定义一致、观测缺失可处理且无相关干扰等条件下，可估计试验人群的 ITT 均值 E[Y(1)]−E[Y(0)]，以及两个处理状态分别的边际结果分布。长期整条负荷轨迹可用于预先定义的峰段/峰后结果；不能把每个半小时都算成一次独立随机化。
2. 随机化并不自动识别 Y_i(0)−Y_i(1) 的分布。两状态分位数之差一般不等于同一家庭节电量的分位数；缺少联合潜在结果关系时，不能称为“每户可交付节电的下尾”。
3. 同日随机组聚合差可估计特定试验日的平均政策效应，但其跨日经验分布混有估计误差。只有在明确总体、共同冲击和抽样结构后，才可讨论聚合政策效应的跨日变动；不能直接当作可签约容量的交付分布。
4. 固定全年 TOU 的赋值不随机化新调用策略。新事件长度、密集调用、可随时增加/取消的调用、设备预热和强制控制均不是原干预。没有这些处理支持，无法用原 RCT 识别这些政策的效果。
5. 2009–2010 年的住宅样本本身不能验证当前热泵、电动车或高渗透自动控制群体。外推需要单独证据，不能由“随机化”二字解决。

## 最接近文献与差异资格

| 文献与角色 | 已有对象 | 对拟议贡献的约束 | 本轮核验层级 |
|---|---|---|---|
| Di Cosmo, Lyons & Nolan (2014), *Estimating the Impact of Time-of-Use Pricing on Irish Electricity Demand*, Energy Journal 35(2):117–136；mainstream | CER 随机试验的电价、信息与分时需求响应 | 不能把真实随机分组或峰段平均因果效果作为新贡献 | 作者/题名/期刊及摘要元数据已核；本轮未完整重读全文 |
| Di Cosmo & O’Hora (2017), *Nudging electricity consumption using TOU pricing and feedback: evidence from Irish households*, Journal of Economic Psychology 61:1–14，DOI [10.1016/j.joep.2017.03.005](https://doi.org/10.1016/j.joep.2017.03.005)；mainstream | 半小时效果、峰后持续、反弹检查及反馈方式差异 | “此前只有平均效应，没人检查峰后反应”不成立；其摘要报告未出现峰后尖峰，不能预设相反结果 | 出版社摘要/作者存档元数据已核；作者全文入口受阻，不能伪称全文已核 |
| Ito, Ida & Tanaka (2018)，上述 AEJ: Economic Policy；mainstream | 真实动态价格与道德劝导随机试验；响应习惯化及间隔后恢复 | 连续干预的衰减/恢复不是空白；更窄新对象仍须证明数据与支持集 | 根代理已核原全文；微观数据公开性尚未证实 |
| Harding & Lamarche (2016), *Empowering Consumers Through Data and Smart Technology: Experimental Evidence on the Consequences of Time-of-Use Electricity Pricing Policies*, JPAM 35(4):906–931，DOI [10.1002/pam.21928](https://doi.org/10.1002/pam.21928)；adjacent | 随机定价与智能技术下的异质性和分布响应 | 仅由均值换成分位数不能声称新科学对象 | 题名/DOI/摘要已核；未把它当作本轮全文完成证据 |

2023–2026 检索还发现近期公平性电价设计、动态电价建模和行为反弹工作，但本支没有完成这些全文审查。因此不声称“最新文献均排除后已确定独特空白”。由于数据资格与目标可识别性已经未通过，本轮停止；没有必要继续扩大文献范围以维持候选。

## 四问的严格答案

- **Why care?** 平均节电是否可以转化为可靠的系统服务确实重要；但这是研究动机，不是这套资料能回答的证明。
- **What’s new?** 当前未闭合。峰后响应、持续性、衰减、恢复和分布异质性均有直接或相邻先例；新名字“可交付尾部”不足以形成贡献。
- **Why believe it?** 原随机化可支持原处理的 ITT 和适当分布对象；对个体反事实差值下尾、新调用策略或现代设备群体的结论尚无合格设计。
- **Why this venue?** 若只是旧 RCT 的更多分组、分位数或模型比较，尚不足以支撑 TPWRS/TSTE/Applied Energy 的系统性新知识主线。只有明确新增决策对象、真实处理支持和实质改变系统安排的证据，才值得重新提出；本轮没有这些证据。

## 停止理由

此次停止是明确的候选筛选决定，并非“等待一轮参数细化”。不启动数据申请、不下载数据、不运行试验；不将这些检查结果或预期效果写入论文。即便将来获准 CER 数据，也不能自动升级 GO，仍必须独立解决处理支持、目标识别和相对直接先例的新意。
