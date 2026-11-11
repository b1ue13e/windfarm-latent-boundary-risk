# 全历史实际归档与冻结包独立复验

**VERIFIED：550/550历史worker及实际历史冻结包复验通过，未发现未闭合的历史来源/任务绑定阻断。** 已实际调用部署的 `validate_freeze(args,cfg)`，不是仅检查实现review或根据作业提交推定成功。本代理未释放任何作业，也未打开、列成员、解析或读取2025测量内容。

远端根目录：`/lstr/sahara/minlpml/junyu/independent_confirmation_20261019_v1`。全历史实查时间为2026-10-19 04:27:50—04:28:26 UTC；冻结包验证时间为04:29:25—04:29:32 UTC。源码部署commit仍为 `24153f857bb0f1e62b041cd5924c2d3bae562f44`。

## 全历史闭合

- 550个任务的3,240个归档成员逐项实际大小及SHA256匹配，错误为零。receipt任务、阶段、状态、seed、超参数、MLP设置和源码/协议均匹配冻结任务表。
- 五seed201—205各110个任务；合计HGB260、MLP260、Persistence30。缺pitch225个worker，另外五条件各65个worker。
- 每seed的360,000个学习样本索引在全部子集、估计器及条件之间SHA一致；每个seed的代表数组另查360,000个唯一且范围内索引，全部对应真实历史有限训练目标。
- 直接从已绑定历史源和prepared selection坐标/预测，按冻结公式计算目标、有限性mask与shortfall身份；550份metadata的anchors/forecast/true/mask/shortfall五项identity全部一致。184个自然UTC日块的ID及有效分母亦逐worker、逐q精确一致，共554,408个有限目标。
- 五档offset均有限且非递减，既存日块violation数均在0至对应有效分母之间。本次没有重新生成模型预测、offset或bootstrap。
- 260个MLP拟合均保存80轮有限训练损失，末轮损失均低于首轮。此项仅验证训练记录完整，不能认证优化饱和或泛化质量。
- prepared的8成员再次通过实际大小/SHA验证。核对期间源码未变，历史源实际SHA与全部worker receipt所消费输入一致。

## 实际冻结门禁

PBS `244730.cm` 的chosen状态为 `COMPLETE`，`uses_confirmation=false`。部署runner的 `validate_freeze` 已实际通过，因此下列实际绑定同时闭合：preflight来源/协议/commit及成功PBS记录、deployment、独立review状态及56项实际来源、prepared、550个历史manifest及其全部成员、历史源、choices与freeze。

| 文件 | 实际SHA256 |
|---|---|
| freeze.json | `c04710efaa9e57b250906a9626c31e5a83559b4cfd30b6a18df2a489a39c7595` |
| choices.json | `358e0884ea36c86f98518a3f4ba5b3902716c60b27c476a93536203f689ada29` |
| chosen/manifest.json | `767ce326d10a769bd39b0434e5407f88520a7f05167ee3ae2313baf237d63d32` |
| execution protocol | `27ba6498427ca425978f6674f013862ba272049f778562cb839969cb7f3bbc33` |

历史联合族为74,500坐标，已存critical为3.981355396946885。本审查只消费既存bounds，未重算重采样。近优目标为历史先定q后的45/13个recipe；完整225/65个q策略是另一个对象，不能混用。

## 已冻结历史集合与参照

以下为历史3日块选择输出，**不是2025确认效果**。所有列示候选q均历史合格；各条件冻结参照均为历史合格的 `WPQ36/HGB/q0.95`。

| 条件 | 2%集合 | 5%集合 | 2%候选五实例最大风险上界 |
|---|---|---|---:|
| pitch_withheld | P1/HGB/q0.95 | P1/HGB/q0.95；P1/MLP/q0.95并列 | 0.078654554 |
| fresh | P1/HGB/q0.95 | 同2% | 0.078679641 |
| delay1 | P1/HGB/q0.95 | 同2% | 0.079316939 |
| delay2 | P1/HGB/q0.95 | 同2% | 0.080192803 |
| delay3 | P1/HGB/q0.95 | 同2% | 0.080540211 |
| delay6_stress | Common/HGB/q0.95 | 同2% | 0.091048895 |

主确认只使用pitch_withheld历史2%集合及其冻结参照：

- 候选 `P1/HGB/q0.95`，资源元组 `[1,1,5]`；历史联合界所需相对容限为0.018143240（约1.8143%），小于预声明2%。这不是点成本下降幅度。
- 参照 `WPQ36/HGB/q0.95`，历史五实例风险上界最大0.078696606，资格flag为true。
- 5%敏感性增加的P1/MLP保留并列，其历史所需相对容限约2.5685%，不属于2%主要确认集合。

缺pitch的45个历史定q recipe以及其他条件各13个recipe均历史风险合格，且均保留在相应possible-feasible竞争者集合中。历史选择没有空集，但程序的空选择分支仍保留；不能因此删掉弃权规则。

P1在fresh/delay条件还共享合法到达的pitch历史；delay6的Common同样包含合法pitch历史。表中这些名称不能解读为跨所有条件均只消费P或不消费遥测。共同forecast本身也依赖历史W/P。

## 认识论边界与后续

本次证明的是实际历史包与冻结程序/选择的来源一致及规定的历史判据结果，不证明候选真实最小、2025效果、bootstrap无条件覆盖或部署安全。64并发与16并发的调度变化不改变冻结数值程序；本审查没有修改调度或单独认证其资源调度属性。

两次实查均未发现 `UNLOCK_EVENT.json`。本代理没有执行qrls或解封动作。后续若主执行者按用户授权推进一次确认，必须继续使用此冻结包并让既有解封门禁再次核对；任何来源/协议/模型变动应停止并重新审查，不能根据2025表现改选或重拟合后继续称作原确认。

## 机器证据

- `full_history_actual_receipt.json`：完整550任务及逐项检查摘要；SHA256 `44303ca3a4314f6ac3e4657e48f0f6fb866e9d6844f0678d23e312fdde25f451`。
- `full_history_freeze_receipt.json`：部署validate_freeze实际通过及各条件冻结集合/逐实例风险；SHA256 `297cb47b8f27f56bff5418801e916da1bc20966b75b7fc04e39adafbcc56db81`。

这两份机器证据是本次新增的只读审计记录，不改写任何原历史结果或失败记录。
