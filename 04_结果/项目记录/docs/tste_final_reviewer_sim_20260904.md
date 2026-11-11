# TSTE 终审 Reviewer 模拟（2026-09-04）

> 评审对象：`paper_tste_ieee.md`、`paper_tste_supplementary.md`、`cover_letter_tste.md`、当前 PDF/提交包与复现 guard。
> 评审口径：三位对抗式审稿人 + Associate Editor/Meta-review；按 IEEE Transactions on Sustainable Energy（TSTE）Regular Paper 判断。
> 本轮新增证据：历史窗口同步延迟上界、跨窗口稳健性扫描、`signature_core_no_pab_std` 消融。

## 一、终审结论与概率校准

**当前裁决：Major Revision / Reject-and-Resubmit 边界；不建议按当前包直接上传。**

| 状态 | 预估最终录用概率 | 主要风险 |
| --- | ---: | --- |
| 当前 Markdown 学术内容 | 35%--45% | 模块化对照削弱核心必要性；延迟场景缺少真实运行 grounding；数处 claim/数字冲突 |
| 当前 PDF/ZIP 直接上传 | 低于 10% | PDF 与提交包为 2026-07-03 旧产物，未包含 9 月新证据；数字 guard 为 blocked |
| 修完全部 P0，仅做一致性与叙事收口 | 45%--55% | 可进入正常外审，但“为何必须 joint routing”仍会被追问 |
| 再补模块化等价对照 + 真实延迟/缺失证据 | 55%--65% | 核心必要性和运行动机同时闭环，达到较稳的 Major Revision 可救形态 |

TSTE 官方范围明确覆盖风电机组及可持续能源系统的设计、实现、并网与控制，本稿主题在范围内；首次投稿 10 页上限也与旧 PDF 页数一致。但当前 Markdown 尚未重新编译，不能用旧 PDF 的 10 页结论代表现稿。

## 二、本轮相对上一轮真正改善的地方

1. **挑窗口攻击基本被化解。** Penmanshiel 与 Kelmarsh 的 secondary/fixed-random windows 的 `signature_full` 平均 NMI 均高于 0.20，说明主结论不是单个窗口偶然性。
2. **`Pab_std` 载荷攻击基本被化解。** 去掉 blade-pitch dispersion 后，WTB/LHB 的 `signature_core` NMI 仍为 0.309/0.578，边界信号并非由该单一后果通道承载。
3. **公平退化语义更完整。** 当延迟同时冻结历史通道时，六步延迟下 gate/rule recall 仍为 0.416/0.196，优势缩小但未消失，堵住了“只退化比较器”的主要反驳。
4. **claim 边界总体克制。** 论文主动承认低 RMSE 模型、clean rule、logistic classifier 和 physical-bin policy 的优势，避免把诊断结果夸成 forecasting SOTA 或 dispatch optimality。

这些增强足以把问题从“实验不可信”推进到“贡献是否足够必要”。后者现在是终审主战场。

## 三、Reviewer #1：理论、机制与创新性

**评分：Soundness 3/4；Novelty 2/4；Overall 5/10；Confidence 4/5。**

### 优点

- 通过 withheld-channel retraining、permuted-label controls、跨农场复现、窗口扫描和 `Pab_std` 消融，证据链明显强于常规“attention/gate 可解释性”论文。
- 论文把机制主张限制为“declared boundary 的可恢复性和 route provenance”，没有声称 anchor-free discovery 或因果机理发现。
- boundary-focused forcing 并未被包装成普遍预测增益，负结果披露较充分。

### 主要质疑

1. **[高风险：核心必要性] 模块化基线事实上削弱了 joint routing 的存在理由。** Supplementary Table A10c 中 GWN+classifier-bin 为 86.54M，低于 boundary/gate-bin 的 95.13M；但表格和正文却称它同时“trails ... gate-bin”。这是数值方向错误。更关键的是，即使 paired cross-backbone CI 跨零，当前证据仍没有证明“同一个模型对象”比“低 RMSE forecaster + classifier/posterior +统一日志”带来不可替代的科学价值。版本、校准和审计完全可以在模块化流水线中实现。
2. **[高风险：创新性] 方法本体仍接近 directed-diffusion GRU + dense MoE + anchor alignment/forcing 的组合。** 真正新意主要在 reviewer-facing evidence protocol，而不是新的学习原理。若联合路由没有相对模块化方案的量化增益，审稿人会把贡献判断为“well-audited engineering integration”。
3. **[中风险：机制措辞] consequence-channel signature 证明的是可预测相关性，不是控制机制的因果识别。** 当前边界措辞大体安全，但摘要中的“graded by consequence-channel quality”仍比证据更强；现有实验没有直接测量每类 consequence channel 的物理因果贡献。

### Reviewer #1 建议

必须把核心命题改成可检验的二选一：

- 若坚持 joint routing 必要性：补一个同输入、同后验分箱、同校准预算、同低 RMSE backbone 的 modular posterior 对照，比较 route-residual calibration、退化鲁棒性、reserve cost/violation 和审计链完整性；
- 若不补：把贡献降为“a reproducible integrated diagnostic design”，删除任何暗示模块化方案无法提供责任链的句子。

## 四、Reviewer #2：实验、统计与复现

**评分：Soundness 2.5/4；Empirical Rigor 2.5/4；Overall 4/10；Confidence 5/5。**

### 优点

- 主要 WTB 结果使用五随机种子，强预测基线覆盖 iTransformer、Graph WaveNet、PatchTST、TiDE 等；有 train-only class-weight provenance 修复。
- 有 seed-paired CI、BH 校正、负对照、时间/空间 holdout、多场站复现和计算开销披露。
- window scan 与 history-delay upper bound 对上一轮最容易导致拒稿的攻击进行了直接回应。

### 提交级阻断

1. **[P0] 当前 PDF/ZIP 不是当前稿。** `paper_tste_ieee.md` 与 supplementary 更新于 2026-09-04，而两份 PDF 和 `artifacts/tste_submission/20260703_141452` 均为 2026-07-03。当前包不包含本轮关键证据。
2. **[P0] 数字一致性 guard 失败。** 当前审计为 `blocked_tste_number_mismatch`，44 项中 24 项失败。这里不等于正文有 24 个真实错误；主要原因是 guard 和其数据源仍指向 legacy 口径。但“最终提交 guard 不能验证最终稿”本身就是复现阻断。
3. **[P0] 构建链会回写旧稿。** `scripts/build_paper_ieee.ps1` 会先运行 `scripts/transform_ieee.py`，而后者仍从 `paper_draft.md` 生成旧标题、旧摘要与 legacy 数字；`prepare_tste_submission.ps1` 仍强制要求 `0.960`、`84.58M`、`88.13M`、`+0.764` 等旧 token。直接构建可能覆盖现稿。
4. **[P0] 现稿至少有四处可见矛盾。** 六步公平延迟增益应为 `0.9327-0.1959=+0.737`，正文却写 `+0.775`；A10c/正文把 86.54M 错说成劣于 95.13M；摘要/正文称 uncertainty bins “match physical-bin”，但 entropy-bin vs physical-bin 的 CI 为 `[+0.8k,+256k]`，严格说显著更差；Supplementary A6b 仍称 legacy checkpoint “used for the headline audit”，与正文/cover 的 train-only single-source 声明冲突。

### 统计与实验风险

1. 窗口扫描只有三随机种子，Kelmarsh 的方差较大；“every window passes”只按 mean NMI 判定，没有报告 pass-rate 或 CI 是否越过 0.20。
2. reserve CI 主要对五个训练种子做 bootstrap，刻画的是优化随机性；没有按日期/天气过程做 block bootstrap，无法充分覆盖时序相关与运营日变异。
3. 预测基线对核心 accuracy guardrail 已足够，但若把文章继续包装成 2026 年方法论文，缺少更近年的风电专用/概率预测基线仍可能被问。由于本文不主张 accuracy SOTA，这一项低于上面四个 P0。

## 五、Reviewer #3：TSTE 适配、运行价值与现实意义

**评分：Soundness 3/4；Significance 2.5/4；Overall 5/10；Confidence 4/5。**

### 优点

- 风电机组、控制边界和 reserve/imbalance-risk screening 均在 TSTE 可接受范围内。
- 论文没有把 proxy cost 写成市场收益，也承认 physical-bin 与低 RMSE backbone 可能更优。
- 多场站结果被限定为 boundary recoverability，不声称直接 reserve transfer，边界诚实。

### 主要质疑

1. **[高风险：场景成立性] “confirming threshold stream can be delayed”仍主要是合成压力测试，而非真实运行事实。** 公平退化和最坏情况上界证明了算法在所定义扰动下更稳，但没有证明真实 SCADA/质量控制链中这种延迟的频率、持续时间和经济后果。整篇 strongest headline 仍挂在这个场景上。
2. **[高风险：运营增量] reserve 结果是 validation-frozen empirical-quantile screening proxy，不是实际备用调度。** 这可以作为 bounded diagnostic，但很难单独支撑强运营影响；尤其 GWN/physical-bin 84.31M 和 modular 86.54M 均优于 proposed gate-bin 95.13M 的绝对值。
3. **[中风险：外部验证] 外部农场只验证 route signature，没有外部 reserve consequence。** 论文已经承认这一点，因此不是诚信问题，但限制了 TSTE significance 上限。

### Reviewer #3 建议

- 首选：用 Kelmarsh/Penmanshiel 的状态、限电归因或通道时间戳，报告真实确认延迟/缺失分布，并把 stress levels 对齐到经验分位数；
- 次选：若无法取得证据，把全文从“operating failure mode”降为“controlled deployment stress test”，删除对现实普遍性的暗示。

## 六、Associate Editor / Meta-review

### 共识

三位 reviewer 都认可：论文已不再是“只画 gate heatmap 的可解释性稿件”；负对照、多场站、窗口稳健性和公平退化让机制证据具备审稿价值。分歧集中在：这些证据是否证明必须把边界诊断嵌入 MoE forecaster，而不是放在更准确的预测器旁边。

### 裁决

**若以当前 PDF/ZIP 投稿：建议退回技术检查或拒稿。** 原因不是页面格式本身，而是上传资产过期、guard blocked、生成脚本可能重写旧稿。

**若只看当前 Markdown：建议 Major Revision，偏 Reject-and-Resubmit。** 现稿有足够结果进入外审，但模块化对照的方向错误会直接损害可信度，而真实运行场景未闭环会限制意义评分。新增窗口和 `Pab_std` 实验把上一轮三个 P0 中的两个变成已解决，却没有自动把录用概率推到 70% 以上。

## 七、P0：投稿前必须修复

1. **统一 source of truth 与构建链。** 让 `paper_tste_ieee.md`/supplementary 成为唯一主源，或把最新内容同步回生成源；更新 transform、supplementary generator、number guard 和 prepare token；重新构建 PDF/ZIP 后再验证页数与内容哈希。
2. **修四处显式冲突。** `+0.775 -> +0.737`；A10c/正文把 86.54M 改为“介于 84.31M 与 95.13M 之间”；把 blanket “match physical-bin”缩成逐策略结论；删除 A6b/正文中 legacy headline 的残余。
3. **解决 joint-vs-modular 核心必要性。** 最少补同口径的 modular posterior reserve 与 degraded-input 对照；若不补，主动降级贡献与标题/摘要措辞。
4. **给延迟场景真实 grounding，或把它明确降格为 stress test。** 不能继续同时使用“真实 failure mode”语气和纯合成证据。

## 八、P1：能显著提高录用率

1. 对 reserve 差异增加 day/block bootstrap 或滚动时间窗复验，区分 seed uncertainty 与 temporal uncertainty。
2. 对窗口扫描报告每个 seed 的 criterion pass-rate、CI 和最差 seed，不仅报告平均值。
3. 将外部农场中的至少一个推进到 reserve consequence，哪怕只做严格限定的 local recalibration audit。
4. 对 AI Use Statement 做 IEEE 政策口径复核：若仅语言编辑可简化；若代码或正文内容由生成式 AI 产生，应准确标识使用范围与程度。

## 九、最小可翻盘路线

| 顺序 | 工作 | 预计成本 | 能翻转的审稿意见 |
| --- | --- | --- | --- |
| 1 | 修 source-of-truth、数字和构建/提交 guard，生成新 PDF/ZIP | 低 | R2 的技术拒稿风险 |
| 2 | 同口径 modular posterior vs joint route 对照 | 中 | R1 的核心必要性攻击 |
| 3 | 真实延迟/缺失分布，或全文 stress-test 降格 | 低--中 | R3 的动机成立性攻击 |
| 4 | block bootstrap + window pass-rate | 低 | R2 的统计外推攻击 |

## 十、终审一句话

**这篇稿子现在的主要问题已不是“证据太少”，而是“证据没有证明必须使用联合路由”，外加提交资产仍停留在旧版本。先修构建与数字，再决定补 modular 等价对照还是主动降级贡献；否则新增的窗口和 `Pab_std` 证据会被一处简单的 86.54M/95.13M 方向错误抵消。**

