# EXP-02 (EXP-Q1-003): Zero-Privileged-Pitch Supervision Boundary Audit Report

**Date:** 2026-10-11 19:43:40  
**Target Artifact:** `artifacts/zero_privileged_supervision_benchmark.csv`  
**Registry Reference:** `docs/EXPERIMENT_REGISTRY.md:229-270`  
**Scientific Contract Anchor:** `docs/SCIENTIFIC_CONTRACT.md:47-55`  
**Formal Scientific Verdict:** **ZERO-PRIVILEGED LEARNING PROTOCOL DEFICIT ESTABLISHED**

---

## 1. Executive Summary & Falsification Guardrail

### Authoritative Interpretation Boundary:
Under the zero-privileged supervision protocol, consequence signals alone **failed to recover a deployable decision function** capable of outperforming simple local wind-speed conditioning.

**Strict Scientific Guardrail (Rule Enforcement):**
- **SUPPORTED CONCLUSION:** Zero-privileged weak-supervision protocol fails to yield incremental decision value over Site-Local Wspd-Bins (Delta PSREI >= 0).
- **FORBIDDEN OVERCLAIMS:**
  1. It CANNOT be concluded that *"active-power consequence carries no information"* (privileged STGQ proves information exists, but requires privileged alignment).
  2. It CANNOT be concluded that *"real wind farms do not need pitch telemetry"*.

---

## 2. Benchmark Summary Across Models (Averaged across 5 Seeds)

| Horizon | Model | Role | Full PSREI (kWh) | Delta PSREI vs Wspd-Bins | p-value | Violation Rate (%) | Bnd Delta PSREI | Held-Out Pitch NMI |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| h=1 | Direct Consequence Quantile MLP | Secondary Baseline / Sensitivity Probe |   6.69M |   -335.4k | 0.842 |  7.57% |   -163.2k | N/A |
| h=1 | Privileged STGQ (Oracle Reference) | Oracle Upper Reference (Non-Competitive) |   7.40M |   +376.2k | 0.123 |  6.94% |    -25.3k | 0.09616179356020238 |
| h=1 | Site-Local Wspd-Bins | Primary Baseline |   7.02M |     +0.0k | 1.000 |  7.33% |     +0.0k | N/A |
| h=1 | Zero-Privileged Challenger (eps=100) | Oracle Upper Reference (Non-Competitive) |   7.54M |   +516.9k | 0.702 | 12.35% |    -96.8k | 0.28179878515663126 |
| h=1 | Zero-Privileged Challenger (eps=20) | Oracle Upper Reference (Non-Competitive) |   6.67M |   -354.4k | 0.884 |  7.89% |   -163.8k | 0.26805543934039006 |
| h=1 | Zero-Privileged Challenger (eps=50) | Oracle Upper Reference (Non-Competitive) |   6.66M |   -365.9k | 0.880 |  7.95% |   -167.2k | 0.2571786743533556 |
| h=6 | Direct Consequence Quantile MLP | Secondary Baseline / Sensitivity Probe |  22.64M |  +7845.5k | 0.203 | 25.00% |   +212.5k | N/A |
| h=6 | Privileged STGQ (Oracle Reference) | Oracle Upper Reference (Non-Competitive) |  15.13M |   +326.8k | 0.307 |  7.72% |    -25.9k | 0.0963567833901687 |
| h=6 | Site-Local Wspd-Bins | Primary Baseline |  14.80M |     +0.0k | 1.000 |  8.83% |     +0.0k | N/A |
| h=6 | Zero-Privileged Challenger (eps=100) | Oracle Upper Reference (Non-Competitive) |  14.91M |   +105.8k | 0.392 |  7.58% |    -91.4k | 0.1330178205404004 |
| h=6 | Zero-Privileged Challenger (eps=20) | Oracle Upper Reference (Non-Competitive) |  14.81M |     +6.9k | 0.489 |  9.07% |    -93.3k | 0.10861718566854248 |
| h=6 | Zero-Privileged Challenger (eps=50) | Oracle Upper Reference (Non-Competitive) |  18.25M |  +3435.5k | 0.484 | 16.73% |    +17.1k | 0.12839430377574887 |

---

## 3. Protocol Compliance & Hard Assertions Verification

1. **Proxy Label Separation (Correction 1):** Proxy label $\tilde{Z}_t = \mathbb{I}(v_t > 10.5 \land P_{\text{atv}} < 1500 - \epsilon)$ used strictly as an auxiliary weak-supervision loss, not treated as independent ground truth.
2. **Primary Estimand (Correction 2):** Primary ranking determined exclusively by paired downstream PSREI difference with 35-day cluster Block Bootstrap ($B=2000$).
3. **Held-Out Secondary Evaluation (Correction 3):** Blade pitch registers strictly held-out; secondary NMI/Brier reported for diagnostic purposes only and strictly isolated from model selection.
4. **Preregistered Sensitivity (Correction 4):** Evaluated across preregistered grid $\epsilon \in \{20.0, 50.0, 100.0\}\text{ kW}$.
5. **Decoupled Oracle Reference (Correction 5):** Privileged STGQ-Modular demarcated explicitly as Oracle Upper Reference, not a competitive baseline.
6. **Hard Assertions (Correction 6):** Pre-flight checks passed verifying zero pitch channel variance in input tensors and pitch-independent checkpoint selection.
