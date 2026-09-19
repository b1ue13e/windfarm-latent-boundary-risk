# Recommended task opening prompt

Use the `research-orchestrator` custom agent, then give it your real task followed by:

> This is a long-task reliability run. Preserve every material requirement in the task ledger. Do not claim any edit, experiment, test, compile, literature fact, numerical claim, or repository-wide consistency result without direct evidence. Keep `.agent_state/` current throughout the run. Before finalizing, use an independent reviewer and run `python .agents/scripts/verify_gate.py`. If the gate fails, continue working rather than summarizing prematurely.

You do not need to paste this paragraph every time once the custom agent is active; it is included here as a recovery prompt if a session drifts.
