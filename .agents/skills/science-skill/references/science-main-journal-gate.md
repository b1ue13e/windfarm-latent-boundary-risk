# Science Main-Journal Gate

Use this file to decide whether an AI/ML project has Science main-journal shape or only strong conference shape.

## Central Standard

Science main-journal experiments must support a major advance in understanding. For AI/ML, the model is rarely the contribution by itself. The experiments must show that the method reveals, tests, or changes a scientific claim that matters beyond one benchmark community.

Use this triage:

| Verdict | Meaning |
|---|---|
| `Go` | The project has a broad claim, decisive controls, orthogonal evidence, external validation, and reproducible artifacts. |
| `Conditional Go` | The idea is potentially Science-level, but one or more decisive evidence layers are missing. |
| `No-Go` | The work is incremental, benchmark-bound, under-controlled, or overclaims from insufficient evidence. |

## Science-Level Versus Strong AI/ML Paper

Strong AI/ML paper:

- Improves a method or benchmark result.
- Provides standard ablations and comparisons.
- Shows engineering novelty or efficiency.
- May be excellent for NeurIPS, ICML, ICLR, KDD, or a domain journal.

Science main-journal AI/ML paper:

- Resolves an important scientific uncertainty or exposes a previously hidden mechanism.
- Shows why the result happens, not only that it happens.
- Survives strong alternative explanations.
- Generalizes across systems, time, domains, species, regions, materials, tasks, or instruments as appropriate.
- Provides a reproducible experimental object that other labs can inspect and extend.

## Claim Pressure Test

Ask these questions before recommending more experiments:

- What old assumption, field debate, or practical bottleneck is being overturned?
- Would the claim still matter if the model name were removed?
- Is the central evidence mechanistic, causal, structural, or only predictive?
- Is there an external system where the claim is tested without retuning the story?
- What would a hostile reviewer say is the simplest alternative explanation?
- Does the current evidence rule that alternative out?

## No-Go Patterns

Mark as `No-Go` for Science main journal when most of these hold:

- Accuracy or AUROC improves by a small margin without scientific interpretation.
- Baselines are weak, old, misconfigured, or missing obvious SOTA.
- Only one dataset family supports the main claim.
- The strongest result depends on one split, one seed, one preprocessing choice, or one metric.
- Mechanistic claims rely only on saliency maps, attention heatmaps, or post-hoc visualizations.
- There is no public reproducibility path.
- Ethical, privacy, licensing, or data-access barriers prevent independent verification and are not handled transparently.

## Conditional-Go Patterns

Use `Conditional Go` when:

- The claim is broad and important, but external validation is missing.
- The model exposes a plausible mechanism, but intervention or counterfactual tests are missing.
- The benchmark is unusually strong, but source data, code, or figure-generation reproducibility is incomplete.
- Negative controls and placebo tests are not yet run.
- The paper has a Science-level question but is still organized like an algorithm paper.

## Official Anchors To Verify When Needed

When the answer depends on exact journal policy, check official Science/AAAS pages rather than relying on memory:

- Science information for authors: `https://www.science.org/authors/science-information-authors`
- Science journals editorial policies: `https://www.science.org/content/page/science-journals-editorial-policies`
- Science Partner Journals program overview: `https://spj.science.org/program-overview`
- SPJ author-guideline pages, as quasi-official same-publisher practice references for data deposition, availability, materials sharing, ethics, and statistical reporting, for example `https://spj.science.org/page/research/for-authors`
- Field-specific repository guidance when applicable, such as GEO, SRA, PDB, Zenodo, OSF, Dryad, or institutional repositories.

Keep official policy separate from best-practice recommendations.
