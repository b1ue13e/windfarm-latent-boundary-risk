# Offline review guide

Version: Scientific Reports evidence-closure revision 2, 21 October 2026. This is a local review package, not a submitted or publicly deposited dataset. All results are from completed studies; no experiment or new statistical estimate is produced by this revision.

## Start with the scientific question

Read the main text, its four main figures and Supplementary Tables S1–S10. The measurement-update study is the main reader route. The reconstruction study is a complementary retrospective feature study, not a second independent replication. Both score the same exposed35-day weather window. Existing masks, fits, offsets, predictions, actions, estimates and thresholds are retained.

The cost is a fixed quantile score plus a common target term. Its decomposition describes procurement and uncovered shortfall; the event endpoint and failed combined criteria restrict substitution interpretations. No code or data in this package establishes field procurement, unique pitch information, equal-budget advantage or safe sensor removal.

## Two archives, different responsibilities

1. `scientific_reports_v2_review_sources.zip` contains manuscript/SI, editable figures, figure/table source values, original aggregate summaries and intervals, frozen source packets, separated code copies, configuration/environment records and the review instructions. Its source inventory supports an integrity check without the original project.
2. `scientific_reports_v2_review_materials.zip` additionally contains the403 existing recovered files under `materials/`, plus the lightweight source ZIP and this guide/inventory. These are existing derived channels, coordinates, raw predictions, actions, day blocks, weights and indices. The raw SCADA CSV and new measurements are absent. Some nonprimary R actions/models were never included in the selected recovery scope; their available aggregate/day-block evidence is not described as a full action recovery.

Extract the lightweight archive into a fresh directory. The full archive's material paths are listed exactly in `materials_inventory.csv`. The folder copies and three frozen source packets must not be merged into one code root: their same-named files can have different executed versions.

## Permitted integrity checks (no research execution)

From the extracted lightweight archive root:

```text
python -B review_package/OFFLINE_CHECK.py
python -B review_package/OFFLINE_CHECK.py --materials-archive /path/to/scientific_reports_v2_review_materials.zip
```

The first checks exact file identities, stored thresholds and twelve false corrected-route outcomes. The second additionally hashes every supplied material member against the historical identity inventory. It does not import NumPy, Torch, joblib or experimental modules, unpickle weights, generate predictions, compute action accounting, recalibrate, bootstrap or run historical tests. Successful execution proves the specified bytes/fields are present, not inferential coverage, a successful runtime replay or scientific acceptance.

`source_data/` and `supplement_data/` preserve original result fields. `tables/tableS9.csv` projects original per-fit risk upper bounds; `failure_guard_ledger.csv` lists204 Boolean responsibilities evaluated from stored fields. It matches all12 original corrected-route outcomes. A failed upper-bound qualification is not a proof of excessive population risk. The HGB seed204 reverse-severity lower bound above0.001 is adverse evidence about that specified replacement; it does not rule out every adaptive power-only policy.

## Version and file responsibilities

| Source root | Immutable packet | Inputs and original dependency | Outputs represented here |
|---|---|---|---|
| `code_versions/R/` | `frozen_R_source.tar` | Versioned raw SCADA; R point forecast/prepared arrays; R protocol and five seeds | Shared forecast;30 condition/seed day-block files; primary pitch-withheld fits/actions; original42-cost-family summaries/intervals |
| `code_versions/M_original/` | `frozen_M_original_packet.tar.gz` | Inherited R prepared forecast/physical array; M original protocol; five shared row-index representatives plus70 aliases |70 primary/control tasks, historical q selection, original actions and154-coordinate outputs |
| `code_versions/M_controls/` | `frozen_M_controls_packet.tar.gz` | M original raw predictions, chosen offsets and prepared arrays; later control protocol | Common historical q, procurement-matching constants, corrected B predicate, control actions and596-coordinate outputs |

Packets are in `supplement_data/code_and_provenance/`. `code_version_manifest.json` binds every separated code member to its parent packet bytes. Original remote paths remain historical provenance in immutable protocols; they are not public URLs or runnable paths on another computer. Use the portable inventory to find the corresponding supplied file. Do not substitute the M-control copy of a same-named source file when reviewing original M or R execution.

## Historical stage DAG and documentary commands

**Do not execute these commands as part of document review.** They specify the original runners and their dependencies, not a validated portable environment or an authorised new run. Original PBS wrappers, protocol identities and task/environment index are retained. Commands below show portable placeholders in place of machine-specific paths; they have not been run for this revision.

- R: raw source → `prepare` → historical state and policy fits by seed/condition → stored calibrated actions/day blocks → `aggregate`. The original aggregate covers all30 run folders for the full42-comparison cost family; a single pitch-withheld run cannot reproduce that family.
- Original M: inherited R forecast/physical coordinates → `prepare` →70 indexed `fit` tasks → `select` →70 indexed `evaluate` tasks → `aggregate`. The60 learned fits and10 simple controls share the five original row-index representatives; aliases must follow the saved hashes.
- Later M controls: original M predictions and offsets → `prepare` →10 indexed `history` workers → `freeze` →10 indexed `evaluate` workers → `aggregate`. There are no new learned models in this later procedure. The original/control packets have different corrected predicate versions.

```text
# R source root; <PROTOCOL> = experiments/decision_information_development_20261018/protocol.json
python scripts/run_decision_information_development.py prepare --protocol <PROTOCOL> --raw-csv <RAW_CSV> --output results/prepared --threads 2
python scripts/run_decision_information_development.py run --protocol <PROTOCOL> --prepared results/prepared --output results/runs/seed<SEED>/<CONDITION> --seed <SEED> --condition <CONDITION> --threads 2
python scripts/run_decision_information_development.py aggregate --protocol <PROTOCOL> --runs results/runs --output results/aggregate --threads 2

# Original M source root; <PROTOCOL> = experiments/state_measurement_pilot_20261020/protocol.json
python scripts/run_state_measurement_pilot.py <STAGE> --protocol <PROTOCOL> --base results --output <STAGE_OUTPUT> --task <TASK>

# Later M-control source root; <PROTOCOL> = experiments/state_calibration_controls_20261020/protocol.json
python scripts/run_state_calibration_controls.py <STAGE> --protocol <PROTOCOL> --base results --output <STAGE_OUTPUT> --worker <WORKER>
```

R conditions are `pitch_withheld`, `fresh`, `delay1`, `delay2`, `delay3`, `delay6_stress`; seeds201–205. Original M stages are prepare/fit/select/evaluate/aggregate; later controls use prepare/history/freeze/evaluate/aggregate. Exact stage output layouts and worker/task mapping come from each packet's PBS wrapper and runner. The protocols' external parent-root settings must be mapped to the supplied portable inputs for a later separately authorised replay; the frozen protocol files themselves are not silently rewritten.

## Clock boundary that must remain visible

The original point model consumes a target at12958, released at12959. R state fitting starts at issue12960, whose nominal F publication is12954. The first five issue times therefore use a retrospectively generated F that cannot be certified at that nominal earlier publication; the sixth is equal to release. Label availability before the state-fit issue is satisfied, but availability before every nominal publication is not. The decision-fit nominal publication starts19434, and later stages are also after the consumed-label boundary. This revision keeps the first records and all original fits/results, states their retrospective training status, and does not estimate the consequence of a corrected trim. See Supplementary Table S8 and `revision_evidence/CLOCK_BOUNDARY_AUDIT.json`.

## Runtime and availability limits

Original execution records identify CPU/two threads, Python3.11.16, NumPy2.4.6, scikit-learn1.9.1 and the MLP's recorded Torch environment. `M_environment.csv`, original receipts and source/configuration hashes identify task-specific details. They are not a tested environment lock or container. Original20,000-draw matrices were not persisted; their generator settings, seeds and draw hashes remain. Runtime replay, action-accounting replay and bootstrap coverage have not been validated by this writing revision.

Document rendering uses Python3.12, Pandoc and installed XeLaTeX. Plotting uses Matplotlib and the supplied local alignment helper, identified by its source hash; glyph/collision audits are QA rather than research. Public redistribution of author code/derived materials and any bundled QA utility must be cleared under the applicable licences before release. The original raw data's CC BY4.0 licence does not automatically grant a licence to every author-created derivative or code file.

## Access status

Local files and archives exist with checksums. External reviewer access, author permission and permanent deposit are **not yet assigned**. No upload or submission occurred. This is a concrete local review delivery, not a claim that external users can already download it. Missing access/declarations are in `AUTHOR_ITEMS.md`; the current result and clock bounds must remain unchanged when that administrative work is completed.
