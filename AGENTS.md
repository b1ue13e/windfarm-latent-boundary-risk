# AGENTS.md

## Language
默认使用简体中文，除非用户明确要求英文。

## Skill routing
遇到以下任务时，优先使用对应 skill：

- 论文拆解 / claim 分析 / reviewer 风险
  使用：论文拆解器

- 研究想法落地 / 科研工具设计 / 项目规划
  使用：研究项目PRD生成器

- 摘要 / 引言 / 方法 / 结论润色
  使用：学术文档润色器

- 降低 AI 感 / 报告味 / 模板味
  使用：论文降AI率重写器

- 按给定 PDF 的结构和风格写作
  使用：PDF写作格式适配器

## Guardrails
- 默认一次只使用一个主 skill
- 除非用户明确要求，不要混用多个主 skill
- 优先保证输出结构稳定
- 不要把摘要复述当作论文分析
- 不要把表面同义替换当作降 AI 重写

## Git workflow
- 每次完成代码修改后，都需要提交一次 git commit。

---

# Reliability Contract for Antigravity

This repository uses an evidence-first execution protocol for long, complex tasks.

## Non-negotiable rules

1. Never claim a task, edit, test, compilation, search, experiment, citation check, or external fact is complete unless there is direct evidence.
2. At the start of every turn, and after every subagent returns, read `.agent_state/RUN_STATE.json`, `.agent_state/TASK_LEDGER.md`, and `.agent_state/EVIDENCE_LEDGER.md` if they exist.
3. Before making substantive edits on a complex task, create or refresh the task ledger with atomic acceptance criteria.
4. Do not silently delete, merge, weaken, or reinterpret user requirements. New discoveries may add tasks, but scope reduction must be explicit.
5. Every completed task must have at least one evidence entry. A checkbox without evidence is not completion.
6. Distinguish epistemic status:
   - VERIFIED: directly supported by file contents, command output, test output, compilation output, or a cited source.
   - INFERRED: reasonable inference from verified evidence, but not directly checked.
   - UNKNOWN: no adequate evidence is currently available.
7. Never convert INFERRED or UNKNOWN into VERIFIED because it is plausible.
8. For numerical scientific claims, experiment counts, table values, citations, API behavior, and version-specific facts, require a concrete source.
9. If a command was not actually executed, do not describe its result.
10. Before final completion, run the verification gate and obtain PASS. If the gate fails, continue working or report the unresolved blockers accurately.

## Long-task anti-drift protocol

Checkpoint state after any of the following:
- a meaningful task is completed;
- 5-8 substantive tool operations have occurred;
- a subagent returns;
- the task scope changes;
- before a likely context compaction or handoff;
- before final verification.

A checkpoint means updating the task ledger, evidence ledger, decision log, and `RUN_STATE.json` so the project state can be reconstructed without trusting chat memory.

## Research-specific grounding

Do not invent papers, citations, DOI values, journal policies, metrics, experiment results, datasets, hardware, baselines, statistical significance, reviewer comments, or manuscript contents. If a source cannot be inspected, mark the claim UNKNOWN or explicitly state that it was not verified.

A successful compile only proves compilation. It does not prove scientific correctness, figure quality, numerical consistency, citation validity, or compliance with a journal.

## Completion standard

A final response may use completion language only if:
- all required ledger tasks are VERIFIED or explicitly BLOCKED with a reason;
- all required verification commands have passed;
- required artifacts exist;
- the independent evidence reviewer has issued PASS or PASS_WITH_BLOCKERS;
- `.agents/scripts/verify_gate.py` returns exit code 0.

If any of these conditions are missing, describe the work as partial rather than complete.
