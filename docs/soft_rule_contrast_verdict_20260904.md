# 方案 A 裁决结果：学习软后验 vs 软化规则（Soft-Rule Contrast）

> 日期：2026-09-04 ｜ 脚本：`scripts/soft_rule_contrast.py`、`scripts/degraded_gate_reserve.py`
> 判据（预注册）：soft-gate-bin 必须在 95% seed-paired CI 上显著优于所有软规则分箱 → 学习有增量；否则贡献降级为"连续性分箱"。

## 1. Clean 条件（ρ=10，5 seeds，边界带）

| 策略 | total cost | vs global | vs physical-bin |
| :--- | :--- | :--- | :--- |
| global | 16.632M | — | — |
| soft-dist-bin（\|Wspd−10.5\|） | 16.615M | −17k | +425k ❌ |
| soft-wspd-bin（Wspd） | 16.250M | −382k ✅ | +60k ❌ |
| physical-bin | 16.190M | — | — |
| soft-gate-bin（P(pitch)） | 16.065M | −568k ✅ | −125k（跨零） |
| **soft-pab-bin（Pab 连续量）** | **15.538M** | **−1.09M ✅** | **−652k ✅ [−803k,−500k]** |

**Head-to-head**：soft-pab-bin 比 soft-gate-bin 低 **526k [330k, 719k]**（CI 不跨零）。

## 2. 退化条件（soft-gate-bin 由退化输入重算；软规则分箱量被同样退化）

| 条件 | soft-gate-bin（重算） | soft-pab-bin | 优势方 |
| :--- | :--- | :--- | :--- |
| clean | 16.065M | 15.538M | soft-pab −526k ✅ |
| delay 1 | 16.068M | 15.560M | soft-pab −508k ✅ |
| delay 3 | 16.091M | 15.763M | soft-pab −328k ✅ |
| delay 6 | 16.105M | 16.048M | soft-pab −57k（近打平） |
| noise (1.0, 2.0) | 16.424M | 16.035M | soft-pab −389k ✅ |

## 3. 裁决

**预注册判据失败**：学到的 P(pitch) 分箱在**任何条件**下都不优于纯 Pab 连续量分箱，clean 时差 526k（显著）、强噪声下仍差 389k。"soft-gate-bin 定价"作为创新点**死亡**，贡献三必须重写。

**为什么 Pab 分箱这么强**：Pab 本身就是边界靠近度的直接物理读数；σ=2° 的噪声和 6 步延迟不足以摧毁其分箱信息。这印证了审稿人可能的攻击——"学习"在这里没有超过"软化"。

## 4. 修正后的主线（仍然成立的增量）

裁决后剩余的真正增量只有三个，全部集中在 **Pab 退化/缺失** 条件下：

1. **Pab 缺失农场**（Kelmarsh 55% / Penmanshiel 78% pitch 稀疏）：soft-pab-bin 需要 Pab 观测，一半 cells 不可用；gate 的 P(pitch) 从后果通道恢复（谱系 0.34/0.38）。→ 需补实验：Kelmarsh 上 soft-gate-bin vs global 的 reserve 对比。
2. **不确定度定价**（entropy/maxprob 分箱）：不确定度是 Pab 给不出的维度（实验 B 已证 vs global 显著 −309k/−325k）。
3. **早期预警鲁棒性**（实验 A 0.933 vs 0.196）：仍需方案 B（多通道分类器对照）排除"通道数量"解释。

## 5. 对论文的动作

- 贡献三重写为："Pab 可观测且干净时，Pab 软分箱是诚实披露的最优定价基线；Pab 延迟/缺失时，路由后验与路由不确定度是唯一可用的软定价信号。"——把 soft-pab-bin 从"我们的方法"移入"诚实基线"，把故事重心移到退化/稀疏条件。
- Table A11b 加 soft-rule 行 + 退化行。
- 必须补的实验（按信息量排序）：
  1. Kelmarsh（pitch 55%）soft-gate-bin vs global reserve（裁定"稀疏农场上 gate 定价是否有值"）。
  2. 方案 B 多通道分类器 signature/鲁棒性对照（裁定"MoE vs 多通道"）。

## 6. 数据溯源

- `artifacts/soft_rule_contrast_20260903/`、`artifacts/degraded_gate_reserve_20260903/`（本地 + grokking 同名路径）
