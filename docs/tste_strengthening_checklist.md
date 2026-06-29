# IEEE TSTE 投稿强化清单（留刊补强路径）

最后更新：2026-06-29。目标期刊：IEEE Transactions on Sustainable Energy。
策略：保留当前 TSTE 主线，先补强化解三大高风险，再投稿。

本清单只规划，不改代码。每项标注：风险对应 / 改动文件 / 需补的表图 / 需跑的命令 /
页面预算影响 / 验收标准。优先级 P0>P1>P2。当前正文已顶满 10 页，任何新增都必须先腾版面，
所以"腾版面"是所有内容类改动的前置条件。

## ⚠️ 源文件真相（动手前必读）

`paper_tste_ieee.md` 与 `paper_tste_supplementary.md` 都是**生成产物**，由
`scripts/prepare_tste_submission.ps1` 在打包时重新生成；直接编辑它们会被打包步骤静默覆盖。
本清单下文给出的 `paper_tste_ieee.md` 行号仅用于**定位**，实际编辑必须落到下列源头：

| 想改的内容 | 真正的源文件 |
|---|---|
| 正文 Introduction→References 全部正文与表图 | `paper_draft.md`（transform 抽取 `# Introduction`→`# Appendix A` 之间） |
| 标题 / 摘要 / 关键词 / YAML 头 | `scripts/transform_ieee.py`（硬编码字符串） |
| 补充材料正文与表 A1–A12 | `scripts/make_supplementary.py`（+ `paper_draft.md` 的 Appendix 段） |
| 补充材料 YAML（已修为 IEEE.csl） | `scripts/make_supplementary.py` |

已验证：`python scripts/transform_ieee.py` 重生成的 `paper_tste_ieee.md` 与提交版**逐字节一致**，
故 `paper_draft.md` 是正文唯一真相，无 drift。注意 `build_paper_ieee.ps1` **不**调用 transform，
只有 `prepare_tste_submission.ps1` 会重生成——所以"只构建预览"可改 .md，但"正式打包"前必须把改动
同步回源文件，否则丢失。

---

## 0. 页面预算（前置，P0）

正文实测 10 页，IEEE PES 初投上限即 10 页，回修空间为零。先腾出约 0.5–0.8 栏：

- [x] **合并 anchor-stress 的两张表**（commit d0327c98）：删除冗余的"Training-level
  anchor-stress guard for claim control"文字状态表，把 leakage-guard/20-run provenance
  并入上方段落；保留数值表 `tab:anchor-stress`。
- [x] **reserve vignette 两张表择一进正文**（commit d0327c98）：删除 4 行
  `Boundary-window reserve outcomes` 表（被相邻 5 行 validation-frozen quantile 表完整包含），
  保留 5 行全景表并把 caption 改为覆盖两者。
- [x] 验收：重建后 `build_paper_ieee.ps1` 干净，main 仍 10 页、supp 4 页、无阻断警告、
  number-consistency `complete_tste_number_consistency`；末页仅 589 词（vs page9 887），
  腾出约 0.5 栏 slack。所有被删数字均在保留表中存活。

---

## 1. 高风险①——"精度更差"的头条（P0，定位类，几乎不需新实验）

目标：不改实验结论，但把叙事从"我们更差但可解释"重排为"我们补上了 SOTA 预测器缺失的
issue-time 运营状态层"，降低顶刊评审的逆风。

- [ ] **摘要首句重构**（`paper_tste_ieee.md` 35–37 行 abstract）：把 RMSE 让步从首屏移到
  contribution 第三点；首屏用"degraded-label 下仍可用的可审计控制边界诊断"作为主价值。
- [ ] **Introduction 末段 contribution 三点**（51 行）：把第三点"prices and bounds the
  intervention"的措辞，从"costs 11.79 RMSE"改为"附带一个被显式量化、被守卫表 A6 约束的
  精度代价"，强调代价是**被审计的**而非被掩盖的。
- [ ] **新增一句 reviewer-facing 定位句**到 Introduction 或 Results 开头：明确"本文不与
  forecasting leaderboard 竞争，而是为已部署的低 RMSE 预测器补一层可审计运营状态信号"。
- 风险对应：评审风险①（卖点是更差精度）。
- 页面影响：净零（重排为主）。
- 验收：abstract 与 cover letter（`cover_letter_tste.md` 第 9 行）数字与措辞一致；
  `verify_tste_number_consistency.py` 通过。

---

## 2. 高风险②——标签退化对比的不对称（P0，证据已存在，需并列呈现）

目标：主动把"gate 读实时 anchor、阈值规则被人为退化"的不对称摆上台面并量化，堵死
"稻草人/不公平对比"质疑。**关键利好：对称退化数据已存在**，无需新跑。

- [ ] **把 anchor 同步退化曲线与早警表并列**：正文早警表 `tab:early-warning`（333–356 行，
  退化的是标签）旁边，引用已有的 anchor-stress 表 `tab:anchor-stress`（358–377 行，退化的是
  gate 自己的 anchor 通道）。两表已都在正文，但目前分述。补一段桥接文字，显式说明：
  "当我们对称地退化 gate 自己的输入（去 Patv/去 Pab/滞后），五seed 均值仍 ≥0.65 NMI，
  因此早警优势来自**可得性差距**而非信息不对称。"（正文 329 行已有雏形，强化为独立小段 + 明确对照）。
- [ ] **可选补图**：把"标签退化 vs anchor 退化"两条 recall/NMI 曲线画到同一张图，
  作为对称性的视觉证据（数据来自 `artifacts/anchor_stress_*` 与
  `artifacts/anchor_stress_early_warning_wtb_strictmask`）。若版面紧张放补充材料。
- [ ] **如尚未跑满**：按 `docs/ieee_tste_transfer_execution.md` 24–39 行的三步协议确认
  `anchor-stress-cache / anchor-stress-train / anchor-stress-guard` 与
  `anchor-stress-early-warning` 全部 complete，决策标记应为
  `complete_anchor_stress_supports_label_degradation_value`。
- 风险对应：评审风险②（对比不对称，最难 rebuttal）。
- 页面影响：+0.2 栏文字（靠第 0 节腾出的版面吸收）。
- 验收：正文能用一句话回答"为什么这不是不公平对比"，且该句有表 A8/anchor-stress 数字支撑。

---

## 3. 高风险③——单数据集 + 外部迁移失败（P1，需少量重组/补跑）

目标：让主张不再只靠 WTB 单基准，把"外部失败"转成"按协议可恢复"。二选一或都做：

- [ ] **方案 3A（轻，推荐先做）：ERA5 从补充提为正文 positive control。**
  当前 ERA5 主结果在补充，正文只剩 observability 对照一句（113–115 行）。把 ERA5 的
  对齐改善结果（routing correction 在 marker 可见时提升 alignment）作为"第二数据集正对照"
  拉回正文一小段 + 一行小表。数据已存在于补充与 `artifacts/paper_assets`，无需新跑。
  这把论证从"单数据集"升级为"WTB(困难)+ERA5(可见)两端对照"。
- [ ] **方案 3B（重，回报更高）：外部迁移"局部重校准后通过"小实验。**
  Table A8 已显示重校准 NMI 0.1324→0.1491（仍不达标）。把它从"失败"升级为"按部署协议
  局部重估后达到 held-out 门槛"需要一次小窗口校准实验：在 Kelmarsh/Penmanshiel 上做
  validation-only 边界重估 + held-out routing check，目标至少一个迁移方向越过 0.50 NMI 门槛。
  相关脚手架见 `scripts/run_external_wind_full_evidence.ps1` 与
  `artifacts/external_wind_*` / `artifacts/spatial_holdout_*`。
  注意：若仍不过门槛，**不要**改写成迁移成功，维持"部署门槛"叙事即可（保持诚实设限）。
- 风险对应：评审风险④（证据基本单数据集；外部迁移失败）。
- 页面影响：方案 3A 约 +0.4 栏（需第 0 节版面）；方案 3B 主要落补充材料，正文加一句。
- 验收：正文出现 ≥2 个数据集的正向证据；外部部分要么明确"协议内可恢复"，要么明确
  "部署门槛"，二者不可含糊。

---

## 4. 高风险⑤/⑥——新颖性与 reserve 价值（P2，措辞强化）

- [ ] **把新颖性从"架构"明确改述为"可审计性框架 + SCADA 可观测性约束"**：在 Related Work
  末段（59 行）补一句和 physics-guided MoE / TimeMoE 的**差异点**：本文约束的是 routing
  decision 本身使其可对照声明边界，而非用预测损失自发分工。
- [ ] **reserve vignette 增补 cost-ratio 敏感性的一句话区间**：正文已有 ρ∈{2,5,10,20,50}
  扫描提及（263 行），把"useful window 仅在 ρ=5–10"这一边界从补充提一句进正文，
  避免评审误读为普适价值。
- 页面影响：净零。

---

## 5. 工程小瑕疵（P0，零科学风险，可立即做）

- [ ] **统一补充材料 CSL**：`paper_tste_supplementary.md` 第 8 行 `csl: elsevier-numbered.csl`
  → 改为 `IEEE.csl`，与主稿一致（Applied Energy 残留）。
- [ ] **构建链全量验证**：依次跑
  `scripts/build_paper_ieee.ps1` → `scripts/prepare_tste_submission.ps1`，确认
  number-consistency（`complete_tste_number_consistency`）、evidence-freeze
  （`complete_ready_for_evidence_freeze`）、页数 ≤10、LaTeX 警告扫描全绿。
- [ ] **人工复核数字一致性**：abstract / cover letter / 正文三处的
  236.13 / 224.34 / 0.960 / 0.196 / 0.508 / 11.79 / 84.58M 等核心数字逐一对齐
  （脚本已校，人工再过一遍）。

---

## 执行顺序建议

1. 第 5 节工程项（半天，零风险，先把链路跑绿作为基线）。
2. 第 0 节腾版面（半天）。
3. 第 1 节定位重排 + 第 2 节对称性并列（1–2 天，化解 Top-2 录用障碍）。
4. 第 3 节方案 3A（ERA5 回正文，1–2 天）。
5. 视时间决定是否做第 3 节方案 3B（外部重校准实验，3–10 天，回报最高）。
6. 第 4 节措辞强化（半天，收尾）。
7. 全量重建 + 打包 + 复核，提交。

每完成一组改动按 `AGENTS.md` 要求 `git commit` 一次。
