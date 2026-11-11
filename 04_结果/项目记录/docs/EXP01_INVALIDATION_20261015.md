# EXP01 v4 invalidation — 2026-10-15

Status: INVALID AS MATCHED DECISION EVIDENCE. Supersedes earlier reports that called
v4 authoritative. Preserve every historical file; do not replace it with another
historical version to obtain a preferred conclusion.

The independent falsifier directly compared saved target.npy/mask.npy in
artifacts/external_wind_runs/{farm}/chronological/external_wind_full_seed201/{val,test}_metrics
against targets reconstructed at the same integer anchors from the evaluated canonical
observability windows. All jointly valid targets differed:

| Farm | Validation mismatches / common valid | Test mismatches / common valid | Window shift |
|---|---:|---:|---:|
| Kelmarsh | 441681 / 441681 | 574800 / 574800 | 120 days |
| Penmanshiel | 1065358 / 1065358 | 1209852 / 1209852 | 720 days |

Saved target and mask arrays exactly match the original chronological caches. At
index30275, original time_index is [211,35]; canonical Kelmarsh is [331,35] and
Penmanshiel [931,35]. This is not floating-point variation or evidence of a transfer
effect: predictions and targets belonged to different physical times. Source code
scripts/repair_exp01_pitch_withheld_v3.py checked only integer anchor equality before
subtracting these targets from the original predictions.

Consequences: withdraw v4 means -315399.62/+352433.95 kWh, their intervals, and both
positive/negative directional interpretations as valid matched comparisons. The CSVs
remain archived as outputs of an erroneous calculation. Earlier v2 is not reinstated.

Corrected replay must train/freeze the site point predictor on the declared raw window,
save physical time/node identities, and assert exact target/mask/time/node alignment
before policy evaluation. The updated alignment guard rejects the existing wrong-window
inputs. This is a hard failure, not a threshold to relax.

Evidence: .agent_state/FALSIFICATION_REPORT.md section13; saved raw arrays and source
paths identified above. New valid external decision results are NOT YET AVAILABLE.
