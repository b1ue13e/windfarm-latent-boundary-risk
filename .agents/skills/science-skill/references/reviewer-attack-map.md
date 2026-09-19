# Reviewer Attack Map

Use this file to generate a prioritized supplement and experiment plan.

## Attack Categories

Map every likely reviewer objection to a decisive response:

| Attack | What it means | Decisive response |
|---|---|---|
| Alternative explanation | Existing theory, simpler model, artifact, or confound explains the result | Strong baseline, negative control, counterfactual, or stratified analysis |
| Data bias | Dataset, site, batch, period, labeler, or sampling process drives the claim | External validation, grouped split, batch audit, domain holdout |
| Overfitting | Result depends on split, seed, hyperparameters, or benchmark selection | Multi-seed, nested validation, hyperparameter sensitivity, unseen benchmark |
| Leakage | Target information enters features or model selection | Leakage sentinel, chronological/group split, preprocessing isolation |
| Causal overclaim | The paper uses causal language without causal design | Downgrade language or add intervention, quasi-experiment, mediation, placebo |
| Mechanism thinness | Model explains nothing beyond correlation | Perturbation, ablation, theory-derived intermediate, independent modality |
| Generalization gap | Claim is too broad for one dataset or domain | External cohort/domain/time validation |
| Reproducibility risk | Reader cannot regenerate results | Public artifact, figure source data, environment lock, reproduction scripts |
| Compliance risk | Privacy, license, ethics, or material-sharing unclear | Approval/accession/license statement, controlled access, data-use audit |

## Priority Rules

Rank proposed work as:

- `Fatal`: without this, the main claim is not credible or may be rejected at editorial/peer review.
- `High-priority`: needed for Science-level strength but not necessarily fatal for a narrower venue.
- `Strengthening`: useful for supplement, rebuttal, or broader adoption.

Prefer one decisive test over several decorative ones.

## Output Template

Use this compact format:

```text
Fatal
- [Experiment/check] -> closes [attack]. Expected decision: if it fails, downgrade claim to [narrower claim].

High-priority
- [Experiment/check] -> closes [attack]. Expected decision: if it fails, keep claim but add boundary [boundary].

Strengthening
- [Experiment/check] -> improves [stability/reproducibility/readability].
```

## Claim Downgrade Rules

If experiments fail or are unavailable, downgrade honestly:

- "Universal" -> "observed across tested domains".
- "Causal" -> "associated with" or "consistent with".
- "Mechanism" -> "candidate mechanism".
- "Robust" -> "stable under the tested perturbations".
- "Deployment-ready" -> "retrospectively validated".
- "Science main-journal ready" -> "strong specialist-venue or Science-family-subjournal candidate".

## Reviewer-Facing Discipline

Do not cite cost, time, or convenience as the primary reason for missing decisive evidence. Use scientific boundaries:

- Data do not yet exist.
- Ethical or legal access prevents direct test.
- Measurement is outside the current causal scope.
- Current evidence supports a narrower claim.
- A future prospective study is required before deployment language is appropriate.
