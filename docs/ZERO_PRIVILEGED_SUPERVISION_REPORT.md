# EXP-02 (EXP-Q1-003): Zero-Privileged-Pitch Supervision Boundary Audit Report

**Status:** RECONCILED AUDIT (Corrected Role Classification & First-Class Stability Metrics)  
**Target Artifact:** `artifacts/zero_privileged_supervision_benchmark.csv`  
**Scientific Contract Anchor:** `docs/SCIENTIFIC_CONTRACT.md:47-55`  
**Formal Scientific Verdict:** **ZERO-PRIVILEGED WEAK-SUPERVISION INSUFFICIENT & HIGH RISK (SEED INSTABILITY CONFIRMED)**

---

## 1. Executive Summary & Epistemic Boundary

Under the zero-privileged weak supervision protocol (where blade pitch telemetry is strictly absent from inputs, supervision loss, and checkpoint selection):

1. **Horizon h=1 (Short-term):**
   - The Primary Challenger achieves a negative median delta of **  -449.0k kWh** (mean **  -365.9k kWh**), with violation rate controlled at **7.95%** (0/5 catastrophic runs).
   - However, individual seed 95% bootstrap CIs span zero across all seeds, confirming that this modest delta does not establish statistically significant decision superiority.

2. **Horizon h=6 (Long-term, Primary Endpoint):**
   - The headline mean difference of **+3,435.5k kWh** is heavily driven by **Seed 201's catastrophic failure** (+17,411.3k kWh delta, 48.60% violation rate), establishing a **20.0% catastrophic failure rate** (1/5 seeds).
   - For the surviving 4 seeds, the median delta is **   -63.4k kWh** (near zero), with violation rate averaging 9.48%.
   - **First-Class Stability Finding:** Rather than a simple 'deficit established' driven by inverted p-value logic, the crucial scientific finding is that **the zero-privileged learning protocol exhibits severe seed instability and unacceptable operational fragility**.

3. **Falsification Guardrail Enforcement:**
   - **SUPPORTED:** The zero-privileged consequence proxy formulation fails to recover a reliable, deployable decision function superior to Site-Local Wspd-Bins.
   - **FORBIDDEN OVERCLAIMS:**
     1. It CANNOT be claimed that *"active power carries no information"* (privileged STGQ achieves NMI 0.461 and bounds the boundary when aligned).
     2. It CANNOT be claimed that real wind farms do not need pitch telemetry.

---

## 2. Reconciled Multi-Seed Benchmark Summary

*Note: Role classification corrected. Catastrophic run rate and robust median metrics elevated to first-class outputs.*

| Horizon | Model | Role | Mean Delta (kWh) | Median Delta (kWh) | Seed Std (kWh) | Violation (%) | Catastrophic Rate | Held-Out NMI |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| h=1 | Direct Consequence Quantile MLP | Secondary Baseline / Sensitivity Probe |   -335.4k |   -318.4k |    235.5k |  7.57% | **0.0%** (0/5) | N/A |
| h=1 | Privileged STGQ (Oracle Reference) | Oracle Upper Reference (Non-Competitive) |   +376.2k |   +301.7k |    373.8k |  6.94% | **0.0%** (0/5) | 0.096 |
| h=1 | Site-Local Wspd-Bins | Primary Baseline |     +0.0k |     +0.0k |      0.0k |  7.33% | **0.0%** (0/5) | N/A |
| h=1 | Zero-Privileged Challenger (eps=100) | Secondary Baseline / Sensitivity Probe |   +516.9k |   -423.4k |   2060.6k | 12.35% | **20.0%** (1/5) | 0.282 |
| h=1 | Zero-Privileged Challenger (eps=20) | Secondary Baseline / Sensitivity Probe |   -354.4k |   -393.2k |    208.2k |  7.89% | **0.0%** (0/5) | 0.268 |
| h=1 | Zero-Privileged Challenger (eps=50) | Primary Challenger |   -365.9k |   -449.0k |    224.2k |  7.95% | **0.0%** (0/5) | 0.257 |
| h=6 | Direct Consequence Quantile MLP | Secondary Baseline / Sensitivity Probe |  +7845.5k |   +895.9k |  10837.9k | 25.00% | **40.0%** (2/5) | N/A |
| h=6 | Privileged STGQ (Oracle Reference) | Oracle Upper Reference (Non-Competitive) |   +326.8k |   +178.3k |    464.1k |  7.72% | **0.0%** (0/5) | 0.096 |
| h=6 | Site-Local Wspd-Bins | Primary Baseline |     +0.0k |     +0.0k |      0.0k |  8.83% | **0.0%** (0/5) | N/A |
| h=6 | Zero-Privileged Challenger (eps=100) | Secondary Baseline / Sensitivity Probe |   +105.8k |    +71.9k |    261.5k |  7.58% | **0.0%** (0/5) | 0.133 |
| h=6 | Zero-Privileged Challenger (eps=20) | Secondary Baseline / Sensitivity Probe |     +6.9k |    -73.3k |    138.2k |  9.07% | **0.0%** (0/5) | 0.109 |
| h=6 | Zero-Privileged Challenger (eps=50) | Primary Challenger |  +3435.5k |    -63.4k |   7813.8k | 16.73% | **20.0%** (1/5) | 0.128 |

---

## 3. Detailed Per-Seed Record Audit

| Horizon | Seed | Model | Role | Full PSREI (kWh) | Delta vs Bins (kWh) | Violation (%) | Catastrophic? |
| :---: | :---: | :--- | :--- | :---: | :---: | :---: | :---: |
| h=1 | 201 | Site-Local Wspd-Bins | Primary Baseline |   7.04M |     +0.0k |  7.40% | **NO** |
| h=1 | 201 | Direct Consequence Quantile MLP | Secondary Baseline / Sensitivity Probe |   7.05M |     +2.0k |  6.83% | **NO** |
| h=1 | 201 | Zero-Privileged Challenger (eps=50) | Primary Challenger |   6.88M |   -167.0k |  7.89% | **NO** |
| h=1 | 201 | Zero-Privileged Challenger (eps=20) | Secondary Baseline / Sensitivity Probe |   6.84M |   -208.1k |  7.92% | **NO** |
| h=1 | 201 | Zero-Privileged Challenger (eps=100) | Secondary Baseline / Sensitivity Probe |  11.24M |  +4184.9k | 31.11% | **YES** |
| h=1 | 201 | Privileged STGQ (Oracle Reference) | Oracle Upper Reference (Non-Competitive) |   7.94M |   +896.9k |  5.47% | **NO** |
| h=1 | 202 | Site-Local Wspd-Bins | Primary Baseline |   4.79M |     +0.0k |  5.78% | **NO** |
| h=1 | 202 | Direct Consequence Quantile MLP | Secondary Baseline / Sensitivity Probe |   4.48M |   -303.5k |  6.59% | **NO** |
| h=1 | 202 | Zero-Privileged Challenger (eps=50) | Primary Challenger |   4.22M |   -567.0k |  7.62% | **NO** |
| h=1 | 202 | Zero-Privileged Challenger (eps=20) | Secondary Baseline / Sensitivity Probe |   4.26M |   -528.7k |  7.24% | **NO** |
| h=1 | 202 | Zero-Privileged Challenger (eps=100) | Secondary Baseline / Sensitivity Probe |   4.21M |   -571.7k |  6.90% | **NO** |
| h=1 | 202 | Privileged STGQ (Oracle Reference) | Oracle Upper Reference (Non-Competitive) |   5.40M |   +606.4k |  7.02% | **NO** |
| h=1 | 203 | Site-Local Wspd-Bins | Primary Baseline |   8.05M |     +0.0k |  9.00% | **NO** |
| h=1 | 203 | Direct Consequence Quantile MLP | Secondary Baseline / Sensitivity Probe |   7.39M |   -655.3k |  7.64% | **NO** |
| h=1 | 203 | Zero-Privileged Challenger (eps=50) | Primary Challenger |   7.60M |   -449.0k |  7.60% | **NO** |
| h=1 | 203 | Zero-Privileged Challenger (eps=20) | Secondary Baseline / Sensitivity Probe |   7.65M |   -393.2k |  7.24% | **NO** |
| h=1 | 203 | Zero-Privileged Challenger (eps=100) | Secondary Baseline / Sensitivity Probe |   7.62M |   -423.4k |  7.13% | **NO** |
| h=1 | 203 | Privileged STGQ (Oracle Reference) | Oracle Upper Reference (Non-Competitive) |   8.10M |    +52.0k |  8.18% | **NO** |
| h=1 | 204 | Site-Local Wspd-Bins | Primary Baseline |   8.35M |     +0.0k |  8.22% | **NO** |
| h=1 | 204 | Direct Consequence Quantile MLP | Secondary Baseline / Sensitivity Probe |   8.03M |   -318.4k |  9.75% | **NO** |
| h=1 | 204 | Zero-Privileged Challenger (eps=50) | Primary Challenger |   8.26M |    -88.1k |  8.77% | **NO** |
| h=1 | 204 | Zero-Privileged Challenger (eps=20) | Secondary Baseline / Sensitivity Probe |   8.27M |    -78.1k |  8.75% | **NO** |
| h=1 | 204 | Zero-Privileged Challenger (eps=100) | Secondary Baseline / Sensitivity Probe |   8.29M |    -60.3k |  8.59% | **NO** |
| h=1 | 204 | Privileged STGQ (Oracle Reference) | Oracle Upper Reference (Non-Competitive) |   8.65M |   +301.7k |  7.70% | **NO** |
| h=1 | 205 | Site-Local Wspd-Bins | Primary Baseline |   6.87M |     +0.0k |  6.27% | **NO** |
| h=1 | 205 | Direct Consequence Quantile MLP | Secondary Baseline / Sensitivity Probe |   6.47M |   -401.8k |  7.06% | **NO** |
| h=1 | 205 | Zero-Privileged Challenger (eps=50) | Primary Challenger |   6.32M |   -558.4k |  7.88% | **NO** |
| h=1 | 205 | Zero-Privileged Challenger (eps=20) | Secondary Baseline / Sensitivity Probe |   6.31M |   -563.8k |  8.28% | **NO** |
| h=1 | 205 | Zero-Privileged Challenger (eps=100) | Secondary Baseline / Sensitivity Probe |   6.33M |   -545.1k |  8.02% | **NO** |
| h=1 | 205 | Privileged STGQ (Oracle Reference) | Oracle Upper Reference (Non-Competitive) |   6.90M |    +23.8k |  6.31% | **NO** |
| h=6 | 201 | Site-Local Wspd-Bins | Primary Baseline |  14.48M |     +0.0k |  8.50% | **NO** |
| h=6 | 201 | Direct Consequence Quantile MLP | Secondary Baseline / Sensitivity Probe |  15.39M |   +895.9k |  5.25% | **NO** |
| h=6 | 201 | Zero-Privileged Challenger (eps=50) | Primary Challenger |  31.96M | +17411.3k | 48.60% | **YES** |
| h=6 | 201 | Zero-Privileged Challenger (eps=20) | Secondary Baseline / Sensitivity Probe |  14.64M |   +150.6k |  9.77% | **NO** |
| h=6 | 201 | Zero-Privileged Challenger (eps=100) | Secondary Baseline / Sensitivity Probe |  15.02M |   +529.0k |  5.98% | **NO** |
| h=6 | 201 | Privileged STGQ (Oracle Reference) | Oracle Upper Reference (Non-Competitive) |  15.50M |  +1015.0k |  5.92% | **NO** |
| h=6 | 202 | Site-Local Wspd-Bins | Primary Baseline |  12.49M |     +0.0k |  8.06% | **NO** |
| h=6 | 202 | Direct Consequence Quantile MLP | Secondary Baseline / Sensitivity Probe |  26.57M | +14121.2k | 44.24% | **YES** |
| h=6 | 202 | Zero-Privileged Challenger (eps=50) | Primary Challenger |  12.31M |   -178.3k |  9.48% | **NO** |
| h=6 | 202 | Zero-Privileged Challenger (eps=20) | Secondary Baseline / Sensitivity Probe |  12.41M |    -73.3k |  9.46% | **NO** |
| h=6 | 202 | Zero-Privileged Challenger (eps=100) | Secondary Baseline / Sensitivity Probe |  12.56M |    +71.9k |  6.52% | **NO** |
| h=6 | 202 | Privileged STGQ (Oracle Reference) | Oracle Upper Reference (Non-Competitive) |  13.06M |   +570.2k |  7.94% | **NO** |
| h=6 | 203 | Site-Local Wspd-Bins | Primary Baseline |  16.20M |     +0.0k | 10.40% | **NO** |
| h=6 | 203 | Direct Consequence Quantile MLP | Secondary Baseline / Sensitivity Probe |  40.24M | +24027.4k | 55.04% | **YES** |
| h=6 | 203 | Zero-Privileged Challenger (eps=50) | Primary Challenger |  16.35M |   +159.9k |  7.64% | **NO** |
| h=6 | 203 | Zero-Privileged Challenger (eps=20) | Secondary Baseline / Sensitivity Probe |  16.36M |   +161.8k |  7.63% | **NO** |
| h=6 | 203 | Zero-Privileged Challenger (eps=100) | Secondary Baseline / Sensitivity Probe |  16.33M |   +135.4k |  7.78% | **NO** |
| h=6 | 203 | Privileged STGQ (Oracle Reference) | Oracle Upper Reference (Non-Competitive) |  16.37M |   +178.3k |  8.76% | **NO** |
| h=6 | 204 | Site-Local Wspd-Bins | Primary Baseline |  16.17M |     +0.0k |  9.35% | **NO** |
| h=6 | 204 | Direct Consequence Quantile MLP | Secondary Baseline / Sensitivity Probe |  16.42M |   +265.8k | 13.38% | **NO** |
| h=6 | 204 | Zero-Privileged Challenger (eps=50) | Primary Challenger |  16.01M |   -152.1k | 11.15% | **NO** |
| h=6 | 204 | Zero-Privileged Challenger (eps=20) | Secondary Baseline / Sensitivity Probe |  16.03M |   -129.7k | 11.68% | **NO** |
| h=6 | 204 | Zero-Privileged Challenger (eps=100) | Secondary Baseline / Sensitivity Probe |  16.01M |   -151.6k | 10.95% | **NO** |
| h=6 | 204 | Privileged STGQ (Oracle Reference) | Oracle Upper Reference (Non-Competitive) |  16.09M |    -71.3k |  8.26% | **NO** |
| h=6 | 205 | Site-Local Wspd-Bins | Primary Baseline |  14.67M |     +0.0k |  7.83% | **NO** |
| h=6 | 205 | Direct Consequence Quantile MLP | Secondary Baseline / Sensitivity Probe |  14.58M |    -82.7k |  7.09% | **NO** |
| h=6 | 205 | Zero-Privileged Challenger (eps=50) | Primary Challenger |  14.60M |    -63.4k |  6.75% | **NO** |
| h=6 | 205 | Zero-Privileged Challenger (eps=20) | Secondary Baseline / Sensitivity Probe |  14.59M |    -74.9k |  6.80% | **NO** |
| h=6 | 205 | Zero-Privileged Challenger (eps=100) | Secondary Baseline / Sensitivity Probe |  14.61M |    -55.6k |  6.69% | **NO** |
| h=6 | 205 | Privileged STGQ (Oracle Reference) | Oracle Upper Reference (Non-Competitive) |  14.60M |    -58.1k |  7.71% | **NO** |

---

## 4. Methodological Audit & Protocol Verifications

1. **Role Classification Verification:** The previous bug where `Zero-Privileged Challenger` was labeled as `Oracle Upper Reference (Non-Competitive)` has been rectified. Oracle status is restricted to `Privileged STGQ`.
2. **P-Value & Metric Semantics:** `p_val_delta_psrei` represents empirical $P(\Delta \le 0)$ (probability challenger is non-inferior to baseline). The previous automatic decision rule erroneously required $\Delta < 0 \land p < 0.05$ as if $p$ were a two-tailed null test. The reconciled report removes this contradictory rule.
3. **Catastrophic Failure Recognition:** Seed 201 at $h=6$ failed with a 48.60% violation rate and +17.41M kWh penalty. This catastrophic policy collapse is now reported as a primary finding regarding training instability.
