# LHB 跨场 Signature 验证 — 数据集适切性判断

> 日期：2026-09-02 ｜ 目的：跑 LHB `signature_full`/`signature_core` 之前，先判断 ENGIE La Haute Borne 数据是否适合该模型与变体协议。
> 核验对象：`artifacts/cache_external_wind/external_wind_la_haute_borne_chronological/`（本地 + 远程同名路径）。

## 1. 通道结构同构性

| 维度 | WTB（signature 已跑） | LHB | 结论 |
| :--- | :--- | :--- | :--- |
| encoder feature_names | 11 通道（Wspd, Wdir_sin/cos, Ndir_sin/cos, Etmp, Itmp, Pab_mean, Pab_std, Prtv, Patv_hist） | **完全相同 11 通道** | 变体零改可用 |
| physics anchor | [Wspd, Pab_mean, wake_score, Patv] | **完全相同 4 通道** | 零化逻辑直接适用 |
| hist_len / pred_len | 36 / 24 | 36 / 24 | 一致 |
| primary_num_classes | 3 + transition | 3 + transition | 一致 |

`_apply_variant` 按 `feature_names`/`physics_names` 字符串匹配零化通道，LHB metadata 中名称与 WTB 一致，**无需任何适配代码**。

## 2. 标签口径与观测性

- `pitch_proxy_used_for_regime = False`，`pitch_observed_fraction = 0.9922` → 桨距角**实测**覆盖 99.2%，非代理。
- `wtb_thresholds = {3.0, 10.5, 2.0°}` → LHB 与 WTB 用**同一声明边界**（非本地阈值）。这使"边界指纹跨场存在"的解读更干净：标签定义相同，变化只在数据分布。
- `primary_class_weights` / `pitch_force_weights` 由 `regime[:train_stop]` 计算 → **train-only 口径**，与 WTB signature 的 provenance 标准一致。

## 3. 数据规模与类分布

- 4 台 Senvion MM82，split 180/30/35 天（35280 步有效）。
- valid 样本类分布：idle 20.5%、MPPT 77.4%、**pitch-control 仅 2.1%**（4219/197275）。
- 风险：pitch 小类 → `signature_core`（去 Wspd/Pab_mean/Patv）可能比 WTB 更易坍缩；`signature_full` 保留 Patv，风险较低。

## 4. 后果通道可用性（signature 变体的"存粮"）

| 通道 | 有效样本覆盖率 |
| :--- | :--- |
| Patv | 86.9% |
| Prtv | 97.8% |
| Pab_std | ~100% |
| 温度/风向/机舱方向 | 99.2–99.99% |
| wake_score | **恒 0**（4 节点无 wake 图） |

`signature_full` 可用 Patv_hist + Prtv + Pab_std + 环境通道；`signature_core` 仅剩 Prtv/Pab_std/环境通道。

## 5. 结论

**适合。** LHB 与 WTB 通道同构、标签同阈值、pitch 实测、class weights train-only，且此前 full-stack 训练已证明管线可跑（5-seed NMI 0.903–0.974）。唯一需要处理的是：
1. 增加 `canonical` 变体作为同协议全 anchor 对照（此前 0.941 是 full-stack 配置，不可直接比较）——已实现。
2. 训练用 `moe_bal_align_force`（与 WTB signature 完全一致的默认参数），保证跨场可比。
3. 预注册判据沿用路线 C 精神：
   - `signature_full` LHB mean NMI ≥ 0.40 且 min-seed ≥ 0.30 → 跨场 signature 成立；
   - < 0.30 → kill 条件（signature 仅 WTB 特设，叙事不可外推）。
   - `signature_core` 仅作辅助证据，不设硬门槛。

## 6. 已知限制（写入结果报告时必须披露）

- 4 节点农场规模小，边界带样本少。
- wake_score 恒 0：LHB 场景没有 WTB 的尾流签名维度。
- 2017–2020 数据只用了前 245 天（split_bounds），余量未用。
