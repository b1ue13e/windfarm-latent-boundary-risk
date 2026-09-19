# Claim-Evidence Matrix Standard Template

使用此模板将论文中的核心论点与实验证据精确绑定：

## 1. 核心贡献主张与证据映射 (Primary Contributions)

| Claim ID | 论文声称 (Paper Claim) | 证据类型 (Type) | 支撑源 (Evidence Source) | 统计置信度 (Metrics & Error Bar) | 状态 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Claim-1** | [例如：提出了一种基于切丛谱不稳定性的早期预警指标] | Theorem + Synthetic Dynamics | Theorem 3.1 & Figure 2(a-c) | Analytic proof on Kuramoto model | Verified |
| **Claim-2** | [例如：相较现有SOTA基线，在强噪声下提前预警时间提升 $\Delta t \ge 25\%$] | Empirical Benchmark (5 Seeds) | Table 1 & Figure 5 | $\Delta t = 42.5 \pm 3.1$ vs Baseline $31.2 \pm 4.5$ ($p=0.003$) | Verified |
| **Claim-3** | [例如：谱滤波模块去除了由于传感器局部丢包带来的伪相变信号] | Ablation Study | Table 2 (w/o Spectral Filter) | False positive rate drops from $18.4\%$ to $2.1\%$ | Verified |

---

## 2. 悬空断言审查与降级清单 (Floating & Overclaimed Items)

列出所有在手稿中出现但缺乏充分证据的陈述：

- **High-Risk Overclaim**:
  - *Raw Text*: "Our framework guarantees convergence on arbitrary non-Euclidean manifolds."
  - *Risk*: 证明仅适用于紧致黎曼流形（Compact Riemannian Manifolds）。
  - *Action*: 限制作用域为 "under compact Riemannian manifold assumptions with bounded sectional curvature".

- **Missing Experiment**:
  - *Raw Text*: "The computational overhead is negligible for million-node graphs."
  - *Risk*: 缺乏 $N=10^6$ 的真实运行耗时与显存曲线。
  - *Action*: 补充 O(E) 复杂度实测图或降级为 "empirically scalable up to $N=10^5$ with sub-second per-epoch latency".
