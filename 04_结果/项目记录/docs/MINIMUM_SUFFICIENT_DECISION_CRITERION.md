# Conditional Minimum-Sufficient Decision Criterion

**Status:** FORMALIZED / NOT YET EMPIRICALLY CERTIFIED  
**Date:** 2026-10-17  
**Experiment:** E04, `experiments/E04/`

## 1. Scope

This document formalizes the paper's **conditional deployment principle**. It is a model-selection criterion under a declared arrival-time information set, not a theorem that one architecture is universally optimal.

The criterion is only meaningful after fixing:

- the deployable information set `I` at issue time;
- the canonical point forecast and residual target;
- the direct baseline using exactly the same `I`;
- the risk tolerances, confidence level, and complexity ordering before test results are inspected.

The current project has frozen `I`, the canonical point forecast, the residual target, and PSREI definition. E04 has been registered because `alpha`, `epsilon_C`, `epsilon_V`, the absolute violation cap, and the final complexity preorder have not yet been frozen for a claim-ready selector.

## 2. Information and decision objects

Let `I_t^(d)` be the information genuinely arrived by dispatch time `t` under degradation condition `d`, as defined in `docs/INFORMATION_SET_CONTRACT.md`.

Let `M(I_t^(d))` be the admissible policy class whose inputs are measurable with respect to `I_t^(d)`. A policy `m` maps the arrived information to an upward reserve decision:

```text
r_m,t = m(I_t^(d)).
```

All policies must use the canonical frozen point forecast `yhat_fixed` and the common shortfall target:

```text
s_t = max(yhat_fixed,t - y_t, 0).
```

For a population `P` and penalty ratio `rho`, define the fixed-target PSREI:

```text
C_P(m) = sum_{t in P} [r_m,t + rho * max(s_t - r_m,t, 0)] * Delta t.
```

Define the empirical violation rate:

```text
V_P(m) = mean_{t in P} 1[s_t > r_m,t].
```

Let `b_I` denote the strongest pre-registered direct conditional baseline under the same information set `I`. In the current mainline this is the site-local wind-speed-conditioned quantile policy when wind speed is available; the baseline must be changed only by a new registered experiment.

## 3. Risk-constrained selection rule

For a confidence level `1 - alpha`, cost tolerance `epsilon_C`, violation tolerance `epsilon_V`, and absolute violation cap `v_max`, define the one-sided upper confidence bounds:

```text
U_(1-alpha)[ C_P(m) - C_P(b_I) ]
U_(1-alpha)[ V_P(m) - V_P(b_I) ].
```

The conditional minimum-sufficient policy is selected by:

```text
m*(I, rho, epsilon_C, epsilon_V)
  = arg min_{m in M(I)} Complexity(m)
```

subject to:

```text
U_(1-alpha)[ C_P(m) - C_P(b_I) ] <= epsilon_C,
U_(1-alpha)[ V_P(m) - V_P(b_I) ] <= epsilon_V,
U_(1-alpha)[ V_P(m) ] <= v_max.
```

The selector is **lexicographic** when several policies satisfy the constraints:

1. minimum pre-registered complexity class;
2. minimum parameter/latency cost within that class;
3. lower point estimate of `C_P(m) - C_P(b_I)`;
4. deterministic tie-break by policy identifier.

The selector must report `NO FEASIBLE POLICY` if no candidate satisfies all constraints. It must not relax tolerances after seeing test outcomes.

## 4. Complexity is a declared preorder, not an architecture myth

`Complexity(m)` is not automatically parameter count. Before execution, E04 must declare a lexicographic preorder such as:

```text
physical rule < calibrated local quantile < direct tabular quantile
< residual MLP < graph representation < routed MoE
```

The preorder is valid only for the stated deployment resource model. A graph model with fewer parameters is not automatically simpler if it requires unavailable topology, higher latency, or a stronger training protocol. Conversely, a representation model is not retained merely because it improves NMI/ARI.

The current evidence suggests the following **candidate map**, not a certified law:

| Information condition | Candidate minimum-sufficient policy | Current evidence status |
|---|---|---|
| Fresh wind and pitch/state | deterministic physical rule | bounded within evaluated WTB boundary band |
| Observable delay with state available | state-conditional recalibration | bounded synthetic stress evidence |
| Pitch withheld, steady/full population | local wind-speed quantile baseline | current strong-baseline candidate is pending audit |
| Pitch withheld, consequence representation | consequence representation | recoverability bounded; decision sufficiency not established |
| External zero-shot transfer | local site baseline unless matched evidence passes | EXP-01 full claim pending; deterministic branch bounded |

## 5. What the criterion would establish

If E04 passes with pre-registered tolerances, it supports only:

> Under information set `I`, population `P`, risk ratio `rho`, resource model, and uncertainty procedure `U`, policy `m*` is the lowest-complexity evaluated policy whose upper risk bounds are within the declared tolerances of the strong direct baseline.

It does **not** establish:

- universal optimality across wind farms, horizons, or telemetry distributions;
- causal necessity of graph structure or MoE routing;
- that representation metrics imply decision value;
- market profit, AC-OPF value, or field latency prevalence;
- an ex-ante transition selector from a post-hoc transition slice.

## 6. Current blockers and falsifiable outcomes

E04 remains planned until the following are frozen:

- `alpha` and the one-sided uncertainty construction;
- `epsilon_C`, `epsilon_V`, and `v_max`;
- the candidate policy set and complexity preorder;
- the population-specific estimand and unit of replication;
- the external-site alignment and raw-window protocol.

Falsifiable outcomes are explicit:

- **No feasible policy:** the candidate class cannot meet the declared risk constraints;
- **Baseline selected:** the simple direct baseline is empirically minimum-sufficient under that condition;
- **Complex policy selected:** only if it passes the same-information risk bounds and is lower in the pre-registered complexity order than all feasible alternatives;
- **Unstable selection:** if the selected class changes across seeds or blocks beyond the pre-registered stability rule, the deployment map is inconclusive.

No current manuscript sentence should describe the criterion as empirically validated until E04 completes and receives an independent falsification review.
