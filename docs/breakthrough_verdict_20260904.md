# 破局裁决汇总（2026-09-04）：三个裁决实验后的贡献重定位

> 实验：方案 A（软规则分箱 + 退化重算 gate）、K1（Kelmarsh 稀疏农场定价）、K2（多通道分类器 signature/鲁棒）、K3（GBDT 软分箱定价）
> 判据全部预注册。结论先给，证据随后。

## 一、总裁决

| 假设 | 裁决 | 证据 |
| :--- | :--- | :--- |
| 学到的 P(pitch) 分箱优于软规则分箱 | ❌ **死** | soft-pab-bin 15.538M < soft-gate-bin 16.065M（−526k CI 不跨零），退化下仍不输 |
| 退化鲁棒是 MoE 独有 | ❌ **死（但部分复活）** | GBDT 多通道分类器 delay6 下 recall 0.868（gate 0.933）；但 GBDT 的概率**没有定价价值**（见下） |
| 稀疏农场上 gate 定价有增量 | ❌ **死** | Kelmarsh：soft-gate-bin vs global −40k 跨零 |
| **与预测联合学习的后验才有定价价值** | ✅ **成立（新发现，核心增量）** | gate 后验 16.07M/16.32M **显著优于** 独立 GBDT 后验 17.66M/17.31M（GBDT 后验比 global 16.63M 还差 1M） |

## 二、四个裁决实验的完整证据

### 1. 软规则分箱（方案 A）
soft-pab-bin 15.538M 全场最优，比 soft-gate-bin 低 526k [330k, 719k]；退化下（delay6/noise）优势收窄但不翻转。→ **P(pitch) 定价不优于物理连续量**，soft-pab 移入诚实基线。

### 2. Kelmarsh 稀疏农场定价（K1）
soft-gate-bin 5.245M vs global 5.285M：Δ=−40k [−202k, +129k] 跨零。→ **稀疏农场上 gate 定价无显著增量**（样本少、标签噪声大）。

### 3. 多通道分类器（K2）
| 模型 | clean NMI | clean recall | delay6 recall | noise recall |
| :--- | :--- | :--- | :--- | :--- |
| logistic-all（11 通道+窗口统计） | 0.500 | 0.146 | 0.195 | 0.278 |
| logistic-cons（9 后果通道） | 0.277 | 0.499 | 0.455 | 0.231 |
| gbdt-cons（9 后果通道） | 0.270 | 0.870 | **0.868** | **0.804** |
| MoE gate（实验 A 参照） | 0.367（core） | 0.971 | 0.933 | 0.951 |

→ GBDT 大体复现鲁棒性（0.87/0.80），但 gate 仍有 6-15pp 增量；且见 K3——GBDT 概率无定价价值。

### 4. GBDT 软分箱定价（K3，决定性）
| 策略 | total cost（ρ=10） |
| :--- | :--- |
| soft-pab-bin（物理） | **15.538M** |
| soft-gate-bin（gate P(pitch)） | 16.065M |
| entropy-gate-bin（gate 熵） | 16.324M |
| global | 16.632M |
| entropy-gbdt-bin（GBDT 熵） | 17.313M |
| soft-gbdt-bin（GBDT P(pitch)） | 17.656M |

→ **独立训练的 GBDT 后验在 reserve 定价上比 global 还差 1M；联合训练的 gate 后验比 GBDT 好 1.6M。** 定价价值来自"与预测器联合学习"（E1 机制：ρ=0.183 类内分级、ρ=0.391 不确定度与误差耦合），不是分类概率本身。

## 三、重定位后的贡献（新主线）

论文的真实机制级增量被四个裁决实验精确锁定为一个：

> **联合学习的软边界后验（jointly-learned boundary-risk posterior）**：
> 1. **定价价值**：与预测器联合训练的软后验比任何独立分类器的后验更有 reserve 定价价值（16.07M vs GBDT 17.66M；比 global 低 568k CI 显著）；纯物理量分箱（Pab）在干净完整观测下更优（15.54M），但需要物理量可用。
> 2. **退化可用性**：物理量延迟/缺失时（Kelmarsh 真实场景 99.6% 非网格事件），联合后验保持边界检测（0.933 vs 0.196）和定价（16.07M 不变），而规则/物理分箱崩坏。
> 3. **可观测性谱系**：pitch 55%/78% 农场仍可恢复边界（0.34/0.38，shuffled 对照随机）。
> 
> 不再是"MoE 路由"的故事，而是"**与预测联合学习的风险后验**"的故事——MoE gate 是这种后验的一种实现，但证据支撑的是联合学习机制，不是专家结构。

## 三补、K4 最终裁决（Dense 同 encoder + 分类头，2026-09-04）

| 策略 | total cost（ρ=10） |
| :--- | :--- |
| soft-pab-bin（物理） | 15.538M |
| soft-gate-bin（MoE 路由后验） | 16.065M |
| **soft-dense-bin（联合无路由后验）** | **16.076M** |
| entropy-gate-bin | 16.324M |
| entropy-dense-bin | 16.471M |

**最终机制定位**：
1. **soft-dense-bin（16.076M）与 soft-gate-bin（16.065M）几乎相同（差 11k）** → 定价价值属于"**与预测联合学习**"，不属于 MoE 路由结构。Dense 预测头 + 分类头的联合训练后验同样有定价价值。
2. 熵定价 gate 略优（16.324 vs 16.471，差 147k）——不确定度维度的 gate 仍有小幅优势，但不足以支撑"路由"叙事。
3. **论文必须放弃 "MoE/路由" 卖点**，改为"联合学习的软边界后验"；MoE gate 与 Dense 分类头作为两种实现等价披露。

## 四、论文动作清单（K4 后定稿）

1. **标题**：删 "Routing"——改为 "Jointly-Learned Boundary-Risk Posterior for Wind-Turbine Reserve Diagnosis at the MPPT-to-Pitch Boundary"（或保留 SCADA-anchored 修饰）。
2. **摘要/贡献重写**：机制 = 联合学习（后验-误差校准）；三个支撑：定价价值（vs GBDT 1.6M）、退化可用性（0.933 vs 0.196）、可观测性谱系。
3. **新增机制定位表**（核心表）：soft-pab / gate 后验 / dense 后验 / GBDT 后验 / global 五行的定价对比 + K2 多通道分类器鲁棒性——这张表回答"为什么联合学习"。
4. **soft-pab-bin 诚实基线**：正文明确"物理连续量分箱是干净观测下的最优定价基线"。
5. **删除/降级**："MoE 架构增量"表述、"gate-bin 硬路由价值"、"P(pitch) 优于软规则"。
6. **诚实披露**：Kelmarsh 定价增量不显著（K1 负结果）；MoE 与 Dense 后验等价（K4）。
7. 模型选择叙事改为："在联合学习机制下，gate 与 dense 分类头等价；论文保留 gate 作为实现（不确定度维度略优 147k + 专家结构提供可解释性），但贡献声明不依赖该选择。"

## 五、数据溯源

- 脚本：`scripts/soft_rule_contrast.py`、`scripts/degraded_gate_reserve.py`、`scripts/kelmarsh_reserve_pricing.py`、`scripts/multichannel_classifier.py`、`scripts/gbdt_reserve_pricing.py`
- 产物：`artifacts/breakthrough_20260904/`（本地）+ grokking 同名目录
