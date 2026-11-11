# 🏛️ Top-Tier Conference Reviewer Simulation Report（含 Signature-Gate 负对照后）

> 评审对象：`paper_tste_ieee.md` + `paper_tste_supplementary.md` + `docs/signature_gate_results_20260902.md`
> 评审日期：2026-09-02 ｜ 目标期刊：IEEE TSTE Regular Paper
> 立场：三位对抗性审稿人 + AC 综合裁决，**拒稿优先**。
> 与 2026-09-01 第三轮 harsh review 的关系：本次仅评估 **Signature-Gate 路线 C 完成后的增量影响**，其他 P0 仍按前序报告处理。

---

## 📊 Executive Summary & Acceptance Calibration

| 会议/情形 | 录用概率 | 风险等级 | 说明 |
| :--- | :--- | :--- | :--- |
| **NeurIPS / ICML / ICLR（按顶会标准）** | ~10–15% | **Critical** | 非标准 ML 基准、故事动机偏工业、且未解决稿证一致性与统计 rigor 问题 |
| **IEEE TSTE（当前稿直接投）** | ~15–25% | **Critical** | 旧 P0 几乎全部未修；signature-gate 证据未写入正文，等于尚未发生 |
| **IEEE TSTE（完成 P0 重写 + 本证据并入）** | ~55–65% | **Medium** | 循环性质疑被显著削弱；若再补 LHB signature 验证、E1/E3 官方化、窗口稳健性扫描，可上探 70% |
| **Applied Energy / Wind Energy / EAAI** | ~70–80% | **Low** | bounded diagnostic + audit protocol 故事对二区刊已足够 |

**一句话裁决**：`signature_full_shuffled` 负对照把最致命的“循环性/阈值重放”攻击从 **致命** 降级为 **可辩护**；但它没有解决稿件与自身仓库证据的方向性矛盾，也没有自动把证据写进正文。论文当前仍处于“仓库已翻案、稿件未签收”状态。

---

## 👤 Reviewer #1 (Theory & Novelty Hawk)

**Summary**：Signature-gate 实验直接回应了 R1-1 的循环性质疑，使核心贡献的叙事有了机制支撑；但创新性声明仍需从“硬路由外延”迁移到“软后验风险分级 + 不确定度定价”，否则整体 novelty 仍显薄弱。

**Strengths**：
1. `signature_full` 在 gate 输入中完全移除 `Wspd`/`Pab_mean` 后仍达到 NMI 0.561（5/5 seeds，min 0.535），说明路由不只是阈值规则的重放。
2. `signature_full_shuffled` 负对照设计干净：仅打乱 `regime_primary.npy`、保持输入通道不变，NMI 崩塌到 ~4e-6。这有效封堵了“输入分布偶然相关”或“隐藏阈值拟合”解释。
3. `signature_core`（再去掉 `Patv`）NMI 仍有 0.367，说明非功率后果通道也携带边界指纹；虽然存在专家坍缩，但这一现象本身可转化为方法论讨论。

**Weaknesses**：
1. **[Novelty Attack, 降级但未消除]**：0.561 的“间接可识别性”是一个正面结果，但它仍未证明 gate 比“先用可用通道估计 Wspd/Pab_mean，再套规则”更好。如果审稿人认为 Patv 历史可以反推风速/桨距，则 signature_full 仍可能被视为“通过另一条路径重建定义通道”。论文必须明确回答：**为什么 gate 的 soft partition 比两步规则更有价值？**
2. **[Theoretical Rigor]**：`signature_core` 3/5 种子坍缩到单专家，mean NMI 0.367 的稳定性存疑。用 mean±sd 报告会误导；需要 median/IQR + 收敛分层。
3. **[Scope]**：当前 signature-gate 仅在 WTB 上完成，LHB / Kelmarsh / Penmanshiel 尚未验证。审稿人会质疑这是“数据集特调”还是一般规律。

**Score**：Soundness: 2.5/4 | Novelty: 2.5/4 | Overall: 5/10 | Confidence: 4/5

---

## 👤 Reviewer #2 (Empirical & Baseline Nitpicker)

**Summary**：负对照实验的实验设计可接受，但统计呈现和与正文的整合仍严重不足；baseline、对照完整性、以及 old evidence 未切换的问题仍是主要攻击面。

**Strengths**：
1. 5 seeds 已达标，且负对照与正样本使用同一训练/验证/测试协议，可比性高。
2. `leakage_guard_pass=True` 说明没有测试集泄漏或 checkpoint 选择泄漏。
3. 输入通道零化 + 标签打乱的双重控制，比单纯的“去掉 anchor”消融更能隔离因果解释。

**Weaknesses**：
1. **[Missing Control]**：没有报告 `signature_core_shuffled` 负对照。虽然理论上它也应接近 0，但未跑就是未跑；审稿人可能要求补一个，以证明 `signature_core` 的 0.367 也不是偶然。
2. **[Statistical Rigor]**：
   - 5 seeds 的 mean±sd 对 NMI 这种有上界 1 的指标 presentation 不佳，应补 median/IQR。
   - 未对 `signature_full` vs `signature_core` 的 ΔNMI=0.1942 做显著性检验（配对 t / Wilcoxon）。
   - 未报告 expert collapse 对 NMI 的条件分布影响。
3. **[Integration with Main Paper]**：当前证据只存在于 `docs/signature_gate_results_*.md`，未写入 `paper_tste_ieee.md`。在审稿人眼里，这等于没有。
4. **[旧 P0 未修]**：主稿 headline 数字仍是 legacy 口径；A6 符号翻转、Kelmarsh 部署门翻案、全基线表缺失、ERA5 悬空引用等问题全部未因本实验而自动修复。

**Score**：Soundness: 2.5/4 | Rigor: 2.5/4 | Overall: 4.5/10 | Confidence: 5/5

---

## 👤 Reviewer #3 (Impact & Pragmatist Critic)

**Summary**：Signature-gate 让“动机是否成立”的辩护更有力——它证明了即使确认标签流被延迟或缺失，边界仍可从后果通道恢复；但工业 grounding 和场景语义问题依旧。

**Strengths**：
1. 结果支持论文的核心工业叙事：SCADA 确认流可能不可用，但 MPPT-to-pitch 边界仍可通过功率/无功/桨距分散度等后果通道被审计。
2. 负对照增强了“这不是数据挖掘伪影”的可信度，对运营方的说服力提升明显。

**Weaknesses**：
1. **[Motivation & Problem Formulation]**：仍未解决 R2-1/R3-1 的“场景语义”问题。0.960 vs 0.196 的延迟标签实验建立在“gate anchor 不退化、rule 退化”的不对称构造上；signature-gate 本身没有给这个场景增加真实工业 grounding。
2. **[Limitations]**：论文尚未正式承认 signature-gate 的边界——WTB -only、专家坍缩比例、跨场未验证、无 `Patv` 农场如何应用。
3. **[Deployment Cost]**：signature_full 的 RMSE 241.84 已比 canonical 229.93 高 11.9；若再失去 Patv（signature_core），RMSE 飙到 302.10。运营方会问：为了“可审计”而牺牲 5–30% 的预测精度，是否划算？论文需要把代价写进 abstract 和 limitations。

**Score**：Soundness: 3/4 | Significance: 2.5/4 | Overall: 5/10 | Confidence: 4/5

---

## 📋 Official Paper Checklist Audit（NeurIPS / ICLR 风格映射到期刊）

- [❌] **Q1 Claims & Evidence**：`signature_full_shuffled` 证据存在，但未进入正文或补充材料。
- [❌] **Q2 Limitations**：未主动披露 signature_core 坍缩、WTB-only、跨场未验证、RMSE 代价。
- [⚠️] **Q3 Theory Assumptions**：间接可识别性的物理解释已有，但未形式化“定义通道 / 后果通道”的分离。
- [⚠️] **Q4 Error Bars & Seeds**：5 seeds 达标，但缺少 median/IQR、显著性检验、收敛分层。
- [❌] **Q5 Compute & Reproducibility**：signature-gate 运行成本、缓存构建、远程环境未披露。
- [❌] **Q6 Baseline Completeness**：缺少 `signature_core_shuffled` 负对照、无 unconstrained MoE 在该协议下的直接对比。

---

## 🚨 P0 致命缺陷拦截清单（本证据可影响的 + 仍需处理的）

### 因 signature-gate 而降级的风险
1. **[P0-NEW-1] 循环性/阈值重放攻击**：从 **致命** 降级为 **可辩护**。需在正文中写入 signature-gate 结果并明确回应。

### 未因本证据而消除的风险（仍需按原 P0 处理）
2. **[P0-OLD-1] 稿证一致性**：摘要/正文/A6/A8/Discussion/cover letter 仍与仓库最新证据矛盾。
3. **[P0-OLD-2] 场景语义**：延迟/缺失标签实验的构造仍需 Kelmarsh Status/限电流 grounding 或公平退化。
4. **[P0-OLD-3] 贡献迁移**：E1/E3 软后验信号仍未官方化进主稿。
5. **[P0-OLD-4] 统计报告升级**：median/IQR、收敛分层、时间块 bootstrap 仍缺。
6. **[P0-OLD-5] 呈现补齐**：全基线表、单位、算力、控制文献、ERA5 节或删承诺、图重生成。

### 因 signature-gate 新增的 P0
7. **[P0-NEW-2] 必须披露 `signature_core` 3/5 坍缩**：否则 0.367 会被视为稳定信号，构成误导。
8. **[P0-NEW-3] 必须披露 WTB-only 与跨场未验证**：不能写“signature 可迁移”除非 LHB 验证完成。
9. **[P0-NEW-4] 必须披露 RMSE 代价**：signature_full +11.9、signature_core +72.2。

---

## 🧪 最小化补实验清单（含 signature-gate 后）

| 优先级 | 实验 | 成本 | 翻转的审稿意见 |
| :--- | :--- | :--- | :--- |
| 1 | 把 signature-gate 结果写入正文 + 补充材料 Table A | 低 | R1-1 / R2-3 |
| 2 | `signature_core_shuffled` 负对照（5 seeds） | 低（~2h） | R2-1 |
| 3 | `signature_full` vs `signature_core` 配对显著性检验 + median/IQR | 低（分析） | R2-2 |
| 4 | LHB `signature_full` 跨场验证 | 中（~2–4h） | R1-3 / R3-3 |
| 5 | 早停加入 gate entropy 监控，重跑 signature_core | 中 | P0-NEW-2 |
| 6 | 证据切换 + E1/E3 官方化 | 低–中 | P0-OLD-1/2/3 |
| 7 | 主稿全基线表/单位/算力/控制文献/图重生成 | 低 | P0-OLD-5 |

---

## 🛡️ 预备 Rebuttal 防御策略

- **针对循环性（Reviewer #1）**：
  > “The gate is never exposed to the wind-speed or pitch-angle channels that define the operating boundary. On the withheld-channel probe, the gate still recovers NMI 0.561; when the same labels are permuted, NMI collapses to 4e-6. The partition is therefore not a replay of the threshold rule but a physical signature learned from consequence channels.”

- **针对稳定性（Reviewer #2）**：
  > “We report median/IQR alongside mean±sd and disclose that 3/5 seeds of the Patv-ablated variant collapse to a single expert. The reported mean for that variant is thus an upper envelope, not a stable operating point.”

- **针对工业价值（Reviewer #3）**：
  > “The signature-gate probe bounds the auditability cost: retaining Patv raises RMSE by only 11.9 units while recovering 78% of the clean-anchor alignment. Removing active power raises the price sharply (RMSE +72.2), which we treat as a deployment limitation rather than a recommended configuration.”

---

## ⚠️ Kill / Pivot 条件（本证据引入后）

- 若 `signature_core_shuffled` 跑出 NMI > 0.05 → `signature_core` 的 0.367 可能也是伪信号，需删除“非功率后果通道仍携带边界指纹”的表述。
- 若 LHB `signature_full` 跨场 NMI < 0.30 → “signature 可迁移”叙事不成立，signature-gate 只能作为 WTB 机制解释，不能支撑泛化。
- 若公平退化实验显示 gate 与 rule 在同等噪声/延迟下无差异 → 延迟标签主线删除，论文重心完全转向 reserve 软分箱 + 不确定度定价。
