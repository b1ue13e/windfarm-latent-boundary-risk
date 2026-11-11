# 实验日志 E06

- 创建：2026-10-18T03:17:04.240Z

## 2026-10-18 E06 execution and verification

- Metis J04 performed the actual E04 replay using the frozen remote cache, residuals, and five dense-classifier checkpoints. The replay command exited 0 and produced all five `seed*_full_policy_day_blocks.npz` arrays with Full population 385,205 and the expected five-seed/35-day-block structure.
- J04's wrapper post-check failed after replay because it compared pre/post input records with different path representations. The failure is preserved; J04 is not counted as a successful job.
- Metis J05 verified the completed replay receipt, repackaged the bundle, ran the receipt-bound selector, and exited 0. It generated `e04_execution_plan.json`, `e04_output_manifest.json`, `e04_execution_receipt.json`, `e04_selection.json`, and `e04_selector_output_manifest.json`.
- Remote receipt status is `EXECUTED`, exit code 0. Selector status remains `NO FEASIBLE POLICY`; the four policy UCB values match the prior E04 values exactly. Remote input attestation reports all 23 inputs unchanged after replay.
- J07 pulled exact residual/checkpoint inputs for local verification and wrote a complete hash manifest, but emitted a post-write shell syntax error; it is retained as transfer evidence only, not a clean execution result.
- Local verifier `experiments/E06/code/verify_e06_bundle.py` returned `PASS_BUNDLE_LOCAL_INPUTS`: receipt/plan/manifest/output/selector provenance hashes all match; all 23 remote input records match exact pulled equivalents. Local replay regression remained 19 passed.
- Artifact: `e06-metis-receipt-bound-replay-20261018 v1`. This closes provenance/file-lineage verification for the replay bundle only; it does not promote the E04 scientific claim or close independent falsification review.


## 2026-10-18T03:54:24.547Z

Metis J04 执行了冻结的五 seed E04 policy replay，命令 exit 0，且远程 post-replay 输入 attestation 显示 23/23 输入 hash 未变化；J04 包装器仅因路径表示比较错误在 post-check 阶段失败。J05 对已完成 replay 进行 receipt-bound repackage 并成功运行 selector：receipt status=EXECUTED、output manifest 含 5 个 seed policy arrays、selector 返回 NO FEASIBLE POLICY；四个 policy 的 primary UCB 数值与既有 E04 结果逐项相同。拉回本地后，plan/manifest/receipt/五个输出数组/selector provenance hash 全部通过，23/23 个远程输入 hash 与精确拉回副本一致。该 finding 只闭合 provenance/file-lineage，不升级 E04 科学结论；J07 exact-input helper 在写完 manifest 后产生 shell syntax error，保留为工具层 blocker。
