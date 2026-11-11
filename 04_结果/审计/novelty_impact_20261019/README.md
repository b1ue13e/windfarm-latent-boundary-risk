# 独立新颖性、科学意义与实际价值审计

先读 [最终判决](../FINAL_NOVELTY_AND_IMPACT_VERDICT.md)。本轮决定：**REPOSITION**；实际净收益 **UNPROVEN**。没有重定义冻结主张、修改原稿或启动新方向。

交付：

- [08 原子主张冻结](../08_claim_inventory.md)与`claim_freeze.json`
- [09 先行威胁](../09_prior_art_threats.md)
- [10 新颖性](../10_novelty_audit.md)
- [11 科学意义](../11_scientific_significance.md)
- [12 实际价值](../12_practical_impact.md)
- [13 七维比较矩阵](../13_prior_art_comparison.csv)：17篇、119维度行
- `reviewer_n/`、`reviewer_s/`、`reviewer_p/`：三席分别提交的意见、证据和读取层级

本轮三席均使用fresh fork（不继承会话历史），各自读取共同冻结材料；同一模型路由，提交前未互读本轮输出。角色分离不是错误统计独立；无正式期刊标准绑定或审稿人准确率校准。

原文PDF/提取文本/HTML及完整工具返回缓存保留在本机，Git只保留审计产物、元数据及来源/哈希清单；本轮未把外部原文缓存当作本项目贡献。复核内容阅读层级和访问失败见Reviewer N的SEARCH_LOG；元数据匹配不是全文审查。

本轮确定性只读计算：

```powershell
python research_audit/novelty_impact_20261019/reviewer_p/recompute_practical.py
python research_audit/novelty_impact_20261019/build_verdict.py
python research_audit/novelty_impact_20261019/verify_registry_metadata.py
```

第一项复核成本、计时、特征物化和最差日，不训练/推理/校准/重采样。第三项只访问公开Crossref，不等于读取论文内容。原科学/数字门禁实际通过，保存于Reviewer P目录；它们不认证新颖性、覆盖或净收益。所有后续任务仅为提案，不自动授权执行。
