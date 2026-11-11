# 当前主张与独立证据

| 主张 | 状态 | 直接证据与边界 |
|---|---|---|
| 历史冻结的低资源策略可在独立年份满足要求 | VERIFIED，限定支持 | P1/HGB/q.95对冻结WPQ36/HGB/q.95平均成本非劣；+0.5641%，联合区间[+0.3575%,+0.7708%]，在2%内；所有实例风险上界≤6.2025%。不是成本优势或全族近优 |
| 独立年份中有限族资源最小性能够识别 | VERIFIED，次要能力 | 全q预声明分析识别P1/HGB/q.925，3日块2%下15个更小候选全部排除，1/7日敏感性一致。与主要q.95分开 |
| 历史程序已事前选中全q最小策略 | NOT ESTABLISHED | 主要q.95不在全q2%充分集合；不能倒换为事后q.925 |
| 各信息条件有普遍最小模型/传感器地图 | NOT ESTABLISHED | 有限已拟合策略、部分压力格、共同W/P预测、共享pitch和资源字典序限制；不覆盖全函数类、参数量或FLOPs |
| 复杂表示必要，或所有神经模型冗余 | NOT ESTABLISHED | 主阳性是简单策略的存在证据，未比较所有表征/架构；5%还保留并确认MLP并列 |
| WTB旧最小性负结果已被推翻 | FALSE | 旧420案例保持；来源、时间、族和拟合配方不同，不作同实验翻转或唯一原因解释 |
| 已建立现场安全/PCC采购价值 | OUT OF SCOPE | 合成到达/上游馈送、风机级替代损失、有限目标和近似时间推断；无现场交付或结算验证 |
| 可以按2025结果调参并继续称独立确认 | FALSE | 后续调整只能探索并寻求新确认数据；当前一次结果不可覆盖 |

证据身份：`result_evidence.tar.gz`、`recovery_verification.json`、实际历史/解封/评估review receipts；数值入口 `recovered/results/aggregate/primary.json` 与 `secondary_span*.json`，派生表 `derived/`。原始年份/物理数组/动作与权重保留在Metis。

可用于论文的限定文段：

> In the sealed-year confirmation, the historically selected single-step-power HGB policy met the predeclared two-percent mean-cost margin to its frozen full-information reference, with a maximum-instance risk upper bound of 6.20%. Its cost was higher by 0.56% (joint approximate interval 0.36%–0.77%). A separate preregistered capability analysis identified a finite-family resource minimum at q0.925, whereas the confirmed policy used q0.95. These findings support bounded low-resource decisions while distinguishing confirmation from retrospective minimality.
