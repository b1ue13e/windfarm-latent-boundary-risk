# F6 专项审计报告：旧日志、旧审计与控制面可重新污染结论

**报告日期：** 2026-10-13  
**问题编号：** Issue F6  
**上游审计：** `docs/REVERSE_SCIENTIFIC_AUDIT_20261012.md` §F6  
**审计对象：**
1. `experiments/E01/log.md`（及 `design.md`、`README.md`）
2. `docs/NO_GRAPH_CONTROL_AUDIT.md` 与 `artifacts/no_graph_architecture_audit.json`
3. `docs/EXPERIMENT_REGISTRY.md`（EXP-01 / EXP-Q2-003 / EXP-03）
4. `.agents/verification_manifest.json` 与 `scripts/verify_scientific_claim_gate.py`
5. `.agent_state/{EVIDENCE_LEDGER.md,TASK_LEDGER.md,RUN_STATE.json}`

**核验状态：** `VERIFIED (DEFECTS CONFIRMED AND CLOSED)`  
**核心裁决：** F6 指出的四条证据中，**三条在本次修复前已被同日提交 `f583c572` 修复**，F6 文本在该时点已部分过期；
盲目按 F6 字面重写那几行会破坏正确内容。真正的残留缺陷位于 `experiments/E01/log.md` 与 `.agent_state` 控制面，
并且**根因是一个会在重跑时重新注入旧内容、并静默删除因果边界章节的生成脚本**。
此外本次审计发现了原 F6 **未捕捉到**的两处更严重问题：EXP-03 溯源哈希被"改标签"而非修复，以及
`no_graph_architecture_audit.json` 内部参数量自相矛盾。

---

## 一、方法：先复核 F6 自身，再修

F6 的结论写于 2026-10-12；仓库在同日 `f583c572`（15:33:46）提交了一次大范围修复。
因此本次审计的第一步**不是**执行 F6，而是逐条复核 F6 的四个证据指针在当前 HEAD 上的真实状态。
结论：**若按字面执行 F6，会把已经正确的文件改坏。**

| F6 原始指控 | 当前 HEAD 实测 | 判定 |
| :--- | :--- | :---: |
| `docs/NO_GRAPH_CONTROL_AUDIT.md` 仍使用 v1 数值 | 已无 v1 数值；`f583c572^` 版本第 56 行确有 `+1,050k to +2,154k kWh on Penmanshiel` | **F6 过期** |
| registry 同时保留 `EXP-01 completed` 与 `EXP-Q2-003 proposed/blocked` | `EXP-Q2-003` **确实仍存在**且标为 PROPOSED/BLOCKED | **成立** |
| 旧 gate 只检查旧 19 个 claim，不检查 EXP-01 v2/02/03 | `verify_scientific_claim_gate.py` §[6] 已覆盖 EXP-01(80 行)/EXP-02/EXP-03 | **F6 过期** |
| `experiments/E01/log.md` 仍把 v1 写成"跨场站普遍规律" | **确实仍存在**，且 `design.md` 仍含被自身审计禁止的"容量匹配"措辞 | **成立** |

> **注：** `verify_replication.py` 的权威 claim 集合为 **21** 条（`C01`–`C19` 再加上两条子 claim
> `C05b`、`C06b`；脚本运行输出 `ALL 21 CLAIMS VERIFIED`），其中**不含任何 EXP-01/02/03 断言**
> —— 这才是 F6"gate 覆盖不足"指控下仍然成立的实质缺口。本次已将其登记为 manifest 必需命令。
> （注：以编号字面看只到 `C19`，故早期笔记中的"19 条"是漏算了两个 `b` 后缀子 claim。）

---

## 二、根因缺陷：生成脚本会主动重新污染（原 F6 未发现）

这是本次审计最重要的发现。`docs/NO_GRAPH_CONTROL_AUDIT.md` 与 `artifacts/no_graph_architecture_audit.json`
**由脚本生成**，而脚本本身携带旧内容：

### 2.1 硬编码的参数量与结论矛盾

`scripts/audit_architecture_complexity.py` 第 164 行把结论文案硬编码为
`STGQ-Modular comprises 256,236 parameters ... (a ~53x parameter ratio)`，
而同一脚本第 121–123 行**运行时算出的**是 `110,012 vs 4,865 = 22.6x`。
于是产物 JSON 同时包含 `"total_parameters": 110012` 与"256,236 / ~53x"的正文 —— 自相矛盾。

**实测：** 重跑脚本后 stdout 明确输出 `Parameter Ratio (STGQ / No-Graph): 22.6x (110,012 vs 4,865)`。

### 2.2 文档模板硬编码 v1 数值，并**删除了因果边界章节**

修复前的模板第 237 行写死
`(+1,050k to +2,154k kWh on Penmanshiel, +888k to +1,501k kWh on Kelmarsh)` —— 正是 v1 量级。
更严重的是：当时生成的文档**只到第 3 节**，而仓库中手工维护的版本含
第 4 节"Causal Necessity Boundary: UNPROVEN / NOT ESTABLISHED"。
**这意味着任何人重跑该脚本，都会静默删除 `docs/SCIENTIFIC_CONTRACT.md` 所要求的因果必要性上限。**

### 2.3 修复

- 结论文案改为由运行时变量插值（`f"{stgq_stats['total_parameters']:,}"`、`{ratio:.1f}x`）；
- 新增 `parameter_ratio_stgq_over_nograph` 与 `causal_necessity_of_spatial_graph: "UNPROVEN / NOT ESTABLISHED"` 结构化字段；
- 摘要量级改为**从冻结的 v2 工件读取 5 种子均值**（而非种子 201 单值或硬编码）；
- 模板补回第 4 节因果边界与顶部修订说明，并在门禁中加断言防止再次丢失。

**验证：** 重跑后文档第 60 行输出 `~23x`、第 64/65 行输出 `+16.88M to +19.59M kWh on Penmanshiel`、
`+3.40M to +3.67M kWh on Kelmarsh`，与 registry 的 per-farm 5 种子均值一致；第 4 节保留。

---

## 三、残余缺陷修复

### 3.1 `experiments/E01/log.md`（v1 越界结论）

v1 条目保留为**显式作废的溯源记录**（标注 `【已作废 v1，保留为溯源】` 并给出 VERIFIED 作废理由），
新增 corrected v2 条目承载真实数值。补记 v2 关键值：

- Penmanshiel h=6：Site-Local Wspd-Bins 13,742,849 kWh（16.59% viol），
  Transferred ΔPSREI = **+5,321,915 kWh**（p=0.003，显著成本惩罚）；No-Graph +16,880,326 kWh。
- Kelmarsh h=6：3,131,041 kWh（11.80% viol），Transferred ΔPSREI = **+435,684 kWh**（p=0.196，不显著）。

同时从 `design.md` 移除"Forbidden Phrasing"清单中自己禁止的"容量匹配单机No-Graph MLP"。

### 3.2 registry 重复登记（F6 成立项）

`EXP-Q2-003` 与 `EXP-01` 是同一实验的两份状态声明。改为 **RETIRED as a duplicate registration of EXP-01**，
并明确指出唯一真正未执行的残余臂是 *site-local latent-state posterior challenger*（EXP-01 未覆盖），
避免"退役重复项"变成"掩盖未做实验"。

### 3.3 参数量 110,012 vs 256,236

已由 §2.1 的根因修复消除：正文不再硬编码，改为运行时插值。

---

## 四、原 F6 未发现的两处更严重缺陷

### 4.1 EXP-03 溯源哈希被"改标签"而非修复（F3.4 未真正解决）

registry、`docs/EXP03_ASYNCHRONOUS_REPORT.md`、`ARTIFACT_MANIFEST.json` 均把
`18079b46d01a399d47df681ec0fa48ab4a55bf0860c8bc99df2c15480bb13d49` 描述为
"Full-Grid SHA-256 provenance hash of the full-grid arrival stream"。**实测不成立：**

| 检查 | 结果 |
| :--- | :--- |
| `arrival_trace.jsonl` 真实 SHA-256 | `fcc119806e6bccad0f458a9cd6188c3150ece307ca0c63acd6b395d7904b3d9c` ≠ `18079b46…` |
| `18079b46…` 是什么 | `hashlib` 累加器，仅覆盖 `async_feat[:144,0,:]` + `dropped_mask[:144,0,:]`（`run_exp03_async_benchmark.py:498,515-516,597`） |
| trace 覆盖范围 | 1,440 包 = 节点 0–1 × 前 144 步 × τ=0；**延迟包数 = 0** |
| `missing_mask.json` | 48 个元素**全为 `false`**（占位符） |
| 可否从归档复现该哈希 | **否** |

且 2026-10-12 的 F3.4 原始描述（`d1619e…`，node 0 / 144 步 / τ=0）与"新"哈希
**覆盖范围完全相同** —— 即该缺陷被**重新贴标签**，而非修复。

**同时**，"strictly fixed … without row dropping"的说法与自身工件矛盾：
`n_evaluated_cells` 恒为 408,937 / 408,939，但 `drop_fraction` 从 0.0 升至 **60.25%**（τ=6）、
`stale_fraction` 升至 **99.79%**。即"固定总体"是 **LOCF 插补**的总体，迟延端点在测"近乎全陈旧"输入，
并非"部分刷新"的流。F3.1（`Patv_hist` 对称延迟）与 F3.2（物理量纲阈值）确认**已真修复**。

**修复：** 在 registry、报告、生成脚本模板、artifact manifest 中全部改为
"Internal Trace Digest (NOT a full-grid provenance hash)"，给出真实文件哈希与覆盖边界；
在 `docs/EXP03_INVALIDATION_NOTICE.md` 增加 **Reconciliation Addendum**（F3.1–F3.4 逐条对照表）；
并如实记录 packet-level 溯源为 **OUTSTANDING**。

### 4.2 门禁无法察觉 60% 的 drop

旧检查仅比较 `n_evaluated_cells` 的取值集合与下限（400,000），
因此**在 60.25% 行被插补/丢弃的情况下仍然 PASS**。已加强为：
同时要求 `drop_fraction`/`stale_fraction` 存在，且当 `drop_fraction > 0.5` 时 registry 必须显式披露 LOCF 边界。

---

## 五、门禁加固与回归证明

### 5.1 新增 gate §[7] Stale-Content Re-Pollution Guard

位置：`scripts/verify_scientific_claim_gate.py`。fail-closed 检查项：

1. `experiments/E01/log.md`、`docs/NO_GRAPH_CONTROL_AUDIT.md`、`docs/EXPERIMENT_REGISTRY.md` 中
   被作废的 v1 数值**不得作为活声明出现**（允许出现在 blockquote / 标题等显式作废区域内）；
2. `no_graph_architecture_audit.json` 正文参数量必须与运行时 `total_parameters` 自洽，
   且必须保留 `causal_necessity_of_spatial_graph == "UNPROVEN / NOT ESTABLISHED"`；
3. `NO_GRAPH_CONTROL_AUDIT.md` 不得丢失因果必要性上限与命名禁令；
4. registry 不得重新出现"开放 PROPOSED/BLOCKED 的重复登记"；
5. EXP-03 溯源不得再被表述为 "Full-Grid SHA-256"；
6. EXP-03 陈旧度必须被披露（`stale_fraction` 存在且 registry 提及 LOCF）。

设计要点：判据**基于区块语义**（blockquote/标题视为注解区），因此"引用并纠正"写法的文本不会误报。

### 5.2 回归证明（证明门禁非空转）

| 注入的原始缺陷 | 门禁响应 |
| :--- | :--- |
| 在 `E01/log.md` 追加活声明 `+448.0k / +48.5k` + "跨场站普遍规律" | `FAIL ... experiments/E01/log.md:32` |
| 把 EXP-01 状态行改回 `PROPOSED / BLOCKED` | `FAIL ... docs/EXPERIMENT_REGISTRY.md:308` |

两次注入后均还原，门禁回到 `PASS`。说明 §[7] 对真实缺陷敏感，而非恒真。

### 5.3 manifest 补齐

`.agents/verification_manifest.json` 的 required commands 增加 `verify_replication`
（21 条 headline claim：`C01`–`C19` + `C05b`/`C06b`），闭合 F6"gate 覆盖不足"中仍然成立的那部分。

---

## 六、控制面注记（保留历史、标注作废）

按"旧报告是溯源记录而非 claim 来源"的契约，历史条目**不删除**，只加作废横幅并给出 v2 真值：

- `.agent_state/EVIDENCE_LEDGER.md` T90（`+448,046` / `+48,494` 等）与 T91 主终点行：加 SUPERSEDED 横幅；
- `.agent_state/EVIDENCE_LEDGER.md` SA02 EXP-03 条目：加"full-grid trace hash / 无丢行"两项更正；
- `.agent_state/TASK_LEDGER.md` SA02：就地 AMENDED，并新增 F6-AUDIT / F6-FIX / F6-TEST 三条；
- `.agent_state/RUN_STATE.json`：`last_verified_task` 更新为 `F6-FIX`；
  T90、T96–T98 条目加更正说明；EXP-02 记录保持原样（未被 F6 波及）。

---

## 七、结论与残留边界

**已闭合（VERIFIED）：**

1. `experiments/E01/log.md` 的 v1 越界结论已作废并可被门禁拦截；
2. `EXP-Q2-003` / `EXP-01` 重复登记已退役；
3. 架构审计的参数量自相矛盾与 v1 量级硬编码已从**根因**消除；
4. 生成脚本重跑不再删除因果边界章节（并有断言保护）；
5. EXP-03 "full-grid 溯源"与"无丢行"两项不实表述已在四处来源纠正；
6. 门禁新增 §[7] 并通过注入回归证明；manifest 补齐 `verify_replication`。

**仍为 OUTSTANDING（不因本次修复而消失）：**

1. **EXP-03 全网格 packet-level 溯源**仍不存在。现有 trace 不含任何延迟包，
   归档哈希不可从工件复现。若论文依赖异步遥测稳健性，需重跑并落盘全网格 trace（或明确降级为无溯源诊断）；
2. **EXP-03 迟延端点的解释边界：** τ=6 时 `stale_fraction` 已达 99.79%，
   该曲线不应被描述为"部分刷新的固定总体响应"；
3. **EXP-03 未进入 `artifacts/joint_uncertainty_summary.json`**（该文件顶层键仅 `EXP-01`/`EXP-02`），
   故 registry 中 EXP-03 的 joint CI 缺少该汇总工件支撑；
4. **`verify_replication.py` 的 21 条 claim（`C01`–`C19` + `C05b`/`C06b`）未覆盖 EXP-01/02/03** —— 本次只把该脚本登记为必需命令，
   并未为其新增 EXP-01/02/03 断言；
5. 本次**未**修改 `docs/SCIENTIFIC_CONTRACT.md`，也**未**重新裁决任何实验结果；
   所有修复限于"阻止旧内容重新污染结论"。

> **范围声明：** 本报告不构成对 EXP-01/02/03 或当前主稿的科学有效性背书。
> 上游 `RA06` 的 `PASS_WITH_BLOCKERS` 与 falsifier 的 `FAIL FOR CURRENT SUBMISSION` 仍然有效。
