# 2026-10-19 执行记录（开发研究，持续追加）

## 冻结与审查

- 用户明确要求补更小信息子集、第二估计器、样本量曲线，并落实独立确认数据；允许 Metis，禁止在旧测试反复调到通过。
- research-skill 第一性原理审查将信息不足与近似/估计/优化不足分开。完整22格仅在缺pitch下，另五条件固定六格；嵌套样本不改变训练日历，固定epoch同时增加计算量，不能声称纯样本效率。
- 独立只读源码审查未发现到达时钟、嵌套样本、历史→选档→评估绑定或配对联合统计的致命问题。审查指出的混合计时已在真实重跑前补独立fit/预测时间；不涉及评估结果或参数选择。
- 代码提交52a75ffa、b533d3c、18c9efc3；数值源码实际冻结18c9efc3，精确工作文件字节包SHA256 `9b0ba9e28c8e2583ef7be9cba2eaeb709625c5143f7271f8ee872f041f62c9d5`。后处理独立冻结7ade6743，包SHA256 `ae70e75713f3ad3008ca2cc6ffe36e6c1b972997000ffdc4e393a38bb1bde652`。
- 主格22输入×HGB/MLP×4预算×5seed=880学习拟合；另外五信息条件六输入×两估计器×两预算×5seed=600，合计1480学习拟合，另30持续性worker。总550历史worker，所有输出保留。
- 测试中一次Windows默认编码导致receipt路径读错，已显式UTF-8修复；属于合成流程测试失败，未读评估结果。

## 部署/配额失败及保留

- 首个精确字节部署清单误用Windows分隔符，Linux校验失败；该版本没有提交数值作业，失败源包与目录保留。
- NFS目录首轮244671预检16项通过；244672 Common/HGB完成，244673 WPQ36/MLP在360k阶段退出。依赖244674—244677未推进。未读取该轮开发评估。
- 后续同目录新写入直接返回 `OSError [Errno122] Disk quota exceeded`；NFS用户quota约35GiB，而df仍有14TiB空闲。原始失败stderr因写入/回传受阻没有完整取得，不能追认为已经定位到原失败精确操作数。
- 首轮不透明数据下载仅留下113246208字节2023.zip.part；没有完整年包校验或测量解析。以上原结果、失败、部分文件全部保留。
- Lustre quota查询无显式用户限额，创建/写入18字节探针成功后只撤销该探针。数值源码和超参完全相同，重新部署到 `/lstr/sahara/minlpml/junyu/information_subset_20261019_18c9efc3_lustre`；没有移动或删除旧数据/结果。

## Lustre作业链

- 244678环境预检；244679 Common/HGB和244680 WPQ36/MLP真实历史检查。244680四预算均完成，360k该组件耗时84.72995秒；该数是执行时间，不是决策收益。
- 244681[].cm：550历史任务，最多12并发×2CPU；已启动，完成数以后续快照为准。1480学习拟合不能由已提交作业推定完成。
- 244682.cm：所有历史成功后冻结共同q选档。风险上限.10、五档offset、rho10、完整格均固定。
- 244683[].cm：选档后评估550任务。
- 244685.cm：评估后独立重建存储raw+offset的所有日块数组，预期45300项精确检查。
- 244684.cm原已依赖评估，现调度依赖改为afterok:244685.cm；先通过独立记账再联合统计。数值源文件未改。
- 244686.cm：汇总成功后生成全部表和样本曲线、风险曲线，再导出逐成员校验的紧凑证据包。图中保留历史未合格点；成本带为边际区间，决策使用配对联合界。
- 全模型、raw预测、fit索引仍留Metis；紧凑包只回传元数据和日块，不能冒称本地复算未回传动作。

## 独立来源

- `experiments/independent_confirmation_20261019/source_binding.json` 在测量取得前绑定官方Zenodo22662930/v2.1.0、2023训练/2024校准/2025封存及官方大小/MD5；绑定SHA256 `4df5eca98530dc2777c92b83213fb0342829d7f926694615363b57cd5c2ddd76`，9份官方元数据MD5通过。
- NFS下载失败后，相同获取程序和绑定在Lustre新目录重新启动，只作网络字节流/哈希；2025不解压、不列ZIP或解析CSV。
- 真正有效获取目录为 `/lstr/sahara/minlpml/junyu/hill_of_towie_confirmation_20261019_18c9efc3_lustre`；完整下载与质量资格尚待完成。
- 一次性I/O依赖helper在2023/2024 receipt齐全后提交PBS资格审计。审计入口拒绝2025，只检查前两年W/P/Q/pitch字段、21节点、UTC期末时刻、重复/缺失坐标，保留负有功，不按工况剔除。可能返回DATA GAP，不自动改年。
- 2023 AeroUp、2024 TuneUp已记录且保留。2025解封须完整分析/历史候选包冻结，当前未解封。此独立外部场站不是原WTB E07延续数据，E07仍未激活。

## 认识论边界

VERIFIED：源码、软件测试、Metis环境预检、两个真实历史检查、配额写入故障、完整批次已经启动及源包身份。

UNKNOWN：全部拟合完成、联合风险/成本结果、各条件最小候选、样本曲线是否稳定、完整独立年包是否取得和实际字段资格、独立确认效果。

当前不改变科学契约、原无解结果或历史来源缺口；不以一致性门禁通过认证新方法。运行结束若无解或曲线未稳定，原样报告。


## 后续执行追加（不追改上文状态）

- 原12并发调度上限改16（32CPU），只改调度吞吐，模型、样本、风险/效果阈值和数值源码均不变；Metis保存scheduler_capacity_change.json。
- 另在本轮评估244683尚为H状态时，冻结NECESSITY_ADDENDUM.md及只读派生审计ee836206，job244688依赖原aggregate。先验证充分，再要求排除所有严格更小候选；排除不了则MINIMUM_UNRESOLVED，不能把最小已认证候选叫真实最小。该审计不改原训练/选档/主统计，联合族已有全部pair lower无需新p值族。只限condition/budget/epsilon和有限家族，未穷尽常数/物理/其他估计器。
- 全三年官方年包已经完整取得：2023=1512000259B，SHA256 e65f7acd65664584e5b72e4ad7ccd4c0f0af4ad68f618b8cf0b4e5c1f4a69521；2024=1557682397B，SHA256 b6bb540e3d2fcc2cff8756d96ef4155037b1cc41b284e6249b41054f4e50fbc3；2025=1596220683B，SHA256 cd439de7bf8e297dd8422d5c93eda04785c56e3861be8d2a79f403ac39b873ee。三者官方MD5/大小均通过；2025.zip未列成员或解析。
- 获取receipt的NOT_PARSED/measurement_contents_opened=False仅记录获取进程行为；2023/24随后由独立PBS读取，不应把该旧获取标记作为当前全项目“从未打开”断言。
- 244687实际历史字段资格失败：Duplicate time/turbine coordinates。失败源、receipt/log保留，原严格raw行键唯一条件仍为失败，未改门禁。
- 244689只读重复诊断完成：两表各自2023重复230组、2024重复231组；全部跨月，每个消费字段同值（含NaN一致），四表0冲突。诊断不删行，不自动资格通过。
- 在2025.zip仍封存时新增IDENTICAL_COPIES_ADDENDUM.md、严格一致副本适配器2885aac1，244690只处理2023/24：同chunk、跨chunk/月/年任何消费字段冲突均整批拒绝；只在证明一致后映射为唯一物理坐标。旧严格QC失败不覆盖，不均值化冲突或选择有利行；原ZIP不改。该适配器独立只读审查未见fatal。结果以后续receipt为准，不把提交当资格通过。


## 最终本地核验与回读限制（本次turn）

- 本地96项相关软件测试通过；两项既有科学/数字门禁输出保留在analyses/information_subset_execution_20261019/gates_final/。它们检查既有一致性，不认证新风险/最小性。
- 最后成功回读显示历史清单321/550；全三年包完整、官方MD5/大小通过，244689四张year×table诊断全部0消费值冲突；244690已提交，尚未取得最终完成receipt。
- 随后本地metis.niu.edu解析失败；系统DNS、指定DNS均超时。未修改SSH信任或接受新主机密钥。已提交PBS在Metis独立执行，但不得猜测最新完成/成功结果。
- 回读恢复后先核验244690来源坐标结果、全网格完成和独立动作/统计/必要性/导出；若失败保持原结果，不修改阈值或重选旧测试。2025模型确认仍未激活、文件未解析。


## 2026-10-19 — final readback and claim narrowing (no numerical rerun)

Metis connectivity restored. Jobs244681/244682/244683/244685/244684/244686/244688/244690 returned complete; historical/evaluation550/550 each and45300 exact action-array checks. Compact recovery42157355B SHA256 c375cf3e327aff65d30e148a4b009b8bea08c773874be410c6bf6abc5f30c3a0; all4461 manifest members verified locally. Necessity57689B and source-metadata14669B outer checksums match; source14 members and four necessity input bindings verified. Adapter actual remote output hashes match its manifest. No refit, bootstrap rerun, q/epsilon expansion or numerical code change.

Primary3-day2%:28/28 cases contain risk-qualified policies,0 identified sufficient sets. Prespecified5% primary pitch-withheld PQ1/HGB/q0.925 succeeds at four budgets, but13/15/15/14 smaller alternatives remain unresolved. Across420 dependent decision cases,367 lack a sufficient candidate and53 lack minimality exclusion;0 minima identified. The paper/contract now report bounded sufficiency and explicit nonidentification, not a deployment hierarchy/minimum map. Earlier35-policy diagnostic remains separately scoped.

244690 historical coordinate preparation is qualified, zero consumed conflicts; the raw-row-uniqueness failure is preserved.2025.zip remains unlisted/unparsed. Independent model confirmation NOT_EXECUTED; complete historical program/selection package must be frozen before unsealing. E04/E07 and old source gaps unchanged. Full receipts, claim map, report and manuscript-build verification: `analyses/claim_revision_recovery_20261019/`.
