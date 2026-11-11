# Recovery bundle

Read `REPORT.md` for current conclusions and `CLAIM_EVIDENCE.md` for claim limits.

The three tarballs preserve the recovered numerical evidence and source metadata. Loose `evidence/`, `necessity/` and `source_metadata/` trees are intentionally excluded from Git; their archive identities are in `download_manifest.json`. On a fresh copy of this directory, extract each tarball into the corresponding loose tree. Verify the outer SHA256 values and the `export_manifest.json` members before using them. The remote source archive was downloaded locally as `source_metadata.tar.gz`; its remote basename differs.

For read-only reporting, run `python analyses/claim_revision_recovery_20261019/summarize_evidence.py` from the repository root **in a fresh directory copy without `derived/`**. The script refuses to overwrite an existing output directory. Do not delete the archived derived results to rerun in place. Input/source hashes and reporting environment are recorded in `derived/receipt.json`. This command neither fits policies nor resamples uncertainty.

Main export includes compact archived blocks, aggregate statistics, source/configuration and execution receipts, rather than every large model/fit-index/raw-action file. Those full assets remain on Metis; `latest_remote_verification.json` checks the actual historical source outputs. Raw annual SCADA archives and derived historical channel arrays are not committed here. No operation in this bundle authorizes parsing the sealed 2025 archive.

`snapshots/` contains exact pre-edit documents/PDFs. Current manuscript PDFs are at the repository root. `build_receipt.json`, `render_receipt.json`, overview images in `rendered/` and `final_validation.json` record the Pandoc/XeLaTeX build and checks. The local loose build and full-resolution rendered PNGs are excluded from Git; retained overview images document the review. `gates_initial/` and `validation_attempt1.json` retain failed checks; `gates_release/` contains the final unchanged consistency gates. `software_tests_receipt.json` records eight passing reporting/necessity/source-adapter regression tests.

These checks establish the stated artifact and consistency scope, not bootstrap coverage, independent confirmation, minimality or field safety.
