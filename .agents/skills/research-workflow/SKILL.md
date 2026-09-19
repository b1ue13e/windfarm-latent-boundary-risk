---
name: research-workflow
description: >-
  End-to-end academic research workflow for turning a rough idea, paper, dataset, or research question into a defensible gap,
  literature map, method shortlist, mathematical understanding, experiment and ablation plan, reproducible Python implementation,
  result analysis, and paper/proposal narrative. Use when the user wants to find a research question, review papers, compare methods,
  decide what is worth trying, understand equations, design experiments, write/debug research code, interpret results, plan a proposal,
  or check whether a research story is internally consistent. Especially useful for ML/AI/statistics/quantitative research.
compatibility: >-
  Agent Skills-compatible. Works best with scholarly/web search plus Python or shell execution; degrades gracefully when some tools are unavailable.
metadata:
  author: custom
  version: "1.0.0"
  language: zh-CN
---

# Research Workflow

把科研当成一条“证据链”，而不是“先想一个新模型，再找理由包装”。

默认主链：

**研究问题 → gap → 检索论文 → 文献矩阵 → 比较方法 → 选择值得尝试的方法 → 数学原理 → 可行性反推 → 实验/消融 → Python 实现 → 结果分析 → 机制解释 → 写作 → 一致性终检**

核心原则：**每一步的输出必须成为下一步的输入。对不上的地方，不润色，直接返工。**

## 0. 先判断当前任务处于哪一段

不要机械地从头开始。先识别用户现在需要的是：

- `IDEA`：只有模糊方向，需要定问题与 gap。
- `LITERATURE`：已有问题，需要检索、比较、找缺口。
- `METHOD`：已有 gap，需要选方法并理解数学。
- `EXPERIMENT`：已有方法，需要设计实验、消融、指标与统计检验。
- `CODE`：已有实验设计，需要写/改/调试 Python。
- `RESULT`：已有结果，需要判断是否可信、为什么、下一步做什么。
- `WRITING`：已有研究内容，需要写 proposal / paper。
- `AUDIT`：已有完整草稿，需要做一致性、可复现性和审稿风险检查。
- `END_TO_END`：用户明确要求从问题一路做到结果或论文。

只问真正阻塞执行的问题。能通过论文、代码、数据、上下文推断的，不让用户重复提供。

## 1. 定问题：先强制写出“三句话”

在开始大规模检索之前，先生成并迭代三句话：

1. **Failure sentence**：现有研究在什么明确条件下做不好什么事？
2. **Cause sentence**：为什么会失败，为什么已有方法没有解决？
3. **Plan sentence**：准备以什么机制/方法解决，目标改善到什么层面？

禁止用以下表达充当 gap：
- “目前研究较少”
- “尚未得到充分关注”
- “很少有人将 A 用于 B”
- “我们首次尝试……”

这些最多是现象，不是可检验的研究缺口。

### Gap 分类

优先寻找：
- **方法空白**：已有方法在明确条件下失效，你提出机制性改进。优先级最高。
- **对象空白**：方法成熟，但尚未在某数据/群体/场景验证。必须回答“为什么该对象改变了问题本身”。
- **矛盾空白**：高质量文献在相近条件下得出冲突结论，需要解释边界条件或机制。说服力强但检索难。

若三句话中出现“研究较少/尚未关注”等空泛措辞，继续找 gap，不进入下一阶段。

详细判断见 [references/gap-guide.md](references/gap-guide.md)。

## 2. 把主问题拆成 2–3 个子问题

主问题只能有一个。子问题必须是主问题的分解，不得是三个平行方向。

每个子问题后强制写：
- 用什么方法回答；
- 用什么数据回答；
- 用什么指标/统计检验回答；
- 如果答不上，是否删除。

输出为：

| 子问题 | 方法 | 数据 | 指标/检验 | 可证伪条件 |
|---|---|---|---|---|

无法映射到方法和数据的子问题，不保留。

## 3. 文献检索：不是“搜很多”，而是“让每篇论文承担角色”

优先搜索近 2–3 年高质量工作，同时保留奠基文献和关键经典基线。

每篇最终引用的论文至少承担一种角色：
- **奠基类**：定义问题、任务、理论或评价框架。
- **主流类**：当前主要做法和强基线。
- **失效类**：直接暴露你要解决的 failure，是 gap 的核心证据。
- **邻域类**：其他领域出现过相似机制，证明你的方法不是凭空发明。

### 检索循环

至少做三轮：
1. **问题词**：任务 + failure condition + metric。
2. **方法词**：主流方法 + limitation/failure/robustness/generalization 等。
3. **反证词**：主动搜索“有没有人已经做过几乎一样的事”，包括同义词、旧术语、其他学科叫法。

若发现高度相似工作：
- 不隐瞒；
- 先比较数据、假设、机制、实验协议、目标；
- 能建立清晰差异则改 gap；
- 差异不足则换问题，不靠措辞制造新颖性。

### 文献矩阵

必须维护矩阵，而不是只写摘要。模板见：
[assets/literature-matrix.csv](assets/literature-matrix.csv)

关键列至少包括：
`paper / year / task / data / method / assumption / main_result / failure / gap_role / similarity_to_us / reusable_component / evidence_strength`

写综述时按主题合并同类文献，不“一篇一段”。

详细规则见 [references/literature-matrix.md](references/literature-matrix.md)。

## 4. 比较方法：先判断“值不值得试”，再写代码

候选方法不能因为“新”“复杂”“SOTA”就进入实验。

对每个候选方法从 0–5 分评价：
- `gap_fit`：是否直接针对 failure mechanism；
- `information_gain`：即使失败，能否回答研究问题；
- `theory_fit`：假设是否适用于当前数据；
- `implementation_risk`：实现/调参风险，分数越高越可控；
- `compute_feasibility`：算力/时间是否可承受；
- `comparison_value`：是否是审稿人会期待的强基线；
- `novelty_value`：是否形成机制级增量而非换模块。

默认优先级：
**直接回答研究问题 > 强基线 > 机制消融 > 花哨模型。**

最终分成：
- `MUST TRY`：不做就无法支撑结论；
- `SHOULD TRY`：高信息增益；
- `OPTIONAL`：资源允许再做；
- `REJECT`：成本高、回答不了问题或假设不匹配。

不能只给分数，必须给一句“为什么值得/不值得试”。

## 5. 数学原理：解释到能实现、能做消融、能解释失败

对每个关键方法按三层解释：

### A. 直觉层
回答：
- 它试图改变什么量？
- 为什么这个量可能改善当前 failure？
- 它与最接近 baseline 的本质差异是什么？

### B. 数学层
给出：
- 变量与维度；
- 目标函数/更新式；
- 关键假设；
- 哪个项负责哪个机制；
- 极端情况下会退化成什么。

不要堆公式。每个公式后解释“它在算法里做了什么”。

### C. 实现层
把数学映射到：
- 输入张量；
- forward；
- loss；
- optimizer/update；
- 超参数；
- 复杂度；
- 数值稳定性风险。

最后生成“数学 → 代码 → 消融”的映射表。

详细模板见 [references/method-math-experiment.md](references/method-math-experiment.md)。

## 6. 可行性反推：从最终图表往回推

在投入编码前，先写“论文最终必须出现的图/表”。

例如：
- 主结果表；
- failure condition 曲线；
- 消融表；
- 机制诊断图；
- 计算成本表；
- 稳健性/统计显著性；
- case study（如适用）。

对每张图/表倒推：
1. 需要哪些字段和数据？
2. 数据现在是否拿得到？权限是谁？
3. 预处理是什么？
4. 要跑哪些模型/种子/数据切分？
5. 需要多少算力和时间？
6. 失败后降级方案是什么？

### 四个必须落地的问题

- 数据是否已经在手？不在手则写获取路径 + 备用公开数据。
- 方法是否真的会做？首次使用则预算学习 + smoke test 时间。
- 是否涉及伦理审批、授权、许可？有则纳入关键路径。
- 如果主方案失败怎么办？至少准备一个降级方案。

时间估计按悲观估计再乘 `1.5`；整体至少留 `20%` 缓冲。

## 7. 实验设计：每个实验都必须回答一个问题

先定义：
- 主假设；
- 次假设；
- failure condition；
- 成功判据；
- 失败判据。

然后再排实验。

### 最小完整实验集合

通常包括：
- 强 baseline；
- 你的完整方法；
- 关键组件消融；
- 与 gap 直接相关的 stress test / subgroup / corruption / shift；
- 多随机种子；
- 资源成本；
- 至少一个“可能推翻你”的反证实验。

### 消融原则

每个组件必须有因果式问题：

“去掉 X 后，如果 Y 明显下降，说明 X 对机制 Z 有贡献。”

禁止仅为了让表格更满而做消融。

### 防止数据泄漏

在写代码前明确：
- train/val/test 切分单位；
- 时间序列是否按时间切；
- 标准化参数从哪里估计；
- 特征工程是否接触 test；
- 模型选择是否偷看 test；
- 重复个体/实体是否跨 split。

实验模板见 [assets/experiment-plan-template.md](assets/experiment-plan-template.md)。

## 8. Python 实现：先最小闭环，再扩展

编码顺序：
1. 数据读取 + 单元 sanity check；
2. 最简单 baseline 跑通；
3. 统一训练/评估接口；
4. 加入新方法；
5. 单 batch overfit / tiny subset smoke test；
6. 正式实验；
7. 自动记录 config、seed、git commit、环境、指标、耗时；
8. 再做并行化和性能优化。

### 代码质量要求

研究代码至少做到：
- seed 可控；
- 配置与代码分离；
- 数据路径不硬编码；
- 指标实现有测试或人工校验；
- checkpoint 可恢复；
- 训练日志可追溯；
- 结果自动落盘；
- 图表从结果文件生成，不手抄数值；
- baseline 与新方法共享同一评估协议。

如果用户给现有代码，先读项目结构和运行路径，再修改；不要凭文件名猜实现。

可用 `scripts/init_research_project.py` 初始化标准目录。

## 9. 结果分析：先判断“能不能信”，再判断“好不好”

收到结果后按这个顺序分析：

### 9.1 可信度
检查：
- 是否所有 seed 都一致；
- 方差是否过大；
- 是否存在异常 run；
- baseline 是否复现合理；
- 指标方向是否搞反；
- 数据泄漏；
- test 是否被反复用于选择；
- 是否只有单一数据集/单一切分支撑结论。

### 9.2 效应
不要只看“涨了多少”：
- 绝对改善；
- 相对改善；
- 方差/置信区间；
- 统计检验（需要时）；
- 在 failure condition 下是否改善更明显；
- 成本是否成比例增加。

### 9.3 机制
问：
- 哪个组件真正贡献了增益？
- 增益是否与最初 cause sentence 一致？
- 结果是否支持原假设，还是迫使我们修改机制解释？
- 哪个失败结果最有信息量？

### 9.4 下一轮实验
只追加“能减少关键不确定性”的实验。
不因为某个结果难看就无限调参，也不因为结果好看就停止反证。

详细见 [references/result-interpretation-writing.md](references/result-interpretation-writing.md)。

## 10. 帮用户真正读懂论文/结果

用户问“这篇论文/这个结果是什么意思”时，不只做摘要。

优先解释：
- 作者真正解决的 failure；
- 方法相对 baseline 改了哪一个机制；
- 公式里的核心量；
- 实验到底验证了什么、没验证什么；
- 哪些结论是证据支持，哪些是作者推断；
- 对当前研究可复用的部分；
- 如果复现，最容易踩的坑。

若用户背景允许，尽量把结论连接到概率、统计、优化、线性代数或机器学习基本原理。

## 11. 写 Proposal / Paper：内容成熟后再包装

### Introduction 四段式

1. 大问题为什么重要：领域层面，2–3 句。
2. 目前做到哪：压缩版文献综述。
3. 还缺什么：必须与 `Failure sentence` 完全一致。
4. 本研究做什么：方法、实验、预期贡献，逐条写清。

`Problem Statement` 可以更具体，但与 Introduction 的缺口用词必须一致。

### 文献综述

不是“谁做了什么”的流水账。
每个小节结尾用一句话回答：
**这一类工作还留下什么没有解决？**

所有小节结论合起来应自然指向 gap。

### 假设 / 概念框架

定量研究：
- 每条假设明确变量、方向、检验方式。

定性研究：
- 画出核心概念与关系，并明确数据如何支撑关系。

无法在分析计划中找到对应检验方式的假设/关系，删除。

### 时间表、预算、附录

时间表按阶段，不按月份机械切：
`数据 → 预处理 → 基线 → 主实验 → 消融/稳健性 → 写作 → 修改`

预算中的每一项必须能映射到方法步骤。

附录放：
- 额外表格；
- 问卷/访谈提纲；
- 数据字典；
- 伦理审批材料；
- 超参数；
- 复现细节。

## 12. 标题最后写

标题结构优先：
**研究对象 + 方法/视角 + 关注的问题**

避免空泛占位词：研究、探讨、初探、若干问题等。

标题必须能覆盖第一句 Failure sentence；覆盖不了说明标题承诺错了。

## 13. 一致性终检：这是硬门槛

最终沿链逐项检查：

**研究问题 → gap → 假设/框架 → 方法 → 数据 → 指标/分析 → 实验 → 时间表 → 结果 → 贡献**

必须回答：
- 每个研究问题，在方法里有对应做法吗？
- 每条假设，有对应检验吗？
- 方法需要的数据，在数据计划里有来源吗？
- 每个关键组件，有实验或消融验证吗？
- 时间表覆盖所有方法步骤吗？
- 贡献只承诺实际实验能支撑的内容吗？
- Introduction 缺口、Problem Statement、Expected Contribution 说的是同一件事吗？
- 结论是否超出数据、数据集和实验协议能支撑的范围？

最常见硬伤：
- 方法多一步，时间表没排；
- 贡献比实验能支撑的多一截；
- 研究问题是 A，结果却主要证明 B；
- introduction 说“鲁棒性”，正文却只测平均精度；
- gap 是特定 failure condition，实验却没专门测该 condition。

终检模板见 [assets/paper-consistency-checklist.md](assets/paper-consistency-checklist.md)。

## 14. 默认交付格式

除非用户另有要求，每个阶段结束给一个“研究状态卡”，不写大段空话：

**当前结论**
- 一句话说目前最重要的判断。

**证据**
- 2–5 条最关键证据；文献事实必须带可核验来源。

**未解决不确定性**
- 最多 3 条。

**下一步**
- 只列能最大幅度减少不确定性的 1–3 个动作。

**Kill / Pivot 条件**
- 说明出现什么证据时应该砍掉或改方向。

## 15. 证据与科研诚信

绝不：
- 编造论文、DOI、实验结果、数据来源；
- 把未验证的猜测写成事实；
- 隐瞒高度相似工作；
- 只报告最好 seed；
- 为了显著性而无止境试验；
- 在看过 test 后继续将其称为 untouched test；
- 先看结果再假装假设是事前提出的。

当来源无法核验时，明确标注“待核验”。
当结果不支持原假设时，优先修改理论，而不是修改事实。

## 16. 两种运行模式

### 快速 Proposal 模式（约 5 天 / 40 小时）
- Day 1：三句话 + gap + 主/子问题。
- Day 1–2：最终图表反推 + 数据/方法/伦理/降级方案。
- Day 2–3：文献矩阵 + 综述。
- Day 3–4：Introduction + Problem Statement + 假设/框架 + Methodology。
- Day 4：时间表 + 预算 + 引用 + 附录。
- Day 5：标题 + 一致性终检。

### 完整 Research 模式
在 Proposal 模式后继续：
- baseline 复现；
- method smoke test；
- 主实验；
- 消融/反证/稳健性；
- 结果可信度分析；
- 机制解释；
- 论文写作；
- 复现包整理。

## 17. 启动模板

用户只给一个模糊想法时，直接用下面格式启动，不要求用户先写完整 proposal：

> **方向/任务**：  
> **我目前认为的 failure**：  
> **可能原因**：  
> **现有数据/代码/论文**：  
> **资源限制（算力/时间/权限）**：  
> **目标（proposal / paper / 复现 / 新方法）**：

信息缺失但不阻塞时，用显式假设继续，并告诉用户哪些假设后续必须验证。
