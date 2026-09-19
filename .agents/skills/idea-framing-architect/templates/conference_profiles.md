# Top-Tier Conference Specialization & Profile Matrix

针对同一套科研成果（如：谱几何预警 / 鲁棒控制 / Target Phenomenon 相变），在不同顶级会议上必须采用完全不同的 **Story Framing** 与审稿人侧重策略：

---

## 1. NeurIPS (Neural Information Processing Systems)
- **审稿人核心偏好**：
  - 关注机理洞察、过参数化表征动力学、相变现象（Emergence / Target Phenomenon / Phase Transitions）以及理论泛化界。
- **Story Framing 模板**：
  > *"We uncover a foundational spectral phase transition governing generalization and stability in overparameterized dynamical networks, establishing analytic bounds on lead time under differential operator curvature collapse."*
- **必须具备的要素**：
  - 定理或严密的命题推导（Theorem / Proposition / Proof Sketches）。
  - 覆盖广泛的基础合成动力学基准（Kuramoto, Lorenz, Standard PDEs）与大规模表征验证。
  - 完整的 NeurIPS Checklist 答复。

---

## 2. ICLR (International Conference on Learning Representations)
- **审稿人核心偏好**：
  - 极度看重表征流形（Representation Geometry）、归纳偏置（Inductive Bias）与架构机理解释。
- **Story Framing 模板**：
  > *"We introduce a geometrically grounded representation learning paradigm that monitors the tangent bundle spectral spectrum to preemptively capture representational collapse before macroscopic degradation."*
- **必须具备的要素**：
  - 谱演化、流形压缩或曲率变化的深度可视化图表（Figure 1 & Figure 4）。
  - 深入剖析自注意力/卷积/图拉普拉斯在特征空间的表征演变轨迹。

---

## 3. ICML (International Conference on Machine Learning)
- **审稿人核心偏好**：
  - 算法收敛界（Convergence Rates）、极小化极大最优性（Minimax Optimality）、严格统计泛函分析。
- **Story Framing 模板**：
  > *"We formulate the early warning task as an online spectral filtering problem on dynamic Riemannian manifolds, proving an $\mathcal{O}(1/\sqrt{T})$ regret bound and minimax optimal sample complexity."*
- **必须具备的要素**：
  - 形式化优化问题定义、闭式解或收敛速度渐近分析（Big-$\mathcal{O}$ / $\Omega$ 证明）。
  - 严格控制计算复杂度与 Wall-clock time 随样本量 $N$ 的增长曲线。

---

## 4. KDD (Knowledge Discovery and Data Mining - Applied / Research Track)
- **审稿人核心偏好**：
  - 真实产业痛点（SCADA 工业传感器、金融交易流、大型电网）、抗噪鲁棒性、吞吐量（Throughput）与毫秒级延迟（Latency）。
- **Story Framing 模板**：
  > *"To address critical failure pre-warning in mission-critical SCADA sensor streams under severe non-stationary noise, we deploy an ultra-lightweight online spectral indicator delivering 48.2ms per-window inference with certifiable robustness against 20% sensor dropouts."*
- **必须具备的要素**：
  - 端到端 Wall-clock 延迟与内存占用大表（Latency vs Accuracy Pareto Frontier）。
  - 真实工业/金融数据集（如真实风机 SCADA、高频交易数据）与抗丢包/漂移测试。

