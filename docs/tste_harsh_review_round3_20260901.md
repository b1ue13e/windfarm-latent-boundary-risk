# 顶刊严苛评审仿真报告 · 第三轮（投稿包 vs 自有证据的完整性裁决）

> 评审对象：`paper_tste_ieee.md` + `paper_tste_supplementary.md` + `cover_letter_tste.md` + 仓库内 artifacts 证据（本轮全部独立核验，不引用前两轮结论代替核验）
> 评审日期：2026-09-01 ｜ 目标期刊：IEEE TSTE（Regular Paper）
> 评审立场：三位对抗性审稿人 + AE 综合裁决，拒稿优先原则。
> 与前两轮的关系：第一轮（循环性/泄漏 checkpoint/稻草人对照）与第二轮（稿证矛盾/窗口选择/种子崩塌）的 P0 **绝大多数仍未在当前投稿包中修复**。本轮重点：(a) 用仓库内证据逐项实锤"未修复"清单；(b) 提出前两轮未覆盖的**新攻击面**，其中两条属于完整性（integrity）级别，比任何实验缺陷都更接近 desk reject。

---

## 📊 Executive Summary 与录用概率校准

| 期刊/情形 | 预测结果 | 风险等级 | 说明 |
| :--- | :--- | :--- | :--- |
| **TSTE（当前投稿包直接投）** | 拒稿 ~70%，Major ~20%，录用 <5% | **Critical** | 投稿包内部、以及投稿包与仓库证据之间**互相矛盾**，且全部可被审稿人从复现包中直接发现 |
| **完成本轮 P0（证据切换+叙事迁移）后** | Major→Accept 路径 ~50-60% | Medium | 干净证据已全部存在于仓库/远程，缺的是"把论文改写为与证据一致"而非补实验 |
| **若 E1/E3 软信号无法官方化或窗口扫描失败** | 转投 Applied Energy / Wind Energy | — | 当前稿件的"审计协议+软后验风险分级"故事对二区刊已具竞争力 |

**一句话裁决**：这篇论文现在最大的敌人是它自己的仓库。摘要宣称 Kelmarsh/Penmanshiel "fail the observability and held-out routing gates"，而仓库内 `artifacts/external_wind_guard_windowfix/external_wind_guard.json` 白纸黑字写着 `cross_site_mechanism_passed`（80/80 运行，NMI 0.5574 ≥ 0.50 门）；补充材料 Table A6 宣称 gate NMI 相对 full MoE "+0.040, positive"，而项目自己的官方 stat-pack 在干净口径下给出 **-0.109 [-0.280, +0.084], p=0.352，方向反转**。审稿人只要运行复现包，这些矛盾全部自爆。**先让论文与自己的证据一致，再谈任何科学性辩护。**

---

## 🚨 第 0 部分：完整性级发现（先于一切科学评审）

### F0-1 部署门叙事四处与仓库 guard 直接矛盾（可被复现包实锤）

| 位置 | 投稿包现状 | 仓库内自有证据 |
| :--- | :--- | :--- |
| 摘要（`paper_tste_ieee.md` L36） | "Kelmarsh and Penmanshiel **fail** the observability and held-out routing gates" | `external_wind_guard_windowfix/external_wind_guard.json`：`status=cross_site_mechanism_ready`、`claim_gate=cross_site_mechanism_passed`、80/80 运行、NMI 0.5574≥0.50、ARI 0.5652≥0.30 |
| 正文 L336 | "Kelmarsh and Penmanshiel remain deployment-gate **failures** because pitch observability and boundary-cell support are insufficient" | 追加五/六已实锤：Kelmarsh 2016 原始数据 pitch 覆盖率 65.5%，"coverage 0.0000" 是本项目**窗口选择管线的假阴性**（`9c28c26` 已修复），不是数据缺失 |
| 讨论章部署门表（L422） | "mean external NMI **0.4877** … below the 0.50 NMI criterion" | 新窗口协议下 0.5574 过门；旧 0.4877 是头部窗口协议的产物 |
| 补充材料 Table A8 | "80/80 runs complete; mean NMI 0.4877 below threshold 0.50 → No-go"；"pitch-feature coverage 0.0000" | 同上，且 A8 的"pitch coverage 0.0000"一行已被团队自己的根因分析证伪 |
| Cover letter L19 | "the Kelmarsh/Penmanshiel pair, **which lacks pitch observability**" | 事实错误。Kelmarsh 有 pitch（65.5%）；这是给编辑的事实性误述 |

**性质**：这不是"旧数字没更新"，而是投稿包陈述与复现包 guard 输出的**方向性矛盾**。若审稿人运行复现包，会发现论文宣称的负面结论在仓库内已经翻案——轻则 Major 并要求解释，重则质疑作者是否了解自己最新证据。

### F0-2 机制对比符号在补充材料中仍是被官方统计推翻的旧口径

补充材料 Table A6（`paper_tste_supplementary.md` L221-222）：
- "Gate NMI vs full physics-aligned MoE **0.040** [0.008, 0.071], positive but not FDR-significant"
- "Gate ARI vs full physics-aligned MoE **0.035** [-0.000, 0.078]"

项目官方 reviewer-stat-pack（train-only 口径，5 seed 配对，见 `tste_trainonly_rerun_results_20260830.md` 追加二）：
- NMI Δ = **-0.109** [-0.280, +0.084], p=0.352；ARI Δ = **-0.138** [-0.356, +0.088], p=0.379。**符号反转且 CI 跨零。**

**连带后果（前两轮未充分展开的精确表述）**：boundary-forced 变体当初"selected for gate recovery"（主文 L287）是在**带污点的 legacy 类权重**下做出的选择；干净权重下 full stack（多 L_aux+L_smooth）对齐更高（0.830 vs 0.721）。即：**模型族内的变体选择本身被同一个 provenance 问题污染**。摘要 headline 变体的存在理由必须重写为干净口径下仍然成立的差异化价值（见 R1-2）。

### F0-3 Headline 运营数字全部仍是 legacy 口径，而干净数字已经存在

| 数字 | 投稿包现值（legacy _checkpoint，类权重非 train-only） | 干净口径已有值（5 seed，追加一/二） |
| :--- | :--- | :--- |
| 6 步延迟 gate recall | 0.960 | **0.9705 ± 0.0299** |
| 6 步延迟 recall gain | +0.764 | **+0.775** |
| gate precision（clean anchor） | 0.759 | **0.630 ± 0.108** |
| shortage 降低 | 14.5% | **≈16.9%**（-0.637M [-0.976,-0.300]） |
| Δcost（gate-bin − global） | -3.55M [-4.65M,-2.45M] | **-4.42M [-7.36M,-1.27M]** |
| Table III 三行 router 数字 | 88.13M/84.58M/83.78M | **99.55M/95.13M/93.82M** |
| full 族 reserve 三行 | 缺 | 95.89M/91.62M/90.39M（新） |

摘要的"two evidence packages are kept distinct"框架（L36）在追加一之后已经过时：干净 rerun **已有完整退化+备用金审计产物**（远程 `artifacts/early_warning_trainweight_5seed_20260830/`、`decision_reserve_trainweight_full_20260830/`，guard 全绿），继续把 headline 挂在类权重有 provenance 污点的 legacy checkpoint 上，等于主动选择较弱证据。且摘要只字不提 legacy 包被替换的**原因**（类权重非 train-only），把两套包呈现为平等的"trade-off 双包"——这是披露失败。

### F0-4 一致性审计工具锚定旧证据，绿灯是假象

`artifacts/tste_number_consistency_audit_polish3/tste_number_consistency_audit.json`：44/44 通过。但其设计是"文档 token 与**声明的源 artifact** 一致"，而源 artifact 全是旧证据。**该工具保证的是"论文与旧证据一致"，恰与当前需要相反。** 同理，`tste_final_read_checklist.md` 第 4 条把 "0.4877/0.5112 不过门"写成**通过标准**——团队的质量门本身还锚定在已被证伪的叙事上。所有 guard/checklist 的 token 清单必须随证据切换更新，否则机器检查会持续给旧叙事发绿灯。

### F0-5 图与派生资产全部是 rerun 之前的产物

`artifacts/final_evidence_package/export/figures/` 核心图（figure2/4/5/6）时间戳 **2026-06-18**，早于 train-only rerun（08-30）与窗口修复（08-31）。Figure 4（routing evidence：WTB 运行平面+混淆矩阵）是 legacy checkpoint 的可视化。证据切换后图必须重生成，否则正文数字与图内数字会出现新一层不一致。

---

## 👤 Reviewer #1：理论与创新性审查（Novelty Hawk）

**评分：Soundness 2/4 ｜ Novelty 2/4 ｜ Overall 4/10 ｜ Confidence 5/5**

### R1-1（致命，存续并收窄）：循环性的终审判决已出，论文还没签收

E1 pilot（追加三）已经用项目自己的数据给"gate 发现规则之外的有效边界"判了死刑：gate-rule 硬分歧处，**规则**条件均值拟合未来功率好 753 kW，gate 仅在 5.3% [3.0%, 7.7%] 分歧细胞上更优。当前稿件的中心叙事（"auditable assignment that links an issue-time route to a declared operating boundary"作为 headline 贡献）仍停留在硬路由外延上。**存活的、确定性阈值规则原理上给不出的增量只有两个**：
- 软后验类内风险分级：rule=MPPT 类内 P(pitch) 与结果残差 Spearman ρ=0.183 [0.123, 0.227]，5/5 种子同号；
- 路由不确定度定价：gate 不确定度 vs 预测误差 ρ=0.391 [0.299, 0.482]；
- 以及 E3 的操作化：软分箱比 global 少 6% reserve（-617k [-984,-278]）、pinball 显著更优（-1.82 [-2.33,-1.30]）、与 physical-bin 成本打平。

这三个 pilot 不进主稿，循环性质疑在二审必然回来，且这次没有任何新证据能再挡一次。

### R1-2（新）：headline 变体的存在理由必须在干净口径下重建

干净口径下 boundary-forced 变体对齐**低于** full stack（0.721 vs 0.830，p=0.352）。该变体继续担任摘要主角的合法理由只剩：(a) 边界带 RMSE 显著优于 full 族（-4.58, p=0.001，官方 pack）；(b) 0.5-std 边界 anchor 噪声退化 5.78 vs anchor-only 105.56；(c) 退化标签 recall gain +0.775；(d) 同模型 reserve 诊断 Δcost -4.42M CI 不跨零。这四条目前分散在正文角落，摘要和贡献段一条都没用上。**注意纠正第二轮评审的一处错误**：无约束 MoE 并未"自己就能对齐"（主文 L342：NMI 0.014，不过门）；翻转的是"boundary-forced 是全族对齐最优变体"，不是"物理约束无用"。后续 rebuttal 措辞必须精确，否则会被审稿人抓第二轮错误。

### R1-3（新）：La Haute Borne 的"replication"用词过度

LHB 的证据结构是：阈值由 **LHB 本地数据估计** + 模型**从头重训** → NMI 0.941。跨场迁移的参数为零、阈值为零。这在方法论上证明的是"**anchor 可观测时机制可再训练（re-trainability）**"，不是任何意义上的 transfer/replication of a learned artifact。且它和 WTB 主结果一样落在一个近循环结构里（监督 gate 拟合其输入通道的阈值函数）。建议措辞降级为 "anchor-observable re-trainability check"，并把它正式定位为"可观测性谱系"上的一点，与 ERA5（信号自可见）、WTB（部分隐藏）、Kelmarsh/Penmanshiel（部署门控）形成统一的 observability spectrum 形式化——这也顺带解决第一轮指出的 ERA5 故事漂移问题。

### R1-4（新）：文献结构的两个硬伤

1. **零风机控制文献**。论文标题主打 "MPPT-to-Pitch Boundary"，但 `references.bib`（50 篇，2025×8 + 2026×2，时效尚可）中**没有任何风机控制经典文献**（region 2/3 过渡控制、MPPT/变桨切换的工程定义与动力学）。TSTE 的电力系统审稿人会首先找这类引用；缺失会被读为"作者用 ML 视角 reinvent 控制边界概念"。
2. **"conformal-style" 术语误用**（主文 L272）。验证集经验分位数≠conformal prediction：无交换性论证、无覆盖保证，且 E3 实测条件覆盖率本就偏移（physical-bin 0.868/0.911）。这个词会吸引统计审稿人的火力，建议删除或改为 "validation-frozen empirical-quantile screening"。

### R1-5（新）：与 KDD Cup 2022 官方基准的关系未讨论

稿件使用自定义协议（H=36/P=24、strict-mask、自划 180/30/35），但未交代与已发表 KDD Cup 2022/SDWPF 基准结果的可比性。熟悉该数据集的审稿人会问：224-236 的 RMSE 落在官方榜单什么位置？至少需要一段"协议差异声明"。

---

## 👤 Reviewer #2：实验与结果审查（Empirical Nitpicker）

**评分：Soundness 2/4 ｜ Empirical Rigor 3/4 ｜ Overall 4/10 ｜ Confidence 5/5**

### R2-1（致命，新表述，比前两轮更尖锐）：标签退化场景目前没有任何自洽的部署语义

逐层推导：
1. 阈值规则 `R^wtb` 的输入是 issue-time 的 Wspd 和 Pab_mean（Table A2：两者均为 ≤t 输入）；gate 的 anchor 是**同一批物理通道**。
2. 因此任何"让规则退化"的场景（延迟/缺失/加噪），按同一信息边界**必然同样退化 gate 的 anchor**。Table II 中 gate 列恒为 0.960（所有退化行不变），恰恰因为 gate 从未被退化——这不是实验结果，是场景构造的恒等式。
3. 唯一能让"rule 退化而 gate 不退化"自洽的解读是：存在一个**独立于原始通道的 QC 确认流**，原始通道先到、确认标签后到。但 (a) 论文未提供任何真实 SCADA QC 延迟文献/数据；(b) 在该解读下，操作员本可以用原始通道直接算规则——规则又活了。
4. 结论：论文最强的数字（0.960 vs 0.196）挂在一个**语义上尚未定义清楚**的场景上。两条出路：(i) 用 Kelmarsh 真实资产 grounding（`Lost Production to Curtailment` 运营商归因流 93.7% 覆盖 + Status 事件流带 IEC 类别和精确时间戳——确认确实晚于原始通道的真实工业对应物）；(ii) 改为**公平退化**：传感器故障/加噪同时作用于 gate 与 rule 的输入，补 test-time gate-under-degradation 的退化行（目前只有 rule/classifier 被退化，gate 的 anchor-stress 只在训练层、且测的是 NMI 不是 early-warning recall）。

### R2-2（新）：n=5 种子配对 bootstrap 是统计上的阿喀琉斯之踵

headline reserve claim 的全部 CI 来自 5 对种子差值的 bootstrap（A11 脚注）。5 对样本的 bootstrap CI 极不稳定，且无法捕捉时间维度的相关结构；审稿人完全可以要求 (a) 时间块 bootstrap（test 期按日/周分块）或 (b) 增加种子数。更根本的是：E1 已实锤硬路由跨种子剧烈波动（分歧率 1.6%–44.6%），**mean±sd 的呈现方式掩盖了路由指标的分布形态**——median/IQR + 收敛状态分层（gate 熵阈值）必须成为所有路由指标的标准报告格式。WTB 主运行至今没有任何收敛分层（seed 203 的教训只在跨场方向做了诊断）。

### R2-3（存续未修，逐项实锤）

- **早停盲区**：早停只看 val_rmse，seed 203 在路由器熵 1.16-1.22（健康 0.12-0.24）时被锁定（best_epoch 4/1）。协议未修，主稿无披露。
- **anchor-stress 倒挂**：去 Patv NMI 0.881、去 Pab_mean 0.878，均**高于**完整模型 0.8716——与干预实验"NMI drop 0.702"的叙事张力至今无解（是否同运行族/同权重协议？）。
- **A10b 单调性断裂**：lag -3（0.361）低于 lag -6（0.405），无讨论。
- **±1.0 m/s 边界带与 ρ=10 无依据**："Ratios 5–10 represent moderate reliability settings"无引用；边界带宽度无敏感性扫描。这两个是 reserve 结论的载重假设。
- **λ 敏感性扫描仍缺**：λ_align=5000/λ_force=10000 与 ERA5 差 5 个数量级，A6 翻转后这个问题从"奇怪"升级为"必须回答"——超大强迫权重在干净口径下没有换来对齐优势（0.721<0.830），它的 RMSE/边界带/噪声鲁棒收益需要逐权重归因。

### R2-4（存续未修）：呈现层缺口

- **主稿仍无全基线预测表**。`artifacts/paper_assets/tables/table_main_benchmark.csv` 已含全部 10 个 WTB 模型 mean±sd（iTransformer 224.34±2.23 … Boundary-forced 236.13±8.41）——零借口级别。且表内两个 MoE 行是 legacy 值，证据切换时需换成 clean 值（router 229.93±2.50、full ≈231.90±4.0）。注意一个被埋没的**正面事实**：clean 口径下 router（229.93）优于容量匹配 Dense（231.42±5.87），"accuracy price"只在相对 iTransformer/GWN 等专用预测器时存在——族内对比其实对论文有利，目前被 legacy 数字埋掉了。
- **单位**："84.58M reserve-cost-equivalent kWh cells"仍在主 Table III；A12 的 MWh/EUR 换算应上主稿。
- **算力披露**：epoch ≈445s、早停 6-9 epoch、110k 参数——数据早已具备，论文仍无 GPU hours/推理延迟。
- **2025+ 风电专用 SOTA 基线数字仍缺**（只有引用）。
- **ERA5 dangling reference（新）**：主文 L117 承诺 "detailed thermodynamic regime definition, architecture choices, and contrast results are reported in Supplementary Material A"，但补充材料**不存在该节**（只有共享表中的 ERA5 行）。悬空引用是审稿人翻补充材料时的即死点。

---

## 👤 Reviewer #3：动机与落地审查（Pragmatist Critic）

**评分：Soundness 3/4 ｜ Significance 2/4 ｜ Overall 4/10 ｜ Confidence 4/5**

### R3-1（致命，存续）：pseudo-problem 终审意见

真实风机的 MPPT/pitch 状态由控制器自身决定并上报，运行商不需要从模型"恢复"自己下发的控制律。论文的真实立足点只能是：**公开数据集缺控制字段 + QC/确认流可延迟**这一审计缺口。Kelmarsh 的限电归因流与 Status 事件流是把动机落到实处的现成素材（且能顺带回答 R2-1 的场景语义问题），继续用合成 6 步延迟而不 grounding，就是把最强的动机辩护留在桌上。

### R3-2（新）：写作层面的自我消耗

- Cover letter 标题（"SCADA-Anchored Regime-Aware Routing for Operational Reserve Diagnosis…"）与稿件标题（"Auditable SCADA-Anchored Routing for Wind-Turbine Reserve Diagnosis at the MPPT-to-Pitch Boundary"）**不一致**——低级但刺眼。
- 过防御问题在证据切换后是重写机会：把"确定性规则做不到的类内风险分级+不确定度定价"升格为正面贡献主线，边界声明压缩到 Limitations 一处。
- 部署门阈值 NMI≥0.50 的依据（何时固定、为何 0.50）未披露；翻案后聚合均值 0.5574 仅勉强过门，且 penmanshiel→kelmarsh 方向 full 模型不过门（0.341）——"过门"叙事必须改为"聚合过门、方向相关"并给分方向表。

---

## 📋 Checklist 审计（本轮全部独立核验）

- [❌] **稿证一致性**：摘要/正文/A6/A8/Discussion 表/cover letter 六处与仓库最新证据矛盾（F0-1/F0-2/F0-3）
- [❌] **复现包自洽性**：guard JSON 会当场翻案论文的负面结论（F0-1）
- [❌] **贡献-证据对齐**：论文主张的贡献 ≠ 其最强可用证据（E1/E3 软信号未进主稿，R1-1）
- [❌] **场景语义**：退化场景无自洽部署语义（R2-1）
- [⚠️] **统计实践**：5 seeds 达标但 n=5 配对 bootstrap + 无 median/IQR + 无收敛分层（R2-2）
- [❌] **主稿全基线表**：资产已存在，未上稿（R2-4）
- [❌] **悬空引用**：Supplementary Material A 之 ERA5 节不存在（R2-4）
- [⚠️] **图年代**：核心图为 2026-06-18 legacy 产物（F0-5）
- [❌] **控制文献**：零风机控制经典引用（R1-4）
- [✅] **数据许可链**：CC-BY-4.0 完整，guard 全绿
- [✅] **AI 声明**：合规

---

## 🚨 P0 致命缺陷拦截清单（按修复顺序）

1. **[P0-R3-1] 证据切换**：headline 运营数字全部切换到 train-only 口径（0.9705/+0.775/0.630/16.9%/99.55M/95.13M/93.82M/Δcost -4.42M [-7.36,-1.27]），legacy checkpoint 降级为历史脚注或删除；A6 两行改为 -0.109 [-0.280,+0.084] p=0.352 / -0.138 [-0.356,+0.088] p=0.379；A8 与 Discussion 部署门表按 windowfix guard（0.5574 过门、方向不对称、窗口协议披露）重写；摘要"two packages"框架删除。同步更新 `verify_tste_number_consistency.py` 的 token 源与两份 checklist。
2. **[P0-R3-2] 场景语义修复**：二选一——(i) Kelmarsh Status/限电流 grounding 标签延迟场景并引用；(ii) 公平退化重跑（gate 与 rule 同受退化）+ 补 test-time gate-under-noise 行。在此之前 Table II 的 0.960 vs 0.196 不可作为 headline。
3. **[P0-R3-3] 贡献迁移**：E1/E3 软信号并入官方管线重跑（reviewer-stat-pack 链路 + BH-FDR），主稿新增软后验分级表；贡献段第一条改为"路由后验=规则类内的条件风险分级器与不确定度仪表"；所有依赖单一硬路由的表述改为软概率/多种子集成口径。
4. **[P0-R3-4] 窗口稳健性扫描**：top-K 可观测窗口 + 随机窗口对照的部署门 NMI 分布。没有这一步，翻案结论可被"挑数据"一票否决。
5. **[P0-R3-5] 统计报告升级**：全部路由指标 median/IQR + gate 熵收敛分层；reserve CI 增加时间块 bootstrap 口径；headline 变体理由按 R1-2 四条重写。
6. **[P0-R3-6] 呈现补齐**：主稿全基线表（换 clean MoE 行）、单位 MWh/EUR、算力披露表、控制文献 4-6 篇、删 "conformal-style"、补 ERA5 节或删主文承诺、修 cover letter 标题与 Kelmarsh 误述、重生成全部图。

## 🧪 最小化补实验清单（按性价比排序）

| 优先级 | 实验 | 预估成本 | 翻转的审稿意见 |
| :--- | :--- | :--- | :--- |
| 1 | 证据切换+官方链路重出表（build_reserve_claim_boundary_table.py 等） | 低（管线现成） | F0-1/2/3 全部 |
| 2 | E1/E3 官方化（并入 stat-pack + 多重比较校正） | 低 | R1-1 |
| 3 | test-time gate-under-degradation 公平退化行 | 低（replay 即可） | R2-1 |
| 4 | 窗口稳健性扫描（裁到 ~24 runs） | 中 | R2-4 / 翻案防御 |
| 5 | 收敛分层 + median/IQR + 时间块 bootstrap（纯分析） | 低 | R2-2/R2-3 |
| 6 | Kelmarsh Status/限电事件流 grounding | 中（数据在本地） | R2-1/R3-1 |
| 7 | 边界带宽度与 λ_force 敏感性 | 中 | R2-3 |
| 8 | 主稿全基线表/算力表导出（资产已在） | 低 | R2-4 |
| 9 | 1 个 2025+ 风电 SOTA 基线 | 中高 | R2-4 |

## 🛡️ 预备 Rebuttal 防御策略

- **循环性**：承认标签是确定性规则；贡献=审计协议+类内条件风险分级（ρ=0.183 同号 5/5 种子）+不确定度定价（ρ=0.391）+软分箱 reserve 效率（-617k CI 显著）——这些是规则原理上给不出的；硬分歧=gate 错误（753 kW）反而证明审计协议能自我证伪。
- **变体选择**：干净口径下 boundary-forced 的价值在边界带 RMSE（-4.58, p=0.001）与 anchor 噪声鲁棒（5.78 vs 105.56），不在全局对齐——选择理由随证据更新，并主动披露 A6 翻转。
- **部署门**：选窗规则无模型、无结果依赖（只看输入掩码）+ 稳健性扫描分布；方向不对称本身就是"部署前必须本地 held-out routing pass"的实证论据。
- **种子崩塌**：转化为方法论贡献——"路由模型的早停/选择准则必须包含路由指标"，并给修复协议。

## ⚠️ Kill / Pivot 条件

- 窗口稳健性扫描若显示仅 argmax 窗口过门 → 部署门翻案不成立，跨场叙事退回纯负面，转投策略启动。
- E1/E3 官方化后若软信号不显著 → 贡献退化为"协议性贡献"，TSTE Regular Paper 论据不足，转 Applied Energy/Wind Energy。
- 公平退化实验若显示 gate 与 rule 在同等退化下无差异 → 标签退化主线删除，论文重心完全转向 reserve 软分箱。

---

## 附：本轮独立核验记录

1. `artifacts/external_wind_guard_windowfix/external_wind_guard.json`：实读，`cross_site_mechanism_passed`、80/80、checks 全 true。
2. `artifacts/paper_assets/tables/table_main_benchmark.csv`：实读，10 个 WTB 模型 mean±sd 齐全；MoE 两行为 legacy 值（236.13/241.42）。
3. `artifacts/tste_number_consistency_audit_polish3/…json`：实读，44/44 绿，但审计口径=文档对旧 artifact。
4. `artifacts/final_evidence_package/export/figures/`：实读目录，核心图时间戳 2026-06-18。
5. `references.bib`：实数 50 条；grep 确认无风机控制文献；2025×8、2026×2。
6. 补充材料全文：确认无 ERA5 thermodynamic regime 专节（主文 L117 承诺悬空）。
7. `cover_letter_tste.md`：标题与稿件不一致；L19 Kelmarsh 误述。
8. 干净口径数字（0.9705/+0.775/0.630/-4.42M/0.830 vs 0.721/E1/E3/窗口修复/seed203）来源：`docs/tste_trainonly_rerun_results_20260830.md` 追加一至八（远程产物路径已记录，正式投稿前需同步入本地复现包）。
