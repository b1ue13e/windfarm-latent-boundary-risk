> 审计日期：2026-10-19，Asia/Shanghai。原始结果、正式稿件、科学契约、原门槛均未修改。VERIFIED=本次直接文件/算术核验；SUPPORTED=有界支持、未全链重现；TENTATIVE=待检解释；CONTRADICTED=有明确反证；UNKNOWN=缺少证据。

# 项目全景与实际审计覆盖

本轮将“文件清点”“内容检查”“数值复核”“原数据端到端重现”分开计量，未声称已独立重跑整个项目。全文件元数据见 `all_accessible_files.csv.gz`；研究资产子表见 `research_assets.csv`；扫描异常见 `inventory_summary.json`。环境、Git对象和技能包只清点路径/大小，不作为科研内容覆盖。递归不跟随链接或junction，无法访问的路径单独登记。

本轮最终清点 **206,614文件、207,866,433,819字节**；其中按顶层排除环境/技能/Git的研究资产 **56,486文件、128,058,498,273字节**。扫描无OS读取异常，1个junction未跟随：`artifacts/raw_replay_external_20261015/penmanshiel/cache`。这是一次非原子元数据快照，期间软件测试可能创建pycache；不保证磁盘此后文件数永远不变。Git清点前快照有476个可达提交；根WTB原CSV不在当前Git跟踪列表。

另见`asset_readability.csv`与`asset_readability_summary.json`：对研究JSON做有界语法解析、CSV仅首记录、NPY/NPZ仅数组头；所有格式错误逐项列出，其余二进制/文本明确标为未解析。不反序列化torch/pickle，不以可读性等同科学有效。

## 1. 原始问题、技术构成与后续问题变化

历史目标是用SCADA次生信号恢复MPPT/pitch边界，在变桨不可见或信息延迟下改善下行备用筛查。方法包括STGQ/时空图、多任务状态监督、MoE、后验条件分位数、物理规则、局部分箱、混合策略和校准。核心风险是将状态恢复、风险形状变化、实际决策收益混为一谈。

最新独立任务已改为：给定共同已发布预测、未来短缺和到达信息，比较直接HGB/MLP分位数政策与持续性控制；先按历史选q与recipe，再冻结，独立年份确认。缺pitch完整格为Common加W/P/Q的非空组合×1/6/36步，共22子集；其他五压力条件只用6子集。共同预测使用W/P各36步，clock和ID共用。它不是原图模型端到端重放，不能由低资源结果得出风速传感器可删。

## 2. 资产与实验对应表

|资产族|内容/实际核查入口|状态与证据用途|
|---|---|---|
|生产实现|`windfarm_moe/`、`src/`、`scripts/`、`main.py`、`tests/`|最新实际入口、输入、损失、选档、推断与必要性已读；未逐行审计所有旧脚本|
|原SCADA/缓存/权重|根WTB CSV、`data/`、`artifacts/`、`experiments/E06/`等|本轮清点；最新完整年包/动作/权重主要在Metis，本地仅compact证据，未新访问远端|
|旧状态/通道/物理诊断|`artifacts/raw_replay_20261015_v2/`、旧`artifacts/`|修正版CSV与旧版本分开；旧h6索引/尺度/分母错误不可跨版沿用|
|E01外部迁移|`artifacts/metis_external_deterministic_20261015_attempt1/audit_report.json`|当前限定外部证据；v4物理窗口错配INVALID，corrected-v2不恢复|
|E02零特权|`artifacts/raw_replay_20261015_v2/exp02/results.csv`|60行修正结果；旧p字段/判决方向错误不得当现行结论|
|E03异步|`artifacts/raw_replay_20261015_v2/`、`artifacts/exp03_async/`|存在已撤回初始值/完整轨迹问题；本轮未重新重放完整到达过程|
|E04/E05/E06|`experiments/E04/results/e04_v2/`、`experiments/E05/`、`analyses/e04_*20261018/`|保留NO FEASIBLE POLICY、64.64%诊断频率及当前五种子切片；旧来源缺口仍在|
|E07|`experiments/E07_history_only_recalibration/protocol.json`|未激活；新WTB日246—280缺资格绑定；不是模型性能负结果|
|10月18日信息开发|`analyses/decision_information_execution_20261018/evidence/`|30/30任务；新增信息B−A较大、状态分数C−B很小，开发性证据|
|10月18日风险前沿|`analyses/risk_cost_frontier_execution_20261018/evidence/`及`secondary_evidence/`|历史选档主要失败与结果知情全35策略次要诊断分开|
|10月19日WTB输入格|`analyses/claim_revision_recovery_20261019/`|1480学习拟合、30持续性worker、420相关案例；无最小性识别|
|10月19日独立确认|`analyses/independent_confirmation_execution_20261019/recovered/`|5037成员逐项哈希；550历史+550确认日块×5q；主要与次要分开|
|稿件/图表/发布物|根Markdown/TeX/PDF、`manuscript/`、`figures/`、ZIP、`standalone_ieee_package/`|用于核对叙事与时间版本；本轮未改稿、未重新渲染所有历史PDF|
|文献|原核验矩阵、`research-manifest.json`；本轮`literature_matrix.csv`|新增13篇有核验层级的主文献；弃用旧伪造brief和错误DOI矩阵|
|Git历史|`git_history.tsv`|全部可达提交元数据；定点追踪冻结提交24153f8、后续结果f2a33f57/63b49590；未声称逐提交重放|
|替代工作流/未跟踪材料|`00_Planning/`至`06_Review/`、`.agent_state/`、备份与scratch等|均纳入清点；不能自动视为现行协议或可信结果|

## 3. 版本、污染与尚未完成资产

1. `docs/EVIDENCE_FREEZE_20261017.md`指定当前强基线候选为+445,639 kWh；+523,044只是历史版。最新候选仍待深层审计，不能因本次新任务通过而追认。
2. `docs/EXP01_INVALIDATION_20261015.md`和`REPLAY_CLAIM_DISPOSITION_20261015.md`撤回v4外部结果。错误窗口产生的正/负方向都没有科学解释价值。
3. `experiments/E06/remote_j02/e01_output/`包含AdamW/Split-Muon/weight_norm等异题优化器结果。登记为MIXED_PROJECT，不纳入风电实验证据账本的有效结论。
4. 旧grokking已销毁且停止追查；当前本地哈希匹配不恢复原生成时权重/输入/后端绑定。E07保持未激活。
5. PROJECT早期H2“Refuted”和48.4%中介节约与当前修正版/契约不一致；详见03。最新记录中的旧“未完成”是时间快照，不得与当日后续完成状态混读。
6. Hill of Towie 2025已经解封并被使用；不能再次作为未查看确认。主确认q.95与次要q.925身份永久分开。

## 4. 内容覆盖的具体分母

- 最新独立compact包：5037/5037导出成员大小/哈希核验；历史与确认1100/1100日块文件、5500个worker×q点账本，非5500次独立训练。
- 确认点统计：550/550任务，365同一天气日、1,059,248同一目标总体；90/90保存界的案例逻辑与15/15更小排除见证复核。
- 当前确认原数据→权重→逐样本动作完整重现：**本轮0次**。compact包不含所有必要大文件；receipt只能支持其绑定身份，不能替代实际原值读取。
- 旧实验：针对关键CSV/JSON和撤回记录分层抽查，详细已读清单见`working/discovery/read_manifest.json`。没有对每份旧checkpoint、每个notebook、所有图PDF、Git历史二进制或所有缓存进行内容审查。
- 文献：13篇接受记录，全文/摘要/官方metadata层级不同；不是穷尽系统综述。完整读证据与访问失败见`working/novelty/NOVELTY_REVIEW.md`。
- 未挂载Metis、已销毁grokking、未解码二进制/大缓存与junction外部对象均非已审覆盖。对模型真实性的总覆盖率不能从文件数量推算。

`02_experiment_ledger.csv`是分层账本：5500个最新worker×q点行、旧族汇总/状态行和额外机器CSV行在`Notes`明确粒度，禁止相加为独立实验次数。


## 本轮最终覆盖与读取异常

元数据清点206,614文件，研究资产56,486文件，目录读取错误0，未跟随junction 1。结构可读性状态如下；它们不代表科学有效性或逐行内容审查。

|状态|文件数|
|---|---:|
|NOT_CONTENT_PARSED|18,398|
|JSON_SYNTAX_READABLE|17,328|
|CSV_FIRST_RECORD_READABLE|4,940|
|READ_OR_PARSE_ERROR|2|
|NOT_PARSED_SIZE_BOUND|1|
|NPZ_ARRAY_HEADERS_ONLY|2,342|
|NPY_HEADER_ONLY|13,475|

逐项读取/格式错误见`asset_readability_summary.json`的errors和`asset_readability.csv`。两项错误是同一官方字段说明CSV的两个副本在UTF-8下解码失败；后续CP1252可逆解码/逗号解析已通过，原失败和原字节均保留，见`readability_encoding_followup.json`；这不证明原作者唯一编码。首次误用分号的诊断也单独保留，不作为成功解析。超过50MiB的未全文解析文件是`analyses/claim_revision_recovery_20261019/evidence/study/results/aggregate/results.json`，本轮读取其420案例派生表，未冒充全文复算。其余未内容解析文件均显式登记，特别是权重/torch/pickle不反序列化。完整原始科研端到端复现本轮仍为0次。
