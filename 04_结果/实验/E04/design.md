# 实验 E04：P1: 条件性最小充分决策准则验证

- 假设：—
- 目的：在冻结到达信息集、冻结点预测与冻结短缺目标下，验证预注册的风险约束复杂度选择准则是否能在各观测条件中选择不劣于强直接基线且复杂度最低的决策函数；若没有候选满足约束，则记录无可行最小充分模型。
- 创建：2026-10-17T08:15:54.905Z

## 设计
1. 在执行任何测试前冻结 `alpha`、`epsilon_C`、`epsilon_V`、绝对违约率上限 `v_max`、候选模型集合、复杂度字典序、单位复制、总体切片和联合种子/日块不确定性程序；未冻结前不得执行 claim-bearing test。
2. 对每个信息条件 `I` 和候选 `m` 计算固定目标 PSREI 差分、违约率差分及其单侧上置信界，基线 `b_I` 必须使用同信息集下的强直接条件分位数策略。
3. 按预注册复杂度序选择第一个满足风险约束的候选；同时报告 `NO FEASIBLE POLICY`、并列、选择不稳定和外部站点窗口不一致等失败状态。
4. 用回放工件复核选择结果不依赖事后调阈值、不使用未来状态切片作为在线选择器；representation metrics 不得替代 decision metrics。
5. 只有在阈值冻结、结果归档和独立 falsification review 完成后，才允许把条件性 deployment map 写成 supported；否则结论为 pending/inconclusive。

## 预注册形式

对 `P` 上的政策集合 `M(I)`：

```text
m*(I,rho,epsilon_C,epsilon_V) = argmin_m Complexity(m)
```

subject to:

```text
U_(1-alpha)[C_P(m)-C_P(b_I)] <= epsilon_C,
U_(1-alpha)[V_P(m)-V_P(b_I)] <= epsilon_V,
U_(1-alpha)[V_P(m)] <= v_max.
```

完整符号、复杂度序和允许解释见 `docs/MINIMUM_SUFFICIENT_DECISION_CRITERION.md`。

## 预注册冻结（执行前写入）

- `alpha = 0.05`; 所有约束使用 one-sided 95% upper confidence bounds。
- `epsilon_C = 0 kWh`; candidate 不能在 PSREI 上被证明劣于同信息强基线。
- `epsilon_V = 0`; candidate 不能被证明有更高违约率差分。
- `v_max = 0.10`; absolute violation cap follows the nominal q=0.90 Newsvendor target。
- 单位复制：5 个训练种子与 35 个连续日级块的联合 seed-by-block bootstrap；不把 cell 当独立复制单位。
- 选择总体：WTB full test population；transition/steady 只作为预注册诊断切片，不改变 primary selection。
- 主要候选：Site-Local Wspd-Bins、Posterior-Conditioned Quantile、Validation-Frozen Hybrid、Pre-Specified Boundary-Band Hybrid。仅使用已有冻结输出，不新增模型或重新调参。
- 复杂度序：Site-Local Wspd-Bins < Posterior-Conditioned Quantile < Validation-Frozen Hybrid < Pre-Specified Boundary-Band Hybrid。该序按部署所需信息、规则复杂度和在线选择器依赖定义，不按参数量单独定义。
- 选择策略：按复杂度序选择首个满足三个约束的 candidate；若没有 candidate，返回 `NO FEASIBLE POLICY`；若 bootstrap 选择频率低于 0.80，则返回 `UNSTABLE SELECTION`。
- 禁止：使用 post-hoc transition oracle 作为在线 selector；看到结果后修改阈值、候选集、complexity order、baseline 或 uncertainty procedure。

## 预期结果

## 结果状态

E04 primary selector completed on Metis v4 replay outputs. The preregistered selector returned `NO FEASIBLE POLICY`: Policy B itself had absolute violation UCB 0.11419 > `v_max=0.10`; C/D/D10 also failed the absolute violation cap and/or cost/violation UCB constraints. Full result is `results/e04_selection.json`. This is a valid no-feasible-policy outcome, not a reason to relax thresholds.

## 观察（Observation）

E05 稳定性诊断已作为独立补充实验登记并执行。基于冻结 v4 五 seed 政策数组的 10,000 次联合重采样，`NO FEASIBLE` 频率为 0.6464，B 的首个选择频率为 0.3523，未达到预注册的 `>=0.80` 稳定性规则。该诊断条件于未绑定原始 replay receipt 的本地 v4 数组，不改变 E04 的 `NO FEASIBLE POLICY` 主结果，也不构成 minimum-sufficient policy 的认证。
