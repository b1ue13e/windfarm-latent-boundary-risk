# Train-only Checkpoint 全量审计重跑结果（P0-2 补救）

> 运行日期：2026-08-30 ｜ 运行位置：远程 grokking (192.168.17.251) `/root/paper3_audit_rerun_20260830`
> 目的：将论文 headline 运营数字从有类权重泄漏污点的 legacy checkpoint 切换到 train-only 类权重 checkpoint（5 seeds: 201–205），验证 P0-2 补救可行性。
> 代码版本：本地 git HEAD（90528db0）；运行环境修复：LD_PRELOAD hpcx UCX 栈。

## 产物路径（远程）

- 退化审计：`artifacts/early_warning_trainweight_5seed_20260830/`（guard 状态 `complete_anchor_stress_supports_label_degradation_value`，7 项检查全过）
- 备用金审计：`artifacts/decision_reserve_trainweight_full_20260830/`（含全部 7 个 strata 层）
- run-table：`artifacts/paper_assets/tables/wtb_trainweight_reserve_runs_20260830.csv`

## 一、标签退化审计：新旧对照（5 seed 均值）

| 指标 | 论文现值（legacy） | train-only 重跑 | 判断 |
| :--- | :--- | :--- | :--- |
| 6 步延迟 gate recall | 0.960 | **0.9705 ± 0.0299** | ✅ 更强 |
| 6 步延迟 rule recall | 0.196 | 0.196（确定性规则，不变） | — |
| 6 步延迟 recall gain | +0.764 | **+0.775** | ✅ 存活且略增 |
| 50% 可用 gate recall vs rule | 0.960 vs 0.508 | 0.9705 vs 0.508（gain +0.462） | ✅ 存活 |
| **gate precision（clean anchor）** | 0.759 | **0.630 ± 0.108** | ⚠️ 明显下降，措辞必须改 |
| rule precision（6 步延迟） | 0.342 | 0.342 | — |

**结论**：退化价值的核心叙事（recall gain）在干净 checkpoint 上完全存活甚至略强。但 precision 从 0.759 → 0.630，摘要/正文/cover letter 中所有 0.759 及"classifier 0.879 precision vs gate 0.759"的对比都要改写；且 0.630 与 logistic classifier 的 0.879 差距拉大，"classifier 是更强 clean-anchor 检测器"的边界声明反而更安全了。

## 二、备用金审计：边界窗口 ρ=10 新旧对照

| 策略 | 论文现值（legacy boundary router） | train-only 重跑 | 说明 |
| :--- | :--- | :--- | :--- |
| Boundary/global | 88.13M / viol 0.1038 / shortage 3.73M | 99.55M / 0.1167 / 4.404M | 绝对成本上升（train-only 边界带 RMSE 更高所致） |
| Boundary/gate-bin | 84.58M / 0.0900 / 3.19M | 95.13M / 0.1021 / 3.767M | 同上 |
| Boundary/physical-bin | 83.78M / 0.0880 / 3.05M | 93.82M / 0.1010 / 3.697M | **physical-bin 仍比 gate-bin 便宜**，边界声明不变 |
| GWN/physical-bin | 84.31M / 0.0931 | 84.31M / 0.0931 | 不变（GWN 为纯预测基线，无类权重泄漏，沿用 legacy） |
| GWN/global | 88.80M / 0.1022 | 88.80M / 0.1022 | 不变 |

### 同模型 seed 配对 CI（gate-bin − global，A11 口径复算）

| 指标 | 论文现值（legacy） | train-only 重跑 | 判断 |
| :--- | :--- | :--- | :--- |
| Δ total cost | -3.55M, CI [-4.65M, -2.45M] | **-4.42M, CI [-7.36M, -1.27M]** | ✅ 仍为显著负（区间变宽但不跨零） |
| Δ violation rate | -0.0138, CI [-0.0203, -0.0072] | **-0.0145, CI [-0.0220, -0.0073]** | ✅ 存活 |
| Δ shortage energy | -0.54M, CI [-0.78M, -0.30M] | **-0.637M, CI [-0.976M, -0.300M]** | ✅ 存活且略强 |
| Δ reserve energy | +3.6% | +1.95M, CI [+0.93M, +2.84M] | ✅ 方向一致 |

**结论**：same-router 边界窗口的备用金诊断 claim 在干净 checkpoint 上**全部存活**，效应量甚至略大，CI 仍不跨零。physical-bin 依然更便宜的边界事实不变（这本来就是已声明的 limitation）。

## 三、必须随之修改的论文位置

1. 摘要/正文/cover letter：0.960→0.971（6 步延迟 recall）、+0.764→+0.775、0.759→0.630（gate precision）、14.5% shortage 降低→按新值 16.9%（0.637/3.767≈16.9%，请以导出表为准）、所有 88.13M/84.58M/83.78M 表格数字。
2. Table III 全表替换为 train-only 版本；A11 CI 行替换；A12 的 MWh/EUR 换算需基于新 delta 重算。
3. 新增披露句：headline 运营审计现基于 train-only 类权重 checkpoint，与 RMSE guardrail（229.93）同源——**这反而消除了"两套证据包"的割裂叙事，是本次重跑的额外红利**。

## 四、遗留事项

1. **Physics-Aligned MoE (full) 行仍用 legacy checkpoint**：该族也带 L_align 类权重，严格说同样存在 provenance 问题。其行只用于有界对照，但若要彻底干净，需对 full 族也做 train-only 重跑（远程机器可承载）。
2. Table A6 中 legacy 行的定位需重写（从"full-audit checkpoint"降级为历史参照）。
3. 本次 CI 为我按官方脚本口径（n=5 seed 配对 bootstrap, 20000 次, 固定种子）手工复算，正式投稿前应跑 `scripts/build_reserve_claim_boundary_table.py` 官方链路重新生成。


---

# 追加：Physics-Aligned MoE (full) 族 train-only 重训结果（2026-08-30 晚）

> 远程产物：`artifacts/trainweight_full_rerun_20260830/`（5 seeds 全部完成）、`artifacts/decision_reserve_trainweight_allclean_20260830/`（全 clean 版 reserve 审计：GWN/PatchTST 沿用 legacy 纯预测基线，两个 MoE 族均为 train-only checkpoint）

## full 族 5 seed 训练指标（test）

| seed | RMSE | MAE | NMI | ARI |
| :--- | :--- | :--- | :--- | :--- |
| 201 | 233.10 | 163.73 | 0.848 | 0.900 |
| 202 | 236.21 | 168.99 | 0.684 | 0.723 |
| 203 | 225.35 | 157.58 | 0.895 | 0.939 |
| 204 | 231.46 | 168.70 | 0.844 | 0.897 |
| 205 | 233.38 | 165.15 | 0.878 | 0.931 |
| **均值** | **231.90** | — | **0.830** | **0.878** |

## ⚠️ 重要叙事发现：A6 机制对比行的符号可能翻转

- 论文 Table A6 现值：Gate NMI vs full physics-aligned MoE = **+0.040**（boundary router 高于 full 族，"positive but not FDR-significant"）。
- 全 clean 口径下：full 族 train-only NMI 均值 **0.830**（但 seed 间方差大，0.684–0.895），boundary router train-only NMI **0.721**——**delta 转为负值**。
- 含义：在干净类权重下，"boundary forcing 是对齐所必需"的论证在 NMI 维度上不再成立；boundary router 的差异化价值需更多依靠 pitch-control RMSE、anchor 噪声鲁棒性（0.5-std 退化 5.78 vs anchor-only 105.56）和 reserve 同模型对比来支撑。A6 表与正文相关句子必须按全 clean 数字重写，正式投稿前需跑 `reviewer-stat-pack` 官方链路出配对统计。

## 全 clean 版 reserve 边界窗口（ρ=10）

| 策略 | cost | viol | shortage | 备注 |
| :--- | :--- | :--- | :--- | :--- |
| Boundary-forced router/global | 99.55M | 0.1167 | 4.404M | 不变（同 checkpoint） |
| Boundary-forced router/gate-bin | 95.13M | 0.1021 | 3.767M | 不变 |
| Boundary-forced router/physical-bin | 93.81M | 0.1010 | 3.697M | 不变，仍比 gate-bin 便宜 |
| Physics-Aligned MoE/global | 95.89M | 0.1014 | 3.826M | **新（train-only）** |
| Physics-Aligned MoE/gate-bin | 91.62M | 0.0907 | 3.328M | **新（train-only）** |
| Physics-Aligned MoE/physical-bin | 90.39M | 0.0888 | 3.200M | **新（train-only）** |
| GWN/global | 88.80M | 0.1022 | 3.848M | 不变（legacy 纯预测基线） |
| GWN/physical-bin | 84.31M | 0.0931 | 3.397M | 不变 |

### 同模型 seed 配对 CI（gate-bin − global，官方 A11 口径复算）

| 族 | Δ cost | Δ violation | Δ shortage |
| :--- | :--- | :--- | :--- |
| Boundary-forced router | -4.42M [-7.36M, -1.27M] | -0.0145 [-0.0220, -0.0073] | -0.637M [-0.976M, -0.300M] |
| Physics-Aligned MoE（新） | -4.26M [-5.43M, -3.04M] | -0.0107 [-0.0164, -0.0054] | -0.498M [-0.715M, -0.280M] |

**结论**：两族的 same-model gate-bin 诊断 claim 在全 clean 口径下均显著成立、方向一致、量级相近——这实际上**加强**了"gate-conditioned binning 作为同模型诊断"的可信度（不再依赖单一变体）。物理分箱仍更便宜的边界事实不变。至此，headline 数字的类权重 provenance 污点已全部清除。


---

# 追加二：官方 reviewer-stat-pack 链路确认（2026-08-30 18:55）

> 产物：`artifacts/reviewer_stat_pack_trainweight_20260830/`（远程），guard 状态 `complete_ready_for_reviewer_statistics`（21 项检查全过，20 runs / 75 paired rows / 15 multiplicity rows）。
> run-table：GWN/PatchTST 为 legacy 纯预测基线，Boundary-forced router 与 Physics-Aligned MoE 均为 train-only checkpoint。

## A6 机制对比行：符号翻转被官方配对统计确认

Reference = Boundary-forced router（train-only），comparator = Physics-Aligned MoE（train-only），5 seed 配对：

| 指标 | router | full MoE | Δ(router − full) | 95% CI | 配对置换 p |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Gate NMI | 0.7208 | 0.8296 | **-0.109** | [-0.280, +0.084] | 0.352 |
| Gate ARI | 0.7398 | 0.8778 | **-0.138** | [-0.356, +0.088] | 0.379 |

**结论（官方链路）**：clean 口径下两族对齐度**无显著差异**（CI 跨零、p≈0.35–0.38），且方向反转为 full 族更高。Table A6 现有 "+0.040 / +0.035，positive but not FDR-significant" 两行必须重写为 "无显著差异" 口径，并删除任何隐含 "boundary forcing 创造对齐" 的措辞。

## 附带确认（pack 内部口径，勿与 headline 混用）

- router vs GWN 整体 RMSE delta +4.68（p=0.001）：accuracy price 依然显著存在，与论文叙事一致；
- router vs full MoE 边界带 RMSE delta -4.58（p=0.001）：**router 在边界带显著优于 full 族**——这是 router 差异化价值的新支点，可部分替代死去的 NMI 叙事；
- 注意：pack 内 RMSE（215.5 等）基于其自身 per-example 评估口径，与 headline 的 229.93/224.34 协议不同，**禁止直接引用到正文**。

## 论文改写要点（基于全部 clean 证据）

1. A6 表两行 NMI/ARI delta 改为：-0.109 [-0.280, +0.084] p=0.352 / -0.138 [-0.356, +0.088] p=0.379，wording consequence 改为 "no significant alignment difference; do not claim boundary forcing is required for alignment"。
2. boundary router 的存在理由改写为：边界带 RMSE 显著低于 full 族（-4.58, p=0.001）+ anchor 噪声鲁棒性（5.78 vs 105.56）+ 退化标签下 recall gain（+0.775）+ 同模型 reserve 诊断（Δcost -4.42M, CI 不跨零）。
3. "两套证据包"叙事合并：headline 审计与 RMSE guardrail 现同源于 train-only checkpoint。


---

# 追加三：E1 分歧价值 pilot 结果（2026-08-30 晚，远程）

> 产物：`artifacts/e1_disagreement_trainweight_20260830/`（远程），脚本 `tools_e1.py`（本地存档 `tmp/e1_disagreement_analysis.py`）
> 数据：train-only boundary router，5 seeds，test split，R∈{MPPT,pitch} 有效 cell（每 seed 291,591 个）

## 结果：强版本假说被自己的 pilot 证伪

| 检验 | 结果 | 判决 |
| :--- | :--- | :--- |
| gate-rule 分歧率 | 均值 16.9%，但 seed 间 1.6%–44.6% 剧烈波动 | ⚠️ 硬路由本身跨 seed 不稳定（另一个 reviewer 可见弱点） |
| 分歧 cell 上谁更对？ | rule 条件均值拟合未来功率优于 gate 条件均值 **753 kW**，gate 仅在 5.3% 的分歧 cell 上更好（CI [3.0%, 7.7%]） | ❌ **硬分歧是 gate 的错误，不是"有效边界"信号** |
| 软后验分级信号（rule=MPPT 边界带内 P(pitch) vs 结果残差） | Spearman ρ=0.183，CI [0.123, 0.227]，5/5 seed 同号 | ✅ 软概率分级携带结果信息 |
| gate 不确定度 vs 预测误差 | ρ=0.391，CI [0.299, 0.482] | ✅ 路由不确定度可预测误差，可直接服务风险筛查 |

## 结论与路线修正

1. **"有效控制边界（硬版本）"假说死亡**：gate 与规则硬分歧的地方，规则是对的。不要再往"gate 发现了规则之外的边界"方向写。
2. **存活的故事**：软后验的**类内分级**（同一 MPPT 规则类内，P(pitch) 高低对应未来功率高低）+ **不确定度定价**（低置信路由 = 高误差区域）。这两个是确定性规则原理上给不出的，且不依赖"gate 比规则聪明"。
3. 新故事的准确表述：**"路由后验是规则类内的条件风险分级器与不确定度仪表"**——直接接通 E3（route-conditioned conformal reserve），而不是接通"边界发现"。
4. 硬路由跨 seed 不稳定（1.6%–44.6%）必须管理：正文所有 claim 改为基于软概率/多 seed 集成，避免任何依赖单一硬路由的表述。


---

# 追加四：E3 路由后验条件化备用金 pilot（2026-08-30 深夜，远程）

> 产物：`artifacts/e3_route_conditioned_20260830/`（远程），脚本 `tools_e3.py`（本地存档 `tmp/e3_route_conditioned_conformal.py`）
> 设计：边界带（|Wspd−10.5|≤1）内，validation-frozen shortfall 分位数；三种分箱策略：global / physical-bin（规则 MPPT/pitch 硬分箱）/ soft-gate-bin（P(pitch) 五分位软分箱，箱边来自验证集）；ρ=10；5 seeds；seed 配对 bootstrap CI。
> 注意：本 pilot 的口径（仅边界带 anchor 的 horizon cell）与正式 reserve 审计（Table III 全样本协议）不同，数字不可直接互换。

## 核心结果（ρ=10，5 seed 均值）

| 策略 | total cost | violation | reserve | shortage | pinball@0.9 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| global | 16.63M | 0.1000 | 10.95M | 0.568M | 43.94 |
| physical-bin | 16.19M | 0.0996 | 10.72M | 0.547M | 42.52 |
| **soft-gate-bin** | **16.06M** | 0.1012 | **10.33M** | 0.573M | **42.12** |

## Seed 配对差异（soft-gate-bin − baseline，95% CI）

| 对比 | Δcost | Δreserve | Δviolation | Δshortage | Δpinball@0.9 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| vs global | **-568k [-726k, -406k]** ✅ | **-617k [-984k, -278k]** ✅ | +0.0012（跨零） | +4.9k（跨零） | **-1.82 [-2.33, -1.30]** ✅ |
| vs physical-bin | -125k [-297k, +34k]（跨零） | **-391k [-732k, -28k]** ✅ | +0.0016（跨零） | +26.6k（跨零） | -0.40 [-0.95, +0.11]（跨零） |

## 条件覆盖率（q=0.90 固定，test 实际覆盖）

global 0.900（单箱平凡校准）；physical-bin 0.868/0.911（类间偏移 4.4pt）；soft-gate-bin 0.867–0.928（箱间偏移 6.1pt）。**条件覆盖率不是卖点**（软分箱并未更校准），卖点在 reserve 效率与 pinball。

## 结论

1. **软后验分箱的核心价值成立**：在 violation/shortage 持平的前提下，比 global 少 6% reserve（CI 显著）、pinball 显著更优——"规则类内的风险分级换来备用金效率"。
2. 与 physical-bin 相比：成本打平（CI 跨零），但 reserve 显著更少、pinball 趋势更优——叙事应为"**以更少的备用金占用达到同等风险**"，不是"更便宜"。
3. 这正好接续 E1 的修正故事：软后验 = 类内风险分级器；硬分箱（gate-bin/物理箱）的对比全部降级为辅助。
4. 论文侧动作：新增一张 soft-gate-bin 对比表（本 pilot 口径需在正文明确界定）；正式投稿前将该协议并入官方 reserve 审计链路重跑，而非引用本 pilot 数字。


---

# 追加五：数据问题排查——Kelmarsh 真实数据资产核查（2026-08-31 凌晨）

> 数据源：本地 `data/external_wind/kelmarsh/Kelmarsh_SCADA_2016_3082.zip`（Zenodo 16807551, CC-BY-4.0）+ 远程信号映射表。

## 关键发现：数据远比当前管线所用的丰富

**1. Kelmarsh 2016 就有 pitch 通道，覆盖率 65.5%。**
`Turbine_Data_Kelmarsh_*_2016.csv` 共 464 列，含三叶片 `Blade angle (pitch position) A/B/C (°)`，T01 实测非 NaN 覆盖率 0.655。论文 Table A8 "pitch-feature coverage 0.0000" 的结论来自**本项目特征提取管线的产物，不是原始数据缺失**——Kelmarsh "部署门失败"的负面结论需要重查，可能是提取/覆盖率过滤环节的假阴性。

**2. 存在非阈值衍生的真实运行状态标签：**
- `Lost Production to Curtailment (Total/Grid/Noise/Shadow/Bats/Birds/Ice/Sector Management/Technical/Marketing)`：运营商归因的限电损失，覆盖率 93.7%——**按原因分类的限电真值**；
- `Potential power default PC / learned PC / reference turbines / MPC`：可用功率估计，覆盖率 92.5%；
- IEC 可用率分类（Time/Production-based, B.2.2/B.2.3/B.2.4/B.3.2）；
- `Density adjusted wind speed`（65.5%）：空气密度修正通道；
- Status_*.csv 事件流：Status/Code/Message/IEC category（Forced outage / Full Performance 等）+ 精确起止时间戳。

**3. 仍然不存在的：MPPT/pitch 控制律的真值标签。** 任何公开数据集都没有"控制器当前处于哪个控制律"的字段——这部分循环性无法靠数据消除，只能继续用"声明边界合规审计"的诚实框架管理。

**4. `Turbine Power setpoint` 2016 年覆盖率 0%**（列存在但全 NaN），更晚年份（2022–2024）可能有值，未验证。

## 战略含义

- "数据的问题"的精确答案：**不是数据匮乏，而是当前管线只提取了最小特征集**。Kelmarsh 的 pitch（65.5%）+ La Haute Borne 的 pitch（99.2%）意味着**两个外部场都能做带真实 pitch 的跨场验证**；
- 限电真值 + 可用功率估计打开一个新故事维度：**限电/降额状态识别**——这是运营商确认流真实存在、且确认确实可能延迟的场景（修复"标签延迟"动机漏洞的现实素材）；
- 优先动作：① 重查 Kelmarsh 特征提取管线为何 pitch 覆盖率为 0；② 用真实 pitch 重跑 Kelmarsh 部署门；③ 评估把"限电状态"作为第二个真实标签运行边界。


---

# 追加六：Kelmarsh pitch 假阴性根因实锤与窗口协议修复（2026-08-31 02:00）

> 代码修复已提交：`9c28c26`（`windfarm_moe/external_wind.py`）；远程 42 项 external_wind 测试全绿。

## 根因链（逐环实锤）

1. **不是表头解析 bug**：Kelmarsh 2016 zip 表头为单行 299 列，`_greenbyte_header_from_sample` 正确解析出全部 `Blade angle (pitch position) A/B/C (°)` 列。
2. **原始数据真实缺口**：Kelmarsh T01 2016 年 pitch 覆盖率全年 65.5%，但 **1–4 月为 0.000**（5 月起才 >0.89）；Penmanshiel 2016–2017 年 pitch 覆盖率同样整段为 0（pitch 记录 2018 年中才开始）。Greenbyte 导出早期无 pitch 通道。
3. **窗口协议放大缺口**：`_write_leave_one_farm_cache_from_chronological` 旧实现取时间轴**头部**窗口（源场前 210 天、目标场前 35 天）。头部恰是无 pitch 段 → penmanshiel→kelmarsh 方向 LOFO 缓存 pitch 特征覆盖率 **0.0000**、有效边界单元 0；kelmarsh→penmanshiel 方向仅 0.1066。论文 Table A8 的 "pitch-feature coverage 0.0000" 由此而来——**部署门失败是窗口选择造成的假阴性，而非 Kelmarsh 数据无 pitch**。
4. metadata 中 `pitch_observed_fraction=0.6823` 与特征掩码 0.0 的"矛盾"也由此解释：LOFO metadata 继承自源场时间序缓存（`dict(source_meta)`），反映的是源场全期覆盖率，不是实际张量窗口的覆盖率。

## 修复：锚点可观测性最大化窗口选择

- 新辅助函数 `_best_anchor_window_start`：在源/目标时间序缓存的 `Wspd × Pab_mean` 联合掩码上滑动窗扫描，选联合可观测率最高的连续窗口（源 30240 步 / 目标 5040 步）。
- metadata 新增 `lofo_window_protocol="anchor_observability_max_v1"`、窗口边界与锚点覆盖率；`pitch_observed_fraction` 改为按实际拼接张量计算（与审计口径一致）。
- 部署门语义自洽：门本身要求"验证 pitch 可观测后再用路由"，因此在锚点可观测的窗口上评估路由正是门的本意。

## 重建后缓存（本地重建，纯 numpy 拼接）

| 方向 | 源窗口 | 源锚点覆盖 | 目标窗口 | 目标锚点覆盖 | 旧 pitch 覆盖率 | 新有效覆盖率 |
|---|---|---|---|---|---|---|
| penmanshiel→kelmarsh | [123736, 153976] | 0.9991 | [36024, 41064] | 1.0000 | 0.0000 | ~1.00 |
| kelmarsh→penmanshiel | [94985, 125225] | 0.9990 | [123736, 128776] | 1.0000 | 0.1066 | ~1.00 |

（张量全节点口径 pitch_feature_coverage 分别为 0.6423/0.3569，因跨场拼接含非活动节点零填充；活动区域内覆盖率 ≈100%。）

## 冒烟验证（远程，penmanshiel→kelmarsh，seed 299，1 epoch）

测试侧 kelmarsh 首次出现真实 regime 指标：pitch_control RMSE 522.2（旧协议下为 0.0/NaN）；test gate NMI 0.404、val gate NMI 0.606——1 epoch 欠拟合下的读数，仅供管线验证，不作结论。

## 进行中和待办

- 远程 4×4090 正在重跑完整 LOFO 部署门协议（2 方向 × 4 模型 × 5 种子 = 40 运行，epochs 20，`artifacts/external_wind_runs_windowfix/`）。
- 完成后：回收运行 → 本地重跑 external-wind-guard + rescue 审计 → 判定 NMI≥0.50 门是否翻过；若仍不过门，则负面结论从"无 pitch 不可评估"升级为"满 pitch 可观测下路由仍不可移植"，证据强度反而更高。


---

# 追加七：窗口修复后 LOFO 部署门重跑结果——门翻案（2026-08-31 12:10）

> 运行位置：远程 `paper3_audit_rerun_20260830/artifacts/external_wind_runs_windowfix/`（40 运行 = 2 方向 × 4 模型 × 5 种子，epochs 20，train-only 口径）；
> 官方 guard：`artifacts/external_wind_guard_windowfix/external_wind_guard.json`（远程重跑，输入为修复后 LOFO 缓存 + 原有时间序缓存/运行）。
> 注意：本表方向按 run 目录农场=源场（train），即 `kelmarsh/leave_one_farm_out` = kelmarsh→penmanshiel。

## 官方 guard 判定（40/40 路由运行完整）

| 指标 | 旧（头部窗口） | 新（锚点可观测窗口） | 门槛 | 判定 |
|---|---|---|---|---|
| 路由 NMI 均值 | 0.4877 | **0.5574** | ≥0.50 | FAIL → **PASS** |
| 路由 ARI 均值 | 0.5112 | **0.5652** | ≥0.30 | PASS → PASS |
| pitch 特征覆盖率 | 0.0000（一方向） | 活动区域 ≈100% | — | 假阴性消除 |
| 边界 RMSE | null（无边界单元） | 677.07 | — | 首次可评估 |

guard 总分母状态目前 `blocked_external_wind_incomplete`（79/80，最后一个 Graph WaveNet baseline 运行收尾中），但 `routing_nmi_meets_minimum=true`、`routing_ari_meets_minimum=true`——**部署门的路由判据在新窗口协议下正式翻过**。

## 分方向 × 分模型明细（test 侧 held-out 农场）

| 方向 | 模型 | NMI mean±sd | ARI mean | 判定 |
|---|---|---|---|---|
| kelmarsh→penmanshiel | full | 0.7705±0.2991 | 0.7610 | 强过门 |
| kelmarsh→penmanshiel | bal_align_force | 0.7523±0.2995 | 0.7346 | 强过门 |
| penmanshiel→kelmarsh | full | 0.3411±0.2088 | 0.3249 | 不过 |
| penmanshiel→kelmarsh | bal_align_force | 0.5054±0.1429 | 0.5482 | 擦线过 |

## 必须诚实写进论文的三件事

1. **方向不对称**：kelmarsh→penmanshiel 强迁移（NMI~0.76-0.77），penmanshiel→kelmarsh  marginal（full 模型不过门）。聚合均值过门主要由前者贡献——论文不能只说"过门"，必须给分方向表。
2. **seed 203 异常**：kelmarsh→penmanshiel 方向两个 MoE 模型在 seed 203 同时崩到 NMI≈0.24-0.25（其余种子 0.73-0.97），指向训练不稳定性而非数据问题，需排查或在文中声明。
3. **故事线升级**：旧叙事"Kelmarsh 部署门失败=负面边界证据"被证伪为窗口协议假阴性。新叙事：**在锚点可观测的部署窗口下，审计路由跨场可迁移（均值 NMI 0.557 过 0.50 门），但迁移性是方向与模型相关的**——这比原来的纯负面结论信息量更高，也把"部署前可观测性核查"从一句告诫变成了有实证的部署协议。

## 待办

- 等最后 1 个 graph_wavenet 运行完成后重跑 guard 拿全绿状态；
- 排查 kelmarsh→penmanshiel seed 203 崩塌原因（训练日志/学习率/初始化）；
- 论文 Table A8 与 §部署门段落按新协议重写（含窗口选择方法的披露）。


---

# 追加八：seed 203 崩塌根因 + 部署门全绿收官（2026-08-31 16:15）

## seed 203 崩塌诊断（kelmarsh→penmanshiel，full 与 bal_align_force 同时 NMI≈0.25）

**结论：路由器欠收敛（高熵未定形），不是预测头崩塌，也不是数据问题。**

证据链：
1. **预测训练完全正常**：seed 203 best val_rmse 248.7/251.7，与其余种子（246–256）同水平；train loss 单调下降，无爆炸、无 NaN；
2. **崩塌的是 gate**：健康种子的 gate 熵 0.12–0.24、max-prob 中位数 1.000（确定性锐化路由，NMI 0.73–0.97）；seed 203 的 gate 熵 **1.16–1.22**、max-prob 中位数仅 **0.66**——softmax 停在平坦区，expert usage 分散在 0/1 号专家（85%/15%），与 WTB regime 对不齐；
3. **两模型同一种子同时犯病** → 共享初始化/数据顺序使路由器陷入平坦极小值；
4. **协议级脆弱性**：所有运行都在 epoch 6–9 早停（patience=5），早停准则只看 val_rmse（预测），**不监控路由对齐**——seed 203 的路由器在尚未锐化时就被早停锁定（best_epoch 4/1）。

论文侧处理建议（三选一，按保守到激进排序）：
- a) 声明种子敏感性，报告 median/IQR 而非仅 mean（mean 0.56 vs median 更高）；
- b) 早停准则加入路由对齐监控（协议改动，需重跑）；
- c) 路由器 warm-up / 更长 patience（方法改动，需消融支撑）。

## 部署门最终状态：全绿

补齐时间序运行的 `target.npy/mask.npy`（6 月旧运行早于现行指标清单；通过 `RegimeWindowDataset` 确定性再生，再生锚点与保存锚点逐一比对完全一致，未重训）后，guard 复跑：

```
status = cross_site_mechanism_ready
claim_gate = cross_site_mechanism_passed
complete_runs = 80/80, routing 40/40, 全部 checks = true
mean_nmi = 0.5574 (≥0.50), mean_ari = 0.5652 (≥0.30)
```

旧 guard（头部窗口协议）：`complete_but_within_wtb_only` / NMI 0.4877 不过门。
新 guard（锚点可观测窗口协议）：**跨场机制证据正式过门**。

## 本次会话代码变更

| commit | 内容 |
|---|---|
| `9c28c26` | LOFO 缓存锚点可观测性最大化窗口选择（修复 pitch 假阴性根因） |
| `09790e5` | paper-batch `--num-workers` 参数（修数据加载瓶颈，GPU 9%→87%） |

## 交付物位置

- 新 LOFO 缓存（本地）：`artifacts/cache_external_wind/external_wind_*_leave_one_farm_out/`（旧头部窗口版本保留为 `*_headwindow_backup/`）
- 新 LOFO 运行（本地套件）：`artifacts/external_wind_runs/{kelmarsh,penmanshiel}/leave_one_farm_out/`（旧运行保留为 `leave_one_farm_out_headwindow_backup/`）
- 全绿 guard（本地）：`artifacts/external_wind_guard_windowfix/external_wind_guard.json`
- 远程工程：`/root/paper3_audit_rerun_20260830`（套件、缓存、guard 输出均已同步）
