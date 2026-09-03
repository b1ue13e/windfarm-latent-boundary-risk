# 实验 A 结果：公平退化下 Gate vs Rule（Early-Window Recall）

> 日期：2026-09-03 ｜ 脚本：`scripts/fair_degradation_replay.py`
> Checkpoint：train-only class-weight rerun（`artifacts/trainweight_class_weight_rerun_20260702/wtb_bal_align_force_seed{201..205}`，本地 best_model.pt 口径同远程）
> 缓存：`artifacts/cache_strictmask_trainweights/wtb_245d`（train-only 权重口径）
> 运行：grokking GPU0，全量 5 seeds ~10 分钟

## 1. 实验语义

旧的 label-degradation audit 只退化 rule/classifier 的输入流，gate 保持 clean——审稿人可攻击为"场景构造恒等式"。本实验**公平退化**：延迟/噪声同时作用于 gate 的 anchor 输入与 rule 的读数，早期 pitch 窗口真值仍由 clean regime 标签定义。

- **Delay d**：issue-time 确认流（Wspd/Pab_mean 读数）迟到 d 步，gate anchor 与 rule 均使用 t-d 读数；历史窗口保留归档流（对应"QC 确认流延迟、归档历史可用"的部署语义）。
- **Noise (σ_w, σ_p)**：Wspd/Pab_mean 加物理单位高斯噪声（0.5/1.0 与 1.0/2.0），映射到标准化空间作用于 encoder 特征与 gate anchor；rule 在原始物理量上加同分布噪声后重算阈值。

## 2. 主结果（5 seeds mean±sd）

| 条件 | gate recall | rule recall | gain（gate−rule） |
| :--- | :--- | :--- | :--- |
| clean | 0.9705 ± 0.0299 | 1.000 ± 0.000 | −0.029 ± 0.030 |
| delay 1 | 0.9622 ± 0.0306 | 0.6554 ± 0.000 | **+0.307 ± 0.031** |
| delay 3 | 0.9430 ± 0.0361 | 0.3811 ± 0.000 | **+0.562 ± 0.036** |
| delay 6 | **0.9327 ± 0.0429** | **0.1959 ± 0.000** | **+0.737 ± 0.043** |
| noise (0.5, 1.0) | 0.9635 ± 0.0375 | 0.8114 ± 0.0157 | **+0.152 ± 0.037** |
| noise (1.0, 2.0) | 0.9505 ± 0.0363 | 0.6800 ± 0.0189 | **+0.271 ± 0.050** |

## 3. 解读

1. **场景语义修复**：gate 的鲁棒性不再来自"gate 没被退化"，而是来自后果通道组合签名——在 6 步延迟下 gate recall 仅从 0.971 降至 0.933（−3.9%），rule 从 1.000 崩至 0.196。
2. **噪声鲁棒**：最强噪声下 gate 0.951 vs rule 0.680，gain +0.271 全部种子同号。
3. **诚实边界**：clean 条件下 rule（1.000）优于 gate（0.971）——与"clean-anchor 分类器更强"的既有叙事一致，鲁棒性优势只在退化场景出现。
4. 与旧表方向一致（旧 0.960 vs 0.196 → 新 0.933 vs 0.196 @ delay6），但新表是公平构造，可直接作为 headline 证据。

## 4. 论文措辞

- 可写："under fair degradation, the gate retains 0.933 recall at six-step delay while the rule falls to 0.196；the signature-based router degrades 3.9% where the single-threshold rule degrades 80.4%."
- 必须同时披露 clean 时 gate 略逊（0.971 vs 1.000）与 precision 面（gate precision ~0.49-0.76 低于 rule clean 0.879；delay6 时 gate 0.65 高于 rule 0.34——precision 在退化下也反转）。
- availability 场景（旧 Table II）保留原语义：gate 测试时不消费确认标签流，属架构性质而非输入退化，单独陈述。

## 5. 数据溯源

- 脚本：`scripts/fair_degradation_replay.py`（含预注册 policy JSON）
- 原始 CSV：`artifacts/fair_degradation_replay_20260903/fair_degradation_raw.csv`（本地 + grokking 同名路径）
- 汇总：`fair_degradation_summary.csv`、配置：`fair_degradation_config.json`
