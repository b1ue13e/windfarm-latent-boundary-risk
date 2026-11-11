# F7 专项审计报告：文献矩阵、文献原文资产与 Mimir 调研真实性核验

**报告日期**：2026-10-13  
**问题编号**：Issue F7  
**审计对象**：
1. `literature/literature_matrix.csv`
2. `literature/top_journal_papers/*.pdf` (51 篇)
3. `docs/MIMIR_INGESTION_AND_AUDIT_REPORT.md` (Stage 0 Literature Review 与资产导入)
4. Mimir 知识库 `research_wiki.json` 中的文献条目

**核验状态**：`VERIFIED (FATAL DEFECT CONFIRMED)`  
**核心裁决**：旧文献矩阵 `literature/literature_matrix.csv` 存在系统性 DOI--标题错配；`literature/top_journal_papers` 绝大多数文件为仓库内部生成的简报伪装；Mimir 报告存在对纯数学论文 `arXiv:2405.01234` 伪造成风电顶刊基线的严重幻觉。**旧文献矩阵与 Mimir Literature GO 决议彻底不可复用，强制标记废弃并重构真实证据层。**

---

## 一、 证据点 1：旧文献矩阵 DOI--标题严重错配审计

通过运行自动化逆向核验脚本 `scripts/audit_literature_f7.py`，针对 `literature/literature_matrix.csv` 中重点排查行与 CrossRef 官方元数据数据库（`api.crossref.org/works/{doi}`）进行双向比对，结果表明在 19 个重点行中存在高达 **18 行** 的失真与错配（10 行指向完全风马牛不相及的其他学科论文，8 行返回 HTTP 404 错误）。

### 1.1 典型错配对照清单（截取自真实 CrossRef 检索数据）

| 行号 (Row) | 声明 paper_id | 声明 DOI | CSV 中声称标题 (风电/控制/气象) | CrossRef 官方真实注册标题 (实际论文) | 真实领域/性质 | 匹配状态 |
| :---: | :--- | :--- | :--- | :--- | :--- | :---: |
| **Row 20** | `Zhou_2022_SciData` | `10.1038/s41597-024-03487-7` | SDWPF: A large-scale spatio-temporal wind power forecasting benchmark with dynamic status | **Chromosome-level genome assembly of the cereal cyst nematode Heterodera flipjevi** | **线虫染色体基因组测序** | ❌ 荒谬错配 |
| **Row 25** | `Mulders_2024_RenewEnergy` | `10.1016/j.renene.2023.119854` | Nonlinear individual pitch control for load reduction in modern wind turbines | **Bioethanol production in bioreactor assisted by magnetic field: Correlation between S. cerevisiae H+ effluxes and fermentative efficiency** | **酵母菌生物乙醇发酵工程** | ❌ 荒谬错配 |
| **Row 30** | `Wang_2025_ApplEnergy` | `10.1016/j.apenergy.2024.124501` | Uncertainty quantification and dynamic operating reserve sizing in renewable-dominated grids | **Experimental investigation of wire-mesh equipped U-tube evacuated tube collector integrated with phase change material for hot water generation** | **太阳能真空管集热热水系统** | ❌ 荒谬错配 |
| **Row 14** | `TautzWeinert_2017_RSER` | `10.1016/j.rser.2016.11.160` | Using SCADA data for wind turbine condition monitoring — A review | **A comprehensive review on biomass and solar energy for sustainable energy generation in Nigeria** | **尼日利亚生物质与太阳能综述** | ❌ 荒谬错配 |
| **Row 15** | `Gonzalez_2019_RenewEnergy` | `10.1016/j.renene.2018.10.019` | On the use of high-frequency SCADA data for improved wind turbine performance monitoring | **Performance assessment of a standard radial turbine as turbo expander for an adapted solar concentration ORC** | **太阳能聚焦有机朗肯循环向心透平** | ❌ 荒谬错配 |
| **Row 18** | `Slootweg_2003_TPWRS` | `10.1109/TPWRS.2002.805018` | General model for variable speed wind turbines including a pitch control model | **Voltage-stability protection and control using a wide-area network of phasor measurements** | **广域相量测量电网电压稳定控制** | ❌ 错配 |
| **Row 32** | `Nielsen_2006_TPWRS` | `10.1109/TPWRS.2006.873111` | Using quantile regression to estimate the wind power forecast distribution | **Application of a Novel Eigenvalue Trajectory Tracing Method to Identify Both Oscillatory Stability Margin and Damping Margin** | **电力系统特征值轨迹跟踪振荡裕度** | ❌ 错配 |
| **Row 33** | `Ela_2011_PESGM` | `10.1109/PES.2011.6039832` | Operating reserves and variable generation: A survey of international practices | **An adaptive protection scheme for distributed systems with distributed generation** | **含分布式电源配电系统自适应保护** | ❌ 错配 |
| **Row 28** | `Pinson_2013_WindEnergy` | `10.1002/we.1558` | Wind power forecasting: From point forecasts to probabilistic scenarios | **Wind Energy literature survey No. 26** | **期刊文摘书目索引栏目** | ❌ 错配 |
| **Row 2** | `Daenens_2025_WES` | `10.5194/wes-10-385-2025` | Spatio-temporal graph neural networks for normal behaviour modelling... | HTTP 404: Not Found (真实论文 DOI 实为 `10.5194/wes-10-1137-2025`) | **无效/拼写错误 DOI** | ❌ 404 |
| **Row 10** | `Pierre_2019_TPWRS` | `10.1109/TPWRS.2018.2882583` | Design of the Pacific Northwest National Laboratory wide-area damping controller | HTTP 404: Not Found (真实论文 DOI 实为 `10.1109/TPWRS.2019.2903782`) | **无效/拼写错误 DOI** | ❌ 404 |
| **Row 12** | `Ullah_2022_TII` | `10.1109/TII.2021.3131065` | Enabling massive machine-type communications in offshore wind farms... | HTTP 404: Not Found (真实论文 DOI 实为 `10.1109/TII.2021.3112386`) | **无效/拼写错误 DOI** | ❌ 404 |

### 1.2 根因溯源
检查 `scripts/build_literature_benchmarking.py` 源码发现：该脚本在第 1-580 行中硬编码了 40+ 篇文献的元数据字典，在人工或脚本批量拼接时，存在严重的“张冠李戴”与未经外部解析验证的拼接错误，直接将生物学、农业科学、热能工程的 DOI 强行贴在风电文献标题上，形成虚假元数据。

---

## 二、 证据点 2：`literature/top_journal_papers/` 资产性质审计

审计对 `literature/top_journal_papers/` 目录下的 51 个 PDF 文件进行了逐一元数据提取和首页文本特征分析：
1. **统计结果**：
   - 总 PDF 数量：**51 个**
   - 首页包含 `Literature Benchmark Brief`：**40 个**（占比 78.4%）
   - 真实外部论文 PDF：**11 个**（占比 21.6%）
2. **生成机制确认**：
   - 在 `scripts/build_literature_benchmarking.py:588-675` 中存在 `generate_pdf_brief(entry, out_pdf_path)` 函数，利用 Python ReportLab 库在本地批量合成了排版格式统一的 1-2 页 Benchmark 简报，并直接以学术论文命名规范输出到 `literature/top_journal_papers/`。
3. **证据效力定性**：
   - 这 40 个 PDF **绝非同行评议期刊发表的论文原文**，而是本仓库早前生成的本地衍生简报。
   - 将其作为“文献原文”存档并声称通过原文验证，构成严重的证据链虚标。

---

## 三、 证据点 3：Mimir 报告 `arXiv:2405.01234` 严重幻觉事件审计

### 3.1 报告中的虚假陈述
在 `docs/MIMIR_INGESTION_AND_AUDIT_REPORT.md` 中：
- 第 42-45 行记录：
  > `- **2405.01234** (Spatial-temporal wind power probabilistic forecasting via physics-guided graph neural networks)`  
  > `- 角色：Mainstream 核心主流基线`  
  > `- 关联度打分：9 / 10`  
  > `- 论述理由：主流时空图基线，本论文在相同到达时刻信息集与控制边界约束下与其展开实证对比。`
- 第 105 行记录：
  > `阶段 0: Literature Review / 文献调研 | DELIVERY-LIT-01 | 5 / 5 (100%) | 2405.01234 [Verified] | GO`

### 3.2 官方真实数据核查
调用 arXiv 官方 API (`http://export.arxiv.org/api/query?id_list=2405.01234`) 检索结果：
- **arXiv ID**：`2405.01234`
- **提交时间**：2024 年 5 月
- **作者**：Ivan D. Chipchakov
- **官方真实标题**：*Matrix invertible extensions over commutative rings. Part III: Hermite rings*
- **研究领域**：Mathematics - Commutative Algebra / Rings and Algebras (`math.RA`, `math.AC`)
- **真实摘要**：探讨交换环上的 Hermite 环与初等因子环 (Elementary Divisor Rings, EDR)，提炼 Kaplansky、McGovern、Roitman、Wiegand 等学者的代数判据。

### 3.3 定性结论
将纯代数数学论文编造成风电时空图预测基线，并给出 9/10 高分与“Verified GO”门控结论，属于彻底的模型幻觉产物。**Mimir Stage 0 的该项交付与文献记录属于污染证据，必须全部撤销与清洗。**

---

## 四、 处置决议与证据层重建规范

1. **废弃旧资产**：
   - 旧文件 `literature/literature_matrix.csv` 标记为 `DEPRECATED`，禁止任何脚本、写作或评审环节读取该文件作为事实证据。
   - `literature/top_journal_papers/` 中 40 个 `Literature Benchmark Brief` PDF 明确分类为 `Derivative Brief (Non-Original)`，剥夺其“论文原文”证据属性。
2. **清洗 Mimir 数据库**：
   - 从 `research_wiki.json` 中彻底移除 `2405.01234` 虚构文献记录及其派生关联。
   - 修正 `docs/MIMIR_INGESTION_AND_AUDIT_REPORT.md`，记录此次审计发现并撤回原虚假 GO 评定。
3. **建立真实、高置信度的新文献证据层**：
   - 严格以经同行评议核实且具有可验证官方 DOI 的真实文献为准（采纳 `docs/REVERSE_AUDIT_LITERATURE_MATRIX_20261012.csv` 中的真实文献集）。
   - 采用标准 `literature_add` 工具，录入覆盖四大关键角色（`foundational`、`mainstream`、`failing`、`adjacent`）的真实文献，确保角色完备无缺口。
