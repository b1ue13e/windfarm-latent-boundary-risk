# 实验日志 E04

- 创建：2026-10-17T08:15:54.906Z


## 2026-10-17T12:47:41.177Z

按预注册 alpha=0.05、epsilon_C=0 kWh、epsilon_V=0、v_max=0.10、Full population、5 seed x 35 daily blocks joint bootstrap 与复杂度序 B<Wspd, C<Posterior, D<Hybrid, D10<Boundary-Hybrid 执行。结果：B 绝对违约率点估计 0.10296、单侧 UCB 0.11419；C UCB cost delta +3,758,647 kWh、absolute violation UCB 0.11731；D UCB cost delta +119,264 kWh、absolute violation UCB 0.11418；D10 UCB cost delta +128,435 kWh、absolute violation UCB 0.11389。所有候选均不满足三个约束，选择器返回 NO FEASIBLE POLICY。该结果来自 Metis v4 frozen-input replay 的逐 seed/day-block policy arrays，未新增模型或调整阈值。

- 远程启动器 J01/J02/J03 因 `script.sh` 缺失而失败；这些是工具层失败，不计为科学结果，保留其日志以供审计。
- v4 direct replay 生成五个 seed 的 full-population policy day-block arrays；选择器结果见 `results/e04_selection.json`。
- 解释：当前 Full population 的绝对违约率约束不可行；没有政策被选择，也没有升级任何复杂模型或最小充分性普遍主张。

## 2026-10-17T12:51:58.153Z

E04 已按预注册规则完成：Metis v4 frozen-input direct replay，5 seeds x 35 day blocks，alpha=0.05，epsilon_C=0，epsilon_V=0，v_max=0.10，候选 B/C/D/D10。选择器返回 NO FEASIBLE POLICY：B absolute violation UCB=0.11419，C=0.11731，D=0.11418，D10=0.11389，均超过 0.10；C/D/D10 的 cost UCB 也为正。该结果说明当前 Full-population 风险约束在候选集中不可行，不支持选择任何复杂模型或普遍最小充分性定律。J01/J02/J03 为脚本传输层失败，不计为科学结果；v4 direct replay 才是有效输入。

独立 review 状态：scientific-reviewer 子代理和第二个独立 audit 子代理均在返回前失败；只读 Codex reviewer 因 WinError 2 无法启动。详见 `results/independent_review_status.md`。独立 review 已返回 `NEEDS-WORK / NOT SCIENTIFICALLY CERTIFIED`：selector 数值在给定 v4 arrays 上支持 NO FEASIBLE POLICY，但 temporal precedence、remote receipt/output-hash binding 和 selector stability 尚未闭合。E04 保持 NEEDS-WORK。

E05 已补做 selector stability/frequency 诊断：10,000 次 joint seed-by-35-day-block resampling，NO FEASIBLE 频率 0.6464，B/C/D/D10 可行频率分别为 0.3523/0.0042/0.0001/0.0002，按复杂度序首选频率分别为 0.3523/0.0013/0/0。结果条件于未绑定 receipt 的 v4 数组，未改写 E04 primary NO FEASIBLE 结论。

E04-v2 已在 preregistration commit 64478031 和 receipt/output manifest 绑定下重新执行，输出见 `results/e04_v2/` 和 `results/e04_v2_review_status.md`。v2 仍返回 NO FEASIBLE，并保留稳定性诊断；独立 falsification review 仍需复核 v2 receipt、manifest 和稳定性结果，E04 保持 NEEDS-WORK。
