# E04–E06、完整切片与2026-10-20状态测量贡献盘点

本轮是只读证据审计，采用 experiment-to-paper 的 audit 模式；只新增本文件与 `SELECTOR_STATE_CLAIMS.csv`。没有执行模型、拟合、推理、校准、统计重算或重采样，没有下载测量、访问远端、改动结果/阈值/契约/V2或提交Git。日期：2026-10-20。正文的 VERIFIED 是已存文件可直接支持，INFERRED 是解释，UNKNOWN 是未核或缺证。既有停止决定约束执行，不使已完成结果自动失效。领域新颖性未在本轮重新检索，均为 UNKNOWN。

## 1. 可保留的知识与不可越过的界线

1. **VERIFIED：E04严格选择器未认证任何策略，但“无认证可行策略”不等于“真实总体都不安全”。** 绝对风险UCB全部超过10%，成本/相对风险也限制复杂候选；观察违约率仅10.259%–10.444%，四个单侧下界均低于10%。它提供风险资格、成本资格与不确定性共同阻碍最小充分识别的具体反例。
2. **VERIFIED：状态条件化重新分配风险，而非普遍改善。** 完整五种子切片显示C在过渡与9.5–11.5m/s边界带的事件/缺额较少且采购更多，在稳态、[5,7.5)m/s及过去下行爬坡组却更差。稳态、[5,7.5)及过去下行爬坡均5/5种子C更差；过渡改善为4/5，seed203例外。切片是事后描述，未来过渡/未来爬坡不能成为在线策略证据。
3. **VERIFIED：状态测量pilot有两类不同事实。** 强新鲜历史及功率更新后再加当前pitch，HGB成本收益上界低于1%；旧历史补新鲜P的成本收益较大，补pitch较小但不为零。这些有限程序的成本界不能建立普遍信息冗余、安全替代或全部状态信息无效。
4. **VERIFIED：同档位HGB保留成本接近、采购与缺额变化的信号。** 共同q=.925下，OP6→OPZ6成本+0.0871%、采购+0.9578%、U−9.5677%；双方历史/开发事件率资格通过。仍未通过完整A/B/C或分配/替代验收。相同q不是相同R、相同风险或同采购预算。
5. **VERIFIED：历史标量预算匹配本身完成且发生迁移失败。** offset段匹配精确，但共同q HGB开发期状态策略比匹配对照多采购0.482345代理kWh/格；因此并未得到开发等预算对照。不能由其失败声称pitch独有信息价值，也不能称已证明增购解释充分。
6. **VERIFIED，范围极窄：事后代数检查排除特定常数增购解释。** 对共同q的五个固定HGB实例，从其原P基线出发、同新增平均R的非负均匀常数增购，其U改善上界均小于所观测pitch程序改善。它没有排除更强P-only自适应校准、其他学习程序或学习误差；Original档位和MLP没有一致复现。不是新确认或总体不可替代性。
7. **VERIFIED：执行/复现链有独立价值。** E06绑定了计算、23个输入与五个输出；C-201完整闭合20个seed×policy单元，各35块。后验末位不确定性、历史失败原因未知与最终动作/账目精确闭合需要分开表述。

以上可作为结果、方法边界或补充材料的贡献候选；本文件不将它们评为全球新颖、不重筛题、不作全局投稿否定，也不撤销停止追加投入。

## 2. E04/E05/E06的具体原证据

### 2.1 E04严格选择器

- 冻结设置：`experiments/E04/PREREGISTRATION_E04_V2.json`；B=风速分箱，C=后验条件分位数，D=验证冻结hybrid，D10=预设边界band hybrid；复杂度B<C<D<D10。不是No-Graph/本地微调/迁移架构排序。
- q*=.90、rho=10、h=6、dt=1/6；alpha=.05、epsilon_C=0、epsilon_V=0、v_max=.10；训练种子201–205，35个原生144-anchor块，主抽样20000/RNG20261017，诊断10000/RNG20261018。
- 评价窗口：`analyses/e04_regime_slices_20261018/alignment.json`，test anchor30275–35255；WTB Day211 slot35至Day245 slot119，每seed385205有效格。块从首anchor起划分，不是自然日；同35天天气在种子间复用。
- 原结果：`experiments/E04/results/e04_v2/e04_v2_selection.json` 的 `policies`/`selection`。

| 策略 | 绝对风险U95 | 相对B成本差U95/kWh，原选择器汇总口径 | 结论 |
|---|---:|---:|---|
| B | .11419393570436379 | 0 | 未过绝对风险 |
| C | .11731446644166825 | 3758647.2788021564 | 成本、相对风险、绝对风险未过 |
| D | .11418291791543933 | 119264.05077571867 | 三项UCB约束未同时过 |
| D10 | .11389418686057207 | 128434.65169582365 | 成本、绝对风险未过；相对风险上界为负 |

结果是 `NO FEASIBLE POLICY`。选择器JSON中 `*_point` 是抽样汇总点，不可替换原数组确定性总体率或五seed均值成本。完整观察成本另见§3，不混用五seed总和与均值。

### 2.2 E05稳定性诊断

`experiments/E05/results/selector_stability.json` 的 `summary`/`rows`：无可行6464/10000=.6464；各自可行频率B .3523、C .0042、D .0001、D10 .0002；第一选择频率B .3523、C .0013、D/D10 0。没有达到>=.80稳定性标准。

每次抽样检查聚合指标约束，没有在每次抽样内重建UCB。因此这不是完整UCB选择器的嵌套通过率，也不是未来无解概率。该JSON保留当时 `execution_receipt_available_for_input_arrays=false` 的历史输入边界；自身诊断运行有 `experiments/E05/results/e04_execution_receipt.json`（EXECUTED/exit0）。后来的E06补齐其独立replay链，不能倒填该旧JSON的历史身份。注册表§E05仍写旧unbound口径，与后来的E06文件构成版本时点差，必须并列说明。

### 2.3 E06与J0来源收据

- `experiments/E06/remote_e06_final/e06_final_bundle/e04_execution_receipt.json`：实际replay EXECUTED/exit0，源码hash `657ee991381d5252b88243d12d64da08f92aeebef799e23f923bdfe15eac3b82`，输入清单与五个输出逐一绑定。
- `.../e06_replay_source.json`：source_job J04，原wrapper `failed_after_replay_due_to_postcheck`，replay命令0；J05重新包装。J04不能记作成功调度作业，但其中已完成计算也不能抹去。
- `.../e06_remote_input_verification.json` 23个输入在replay后未变；`experiments/E06/results/local_verification.json` 为 `PASS_BUNDLE_LOCAL_INPUTS`，23个远端记录与本地精确副本匹配。旧测试/原数字/独立科学认证没有因此升级。
- 本轮另外只读计算文件SHA/大小：E04-v2与E06各5个输出NPZ，10/10与各自收据完全匹配。没有解包模型或重新计算指标。
- J02本地`experiments/E06/remote_j02/pulled-manifest.json`只证明2026-10-18有相应传输及文件；不能单凭它认证原执行。其强基线数据与E01内容由其他盘点角色负责，不在本文件冒领全审。
- J07 exact-input传输的shell后置语法错误保留在E06 log；其已写出的输入manifest可用于本地文件身份核对，不能将J07改写为成功科研作业。
- **本轮发现的局部元数据缺口：** `experiments/E04/results/e04_v2/e04_v2_execution_plan.json#metadata.remote_replay_script_sha256` 是64位 `007088D9F2C6116C5D6467F8982808101625BF6348F308F55DEDF001DB9E405F`，对应receipt的同字段却为63位 `007088D9F2C611D5F6467F8982808101625BF6348F308F55DEDF001DB9E405F`。因此不能声称这两个附加源码标识字段完全一致。本轮不修它、不推测原错字来源；输出字节匹配及E06另一条源码/输入收据仍各自成立。
- J01/J03/J06/J08/J09完整调度/执行档本轮未逐项审查；J08路径出现在v2 selector来源中，不等于其全作业收据已核。未审查不等于不存在。

## 3. E04可行性、工况切片与精确性

### 3.1 不是“只因置信界保守”或“真实总体已超限”

直接来源 `analyses/e04_feasibility_diagnostic_20261018/diagnostic.json#policies.*.registered_gap`：

| 策略 | 原数组观察V | 单侧L95 | 单侧U95 | U95超限距离中不确定性余量占比 |
|---|---:|---:|---:|---:|
| B | .10283719058683038 | .09292903996002959 | .11419393570436379 | .8001124814199269 |
| C | .10443945431653276 | .0936876149917864 | .11731446644166825 | .7435985491387158 |
| D | .10278059734427124 | .0928345501677142 | .11418291791543933 | .8039474415032528 |
| D10 | .10259420308666814 | .09271208741370102 | .11389418686057207 | .81328859956319 |

四个点率也都大于.10，故只看点率仍无可行；四个L95又都小于.10，故未证明真实总体超限。不确定性比例是算术分解，不是因果归因。共享日块敏感性界更宽，不能据此认证现场安全或跨站系统性欠校准。

### 3.2 完整四策略/五种子观察结果

最终版本应读 `analyses/e04_complete_policy_comparison_20261018/v2/`，其中`full_policy_metrics.csv`：B/C/D/D10五seed均值PSREI分别14979309.812301 /15424949.648526 /14990724.703307 /14994057.786527 kWh；C/D/D10相对B均值增加445639.836226 /11414.891006 /14747.974226 kWh。这是原策略观察均值，不是新bootstrap结果。

完整切片来自 `analyses/e04_c201_exactness_20261018/reconciliation/complete_summary/pooled_slices.csv`，不是原只含四seed C的旧汇总：

| 组 | B事件率 | C事件率 | B/C平均备用kW | 边界 |
|---|---:|---:|---:|---|
| [5,7.5)m/s | 11.9243% | 15.8899% | 212.4944/186.3395 | C在5/5seed更差 |
| [7.5,10)m/s | 11.4186% | 12.3180% | 326.5781/314.7099 | 描述性 |
| 稳态 | 10.5733% | 11.5599% | 173.1056/167.5911 | C在5/5seed更差 |
| 过渡 | 9.7745% | 8.4817% | 147.9208/153.9231 | C在4/5seed较好，含未来标签 |
| 过去60min降功率>150kW | 18.1378% | 20.3232% | 181.9861/171.4185 | C在5/5seed更差 |
| 9.5–11.5m/s边界 | 7.6517% | 6.4533% | 311.0642/344.0962 | C多买备用，非成本胜出 |

`comparison.json#own_top5_blocks`：B/D/D10为31/34/29/13/19，C为34/31/29/26/12，说明C会重排风险块。未来60min实际功率下降>150kW组，B有256775/1926025重复seed格、100500/198067次违约；这是已存事后关联，不认证可预测性。上述组差没有新的同时推断/机制控制，不可写成确定物理机制或在线策略收益。

### 3.3 精确性贡献与历史失败保留

`analyses/e04_c201_exactness_20261018/reconciliation/result.json`：`ALL_20_SEED_POLICY_CELLS_EXACT`，5seed×4policy×35块的n、违约、成本精确闭合。C-201事先指定A100 repeat1后验，A100/RTX5060各两次固定重放均35/35块成本差零；未放宽容差。

旧 `analyses/e04_regime_slices_20261018/closure_seed201.json` 的C成本最大差4.256908416748047 kWh仍保留。历史失败后验未存，无法确认触发。相同设备后验有末位差，本次分箱与动作一致；node20相邻箱成本差数值吻合仅是候选机制。不能把原失败抹去、宣称后验逐位确定或指定GPU造成历史错误。此族贡献主要是可审查重建与数值稳健边界，领域新颖性UNKNOWN。

## 4. 状态测量pilot：测量与新鲜度应分别解释

原配置 `experiments/state_measurement_pilot_20261020/protocol.json`；F=共同预测/时钟/ID+WPQ36+六个P汇总，FZ再加当期三叶pitch均值；O6把最后6槽测量遮蔽，OP6补当期P及两个差值，OZ6补当期pitch，OPZ6两者都有。没有pitch历史/变化率；不能代表完整真实状态信息。

共同h6、forecast_age6、目标释放延迟1、rho10、dt1/6。阶段是半开区间：fit[19440,25193)，offset[25200,27641)，selection[27648,30233)，evaluation[30240,35273)；后者Day211–245、671538主人口格/35天气日。主人口同时要求未来P、当前P和三叶pitch有限；all-target/Zobs另列，不能挪用总体。每seed360000共同训练行，201–205；HGB固定100迭代、15叶，MLP64/32、80epoch；同训练行/配方不等于参数/FLOP/收敛资格匹配。F/FZ/O6/OP6/OZ6/OPZ6原始宽度118/119/118/121/119/122，pitch本来就增加输入。

`summary.json#registered_intervals`的G正表示成本降低，D表示功率相对pitch成本溢价；开发154坐标、alpha.05、20000共享圆形3日块/RNG20261030，1/7日敏感性。阈值1%成本、10%事件率、.001*Cstar加权U，Cstar=40.04664774157611；这些是研发判据，不是业务SLA或期刊门槛。

| HGB比较 | 成本收益G，或溢价D | 原近似联合区间 |
|---|---:|---|
| F→FZ | −.134790% | [−.433947%,+.164367%] |
| O6→OZ6 | +3.508853% | [+.494479%,+6.523226%] |
| O6→OP6 | +13.168687% | [+8.094772%,+18.242601%] |
| OP6相对OZ6成本溢价D | −10.011109% | [−13.737287%,−6.284931%] |
| OP6→OPZ6 | −.086548% | [−.615779%,+.442683%] |

14组历史选择均有资格，选档后才开发评分；HGB F/O6 q=.925，其余多数.90。原开发HGB仅F/O6及简单控制等部分合格；FZ/OP6/OZ6/OPZ6、MLP多个上界跨10%，不是已证明这些策略真实率均大于10%。全部MLP原成本比较及两估计器route flag在CSV中保存，不由HGB精度界代替MLP。

执行事实：60主拟合+10简单控制，原`VERIFICATION.json`和`action_audit.json`记210条人口/动作版本、1470项检查，部分派生包822成员验证。直接读` scheduler_history.json#Jobs`为149条：244971 F/exit1，其他148条F/exit0（含父项，不是149个独立实验）；首次失败在训练前。全权重/索引/动作留远端，本地导出明确是partial，不能宣称本轮核过所有远端字节。

## 5. B修正、微缺额与保留的反证

`research_audit/state_measurement_pilot_code_review_20261020/findings.json#b_implementation_discrepancy`：旧B额外要求U(OZ)−U(O)、U(OP)−U(O)守门，方案未列；反例旧判false/规定判true。实际HGB/MLP original_B与specified_B均false，结论未翻转。原程序保留，不能把实现问题当全部失败原因，也不能拿B失败推出pitch无价值。

同目录`review.json#records`：固定seed201、两估计器六格共12个权重全开发预测逐值相等（不是全部60）；各抽4096坐标独立重建特征，最大差1.1920928955078125e−7（OLS浮点累计），缺失掩码一致，未发现通道/时点错位。FZ/OZ6/OPZ6分别26/173/41个树节点实际使用pitch，不能说pitch没接入，也不证明已充分学到最优状态程序。154坐标原抽样重构误差<4e−16是既有数值复现记录，不认证覆盖率。

seed201原校准F/FZ严格事件36830/58652，其中≤1kW为11134/33107，>1kW为25696/25545；即总事件多21822，而大缺额少151。1kW仅量级审计，原V仍S>r；不能自行删除微缺额、称噪声或放宽风险阈值。MLP微缺额比例很低，不可将所有未资格归为此机制。

`findings.json#retained_HGB_OP_to_OPZ`：原q程序C+0.086548%、R+0.966805%、U−9.561358%；成本溢价区间[−.442683%,+.615779%]；seed202/204/205的OP−OPZ加权U下界超过.001。这个差异本身阻碍“安全替代”主张，但采购更高仍是反证责任；原两策略事件率资格未闭合。它是固定策略差，不是pitch独有信息量。

## 6. 共同q与历史采购匹配：哪里已经公平

`experiments/state_calibration_controls_20261020/protocol.json`与`frozen.json`：只使用旧权重绑定的归档raw预测，新fit0；60权重hash绑定是既有记录，不是本轮远端字节复验。共同q=.925取历史450族中首个全60实例合格档，非开发选择，也非把原学习q改成.925。采购delta仅拟合Day176–192均值，193–210资格，211–245一次开发评分；不使用开发R差回配。

- 修正后B及A/C：`summary.json#corrected_routes` 四组Original/Common×HGB/MLP均false。
- 共同q下：HGB OP6 C32.37781579124639/R29.699322755870288/U.26784930353761033；OPZ6 C32.40601483913893/R29.98379360751082/U.24222212316281092。成本+0.087094%，R+0.9578%，U−9.5677%。G区间[−.644935%,+.470748%]，反向成本溢价[−.470748%,+.644935%]；不能把`mean_R`坐标（差/Cstar）误标成相对R百分比。
- `jointly_qualified`中Common:HGB:OP6与OPZ6均true；事件率最大UCB约7.271%/7.083%。这修复了原q下的相关事件率未资格，但没有使完整替代/分配守门自动通过。
- MLP共同q OP→OPZ平均C+0.659%、R+1.548%、U−3.467%，方向/逐实例关系不稳定；旧信息加pitch原档G+3.355%在共同档变为约−.121%，说明校准程序可改变成本结论。
- `budget_transfer.csv`的Common/HGB/residual_state五seed：offset平均R基线34.184660、状态33.986738、匹配33.986738；selection34.379466/34.308759/34.181795；development29.699323/29.983794/29.501449。开发状态比匹配多.482345，预算方向翻转。此为已完成、应报告的转移失败。
- Common:HGB:Match_residual_state开发V=.20066861443432837；最高实例风险下界约14.790%，是真正有超限证据的特定失败控制，不是所有P-only均失败。MLP匹配控制可过事件率门，但原分配/替代条件仍未通过。
- `summary.json#attribution`所有state_allocation_candidate/matched_power_sufficient均false。因此正式“状态分配优势成立”与“匹配P足够”两结论都未建立。

执行已完成：`VERIFICATION.json`、`action_audit.json`与`point_reconstruction.json`记750个历史budget拟合、180实例/360人口动作版本/2520项检查；596坐标的既有点重构最大误差2.0123e−16；27条调度全F/exit0。两阶段各alpha.05，不合成为全链95%；1/7天敏感性未用于挑选主要结果。原154与新596是不同族，不能用新区间追改旧区间。

### 6.1 事后常数增购界能支持什么

`additional_purchase_bound.json#records.Common:HGB`，对任意常数d>=0，U(r)−U(r+d)≤ΔR·V(r)。在该固定窗口、固定基线、同新增平均R约束内，5seed的观测U改善超过界的差为.0158648307/.0181879240/.0049619172/.0035237608/.0105065377，全部正。该结论对所限定常数类是代数事实，无须将一个事后d当新策略评分。

Original:HGB、Original:MLP、Common:MLP的`all_five_finite_window_excesses_positive`均false。共同q结果并非五份独立天气复现，且未排除P工况自适应、滚动误差、在线校准、其他P-only学习误差。**可保留“均匀增购不足以完全解释该HGB程序差异”的有界线索；不可写“pitch独有信息已识别”“状态不可替代”或“真实等预算运行收益”。**

## 7. V2覆盖、未执行与未核查

**V2覆盖审计（本轮已查正文、补充、GAPS）：** `manuscripts/wind_energy_v2/manuscript.md`和`supplementary.md`覆盖后来的WTB420例及Towie2025独立固定参照/次要有限族分析；没有收录本文件E04四策略选择器、E05、完整B/C工况风险重分配、state pilot、B修正、共同q、预算转移失败及常数增购界。其“WTB无有限族最小性”不能代替这些不同问题的实验。遗漏不自动等于论文应全纳：可分别选作主贡献、补充或复现边界，需根据具体稿件叙事决定；本轮不改V2。

**完成并已读取原结果/配置/收据的覆盖：** E04-v2 JSON/五NPZ文件身份；E05原JSON/CSV结构及运行receipt；E06实际replay receipt/plan/manifest/23项本地核验；可行性diagnostic JSON；完整四策略CSV与comparison JSON；C201 reconciliation/exactness结果及旧失败；pilot protocol/summary/envelopes结构/instance CSV/historical choice结构/qualification/scheduler/export/action audit；代码审计findings/review；controls protocol/frozen/summary/instance/budget CSV/附加代数/point reconstruction/调度/action audit；当前V2文本。伴随CSV保存具体key/row、seed/window、控制及限制。

**明确未执行，不能计阴性：** E07历史重校准（协议草案，缺新WTB246–280窗口）；pilot S3–S5、备用配方、第二场站状态测量确认、组合净短缺；reserve-allocation V1/V2的C5、强P-only程序与新预算机制均仅规划/审查。`research_audit/reserve_allocation_confirmation_v2_20261020/WINDOW_DECISION.json`把Towie2026 Jan–Apr取消独立确认身份，qualified_independent_windows=0，exposure仍UNKNOWN；不是证明全世界无资料，也不取消原Towie2025旧问题的独立身份。

**未核/缺证：** 当前远端完整权重/动作/fit索引字节可用性；J01/J03/J06/J08/J09全收据；旧C201失败后验；真实到达日志/计量分辨率/采购与交付职责；更强P-only及真正开发等预算或因果预算机制；新问题独立未见窗口；所有状态信息/Bayes最优/物理因果机制；依赖bootstrap名义覆盖率；近邻全文排重与领域新颖性。没有根据缺这些证据把已存有界信号改判无效。

## 8. 本轮验证范围

本轮新增内容是文档与直接读取既有值的CSV清单；没有调用既有统计生成器或科学门禁的重采样分支。静态检查来源文件存在、CSV结构/来源hash、E04-v2/E06十个输出收据hash及调度记录状态。CSV共311条、23个审计子族、17个直接数值/判定来源文件；ID唯一，引用存在，所录来源SHA与当前文件匹配。另只读查看两份seed201 NPZ的键、shape和dtype，四策略cost/viol及n均为35元素float64，没有汇总或重算指标。既有科学/数字门禁、模型复现和统计重构的通过记录以其原VERIFICATION文件为依据，不冒称本轮重新执行；本轮不宣布新的科研里程碑或升级契约。
