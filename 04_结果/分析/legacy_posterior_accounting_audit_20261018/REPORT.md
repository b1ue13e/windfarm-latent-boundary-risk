# 后验首次成本恒等式失败：缓存影响与数值路径核查

日期：2026-10-18。**E07 未激活。** 本次只读取旧冻结数组和找回的源码/日志，做独立算术诊断；没有调用原生产脚本、加载模型、提取后验、执行 bootstrap 或运行 E07 校准，没有替换任何旧结果。使用的是旧 matched-budget 的残差及后验缓存，不是当前 receipt-bound E04/E06 输入。

## 结论

**现有证据支持数值算术问题解释，而不支持把该断言失败当作缓存生成失败。** 在现存旧数组上，原 float32 路径复现 seed201／Transition 恒等式不通过；使用找回的后续源码所采用的“减法前转为 float64”路径，保持原 `1e-4 kWh` 阈值，五种子的全部诊断单元通过。后续已归档基线 CSV 的 90 个备用、短缺及成本字段与该路径精确一致。

**历史首次运行的精确误差与缓存完整正确性仍为 UNKNOWN。** 原日志没有记录两个布尔检查各自的误差，也没有生成当时的缓存完整哈希、权重/依赖快照和精确 NumPy 环境。本文中的精确误差值属于本次现存数组诊断，不冒充历史运行输出。数值恒等式通过也不能认证后验模型、时间对齐、信息集或科学主张正确。

## 原执行顺序及缓存隔离

原初版源码 [before_step125](../legacy_generation_lineage_audit_20261018/evidence/run_matched_budget_frontier.py_before_step125.txt) 与 [task-126 原日志](../legacy_generation_lineage_audit_20261018/evidence/run_matched_budget_frontier.py_task126.log.txt) 相互对应：

1. 源码第 159—203 行先提取 **201—205 全五种子**的 val/test 标量后验；第 198 行调用 `np.savez_compressed`，返回后第 203 行打印保存成功。
2. 之后进入 Phase 1，构造 B/C 备用向量，按固定的同一掩码计算成本、备用和短缺。第 283—285 行检查两项 `abs(C - (R + 10U)) < 1e-4`。
3. 日志明确先出现五次提取及保存成功，再在 **seed201 的首个 Transition 单元**抛出断言。断言在结果行 append 之前；首个 `baseline_reproduction.csv` 写出在第 322 行，因此本次失败运行未执行该 CSV 以及后续结果的写出。不能据此断言目录中此前没有旧文件。
4. 成本函数没有文件写操作；断言后没有回写/删除缓存的异常处理。保存后的 Phase 1 只读取后验，分箱边界由新的分位数数组形成；成本汇总不反馈到模型或后验数组。故**就该代码路径而言，断言不通过不能回溯改变已完成写出的缓存**。

缓存写出分支在初版、float64 修补版和后续 `--force` 版中 AST 相同；历史 B/C 动作构造代码也完全相同。`compute_slice_metrics` 的改动仅是最前面两项输入选择改为 float64，剩余函数体相同。预算缩放另有修补，但不参与 Phase 1 的该恒等式检查。

原检查是数学记账恒等式：

\[
C=\Delta t\sum_i\{r_i+10\max(s_i-r_i,0)\},\quad
R=\Delta t\sum_i r_i,\quad U=\Delta t\sum_i\max(s_i-r_i,0).
\]

对同一组有限数值和同一掩码，实数运算下该恒等式对任意后验诱导的备用向量都成立。因此它不是后验校准或预测质量检验。**B 不依赖后验缓存，其独立检查也可能因算术精度失败。** 缓存中的 NaN 或其他错误当然可能造成别的问题，但本次须靠独立检查判断，不能从这个异常倒推。

## 固定输入的算术对照

使用原 `q*=0.90`、`rho=10`、`dt=1/6` 和原分箱公式，重新求值旧历史动作，仅用于隔离记账路径；不搜索参数、不拟合新策略，不保存替代动作或原格式结果表。这不是 E07 校准。各数值路径共享同一内存中的备用向量、短缺目标和掩码。

本次环境为本地 **CPU / Python 3.12.10 / NumPy 2.4.6**；该环境中 float32 数组运算、归约及归约结果乘 Python 标量均可保留 float32。原生成时的精确版本未绑定，所以不把本次标量提升行为追认为历史环境事实。

首次日志对应的 circular Transition 人群，seed201 的结果如下：

| 策略 | 原 float32 全路径的绝对记账误差 | 仅求和转 float64 | 减法前整体转 float64 |
| :--- | ---: | ---: | ---: |
| B（不使用后验） | 0.625 kWh | 0.0062281284481287 kWh | 0 kWh |
| C（后验条件） | 0.140625 kWh | 0.005321502685546875 kWh | 0 kWh |

原阈值始终是 **严格小于 `0.0001 kWh`**，没有采用旧单元测试中较宽的 `0.05 kWh`。仅提升归约精度仍会留下 float32 逐元素短缺/成本运算的舍入差异，不能把问题简化为只需更换求和器。

| 人群 / 每种路径 30 项（5 种子 × B/C × 3 切片） | 原 float32 失败数 / 最大误差 | 仅求和 float64 失败数 / 最大误差 | 减法前 float64 失败数 / 最大误差 |
| :--- | :--- | :--- | :--- |
| 原 circular 掩码 | 29/30；1.875 kWh | 30/30；0.0555496197193861 kWh | 0/30；1.862645149230957e-9 kWh |
| 后续 bounded 掩码 | 29/30；1.21875 kWh | 30/30；0.0555496197193861 kWh | 0/30；1.862645149230957e-9 kWh |

两种精度下，60 组对照的样本数及违约计数全部相同，单组成本最大绝对变化为 **2.180066427215934 kWh**。这只量化记账路径的影响，不是缓存正确性、总体校准或安全认证。

源程序初版到后续最终版还有独立的切片修补：circular Transition 为 **139684**，bounded 为 **139653**；Full 始终 **385205**。不能把后续过渡切片数值的全部变化都归因于精度修补，更不能把不同人群混在一起比较。

## 已写出的缓存和后续结果

- **当前缓存结构检查 VERIFIED**：10 个标量后验数组键齐全，五种子 val/test 长度为 570974/667454，均为 float32；ZIP CRC 通过，所有元素有限且位于 `[0,1]`。文件完整 SHA256 为 `d40f0ddbaee7f4a2c89dbacdfb05be0a858897f1ce02c648b989fb8a8037cbca`，与旧发布包身份一致。
- **缓存生成语义 UNKNOWN**：后验 NPZ 自身没有节点/时间坐标。长度和本次总体计数一致，不能独立证明每个后验与时间节点逐项对应，也不能证明生成时的模型、输入信息集、权重及环境正确。首次输出到现存字节的完整历史连续性仍未闭合。
- **后续基线数值 VERIFIED（旧数组范围）**：使用 bounded 掩码和 float64 路径，5 种子 × B/C × Full/Transition/Steady × 备用/短缺/成本，共 **90/90 字段**与现存 `baseline_reproduction.csv` 的浮点数值完全相同，最大绝对差 **0**；没有采用近似匹配来替代精确匹配。
- **后续记账一致性 VERIFIED**：直接读取基线、Frontier A 和 validation-calibrated Frontier 的已存 CSV，共 **1836 项**成本恒等式检查，在原 `1e-4` 阈值下全部通过；最大误差为 **3.725290298461914e-9 kWh**。这不验证前沿构造、bootstrap 推断、物理机制或成本优越性。
- **原失败保留**：首次运行没有产生可接受的 Phase 1 成果，不能把它改称完整成功运行。后续历史日志明确加载已有缓存；在 dtype 修补后 Phase 1 可以完成，但其他阶段仍有 `np.trapz`、bootstrap 变量等历史失败，原记录均保留。

因此，**在可核实的程序路径与现存数值上，失败来自下游浮点算术，未发现由该异常反向污染缓存、或把失败运行的成本字段写入后续 CSV 的路径**。将这一结论扩大为“缓存生成全过程已认证”或“后续所有结果均正确”，证据不足，仍为 UNKNOWN。

## Claim–Evidence 与保留边界

| 主张 | 支撑 | 状态 |
| :--- | :--- | :--- |
| 缓存写出早于断言；该异常没有缓存回写路径 | 原代码、原日志和静态结构检查 | VERIFIED，代码路径范围 |
| 当前输入可由精度差异复现检查失败，且 B 独立于缓存也失败 | 固定动作/掩码的三路径算术对照 | VERIFIED，本次环境 |
| 原历史失败精确等于本文 B/C 误差值 | 原日志未持久化各检查误差，环境未完全绑定 | UNKNOWN，不冒充原输出 |
| 后续基线 90 项数值与 float64 路径一致 | 现存旧数组与原 CSV 精确对照 | VERIFIED，不跨数据版本 |
| 缓存语义正确、所有后续结果或科学主张已获认证 | 缺生成时完整哈希与独立语义核验；恒等式不检验预测质量 | UNKNOWN / 不支持升级 |

可用于文稿的有界表述：

> The initial accounting assertion occurred after all five posterior arrays had been written. On the preserved legacy arrays, float32 arithmetic reproduces the assertion failure, including for the posterior-independent baseline; promoting inputs before arithmetic satisfies the unchanged tolerance and exactly matches the archived baseline fields. This supports a numerical-accounting explanation without certifying the cache's complete generation provenance or semantic validity.

## 产物、保护与验证

独立诊断脚本：[audit_legacy_posterior_accounting.py](../../scripts/audit_legacy_posterior_accounting.py)；完整算术表、环境和前后输入哈希：[run_v1/diagnostic.json](run_v1/diagnostic.json)；汇总与源码比较：[summary.json](summary.json)。首次检查器曾因 Windows 路径分隔符报错，在数值计算及产物写出前停止，修复记录见 `preflight_attempts.json`，没有改动原始资产。

本次诊断内 **99 个受保护输入**的前后完整哈希一致，包括两轮既有来源审计、旧缓存和残差、相关缓存元数据、旧结果 CSV 及 E07 草案。原始结果、历史失败日志、既有 UNKNOWN 与阈值均保留；没有改写旧审计记录，没有升级独立科学审查状态。

验证：新增算术/缓存/输出保护测试、既有 matched-budget 测试及 E07 数据盘点测试共 **19 passed**；两项既有科学/数字门禁通过。旧 matched-budget 测试中的宽阈值保持原样，本报告的 1836 项检查独立使用原生产断言 `1e-4`。最终绑定见 [audit_manifest.json](audit_manifest.json)，校验记录见 [verification.json](verification.json)。
