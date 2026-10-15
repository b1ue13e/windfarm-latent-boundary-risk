> WITHDRAWAL NOTICE — 2026-10-15: Historical asynchronous results used potentially unarrived initialization and incomplete packet provenance. Their interpretation as causal arrival-time decision evidence is withdrawn. Corrected v2 full-grid replay is pending; old numbers are preserved below.

# EXP-03 Asynchronous Telemetry Envelope Benchmark Report

**Status:** RECONCILED HARDENED PROTOCOL (Strict Parity & Fixed Population)  
**Execution Environment:** NVIDIA A100-PCIE-40GB GPU (Metis Cloud Node)  
**Scientific Scope:** Synthetic Asynchronous Envelope (Non-Extrapolatable to Industrial Prevalence)  
**Target Artifact:** `artifacts/exp03_async/psrei_vs_delay.csv`  
**Internal Trace Digest (`input_trace_hash.txt`):** `18079b46d01a399d47df681ec0fa48ab4a55bf0860c8bc99df2c15480bb13d49`  

> **Provenance boundary (2026-10-13, F6 correction).** `18079b46…` is an *internal* Python `hashlib`
> accumulator digest, **not** a file SHA-256 and **not** a full-grid arrival-stream hash. It is computed
> during execution over `async_feat[:144, 0, :]` and `dropped_mask[:144, 0, :]` only — node 0, first 144
> steps (`scripts/run_exp03_async_benchmark.py:498,515-516,597`). It does not cover the evaluated grid
> (all turbines × 5 seeds × 7 delays × 2 horizons) and cannot be recomputed from any archived artifact.
> The materialized `arrival_trace.jsonl` covers nodes 0–1 × first 144 steps at $\tau=0$ and contains
> **zero delayed packets**; its own SHA-256 (`fcc119806e6bccad0f458a9cd6188c3150ece307ca0c63acd6b395d7904b3d9c`)
> differs from the digest above, and `missing_mask.json` is a 48-element all-`false` placeholder.
> Packet-level provenance for the evaluated grid remains **OUTSTANDING**.

---

## 1. Executive Summary & Epistemic Boundaries

This benchmark evaluates reserve screening under discrete integer-step out-of-order telemetry arrival
under **strict arrival-time information parity** (all consumed channels including `Patv_hist` delayed symmetrically)
and on a **strictly fixed dispatch-anchor population** (evaluated cells: 408937 cells constant across all delays; no sample collapse).

### Key Empirical Estimands:
1. **Critical Latency Threshold (Hierarchical $\tau^*$):**
   - For Horizon $h=1$: $\tau^* = 1 \times 10$ minutes.
   - For Horizon $h=6$: $\tau^* = 0 \times 10$ minutes.
2. **Fixed Population Integrity (LOCF-imputed, bounded):**
   - Evaluated cells remain constant (408,937 cells) across all $\tau \in [0, 6]$ by *imputing* stale values rather than dropping rows.
   - Telemetry drop fraction rises from 0.0% at $\tau=0$ to 60.3% at $\tau=6$, handled via causal LOCF.
   - **Boundary:** the LOCF stale fraction rises to **99.79%** at $\tau=6$; at $\tau=3$ it is already 95.75%. Late-delay points therefore measure degradation under near-total staleness, not a partially-refreshed stream. "Fixed population" means a fixed *evaluated* population, not fresh observations.
   - Total PSREI does NOT collapse with delay; normalized per-cell cost reflects latency penalties.

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
2. **Fixed Population Guardrail (bounded):** The previous artifact where population collapsed to 2.47% at $\tau=6$ is eliminated: causal LOCF keeps the *evaluated* population constant without retrospective backfill or row dropping. It does so by imputing stale values, so at $\tau=6$ the stale fraction reaches 99.79%. Fixed-population *evaluation* must not be reported as a fully-refreshed telemetry stream.
3. **Synthetic Envelope Limitation:** These findings represent a controlled boundary envelope under synthetic Poisson/jitter arrivals; they do not establish empirical SCADA failure distributions in commercial wind fleets.
4. **Reverse Null Protection Confirmed:** Complex representations do not buffer against telemetry delay; local conditional baselines maintain comparable or superior resilience across the delay spectrum.
5. **Provenance Limitation:** The archived packet trace covers only nodes 0–1 and the first 144 steps at $\tau=0$; the recorded trace digest is an internal accumulator over node 0 / first 144 steps, not a full-grid arrival-stream hash. Full-grid packet-level provenance remains OUTSTANDING.
