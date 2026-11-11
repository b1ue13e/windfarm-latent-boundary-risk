# 物理规则、遥测退化、外场与运行支线贡献盘点

审计日期：2026-10-20。模式：experiment-to-paper / audit。仅读取已有表格、JSON、源码、协议和审计记录，未加载模型、运行推理、拟合、校准、统计重算、重采样、仿真、下载测量或访问远端。没有改动原结果、阈值、论文、科学契约或执行队列；本文件不宣布新的科研里程碑。

已读AGENTS、SCIENTIFIC_CONTRACT、PROJECT历史、EXPERIMENT_REGISTRY及experiment-to-paper证据规范。本支线的精确主张表为`OPERATIONAL_CLAIMS.csv`。数字均为原文件已存值或逐种子原值展示，没有新估计均值、差分、区间或显著性。文献新颖性本轮未检索，统一为UNKNOWN。

## 结论边界

**VERIFIED：Wind Energy V2仅采用20261019信息格/独立年份主线，确实省略了大量物理规则、延迟重校准、异步、外场表征、全场聚合、价格、BESS、早期预警和ERA5实验。省略不等于这些实验没有完成，也不等于它们没有知识内容。**V2正文与补充仅在后者272行笼统说明旧graph/recovery/MoE分支未用于本文主比较；它不是所有历史分支的实验审计。V2有关特定接口、实际资源净收益与业务接受度未闭合的判断，不能直接传播为整个项目所有问题无效。

**VERIFIED：这些支线也不能整体恢复为旧版部署规律。**部分旧主张有硬错误；部分只是弱对照、统计不确定、缺运行来源或缺独立确认；另有明确的局部阳性和可解释负结果。下文分别记录。科学契约未在本轮修订；契约与后续coverage的差异列为待裁决，不擅自升级或撤回契约。

## A. 新鲜物理规则与重校准

### OP01 新鲜遥测下的物理备用规则：有历史局部阳性，现代共同目标版本未给出统一胜出

- 原表：`artifacts/clean_evidence_v2/risk_layer_benchmark/h1_lead1/cross_seed_aggregate.csv`第3行（两行表头之后）`clean,1,Continuous Physical Quantile`，PSREI 589534.8875、std77390.4726；同组Joint Dense Head686555.2375。h6对应目录`h6_lead6`，`clean,6,Continuous Physical Quantile`881367.3、std95741.4693、V.06812649；Dense991180.775。逐种子原表为各目录`results_by_seed.csv`，seeds201–205。
- 范围：WTB boundary band；h1原201种子`n_events=13883`。旧报告将它与全场15M成本相减是不合法的。`docs/FAILURE_FALLBACK_BOUNDARY.md`的全域部署要求及8.1%推广不能由此支持。
- 当前状态：`raw_replay_20261015_v2/coverage.json`将两组旧clean结果记WITHDRAWN、替代为corrected four-condition V2；`REPLAY_CLAIM_DISPOSITION_20261015.md`说明旧phase没有固定共同目标/边界人口。这阻止其作为现行确认结果，不使原表局部比较变成不存在。
- 修正结果：`raw_replay_20261015_v2/downstream_recovery_v1_attempt1/phase_aggregate/phase_scan_results_by_seed.csv`中`seed201,lead_step0,lag_steps0,all`：physics340506.4079、Dense308693.0982；`seed204`同格：physics905387.1073、Dense986609.1977。原文件有五种子×3lead×5lag×2channel共150格；本轮不计算新平均。不同种子有相反排序，不能写物理在所有种子/所有比较中最强。
- 可保留知识：新鲜物理输入与简单条件分位数是必须纳入的强候选；历史boundary子任务确有简单物理规则胜过复杂网络的阳性。全场固定目标下统一物理胜出、真实部署优先级仍未建立。来源资格与历史/修正版本不能混写。

### OP02 Regime-2 absorption：数值真实，局部配对身份应保留；不是现代共同目标的延迟定律

- 原始可读派生表：`artifacts/regime2-recalibration-absorption/v1/regime2_recalibration_absorption.csv`的`tau_min=10/20/30/60,channel_mode=all`，shortage依次37.6538→23.9912、51.8423→23.9025、69.0689→26.4428、127.552→42.7873MWh；原表absorption36.28/53.89/61.72/66.46%，60min V.0946。表有cost与violation而非只存percent。
- `artifact.json`、`provenance.md`绑定生成入口`regenerate_regime2_absorption.py`、输入`single_task_dense_vs_multitask_moe_ablation.csv` SHA256 `dfbdd3d7884337ba8d0a1ed5fbc760463cd95752e984d60e2edb0c43533b50d2`。这是lead_step0、同channel、同lag的物理校准对照。旧55.3%确是跨channel的pitch-withholding比值，不能恢复为校准收益。
- 科学契约§3仍给这些数VERIFIED，后续claim disposition则说旧跨延迟曲线混目标/移动边界，**同condition物理重校准只保留局部范围**。本盘点保留这层身份，不把它当共同target跨delay单调因果结论，也不把coverage的旧表WITHDRAWN扩大成校准完全无用。
- 可保留知识：历史可观测条件内的低复杂度recalibration能改变风险与成本；实际净收益依赖目标、校准人口、信息时钟与风险资格，旧值不可替换新共同目标结果。

### OP03 修正共同目标phase：有正有负，不是“所有延迟信息无效”

- 原表同OP01 corrected CSV，`target_protocol=canonical-frozen-reference-v1`；`aggregation_receipt.json`列五个phase执行收据、`rows=150`、`abstention_rows=210`、`status=EXECUTED_PENDING_NUMERICAL_AUDIT`、`scientific_completion=false`。
- 直接原行：`201,lead0,lag6,all,n=13883`shortage13.7497569→12.4578200MWh，但cost356440.5007→383277.2550；`202`同格shortage14.9687123→15.1625062。`201,lead5,lag6,all`shortage14.5814934→15.9765790、cost674731.0100→677076.2868；`203,lead5`cost1059071.0547→1055587.6506且shortage24.4609200→25.6085337。不得把一种指标收益替换另一种。
- 状态：执行与收据已存；局部risk/cost trade-off存在。缺共同覆盖的强基线、完整数值/统计复审，不能宣传普遍校准获益或失败。旧66.46%结果也不能移植为此版本的结果。
- `boundary_phase_scan/phase_boundary_regime_classification.csv`的Regime I/III标签是旧启发式分类（例如60min/60min下refusal_probability=.8），不是E04形式选择器或工业部署地图。

### OP04 对称退化下的早期状态识别

- `artifacts/fair_degradation_replay_20260903/fair_degradation_summary.csv`：clean gate recall.97054054 vs rule1；delay1 .83459459 vs .65540541；delay3 .62 vs .38108108；delay6 .41702703 vs .19594595；5seed原表`fair_degradation_raw.csv`与`seed_201.csv`等。
- `REPOSITORY_EVIDENCE_MAP.md`§5记旧.933 recall与未shift history版本废弃，修正使用UnifiedArrivalDataset。上述表是明确独立的退化识别支线，不是EXP03成本结果。
- 允许：在已存合成延迟/噪声条件的目标识别中，模型还保留一部分相对stale阈值的召回；clean简单规则更好。没有成本或更强同信息识别器比较，不能称部署必要、在线提前预警已认证或延迟频率真实。

## B. Markov和异步包到达

### OP05 honest Markov–Gilbert：性能尚存，F1优势不确定

- `markov_gilbert_eval_honest/markov_gilbert_summary.csv`：clean rule recall/precision/F1全1；corrupted posterior recall.96242865、precision.89466693、F1.92470706；honest stale rule recall.83964712、precision.97853039、F1.90378439。`markov_gilbert_guard.json`：seeds201–205、p_gb.08、p_bb.75、maxlag6、146552 burst cells/seed；F1差.02092267，原区间[-.01390700,.05016273]跨零。
- 原`markov_gilbert_eval`另存非同版本结果，不能替换honest版。`scripts/eval_markov_gilbert_telemetry.py:239–255`同时污染anchor W/Pab和被列出的history channels。哪些所有动态上下文也同等退化、源输入与执行字节绑定，本轮未全链认证；不能只凭guard写完全因果对称。
- 可保留：burst条件下识别召回/精度的不同权衡；复杂未显著赢不等于无boundary信息。无新统计，不宣称F1显著胜出，也不宣称等价。

### OP06 EXP03旧版：有实现硬错，原因果成本/临界延迟不能恢复

- `exp03_async/psrei_vs_delay.csv`与`EXP03_INVALIDATION_NOTICE.md`、`EXP03_ASYNCHRONOUS_REPORT.md`的历史表：初版真实Patv_hist未延迟、标准化尺度阈值致proxy collapse、人口坍缩；hardened版本修了前两项并LOCF固定评价人口，但初始化可能使用尚未到达值，packet trace只覆盖tau0小样本、mask为占位。
- `REPLAY_CLAIM_DISPOSITION_20261015.md`继续撤回其causal arrival curve。旧tau*=1/0与“复杂表示不缓冲延迟”的普遍结论同样撤回；不能只撤阳性保负性。

### OP07 EXP03修正版：已经执行，不等于全文包级溯源闭合

- `raw_replay_20261015_v2/exp03/psrei_vs_delay.csv`70行，`execution/exp03/record.json`记录EXECUTED、exit0、结束2026-10-15T17:36:51.896549Z，输出19756B SHA256 `944b125e2596b89cdd17ae9e951a7f1093627af62d47519672707ba483d2d73d`。seeds201–205、h1/h6、delay0–6。
- 原行`tau0,201,h1`：baseline per-cell18.05070097、challenger17.72862201；`tau6,205,h1`：24.59811100 vs22.07603127，原种子bootstrap差-1038930.22045、区间[-1950512.99155,-318259.82119]；`tau6,205,h6`40.79702667 vs41.06187475，区间跨零。**这些是原种子例示，不是全族平均/联合推断。**
- 60min原drop_fraction.6025056266、stale_fraction.9978983061，late end几乎全stale；固定评价人口408937/408939不等于信息未丢失。p_val是有方向经验概率，不能平均各seed区间端点给全族显著性。
- 允许：已完成修正arrival-envelope实验且结果有异质性；当前本地目录只回传CSV，receipt输出也只列CSV，不能据此宣称full packet trace已经本地审完。包级全链、联合成本/风险与临界点资格UNKNOWN。V2的省略不能将已执行改为未执行。

## C. 外场预测、表征、校准和迁移

### OP08 旧外场模型网格：真正跑过，不是原理上的普适迁移证明

- `external_wind_guard_windowfix/external_wind_guard.json`记80/80 runs、4models、5seeds、Kelmarsh/Penmanshiel chronological与两个leave-one-farm-out方向；`external_wind_reviewer_stats/{site or direction}/{split}/_run_table/external_wind_test_aggregated_runs.csv`存每run RMSE、NMI/ARI、参数与时耗。
- 例如`kelmarsh_to_penmanshiel/leave_one_farm_out`原seed201 force行RMSE361.308864、seed202353.680450，NMI空。guard曾宣称metric齐全，但原行的空格不能被guard覆盖。
- `coverage.json`撤回旧guard、声称deterministic替代；后者只完成WTB权重→两外场的受限决策，不是这些chronological/互迁移模型的完整复演。旧模型表可留作历史比较和域差异诊断，现代matched-target、训练/数据身份、缺指标仍待逐支关闭。

### OP09 外场boundary threshold重校准：Kelmarsh局部表征阳性，Penmanshiel不恢复

- `external_wind_portability_rescue/external_wind_recalibration_summary.csv`，key`kelmarsh,empty target,chronological,Physics-Aligned MoE,n_runs5`：test NMI.56488247497→.63434848470、ARI.60397140661→.67913725074。force模型NMI.41230208826→.47448352326。Penmanshiel对应Physics-Aligned MoE行0→0；另一方向接近0。
- `external_wind_recalibration_guard.json`40run completed，整族mean NMI.1323924287→.1491244563为原guard数，不代表各场站改善。`rescue_summary.json`记80/80完成但portable_wording_allowed=false，原因包括指标不全/门槛未过；不是所有fit未运行。
- 允许：校准阈值对局部边界对齐有时有用，作用异质，不能把它叫下游reserve gain或普适迁移。

### OP10 小校准窗gate adaptation：accuracy改善与balanced accuracy反向

- `external_wind_small_calibration_adaptation/adaptation_summary.csv` key`kelmarsh,chronological,Physics-Aligned MoE,n5`：accuracy.887127→.931261，但balanced accuracy.675084→.518463、macroF1.620172→.510435。Penmanshiel相同行accuracy.4→.894866、balanced accuracy.4→.5、NMI0→0。
- guard记录40/40 adapted、`chronological_balanced_accuracy_meets_minimum=false`、总体`site_specific_adaptation_wording_allowed=false`。这是运行完成但资格失败，不能以多数类accuracy单指标救活“本地少量样本修复迁移”。同样不能说所有本地校准永远无效。

### OP11 LHB anchor-observable表征：明确阳性边界诊断，不能被两外场deterministic代替

- `external_wind_lhb_anchor_intervention_full/lhb_anchor_observability_compact.csv`：actual NMI.9408064155、ARI.9711510497；anchor_pab_zero NMI.6957615083；wspd_zero.7521460063；patv_zero.9534102849；joint boundary_zero.0012638106；random_physics.0279332938。
- `lhb_anchor_observability_guard.json`五runs，主张明确`anchor_observable_cross_site_replication_not_anchor_free_discovery`。`lhb_anchor_stress_guard_full_combined/anchor_stress_summary.csv`五种子/variant，lagged_pab_wspd NMI.7215055271、no_pab_mean.8497741538、no_patv.9525227335。LHB cache metadata有4nodes、54289steps、2017–2020来源档案与字段记录；本轮未读取原测量。
- 解释：现成网络确实依赖W/Pab边界anchors而非Patv反馈；单独一部分anchor保留信息。它不证明无anchor隐藏机理，也不证明备用决策增益、因果自然机制或跨年确认。
- 状态冲突：coverage将此guard笼统WITHDRAWN并称deterministic替代；deterministic没有LHB输出。本轮没有发现针对本组NMI的独立数值反证，故登记为**历史诊断阳性/现代复演与确认资格未闭合**；不能伪称当前contract之外已恢复有效部署主张。

### OP12 EXP01多版本：硬错与来源失败必须区别

- v4/pitchmasked retrospective的Penmanshiel h6 -315399.62、Kelmarsh+352433.95，由`EXP01_INVALIDATION_20261015.md`判定预测与target物理窗口错配；正负方向均无效。旧corrected-v2的+5.322M/+435684也被`EVIDENCE_FREEZE_20261017.md`superseded/not reinstated，不能恢复为当前外场数字。
- 原默认推理audit242736 exact gate失败，后来242739定位同输入默认重复forward不精确、显式deterministic重复精确。该旧失败是重复性门禁失败，不是“风场所有信息无效”。不能把未知kernels原因编为无害。

### OP13 deterministic_matched_transfer：受限负结果真实，不是普遍外场定理

- `artifacts/metis_external_deterministic_20261015_attempt1/audit_report.json`：`status=EXACT_EXTERNAL_EVIDENCE_VERIFIED`、PBS242742、A100-PCIE40GB/PyTorch2.11.0+cu128/Python3.11.16；20个site×seed×horizon的results及4个statistics结果。
- key`kelmarsh,h6`mean delta+6322.697575、95%[-31417.261401,+46732.590610]；`penmanshiel,h6`+356014.397853、[+162798.520598,+566245.720865]。h1对应+31325.120290、区间跨0；Penmanshiel+230645.731683、区间为正。原seed201–205、35连续144合格issue块、5000两阶段抽样；这些并非自然天气日保证。
- 条件：既有WTB gate完整权重、当地固定point forecast、当地validation quantile calibration；history有特权pitch，deployment屏蔽pitch。不是full zero-shot pipeline，也未认证raw retraining。允许说当前协议的Penmanshiel成本惩罚与Kelmarsh无已证成本改善，不能称所有迁移失败/简单基线认证最小/图不必要。

### OP14 IEC density与多年度rolling：有利结果有对应实验，但弱基线与任务不同

- `iec_density_rolling_eval/iec_rolling_guard.json`原r10：Kelmarsh walkforward delta-6187492.906148、CI[-7518144.713571,-4765045.781336]；Penmanshiel-4339714.631343、[-8241400.115669,-438029.147018]。static-freeze两场区间均跨0。LHB pooled+42927.184961、[-28744.626081,+141198.161788]；rolling+1006532.132952、[+285337.559742,+1755204.844799]。
- 原表`{farm}_rolling_by_seed.csv`与`{farm}_rolling_paired_summary.csv`有five seeds、window、rho、policy、rated wind/band/elevation、n_cells。对照为global/soft-pab，不是强same-information wind-bin closure；rolling更换校准窗口/目标支持，不可和EXP01/h6新冻结forecast相减。
- 允许：校准窗口与场站异质性是可见的历史实证问题；复杂在某些弱对照/rolling条件收益，在LHB反向，不能说“外场所有实验都负”。不能据LHB CI跨0的pooled项证明overfitting或local sufficiency。

### OP15 external_reserve_enhanced：数字资产存在，来源资格UNKNOWN

- `external_reserve_enhanced_summary.csv`记Kelmarsh five-seed mean-21860、[-24380,-19340]；by_seed15行，n_cells18450，成本为整百/整千。guard没有协议、split或输入/执行身份绑定。已定位`remote_external_reserve_enhancement.py`，其正常路径从val/test保存数组计算且无数据时fail，并有seed bootstrap；这不证明本地表恰来自该源码/输入。仅表格圆整数不能推断伪造，也不能当实验已经可信执行。
- 状态：静态数字可读，生成/执行provenance未闭合；不得纳入当前实证headline。保留在未核清资产清单，不能当普遍校准/迁移阳性。

## D. 聚合、价格、运行代理与BESS

### OP16 全场聚合reserve：完成了另一层问题，原成本优势不确定

- `farm_aggregate_reserve_20260905/farm_pcc_paired_summary.csv` key`all_steps,rho10,total_cost,joint-posterior-aggregate vs global-pcc-quantile`delta-2319718.259245、CI[-6068464.031966,+1726049.411784]；vs gaussian-pcc-param -1367881.678296、区间跨0。transition同global+99629.388151、[-306189.743880,+505448.520182]。
- vs soft-pab all_steps-7927356.721354、区间负；但wilcoxon_p=.125，不能择CI丢检验。transition vs soft-pab-1328976.002018且wilcoxon .0625。guard声明seeds201–205、rho5/10/20、20000 bootstrap；原表保留全部。
- `scripts/eval_farm_aggregate_reserve.py`是134机功率和的代理，不是观测PCC独立计量、网损/网络可交付认证。`transitional`由pitch比例10%–90%定义，不等于可部署在线选择器。不能因V2没PCC就说项目未做任何组合层分析，也不能用本表补V2真实PCC缺口。

### OP17 真实价格加权：与市场调度分开，保留表中正负方向

- `dynamic_price_settlement_audit/{farm}_real_price_paired_summary.csv`，rho10、`walkforward_rolling_pooled,total_cashflow_gbp,soft-gate-bin vs global`：Penmanshiel-187148.93125、CI[-361377.859375,-12920.003125]；Kelmarsh-134032.5265625、[-166699.68125,-97392.234375]。`pooled_multiyear_full`同对照：Penmanshiel+496773.1、[+260102.1,+733444.1]；Kelmarsh-358064.1125、区间负。
- vs soft-pab与不同rho也异质，Kelmarsh rolling rho20 total_cashflow+50259.39375、区间为正。不能只取有利窗或称所有价格分析负。
- `ELEXON_A12_PROVENANCE_AUDIT.md`给157804个2016–2024半小时价格来源、负价处理，明确是预计算reserve/shortfall历史价格加权；不是市场clearing、reserve activation或AC-OPF。该来源/处理说明并不自动认证所有物理目标与时间映射。
- `REPOSITORY_EVIDENCE_MAP.md`记更早GBP现金套利支线有日期offset、24horizon重叠计数与无激活物理，已隔离；本轮未证明A12新price表完整修复每一旧错。现源码`remote_dynamic_price_settlement_replay.py:284–289`仍展平成全部Ht horizons再匹配SBP；因此允许历史加权敏感性，不能当唯一实际现金流或成本部署认证。强same-information baseline、forecast/物理窗口绑定及非重叠现金流仍未核清。

### OP18 toy operational cost：完成的代理换算，不是独立运行收益证据

- `reserve_toy_operational_cost/reserve_toy_operational_cost.csv`，boundary GraphWaveNet physical-bin84314352.5391，Boundary router gate-bin84577216.7958，router global88128653.4939；full GraphWaveNet/global464072749.1912、router/global501319742.7764。
- `_raw.csv`首行明示`n_runs=5`、rho10、boundary valid_cells10695。`.json`明示normalized single-farm proxy、不是UC/OPF/market clearing/real dispatch integration。部分同策略从reserve_decision和probabilistic_baseline重复列示，不是独立实验重复。
- 允许：损失分账/风险采购权衡的历史辅助材料。它改变point forecaster且不同subset，不能接成固定同forecast的pitch独有价值，也不能把proxy成本叫货币收益。

### OP19 BESS：合成储能资源改善有原始结果；不证明预测/状态算法创造价值

- `wind_bess_simulation/bess_dispatch_summary.csv`，delay6、20MWh/10MW：unbuffered cost487745.747721、BESS MPC331256.587081、原cost_reduction_pct32.1400730；shortage2514.879395→1401.161654MWh、原mitigation45.7251852；V.38819514→.20582212。guard列seeds201–205、delay0/1/3/6、capacity5/10/20/30/40、c-rate.5、lookahead6。
- 同表heuristic与MPC在全部显示延迟主指标相同；没有MPC增量。`run_wind_bess_simulation.py`输入旧wtb_full预测/target，按causal aggregation后用h0；延迟同时改commit schedule，属于另一任务。缺测值nan_to_num为0、有效步压缩、时点状态和成本参数都需要独立审计，不能因JSON叫completed就当现场闭环。
- 允许：已有五seed合成储能资源/退化压力敏感性，不是未做任何运行仿真；资源新增后的收益不可归为遥测/representation收益。真实BESS、PCC交付、市场调度、现代冻结任务、同资源强基线均未认证。

## E. 早期预警与ERA5

### OP20 旧早期预警anchor stress与简单分类器：存在识别阳性，也有强反证

- `anchor_stress_early_warning_wtb_strictmask/anchor_stress_early_warning_summary.csv` keycanonical delay6：5runs、211 transitions、740 target cells/2154support，gate recall.96027027 vs stale threshold.19594595；clean阈值recall1且precision.87885986优于gate .75864179。预触发ranking一格AP.08485323、AUROC.98229832但target_rate.000754585；高AUROC不能掩盖低precision稀有事件。
- `early_warning_classifier_baseline_wtb/early_warning_classifier_baseline_summary.csv`：clean logistic recall1、precision.87885986；delay6仍1/.87886，gate.96027/.75864。该classifier读clean issue-time anchors；与label-delay规则并非所有通道共同arrival退化。
- `coverage.json`将这些旧claims撤回confirmatory use，原因泛称raw replay superseded，没有对本组每个target/metric做独立否证。允许保留“现有输入及标签构造下简单分类器可匹配/超过复杂gate”的历史控制知识，不能复活现代受限arrival的ex-ante warning或成本收益。当前风速能分割被筛标签的问题进一步限制隐藏状态叙事。

### OP21 ERA5主实验与baseline扩展：真的有独立科学任务，不能冒充风场外部确认

- `cloud_revision/era5/20260525_163247/run_metadata.json`记录dataset era5、seeds401–405与真实启动命令；`main/suite_summary.json`15rows dense/unconstrained/full、每run训练历史/val/test摘要、参数。`era5_full_seed401/test_metrics/metrics.json`overall RMSE.85421615945、NMI.04513897929/ARI.06060889689；dense401 RMSE.90875739539。full405 RMSE.85406385112、dense405.75366786049，排序并不一致。full各seed NMI原值.045139/.345433/.189250/.235439/.234657。
- `era5_baseline_expansion_20260529/_tables/era5_test_aggregated_runs.csv`12rows、seeds501–503、GraphWaveNet/PatchTST/STGCN/TCN，383 test windows；seed501 RMSE依次.8684388803/.8656087435/1.1161561701/.9103115179。**三seed baseline与五seed主模型不能当完全配对统计。**
- `REPOSITORY_EVIDENCE_MAP.md`列16×16/256cells、2208 hourly frames、train0–1325/val1325–1766/test1766–2208，是thermodynamic convective contrast。它可作跨任务表征/复杂度异质性历史材料，不是pitch/备用收益实验证据；未读原ERA5测量、未核现行预处理和完整软件环境。
- 发现污染：`_baseline_inventory/era5/era5_test_aggregated_runs.csv`首行dataset标era5但run_dir指`wtb_align_seed201`、RMSE263.452127、num_windows4981。**此文件的ERA5标签不能信任，已隔离，未与真正ERA5输出混用。**这证明要逐文件查身份，不等于真正ERA5分支无效。

### OP22 LHB withheld-anchor训练复现：不能与单次anchor移除混成同一实验

- `signature_gate_lhb_guard_20260902/anchor_stress_summary.csv`：canonical五seed NMI.9752334391；signature_full五seed NMI.6743138818、ARI.7400975954；signature_core五seed NMI.5749875271、ARI.6269737268。`signature_gate_lhb_shuffled_guard_20260902/anchor_stress_summary.csv`：core_shuffled NMI.0002403142。`signature_gate_guard_no_pab_std_lhb_20260903/anchor_stress_summary.csv`：no_pab_std五seed NMI.5775309085、std.1349104259。
- 这些是**重训输入约束**而非OP11同checkpoint输入干预；不能用OP11同时抹去boundary anchor的collapse否定本组重新学习的consequence signature。core旧命名不能自动理解为所有pitch统计已屏蔽，no_pab_std版本需单独引用。
- cache_status指向`cache_signature_lhb/external_wind_la_haute_borne_chronological_*`，metadata含variant marker；本轮没有载入tensor逐通道检查。原guard要求min_nmi.4且claims明确constrained routing，不是anchor-free physical discovery。负/阳性都在历史有限输入协议下。
- 可保留：另一场站从头训练也能学到与声明标签相关的非定义通道signature，有no_pab_std和shuffle对照；不能称WTB参数零样本迁移或reserve收益。训练身份/privileged labels/当前标签wind-separability/独立复演仍约束解释。

### OP23 Kelmarsh/Penmanshiel signature主窗与扫描：有信号，原门槛未通过不能写无信息

- `signature_gate_farms_guard_20260903/penmanshiel/anchor_stress_summary.csv`：五seed signature_full NMI.3024170953、core.1953712339、full_shuffled.0000442455；Kelmarsh对应full.3402112520、core.3775466564、full_shuffled.0000924724。主窗full/core均`nmi_gate_pass=false`；原表自身将claim降为declared-anchor constrained routing。
- 独立存储扫描窗`penmanshiel_sec / penmanshiel_rand / kelmarsh_sec / kelmarsh_rand`各`anchor_stress_summary.csv`：full三seed NMI原值.4575700832/.2941117890/.3586361656/.2773964250。不得把扫描窗当新的场站或五seed确认，不能以扫描过.20修补主窗原门槛。
- `.experiment-to-paper/experiment_matrix.md`旧“78%/55% pitch coverage”受`REPOSITORY_EVIDENCE_MAP.md`§5硬错影响：0°被当缺测，不能恢复；**coverage统计错误不自动证明这些NMI为假**。必须区分字段缺失、物理0°与withholding干预。
- 可保留：与shuffle相比仍有描述性标签关联、场站/窗口异质；原资格失败保留，不宣称普适boundary可恢复、因果机理或决策充分性。本轮未做新的label/MI统计。

### OP24 Kelmarsh真实Status事件grounding：完成的来源描述，未测通信延迟

- `kelmarsh_grounding_20260903/kelmarsh_grounding_summary.json`：源`Kelmarsh_SCADA_2016_3082.zip`、区间2016-01-01至2017-01-01、export timestamp2022-01-27；n_status_events14019、n_events_off_10min_grid13957、off_grid_fraction.9955774306、pitch_related_events14。
- 允许：这一真实日志的Status事件有秒级异步时标，大多数不落10分钟边界。它是运行来源材料；V2省略它不代表项目完全没有现实SCADA事件证据。
- 边界：event timestamp不等于arrival timestamp；没有真实10–60min传输分布、整条pitch流/策略输入可用时钟或经济后果，不能拿99.6%支持延迟压力概率。summary来源可追，但本轮没有打开测量ZIP重验。

## F. 明确未核清的范围

1. 当前科学契约“fresh物理最强/Regime2吸收”仍列VERIFIED，与后续coverage批量WITHDRAWN和corrected phase之间的逐任务裁决。该冲突不能通过改旧数字或只引用较新文件自动消失。
2. corrected phase完整validation-head/校准/动作中间件与独立数值/统计审查。本轮仅读150行源表中的指定行和aggregation receipt，不宣称150格逐值复演。
3. corrected EXP03 full-grid packet trace、mask、选择事件与native blocks是否归档/回传。当前receipt仅输出CSV；未知不是已证明trace不存在，更不是结果全部错误。
4. honest Markov动态边、feature masks、所有输入通道同步退化与实际运行源码绑定；field burst参数频率未测。
5. 旧外场80-run模型矩阵、LHB所有权重/输入/训练身份的完整本地闭环；coverage的替代关系不完全对应实验对象。
6. small-calibration各run所用历史窗、阈值选档是否与test隔离，以及指标缺格/类别塌缩的精确原因。原失败保持，不重新调门槛。
7. IEC rolling与price分支的源物理窗口、forecast identity、单交付时点/多horizon estimand、时钟、缺测、价格映射和强基线资格；正负原值保留但不升级部署效应。
8. external_reserve_enhanced生成与执行来源；整百数值本身不是造假证据，也不是有效执行证明。
9. PCC代理是否固定成员/缺测规则、观测汇总是否独立计量、每组人口和随机性单位。本轮没有加载其预测/权重或重算bootstrap。
10. BESS有效时间网格、缺测置零、控制时点/forecast horizon、SoC/周期账目、真实成本设定与heuristic=MPC原因；不能给其旧32.14%增加统计认证。
11. 早期预警event去重、transition mask、未来标签影响与同到达的强分类器；旧positive/negative仅作历史诊断。
12. 真ERA5来源哈希/预处理/scaler、训练设备环境和三seed/五seed不配对的不确定性；早期合并paper_assets快照没有逐版本全审。_baseline_inventory混标已记录，但未排查全部历史副本。
13. 外场signature各输入/物理mask与Pab_std在训练、val、test及anchor中的真实清除身份；窗口扫描是否先验/独立，不以guard门槛替代证据检验。Status日志原测量未重读、没有arrival时间字段审计。

以上范围对应父任务`ASSET_INVENTORY.csv`中可检索到的目录，不代表58,377文件全文全审。本分支覆盖24个科学可比族/版本责任，详见CSV；没有按新V2稿的狭窄问题筛掉整条历史，也没有恢复硬证据失效的版本。贡献可用性需分别判为：历史诊断阳性、受限负结果、实现无效、统计未决或来源未闭合；领域新颖性与整项目期刊结论本轮均UNKNOWN。
