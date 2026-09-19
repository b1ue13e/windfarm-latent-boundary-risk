# Statistics And Reproducibility

Use this file for statistical audit, uncertainty, reproducibility packaging, and official policy distinction.

## Statistical Integrity

For AI/ML projects, require:

- Predefined primary metric and primary comparison.
- Effect size and uncertainty interval, not only significance.
- Multiple random seeds and per-seed results.
- Appropriate paired tests when comparing models on the same examples.
- Multiple-comparison correction when many hypotheses, groups, metrics, or thresholds are tested.
- Clear outlier/exclusion rules decided before inspecting the desired result.
- Calibration and decision-threshold reporting when claims depend on probabilities or accepted sets.
- Subgroup and stress-regime reporting when the broad claim depends on heterogeneity.

If the project uses classical statistical tests:

- Check distributional assumptions before parametric tests.
- Use nonparametric or bootstrap alternatives when assumptions are weak.
- Report confidence intervals and sample sizes.
- Avoid mixing technical repeats with independent biological/entity repeats.

For computational benchmarks, "power analysis" often becomes minimum detectable effect, bootstrap precision, or simulation-based sensitivity analysis.

## Reproducibility Package

A Science-level computational reproducibility package should include:

- Data download or access instructions.
- Dataset license and third-party terms.
- Preprocessing scripts.
- Train/evaluate scripts.
- Environment lock: `requirements-lock.txt`, `environment.yml`, container, or exact package versions.
- Random seeds and deterministic settings where possible.
- Model checkpoints or instructions for regenerating them.
- Raw per-example predictions or score files for key tables.
- Figure source data and figure-generation scripts.
- A short reproduction path for main figures and tables.
- Checksums or artifact manifest for important files.

If data cannot be public, require a controlled-access plan and a synthetic or de-identified reproduction path where feasible.

## Figure And Result Traceability

Every table or figure should answer:

- Which raw or processed data file created it?
- Which script created it?
- Which commit or version created it?
- Which parameters and random seeds were used?
- Can a reader regenerate it without contacting the authors?

If the answer is no, mark it as a reproducibility gap.

## Official Policy Anchors

When exact policy matters, verify official sources:

- Science information for authors for manuscript structure and methods expectations: `https://www.science.org/authors/science-information-authors`
- Science journals editorial policies for research integrity, ethics, and publication policy: `https://www.science.org/content/page/science-journals-editorial-policies`
- Science Partner Journals program overview for the relationship between SPJ and AAAS/Science best practices: `https://spj.science.org/program-overview`
- SPJ author guidelines as quasi-official same-publisher practice references for data/material/software availability, statistical reporting, and ethics, for example: `https://spj.science.org/page/research/for-authors`
- Repository-specific policies for data types: GEO/SRA for sequencing, PDB for structures, Zenodo/OSF/Dryad/Figshare for general artifacts, GitHub plus archival DOI for code.

Use cautious phrasing:

- Say "official policy requires or states" only after verification.
- Say "Science-level best practice" for hostile-reviewer controls, extra negative controls, orthogonal validation, and one-command reproduction if not directly mandated.

## Availability Statements

Audit, do not invent:

- Data availability statement.
- Code availability statement.
- Model availability statement.
- Materials availability statement if physical, biological, or specialized computational artifacts are involved.
- Ethics/IRB/animal/human-subject statement when applicable.
- License and terms-of-use statement for third-party data.

If information is absent, write `needs verification` or `not yet provided`.
