# 实验 E06：E04 provenance-bound Metis replay

- 假设：—
- 目的：在不改变 E04 预注册阈值、候选集、bootstrap 或输入信息集的前提下，在 Metis 重新执行有效 E04 policy replay，并生成 plan、manifest、execution receipt 与带 provenance hashes 的 selector result，随后完成本地完整 hash 校验。
- 创建：2026-10-18T03:17:04.238Z

## 设计
1. 核对 Metis 源目录、冻结 preregistration、缓存/残差和五个 seed 输入路径及 hash
2. 在远程 bundle 内生成不可变 execution plan，执行有效 replay，生成 output manifest 与 EXECUTED receipt
3. 使用 receipt-bound selector 计算 E04 primary/stability 输出并记录 receipt/plan/manifest/selector hash
4. 拉回全部小型证据文件，在本地验证 receipt、manifest、输出、selector provenance 与输入 hash 一致性

## 预期结果

## 观察（Observation）

- Metis J04 完成实际 replay 计算并生成五个 seed 数组；包装器的 post-check 因路径表示比较错误失败，未将 J04 计为成功作业。
- Metis J05 对 J04 已完成的 replay 进行 receipt-bound repackage，并成功运行 selector。远程 receipt 为 `EXECUTED`、exit code 0；selector 返回 `NO FEASIBLE POLICY`。
- 拉回本地后，receipt、plan、manifest、五个输出数组和 selector provenance hash 全部一致；23/23 个远程输入 hash 与精确拉回副本一致。
- 该实验只完成输出 provenance/file-lineage closure，不改变 E04 科学结论，也不替代独立 falsification review。
