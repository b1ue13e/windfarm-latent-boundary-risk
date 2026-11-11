# 代码

从仓库根目录使用统一入口 `python project.py`，无需手动设置 Python 导入路径。

| 位置 | 用途 |
| --- | --- |
| `工程/windfarm_moe` | 模型、数据处理、备用决策、统计与核验实现 |
| `工程/scripts` | 实验和分析入口；用 `python project.py run-script scripts/脚本名.py 参数` 调用 |
| `工程/tests` | 对应测试；根目录 `pytest.ini` 已指向此处 |
| `工程/requirements.txt` | 科研计算依赖；当前环境版本见原执行收据 |
| `reproduction.py` | 当前论文核验、既存点结果重建与正式图重绘 |
| `实验复现/mainline_report.py` | 使用新路径解析器的 2026 年报告汇总代码 |
| `工具` | 本地 Pandoc 等工具，不加入 Git |

现行论文的生产代码入口：

```powershell
python project.py run-script scripts/run_praw_offline_supplement.py --help
python project.py run-script scripts/run_independent_confirmation.py --help
python project.py run-script 02_代码/实验复现/mainline_report.py --help
```

实际执行时仍使用原协议要求的种子、数据与 PBS 分配，不将旧测试重新用作未查看数据。当前整理任务只运行核验、既存结果记账重建、绘图和编译；不恢复研究队列。

历史实际执行源码及部署快照留在 `04_结果` 的对应证据包中，保持原字节和原收据的哈希关系。维护代码集中在本目录；源码快照不作为第二套可随意修改的实现。

详见 [复现说明](../复现说明.md)。
