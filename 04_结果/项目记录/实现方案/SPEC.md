# Implementation Spec — Metis E04 Receipt/Hash Binding

- **Target:** Bind E04 policy-array outputs and selector output to immutable execution receipts so a result cannot be treated as executed merely because files exist.
- **Inputs:** `experiments/E04/code/select_e04_v2.py`, five `seed*_full_policy_day_blocks.npz` files, frozen preregistration JSON, command/input metadata.
- **Outputs:** `experiments/E04/code/e04_provenance.py`; selector-side receipt verification; regression tests; `implement-stage/` build records.
- **Output schema:** JSON receipt with schema version, status, argv, git commit, preregistration hash, input file records, output manifest hash, output file records, and receipt hash recorded by the parent result.
- **Success command:** `python -m pytest tests/test_e04_receipt_binding.py -q`.
- **Base commit:** `5b8c154d`.
- **Scope cuts:** No rerun of Metis jobs, no changes to E04 thresholds/candidates/statistics, no retroactive certification of existing v4 arrays, and no manuscript claim upgrade.
