# Time-forward holdout audit

This audit slices saved split predictions into contiguous anchor-time blocks and compares late-test behavior with early-test behavior.

## Block summaries

- MoE + L_bal + L_align + L_force block 1 (early): RMSE 217.4623 +/- 9.6060; switch RMSE 209.3283 +/- 8.7584; NMI 0.8593 +/- 0.0420; ARI 0.9182 +/- 0.0325; n=10.
- MoE + L_bal + L_align + L_force block 2 (middle_2): RMSE 243.6546 +/- 7.4467; switch RMSE 250.9040 +/- 9.6873; NMI 0.8693 +/- 0.0374; ARI 0.9117 +/- 0.0365; n=10.
- MoE + L_bal + L_align + L_force block 3 (middle_3): RMSE 199.7237 +/- 7.6958; switch RMSE 200.7185 +/- 7.9983; NMI 0.8500 +/- 0.0445; ARI 0.9207 +/- 0.0318; n=10.
- MoE + L_bal + L_align + L_force block 4 (late): RMSE 267.8077 +/- 10.4767; switch RMSE 272.6831 +/- 9.7232; NMI 0.8661 +/- 0.0393; ARI 0.9079 +/- 0.0364; n=10.

## Late-vs-early effects

- MoE + L_bal + L_align + L_force block_4_minus_block_1: Delta RMSE 50.3454 [46.8137, 54.1758]; Delta switch RMSE 63.3549 [60.7291, 65.3319]; Delta NMI 0.0068 [0.0021, 0.0127].
