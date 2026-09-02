# Pitch 稀疏农场窗口重建与观测谱系实验记录

> 日期：2026-09-03 ｜ 实验：可观测性谱系 signature 探针（Penmanshiel / Kelmarsh / LHB）
> 重建脚本：`scripts/rebuild_obs_windows.py`（预注册窗口规则，无结果依赖）

## 1. 发现：原始缓存的窗口假阴性

原始 `external_wind_*_chronological` 缓存按"数据开头 245 天"切片，但：

| 农场 | 原始窗口（day 0-245） | 问题 |
| :--- | :--- | :--- |
| Penmanshiel | pitch=0.000, valid=0.000 | 2016 年前 660 天 pitch 通道完全缺失 → 训练零有效标签（align=0 实锤） |
| Kelmarsh | pitch=0.801, valid=0.473 | 前 120 天 Wspd/标签缺失 → train valid 仅 30.4% |

这印证 harsh review F0-1 的"coverage 0.0000 是窗口选择假阴性"——本质是**窗口选择**问题，不是数据缺失。

## 2. 预注册窗口规则（只看输入掩码，不看任何模型输出）

- **Penmanshiel**：最早的连续 245 天窗口，满足日 pitch 覆盖率 ≥ 0.70 且日 regime-valid ≥ 0.70 → **day 720 起**（实测 pitch=0.781，valid=0.889）。
- **Kelmarsh**：最早的连续 245 天窗口，满足日 regime-valid ≥ 0.70（pitch 覆盖率是农场真实的部分可观测特性，不设阈值）→ **day 120 起**（实测 pitch=0.551，valid=0.934）。

## 3. 可观测性谱系

| 农场 | pitch 覆盖率 | 节点数 | 谱系位置 |
| :--- | :--- | :--- | :--- |
| LHB | 99.2% | 4 | 全观测参考（signature 已跑：canonical 0.975 / full 0.674 / core 0.575） |
| Penmanshiel | 78.1% | 14 | 中等稀疏 |
| Kelmarsh | 55.1% | 6 | 严重稀疏 |
| （WTB） | ~100% | 134 | 主基准（canonical 0.721 / full 0.561 / core 0.367） |

## 4. 实验矩阵（25979，num_workers=0，5 GPU）

- Penmanshiel：canonical / signature_full / signature_core / signature_full_shuffled × 5 seeds = 20 runs
- Kelmarsh：canonical / signature_full / signature_core × 5 seeds = 15 runs
- 判据：Penmanshiel/Kelmarsh `signature_core` NMI ≥ 0.20 → "pitch 稀疏农场边界可恢复"；若随 pitch 覆盖率单调下降 → 部署谱系叙事坐实。

## 5. 执行修正记录

- 首次队列（00:44）用原始缓存 → Penmanshiel align=0 无效，发现后立即止损（00:52）。
- 二次队列（01:32）用重建缓存 + num_workers=0 → 有效但 ~13-30 min/epoch（宿主机 CPU 被 paper1 占用）。
- 三次切换 num_workers=4 实测**更慢**（20min 0.45 epoch vs nw0 1.5 epoch，CPU 竞争下多进程切换开销大于收益）→ 切回 num_workers=0。
- 当前队列（01:57）num_workers=0 运行中。预计 14-21 小时（后台，不占用老师 CPU 之外资源）。

## 6. 环境注意

- 25979 容器与 grokking 共享宿主内核：`kill` 训练进程会把 DataLoader workers 变孤儿（spawn_main 僵尸），需同步清理；正常跑完不会产生。
- paper1（老师的 `run_physgate_cross_site.py`）占 GPU0 + 大量 CPU；我们只用 GPU1-5 且数据加载单线程。
