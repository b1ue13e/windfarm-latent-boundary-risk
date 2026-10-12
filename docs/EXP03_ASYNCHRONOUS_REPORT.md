# EXP-03 Asynchronous Telemetry Envelope Benchmark Report

**Status:** RECONCILED HARDENED PROTOCOL (Strict Parity & Fixed Population)  
**Execution Environment:** NVIDIA A100-PCIE-40GB GPU (Metis Cloud Node)  
**Scientific Scope:** Synthetic Asynchronous Envelope (Non-Extrapolatable to Industrial Prevalence)  
**Target Artifact:** `artifacts/exp03_async/psrei_vs_delay.csv`  
**Provenance Hash (Full-Grid SHA-256):** `18079b46d01a399d47df681ec0fa48ab4a55bf0860c8bc99df2c15480bb13d49`  

---

## 1. Executive Summary & Epistemic Boundaries

This benchmark evaluates reserve screening under discrete integer-step out-of-order telemetry arrival
under **strict arrival-time information parity** (all consumed channels including `Patv_hist` delayed symmetrically)
and on a **strictly fixed dispatch-anchor population** (evaluated cells: 408937 cells constant across all delays; no sample collapse).

### Key Empirical Estimands:
1. **Critical Latency Threshold (Hierarchical $\tau^*$):**
   - For Horizon $h=1$: $\tau^* = 1 \times 10$ minutes.
   - For Horizon $h=6$: $\tau^* = 0 \times 10$ minutes.
2. **Fixed Population Integrity:**
   - Evaluated cells remain 100% constant (408937 cells) across all $\tau \in [0, 6]$.
   - Telemetry drop fraction increases from 0.0% at $\tau=0$ to 60.3% at $\tau=6$, handled transparently via causal LOCF.
   - Total PSREI does NOT collapse with delay; normalized per-cell cost accurately reflects latency penalties.

---

## 2. Benchmark Summary Table by Horizon and Delay Level

| Horizon | Delay $\tau$ | Latency | Evaluated Cells | Drop Rate | Median $\Delta$ (kWh) | Mean $\Delta$ (kWh) | Joint 95% CI (kWh) | $P(\Delta \le 0)$ | Chal Viol (%) | Base Viol (%) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| h=1 | 0 | 0 min | 408937 |  0.0% |   -590.9k |   -528.0k | [ -1142.5k,    -34.9k] | 0.985 |  7.34% |  7.33% |
| h=1 | 1 | 10 min | 408937 |  0.0% |   -342.4k |   -361.0k | [  -977.2k,   +128.5k] | 0.897 |  7.99% |  7.44% |
| h=1 | 2 | 20 min | 408937 |  0.5% |   -222.5k |   -274.4k | [  -878.6k,   +204.6k] | 0.832 |  8.39% |  7.55% |
| h=1 | 3 | 30 min | 408937 |  5.1% |   -106.7k |   -195.4k | [  -791.6k,   +265.8k] | 0.739 |  8.69% |  7.62% |
| h=1 | 4 | 40 min | 408937 | 18.9% |    +15.3k |    -99.7k | [  -701.5k,   +366.4k] | 0.610 |  8.95% |  7.69% |
| h=1 | 5 | 50 min | 408937 | 39.7% |   +133.5k |     -9.3k | [  -609.7k,   +451.7k] | 0.481 |  9.25% |  7.78% |
| h=1 | 6 | 60 min | 408937 | 60.3% |   +299.4k |   +176.4k | [  -416.2k,   +635.7k] | 0.239 |  9.64% |  7.87% |
| h=6 | 0 | 0 min | 408939 |  0.0% |   -158.0k |   -171.6k | [  -804.3k,   +327.7k] | 0.706 | 11.05% |  8.83% |
| h=6 | 1 | 10 min | 408939 |  0.0% |   -156.0k |   -137.1k | [  -786.0k,   +352.5k] | 0.657 | 10.91% |  8.75% |
| h=6 | 2 | 20 min | 408939 |  0.5% |   -137.4k |   -100.3k | [  -740.2k,   +379.3k] | 0.609 | 10.89% |  8.71% |
| h=6 | 3 | 30 min | 408939 |  5.1% |   -141.4k |    -88.9k | [  -733.2k,   +393.5k] | 0.596 | 10.85% |  8.68% |
| h=6 | 4 | 40 min | 408939 | 18.9% |   -111.2k |    -41.7k | [  -669.3k,   +428.1k] | 0.531 | 10.82% |  8.66% |
| h=6 | 5 | 50 min | 408939 | 39.7% |   -107.7k |    -32.0k | [  -659.1k,   +448.9k] | 0.515 | 10.77% |  8.67% |
| h=6 | 6 | 60 min | 408939 | 60.3% |    -24.6k |    +21.6k | [  -584.2k,   +500.5k] | 0.434 | 10.78% |  8.73% |

---

## 3. Scientific Falsification & Interpretive Guardrails

1. **Information Parity Enforcement:** Both Site-Local Wspd-Bins and Challenger observe identical delayed telemetry; active power history (`Patv_hist`) is subjected to identical discrete delay buffers.
2. **Fixed Population Guardrail:** The previous artifact where population collapsed to 2.47% at $\tau=6$ is eliminated. Causal LOCF maintains valid input tensors without retrospective backfill or row dropping.
3. **Synthetic Envelope Limitation:** These findings represent a controlled boundary envelope under synthetic Poisson/jitter arrivals; they do not establish empirical SCADA failure distributions in commercial wind fleets.
4. **Reverse Null Protection Confirmed:** Complex representations do not buffer against telemetry delay; local conditional baselines maintain comparable or superior resilience across the delay spectrum.
