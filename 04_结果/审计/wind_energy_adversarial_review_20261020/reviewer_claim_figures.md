# Wind Energy 稿件：主张—证据—图表对抗审查

审查日期：2026-10-20。角色：主张与图表审查；模式：只读、投稿前实质审查。采用 `paper-review` 的显示/符号/溯源及计算研究模块，参照 `academic-writing-skills` 的证据和严重度规则。S0=排版；S1=局部阅读；S2=可能误读/局部证据呈现不完整；S3=主论证/可复现性/跨文件或投稿完整性；S4=证据有效性、主要结论或伦理。本文的 VERIFIED 表示直接文件/源码/静态核对支持，INFERRED 表示审查推论，UNKNOWN 表示本轮未验证。

## 审查边界与裁决

先读 `AGENTS.md`、科学契约第8—9节和 `PROJECT.md` 末节；随后完整冷读正文与SI。没有先读旧 `qa/` 审查/验收、`FOUR_QUESTIONS_CN.md`，也没有以旧审查结论作为本轮证据。核了四幅实际PNG、四份 `source_data`、`build_figures.py`、六张SI表及对应附件、原始 primary/secondary JSON、历史冻结 choices/bounds 和 primary loss ledger。没有改稿/阈值/原结果，没有运行拟合、预测、校准、统计重算、重采样、仿真、测量下载、远端命令或科学门禁。下面对既存数组做的索引、argmax、计数、单位换算和逐字段/逐字节比较均是静态记录检查，不产生新估计或新区间。

**裁决：本角色未发现 S3/S4 的数值失实、主次结果替换、15项排除失效或图表改变科学结论。主q=.95的固定参照非劣、正成本溢价和U增加，以及次q=.925的有限族最小性，与所读原始记录一致。现有证据不支持成本胜出、真实资源节约、传感器移除或现场可交付，正文已经保留这些边界。**

仍有一个应在投稿前修的 S2 证据呈现缺口：图3和SI表S4把“排除更小策略”显示得很充分，却没有把被选策略满足全族成本充分性的实际联合上界显示出来。图3a的边际成本棒不能承担这一步；承担最坏比较的竞争者及历史为何没选q=.925，也没有在稿件中交代。所需证据已在冻结JSON中，无需新分析。详见 CF-01。这个缺口不推翻既存分类，也不要求新增实验。

## 主张表

以下 `M:L` 指 `manuscripts/wind_energy/manuscript.md` 行号，`S:L` 指 `supplementary.md` 行号。JSON用精确字段代替易变的大文件行号。

| 主张/读者可能推论 | 稿件位置 | 原始证据与检查 | 裁决、级别及范围 |
|:--|:--|:--|:--|
| 主q=.95历史选择完成后，对2025固定WPQ36/q=.95参照通过2%成本、10%事件率要求 | 摘要M32；M168—170；结论M239；图2 | `recovered/results/aggregate/primary.json`：labels顺序、`uses_test_selection=false`、`verdict.status=ALL_FROZEN_CANDIDATES_CONFIRMED`、14坐标 | VERIFIED。是一个固定参照的有界确认；稿件没有改称全族近优。 |
| 主候选成本67.020403，参照66.644430；+0.5641%，联合区间[+.3575%,+.7708%] | M168；S143；图2a | `primary.json.bounds.groups[0].mean_cost`、`relative_ratio_{point,lower,upper}[0][1]` | VERIFIED。两个界都正，图中零和2%都可见，没有把非劣画成胜出。 |
| 最大实例风险上界6.2025%，参照6.2004%，均<10% | M170；S143；图2b | `primary.json.bounds.groups[0].risk_upper`，候选最大为seed205，参照最大为seed204 | VERIFIED。图显示全部五实例点与界，没有把五种子当五独立天气年。 |
| 采购几乎不变，U均值上升2.1843%，小幅事件率下降不代表缺额更轻 | 摘要M32；M176—178；主表2；S145；结论M239 | `research_audit/resource_loss_ledger_20261019/loss_ledger.csv`、`policy_seed_ledger.csv` | VERIFIED为既存点账目；每实例U差值为正。没有U专属置信区间，稿件明确不赋予新显著性。 |
| q=.95与q=.925是相同拟合预测器的不同历史offset，不能混作两套重训模型 | M87；S108—119 | `windfarm_moe/independent_confirmation.py:57—64`及 `risk_frontier.offset_grid` 的单预测器offset族；`protocol.json.offset_quantiles` | VERIFIED。稿件的术语说明正确。 |
| 次q=.925在2025全q族2%下资源最小 | M191—195；S149—179；图3 | `secondary_span3.json.results[pitch_withheld].secondary_retrospective_full_q[epsilon=.02]`：`eligible_indices`含41，`minimum_resource_indices=[41]`；`minimum_audit.chosen=[41]` | VERIFIED，限225策略、已声明字典序。对读者的联合成本数值闭环缺失，见CF-01（S2）。 |
| q=.925成本65.739232，最大实例风险上界9.7699%，资源(1,1,5) | M191；S155；表S5；图3a | 同组 `mean_cost[41]`、`risk_upper[:,41]`、`resources[41]` | VERIFIED。图纵轴是最大实例**上界**，不是点风险；图注写清。 |
| 全部15个严格更小策略均被排除，其中2风险、13成本 | M191、195；S155—177；图3b、表S4 | 原 `minimum_audit.smaller/excluded` 均15、`unresolved=[]`。索引0—9为两Common估计器×五q；220—224为Persistence×五q；与源表和SI逐条一致 | VERIFIED。没有遗漏本族严格更小项；同资源W1/Q1等不是“严格更小”，也不应偷偷算入15。 |
| 13个成本排除使用合格证人 | 表S4；S153、159 | 原excluded中证人171=`PQ6/HGB/q0.925`、181=`PQ36/HGB/q0.925`，二者均在同一结果的`risk_qualified_indices`，五实例upper均<10% | VERIFIED。图3a没有显示这些证人；不导致数值错误，但削弱图的自证性（CF-01）。 |
| 主q=.95没有进入次全q2%充分集合 | M193；S179；图3脚注；结论M241 | 原 `eligible_indices`不含42；`required_relative_tolerance[42]=.03517815071811852` | VERIFIED为“未通过认证”。不能写成已经证明其真实成本必超2%，因为相关lower仍跨2%；当前稿没有这样写。 |
| q=.925结果不意味着历史选择器当时选中了该全族最小者 | M193、225；S179 | `history_freeze/choices.json.groups[pitch_withheld].q_indices[8]=42`，`sets['0.02'].original_indices=[42]` | VERIFIED。历史没有选41的具体风险原因在本报告后述，可补充解释。 |
| 112→5是原始reserve learner列数的功能性减少 | M83、97、137—138、217—221；表S1 | `registered_confirmation_policies.csv`与原JSON resource；`independent_confirmation.features`先造完整矩阵，`predict`再选cols | VERIFIED。HGB/MLP缺失指标转化维度、共同forecast输入及148列实现开销均已声明。不能外推实际内存/通信/传感器节约。 |
| 2023/24分阶段，实际freeze先于2025解封 | M146—152；S219；图1b、表S3 | `protocol.json.windows`、`history_freeze/freeze.json.created_utc`、`unlocked_actual_receipt.json.event.utc` | 图和源表的时间值VERIFIED一致；图把数据代表的年份与2026实际运行事件区分。完整日志真实性/全知情史不由这张图单独认证。 |
| 共同预测器到issue−6，目标issue+6，是12步上游跨度、6步决策lead | M61；图1a；S26 | 正文/图中文字一致，源码 `stage_data` future target `anchors+6`，`point_features`与共同forecast约定 | VERIFIED为所读定义/源码范围。没有声称实测工业到达时钟。 |
| 1,059,248共同有限future-power目标，零/负值保留 | 主表1；M79、134；S76；图2注 | ledger各实例count一致；源码 `stage_data`仅`mask=np.isfinite(true)`，不按输入/状态/pitch删目标 | VERIFIED为所读记录和源码；未重新读测量数组验证逐目标身份。 |
| Towie90格：46最小、26未解、18无充分；固定历史集合63确认、24无选、3未确认 | M201、205；S185—189；图4a | 原 `derived/secondary_cases.csv`及SI逐字节副本的记录计数一致 | VERIFIED。依赖格数非独立复现；3项均delay3/.005、span1/3/7，稿件保留。 |
| 图4a只显示三天主跨度，完整其他跨度见SI | M201；图4注 | `build_figures.boundary_rows`仅筛span3，源表30个Towie行与原记录相同 | VERIFIED。图不是46/90独立成功率可视化。 |
| WTB28个三天2%比较有风险合格项但无充分候选 | M207；S193—195；图4b | 原 `all_decision_cases.csv`筛span3/.02共28，`risk_qualified_count>0`全为真，均`NO_IDENTIFIED_POLICY` | VERIFIED。不是所有策略都不安全/不可行。 |
| WTB420格367无充分、53最小未解、0最小；5%下四预算有PQ1/HGB候选 | M207；S195—199 | 原 `necessity.csv`分类记录；`pq1_candidate_table.csv`、`all_decision_cases.csv` | VERIFIED。次full-q40k/5%仍无充分的事实未被“历史recipe四预算可行”覆盖；正文明确所指分析责任。 |
| WTB360k PQ1成本32.670107、风险上界8.5952%，14/21较小项未解 | S197 | 原 `derived/pq1_candidate_table.csv`对应360k行 | VERIFIED。保留阴性/未识别解释，没有把已合格的PQ1叫已识别最小。 |
| 图3横棒是边际percentile；主图2是联合配对界；不能由重叠棒判差异 | M197；S133—135、141、149 | 源码 `subset_inference.py`的`np.quantile(dc,.025/.975)`与max-standardised比值界分开；图3源字段直接读前者，图2读ratio界 | VERIFIED。图注准确。图3边际棒的定位功能仍可改进（CF-01）。 |
| 1/7天次分析均q=.925；上界9.6015%/9.8752% | M203；表S5 | 原secondary_span1/7同组字段与CSV投影一致 | VERIFIED。三跨度分开，不是联合覆盖，稿件已说明。 |
| 结果不证明全局信息冗余、零样本迁移、经济节约或现场备用安全 | 摘要末句；M217—235；S241—245 | 所读研究任务只有共同预测+既存policy成本/事件代理，未提供相关外部物理/经济测量 | 对这些扩张主张属于UNKNOWN/未证；稿件已正确限制，没有需要纠正的越界句。 |

## CF-01：核心全族充分性的“联合成本那一半”仍藏在原始JSON里

- **级别/状态**：S2，OPEN；缺失位置为VERIFIED；误读风险是INFERRED。
- **位置**：M191—197；S151—179；图3a/b；`scripts/build_figures.py:81—111,229—277`；表S4。
- **具体问题**：图3a只画Common、P1、WPQ36三个HGB系列的边际成本棒和最大实例风险上界；图3b只给15项R/C排除矩阵。表S4进一步展示“更小策略为什么可排除”，却不展示P1本身对全部possibly-feasible竞争者的最坏**配对联合成本upper**。因此图3的两面板不足以独立展示“P1足够 + 每个更小者不够”的完整证据。图注明确棒非联合界，避免了错误推论，但同时也意味着棒不能提供主句所需的充分性证据。
- **最小修正**：直接从既存JSON投影一个小表或一句数值说明，列q=.925与q=.95的全族最坏paired-cost upper、控制竞争者及其资格身份；附一行说明历史q=.925因风险upper未资格。若保留图3a三个系列，明确其用于展示代表性cost/risk校准轨迹，核心判据见该小表；无需把225条策略全画进主图。表S4可加两证人最大实例risk upper，或注中给出，使“risk-qualified witness”也能就地核验。
- **权限**：仅稿件/图注/表格的既存证据投影，不改原结果/阈值；本轮没有实施。
- **投稿阻断**：不是研究有效性S3/S4阻断；建议投稿前修好此S2，不能只因图3美观或所有数字对上就把呈现链条视为闭合。

### 只读追踪得到的精确闭环

原文件：`analyses/independent_confirmation_execution_20261019/recovered/results/aggregate/secondary_span3.json`。

定位组：`results[condition='pitch_withheld']`。在 `secondary_retrospective_full_q[epsilon=.02].sufficient_set` 中，`possible_feasible_indices`有197项，`required_relative_tolerance`是所存各候选对这个集合的最坏成本比upper。只读argmax定位结果如下；这里没有重新估计区间。

| 候选 | 存储索引 | 控制竞争者 | 该配对point / lower / upper（%） | 该候选的全族认证 |
|:--|--:|:--|:--|:--|
| P1/HGB/q0.925 | 41 | 索引180，PQ36/HGB/q0.9 | 0.580255 / 0.186310 / **0.974200** | 成本upper<2%；风险upper全<10%，通过 |
| P1/HGB/q0.95 | 42 | 同一索引180 | 2.540432 / 1.563048 / **3.517815** | 成本upper>2%，未认证 |

字段分别为 `relative_ratio_point[i][180]`、`relative_ratio_lower[i][180]`、`relative_ratio_upper[i][180]`，恰与 `required_relative_tolerance[i]`一致。

**竞争者180不是风险合格策略。** 它的五实例风险lower全<10%，所以仍是possibly feasible；但upper为10.9488%、11.2583%、11.5257%、11.4335%、11.1496%，不能被叫作“已经合格而胜出的最强参照”。不能因为其点风险部分>10%就私自从成本比较中删掉它，原规则保留它是正确的。

q=.95的非认证也不是只由这个风险未解竞争者造成：对已风险合格的PQ6/q=.925、PQ36/q=.925和WPQ36/q=.925，所存cost upper分别为3.443900%、3.475310%、3.448228%，仍>2%。相应lower为1.579487%、1.565055%、1.523510%，均没有越过2%。因此正确结论是**未能认证2%充分**，不是**已经证明真实成本违反2%**。

两种全族证人的资格也可直接显示：

| 表S4成本排除证人 | 索引 | 最大实例风险upper（%） | 字段 |
|:--|--:|--:|:--|
| PQ6/HGB/q0.925 | 171 | 9.756399 | `risk_upper[:,171]`，且171在`risk_qualified_indices` |
| PQ36/HGB/q0.925 | 181 | 9.659799 | `risk_upper[:,181]`，且181在`risk_qualified_indices` |

图3a没有显示180/171/181。已有标明“selected HGB policies”的标题，使这不是隐瞒全族的确证；但最坏成本比较和实际证人都在图外，读者不能由图中的橙色WPQ36成本棒替代这三种不同职责。

### 历史为什么选q=.95，而不是成本较低的q=.925

精确原路径：

- `analyses/independent_confirmation_execution_20261019/history_freeze/bounds.json.groups[0]`：历史2024选择期全q联合界。
- 同目录 `choices.json.groups[condition='pitch_withheld']`：`q_indices[8]=42`、`q_historically_qualified[8]=true`、`sets['0.02'].original_indices=[42]`、`reference_index=212`、`reference_historically_qualified=true`。
- 判定源码 `windfarm_moe/independent_confirmation.py:67—95`：先在每recipe内排除任何实例risk upper>cap的q，再从剩余q中选最低历史均值成本；不是在所有q中不加资格地找最低成本。

| 历史P1/HGB校准 | 历史均值成本 | 五实例风险upper范围（%） | 历史资格 |
|:--|--:|--:|:--|
| q0.925，index41 | 72.04798840838436 | 11.0174—11.0719 | 五实例upper均>10%，不合格 |
| q0.95，index42 | 73.05620402203374 | 7.8549—7.8655 | 合格；较更高合格q成本低，被选 |

这是解释主次差别的重要具体证据：q=.925不是解封后新拟合出来，它历史已拟合，但在2024选择期没有风险资格；到了2025次分析才满足风险/成本充分性。历史upper未过不等于当年真实风险已被证明>10%，也不等于选择器实现错误。

**可解释的边界**：VERIFIED的是不同年份所存风险界、资格规则、不同比较集合和校准档位的影响。INFERRED的是它们足以解释“同一predictor不同offset、主确认与次全族结论为何不矛盾”。UNKNOWN的是哪一种天气、地形、控制或缺失机制导致跨年的差异；没有因果机制分析，不能把这些字段升格成物理解释。

## 四图与八表的证据职责检查

| 显示对象 | 是否真的承担所对应段落 | 省略/统计语义的检查 |
|:--|:--|:--|
| 图1a | 支持共同forecast与增量reserve层的区分 | 箭头是数据流，没有物理因果用语；保留上游W/P。 |
| 图1b | 支持历史数据阶段与实际freeze/unlock的不同时间轴 | 2023—25是数据代表期，04:27/04:30是2026执行事件。图只打印package creation和unlock，实际freeze validation见S5.2；未发现当前时序冲突。 |
| 图2a | 直接支持正溢价且upper<2%的主非劣 | 一条配对联合区间不冒充边际cost棒；不把0.564%舍入为零。 |
| 图2b | 直接支持五固定实例均风险资格 | 实例205点风险候选高于参照仍显示，未只选有利实例；坐标裁切未隐藏所需点/界/10%线。 |
| 图3a | 提供代表性校准cost/risk几何，不能单独证明全族充分 | 仅15个HGB点，完整225策略未画；选择范围有标题，边际棒/联合纵轴有图注。需补CF-01的直接判据，不能由棒重叠论同效。 |
| 图3b | 正确覆盖全部15项严格更小注册项的排除类别 | 图上R/C是判定类型而非新效应量；真实witness及lower在S4。没有把同tuple全部实现叫唯一最小。 |
| 图4a | 正确显示30个三天次分析的分类 | 完整90格统计在文/CSV；M不等于业务成功率。各容限下最小元组可改变，M/U随容限非单调不是此图必然错误。 |
| 图4b | 正确保留WTB阴性和未注册预算格 | 28个两个责任一致的结果合成14格，图脚注说明；“—”不是失败数据。没有把其与Towie作控制变量实验。 |
| 主表1 | 主比较的样本、输入、q、参照和要求清楚 | 5/112为raw selected widths；每个策略的forecast仍用W/P，不能解释为总信息成本。 |
| 主表2 | 正确保留loss分解和更高U | 单位、差值先算后round和无新CI均注明；未用事件率近同把U增量隐藏。 |
| 表S1 | 完整22输入格、宽度 | Common四列；三通道36步112列；MLP/HGB缺失处理另释，raw宽度非统一实际输入维度。 |
| 表S2 | 五压力条件与pitch共享、部分格 | Fresh与delays含pitch，不能把其P1与pitch-withheld P1当同总信息；文中有明示。 |
| 表S3 | 时间窗/WTB与Towie分工正确 | 半开窗和末端标签成熟规则单列，不能从日历边界直接推无泄漏；本轮不重跑人口/clock测试。 |
| 表S4 | 数值与全部15证人一致 | 两风险行用instance201均确实>10%；Common/MLP选中行仅10.0104%，仍保留，没有把接近门槛改写成高置信安全结论。CSV保留更多风险证人。 |
| 表S5 | 三个独立跨度的同一q=.925结果 | point cost不变因预测/人口不变，upper随跨度变；不是三个独立年度重复。 |
| 表S6 | 指向primary/secondary/ledger/WTB源记录 | 是本地证据导航，未冒称完整模型/测量字节已纳入写作包。公开可获得性的投稿要求由另一个可复现性角色审。 |

## 核对结果与未覆盖事项

1. 图2源CSV的33个数字字段直接等于原primary JSON的相应字段（含百分比换算）；图3的150个标签/数字/证人字段与原secondary JSON一致；图4的58行逐行等于其指向的原CSV（30个Towie+28个WTB）。图1的五个window和两个实际事件记录也与其原JSON值一致。
2. 三份完整case附件 `towie_all_90_cases.csv`、`wtb_all_420_sufficiency_cases.csv`、`wtb_all_420_minimum_cases.csv` 与所指原CSV逐字节一致。550策略资源附件、15证人附件和三跨度附件所述规则与原JSON投影入口一致。没有把projection receipt当成统计有效性证书。
3. 所有四幅实际PNG均已查看；审的是数量、标签、面板职责、坐标语义及省略是否改变推论，没有以颜色、留白、漂亮程度来判科学质量。
4. 本角色没有复核原始测量、完整逐时动作、bootstrap抽样或coverage，也没有复现远端权重；其真实性/覆盖率不能由本次显示审查或字段一致性代替。没有复查文献和期刊官方格式；那些不是本角色覆盖范围。
5. 除本报告外没有写文件，不commit，不改PROJECT。未运行科研门禁：本轮没有声称新科研里程碑，只记录对既存写作产物的有界审查。

投稿前最小动作是补CF-01现成字段的展示闭环，并保持现有负结果及边界。若作者进一步升级成“q=.925历史就应当选”“q=.95已证真实超2%”“所有更简单函数都无效”或“减少了实际遥测成本”，本次审查不为这些新主张背书。
