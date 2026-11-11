# 旧残差与后验缓存原生成来源追查

日期：2026-10-18。承接 [旧发布包勘误](../legacy_release_hash_audit_20261018/REPORT.md)。E07 保持未激活；本次不执行生产脚本、不推理、不训练、不校准、不重生成或替换结果。

## 结论与证据边界

**原日志及未提交入口源码的追踪取得部分闭合，完整原生成链仍为 UNKNOWN。** 找到了本地原任务日志、文件写入和补丁记录，并恢复了启动前的入口源码文本。provenance 所记 `621bb8b` 是当时仓库 HEAD，不能代表未提交的后验生产脚本；历史 `git status` 明确把该脚本列为 untracked。

这里的源码恢复只处理记录中的字符串与补丁，保存为 `.py…txt` 证据文件，不执行其中任何代码。文本 SHA256 指恢复后的 UTF-8/LF 载荷；不是补写一份当时运行文件的哈希凭证。原始编码、文件系统换行及未记录的外部修改没有被追认。

| 环节 | 本次证据 | 判定 |
| :--- | :--- | :--- |
| 残差入口源码与执行命令 | 原写入、一次键名修补、启动及成功完成记录；恢复文本与发布标签 Git blob 完全相同 | VERIFIED，限历史记录可追踪的入口文本与执行 |
| 残差日志与原元数据 | 五种子 × val/test × h1/h6 共 20 个两位 RMSE 标记相符 | VERIFIED，四舍五入一致，不等于数组逐位或哈希绑定 |
| 后验缓存首次写入 | 原初版源码、五种子提取及保存日志，随后成本恒等式断言失败 | VERIFIED；保留失败，不将失败缓存自动认证为正确 |
| 后验 provenance 的 HEAD 缺脚本 | 原 HEAD 输出及 untracked 状态；源码写入早于首次运行、首次提交晚于生成 | VERIFIED，HEAD 是仓库基线，不是该入口的源码快照 |
| provenance 对应的后续运行 | `--force` 日志读取旧缓存；恢复入口与 `4a79b09d` 首次提交版本一致 | VERIFIED，限入口及读取/写出路径；未将其改称缓存首次生成 |
| 原生成输出完整哈希、依赖、权重和数值环境绑定 | 原日志没有同时绑定输出 SHA256、源码/依赖/权重哈希及完整环境的凭证 | **UNKNOWN / NOT CLOSED** |
| Metis 上找到旧生成证据 | 已检查目录、日志和归档中的目标文件；命中均属于 2026-10 后期重放 | 在本次检索范围内未找到；范围之外 UNKNOWN |

## 残差：原生成日志及源码

原记录位于本地 Antigravity 会话 `0e90f7dd-c8dc-4a00-baca-113e8dfc066e`：

- 2026-09-18 **05:03:22 +08:00** 首次运行 `python scripts/build_fixed_forecast_residuals.py`，因 `regime_label` 键不存在失败。该失败输出保留于 [original_execution_observations.json](original_execution_observations.json)。
- 原记录随后把该键改为 `regime_primary`，并读取 `regime_primary_valid`。**05:03:33—05:05:16 +08:00** 的 `task-171` 以 exit 0 完成；[原日志快照](evidence/build_fixed_forecast_residuals.py_task171.log.txt) 明确记录 `cuda:0`、Python312 路径、134 节点、4261/4981 个 val/test 窗口、201—205 五种子及两个保存路径。
- [恢复的成功运行入口文本](evidence/build_fixed_forecast_residuals.py_before_step170.txt) 为 6513 个 UTF-8 字节，SHA256 `a5bc5888e59850fda9cdc910a0d8cafb45249f42f8f4d42de4d9bc15a35f065d`，与 `c9907798`、`621bb8b` 及发布标签中的该文件 Git blob 一致。`c9907798` 于 2026-09-19 首次提交该路径，晚于记录中的执行。
- 原日志记录的文件大小为 **165.38 MB**，与现存 173410167 字节的显示精度相容；这不是精确字节数证明。20 个已打印 RMSE 标记与现存元数据两位格式一致，见 [对照清单](residual_log_metadata_comparison.json)。

**没有**找到该次运行同时输出完整 NPZ SHA256、完整输入/权重哈希与环境版本的记录。因此可恢复入口文本并支持这次保存事件，但不能据此补造该次运行与当前 NPZ 字节之间的直接凭证。GPU 型号、当时 CUDA/PyTorch 等精确版本仍未绑定；不借用今天设备或环境填补。

残差原元数据本身没有 `git_head` 或执行源码快照字段；本次不向旧元数据补入提交号。

## 后验：首次生成与 provenance 是不同运行

原记录位于会话 `e2ab7379-d77a-424d-9247-1d5be42d6962`。下列时刻均为 **2026-09-22，+08:00**；事件清单同时保留原 UTC 时间。

| 时刻 / 任务 | 记录中的入口版本 | 原日志中的行为与结果 |
| :--- | :--- | :--- |
| 01:23:18，仓库检查 | HEAD `621bb8b5817483f54bfb7a51fcd0f9a0751fc542` | 记录仓库基线；还未写入后验脚本 |
| 01:43:01，写入脚本 | 初版完整源码载荷 | 原工具写入记录可恢复 |
| 01:45:12，task-126 | 启动前文本 SHA256 `e6d14dd05ace978748593be9e83bfec2bd37cfa3c2dee0faa9984368e28a5a40` | 提取 201—205 五种子，保存后验缓存；随后在 Transition seed201 的成本恒等式断言失败（exit 1） |
| 01:48:33，task-152 | 修正 float64 汇总及预算缩放后的版本 | **读取已有缓存**；后续因 `np.trapz` 缺失失败 |
| 07:33:45，task-170 | 进一步修补后的版本 | 读取缓存；后续 `sample_day_ids` 错误，保留失败 |
| 07:34:56，task-188；09:46:12，task-403 | 运行前文本 SHA256 `c809ff9e73af51b973cff04f3f5a4ed4276fd577b8ec2e16cf0e998327bbf21c` | 读取已有缓存，日志记录完成 |
| 07:41:12，git status | 后验脚本明确列为 **untracked** | 直接解释 HEAD 中不存在该文件 |
| 09:51:17，task-507，`--force` | 启动前文本 SHA256 `463f2a3d0ef9186010f091b622e85e0e7de1bce8a4865b850a432f9e3acafc91` | 仍**读取已有后验缓存**，写 provenance 并重算后续统计；日志记录完成 |

七份原日志（残差一份、后验六份）完整复制并绑定哈希，见 [original_log_sources.json](original_log_sources.json)。没有用成功运行覆盖失败日志。

现存原 `artifacts/matched_budget/provenance.json` 时间戳为 `2026-09-22T01:51:21.430134+00:00`，即 **09:51:21 +08:00**，落在 `task-507` 启动后约四秒。结合该日志的 “Loading cached posterior probabilities” 与 “Saved provenance” 及源码写入顺序，**INFERRED：现存 provenance 对应这次后续 campaign 运行的写出，而非首次缓存提取**。时间相符与内容顺序不是密码学执行凭证，故该精确归属保留推断标记。

该次 `--force` 入口的恢复文本与 **2026-09-25 的 `4a79b09d` 首次提交版本**精确相同；发布标签版 `5c809aec…` 只多了仓库根路径可配置化变更。首次提取入口则不是这两个后期版本。所有恢复版本和发布标签中的缓存存在性判断、读入及提取写出分支具有相同 AST，见 [cache_branch_comparison.json](cache_branch_comparison.json)；这不能证明导入依赖、权重或实际输出数值相同。

所以，provenance 中“脚本在提交中缺失”的原因已由未提交源码记录解释。**不能**把 `621bb8b`、`4a79b09d` 或发布标签单独当作首次缓存执行版本；也不能把 `--force` 理解为重新生成后验。启动前版本、命令、原记录行号及哈希均见 [recovered_source_versions.json](recovered_source_versions.json)、[source_recovery_events.json](source_recovery_events.json) 和 [git_source_bindings.json](git_source_bindings.json)。

## Metis、归档与检索完整性

- 本地项目、现存隔离克隆、整理隔离区及研究/归档索引根目录共盘点 51560 个文件；检查 1415 份候选日志和 320 个归档目录。编辑器历史未命中两个目标脚本；指定 Codex 2026-09 日期目录也未命中。Antigravity 全量会话日志的目标检索定位到上述原记录；Claude 项目中命中的是后期引用，未提供首次生成凭证。
- Metis 只读检查 `/home/junyu`、`/lstr/sahara/minlpml/junyu`，包括 `dsh-scratch`、`paper3_raw_replay_20261015` 和备份目录；盘点 212755 个文件，检查 1792 份候选日志、168 个归档目录，并对命中归档中 192 个目标成员完整计算 SHA256。目录遍历未报权限错误；一份后期 E05 输入归档报 “File is not a zip file”，保留在清单中，未修复或替换。
- Metis 归档内命中的两个生产入口均是后期修订版：残差源码 `bbcb11ec…`、后验源码 `9c622ead…`。没有找到原未提交版本的独立执行快照。
- Metis 现存后期残差为 **175752841** 字节，SHA256 `50499806cf6103d869086318858d9eb2cde89f99dac43c65917cc423572330a1`；后期后验为 **22412850** 字节，SHA256 `1c87d3627ddffbdf1106cdd7b1d29e17c3791810e01ec5e56c8ac1e2ef855b21`。两者均与旧发布成员不同，相关日志和凭证不能补作旧缓存的原生成证据。见 [后期重放身份清单](metis_later_replay_fingerprints.json)。

所有检索根、排除目录、文件计数、命中路径与失败均在 `local_inventory.json`、`metis_inventory.json`、两个 `*_log_search.json`、归档清单及 `supplemental_search_scope.json` 中记录。依赖安装、凭据目录、其他未挂载位置、已删除文件及其他机器不属于已完整核查范围；“本次未找到”不等于全局不存在。时间戳只作来源线索，不代替字节或执行绑定。

另对本地 Antigravity 规范全量会话日志逐一检索两个旧成员的完整 SHA256（忽略大小写），零命中，见 [historical_full_hash_search.json](historical_full_hash_search.json)。这进一步限定了原记录可支持的输出绑定程度，不改变历史 Git 清单已记录完整哈希这一事实。

## 保留的 UNKNOWN 与交付

1. 原生成当时的输出完整 SHA256、完整导入依赖与权重身份、GPU 型号及软件环境没有闭合。
2. 原写入/补丁日志支持启动前入口文本恢复，但不是当时运行文件和所有依赖的签名快照。首次生成之后到首次已知完整哈希清单之间的字节连续性仍未证明。
3. 本次没有重演旧运行、覆盖 provenance、补写原日志、重生成结果或改变风险门槛；旧发布勘误报告及其 UNKNOWN 记录保持原样，本报告作为后续补充。

新增 [证据清单](legacy_generation_evidence_manifest.json) 分别标注已恢复入口、已观察执行、后期版本绑定及缺失的输出链；文件保护与核验结果见 [verification.json](verification.json)。本次不升级科学认证，也不激活 E07。

核验结果：46 个受保护文件的前后完整哈希及大小一致，7 份原日志逐字节复制；18 个源码相关原记录行哈希和 8 个恢复文本通过检查。既有 E07 盘点测试 **8 passed**，两项既有科学/数字门禁通过。检查器曾遇到默认编码和证据文件创建顺序错误，修正为显式 UTF-8 及正确检查顺序后通过；原始数据与科学判据未改，尝试记录完整保存在 `verification.json`。

可用于文稿的有界表述：

> Historical command logs and recorded source edits identify the residual-generation entry point and distinguish the initial posterior-cache extraction from later cache-consuming campaign runs. The provenance HEAD denotes a repository baseline with an untracked producer script. Complete generation-time output, dependency and environment binding remains unverified.
