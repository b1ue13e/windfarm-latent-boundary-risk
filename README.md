# Latent Operating-Boundary Recovery and Reserve-Risk Screening

[中文说明](README.zh-CN.md) · [Repository](https://github.com/b1ue13e/windfarm-latent-boundary-risk)

Research codebase investigating whether secondary SCADA consequence signals can recover a latent aerodynamic control boundary (MPPT Region 2 vs. active blade-pitch regulation Region 3) under degraded telemetry, and whether this recovered boundary provides independent value for asymmetric spinning reserve decisions.

## Manuscript Status and Scope Boundary

This repository preserves the manuscript engineering package prepared for *IEEE Transactions on Sustainable Energy* (TSTE):
- Main text: [`paper_tste_ieee.md`](paper_tste_ieee.md) and [`paper_tste_ieee.pdf`](paper_tste_ieee.pdf)
- Technical supplementary: [`paper_tste_supplementary.md`](paper_tste_supplementary.md) and [`paper_tste_supplementary.pdf`](paper_tste_supplementary.pdf)
- Supporting materials: [`cover_letter_tste.md`](cover_letter_tste.md) and [`UPDATED_MANUSCRIPT_CHANGELOG.md`](UPDATED_MANUSCRIPT_CHANGELOG.md)

**Notice on submission status**: The TSTE manuscript format, target templates, and cover letters reflect the prepared manuscript engineering package. They do not constitute proof of active journal submission or acceptance.

## Core Problem and Architecture

- **Research question**: When turbine blade-pitch measurements become unobservable or delayed, can turbine electrical and mechanical response signals recover regime transitions, and does that recovery reduce shortfall risk during operational transitions?
- **Research Question and Scope**: Investigates whether recovered boundary information reduces shortfall risk during operating-regime transitions; see the formal question formulation in [`docs/CANONICAL_RESEARCH_QUESTION.md`](docs/CANONICAL_RESEARCH_QUESTION.md) and the audit resolution in [`RESEARCH_VERDICT.md`](RESEARCH_VERDICT.md).
- **Core package**: `windfarm_moe/` implements spatial-temporal graph modeling, operating regime classification, and mixture-of-experts forecasting.
- **Top-level CLI**: `main.py` provides preprocessing, training, and verification subcommands.

## Environment Setup and Verification

Python 3.10 or 3.11 with standard scientific computing libraries:

```bash
python -m venv .venv
# Activate environment
pip install -r requirements.txt
pip install -r requirements-ci.txt
```

### Smoke Tests and Verification Gates

Run unit and paper-consistency smoke tests:

```bash
python -m pytest tests/test_smoke.py tests/test_paper.py
```

Run the lightweight replication and claim verifier:

```bash
python scripts/verify_replication.py
```

Run the automated contract check:

```bash
python .agents/scripts/verify_gate.py
```

## Key Documentation and Artifact Maps

- [Canonical Research Question](docs/CANONICAL_RESEARCH_QUESTION.md): frozen mathematical definition of states, information sets, and decision bounds.
- [Evidence Map](docs/REPOSITORY_EVIDENCE_MAP.md): navigation across experimental evidence and decisive gates.
- [Research Verdict](RESEARCH_VERDICT.md) and [Decisive Report](DECISIVE_EXPERIMENT_REPORT.md): final audit resolution and bounded operational limits.
- [Artifact Manifest](artifacts/ARTIFACT_MANIFEST.json): SHA-256 checksum registry for derived evaluation arrays.
- [Data Availability](docs/DATA_AVAILABILITY_AND_PREPROCESSING.md): source data provenance and download instructions.
- [Clean-Clone Reproducibility Audit](docs/CLEAN_CLONE_REPRODUCIBILITY_AUDIT.md): external replication audit.
- [Task Contract](START_PROMPT.md): non-negotiable verification and scientific integrity rules.

## Branch and Remote Notice

This documentation describes the tracked files on the remote default branch (`revision_topjournal_reconstruction`). Local developer environments may hold experimental caches, historical logs, or unpushed revisions that are intentionally kept distinct from this remote branch.