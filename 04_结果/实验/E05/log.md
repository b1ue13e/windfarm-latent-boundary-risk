# 实验日志 E05

- 创建：2026-10-18T02:44:14.701Z


## 2026-10-18T03:04:50.622Z

在冻结的 E04 v4 五个 seed_full_policy_day_blocks.npz 数组上，按预注册 alpha=0.05、epsilon_C=0 kWh、epsilon_V=0、v_max=0.10、候选顺序 B<C<D<D10 和独立稳定性随机种子 20261018 执行 10,000 次 joint seed-by-35-day-block resampling。NO FEASIBLE 频率为 0.6464（6464/10000，Monte Carlo SE 0.00478）；各政策可行频率 B=0.3523、C=0.0042、D=0.0001、D10=0.0002；按复杂度序的首个选择频率 B=0.3523、C=0.0013、D=0、D10=0。当前 receipt-bound 诊断输出 JSON SHA-256=`f2e58ab12ac1228784a3a27187ec769f459162e5fa86892bafd8e774317c8f93`、CSV SHA-256=`d0a8c269ad13f94e9dbb5716282a55a354e6e1154b4678cee6075489eef794c2`，频率总和与计数约束通过。E05 receipt 已绑定本次诊断命令、预注册文件、E04 主结果与五个数组输入；但原始 v4 replay receipt 仍缺失，不能把 E05 诊断 receipt 解释为原始 replay 认证。

结论：E05 为 inconclusive。NO FEASIBLE 占多数重采样，且没有候选达到设计中的 >=0.80 首选稳定性频率；因此不认证 B 为 minimum-sufficient policy，也不支持复杂策略部署必要性。E04 仍需原始 replay receipt/hash binding 与独立 falsification review。
