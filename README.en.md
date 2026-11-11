# 风电备用决策论文与复现材料

当前论文：*Current Power as Incremental Telemetry for Wind Power Reserve Decisions*。

| 目录 | 查找内容 |
| --- | --- |
| [01_当前论文](01_当前论文/TSTE/README.md) | 正文、补充材料、TeX、正式图、绘图数据与参考文献 |
| [02_代码](02_代码/README.md) | 实现、实验/分析入口、测试和依赖 |
| [03_数据](03_数据/README.md) | 原始 SCADA、外部数据与预处理缓存 |
| [04_结果](04_结果/README.md) | 当前论文证据、完整实验结果、审计与复现输出 |

从项目根目录运行：

```powershell
python project.py verify
python project.py reproduce-results
python project.py redraw
python project.py build-paper
```

[复现说明](复现说明.md) 列出每个入口的作用、数据依赖和原实验执行条件。新输出写入 `04_结果/复现运行`，不覆盖封存结果。

[项目状态](PROJECT.md) 仍为 `STOP_ADDITIONAL_INVESTMENT`；此次整理不启动训练、采数或新研究。科学主张以 [科学契约](04_结果/项目记录/docs/SCIENTIFIC_CONTRACT.md) 为准。目标期刊或目录名不表示已投稿。

旧目录不再按尝试/阶段嵌套；冻结文件中的旧路径通过共享解析器读取：

```powershell
python project.py locate experiments/E04
python project.py locate analyses/independent_confirmation_execution_20261019
```

[目录重构记录](04_结果/项目记录/复现目录重构_20261111/README.md) 保留迁移身份与验收结果；原始数据不提交 Git。
