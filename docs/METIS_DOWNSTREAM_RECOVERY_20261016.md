# Metis 下游恢复与并行运行 — 2026-10-16

当前仍为部分进展，不是整篇论文复现成功。新快照时刻为北京时间2026-10-16 08:19:50。

## 实际执行状态

| 项目 | PBS / 实际记录 | 当前可确认范围 |
|---|---|---|
| 通道消融、EXP02、EXP03 | core242628 F/exit0；三个执行收据均EXECUTED0 | 程序执行结束；数值、完整证据与论文结论尚待独立核对 |
| 匹配预算与ρ敏感性 | diagnostics242629失败前两个阶段各EXECUTED0 | 程序退出0，不代替动作/统计证据审计 |
| 原相位扫描 | diagnostics242629 F/exit1 | 完整失败归档，未认证、未覆盖 |
| 新相位扫描201–205 | 242793[0–4]均R | 五个种子在五张PBS分配GPU上运行，尚未结束 |
| 监督消融 | 242794 R | 独立GPU运行，尚未结束 |
| 有功功率审计 | 242795 R | 独立GPU运行，尚未结束 |
| 相位合并 | 242796 H，依赖新数组afterok | 正常等待；仅全部五种子及30条件/42弃权单元每种子齐全才合并 |

## 已查明的执行缺陷

原报错是训练头目标的np.array_equal检查失败。两套保存的training_targets.npz实际上文件字节也完全相同：9600×134数组，925335个有效目标全部有限且逐值一致；16722个NaN全在掩码外且位置相同。默认数组相等比较会拒绝对应NaN。原始19成员失败包6889924bytes，SHA256为ba270b4e393dab3c2e49a4012d96bfd13125fa17e18b671bc2e5429067086573，已回传逐成员验哈希。

新版本只把对应的缺失占位按缺失语义比较：窗口/掩码/形状必须精确相同；原有效单元必须全部有限；全阵按equal_nan=True仍须精确相等。改变有效值（包括nextafter差别）、移动NaN、改变无效有限值、非有限有效值均停止，不使用容差。旧失败不因此变为通过，新辅助头从头训练，不伪称优化器续训。

源审查还加强了固定预测/目标形状与有限性、弃权输入与原人口精确一致、验证α及非平凡阈值有限性；保留coverage1的预定义无穷阈值。中间产物新增真实验证校准、策略动作及弃权输入归档。原5种子、30条件、150缓存批/5轮辅助头预算、校准算法、风速基线、q/rho/dt、覆盖率网格和不确定性程序均保持原定义。确定性数值环境显式记录；不据此认证旧结果或跨硬件重训逐值一致。

审查中曾错误推断cond_id未定义；原冻结源码第470行已定义，故该推断已明确撤回，最终代码保留原命名。没有可宣称的NameError修复。

## 实际预检与来源

注册RAW-DOWNSTREAM-PHASE-EXECUTION-REPAIR-V1后，源审查闭合，再提交真实PBS预检242792：实际F/exit0。45模型产物核验0pending/0failure，8个软件回归检查实际通过（0.17秒），并执行真实CUDA环境/隔离导入、失败NPZ检查、缓存/模型/固定残差/源文件核验。

源commit69251ab6f51358b35f56b37c109fa3a921fdaf7f；10文件包SHA533c27e2fc96d49444742e1ac346f6eb8e6afe1c389a17e1a318013acc376d0d；manifest SHA6638ce0fd54720ed3980dfb042a651443a8e1f033c70439cddc2ad94f607dcc8。独立工具部署在metis_execution/downstream_recovery/attempt1，云端冻结scripts/windfarm_moe未修改；旧未执行预审包也保留。实际源码与包phase SHA为09ce0ac0b3c2904baebcfcfffd7c60e3d34efb91591780e8a630c20fbc7aa9b4。

预检后再次查询有13个满足GPU/4CPU/64GB的普通节点，按5个独立相位种子加2个独立族使用7张GPU。提交日志、依赖、前后PBS记录全部保留；没有强制qrun或改其他项目任务。每个worker再次核预检实际F0、源/输入hash和新目录，无覆盖运行。

- [实际预检报告](../artifacts/metis_downstream_recovery_20261016_attempt1/preflight_report.json)
- [实际预检完整输出](../artifacts/metis_downstream_recovery_20261016_attempt1/preflight.stdout)
- [限域源码复核](../artifacts/metis_downstream_recovery_20261016_attempt1/source_falsifier_review.txt)
- [限域证据复核](../artifacts/metis_downstream_recovery_20261016_attempt1/initial_evidence_review.txt)
- [新快照独立哈希核验](../artifacts/metis_followup_20261016_0804/final_verification.json)
- [真实提交程序与完整参数](../artifacts/metis_downstream_recovery_20261016_attempt1/submit_workers.py)

初始快照928文件/34对PBS输出流独立哈希核验；新快照20261016T001950Z_27c31733的1026文件/39对输出流也逐项核验，包含真实7份RUNNING收据，返回预检报告/日志与快照字节一致。运行文件仅代表当时可见字节，不能当作最终日志或完成训练。

## 明确未闭合的部分

预检completed_core_integrity中的通道深清单路径曾使用channels/evidence，而真实路径为channels/summary_runs，因此该项记录0个深manifest；匹配预算/ρ也没有相应深manifest。这些记录不能当作完整数值或证据审计。它不影响独立worker所依赖的真实模型/缓存/固定目标输入核验；TRR19仍保留完整通道/EXP02/EXP03/匹配预算/ρ的数值与证据审计要求。

尚需核验每个结果的实际模型、动作、掩码/时间/节点、原生块、统计，以及EXP03完整包网格/缺失/陈旧状态；完成新五种子相位和两族后还要检查全部46项覆盖和逐项论文结论。旧错误窗口的外部结果、旧异步溯源和其他撤回结论不会因这次执行恢复而恢复。全部负/零结果照实保留。最终科学反证、独立证据审查及全项目门控仍未通过；自动跟进继续。
