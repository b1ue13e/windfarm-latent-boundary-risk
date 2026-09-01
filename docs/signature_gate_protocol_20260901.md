# 路线 C 实验协议：Signature-Gate（无定义通道的控制边界可识别性）

> 日期：2026-09-01 ｜ 状态：预声明（pre-registered decision thresholds，先于实验运行）
> 背景：第三轮严苛评审（`tste_harsh_review_round3_20260901.md`）指出论文创新性受循环性天花板压制：regime 标签是 `Wspd × Pab_mean` 的确定性阈值函数，而 gate anchor 恰好含这两个通道。本协议把循环性从"缺陷"转化为"中心实验"。

## 1. 研究问题

当 gate 在**任何时刻、任何通路**都看不到标签定义通道（`Wspd`、`Pab_mean`）时，MPPT-to-pitch 控制边界是否仍可从"控制动作后果通道"（`Patv`、`Prtv`、`Pab_std`、wake score、方向、温度）中识别？

若可识别，论文故事从"约束 gate 拟合声明边界（近循环）"升格为"**控制边界可通过其气动/电气指纹间接识别**（机制发现）"；若不可识别，则实证封死"间接识别"路线，论文退回审计协议定位并启动路线 A（Kelmarsh 限电真实标签）。

## 2. 假设与判据（预声明，不可事后修改）

- **H1（主假设）**：`signature_full` 变体 5 种子 mean NMI ≥ 0.40 **且** min-seed NMI ≥ 0.30。
  - H1 成立 → 控制边界经后果通道部分可识别，论文按 §6 成功预案重写。
- **H2（次假设，分析性，不设硬门）**：`signature_full` − `signature_core` 的 ΔNMI ≥ 0.15 → 指纹主要由功率通道承载；Δ < 0.15 → 非功率指纹（Pab_std/Prtv/wake）独立存在。
- **灰色区**：mean NMI ∈ [0.20, 0.40) → 部分可识别，贡献 = "部分可识别性 + 审计协议"，路线 A 并行推进。
- **Failure condition（路线 C 关闭）**：mean NMI < 0.20 → 边界仅经定义通道可观测，主线切路线 A。

**参照系**（既有证据，预声明）：
| 参照 | NMI | 含义 |
| :--- | :--- | :--- |
| canonical 全 anchor（train-only） | 0.721 | 定义通道完全可及的上界参照 |
| lagged_pab_wspd（弱访问） | 0.684 | 定义通道延迟一步 |
| unconstrained MoE | 0.014 | 无对齐监督的下界 |
| chance | ≈0 | 常数/随机路由 |

选择 0.40 的依据：约为 canonical 上界的一半，且显著高于任何先验泄露可解释的水平；0.20 以下与 unconstrained MoE 的 0.014 差距不足以支撑"可识别"措辞。

## 3. 变体定义（预声明）

| 变体 | features.npy 零化 | physics_model.npy 零化 | 模型剩余可见 |
| :--- | :--- | :--- | :--- |
| `signature_full` | `Wspd`, `Pab_mean`（mask=0） | `Wspd`, `Pab_mean` | Wdir±, Ndir±, Etmp, Itmp, Pab_std, Prtv, Patv_hist + anchor[wake_score, Patv] |
| `signature_core` | 上列 + `Patv_hist` | 上列 + `Patv` | Wdir±, Ndir±, Etmp, Itmp, Pab_std, Prtv + anchor[wake_score] |

关键设计决定：
1. **raw `physics.npy 不零化`**——模型只读 `physics_model.npy`（`windfarm_moe/data.py:140`），raw physics 仅供评估/分析（边界带审计、saved anchor_physics.npy），保持评估口径与 canonical 运行可比。
2. **`regime_primary.npy` / `regime_primary_valid.npy` 不动**——标签独立存储，变体机制物理上无法污染标签（已核实 `_apply_variant` 不触碰）。
3. **动态尾流图不动**——edge 张量在预处理时由原始 Wdir 计算并缓存（(35280,134,5)），Wdir 为保留通道。
4. **target/target_mask 不动**——预测任务本身不变，仅输入可观测性收紧。
5. 工业语义：两个变体等价于"风速仪/桨距角（/功率）通道被 QC 挂起或传感器故障"的部署场景——为主稿标签退化故事提供真实语义出口。

## 4. 训练协议（与 canonical anchor-stress 完全一致，保证可比性）

`moe_full_no_aux`（bal+align+force），align_weight=5000, force=10000, bal=1000, epochs=20, patience=5（早停仅监控 val RMSE——与 headline 运行同一盲区，seed 203 教训如实记录，不专为签名变体修协议）, seeds 201–205, strict-mask 评估缓存, batch 16, hidden 64, experts 4, tau 0.7, lr 2e-3。

队列：2 变体 × 5 种子 = 10 runs，约 1 h/run（445 s/epoch × 6–9 epoch），远程 4×4090 并行 ≈ 3 h 完成。

## 5. 反泄漏与诚信核查

- [x] 标签独立存储（`regime_primary.npy`），变体机制不触碰。
- [x] 模型通路仅 features + physics_model（`data.py:140` 核实）。
- [x] 零化 = 标准化空间均值插补 + mask=0，与既有 anchor-stress 变体同一约定。
- [ ] 运行后：对 `signature_full` 各 seed 从 `gate_prob.npy` 补 gate 熵收敛诊断（seed-203 型崩塌排查）。
- [ ] 若 H1 成立，补做 `signature_shuffled`（标签打乱负对照）以排除监督泄漏的残余解释。

## 6. 论文预案（按结果分支，预声明）

**H1 成立**：
1. 新增小节 "Control-boundary identifiability from consequence channels"，主表：signature_full/signature_core 的 NMI/ARI/RMSE cost ± sd（median/IQR 同报）。
2. 循环性防御段重写：标签与输入不共享定义通道；残存相关性来自物理（功率曲线、变桨不平衡、尾流），这正是 MoE 的存在理由（指纹无已知确定性规则）。
3. 泛化故事升级：跨场实验下一步测"signature 可迁移性"（LHB/Kelmarsh signature-gate 重跑），替代已死的"参数/阈值迁移"问题。
4. 摘要贡献第一条改为"间接可识别性 + 审计协议"。

**灰色区**：贡献 = "部分可识别性 + 审计协议"，signature 表进补充材料，主稿维持评审三推荐的软后验分级主线（路线 B），并行启动路线 A。

**Failure condition 触发**：结果写为 limitation 的实证封死（"边界仅经定义通道可观测"），强化审计协议定位；主线切路线 A（Kelmarsh 限电/Status 真实标签基准）。

## 7. 执行记录（运行后填写）

- [x] 本地缓存构建与单元测试：`artifacts/cache_signature/wtb_245d_{signature_full,signature_core}`（源 `cache_strictmask`）；`tests/test_anchor_stress.py::test_signature_variants_remove_defining_channels_only` 通过（7/7）。
- [x] 本地 smoke 训练（1 epoch, limit batches）：`artifacts/signature_smoke/`，评估链路（NMI/ARI/混淆矩阵/expert usage）全通。
- [x] 远程缓存构建：`grokking:/root/paper3_audit_rerun_20260830/artifacts/cache_signature_trainweight/`（源 `cache_strictmask_trainweights`，与 train-only 干净证据线同源，零化语义逐通道核验一致）。
- [x] 远程 10 runs 队列：2026-09-01 16:15 启动（`run_signature_gate.sh`，4 GPU 工人 3/3/2/2 均衡），日志 `logs/signature_gate_20260901/`，预计 3–6 h。
- [ ] guard 汇总（队列自动执行：`artifacts/signature_gate_guard_20260901/`，min-nmi 0.40）+ gate 熵诊断（从各 run `test_metrics/gate_prob.npy` 补）。
- [ ] 结果判定（对照 §2 预声明阈值）
- [ ] 结果文档 `signature_gate_results_YYYYMMDD.md`

### 回收与分析命令（结果回收时执行）

```bash
# 远程：队列与 guard 状态
ssh root@192.168.17.251 "cd /root/paper3_audit_rerun_20260830 && cat logs/signature_gate_20260901_queue.log && cat artifacts/signature_gate_guard_20260901/anchor_stress_guard.json"
# 本地回收
scp -r root@192.168.17.251:/root/paper3_audit_rerun_20260830/artifacts/signature_gate_runs_20260901 artifacts/
scp -r root@192.168.17.251:/root/paper3_audit_rerun_20260830/artifacts/signature_gate_guard_20260901 artifacts/
```

判定时核对：`signature_gate_guard_20260901/anchor_stress_summary.csv` 的 `nmi_mean`（对照 §2：≥0.40 且 min-seed≥0.30 为 H1 成立；[0.20,0.40) 灰色区；<0.20 触发 failure condition）与 `signature_full − signature_core` 的 ΔNMI（H2，≥0.15 判功率通道主导）。
