## v1 · 2026-10-12T00:44:34.634Z · session-8bff

描述：EXP-02 zero-privileged supervision benchmark results and audit report evaluating consequence-only recovery of latent control boundaries without blade pitch telemetry.

命令：`python scripts/run_exp02_zero_privileged_supervision.py --cache-dir artifacts/cache_strictmask_trainweights/wtb_245d --residuals-file artifacts/fixed_forecast_residuals.npz --runs-root artifacts/strictmask_ablation_rerun_wtb_full --output-csv artifacts/zero_privileged_supervision_benchmark.csv --output-report docs/ZERO_PRIVILEGED_SUPERVISION_REPORT.md --epochs 12 --device cuda`

输入：artifacts/fixed_forecast_residuals.npz

输入哈希：artifacts/fixed_forecast_residuals.npz#b05b3751f45e

备注：Executed on Metis compute node with NVIDIA A100-PCIE-40GB GPU across 5 seeds and 2 horizons (h=1, h=6) under strict zero-pitch assertions. Falsification guardrail observed: zero-privileged challenger failed to achieve positive delta PSREI over Site-Local Wspd-Bins.

环境：win32 x64 / node v24.18.1

| 文件 | SHA-256 | 大小 (B) | 来源 |
| --- | --- | ---: | --- |
| `zero_privileged_supervision_benchmark.csv` | `b8c40e3df3c8a9530e2a8a9da1edd46411bd216592c7d1680a81c5b5b0356466` | 19740 | 复制 |
| `ZERO_PRIVILEGED_SUPERVISION_REPORT.md` | `cf9c707022248a46fb776ca48891a8add2f83f5b1be16327b93f65c12cbcee18` | 4362 | 复制 |
