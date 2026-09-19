---
name: vibe-to-latex
description: 科研直觉/讨论笔记转顶会 LaTeX 与数学规范 Skill (NeurIPS/ICLR/ICML)。支持输入微信讨论记录、口语化灵感、实验日记与白板草图，自动提炼并生成严谨的 LaTeX 数学定义（Definition/Theorem）、形式化问题陈述（Problem Formulation）与统一符号体系。
---

# Vibe-to-LaTeX Skill (科研直觉与笔记转顶会数学化手稿)

当用户输入非正式的中文讨论、碎片化的科研直觉、实验随笔或导师沟通记录时，调用本 Skill 快速将 “Vibe / Intuition” 升级为标准的顶会级 LaTeX 表达。

---

## 核心转化管线 (Pipeline)

```mermaid
flowchart TD
    Raw["输入: 微信记录 / 讨论录音 / 碎片草稿"] --> Extract["1. 核心科学直觉提取 (Hypothesis & Mechanism)"]
    Extract --> Formalize["2. 形式化数学定义 (Manifold/Graph/Operator/Metric)"]
    Formalize --> Notation["3. 全局数学符号表统一 (Notation Consistency)"]
    Notation --> LaTeX["4. 结构化 LaTeX 模块输出 (Definition / Lemma / Algorithm)"]
```

---

## 转化规范与规则

### 1. 概念升华规范 (Abstraction Ladder)
- **口语表述**：“当系统快要崩的时候，几个特征值会挤在一起，算出来的曲率也会跳水。”
- **数学定义**：
  $$\text{Let } \mathcal{M} \text{ be a Riemannian manifold with Ricci curvature } \mathrm{Ric}(v, v). \text{ Near the bifurcation point } t^*, \text{ the spectral gap } \gamma(t) = \lambda_2(t) - \lambda_1(t) \to 0, \text{ inducing a curvature singularity } \lim_{t \to t^*} \kappa_R(t) = -\infty.$$
- **论文八股文**：
  *"We formalize this intuition by modeling the system trajectory on a Riemannian manifold, establishing that spectral gap collapse is topologically dual to a curvature singularity preceding critical transitions."*

### 2. 符号一致性矩阵 (Notation Standard)
- 标量：$s, c, t, \alpha, \lambda$
- 向量：$\mathbf{x}, \mathbf{y}, \mathbf{v} \in \mathbb{R}^d$（粗体小写）
- 矩阵/算子：$\mathbf{A}, \mathbf{W}, \mathbf{L} \in \mathbb{R}^{n \times n}$（粗体大写）
- 流形/集合/图：$\mathcal{M}, \mathcal{G} = (\mathcal{V}, \mathcal{E}), \mathcal{S}$（花体大写）
- 期望与概率：$\mathbb{E}[\cdot], \mathbb{P}(\cdot)$（黑板粗体）

---

## 常用工具与模板库
- 模板库：`templates/latex_math_templates.md`（涵盖 Problem Formulation, Definition, Theorem, Algorithm 伪代码）
- 核心提示词：`prompts/vibe_formalizer.md`

---

## 输出内容格式
1. **🔬 核心假设与形式化陈述 (Formal Hypothesis)**
2. **📐 全文数学符号对照表 (Notation Table)**
3. **📄 可直接编译的 LaTeX 代码块 (LaTeX Environment Ready: `definition`, `theorem`, `proof`)**
