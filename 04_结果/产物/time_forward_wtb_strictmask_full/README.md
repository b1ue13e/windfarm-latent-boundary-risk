# Strict-Mask WTB Time-Forward Test-Slice Audit

## Purpose

This audit slices saved strict-mask test predictions into four contiguous anchor-time blocks. It is a post-hoc stability stress test, not a replacement for an external dataset or a pre-specified future-period holdout.

Command:

```text
python main.py time-forward-audit --dataset wtb --root-dir . --run-table artifacts\mechanism_gate_wtb_strictmask_full\mechanism_gate_run_table.csv --output-dir artifacts\time_forward_wtb_strictmask_full --models "MoE + L_bal + L_align + L_force" --split test --num-blocks 4 --steps-per-hour 6 --bootstrap-samples 1000 --seed 42
```

## Block Summary

| Block | Anchor Range | Overall RMSE | Switch RMSE | Pitch-Control RMSE | NMI | ARI |
|---|---:|---:|---:|---:|---:|---:|
| 1 early | 30275-31520 | 217.4623 +/- 9.6060 | 209.3283 +/- 8.7584 | 313.2296 +/- 18.0522 | 0.8593 +/- 0.0420 | 0.9182 +/- 0.0325 |
| 2 middle | 31521-32765 | 243.6546 +/- 7.4467 | 250.9040 +/- 9.6873 | 286.0920 +/- 25.8877 | 0.8693 +/- 0.0374 | 0.9117 +/- 0.0365 |
| 3 middle | 32766-34010 | 199.7237 +/- 7.6958 | 200.7185 +/- 7.9983 | 389.8270 +/- 38.6300 | 0.8500 +/- 0.0445 | 0.9207 +/- 0.0318 |
| 4 late | 34011-35255 | 267.8077 +/- 10.4767 | 272.6831 +/- 9.7232 | 278.6590 +/- 18.6570 | 0.8661 +/- 0.0393 | 0.9079 +/- 0.0364 |

## Late-vs-Early Effect

- Delta overall RMSE: `+50.3454` CI `[45.2176, 55.1826]`.
- Delta switch RMSE: `+63.3549` CI `[59.5739, 65.6209]`.
- Delta pitch-control RMSE: `-34.5707` CI `[-54.6947, -12.1980]`.
- Delta NMI: `+0.0068` CI `[0.0012, 0.0156]`.
- Delta ARI: `-0.0102` CI `[-0.0166, -0.0030]`.

## Interpretation

The strict-mask model keeps strong boundary-routing semantics in the late test block, but forecasting accuracy worsens materially in the late block. This strengthens the mechanism claim while weakening any deployment-ready or forecasting-robustness claim. A top-journal version should either add an external/pre-specified future holdout or explicitly frame this as retrospective mechanism evidence with a documented late-period forecasting risk.
