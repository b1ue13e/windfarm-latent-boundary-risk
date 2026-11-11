# Strict-cache strong-baseline rerun protocol

Status: `protocol_only_not_executed`.

This artifact freezes the fair WTB strong-baseline rerun plan. It is not evidence that the rerun has passed.

## Baselines

- Graph WaveNet (`graph_wavenet`), seeds 201, 202, 203, 204, 205.
- Graph Transformer (`graph_transformer`), seeds 201, 202, 203, 204, 205.
- GAT-GRU (`gat_gru`), seeds 201, 202, 203, 204, 205.
- PatchTST (`patchtst`), seeds 201, 202, 203, 204, 205.
- iTransformer (`itransformer`), seeds 201, 202, 203, 204, 205.
- TiDE (`tide`), seeds 201, 202, 203, 204, 205.

## Guard Conditions

- The cache metadata must match the requested WTB split.
- The cache must carry the `strict_anchor_mask_patch` marker.
- Full-cache anchor-mask verification must report zero strict-anchor violations.
- Every expected baseline run must have matching `training_summary.json` and `test_metrics/metrics.json`.

## Commands

```powershell
python main.py strict-baseline-guard --dataset wtb --root-dir . --cache-root artifacts/cache_strictmask --train-days 180 --val-days 30 --test-days 35 --hist-len 36 --pred-len 24 --protocol-dir artifacts\strict_baseline_protocol_wtb_strictmask_20260628_expanded --suite-dir artifacts\strictmask_baseline_rerun_wtb_full --output-dir artifacts\strict_baseline_protocol_wtb_strictmask_20260628_expanded\guard
python main.py paper-batch --dataset wtb --root-dir . --cache-root artifacts/cache_strictmask --train-days 180 --val-days 30 --test-days 35 --hist-len 36 --pred-len 24 --output-dir artifacts\strictmask_baseline_rerun_wtb_full --groups strong_baselines --variant-keys graph_wavenet,graph_transformer,gat_gru,patchtst,itransformer,tide --seeds 201,202,203,204,205 --strong-baseline-seeds 201,202,203,204,205 --epochs 20 --batch-size 16 --hidden-dim 64 --skip-visuals
python main.py strict-baseline-guard --dataset wtb --root-dir . --cache-root artifacts/cache_strictmask --train-days 180 --val-days 30 --test-days 35 --hist-len 36 --pred-len 24 --protocol-dir artifacts\strict_baseline_protocol_wtb_strictmask_20260628_expanded --suite-dir artifacts\strictmask_baseline_rerun_wtb_full --output-dir artifacts\strict_baseline_protocol_wtb_strictmask_20260628_expanded\guard_after_training
```
