# Reviewer C：实验重建、反例与研究发现审计

日期：2026-10-19（Asia/Shanghai）。角色为研究意义与跨实验发现审查；不是来源全链认证或重新实验。`VERIFIED`仅用于本次实际读到的文件和重汇总；`INFERRED`明确指解释；`UNKNOWN`指未取得的证据。

## 1. 实际检查范围

已完整读取 AGENTS.md、docs/SCIENTIFIC_CONTRACT.md、PROJECT.md，按 academic-paper-reviewer 的只读、角色分离要求工作；未读其他本轮 reviewer 的输出。没有训练、模型推理、远端访问、新校准、新重采样或修改任何原结果。

本子任务做的是**实验族清点加指定结果内容审计**，不能冒充全仓库逐文件内容审计。全项目文件总量应以主代理的资产清单为准。机器可读族清单为 `family_ledger.csv`，覆盖 28 个真实族/分支，包括失败、替代、无效和未激活分支。

内容全量读取与有限抽样分别如下：

| 范围 | 实际内容覆盖 | 不含的工作 |
|---|---|---|
| 旧/修正 E02 | 两版各 60 CSV 行，按模型×horizon×种子重汇总；读注册和现存生成/判决源码 | 未拟合模型；未从不存在于本地所查目录的日块重建联合 CI |
| 旧/修正 channel | 两版各 10 行 | 未重跑分类器；旧 h6 数值不恢复资格 |
| 旧/修正 Phase | 两版各 150 行；按相同 horizon/lag/channel 计算均值 | 未把不同目标、不同支持集版本混池 |
| E01 | 无效 v4 的 20 seed 行与 4 统计行；当前 deterministic JSON 的 20 行重汇总 | 未做原始数据重训；无效 v4 不能用作正/负外部结论 |
| E03 | 旧/修正各 70 行；修正版输出 SHA/大小与 exit0 receipt 绑定核对 | 未逐包核对完整 arrival trace，也未重新产生 crossover CI |
| 旧 dense/MoE | 50 个 run 汇总行 | 未认证其原训练现场，也未把预测误差当备用价值 |
| E04—E07 | 原 selector JSON、stability JSON、后期 bundle 选择结果、E07 protocol；描述性切片部分行 | 未重算原 bootstrap、未重新激活 E07 |
| 20261018 信息决策 | 480 个 seed/condition/model/version 行，96 个汇总行及已存配对区间 | 未把已查看 WTB 当独立确认 |
| 20261018 风险前沿 | 主/次 JSON 与表头、关键条件/区间 | 不声明全部逐元素复算 |
| 20261019 WTB 格 | 420 个决策案例 CSV、176 个缺 pitch 曲线行、4 个 PQ1 候选行 | 必要性计数与已存摘要核对，未独立重生其联合包络 |
| 20261019 独立年份 | **全部 550 个 evaluate metadata + blocks.npz**，共 550 个策略均值、2750 个种子风险点；3 日主次 JSON 和90案例CSV | 未读取模型权重用于推理；未重新计算不确定性包络 |

`read_manifest.json`记录 1128 个由重建脚本直接读取的结果/metadata/block 文件及哈希，**不包含每次交互命令中的文档/源码读取**。命令探索中的两次诊断脚本失败分别是空 NMI 字段和错误假定 CSV 列名；修复审计脚本后完整运行成功，不涉及科研实现或原数据。最终复算脚本为 `reconstruct_evidence.py`，输出 `recomputed_facts.json` 与 `independent_policy_points.csv`。

## 2. 最强正证据：下游增量输入约简的独立年份支持

**VERIFIED。** 解封前历史选择表实际选择 `P1/HGB/q0.95`，固定参照 `WPQ36/HGB/q0.95`：

- 选择证据：[historical_choices_summary.csv](E:/论文3/analyses/independent_confirmation_execution_20261019/historical_choices_summary.csv:2)。
- 原统计输出：[primary.json](E:/论文3/analyses/independent_confirmation_execution_20261019/recovered/results/aggregate/primary.json:17)，均值在24—25行，配对相对区间在104/114/124行。
- P1 成本 **67.02040332110329**；参照 **66.64443044512103** kWh/有效 turbine-interval。P1 更贵 **0.5641474816%**；已存共同日块近似区间 **[+0.3574680065%, +0.7708269567%]**。在声明的2%固定参照非劣要求内通过，不能写成成本更优。
- 候选/参照最大实例风险 UCB **6.2024677991% / 6.2003949795%**，低于10%。区间针对冻结五实例和既定共享日块近似，不是未来气候覆盖保证。

本次从全部550个存档日块包求和，**精确重得上述两个主均值与比例**；对全部550个策略点均值的最大绝对差为 **2.842170943040401e−14**，2750个实例风险点差全部为0。该细微成本差是当前不同求和顺序的记录，不放宽任何原门槛。此验证重建的是存档动作统计，不是重新预测或独立认证统计覆盖。

**INFERRED（研究意义）。** 最强保留结果是：在这个固定预测承诺上，一个不恢复 pitch 状态的低输入直接分位数策略，能在独立年份保持事先声明的风险与相对成本要求。这提供“某些条件下无需显式状态恢复即可合格”的存在性例子，比又一项 NMI 改善更切题。

必须保留三条边界：

1. [independent_confirmation.py](E:/论文3/windfarm_moe/independent_confirmation.py:32) 中共同点预测已经读取 W/P 各36历史。因此 P1 是**共同预测之外的下游增量遥测约简**，不是端到端单传感器系统，也不是风速无用。
2. 同文件49—54行的资源顺序是通道数、是否学习、原始输入列数。HGB/MLP不按参数量或FLOPs排序；`[1,1,5]` 不等于总系统只消耗5个观测或5个参数。
3. q0.95/q0.925 是历史残差 offset 档位标签；基础 Newsvendor 目标仍为 rho10 对应名义0.90，不能写成事后修改了原风险 cap 或目标。

## 3. 最小性结论与主确认必须拆开

**VERIFIED。** 独立年份缺 pitch、225策略、3日块、2%全 q 次要能力分析识别 `P1/HGB/q0.925`：成本 **65.73923230784504**、最大实例风险 UCB **9.76988760696712%**，15个严格更小候选全部排除（2个风险下界超cap，13个成本差下界超容限）。依据 [secondary_span3.json](E:/论文3/analyses/independent_confirmation_execution_20261019/recovered/results/aggregate/secondary_span3.json:1) 与 [summary.json](E:/论文3/analyses/independent_confirmation_execution_20261019/derived/summary.json:30)。

此处 q.925 来自**预声明的次要、测试侧全 q 能力分析**；不能把其最小性授予事前 q.95。q.95 在全 q 家族2%充分集合之外，并不否定它相对固定 q.95参照的2%非劣；比较对象、包络坐标族和判据不同。

90个共享案例的状态为46个有限族最小性识别、26个未解、18个无充分候选；历史冻结选择的结果为63确认、24历史无选择、3未确认。3个未确认均是 delay3、0.5%、1/3/7日块，不能用同条件全 q 的成功覆盖。来源为 [secondary_cases.csv](E:/论文3/analyses/independent_confirmation_execution_20261019/derived/secondary_cases.csv:1)。

**重要反例。** 先前 WTB420案例中367无充分候选、53最小性未解决、0有限族最小性识别。主3日块2%的28案例全部有风险合格策略、却0近优充分；所以失败包含比较不确定性/候选成本前沿问题，不能解释成“都不安全”。PQ1/HGB在预声明5%下四预算可以充分，但13/15/15/14个更小候选未排除。见 [all_decision_cases.csv](E:/论文3/analyses/claim_revision_recovery_20261019/derived/all_decision_cases.csv:1)、[pq1_candidate_table.csv](E:/论文3/analyses/claim_revision_recovery_20261019/derived/pq1_candidate_table.csv:2)。

**INFERRED。** “一个低资源策略合格”与“能排除所有更小候选”是不同的经验难度；前者跨年确认成功，后者强烈依赖窗口/有限族/容限/联合包络。两场站不同总体不能被当成同一机制的自然实验，更不能从WTB失败、HofT成功断言是哪种物理机制导致差异。

## 4. 表征、成本、风险三种排序确实会冲突

### 4.1 有功签名有效，但 wake/全套输入没有必要性证据

当前修正版 channel CSV 实际为 C2 NMI **0.4612504**、ARI **0.6469264**，C9 NMI **0.4627235**、ARI **0.6475978**，全套 C1 NMI仅 **0.2258342**。修正过渡召回 C2 **76.9703%**，旧62.9%含无效相邻标签事件，不能把两个分母混用。文件：[summary.csv](E:/论文3/artifacts/raw_replay_20261015_v2/channels/summary.csv:3)，C1在2行、C9在10行；其 SHA/大小与原 `execution/channels/record.json`的exit0记录匹配。

修正版 C2 h6成本16,393,607.8，高于其同目标直接参照234,912.8；C9成本16,536,309.8，违约率却从C2的9.36995%降至8.74742%。因此即使NMI几乎相同，风险与成本也会移动。不能从“有功可恢复”跳到“wake有增量决策价值”，更不能用旧 h6 residual-index1错误数值支持结论。

旧50 run消融的dense RMSE均值231.4236，而bal_align_force为236.1305；后者NMI.8716并没有保证更低RMSE。该结果只是历史预测表，不是当前备用充分性的直接证据；非显著不等于等价。

### 4.2 新开发里主要改进来自直接后果信号，pitch分数增益小且不能排除控制解释

缺pitch时 A_Wind **35.56305184**，B_Consequences **32.82868789**，C_PitchScore **32.76070703**，成本下降分别 **7.6888%** 与 **0.2071%**。B−A主3日块同时区间为 **[−4.852907, −0.837085]**；C−B为 **[−0.171425, −0.004112]**，但1日块同时区间 **[−0.153849,+0.003196]**跨零，且仅3/5种子改善。C对WindScore/ShuffledScore的主同时区间分别 **[−0.175289,+0.018667] / [−0.182020,+0.012103]**，不能建立pitch语义独有增益。

来源：[summary.csv](E:/论文3/analyses/decision_information_execution_20261018/evidence/results/aggregate/summary.csv:82)，配对区间为同目录 `paired_intervals.json`。这不是“C完全无效”的证明；是现有控制不支持把微小提升归因于物理状态恢复。B/C calibrated风险 **11.5666%/11.4220%**，更便宜也不能直接称风险合格。

### 4.3 新线索：几乎相同成本下，严格违约率可以跳变

**VERIFIED（文件内现象）。** 缺pitch B raw→calibrated：成本 **32.82955137→32.82868789**，仅下降约0.00263%，违约率却 **7.81714%→11.56658%**，增加3.74944个百分点。seed205则 **7.67410%→12.02709%**，对应成本32.67752815→32.67695557。其历史 correction为 **−0.25571485 kW**，见 `runs/seed205/pitch_withheld/calibration_offsets.json`。

生成源码 [run_decision_information_development.py](E:/论文3/scripts/run_decision_information_development.py:406) 对raw加全局历史offset再截零；[decision_information.py](E:/论文3/windfarm_moe/decision_information.py:74) 的事件定义为严格 `shortfall > reserve`，损失为连续的采购+短缺罚金。

**INFERRED。** 这符合阈值附近残差质量集中、少量备用移动跨越很多事件的解释，说明“名义校准更好/成本稍低”与绝对违约约束可能冲突。**UNKNOWN：**本次未逐动作核对新增违约的短缺大小分布，不能说已经证明零点原子、特定数据清洗或特定物理工况是原因。建议优先用存档动作做阈值附近直方图与新增违约严重度分解；不重新调阈值、不得借此取消原10%要求。它是值得追的机制线索，当前仍不是论文主发现。

## 5. E02 的关键版本反转：不能沿用固定失败叙事

旧E02确实有eps50 h6平均成本+3.435M、风险16.7253%；但它包含已登记的物理功率scaler问题，且旧报告判决逻辑把 `P(delta<=0)`当p值，用 `(delta<0 and p<.05)`判胜。现存 [run_exp02_zero_privileged_supervision.py](E:/论文3/scripts/run_exp02_zero_privileged_supervision.py:31) 明文说明旧规则自相矛盾，353行计算方向性概率。旧v1报告的固定“protocol deficit established”不是可靠的原始证据。

修正CSV有60行，与 [execution/exp02/record.json](E:/论文3/artifacts/raw_replay_20261015_v2/execution/exp02/record.json:218)的EXECUTED/exit0、SHA `f2df21e67cea1c661c4415a5377d02392433f30452b3c867080e32fc9df187ee`和大小精确对应。直接按五种子配对重汇总：

| endpoint/eps | 原始成本差均值kWh | 已存bootstrap delta均值kWh | 负delta种子 | challenger风险 |
|---|---:|---:|---:|---:|
| h1/50 | −394,230.797 | −395,317.582 | 5/5 | 9.1160% |
| h6/50 | −113,225.657 | −110,081.758 | 3/5 | 8.7957% |
| h1/20 | +759,183.903 | +754,201.691 | 4/5 | 15.1524% |
| h6/20 | +4,670,876.743 | +4,652,813.077 | 3/5 | 18.5741% |
| h1/100 | +788,121.403 | +782,998.315 | 4/5 | 14.9389% |
| h6/100 | +4,666,451.543 | +4,648,612.757 | 3/5 | 18.2322% |

原始均值与bootstrap均值不是同一个对象，不能用后者假称精确原始差。主eps50；eps20/100是敏感性。注册 [EXPERIMENT_REGISTRY.md](E:/论文3/docs/EXPERIMENT_REGISTRY.md:311)列h6与h1两个endpoint；本审计没有找到h1为未注册探索端点的证据，不将其改写为exploratory。现存report-level规则要求两horizon均支持才能宣称稳定优势。

h1 eps50五种子CI依次为[−413461,+36490]、[−280312,+105038]、[−999594,−246732]、[−575558,+257444]、[−1839797,−278255]；h6为[−217288,+407297]、[−528442,−219]、[−1107338,+233023]、[−300306,+1000195]、[−626234,+144086]。直接原CSV位置分别4/10/16/22/28及34/40/46/52/58行，完整精度记录于本次facts。

**UNKNOWN / 边界。** 没有重建跨日块/种子的联合CI，不能由五个CI均值、五个方向概率均值或点估计转成显著优势。正确判断仍是“稳定增益未建立”；但不能继续把**现行h6成本必然增加或零特权一律失败**当已证伪事实。也不能借这次版本反转宣称物理proxy已经成功或推翻全部项目契约。

## 6. 旧状态恢复→决策优势叙事的其他断点

**当前强基线。** Full posterior比风速分箱贵 **445,639.836 kWh**，B/C风险10.2837%/10.4439%；transition成本也多71,204左右、但风险9.77%→8.48%。joint interaction **[−597,952.521,+19,013.038]**跨零，不能称确认的过渡异质性。旧+523,044及非跨零interaction是SUPERSEDED，不可混用。原文件：[当前closure](E:/论文3/artifacts/raw_replay_20261015_v2/strong_baseline_retry_import_v1/strong_baseline_closure_summary.csv:3)、[完整四策略](E:/论文3/analyses/e04_complete_policy_comparison_20261018/v2/full_policy_metrics.csv:2)。

**风险热点不是简单的边界故事。** 描述性完整切片边界B/C为7.6517%/6.4533%；未来60min下降>150kW组为39.1393%/42.9878%。[risk_matrix.csv](E:/论文3/analyses/e04_complete_policy_comparison_20261018/v2/risk_matrix.csv:2)。前者本身不是最高风险，后者又是ex-post未来标签；应写风险重新分配，不能把未来爬坡当可在线选择策略。表中重复五种子的样本数不是独立样本量。

**E04的无解保持。** 四个风险UCB均大于10%；E05 64.64%只是指定联合种子/块抽样中的聚合约束无解频率。B/C点风险只略超10%且单侧下界仍低于cap，不得升级为总体安全已被证伪或系统性欠校准。

**Phase版本范围。** 旧66.5%（127.552→42.787）的历史同条件诊断仍由科学契约保留，但不是新的共同目标普遍规律。本次修正固定目标150行显示，h6/all/lag6短缺21.344206→22.409736（反而增加4.992%），h1/all/lag6只降低4.372%。不能比较两个版本的绝对MWh后断言物理机制反转；能确定的是普适“延迟越大，简单重校准单调吸收多数损失”的叙事不由新共同目标数据普遍支持。

**外部证据。** v4在物理窗口审计后INVALID，旧Penmanshiel负成本差不是有效外部成功。当前deterministic分支h6 Kelmarsh +6,322.698、CI[−31,417.261,+46,732.591]；Penmanshiel +356,014.398、CI[+162,798.521,+566,245.721]。它仅说明指定既有权重、本地预测/校准/窗口没有建立成本改善，不证明跨场站永远无益。LHB没有本轮同等有效的新决策闭环，不补写成第三个成功/失败复制。

**E03。** 修正版70行与receipt匹配，但60min几乎全部stale（平均99.7898%）；这仍是合成压力而非真实工业延迟分布。本轮只核对summary，不复核所有packet或联合crossover，不能宣布其全面完成。E07仍是未激活的数据资格缺口，不是一个负性能实验。

**文档残留。** [PROJECT.md](E:/论文3/PROJECT.md:53)仍将“48.4%过渡超额节约”写VERIFIED，和当前跨零interaction/更高成本的契约边界冲突；该条必须登记为历史残留，不作现行主张。另 `experiments/E06/remote_j02/e01_output/`的matched_state/common_support文件内容是AdamW/Split-Muon/weight_norm研究，应从本项目E01证据中排除；仅按目录名自动归类会污染结论。

## 7. 发现候选排序与可证伪性

| 排名 | 候选发现 | 已有证据强度 | 关键替代解释/缺口 | 本人建议 |
|---|---|---|---|---|
| 1 | 固定共同预测后，下游极少增量遥测可以在独立年份维持声明风险/成本要求；此充分性不自动等于可迁移最小性 | 最高：事前选择+一次独立确认+本次完整存档点统计复算 | 共同预测已含W/P；参照非全函数最优；单独年份/场站 | 主线，精确限定 |
| 2 | 连续成本与严格事件风险在校准后出现显著不一致，解释何以“更低成本”不等于“风险合格” | 强描述性：480行、负offset、源码判据 | 新增违规的严重度/残差密度/物理定位未复核 | 优先用现成动作补一个机制诊断，不调参 |
| 3 | 表征可恢复不保证状态语义具有独有决策价值 | 多族一致：有功主导、控制分数、strong baseline负结果 | 不同版本/目标不能池化；score微增益非完全零 | 作为主线动机及反证，不宣称普遍无用 |
| 4 | 最小性识别是证据能力而非只看最优点成本，WTB与独立年状态不同 | 420与90案透明、原始均值可复核 | 总体和有限族不同，无因果识别 | 协议贡献/补充结果 |
| 5 | 重校准或潜在状态在延迟条件普遍占优 | 不足；旧/新目标及支持不一致 | corrected Phase不支持单调普适增益 | 撤出普遍主张 |
| 6 | 新GNN/MoE/空间机制的必要性或新隐藏物理状态发现 | 不足或已有反例 | fresh-wind标签分离、容量混杂、MoE弱证据 | 停止围绕该方向扩结构 |

唯一推荐核心问题：**在固定预测承诺和风险要求下，哪些额外到达遥测足以维持跨年份的备用决策价值，且这种充分性何时足以支持有限候选族中的输入约简？**

English: **Which additional arrived telemetry is sufficient to preserve reserve-decision value across years under a fixed forecast commitment and risk requirement, and when does the evidence justify input reduction within a declared finite policy family?**

这是当前最有证据支撑的问题，并非“已发现普适最小信息定律”。如果投稿要求方法学突破，现有一例非劣与预声明筛选框架仍可能不够；需以真实运维代价/可执行通道限制说明约简的价值，而不是继续增加模型名或把审计工作量当创新。

## 8. 最小下一步，不运行新实验

1. **优先消除版本错配。** 把E02 corrected原始均值、bootstrap均值、各seed CI与旧版本分开；找回已有日块后才能复核联合CI。本轮不新抽样。若corrected仍无稳定优势，保留该结论；若已有联合证据支持，应先经主代理科学主张门禁再改文档。
2. **用现存20261018动作定位事件跳变。** 固定原规则/offset，比较raw/calibrated新增违约的短缺幅度、near-zero残差比例和累计成本贡献。完成标准：人数、原始累计成本/违约精确闭合，解释能覆盖主异常而非挑单例；否则维持UNKNOWN。
3. **给主非劣结果赋予现实单位。** 清楚列共同预测成本、P1额外遥测需求、资源序的工程含义；若没有实际成本/带宽/缺测收益，论文只能称输入约简基准，不得声称现场节约。
4. **不在已用2025上再改策略图谱。** 当前2025已经解封并使用；新增调参只能列探索，任何新确认要另找真实未查看来源。阻止在WTB旧窗口继续扩q/epsilon/网络直到出现赢家。

本报告没有修改科学契约、稿件、原始结果或门禁。门禁通过与否由主代理的整体审计记录，不能把本角色的重汇总完成写成全面科学认证。
