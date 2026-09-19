# Experiment Gates

Use this reference to decide whether the mainline can be strengthened or must be downgraded.

## Claim Gates

L0: CSI300 rank-fusion workflow

- Pass: strict CSI300 refusion improves over HGB anchor or has clearly reported bounded support.
- Controls: matched random fusion and leakage sentinels.
- Failure language: "CSI300-specific auxiliary workflow."

L1: Source-pretrained auxiliary signal

- Pass: real-source fusion beats random, shuffled-source, unrelated-source, label-shuffle, and time-shifted controls.
- Failure language: "rank-fusion interface effect."

L2: Market-conditioned transfer

- Pass: validation-year-only market-adapted rule beats HGB anchor in external test years.
- Failure language: "internal-market evidence only."

L3: Candidate mechanism

- Pass: perturbation/counterfactual tests show directional movement for volatility, persistence, frequency bands, or drawdown path shape.
- Failure language: "empirical auxiliary signal, mechanism unresolved."

L4: Broad transferable mechanism

- Pass: multiple external market families pass locked or predeclared validation and mechanism tests.
- Failure language: "conditional transfer, not broad transfer."

## Fatal Downgrades

- If external locked transfer remains negative and market-adapted validation fails, do not claim transfer.
- If shuffled/unrelated/phase-randomized sources match real-source, do not claim source-domain mechanism.
- If label/time controls survive, rerun or abandon the claim.
- If reproducibility artifacts are missing, do not target top-journal review.

## Required Reporting

Always report:

- HGB anchor comparison.
- Matched random comparison.
- External non-confirmation.
- Positive seeds and positive years.
- Bootstrap confidence intervals.
- Discovery vs confirmation path.
- Data/code/model availability state.
