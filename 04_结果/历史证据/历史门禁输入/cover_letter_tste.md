# IEEE Transactions on Sustainable Energy
## Cover-letter draft and evidence summary

**Revision date:** 19 October 2026
**Status:** Unsent draft; manuscript editing does not resume research execution or authorize submission.
**Corresponding author:** Juntao Du, School of Statistics and Applied Mathematics, Anhui University of Finance and Economics, Bengbu 233030, China
**Contact:** `dujuntao@aufe.edu.cn`

**Manuscript:** *Information Value and Decision Sufficiency under Degraded Wind-Turbine SCADA Telemetry*
**Authors:** Junyu Li and Juntao Du

Dear Editor-in-Chief,

This manuscript evaluates telemetry subsets for turbine-level reserve-risk screening under fixed forecast commitments, shortfall targets and synthetic information-arrival conditions. Its contribution is an empirical decision assessment in declared finite policy families, with development results, independent fixed-reference confirmation and secondary resource-minimality identification kept distinct.

The controlled 134-turbine WTB development study compares 22 pitch-withheld input subsets, two direct quantile estimators and four nested training-row budgets. All primary three-day groups contain risk-qualified policies, but none establishes two-percent near-optimality. At the predeclared five-percent sensitivity margin, current active/reactive power with HGB supplies a sufficient candidate at all four budgets. None of 420 shared-data decision cases identifies finite-family minimality. These negative and unresolved results are retained.

A separate Hill of Towie study fits on 2023, calibrates and selects on 2024, and freezes the complete historical program before one unlock of 2025. Historical P1/HGB/q0.95 selection passes the two-percent mean-cost noninferiority criterion against its frozen WPQ36/HGB/q0.95 reference. Its cost is higher by 0.5641%, with joint approximate interval [0.3575%, 0.7708%]; maximum instance risk upper bound is 6.2025%, below the declared 10% cap. This supports noninferiority to that reference, not cost superiority or full-family near-optimality.

The distinct predeclared full-q secondary analysis identifies P1/HGB/q0.925 as a resource minimum in the registered finite family, excluding all 15 strictly smaller candidates. The primary q0.95 policy is not in that full-q two-percent sufficient set. Across 90 dependent secondary cases, 46 identify minima, 26 leave minimality unresolved and 18 identify no sufficient candidate. The fixed historical-set assessment retains three delay3/0.5% failures. These assessments are not independent weather replications.

The common forecast already uses wind and power. Resource ordering describes incremental channels, predictor passes and raw input width, rather than measured end-to-end acquisition, runtime or monetary savings. Day-block inference is approximate, conditional on five frozen instances and the finite-future-power target population; block-length sensitivity does not certify nominal coverage under arbitrary seasonal or control drift. The two-percent tolerance is numerical, not a demonstrated business acceptance threshold. The study does not establish a universal deployment hierarchy, representation necessity, PCC procurement value or field safety.

Historical state-recovery and architecture comparisons remain bounded diagnostics. A routing test with p=0.380 does not prove equivalence. The imported strong-baseline posterior penalty of +445,639 kWh remains pending deep audit. E04 retains its no-feasible-policy result and E07 remains inactive. The new confirmation does not repair legacy provenance gaps or reinstate withdrawn transfer branches.

Public SCADA sources, frozen protocols, manifests, compact outputs and verification scripts are documented in the manuscript and repository. Some historical execution bindings remain incomplete, while full raw arrays and models for later receipt-bound studies are retained separately. The manuscript discloses assistance from ChatGPT and Codex with prose, formatting and verification scripts; author responsibility remains with the authors. No claim of complete end-to-end reproduction follows from file-hash checks.

Thank you for considering this bounded empirical contribution to renewable-generation decision assessment.

Sincerely,
Juntao Du, on behalf of the authors

---

## Retained historical numerical references

The following records remain explicit for consistency with the archived manuscript tables. They are not additional current contributions or deployment recommendations.

- Historical forecasting diagnostic: strict-cache iTransformer RMSE 224.34; training-split class-weight router RMSE 229.93, gap 5.59, and NMI 0.721. Forecasting and representation scores do not establish reserve-decision value.
- Historical PCC proxy diagnostic: signed cost differences of -2.32M kWh versus Global PCC Quantile, with interval [-6.07M, 1.73M] crossing zero, and -1.37M kWh versus Gaussian sizing; the transition comparison records -1.33M kWh. These archived contrasts do not certify matched-target decision gains, actual procurement savings or a PCC smoothing mechanism.
- The bounded `deterministic_matched_transfer_v1` branch retains h=6 posterior-minus-local-wind-bin deltas of +6.3k kWh for Kelmarsh (interval crossing zero) and +356.0k kWh for Penmanshiel. Corrected-v2 is superseded/not reinstated; v4 is invalidated. These records do not establish universal cross-site advantage.
