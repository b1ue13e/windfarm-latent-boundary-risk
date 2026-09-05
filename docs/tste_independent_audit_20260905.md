# TSTE 投稿独立严苛审计（2026-09-05 晚）

> 审计口径：不采信任何既有评审文档的结论，直接核对 `paper_tste_ieee.md`、`paper_tste_supplementary.md` 与 `artifacts/` 原始数据之间的对应关系；以 IEEE TSTE Regular Paper（一区）标准裁决。
> 与 09-04 reviewer sim 的差异：本轮覆盖了 09-05 新增的 PCC 聚合定价、Markov-Gilbert 突发丢包、17.6 机年 walk-forward 证据，并做了独立的数字-产物对账。

## 一、一句话裁决

**当前稿件已经跨过"能否投一区"的门槛，是一篇有真实机制证据的 TSTE 候选稿；但存在一处选择性报告（LHB walk-forward 负结果被静默）和一处统计框架弱点，按最严苛标准这两处必须在投稿前处理，否则是把拒稿柄主动递给审稿人。**

预估录用概率（修完本文 P0 后投稿）：**45%–55% 进入 Major Revision 可救区间**；不修补 LHB 披露问题则下调 10–15 个百分点。

## 二、我核验了什么

| 核验项 | 方法 | 结果 |
|---|---|---|
| 主稿 20+ 个载荷数字 vs artifacts 原始 CSV/JSON | 逐一比对 | 全部吻合（含 -6.19M/-4.34M walk-forward、-11.22M PCC、0.933/0.196、16.065M 机制表） |
| 09-04 reviewer sim 的 6 个语义 P0 | 检查现稿与 guard 状态 | 已全部修复（86.54M 方向、ERA5 0.90+、+0.737、claim csv 统一） |
| 提交包时效性 | VERIFICATION_REPORT.md | 09-05 18:55 新包，10 页主稿 + 8 页补充，number guard 通过 |
| walk-forward 模型溯源 | 训练 manifest + 缓存 metadata + 评估脚本 | 见第四节问题 3 |
| 外部场站完整结果 | iec_density_rolling_eval 三个 paired_summary.csv 全量读取 | 发现 LHB 与 ρ 敏感性两处未披露结果 |
| 远程算力 | SSH 实测 192.168.17.251:25329 / :25979 | 4× + 6× RTX 4090 全空闲，可立即补实验 |

## 三、主线成立性判断

当前主线："**与预测联合学习的软边界后验，在确认通道退化时提供可审计的 defense-in-depth reserve 筛查层**"。

这条主线是成立的，而且是经过四个预注册裁决实验（soft-pab 对照、K1 Kelmarsh、K2 多通道分类器、K3 GBDT 定价、K4 dense 等价）反向逼出来的，不是靠措辞包装的。三个机制分工清晰：

1. **定价价值属于联合学习**（joint 16.065M vs GBDT 独立后验 17.656M，1.6M 差距）；
2. **退化鲁棒属于路由结构**（delay6 routed 0.933 vs non-routed 0.286）；
3. **干净观测下物理连续量最优**（soft-pab 15.538M）——诚实披露，反而强化了 defense-in-depth 定位。

这是典型的"证据规格高于方法新颖性"的一区稿形态：学习原理本身（directed-diffusion GRU + dense MoE + anchor alignment）是组合式创新，真正的贡献是**可证伪的证据协议 + 机制归属分解 + 跨场站多年运营验证**。TSTE 接受这种形态，但它决定了本文的上限是"扎实的一线能源系统方法论文"，不是"高影响力方法突破"。

## 四、发现的问题（按严重度排序）

### P0-1：LHB walk-forward 负结果被静默（选择性报告）

`la_haute_borne_rolling_paired_summary.csv` 显示：LHB walk-forward pooled，soft-gate-bin vs global = **+1.01M，CI [+0.285M, +1.755M]**——在 99% pitch 覆盖、边界完全可观测的场站上，gate 分箱显著**劣于** global。该结果已计算、在产物中、在复现包路径上，但主稿和补充材料均未报告（A9g/A9h 只给 Kelmarsh/Penmanshiel）。

- 风险：审稿人跑复现包或要求"三场站统一报告"时直接命中，一篇以"诚实负结果"立身的稿件被发现选择性披露，伤害是加倍的。
- 同时也是机会：这个结果**强化** defense-in-depth 叙事——"边界完全可观测时后验分箱没有存在理由，价值严格条件于可观测性谱系"。主动写出来是加分项，藏着是减分项。
- 动作：补充材料加 LHB rolling 表 + 主稿一句边界条件声明。成本：半天。

### P0-2：外部场站 ρ 敏感性不对称未披露

原始数据显示：

- Kelmarsh ρ=20：gate vs soft-pab = **+0.95M（CI [+0.15M, +1.65M]）**，物理规则反超；
- Kelmarsh ρ=5：gate vs soft-pab = -0.37M，CI 跨零；
- Penmanshiel ρ=20：gate vs global 不显著。

主稿"outperforming physical pitch rules by -2.67M"只在 ρ=10 成立。补充材料对 WTB 披露了 ρ=50 反转，但外部场站只给 ρ=10 单点。

- 动作：A9g/A9h 补 ρ∈{5,20} 列，或明确写"外部结论限于中度缺电惩罚窗口"。成本：低（数据已有，纯披露）。

### P1-1：walk-forward 的 CI 统计基础偏弱

所有 fold 级 CI 都是 n=5 seed-paired bootstrap，只刻画优化随机性，不刻画年际天气变异。审稿人若懂时序统计会问：为什么 2018 和 2024 的差异只用 5 个 seed 的 CI 表示？

- 已有救场证据：fold 级符号一致性（Kelmarsh 6/7、Penmanshiel 4/4 成熟期）本身就是分布-free 的强证据（10/11 同号，符号检验 p≈0.006）。
- 动作：把统计叙述从"seed CI 严格排零"改为"fold 级符号一致性 + seed CI 辅助"，或加 fold-block bootstrap。措辞改动为主，可选补一个 fold 级聚合检验。

### P1-2：walk-forward 只重校准分位数，模型本身冻结

Kelmarsh/Penmanshiel 的 gate 模型是在一个 245 天观测窗（2016 年）上训练一次后冻结，9 年评估中仅 reserve 分位数做 2 年滚动重校准。当前措辞"walk-forward rolling recalibration eliminates concept drift"严格说是**分位数重校准消除了定价层漂移**，并未证明 gate 后验本身 9 年不漂移。

- 好消息：训练窗在测试年之前（2016 训，2018–2024 测），无时间泄漏——我核对了 obs_window 缓存的窗口选取规则，这点是干净的。
- 动作一（低成本）：措辞精确化 + 补一个 gate NMI 随年份衰减曲线（推理即可，无需重训）。
- 动作二（高成本，4090 上约 1–2 天）：做一版模型级逐年重训的 walk-forward，哪怕只报 Kelmarsh。这是把 P1-1/P1-2 同时闭环的决定性实验。

### P2-1：novelty 定位仍需管理预期

学习原理层面无新机制；PCC 聚合、Newsvendor 定价、IEC 61400-12-1 密度校准都是成熟工具的组合。审稿人 Novelty 打分大概率 2.5–3/4。这不可修复，只能靠把"evidence protocol + 机制归属 + 17.6 机年运营验证"作为贡献主轴写满——现稿已基本做到。

### P2-2：真实延迟分布仍未闭环

Markov-Gilbert 突发丢包和 Kelmarsh 99.6% 非网格事件是合理 grounding，但"1–6 步确认延迟在真实系统中的频率"仍无测量。Kelmarsh Status 流有 14,019 条秒级事件，**估计 event-to-confirmation lag 分布是现成的数据、现成的算力、约 1–2 天工作量**，建议做掉；做不到则维持 controlled stress test 措辞（现稿已做到，可接受）。

## 五、已核实的强项（不要动）

1. **机制归属分解表**（soft-pab / rule / logistic / GBDT / joint non-routed / joint routed 六行）：这是全文最有说服力的一张表，定价-退化双维度同时归属，设计上已经接近 causal attribution 的实证极限。
2. **17.6 机年、10/11 fold 排零**：在一区能源期刊中，跨两个商业场站的多年滚动验证属于前 10% 的外部效度证据。
3. **负结果体系**：expert collapse 3/5 seeds、硬路由 disagreement 16.9%、K1 null、Penmanshiel fold1 投产期 +3.8M——全部在稿。这是本文与"调参刷点稿"的本质区别。
4. **工程纪律**：number guard、evidence freeze、提交包 hash 校验、train-only 单一证据源——09-04 的构建链 P0 已全部修复并验证。

## 六、与一区的距离：分维度裁决

| 维度 | 现状 | 一区门槛 | 距离 |
|---|---|---|---|
| 研究问题成立性 | 边界诊断层需求明确，PCC 聚合把问题抬到场站级 | 明确且重要 | **已达** |
| 方法新颖性 | 组合式创新，协议新颖 | 机制或问题新颖 | 边缘，靠证据补 |
| 实验充分性 | 5 种子、强基线、负对照、holdout、4 场站、17.6 机年 | 充分 | **已达且超标** |
| 统计严谨性 | seed CI + BH 校正；但时序不确定性框架弱 | 不确定性量化可信 | **半步差距（P1-1）** |
| 外部效度 | 3 外部场站 + 多年滚动；LHB 负结果静默 | 诚实完整 | **半步差距（P0-1/P0-2）** |
| 运营闭环 | Newsvendor proxy + walk-forward，无真实调度/市场闭环 | TSTE 接受 proxy，但须克制 | 已达（措辞已克制） |
| 写作一致性 | 09-05 后数字-产物一致，guard 通过 | 无内部矛盾 | **已达** |

## 七、投稿前动作清单（按 ROI 排序）

| 序 | 动作 | 成本 | 解决 |
|---|---|---|---|
| 1 | 披露 LHB walk-forward 负结果并改写为边界条件论据 | 半天 | P0-1 |
| 2 | A9g/A9h 补 ρ∈{5,20} 或限定中度惩罚窗口 | 半天 | P0-2 |
| 3 | 统计叙述改 fold 级符号一致性为主 | 1 小时 | P1-1 |
| 4 | Kelmarsh Status 流 event-to-confirmation lag 分布 | 1–2 天（4090 空闲） | P2-2，R3 动机攻击 |
| 5 | gate NMI 年度衰减曲线（纯推理） | 半天 | P1-2 |
| 6 | （可选，决定性）模型级逐年重训 walk-forward | 1–2 天（4090） | P1-1+P1-2 同时闭环 |

1–3 是投稿前必须；4–6 是把 45–55% 推向 60%+ 的增量。

## 八、Kill / Pivot 条件

- 若审稿人要求"证明 joint routing 相对模块化流水线的不可替代科学价值"且不接受 degradation-robustness + 单一部署对象的回答——这不构成 kill，构成**贡献降格**（从"机制贡献"降为"可复现诊断协议贡献"），稿件依然成立但档次下移。
- 若 LHB 类负结果在更多 ρ 或更多 fold 上扩散（如补做 ρ=5/20 后 Kelmarsh 也反转），则 defense-in-depth 叙事需要收窄到"仅 pitch 稀疏场站"，一区定位降为一区边缘/强二区。

## 九、终审一句话

**这篇稿件的证据底盘已经超过多数 TSTE 录用稿，剩下的不是"补实验冲一区"的问题，而是"把最后两处不完整的披露补齐、把统计叙述校准到证据实际强度"的问题。当前最大的风险不是证据不够，而是自己建立的诚实人设被一处选择性报告反噬。**
