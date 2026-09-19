# 9-Page Top-Tier Conference Blueprint Template (NeurIPS / ICLR / ICML)

以下是经过无数 Oral / Spotlight 验证的标准 9 页纸页码预算与章节结构：

```
[Page 1] 
  ├── Title & Abstract (高信息密度，明确背景、痛点、核心洞察、定量增益)
  ├── 1. Introduction (Part 1: 现实背景与核心矛盾)
  └── [Teaser Figure / Figure 1] (整篇论文的 Concept / Mechanism 概览图)

[Page 2]
  ├── 1. Introduction (Part 2: 现有工作的根本局限 & 我们的核心机理)
  ├── 1.1 Summary of Contributions (严格 3 个递进 Bullets)
  └── 2. Related Work (分类对比，必须突出与 SOTA 的本质范式区别)

[Page 3]
  ├── 3. Problem Formulation & Preliminaries (形式化符号体系、流形/算子定义)
  └── 3.1 Motivation & Geometric Intuition (为什么现有指标失效，从几何角度展示直觉)

[Page 4]
  ├── 4. Methodology (核心算法设计)
  ├── 4.1 Theoretical Formulation (定义、算子构建与目标函数)
  └── [Figure 2: Method Architecture / Pipeline Flowchart]

[Page 5]
  ├── 4.2 Theoretical Analysis (定理证明骨架、误差界、复杂度分析)
  └── 5. Experiments Setup (Datasets, Baselines, Evaluation Protocol)

[Page 6]
  ├── 5.1 Main Benchmark Results (核心性能大表 Table 1，含 Error Bar & 显著性)
  └── [Figure 3: Synthetic vs Real Benchmark Visualizations]

[Page 7]
  ├── 5.2 Robustness & Out-of-Distribution Analysis (抗噪、分布偏移测试)
  └── 5.3 In-depth Ablation Studies (模块消融、超参数敏感性)

[Page 8]
  ├── 5.4 Mechanistic Case Study / Interpretability (为什么有效：谱演化/表征轨迹可视化)
  └── 5.5 Computational Efficiency & Scalability (GPU Hours / Scaling Curves)

[Page 9]
  ├── 6. Discussion, Limitations & Broader Impacts (坦承边界条件与安全/社会影响)
  └── 7. Conclusion (总结与未来展望)

[Pages 10+]
  └── References & Appendix (NeurIPS/ICLR 参考文献与证明、超参、补充实验)
```
