# 受控比较实证稿：图表与复核材料交付职责

日期：2026-10-20；模式：`experiment-to-paper / audit`。本交付子任务仅核文件、协议、源码和官方数据元数据，未执行模型、校准、统计重算/重采样、原始测量读取、远端访问或新测量下载，未改论文、V2、阈值或旧资产。主审另行只读回收的既存派生资产以主索引及回收清单为准；原compact范围的缺件不代表远端不存在。本文不重新评判期刊，不新增研究问题。

## 1. 先固定复核层级

| 层级 | 最小材料 | 能核什么 | 不能冒称什么 |
|---|---|---|---|
| L1 展示复核 | 封存JSON/CSV、原字段选择器、比较方向/分母/单位/人口/统计族、来源hash、图表投影记录 | 数字抄录、符号/单位变换、原区间展示与结论是否相符；无需模型或原始SCADA | 不重现动作或区间生成，不认证真实执行史 |
| L2 账目复核 | 已有逐fit、逐策略、逐日C/R/U/V/N和标签/天序；动作级账目还需原动作、shortfall、mask、forecast及坐标 | 日汇总重合成点账、C=R+10U；动作层需逐值核clip、offset、S>R、dt只用一次 | 日总量不能单独证明每个动作/人口正确；原审计报告不是本轮逐动作重验 |
| L3 原区间计算复现 | L2每日总量、原实现、alpha/族/块/种子、draw hash和原环境；若要避免生成新随机数，可提供已存draw索引或原envelope | 现有envelope可直接审判定；要复现生成须另获授权运行原计算 | 有draw hash不等于持有draw字节；数值一致不认证名义覆盖率或未来安全 |
| L4 拟合/推理重现 | 合法取得且身份对应的原SCADA、全部阶段坐标/处理规则、历史训练行、参数/随机种子、依赖环境、上游预测与相应模型或可重训入口 | 另行授权后重训或用原权重推理 | 不把L4作为所有有界实证稿必须现在完成的通用硬门；没有L4就不得声称全链重现 |

固定论文可在L1与已存L2资料上透明写作；是否要求更多材料由实际主张与适用期刊政策决定。**全部权重不是L1图表审计的必需品，也不能因L4未齐自动否定已存结果。**

## 2. V2复核包实际覆盖

`VERIFIED`：`manuscripts/wind_energy_v2/public_review_package/README.md`、`PROVENANCE.json`、`verification_report.json`及旧独立核验报告表明，V2包是Towie2025固定参照/有限族选择、WTB子集选择的**既存统计和判定审计包**。现有69项payload的审核覆盖主q=.95、次要q=.925/15个排除、90/420格、旧图3桥和旧后果账本。其`source_static`是静态片段，不是安装完备的执行流水线。

**不覆盖本稿R的42成本比较，也不覆盖M的154/596族、六格、修正A/B/C与历史采购匹配。** 旧包PASS不能移名为新主线PASS；旧包可保持只读，最多作为明确标记的旧选择器旁证材料。新的材料索引和复核包必须单独命名，不能修改旧manifest制造跨研究覆盖。

## 3. 两研究现有材料足以承担哪些职责

### R：20261018恢复/直接历史开发研究

`VERIFIED`：封存`analyses/decision_information_execution_20261018/evidence/`内有协议、源码、prepared/运行/aggregate收据、原504条配对区间、aggregate和逐fit CSV、恢复MSE/列数诊断及既存动作审计报告。原`compact_evidence_manifest.json`明确是compact metadata export。该范围未包含`.npz`、`.npy`或`.joblib`字节（本轮只枚举文件名，未读数组）。

- **L1可闭合**：主三日42成本族、1/7日已有敏感性、六个成本对照（含必须补回的D−B）、逐fit点值、MSE点值、E=基础40列+恢复1列。
- **L2有限**：逐fit总量和原审计报告可追溯；逐日`block_totals.npz`及逐动作字节在本地该compact包缺失，无法据本包独立从每日或每动作重建。收据中的上游hash证明所声称输入身份，不等于当前可取得这些输入字节。
- **L3只能原区间审计**：可核已有point/CI/族/块/seed，不能在本地compact包独立复现生成。不存在已存D−C直接比较，不得从D−B/C−B两区间推导真实pitch显著优于恢复分数。
- **L4未齐**：原模型、训练索引、prepared和动作的现时远端存活/字节未核，不SSH补查。本稿可明确称“archived-result audit”，不称完整训练重现。

### M：20261020测量六格及其无重训校准控制

`VERIFIED`：pilot导出脚本明确仅导出派生材料，保留既有`selection_blocks.npz`、`blocks.npz`、aggregate `paired_day_totals.npz`、envelopes与审计/收据；模型、fit索引、raw预测、prepared与全动作留远端。controls导出脚本递归保留派生JSON/NPZ但明确排除`actions.npz`，包括`day_totals.npz`、历史blocks/risks、freeze、envelopes和audit。

- **L1可闭合**：两估计器、Original/Common两版本的五成本对照、完整六格C/R/U/V点值、事件资格、修正A/B/C、历史预算漂移和常数增购原代数结果。`summary.json`索引必须按labels定位，不能依赖猜测数组顺序。
- **L2每日点账材料本地存在**：pilot `evidence/results/aggregate/paired_day_totals.npz`与controls `evidence/results/aggregate/day_totals.npz`；另有`instance_metrics.csv`。这些是交付时可包含或投影成CSV的已存资产，本次未读数组或重算。逐动作复核仍仅有原审计报告/身份，不能声称本地已独立动作重验。
- **L3生成所需主要日量与原源码/参数存在**：保存envelope、原draw hash及原统计族可以进行不重采样的L1判定审计；本轮不再生成draw/界限。精确原draw字节是否保存并未由hash自动解决。
- **L4未齐**：没有本地完整权重/raw预测/训练行/全prepared；不能将README写成端到端重现包。共同q=.925是旧预测后的offset配方，不是新训练模型。

### 环境可追溯，不等于可安装锁文件

`VERIFIED`：R aggregate receipt及M两个aggregate receipts均记录Python3.11.16、NumPy2.4.6、scikit-learn1.9.1、torch2.11.0+cu128和Linux平台。M记录CPU、2线程、AMD EPYC7713；controls明确仅CPU归档预测记账，pilot明确未分配GPU。实际计算职责不应误写为GPU训练。收据/部署manifest可做环境摘要；现仓库`requirements.txt`不能未经核对冒称全部历史阶段的精确lock。公开包需另列“recorded execution environment”和“not an installable full pipeline”。

## 4. 四图三表可否直接由旧结果制作

**可以作为L1展示投影，无须补实验或重算区间；尚未生成新图，也未完成最终视觉QA。** 逐项最小字段和限制见`DISPLAY_REQUIREMENTS.csv`。图1为已有协议示意；图2读原154族与Common596族，G翻号并交换上下端点、D保持；图3补D−B，MSE只点值；图4必须分开G与`mean_R=ΔR/Cstar`、`mean_U=10ΔU/Cstar`，相对U−9.5677%仅点值。原图1/2/3/4文件是旧V2选择器图，不能直接充当新稿图。

图表投影仅保留已存数与代数单位变换，不计算新CI、p值、交互项或跨研究合并量。若尚无绘图脚本，新表/CSV索引足以确定绘制输入，但“已有图已完工”仍为UNKNOWN。

## 5. 数据合法路径与身份桥接

本次仅取官方网页/JSON元数据，未请求任何测量文件URL内容：

- 官方[Figshare v2记录](https://doi.org/10.6084/m9.figshare.24798654.v2)及[API元数据](https://api.figshare.com/v2/articles/24798654/versions/2)（2026-10-20核）明确列 **CC BY4.0**，KDD原245日文件`sdwpf_245days_v1.csv`，334304460 bytes，MD5 `8f0cc58c4b0d0fb809824035d05b4e76`。说明区分该KDD245日文件与两年`sdwpf_full`，不得悄换更长版本充作原数据或未见确认。
- 官方组织者[2022答复](https://github.com/PaddlePaddle/PaddleSpatial/discussions/18)准许非商用研究并要求引用。该答复不是CC BY-NC-SA4.0文本；PaddleSpatial软件Apache许可也不自动覆盖任意测量副本。
- **旧`docs/DATA_AVAILABILITY_AND_PREPROCESSING.md`的CC BY-NC-SA4.0条目与上述正式存档不同，不能未经核实照搬。** 本次不改旧文档。新材料索引引用官方存档及其当时许可，并明确适用版本。
- **精确副本映射已闭合。** 主审的`../RAW_IDENTITY.json`记录对原远端`wtbdata_245days.csv`只读取文件大小、MD5和SHA256、未传输测量：334304460 bytes，MD5 `8f0cc58c4b0d0fb809824035d05b4e76`，SHA256 `6cf7613a82c61bb5cf9fcbbf22e3f6c48165fa32021eb6f1905cb2b7af4d7667`。大小/MD5与官方Figshare v2的245日文件一致，SHA256与两研究冻结原始输入身份一致，因而可将该公开版本绑定为两研究原数据的合法可获取路径。不是将SHA256与MD5直接互比，也未下载新文件；未据此认证后续处理、动作、模型或全部计算可重现。

以上包括官方元数据与原副本文件身份桥接，非法律意见或原始数据质量认证。原SCADA不提交Git、不装入当前公开候选包。衍生日总量、动作、代码的发布许可与作者权利需分别确认，不由原数据许可自动全部代办。

## 6. 可公开交付与清理规则

建议候选包只含本稿R/M所需原aggregate/逐fit/日量派生资产、协议公开投影、源码静态快照、收据公开投影、字段指南、source/manifest和不执行研究计算的验证入口。研究原档保持只读。

1. **原件与公开投影区分**：无需清理的结果JSON/CSV做BYTE_IDENTICAL；protocol、receipt、deployment/export manifest含机器root、用户名、主机、PBS细节时另做投影，保存原hash、投影hash、删字段清单和相对路径别名。不得覆写原件或以新hash伪装原执行身份。
2. **不要直接打包整个evidence或logs**：其中存在绝对机器路径和运行环境信息；只列明确白名单。禁止凭据、SSH配置、私人skills、完整`.venv`、缓存、原测量、第三方论文PDF、Git目录、无意携带的失败隐私日志。失败结果的科学信息仍保留，不因清理敏感内容隐藏负结果。
3. **外部复核说明精确**：L1验证不导入模型源码、不联网、不调用旧aggregate/build-all、不生成draw。公开L2日量不意味着L3已运行；L3源码只静态交付须标注。
4. **长期发布与作者责任未授权**：本次不发布、不选最终软件/派生数据许可、不投稿。长期URL/DOI、作者批准及适用权利待确认；此事与现有统计证据是否成立分开。

## 7. 本轮结论

`VERIFIED`：两研究主要有界主张具备L1图表/表格来源；M另有既存每日账目资产可交付；原副本与官方245日文件的大小/MD5和研究SHA256身份桥接已闭合。旧V2包不能覆盖新主线，需单列新材料。原compact范围未提供的R日量/动作/模型和M完整动作/模型/预测，正由主审另行核查既存字节，最终状态看新回收清单；不因发现远端目录而提前认证动作账目。全部阶段精确安装锁和对外发布权利仍未闭合。这些是分层缺件，不以新训练解决，不把未齐升级为“所有结果不可用”。
