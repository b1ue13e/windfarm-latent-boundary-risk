# Regime-Aware Physics-Aligned MoE 风电预测框架

> GitHub research package: the active scientific question is whether consequence signals recover a hidden MPPT-to-pitch boundary under matched arrival-time information, and whether that recovery changes tail-risk allocation during transitions. The project treats physics, recalibration, direct quantiles, and learned representations as competing information-boundary policies rather than as a universal neural leaderboard.

## GitHub collaboration

The repository is organized for evidence-first collaboration. Start with `docs/CANONICAL_RESEARCH_QUESTION.md`, `docs/REPOSITORY_EVIDENCE_MAP.md`, and `docs/FIRST_PRINCIPLES_ADVERSARIAL_AUDIT_20260921.md`. Pull requests run the lightweight contract checks in `.github/workflows/verify.yml`; the artifact-backed full gate is a separate manual workflow because raw data, local caches, and generated PDFs are excluded from a clean source clone. Use the issue templates for claim audits and atomic experiments.

这个工程围绕风电场多风机时序预测与机制证据构建展开：从原始风机坐标和 10 分钟粒度时序数据出发，构造动态有向尾流图、物理 regime 标签、时空编码器、MoE gate/expert 模型，并配套了 reviewer-facing 的证据导出、负控制、跨域验证、运行复现和论文构建脚本。

当前唯一活跃投稿主线是 **IEEE Transactions on Sustainable Energy (TSTE)**。根目录中的 `paper_tste_ieee.md`、`paper_tste_supplementary.md`、`cover_letter_tste.md` 和 `scripts/prepare_tste_submission.ps1` 组成当前投稿工程；`paper_draft.*` 与 Applied Energy 相关脚本保留为源稿/历史 failsafe，不再作为默认投稿目标。

## External Reproducibility & Replication Guide

This repository adheres to an evidence-first, strict zero-drift scientific contract. Every quantitative claim in the manuscript is backed by cryptographic SHA256 provenance in [`artifacts/ARTIFACT_MANIFEST.json`](artifacts/ARTIFACT_MANIFEST.json).

### Three Replication Tiers

| Tier | Scope | Hardware | Time | Command |
| :--- | :--- | :--- | :--- | :--- |
| **Tier 1: Fast Replication** | Full manuscript claim verification & SHA256 cryptographic audit across all 18 headline claims | Any Laptop / CPU | **< 1 min** | `python scripts/verify_replication.py` |
| **Tier 2: Full Re-Evaluation** | Re-evaluate matched-budget frontiers, rho sensitivities, and bootstrap contrasts from cached predictions | Standard Workstation | **~ 30 min** | `python scripts/run_matched_budget_frontier.py && python scripts/run_rho_sensitivity.py` |
| **Tier 3: End-to-End Retraining** | Retrain all 5 seeds of Spatio-Temporal MoE, baselines, and cross-site transfers from raw SCADA | HPC Cluster (A100 / Blackwell) | **~ 48 hrs** | See [`docs/DATA_AVAILABILITY_AND_PREPROCESSING.md`](docs/DATA_AVAILABILITY_AND_PREPROCESSING.md) |

### 5-Step Clean Clone Reproduction

```powershell
# Step 1: Clone the public repository at the release tag
git clone --branch tste-submission-v1.0 https://github.com/b1ue13e/windfarm-latent-boundary-risk.git
cd windfarm-latent-boundary-risk

# Step 2: Create isolated Python virtual environment & install dependencies
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Step 3: Fetch release artifacts (Category B evaluation arrays, ~186.5 MB automatically downloaded from GitHub Releases)
python scripts/fetch_artifacts.py

# Optional: developer override with local archive
# python scripts/fetch_artifacts.py --local-archive <path-to-windfarm_derived_artifacts_v1.0.zip>

# Step 4: Run the one-command replication auditor
python scripts/verify_replication.py

# Step 5: Verify manuscript numerical consistency & scientific gates
python scripts/verify_scientific_claim_gate.py
python scripts/verify_tste_number_consistency.py
```

For full details on public data availability, download URLs (Zenodo, ENGIE), preprocessing pipeline, and hash registry, see [`docs/DATA_AVAILABILITY_AND_PREPROCESSING.md`](docs/DATA_AVAILABILITY_AND_PREPROCESSING.md) and [`docs/CLEAN_CLONE_REPRODUCIBILITY_AUDIT.md`](docs/CLEAN_CLONE_REPRODUCIBILITY_AUDIT.md).

## 快速开始

先构建缓存：

```powershell
python main.py preprocess --root-dir .
```

小规模 smoke 训练：

```powershell
python main.py train --root-dir . --max-days 3 --epochs 1 --batch-size 2 --mode moe_phys_full --skip-visuals
```

构建当前 IEEE TSTE 论文 PDF：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build_paper_ieee.ps1
```

打包 TSTE 投稿包前，若换了机器或刚清理过磁盘，先看构建/打包环境注意事项（`rg` 需在 PATH、run 产物 `target.npy`/`mask.npy` 清理后用 `scripts/restore_run_targets.py` 无损还原）：`docs/ieee_tste_transfer_execution.md` 的 “Build And Submission Environment Notes”。

运行一组轻量测试：

```powershell
python -m pytest tests/test_smoke.py tests/test_paper.py
```

## 当前入口

- `main.py`: CLI 主入口，包含预处理、训练、外部数据、证据导出、复现包、论文 guard 等命令。
- `windfarm_moe/`: 核心包，包含数据、模型、评估、机制检验、负控制、复现与论文资产生成逻辑。
- `scripts/`: IEEE TSTE 构建/提交包脚本、论文 guard、历史 Applied Energy 诊断、外部风电证据和云端运行辅助脚本。
- `tests/`: 单元测试与 smoke 测试。
- `paper_tste_ieee.md`, `paper_tste_ieee.pdf`: 当前 IEEE TSTE 主稿源文件与 PDF。
- `paper_tste_supplementary.md`, `paper_tste_supplementary.pdf`: 当前 IEEE TSTE 补充材料源文件与 PDF。
- `cover_letter_tste.md`: 当前 TSTE cover letter。
- `paper_draft.md`, `paper_draft.pdf`, `paper_draft_compiled.tex`, `paper_draft_compiled.pdf`: 源稿/历史 Applied Energy failsafe 与构建产物，保留在根目录以匹配现有脚本默认路径。
- `references.bib`, `IEEE.csl`, `elsevier-harvard.csl`: 当前文献库、TSTE 使用的 IEEE CSL 和历史 Elsevier CSL。

更完整的文件地图见 `docs/project_inventory.md`。

## 数据与输出

- `wtbdata_245days.csv` 和 `sdwpf_baidukddcup2022_turb_location.CSV` 是默认 CLI 会读取的原始数据文件，保留在项目根目录，但不纳入 Git。
- `artifacts/` 存放实验缓存、表格、图片、guard、最终证据包和 reviewer-facing 导出。已有关键证据可被追踪，新生成的大批输出默认忽略。
- `archives/` 存放历史稿件版本、旧云端包和原始 XML 结果。
- `logs/` 存放 LaTeX 辅助文件和检查日志。
- `pagecheck/`、`tmp/` 为本地检查与临时目录。

## 说明

- `Wdir` 默认按“来流方向”解释，尾流方向使用反向流向向量。
- 缺失或负功率目标不会参与监督，但其掩码会保留给模型使用。
- 当前版本主要依赖已有环境中的 `PyTorch + pandas + sklearn + matplotlib + seaborn`。
