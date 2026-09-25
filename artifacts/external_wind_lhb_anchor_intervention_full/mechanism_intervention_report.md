# Mechanism intervention audit

This audit reloads trained WTB MoE checkpoints and replays the test split after targeted physical-variable interventions.

## Actual replay

- Physics-Aligned MoE: RMSE 185.9746; NMI/ARI 0.9408 / 0.9712; n=5.

## Intervention effects

- Physics-Aligned MoE under anchor_pab_zero: Delta RMSE 0.6625 [0.0104, 1.4343], drop NMI 0.2450 [0.1796, 0.3105].
- Physics-Aligned MoE under anchor_wspd_zero: Delta RMSE 1.1971 [0.4492, 2.3025], drop NMI 0.1887 [0.0664, 0.3554].
- Physics-Aligned MoE under anchor_patv_zero: Delta RMSE 0.0741 [0.0141, 0.1496], drop NMI -0.0126 [-0.0470, 0.0132].
- Physics-Aligned MoE under anchor_boundary_zero: Delta RMSE 3.7595 [1.4220, 6.4420], drop NMI 0.9395 [0.9140, 0.9673].
- Physics-Aligned MoE under anchor_random_physics: Delta RMSE 5.5967 [3.4501, 7.8208], drop NMI 0.9129 [0.8842, 0.9407].
- Physics-Aligned MoE under anchor_wspd_only: Delta RMSE 1.3797 [0.1693, 2.9011], drop NMI 0.1887 [0.0450, 0.4010].
- Physics-Aligned MoE under anchor_pab_only: Delta RMSE 1.8391 [0.6426, 3.6621], drop NMI 0.2706 [0.1062, 0.5683].
- Physics-Aligned MoE under anchor_boundary_node_shuffle: Delta RMSE 0.0450 [0.0091, 0.0858], drop NMI 0.2437 [0.2226, 0.2647].
- Physics-Aligned MoE under anchor_boundary_global_shuffle: Delta RMSE 0.6830 [0.4717, 0.9068], drop NMI 0.4522 [0.4243, 0.4767].
- Physics-Aligned MoE under anchor_wake_zero: Delta RMSE -0.0000 [-0.0000, 0.0000], drop NMI 0.0000 [0.0000, 0.0000].
- Physics-Aligned MoE under anchor_all_zero: Delta RMSE 3.7930 [1.4230, 6.1630], drop NMI 0.9050 [0.8117, 0.9660].
