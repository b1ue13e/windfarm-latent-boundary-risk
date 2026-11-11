# Derivation Package: Conditional Minimum-Sufficient Decision Rule

**Status:** COHERENT AFTER REFRAMING / EXTRA PRE-REGISTRATION REQUIRED

## Target

Formalize “minimum sufficient model” as a conditional risk-constrained selection rule under the same arrival-time information set, frozen point forecast, and frozen shortfall target.

## Objects

- `I_t^(d)`: arrived deployment information at issue time `t`.
- `M(I)`: policies measurable with respect to `I`.
- `b_I`: strongest direct conditional baseline under the same `I`.
- `yhat_fixed`: canonical point forecast shared by all reserve policies.
- `s_t = max(yhat_fixed,t - y_t, 0)`: common residual target.
- `C_P(m)`: fixed-target PSREI on population `P`.
- `V_P(m)`: violation rate on `P`.

## Selection rule

For pre-registered `alpha`, `epsilon_C`, `epsilon_V`, `v_max`, and a declared complexity preorder:

```text
m*(I, rho, epsilon_C, epsilon_V) = argmin Complexity(m)
```

subject to:

```text
U_(1-alpha)[C_P(m) - C_P(b_I)] <= epsilon_C,
U_(1-alpha)[V_P(m) - V_P(b_I)] <= epsilon_V,
U_(1-alpha)[V_P(m)] <= v_max.
```

This is an operational selection criterion, not a universal optimality theorem. The upper bounds must be computed with the registered unit of replication and joint seed/block uncertainty. If no policy is feasible, the correct result is `NO FEASIBLE POLICY`.

## Why the reframing is necessary

The current repository freezes the information set, point forecast, residual target, PSREI, and direct-baseline role. It does not yet freeze the tolerances, confidence level, admissible policy set, or complexity preorder. Therefore the criterion is coherent as a falsifiable protocol but is not yet empirically certified. E04 registers the missing decision before any new test result is used.

## Scope ceiling

A successful E04 result would support only a conditional statement for the evaluated information regime, population, risk ratio, resource model, and uncertainty procedure. It would not establish universal model ranking, graph/MoE necessity, market value, or an online transition selector.
