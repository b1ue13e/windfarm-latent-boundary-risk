# 辅助预测与旧残差 yhat 的非精确差异追查

日期：2026-10-18。**E07 保持未激活。** 本次只读取已有预测、权重文件、源码及日志；权重以 `torch.load(weights_only=True, map_location='cpu')` 安全读取元数据和张量指纹，没有实例化网络、调用 `load_state_dict` 或 forward，没有重新推理、训练、校准或改写原结果。

## 结论

**已核实一个执行条件差异：辅助预测按 batch size 16 评估，旧残差入口指定 batch size 64。** 差异形态与浮点执行路径差异相容；记录中的坐标、数据定义及该模式的有效源码分支没有显示相应的不一致。**但不能只凭这些只读证据，把 batch/浮点效应与未记录的历史权重、输入或环境变化唯一分离。最终原因仍为 UNKNOWN，10/10 组保持非精确匹配。**

没有用绝对误差、相对误差或 ULP 范围新增“通过”阈值，也没有把辅助档案替换成残差包中的 yhat。

## 差异的直接描述

比较辅助 `pred.npy[:, :6, :]` 与旧残差 `yhat_{split}_seed*`，均为 float32，坐标和目标/掩码的前次精确核验记录保持不变。下列数字只描述差异，不能作为因果识别或匹配放宽标准。

| Seed | val 最大绝对差（kW） | test 最大绝对差（kW） | val / test 最大 ULP 距离 |
| :--- | ---: | ---: | :--- |
| 201 | 0.0008544921875 | 0.000732421875 | 28 / 17 |
| 202 | 0.000732421875 | 0.000732421875 | 20 / 18 |
| 203 | 0.00347900390625 | 0.0008544921875 | 57 / 14 |
| 204 | 0.0008544921875 | 0.0008544921875 | 23 / 75 |
| 205 | 0.00177001953125 | 0.0008544921875 | 61 / 19 |

十组的平均绝对差范围为约 `2.52e-5—4.42e-5 kW`；seed204/test 有 4 个元素的 ULP 距离超过 64，最大为 75。它们没有被剔除。全部预测值有限；非零差异的元素数量及六个 horizon 分项见 [run_v1/diagnostic.json](run_v1/diagnostic.json)。**严格字节匹配仍是 0/10。**

## 原权重：当前身份可核实，原执行关联未闭合

- 五份现存 `best_model.pt` 各包含 52 个状态张量，当前张量类型均为 float32，模式均为 `moe_phys_full`。文件完整哈希、逐张量指纹、模型配置、训练配置见 [current_checkpoint_inspection.json](current_checkpoint_inspection.json)。安全反序列化和张量字节读取不执行模型。
- 当前文件哈希与 **2026-10-15 05:28 UTC** 冻结协议中五个 `source_config_checkpoint` 的哈希 **5/5 相同**，见 [historical_checkpoint_hash_comparison.json](historical_checkpoint_hash_comparison.json)。这把当前文件绑定到该日期的静态记录，不能倒填为 2026-08-30 辅助评估或 2026-09-18 残差生成时的权重凭证。
- 原残差源码及任务日志确实指向同名 `trainweight_full_rerun_20260830/wtb_full_seed{seed}`；版本化训练源码则保存 best-state 后以该状态评估。路径和代码意图相符，但原日志没有同时保存实际读入权重的完整哈希，checkpoint 也没有与每份预测的生成事件直接绑定。
- 这些 checkpoint 不在本次检查的 `90528db0`、`621bb8b` 或发布标签 Git 树中，见 [checkpoint_git_presence.json](checkpoint_git_presence.json)。不能用代码提交号单独证明运行权重身份。当前目录还缺 seed203—205 的 `training_summary.json`；未重建缺失记录。

因此，“当前权重与后期记录一致”是 VERIFIED；“两个原执行实际用了完全同一组张量”仍为 UNKNOWN。

## 输入：可验证的现存一致性与未保存的现场

1. **当前元信息**：五个 checkpoint 内的完整数据 metadata 与现存 `cache_strictmask_trainweights/wtb_245d/metadata.json` 相同，包括特征顺序、归一化统计、split 边界、图配置和标签/类权重定义。没有发现这部分现存配置差异。
2. **当前数组副本**：trainweight cache 与其元信息所指 strict cache 的 12 个已查数组（features、feature_mask、physics、physics_model、edge_index、edge_weight、target、target_mask、regime_primary、regime_primary_valid、time_index、node_ids）完整文件哈希相同。该结果限当前副本，不能证明原执行时读入的文件没有换版。
3. **坐标证据**：前次审计中辅助 anchor、未来目标/目标 mask、issue validity 的 10/10 数组与残差/现存 cache 字节相同；本次绑定并保护了这些既有证据。没有发现这些显式字段层面的时间/节点错位。
4. **容易误用的输入参考**：辅助 `anchor_physics.npy` 的 10/10 数组与当前原始 `bundle.physics[anchor]` 字节一致，与标准化 `physics_model[anchor]` 则 0/10 一致。评估源码在 forward 完成后另从 **`bundle.physics`** 保存它；真正的模型输入由加载器从 **`physics_model`** 取出。这个命名相似的文件不是实际推理输入张量快照，不能拿它证明完整输入一致。

历史 `x_hist`、特征掩码、图边/边权及标准化 anchor 输入没有随两套输出逐批绑定；归一化 metadata 相同和当前副本一致不能取代这些现场哈希。因此，未记录的输入版本变化或输入层坐标变化仍不能完全排除。

## 批大小与源码版本

辅助十份 `metrics.json` 均记录 val `4261 windows / 267 batches`、test `4981 windows / 312 batches`；在完整、不丢尾批的加载器下，整数 batch size 唯一为 **16**，也与五份 checkpoint 的配置一致。旧残差找回的启动前源码显式指定 **64**，其完整窗口数也与日志相同；日志没有逐批输入哈希，故将 64 描述为源码设置，不伪称另有实际批次凭证。

| split | 辅助记录的批次数 / batch16 尾批 | 残差源码 batch64 对应批次数 / 尾批 |
| :--- | :--- | :--- |
| val | 267 / 5 | 67 / 37 |
| test | 312 / 5 | 78 / 53 |

这是一项真实的可核实条件差异，但本次没有运行 batch16/64 的模型对照，不能把差异全部归因给它。

两边配置的 worker 数均为 0、评估不 shuffle；辅助训练入口的 DataLoader 工厂指定 `pin_memory=True`，残差入口未显式设置该参数。该代码差异也只作执行条件记录，不被追认为已证实的误差原因。

原文档把辅助评估的代码基线记为 `90528db0`；残差入口对应后来的源码。两版本的 `train.py`、`evaluate.py`、`data.py`、`utils.py` 和 checkpoint 加载辅助一致；`model.py` 文件本身不同，新增了 `dense_classifier` 分支。针对五份记录中的 `mode=moe_phys_full` 静态消去该非适用分支后，**整个模块 AST 与旧版一致**。这是该模式的源码契约比较，不是原机器实际执行源码/依赖的字节凭证。完整旧/新文本和哈希保留于 `source_snapshots/` 与 [source_versions.json](source_versions.json)。

两条评估入口均请求 `model.eval()` 和 `no_grad()`，均先输出 24 步、再比较前六步；没有显式评估 autocast。训练循环使用 AMP，但这不能被改写为两套已存评估结果分别采用 FP16/FP32。今天读到的参数和输出类型也不能恢复当时所有 GPU 中间运算设置。

## 数值环境：新增的部分直接记录

找到了残差生成前约七分钟、同会话 **2026-09-18 04:56 +08:00** 的原检查输出：**Python 3.12.10、Torch 2.11.0+cu128、CUDA available=True**；残差 task-171 另直接记录 Windows Python312 路径和 `cuda:0`。见 [original_extraction_observations.json](original_extraction_observations.json)。这比只靠当前机器版本更强，但不是每次 forward 的完整运行凭证。

辅助档案的旧文档记载源于 grokking 的 `/root/paper3_audit_rerun_20260830`，以及一个 HPCX/UCX 环境修补；未找到其完整 GPU、驱动、PyTorch/CUDA/cuDNN 版本记录。一次只读 SSH 检查在严格主机身份校验阶段失败，**未访问原远端文件系统、未修改信任配置或绕过校验**，见 [access_scope.json](access_scope.json)。该原端权重与环境复核仍有缺口。

两次实际执行的 TF32、确定性开关、cuDNN/CUBLAS 后端选择、GPU 型号和驱动均未完整绑定。不能把当前权重检查器的 Torch 版本当作辅助评估环境，也不能凭 `cu128` 构建标签补出当时驱动或实际数值开关。

## 归因与认识论状态

| 判断 | 状态及依据 |
| :--- | :--- |
| 10/10 不精确，差异量级与 ULP 分布如上 | VERIFIED，直接保存数组比较；没有放宽标准 |
| batch16 与残差源码 batch64 不同 | VERIFIED，配置/批次数及找回源码；不是因果消融 |
| 已查显式坐标、目标/掩码和当前元信息没有相应错位 | VERIFIED，限定现存字段；不能扩张到全部历史输入 |
| 已比较源码在记录中的 MoE 模式下公式相容 | VERIFIED，静态条件化比较；不是执行现场证明 |
| 浮点执行路径/批大小是合理候选解释 | INFERRED，差异形态及条件差异支持；未做模型复算 |
| 差异已经唯一归因于浮点，历史权重/输入版本变化可完全排除 | UNKNOWN，缺原执行权重、输入和后端环境绑定 |

可用于文稿的有界表述：

> All ten saved prediction comparisons remain non-exact. A batch-size difference is documented, and the observed small float32 discrepancies are compatible with numerical execution differences. However, the original weight, input and backend-state bindings are incomplete, so the cause cannot be uniquely identified without additional contemporaneous evidence.

本次诊断中 **255 个受保护文件**前后完整哈希一致。旧预测、旧残差、权重、输入及既有审计记录均保留；E07 继续未激活，没有重新推理、生成替代预测或改变匹配/风险门槛。完整数组统计见 [run_v1/diagnostic.json](run_v1/diagnostic.json)，[汇总](summary.json) 和 [环境证据](environment_evidence.json) 分开记录直接证据、推断与 UNKNOWN。

验证：数值描述/批次/source 分支测试及既有对齐、记账、E07 盘点测试共 **26 passed**；两项既有科学/数字门禁通过。完整绑定见 [audit_manifest.json](audit_manifest.json)，最终校验见 [verification.json](verification.json)。这些检查没有把非精确比较或来源缺口改判为通过，也未升级科学认证。
