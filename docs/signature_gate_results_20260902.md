# 路线 C 结果报告：Signature-Gate 实验（无定义通道的控制边界可识别性）

> 实验协议：`docs/signature_gate_protocol_20260901.md`（预声明阈值，先于结果）
> 运行时间：2026-09-01 21:02 – 23:52（远程 grokking，4× RTX 4090，--num-workers 4）
> 产物本地路径：`artifacts/signature_gate_runs_20260901/`、`artifacts/signature_gate_guard_20260901/`

## 1. 预声明判据回顾

| 假设 | 判据 | 结果 |
| :--- | :--- | :--- |
| **H1** | `signature_full`（去 Wspd+Pab_mean，保留 Patv）mean NMI ≥ 0.40 **且** min-seed ≥ 0.30 | **成立**（mean 0.5613，min 0.5350） |
| **H2** | ΔNMI(signature_full − signature_core) ≥ 0.15 | **成立**（Δ = 0.1942） |
| 灰色区 | `signature_core` mean NMI ∈ [0.20, 0.40) | **命中上沿**（mean 0.3671，min 0.3398） |
| Failure | `signature_full` mean NMI < 0.20 | 未触发 |

**结论**：路线 C **成功**。控制边界在定义通道被完全屏蔽后仍可通过后果通道（含 Patv）识别；去掉 Patv 后识别能力显著下降但仍保持部分信号。

## 2. 主结果表

| 变体 | 含义 | RMSE mean±std | NMI mean±std | NMI median [IQR] | NMI min / max | ARI mean±std | expert_usage_entropy mean |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| signature_full | 无 Wspd/Pab_mean，保留 Patv | 241.84 ± 7.19 | **0.5613 ± 0.0199** | 0.5625 [0.5543, 0.5648] | 0.5350 / 0.5901 | 0.6347 ± 0.0239 | 0.746 |
| signature_core | 再去掉 Patv | 302.10 ± 9.16 | **0.3671 ± 0.0372** | 0.3535 [0.3477, 0.3627] | 0.3398 / 0.4320 | 0.4342 ± 0.0378 | 0.405 |
| **signature_full_shuffled** | `signature_full` 但 regime_primary 被随机打乱 | 241.50 ± 10.25 | **3.99e-06 ± 2.10e-06** | 4.21e-06 [2.06e-06, 5.80e-06] | 1.77e-06 / 6.91e-06 | -1.34e-05 ± 5.28e-05 | — |
| **signature_core_shuffled** | `signature_core` 但 regime_primary 被随机打乱 | 296.69 ± 16.22 | **4.66e-06 ± 3.40e-06** | 6.12e-06 [1.41e-06, 8.64e-06] | 8.05e-07 / 8.64e-06 | -1.98e-04 ± 1.74e-04 | — |
| 参照：canonical full-anchor（train-only） | 全锚点可及 | 229.93 | 0.7208 | — | — | 0.7398 | — |
| 参照：unconstrained MoE | 无对齐监督 | — | ~0.014 | — | — | — | — |

关键观察：
- `signature_full` 保留了 canonical NMI **77.9%**（0.5613 / 0.7208），同时 RMSE 仅上升 11.9（241.84 vs 229.93）。
- `signature_core` 掉落到 canonical NMI 的 **50.9%**，RMSE 大幅上升 72.2。
- H2 的 Δ = 0.1942 说明 **Patv 功率通道是承载边界指纹的主力**，但非功率后果通道（Prtv、Pab_std、wake、方向、温度）仍保留部分可识别信号。
- **负对照成立**：`signature_full_shuffled` 的 NMI 落到随机水平（~4e-6，ARI ~ -1.3e-5），说明 `signature_full` 的 0.561 不是输入分布的偶然相关，而是需要正确 regime 监督才能恢复的真实边界指纹。
- **第二个负对照也成立**：`signature_core_shuffled` NMI 4.66e-06 ± 3.40e-06、ARI -1.98e-04，说明 `signature_core` 的 0.367 同样不是偶然；非功率后果通道的信号在打乱标签后同样崩塌。

## 3. 逐种子明细与收敛稳定性

```
signature_full:
  seed 201: RMSE=236.73 NMI=0.5648 ARI=0.6067  ent=0.827  usage=[0.64,0.29,0.07,0.00]
  seed 202: RMSE=239.87 NMI=0.5901 ARI=0.6654  ent=0.879  usage=[0.60,0.32,0.08,0.00]
  seed 203: RMSE=248.78 NMI=0.5543 ARI=0.6212  ent=1.085  usage=[0.59,0.23,0.08,0.09]
  seed 204: RMSE=251.50 NMI=0.5625 ARI=0.6527  ent=0.929  usage=[0.60,0.29,0.11,0.00]
  seed 205: RMSE=232.35 NMI=0.5350 ARI=0.6276  ent=0.008  usage=[0.00,0.00,0.00,1.00]  ← expert collapse

signature_core:
  seed 201: RMSE=308.52 NMI=0.3535 ARI=0.4251  ent=0.963  usage=[0.58,0.17,0.25,0.00]
  seed 202: RMSE=309.92 NMI=0.3477 ARI=0.4097  ent=0.001  usage=[0.00,0.00,0.00,1.00]  ← collapse
  seed 203: RMSE=286.37 NMI=0.4320 ARI=0.5011  ent=1.048  usage=[0.60,0.25,0.10,0.06]
  seed 204: RMSE=304.31 NMI=0.3627 ARI=0.4172  ent=0.001  usage=[0.00,0.00,0.00,1.00]  ← collapse
  seed 205: RMSE=301.38 NMI=0.3398 ARI=0.4180  ent=0.012  usage=[0.00,0.00,0.00,1.00]  ← collapse
```

**收敛诊断**：
- `signature_full` 仅 seed 205 出现单专家坍缩（entropy 0.008），但 NMI 仍达 0.535；其余 4/5 种子专家使用分散。
- `signature_core` 有 **3/5 种子坍缩到单专家**（entropy ≈0），仅 seed 203 保持健康路由。这意味着 `signature_core` 的 mean NMI 0.367 主要由“坍缩后仍部分对齐”的种子支撑，真实非功率指纹比均值更弱。论文中应使用 **median/IQR** 而非 mean±sd 描述 `signature_core`，并主动披露坍缩比例。

## 4. 打乱标签负对照（新增）

运行时间：2026-09-02 02:52 – 04:55（`signature_full_shuffled`）与 05:24 – 10:42（`signature_core_shuffled`，远程 grokking，`num_workers=0`）。
预注册操作：仅对 `regime_primary.npy` 做 **per-run 随机打乱**，同时把 `regime_aux_valid` 置零，保持输入通道与 `signature_full` / `signature_core` 完全相同。若模型之前是“记住输入分布的偶然相关”，则打乱标签不应影响 NMI；若边界指纹确实依赖标签所代表的物理状态，则 NMI 应崩塌。

| 指标 | signature_full_shuffled | signature_core_shuffled |
| :--- | :--- | :--- |
| NMI mean ± std | 3.99e-06 ± 2.10e-06 | 4.66e-06 ± 3.40e-06 |
| NMI range | 1.77e-06 – 6.91e-06 | 8.05e-07 – 8.64e-06 |
| ARI mean ± std | -1.34e-05 ± 5.28e-05 | -1.98e-04 ± 1.74e-04 |
| leakage_guard_pass | True（5/5） | True（5/5） |
| claim_boundary | downgrade_to_declared_anchor_constrained_routing（预期失败） | downgrade_to_declared_anchor_constrained_routing（预期失败） |

逐种子：
```
signature_full_shuffled:
  seed 201: RMSE=239.75 NMI=2.12e-06 ARI=5.12e-05
  seed 202: RMSE=232.12 NMI=6.91e-06 ARI=-1.72e-05
  seed 203: RMSE=255.83 NMI=1.77e-06 ARI=5.12e-06
  seed 204: RMSE=252.33 NMI=4.57e-06 ARI=-9.48e-05
  seed 205: RMSE=227.59 NMI=4.58e-06 ARI=-1.15e-05

signature_core_shuffled:
  seed 201: RMSE=268.92 NMI=8.05e-07 ARI=5.64e-06
  seed 202: RMSE=283.39 NMI=1.41e-06 ARI=-1.51e-04
  seed 203: RMSE=313.66 NMI=6.12e-06 ARI=-1.50e-04
  seed 204: RMSE=304.72 NMI=8.64e-06 ARI=-2.27e-04
  seed 205: RMSE=312.74 NMI=6.31e-06 ARI=-4.70e-04
```

结论：
- **两个负对照均通过**。打乱标签后 gate 路由与 regime 标签的相关性降到与无监督 MoE 同一量级（~0.014 以下），且低于 canonical 三个数量级。
- 这直接封堵了审稿人可能提出的“输入分布偶然相关”或“模型只是拟合了某种隐藏阈值”解释；`signature_full` 的 0.561 与 `signature_core` 的 0.367 都必须有正确标签 supervision 才能恢复。
- `signature_core_shuffled` 同时证明：即使 `signature_core` 3/5 种子坍缩，其残存的 0.367 对齐也不是监督格式或类别边际分布的伪影。

## 5. 对论文的直接影响

### 5.1 循环性质疑被根本性削弱

原质疑：regime 标签是 `Wspd × Pab_mean` 的确定性函数，而 gate anchor 含相同通道，等于“用定义通道拟合定义”。

本实验：gate **从未在任何时刻看到 Wspd/Pab_mean**，仍达到 NMI 0.561（保留 Patv）或 0.354（纯非功率通道）。残存相关性来自物理（功率曲线、变桨对无功/桨距不平衡/尾流的影响），而非定义通道共享。循环性从“结构性缺陷”转化为“**可量化的间接可识别性**”科学问题。

打乱标签负对照进一步证明：0.561 不是输入分布的偶然相关或隐藏阈值拟合；只有正确 regime supervision 才能恢复该 signature。

### 5.2 推荐改写的论文主线

将摘要/贡献第一条调整为：

> “We show that the MPPT-to-pitch boundary remains identifiable when the label-defining wind-speed and pitch-angle channels are withheld from the model, because the control transition leaves a detectable signature in consequence channels (active-power history, reactive power, blade-pitch dispersion, and wake state). The gate therefore does more than replay a threshold rule: it recovers a physical signature of the control law.”

具体改写动作：
1. 新增主结果表（或放入补充材料 Table A?），列 `signature_full` / `signature_core` / `signature_full_shuffled` / canonical / unconstrained 五行。
2. 在 Methods/Results 增加 “Signature-gate identifiability probe” 小节，说明变体设计（零化定义通道、打乱标签负对照、保留 raw physics 用于评估、标签独立存储）。
3. 循环性防御段重写：从“we constrain the route to a declared boundary”改为“the boundary is recoverable from consequence channels, and the route is constrained to match it where anchors are available”。
4. 泛化故事升级：下一步可重跑 `signature_full` 在 LHB / Kelmarsh（保留 Patv 的农场），测试 **signature 的跨场可迁移性**，替代已死的“参数/阈值迁移”问题。

### 5.3 必须同步披露的边界

- `signature_core` 的 3/5 种子坍缩必须写进正文或补充材料；避免把 0.367 的 mean 说成稳定信号。
- `signature_full` seed 205 的坍缩也要披露；后续可增加早停/选择监控 gate entropy 的方法论补丁。
- 当前结果仅针对 WTB；跨场 signature 可迁移性尚未验证，不能写成通用结论。

## 6. 下一步实验建议（按优先级）

1. **signature_full 跨场验证**（中优先级）：在 LHB（Patv 可观测）上重跑 `signature_full`，看跨场 NMI 是否保持；这能把泛化故事从“参数不可迁移”升级为“signature 可迁移”。
2. **早停加入 gate entropy 监控**（方法学补丁）：`signature_core` 的坍缩说明早停仅看 val_rmse 会锁定未收敛路由；加入 entropy 监控可减少坍缩种子比例，让 mean 更可信。
3. **审稿人再模拟**：用更新后的结果（含负对照）重新跑 `topconf-reviewer` 或 `claim-evidence-mapper`，确认循环性/新颖性质疑被降级到几号风险，补哪些图/表。

## 7. 决策更新

- **路线 C**：**继续**，不按 failure condition 切出。
- **路线 A（Kelmarsh 限电真实标签）**：从“主线候选”降为“平行 enrichment”，用于给标签延迟场景提供真实工业 grounding，但不是创新性主支柱。
- **路线 B（软后验风险分级）**：与路线 C 合并——论文贡献现在有两根支柱：(a) 间接可识别性（signature-gate）；(b) 规则类内软后验风险分级（E1/E3）。

## 8. 数据溯源

- 远程运行：`grokking:/root/paper3_audit_rerun_20260830/artifacts/signature_gate_runs_20260901/`
- 本地副本：`E:\论文3\artifacts\signature_gate_runs_20260901\`
- 主 Guard：`E:\论文3\artifacts\signature_gate_guard_20260901\anchor_stress_guard.json`
- 打乱标签 Guard：`E:\论文3\artifacts\signature_gate_guard_shuffled_20260902\anchor_stress_guard.json`
- core 打乱标签 Guard：`E:\论文3\artifacts\signature_gate_guard_core_shuffled_20260902\anchor_stress_guard.json`
- 分析脚本：`tmp/analyze_signature_results.py`
