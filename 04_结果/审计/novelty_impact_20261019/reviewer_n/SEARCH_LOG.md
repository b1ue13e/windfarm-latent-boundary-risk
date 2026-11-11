# Reviewer N 实际检索与取文日志

时间：2026-10-19，UTC约06:13–06:21；终端与web检索。所有新增文件仅在本目录。读入AGENTS.md、docs/SCIENTIFIC_CONTRACT.md、PROJECT.md、research-skill/SKILL.md、08_claim_inventory.md及claim_freeze.json。未读取其他本轮reviewer输出或弃用brief/旧literature_matrix。

## 搜索轮次与原样queries

以下为本轮实际发送的查询，不将搜索结果列表数量解释为纳入研究数；结果中的聚合站只用于发现原始来源，不用作内容事实。

### Round 1：指定种子、经典与same problem

1. "10.1002/we.416"
2. "10.1109/TPWRS.2021.3053847"
3. "10.1016/j.energy.2024.131544"
4. "Short-term variations in wind power" pdf Pritchard
5. "Operating Reserve Quantification" "pdf"
6. "Probabilistic wind power forecasting resilient" arxiv
7. Pritchard quantile wind power 416 filetype:pdf
8. "Pritchard" "probabilistic persistence" wind
9. "Zhao" "Wan" "9334448" pdf
10. "Operating Reserve Quantification Using Prediction Intervals" -site:researchgate.net -site:scispace.com -site:ablesci.com

发现：Pritchard出版社正文部分成功；Wen arXiv v3；IEEE Zhao原始记录；作者机构Sun2022全文。全任务先行尚未确认。

### Round 2：same phenomenon/method/insight与negative

11. wind power "feature selection" "quantile" "2024"
12. wind power reserve "forecast errors" "feature selection"
13. wind power "probabilistic persistence" 2021 2022 2023 2024 2025
14. wind power decision focused learning forecast accuracy economic value 2023
15. wind "features" "economic value" Muñoz forecast selection
16. "Feature selection" "renewable" "trading" forecasting economic value
17. "wind" "minimum" "sufficient" "reserve" telemetry
18. "wind power" "feature selection" "decision" quantile reserve
19. "wind" "economic value" "feature selection" forecasting -site:researchgate.net -site:scispace.com
20. "Selecting" "features" "value" "renewable energy" forecasting
21. "An Integrated Approach for Value-Oriented Energy Forecasting"

发现：Muñoz2023在线交易原文、Wahdany2023、Bouche2023、Rutyna2025；Carriere2019为候选，未将其聚合站文本当原文。未把feature selection泛词搜索当成引文追踪。

### Round 3：方法近邻、反证与真实引文扩展

22. site:onlinelibrary.wiley.com/doi/10.1002/we.416 "5." "sharpness"
23. site:onlinelibrary.wiley.com/doi/10.1002/we.416 "selection"
24. site:onlinelibrary.wiley.com/doi/10.1002/we.416 "Table IV"
25. "Towards resilient energy forecasting"
26. "Resilient Feature-driven Trading of Renewable Energy with Missing Data"
27. "wind" "forecasting features" "economic" "Stratigakos"
28. "More than accuracy" "wind" 2023
29. "Using quantile regression to extend an existing wind power forecasting system" pdf
30. "Operating Reserve Quantification" "Zhao" "Can Wan" pdf fulltext
31. "wind" "feature selection" "economic value" "forecasts" -site:researchgate.net -site:scispace.com -site:ouci.dntb.gov.ua -site:wikipedia.org
32. "wind power" "pitch" "regime" "probabilistic" "2021" "2024"
33. "wind power" "reserve" "telemetry" "sufficient"
34. wind power reserve input selection minimum sufficient information risk cost 2021 2022 2023 2024 2025 2026
35. wind power "state" "quantile" "decision" pitch boundary
36. "wind power" "accuracy" "profits" "losses" 2023 forecasting
37. "Feature-driven improvement of renewable energy forecasting and trading"
38. "Feature-driven improvement" "pdf"
39. "Feature-driven improvement" "feature selection"
40. "Short-term variations in wind power" "5." "model"
41. "Short-term variations in wind power" "sharpness" "Table"
42. "Short-term variations in wind power" "5.1"
43. "Short-term variations in wind power" "CONCLUSIONS"

22–24及40–43未恢复Pritchard后半正文；不从摘要补造§5实验定位。34–36含2026词，出现候选但未据其摘要作强覆盖。37–39找得作者Muñoz2020全文；其新颖性评价以本地PDF §§II–IV为准。

## 真实backward与forward citation边

|方向|种子→实际追踪目标|真实引文位置/来源|检索/取文结果|
|---|---|---|---|
|backward|Pritchard2011→Nielsen/Madsen/Nielsen2006|Pritchard出版社References[4]，https://onlinelibrary.wiley.com/doi/abs/10.1002/we.416；正文§1/§4亦标Ref4|按目标题名检索，找到DOI10.1002/we.180及DTU/出版社元数据；全文未取得，未作正文强判。|
|backward|Wen2024→Stratigakos et al.2023/2024|作者v3 PDF26 References准确列Towards resilient energy forecasting；正文§1.2及§7.1引用|找到接受稿与期刊最终卷期15(1),2024,874–885，DOI10.1109/TSG.2023.3272379。不是概念query伪装引用；Wen所用年份2023为online/接受阶段。|
|forward|Zhao/Wan/Song2021→Sun et al.2022|Sun作者机构PDF22，印刷036303-21，References[19]准确题名与TPWRS36(4)3701(2021)；§II正文[19]|通过精确DOI/题名检索发现引文，再打开Sun全文核实引用。该条原bibliography只列C.Zhao/C.Wan，目标第三作者以IEEE/Crossref核实，未静默改写原引文。|
|forward|Stratigakos2023/2024→Kühnau et al.2023|Kühnau作者机构5页PDF p5 References[8]，p1–2 §I-A正文引[8]|全文取得并核读。引用的是2023发表阶段的robust forecasting；Kühnau进一步做缺失feature的交易损失。|
|forward|Muñoz2020→Kühnau2023|Kühnau PDF p5 References[6]，p2 §I-A讨论其data delay处理|全文引文成立；再按Muñoz题名找到作者arXiv1907.07580并核读。|

未执行专有数据库“全部被引文献”穷举，因此这些是实际可核查边，不是完整citation graph；不能报告穷尽forward citations。

## 取文成功与失败

- Pritchard：web在 https://onlinelibrary.wiley.com/doi/10.1002/we.416 实际返回551行页面，正文读取到行249（§4.4标题）。§3行117–184及§4.0/4.3行185–248提供强判。后续lineno249/250/270/320、fragment及full路径多次InternalError/timeout；Python直取HTML和PDF均403。pdf/epdf路径工具不可访问。故fetch_level=PARTIAL_PRIMARY_BODY，不能标全文核验。公开页首部分已足以证明当前功率条件分位数与跨年验证，不足以深审其后半实验。
- Zhao2021：IEEE https://ieeexplore.ieee.org/abstract/document/9334448 的web索引有原摘要、元数据、章节目录，/document页正文只有空壳；Python HTML与stampPDF/getPDF.jsp均418。未取得其方法、实验、附录，fetch_level=PRIMARY_ABSTRACT_TOC。没有使用科研通/ResearchGate请求PDF当作全文来源，也未绕过访问控制。
- Wen2024：出版社页面web可读摘要/介绍/讨论片段但direct open InternalError；作者 https://arxiv.org/pdf/2305.14662 下载850250B，明确v3/2024-04-24，26页；初始另取v2HTML仅作导航，最终正文页定位均v3。核读§§3–7与AppA，未声称与最终出版社PDF逐字一致。
- Sun2022：作者机构PDF下载6264659B，23页。核读§§I–III、VI、AppA2–3、References19；保留净负荷/15分钟–5分钟forecast差与本项目shortfall不相同。
- Stratigakos：orbit.dtu.dk/files路径web403，合法作者机构backend.orbit.dtu.dk/ws/portalfiles/portal/320707182/...成功6242955B。pypdf核实13页（机构封面+12页接受稿），核读§§II–IV；未逐项审计全部结果。pdftotext中的图字体出现控制符，不能用文本form-feed数量作PDF页数。
- Kühnau：UCL原始PDF web一次timeout，Python同URL正常取2797588B；5页全部阅读，PDF图字体有局部乱码，但方法正文、表I/II和参考文献可读。
- Wahdany：TU Delft最终版含封面PDF成功1482481B，13页；重点核读§1、§4.3–4.6及Tables3–6；不将forecast任务变化当同目标比较。
- Muñoz2020：arXiv1907.07580成功262987B，11页；核读§II、§III与§IV。明确其rolling fit、时间一致性限制与本项目冻结接口不同。
- Nielsen2006：DTU原始pubdb/4254-full.html仅元数据，无PDF链接；Wiley正文页实际只返回摘要+References。不能把full.html文件名当全文证明。
- Rutyna2025：MDPI原始网页读取摘要、§4和§6及future-work；只作邻域，不据其dimensionality百分比对本项目作实质先行判决。
- Bouche2023：ScienceDirect原记录有摘要；作者arXiv2204.09362只定位到记录，未在本轮深读正文；只作邻域候选。

本地取文记录：fetch_receipt.json、fetch_receipt2.json；元数据：crossref_metadata.json。所有纳入CSV的DOI均查Crossref；年份按最终卷期，Nielsen2006保留online2005/volume2006差异。Muñoz2020元数据另外由作者机构+arXiv与DOI对应核验。没有将Google搜索自动生成的引用数字视作证据。

## 范围与可重复性限制

七类检索是有针对性的反向审查，不是PRISMA系统综述。未以查询无结果证明无先行、未把全文拿不到判为无威胁。无新训练/推理/重采样/远端、无原实验/稿件编辑。输出内容审查与原项目科学门禁是不同责任；本文件不声称认证所有科学结论。
