# Gap Identification & Refinement Guide (研究缺口判定指南)

## 1. 核心定义
一个真正合格的 Research Gap，必须是一个**机制性的、可检验的失效**，而不是文献数量的多少。

### 严禁使用的伪 Gap (False Gaps)
- “目前研究较少 / Few studies have focused on...”
- “尚未得到充分关注 / Has received limited attention...”
- “很少有人将 A 用于 B / Rarely combined A with B...”
- “我们首次尝试 / To our best knowledge, we are the first to...”

## 2. 三大核心 Gap 类型

### A. 方法空白 (Methodological Gap) - 优先级最高
- **定义**：主流方法在特定条件下明确失效（Failure condition），现有改进未能触及根本机理。
- **检验标准**：你能否用实验或推导精确重现该失效？你能否指出是哪个数学假设或结构限制导致了该失效？

### B. 对象/场景空白 (Contextual/Empirical Gap)
- **定义**：现有方法在通用场景成立，但在新场景/数据下失效。
- **必须回答**：“为什么新场景改变了问题的根本假设或数据生成机制？”而非仅仅“换了个数据集跑跑”。

### C. 矛盾空白 (Contradictory Evidence Gap)
- **定义**：高质量文献在相近条件下得出冲突结论。
- **切入点**：识别隐藏的混淆变量（Confounder）或边界条件（Boundary Condition）。

## 3. 三句话强制检验法 (Three-Sentence Anchor)
1. **Failure Sentence**：在 [明确环境/数据条件] 下，现有主流方法 [Baseline] 在处理 [具体任务] 时会出现 [具体失效现象]。
2. **Cause Sentence**：该失败的根本原因在于其依赖的 [核心假设/计算机制]，导致其无法应对 [关键扰动/分布偏移/长尾]。
3. **Plan Sentence**：本研究提出 [新机制/新表征]，通过重构 [目标函数/交互结构]，在保证 [基准性能] 的前提下消除上述失效。
