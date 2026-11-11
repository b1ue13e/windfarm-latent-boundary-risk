# 结果与证据

先从当前论文需要的三组结果进入：

| 论文内容 | 结果包 |
| --- | --- |
| SDWPF 当前测量对比 | [praw_supplement_v3_execution_20261021](分析/praw_supplement_v3_execution_20261021/REPORT.md) |
| Hill of Towie 2025 年确认 | [independent_confirmation_execution_20261019](分析/independent_confirmation_execution_20261019/REPORT.md) |
| Hill of Towie 2026 年 1—4 月验证 | [mainline_supplement_20261026](实验/mainline_supplement_20261026/REPORT_CN.md) |

其余材料按用途平放，不再按尝试或阶段套目录：

- `实验/实验名`：协议、原执行源码快照、结果、日志和运行凭证。
- `分析/分析名`：派生汇总、既存结果复核与分析记录。
- `产物/名称`：历史实验的表、模型权重和相关输出。
- `审计/审计名`：独立审查、来源和主张边界记录。
- `历史证据`、`历史工作记录`：上一轮清理保留的旧数据、执行/写作审计和备份。
- `项目记录`：科学契约、状态、实验总账和目录迁移记录。
- `复现运行`：本次及以后使用根目录入口生成的新输出；不与冻结结果混放。
- `运行缓存`：可重建工程缓存。

负结果、失败和未核实状态按原内容保留。既有日志、JSON/CSV、manifest 和收据中的旧路径不改写；用 `python project.py locate 旧路径` 查询现存位置。

当前可运行的源码见 [代码目录](../02_代码/README.md)，现行论文见 [TSTE](../01_当前论文/TSTE/README.md)；历史源码快照仅承担原执行来源证明。
