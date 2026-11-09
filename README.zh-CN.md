# 风电潜在运行边界与备用风险研究（中文说明）

[English](README.md) · [GitHub 仓库](https://github.com/b1ue13e/windfarm-latent-boundary-risk)

本仓库研究的核心科学问题是：在受限到达信息条件下，当风机关键控制边界局部不可见时，次级 SCADA 后果信号能否有效恢复隐蔽工况信息（如 MPPT 区域 2 与变桨调节区域 3 之间的转换），以及该恢复信息能否为非对称备用决策提供独立价值。

## 稿件状态与范围说明

本仓库包含按 IEEE Transactions on Sustainable Energy (TSTE) 格式整理的稿件工程包：
- 主稿源文件与 PDF：[`paper_tste_ieee.md`](paper_tste_ieee.md) 与 [`paper_tste_ieee.pdf`](paper_tste_ieee.pdf)
- 补充材料：[`paper_tste_supplementary.md`](paper_tste_supplementary.md) 与 [`paper_tste_supplementary.pdf`](paper_tste_supplementary.pdf)
- 投稿相关文件：[`cover_letter_tste.md`](cover_letter_tste.md) 与 [`UPDATED_MANUSCRIPT_CHANGELOG.md`](UPDATED_MANUSCRIPT_CHANGELOG.md)

**投稿状态说明**：仓库内保留的 TSTE 格式、模板和封面信属于已准备的学术稿件工程包，不代表该稿件已被正式投稿或录用。

## 核心问题与架构

- **核心科学问题**：当风机变桨角度遥测缺失或延迟时，机组电气与机械响应信号能否推断出真实的运行工况，并降低非对称调度下的电量不足风险？
- **主要结论边界**：核心结论严格限定为“转换窗口内的局部尾部风险对冲”，而非全场全时段成本降低；详见冻结的科学问题定义文档 [`docs/CANONICAL_RESEARCH_QUESTION.md`](docs/CANONICAL_RESEARCH_QUESTION.md)。
- **核心代码包**：`windfarm_moe/` 包含时空图建模、工况分类与混合专家预测模型。
- **命令行入口**：`main.py` 提供预处理、训练与验证的统一入口。

## 环境配置与验证入口

推荐 Python 3.10 或 3.11 环境：

```bash
python -m venv .venv
# 激活虚拟环境
pip install -r requirements.txt
pip install -r requirements-ci.txt
```

### 运行测试与验证门禁

运行冒烟测试与论文一致性测试：

```bash
python -m pytest tests/test_smoke.py tests/test_paper.py
```

运行轻量级复现核验脚本：

```bash
python scripts/verify_replication.py
```

运行状态与契约一致性门禁：

```bash
python .agents/scripts/verify_gate.py
```

## 关键文档导航

- [核心科学问题](docs/CANONICAL_RESEARCH_QUESTION.md)：状态、信息集与决策边界的形式化定义。
- [证据全景地图](docs/REPOSITORY_EVIDENCE_MAP.md)：实验证据与关键门禁导航。
- [最终裁定报告](RESEARCH_VERDICT.md) 与 [决定性实验报告](DECISIVE_EXPERIMENT_REPORT.md)：核验结论与负结果边界说明。
- [工件清单与哈希记录](artifacts/ARTIFACT_MANIFEST.json)：主要衍生评估数据的 SHA-256 注册表。
- [数据获取与预处理说明](docs/DATA_AVAILABILITY_AND_PREPROCESSING.md)：公开数据集获取与处理指引。
- [纯净克隆复现审计](docs/CLEAN_CLONE_REPRODUCIBILITY_AUDIT.md)：外部独立复现说明。
- [科研契约与工作规范](START_PROMPT.md)：防漂移协议与执行纪律。

## 分支与远端说明

本说明对应远端默认分支（`revision_topjournal_reconstruction`）已检入的代码与文件。本地开发工作树中保留的历史记录、未推送代码与大体积运行缓存与本远端分支互相隔离。