# Reviewer P：实用价值独立审计

日期：2026-10-19。最终实际净收益等级：**UNPROVEN**。这不是否定C1数值，而是C7的资源节约和真实决策收益尚未闭合。限定研究协议内的输入约简证据具有中等应用研究价值；不能据此把实际净收益评为MODERATE/HIGH。

本审计使用research-skill的AUDIT/RESULT路径。完整读取项目约束、当前论文及冻结C1—C8；独立检查features、point_features、learner、predict、historical、evaluate、metadata、receipt和存档日块。未读取其他本轮reviewer输出，未训练、推理、重采样、访问远端或修改原资产。所有数字来自所列存档或明确标注的算术推导。未引入新文献或有关真实运营实践的外部事实断言。

## 1. 谁可能受益，已经观察到谁

**VERIFIED**：实际任务是固定共同预测后的、机组级短缺代理备用层；不是重新设计发电预测器。共同预测在issue前六步发布，使用截至issue−6的W/P各36个历史值，预测issue+6。备用层接收同一预测、clock、ID和新增遥测。对所有候选固定未来目标及finite-target mask。

**INFERRED**：可能的使用者是已有共同预测服务、却须额外维护备用模块输入接口的场站EMS/聚合侧软件团队；只有独立备用接口确有复制、授权、存储或维护负担时，少接输入才可能产生可计量节约。这是一个条件适用场景，未被实际用户访谈、接口合同或部署记录验证。

**UNKNOWN**：真实使用者、其目前工程做法、额外通道接入收费、现有缓存复用、网络payload、OEM接口权限、arrival/publication日志和维护工时均未观测。若同一进程已经持有W/P历史，P1减少的是下游读取列数；不能推断上游停采W、功率传感器减少或原始数据总传输减少。

## 2. 输入宽度与实际实现资源

|量|P1/HGB|WPQ36/HGB|认识论边界|
|---|---:|---:|---|
|备用层新增物理通道|P：1|W/P/Q：3|功能接口定义；P仍已在上游使用|
|备用估计器pass|1|1|不含共享点预测pass|
|进入learner的原始列|5|112|forecast、sin、cos、ID共4列，再加P1或3×36|
|单行float32原始张量大小|20 B|448 B|理论数组大小，不是线上报文大小|
|原始列减少比例|95.5357%|参照|不是sensor/端到端bytes/FLOPs节约|
|HGB变换后精确输入宽度|UNKNOWN|UNKNOWN|SimpleImputer(add_indicator=True)取决于fit时缺失列；回收包未导出model.joblib|
|MLP变换后宽度|10|224|standardize明确拼接同宽缺失指示列|
|共享上游原输入|72个W/P历史值|同左|不能删掉或归零其成本|

**VERIFIED（源码与shape算术）**：现有`stage_data`在选择子列前，对每个recipe统一构建4个公共列+4通道×36历史=**148列**的完整float32 X，包含后续模型不用的列。2025 forecast形状为52,553×21，共1,103,613行，X本体为**653,338,896 B（623.073 MiB）**。这不等于进程峰值内存。训练表达式先执行`fit['X'][indices]`再取cols，360k行第一份索引拷贝仍为**213,120,000 B**，P1和全量均如此。故当前生产脚本没有兑现与5/112同幅的特征构建/大数组内存下降；若未来修改实现才可能兑现，当前未测。

输入依据：`windfarm_moe/independent_confirmation.py:21`、`:32`、`:49`，`windfarm_moe/information_subset.py:22`、`:60`，`scripts/run_independent_confirmation.py:251`、`:299`，`scripts/run_decision_information_development.py:202`。HGB nominal q=.90，100迭代、最多15叶、min_leaf50；随后历史offset进行q定档，q=.95不是重新拟合的HGB量化头。

## 3. 存档计时、CPU与内存

下表是pitch_withheld的五个冻结实例均值；完整范围、节点与逐worker数据见`worker_timing.csv`。历史fit_seconds是真实记录的model.fit区间；它没有包含全部特征构建、offset拟合或上游点预测。历史与evaluate阶段时间来自receipt UTC起止。

|实际存档recipe|fit均值(s)|完整历史阶段(s)|完整2025 evaluate阶段(s)|纯predict计时|
|---|---:|---:|---:|---|
|Common/HGB|1.583|5.795|5.019|缺失|
|P1/HGB|2.500|8.665|5.347|缺失|
|WPQ36/HGB|34.679|42.532|6.797|缺失|
|P1/Persistence|0|2.168|3.101|缺失|
|P1/MLP|30.232|32.673|2.988|缺失|
|WPQ36/MLP|131.922|136.784|5.737|缺失|

**VERIFIED**：P1/HGB fit范围1.675—3.576s，WPQ36/HGB33.319—37.122s；均值差32.179s（92.790%）。完整evaluate均值差1.450s。**INFERRED**：该输入缩减很可能降低固定HGB训练负担。**UNKNOWN**：不能把不同节点、并发调度下的存档差认作受控硬件benchmark，更不能把evaluate总时间报为单次推理latency。evaluate还包括输入验证、joblib加载、完整148列构建、5档日块记账/独立检查及压缩写出；一次年度批处理与在线逐条服务不同。

环境receipt记录CPU only，Python3.11.16、numpy2.4.6、pandas2.3.3、sklearn1.9.1、torch2.11.0+cu128（CUDA build12.8不表示使用GPU），Linux及cn节点。PBS每worker请求2 CPU、16GB，线程上限2。**实际每recipe cput/峰值RSS未留存在最终array状态中，CPU型号亦UNKNOWN**。`final_job_status.json`仅给准备/解封/汇总等整作业的测量，例如prepare cput44s、mem918012kb、wall32s，unlock40s/813028kb/38s，aggregate92s/966908kb/113s。这些不能归为P1线上资源。不能以16GB申请量声称实际占用16GB，不能以Torch CUDA版本声称GPU提速。

预算意义：在此固定CPU小树任务内，单次离线fit差约32s，现有证据不支持新增大型模型或昂贵GPU来解决“节约是否抵偿溢价”；实际工程成本主要未测，而非缺少更大算力。

## 4. 成本溢价、风险与最差案例

**VERIFIED**：从原blocks独立汇总，P1/HGB/q.95与WPQ36/HGB/q.95每实例相同1,059,248有效目标；五实例均值67.020403与66.644430，差**+0.375973 kWh-equivalent/有效机组间隔**。主joint approximate ratio区间为**[+0.357468%, +0.770827%]**，点值**+0.564147%**。它满足预设2%固定参照容限，但成本上升，5/5实例均上升（各+0.4216%—+0.6656%）。

对观测2025的机组级代理求和，五实例年总溢价均值为**+398,248.517 kWh-equivalent**，范围+297,796.751—+468,904.749。这是`reserve/6+10×shortage/6`的带罚权代理，不是实际额外电能、货币、PCC采购账单或财务盈亏。不得乘一个未经绑定的电价转成人民币/英镑收益。

主两模型最大实例风险U分别6.202468%与6.200395%；全期风险点值约5.52%—5.55%。完整附加225族的更宽joint family给q.95不同U（P1为6.704886%）；主/次要U来自不同坐标族，不能混抄。q.925的9.769888%是预声明次要有限族结果，非主策略风险。

**VERIFIED（事后描述，无新重采样）**：

- 最大P1日成本溢价为2025-12-13、seed201：+27,602.429代理单位，较该日参照+6.4938%；当日风险7.7712% vs6.9444%。全期2%要求并未要求每个日子2%，因此这不是主判据违约，但限制“日常稳定节约”的说法。
- 最大P1日风险为2025-10-31、seed204：**21.1019%**（参照20.9286%），2,886有效格。全期U≤10%不提供每日风险保证，也未证明P1造成该日天气/物理失效。
- 共1,825个seed-day槽，60个无有效目标日槽原样保留（同12个日期×5实例）；1,765个非空槽中68.1586%成本溢价为正。这不是1,765次独立天气重复，不能据此另作概率保证。

全年风险不是极端爬坡、状态类别、季节或未来年份逐子群保证。无PCC净额、备用容量/爬坡/SoC/网络约束与真实调度可交付性绑定，尚不能声称已供足可用备用或现场安全。

## 5. 合适的现实替代基线与已测边界

以下为同2025、相同forecast/target的已测baseline。风险U均取**次要225族3日界**，与主14坐标族分开。下表不重新选择主策略，也不将事后q能力格伪装成上线选择。

|策略|资源|q|均值代理成本|最大风险U|工程意义与局限|
|---|---|---:|---:|---:|---|
|Common/HGB|[0,1,4]|.95|78.272922|6.9941%|forecast+clock+ID的无新增遥测方案；已测且风险合格，但比P1贵；不是只发一个恒定reserve|
|Common/MLP|[0,1,4]|.95|78.659148|7.0324%|第二估计器的同接口比较；不能由固定recipe泛化神经优劣|
|P1/Persistence|[1,0,2]|.925|86.969480|9.2874%|无学习predictor的`max(forecast−current P,0)+历史offset`；已测且风险合格，成本较高|
|P1/Persistence|[1,0,2]|.95|92.283489|6.4729%|主q同档粗比较；不代表最佳工程fallback|
|WPQ36/HGB|[3,1,112]|.95|66.644430|6.6934%|历史冻结full reference；强同目标直接条件分位数，P1并未降低其成本|
|WPQ36/HGB|[3,1,112]|.925|65.394775|9.5213%|次要全q能力格的更低成本风险合格候选；不可改成主要参照|
|P1/HGB|[1,1,5]|.925|65.739232|9.7699%|有限族次要minimum，不是主q.95|

P1/q.95比Common/HGB/q.95点成本低14.3760%，比Persistence/q.95低27.3755%，支持“新鲜功率对这组弱/简单参照有信息价值”。但Common不含新鲜P，不能用其更差替代C1的full matched reference。Persistence已是公平的低计算比较，不能虚构“无简单基线”。当前工作尚未观测真实部署团队的现行策略；历史margin表、固定经验备用、已有EMS后处理或故障回退只是**可能**工程对照，其实际使用、训练规则与合适风险门槛UNKNOWN，未在本确认任务实现并冻结为工程fallback。旧物理/分箱结果目标、总体和来源边界不同，不能粘来填这一空格。

## 6. C1—C8的实用价值裁决

|Claim|本轮判断|实际含义|
|---|---|---|
|C1|SUPPORTED，框架内数值VERIFIED|一个独立年固定参照非劣；溢价明确为正；不是经济改善|
|C2|SUPPORTED，严格限接口|5列vs112列与较短fit存档可核实；不能升级端到端sensor/bytes/FLOPs收益|
|C3|UNKNOWN|只有一个封存确认年；再次查看2025不能检验额外未查看窗口维持性|
|C4|VERIFIED，有限族次要边界|说明声明recipe/order内可排除较小候选；没有实测工程最小资源含义|
|C5|VERIFIED，研究设计意义|固定参照、全族近优、最小性责任分离有助审计；未直接改善调度或费用|
|C6|有界SUPPORTED|保留状态恢复≠决策收益的负/零证据；旧支线来源/版本限制阻止全面运营结论|
|C7|UNPROVEN|溢价与实际接口节约、维护收益、PCC/财务输出未接通|
|C8|本角色未验证新颖性|精确任务接口带来可审计案例，不自动构成竞争性创新；新颖性须由独立先行工作审查裁决|

论文还有易使读者混淆的残留：Introduction第三贡献仍称未来confirmation，而后文已完成；PCC段将boundary transitions称为dominant unhedged risk、h6称spatial wakes govern decisions，却未由此次最小输入确认检验。上述句子不能充当实用收益依据。本审计不修改论文。

## 7. 可复核性

运行命令：`python research_audit/novelty_impact_20261019/reviewer_p/recompute_practical.py`。输出为`practical_derived.json`、`worker_metrics.csv`、`worker_timing.csv`、`baseline_envelope.csv`、`primary_seed_pairs.csv`、`primary_days.csv`和`practical_receipt.json`。脚本仅加载JSON/NPZ做确定性算术；重建主要均值以绝对1e-12核对，记账恒等式核对通过。700个受保护输入前后SHA256一致，冻结claim源哈希全部匹配；receipt含本地环境、脚本hash与命令，不以当前本地环境冒充Metis训练环境。

两项既有科学/数字门禁退出码均0，输出在本目录`scientific_gate.txt`和`number_gate/`。它们仅核验现行表述/数字一致性，不认证依赖块覆盖或C7。唯一next-action见`REVIEWER_P.md`；本轮未执行新benchmark或新增实验。
