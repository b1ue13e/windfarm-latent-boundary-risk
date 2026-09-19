# Literature Matrix Specification (文献矩阵操作规范)

## 1. 字段说明
- `paper`: 论文标题或简写 (如 Vaswani et al., 2017)
- `year`: 发表年份
- `task`: 研究任务
- `data`: 验证数据集
- `method`: 核心方法机制
- `assumption`: 算法成立的关键假设
- `main_result`: 核心定量指标或理论结论
- `failure`: 论文明确承认或实验暴露的局限性/失效条件
- `gap_role`: 论文角色 (`奠基类` / `主流类` / `失效类` / `邻域类`)
- `similarity_to_us`: 与本研究的相似度 (`High` / `Medium` / `Low`)
- `reusable_component`: 可复用的代码/基准/数据流水线
- `evidence_strength`: 证据力度 (`Strong` / `Moderate` / `Weak`)

## 2. 三轮检索策略
1. **问题词轮**：聚焦任务与失效指标（Task + Failure Condition + Metric）。
2. **方法词轮**：主流方法 + 限制词（Method + Limitation / Vulnerability / Failure）。
3. **反证词轮**：逆向检索已有的类似解法（同义词、 cross-domain 类似机制），防止重复造轮子。
