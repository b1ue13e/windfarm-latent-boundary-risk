# Completion Contract

This rule always applies to complex tasks.

## Task ledger semantics

Use exactly these task states:
- `[ ] TODO`
- `[-] DOING`
- `[x] VERIFIED`
- `[!] BLOCKED`

Each task line must contain a stable task ID such as `T01`, `T02`, ... and an observable acceptance criterion.

Example:

`- [x] T03 VERIFIED — Regenerate Figure 2 and remove the deprecated subtitle. Acceptance: regenerated PDF exists; old phrase count is 0; new phrase count >= 1.`

## Evidence requirement

Every `VERIFIED` task requires at least one matching `Task-ID: Txx` section in `.agent_state/EVIDENCE_LEDGER.md`.

Strong evidence:
- exact file path + line/range inspected;
- command + exit code + relevant output;
- test/compile log + artifact path;
- source URL/identifier + exact supported claim;
- checksum or file existence check when appropriate.

Weak evidence that cannot stand alone:
- "looks correct";
- "should work";
- previous assistant summary;
- a task checkbox created by the same model;
- a generated report that merely repeats the intended result.

## Stop condition

Do not end a long task merely because progress is substantial. Finalization is a separate task and requires:
1. independent review;
2. verification commands;
3. `verify_gate.py` PASS.
