# 项目独立严苛审计与一区破局方案（2026-09-06）

审计基线：Git `bb2c281623aaf13462c44301ff2c709a4fd07c3d`。对象为当前 TSTE 主稿、补充材料、实验代码、底层 CSV、缓存掩码和远程 checkpoint。结论不沿用旧审计的录用概率。

**裁决：项目具有值得继续做的研究内核，但当前版本不应投稿，现有证据不足以认定已经支撑一篇可信的一区完整稿。主要问题已超过“创新性稍弱、再补几个实验”：缺失率定义错误、退化信息集不对称、部分新基线不可溯源、时间边界污染，以及现金收益口径错误，正在支撑摘要中的核心主张。必须先重建可信证据，再谈期刊上限。**

这不等于整个项目无效。较早的 WTB 预测对照、去定义通道的 signature 实验、部分负控制和同模型残差分箱仍有价值。本次也未发现足以断言“所有实验均无效”的证据。应逐项隔离失效主张，避免把真实结果与不可用结果一起打包。

这里的“一区”是研究质量目标，不替代正式分区认定。JCR Q1 与中科院大类/小类一区不是同一口径；指定年份和学科的正式分区仍应以机构可访问的官方分区表核验。TSTE 的 scope 已核查，不能把“在 scope 内”当成达到录用标准。

## 1. 审计范围与证据等级

- 枚举本地 artifacts 下 26,293 个路径，查看全部主要实验族的目录和当前论文依赖；精读主稿、主要补充实验、现行评估脚本及近期审计。没有逐字阅读每份历史日志，也没有重新训练所有模型。
- 直接检查 WTB soft-pricing、dense/GBDT 对照、fair degradation、PCC、Markov-Gilbert、三场站 rolling、真实价格回放和年度 gate 稳定性产物。
- SSH 实测两台机器：25329 为 4 张 RTX 4090，25979 为 6 张 RTX 4090；当时 GPU utilization 均为 0%，25329 部分显存仍被占用，不能等同于无其他进程。
- 读取 25329 上三个外部场站共 15 个 checkpoint 的训练 metadata。核验缓存观测掩码、窗口偏移，抽查训练窗口与全年缓存的输入数值一致性。
- 新的远程证据快照保存于 [remote_provenance.json](E:/论文3/docs/audit_20260906/remote_provenance.json)。未启动新的训练，也未改动原论文和实验代码。
- 网络调研侧重已发表的近邻方法、缺失数据概率预测、预测—决策接口和 TSTE 官方范围；无法获取全文的论文只使用出版方摘要信息，不把摘要未写出的实验细节当事实。

“CSV 存在”“guard 通过”“训练脚本能启动”“论文数字与 CSV 一致”是不同等级的证据。下面优先处理能够从代码或缓存直接证实的问题。

## 2. 当前主线究竟是什么

原始路线是动态图、GRU、物理对齐 MoE 改善风电预测。整体精度结果没有支撑这条路线：train-only router RMSE 229.93，而 iTransformer 为 224.34、GWN 为 225.74。因此当前转向“联合学习的边界后验，服务确认流退化下的风险识别与备用筛查”在研究逻辑上是合理的。

它实际包含三个不同命题：

1. 去掉定义标签的风速/平均变桨角后，其他传感器是否仍含有可恢复的 operating-state 信息？
2. 在所有方法看到相同可用信息时，这个后验是否优于简单分类器、序列分类器和直接条件分位数？
3. 识别增量是否转化为同一决策时间线上、同一预测骨干下、可实施的风险收益？

目前第一项有实证基础；第二、三项存在明显证据缺口和实现错误。把三项分别在不同任务、不同 checkpoint 或不同观测条件下做出漂亮数字，不能推出完整的工程闭环。

## 3. 投稿阻断项：由代码或缓存直接证实

### P0-A：55%/78% 不是传感器观测覆盖率，核心应用动机写错

`scripts/rebuild_obs_windows.py` 用 `(physics[..., 1] != 0).mean()` 生成 `window_pitch_coverage`。`physics` 中是填补后的变桨角；非零比例不是原始观测率。零度变桨本身可以是正常有效记录。

同一 obs_window 的原始 `feature_mask[..., Pab_mean]` 直接计算得到：

| 场站 | 文稿所谓 pitch coverage | 实际变桨观测掩码均值 | 每台风机的实际覆盖率 |
|---|---:|---:|---|
| Kelmarsh | 55.13% | **97.32%** | 约 96.84%–97.66% |
| Penmanshiel | 78.09% | **99.13%** | 约 96.39%–99.72% |

因此，摘要及机制表“Kelmarsh 超过 40% 风机不能用物理变桨分位数”没有成立。即使 55% 真是逐时间点覆盖率，也不能直接转换为 45% 风机完全无传感器。

另外，外部 reserve 脚本把填补后的 `physics` 用 `isfinite(pab) & (pab > -5)` 当观测标记；在上述两个窗口中该判断覆盖率都是 100%。这进一步说明缺失机制没有按原始 mask 定义。

**处理：撤下由 55%/78% 推导出的稀疏观测结论。先重算每台风机、每年、每个通道的原始缺失率及连续缺失时长；若使用合成丢包，应明确是合成任务，不能用错误的真实缺失率作验证。**

### P0-B：“公平退化”保留了模型的当期原始传感器信息

`scripts/fair_degradation_replay.py` 默认只修改 `anchor_physics` 的 Wspd/Pab，`history_delay=False` 时保留 `x_hist`。而 `RegimeWindowDataset` 的历史切片包含 issue time 本身，即 `t-H+1:t`。所以编码器最后一个位置仍可读取当期干净 Wspd/Pab；规则基线却只能读取延迟的值。

这不是未来目标泄漏，而是**方法之间可用信息不相等**。若设想“原始流及时、确认后的 flag 晚到”，那规则同样可从及时原始流重新计算，而不必等待 flag。若设想“传感器流本身晚到”，则编码器内同名通道也应同步变旧。

`scripts/eval_markov_gilbert_telemetry.py` 更明确：`x_hist = batch['x_hist'].to(device)`，循环里只更新 `anc_corrupted`，然后直接用原始 `x_hist` 做 forward。因此 0.994 recall、0.967 F1 不能证明当前文字中的真实输入通道丢包鲁棒。该脚本在所有 burst-valid cells 上评估，并非专门 early-window；摘要又把它称为 early-window recall。

现有 stalled-history 结果（例如 delay6 recall 0.416 vs rule 0.196）值得保留为进一步核验的候选，但需统一缺失 mask、历史序列、衍生通道和事件评价支持集后才能升为主证据。不能用 0.933 的 headline 替代这项更困难的试验。

**处理：实现一个共同的 arrival-time 观测层，在进入任何模型之前只产生一份退化后的数据。原始流、历史、锚点、mask、相关衍生量一起处理；规则、MLP/GBDT、GRU/TCN 分类器、joint dense、joint MoE 共享它。**

### P0-C：新增两种 MLP 与硬件指标尚无可复现证据链

本地和 25329 的 `scripts/remote_matched_modular_baseline.py` 定义了 `ConsequenceMLP`、`compute_ece`，但 main 中没有实例化 MLP、训练循环、optimizer、checkpoint 载入、MLP 推理或 ECE 调用。它读取旧 dense/GBDT/退化 CSV 后拼表，仍在 summary 中直接写出：

- Independent Consequence MLP = 17.340M；
- Cascaded Frozen MLP = 16.412M。

现有 `matched_modular_results.csv` 包含两行 MLP，以及 latency、ECE、CI 等该脚本不生成的列；该目录只有两个汇总文件。本次检索没有找到支撑两行 MLP 的逐 seed 训练/预测产物。25979 的对应项目也未检出这套新 MLP 产物。

这足以判定**当前产物无法由所提供脚本复现**；不据此推断作者意图或断言其他位置绝不存在证据。在补齐原始产物前，两个 MLP 数字及“联合训练不可替代”结论不能使用。

还有一处明确的比较对象错误：CSV 中 Cascaded 的 `[-0.385,-0.052]M` 是 `delta_vs_global_M` 的 CI，主文却把它用于“joint vs Cascaded 差 0.347M”的主张。两组配对差不同，不能转用 CI。

**处理：暂时隔离这两行与延迟/ECE硬件字段；从 checkpoint、逐 seed 概率、同一残差数组重新算出表格。110,012 参数数目已从 checkpoint 验证，可以保留；4.12 ms、21.8 ms、运行内存及工业硬件泛化需要真实 profiler 日志。**

### P0-D：多年 rolling 的部分 test 覆盖训练/选模期

checkpoint metadata 显示：

- Kelmarsh 从源缓存第 120 天开始，训练 180 天，验证 30 天；不能写所有模型都在 commissioning 第一天训练。
- **Penmanshiel 从第 720 天开始**，训练区间为源时间第 720–900 天，选模验证到第 930 天。
- LHB 训练为第 0–180 天，选模验证到第 210 天。

外部 rolling 脚本却对 Penmanshiel 从第 730 天开始第一折 test（两年校准后一年测试），与模型训练及验证大量重叠。LHB 的第一 quarterly test 是索引 `[13500,27000)`，约第 93.75–187.5 天，也与模型训练重叠；第二季度部分覆盖选模期。

此外，先对全时期统一 inference，再按 anchor 是否落在校准区间截取，没有要求 `anchor + pred_len < calibration_end`；最后若干校准 anchor 的 24 步目标跨过 test 起点。基础 `RegimeWindowDataset` 原先有 horizon 边界限制，这个新回放切法没有继承。

这不意味着所有多年结果都失败：Kelmarsh 较后折、Penmanshiel 第二折及以后仍是有价值的候选。但“13 折严格前瞻”“消除多年 concept drift”必须撤回后重算。仅删除负面的第一折也不够，要按**训练和选模结束时间**统一定义准入，而不是按收益正负筛折。

**处理：每折输出 train_end、selection_end、calibration_target_end、first_test_target、last_test_target；断言所有模型选择和校准的目标时间早于 test。旧模型不能用于早于其训练结束的前瞻性回放。**

### P0-E：GBP 现金收益暂不可用，价格与能量时间线均不成立

`scripts/remote_dynamic_price_settlement_replay.py` 固定 `start_date=2016-01-01`，用 step/144 推日期、每三个 step 推半小时 period，没有读取实际日历时间。原始压缩 CSV 中 Kelmarsh 首记录为 2016-01-03；Penmanshiel 的 2016 文件从 6 月开始。缓存构造从原始最小 timestamp 起建网格，保存的 `time_index` 只是 day/slot 整数，不是完整 UTC 日期。因而“contemporaneous UK SBP”配价发生系统偏移，Penmanshiel 可达约五个月。

固定 52,560 步等于 365 天，不等于跨闰年或从年中开始的日历年。Elexon Settlement Day 也不是全年每天 48 个 period：夏令时切换有 46/50 个，官方定义见 [Elexon Settlement Period](https://www.elexon.co.uk/bsc/glossary/settlement-period/)。当前映射没有处理这些边界，缺价格还用全期均值填补。

另一问题是重叠预测窗口：24 个 horizon 的每个 forecast cell 都乘 1/6 小时后加总。一个实际交付时刻最多在多个起报窗口里被重复计费。它可以是 forecast-cell 加权损失，但不能直接称一次实际结算现金流，也不能据此算每风机每年 ROI。除以 24 也不能代替定义唯一执行策略，因为边界筛选、缺失和实际选择的 horizon 会改变权重。

算法还假定 reserve r 可直接抵消短缺，并按固定 £15/MWh 计成本。若这是持有备用，需要容量、爬坡、持续时间和激活来源；若这是减少申报，需要出售机会成本和双向偏差结算。当前既无实体执行器，也无完整交易收支。

**处理：GBP 回放降为待重算的价格加权诊断。保留完整 UTC timestamp，用真实 Settlement Period 映射，明确每个交付时刻只执行一次的决策；若继续做运营收益，至少落实一种实际动作及其成本/约束。**

### P0-F：Newsvendor 解析式写错

稿中成本为 `C(r)=r + rho E[(s-r)+]`。连续分布内点最优满足：

`C'(r)=1-rho Pr(s>r)=0`，所以 `F_s(r*)=1-1/rho`。

在 rho=10 时应为 **0.9**，不是 `rho/(rho+1)=10/11`。后者对应另一种 overage/underage 成本定义。成本函数对 r 是凸的，主文“non-convex risk pricing”也需要区分神经网络训练非凸与决策问题本身。

现有不少策略通过验证集网格直接最小化正确的数值成本，因此不能断言所有 cost 数字都受此错误影响；但 `eval_farm_aggregate_reserve.py` 的 `q_target` 确实用了 rho/(rho+1)，pinball 评价也要对应修正。

## 4. 即使排除以上错误，顶刊仍会追问的科学问题

### 4.1 方法必要性尚未建立

在有原始逐 seed 对照的 soft-pricing 中：

| 比较 | 已有数值 | 能支持什么 |
|---|---|---|
| Joint soft gate vs global | -0.568M；CI [-0.726,-0.406]M | 当前 WTB 窗口内条件分箱优于无条件分箱 |
| Joint soft gate vs physical-bin | -0.125M；CI [-0.297,+0.034]M | 没有检出优于该物理分箱 |
| Joint dense vs joint routed | +0.011M；CI [-0.163,+0.186]M | 没有检出路由带来的定价增量，不等于严格等效 |
| Continuous pitch quantile vs joint gate | 15.538M vs 16.065M | 干净观测下物理连续量更强 |
| Independent GBDT vs joint gate | +1.591M；CI [+1.396,+1.755]M | 优于这一个 classifier-posterior 对照 |

来源：`artifacts/p1_stats_20260904/unified_control_table.csv` 及 dense/GBDT 原始实验族。M 的口径仍是当前 forecast-cell cost，不是货币。

独立分类器拟合的是 regime 标签，而真正的风险任务是预测 residual quantile。分类器不善于残差定价，不能证明“联合学习不可替代”。最应挑战本方法的对手是**同样输入、同样预算的直接条件分位数模型**，以及用 frozen backbone 表征拟合 residual quantile 的模块化管线。

“一个 checkpoint 更便于审计”属于可取的工程属性，但模块化模型也能统一打包、版本管理和日志追踪；单部署对象本身不能替代算法必要性证据。

### 4.2 PCC 目前是可用目标子集聚合，不是真实计量点闭环

PCC 脚本在 `t_P_pred` 中使用未来 `t_mask` 筛风机，再对预测和目标求和。未来目标有效性可用于离线评测筛样本，但不能决定实际 issue-time 聚合预测包含哪些机组。

产物显示平均有效风机约 121.04，低于文稿总数 134；transitional test windows 只有 **71/4981=1.43%**。71 个相邻时刻并非 71 个独立天气事件；把每个窗口展开 24 个 horizon 再做 seed bootstrap，不能证明季节或事件层面的稳健性。

需要固定可用机组策略或真实 meter 数据、交付时刻去重和事件 block uncertainty。否则可称“有效机组子集上的聚合预测诊断”，不宜称“full operational envelope PCC economic value”。

### 4.3 LHB 负结果的解释是事后假说，不是已证实机制

现稿已披露 LHB +1.007M 的 rolling 负结果和 Kelmarsh rho=20 反转；旧审计关于未披露的指控已过时。但是，把 LHB 失败归因于“4 台风机无 PCC 平滑”和“秋季方差放大”没有对应因果对照。

LHB/Kelmarsh/Penmanshiel 的外部脚本计算的是 turbine-cell 短缺，未先聚合到 PCC；不能将一个非聚合试验的失败归因为缺少 PCC 组合平滑。四台风机也并非数学上没有误差抵消。

180 天校准与 quarterly 回放更换了测试时间与支持集，不能用两者差值单独证明“延长校准有效”。应在同一 test 上只改变校准长度，并在同一场站内随机/分层改变聚合机组数。

### 4.4 统计重复单位与探索后确认需要重建

5 个 seed 只刻画算法随机性，不是 5 个独立场站或天气历史；20,000 次 bootstrap 不会创造 20,000 次独立验证。13 个年度 fold 共享模型、重叠校准年，两个 UK 场站可能共享气候冲击，不能无条件按独立 Bernoulli 做“exact”符号检验。

12/13 的 0.00171 是独立假设下的单侧结果；13/13 的 0.000122 同样是单侧。应明确假设，作为描述性辅助，主不确定性来自同步时间块、天气事件或场站留出。两场站不足以稳定估计总体跨场分布，bootstrap 技巧无法补出新的独立场站。

经过大量路线尝试后重新收束主张可以接受，但新 endpoint、窗口和 baseline 必须在未来未触碰的确认集上冻结。Git 中写“pre-registered”不等于证明所有选择均先于结果；应给出协议版本、冻结时间、选择变量与未见结果的边界。

### 4.5 Signature、后验校准与稳定性不是同一件事

去掉 Wspd/Pab 后 NMI 高于置换控制，说明剩余通道包含可预测的标签信息；不证明真实控制机制、独立确认的设备状态或因果识别。可以保留这条窄而真实的主张。

NMI 也不证明 soft probability 是已校准 posterior，更不证明它是 future risk probability。应加 Brier/log-loss、reliability diagram、PR-AUC、固定误报率下 recall 和事件级 detection delay。

年度 marginal gate 分布相近可能来自真实稳定，也可能来自低动态输出甚至 collapse。`1/(1+W1)` 在概率范围内天然接近 1，不能只用 0.995 的视觉效果证明物理表征九年不衰减。应结合每年类条件校准、每 seed 混淆矩阵、事件检出和 loss；当前数据只能支持有限描述，不支持“漂移被消除”。

### 4.6 工程成本表也需实测与口径统一

参数量 110,012 已核验；float32 权重约 430 KiB 是合理量级。但这不等于整个推理内存小于 1.5 MB。仅 batch=1 的历史特征和同形状 float32 mask 就约 424,512 bytes，再加权重、图张量、隐状态、激活和运行库，必须 profiler 实测。

主文“<1 kWh/年”与补充材料 100 W 常开服务器的 876 kWh/年是不同成本口径，未清楚区分。134 台分摊的 £1.63/台不能直接搬去 6 台或 14 台场站；若同用 £219/场年假设，应分别约 £36.5 和 £15.64/台年。零增量 CAPEX、工业 CPU 型号间统一延时均需部署事实，不能作为实测结论。

## 5. 文献调研后的竞争位置

| 一手来源 | 已经覆盖的内容 | 本项目必须回答的新增问题 |
|---|---|---|
| Zhao 等，2026，IJEPES，*A physics-aware dynamic graph and mixture-of-experts framework for wind power forecasting*，DOI 10.1016/j.ijepes.2026.111769 | 动态图、物理指导、MoE 已有直接风电近邻；出版方摘要报告多预测跨度实验 | 不能再以动态图+物理+MoE 组合作主创新；需具体说明约束 route 与约束 prediction 的差别及其决策价值 |
| Meng、Guo、Zhao，TSTE 2026，DOI 10.1109/TSTE.2025.3611370 | 缺失观测下端到端非参数概率预测及在线插补 | 同信息集 missingness-aware 概率预测是必须重视的竞争方向 |
| Wen，Energy 2024，*Probabilistic wind power forecasting resilient to missing values: An adaptive quantile regression approach* | 缺失模式下自适应分位数 | 需要直接条件风险预测对照，而非只对照 global quantile 和标签分类器 |
| *Operating Reserve Quantification Using Prediction Intervals of Wind Power: An Integrated Probabilistic Forecasting and Decision Methodology*，TPWRS 2021 | 预测区间和备用成本的集成优化 | 将预测与 reserve 连接本身已有先例；新意要落在可观测信息、可靠性约束或可解释适用边界 |
| *Decision-Focused Learning for Power System Decision-Making Under Uncertainty*，TPWRS 2026，DOI 10.1109/TPWRS.2025.3597806 | 面向决策价值的学习框架 | 后处理 reserve audit 不自动等于 decision-focused learning |

链接：[IJEPES 2026](https://www.sciencedirect.com/science/article/pii/S0142061526002115)、[TSTE 2026 作者机构存档](https://ira.lib.polyu.edu.hk/handle/10397/117725)、[Energy 作者预印本](https://arxiv.org/abs/2305.14662)、[TPWRS 2021 出版方页面](https://ieeexplore.ieee.org/abstract/document/9334448)、[TPWRS 2026 DOI](https://doi.org/10.1109/TPWRS.2025.3597806)。这些是相关先行工作的定位，不跨数据集比较其报告指标。

检索中出现的纽约电网经济价值预印本 arXiv:2512.21754，打开后确认最新版本已撤回，本报告不将其当作有效竞争标杆。这也说明不能仅凭搜索摘要写文献综述。

[TSTE 官方范围](https://ieee-pes.org/publications/transactions-on-sustainable-energy/)强调可并入电网的可持续能源系统及设计、实现、并网、控制。本文若以 reserve/运营收益进入该范围，就必须承担相应决策边界的证明责任。增加 PCC、IEC、Newsvendor 等术语本身不满足这个要求。

## 6. 实验资产应如何取舍

| 实验族 | 本轮判断 | 处理 |
|---|---|---|
| WTB train-only 预测基线 | 有用；明确非预测 SOTA | 保留最少必要准确率对照 |
| 原始/legacy 高 NMI、不同辅助权重实验 | 可作历史证据，不能混成同一主实验 | 主表锁一个配置；其他移补充 |
| Withheld-channel 与 shuffled 控制 | 核心可保留；限定为监督标签信息恢复 | 加真实 mask 与事件支持审计 |
| No-Pab-std、no-Patv、时间/空间 holdout | 有价值的适用边界 | 补训练窗与配置对应，不再扩增同类表 |
| Anchor intervention、wake near-null | 说明信息依赖，不是控制因果识别 | 缩减物理机制措辞 |
| Dense/GBDT 原始 soft-pricing | 支撑部分比较，不支撑 joint 必要性 | 补直接残差分位数及真正 matched 对照 |
| 新增 Frozen/Independent MLP | 未具备可复现证据链 | 隔离，重训或找回完整产物 |
| 默认 delay / Markov | 信息不对等、部分指标支持集不一致 | 撤 headline，统一观测层重做 |
| Stalled-history / noise | 候选有效证据 | 按同信息集和固定误报率重审 |
| PCC 聚合 | 有潜力，未来 mask 与少事件限制严重 | 重定义 meter/固定机组与唯一交付时间 |
| 外部多年 rolling | 部分折受污染，剩余数据仍有价值 | 清除时间污染、horizon 越界；完整重算 |
| LHB 和 rho 反转 | 已披露，属于必要负结果 | 不把事后解释当机制证明 |
| 年度 gate 稳定性 | 描述性可用，部分时间在训练前 | 不声称消除漂移或九年前瞻稳定 |
| Elexon GBP 与 ROI | 当前不可用 | 真实 timestamp、一次决策、执行成本重做 |
| ERA5 对照 | 与当前能源决策主线联系弱；persistence 本身更强 | 放补充或删除，不占主文叙事 |
| Number/evidence guards | 检查能力有限 | 增加计算来源、比较对象、时间与 mask 不变量 |

## 7. 如何破局：先验证一个能被推翻的问题

建议将候选研究问题收束为：

> 在相同、带到达时间的 SCADA 信息约束下，边界监督的共享表征是否能在不增加误报和备用超支的条件下，改善场站级短缺风险；它在哪些观测条件下应该被启用或拒绝？

这比“MoE 不可替代”更可检验，也允许最简单的方法获胜。若真实观测并不稀疏，就明确研究可控通信退化；再争取实际故障日志验证其频率和严重性。

### 第一阶段：恢复可信底座（优先于任何大训练）

1. 为每个 headline 建 claim → 逐 seed 数组 → checkpoint/hash → config → 源 timestamp/mask 的记录；缺项直接不参与主张。
2. 用原始 mask 重建观测率。用 UTC 记录训练、选模、校准、测试区间；保存原始特征的 scaler，不只修改 metadata 声称重新标准化。
3. 保留旧产物，只在新目录输出修正结果；避免重写旧 CSV 后使旧论文表面“仍通过 guard”。
4. 修正成本公式、比较对象、forecast-cell 单位。将新增两个 MLP 和现金 ROI 撤出候选主证据。
5. 从尚未用于新方案选择的数据中设确认集；已用于大量探索的数据明确标为 exploratory，不能事后重命名为 untouched。

### 第二阶段：一个决定性 matched 实验

固定同一低 RMSE forecaster 和同一 residual target，比较以下风险层：

| 方法 | 要回答的问题 |
|---|---|
| Global / continuous physical quantile | 无条件、物理条件化是否已经足够 |
| Missingness-aware GBDT quantile 或 quantile forest | 简单直接风险预测能否替代后验分箱 |
| 序列分类器 + 同预算校准 | 增量是不是仅来自读取历史 |
| Frozen encoder + residual quantile head | 是否需要端到端联合优化 |
| Joint dense | 共享表征是否已经足够 |
| Joint routed | 路由是否提供超出共享表征的增量 |

统一训练/调参预算、传感器输入、到达时间、历史长度、mask、校准预算和故障增强。比较 clean、真实缺失、整个通道 delay、burst、偏置漂移、相关多通道丢失；不要只选有利的故障率。

主指标选一个：**同可靠性约束下的唯一交付时刻平均 cost/regret**。同步报告超限概率、shortage、reserve、pinball、事件级 recall、误报次数/日、检测延迟、校准。置信区间以共同天气/时间块为主，seed 作为算法不确定性附层。

通过标准应在新结果前冻结：相对验证集选出的最强非路由对照，在独立确认时间段改善主指标，且不靠增加误报或放松可靠性换收益；实际最低有意义差值要由应用需求设定，不能事后用“只要显著”代替。

### 第三阶段：外部确认与工程动作

在至少两个外部场站做统一时间协议；这是建议的项目验收条件，不是期刊硬性数量规定。LHB 保留作负对照，Penmanshiel 从选模结束以后起算，Kelmarsh 按真实日期切片。新外部站点比给旧 WTB 加 20 个 seed 更有信息价值。

选择一种实际动作：有限容量/爬坡/激活成本的缓冲资源，或具有申报机会成本和双向偏差的交易决策。每个交付时刻只计算一次执行记录，明确价格可知时点。若拿不到这些要素，论文就停在风险诊断范围，不声称已实现现金收益。

真实事件日志需有同一事件的发生、发送或接收、确认标识，才能估计通信延迟。把秒级事件向上取整到 10 分钟网格，只得到网格对齐等待，不是测得通信延迟；旧审计建议“直接估 event-to-confirmation lag”也不能无条件照做。

### 结果出来之后的分叉与止损

- **Joint dense 与 MoE 相当**：把贡献转为边界监督的条件风险表征，采用更简单实现；无需继续为 MoE 辩护。
- **直接分位数/序列分类器更强**：不再声称方法优势。可研究观测受限条件下方法失效边界，但一区仍需可复用的新发现和独立验证，单个负结果不会自动达到一区。
- **识别改善但决策无改善**：收口为诊断论文，停止现金收益叙事；TSTE 适配性下降，重新按真实贡献选刊。
- **同信息集后退化优势消失**：停止当前 defense-in-depth 方法主张，而不是另找一个更差 baseline。
- **多场站上有稳定、工程量级的决策收益**：TSTE 或同层级能源期刊才成为可信投稿目标。
- **若目标为 Nature Energy/Science 等旗舰**：还需普适新原理、显著系统意义、独立多系统/真实部署验证。现有组合模型加 SCADA 后处理不具备这一证据基础；增加算力无法替代这些要素。

## 8. 算力如何分配

本次已验证 4+6 张 4090 可访问，25329 原生 torch 导入有 HPCX 动态库冲突；采用项目既有 LD_PRELOAD 库组后成功读取所有 checkpoint。后续执行应沿用已验证环境，不修改系统库。

先用 CPU 完成 mask、timestamp、claim 表和数组检验；这一步比占满 GPU 更紧急。阶段二可将 25329 的四卡用于 WTB matched 风险层与同信息集回放，25979 的六卡用于外部场站确认；先跑一 seed 完成数据与时间协议检查，再并行五 seed。不得把一次 smoke 的数字写入正式机制表。

工作量粗估：数据/溯源纠正约数个工作日，完整 matched 与外部确认约一至数周；这是组织工作量估计，不是基于全新任务实测的 GPU 工期承诺。仅需要重新校准/评估的任务优先复用可信预测数组，只有模型训练期或特征规范错误才重训。真实日志或新场站是外部资源瓶颈，10 张卡不能解决。

## 9. 最终投稿判断

| 目标 | 当前判断 | 决定性差距 |
|---|---|---|
| 一篇可发表的研究论文 | 存在真实内核和大量可复用资产 | 必须先清理证据错误；降刊不能豁免有效性要求 |
| 一般一区质量目标 | 有潜力，尚未被当前结果证实 | 同信息集强对照、独立确认集、真实有效的风险评价 |
| TSTE/同层级强能源期刊 | 当前版本不建议投稿 | 摘要核心动机及两条运营证据链需要重建 |
| 领域旗舰/综合顶刊 | 目前距离大 | 方法普适性、系统重要性与真实部署证据 |

原审计中的“超过多数 TSTE 稿件”“证据前 10%”“45%–55% 或 60%+ 录用概率”没有可核验的期刊样本支撑。本报告不继承这些数值。**最值得继续投入的是已经显示出的可学习边界信息；最需要停止的是用失真的缺失率、不对等退化和重复计费给它追加工程价值。恢复证据链后，让一个真正公平、可以失败的实验决定主线，才是目前性价比最高的破局。**
