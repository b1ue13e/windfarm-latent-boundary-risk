# 独立确认核心：只读选择逻辑审查

日期：2026-10-19。对象：windfarm_moe/independent_confirmation.py、tests/test_independent_confirmation.py 及复用的 near_optimal_set。本次没有运行模型或重采样，也没有解析2025或修改主实现。

## 结论

**VERIFIED（静态）：在“每模型先以历史选择一个q，再以这些冻结q策略构成主recipe家族”的定义下，未发现 possible-feasible 比较、空选择、并列或历史reference选择的致命逻辑错误。完整runner与新协议仍待审查，当前不是解封许可。**

- `historical_selection` 每模型选风险上界全实例合格且历史平均成本最低的q，成本并列按预先固定q顺序；无合格q则选末档诊断并标记不合格。
- 近优比较使用所保留家族中全部风险下界可能可行的策略；历史不合格不被直接当作真实不可行删除。
- `near_optimal_set` 返回空集或全部最小资源并列者，未通过实际成本/字节/耗时对资源并列者事后选赢家。
- reference 只由历史WPQ36/HGB或MLP的已选q确定；无合格reference时保留q.99诊断，`reference_historically_qualified=False`。
- `confirmation_verdict` 保留历史无选择；确认需要每个冻结候选的全部实例风险、相对冻结reference的配对成本上界，以及reference历史资格和确认风险通过。不允许从确认结果重新挑选候选。

## 需要在协议明确的有限族边界

原联合界虽覆盖全部q格，但近优步骤对子矩阵做切片，只与每模型历史选中q比较。因此完整主格的近优目标是45个recipe（22子集×2估计器+持续性），压力格是13个recipe，不是225/65个全q策略。

未选q可能仍有风险下界可行者。若主结论写成相对完整q族的近优，当前子矩阵会遗漏这些竞争者；若协议明确“冻结历史q后的recipe family”为主要估计对象，则该切片合法，完整q族仅作次要诊断。联合界覆盖更大族本身不能把近优比较对象自动扩大。

主确认只相对历史冻结reference作检验，不再检验2025的有限族最优性或必要性。历史选中的recipe集合也不能称为已识别的真实最小信息集。

## 待完整runner核对

1. 发布前模型训练成熟：末point-fit标签release必须严格早于最早forecast publication=policy issue−6。主实施者已说明将点训练上界额外提前六步并加断言，仍须看实际实现。
2. period-END跨年：主实施者已说明封存原六字段+seen，再逐字段比较2025边界；仍须看实际实现和解封前测试。
3. 在切片之前检查label数是q数整倍数、resources/风险/比值维度和期望seed数一致，避免元数据错位使模型或末尾q被静默遗漏。
4. `anchor_window`统一使用最小anchor41；新协议应明确此项，尤其point-fit只需要35步历史时，该实现比最小合法范围额外截去六个起始点。不得在解封后按效果更换范围。
5. 一次性解封入口绑定完整历史包与程序字节；主确认族和次要全族分开记录，历史空选择不由次要结果补选。

**阻断状态：上述第1/2项已被实施者接纳为设计要求，但完整runner/protocol未就绪前仍不能标记VERIFIED闭合。**
