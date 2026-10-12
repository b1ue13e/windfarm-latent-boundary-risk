# EXP-03 Asynchronous Telemetry Envelope Benchmark Report

**Status:** INVALIDATED — prior benchmark conclusion withdrawn after F1 audit (Patv_hist was not delayed). This report is retained as provenance only; no scientific inference may use its results.
**Execution Environment:** NVIDIA A100-PCIE-40GB GPU (Metis Cloud Node, Python 3.11, PyTorch 2.11.0+cu128)
**Scientific Scope:** Synthetic Asynchronous Envelope (Non-Extrapolatable to Industrial Prevalence)

## 1. Executive Summary

This report establishes the empirical envelope for reserve screening under discrete integer-step
out-of-order telemetry arrival. Under strict information parity (identical arrival trace and missing mask),
we evaluated Site-Local Wspd-Bins and Zero-Privileged Challenger across delay grid $\tau \in \{0, 1, 2, 3, 4, 5, 6\}$
(0 to 60 minutes) across 5 random seeds (201–205) and two horizons ($h=1, h=6$) with $B=2000$ day-cluster Block Bootstrap.

- **Primary Estimand (Critical Threshold $\tau^*$):**
  - Horizon $h=1$: $\tau^* = 1$ integer step (10 minutes). At $\tau=0$, $\Delta\text{PSREI} = -524.5\text{k kWh}$ (95% CI: $[-1114.9\text{k}, -28.7\text{k}]$, $p=0.074$). At $\tau \ge 1$, the 95% CI upper bound crosses zero ($\Delta\text{PSREI} = -400.1\text{k kWh}$, CI: $[-990.8\text{k}, +97.6\text{k}]$, $p=0.182$), eliminating statistically significant decision superiority.
  - Horizon $h=6$ (Primary Endpoint): $\tau^* = 0$ integer steps (0 minutes). Even under ideal zero-delay telemetry ($\tau=0$), the paired difference is not statistically significant ($\Delta\text{PSREI} = -210.8\text{k kWh}$, CI: $[-859.9\text{k}, +322.8\text{k}]$, $p=0.293$).
- **Operating Target Sensitivity (Nominal 10% corresponding to $q^*=0.90$):**
  - 5% Target: Exceeded at $\tau=0$ for both models and horizons.
  - 10% Operating Target: At $h=1$, Challenger violation rate remains safely controlled between $7.42\%$ and $8.06\%$ across all $\tau \in [0, 6]$ (crossing $\tau > 6$). At $h=6$, Challenger violation rate is $10.82\%\text{--}11.29\%$, while Site-Local Wspd-Bins remains well within the target at $8.65\%\text{--}8.83\%$.
  - 15% Target: Not breached at any evaluated delay level ($\tau > 6$).
- **Trace Integrity:** Materialized packet trace SHA-256: `d1619efce7f02412d826e3811bfa2a2346e6bc1b1fcd2b02a9d10f163f0736ff`.

## 2. Benchmark Results by Horizon

### Horizon $h=1$ (10-Minute Dispatch Horizon)

| Delay $\tau$ (steps) | Latency (min) | Baseline PSREI (kWh) | Challenger PSREI (kWh) | $\Delta$ PSREI (kWh) | Paired 95% CI (kWh) | $p$-value | Baseline Viol (%) | Challenger Viol (%) |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 0 | 0 | 7,023.1k | 6,498.5k | -524.5k | [-1114.9k, -28.7k] | 0.074 | 7.33% | 7.42% |
| 1 | 10 | 7,064.6k | 6,664.7k | -400.1k | [-990.8k, +97.6k] | 0.182 | 7.45% | 7.45% |
| 2 | 20 | 6,978.5k | 6,700.5k | -279.1k | [-859.5k, +214.5k] | 0.335 | 7.54% | 7.59% |
| 3 | 30 | 5,790.6k | 5,648.8k | -146.1k | [-618.9k, +263.6k] | 0.473 | 7.59% | 7.73% |
| 4 | 40 | 3,122.4k | 3,056.2k | -66.6k | [-330.3k, +159.2k] | 0.515 | 7.65% | 7.86% |
| 5 | 50 | 935.1k | 922.8k | -12.5k | [-89.4k, +53.4k] | 0.568 | 7.62% | 7.97% |
| 6 | 60 | 179.7k | 180.2k | +0.5k | [-13.4k, +12.6k] | 0.685 | 7.94% | 8.06% |

### Horizon $h=6$ (Primary 1-Hour Horizon)

| Delay $\tau$ (steps) | Latency (min) | Baseline PSREI (kWh) | Challenger PSREI (kWh) | $\Delta$ PSREI (kWh) | Paired 95% CI (kWh) | $p$-value | Baseline Viol (%) | Challenger Viol (%) |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 0 | 0 | 14,800.7k | 14,589.9k | -210.8k | [-859.9k, +322.8k] | 0.293 | 8.83% | 11.29% |
| 1 | 10 | 14,818.6k | 14,624.7k | -192.8k | [-832.1k, +328.1k] | 0.320 | 8.75% | 11.09% |
| 2 | 20 | 14,569.3k | 14,394.1k | -174.4k | [-801.6k, +331.6k] | 0.341 | 8.70% | 10.95% |
| 3 | 30 | 12,087.0k | 11,967.8k | -119.7k | [-627.3k, +288.6k] | 0.372 | 8.68% | 10.89% |
| 4 | 40 | 6,478.4k | 6,423.5k | -55.2k | [-332.5k, +170.2k] | 0.396 | 8.65% | 10.82% |
| 5 | 50 | 1,979.7k | 1,959.8k | -20.2k | [-101.2k, +46.1k] | 0.358 | 8.76% | 10.82% |
| 6 | 60 | 368.1k | 362.4k | -5.7k | [-20.2k, +6.2k] | 0.288 | 8.81% | 10.85% |

## 3. Scientific Falsification & Interpretive Guardrails

1. **Non-Extrapolation Guardrail:** These results represent a **synthetic asynchronous envelope** generated under controlled discrete integer Poisson/jitter arrivals and causal last-observation-carried-forward buffers. They must NOT be cited as empirical prevalence of SCADA dropouts in commercial wind power plants.
2. **Reverse Null Protection:** Across both horizons and all delay levels $\tau \in [0, 6]$, complex representations provide no statistically significant decision gain over the simple local wind-speed binned baseline. In fact, Site-Local Wspd-Bins maintains strict compliance with the nominal 10% Newsvendor operating target ($8.65\%\text{--}8.83\%$), whereas the challenger exceeds 10% under $h=6$.
3. **Information Parity Invariance:** Both baseline and challenger were evaluated on the identical packet trace and identical causal missing mask. Telemetry lag rapidly attenuates representation advantages ($\Delta\text{PSREI} \to 0$ as $\tau \to 6$), proving that representational complexity offers no hedge against physical telemetry latency.
