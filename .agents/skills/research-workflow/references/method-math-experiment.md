# Method, Math & Experiment Mapping (方法、数学与实验映射)

## 1. 三层方法阐述法
### A. 直觉层 (Intuitive Layer)
- 它试图改变系统的哪一个关键物理量/表征分布？
- 为什么改变这个量能够在因果层面上缓解 failure？
- 与最接近的基线（SOTA Baseline）相比，首要差异点是什么？

### B. 数学层 (Mathematical Formulation)
- 严谨定义变量集合与张量维度（如 $X \in \mathbb{R}^{B \times T \times D}$）。
- 给出优化目标函数（Objective / Loss Function）与参数更新式。
- 标明公式中每个正则项、权重项所对应的具体物理/机制意义。
- 分析边界与退化情况（例如 $\lambda \to 0$ 或 $T \to \infty$ 时算法退化为何物）。

### C. 实现层 (Implementation Layer)
- 输入张量格式与前向传播数据流。
- 梯度计算与数值稳定性控制（如 log-sum-exp, epsilon clip, 梯度裁剪）。
- 时间/空间复杂度分析及瓶颈诊断。

## 2. 数学-代码-消融三维对齐表
| 数学组件 | 损失项/更新算子 | 代码对应函数/模块 | 消融变体 (Ablation Variant) | 预期消融现象 |
|---|---|---|---|---|
| 动态平滑项 | $\mathcal{L}_{\text{smooth}}$ | `loss.py:compute_smooth_loss()` | `w/o smooth` | 剧烈震荡，收敛不稳定 |
| 跨模态注意力 | $\text{Attn}(Q, K, V)$ | `models.py:CrossModalLayer` | `replace with Concat+MLP` | 表达能力下降，跨域对齐失效 |
