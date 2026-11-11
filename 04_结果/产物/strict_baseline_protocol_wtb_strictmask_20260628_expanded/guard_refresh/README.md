# Strict-cache strong-baseline guard

Status: `complete_ready_for_strict_baseline_comparison`

This guard prevents legacy or incomplete baseline runs from being used as strict-cache leaderboard evidence.

## Checks

- protocol_json_exists: `True`
- protocol_status_is_not_executed: `True`
- protocol_bounds_match_requested: `True`
- protocol_cache_root_matches_requested: `True`
- protocol_cache_dir_matches_requested: `True`
- cache_metadata_exists: `True`
- cache_bounds_match_requested: `True`
- cache_has_strict_anchor_patch_marker: `True`
- cache_strict_anchor_check_ran: `True`
- cache_strict_anchor_violations_zero: `True`
- all_expected_runs_complete: `True`

## Run Completion

- Expected runs: `30`
- Complete runs: `30`
- Missing or incomplete runs: `0`

## Anchor-Mask Report

```json
{
  "can_check": true,
  "anchor_feature_names": [
    "Wspd",
    "Pab_mean"
  ],
  "anchor_feature_indices": [
    0,
    7
  ],
  "total_missing_anchor_cells": 49518,
  "strict_anchor_violations": 0,
  "strict_anchor_pass": true,
  "metadata_patch_present": true,
  "metadata_removed_regime_valid": 49518,
  "metadata_removed_aux_valid": null,
  "metadata_patch_violations_after_patch": null
}
```
