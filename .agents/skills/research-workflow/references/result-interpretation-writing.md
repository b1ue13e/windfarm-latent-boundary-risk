# Result Interpretation & Scientific Writing (结果解释与论文写作)

## 1. 结果分析阶梯
1. **可信度校验 (Credibility First)**：
   - 检查各种子方差是否可控。
   - 确认测试集指标计算未受到标签泄漏或方向错误影响。
2. **效应量化 (Effect Analysis)**：
   - 不仅报告绝对/相对增益，更要聚焦 Failure Condition 下的改善斜率。
3. **机制归因 (Mechanistic Attribution)**：
   - 增益是否符合最初的 Cause Sentence？如果不符合，诚实调整机制解释。

## 2. 论文写作四段式规范 (Introduction)
- **Para 1 (Context)**：宏观背景与任务重要性（2-3 句直奔主题）。
- **Para 2 (State of the Art)**：现有代表性方案与其技术路径。
- **Para 3 (The Core Failure & Gap)**：在特定条件下不可避免的失效，现有方案无法逾越的根源（紧扣 Failure Sentence）。
- **Para 4 (Proposed Solution & Contributions)**：本文提出的机制、实验验证成果与 3 点清晰贡献。
