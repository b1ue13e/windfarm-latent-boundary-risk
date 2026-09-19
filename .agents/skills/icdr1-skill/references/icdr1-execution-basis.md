# ICDR1 / RGRC ICLR 2027 Sprint Basis

## 0. Current Judgment

This project is worth pushing for ICLR, but only under a hard decision rule:

**Use the first 3 weeks to test whether the frequency loss can make RDR flip. If it cannot, stop defending the original strong story and switch narratives immediately.**

The working deadline assumption is an ICLR 2027 submission window around early October 2026. As of 2026-06-23, treat this as about 15 weeks of usable time. Re-check the official ICLR 2027 dates when they are posted.

The core risk is not paper writing speed. The core risk is that the current RDR result makes the paper refute itself: if the residual-correction model degrades faster than Attention-as-main-path, reviewers can say the main claim is contradicted by the ablation.

## 1. Non-Negotiable Thesis

The original RGRC thesis remains:

**In long-horizon time-series forecasting, Attention should not be the main trend path. It should be structurally restricted to a high-frequency residual correction path.**

The model must preserve:

- Additive prediction: `y_hat = y_main + delta_y_attn`.
- Main path: low-frequency trend and stable structure.
- Local routing path: mid-frequency chunk/block structure.
- Residual Attention path: high-frequency residual correction.
- Frequency separation loss as a training objective, not a post-hoc visualization.
- Fixed-budget chunk routing as the efficiency mechanism.

Do not add unrelated theory, FSQ tokenization, macro text, cross-modal inputs, or extra conceptual layers during the first submission attempt.

## 2. Phase 0: Decision Window, Weeks 1-3

### Goal

Do only one thing:

**Make the frequency loss actually affect training, then check whether RDR flips.**

No full benchmark expansion, no paper drafting, and no Stage 3 efficiency push until this gate is answered.

### Required Training Diagnostics

Every committed run must print or log, at least per epoch:

```text
L_pred
L_main
L_res
E_low(attn)
E_high(main)
RDR by horizon
RCR by window type when available
```

Interpretation:

- If `E_low(attn)` is already near 0 from the first epoch, the Attention output may already be high-frequency or the loss scale may be ineffective. Diagnose lambda/scale before claiming success.
- If `L_main`, `L_res`, `E_low(attn)`, and `E_high(main)` are numerically dwarfed by `L_pred`, tune `lambda1..lambda4` or normalize the frequency losses.
- If frequency terms move in the desired direction but RDR still does not flip, the strong stability claim is weak. Try a different stress surface before expanding the benchmark.

### Phase 0 Dataset Escalation

Start with the current Stage 1 surfaces. If RDR remains unfavorable after loss-scale repair, test datasets where the role-separation hypothesis has a better chance:

- Exchange Rate: strong trend drift.
- ILI: short sequence and strong regime shift.
- Synthetic level shift: manually injected level shifts with known timing.

Do not treat a hand-picked synthetic win as the main result. Use it to diagnose mechanism and decide the story.

### Week 3 Decision Table

| Result | Action |
| --- | --- |
| RDR flips and frequency-separation plots are strong | Continue with the original strong RGRC story. |
| RDR flips but frequency plots are weak | Reduce the frequency-loss contribution in the narrative; emphasize architecture and residual-role constraint. |
| RDR still does not flip | Switch to the conservative diagnostic-framework story immediately. |

The decision at the end of week 3 is mandatory. Do not spend week 8 tuning the same failed RDR gate.

## 3. Phase 1A: If RDR Flips, Weeks 4-15

This is the ideal path. Move fast and keep the paper claim sharp.

### Weeks 4-5: Main Experiment Expansion

Run:

- Datasets: ETTm2, ETTh2, Weather, Electricity.
- Horizons: 96, 192, 336, 720.
- Seeds: 3 fixed seeds.
- Main variants: the first 7 ablations.

Priority ablations:

1. Full RGRC.
2. No Attention.
3. Attention as Main Path.
4. W/O Frequency Loss.
5. W/O Periodic Prior.
6. Dense Chunk Routing.
7. Random Routing.

Keep parameter budgets as close as possible. Do not post-hoc add seeds only for favorable runs.

### Week 6: Efficiency Experiment

Measure only what is necessary:

- VRAM.
- Latency.
- Throughput if already easy.
- Sequence lengths: 1K, 2K, 4K, 8K, 16K.

Do not require 32K for the main submission if it burns time. The claim is real hardware scaling, not a theoretical victory lap.

### Weeks 7-8: Core Figures

Produce reproducible scripts for:

1. Frequency separation and branch reconstruction.
2. RDR curves.
3. Efficiency frontier.

By the end of week 7, figure scripts should be one-command reproducible. If the plot pipeline is manual, the project is carrying hidden risk.

### Weeks 9-10: Paper Draft

Write only after the evidence gate is passed.

Prioritize:

- Introduction: why Attention-as-main-path is overburdened.
- Method: additive decomposition, role split, fixed-budget routing, frequency loss.
- Experimental setup: enough detail to block cherry-picking concerns.

Reuse the previous white-paper structure, but do not let it bloat the claim.

### Weeks 11-15: Polish and Submission

Use this time for:

- Robustness checks.
- Reviewer-risk responses.
- Final tables and appendix.
- Rebuttal preparation.
- Submission packaging.

## 4. Phase 1B: If RDR Does Not Flip

Do not keep defending the original strong claim. Move the contribution center to what can still be true.

### Plausible Contributions

1. Structural role-separation framework: even without universal MSE wins, it is valuable if Attention empirically behaves as a high-frequency component.
2. RCR behavior under regime-shift windows: if the gate rises under shocks and stays modest in stable windows, this is meaningful mechanism evidence.
3. Fixed-budget chunk routing: if real VRAM/latency improves, this remains a clean systems contribution.

### Conservative Story

Use this framing:

> We do not claim RGRC wins on every benchmark. We provide a diagnostic framework that reveals when constraining Attention as a residual corrector is beneficial, and we use frequency analysis to make the role separation empirically inspectable.

This story is less flashy but harder to kill. It can survive a competitive, non-dominant main table if the analysis is honest and the diagnostic evidence is strong.

### Claim Boundaries

Allowed:

- RGRC can be beneficial under drift/regime-shift conditions.
- Attention-as-residual exposes interpretable high-frequency behavior.
- RCR and frequency-band diagnostics help explain when residual Attention helps.
- Fixed-budget routing can reduce hardware cost relative to dense routing.

Not allowed:

- RGRC universally beats all LTSF baselines.
- Frequency loss is the main contribution if the plots are weak.
- RDR proves stability if the curve does not support it.

## 5. Evidence Chains

### Chain 1: Performance and Degradation

Needed for the strong story:

```text
Full RGRC RDR < Attention-as-main-path RDR
```

Especially on long horizons and regime-shift windows.

If only MSE is competitive but RDR is not better, do not use the strong long-horizon-stability claim.

### Chain 2: Role Separation

Needed for both stories:

```text
y_main -> low-frequency energy concentration
delta_y_attn -> high-frequency residual concentration
```

Support with:

- PSD or cumulative spectral energy curves.
- Band energy ratios.
- Branch reconstruction plots.
- RCR behavior across stable, high-frequency, and regime-shift windows.

### Chain 3: Efficiency

Needed for the efficiency claim:

```text
Fixed-budget RGRC < Dense Chunk Routing / Dense Attention
```

Measure real VRAM and latency. Complexity formulas are not enough.

## 6. Risk Controls

### Do Not

- Do not start paper writing before the Phase 0 gate is answered.
- Do not run Stage 3 efficiency before Stage 1 evidence is credible.
- Do not choose weak baselines just to make the main table prettier.
- Do not keep tuning RDR past the week-3 decision point.
- Do not make frequency loss a headline contribution if its plots are weak.

### Must Do

- Force the week-3 decision.
- Use 3 fixed seeds for committed experiments.
- Keep figure scripts reproducible by week 7.
- Log loss components so loss-scale failures are visible.
- Preserve all negative results needed to choose the honest story.

## 7. Minimal Experiment Contract

The minimum viable Phase 0 experiment set is:

- Datasets: ETTm2 and Weather first.
- Variants: Full RGRC, Attention as Main Path, W/O Frequency Loss, No Attention.
- Horizons: enough to compute RDR, ideally 96, 192, 336, 720.
- Seeds: use fixed seeds; smoke tests may use one seed, but decision runs need 3.
- Logs: loss components, frequency energies, MSE/MAE, RDR, and RCR if available.

The minimum Phase 1A main table is:

- Datasets: ETTm2, ETTh2, Weather, Electricity.
- Horizons: 96, 192, 336, 720.
- Seeds: 3.
- Baselines: DLinear, NLinear, PatchTST, iTransformer, TimesNet when feasible.
- Ablations: first 7 variants.

## 8. Paper Strategy

### Strong Path Title/Claim

Use if RDR flips and figures support the mechanism:

**Roles Are All Time Series Need: Rethinking Attention as Residual Correction**

Claim:

**Constraining Attention as a residual corrector improves long-horizon stability, preserves high-frequency adaptability, and provides interpretable temporal role separation.**

### Conservative Path Title/Claim

Use if RDR does not flip:

**Diagnosing Residual Attention in Long-Horizon Time-Series Forecasting**

Claim:

**RGRC is a diagnostic architecture for studying when residual Attention helps, with frequency and RCR analyses exposing its operating regime.**

## 9. Final Execution Principle

The dangerous state is not failure. The dangerous state is ambiguity.

By week 3, decide whether RGRC is an ICLR strong-claim paper or a conservative diagnostic-framework paper. Both can be useful. Only the undecided middle path is a time sink.
