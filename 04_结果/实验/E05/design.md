# 实验 E05：E05: E04 selector stability/frequency diagnostic

- 假设：—
- 目的：在不改变 E04 阈值、候选集、复杂度序、总体与联合 seed/block 重采样规则的前提下，估计风险约束选择器在五个冻结政策数组上的可行频率、首个可行政策频率和 NO FEASIBLE 频率，明确选择稳定性是否可由当前数组支持。
- 创建：2026-10-18T02:44:14.698Z

## 设计
1. 冻结并记录 E04 五个 seed_full_policy_day_blocks.npz 输入文件 SHA-256 及 PREREGISTRATION_E04_V2.json 哈希。
2. 用独立稳定性随机种子 20261018 进行 10,000 次 joint seed-by-35-day-block resampling。
3. 每次按 B<C<D<D10 评估 cost delta、violation delta、absolute violation 三个约束，记录各政策可行频率、首个可行政策频率与 NO FEASIBLE 频率。
4. 保留 E04 primary selector 的 NO FEASIBLE 结果，不使用稳定性频率修改主选择结论；对输入未绑定原始执行 receipt 的限制做条件性披露。

## 预期结果

## 观察（Observation）
