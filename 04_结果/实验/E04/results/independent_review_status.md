# E04 Independent Review Status

**Date:** 2026-10-17
**Status:** `BLOCKED_RUNTIME / NOT SCIENTIFICALLY CERTIFIED`

## Attempts

- Scientific-reviewer subagent `a0d6d002-7b0d-428f-a2e2-d90e61fd9f66` failed before returning a closing report.
- Independent audit subagent `14564a1a-db71-4cc2-8f19-0afd8ca643ee` failed before returning a closing report.
- A read-only Codex reviewer could not start because the runtime reported `WinError 2` (missing executable).

No failed reviewer attempt was converted into a PASS. E04 remains `PARTIAL_VERIFIED / independent review pending`.

## Direct numerical sanity check

A separate local read-only script directly loaded the five `seed*_full_policy_day_blocks.npz` arrays and checked the raw full-population block counts and aggregate ratios:

- Each seed contains `n = 385,205` full-population cells.
- Aggregate violation fractions were approximately B `0.10284`, C `0.10444`, D `0.10278`, D10 `0.10259`.
- Aggregate PSREI sums were approximately B `14,979,310`, C `15,424,950`, D `14,990,725`, D10 `14,994,058` kWh.
- These checks agree in direction and scale with `experiments/E04/results/e04_selection.json`; they do not replace the registered joint bootstrap audit or independent falsification review.

## Scientific disposition

The valid E04 v4 direct replay and selector output support the operational result `NO FEASIBLE POLICY` under the pre-registered constraints. They do not support a complex-model deployment-necessity claim, and they do not close the independent-review gate. A later continuation must obtain the missing reviewer report before upgrading E04 beyond partial verification.

## Returned independent review — 2026-10-17

**Overall verdict:** `NEEDS-WORK / NOT SCIENTIFICALLY CERTIFIED`.

### Claim-level verdicts

1. **Protocol fidelity:** `needs-work`. The selector code and JSON agree on alpha, tolerances, candidate order, and the Full-population selector, but exact temporal precedence is not independently certified: the design freeze block is later than the result JSON and there is no immutable pre-result hash/commit proving all thresholds preceded execution.
2. **Numeric consistency:** `supported, conditional on the v4 arrays`. The selector uses bootstrap UCB quantiles rather than aggregate means; the returned values match `e04_selection.json`. Violation quantities are fractions in the selector and closure percentages are display fields, so there is no identified percent/fraction mix-up.
3. **NO FEASIBLE POLICY:** `supported, conditional on the v4 arrays`. B has absolute violation UCB `0.1141939 > 0.10`; C has cost UCB `+3,758,647 kWh` and absolute violation UCB `0.1173145`; D has cost UCB `+119,264 kWh` and absolute violation UCB `0.1141829`; D10 has cost UCB `+128,435 kWh` and absolute violation UCB `0.1138942`.
4. **Deployment necessity:** `supported as a negative boundary only`. E04 supports only that no candidate in this tested Full-population class satisfies all constraints. It does not prove B is minimum-sufficient, that complex models have no value, or that the criterion is a universal law.
5. **Remote execution provenance:** `needs-work`. J01/J02/J03 logs show `bash: script.sh: No such file or directory`; J02 is registered as succeeded/exit 0 despite empty stdout. The v4 arrays therefore lack an independently bound process receipt/output hash, even though the direct v4 replay itself produced the arrays.

### Required fixes before promotion

- create a true immutable pre-execution registration hash/commit for the threshold and candidate freeze;
- repair the remote launcher/receipt path and bind the v4 outputs to a valid process receipt and output hash;
- estimate selector stability/frequency under the pre-registered seed/block resampling rule; the current selector explicitly says `frequency not estimated in this aggregate selector`;
- rerun independent falsification review after those provenance and stability fixes.

This report does not promote E04 beyond `NEEDS-WORK / NOT SCIENTIFICALLY CERTIFIED`.
