# 补查：历史预算、可靠性、分类器与归档

2026-10-20。仅读已有文件；数值均抄录已存字段，不作新均值、区间、显著性或策略计算。以下补充三个角色报告之外的目录责任，不把历史结果升级为现行确认。

## H01 历史同预算前沿与风险重分配

`artifacts/matched_budget/provenance.json`绑定2026-09-22、git621bb8b、五seed201–205、h6、rho10、trainweights缓存、旧fixed residual和classifier checkpoint。`frontier_auc_summary.csv`包含Full/Steady/Transition各5行：例如Transition seed201的AUC delta U为−3099.1407、favorable support60%，seed202为+4347.6014、support0；其余Transition203–205均为正。Full除seed202外也为正。不能只取seed201局部有利区间宣传普遍分配优势。

`mechanism_reallocation_diagnostic.csv`五行的net_preferential_reallocation均为正（7.56035/.52040/1.38227/.34341/2.64653），但相关系数有正有负；这说明所存程序对已发生shortage格和非shortage格分配不同，不证明线上可识别或信息因果贡献，更不抵消前沿的不利/混合结果。

`frozen_policy_rho_sensitivity.csv`保持Transition ΔR149241.3311、ΔU−3650.2639，表中rho10成本差+112738.6926，rho41为−419.4868。`reoptimized_rho_sensitivity.csv`是另一问题：允许每个rho改变策略。**固定动作改变评价权重与改变策略最优档位不能混为一条经济规律。**这组旧数据有风险/预算权衡内容，但使用旧模型/目标，不可代替20261020 state controls开发预算匹配，也不能作为实际电价或接受证明。未载入其cached_posterior_probs或重新计算前沿。

## H02 历史iso-reliability比较确实运行并有复杂度替代结果

`artifacts/decisive_fair_risk/decisive_cross_seed_aggregate.csv`与`benchmark_report.md`列五seed、h1、clean/delay6/markov_burst/sensor_noise及8种配方。delay6的Frozen Backbone + Residual Quantile平均cost1284098.2、V9.7%，Joint Routed1412321.5、V10.6%；clean的GBDT574821.7、V7.6%，Joint Routed660989.7、V7.2%。这些原表支持不同复杂度/风险—成本取舍，不能宣传每场景同一冠军。

原report标题里同时出现“validation multipliers”和“FROZEN on test set”，措辞本身不能证明严格的历史隔离。`route_dispatch_verdict.json`中`dense_vs_moe_equivalent=false`也不等于已完成等效检验。其旧boundary总体、forecast/时钟及校准身份应保持历史范围；本次没有重走完整生成链。不能用该旧表挽救现代共同目标上的普遍部署地图，也不应说项目从未比较过简单GBDT、sequence classifier或模块化量化。

## H03 历史强分类器和非路由对照

`artifacts/breakthrough_20260904/multichannel_classifier_results.csv`记录：gbdt-cons的delay6 recall.8675676、precision.3902736，noise_shared recall.8040541；logistic-cons delay6 recall.4554054。原表没有seed列，不补造五seed显著性。

`dense_fair_degradation_summary.csv`另有5seed汇总，delay6非路由头recall.2862162，对照规则.1959459。它不是当前对称历史退化的routed summary .417027，也不是旧未完全shift历史的.933。几种程序/信息访问不同，不能把这些点值拼成路由因果效应；可保留“独立简单分类器也能提取退化条件下的标签信号”的具体对照。

同目录`dense_pricing_by_seed.csv`、`gbdt_reserve_pricing_by_seed.csv`、`kelmarsh_reserve_paired_summary.csv`为原局部定价/外场补充，角色报告已覆盖相应弱global、physical-bin及外场统计边界；本补查不重复换算。

## H04 直接分位数基准不止风速分箱

`artifacts/direct_quantile_baselines_summary.csv`有40行、4条件×2horizon×5模型。clean h1：Wspd-bin cost7139155、GBDT6494554.055、Direct MLP6693867.5；clean h6：Wspd-bin14545608、GBDT15665274.893、MLP14015895。horizon会改变排序；风险率也不同，不能只按cost叫全面更优。该表没有seed列/联合区间，来源及是否所有参数匹配本次没有完全闭合。

这仍证明已有直接GBDT/MLP比较资产，不能把“复杂状态模型没赢”扩成“从未出现神经模型有利点估计”。表的存在和有利点估计不等于稳定收益或同信息最优。

## H05 历史归档不是遗漏的新实验集

对`archives/`下3个压缩包只读取成员目录，生成`HISTORICAL_ARCHIVE_INDEX.csv`共70成员。195MB的derived zip只含两个旧NPZ；March cloud tar是旧paper表、图和汇总；code.zip是代码/测试/字节码。本轮没有载入数组或运行旧代码，不能把归档副本计成另一份独立实验。

`archives/raw_results/*.xml`实际以diagrams.net的mxfile开头，是图形源，不能因文件夹名叫raw_results就当实验数据。`backups/`六JSON是wiki/import备份，`revision_outputs/`为修稿和论证记录；它们不是独立科研运行。旧修稿账本称PCC过渡节省1.33M时，实际比较对象是soft-pab而非global；“微风场缺空间冗余导致失败”等归因没有对应因果识别，不能回收为新机制。保留原文及其范围问题，不改旧文件。

本补查补齐目录职责，不声称这些历史分支全链可复现或领域新颖。各来源在完整资产表有原路径/大小/时点；重要来源的最终哈希另由主审绑定。
