# GitHub Reproducibility Plan

## Purpose

GitHub is used as the research control plane for this project: source history, evidence provenance, automated checks, reviewer-facing discussion, and release snapshots live in one auditable place. It is not treated as a substitute for raw-data access or for scientific validation.

## Repository contract

- **Default visibility:** private until the authors decide which code, derived evidence, and manuscript versions are publishable.
- **Source of truth:** the Git repository records code, manifests, documentation, manuscript sources, and small derived tables that can be redistributed.
- **Excluded by default:** raw SCADA files, local caches, credentials, temporary runs, and generated build directories.
- **Evidence status:** claims use `VERIFIED`, `INFERRED`, `UNKNOWN`, or `BLOCKED`; a green CI check does not upgrade an epistemic status.
- **Decision target:** PSREI at the declared nominal 10% violation target; market cashflow and Level-2 AC-OPF remain outside this repository contract.

## GitHub workflows

### Pull requests and pushes

`.github/workflows/verify.yml` runs the lightweight contract layer:

1. Python compilation for the core package and verifier scripts.
2. State/evidence validation through `verify_gate.py --no-run-commands`.
3. Fresh-checkout validation through `scripts/github_smoke_check.py`.

This layer is designed to run without raw data, local caches, or a LaTeX installation.

### Manual full gate

The same workflow exposes a `workflow_dispatch` input named `full_gate`. When enabled, it installs the verifier dependencies, checks that build PDFs and canonical artifacts are present, runs the existing artifact-backed verification gate, and uploads `.agent_state/GATE_REPORT.md`.

The full gate must not be advertised as a clean-clone guarantee because the present evidence gate depends on generated PDFs and experiment artifacts that are deliberately outside the default source package.

## Collaboration protocol

- Open a **Claim or evidence audit** issue for every disputed numerical or causal statement.
- Open an **Experiment or reproduction request** issue for one atomic falsifiable question, with an explicit deployable information set, matched baseline, and acceptance criterion.
- Every pull request records its evidence source, verification commands, and remaining UNKNOWN/BLOCKED scope.
- Changes to manuscript claims, evidence ledgers, verification scripts, or data contracts require review by the repository owner.

## Release path

1. Merge a source-only release candidate after CI is green.
2. Run the full evidence gate on a machine containing the canonical artifacts.
3. Attach the verification report and manuscript PDFs to a GitHub Release.
4. Publish a DOI/archive snapshot only after data licenses, AI disclosure, and artifact provenance are reviewed.

## Immediate security action

The token supplied in the setup conversation must be revoked and replaced. It must never be placed in `.git/config`, workflow YAML, issue text, or repository secrets under a broad personal scope. For future pushes, use GitHub CLI authentication or a repository-scoped token stored by the local credential manager.
