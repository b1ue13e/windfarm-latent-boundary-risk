# TSTE 英文稿与正式图组 v14

标题：Current Power as Incremental Telemetry for Wind Power Reserve Decisions

当前正文为 manuscript.pdf，共8页；补充材料为 supplementary.pdf。权威源为 manuscript.tex、sections/*.tex 和 references.bib；manuscript.md 是便读导出副本。

正文采用五张图、16个互补面板：

1. 整体架构与信息时序：t−6 的预测输入截止、t 的备用决策、t+6 的10分钟目标；明确两次截零、冻结模型、历史偏移和事后计分。
2. 完整144次决策实例：原始非负估计、备用请求和实际短缺，以及全部历史校准偏移。
3. 匹配测量对照：四种输入、HGB/MLP、五次固定拟合；原同时区间和全部35个天气日。
4. 跨年取舍：5与112列备用输入、原成本/事件率界、采购与未覆盖短缺成本分解、全部20个拟合结果。
5. 全日历：365/120个日期和有效日期的配对成本背景；2025年9月11–22日无有效目标，保留缺失标记。

图形在 figures/v14，均提供 PDF、可编辑SVG和600dpiPNG。绘图入口 figure_code/figures_v14.py 使用已有 source_data/v2、v4、v10；附带对齐辅助脚本，可在本机重绘。source_data/v3 另为现行受保护输入核验所需。这些版本号表示数据来源，不是待清理的旧稿件。

2026-11-11 按用户要求删除旧稿件、旧图形及旧交付包。当前目录保留现行稿件、绘图数据、构建与检查入口；历史审计及其快照移至 ../../04_结果/历史证据，文献和核验元数据移至 ../参考文献/TSTE当前稿件。原始实验结果、阈值、区间和补充材料不改。

在仓库根目录运行（新输出进入独立复现目录，不覆盖当前PDF或原始结果）：

```powershell
python project.py verify
python project.py reproduce-results
python project.py redraw
python project.py build-paper
```

绘图源码仍为 `figure_code/figures_v14.py`，构建源码为 `qa/build_pdfs.py`；新入口设置好导入路径、工作目录和隔离输出位置。训练及原确认实验入口见 [复现说明](../../复现说明.md)。

主图以Gilbert2020、Soares2016、Wen2022的已下载TSTE论文和用户提供的Top-Conf Figure Gallery为设计参考。全部图形由本稿的方法和真实数据重新绘制，未复制参考图、未调用图片生成模型。原科学及数字检查仅检查既存结果；数字检查使用脚本内置的缓存核对路径，没有重新生成统计量。

完整交付包：tste_figures_v14.zip，含正文和补充PDF、TeX、图形、绘图代码、源数据和复现说明。检查记录在 qa/figure_rebuild_v14，不进入论文。尚未投稿。
