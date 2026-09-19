# AI/ML Experiment Hardening

Use this file to convert a promising AI/ML experiment into a hostile-reviewer-resistant experiment plan.

## Baseline Ladder

Require baselines in tiers:

1. **Trivial controls**: random, majority, naive, chronological naive, rule-based, or simple heuristic.
2. **Classical strong controls**: linear/logistic, random forest, gradient boosting, calibrated SVM, ARIMA/ETS, or domain-standard non-deep method.
3. **Current SOTA**: recent strong models, domain leaderboards, foundation models, or widely accepted production baselines.
4. **Oracle or upper-bound controls** when relevant: target-domain oracle, label-leakage sentinel, perfect calibration upper bound, or human expert benchmark.
5. **Ablated versions**: remove each claimed contribution and each data source that carries scientific meaning.

Do not accept a claim as strong when the main competitor is weak or misconfigured.

## Leakage And Confounding Audit

For every dataset or split, check:

- Train/validation/test isolation.
- Time leakage and look-ahead bias.
- Subject, patient, site, province, asset, or batch overlap.
- Duplicate and near-duplicate examples.
- Target-derived features, post-outcome features, or preprocessing fitted on the full dataset.
- Hyperparameter selection using test labels.
- Early stopping, model selection, or checkpoint selection using target-domain information.
- Batch, instrument, geography, platform, labeler, or acquisition artifacts.

Recommended decisive tests:

- Label-shuffle sanity check.
- Feature-shuffle or target-derived-feature removal.
- Grouped splits by entity, site, time, or domain.
- Leave-one-domain-out validation.
- Dataset artifact classifier: can a simple model detect the split/domain too easily?

## Stability Requirements

For Science-level claims, a single lucky run is not evidence.

Require:

- Multiple random seeds with mean, uncertainty, and per-seed table.
- Multiple data splits where the split is not fixed by a public benchmark.
- Sensitivity to preprocessing, missing-data handling, calibration, and threshold choice.
- Hyperparameter robustness around the selected configuration.
- Failure cases and boundary conditions.

For high-stakes claims, report effect sizes and confidence intervals, not only p-values.

## Ablation And Mechanism Tests

Each main contribution must have a direct ablation:

- Remove the proposed module.
- Replace it with a simple alternative.
- Freeze or randomize the claimed mechanism.
- Vary the mechanism strength.
- Test whether the claimed intermediate variable changes as predicted.

For interpretability claims:

- Do not rely on saliency or attention alone.
- Add intervention: remove, perturb, mask, counterfactually edit, or synthetically generate the claimed factor.
- Compare with known causal or mechanistic markers when available.

## External And OOD Validation

Broad claims need validation outside the discovery setting:

- New dataset family.
- New institution, geography, species, material, market, time period, or instrument.
- Temporal holdout beyond the model-selection period.
- Cross-domain transfer without reselecting the main story.
- Stress conditions, distribution shift, or rare-event regime.

If external data are unavailable, state that the Science claim is not yet supported and propose the nearest credible proxy.

## Negative Controls And Placebos

Use negative controls to rule out story-shaped artifacts:

- Outcome placebo: predict a related but scientifically irrelevant outcome.
- Exposure placebo: use a fake intervention or impossible time order.
- Domain placebo: test where the mechanism should not operate.
- Feature placebo: include random or shuffled features.
- Label placebo: shuffle labels or permute within groups.
- Temporal placebo: shift the event date to a false window.

Strong negative controls are often more valuable than extra positive benchmarks.
