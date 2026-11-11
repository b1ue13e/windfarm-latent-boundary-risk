# Threshold/label validity audit

Status: `passed_threshold_label_validity_audit`

This audit re-labels the saved WTB gate outputs across nearby rated-wind and pitch thresholds. It is a label-validity sensitivity check, not a new training run and not the semantic negative control itself.

## Checks

- selected_runs_present: `True`
- all_grid_cells_present: `True`
- canonical_threshold_present: `True`
- support_does_not_collapse: `True`
- routing_recovery_conclusion_stable: `True`
- control_taxonomy_separates_mask_and_semantic_controls: `True`
- semantic_negative_control_passed: `True`

## Control taxonomy

Mask/threshold controls check support and label-stability; semantic negative controls deliberately break routing semantics.
