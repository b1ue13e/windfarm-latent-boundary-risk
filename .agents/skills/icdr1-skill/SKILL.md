---
name: icdr1-skill
description: Keep ICDR1/RGRC research execution aligned with the ICLR 2027 sprint strategy and long-horizon time-series protocol. Use when working on ICDR1, RGRC, Role-Gated Residual Correction, residual attention for time-series forecasting, fixed-budget chunk routing, bi-directional frequency separation loss, RDR/RCR diagnosis, ICLR experiment planning, reviewer-risk checks, paper writing, code structure, ablations, figures, go/no-go decisions, or any follow-up task that must obey the 15-week decision-window execution basis.
---

# ICDR1 Skill

## Core Directive

Use this skill to keep ICDR1 work anchored to the current ICLR 2027 sprint thesis: RGRC is worth pursuing only if the frequency-separation loss can make the residual-correction story empirically credible quickly. The first decision gate is whether RDR can flip within the Phase 0 window.

Before making research, writing, experiment, or implementation decisions, read `references/icdr1-execution-basis.md` when the task depends on details beyond the guardrails below.

## Guardrails

- Keep the first version focused on RGRC: Role-Gated Residual Correction Network.
- Preserve the additive decomposition: final prediction equals non-attentive main path plus residual attention correction.
- Keep the three roles distinct: low-frequency global/main path, mid-frequency local routing path, and high-frequency residual attention path.
- Use fixed-budget chunk routing without global pairwise chunk retrieval as the efficiency claim.
- Treat bi-directional frequency separation loss as part of the training objective, not just an analysis plot.
- Treat RDR as the decisive Phase 0 gate. Do not expand the full benchmark suite, write the paper, or prioritize Stage 3 efficiency before the RDR/frequency-loss diagnosis is complete.
- During Phase 0, print and inspect `L_pred`, `L_main`, `L_res`, `E_low(attn)`, and `E_high(main)` every epoch/run. If `E_low(attn)` is near zero from the first epoch, suspect a scale/lambda failure rather than successful role separation.
- Force a decision by the end of week 3: continue the original RGRC story only if RDR flips and the frequency evidence is at least defensible.
- If RDR does not flip, immediately switch to the conservative diagnostic-framework narrative instead of spending more weeks tuning the same claim.
- Do not add FSQ tokenization, cross-modal modeling, macro text, five-elements concepts, or unrelated theory unless the user explicitly overrides this project constraint.
- Do not cherry-pick weak baselines or post-hoc seeds. Use fixed 3-seed protocols for committed experiments.

## Execution Workflow

1. Align the task to one of the project surfaces: method design, implementation, experiments, figures, paper writing, reviewer response, or go/no-go judgment.
2. Determine which sprint phase applies:
   - Phase 0, weeks 1-3: repair and diagnose frequency loss; decide whether RDR flips.
   - Phase 1A, weeks 4-15: if RDR flips, execute the compressed original ICLR story.
   - Phase 1B, week 4 onward: if RDR does not flip, switch to the diagnostic/conservative story.
3. In Phase 0, prioritize only experiments that answer whether frequency separation is active and whether Full RGRC degrades more slowly than Attention as Main Path.
4. In Phase 1A, expand to ETTm2, ETTh2, Weather, Electricity; use horizons 96/192/336/720, 3 seeds, and the first 7 ablations before spending effort on paper polish.
5. In Phase 1B, recast contributions around structural role separation, RCR behavior under regime shift, and fixed-budget routing efficiency. Stop claiming universal benchmark dominance.
6. When writing or revising the paper, match the claim to the evidence:
   - Strong path: residual Attention improves long-horizon stability, role separation, and efficiency.
   - Conservative path: RGRC is a diagnostic framework that reveals when constraining Attention as a residual corrector helps.

## Reference

The full execution basis lives in `references/icdr1-execution-basis.md`. Use it as the source of truth for the 15-week sprint plan, Phase 0 decision gate, Phase 1A/1B branch logic, experiment protocol, ablation priorities, figure plan, and reviewer-risk controls.
