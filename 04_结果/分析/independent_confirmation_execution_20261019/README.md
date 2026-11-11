# Frozen independent confirmation

Start with `REPORT.md` and `CLAIM_EVIDENCE.md`. The independent implementation, historical and confirmation reviews record the audit scope and retained limitations.

- `deployment_packet.tar.gz`: exact pre-test source/configuration/PBS bytes, bound by `transport.json` and `deployment_manifest.json`; normalized tracked source commit24153f8.
- `result_evidence.tar.gz`: compact completed output,5037 members; exact local/remote mapping and SHA in `download_manifest.json`. Raw annual SCADA, physical channels, full actions, fit indices and model pickles remain on Metis.
- `history_freeze/`: the five exact chosen-stage files, also inside the output archive. `unlock_release.json` records scheduling authorization; the actual one-time event is inside the recovered archive and independently audited.
- `recovered/` is a loose ignored extraction. To recreate it on a fresh copy, verify the outer hash and extract into a new empty directory, then verify every `export_manifest.json` entry. Do not overwrite old results. Both source and output tarballs are needed for exact source replay; standalone Git newline conversion may change byte hashes.
- `derived/` is read-only reporting from frozen outputs. Run `summarize_confirmation.py` only in a fresh directory copy without an existing `derived/`; it refuses replacement and records input/source identities. It does not fit or resample.
- Additional archive/claim consistency: `python scripts/verify_independent_confirmation_gate.py --output <new-file.json>`. It verifies history before unlock, source/protocol identity, primary fixed-reference verdict and all90 secondary minimality classifications. It also accepts faithfully reported negative outcomes. Original scientific/number gates remain unchanged.
- `snapshots/` preserves the pre-update manuscripts/PDFs and documents. Current PDFs are at repository root; build/render/final gate receipts describe the checked version. Loose TeX build and full-resolution renders are ignored; reviewed overview images are retained.

Confirmation data have now been used. They cannot become untouched again through renaming, refitting or a new folder. Any later outcome-informed tuning is exploration. None of these consistency checks certifies bootstrap coverage or field safety.
