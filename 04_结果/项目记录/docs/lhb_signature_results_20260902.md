# LHB 跨场 Signature 验证结果报告

> 协议与适切性判断：`docs/lhb_signature_feasibility_20260902.md`
> 运行时间：2026-09-02 17:44 – 21:53（远程 grokking，3× RTX 4090，num_workers 4）
> 判据（预注册）：`signature_full` LHB mean NMI ≥ 0.40 且 min-seed ≥ 0.30 → 跨场成立；< 0.30 → kill。
> 产物：`artifacts/signature_gate_lhb_runs_20260902/`、`artifacts/signature_gate_lhb_guard_20260902/`

## 1. 主结果

| 变体 | NMI mean ± std | NMI min / max | ARI mean ± std | RMSE mean ± std | claim |
| :--- | :--- | :--- | :--- | :--- | :--- |
| canonical（全 anchor 同协议） | **0.9752 ± 0.0088** | 0.9599 / 0.9824 | 0.9904 ± 0.0044 | 185.0 ± 1.9 | 全 anchor 边界高度可识别 |
| signature_full（去 Wspd/Pab_mean） | **0.6743 ± 0.1209** | **0.4985 / 0.7943** | 0.7401 ± 0.1604 | 185.1 ± 1.4 | **跨场成立** |
| signature_core（再去 Patv） | **0.5750 ± 0.0423** | 0.5195 / 0.6108 | 0.6270 ± 0.0638 | 188.0 ± 1.0 | 非功率后果通道跨场信号强 |
| **signature_full_shuffled** | **1.92e-04 ± 8.90e-05** | 4.80e-05 / 2.82e-04 | 5.19e-04 ± 2.86e-03 | 185.4 ± 1.2 | **负对照：随机水平** |

逐种子：

```
canonical:              201:0.977 202:0.960 203:0.982 204:0.979 205:0.978
signature_full:         201:0.742 202:0.794 203:0.498 204:0.603 205:0.733
signature_core:         201:0.607 202:0.611 203:0.520 204:0.598 205:0.540
signature_full_shuffled:201:4.80e-05 202:1.78e-04 203:2.37e-04 204:2.17e-04 205:2.82e-04
```

## 2. 判据裁决

- **H1-LHB 通过**：`signature_full` mean NMI 0.674 ≥ 0.40，min-seed 0.499 ≥ 0.30。
- **Kill 条件未触发**：0.674 ≫ 0.30 → signature **不是 WTB 特设**，边界指纹在 LHB（同一阈值定义、不同风机型号与场地）同样存在。
- 相对保持率：`signature_full` 保留 canonical 的 **69.1%**（0.674/0.975）；`signature_core` 保留 **59.0%**。
- **负对照通过**：`signature_full_shuffled` NMI 1.92e-04 ± 8.90e-05，远低于 0.40 门槛，仅比 WTB 的 4e-06 高一个量级，仍属随机水平；封堵了"LHB 输入分布偶然相关"解释。

## 3. 与 WTB 的对比

| 变体 | WTB | LHB | 方向 |
| :--- | :--- | :--- | :--- |
| canonical | 0.7208 | 0.9752 | LHB 数据更干净（4 台新 Senvion、pitch 实测 99.2%、无尾流混淆） |
| signature_full | 0.5613 | **0.6743** | LHB 更高 |
| signature_core | 0.3671（3/5 坍缩） | **0.5750（0/5 坍缩）** | LHB 显著更高且稳定 |

关键观察：
1. 非功率后果通道（Prtv/Pab_std/环境通道）在 LHB 上信号更强（0.575 vs 0.367），且**无一坍缩**——WTB 的坍缩是数据集噪声特性，不是方法缺陷。
2. LHB 的 signature_full 跨种子波动大于 WTB（std 0.121 vs 0.020），min 0.499；报告时应使用 mean±sd + min 披露，避免 overclaim 稳定性。
3. RMSE 几乎不随通道遮蔽变化（185.0 → 185.1 → 188.0），说明 LHB 的预测任务对边界通道不敏感，但路由对齐仍需要它们——signature 效应与预测精度解耦。

## 4. 对论文的影响

- 泛化叙事升级成立：从"signature 仅 WTB"升级为"**signature 在 WTB 与 LHB 两个 anchor-observable 农场均可恢复**"。
- 建议正文措辞："the boundary signature transfers across farms under a shared threshold definition"——**不是**参数/权重迁移，而是**机制可复制性**（mechanism replication across farms）。
- 必须披露：LHB 4 节点小规模、signature_full 种子波动（min 0.499）、wake_score 恒 0（无尾流维度）。
- 下一步可选：LHB `signature_core_shuffled` 负对照（2026-09-03 完成：NMI 2.40e-04 ± 1.23e-04，随机水平 ✓），或直接进入论文主线重写。

## 5. 数据溯源

- 远程运行（LHB 主实验）：`grokking:/root/paper3_audit_rerun_20260830/artifacts/signature_gate_lhb_runs_20260902/`
- 远程运行（LHB 负对照）：`25979:/root/paper3_audit_rerun_20260830/artifacts/signature_gate_lhb_shuffled_runs_20260902/`
- 本地副本：`E:\论文3\artifacts\signature_gate_lhb_runs_20260902\`、`E:\论文3\artifacts\signature_gate_lhb_shuffled_runs_20260902\`
- Guard：`E:\论文3\artifacts\signature_gate_lhb_guard_20260902\anchor_stress_guard.json`、`E:\论文3\artifacts\signature_gate_lhb_shuffled_guard_20260902\anchor_stress_guard.json`
