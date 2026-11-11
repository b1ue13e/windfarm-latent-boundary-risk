# Anchor-stress early-warning audit

Status: `complete_anchor_stress_supports_label_degradation_value`

This audit compares saved gate assignments with degraded threshold-label baselines around MPPT-to-pitch transitions.
It supports a conservative operational claim: gate value under delayed, missing, or noisy labels.

## Checks

- all_requested_runs_complete: `True`
- delay_degradation_curve_nonempty: `True`
- label_availability_curve_nonempty: `True`
- gate_beats_delayed_threshold_labels: `True`
- gate_beats_low_availability_threshold_labels: `True`
- pretrigger_ranking_auc_passes: `True`
- threshold_sensor_noise_curve_present: `True`

## Summary

- canonical / label_delay / delay_steps=1: gate recall 0.960, rule recall 0.655, gain 0.305
- canonical / label_delay / delay_steps=3: gate recall 0.960, rule recall 0.381, gain 0.579
- canonical / label_delay / delay_steps=6: gate recall 0.960, rule recall 0.196, gain 0.764
- canonical / label_availability / available_rate=1.00: gate recall 0.960, rule recall 1.000, gain -0.040
- canonical / label_availability / available_rate=0.75: gate recall 0.960, rule recall 0.744, gain 0.216
- canonical / label_availability / available_rate=0.50: gate recall 0.960, rule recall 0.508, gain 0.452
- canonical / label_availability / available_rate=0.25: gate recall 0.960, rule recall 0.242, gain 0.718
- canonical / threshold_sensor_noise / wspd_sd=0.25;pab_sd=0.50: gate recall 0.960, rule recall 0.896, gain 0.064
- canonical / threshold_sensor_noise / wspd_sd=0.50;pab_sd=1.00: gate recall 0.960, rule recall 0.808, gain 0.152
- canonical / threshold_sensor_noise / wspd_sd=1.00;pab_sd=2.00: gate recall 0.960, rule recall 0.652, gain 0.308
