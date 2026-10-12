# 实验 E03：EXP-03: 整数步异步 packet 到达 envelope

- 假设：—
- 目的：在显式 event_time/arrival_time/sequence_id 协议下，比较 challenger 与 Site-Local Wspd-Bins 的 PSREI-vs-delay 曲线，并估计预注册临界点 tau*；同时报告 5%/10%/15% operating target 敏感性。
- 创建：2026-10-12T01:17:28.840Z

## 设计
1. 冻结整数时间步 packet simulator、同到达排序、有限 causal buffer、迟包丢弃与共享 missing mask 协议
2. 用同一 arrival trace 和 missing mask 驱动 Site-Local Wspd-Bins 与 challenger
3. 按每场站、每 horizon 计算 paired PSREI-vs-delay 曲线和 tau*，不把 10% 当作唯一 breakdown threshold
4. 执行 packet-level unit tests、记录输入 trace SHA256，并将合成结果标记为 synthetic asynchronous envelope

## 预期结果

- 若 Metis 连接和输入数据可用，输出每场站/每 horizon 的 paired PSREI-vs-delay 曲线、tau*、5/10/15% operating target 敏感性及 packet diagnostics。
- 结果方向不预设；负结果和 null 结果均为有效证据。

## 当前阻塞

- 2026-10-12：本机无 OpenSSH `ssh/scp` 命令，DSH `remote_host_add` 无法注册 Metis；当前没有可用的 DSH remote/server 条目。
- 因此尚未提交云端作业，也没有伪造 `psrei_vs_delay.csv` 或云端结果。

## 观察（Observation）
- 本地 packet protocol tests：5 passed。
- 既有 arrival-feed 回归：10 passed。
- Trace 已物化，SHA256=`247bd671d86b62d7ca19633e11af5aa79253c38b56558033861b0af2884bf944`。
