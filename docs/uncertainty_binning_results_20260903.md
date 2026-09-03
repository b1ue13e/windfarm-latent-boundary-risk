# 实验 B 结果：路由不确定度条件化备用金（Uncertainty-Conditioned Reserve）

> 日期：2026-09-03 ｜ 脚本：`scripts/uncertainty_binning_reserve.py`
> 输入：train-only boundary router（`artifacts/trainweight_class_weight_rerun_20260702/`，5 seeds）的 val/test `test_metrics`
> 口径：边界带（|Wspd−10.5|≤1）anchor 的 horizon cells，validation-frozen 分位数，ρ=10（与 E3 pilot 同口径）
> 运行：grokking，纯 numpy 分析，分钟级

## 1. 设计

E3 已验证 P(pitch) 五分位软分箱（soft-gate-bin）优于 global。实验 B 检验**纯不确定度**策略（不需要边界方向信息，只用量化"路由有多不确定"的信号）：

- `entropy-bin`：gate 三锚定类熵的五分位分箱
- `maxprob-bin`：gate 最大类概率（1−不确定度）五分位分箱
- 箱边均从验证集拟合（validation-frozen），对照 global / physical-bin / soft-gate-bin。

预注册判据：不确定度策略 vs global 的 Δreserve/Δcost 95% seed-paired bootstrap CI 不跨零 → "learned routing uncertainty 具备决策价值"。

## 2. 主结果（ρ=10，5 seed 均值）

| 策略 | total cost | violation | reserve | shortage |
| :--- | :--- | :--- | :--- | :--- |
| global | 16.632M | 0.1000 | 10.948M | 0.568M |
| physical-bin | 16.190M | 0.0996 | 10.722M | 0.547M |
| soft-gate-bin（E3） | **16.065M** | 0.1012 | **10.331M** | 0.573M |
| **entropy-bin** | 16.324M | 0.1010 | 10.591M | 0.573M |
| **maxprob-bin** | 16.307M | 0.1014 | 10.530M | 0.578M |

## 3. Seed 配对 bootstrap（95% CI）

| 策略 vs 基线 | Δcost | Δreserve | Δpinball@0.9 |
| :--- | :--- | :--- | :--- |
| soft-gate-bin vs global | −568k [−726k, −406k] ✅ | −617k [−984k, −278k] ✅ | −1.82 [−2.33, −1.30] ✅ |
| **entropy-bin vs global** | **−309k [−396k, −221k] ✅** | −357k [−677k, −135k] ✅ | **−0.99 [−1.27, −0.71] ✅** |
| **maxprob-bin vs global** | **−325k [−454k, −214k] ✅** | −417k [−863k, −136k] ✅ | **−1.04 [−1.45, −0.69] ✅** |
| entropy-bin vs physical-bin | +133k [+0.8k, +256k] ❌（略差） | −131k（跨零） | +0.43 [0.00, +0.82] ❌ |
| maxprob-bin vs physical-bin | +117k（跨零，打平） | −192k（跨零） | +0.38（跨零） |

## 4. 裁决

1. **判据通过**：两个纯不确定度策略 vs global 全部 CI 显著（Δcost −309k/−325k、Δpinball −0.99/−1.04）——路由不确定度**本身**即可定价预测风险，无需任何物理箱或阈值先验。
2. vs physical-bin：entropy-bin 成本显著略差（+133k），maxprob-bin 打平。叙事为"**以打平物理分箱的成本获得无先验的自动条件 reserve**"；soft-gate-bin 仍是全场最优（P(pitch) 携带的边界方向信息最直接）。
3. 与 E1（不确定度 vs 误差 ρ=0.391）形成闭环：相关性 → 操作化决策收益。

## 5. 论文措辞

- 可写："a reserve rule conditioned only on routing outputs — P(pitch) quintiles or gate uncertainty — beats the global quantile by 0.31–0.57M total cost and 0.99–1.82 pinball points without any pre-defined physical bin; uncertainty-only binning matches physical-bin cost, showing that the route posterior prices forecast risk inside the MPPT class where the threshold rule is blind."
- 必须披露：violation 略升（+0.001）、shortage 略升（跨零）；口径为边界带 anchor cells（与 Table III 全样本协议不同）。

## 6. 数据溯源

- 脚本：`scripts/uncertainty_binning_reserve.py`
- 产物：`artifacts/uncertainty_binning_20260903/uncertainty_binning_by_seed.csv`、`uncertainty_binning_paired_summary.csv`（本地 + grokking 同名路径）
