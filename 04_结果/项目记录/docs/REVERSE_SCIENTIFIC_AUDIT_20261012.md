# 科研项目逆向审计（2026-10-12）

**对象：** `E:\论文3` 当前仓库与 `revision_topjournal_reconstruction` 分支  
**阶段：** 第一阶段只读科学审计；未改动正式实验结果、`docs/SCIENTIFIC_CONTRACT.md` 或 GitHub main  
**证据口径：** `VERIFIED` 为文件、代码、工件、命令输出或权威来源直接支持；`INFERRED` 为由已验证证据作出的合理推断；`UNKNOWN` 为当前证据不足。  
**审计决定：** **REVISE（投稿硬停）**。项目主线无需 Stop，但在下列硬缺陷关闭前，不得宣称“科学闭环”“最终可投稿”或复用旧 PASS。

## 0. 审计结论摘要

项目最可守、也最有价值的主线不是新架构，而是一个负结果与边界结果：

> 在同一到达时刻信息集下，运行状态的可恢复性不推出备用决策优越性；强局部条件分位数往往是更小、更稳的充分决策函数。

这一主线有真实工件支撑，尤其是 WTB 强基线闭环和 matched-budget falsification。但当前仓库把三种状态混在一起：

1. 2026-09-29 以前的主稿与旧验证门；
2. 2026-10-12 的 EXP-01 corrected v2、EXP-02、EXP-03；
3. 仍未同步或已被新结果推翻的旧日志、旧矩阵与旧 PASS 报告。

最严重的问题是：EXP-03 不满足其声称的信息对称与固定人口，EXP-02 的自动统计判决方向和角色标签有错误，当前主稿把来自 60 分钟 Delay-6 的 55.3% 归到了 10--30 分钟，并继续突出外场相对弱 global quantile 的旧收益。

## 1. 可直接复用的已有成果

| 成果 | 状态 | 可复用边界 | 证据 |
|---|---|---|---|
| 冻结的科学问题、same-information 规则与 claim ceiling | VERIFIED | 继续作为全项目解释上限；不得为结果过门而修改 | `docs/SCIENTIFIC_CONTRACT.md:9-38,99-167` |
| 固定点预测、固定 shortfall target 与相同信息集设计 | VERIFIED | WTB 主实验可继续使用；外场必须使用各场站独立 frozen point forecast | `docs/FIXED_TARGET_CONTRACT.md`; `docs/INFORMATION_SET_CONTRACT.md`; `docs/EXPERIMENT_AUDIT.md:8-20` |
| 新鲜遥测下物理规则在 WTB 边界带最低已评估 PSREI | VERIFIED，限域 | 只能写成 WTB、边界带、冻结协议内的最优已评估方法；13,883 是 turbine-time cells，不是独立事件 | `paper_tste_ieee.md:285-370`; `docs/SCIENTIFIC_CONTRACT.md:103` |
| 60 分钟合成 Delay-6 下 matched recalibration 吸收 55.3% shortage loss | VERIFIED，但正文时间条件错误 | 可写为 60 分钟合成压力端点；不能归入 10--30 分钟 | `artifacts/ARTIFACT_MANIFEST.json:69-71`; `docs/TSTE_OPERATIONAL_RELEVANCE_PREREGISTRATION.md:24`; `paper_tste_ieee.md:393-409` |
| 有功功率是 privileged-training recoverability 的主要 mediator | VERIFIED，受限 | 可写“active-power consequence signature”；不能写复杂时空机制必要 | `artifacts/channel_consequence_ablations.csv`; `docs/ACTIVE_POWER_IDENTIFIABILITY_AUDIT.md:25-38`; `docs/SCIENTIFIC_CONTRACT.md:43-55` |
| 强 wind-speed-conditioned quantile 的 plant-wide / steady 优势 | VERIFIED | 可直接保留负结果：posterior 全场 +523,044 kWh、steady 约 +410k kWh | `artifacts/strong_baseline_closure_summary.csv`; `docs/SCIENTIFIC_CONTRACT.md:57-82` |
| matched-budget 下未建立 posterior allocation advantage | VERIFIED | 可写 4/5 seeds 更差、平均 uncovered shortage 约 +5.24k kWh；不得升级为所有条件下的普遍定律 | `artifacts/matched_budget/exact_matched_budget_frontier.csv`; `docs/MATCHED_BUDGET_FINAL_AUDIT.md:20-30` |
| MoE routing 非必要 | VERIFIED 的负结果 | 可保留为架构消融；不可再宣传路由创新 | `artifacts/factorial_boundary_ablation_summary.csv`; `docs/SCIENTIFIC_CONTRACT.md:111` |
| EXP-01 corrected v2 的 transferred-STGQ 外场负结果 | VERIFIED 为描述性 seed-level 事实 | Penmanshiel h=6 五个 seed 差分均为正；aggregate inference 需重算 | `artifacts/external_matched_control_benchmark.csv`; `docs/EXPERIMENT_AUDIT.md:12-75`; `docs/EXPERIMENT_REGISTRY.md:341-360` |

## 2. 缺失的科学证据

1. **新实验的联合不确定性。** EXP-01/02/03 把每个 seed 的 bootstrap 概率、CI 端点或 p 字段取算术平均；没有一次同时覆盖“训练随机性 × 日级时间相关性”的联合推断。`VERIFIED`：`scripts/run_exp01_matched_control_benchmark.py:691-705`、`scripts/run_exp02_zero_privileged_supervision.py:773-788`、`scripts/run_exp03_async_benchmark.py:511-523`。
2. **严格相同信息集的异步实验。** EXP-03 没有延迟真实字段 `Patv_hist`，挑战者读到了新鲜的主导 mediator，而基线只读 delayed Wspd。`VERIFIED`：`artifacts/cache_strictmask_trainweights/wtb_245d/metadata.json:5-16`、`scripts/run_exp03_async_benchmark.py:132-145,310,340-348,406-445`。
3. **固定人口或透明 missingness 处理。** EXP-03 的有效人口从 $\tau=0$ 的 100% 降到 $\tau=6$ 的 2.47%，总 PSREI 随样本删除坍缩；未报告 `n_cells`、drop fraction 和 per-cell metric。只读复算命令记录在本审计证据台账。
4. **可验证的全量 packet provenance。** 当前 hash 只对应首个 delay 的 node-0、前 144 步样本；`missing_mask.json` 是 `t % 5 != 0` 的人工样例。`VERIFIED`：`scripts/run_exp03_async_benchmark.py:413-414,474-493`。
5. **零特权协议的正确统计和稳定性。** EXP-02 h=6 均值主要由 Seed 201 的 +17.41M 极端失败驱动；报告没有把 catastrophic-run rate 作为一等结果。`VERIFIED`：`artifacts/zero_privileged_supervision_benchmark.csv`。
6. **外场图结构的因果必要性。** No-Graph control 只有 4,865 参数，STGQ 有 110,012 参数，且 No-Graph 从 validation 子集训练；不是容量、优化预算或训练数据等价对照。`VERIFIED`：`docs/NO_GRAPH_CONTROL_AUDIT.md:23-27,48-58`; `docs/EXPERIMENT_AUDIT.md:33-48`。
7. **可部署的 transition policy。** 当前 transition slice 由真实未来状态变化向前后扩展 3 步定义，是 post-hoc oracle slice，不是到达时刻可用的在线选择器。`VERIFIED`：`scripts/test_strong_baseline_closure.py:121-139`; `scripts/run_decision_mediation_test.py:130-146`。
8. **现场分钟级延迟与 pitch 屏蔽的频率证据。** Ullah et al. 2022 支持通信连通性与丢包动机，但不支持 10--60 分钟排队延迟常态或当前 Markov 参数；“aggregator firewall frequently restricts pitch”仍为 `UNKNOWN`。`paper_tste_ieee.md:81,263`; `docs/REVERSE_AUDIT_LITERATURE_MATRIX_20261012.csv`。
9. **覆盖新实验的控制面。** 审计开始时，`REVIEW_REPORT.md` 只覆盖 T72--T78、`FALSIFICATION_REPORT.md` 日期为 2026-09-26；本轮 RA05/RA06 已分别更新为 2026-10-12 的 scientific `FAIL` 与 audit-integrity `PASS_WITH_BLOCKERS`。但 `.agents/verification_manifest.json` 和 `artifacts/ARTIFACT_MANIFEST.json` 仍早于三项新实验，因此旧/当前 procedural gate 仍不能把 EXP-01/02/03 的科学状态转成 PASS。`VERIFIED`：`.agent_state/FALSIFICATION_REPORT.md`; `.agent_state/REVIEW_REPORT.md`; `.agents/verification_manifest.json`; `artifacts/ARTIFACT_MANIFEST.json`。

## 3. 可能的致命缺陷

### F1 — EXP-03 信息不对称，主结果不可用于科学推断

`simulate_asynchronous_scada_stream()` 的延迟列表是 `Wspd, Patv, Etmp, Itmp, Prtv`，但实际缓存字段是 `Patv_hist`。脚本在模型特征构造时正确回退到 `Patv_hist`，模拟器却没有；因此 active power 保持新鲜。由于 active power 已被旧实验识别为主要 mediator，这不是小误差，而是核心比较器信息集违规。

- 证据：`scripts/run_exp03_async_benchmark.py:132-145,310,340-348,406-445`
- 证据：`artifacts/cache_strictmask_trainweights/wtb_245d/metadata.json:5-16`
- 结论：`VERIFIED`，已撤回 EXP-03 当前 verdict 并标记为 `INVALIDATED`；历史结果仅保留为 provenance，不得用于科学推断。修复后的模拟器回归测试覆盖 `Patv_hist`，但不使旧运行结果恢复有效。

### F2 — EXP-03 proxy supervision 在标准化尺度上使用物理阈值，代理标签全为零

脚本直接用标准化后的 `Wspd` 与 `Patv_hist` 同 10.5 m/s 和 1450 kW 比较。只读复算得到 validation proxy positives 为 **0 / 570,974**；Wspd 标准化范围约 [-1.55, 4.96]，Patv_hist 范围约 [-0.91, 2.84]。因此所谓 zero-privileged proxy head 实际退化为全零分类，不等同于 EXP-02 模型。

- 证据：`scripts/run_exp03_async_benchmark.py:335-371`
- 证据：`artifacts/cache_strictmask_trainweights/wtb_245d/metadata.json` 的 `feature_stats`
- 结论：`VERIFIED`，EXP-03 challenger 身份被错误描述。

### F3 — EXP-03 曲线由人口坍缩驱动，trace/mask 证据不真实覆盖执行网格

有效率按实际 runner 只读复算为：1.0000、0.9998、0.9812、0.8135、0.4344、0.1326、0.0247。h=6 baseline total PSREI 同时从约 14.80M 降到 0.37M。当前曲线不是同一 estimand population 上的 latency response。并且 trace hash 只覆盖 $\tau=0$ 小样本，missing mask 是人工占位。

- 证据：`scripts/run_exp03_async_benchmark.py:135-177,402-445,474-493`
- 证据：`artifacts/exp03_async/psrei_vs_delay.csv`
- 证据：`artifacts/exp03_async/missing_mask.json`
- 结论：`VERIFIED`，registry 所称 trace integrity 与固定比较不成立。

### F4 — EXP-02 自动 verdict 与模型角色逻辑错误

bootstrap 字段 `p_val_delta_psrei` 实际定义为 $P(\Delta \le 0)$，是“挑战者不更差/更优”的经验概率，不是常规 p-value；报告生成器却要求 `delta < 0` 同时 `p < .05` 才判优势，方向相反。角色判断先执行 `"Privileged" in model_name`，所以 `Zero-Privileged Challenger` 全部被标为 Oracle。

- 证据：`scripts/run_exp02_zero_privileged_supervision.py:303-312,717-729,773-792`
- 证据：`artifacts/zero_privileged_supervision_benchmark.csv` 的 `model_role`
- 结论：`VERIFIED`，可保留“未观察到稳定优势”，但不能保留“deficit established”的当前自动判决。

### F5 — 当前主稿存在 headline 时间归因错误与外场选择性弱比较器

摘要、引言和 Discussion 把 55.3% 写成 10--30 分钟结果，真实 127.6→57.0 MWh 来自 60 分钟 Delay-6。主稿继续突出 Penmanshiel 相对 global quantile 的 -2.14M，而 corrected v2 相对 Site-Local Wspd-Bins 为 +5.322M penalty。

- 证据：`paper_tste_ieee.md:68,97,377-409,451-456`
- 证据：`artifacts/ARTIFACT_MANIFEST.json:69-71`
- 证据：`docs/EXPERIMENT_REGISTRY.md:341-360`
- 结论：`VERIFIED`，当前 PDF 不应投稿。

> **F5 关闭记录（2026-10-13）。** 上述原文保留为审计发现的历史记录。修复时做了逆向取证，发现本条的诊断本身**不完整**：55.3% 不只是时间归因错误，而是**指标定义错误**。旧 C05 计算 `1 - phys_clean_shortage(no_pitch)/phys_clean_shortage(all)`（lag=6），分子分母**都是未校准物理**，分母取 `all` 通道、分子取**扣留 pitch** 通道——比值跨了 `channel_mode`，量的是 Regime 3 的扣留效应，重校准从未参与运算。因此 `127.6→57.0 MWh` 也不是"60 分钟的真实重校准值"，而是 60 分钟 `no_pitch` **未校准**短缺；该令牌在任何 τ 下都没有有效解释。
>
> 真实 Regime-2 量应在 `channel_mode='all'` 内部、同 lag 配对：τ=10/20/30 min 吸收 **36.28%/53.89%/61.72%**，τ=60 端点为 **66.46%**（`127.552 → 42.787 MWh`，违约 9.46%）。工件 `artifacts/regime2-recalibration-absorption`（v1），由 `scripts/regenerate_regime2_absorption.py` 生成并带断言；`verify_replication.py` 的 C05/C05b/C06/C06b 已重定义，C19 令牌数由 73 扩至 77。
>
> 第二个缺陷（选择性弱比较器）已按 corrected v2 换为强基线：主稿、图 5 标题、Discussion 第 5 条、Limitations 第 4 条一律采用 **Site-Local Wspd-Bins** 为参照（Penmanshiel h=6 +5,321,915 kWh，p=0.003；Kelmarsh h=6 +435,684 kWh，p=0.196），结论为**外场不存在正向决策价值**。global quantile 旧行按负结果保留原则不删除，在补充材料 Table A8/A8b 标注 `superseded`，并新增权威 Table A8c。
>
> 验证：`verify_replication.py` = FULLY_REPRODUCIBLE（21/21，exit 0）；数字一致性 77/77；`verify_gate.py` PASS；`verify_final_pdf_integrity.py` PASS；主稿 10.0 页、补充材料 46 页。提交 `c7e008b8`、`054872aa`、`2077db8c`。**F5 已关闭。**

### F6 — 旧日志、旧审计与控制面可重新污染结论

`experiments/E01/log.md` 仍把 v1 +448k/+48.5k 写成“跨场站普遍规律”；`docs/NO_GRAPH_CONTROL_AUDIT.md` 仍使用 v1 数值；registry 同时保留 `EXP-01 completed` 和语义重复的 `EXP-Q2-003 proposed/blocked`。旧 gate 只检查旧 19 个 claim，不检查 EXP-01 v2、EXP-02、EXP-03。

- 证据：`experiments/E01/log.md`
- 证据：`docs/NO_GRAPH_CONTROL_AUDIT.md:56`
- 证据：`docs/EXPERIMENT_REGISTRY.md:300-391`
- 证据：`.agents/verification_manifest.json`
- 结论：`VERIFIED`，旧 PASS 不能作为本轮闭环证据。

### F7 — 文献矩阵和“文献原文”资产不可作为可靠证据层

旧 `literature/literature_matrix.csv` 至少 15 行存在 DOI--标题错配；`literature/top_journal_papers` 51 个 PDF 中，40 个首页是仓库生成的 `Literature Benchmark Brief`，不是论文原文。Mimir 报告还把 arXiv:2405.01234 错写成风电论文；该编号实际是交换环上的 Hermite rings 数学论文。

- 证据：`literature/literature_matrix.csv:2,10-18,20,25,27-33`
- 证据：`docs/MIMIR_INGESTION_AND_AUDIT_REPORT.md:39-45,105`
- 外部核验：`https://arxiv.org/abs/2405.01234`
- 结论：`VERIFIED`，旧 literature matrix 和 Mimir Literature GO 不可复用。

### 重大但非单独硬停的问题

- **直接 baseline 清单不闭合：** 文档反复声称 B0--B5，但当前 `run_direct_quantile_baselines.py` 与结果 CSV 只有 B0--B4；旧 gate 只检查 B3 在 h=6 是否失败，没有检查 baseline 集合完整性。
- **外场主对照信息量不完全匹配：** EXP-01 primary baseline 只用 Wspd，transferred challenger 使用多通道 consequence；同信息 No-Graph 又只有 4,865 参数、从 validation 子集训练。`EXP-Q2-003` 仍在 registry 中标为 BLOCKED。
- **EXP-02 的“matched-budget”命名不成立：** 代码是在相同 quantile/target 下比较 PSREI，并未像 matched-budget frontier 那样强制 $\Delta R=0$。
- **预冻结链不够强：** EXP-01 的脚本、结果和 completed registry 同一提交；h=6 主终点在看到 v1 后加入；v2 更换 point forecast 后沿用同一 Experiment ID。EXP-02 主要协议与 observed results 同一提交。它们可称 protocol correction / exploratory closure，不应追溯包装成干净 confirmatory preregistration。
- **环境与发布未覆盖新实验：** `requirements.txt` 是宽松版本范围而非 lock；公开 tag/release `tste-submission-v1.0` 早于 EXP-01/02/03；EXP-03 结果文件被 `.gitignore` 排除。

## 4. Claim–Evidence 逆向映射

| Claim | 状态 | 最强反证/边界 | 允许措辞 |
|---|---|---|---|
| 商业 SCADA 普遍有 10--60 分钟延迟且 aggregator 常屏蔽 pitch | UNKNOWN / 过强 | 当前文献只支持通信风险与 10 分钟 reporting，不支持该频率和分布 | “合成压力场景与潜在寄存器不可用性” |
| 新鲜遥测下物理规则最低成本 | VERIFIED，限 WTB 边界带 | 只占约 2.4% turbine-time cells，不是全场普遍排序 | “在 WTB 既定边界带和冻结协议内最低已评估 PSREI” |
| 10--30 分钟重校准吸收 55.3% | REFUTED AS WRITTEN | 55.3% 对应 60 分钟 Delay-6 | “在 60 分钟合成压力端点吸收 55.3%” |
| pitch withheld 后 consequence signals 保留状态信息 | VERIFIED，privileged-training setting | 主要是 contemporaneous active-power direct readout | “active-power signature retains boundary information” |
| boundary posterior 已精确校准 | PARTIAL | bulk ECE 通过，但 tail MCE 约 0.75--0.85 | “bulk-calibrated boundary score/posterior with tail-bin dispersion” |
| learned representation 有独立 plant-wide 决策价值 | REFUTED | wind-speed bins 低 523,044 kWh | 明确保留负结果 |
| posterior 在 transition 具有可部署优势 | NOT ESTABLISHED | slice 是未来真值定义的 post-hoc oracle；matched budget 无 allocation advantage | “事后 transition slice 中观察到风险形状差异” |
| MoE routing 是机制 | REFUTED | dense/modular parity，p=.380 | “routing complexity is not the operative source” |
| Penmanshiel 外场 STGQ 有增益 | SUPERSEDED for strong comparator | v2 transferred-STGQ vs local bins +5.322M penalty | “相对 global quantile 的旧差分不是独立价值；强局部基线下转移失败” |
| 场站差异由空间冗余、尾流或 turbine count 解释 | UNKNOWN | no-graph 不容量匹配，站点数太少，不能识别 moderator | “存在场站异质性；调节因素尚未识别” |
| zero-privileged learning deficit established | INVALID CURRENT VERDICT | p 方向、角色标签、seed instability | “当前实现未显示一致稳健优势；待正确推断重判” |
| async delay 下复杂表示无 hedge | INVALID | 新鲜 Patv_hist、全零 proxy、人口坍缩、伪 mask/partial trace | 不得作科学结论，需重跑 |
| minimum-sufficient hierarchy 是普遍定律 | PARTIAL / CONDITIONAL | 仅特定站点与协议；外部/异步仍未闭合 | “在已评估信息条件和站点内的条件性 deployment map” |

## 5. 文献与创新性逆向审计

完整矩阵见 `docs/REVERSE_AUDIT_LITERATURE_MATRIX_20261012.csv`。宽口径创新性受到三条直接威胁：

1. **Bel-Hadj et al. 2026** 已在 44 台风机上用无 SCADA 训练的高频加速度恢复运行状态、pitch 与 downstream fatigue utility。一般性的“由替代后果信号恢复运行状态”不新。
2. **Wang, Wang & Ma 2026** 已组合动态有向 wake graph、多步 quantile 与 CQR。graph + physics + quantile + calibration 不新。
3. **Wang & Wang 2026** 已组合 regime-aware quantile、reserve-relevant shortfall、CQR 与跨场测试。regime-conditioned reserve-risk calibration 不新。

另外，Zhao et al. 2026 几乎逐项覆盖 dynamic graph + physics/data MoE。项目可守的新意只能收窄为：

> pitch-hidden arrival-time information boundary + same-information simple baseline + recoverability/decision separation + matched-budget negative/null closure。

## 6. 最值得补做的三个实验

### E1 — EXP-03-R：固定人口、真实字段、全量可审计的异步重跑

- 新建 Experiment ID，不覆盖 EXP-03。
- 延迟模型实际使用的全部输入字段，包括 `Patv_hist`；先反标准化或完全在标准化阈值上定义 proxy。
- 每个 delay / simulator seed 保存全量 trace hash、channel mask、drop/late fraction。
- 主 estimand 使用固定 dispatch anchors；同时报告 coverage、per-cell PSREI 与 total PSREI。
- 联合推断应先计算 day-level paired effect，再对 day × model seed / simulator seed 做明确的层级或嵌套 bootstrap。
- **反证条件：** 若 corrected challenger 在固定人口和同一信息集下不优于 Wspd-Bins，则删除“representation buffers latency”与 async decision-value 叙事，保留负结果。

### E2 — 外场 confirmatory graph-vs-local-baseline 实验

- 新建 Experiment ID；当前 Fine-tuned STGQ 结果只能视为 exploratory，因为 Penmanshiel 4/5 seeds 获益、1 seed 灾难性失败。
- Primary challenger 改为 site-local fine-tuned graph；对照为相同训练样本、参数预算、优化预算的 no-graph model，以及 Site-Local Wspd-Bins。
- 冻结独立 site-specific point forecast、primary h=6、每站单独 estimand，不做有利站点合并。
- 报告 median、seed failure rate、calibration、compute 与 matched-budget effect。
- **反证条件：** 若 graph 在 Penmanshiel/Kelmarsh 均不能稳定战胜 matched no-graph/local bins，删除空间机制与 external decision-value 贡献。

### E3 — Ex-ante transition decision experiment

- 禁止用未来真实 regime change 构造部署选择器。
- 仅用到达时刻可用特征产生在线 transition alarm；alarm 规则和阈值只在 validation 冻结。
- 在同一 point forecast、shortfall target、reserve budget 下比较 alarm-gated posterior 与 Site-Local Wspd-Bins。
- 在 WTB、Penmanshiel、Kelmarsh 分站报告，不做 pooled favorable headline。
- **反证条件：** 若 ex-ante alarm 无增量或只在 oracle slice 有效，把 transition-localized finding 降级为机制诊断，不再称部署策略。

> EXP-02-R 排在第四位：只有在论文继续保留“pitch 从未记录”主张时才重跑。否则应先撤销错误自动 verdict、把该分支隔离为未闭合探索。

## 7. Go / Revise / Stop

### 决策：REVISE（附投稿硬停）

**不是 Go：** 当前主稿有 headline 条件错误、遗漏强 comparator 的新结果；EXP-02/03 结论无效或不可用；旧验证门没有覆盖新证据；文献资产存在系统性错配。

**不是 Stop：** WTB 上的强基线闭环、matched-budget falsification、active-power mediator 和 MoE negative result 仍构成可发表的、诚实的边界性贡献。项目应从“新模型胜出”进一步收缩为“何时复杂表示不值得，以及如何分离状态可恢复性与决策充分性”的负结果论文。

**转向条件：**

- 若 E1 和 E3 均失败：转为 observability / falsification / minimum-sufficiency audit paper，删除 deployable latent-transition policy。
- 若 E2 失败：删除 cross-site graph value 与 wake/spatial moderator 贡献，只保留外场负验证。
- 若更新后的文献对比仍无法说明本项目在 matched-information decision falsification 上的差异：停止当前架构论文路线，改投方法论审计/负结果定位，而非继续添加模块。

## 8. /grill-me：审稿人最可能追问的十个问题

1. 55.3% 明明来自 60 分钟 Delay-6，为什么摘要写成 10--30 分钟？
2. 物理规则只在 13,883 个 boundary cells 上最低成本，为什么称为一般性的 minimum sufficient model？
3. active power AUROC=.988 是潜状态恢复，还是额定功率钳位的近直接读出？
4. 哪个已核验现场来源证明 pitch registers 在 aggregator/VPP 场景中“frequently restricted”？
5. 为什么正文突出 Penmanshiel 相对 global quantile 的 -2.14M，而不报告 corrected v2 相对 local bins 的 +5.322M？
6. 为什么把五个 seed 的 bootstrap CI 和概率直接平均？
7. EXP-02 中 $p=P(\Delta\le0)$，为何 verdict 反而要求有利的 $\Delta<0$ 与 $p<.05$？
8. EXP-03 为什么给 challenger 新鲜 `Patv_hist`，却称相同到达信息集？
9. 为什么 archived `missing_mask.json` 不是实际 mask，trace hash 又只覆盖 $\tau=0$ 小样本？
10. transition window 使用未来真值向前扩 3 步；真实部署在事件发生前如何知道自己处于该 slice？

## 9. 审计边界与未修改项

- 未修改 `paper_tste_ieee.md`、`paper_tste_supplementary.md`、任何正式实验 CSV/NPZ/JSON、`docs/SCIENTIFIC_CONTRACT.md` 或 GitHub main。
- 未把任何现有实验追溯性地改称为 preregistered。Git 历史显示 EXP-01 完成记录与实验条目同一提交，endpoint hierarchy 在看过 v1 后加入；因此 corrected v2 只能称 protocol correction，不称独立 confirmatory preregistration。
- 外部文献结论仅使用已核验 DOI/出版社或作者版本；无法核验的条目标记 UNKNOWN。

## 10. 独立终审

- Scientific falsifier：`.agent_state/FALSIFICATION_REPORT.md`，结论 **FAIL FOR CURRENT SUBMISSION; REVISE THE PROJECT**。
- Independent evidence review：`.agent_state/REVIEW_REPORT.md`，结论 **PASS_WITH_BLOCKERS for audit integrity**；该 PASS 仅证明本审计证据链完整，不代表论文或 EXP-01/02/03 科学通过。
