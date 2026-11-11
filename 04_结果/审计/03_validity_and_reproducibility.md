> 审计日期：2026-10-19，Asia/Shanghai。原始结果、正式稿件、科学契约、原门槛均未修改。VERIFIED=本次直接文件/算术核验；SUPPORTED=有界支持、未全链重现；TENTATIVE=待检解释；CONTRADICTED=有明确反证；UNKNOWN=缺少证据。

# 有效性、实现与复现审计

## 结论

**VERIFIED：最新compact证据在本轮全量日块后算术、文件身份、历史选择与保存界判定上闭合；未发现确定性实现阻断。SUPPORTED：主q.95在声明的固定参照下有界非劣。UNKNOWN：原数据端到端复现、联合界真实覆盖和现场备用交付。** 旧证据存在版本/统计语义冲突，不能因新研究通过而恢复旧主张。

## 已执行核验

|核验|实际结果|不能推出什么|
|---|---|---|
|`working/rigor/recompute.py`|5037成员哈希一致；550确认任务；点成本最大差2.84e-14、点风险差0；90判定一致|不是原动作/完整模型重放或区间重新生成|
|`working/rigor/ledger_points.py`|历史/确认各550×5q=5500行；1100日块前后哈希一致|q档位不是独立训练；种子不是独立天气|
|`recompute_primary_slices.py`|130个policy×seed×期间描述行；年均精确复现；12月度均值溢价−0.1178%至+0.9413%|月度是事后点描述，无新CI、不作确认|
|`run_validation.py`|41测试通过；科学gate PASS；77/77数字检查通过；独立归档gate PASS；受保护输入哈希一致|门禁仅认证测试/归档/表述一致，不认证统计覆盖/安全|
|本轮科研计算|未新训练、未推理、未校准、未重采样原科学数据、未访问远端|单元测试可在合成小数组上测试随机算法，不能与新实验混淆|

详细命令、时间、Python/NumPy/系统和哈希均见`validation/validation_receipt.json`及`working/rigor/*receipt.json`。测试的一个warning来自禁用pytest cacheprovider后cache_dir选项未识别；41项测试实际通过，无结果过滤。

## 发现/限制及影响范围

### V01 主要确认与次要最小性身份不能替换（VERIFIED，高）

`windfarm_moe/independent_confirmation.py:99`的`confirmation_verdict`仅检查历史固定候选/参照的绝对风险与配对平均成本比；`scripts/run_independent_confirmation.py:537`附近建主要14坐标，551附近另建全q能力族。主要P1/HGB/q.95成本67.020403，固定参照66.644430，溢价+0.5641%，近似区间[+0.3575%,+0.7708%]。5/5种子成本更高。该策略并非全q族2%充分成员；次要P1/HGB/q.925才被识别为资源最小，成本65.739232、风险U9.7699%。影响所有摘要、贡献、主表和图例：不得将q.925赋予“事前选中并确认”。

### V02 新判据不是原E04修复（VERIFIED，高）

原E04规定成本差、违约率差和绝对违约率三约束；新`confirmation_verdict`与`risk_frontier.py:65`的`near_optimal_set`只保留绝对cap和相对成本。后者已事前冻结，是独立新研究，不是违规放宽原E04；但新成功不检验原E04的相对违约率差要求。另场站、点预测、目标和候选不同。禁止把差异唯一归因于样本量、信息机制、校准或统计改良。E04原NO FEASIBLE POLICY不变。

### V03 资源字典序只描述下游增量输入（VERIFIED，高）

`independent_confirmation.py:32`的`point_features`已使用W/P各36步；21行附近common为预测、日内sin/cos、ID。49行`resource`按新增通道、预测器pass、原输入宽度排序。P1=[1,1,5]不是全系统只用一个传感器，MLP还加入缺失指示且参数量/训练耗时不同。`information_subset.py:20`在pitch可见条件共同加入pitch历史；压力格不完整。因此不证明全系统W/Q冗余、实际FLOPs最小或部署延迟已节省。

### V04 年度季节漂移下联合界覆盖未知（UNKNOWN，高）

`risk_frontier.py:25`循环日块抽样，`subset_inference.py`用最大标准化偏差构造近似界；主要14坐标、次要每块长74,500坐标。五冻结实例平均成本与逐实例风险共用天气抽样；这是避免伪复制的合理设计。20,000次抽样及1/3/7日一致不能证明年内季节/控制漂移下95%真实覆盖，三个块长也非单一联合95%事件。当前最小性识别是条件于近似界的结论。最小验证建议是预声明的覆盖/假最小率反证研究，非在2025换块长挑结果。

### V05 compact复现范围受限（VERIFIED/UNKNOWN，高）

`scripts/export_independent_confirmation.py:25`附近排除raw_actions、physical、fit_indices及模型。当前本地550确认目录只有metadata/receipt/manifest/blocks；受绑定的大文件主要留在Metis。本轮可以重算block→统计→判定，不能宣称CSV→模型→逐步动作的完整重现。原始CSV本地只清点，不为了审计再发起远端训练。

### V06 E02旧统计字段和裁决语义有已知错误（VERIFIED，高，旧族）

`scripts/run_exp02_zero_privileged_supervision.py:31–43`明文记录旧字段其实是`P(delta<=0)`，却用`delta<0 and p<.05`判胜，方向矛盾。当前代码改为`p_non_inferior`与四条件裁决。`artifacts/raw_replay_20261015_v2/exp02/results.csv`60行显示eps50的h6点配对均值差−113,225.657 kWh（3/5种子负），h1为−394,230.797（5/5负）。这反驳“所有版本均恶化”的读法，不证明稳定显著增益。本轮不重算联合CI；旧h6+3.435M仅历史。PROJECT H2“已被否定”应进入下一次文档裁决，不能用旧错误规则支撑。

### V07 延迟吸收率不可跨目标/总体通用（VERIFIED，旧族）

契约121行与稿件426行保留36.3%—66.5%的历史同条件诊断；更晚共同目标修正版`artifacts/raw_replay_20261015_v2/downstream_recovery_v1_attempt1/phase_aggregate/phase_scan_results_by_seed.csv`的h6/all/lag6短缺为21.344→22.410 MWh，算术吸收−4.99%；h1对应22.388→21.409，仅4.37%。两者不估计同一对象，不能视为旧数字抄错或改写旧CSV，更不能继续将历史趋势当冻结目标下普遍规律。需显式历史标签或注册裁决；本轮不更改科学契约。

### V08 跨版本叙事污染（VERIFIED，高，文档）

`PROJECT.md:53`仍将48.4%超额备用节约/中介分析列VERIFIED，科学契约Q2却禁止将风险权衡写为成本优越。`research-manifest.json`前部仍保留旧外场立意。旧E01 v4物理窗口错配已INVALID；`remote_j02/e01_output`还混有优化器实验。门禁通过未捕获上述全部科学语义冲突，说明门禁覆盖有界，不说明应削弱门禁。应保留旧记录、在后续授权稿件整理中增加版本/范围裁决。

### V09 掩码、历史来源和外场范围（SUPPORTED/UNKNOWN）

旧val/test issue mask定义差异、posterior历史坐标绑定和10/10辅助预测非精确差异在`analyses/legacy_*20261018/`已有冻结UNKNOWN。本轮未重算其影响，也不为其补造来源。外场只认deterministic限定分支；其Kelmarsh h6区间跨零、Penmanshiel成本惩罚，不能宣称普遍迁移失败或简单基线已认证最小。

## 时间与代码审查的正向证据

`independent_confirmation.py:14`的阶段窗口截尾，入口215–247附近额外提前point-fit六步，并检查最后标签publication26057<首预测publication26058；2024/25六原字段+seen比较在平均pitch前完成。fit、offset、selection各有不同历史阶段；标准化仅fit样本。候选目标/掩码/forecast身份一致。本次检查未见显式未来泄漏。实际原始时间语义仍由合成双馈送假设支持，无现场arrival日志。

完整Reviewer B和所有具体算法行号见`working/rigor/REVIEWER_B.md`。本报告提出的是审计裁决建议，不擅自升级/修改科学契约。
