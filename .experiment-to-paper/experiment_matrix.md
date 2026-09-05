# 实验矩阵（2026-09-05）

| 家族 | 协议/对象 | 重复 | 核心观察 | 可支持 | 状态/边界 | 主要来源 |
|---|---|---:|---|---|---|---|
| WTB 预测基准 | 同 strict-mask 缓存；iTransformer、GWN、TiDE、PatchTST、Dense、MoE | 多数 5 seeds | iTransformer 224.34；GWN 225.74；train-only router 229.93；legacy router 236.13 | 路由有明确但有限的 RMSE 代价 | 完成；不能声称预测 SOTA | `paper_tste_supplementary.md` A13；`artifacts/paper_assets/tables/table_main_benchmark.csv` |
| 路由对齐 | WTB declared MPPT/pitch boundary | 5 seeds | legacy router NMI/ARI 0.8716/0.9166；train-only 0.7208/0.7398；unconstrained MoE NMI 0.014 | 监督后验能恢复 declared boundary | 完成；不是 anchor-free discovery | 主文 Table I；补充 A6b |
| 干预与负对照 | boundary-anchor zero、wake zero、时间/空间置换 | 5 seeds | boundary-anchor zero 使 NMI/ARI 降 0.702/0.859；wake zero 近零；placebo 明显低于实际 | declared boundary anchor 是 load-bearing source | 完成；主要是 legacy 完整审计链 | `strict_wtb_mechanism_effects.csv`、`strict_wtb_placebo_effects.csv` |
| 时间/空间 holdout | withheld turbines、future block | 5 seeds | held-out NMI 0.834；future NMI 0.835 | WTB 内部可迁移 | 完成；不等于跨场参数迁移 | 主文 Table I |
| WTB withheld-channel | 去 Wspd/Pab；再去 Patv；标签置换 | 5 seeds | signature_full NMI 0.561；core 0.367，3/5 expert collapse；shuffled 约 4e-6 | 边界不只是定义通道阈值重放 | 完成；core 稳定性弱 | 主文 Table II；补充 A9b |
| LHB replication | 相同阈值、从头训练 | 5 seeds | canonical 0.975；signature_full/core 0.674/0.575；shuffled 1.92e-4 | 跨场边界 signature 可复现 | 完成；是 re-trainability，不是 parameter transfer | 补充 A9c |
| Partial-pitch farms | Penmanshiel 78%、Kelmarsh 55%；输入盲窗口 | 主窗 5 seeds；扫描 3 seeds | signature_full 0.302/0.340；Kelmarsh core 0.378；Penmanshiel core 0.195；4/4 扫描窗逐 seed 通过 0.20 | 异质可观测条件下仍高于 chance | 完成；结果不随 pitch coverage 单调 | 补充 A9d--A9f；`farm_median_iqr.csv` |
| 公平退化 | gate 与 rule 同时退化 issue-time Wspd/Pab；噪声作用于历史与当前 | 5 seeds | delay6 gate/rule 0.933/0.196；strong noise 0.951/0.680；stalled-history upper bound 0.416/0.196 | 路由后验在定义退化协议下更稳健 | 完成；延迟仍是 controlled stress test | 主文 Table II；补充 A10d |
| 非路由联合头 | 同 encoder、joint posterior、无 routing | 5 seeds | delay6 recall 0.286；soft-dense cost 16.076M vs routed 16.065M，差异未检出 | 联合学习解释定价，路由解释退化鲁棒性 | 完成；未预设等价界，不能声称统计等价 | 主文 mechanism table；补充 A11d/e |
| 独立分类器 | Logistic 与 GBDT consequence-channel controls | 5 seeds/固定验证拟合 | clean logistic 更强；GBDT delay6 0.868、noise 0.804；GBDT soft pricing 17.656M | 鲁棒性不是简单阈值效应；独立后验未自动获得定价价值 | 完成；GBDT 并非穷尽所有模块化方案 | A10、A11c/d；`multichannel_classifier_results.csv` |
| 软后验定价 | boundary band、rho=10、validation-frozen quintiles | 5 seeds | global 16.632M；joint soft 16.065M，delta -0.568M CI [-0.726,-0.406]；soft physical 15.538M；GBDT 17.656M | 学到的软后验在 global 之上提供风险分层 | 完成；不优于干净物理连续量，与 physical-bin 差异跨零 | A11b--A11e；`unified_control_table.csv` |
| 硬 route reserve audit | boundary subset、rho=10、另一聚合管线 | 5 seeds | router global/gate/physical 99.55/95.13/93.82M；GWN physical 84.31M | 同模型 gate-bin 优于 global | 完成；不能与 16M 软后验表混作同一尺度 | 主文 Table III；`reserve_decision_summary.csv` |
| 外部 reserve | Kelmarsh sparse farm | 5 seeds | joint soft vs global -0.04M，CI [-0.20,+0.13] | 外部场站尚未检出定价增量 | 完成的负结果 | A11d/e；`kelmarsh_reserve_by_seed.csv` |
| 运营 grounding | Kelmarsh Status 异步事件流 | 描述统计 | 14,019 个事件，99.6% 位于 10 分钟网格之间 | 确认流异步具有现实基础 | 完成；未测得真实固定延迟分布及经济后果 | 补充“Kelmarsh asynchronous event-stream grounding” |
| ERA5 对照 | thermodynamic observability | MoE 5 seeds；baseline 3 seeds | 表格记录 Physics-Aligned MoE NMI 0.210、Unconstrained 0.032 | 最多作弱可观测性对照 | **冲突**：补充文字声称 NMI 0.90+，未被最终表支持 | 补充末节；`table_routing_quality.csv` |
| 统计与复现 | paired bootstrap、Bonferroni、week-block bootstrap、package guards | 5 seeds；35 test days | 13-family 结论经 Bonferroni 后方向保留；包内 43 项 token check 通过 | 主要 WTB 结论有重复和多重比较控制 | 部分完成；block-bootstrap 与主表量纲需统一说明 | A11e；`p1_stats_20260904/`；最新 verification report |

## 不可直接合并的口径

1. 229.93 的 train-only headline 与 236.13 的 legacy 完整审计 checkpoint 不应混成同一模型结果。
2. 95.13M/99.55M 的硬 route reserve audit 与 16.065M/16.632M 的 soft posterior boundary-band audit 是两条不同聚合管线，不能横向排序。
3. seed-paired CI 描述训练随机性；week-block bootstrap 描述时间相关性，二者不能互相替代。
4. 外部场站的 signature recovery 与外部 reserve value 是不同主张；当前前者为正、后者未检出。
