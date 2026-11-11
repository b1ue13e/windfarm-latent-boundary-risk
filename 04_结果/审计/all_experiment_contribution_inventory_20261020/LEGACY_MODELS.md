# 历史模型、预测、表征、机制与消融资产贡献盘点

审计日期：2026-10-20。范围：本地现有 March–September paper runs、May/June 汇总与 strict-mask 系列、训练权重修正、anchor/signature/negative-control、October raw core/channel/supervision/factorial/strong-baseline/EXP02 分支。只读原 CSV/JSON/配置/收据及已有审计，没有加载权重、推理、重采样、计算新的科学统计、远端访问或修改旧资产。使用 experiment-to-paper 的 audit 模式及其 evidence contract。新颖性没有另作文献检索，以下均不是文献优先权认证。

## 对“只有 V2 这么点贡献”的直接回答

**VERIFIED：V2 的结果范围比本项目完成的实验范围窄。** `manuscripts/wind_energy_v2/manuscript.md`、`supplementary.md` 的主结果集中于 WTB 信息子集开发和 Hill of Towie 冻结选择确认；补充第272行只概括旧 graph/recovery/MoE 有独立来源缺口，没有带入本报告下列历史结果。不能将 V2 当前论文是否足够、或其投入裁决，外推为“所有实验都没有知识贡献”。

尤其值得保留的六类知识是：

1. **有直接配对统计支持的表征效应**：修正后 masked-inference supervision 实验中，alignment 相对 no-alignment 的 NMI 增量 +0.4550，种子配对 t 区间 [0.1513,0.7588]，ARI +0.5379 [0.1736,0.9023]；同时 h6 成本区间跨零。它支持“训练监督改变表征”，并直接展示表征和决策效应不能互换。
2. **通道和时间信息的具体来源**：C2 功率单通道的 NMI≈0.461/ARI≈0.647；另一个七条件 probe 中，单步 lag-1 功率 AUROC≈0.984/AUPRC≈0.708，接近 current+history 的0.988/0.719。不能一概说恢复完全依靠当期功率，也不能把它写成复杂动态机制必要。
3. **有界阳性及混合结果**：修正后的四条件 factorial h6 Full 上，delay6、pitch-withheld、两者同时的后验−风速分箱点差分别为 −62,128.6、−5,239.0、−130,799.6 kWh；clean 为 +128,217.4。保存动作算术审计闭合，但没有当前配对不确定性结论，且四个 Boundary 点差全为正。这是条件化的经验现象，不是“全无阳性”，也不支持全面优越。
4. **真实的失败边界**：May/June 的预测榜、容量控制、ERA5 persistence、anchor-only/context 控制说明语义更对齐不保证预测更好；September modular 对照没有证明联合训练或路由不可替代。
5. **控制实验提供的诊断知识**：temporal/global label placebo 破坏对齐；wind/pitch anchor 清零远大于 wake 清零；阈值负控的标签互补却保持 NMI/ARI，说明这些不具标签语义敏感性的指标不能单独认证物理阈值。
6. **EXP02 并非统一方向的失败**：当前 eps50 在 h1/h6 有利点差，但保存报告中统计层存在冲突，正文未达预设.95证据门槛；旧“全面证伪”与“所有版本都更差”均不成立。它应记为方向性阳性、统计/版本待核，而非稳定收益。

这些知识是否能单独构成新论文的贡献，**UNKNOWN**；本次没有新筛题、查新或期刊判断。

## 状态字典及读取原则

- **VERIFIED_ARTIFACT / BOUNDED_POSITIVE**：本次直接读到文件、键或行；若有独立算术/收据，只在其范围有效。
- **DESCRIPTIVE_POSITIVE / DESCRIPTIVE_MIXED**：保存点结果有利/混合，不能补造显著性。
- **NULL_OR_UNCERTAIN**：区间跨零或缺少可比较推断，不等于等价或已证无效。
- **NEGATIVE_WITHIN_PROTOCOL**：该协议下的方向不利；不是普遍无用或全项目否证。
- **KNOWN_INVALID_FOR_NAMED_CLAIM**：有具体缺陷破坏特定主张，如 wrong residual horizon、wrong physical window、旧 proxy scaling。只撤回受影响部分。
- **SUPERSEDED**：较新版本替代当前数值报告；历史结果仍存在，不能据此说其每个数字造假或科学方向已反证。
- **PROVENANCE_OR_AUDIT_OPEN**：有输出但来源/深审计未闭合。不是“结果已被证伪”。

所有五种子均为固定测试天气下的训练实例，不等于五个独立天气年。旧 paired reviewer 表若把 validation 与 ablation 的同种子复制算作 n=10，不应作为十次独立复制。报告与原 run 目录有冲突时分别记录，不替换原文件。CSV 台账为 `LEGACY_CLAIMS.csv`，每行给键/条件/种子/对照/限制。

## 1. March–May 原始预测与物理对齐：有局部阳性，强预测优势未建立

### 1.1 March paper runs 与 May 前快照

原始入口 `artifacts/paper_runs/wtb_full_revision_20260314/manifest.json`：main seeds101–105，ablation201–203，sensitivity301–303；历史 project_root 为 F:\\论文3。`collected_results/snapshot_20260318_134107/runs.csv` 的 `complete=True` 行存在空 test_rmse 等列，**空白不是0，也不能只靠 complete 宣布整个基准数值核验完成**。另有 snapshot_133802 和原训练 JSON；本次只抽核来源和代表资产，没有逐一读完400份表。

`artifacts/paper_assets_backup_before_era5_merge_20260526/tables/table_main_results.csv`，WTB 行：Dense261.16±8.92（n5），Unconstrained258.47±9.65（n5），WTB Corrected Routing258.20±4.04（n3）。同目录 `table_wtb_ablation.csv`：unconstrained NMI.0124，align.8029，bal+align+force.8758，而 overall RMSE255.42/259.35/258.20。可留“监督显著改变分区的描述现象、预测和对齐不一致”；不可用3/5种子混合和旧协议写 strong-baseline superiority。May 表确有小于 Dense 的点结果，但没有本次核实的公平强基线显著性结论。

### 1.2 May ERA5 与扩展基准

`artifacts/paper_assets_merged_era5_20260526/tables/table_main_results.csv`：ERA5 Dense.8641（n5），Unconstrained.9294（n5），Physics-Aligned.8735（n5）。`artifacts/paper_assets/tables/table_routing_quality.csv` 同时报 NMI.0317→.2100、ARI.0253→.2279。**这是相对 unconstrained 的有利点现象**；Dense点RMSE仍更低。实际 run 来源见 `paper_assets/tables/era5_test_aggregated_runs.csv`，例如 `cloud_revision/era5/20260525_163247/main/era5_dense_seed401`，seeds401–405，不是 WTB 的201–205。

`artifacts/paper_assets_expanded_era5_20260529c/tables/table_main_benchmark.csv` 另显示 ERA5 Persistence.7127优于表中全部 learned recipes；WTB Graph WaveNet230.74（n3），Physics-Aligned258.38（n5），PatchTST263.92（n3），Dense261.16（n5）。因此可以保留“物理对齐相对部分弱比较有改善、全局最强对照推翻了预测冠军叙事”，不能把任何小幅局部阳性说成不存在。backup/merged/expanded/copies 的样本数和SD版本不同，不能拼成一张新表。

### 1.3 June strict-mask 预测榜与容量对照

`artifacts/paper_assets/tables/table_main_benchmark.csv` 及 `wtb_test_aggregated_runs.csv`：Graph WaveNet225.74±2.60，PatchTST228.07±4.05，iTransformer224.34±2.23，TiDE227.31±3.05，Dense231.42±5.87，Unconstrained235.40±7.96，Boundary-forced236.13±8.41，Physics-Aligned241.42±4.28（均n5）。这批结果不支持该 MoE 作为预测最强模型；仍有解释性对齐问题可研究。strict refresh_20260613 同均值但SD不同（如 Graph225.74±2.33），反映汇总规范版本，不能挑较小SD。

容量控制必须读 run 表：`paper_assets/tables/wtb_parameter_table.csv` 写 Dense/MoE 均110,012；但 `table_robustness.csv` 和实际 aggregate rows 将 Dense 记115,240、MoE110,012。ERA5参数表也有103,843与run表103,272的版本不一致。因此只能称历史命名的 Capacity-Matched Dense comparator，不能本次认证精确等参数因果实验。`capacity_matched_dense_wtb/wtb_dense_seed201/training_summary.json` 存9 epoch训练史，best_epoch4、best_val_rmse216.8535、训练3371.44秒；源文件存在不等于当前硬件成本可比。

旧 strict reviewer 配对表 `strictmask_combined_reviewer_stats/paired_effects_summary.csv` 对 Graph/Patch 的 reference RMSE≈219.9，而论文表236.13；`reviewer_stat_pack_config.json` 合并 validation/baseline/ablation三suite，reference n10。**这是评价/聚合口径不同的警告**，本次不将其均值p值当独立的总体显著性证据。`paired_permutation_p_mse_mean` 本身也不是一个联合检验。

## 2. 消融：对齐可提高，预测、校准和训练来源需分别查

`paper_assets/tables/table_wtb_ablation.csv` 全五种子行：Unconstrained NMI.0136/ARI.0076；bal .2401/.1978；align .7973/.8651；bal+align .8189/.8893；bal+align+force .8716/.9166；再加smooth降至.8320/.8673且RMSE239.61高于236.13。Anchor-only .8895/.9219，RMSE233.46；context .7521/.8020，RMSE242.75。这些值支持“不同损失主要改路由语义，不能保证预测收益”，不支持每个新增loss有效或复杂context必需。

具体独立阳性：`anchor_only_decisive_comparison_20260613/anchor_only_decisive_deltas.csv` strict_test 中 Boundary-forced 相对 Anchor-only 在 pitch_control RMSE低30.8648，但 overall高2.6706、switch高2.9559、NMI低.01784；相对context overall低6.6218、NMI高.11952。**局部pitch误差和全局误差的权衡值得保留**，不是单向赢。

校准负信息不应遗漏：同目录 `gate_calibration_summary.csv` strict_test Boundary-forced gate_accuracy.97776、ECE.41713、Brier.42987；Anchor-only accuracy.97932、ECE.19725、Brier.15459。这是历史原门分数诊断，与后来二类后验ECE/校准指标不同，不能拼接或把高NMI解释成已校准概率。门类映射和分数口径的进一步解释未在本次闭合。

checkpoint缺陷有具体修复记录：`checkpoint_replay_fix_wtb/README.md` 说明旧 in-memory best_state未clone，被后续epoch修改；partial smoke无reference不能当论文证据。`checkpoint_replay_fix_wtb_full` seeds201–205与`mechanism_gate_wtb_corrected_full`为修复后完整分支；后者5/5 replay匹配但seed204 NMI.3799、ARI.3259，平均NMI.7616±.2256，不能声称每种子高对齐。**后来的 strict-mask 5/5 replay通过不追认更早 broken-checkpoint结果**。

缺失anchor评估修正：`strict_anchor_mask_diagnostic_wtb_20260609/strict_anchor_mask_summary.csv` 原NMI.761554→strict.759123，ARI.783173→.782134，drop_rate.00230785；说明该已存模型的评估对这次过滤敏感性小，**不能代替严格mask重训**。`cache_strictmask/wtb_245d/metadata.json` 的 strict_anchor_mask_patch 进一步记录原有效4,142,408→4,092,890，删除49,518；两者是不同范围的分母，不冲突、不互换。

class-weight存在明确的全周期来源问题：`class_weight_boundary_audit/class_weight_boundary_audit.json` 将旧strict缓存 `metadata_matches_full_period=true`、train_only=false；trainweights缓存相反。`class_weight_sensitivity_summary.csv` 的train-only复跑seeds201–205仍有NMI.720770±.170672、ARI.739759±.219645，overall RMSE229.9287（旧236.1305）。这是真正应保留的修正后表征阳性，**原.8716/.9166不能当无泄漏现行指标**，也不能因旧有污染把新复跑全部扔掉；本次未找齐该复跑的全硬件/软件receipt，标来源范围受限。

August `trainweight_full_rerun_20260830/wtb_full_seed201/training_summary.json` 可直接读参数110,012、seed201、mode=moe_phys_full及loss weights（align5000、aux250、smooth.05、balance1000、force10000），test_summary NMI.847852/ARI.899587、switch RMSE235.1102。seeds202–205目录也存在。**本次不为五种子新算均值**；原生成环境/完整输入/权重联合绑定见`analyses/legacy_*20261018`仍未闭合。结果是原始描述资产，不是已证明无效，也不是全链已复现。

## 3. 边界、placebo、anchor和时空泛化：是诊断贡献

- `boundary_slice_wtb_strictmask_full/boundary_slice_effects.csv`，n5，boundary_band−nonboundary RMSE +67.0731 [52.5408,84.2072]、相对pitch_core +50.0058 [41.5782,56.4701]。config固定rated10.5、pitch2、band1、bootstrap1000/seed42。可以说所评边界带较难；它不是Full或Transition决策收益，也不是新独立数据。
- `time_forward_wtb_strictmask_full/time_forward_report.md` late−early RMSE +50.3454 [46.8137,54.1758]，NMI却 +.0068 [.0021,.0127]；n10涉及同种子suite复制，不能当10独立种子。这保留“预测漂移与语义对齐漂移分离”的知识。
- `routing_placebo_wtb_strictmask_full/routing_placebo_effects.csv` actual−global_shuffle NMI+.8716、actual−shift144+.8324、within_time+.3337、node_permutation+.3289。支持保存门分区与标签的具体时空对应高于这些置乱；不证明空间图的因果必要。
- `boundary_negative_controls_wtb/boundary_negative_controls_summary.csv` wrong_rated/pitch四行shared_label_change_rate=1，但NMI/ARI与actual完全相同；这对“错误阈值必使NMI崩溃”的说法是反例。random_boundary NMI.6706而time_shift.0392，也说明不能把随机/时间/标签互补当同种负控。`threshold_label_validity_audit.../README.md`明确“阈值敏感性不是语义负控”，应保留这项方法诊断。
- 严格mask anchor干预的直接source `mechanism_gate_wtb_strictmask_full/mechanism_intervention/mechanism_intervention_summary.csv`：actual NMI.871618；boundary_zero .169897，wake_zero .870647，all_zero .152498。effect原表/README：boundary整体RMSE+2.6792 [0.7347,4.5598]，wake+.0031 [−.0016,.0110]，pitch-control boundary误差区间跨零。它证明**该已训练模型依赖所给边界anchors**；训练/部署可见pitch setting、全周期权重污染仍限制其用途，不是隐藏机理因果发现。
- 修正checkpoint分支 `mechanism_gate_wtb_corrected_full/mechanism_intervention/mechanism_intervention_effects.csv`：boundary_zero NMI drop.439077 [.160846,.687769]、overall RMSE+3.29735 [.68855,5.91107]；wake_zero overall+.02625 [−.01101,.08267]。可保留已重放范围内的anchor依赖/近零wake对照和种子异质性。
- `strictmask_threshold_controls_mechanism/mechanism_intervention_effects.csv` Physics-Aligned20run行：boundary_zero NMI drop.544465 [.443437,.646548]、RMSE+4.77227 [3.70974,6.05098]。这些是4阈值×5种子的相关敏感性runs，不是20独立数据集。
- `future_holdout.../paired_effects_summary.csv` seeds301–305：router overall218.634 vsanchor221.060，switch219.068 vs222.825；但context overall216.718更低。`future_holdout.../boundary_slice_summary.csv` boundary RMSE345.159，nonboundary250.473。future命名不等于新增未见时间源；后来的E07 availability审计明确该cache仍旧Day1–245。其内部留出诊断可保留，但不得升级独立未来确认。
- `anchor_only_decisive.../anchor_only_decisive_deltas.csv` spatial_holdout：router233.871 vsanchor234.241，context229.467更低；router NMI.834019 vsanchor.866080/context.747947。真实run表有seeds401–405；而早期protocol.json仍写protocol_only_not_executed。这是过时状态，不是没run。`spatial_holdout.../paired_effects_summary.csv`本次读到为空，不能补造其配对推断。它是同一WTB的跨机组探针，非跨风场确认。

## 4. September signature与modular对照

`signature_gate_guard_20260901/anchor_stress_summary.csv`：signature_core n5 NMI.367148/ARI.434224；signature_full .561332/.634722。`signature_gate_guard_no_pab_std_wtb_20260903`去Pab_std后仍NMI.309419/ARI.355875，五种子完整且保存guard pass。`signature_gate_guard_core_shuffled_20260902` 同源shuffled为NMI4.656e−6/ARI−.0001984。这保留“扣除明显pitch派生通道后仍存在统计可恢复性、置乱监督破坏它”的限定阳性，不证明anchor-free发现、图必要或决策收益；guard min_nmi=.2只是历史诊断门槛，不是科学显著性。

`matched_modular_comparison/matched_modular_results.csv` joint routed16.065M vsdense16.076M、global16.632M；soft-pab15.538M、rule16.190M。原summary称routing decisive/joint indispensable，**措辞超过对照**：信息集weak/conseq/physical不同，全局比较弱，不能据此主张joint不可替代。`matched_modular_rerun_5seeds/modular_mlp_summary_5seeds.csv` Cascaded Frozen MLP成本15.528M，相对joint差−.536587M、区间[−1.988160,+.914986]；Independent MLP15.8047M、差−.259977M、区间[−1.771066,+1.251111]。这些跨零结果没有证明模块化胜出，也没有证明joint的必要。原数据与fixed-target来源欠闭合，保留为历史不确定性，不作为新强决策比较。

### 4.1 LHB与partial-pitch场站的表征阳性

原 `signature_gate_lhb_guard_20260902/anchor_stress_summary.csv`：LHB canonical NMI.975233，signature_full .674314、core .574988；`signature_gate_guard_no_pab_std_lhb_20260903`去Pab_std仍.577531；`signature_gate_lhb_shuffled_guard_20260902` core_shuffled .000240314。这些均5seed完整guard；旧matrix写shuffled1.92e−4，**与当前原summary不同，不取旧更小值**。它支持异场本地重训后仍有后果signature，不能说WTB权重零样本迁移、物理因果或决策收益。

`p1_stats_20260904/farm_median_iqr.csv`保存Penmanshiel full/core NMI.302417/.195371、Kelmarsh .340211/.377547；对应full_shuffled为4.4245e−5/9.2472e−5。Penmanshiel canonical .69872的IQR为[.27873,.99374]，说明种子异质性大。`window_scan_pass_rate.csv` 的四个sec/rand窗均3/3过原NMI.20诊断门槛，**不是4个独立风场，也不是统计显著性检验**。本次读的是保存汇总；各场完整source/硬件与测量mask绑定未再逐行审计。它保留“signature在这些本地recipe与窗中可再现、效果不随场站单调”的描述知识，不能因后来的reserve失败抹掉。

### 4.2 公平退化分类阳性与版本冲突

`fair_degradation_replay_20260903/fair_degradation_config.json`绑定train-only cache与July rerun、seeds201–205、delay1/3/6、noise两档；规则和gate的Wspd/Pab在anchor与history同时退化。当前原summary：delay1 gate/rule recall .834595/.655405，delay3 .620000/.381081，delay6 .417027/.195946，强noise .950541/.680000。`raw.csv`同时提供precision/F1；例如seed201 delay6 recall .445946/.195946，precision .365449/.341981，F1 .401704/.249141。这是具体受控early-window classification阳性，**不是单看recall便证明风险或备用优势**。

同一目录`seed_201.csv` delay6却为.377027（当前合并raw为.445946）；说明逐seed旧文件与合并raw不是完全同快照。旧`.experiment-to-paper/experiment_matrix.md`的gate .933亦非此次实际summary，不在无原对应结果下恢复其为当前数字。`breakthrough_20260904/dense_fair_degradation_summary.csv` delay6 .286216；但其输入/历史stall版本需要绑定，不能直接以.417或旧.933减.286作因果routing增量。

`breakthrough_20260904/multichannel_classifier_results.csv`独立GBDT-consequence delay6 recall.867568、precision.390274，shared-noise recall.804054/precision.372340；logistic-cons delay6 recall.455405，logistic-all.194595。这保留“退化恢复并非路由独有，简单后果分类器也可能很强”的重要知识。表中这些分类器行不是五seed表，不能从目录名给它添五seed/误差棒。

### 4.3 旧soft posterior确有局部、弱参照上的统计阳性

`soft_rule_contrast_20260903/soft_rule_contrast_paired_summary.csv` 的rho10/clean/total_cost：soft-gate-bin−global为−567,544.935 kWh，已存CI[−726,045.796,−405,944.687]（n5）；`p1_stats_20260904/unified_control_table.csv`同项Bonferroni13族CI[−793,765.694,−345,624.539]。同表soft-gate−physical-bin为−125,398.348、CI[−296,993.663,+34,073.823]，而soft-pab−global为−1,093,890.093、CI[−1,321,084.209,−876,317.824]。**局部soft risk stratification相对global的阳性存在，不能因当前strong没赢称该结果不存在。** 其比较对象、boundary population、旧聚合/来源范围和后续fixed-target任务不同，也不能据此claim相对强同信息wind/pitch策略优越。

原by_seed第一行明确n_cells187175、seed201、conditionclean、policyglobal，表述应限定该局部历史population。`p1_stats/.../pooled_time_block_bootstrap.json`另有约−22.4M/−23.4M的observed_delta及week-block区间，量纲/聚合尺度与−.568M表不同；本次不拼接这两组CI或借week-block给soft表补认证。旧coverage把这些族笼统WITHDRAWN不提供每行具体失效，不能因此自动宣布此统计比较已被反证；保留为**历史局部阳性、当前确认用途未恢复/来源与目标限制**。

## 5. October纠正后的channel与lag探针：V2遗漏的有界表征知识

权威原source为 `artifacts/raw_replay_20261015_v2/channels/summary.csv`，收据`execution/channels/record.json`，缓存名为 raw replay `cache_wtb`。201–205种子、h1/h6；current assessment 的returned copy与原记录hash逐项相符（`receipt_output_checks.json`、`independent_receipt_checks.json`）。**这认证执行/文件身份，deep动作/统计审计仍未闭合。**

|键|已有结果|能保留的知识|
|---|---|---|
|C2 Active_Power_Only|Brier.0112119，NMI.4612504，ARI.6469264，valid-adjacent transition recall.769703|功率摘要保留标签信息；不是旧62.9%分母|
|C9 Active_Power_Wake|NMI.4627235，ARI.6475978，Brier.0114123|对C2提升很小且Brier略差；wake必要增量未建立，非等价证明|
|C1 Full_Suite|NMI.2258342，Brier.0218475|“更多通道必然更好”不成立于这套固定recipe|
|C3 Reactive_Only|NMI.3535743，ARI.5298320|反应功率也有辨别信息；不能把信息全部唯一归因功率|
|C4 Thermal_Only|NMI1.7218e−5，ARI−8.3247e−5，transition recall0|该单独thermal分类recipe失败，不能说thermal毫无增量价值|
|C5 Direction_Yaw/C6 Wake|NMI.006207/0|这些单组recipe识别弱，不能证明物理上无用|

C2 h6 `delta_vs_direct_h6_kwh=+234,912.8`、C1+957,926.8、C9+377,614.8，不能把表征阳性写成成本阳性。**旧**`artifacts/channel_consequence_ablations.csv` h6曾选 residual index1而非5、用固定direct常数，且invalid-adjacent制造转换事件；这些特定h6/比较/recall主张已证无效。NMI近似一致不等于所有旧字段都有效，也不必把全部表征数值归零。当前契约/registry仍有62.9%残留，与新文件冲突，本次仅标记。

`raw_replay.../downstream_recovery_v1_attempt1/active_power/results.csv`及`report.md`另有七条件35种子行：

- A current+history AUROC.988、AUPRC.719、F1.613；B history-only .982/.540/.468；C lag1-only .984/.708/.587。
- D no-thermal AUROC.969→with-thermal.975、Brier.0247→.0240，但F1.486→.475；E no-active-power .950→.954、Brier.0284→.0257，F1.472→.465。**存在小幅有利描述增量，也有阈值F1反向。** “thermal单独失败”不能推出“thermal加入任何模型均无收益”。
- A/C h6描述成本14,979,235/14,896,401，B15,189,576；这些probe的决策mask额外限制valid-labelled regimes，不是Full，缺少配对检验，不构成lag1成本更优的主张。

report声明训练最多200,000 labelled cells（seed42抽样）、3epochs；源码 `scripts/run_active_power_anchor_audit.py:273–309`有train-only scaler、训练索引存档。当前valid标签按wind/pitch筛选，已知fresh wind能完全分开保留标签；这些结果只支持条件标签可恢复，不证明wind之外的潜物理信息或全体工况有效。

## 6. 修正后的监督与四条件factorial：阳性和负结果同时保留

### 6.1 同骨干监督的当前有界阳性

原表 `raw_replay.../downstream_recovery_v1_attempt1/supervision/paired_seed_statistics.csv` 与 `results.csv`，收据 `execution/downstream_v1_supervision/record.json`（2026-10-16，git3ec8033，Metis路径）。两臂历史pitch都保留，deployment同时将pitch值和mask清零；只有alignment λ5000对0。五种子配对t而非seed×day联合bootstrap。

NMI+0.4550415、CI[.1512876,.7587955]、p=.0141534；ARI+.5379389、CI[.1735916,.9022861]、p=.0148619。h1 Full成本−2,061,829.5，CI[−4,851,907.9,+728,248.9]；h6−1,614,571.8，CI[−4,301,643.7,+1,072,500.1]；Boundary h6−9,957.99，CI[−89,284.67,+69,368.69]。**监督的表征阳性有现成统计支持；决策优势统计未定，不能说其已证无效。** Brier/recall区间也跨零。deep审计仍pending，不能把seed t检验说成天气稳健确认。

### 6.2 四条件，固定同目标的描述阳性

source：`metis_core_recovery_20261015_attempt1/factorial_result_export/aggregate/{summary.csv,all_seed_results.csv,provenance.json}`；同目录report明确20condition×seed runs、11arms、J是C别名，非独立复制。`metis_factorial_numeric_audit_20261015_attempt2/report.json` PBS242732 为 EXACT_ARTIFACT_ARITHMETIC_VERIFIED；它重算保存动作算术，不是原模型完整重新推理。`current_research_assessment_20261017/factorial_h6_contrasts.csv` 已保存：

|h6 C−K|Full kWh|Boundary kWh|Full reserve增量 / shortage增量|
|---|---:|---:|---:|
|clean|+128,217.39|+8,692.37|+718,498.67 / −59,028.13|
|delay6|−62,128.60|+8,078.19|+712,153.47 / −77,428.21|
|pitch_withheld|−5,238.99|+16,235.42|+791,486.47 / −79,672.55|
|both|−130,799.65|+8,206.67|+832,910.67 / −96,371.03|

三项Full点成本有利并伴更低观察违约；清洁场景成本不利。全部Boundary成本不利。没有配对CI时只称描述性条件现象，不能称稳健优势、等价、真正最优、机制必要。fresh-pitch条件中K wind-only不是最强同信息fresh-pitch对照，亦不能用来声称“所有同信息强直接策略”。Boundary是rated band，Transition是未来状态切换后的诊断，两者不可互换。

当前factorial Dense I与Routed C的方向也不能被旧p=.380一句抹平：summary中pitch-withheld h6 Full I16,621,569.225 / C16,153,456.3375（原表键以实际variant匹配）；clean I16,964,646.4375 / C16,286,912.725，Boundary却可能不同。**本次不新算差/CI，不由点结果认证路由必要。** 旧Dense/路由不显著不等于等价；新数字也不证明graph因果。

### 6.3 phase-scan是另一总体，不能借旧吸收率讲普遍规律

`raw_replay.../downstream_recovery_v1_attempt1/phase_aggregate/phase_scan_results_by_seed.csv` 记录canonical-frozen-reference-v1、seed201–205、lead0/5、lag0/1/2/3/6、all/no_pitch。h6/all/lag6五行中phys_recal_shortage **逐行都高于** phys_clean_shortage：seed201为14.58149→15.97658、202为15.84528→16.83450、203为24.46092→25.60853、204为31.08854→31.79053、205为20.74479→21.83854 MWh（源码`eval_single_task_dense_phase_scan.py`明文取`shortage_mwh`）。成本则有好有坏。它保留“校准效应依目标/总体而变”的知识，不能说旧同条件历史吸收36.3%–66.5%在这个新固定目标上仍普遍成立。旧cross-delay population/target未固定导致部分比较撤回；不能把这解释为所有历史local recalibration对照都无效。

## 7. strong baseline：旧有效性、现行候选与审计缺口分开

`artifacts/strong_baseline_closure_summary.csv`旧h6 Full B13,784,320/C14,307,364，+523,044；`strong_baseline_joint_v2/strong_baseline_joint_interaction_v2.json`旧joint interaction−297,565.35，CI[−651,679.77,−18,020.61]。更早CSV seed p均值和CI平均写成“联合显著”无效；joint_v2修正了该统计聚合语义，但**仍是已被当前数值版本替代的旧任务证据**，不能把这次旧joint修复等同全链重现。

当前source `raw_replay.../strong_baseline_retry_import_v1/strong_baseline_closure_summary.csv`，artifact wrapper `strong-baseline-canonical-candidate-20261017/v1`保留同快照。Full B14,979,310/C15,424,949、Transition B4,572,112/C4,643,315、Steady B10,407,198/C10,781,634，保存delta+445,639/+71,204/+374,436。Transition C违约8.48%比B9.77%低、shortage106,068比112,918低，reserve3,582,637比3,442,931高。Full C却reserve更低、shortage和viol更高，不能统一概括成“全场多买reserve更安全”。

当前joint JSON interaction−303,232.337659，CI[−597,952.520900,+19,013.037805]，P≤0=.967。可保留有界transition风险权衡；**不支持已确认异质性**。`docs/EVIDENCE_FREEZE_20261017.md`明确其为canonical-candidate/pending deep action/block/statistical audit，returned receipt/hash已查。缺审计不是统计已反证，也不是准许将有利切片claim-ready。V2未保留这组限定知识；原契约“REFUTED by current closure”字样若被读成正式证伪，应服从同契约pending限定。本次不改契约。

## 8. EXP02：必须纠正“全面证伪”的历史读法

### 8.1 旧版的具体失效，不殃及所有后续分支

`artifacts/exp02-zero-privileged-supervision/v1/zero_privileged_supervision_benchmark.csv` 将Zero-Privileged误列Oracle；旧`full_delta_psrei_pval`其实P(Δ≤0)，旧代码又用Δ<0且p<.05判胜，方向自相矛盾。`docs/REPLAY_CLAIM_DISPOSITION_20261015.md`另明确proxy用了错误power scaler（ε50 val189/test24标签不同）。旧h6+3.435M、20%灾难种子不能沿用作当前“零特权必失败”结论。

### 8.2 当前输出有利点方向、正式统计未闭合

source `raw_replay.../exp02/results.csv`60行，201–205、h1/h6、ε20/50/100、direct MLP、wind-bin、privileged diagnostic；execution/exp02/record.json绑定commit3ec8033、输入residual SHA504998...、输出SHAf2df21...、EXECUTED/exit0、Metis 2026-10-15。CSV以正确primary角色列eps50；h1五种子`full_delta_psrei_mean`都负，h6 eps50三负二正，且ε50没有旧式灾难种子；**不存在所有条件必然更差的证据**。

同目录report正文h1：mean Δ−395,317.6、P=.8935（未达.95）、violation+.0783pp、shortage−12,613.7；h6：Δ−110,081.8、P=.653、violation−1.5632pp、shortage−107,620.1。h6 eps20/100有seed201 reserve0、57.123%违约的大失败，直接MLP亦不稳定。代理表征NMI>0不证明恢复独立物理真值，proxy直接用W/P构造。

**重要冲突**：report Section3又保留h1 eps50CI[−945.9k,−11.9k]、P=.978、h6P=.718，与Section1/2正文.8935/.653不一致；row中的bootstrap均值和report点量也非可无条件互换。执行receipt只绑定CSV输出，不能绑定后来报告每个统计数字为同次联合区间。day_blocks本地未列为返回output。本次不选有利段、不新bootstrap；记录`STATISTICAL_VERSION_CONFLICT / DIRECTIONAL_ONLY`。registry仍列旧h6灾难主arm、旧数值和CONCLUDED，但不能覆盖当前输出，也不能由当前点差升级稳定收益。

## 9. 版本冲突集中登记

本次只登记，不修改原科学契约或registry：Q1/EXP-Q1-001仍有旧62.9% recall，当前valid-adjacent原表为76.9703%；EXP02 registry保留旧primary h6灾难种子，当前eps50没有该失败而ε20/100仍有；EXP02当前report Section1/2与Section3的概率/区间互不一致；旧forecast parameter表的“完全等容量”与实际run参数不一致；旧future/spatial protocol_only状态已被保存run覆盖；旧fair-degradation matrix .933与当前summary .417027、同目录逐seed文件也不一致。strong旧joint非跨零区间不能取代当前跨零candidate；旧校准吸收率不能运送到新固定目标phase。上述冲突均进入CSV对应条目，没有平均区间或挑选有利表。

## 10. 覆盖边界与未核资产

本报告具体读到的来源族包括 paper_runs/paper_suite/cloud_revision 的代表清单和May/June原汇总；paper_assets backup/merged/expanded/strict-refresh；capacity；strictmask validation/baseline/ablation run表和代表训练JSON；checkpoint修复及corrected/strict机制；classweight/July/August trainweight；boundary/time-forward/negative-control/placebo/threshold；future/spatial；September signature/shuffled/no_pab_std/modular；October raw channels/active/supervision/phase/factorial/strong/EXP02及相应receipts与已有独立审计。

覆盖不等于全部文件逐字读完。初版索引为58,377文件/403目录组；根审计补入源目录后更新为58,430文件/407目录组（以最新`INVENTORY_RECEIPT.json`为准）。`DIRECTORY_INVENTORY.csv`确认这些目录存在、规模和表候选数；**本次未独立读取全部400份paper_runs表、全部87份cloud表、每个sensitivity/seed训练日志、完整数组和checkpoint、所有同名备份拷贝**。未核的具体次级族：`anchor_stress_early_warning_wtb_strictmask`、`early_warning_classifier_baseline_wtb`、`boundary_phase_scan`全部子表、`signature_gate_farms_*`各场完整细分（本次读了farm_median_iqr和window_pass汇总）、`breakthrough_20260904`全部逐行账、`p1_stats_20260904`完整统计生成链、`operational_baselines_wtb_strictmask`全部策略、`strict_wtb_evidence_sources_20260609`各副本、old smoke/debug，以及未解包的归档。它们应由全资产表保留为未核/重叠范围，不能称无价值或没结果。

legacy环境与可复现性缺口的细分由`analyses/legacy_cache_alignment_audit_20261018`、`legacy_generation_lineage_audit_20261018`、`legacy_posterior_accounting_audit_20261018`、`legacy_release_hash_audit_20261018`、`legacy_yhat_difference_audit_20261018`与`grokking_legacy_execution_audit_20261018`管辖。本次读过PROJECT冻结摘要，不重做数值、也未证明旧模型全无效。原grokking实例销毁导致原执行联合绑定缺失；新receipt-bound分支不能倒填旧来源，旧来源缺口也不自动否定新分支。

**本次产物是证据盘点，不是科研里程碑完成声明。没有运行新门禁或实验，不能将本文当全项目科学认证、投稿就绪或恢复投入授权。**
