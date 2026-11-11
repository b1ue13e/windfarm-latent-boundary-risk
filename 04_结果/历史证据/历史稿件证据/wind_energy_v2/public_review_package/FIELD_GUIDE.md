# Claim-to-field guide

All indices below are zero-based. Costs are kWh-equivalent per valid turbine interval; event rates and relative ratios are stored as fractions unless a CSV explicitly states percent. Time is UTC. The confirmation cost denominator is 1,059,248 finite-future-power turbine intervals per instance. Original zero and negative powers remain in the original target construction.

| Responsibility | Archived source and fields | Verification operation |
|---|---|---|
| Historical selection | `data/history/choices.json`, `groups[0].sets["0.02"].original_indices`, `reference_index`, `uses_confirmation` | Map frozen indices to labels and bind SHA to primary output |
| Primary q=.95 cost | `data/confirmation/primary.json`, `bounds.groups[0].relative_ratio_{point,lower,upper}[0][1]` | Multiply by 100 for display; upper ≤ .02 |
| Primary risks | Same JSON, `bounds.groups[0].risk_upper[instance][policy]` | Every one of five fixed-instance bounds ≤ .10 for both policies |
| Full-family cost bridge | `data/confirmation/secondary_span3.json`, `results[condition=pitch_withheld].relative_ratio_upper[j][k]` | Take maximum over k with every `risk_lower[instance][k]` ≤ .10; compare to stored `sufficient_set.required_relative_tolerance[j]` |
| q=.925 vs q=.95 distinction | Same group, label indices 41 and 42 | Compare required upper against .02 and membership in stored eligible set; no new uncertainty |
| Resource identification | Same group, `resources`, `secondary_retrospective_full_q[epsilon=.02].minimum_audit` | Lexicographic resource order; every strictly smaller registered resource excluded by risk-lower or feasible cost witness |
| Cost witnesses | Same group, `relative_ratio_lower[j][k]`, `risk_upper[:,k]` | Witness k must have all upper event bounds ≤ .10; lower relative cost of smaller j against k must exceed .02 |
| Risk witnesses | Same group, `risk_lower[:,j]` | At least one fixed instance lower bound > .10 |
| Towie classifications | All `data/confirmation/secondary_span*.json` plus `csv/towie_all_90_cases.csv` | Reapply stored bounds for six conditions × five margins × three separate spans |
| WTB boundary | `data/wtb/aggregate.json`, `data/wtb/necessity.json`, two WTB CSVs | Reapply stored bounds at each condition/budget/span/analysis/margin; preserve no-sufficient and unresolved categories |
| Cost decomposition | `data/ledger/policy_seed_ledger.csv` and `derived.json` | Average the same five fixed instance summaries; expose procurement and uncovered-shortfall separately |
| Plot data lineage | `figure_data/*.csv` plus `PROVENANCE.json` | Identity of original plotted data; Figure 2 numbers additionally checked against primary source fields |
| Code identity | `source_static/` plus `PROVENANCE.json` | Frozen execution source hash where present, Git commit and CRLF-normalized content identity |

The primary fourteen-coordinate envelope and each full-family 74,500-coordinate secondary envelope are separate. Legacy Figure 3's marginal mean-cost error bars are not a joint pairwise decision criterion. V2 Figure 3 instead displays the stored worst-cost upper bound directly, alongside the maximum fit-specific risk upper and fifteen exclusions; it introduces no error bar or interval. A full-family upper above 2% means failure to certify at that margin, not a lower-bound proof that true regret exceeds 2%.

JSON files preserve original serialized values, including non-finite literal extensions if present. Python's standard JSON reader accepts these archived files; a strict RFC-only reader may require an explicit non-finite handling policy. Reformatting such files changes their hashes and is not an allowed way to silently replace the archived originals.

This package checks decisions made from pre-existing numerical bounds. It does not make additional inferential estimates, select new models, change q, reinterpret cost margins as business approvals, or assert a universal function-class minimum.
