# Strict WTB Evidence Source Package

This folder centralizes the strict-anchor-mask WTB evidence stack for manuscript table and supplement regeneration.

## Contents

- `tables/strict_wtb_seed_metrics.csv`: per-seed strict-mask metrics.
- `tables/strict_wtb_summary.csv`: five-seed mean and standard deviation.
- `tables/strict_wtb_mechanism_effects.csv`: replay-safe mechanism intervention effects.
- `tables/strict_wtb_mechanism_raw.csv`: per-seed mechanism intervention raw metrics.
- `tables/strict_wtb_placebo_effects.csv`: routing placebo separations.
- `tables/strict_wtb_placebo_raw.csv`: per-seed routing placebo raw metrics.
- `tables/strict_wtb_time_forward_summary.csv`: post-hoc time-forward block metrics.
- `tables/strict_wtb_time_forward_effects.csv`: late-vs-early effects.
- `tables/strict_wtb_time_forward_shift_diagnostics.csv`: block-level late-period distribution-shift diagnostics.
- `tables/strict_wtb_time_forward_shift_effects.csv`: late-minus-early shift distances and paired effects.
- `tables/strict_wtb_boundary_slice_summary.csv`: MPPT-to-pitch boundary-band slice metrics.
- `tables/strict_wtb_boundary_slice_effects.csv`: boundary-band versus comparator-slice effects.
- `generated/*.tex`: LaTeX source tables generated from the CSV files.
- `strict_wtb_evidence_manifest.json`: input/output SHA256 manifest.

## Science-Level Interpretation

The package supports a strict-mask mechanism/routing claim, not an accuracy-SOTA or deployment-robustness claim.

## Key Numbers

- Overall RMSE: `236.1305 +/- 8.4096`.
- Switch RMSE: `239.8552 +/- 8.8508`.
- NMI / ARI: `0.8716 +/- 0.0418` / `0.9166 +/- 0.0371`.
- Boundary-band RMSE / NMI / ARI: `321.1711` / `0.6562` / `0.7766`.
- Boundary-vs-nonboundary delta RMSE: `67.0731`.
- Replay status: `matches_reference` over `5` runs.
- Late-vs-early overall RMSE delta: `50.3454`.
- Late-shift abs-ramp delta / regime TV: `-1104.6378` / `0.2983`.
