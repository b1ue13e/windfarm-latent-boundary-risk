# IEEE TSTE Strengthening Checklist

Last updated: 2026-07-03. Target journal: IEEE Transactions on Sustainable Energy.
This checklist tracks the current "steady IEEE journal" route after the July 2026
evidence tightening pass.

## Source-Of-Truth Files

`paper_tste_ieee.md` and `paper_tste_supplementary.md` are generated artifacts.
Edit these sources instead:

| Content | Source file |
|---|---|
| Main text from Introduction through References | `paper_draft.md` |
| Title, abstract, keywords, IEEE header | `scripts/transform_ieee.py` |
| Supplementary appendix extraction and generated table insertion | `scripts/make_supplementary.py` |
| Reserve claim-boundary table | `scripts/build_reserve_claim_boundary_table.py` |
| External deployment-gate wording | `scripts/build_external_deployment_gate_audit.py` |
| La Haute Borne replay wording | `scripts/build_lhb_anchor_observability.py` |
| Submission token guard and package metadata | `scripts/prepare_tste_submission.ps1` |

## P0 Acceptance Gates

- [x] RMSE guardrail narrowed: train-only class-weight rerun reaches RMSE 229.93, within
  5.59 units of iTransformer 224.34. Legacy 236.13 is retained only as the complete
  operational-audit checkpoint.
- [x] MoE indispensability narrowed honestly: no classifier-superiority claim. The paper
  claims in-model route responsibility, same-run route-conditioned residual/reserve slicing,
  and A10b route-evolution behavior (0.815 at transition vs 0.361/0.405 under lead shifts).
- [x] Reserve diagnostics strengthened: same-router boundary gate-bin vs global has
  seed-paired CI below zero for total cost, violation, and shortage. Cross-backbone,
  physical-bin, and full-sample caveats remain explicit.
- [x] La Haute Borne upgraded: framed as anchor-observable cross-site mechanism replication
  (NMI 0.941, ARI 0.971), not as a side check and not as automatic reserve transfer.
- [x] Kelmarsh/Penmanshiel failures explained as deployment conditions: pitch observability,
  boundary-cell support, local threshold estimation, and held-out routing must pass before
  cross-farm use.
- [x] Operational value scoped: reserve evidence is a pre-dispatch reserve/imbalance-risk
  screening proxy, not market clearing, OPF, unit commitment, settlement, or delivered
  energy value.

## Machine Checks To Keep Green

Run after edits:

```powershell
python scripts\build_reserve_claim_boundary_table.py
python scripts\build_lhb_anchor_observability.py
python scripts\build_external_deployment_gate_audit.py
python scripts\make_supplementary.py
python scripts\transform_ieee.py
python scripts\verify_tste_number_consistency.py --output-dir artifacts\tste_number_consistency_audit
```

Expected number-consistency status:

```text
complete_tste_number_consistency
```

Core tokens to spot-check by eye:

```text
229.93, 224.34, 5.59, 236.13,
0.721, 0.740, 0.941, 0.971,
0.4877, 0.5112,
0.960, 0.196, 0.508,
0.815, 0.361, 0.405,
-4.65M, -2.45M, -0.0203, -0.0072, -0.78M, -0.30M
```

## Human Read Checks

- The abstract should lead with degraded-label reserve screening and auditable boundary
  routing, not reserve procurement or forecasting leaderboard wins.
- The contribution statement should explicitly separate train-only RMSE guardrail from
  legacy full-audit artifacts.
- The modular alternative should remain credible: low-RMSE forecaster + live-anchor
  classifier + physical-bin reserve is valid when only a state flag is needed.
- The reserve paragraph should say "same-router diagnostic" and "physical-bin baselines
  remain competitive."
- The LHB paragraph should say "anchor-observable cross-site mechanism replication."
- The deployment section should make Kelmarsh/Penmanshiel a no-go condition, not a hidden
  failure.

## Build / Package Reminder

Before upload, run the full package path:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\prepare_tste_submission.ps1
```

The package must pass the PDF page-count checks, evidence-freeze guard, number-consistency
audit, upload manifest verification, and independent package verifier.
