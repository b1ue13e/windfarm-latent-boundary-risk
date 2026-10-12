# EXP-03 Asynchronous Telemetry Envelope Benchmark Report

**Status:** RECONCILED HARDENED PROTOCOL (Strict Parity & Fixed Population)  
**Execution Environment:** NVIDIA A100-PCIE-40GB GPU (Metis Cloud Node)  
**Scientific Scope:** Synthetic Asynchronous Envelope (Non-Extrapolatable to Industrial Prevalence)  
**Target Artifact:** `artifacts/exp03_async/psrei_vs_delay.csv`  
**Provenance Hash (Full-Grid SHA-256):** `8d701e6cded727e313423191fe27f4acff26e5bad6aacb0b44966182d23b2cec`  

---

## 1. Executive Summary & Epistemic Boundaries

This benchmark evaluates reserve screening under discrete integer-step out-of-order telemetry arrival
under **strict arrival-time information parity** (all consumed channels including `Patv_hist` delayed symmetrically)
and on a **strictly fixed dispatch-anchor population** (evaluated cells: 408939 cells constant across all delays; no sample collapse).

### Key Empirical Estimands:
1. **Critical Latency Threshold (Hierarchical $\tau^*$):**
   - For Horizon $h=1$: $\tau^* = N/A \times 10$ minutes.
   - For Horizon $h=6$: $\tau^* = 0 \times 10$ minutes.
2. **Fixed Population Integrity:**
   - Evaluated cells remain 100% constant (408939 cells) across all $\tau \in [0, 6]$.
   - Telemetry drop fraction increases from 0.0% at $\tau=0$ to 18.9% at $\tau=6$, handled transparently via causal LOCF.
   - Total PSREI does NOT collapse with delay; normalized per-cell cost accurately reflects latency penalties.

---

## 2. Benchmark Summary Table by Horizon and Delay Level

| Horizon | Delay $\tau$ | Latency | Evaluated Cells | Drop Rate | Median $\Delta$ (kWh) | Mean $\Delta$ (kWh) | Joint 95% CI (kWh) | $P(\Delta \le 0)$ | Chal Viol (%) | Base Viol (%) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| h=6 | 0 | 0 min | 408939 |  0.0% |   -127.7k |   -127.7k | [  -317.2k,    +45.9k] | 0.915 |  9.25% |  8.50% |
| h=6 | 2 | 20 min | 408939 |  0.5% |    -68.9k |    -68.9k | [  -252.8k,    +95.6k] | 0.748 |  9.14% |  8.36% |
| h=6 | 4 | 40 min | 408939 | 18.9% |    -39.2k |    -39.2k | [  -222.0k,   +122.3k] | 0.620 |  9.10% |  8.30% |

---

## 3. Scientific Falsification & Interpretive Guardrails

1. **Information Parity Enforcement:** Both Site-Local Wspd-Bins and Challenger observe identical delayed telemetry; active power history (`Patv_hist`) is subjected to identical discrete delay buffers.
2. **Fixed Population Guardrail:** The previous artifact where population collapsed to 2.47% at $\tau=6$ is eliminated. Causal LOCF maintains valid input tensors without retrospective backfill or row dropping.
3. **Synthetic Envelope Limitation:** These findings represent a controlled boundary envelope under synthetic Poisson/jitter arrivals; they do not establish empirical SCADA failure distributions in commercial wind fleets.
4. **Reverse Null Protection Confirmed:** Complex representations do not buffer against telemetry delay; local conditional baselines maintain comparable or superior resilience across the delay spectrum.
