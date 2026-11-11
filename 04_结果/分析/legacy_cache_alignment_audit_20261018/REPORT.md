# 旧后验缓存与残差：时间、节点和掩码对齐审计

日期：2026-10-18。**E07 保持未激活。** 只读取原源码、日志展示文本及现存数组；不导入模型或 Torch、不运行推理、不重生成缓存、不重估策略或 bootstrap，不改动结果和门槛。

## 结论分层

**VERIFIED（直接数组证据）**：旧残差的 anchor、未来六步目标、目标掩码及 issue 标签，与现存 WTB 缓存按原加载器索引取得的数组逐元素字节相同。五种子短缺数组与原公式也字节相同。没有发现这部分相对现存缓存的时间步或节点列错位。

**INFERRED（源码支持的预期顺序）**：后验生成入口请求顺序取窗、保留全部节点，再按时间优先/节点次序展平；其预期坐标契约与残差切出 h=6 后的展平顺序相容。代码请求这一顺序，是源码事实；将该契约套用到历史生成的每一个现存概率值，仍是推断。

**UNKNOWN（缺少直接绑定）**：后验 NPZ 没有 anchor、节点 ID、掩码或输入坐标哈希；没有找到同一 canonical 分类器目录下的带坐标独立概率参考。故无法在不重新推理的条件下认证每个后验值的实际历史时间/节点身份。长度正确、汇总精确复现和源码相容均不能填补这一缺口。

## 原加载器与生成入口的顺序

原源码及版本见 [source_versions.json](source_versions.json) 和 `source_snapshots/`。`data.py`、`arrival_feed.py`、`model.py`、checkpoint 加载辅助及预处理/评估源码在本次比较的 `c9907798`、`621bb8b`、发布标签和审计前 HEAD 中 Git blob 一致。原会话中还直接展示了加载器/模型的 **513 行文本**（含重叠行及末尾空显示行），与版本化源码逐行相同，见 [original_loader_observations.json](original_loader_observations.json)。这证明观察到的文本及版本关系，不是原运行全部依赖的执行时字节哈希凭证。

- `RegimeWindowDataset` 为每个 split 使用 `hist_len=36, pred_len=24`：anchor 从 `start+35` 到 `end-25`，升序、步长 1；历史窗口截至 anchor，未来目标为 `[anchor+1, ..., anchor+24]`。返回节点列时没有排序、压缩或按有效性筛选。
- 后验使用的 `UnifiedArrivalDataset` 包装同一基类，直接暴露其 `anchor_indices`。该入口设置 `delay_steps=0`，扣留 `Pab_mean/Pab_std`；包装器修改输入特征/特征掩码及 anchor physics，不修改 target、target_mask、anchor 或标签的行列顺序。**特征掩码与目标有效掩码是不同对象**，不能因扣留特征而擅自把目标掩码改掉。
- 两个生成入口的 val/test DataLoader 均指定 `batch_size=64, shuffle=False`。残差入口拼接 `(batch, horizon, node)`；后验入口拼接 `(batch, node)` 后 `reshape(-1)`，没有用目标掩码预先压缩概率。
- 消费端明确先取残差 `[:, 5, :]`，再展平，得到 `(time,node)` 顺序；没有把六个 horizon 混入概率的一维索引。后验是 **issue 时刻 anchor 的状态条件量**，对应风险目标则在 `anchor+h`，不应把概率坐标误标为目标时刻 `anchor+6`。

源码定义的预期对应关系是：

\[
k=i\times134+j,\quad p[k]\leftrightarrow (a_i,\mathrm{node}_j),\quad
s[:,h-1,:][i,j]\leftrightarrow(a_i+h,\mathrm{node}_j).
\]

审计输出中的 `derived_coordinate_sha256` 只是按此规则计算的**预期坐标摘要**，不是随历史概率保存的坐标凭证，不能追认为概率逐值绑定。

## 残差数组的直接核验

本次绑定的是旧发布残差 `b05b3751…` 和旧后验 `d40f0ddb…`；不是当前 E04/E06 的另一套 receipt-bound 数组。

| Split | 原 anchor（含端点）/ 窗口数 | issue 的匿名 Day/时刻范围 | h=6 目标的 Day/时刻范围 |
| :--- | :--- | :--- | :--- |
| val | 25955—30215 / 4261 | Day181 05:50—Day210 19:50 | Day181 06:50—Day210 20:50 |
| test | 30275—35255 / 4981 | Day211 05:50—Day245 19:50 | Day211 06:50—Day245 20:50 |

现存 `time_index.npy` 与 `(index//144+1, index%144)` 全量字节一致，`node_ids.npy` 为 1—134。这里验证的是数据内部的匿名 Day/10 分钟 slot，不能由此认证真实日历日期、时区或历史设备时钟。

- **目标与掩码**：各核对 **7,430,568** 个元素，全部 horizon 的 `ytrue[i,h,j]` 与当前 cache 的 `target[a_i+h+1,j]` 字节一致，mask 与对应 `target_mask` 也字节一致。没有使用数值容差或忽略 NaN。
- **issue 标签**：`z_label` 与 cache 的 `regime_primary[anchor]` 经原加载器规定的 int64 类型转换后字节一致；不是未来标签。
- **短缺内部一致性**：5 种子 × 2 split 共 **37,152,840** 个元素与原 `max(yhat-ytrue,0)*mask` 公式字节一致。该结果只证明当前存储字段的内部关系，不独立证明当时模型推理的真实节点身份。
- **节点列证据**：134 列跨 val/test 的完整目标/掩码指纹互不相同，且与现存 cache 列逐列相同，支持残差中目标/掩码的列位置对应。把这些列称为 TurbID 1—134 还依赖 cache 声明及预处理规则（`TurbID-1`、位置表按 TurbID 排序）；本次没有重新流读原 SCADA 或补造生成时的节点快照。
- **反例检查**：将目标索引错误增加一步，val/test 分别有 2,398,618 / 2,597,664 个元素字节不一致；逆置节点列则为 2,670,036 / 2,971,464。说明本次检查可以识别同形状的真实索引差异，不是只比长度或总和。未保存任何被错排的数组。

## 掩码角色与 NaN

原残差生成器保存的是未来目标掩码；它虽读取 `regime_primary_valid`，并未将该字段叠入残差 mask。后验存储全窗口、全节点概率，也不附带目标掩码。旧 matched-budget 在消费端另外定义：

| h=6 支持 | val | test |
| :--- | ---: | ---: |
| 全窗口 × 节点 | 570974 | 667454 |
| 未来目标有效 | 383102 | 408939 |
| 未来目标及 issue 状态均有效 | 318779 | 385205 |
| 目标有效、issue 状态无效 | 64323 | 23734 |
| **原消费端实际选用** | **383102：只用目标 mask** | **385205：目标 mask AND issue valid** |

这项验证/测试支持不对称是原源码直接定义的事实，**不是数组时间错位的证据**。它改变了进入历史验证分箱与测试评估的样本支持；对校准和最终决策结论的影响在本次未检验，保留 UNKNOWN。没有把两边改成共同 mask，也没有删除不利样本。

原公式中 `NaN*0` 仍为 NaN。六个 horizon 合计，val/test 的目标和每个种子的短缺数组分别有 **20082 / 8868** 个非有限值；它们在字节比较中保留。h=6 每种子分别为 **3346 / 1477** 个，均在目标 mask 外；**所有六步、全部五种子的有效目标掩码内非有限短缺计数均为 0**。本次没有置零、插补或用 `equal_nan` 替代字节一致性。

## 辅助存量档案：保留精确不匹配

另读取 `trainweight_full_rerun_20260830/wtb_full_seed*/{val,test}_metrics/` 的已有数组，不运行模型：

| 字段 | 严格比较结果 |
| :--- | :--- |
| anchor、目标前六步、目标 mask 前六步、issue validity | 各 10/10 份数组字节一致 |
| issue 标签 | 原档案 int16、残差 int64，**原字节不匹配 10/10**；评估源码明确以 int16 存储。另行作显式无损整数扩宽后，标签值 10/10 相同；未将其改称原字节一致 |
| 原档案预测前六步 vs 残差包 yhat | **0/10 字节一致**，最大有限值差 **0.00347900390625 kW**；不放宽精确匹配标准 |

标签的两个比较结果分开保留于 [label_value_comparison.json](label_value_comparison.json) 和主数组记录。预测差异原因没有闭合，不因差值较小就认定为同一次输出，也不将其认定为节点错位。它不能充当 yhat 或后验的独立精确坐标凭证。原预测、残差及旧结果未改。

canonical 后验分类器输入目录本次只找到五个 checkpoint，没有 `.npy/.npz` 的概率/anchor 辅助档案。此结论限清单列明的目录，不等于所有未检索位置都不存在参考。

## 为什么长度和先前汇总复现不能升级证明

现存后验 10 个概率数组的长度、float32 类型及有限性均相容；源码也要求相同的窗口/节点顺序。但没有随这些值保存坐标，故无法仅凭这些检查排除历史取窗/节点置换或输入版本变化。

先前 **90/90** 个基线备用/短缺/成本字段精确复现，是记账及同一输入上的程序重建证据，不是独立的概率坐标证据。若把两个不同概率在同一后验分箱内交换，备用动作可以逐点完全不变，所有这些汇总也不变，而概率的时间/节点身份已变化。本次只用合成小数组测试这个非唯一性反例，没有置换原概率缓存。

| 待确认主张 | 证据层级 | 本次允许的判断 |
| :--- | :--- | :--- |
| 残差目标、目标掩码、issue 标签与现存 cache 坐标一致 | 全量直接数组字节比较 | VERIFIED，限这些字段及现存 cache |
| 后验预期与残差 h=6 切片采用相同时间/节点展平顺序 | 原入口、加载器、观察到的源码及长度 | 源码契约 VERIFIED；实际历史逐值应用 INFERRED |
| 每个现存后验值的真实历史坐标已认证 | 缺概率自身坐标或同条件独立精确参考 | UNKNOWN |
| 原预测 yhat 与辅助预测档案是同一次逐位输出 | 10/10 存在非零差异 | 不支持；差异原因 UNKNOWN |
| 数值汇总一致可以认证全部坐标及生成来源 | 分箱内交换反例表明不可识别 | 不支持，不能升级科学认证 |

可用于文稿的有界表述：

> The stored residual targets and masks agree elementwise with the current cache under the recorded anchor and horizon indexing. The source code specifies a compatible time-major, node-minor posterior order, but the probability-only archive does not provide direct per-value coordinate provenance. Matching lengths and aggregate decision metrics therefore do not certify its historical alignment.

## 产物及保护

独立脚本：[audit_legacy_cache_alignment.py](../../scripts/audit_legacy_cache_alignment.py)；主数组核对：[run_v1/alignment.json](run_v1/alignment.json)；[汇总](summary.json)；原加载器展示文本与 Git 快照另有哈希和行号清单。脚本只用 NumPy 读取和索引数组；源码作为文本/AST 证据，不执行生成入口。

本次数组核查内 **161 个受保护文件**前后完整哈希一致。既有三轮旧来源/数值审计、原始数组与辅助预测档案、失败记录及 E07 协议均保留。E07 空绑定不变，未校准、未推理、未重生成，门槛与原选择结论不变。

验证：对齐/NaN/置换反例测试、先前记账测试及 E07 数据盘点测试共 **21 passed**；两项既有科学/数字门禁通过。测试不把不精确预测参考或缺坐标概率改判为通过，完整生成链和后验逐值对齐仍为 UNKNOWN。证据绑定见 [audit_manifest.json](audit_manifest.json)，最终校验见 [verification.json](verification.json)。
