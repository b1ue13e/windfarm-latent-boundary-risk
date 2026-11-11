# 实验 E03：EXP-03: 整数步异步 packet 到达 envelope

**状态：INVALIDATED（2026-10-12）**

## 失效原因

F1 信息集违规已确认：`simulate_asynchronous_scada_stream()` 原先将 active-power 通道写为 `Patv`，但实际缓存字段为 `Patv_hist`。因此模型读取的主要 mediator 没有进入延迟模拟，baseline 与 challenger 的部署信息集不对称。旧运行结果及其 tau* 结论已撤回，仅保留为 provenance，不得用于科学推断。

证据：`scripts/run_exp03_async_benchmark.py:132-145,310,340-348,406-445`；`artifacts/cache_strictmask_trainweights/wtb_245d/metadata.json:5-16`；`docs/REVERSE_SCIENTIFIC_AUDIT_20261012.md:50-56`。

## 原始设计（已失效）

1. 冻结整数时间步 packet simulator、同到达排序、有限 causal buffer、迟包丢弃与共享 missing mask 协议。
2. 用同一 arrival trace 和 missing mask 驱动 Site-Local Wspd-Bins 与 challenger。
3. 按每个 horizon 计算 paired PSREI-vs-delay 曲线和 tau*，报告 5%/10%/15% operating target 敏感性。
4. 执行 packet-level unit tests、记录输入 trace SHA256，并将合成结果标记为 synthetic asynchronous envelope。

## 修复记录

模拟器现在按 canonical alias 解析 active power：优先 `Patv_hist`，兼容旧输入字段 `Patv`。新增回归测试：
- `test_async_simulator_delays_canonical_patv_hist_channel`
- `test_async_simulator_supports_legacy_patv_alias`

验证命令：`python -m pytest tests/test_exp03_async_arrival.py -q`，结果 `8 passed`。该修复只验证实现层行为，不恢复旧 benchmark 的科学有效性。

## 后续处置

任何重新运行必须先注册新的 Experiment ID，冻结固定评估人口、完整 trace/mask provenance、proxy label 的物理尺度处理和不确定性程序；不得覆盖 E03 或复用旧结果作为新证据。
