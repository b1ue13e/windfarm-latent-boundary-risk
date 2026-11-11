# C-201 精确重建追查与五种子证据闭合

日期：2026-10-18（Asia/Shanghai）。范围：执行与数值证据核对；不重新训练、不改变原结果或风险门槛。

## 结论

**VERIFIED：C-201 的原日块样本数、违约次数和成本已精确重建。** 原 Metis 主机当前 A100 环境与本地 RTX 5060 各做两次固定重放，四次均有 35/35 块成本差为零，样本数和违约次数也逐块完全一致。没有使用误差容限、四舍五入、删块或阈值调整来判为通过。

**VERIFIED：新的完整汇总已闭合五种子 × B/C/D/D10 的 20 组策略，每组 35 块。** C-201 使用事先指定的 A100 第一次重放后验快照，其他种子重新执行原切片流水线；原精确核对全部保留。C 已进入新的完整五种子切片汇总。

**UNKNOWN：此前 4.256908416748047 kWh 差异的具体历史触发。** 那次未保存后验、分箱成员或完整成本差向量，因此本次不能把任何候选样本或 GPU 数值机制说成已证实的历史原因。历史失败记录保持原样；新重放闭合不抹除它。

## 1. 原执行源码与环境

从原 Metis 主机只读取回并核对：

- 原执行脚本 `test_strong_baseline_closure_e04_v4.py`：SHA-256 `657ee991381d5252b88243d12d64da08f92aeebef799e23f923bdfe15eac3b82`，与 J04 provenance/receipt 记载一致；本地保存为 `original_execution_source.py`。
- J04 源码快照：SHA-256 `a98916425abfd02a4996de6d16c60af32ac508204b1cc5f6f27bc5e21cb5796e`，与原记录一致；实际导入的模型、数据和配置源码另逐项验证。
- 原 stdout/stderr：保留计算成功及包装器后置检查失败的记录。原 stderr 的 post-check 失败没有被隐藏，也没有被改写成模型计算失败。

原执行脚本与本地 E04-v2 文件的差异仅涉及结果保存/目录组织及 import 排列；C 的后验转换、五分箱、箱内 0.90 分位数和成本计算相同。本次通过 AST 直接抽取并执行哈希绑定原脚本的 `get_probs` 至 Policy C 代码段，没有手改其分箱逻辑。

| 项目 | J04 历史记录 | 本次 Metis 重放 | 本次本地重放 |
|---|---|---|---|
| OS / Python | Linux；3.11.16 | Linux；3.11.16 | Windows；3.12.10 |
| GPU | 原命令为 cuda:0，历史逐项硬件记录不足 | A100-PCIE-40GB | RTX 5060 |
| PyTorch / CUDA | 历史记录未完整逐项绑定 | 2.11.0+cu128 / 12.8 | 2.11.0+cu128 / 12.8 |
| NumPy / cuDNN | 历史记录未完整逐项绑定 | 2.4.6 / 91900 | 2.4.6 / 91900 |
| cuDNN benchmark / deterministic | 未完整归档 | false / false | false / false |
| cuDNN TF32 / matmul TF32 | 未完整归档 | true / false | true / false |
| deterministic algorithms | 未完整归档 | false | false |
| Torch CPU threads | 未完整归档 | 128 | 4（此前本地诊断配置） |

这些当前设置不能倒推成历史 J04 的完整配置。两平台还同时存在 OS、Python、线程数差异，不能把平台比较解释为只改变 GPU 的因果实验。仓库顶层 `runtime.json` / `environment.txt` 描述的是本地环境，未冒充原远程执行环境。

重放权重 seed=201，显式记录 Torch seed=201 和 NumPy seed=20261021；历史初始化 RNG 未完整归档。两次重复是固定诊断，不根据结果增加次数或挑选数值配置。完整命令、环境、保护输入和输出哈希在各平台 `plan.json` / `manifest.json`。

## 2. 后验与分箱阈值核对

原训练/评估目录虽保存了 `val_metrics/gate_prob.npy`，其保存的 anchor pitch 通道有 567,973/570,974 个非零值，与本次桨距完全扣留的 E04 信息条件不一致。因此未用这些历史 clean-evaluation gate 冒充原 E04 后验。

本次四个重放均归档：完整验证/测试后验、五分箱边界、箱内备用分位数、验证/测试箱成员、备用向量、anchor 和 node IDs。

| 后验箱（0-based） | 验证有效 n | 测试有效 n | 备用 Q0.90（kW） |
|---|---:|---:|---:|
| 0 | 76,621 | 126,294 | 128.80987548828125 |
| 1 | 76,620 | 115,128 | 150.9319305419922 |
| 2 | 76,620 | 82,801 | 176.473388671875 |
| 3 | 76,620 | 44,916 | 281.41778564453125 |
| 4 | 76,621 | 16,066 | 227.30859375 |

四次的箱成员与上述备用分位数完全一致；最高后验箱备用低于前一箱是原经验校准的结果，未擅自排序或加入单调约束。

四个内部后验边界的本轮取值范围为：

```text
20%: 1.9614971336068263e-7
40%: [4.797634028363972e-6, 4.797639485332183e-6]
60%: [1.1383256205590531e-4, 1.1383260862203403e-4]
80%: 0.9996882915496826
```

外侧边界保持原 `-inf/+inf`，箱区间仍为左闭右开。这些边界数值并非全部逐位相同。相同设备重复运行也有数万后验元素发生末位变化：例如两次 RTX 测试后验有 21,320 个元素不同，最大绝对差约 `1.13e-6`；但本轮成员归属和最终备用向量都完全一致。**“后验逐位不可重复”与“本轮策略结果精确闭合”必须分开报告。**

此处无法与缺失的历史 J04 后验逐元素比较；精确闭合指原定义的日块样本数、违约次数和成本，不是宣称恢复了不存在的原后验日志。

## 3. 4.256908 kWh 的来源：已知事实与候选解释

旧记录为：`analyses/e04_regime_slices_20261018/closure_seed201.json` 中 C 成本最大日块差 `4.256908416748047 kWh`。该记录未被修改。本次四次固定重放均没有再次出现此差异。

当前后验中最接近 40% 分箱边界的一个有效测试样本为：

- turbine/node 20，issue anchor 31756，WTB day 221、slot 76（12:40），原块 11。
- 后验约 `4.7976436690e-6`，边界约 `4.7976340284e-6`，距离约 `9.6e-12`。
- 该样本 shortfall 为 0；相邻两箱备用为 150.9319305 与 176.4733887 kW。
- 用原 float32 成本表达式计算，相邻两箱在这个样本上的采购成本差**恰好为 4.256908416748047 kWh**；两种备用均不违约，因而理论上可能出现“违约数不变而成本改变”的模式。

**INFERRED：后验末位扰动与硬分箱边界的相互作用是值得怀疑的候选解释。** 这里没有扰动或改写任何实测后验、没有把样本重新分配后替换原成本，也没有为了复现失败而搜索开关。上述相邻箱成本计算仅展示一个与旧差异同数值、同类型的可能机制。

**UNKNOWN：历史失败是否发生在这个样本、这个日块、这个边界，或是否另有原因。** 数值吻合不足以证明历史事件身份。`boundary_candidate.json` 明确标记为候选，不能当作旧运行轨迹。其 `positive_margin` 使用 NumPy float32 标量相减；报告中的约 `9.6e-12` 是对该数量级的描述，不能将该字段当作精确 float64 差值。

## 4. 完整五种子证据如何闭合

新的 `reconcile_e04_c201_evidence.py`：

1. 验证四份重放档案的 manifest、后验文件和精确门禁状态。
2. 事先指定 A100 repeat1 作为 C-201 的后验输入，不按结果挑选快照；本轮四份档案本来也全部精确通过。
3. 验证后验的 checkpoint、anchor、node 身份，并由**未修改的原切片脚本**重建 C-201 的策略动作。明确记录其后验来源为 A100 档案。
4. 对其余种子执行同一原切片流程，再对五种子全部 B/C/D/D10 重验 35 块 n、违约和成本。
5. 只有 20/20 组全部精确通过，才生成完整汇总；任一组失败都中止完整闭合声明。

结果：`reconciliation/result.json` 为 `ALL_20_SEED_POLICY_CELLS_EXACT`；逐组清单在 `reconciliation/exactness_grid.csv`。五种子 C 已进入 `reconciliation/complete_summary/pooled_slices.csv`。此前只有四种子 C 的旧分析保留为历史版本，未覆盖或补写。

原始 E04/E05 的数值、日块、checkpoint、分位数规则、显著性水平与风险门槛全部不变。**原选择结论仍然是 `NO FEASIBLE POLICY`。** 数值重建闭合不等于安全可行性、后验逐位确定性或独立科学审查闭合。

## 5. Claim–Evidence 状态

| 命题 | 状态 | 边界 |
|---|---|---|
| 原源码与快照身份已核对 | VERIFIED | 与 J04 哈希记录一致 |
| 本轮 C-201 四次重放的原日块指标一致 | VERIFIED | 35/35 的 n、违约、成本逐项精确 |
| 新汇总具备完整五种子 C 证据 | VERIFIED | 20 组策略整体门禁通过；非历史后验逐位证明 |
| 当前后验浮点输出存在重复差异 | VERIFIED | 同设备重放可见，已归档 |
| 旧成本差由某特定 GPU 或 node20 跨箱造成 | UNKNOWN / 未证实 | 失败后验缺失，候选数值吻合不是历史归因 |
| C 策略已安全或选择器已有可行策略 | 不成立 | 本次只修复重建证据缺口，主选择结论不变 |

可用于论文/复现说明的英文表述：

> Exact reconstruction of the archived day-block sample counts, violations, and costs was recovered for all five seeds without changing matching tolerances or policy thresholds. Floating-point posterior outputs were not bitwise repeatable, although bin assignments and reserve actions agreed across the fixed audit repeats. The precise cause of the earlier reconstruction discrepancy remains unresolved because that failed run did not archive its posterior outputs.

## 6. 验证、归档与后续边界

- `python -m pytest tests/test_e04_c201_exactness.py tests/test_e04_regime_slices.py tests/test_e04_feasibility_diagnostic.py tests/test_e04_receipt_binding.py -q`：**29 passed**。
- 科学主张门禁：**PASS**；数字一致性门禁：**complete_tste_number_consistency**，输出到本次独立目录。
- A100、RTX 两套审计各自验证受保护输入前后哈希不变；完整五种子重建继续使用 38 项原输入保护及档案哈希校验。此前失败记录、旧分析和原科研结果均保持只读。
- 原科学契约与独立审查状态未升级。若今后要主张跨平台逐位可重复，须另行明确数值执行契约并前置归档；不能用本次结果倒填历史设置。
- 大型后验 NPZ 保存在本地的 `a100/`、`rtx5060/` 及 Metis 独立目录 `/home/junyu/dsh-scratch/e04_c201_exactness_20261018/a100/`；JSON/manifest 记录其哈希。Git 提交保留审计脚本、报告、哈希记录与聚合表，不提交原 SCADA 或大型后验张量。

复现入口：`scripts/audit_e04_c201_exactness.py --help`（各档案 `plan.json` 含实际完整命令）；五种子合并命令：

```powershell
python scripts/reconcile_e04_c201_evidence.py --evidence-dir analyses/e04_c201_exactness_20261018 --output-dir analyses/e04_c201_exactness_20261018/reconciliation
```

该命令仅允许全新输出目录。已存在的档案不能覆盖；重放或合并时需使用新的目录名。
