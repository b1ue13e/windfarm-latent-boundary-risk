# 历史来源缺口冻结与证据使用边界

日期：2026-10-18。状态：**FROZEN GAPS / NOT SCIENTIFICALLY CERTIFIED**。本文件补充现有审计的解释边界，不修改 [科学契约](SCIENTIFIC_CONTRACT.md)、原始结果或独立科学审查状态。

## 冻结决定

用户确认原 grokking 租用算力云实例已销毁，并要求停止追查。实例状态标为 **USER-CONFIRMED**，不是本次远端检查结论。停止该远端、替代地址或新主机密钥的追查，不再请求新指纹。本次仅整理已有证据，没有网络访问、模型推理、训练、校准、重采样或结果重生成。

不能闭合的来源保留为 **UNKNOWN / NOT CLOSED**，不补写为通过。“冻结”固定本次证据边界，不证明其他离线备份全球不存在。日后若实际取得同时期留存，只能另建追加审计，不能覆盖本记录或倒填历史凭证；本次不启动补证实验。

## Claim–Evidence 使用表

| ID / 原子判断 | 证据与认识论状态 | 仍可使用的范围 | 不能据此认证的主张 |
| :--- | :--- | :--- | :--- |
| H1 旧发布包身份闭合 | [勘误审计](../analyses/legacy_release_hash_audit_20261018/REPORT.md)：ZIP、实际两成员、散文件与历史清单一致，VERIFIED | 指定字节资产的分发身份、文档勘误和输入绑定 | 原训练真实性、首次生成至首份完整哈希记录的连续性、无选择性报告 |
| H2 生成事件部分可追踪 | [源码/日志审计](../analyses/legacy_generation_lineage_audit_20261018/REPORT.md)：残差成功日志、后验首次保存及失败日志、未提交入口恢复，VERIFIED（记录范围） | 区分首次提取与后续读缓存；HEAD 只是仓库基线 | HEAD 或后期提交等同首次实际执行版本；完整依赖/权重/输入/输出现场绑定 |
| H3 首次成本断言失败 | [记账审计](../analyses/legacy_posterior_accounting_audit_20261018/REPORT.md)：保存早于失败且失败路径不回写缓存；现存数组和已存表的数值诊断，VERIFIED | 现存数组的记账诊断；运算精度是历史失败的 INFERRED 候选解释 | 历史精确误差已恢复；缓存概率语义或全部下游结果自动有效 |
| H4 残差坐标与内部关系 | [对齐审计](../analyses/legacy_cache_alignment_audit_20261018/REPORT.md)：显式 anchor/目标/掩码对现存缓存精确对应，短缺公式字节一致，VERIFIED | 相对指定缓存的时间/节点列对应、有效支持与字段内部一致性诊断 | 真实日历/设备时钟、原模型输入现场或后验逐值历史坐标已认证 |
| H5 后验顺序与掩码 | 同一审计：源码规定时间优先/节点次序；概率包无坐标；消费端 val/test 掩码不对称是 VERIFIED 源码事实 | 预期顺序为 INFERRED；可报告支持差异，其决策影响 UNKNOWN | 长度、概率范围、CRC、汇总匹配证明逐值坐标；统一掩码后替换原结果 |
| H6 辅助预测与旧 yhat 差异 | [差异审计](../analyses/legacy_yhat_difference_audit_20261018/REPORT.md)：十组全部非精确；辅助 batch16、残差源码 batch64，VERIFIED | 差异量级、已查显式坐标及当前权重/输入副本身份；浮点路径为 INFERRED 候选 | 唯一归因于浮点；两个原执行权重/完整输入相同；辅助预测能精确替代旧 yhat 或认证后验坐标 |
| H7 原辅助评估执行来源 | [grokking 审计](../analyses/grokking_legacy_execution_audit_20261018/REPORT.md)：此前严格主机校验在认证前拒绝，限定本地检索未复得原凭证 | 保留拒绝、检索范围及用户销毁说明；完整来源 UNKNOWN | 已进入原文件系统确认日志不存在；当前端点是原实例；原环境和权重/输入绑定已恢复 |
| H8 后期独立绑定包和切片 | [C-201 闭合](../analyses/e04_c201_exactness_20261018/REPORT.md)、[完整四策略比较](../analyses/e04_complete_policy_comparison_20261018/REPORT.md)，VERIFIED（指定 bundle/重放/描述性范围） | 完整五种子日块闭合、风速/爬坡/过渡切片及原失败记录 | 旧包缺口一并否定新包；新包倒填旧包来源；事后切片推出物理因果、系统性欠校准或部署安全 |
| H9 E04/E05 负结果 | [PROJECT](../PROJECT.md) 及其引用的原选择/诊断文件，VERIFIED（既定口径） | 保留 NO FEASIBLE POLICY 和逐抽样聚合约束的 64.64% 无解频率 | 基线已认证最小充分；64.64% 是未来工业失败概率或完整 UCB 选择器嵌套重采样频率 |
| H10 E07 确认性资格 | [数据可用性审计](../analyses/e07_data_availability_audit_20261018/REPORT.md)、[原协议](../experiments/E07_history_only_recalibration/protocol.json) | 未执行预注册草案和数据缺口记录 | 已激活、重校准有效、旧测试能再次作确认性证据 |

逐项 VERIFIED 不等于整篇科学认证。文件/执行身份、统计有效性、因果解释和部署资格分别判断。总体仍为 **NEEDS-WORK / NOT SCIENTIFICALLY CERTIFIED**；[2026-10-17 证据冻结](EVIDENCE_FREEZE_20261017.md) 对候选重放、撤回及有界外部证据的限制继续有效。EXP-01 被撤回/替代的旧分支不恢复资格。

## 固定资产与保留的 UNKNOWN

旧 ZIP SHA256 为 `cf90924b1fead36317addabfcbee6aa6236bebc29889f8ce5dfd57466fc7fc22`，实际只有两成员：

| 成员 | 字节数 | SHA256 |
| :--- | ---: | :--- |
| `artifacts/fixed_forecast_residuals.npz` | 173410167 | `b05b3751f45e611e073d1dfe4c4545b9775ca625e3c76e85558328cfc30a49a9` |
| `artifacts/matched_budget/cached_posterior_probs.npz` | 22475033 | `d40f0ddbaee7f4a2c89dbacdfb05be0a858897f1ce02c648b989fb8a8037cbca` |

当前 E04/E06 的 175752841 字节残差 SHA256 为 `50499806cf6103d869086318858d9eb2cde89f99dac43c65917cc423572330a1`，不能与旧分发资产混用来源。哈希证明指定字节相同，不证明生成真实性或无选择性报告。

冻结为 UNKNOWN 的缺口包括：原生成时完整输出/依赖/权重/输入/环境联合绑定；旧后验逐值实际历史坐标；十组预测非精确差异的唯一原因；原成本断言失败的精确操作数和环境；val/test 掩码不对称对校准/决策的影响；原实例备份可用性及准确销毁时间。当前权重与后期清单相同、残差生成前同会话的 Python/Torch 记录，均不填补原辅助评估现场。历史 C-201 失败没有原失败后验，其具体触发亦 UNKNOWN。

## E07 与门槛原样封存

E07 仍为 `DRAFT_NOT_EXECUTED_PENDING_ACTIVATION_MANIFESTS`。原策略包、历史校准包、未来采集规范三项激活哈希及确认性数据清单为空；已确认合格新窗口数为零。已查 WTB 止于 Day245，未取得原 issue35280–40319 和 padding40320–40343 的新来源；未查位置不能说成不存在。

原 $q^*=0.90$、$\alpha=0.05$（单侧 95% UCB）、$v_{\max}=0.10$ 及零成本/违约差容限不变。旧测试是已查看历史材料，不复用为新确认性证据。本次不绑定替代数据、不激活、不校准，也不以新实验补造历史。未来研究不追认历史来源。

## 悬空断言处置及论文表述

现行指南撤回“全部主张通过”“所有输出哈希保证无篡改或选择性报告”和统一 GPU/软件环境声明。六份旧文档逐字节快照见 [输入清单](../analyses/historical_provenance_freeze_20261018/input_manifest.json)。历史 `19/19 PASS` 等报告保留，只表示当时脚本范围的检查，不作为当前科学认证；既有门禁通过亦不填补 UNKNOWN。

可用于英文稿的有界表述：

> Archived arrays support bounded checks of file identity, stored accounting and diagnostic contrasts. Historical logs and recovered entry-point text do not jointly bind the original weights, complete inputs and numerical environment. The original rented compute instance has been reported destroyed, and its investigation has stopped. All ten auxiliary prediction comparisons remain non-exact, and the probability-only posterior archive lacks direct per-value coordinate provenance. These assets therefore do not certify end-to-end reproduction, causal attribution or deployment safety. Independently receipt-bound later bundles retain only their separately audited scope. E07 remains inactive, with no eligible unseen confirmation window bound.

## 本次交付与核验

仅更新文档；原结果、旧日志、旧审计、发布包和协议不改。六份编辑前快照与 486 个受保护文件的哈希见 [输入清单](../analyses/historical_provenance_freeze_20261018/input_manifest.json)，只读核验和既有门禁结果见 [verification.json](../analyses/historical_provenance_freeze_20261018/verification.json)。门禁检查既有规则与数字一致性，不等于科学认证。更新的是稿件源文件；已生成 PDF/旧投稿包未重建，不能视为已同步。
