# Literature Assets & Evidence Governance Notice

## ⚠️ CRITICAL NOTICE: Deprecation of Historical Literature Assets (Issue F7)

经 2026-10-13 专项科研审计（详见 `docs/F7_LITERATURE_ASSET_AUDIT_REPORT.md` 与 `docs/REVERSE_SCIENTIFIC_AUDIT_20261012.md`），本目录下历史文献资产存在严重真实性缺陷，**已全面废弃，禁止作为科研论断的可靠证据层**：

1. **`literature/literature_matrix.csv` (DEPRECATED / UNRELIABLE)**:
   - 经 CrossRef 自动化逆向核验，至少 18 行存在严重的 DOI--标题错配或 404 无效 DOI（例如将线虫基因组测序、酵母菌发酵、真空管热水器等不相干论文的 DOI 强行贴在风电标题上）。
   - **禁止** 任何脚本、论文撰写或评审逻辑引用该 CSV 作为学术事实来源。

2. **`literature/top_journal_papers/*.pdf` (DERIVATIVE BRIEFS - NOT ORIGINAL PAPERS)**:
   - 经自动化 PDF 首页文本解析，该目录下 51 个 PDF 文件中，有 **40 个文件**（占比 78.4%）首页为仓库内 ReportLab 自动合成的 `Literature Benchmark Brief`，**并非期刊发表的论文原文**。
   - 仅有 11 个为真正的外部论文全文。
   - **禁止** 将上述 Brief PDF 作为“已核验论文原文”作为科学证据层。

---

## 真实文献证据层与权威事实源

项目的真实学术证据层已迁移并严格受控于以下资产：
1. **`docs/REVERSE_AUDIT_LITERATURE_MATRIX_20261012.csv`**:
   - 经过严格逐篇核验的 15 篇顶级期刊/会议论文，包含真实可解析 DOI、验证状态及针对本项目技术路径的创新性威胁分析。
2. **`research-manifest.json` (通过 `literature_add` / `literature_matrix` 维护)**:
   - 结构化录入且四类角色（`foundational`、`mainstream`、`failing`、`adjacent`）完备的科研证据链文献矩阵。
