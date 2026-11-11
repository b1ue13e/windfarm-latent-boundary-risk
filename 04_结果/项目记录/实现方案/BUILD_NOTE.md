# Build Note — Metis E04 Receipt/Hash Binding

| Rung | Feature | Acceptance check (ONE command) | Tier | Status |
|------|---------|-------------------------------|------|--------|
| F0 | Receipt/manifest utility can write and verify a complete E04 output bundle | `python -m pytest tests/test_e04_receipt_binding.py -q` | MUST | ✅ VERIFIED (5 passed) |
| F1 | E04 selector requires a verified receipt and binds its result to the receipt/manifest | `python -m pytest tests/test_e04_receipt_binding.py tests/test_replay_integrity.py -q` | MUST | ✅ VERIFIED (19 passed) |

## Run record

- Base commit: `5b8c154d`.
- `python -m pytest tests/test_e04_receipt_binding.py -q` -> exit 0, 5 passed.
- `python -m pytest tests/test_e04_receipt_binding.py tests/test_replay_integrity.py -q` -> exit 0, 19 passed, 1 unrelated pynvml deprecation warning.
- `python -m py_compile experiments/E04/code/e04_provenance.py experiments/E04/code/run_e04_bound.py experiments/E04/code/select_e04_v2.py tests/test_e04_receipt_binding.py` -> exit 0.
- Wrapper smoke command -> exit 0; generated `e04_execution_plan.json`, `e04_output_manifest.json`, and `e04_execution_receipt.json` with status `EXECUTED`.
- Independent Codex silent-assumption sweep -> unavailable: runtime returned `WinError 2`; no external PASS claimed.

## Deferred

- No Metis rerun or remote launcher execution in this code-only fix.
- No retroactive promotion of the existing v4 arrays.

## Blockers

- None yet.
