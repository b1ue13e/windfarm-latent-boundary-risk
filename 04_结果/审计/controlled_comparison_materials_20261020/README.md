# 固定受控比较实证稿：复核材料包

本包服务于同一篇稿件：*Measurement Freshness and State Reconstruction for Wind-Power Shortfall Decisions: A Controlled SCADA Evaluation*。不另换主线；本轮没有修改V2、论文、原实验结果、阈值或科学契约，也不投稿。

**本包是现有资产的整理与身份核查，不是新实验或新的统计确认。**最终逐件回收状态以`CURRENT_AVAILABILITY.json`和`RECOVERED_FILES.csv`为准；两个子报告记录的是各自核查时点，不能用旧compact的缺件状态覆盖主索引后来的补件。

## 从哪里开始看

1. `MATERIALS_STATUS.md`：本轮实际闭合范围、仍缺什么、对应主张怎样收窄。
2. `CLAIM_EVIDENCE_DISPLAY.csv`：12项正文／补充职责，逐项对应来源字段、图表、人口、单位、推断族和主张上限。图号只约定未来稿件位置，没有改图或改论文。
3. `study_R/CLAIMS_R.csv`与`study_M/CLAIMS_M.csv`：分别提供12项R原子主张、226项M原字段定位；这些行数不是贡献数或独立实验数。
4. `GAPS_MASTER.csv`：本轮主缺件清单；明确已闭合、仅材料齐备未执行、原来未保存、原比较未生成、现有证据未识别及投稿管理材料的区别。
5. `study_R/MATERIALS_R.md`、`study_M/MATERIALS_M.md`和`crosscheck/DELIVERY_REQUIREMENTS.md`：原compact、冻结执行版本、环境、原任务材料和复核层级。

## 主张—图表约定

| 未来展示 | 固定用途 | 已存展示数据 |
|:--|:--|:--|
| 图1／表1 | 两研究信息操作、合成时钟、分阶段拟合与人口，明确共享天气而非独立复现 | 两协议及冻结文件；来源许可记录；R输入宽度诊断；M环境索引 |
| 图2 | M的当前P／pitch更新比较，HGB／MLP和原／共同校准均保留 | `study_M/display_M_cost.csv`，30行含10项原154族和20项后续596族；后者的Original只作原族之外的敏感性，不能追改154界 |
| 图3 | R的直接历史、恢复分数、两个语义控制、真实pitch D、指定压缩E | `study_R/display_R_cost.csv`，108条原记录；主文过滤pitch_withheld、span3，其他条件／跨度放SI；必须保留D−B |
| 图3小面板／SI | 连续pitch预测诊断 | `study_R/display_R_mse_per_fit.csv`，15个已有点；不补均值、区间或MSE到成本的中介比例 |
| 图4 | 成本近似相近时的采购、短缺、资格和MLP差异 | `study_M/display_M_decomposition.csv`，104条已有字段；mean_U原界是10ΔU/Cstar，不是相对U变化的界 |
| 表2 | 完整六格、原／共同、两个估计器的已存结果和资格 | `study_M/display_M_programs.csv`，84条：60个原逐fit记录和24个后续已存均值；没有重新求均值 |
| 表3／SI7 | 修正A/B/C失败及历史预算转移职责 | `study_M/display_M_routes.csv`四配置；原budget_transfer、frozen、attribution与常数类代数记录 |

六份CSV共345行，均为原值投影，不是新增样本或新统计。原G／D方向保留；未来若画统一成本差轴，只允许明确的符号和单位转换。无已存区间的量只画点，不将两条各对B的区间相减作D−C。

## 复核层级

- **L1：展示复核。** 原JSON／CSV、选择器和逐字段断言可供核对图表数值与文字范围。
- **L2：输入／动作／逐日账目材料。** `recovered/`保存按旧manifest SHA核验的既存数组、索引和模型；本轮核文件身份及数组结构，不重新计算损失／校准或动作账目。旧动作审计保留其原日期和范围。
- **L3：原区间生成材料。** 整理已存日块、原源码、版本、种子、跨度、族、抽样hash与已有区间；不重新采样。原抽样矩阵没有持久化，不能声称数组本体在包内。参数和生成规则可供日后获授权的复现使用，但不等于本轮已实现逐位复现或认证覆盖率。
- **L4：拟合／推理复现材料。** 找回执行版本源码、既存权重和样本索引，并将两研究共用、字节相同的既存派生物理通道阵列只回收一份；没有加载模型、重建特征、重新训练或推理。原始SCADA CSV不复制进本包，改用已精确绑定的合法公开入口；这些材料存在不等于一键端到端复现已验收。

完整性核验和实际运行复现是不同的验收。本轮不把L1闭合说成L4通过，也不以不需要权重的图表复核反过来否定局部经验结论。

## 原数据来源和版本

正式记录为Jingbo Zhou的Figshare v2：*SDWPF: A Dataset for Spatial Dynamic Wind Power Forecasting over a Large Turbine Array*，DOI`10.6084/m9.figshare.24798654.v2`，官方记录许可CC BY 4.0。245日文件的334304460 B、MD5`8f0cc58c4b0d0fb809824035d05b4e76`与两研究使用的Metis原文件一致；其SHA256为`6cf7613a82c61bb5cf9fcbbf22e3f6c48165fa32021eb6f1905cb2b7af4d7667`。

见`data_source/figshare_24798654_v2.json`、`data_source/SOURCE_AND_LICENSE.json`和`RAW_IDENTITY.json`。本轮仅取官方元数据并读取既有原文件hash，没有下载或复制原始测量。旧指南中另一许可标签不沿用到这一明确版本；旧文档不改。

## 原件、复核包与公开的区别

`study_R/original`、`study_M/copies`为小型原件的原样副本，包括三个compact包和原部署包；目录里保留的旧研究入口仅作源证据，**不要执行它们来完成本轮材料验证**。两份`extract_display_*.py`只用标准库投影现有字段，可离线运行，不导入研究模块。

`recovered/`中的大文件不提交Git。它们由旧manifest约束、单列清单，继续保留在本地交付目录。轻量review_core ZIP不伪装成已经内含全部动作的端到端复现包；若向评审交付动作材料，应同时提供对应大文件及清单。

本包尚未上传公开仓库、赋予作者代码新的开放许可或替作者确认数据声明。数据来源许可与版本已核，不等于作者材料已经公开；长期地址、代码／派生材料许可和作者同意仍需投稿准备阶段落实。不用“合理请求可得”替代实际文件可交付性。

## 不变的结论边界

可报告有限程序的成本对照、混合的恢复／真实测量结果，以及校准和R/U/V权衡；保留A/B/C全false、MLP差异、未分离语义和预算漂移。不能写状态独有信息、功率安全替代、普遍状态冗余、真实费用节约或独立确认。R和M不跨表合并、不混族、不借Towie2025的新问题确认身份。

旧科学门禁及77项缓存数字检查仅维持旧一致性；本包的展示字段、来源身份与文件保护另行验证。没有以旧门禁为新主线的期刊价值、bootstrap覆盖率或部署安全背书。
