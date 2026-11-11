# Metis 外部确定性版本的限定证据核对 — 2026-10-15

当前状态：VERIFIED（仅新版本固定权重推理、决策计算和统计复核）。整个原始数据重跑、46项覆盖及论文核对尚未完成。旧版精确复现失败仍为 FAILED / UNCERTIFIED。

## 真实失败与修复

原生产242600虽退出0，独立GPU审计242736却退出1：Kelmarsh seed201验证集的保存gate与同权重、同输入的新推理不逐值相等。完整失败日志、源码、输入身份和非相等数组已归档；10文件、822276bytes的归档SHA256为201c76a3166b26630c8023a7923016d13fdc2037a457a952fb7c8ac4f89b1181。原输出未覆盖，旧版通过精确复现的结论已撤回。

注册后的PBS诊断242739退出0。同一固定输入的两次默认推理有49156个float32值不同，最大差7.152557373046875e-7；预先声明的确定性配置重复推理逐值相等。确定性结果与旧结果仍不同。此证据说明该输入下观察到的重复性差异；旧进程未记录的后台配置和具体核函数原因仍UNKNOWN，不把argmax未变称为无害，也不改精确门槛。

新版本deterministic_matched_transfer_v1使用既有完整训练权重，未重训或部分续训。先注册，再通过真实GPU预检242740、生产242741、独立新进程GPU审计242742和独立CPU版本比较242745，均实际F/exit0。科学基线、输入窗口、5种子、q0.90、rho10、dt1/6、原5000次两阶段重采样及随机数种子20261014保持原定义。

## 原始产物与复核来源

- 生产输出与收据：云端artifacts/raw_replay_external_models_20261015/deterministic_matched_transfer_v1及execution/deterministic_matched_transfer_v1/record.json。
- 新审计真实报告：[audit_report.json](../artifacts/metis_external_deterministic_20261015_attempt1/audit_report.json)；程序源码scripts/audit_metis_external_transfer.py及不可变部署包manifest.json（source commit cf820b7）；报告自身记录部署包与源码SHA。
- 版本比较：[report.json](../artifacts/metis_external_version_comparison_20261015_attempt1/report.json)。直接核对20个key、来源权重、训练摘要、评价样本数和风速基线成本/违约率精确不变；它没有直接逐值比较旧新全部mask/time/node数组。新版本的逐样本target/mask/time/node身份由GPU审计另行绑定。
- 快照20261015T154812Z_bdce736a：829文件和34对完整PBS命令输出流独立验SHA通过。运行中的通道日志仅代表该时刻可见字节，不是最终日志。证据见artifacts/metis_heartbeat_20261015_2232/final_verification.json及快照index.json。
- 生产numeric_execution_profile.json额外回传，495bytes，SHA256 9e64c38c5b28de9fab48bb87c2ce95e5e053373119b446b3cd6d6f6dd5b28924，与快照生产收据匹配；逐字段比较见[producer_profile_verification.json](../artifacts/metis_external_deterministic_20261015_attempt1/producer_profile_verification.json)。只允许实际host/PBS job不同，14个配置/软件/GPU字段均相同。

原始数据SHA→原始窗口缓存/训练清单→完整WTB门控权重和当地冻结点预测→保存gate/真实目标及mask/time/node→逐cell动作与原生块→种子CSV→两阶段统计全部在该限定分支有机器可查记录。45模型产物的独立审计242626只证明已有训练产物/记录身份，不替代其他实验或全论文认证。GPU审计复用冻结helper，不能表述为完全独立的算法实现。

## 不筛选方向的结果

此处“成本”为PSREI代理惩罚能量（kWh），不是货币利润。Δ定义为后验策略代理成本减去当地风速分箱基线代理成本，正值表示惩罚更高。每组5种子、35个连续144个合格issue索引块（最后块可不足144），不是自然日/天气事件对齐保证。区间来自两阶段种子×块5000次重采样；P(Δ≤0)是经验概率，不是经典双侧p值。

| 场站 | 预测步 | 平均Δ (kWh) | 95%区间 (kWh) | P(Δ≤0) |
|---|---|---:|---:|---:|
| kelmarsh | h=1 | +31,325.120290 | [-12,858.182225, 83,684.097164] | 0.0858 |
| kelmarsh | h=6 | +6,322.697575 | [-31,417.261401, 46,732.590610] | 0.3636 |
| penmanshiel | h=1 | +230,645.731683 | [65,048.036971, 431,709.872189] | 0.0014 |
| penmanshiel | h=6 | +356,014.397853 | [162,798.520598, 566,245.720865] | 0.0002 |

主终点h=6：Kelmarsh未建立相对风速基线的成本改善（区间跨0）；Penmanshiel在当前协议下存在成本惩罚。h=1同样完整保留，不选取有利场站或步长。版本比较观察到20行后验成本与违约率恰好不变，不能据此把旧gate精确失败改为通过。

这些结论仅限当前两个原始数据窗口、既有WTB门控权重、双方共用的当地冻结点预测及当地验证校准。外部后验使用原gate[...,2]五个分位箱，风速基线十个验证分位箱、min_n30/global fallback；不要与四条件族的前三类归一化后验混为同一实现。历史训练使用特权pitch；推理时physics Pab_mean与history Pab_mean/std均屏蔽。该证据不认证完整零样本流程、历史从未记录pitch、pitch-free点预测、跨硬件重新训练逐值一致性、图因果必要性或电网市场价值。

## 余项与审查边界

四条件20次运行及880行/176组的保存产物算术审计已另有限定PASS，见FACTORIAL_V2_EVIDENCE_20261015.md。本快照core242628仍R，通道进展至C6（仅部分）；后继诊断242629仍H，不能记作完成。尚有EXP02/EXP03、其他覆盖族、逐项表图/论文一致性、最终独立科学与证据审查。任何未复现的旧结论保持撤回。

独立审查文件位于同一新分支目录independent_evidence_review.txt和scientific_falsifier_review.txt；其范围仅为本分支。最终全项目门控仍应失败直到剩余真实要求满足，不得修改门槛让其通过。
