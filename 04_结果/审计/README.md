# 科研审计交付索引

现行执行边界为[正式停止决定](../docs/MAINLINE_STOP_DECISION_20261019.md)：项目保持STOP_ADDITIONAL_INVESTMENT，可执行队列为空。

Q1最新定位与证据边界见[研究决策记录](q1_research_decision_20261019/DECISION.md)及其[机器记录](q1_research_decision_20261019/decision.json)：已解决S1—S6、真正阻断A1—A2、最低证据E1—E4和可选增强B/C分开归档。该记录保留候选，不恢复研究，不将纸面闭合升级为科学结论；后续不得无新证据重复追加要求。

[E1证据路径补充](q1_research_decision_20261019/E1_EVIDENCE_PATHS.md)区分可能取得独立确认资格、独立性未证实的预声明二次分析与探索性分析。2026候选继续UNKNOWN，E1未闭合；没有窗口因归档取得资格，也不产生采数或实验队列。

[E2资产与冻结产物补充](q1_research_decision_20261019/E2_ASSET_REUSE.md)区分可复用资产、历史参考／需证明匹配的资产和缺失的F1—F5，固定最低实际历史包条件。E2未闭合，没有生成新模型、阈值或冻结包，不创建执行待办。

[E3实现与统计适用性补充](q1_research_decision_20261019/E3_IMPLEMENTATION_AND_APPLICABILITY.md)固定可复用实现、旧认证边界、必要证据V1—V4和可选增强。E3仍未闭合；本次归档不运行测试、门禁或实验，不创建执行待办。

既有审计主体可从 [PI 决策备忘录](FINAL_RESEARCH_STRATEGY.md)按需要追溯；其中历史建议不构成现行执行队列：

1. [项目资产与覆盖](01_project_inventory.md)
2. [7,525行分层实验账本](02_experiment_ledger.csv)；行数不等于独立实验次数
3. [有效性与复现问题](03_validity_and_reproducibility.md)
4. [候选发现排序](04_discovery_ranking.md)
5. [三个科学问题与唯一推荐](05_scientific_problem_candidates.md)
6. [最小决定性补证据](06_decisive_experiments.md)；均为提案，未启动
7. [三角色审查与综合裁决](07_reviewer_assessment.md)
8. [13篇核验文献矩阵](literature_matrix.csv)
9. [核心图PNG](figures/core_evidence.png)、[矢量PDF](figures/core_evidence.pdf)、[可编辑SVG](figures/core_evidence.svg)

`inventory_summary.json`、`all_accessible_files.csv.gz`和`research_assets.csv`是元数据清点，不代表逐文件内容审查。`working/`保留三角色的原始报告、复算脚本、读文件哈希与分工范围。`validation/`保存实际门禁、测试和受保护输入身份。`derived/`是原日块的本轮月度描述性重汇总，无新置信区间。

可复核命令（均从仓库根运行，输出仅在本目录）：

```powershell
python research_audit/working/rigor/recompute.py
python research_audit/working/rigor/ledger_points.py
python research_audit/working/discovery/reconstruct_evidence.py
python research_audit/recompute_primary_slices.py
python research_audit/build_ledger.py
python research_audit/plot_evidence.py
```

现有归档gate使用exclusive-create保存结果；`run_validation.py`用于本轮首次执行，其既有输出保留，不应为重跑删除原审计记录。若需再运行，应在新输出目录记录，不能覆盖既有结果。

本轮只重汇总存档块/CSV、运行低成本软件检查；未新训练、推理、校准、对原科学数据重采样或访问远端；合成小数组单元测试与新科学实验分开。正式论文/原数据/旧结果/科学契约/门槛均未修改。
