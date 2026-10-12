# EXP-03 Asynchronous Telemetry Envelope Benchmark Report

**Status:** CONCLUDED ON METIS CLUSTER
**Execution Environment:** NVIDIA A100-PCIE-40GB GPU (Metis Cloud Node)
**Scientific Scope:** Synthetic Asynchronous Envelope (Non-Extrapolatable to Industrial Prevalence)

## 1. Executive Summary

This report establishes the empirical envelope for reserve screening under discrete integer-step
out-of-order telemetry arrival. Under strict information parity (identical arrival trace and missing mask),
we evaluated Site-Local Wspd-Bins and Zero-Privileged Challenger across delay grid tau in [0, 1, 2, 3, 4, 5, 6]
(0 to 60 minutes).

- **Primary Estimand (Critical Threshold tau*):** tau* = 0 integer steps (0 minutes).
- **Operating Target Sensitivity:**
  - 5% Violation Target: Crosses at tau = 0
  - 10% Violation Operating Target (q*=0.90): Crosses at tau = 0
  - 15% Violation Target: Crosses at tau = >6
- **Trace Integrity:** Materialized packet trace SHA-256: `ee4fca8cb3bbb0980c243dd767cdadb4ca6630bad6442f627684aaa72380a5eb`.

## 2. Summary Table by Delay Level

| Delay tau (steps) | Latency (min) | Baseline PSREI (kWh) | Challenger PSREI (kWh) | Delta PSREI (kWh) | 95% CI (kWh) | Challenger Viol (%) | Baseline Viol (%) |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 0 | 0 | +42.2k | - | +42.2k | [-532.7k, +531.8k] | 12.26% | 8.50% |
| 2 | 20 | +36.2k | - | +36.2k | [-639.6k, +567.4k] | 10.84% | 8.38% |
| 4 | 40 | +119.0k | - | +119.0k | [-55.7k, +264.6k] | 7.98% | 8.25% |

## 3. Scientific Falsification & Interpretive Guardrails

1. **Non-Extrapolation Guardrail:** These results represent a **synthetic asynchronous envelope** generated under controlled discrete Poisson/jitter delays. They must NOT be cited as empirical prevalence of SCADA dropouts in commercial wind power plants.
2. **Reverse Null Protection:** Even under progressive telemetry delay and causal packet drops, the local conditional quantile baseline remains robust, confirming that spatial/representation complexity provides no unearned buffer against physical telemetry lag.
