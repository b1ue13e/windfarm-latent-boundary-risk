# Orthogonal Evidence Chain

Use this file when converting claims into a matrix of independent evidence.

## Principle

Science-level evidence is not one method repeated many times. It is a set of independent tests that would fail for different reasons. For AI/ML, orthogonality usually means combining predictive performance, mechanism/intervention, external validation, and reproducible artifact evidence.

## Minimum Matrix

For each major claim, fill this matrix:

| Claim | Current evidence | Missing evidence | Orthogonal validation | Reviewer attack |
|---|---|---|---|---|
| What the paper wants readers to believe | Existing figures/tables/results | Decisive missing experiment | Independent method or data source | Strongest alternative explanation |

## Evidence Types

Use at least three independent evidence types for a Science-level central claim:

1. **Predictive or quantitative evidence**
   - Strong baselines, uncertainty, external validation, subgroup analysis, and failure cases.

2. **Mechanistic or explanatory evidence**
   - Intervention, perturbation, counterfactual editing, causal mediation, theory-derived prediction, or interpretable intermediate variable.

3. **Generalization evidence**
   - New domains, time periods, institutions, instruments, data families, or stress regimes.

4. **Negative-control evidence**
   - Placebo outcomes, impossible time orders, shuffled labels, artifact checks, leakage sentinels, or domain where the mechanism should not appear.

5. **Reproducibility evidence**
   - Public data/code/model artifacts, figure source data, environment lock, one-command reproduction, and independent rerun.

## Claim Decomposition

Split overlarge claims before evaluating evidence.

Bad claim:

> Our model discovers a universal mechanism of disease progression.

Better decomposition:

- The model predicts progression better than strong clinical and ML baselines.
- The learned factor corresponds to a measurable biological pathway.
- Perturbing that pathway changes predictions in the expected direction.
- The factor generalizes across hospitals, cohorts, and measurement platforms.
- Negative-control outcomes do not show the same pattern.

## Orthogonality Warnings

These are not truly orthogonal by themselves:

- Same dataset with more metrics.
- Same model with different random seeds.
- Same benchmark with slightly different split.
- Multiple post-hoc explanation maps using the same trained model.
- More ablations that only prove engineering contribution, not scientific mechanism.

They can support stability, but they do not replace independent evidence.

## Rescue Experiments

Common missing decisive experiments:

- External cohort or domain holdout.
- Intervention on the claimed causal factor.
- Synthetic data where ground-truth mechanism is known.
- Counterfactual editing of inputs or environments.
- Independent measurement modality.
- Human expert or domain-standard protocol comparison.
- Placebo and negative controls.
- Prospective or time-forward validation.
