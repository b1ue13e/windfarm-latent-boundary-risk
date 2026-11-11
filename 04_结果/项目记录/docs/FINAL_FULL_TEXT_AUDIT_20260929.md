# Full-Text Manuscript Audit

**Date:** 2026-09-29
**Scope:** Current main manuscript, supplementary manuscript, standalone source, current build outputs, scientific contract, experiment registry, and submission-freeze provenance.

## Reviewed scope

- Main manuscript source: \`paper_tste_ieee.md\` (501 lines), read section by section.
- Supplementary source: \`paper_tste_supplementary.md\` (1814 lines), including narrative text, table captions, notes, figures, reference directory, and exploratory appendices.
- Standalone source: \`standalone_ieee_package/main.tex\`.
- Current builds: \`build/paper_tste_ieee.pdf\` and \`build/paper_tste_supplementary.pdf\`.
- Authority files: \`docs/SCIENTIFIC_CONTRACT.md\` and \`docs/EXPERIMENT_REGISTRY.md\`.

## Corrections made in this pass

1. The \`46.7--68.6 kW h\` range is now identified as relative to condition-matched recalibrated physics. It is not described as a reduction relative to unadapted physics.
2. “Routinely encounter” was bounded to “can encounter” because the field distribution of industrial latency remains unknown.
3. The supplementary statement that the Kelmarsh timing statistic “proves” a communication-delay claim was changed to “indicating”; the statistic is explicitly stated not to identify the underlying delay distribution.
4. “Static recalibration breaks down only ...” was bounded to the evaluated latency grid.

## Open findings

### F1 — Canonical steady-state delta conflict (OPEN, P1)

The current strong-baseline CSV and current manuscript use \`+410,304 kWh\`, while the authoritative scientific contract and experiment registry use \`+410,340 kWh\`. Older closure reports contain additional rounded variants (\`+410,339\`, \`+410,340\`, and \`+410,217\`). No value was changed in this audit because the canonical estimand/artifact pair must be resolved first.

Required resolution: select one registered artifact as the canonical source, reconcile the arithmetic and rounding convention, then update the contract, manuscript, supplementary text, verifier, and release manifest together.

### F2 — Submission freeze is stale (OPEN, P1)

The current sources were modified after the 2026-09-23 PES-compliant freeze. The freeze directory and ZIP must be regenerated from the corrected current source and current PDFs before upload.

### F3 — Historical provenance documents contain superseded claims (OPEN, P2)

Some older audit/provenance documents still contain pre-closure global-quantile superiority or decision-value language. They are not current manuscript sources, but the repository must continue to mark them as historical provenance and prevent them from entering a release package as current evidence.

## Verification status

This audit is not complete until the corrected sources are rebuilt, the standalone source is re-exported, all verification commands pass against the new build, and a regenerated submission package has a fresh checksum manifest.
