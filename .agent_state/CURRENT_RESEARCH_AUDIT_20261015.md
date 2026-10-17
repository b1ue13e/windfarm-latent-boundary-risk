# 当前创新、实现、对照与复现审计

日期：2026-10-15。范围：本地代码、已归档实验产物、当前论文与复现入口。未执行从原始数据开始的全量训练；未进行新的文献检索，故不认证全球首创性。科学解释不得超过 `docs/SCIENTIFIC_CONTRACT.md`。

## 1. 本轮结论

现有证据支持一个有明确负结果的研究问题：在不同遥测可观测条件下，哪种最简单的备用风险决策足够？尚未建立复杂状态表示的全场成本优势、图结构必要性或普遍跨场泛化优势。不能认证“每个结果都是可独立复现的真实训练直接产物”。非神经基线本身不需要神经训练，其结果应由真实拟合与评估产生；bootstrap 是统计计算产物，应与模型训练产物区分。

## 2. Idea → implementation → evidence

| Idea | 实际实现 | 当前证据边界 |
|---|---|---|
| 遥测新鲜度与通道缺失决定简单模型是否足够 | `windfarm_moe/arrival_feed.py`；`scripts/eval_single_task_dense_phase_scan.py` 中物理条件分箱、验证集校准与延迟/缺失扫描 | 合成应力评估；`artifacts/regime2_recalibration_absorption.csv` 支持再校准降低短缺，不支持现场延迟频率或全行业适用性 |
| 由后果信号恢复工况信息 | `scripts/run_channel_consequence_ablations.py:74` ConsequenceMLP；每通道 latest/mean/std/max 特征，工况交叉熵监督 | `artifacts/channel_consequence_ablations.csv` 是单独 MLP 通道探针，不能称为完整 STGNN 模块消融或无监督物理发现 |
| 状态后验能改善备用决策 | `scripts/test_strong_baseline_closure.py:176` 全局分位数；`:180` 风速10箱；`:195` 后验5箱，各用验证集短缺90%分位数 | 冻结点预测与短缺目标，当前全场后验成本更高；这是一条表征→分箱校准→决策链，不能混写为所有结果均来自同一个端到端 quantile 网络 |
| MoE/图结构是收益来源 | `windfarm_moe/model.py` 提供时空编码、gate、expert、dense实现；另有 dense/routed 与 No-Graph 对照 | 路由必要性未建立；No-Graph 4,865 参数 vs STGQ 110,012 参数且训练不对等，不能做图结构因果归因 |
| 外部场站可迁移 | `scripts/repair_exp01_pitch_withheld_v3.py`，WTB来源权重、双桨距通道屏蔽、场站本地风速基线 | 最新 `artifacts/exp01_pitchmasked_v4/` 是追溯性协议修复，不是新预注册验证；两个场站均未建立正向优势 |

## 3. Baseline

主决策 baseline 为 Site-Local Wind-Speed Binned Quantile：按风速分10箱，在校准集每箱估计冻结短缺目标的0.90分位数。WTB 实现使用0–25 m/s边界并延伸首末箱至无穷，样本不足回退全局分位数（`scripts/test_strong_baseline_closure.py:180`）。

其余对照包括：全局残差分位数（弱对照）；物理条件规则及非神经再校准；Missingness-Aware GBDT；Direct Consequence Quantile MLP；dense/routed及冻结编码器MLP；No-Graph架构探针。零特权实验中的 Privileged STGQ 是不公平的 oracle 参考，不得作为公平 baseline。

## 4. 当前结果：均为已存产物核查，不声称本轮重新训练

PSREI 越低越好；其单位为 kWh，是代理损失，不是货币利润。主评估 h=6 为1小时；Delta=challenger-baseline。

最新 WTB 表：`artifacts/strong_baseline_joint_v2/strong_baseline_closure_summary.csv`。

| 切片 | 风速分箱 PSREI | 后验条件 PSREI | 已存 delta |
|---|---:|---:|---:|
| 全场 | 13,784,320 | 14,307,364 | +523,044 |
| 过渡 | 4,319,319 | 4,432,058 | +112,739 |
| 稳态 | 9,465,001 | 9,875,306 | +410,304 |

表内各列独立取整，稳态显示值相减与delta可差1 kWh。旧科学约束中的切片数值略异；这里明确引用最新重评估产物，不混用版本。

过渡窗口违约率 8.36%→7.24%，备用采购 3,417,020→3,566,261 kWh。只能说增加备用后风险形态改变；不能说成本更低。过渡切片需要已实现的工况变化，是事后诊断，不是已验证的在线切换策略。

`artifacts/strong_baseline_joint_v2/strong_baseline_joint_interaction_v2.json`：交互均值 -297,565 kWh，95%区间 [-651,680,-18,021]，经验 P(interaction≤0)=0.9824；不是经典p值，也不是总体节省。种子202方向相反。

`artifacts/matched_budget/frontier_auc_summary.csv`：本轮从5个Transition行重算bootstrap聚合平均短缺差 +5,233.969389 kWh；4/5种子平均差为正，但只有3/5种子在全部列示预算支持上无有利点。主稿“4/5在所有预算下更差”的表述超出该表。`exact_matched_budget_frontier.csv` 的原样本平均约+5,284.617 kWh，与bootstrap均值是不同估计量（生成器 `scripts/run_matched_budget_frontier.py:662`、`:679`），不能将二者差别指认为伪造。

最新外部结果：`artifacts/exp01_pitchmasked_v4/exp01_pitchmasked_v3_joint_statistics.csv`，h=6：
- Penmanshiel：Delta -315,399.62，95%区间 [-1,590,023.53,+970,006.32] kWh；方向不确定。
- Kelmarsh：Delta +352,433.95，95%区间 [+59,969.70,+736,901.18] kWh；成本惩罚。
- 以上统计是种子×日块重抽样；bootstrap方向概率不能称为双侧p值。

## 5. 消融及其解释

1. 通道：C1全通道NMI=0.22586；C2有功功率NMI=0.46124、ARI=0.64692、过渡召回0.62863；C9功率+尾流NMI=0.46272；C6尾流单独NMI=0。来源 `artifacts/channel_consequence_ablations.csv`。说明该探针中功率信息突出，未建立尾流的必要增量。其成本差参考为代码181–182行硬编码历史数值，不能直接取代匹配的强baseline闭环。
2. 监督：lambda_align=0 vs 5000；本轮从 `artifacts/clean_privileged_supervision_ablation.csv` 重算NMI均值0.24014→0.81892、ARI 0.19780→0.88933。h=6成本均值15,437,653.8→15,125,696.6，但不能把点估计当显著收益；配对区间跨零（`docs/PRIVILEGED_SUPERVISION_ABLATION.md`）。两组均使用历史桨距输入，去掉alignment不等于去掉历史桨距。
3. 路由：dense/routed配对区间跨零（`artifacts/verified_tables/table4_h1_paired.md`），支持“未证明路由必要”，不支持数学等价。
4. 图结构：容量与训练条件不匹配，见 `docs/NO_GRAPH_CONTROL_AUDIT.md`；不能证明空间图是原因。
5. 决策：matched reserve budget、rho敏感性、全局/风速/后验/混合策略对照分开检验分配效果与备用量效应；相同预算下平均短缺未获改善。
6. 完全无历史桨距：EXP02不同于lambda消融。`docs/ZERO_PRIVILEGED_SUPERVISION_REPORT.md` 和 `artifacts/zero_privileged_supervision_benchmark.csv` 报告主挑战者eps50在h=6平均Delta约+3.435M kWh，未建立稳定优势；原报告的虚假两层bootstrap措辞已修订，不能当作完整原生时间块不确定性闭环。

## 6. 尚不满足用户严格复现要求之处

- 本轮没有从原始SCADA重新训练全部模型、消融和种子；既有CSV及SHA256只证明文件存在/一致，不能单独证明历史训练来源真实。
- `scripts/run_channel_consequence_ablations.py` 有真实优化代码，但仅汇总输出，不能由脚本存在推定每个历史结果都已具备权重、日志、逐样本预测完整证据链。
- EXP03 trace仅归档小样本，`missing_mask.json`是48个false；不能复算完整延迟×种子×horizon输入历史。详见 registry EXP03 F4及 `docs/EXP03_INVALIDATION_NOTICE.md`。
- 当前稿件与补充稿、旧manifest/数值检查之间存在版本差异，不能将任意历史PASS当作当前科学内容认证。
- Exp-C：科学反证审查员本轮直接从缓存按正式窗口anchors复算639,378个有效单元、0个错误。它验证的是当前标签/掩码下风速规则可完全分离标签，进一步削弱“隐藏状态必须靠复杂网络识别”的动机；并不验证现实中的全部运行状态可被该规则完全识别。命令与缓存见本轮 `FALSIFICATION_REPORT.md`。
- 独立复核实际执行 `python main.py external_cache --help` 返回exit 1（无此子命令）；文档所列外部预处理命令不可运行，实际CLI为 `external-wind-preprocess --farm`。文档宣称的WTB默认缓存位置也与CLI默认值不符，且没有完整5种子重训练矩阵。来源 `docs/DATA_AVAILABILITY_AND_PREPROCESSING.md:68`、`:75`，`main.py:195`、`windfarm_moe/config.py:94`。
- 独立复核载入5个 `strictmask_ablation_rerun_wtb_full/wtb_bal_align_force_seed201..205/` 权重与training_summary，存在非空loss历史且seed/WTB元数据匹配。这是档案自洽证据，不等于全部实验已由独立raw-data重训证明。
- 论文的“首创性”未进行新的原始文献核验；这里只判断仓库内证据支持哪些贡献。

达到用户要求需为每个表/图冻结并串联：原始数据哈希→预处理/切分→代码commit→完整命令/环境/随机种子→训练日志/权重→逐样本预测/掩码→评估与统计→论文数值；再从隔离干净环境运行全流程，公布逐项复现误差容限。当前结论是尚未认证，不能承诺任意硬件逐bit一致。

## 7. 本轮直接验证记录

- `python scripts/audit_phase2_retrospective.py`：2026-10-15实际执行，exit 0，C01–C06 PASS。覆盖5个WTB checkpoint元数据、桨距屏蔽代码与断言、样本对齐、EXP01 v4统计、原生日块bootstrap重算、历史产物保留；不覆盖全量重训练。
- Python/pandas读取真实CSV并重算监督均值和matched-budget均值：exit 0，数值见上文。
- 科学反证、独立证据复核及仓库gate结果以本轮追加的 `.agent_state/FALSIFICATION_REPORT.md`、`AUDIT_REPORT.md`、`REVIEW_REPORT.md`、`GATE_REPORT.md` 为准。审计通过不等于科学包可投稿或完全复现。

本轮仓库门禁实际执行：`python .agents/scripts/verify_gate.py`，exit 0，五项必需命令均exit 0。独立科学反证仍为当前科学包认证FAIL；门禁仅通过其现有检查范围，不能覆盖或抹除上述阻断项。本轮仅追加审计与状态文件，没有修改实现、实验结果、论文或科学约束。
