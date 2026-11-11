# Portable archived-result review package

**Local prepublication candidate; not publicly deposited, licensed for redistribution, submitted, or externally certified.**

This directory supports numerical review of the Wind Energy revision without the original workstation, cluster access, measurement files, model weights, private skills, or external packages. Python 3.10 or later is sufficient for the verifier.

From any location, run:

```text
python verify_package.py
python -m unittest test_package.py
python refresh_manifest.py --check
```

The default report is written to standard output; `--output report.json` optionally saves a local report. The auditor reads only package-relative paths. It does not import the model source snapshots, access the network, fit models, predict, recalibrate, generate bootstrap draws, or open measurements. After author-approved packaging changes, run `python refresh_manifest.py` and rerun the auditor; manifest refresh is not public release or proof of new provenance.

## What can be checked

- Every listed file's size and SHA256, and byte-identical versus explicitly projected source identities in `PROVENANCE.json`.
- The primary q0.95 labels, frozen historical-choice hash, fourteen-coordinate envelope, paired cost-ratio direction and five fixed-instance event-rate bounds.
- All three stored secondary full-family envelopes, their deterministic sufficiency inequalities and smaller-candidate exclusion witnesses; the separate q0.925 result and its fifteen exclusions.
- The Figure 3 cost bridge directly from stored ratios: approximately 0.9742% for q0.925 and 3.5178% for q0.95, against the original 2% requirement. The latter is non-certification, not proof that true regret exceeds 2%.
- All ninety Towie classifications and the 63/24/3 frozen-choice outcomes. These are dependent assessments, not ninety independent studies.
- All 420 WTB classifications against the original stored aggregate envelopes and necessity records, including 367 no certified sufficient policy, 53 unresolved minimum, and zero identified minima. No interval is recomputed.
- The ten-row fixed-instance loss ledger and the point increase in uncovered-shortfall magnitude. No new shortage interval or significance test is supplied.
- The archived Figure 2 source CSV against primary JSON fields. V2 Figure 3's seventeen source rows are checked field by field against the original aggregate: both cost and risk upper bounds, the controlling possibly feasible competitor, all fifteen exclusions, and the risk qualification of every cost witness. Other plotted data and all supplement CSVs have byte/source identity records.

`data/confirmation/` and `data/wtb/` hold completed aggregate statistical outputs. `data/history/` retains historical choices and bounds. `csv/` contains the complete supplementary attachments. The CSVs directly under `figure_data/` are explicitly preserved V1 plot data; `figure_data/v2/` contains the four V2 plot CSVs and Figure 3 field manifest. `figures/` holds the four V2 figures in PDF, SVG and PNG. The verifier checks the decisive V2 bridge directly; it does not certify pixel identity or independently regenerate every graphic.

`documents/` contains the local V2 manuscript and supplement in PDF/editable sources, references and the CSL's original licence, the revision response, the Chinese four-question explanation, and remaining evidence/publication gaps. The interface review distinguishes general forecast-derived reserve practice from the still-unestablished exact two-feed use case. These documents are included for local review, not represented as an already accepted, submitted or publicly deposited article.

`source_static/` contains essential frozen calculation, selection, feature and execution source for **static inspection only**. It is not an installable research pipeline. `PROVENANCE.json` records the source commit, execution hash match where available, and CRLF-normalized Git-content match. Internal deployment paths were removed only from the protocol/freeze/seed-ledger projections; the original hashes and omitted-field descriptions remain explicit. The original full execution archive is not included or claimed to be reconstructible from a projected freeze record.

## What cannot be reproduced or certified

This is an **archived-statistic and decision-audit package**, not end-to-end computational reproduction. It does not regenerate training, fitted weights, raw trajectories, daily action totals, bootstrap draws, or the archived confidence envelopes. Original measurement archives, models and full execution dependencies are not bundled. Matching stored numbers does not establish nominal confidence coverage, seasonal exchangeability, field safety, cross-site transfer, real reserve delivery, cancelable telemetry costs, or a business-approved tolerance.

The five fixed fits remain conditional instances, not five independent weather realizations. Primary and secondary envelopes have different multiplicity families. One-, three- and seven-day sensitivities are not pooled into a new confidence guarantee. Public source availability does not resolve previously documented exposure or create a new confirmation window.

## Publication and rights status

No archival DOI, release URL, blanket open-source licence or redistribution permission is asserted. Authors must confirm rights for source code, derived data, and the final package and select a repository before publication. The original wind-data licences and citation duties remain applicable; no third-party paper PDFs, measurement archives, private skill files, credentials, cluster host details, or user-specific absolute paths are included. See `PUBLICATION_GAPS.md`.

The SHA256 manifest is an integrity record, not a digital signature or independent timestamp. The manifest does not hash itself. Verification outputs, the portability report and bytecode caches are generated files outside its scientific payload. The refresh script only inventories approved file types and directories, refuses symlinks and common private deployment strings, and rejects unexpected files rather than silently publishing them. Do not use it to relabel altered scientific outputs as original records.
