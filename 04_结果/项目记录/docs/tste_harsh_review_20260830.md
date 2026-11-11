# IEEE TSTE 投稿严苛评审仿真报告（最严苛视角）

> 评审对象：`paper_tste_ieee.md` + `paper_tste_supplementary.md` + `cover_letter_tste.md`
> 评审日期：2026-08-30 ｜ 目标期刊：IEEE Transactions on Sustainable Energy (Regular Paper, 10 页)
> 评审立场：三位对抗性审稿人 + AE（副主编）综合裁决，按"拒稿优先"原则挑错。

---

## 📊 Executive Summary 与录用概率校准

| 期刊/情形 | 预测结果 | 风险等级 | 说明 |
| :--- | :--- | :--- | :--- |
| **IEEE TSTE（当前形态直接投）** | Major Revision 概率 ~45%，拒稿 ~40%，直接录用 <5% | **High** | 动机循环性与"标签延迟"场景真实性是致命攻击面 |
| **TSTE（完成 P0 修复后）** | 录用概率提升至 ~55-65% | Medium | 诚实边界策略是加分项，但需先把"稻草人对照"修掉 |
| **降级备选（Applied Energy / EAAI / Wind Energy）** | 录用概率 ~70%+ | Low | 当前稿件的完成度对二区期刊已具竞争力 |

**一句话裁决**：这篇论文最大的风险不是实验不够，而是——**在所有防御性免责声明之后，审稿人可能找不到"剩下的贡献"**。稿件诚实地承认了：预测不如 iTransformer、检测不如一个 logistic 回归、备用金策略不如简单物理分箱、跨场迁移失败。AE 会问：那我为什么要发这篇论文？目前的答案是"in-model route provenance"（模型内路由溯源），但这个答案还没有被论证为值一个 Regular Paper 的篇幅。

---

## 👤 Reviewer #1：理论与创新性审查（Novelty Hawk）

**评分：Soundness 2/4 ｜ Novelty 2/4 ｜ Overall 4/10 ｜ Confidence 5/5**

### 致命质疑 1：核心结果是近循环论证（near-tautology）
- Regime 标签 `R^wtb` 是 **Wspd 和 Pab_mean 的确定性阈值函数**（式 3：`u_idle=3.0, u_rated=10.5, p_th=2.0°`）。
- Gate 的 anchor 输入恰恰是 `[Wspd, Pab_mean, s_wake, Patv]`。
- 然后用 λ_align=5000、λ_force=10000 的**超大监督权重**强迫 gate logit 拟合这个确定性函数，最后报告 NMI 0.87/0.94 作为"机制恢复"。
- **这在数学上接近于"模型学会了我们硬编码进去的规则"**。Table A10 已经自证：一个两特征 logistic 回归即可达到 recall 1.000——这恰恰说明标签本身没有需要"恢复"的信息量。
- Table A7/A9 的 outcome-channel 与 zeroing 审计缓解了部分质疑，但没有回答根本问题：**gate 相对"直接计算阈值规则"多提供了什么？** 目前的答案（route probability、residual slicing、provenance trail）是工程叙事，不是机制洞察。

### 致命质疑 2：创新性属于"约束位置的挪动"，理论贡献单薄
- Related Work 把自己的差异化定位为"we constrain the route rather than the prediction"。这是**设计模式的声明**，不是理论结果：没有收敛性分析、没有可识别性（identifiability）条件、没有任何定理说明在什么条件下 anchored gate 能/不能恢复真实控制律。
- λ 权重跨数据集相差 5 个数量级（WTB λ_force=10000 vs ERA5 0.2 量级），论文未给出任何权重选择原则或敏感性扫描。审稿人会推断：**这个框架只在把监督权重调到压制预测损失时才"工作"**。

### 质疑 3：ERA5 支线是故事漂移的残留
- ERA5 用感热通量做热力学 regime，与 WTB 的控制边界故事物理上不同质。主稿已降级为一句话+补充材料，但它的存在让 "observability contrast" 的论证显得拼凑。建议：要么删除，要么把它升格为"边界可观测性谱系"的正式一环并给出统一的形式化定义。

---

## 👤 Reviewer #2：实验与对照审查（Empirical Nitpicker）

**评分：Soundness 2/4 ｜ Empirical Rigor 2/4 ｜ Overall 4/10 ｜ Confidence 5/5**

### 致命质疑 1：headline 运营结果来自有泄漏嫌疑的 legacy checkpoint
- Table A6b 自证：legacy strict-cache checkpoint 的 class weight **不是 train-only 计算的**（train-only rerun 是后来的补救）。
- 而 0.960 recall（6 步延迟）、14.5% shortage 降低、Table II/III 全部运营审计数字，**都出自这个 legacy checkpoint**；干净的 train-only rerun（NMI 0.721 / RMSE 229.93）却没有对应的完整运营审计产物。
- **这构成审稿人可直接引用的拒稿理由**：headline operational claims derive from a checkpoint whose supervision weights were computed with non-training statistics。补救只有一个：用 train-only checkpoint 重跑全部 degradation + reserve 审计。

### 致命质疑 2：主稿缺少完整的预测基准表
- 主稿四个表分别是：机制检查表、标签退化表、备用金表、部署门表——**没有一张标准的全基线预测对比表**（iTransformer / PatchTST / TiDE / GWN / GAT-GRU / Graph Transformer / XGBoost / LightGBM / persistence / power-curve 的 MAE/RMSE ± std 全列）。
- 对一篇以"accuracy price"为核心论点的论文，把价格写在内文散文里而不给表，是不可接受的呈现缺陷。30 个 baseline runs 已经跑了，只需导出。

### 致命质疑 3：标签退化场景的对照是稻草人
- Table II 中 "Rule" 在 6 步延迟下 recall 掉到 0.196——但**延迟的是标签流，不是标签的输入**。阈值规则只依赖 Wspd 和 Pab_mean，而这两个量按论文自己的信息边界（≤t 可用）在 issue time 是实时可得的。
- 一个操作员在 t 时刻可以直接计算 `R^wtb(w_t, p̄_t)`，根本不需要等"confirmed threshold stream"。因此 "delayed rule" 对照构造了一个**现实中不存在的笨对手**。
- 唯一能让场景成立的辩护是：SCADA 质量控制/验证管线确实会延迟"已确认"标签而原始通道先行——但这需要真实风电场 SCADA QC 延迟的文献或数据支撑，目前论文没有给。

### 质疑 4：备用金审计的最优策略不是 gate-bin
- Table III：Boundary/physical-bin 成本 83.78M **低于** Boundary/gate-bin 84.58M。论文主张的 gate-bin 策略输给了"按声明物理边界直接分箱"这个零学习成本的基线。
- 加上 gate 本身被监督去模仿物理边界，gate-bin ≈ 带噪的 physical-bin——这个对比同样接近循环。
- 唯一存活的 claim（same-model gate-bin < global, CI [-4.65M,-2.45M]）是一个**模型内部的对角线对比**，对读者的决策价值有限。
- 单位问题："84.58M 表示 84.58 million reserve-cost-equivalent kWh cells, not currency"——生造单位会让 TSTE 的电力系统审稿人直接皱眉。Table A12 的 MWh/EUR 换算应在主稿就给出。

### 质疑 5：统计与一致性问题
- 5 seeds 达标，A6 有 BH-FDR，值得肯定。但：
  - **anchor-stress guard 数字异常**：去掉 Patv 后 mean NMI 0.881、去 Pab_mean 0.878，**均高于**完整模型的 0.8716。去掉一个"load-bearing"通道反而提升对齐，与 Table I 干预实验（NMI drop 0.702）的叙事张力很大，论文未解释两者是否同一运行族/同一权重协议。
  - A10b 的 lag -3 (0.361) 低于 lag -6 (0.405)，单调性断裂，未讨论。
  - Table A10 中 noise 行 gate 值恒为 0.960（直接复用 clean-route 审计），而 classifier/rule 是在噪声 anchor 上重算的——**同一行内的比较口径不一致**，虽然脚注承认，但表中并置仍会误导。

### 质疑 6：基线时效性与算力披露
- 基线含 iTransformer/PatchTST/TiDE（2023-2024），可接受；但 2024-2026 风电专用 SOTA（如 wake-aware 时空 Transformer、physics-informed 风电预测）只有文字引用没有实验对比。TSTE 审稿人很可能要求至少一个 2025+ 风电专用基线的数字。
- 论文未报告 GPU hours / 训练时长 / 推理延迟。对声称"deployable provenance layer"的系统，推理开销是落地评审的必要项。

---

## 👤 Reviewer #3：动机与落地审查（Pragmatist Critic）

**评分：Soundness 3/4 ｜ Significance 2/4 ｜ Overall 3/10 ｜ Confidence 4/5**

### 致命质疑：这个问题可能是人造的（pseudo-problem）
- 真实风机的控制模式（MPPT vs pitch）**由机组控制器自身决定并实时上报 SCADA**。运行商不需要从模型里"恢复"自己下发的控制律。
- 论文的真实处境是：公开数据集（KDD Cup 2022）没有控制模式字段，所以用 Wspd/pitch 阈值造了伪标签——这是**数据集缺陷驱动的研究**，不是工业痛点驱动的研究。
- "confirmed threshold stream can be delayed" 需要实证支撑：哪个真实 SCADA 系统中，控制模式确认会比原始风速/桨距角通道晚 60 分钟？没有这个证据，整个 label-degradation 故事（论文最强的数字 0.960 vs 0.196 恰恰挂在这里）都建在沙子上。

### 质疑 2：诚实边界策略过度执行，贡献被自我消解
- Cover letter 的 5 条 "honest boundaries" + 正文 Limitations + 补充材料 12 张 claim-boundary 表，加起来让论文读起来像一份预先写好的 rebuttal。诚实是美德，但**当每段主张后都跟着一句"但我们不 claim X"时，AE 会总结为：这篇论文不 claim 任何东西**。
- 建议：把边界声明压缩到一处（Limitations + 一张总表），把省下的篇幅用于正面论证 provenance layer 的独立价值（例如：版本化/校准/监控一体化在真实 MLOps 场景的成本节约案例）。

### 质疑 3：跨场证据的净效果是负面的
- La Haute Borne 复制成功（NMI 0.941）但同一套标签定义（阈值自该场数据估计）；Kelmarsh/Penmanshiel 全面失败（NMI 0.4877 < 0.50）。外部证据的 take-away 变成了"只在桨距角可直接观测且本地重训练时有效"——**这等价于说方法不可迁移**。当前 "deployment gate" 的正面叙事（我们把失败变成协议）是聪明的修辞，但遮不住净负信号。

---

## 📋 官方格式与 Checklist 审计

- [✅] **Claims & Evidence**：每个 claim 都有边界表对应——执行过度（见 R3-质疑 2）
- [✅] **Limitations 章节**：有，且诚实
- [❌] **主稿缺预测基准表**：30 个 baseline runs 未以表格呈现
- [⚠️] **Error Bars & Seeds**：主体达标（5 seeds），但 train-only rerun 的完整运营审计缺失；部分 CI 仅 legacy 包
- [⚠️] **算力/复现披露**：代码承诺 "will be made available"，无 GPU hours/推理延迟；10 页正文达标
- [⚠️] **AI Use Statement**：已声明（仅语言编辑），符合 IEEE 政策
- [❌] **单位规范**："reserve-cost-equivalent kWh cells (M)" 非标准，需全部转为 MWh + EUR 或纯归一化量

---

## 🚨 P0 致命缺陷拦截清单（投稿前 Must-Fix）

1. **[P0-1] 修复循环性攻击面**：正面回答 "gate 相对直接计算阈值规则多提供了什么"。最小方案：在主稿加入一个对比——issue-time 阈值规则直接分箱 vs gate 分箱在**同一信息边界下**的完整对照（目前 threshold rule 只以"延迟版本"出现，从未以"实时版本"公平对比）。如果实时规则打平或胜出，必须改写 contribution。
2. **[P0-2] 用 train-only checkpoint 重跑全部 headline 审计**：0.960 recall、Table II 全部退化场景、Table III 备用金审计，必须从 legacy（类权重非 train-only）切换到干净 checkpoint，否则 headline 数字携带泄漏污点。
3. **[P0-3] 论证或重建标签延迟场景的真实性**：给出真实 SCADA 系统中"确认标签延迟于原始通道"的文献/数据证据；若找不到，把场景改写为"桨距角传感器故障/缺失"（这在工业上真实存在），并相应重做退化实验。
4. **[P0-4] 主稿补全预测基准表**：MAE/RMSE ± std，含全部神经与工程基线，标注 5-seed 协议。
5. **[P0-5] 统一度量口径**：reserve 成本全部改用 MWh + EUR/MWh 或明确归一化；修复 Table A10 同行口径不一致；解释 anchor-stress NMI 0.881 > 0.8716 的倒挂。

## 🧪 最小化补实验清单（按性价比排序）

| 优先级 | 实验 | 预估成本 | 翻转的审稿意见 |
| :--- | :--- | :--- | :--- |
| 1 | train-only checkpoint 全套退化+备用金审计重跑 | 中（管线已有） | R2-致命 1 |
| 2 | 实时阈值规则 vs gate 的公平对照（无延迟、同信息边界） | 低（规则是确定性的，只需评估） | R1-致命 1 / R2-致命 3 |
| 3 | 主稿预测基准全表导出 | 低（runs 已完成） | R2-致命 2 |
| 4 | λ 权重敏感性扫描（λ_force ∈ {0, 100, 1k, 10k} 的 NMI/RMSE 曲线） | 中 | R1-质疑 2 |
| 5 | 一个 2025+ 风电专用 SOTA 基线数字 | 中高 | R2-质疑 6 |
| 6 | 推理延迟 + 参数量 + GPU hours 表 | 低 | R2-质疑 6 / R3 落地性 |

## 🛡️ 预备 Rebuttal 防御策略

- **针对循环性质疑**：不要否认标签是确定性规则——转而论证论文的贡献是**审计协议本身**（route provenance + frozen-quantile reserve screen + deployment gates），并引用 MLOps/模型治理文献说明"可审计性"在并网合规场景是独立价值。Table A7 的 outcome-channel 对比（future power ramp +81.8 kW vs anchor-time Patv -44.1 kW）是唯一能证明"gate 编码了超出阈值规则的信息"的证据，应升格到主稿显著位置。
- **针对稻草人对照**：若实验 2 显示实时规则打平 gate，则把叙事重心从"检测"彻底转向"联合训练带来的 residual-reserve 耦合切片"（A10c 已铺路），承认检测本身无增量。
- **针对动机质疑**：补充 SCADA QC 延迟文献；若无，改用"传感器故障下的降级运行"框架重写 Introduction 第 1 段。

---

## 附：数字一致性抽查（本次评审已核对）

摘要 0.721/0.740/229.93/224.34/236.13/0.960/0.196/0.508 与正文、Table A6b、cover letter 一致；La Haute Borne 0.9408≈0.941 一致；Table I legacy 0.8716/0.9166 与 A6b 一致。**未发现数字漂移**，但发现上述口径倒挂（anchor-stress 0.881 > 0.8716）与同行口径不一致（Table A10 noise 行）。
