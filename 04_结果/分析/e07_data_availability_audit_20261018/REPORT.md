# E07 本地与 Metis 未查看窗口可用性审计

日期：2026-10-18（Asia/Shanghai）。**只读、结果盲化的数据身份审计；未运行预测、重校准或性能评价。**

## 结论

**VERIFIED（限定于已记录检索范围）：未发现符合 E07 的新 WTB134 时间窗口。** 本地与 Metis 原始 CSV 为同一 245 日数据的精确副本；本地 15 个、Metis 2 个 WTB 缓存均止于第 245 日。两端均没有覆盖 E07 所需完整时间轴的缓存或坐标已核实原始数据候选。

**因此没有绑定确认性数据清单，也未激活 E07。** `prospective_collection_spec_manifest_sha256` 保持 null；策略/校准包绑定字段也未冒充完成。E07 只增加了数据可用性审计引用、缺口及激活前的来源/未查看证明要求。风险门槛、窗口、主候选和校准配方均未改。

**UNKNOWN：** 未检索/未挂载位置是否另有数据、未来同一物理风场连续数据能否取得，以及任何新窗口的真实标签到达和此前访问记录。没有访问日志不等于“从未查看”。本结论不是对整台电脑、整个 Metis 或其他用户存储的绝对不存在证明。

当前正式审计清单为 `final/availability_manifest.json`，类型为 `AVAILABILITY_AUDIT_MANIFEST_NOT_CONFIRMATORY_DATA_MANIFEST`；不是可用于启动校准的测试数据包。根目录初次清单及其生成源码快照保留，最终结论与其一致。

## 1. 检索范围与盲化边界

本地：

- `E:\论文3`，包含 data、artifacts、archives、backups、scratch 等非排除子目录。
- `C:\Users\lidong\Downloads`。
- 查询的 `E:\data`、`E:\datasets`、`E:\数据` 当前不存在，已记录。

Metis：

- `/lstr/sahara/minlpml/junyu`。
- `/home/junyu/dsh-scratch`（实际解析至 `/nfs/ihfs/home_metis/junyu/dsh-scratch`）。
- 查询的该用户 data/datasets/Downloads 目录当前不存在，已记录。

不跟随目录符号链接；排除 Git、环境/包目录、模型下载缓存等。清单记录实际 roots、排除目录及读取错误；两端本次读取错误均为 0。

文件发现规则在 `scripts/audit_e07_window_inventory.py`：检查 metadata.json；WTB/SDWPF 命名 CSV 及相应目录中的 train/test/data.csv；相关命名压缩包和已知派生发布包；另列其他风场档案。非 CSV 的相关命名数据会记录需盲化跟进，本次没有此类异常。未穷举任意名称的匿名文件、所有嵌套压缩包或所有挂载卷。

只解释以下内容：路径/尺寸、哈希、JSON 身份字段、NPY header、node IDs、时间/anchor 坐标。原 CSV 仅投影 `TurbID,Day,Tmstamp`；不转换或统计 Patv 等结果列。哈希会读取字节，但不会据此解释目标值。发布包补充检查也只载入坐标数组，未载入 target/shortfall/posterior 数值。

本地有 315 个 CSV 文件名命中，其中只有一个具备本次检查的原始 WTB 时间/节点三列；其余多为已有派生报表，仅读头而非将它们误计为 315 个数据源。

## 2. 两端已存在历史来源的精确核验

| 项目 | 本地 | Metis |
|---|---|---|
| 原始文件 | `E:\论文3\wtbdata_245days.csv` | `.../paper3_raw_replay_20261015/wtbdata_245days.csv` |
| 字节数 | 334,304,460 | 334,304,460 |
| 原始 SHA-256 | `6cf7613a82c61bb5cf9fcbbf22e3f6c48165fa32021eb6f1905cb2b7af4d7667` | 完全相同 |
| 实际坐标行数 | 4,727,520 | 4,727,520 |
| 不同时间—节点单元 | 4,727,520 | 4,727,520 |
| 重复坐标 / 范围内缺失单元 | 0 / 0 | 0 / 0 |
| 原始节点标签集合 | 1—134 | 1—134 |
| Day 范围 | 1—245 | 1—245 |
| 全局十分钟索引 | 0—35279 | 0—35279 |

节点位置表两端均为 3310 字节，SHA-256 为 `15c19ceca43171dfda06e8de487d4d55eb116112904d77958aed7260c2f0d9fe`，与冻结来源记录一致。坐标文件、原始时间/节点矩阵和缓存节点顺序相符，支持**同一已有历史数据身份**，不支持“存在新时段”的结论。

本地 15 个 WTB 缓存的实际时间坐标均为 35,280 步、134 节点，末端为 Day245/slot143。Metis 两个 WTB 缓存（raw-recorded 与 train-weight cache）也一样。target 数组仅检查 header/轴长度，不读取其值。

## 3. 为什么现有其他材料不能绑定为 E07 新测试

| 材料 | 排除理由 |
|---|---|
| 两端原始 WTB CSV | 同一历史哈希，实际时间止于 245 日，没有新的预测期/padding |
| 本地 `cache_strictmask_future/wtb_245d` | holdout=`[30240,35280)`，对应 211—245 日；与已分析 E04 测试期重合，名称 future 不等于当前研究从未查看 |
| 其余 WTB 缓存 | 特征遮罩/分组/权重/切分变体，没有延伸来源时间轴 |
| 已发布派生 ZIP | 内含残差锚点 val25955—30215、test30275—35255，仍是旧窗口；缓存后验没有独立新来源的时钟/节点证明 |
| Kelmarsh / Penmanshiel / LHB | Metis 缓存节点数分别为 6/14/4；本地/远程档案属于其他风场，不能代替预定 WTB134 队列 |
| 更晚的文件修改/下载时间、重新编号 | 不证明观测更晚或此前未查看，不能通过改 Day 标签来填补缺失日期 |

本地另列 31 个、Metis 30 个其他风场 ZIP 档案，仅登记路径与尺寸，不打开其结果列。即使其中可能有尚未评估的时间段，也需要独立的新场站实验定义；本次不擅自替换 E07 场站或节点。

## 4. 精确数据缺口

E07 当前所需：

```text
新 issue anchors: 35280—40319（5040 个，逻辑上 Day246—280）
模型离线 padding: 40320—40343（24 个十分钟步）
合计缺少已核实时间位置: 5064
对应缺少时间×节点单元: 5064×134 = 678576
```

这里是原 WTB 相对索引，原 CSV 没有提供已核实的公历/时区连续映射。将来提供数据时还须证明：

1. 同一物理 134 台机组，与已冻结节点映射一致；相同节点数或标签重命名不够。
2. 新观测与既有匿名时钟的连续衔接；不得复制、重编号或人工填充旧数据。
3. 预定完整窗口和 padding；不得只挑表现好的时间段。
4. 对新窗口的采集/访问/已有分析记录，正面支持未查看状态；不能用“没找到日志”代替证明。
5. 标签、QC 的实际到达记录，支持历史校准在新预测起点前已经成熟。

当前策略/校准包 manifest 也尚未绑定；其中校准偏移本就未运行，这不应被写成一个已完成但失败的性能实验。

## 5. 旧发布包来源核验的额外缺口

派生包 `archives/windfarm_derived_artifacts_v1.0.zip` 整体为 195,613,174 字节，实测 SHA-256=`cf90924b1fead36317addabfcbee6aa6236bebc29889f8ce5dfd57466fc7fc22`，与旧发布文档一致。但内部成员的文档哈希与实测不一致：

| 成员 | 旧文档所列 SHA-256 | 实测 SHA-256 |
|---|---|---|
| fixed_forecast_residuals.npz | `b05b3751f45e2a2c1619623da3d038317769caec7d6a59b207eb4ea088e5d0d7` | `b05b3751f45e611e073d1dfe4c4545b9775ca625e3c76e85558328cfc30a49a9` |
| cached_posterior_probs.npz | `d40f0ddbaee7452d3a339dd8917e766fb31ec227242c7f078d46a48970e4e7e7` | `d40f0ddbaee7f4a2c89dbacdfb05be0a858897f1ce02c648b989fb8a8037cbca` |

**VERIFIED：哈希文档不一致；原因 UNKNOWN。** 记录在 `archive_coordinates_audit.json` 与正式清单，不改动旧文档、发布包或结果。此包本就不能提供 E07 新窗口，也不将此异常推广为当前 receipt-bound E04/E06 数据全部无效。

## 6. 预注册与清单状态

- E07 保持 `DRAFT_NOT_EXECUTED_PENDING_ACTIVATION_MANIFESTS`。
- 添加的是**数据可用性审计清单**及哈希，不是确认性测试集绑定。
- `prospective_collection_spec_manifest_sha256`、策略包/校准包绑定字段仍为 null。
- 协议的 data、frozen_objects、gates、calibration、evaluation 五个科学配置部分与更新前逐项相同；只新增 availability 审计元数据和更明确的激活证据要求。见 `protocol_update_attestation.json`。
- 清单中记录的协议输入哈希对应审计时的更新前版本，已按字节保存为 `protocol_before_availability_audit.json`；不是声称后来新增审计注释后整个协议文件仍未变化。

后续只有补齐并验证新来源，才可绑定确认性数据清单、封存参数并启动。现有 35 日仍不复用作新方案的确认性证据；不降低 v_max、置信要求、完整窗口、节点或来源要求。

## 7. 审计产物与认识论状态

| 命题 | 状态 |
|---|---|
| 本地/Metis WTB 原 CSV 为完整的同一 245 日坐标矩阵 | VERIFIED，哈希与坐标投影核验 |
| 已查 WTB 缓存能覆盖 E07 新窗口 | 否，所有实际末端均为 35279 |
| 旧 future/holdout 或派生发布包是未查看新数据 | 否，时间身份与旧窗口重合 |
| 已有符合 E07 的确认性窗口并成功绑定 | 否，绑定保持 null |
| 任意未查位置也绝不存在数据 | UNKNOWN，审计不作此断言 |
| 新校准有效、无效或已通过安全认证 | UNKNOWN / 未执行 |

主要文件：`local_inventory.json`、`metis_inventory.json`（两端元数据记录）、`archive_coordinates_audit.json`、`final/availability_manifest.json`、`final/candidate_rejections.csv`、`protocol_update_attestation.json`。

Metis 清单传回后的 SHA-256 与远端实际输出一致：`d84cd4e8439503494e8a463f6a9e57b57c6a63b5a269683a02cd435512c5816b`；两端执行的 collector 源码 SHA-256 同为 `c540e37406d4d5a66ebbaa417179a1e9a021157a6625773c2fd0e7f528f59061`。命令、主机、环境、UTC 起止时间及根目录在清单中。

本任务只进行了 CPU 文件/坐标 I/O，未训练、推理、拟合校准、计算结果分位数或运行新测试。时间/节点完整性统计不是模型性能统计；随机种子不适用于此确定性元数据检查。

验证：43 项相关测试通过，含目标 payload 禁读、CSV 身份列投影、padding、节点顺序、未查看状态、搜索错误和协议未激活检查；两项既有科学/数字门禁通过。门禁通过不替代新数据来源或未查看证明。

> The audited local and Metis copies contain the same 245-day WTB source and do not supply the registered later confirmation window. No confirmatory dataset was bound. Only identifiers, timestamps, shapes and cryptographic records were inspected; outcome values were not interpreted. This scoped availability result does not establish absence on unsearched storage or effectiveness of recalibration.
