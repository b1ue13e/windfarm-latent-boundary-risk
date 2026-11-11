# Wind Energy V2：方法、图3与证据桥跨轮核验

**结论：WE-03、WE-04、WE-05、WE-06 在 V2 当前明确收窄的主张范围内均为 RESOLVED；本角色未发现新增的方法或图3投稿阻断项。** 这里的闭合是定义、解释和呈现责任闭合，不是 bootstrap 名义覆盖、任意未来年风险、现场交付或实际资源节省获得认证。后四项仍为 UNKNOWN／未验证；V2 已明确不作这些主张，故不把已撤回的强主张继续当成未完成修订要求。整稿贡献、实际接口意义及投稿包的最终判断由综合复核承担。

REVIEW PROFILE：一般科学审查，计算方法与显示/符号/来源模块。  
PAPER：Incremental Telemetry for Wind-Power Shortfall Decisions under a Fixed Forecast Commitment。  
MODE：只读跨轮复核；唯一新增文件为本报告。  
ROUND：原对抗审查后的 V2 复核。  
SOURCE BASIS：原审查 REVIEW、reviewer_methods、reviewer_claim_figures；V1/V2 正文和 SI；原始 primary/secondary/history JSON；冻结实现源码；V1/V2 图3 PNG；V2 图源 CSV 和 manifest。未以作者回应或旧 QA 的 PASS 作为闭合依据。  
SKILL：paper-review；以 academic-writing-skills 为完整性基础，加载跨轮、计算研究及公式/显示来源模块。已读 AGENTS、科学契约第8–9节和 PROJECT 最新节。

## 1. 原意见与 V2 的实际修复

以下 M1/S1 为 V1 正文/SI，M2/S2 为 V2 正文/SI；所有锚点均指当前文件的实际行号。

| 原意见 | V1 证据 | V2 实际修复与源实现核验 | 状态；范围内是否仍阻投稿 |
|:--|:--|:--|:--|
| WE-03：有限记录确定点值和推断随机对象未并列定义；敏感性不证明覆盖 | M1:101–111、156–160；S1:131–135；原方法意见 M1/M2 | M2:103、162–164；S2:133–157 新定义共同日向量、有限记录统计量、工作过程 law D 的人口比值，以及正分母/有限期望条件。与原 subset_inference:43–62 的分子/分母合并和比值计算一致。摘要 M2:32、讨论243、结论251均明确无名义覆盖验证。 | **RESOLVED**，VERIFIED（定义和传播）；覆盖真实性 UNKNOWN。对现有条件程序性表述不再构成阻断。 |
| WE-04：图3只给成本边际棒与较小者排除，缺候选先充分的联合成本证据桥 | M1:191–197、V1图3a；原 CF-01 | M2:197–207、S2表S7:280–292；V2图3a直接显示0.9742%/3.5178%，图3b显示同一副族风险9.7699%/6.7049%，并标清180的 possibly-feasible 身份与171/181的 witness 资格。下文直接核原 JSON 全部字段及15项排除。 | **RESOLVED**，VERIFIED；无剩余图3证据桥阻断。 |
| WE-05：单数 policy 掩盖五固定fit平均损失；主次两族各 alpha=.05 不是整篇统一95% | M1摘要/结论和M1:101–111；原方法 M6/M7 | M2摘要32、方法103/113、结果172/174、结论249及S2:131/163明确五fit均损失与逐fit风险；M2:164、S2:157明确主次各.05、跨度不联合，同副族多容限复用相同界。源码没有重抽seed或平均动作。 | **RESOLVED**，VERIFIED；未追加逐fit成本门槛，也未改alpha。 |
| WE-06：注册资源序与两个算法不能推出信息理论必要性、最强同信息函数或实测节省 | M1:89–97、195、217–221；原方法 M4/M8 | M2:99、121、205、227–231及S2:66/104/177/201明确注册拟合族、raw宽度、上游W/P与148列实现；M2:227区分信息冗余和估计/优化效应；标题及摘要未恢复全局必要性。 | **RESOLVED**（原已基本限定范围在V2保持并强化），VERIFIED；实际资源效益仍UNKNOWN，但现稿未主张它。 |

当前核验对象：[V2正文](E:/论文3/manuscripts/wind_energy_v2/manuscript.md:101)、[V2补充](E:/论文3/manuscripts/wind_energy_v2/supplementary.md:123)。历史对照：[V1正文](E:/论文3/manuscripts/wind_energy/manuscript.md:99)、[V1补充](E:/论文3/manuscripts/wind_energy/supplementary.md:123)、[原综合意见](E:/论文3/research_audit/wind_energy_adversarial_review_20261020/REVIEW.md)、[原方法意见](E:/论文3/research_audit/wind_energy_adversarial_review_20261020/reviewer_methods.md:43)、[原显示意见](E:/论文3/research_audit/wind_energy_adversarial_review_20261020/reviewer_claim_figures.md:43)。

## 2. 新日过程定义是否实质换 estimand

**没有发现实质更换。** S2:133–151 以 N_d 表示共同有限目标数，A_(s,m,d) 表示第s固定fit的日损失总量，B_(s,m,d) 表示日严格事件数。其有限记录成本是先对五fit日总量平均，再对日求和除以总N；逐fit事件率则以各自事件总量除以同一总N。工作人口定义是这些日总量期望与期望N之比，再形成两成本的比值。这是原 pooled-ratio 统计量的自然工作过程对应物。

直接实现锚点：

- [run_independent_confirmation.py:316](E:/论文3/scripts/run_independent_confirmation.py:316) 的 groups_at 在每个q/fit/策略间要求相同日count和block_ids（347–352），构成 seed×candidate×day 数组（362）。评估时的独立逐格累计式（503–514）对应日损失总量、日count和严格事件数。
- [subset_inference.py:43](E:/论文3/windfarm_moe/subset_inference.py:43) 计算 `c.mean(axis=0).sum(axis=-1)/counts.sum()`；44行在每个共享块权重下重新组合成本分子与count分母；47–53行保留逐fit事件率；54–62行先形成这两种成本的比值，而非逐日比值平均或逐fit比值平均。
- [risk_frontier.py:25](E:/论文3/windfarm_moe/risk_frontier.py:25) 以共享 circular day-block multiplicities 重抽日；没有重抽机组或训练seed。subset_inference:68–79用最大标准化偏差的经验分位构造存储界。

因此 V2 没有改成 E[A/N] 这种不等权日平均，没有把五fit当五个天气重复，没有把成本改成平均动作的ensemble损失，也没有把目标从 recorded-target observation law 换成完整运行时段风险。N的缺失机制属于D的一部分，S2:151明确不宣称缺失随机或未记录时段同风险。

**推断许可仍被正确限制。** S2:153 明确D只是解释原计算所需的工作对象，没有验证D或覆盖；M2:164及S2:203明确程序输出可复核与人口覆盖是两种责任。新增排除证明只在一个同时覆盖人口参数的事件E上推出 Q⊆G⊆A，再推有限族近优和较小者排除。该代数与 [near_optimal_set](E:/论文3/windfarm_moe/risk_frontier.py:65) 及 [diagnose](E:/论文3/scripts/audit_subset_minimum_necessity.py:16) 一致；没有从可复核分类擅自推出E在实际年份具有95%概率。D也没有被写成新近冻结或已实证成立的分布模型。

由此关闭的是原 WE-03 的对象不明及过度推断风险。真实年内稳定性和覆盖资格仍未取得；在现有明确条件解释下，不要求为已撤回的现场/未来年保证追加实验。

## 3. 原始字段到图3/表S7的闭环

直接读取的原文件（下文分别简称 P、G、H、C）：

| 简称 | 原文件与本次读取SHA256 |
|:--|:--|
| P | [primary.json](E:/论文3/analyses/independent_confirmation_execution_20261019/recovered/results/aggregate/primary.json)：`f703e64fb7e20843f7daddeb9cc3b0b6d4e95594658560831ba425ac1df7bf72` |
| G | [secondary_span3.json](E:/论文3/analyses/independent_confirmation_execution_20261019/recovered/results/aggregate/secondary_span3.json)，定位 `results[condition='pitch_withheld']`：`67d6573e2f900e0e27a7f02a2915403e50d6abc4dd31cc9794709b7dde2bf060` |
| H | [历史bounds.json](E:/论文3/analyses/independent_confirmation_execution_20261019/history_freeze/bounds.json)，定位 `groups[0]`：`9da74aab5654ff5b8eeb7636834d4914c01adddc467bfd7274a3280e7a0a6a0b` |
| C | [历史choices.json](E:/论文3/analyses/independent_confirmation_execution_20261019/history_freeze/choices.json)，定位 pitch_withheld 组：`358e0884ea36c86f98518a3f4ba5b3902716c60b27c476a93536203f689ada29` |

G中的D2表示 `secondary_retrospective_full_q[epsilon=.02]`。下表均为既有字段提取、最大值/argmax及×100显示转换，不是新区间。

| 对象/字段 | 原始值 | V2显示/解释 | 核验 |
|:--|:--|:--|:--|
| 索引41，P1/HGB/q0.925；`D2.sufficient_set.required_relative_tolerance[41]` | 0.009741996453634834 | 0.9742%<2%；充分 | 一致；41在eligible，minimum_resource_indices=[41] |
| 索引42，P1/HGB/q0.95；同字段[42] | 0.03517815071811852 | 3.5178%>2%；成本未认证 | 一致；42不在eligible |
| `max(G.risk_upper[:,41])` | 0.0976988760696712 | 9.7699% | 一致 |
| `max(G.risk_upper[:,42])` | 0.0670488602271627 | 6.7049%（副族） | 一致；没有错用主族6.2025% |
| 两候选最坏成本比较的argmax | 180，PQ36/HGB/q0.9；`relative_ratio_upper[41/42][180]`恰等于上述required值 | possibly feasible，非risk-qualified | 一致；180在possible_feasible_indices，不在risk_qualified_indices；五个lower全≤.10，而upper全>.10，最大upper=.11525734470810363 |
| 成本排除见证171，PQ6/HGB/q0.925 | 五fit upper最大=.09756399270149216；171在risk_qualified_indices | 9.7564%；合格见证 | 一致 |
| 成本排除见证181，PQ36/HGB/q0.925 | 五fit upper最大=.09659798632751562；181在risk_qualified_indices | 9.6598%；合格见证 | 一致 |
| q.95相对合格171/181/211的成本upper | .03443900155039654 / .034753095871812564 / .03448228017880948 | 3.4439/3.4753/3.4482% | 一致；对应lower=.015794866804682388/.015650546089210637/.015235101288032427，全<.02，因此只是未认证，未证明真实超2% |

V2实际显示检查：目视 [V2图3](E:/论文3/manuscripts/wind_energy_v2/figures/fig3_secondary_minimality.png) 与 [V1图3](E:/论文3/manuscripts/wind_energy/figures/fig3_secondary_minimality.png)。V2的a/b轴明确为上界，2%与10%原线保留；diamond/star语义明确；c给全部15个较小者；图内直接注明180不合格、成本排除见证已合格以及upper失败不是已证超限。图注M2:207、表S7与紧邻正文没有恢复被V1边际棒无法支持的推断。[图源投影入口](E:/论文3/manuscripts/wind_energy_v2/scripts/build_figures.py:114)只取存储字段和定位argmax。

### 15项排除逐项核验

G.D2.minimum_audit 的 `chosen=[41]`、`smaller=[0,1,2,3,4,5,6,7,8,9,220,221,222,223,224]`、`unresolved=[]`；严格资源序重新核对得到同一15项。两项风险排除为0和5，其原 `witness_seed_indices` 分别是[0,1,3,4]和[0,2,3,4]；CSV转换为201起始的seed编号正确。13项成本排除均满足原 `relative_ratio_lower[j][k]>.02`，且对应k=171或181的每一fit风险upper≤.10。

以下成本lower为原比例值（表S4将其×100）：

| 较小索引 | 见证索引 | 原ratio_lower |
|--:|--:|--:|
| 1 | 171 | 0.1459006584197605 |
| 2 | 171 | 0.15439508091942897 |
| 3 | 171 | 0.27238983813608997 |
| 4 | 181 | 0.6124142231938193 |
| 6 | 171 | 0.15085372797984742 |
| 7 | 171 | 0.15841834751296274 |
| 8 | 171 | 0.27152553590812156 |
| 9 | 181 | 0.6161804043276944 |
| 220 | 181 | 0.2530794545392703 |
| 221 | 181 | 0.250732550005196 |
| 222 | 181 | 0.29140295386766235 |
| 223 | 181 | 0.46534879213636876 |
| 224 | 181 | 0.85582090431781 |

对照 [V2图源CSV](E:/论文3/manuscripts/wind_energy_v2/source_data/fig3_secondary_minimality.csv)、[15见证CSV](E:/论文3/manuscripts/wind_energy_v2/supplement_data/towie_q925_all_15_witnesses.csv)、S2表S4:181–199及表S7:280–292，未发现遗漏、见证未资格、数字或单位转换错误。独立标准库只读断言结果为：`DETERMINISTIC_PROJECTION_CHECK: PASS; 2 candidate rows; all 15 smaller rows; 2 risk and 13 cost exclusions; witness qualifications and all displayed source numerics agree.`

### 历史q.925未资格及主次身份

H的41成本=72.04798840838436；五fit upper=[.11071948147739905,.11048946346250008,.11052277011524096,.11037818681082823,.1101743675160057]，显示范围11.0174%–11.0719%正确。H的42成本=73.05620402203374，upper范围.07854931123818945–.07865455360052429，显示7.8549%–7.8655%正确。C的 `q_indices[8]=42`、`sets['0.02'].original_indices=[42]`、`reference_index=212`、`reference_historically_qualified=true` 与主P的两labels及 `uses_test_selection=false` 一致。

M2:203、S2:292只说历史upper未通过，不说历史真实风险已证>10%；没有把2025次要q.925倒灌为历史selector成功。两种责任没有合并。

## 4. 五fit与alpha的独立核验

P的mean_cost=[67.02040332110329,66.64443044512103]；paired point/lower/upper=[.005641474815991643,.0035746800646510356,.00770826956733225]。P的candidate逐fit upper最大=.062024677991181394，reference最大=.062003949794789875。V2的主结果、摘要和结论保留同一均损失/逐fit风险责任，没有要求每fit成本都非劣，也没有声称从训练算法再抽一fit仍非劣。

原 [protocol.json:103](E:/论文3/experiments/independent_confirmation_execution_20261019/protocol.json:103) 的alpha=.05、n_boot=20000、bootstrap_seed=20261029、seeds=201–205不变。[aggregate入口:543](E:/论文3/scripts/run_independent_confirmation.py:543)对两策略主族单独构界；552行对完整副族另行构界，各 span 重用该alpha。原字段主14坐标、副74500坐标与 2×5+2²=14、(225×5+225²)+5×(65×5+65²)=74500 一致。副族各epsilon在同一已存env上判定（560–565），并未为五epsilon重新生成五个独立界。V2没有声称整篇统一95%。

源码绑定检查：对本次使用的 subset_inference、risk_frontier、independent_confirmation、run_independent_confirmation、audit_subset_minimum_necessity 执行 `git diff 24153f8 -- <上述五路径>`，输出为空；前三个源码与portable包副本逐字节一致。包身份不用于替代原文件的上述数值核验。

## 5. 真正新增的问题与边界

**本范围未发现 NEW / REGRESSED 的实质问题。** 不把原 WE-03 的覆盖未知重命名为新增问题，不把原 WE-06 中已明确排除的全局资源/信息主张重新要求证明，也不因新图省略V1的代表性边际轨迹而要求恢复它：V2图3承担的是更直接的联合判定职责，成本点值及后果账目仍在结果和SI中。

当前未获验证的性质仍应保持：实际年过程是否满足D近似、人口覆盖是否达到名义水平、未记录目标时段和下一年能否外推、现场接口需求、实际资源节省。**这些未知没有被本报告或V2的新定义变成已证实事实。** 若后续恢复这些强主张，应重新开对应责任；当前没有理由把它们作为WE-03/06未修的重复意见。

## 6. 功能完整性回顾与执行记录

- CHECKED：指定四项原意见、V1/V2方法与下游摘要/结果/结论、SI新增D与条件证明、原主次/历史JSON字段、图3的旧新实际PNG、完整15见证及成本/风险资格、源投影规则、冻结实现差异、alpha与坐标责任。
- OUTSIDE_SCOPE：整稿新颖性/应用重要性、全部近邻全文与期刊政策、portable包完整可移植性、全PDF排版审查、所有远端权重/原始测量当前现存性；其他角色负责或综合报告注明。
- UNKNOWN：真实过程law与coverage、未记录时段外推、现场交付与实测资源收益；不是本轮已验证事项。
- 仅做文件读取、SHA、索引/argmax/计数/×100、原界不等式判断与代数检查；没有加载权重、模型推理、拟合、校准、bootstrap生成/统计重采样、仿真、新测量读取/下载或远端访问；没有生成新区间。
- 没有改V1/V2稿、图、阈值、源码、结果、科学契约、PROJECT；不commit。未运行科研门禁，因为本报告不是新增科研里程碑或覆盖认证，不以门禁替代本次跨轮判断。

本报告为有界方法/显示复核完成记录，不能单独作为整篇投稿放行。
