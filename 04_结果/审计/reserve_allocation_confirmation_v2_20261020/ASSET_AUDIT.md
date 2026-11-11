# 现有曝光记录与匹配权重：本地静态核查

2026-10-20。仅查既有本地协议、收据、manifest、源码、任务metadata及文件存在性。未加载pickle/joblib/torch权重，未运行模型，未访问Metis，未读任何新测量。

## 1. 曝光结论：取消独立职责

直接记录：`research_audit/q1_paper_closure_20261019/exposure_record.json`保留用户对Towie2026测量/图表/派生结果查看史的答复“无法确认查看历史”，并明确`confirmation_eligible=false`。既有E1补充路径说明记录/声明须合理支持相关设计未利用该窗；没有要求证明所有公共用户从未看过。

本轮核读该记录、E1路径、旧source_binding、旧2025确认报告及本地导出清单。旧source_binding列2023/24/25；2025旧解封可以证明其当时的职责，不能替2026补设计知情史。没有取得新的参与者说明、可追溯的受保护2026子窗或封存证据。

所以V2对Towie2026的决定是**CANCELLED_AS_INDEPENDENT_CONFIRMATION**，不继续作为待下载即可闭合的确认候选。其曝光事实仍UNKNOWN，不能改写成“已证明看过”。已知其公开入口与文件身份，以及2.1.0与2.0.0测量相同，不提供新的独立身份。

当前没有其他已核实合格的独立窗口。WTB和Towie2025已暴露；既有Kelmarsh/Penmanshiel使用记录不能认证独立备份。未自动选新窗、下载、切月或委托第三方；任何回顾性2026实验也未获本轮执行授权。

覆盖边界：这里核的是已有相关记录，**不是完备的账号/全部作者/所有磁盘访问取证**。曾尝试全工作树包含ignored文件的广泛文件名枚举，因耗时中止；没有以这个未完成检索声称全局没有权重或2026档。最终判断依赖明确旧答复及未取得新资格证明，而非搜索未命中。

## 2. WTB模型：旧任务匹配，不能当新分配器

本地`experiments/state_measurement_pilot_20261020/evidence/results/fits/`有70条任务收据与manifest，其中60条学习模型、10条简单控制。60学习条目为HGB/MLP × F/FZ/O6/OP6/OZ6/OPZ6 × 五实例201—205。收据绑定协议、源代码、训练行索引身份、seed、历史窗口与设备；manifest列`model.joblib`大小和SHA256。

`windfarm_moe/state_measurement.py`的真实特征实现表明：FZ/OZ6/OPZ6只追加当前三叶片均值，不是pitch36。OP6/OPZ6为主a6共同WPQ历史、当期P与P摘要的同任务配对；F/FZ为fresh配对。这些可作为旧WTB有限程序开发分数的复用候选，不能把它们解释成C5条件超额损失模型或Towie/组模型。

举例：HGB/OP6/201对应旧task15，归档模型SHA256为`12b65b0e149bd803a13c47bdf423dd334cc07d3a1bd0828c80c2faa9a82f0559`；这里只引用既有manifest，不声称本轮重新校验了远端模型字节。

本地导出清单明确只含部分派生证据；在这70个索引导出目录中没有模型本体。权重曾归档在Metis旧生产根：`/lstr/sahara/minlpml/junyu/state_measurement_pilot_20261020_v2/results/fits/<task>/model.joblib`。本轮没有远端检查，当前存在性/可读性/环境兼容性是UNKNOWN。以后如复用，须另授权后按已列hash核字节并测试，不能把“有历史hash”说成“当前已可直接运行”。

## 3. Towie模型：参考可定位，当期pitch配对不匹配

本地`analyses/independent_confirmation_execution_20261019/recovered/results/historical/`共550条任务metadata/receipt/manifest，520条有学习模型条目、30条为Persistence。逐条索引见[WEIGHT_INDEX.csv](WEIGHT_INDEX.csv)；此为任务/哈希登记，不是重算模型性能。

`windfarm_moe/information_subset.py::telemetry_columns`在`pitch_available=true`时加入全部已到达pitch历史槽。旧fresh/delay1/2/3/6 pressure模型因而不是V2“a6 WPQ+当期P+只加当期pitch”的身份。`pitch_withheld`虽无pitch，也没有V2完全相同的刷新与P摘要结构，不能直接当配对P端。

**预算参考的有界复用：** 旧`pitch_withheld/WPQ36/HGB`是完整fresh WPQ、无pitch的信息集，可承担与主选择无关的历史P-only预算参考候选；其task为42/87/132/177/222，对应五实例。需要后续证明F/目标/日历及旧offset身份一致，再使用q=.925/.95的2024动作；本轮没有取动作或算B。组参考不由逐机参考相加冒充。

在这550个已审任务中，没有V2当期pitch配对、C5超额损失/组分配器的同身份训练条目；这不证明整个远端绝无相关文件。索引导出目录同样没有权重本体。本轮没有把远端文件名、旧feature模型或已有低资源结果转换成“新任务权重就绪”。

## 4. 实际复用决定

| 资产 | V2用途 | 当前限制 |
|---|---|---|
| WTB60学习实例 | 原始分数、配对身份及已暴露开发流程候选 | 模型字节/当前环境未复核；C5和组目标不匹配 |
| Towie无pitch WPQ36/HGB五实例 | 独立历史预算参考候选 | F/旧q/2024动作身份需后续绑定；未算数值 |
| Towie旧pressure模型 | 旧结果上下文/源码/历史pipeline | pitch历史对象不匹配，不当当前Z |
| receipt/manifest/来源hash | 身份和未来复用检查依据 | 不替代新学习、统计覆盖或独立性 |
| 2026公开元数据 | 记录数据来源与混合控制范围 | 取消在V2中的独立确认角色，不开测量 |

新C5、组合程序和同任务Towie当前pitch配对仍需未来另行授权建立。620条索引中的模型hash是**已归档声明**，实际权重字节本轮验证数为零。复用资产的价值与新主张是否成立分开。

## 5. 可复核文件

[ASSET_IDENTITY_AUDIT.json](ASSET_IDENTITY_AUDIT.json)列统计与边界；[INPUT_HASHES.json](INPUT_HASHES.json)列逐条读取材料身份；[WINDOW_DECISION.json](WINDOW_DECISION.json)明确取消状态。静态核对收据/metadata与其已有manifest绑定，不读取模型或NPZ/测量内容。
