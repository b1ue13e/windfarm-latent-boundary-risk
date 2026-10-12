# 实验日志 E03

- 创建：2026-10-12T01:17:28.845Z


## 2026-10-12T02:38:11.381Z

E03：在 Metis HPC（NVIDIA A100-PCIE-40GB GPU）上完成整数步异步 telemetry envelope 基准评测（5种子 201-205，2时域 h=1与h=6，延迟网格 tau in {0,1,2,3,4,5,6} 对应 0-60 分钟，B=2000 Block Bootstrap）。在严格因果缓冲区（只能读 arrival_time <= t，迟于 max_lateness 丢弃，无未来回填）与完全对称到达轨迹/缺失掩码（Trace SHA256=d1619efce7f02412d826e3811bfa2a2346e6bc1b1fcd2b02a9d10f163f0736ff）下：1) 在 h=1 时，临界点 tau*=1 步（10分钟），tau=0 时 Delta PSREI=-524.5k kWh，但在 tau>=1 时 95% CI 上界跨越零轴（tau=1: -400.1k kWh, CI [-990.8k, +97.6k], p=0.182），统计优势立即消失；2) 在核心主终点 h=6 时，临界点 tau*=0 步（0分钟），即使在理想无延迟 tau=0 下，Delta PSREI=-210.8k kWh (CI [-859.9k, +322.8k], p=0.293)，全延迟区间内置信区间均宽幅跨零，无显著决策增益；3) 标称 10% operating target（对应 q*=0.90）敏感性：h=1 下 Challenger 违约率在 7.42%-8.06% 之间平稳受控；h=6 下 Challenger 违约率为 10.82%-11.29%，而 Site-Local Wspd-Bins 严格控制在 8.65%-8.83%（完全满足 10% 标称目标）。确立合成异步信封边界，复杂表示对物理遥测滞后无缓冲能力。
