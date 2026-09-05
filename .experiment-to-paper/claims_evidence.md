# Claim–Evidence 映射（2026-09-05）

| ID | 状态 | 可用主张 | 证据 | 强度 | 禁止外推 |
|---|---|---|---|---|---|
| C1 | Observed | train-only router 的 WTB RMSE 为 229.93，较 iTransformer 高 5.59 | A6b、A13 | 中 | 不得称预测 SOTA 或优于强预测器 |
| C2 | Observed | declared MPPT/pitch boundary 可由受监督后验恢复 | train-only NMI/ARI 0.721/0.740；unconstrained NMI 0.014 | 强 | 不得称无监督物理发现 |
| C3 | Observed | 去除 Wspd/Pab 后边界 signature 仍存在，且标签置换后归零 | WTB 0.561 vs 4e-6；LHB 0.674/0.575 vs 1.92e-4 | 强 | 不得称识别了真实控制器因果状态 |
| C4 | Inferred | consequence channels 携带可学习的边界后果 signature | withheld-channel、Pab_std ablation、跨场结果共同支持 | 中强 | 不得把某一通道写成已识别的因果载体 |
| C5 | Observed | 在预定义公平退化协议下，routed posterior 比 rule 和 joint non-routed head 保留更高 recall | delay6 0.933 vs 0.196/0.286 | 强（协议内） | 不得声称所有真实 SCADA 故障下均鲁棒 |
| C6 | Observed | 独立 GBDT 也能保留较高 degraded recall | delay6 0.868、strong noise 0.804 | 强 | 不得声称退化鲁棒性为 MoE 独有 |
| C7 | Inferred | routing structure 对退化识别有增量 | routed 0.933 vs matched joint non-routed 0.286 | 中强 | 仍需注意输入/结构差异和外部复现 |
| C8 | Observed | joint soft posterior 在 WTB boundary band 优于 global quantile | -0.568M，CI [-0.726,-0.406]；Bonferroni 后仍过零 | 强（局部 proxy） | 不得称市场收益、OPF/UC/dispatch 最优 |
| C9 | Inferred | 定价信息更符合 joint-learning/shared-representation 解释，而非 routing 解释 | joint dense 16.076M 与 routed 16.065M 未检出差异；independent GBDT 17.656M | 中 | 未穷尽同容量、同调参预算的独立 posterior；不得写成因果定论 |
| C10 | Observed | clean complete observation 下 continuous pitch quantile 最优 | 15.538M，显著低于 joint soft 16.065M | 强 | 不能宣称 learned posterior 在干净观测下优于物理信号 |
| C11 | Observed | 外部场站 boundary signature 在异质观测条件下高于 shuffled chance | LHB、Penmanshiel、Kelmarsh；窗口扫描 4/4 通过 | 中强 | 不能写成随 pitch coverage 单调变化或自动跨场部署 |
| C12 | Observed | Kelmarsh 外部 reserve 增量未检出 | -0.04M，CI [-0.20,+0.13] | 强负结果 | 不得声称外部经济价值已验证 |
| C13 | Observed | hard route 在同一 router 上改善 global reserve proxy，但不赢强 backbone/physical control | 95.13M vs 99.55M；GWN physical 84.31M；router physical 93.82M | 中 | 不得跨 backbone 称策略优越 |
| C14 | Proposed | 联合学习相对匹配模块化 posterior 具有不可替代优势 | 当前不足 | 未建立 | 需要同输入、同容量、同校准预算与同日志责任链对照 |
| C15 | Proposed | 真实风场延迟/缺失会带来可量化运营收益 | 当前只有异步事件 grounding 与 synthetic stress | 未建立 | 需要真实延迟分布、事件级标签或外部 reserve consequence |

## 一句话主张锁

可写：**结果支持这样一种解释：联合学习使软边界后验与预测残差风险对齐，而路由结构使该后验在确认通道退化时保留边界识别能力。**

不可写：**MoE 自动发现了物理状态，并在所有场站以更低预测误差和更优备用策略取代现有方法。**
