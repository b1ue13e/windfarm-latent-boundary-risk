# EXP-02 (EXP-Q1-003): Zero-Privileged-Pitch Supervision Boundary Audit Report

**Date:** 2026-10-13 09:00:52  
**Target Artifact:** `artifacts/zero_privileged_supervision_benchmark.csv`  
**Registry Reference:** `docs/EXPERIMENT_REGISTRY.md:229-292`  
**Scientific Contract Anchor:** `docs/SCIENTIFIC_CONTRACT.md:47-55`  
**Formal Scientific Verdict:** **NO STABLE ZERO-PRIVILEGED ADVANTAGE ESTABLISHED** (DEFICIT NOT ESTABLISHED; INSTABILITY OBSERVED)

---

## 1. Pre-registered decision rule

A challenger is reported as a supported decision improvement only when both
pre-registered statistical conditions hold at the stated horizon:

1. **C1 point estimate non-inferior** — `mean delta PSREI <= 0` (PSREI is a cost).
2. **C2 strong non-inferiority evidence** — `P(delta <= 0) >= 0.95`.

Otherwise the verdict is "no stable advantage observed".

`P(delta <= 0)` is the empirical bootstrap probability that the challenger is
non-inferior. It is **not** a conventional two-sided p-value.

### Diagnostics (reported, not gating)

PSREI is a *cost*, and a policy that simply procures less reserve is mechanically
cheaper while violating more often. A cheaper point estimate is therefore only
interpretable alongside procurement/risk levels, so the following are reported
next to the verdict rather than folded into it:

- **D1** reserve not under-procured — `delta violation <= 0.0 pp`.
- **D2** shortage exposure not degraded — `delta shortage <= 0.0 kWh`.

They are deliberately **not** part of the gate, so that the verdict cannot be
steered by a post-hoc-chosen tolerance. A passing verdict accompanied by failing
diagnostics is summarised as "cheaper but not demonstrably better".


Applied to the Primary Challenger `Zero-Privileged Challenger (eps=50)` against the Primary
Baseline `Site-Local Wspd-Bins`:

**Horizon h=1** — verdict `DIRECTIONAL_ONLY_NOT_CONCLUSIVE`:
   - [PASS] C1 point estimate non-inferior: mean delta PSREI = -365,904.0 kWh (<= 0 required)
   - [FAIL] C2 strong non-inferiority evidence: P(delta <= 0) = 0.8805 (>= 0.95 required)
   - [degraded] D1 reserve not under-procured (diagnostic): delta violation = +0.6208 pp
   - [degraded] D2 shortage exposure not degraded (diagnostic): delta shortage = +58,762.5 kWh
   - threshold sensitivity (C1 && P>=0.95): 0.500->SUPPORTED, 0.800->SUPPORTED, 0.900->null, 0.950->null, 0.975->null

**Horizon h=6** — verdict `NO_STABLE_ADVANTAGE_OBSERVED`:
   - [FAIL] C1 point estimate non-inferior: mean delta PSREI = +3,435,465.4 kWh (<= 0 required)
   - [FAIL] C2 strong non-inferiority evidence: P(delta <= 0) = 0.4837 (>= 0.95 required)
   - [degraded] D1 reserve not under-procured (diagnostic): delta violation = +7.8984 pp
   - [degraded] D2 shortage exposure not degraded (diagnostic): delta shortage = +558,694.3 kWh
   - threshold sensitivity (C1 && P>=0.95): 0.500->null, 0.800->null, 0.900->null, 0.950->null, 0.975->null

---

## 2. Executive Summary

Under the zero-privileged weak supervision protocol (blade pitch strictly withheld
from inputs, supervision loss, and checkpoint selection):

1. **Horizon h=1.** Mean delta PSREI = **-365.9k kWh**
   with empirical P(non-inferior) = **0.8805**.
   The challenger procures **-953.3k kWh**
   less reserve than the baseline, which is why its PSREI is lower; violation rate
   moves 7.33% -> 7.95%
   (delta **+0.62 pp**) and shortage exposure
   **+58.8k kWh**.
2. **Horizon h=6 (primary endpoint).** Mean delta PSREI =
   **+3,435.5k kWh**, but this mean is
   dominated by a single catastrophic seed (Seed 201:
   +17,411.3k kWh delta, 48.60% violation rate). Catastrophic
   run rate = **20.0%** (1/5 seeds).
3. **Operational fragility:** reserve procurement collapses by
   **-2,140.5k kWh**
   at h=6 while violation rises 8.83% ->
   16.73% and shortage exposure rises
   **+558.7k kWh**.

**Supported conclusion:** the tested zero-privileged weak-supervision protocol
establishes no stable downstream decision advantage over Site-Local Wspd-Bins,
and exhibits severe seed instability at the longer horizon. At h=1 the point
estimate favours the challenger at the pre-registered level C1 but fails the
evidence bar C2, and it does so by procuring less reserve at a higher violation
rate -- so the h=1 direction is "cheaper but not demonstrably better" rather
than an established gain.

**Strict Scientific Guardrail:**
- **FORBIDDEN OVERCLAIMS:**
  1. It CANNOT be concluded that *"active-power consequence carries no mutual
     information"* (privileged STGQ bounds the boundary when aligned).
  2. It CANNOT be concluded that *"real wind farms do not need pitch telemetry"*.
  3. It CANNOT be concluded that a *"deficit is established"* as a general
     property of consequence supervision. The current evidence licenses only
     "no stable advantage established under this protocol", because the h=6 mean
     is driven by one collapsed seed rather than by a uniform deficit.

---

## 3. Joint Hierarchical Uncertainty & Stability Summary (Two-Level Bootstrap)

*Note: Resamples simultaneously across day-clusters and model training seeds, so
CIs and probabilities are not computed by improperly averaging per-seed bounds.*

| Horizon | Model | Role | Median Delta (kWh) | Mean Delta (kWh) | Seed Std (kWh) | Joint 95% CI (Delta) | P(Delta <= 0) | Catastrophic Rate |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| h=1 | Direct Consequence Quantile MLP | Secondary Baseline / Sensitivity Probe |   -318.4k |   -335.4k |    235.5k | - | - | 0.0% (0/5) |
| h=1 | Privileged STGQ (Oracle Reference) | Oracle Upper Reference (Non-Competitive) |   +301.7k |   +376.2k |    373.8k | - | - | 0.0% (0/5) |
| h=1 | Site-Local Wspd-Bins | Primary Baseline |     +0.0k |     +0.0k |      0.0k | - | - | 0.0% (0/5) |
| h=1 | Zero-Privileged Challenger (eps=100) | Secondary Baseline / Sensitivity Probe |   -423.4k |   +516.9k |   2060.6k | - | - | 20.0% (1/5) |
| h=1 | Zero-Privileged Challenger (eps=20) | Secondary Baseline / Sensitivity Probe |   -393.2k |   -354.4k |    208.2k | - | - | 0.0% (0/5) |
| h=1 | Zero-Privileged Challenger (eps=50) | Primary Challenger |   -449.0k |   -365.9k |    224.2k | - | - | 0.0% (0/5) |
| h=6 | Direct Consequence Quantile MLP | Secondary Baseline / Sensitivity Probe |   +895.9k |  +7845.5k |  10837.9k | - | - | 40.0% (2/5) |
| h=6 | Privileged STGQ (Oracle Reference) | Oracle Upper Reference (Non-Competitive) |   +178.3k |   +326.8k |    464.1k | - | - | 0.0% (0/5) |
| h=6 | Site-Local Wspd-Bins | Primary Baseline |     +0.0k |     +0.0k |      0.0k | - | - | 0.0% (0/5) |
| h=6 | Zero-Privileged Challenger (eps=100) | Secondary Baseline / Sensitivity Probe |    +71.9k |   +105.8k |    261.5k | - | - | 0.0% (0/5) |
| h=6 | Zero-Privileged Challenger (eps=20) | Secondary Baseline / Sensitivity Probe |    -73.3k |     +6.9k |    138.2k | - | - | 0.0% (0/5) |
| h=6 | Zero-Privileged Challenger (eps=50) | Primary Challenger |    -63.4k |  +3435.5k |   7813.8k | - | - | 20.0% (1/5) |

---

## 4. Detailed Per-Seed Disaggregation (Transparency on Seed Variance)

| Horizon | Seed | Model | Role | Full PSREI (kWh) | Delta PSREI vs Bins | Violation (%) | Catastrophic? | Held-Out NMI |
| :--- | :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| h=1 | 201 | Site-Local Wspd-Bins | Primary Baseline |   7.04M |     +0.0k |  7.40% | **NO** | N/A |
| h=1 | 201 | Direct Consequence Quantile MLP | Secondary Baseline / Sensitivity Probe |   7.05M |     +2.0k |  6.83% | **NO** | N/A |
| h=1 | 201 | Zero-Privileged Challenger (eps=50) | Primary Challenger |   6.88M |   -167.0k |  7.89% | **NO** | 0.4063589927404757 |
| h=1 | 201 | Zero-Privileged Challenger (eps=20) | Secondary Baseline / Sensitivity Probe |   6.84M |   -208.1k |  7.92% | **NO** | 0.3775026168689934 |
| h=1 | 201 | Zero-Privileged Challenger (eps=100) | Secondary Baseline / Sensitivity Probe |  11.24M |  +4184.9k | 31.11% | **YES** | 0.4948766138439873 |
| h=1 | 201 | Privileged STGQ (Oracle Reference) | Oracle Upper Reference (Non-Competitive) |   7.94M |   +896.9k |  5.47% | **NO** | 0.1201691719382034 |
| h=1 | 202 | Site-Local Wspd-Bins | Primary Baseline |   4.79M |     +0.0k |  5.78% | **NO** | N/A |
| h=1 | 202 | Direct Consequence Quantile MLP | Secondary Baseline / Sensitivity Probe |   4.48M |   -303.5k |  6.59% | **NO** | N/A |
| h=1 | 202 | Zero-Privileged Challenger (eps=50) | Primary Challenger |   4.22M |   -567.0k |  7.62% | **NO** | 0.123954791760538 |
| h=1 | 202 | Zero-Privileged Challenger (eps=20) | Secondary Baseline / Sensitivity Probe |   4.26M |   -528.7k |  7.24% | **NO** | 0.1392741815344145 |
| h=1 | 202 | Zero-Privileged Challenger (eps=100) | Secondary Baseline / Sensitivity Probe |   4.21M |   -571.7k |  6.90% | **NO** | 0.1241668625651553 |
| h=1 | 202 | Privileged STGQ (Oracle Reference) | Oracle Upper Reference (Non-Competitive) |   5.40M |   +606.4k |  7.02% | **NO** | 0.0 |
| h=1 | 203 | Site-Local Wspd-Bins | Primary Baseline |   8.05M |     +0.0k |  9.00% | **NO** | N/A |
| h=1 | 203 | Direct Consequence Quantile MLP | Secondary Baseline / Sensitivity Probe |   7.39M |   -655.3k |  7.64% | **NO** | N/A |
| h=1 | 203 | Zero-Privileged Challenger (eps=50) | Primary Challenger |   7.60M |   -449.0k |  7.60% | **NO** | 0.3699751722220255 |
| h=1 | 203 | Zero-Privileged Challenger (eps=20) | Secondary Baseline / Sensitivity Probe |   7.65M |   -393.2k |  7.24% | **NO** | 0.3860592570522657 |
| h=1 | 203 | Zero-Privileged Challenger (eps=100) | Secondary Baseline / Sensitivity Probe |   7.62M |   -423.4k |  7.13% | **NO** | 0.3880352982176152 |
| h=1 | 203 | Privileged STGQ (Oracle Reference) | Oracle Upper Reference (Non-Competitive) |   8.10M |    +52.0k |  8.18% | **NO** | 0.2604431850509319 |
| h=1 | 204 | Site-Local Wspd-Bins | Primary Baseline |   8.35M |     +0.0k |  8.22% | **NO** | N/A |
| h=1 | 204 | Direct Consequence Quantile MLP | Secondary Baseline / Sensitivity Probe |   8.03M |   -318.4k |  9.75% | **NO** | N/A |
| h=1 | 204 | Zero-Privileged Challenger (eps=50) | Primary Challenger |   8.26M |    -88.1k |  8.77% | **NO** | 0.3078064436902644 |
| h=1 | 204 | Zero-Privileged Challenger (eps=20) | Secondary Baseline / Sensitivity Probe |   8.27M |    -78.1k |  8.75% | **NO** | 0.3420598735150052 |
| h=1 | 204 | Zero-Privileged Challenger (eps=100) | Secondary Baseline / Sensitivity Probe |   8.29M |    -60.3k |  8.59% | **NO** | 0.3098577638936726 |
| h=1 | 204 | Privileged STGQ (Oracle Reference) | Oracle Upper Reference (Non-Competitive) |   8.65M |   +301.7k |  7.70% | **NO** | 0.1001966108118764 |
| h=1 | 205 | Site-Local Wspd-Bins | Primary Baseline |   6.87M |     +0.0k |  6.27% | **NO** | N/A |
| h=1 | 205 | Direct Consequence Quantile MLP | Secondary Baseline / Sensitivity Probe |   6.47M |   -401.8k |  7.06% | **NO** | N/A |
| h=1 | 205 | Zero-Privileged Challenger (eps=50) | Primary Challenger |   6.32M |   -558.4k |  7.88% | **NO** | 0.0777979713534745 |
| h=1 | 205 | Zero-Privileged Challenger (eps=20) | Secondary Baseline / Sensitivity Probe |   6.31M |   -563.8k |  8.28% | **NO** | 0.0953812677312713 |
| h=1 | 205 | Zero-Privileged Challenger (eps=100) | Secondary Baseline / Sensitivity Probe |   6.33M |   -545.1k |  8.02% | **NO** | 0.0920573872627258 |
| h=1 | 205 | Privileged STGQ (Oracle Reference) | Oracle Upper Reference (Non-Competitive) |   6.90M |    +23.8k |  6.31% | **NO** | 0.0 |
| h=6 | 201 | Site-Local Wspd-Bins | Primary Baseline |  14.48M |     +0.0k |  8.50% | **NO** | N/A |
| h=6 | 201 | Direct Consequence Quantile MLP | Secondary Baseline / Sensitivity Probe |  15.39M |   +895.9k |  5.25% | **NO** | N/A |
| h=6 | 201 | Zero-Privileged Challenger (eps=50) | Primary Challenger |  31.96M | +17411.3k | 48.60% | **YES** | 0.3930674345531 |
| h=6 | 201 | Zero-Privileged Challenger (eps=20) | Secondary Baseline / Sensitivity Probe |  14.64M |   +150.6k |  9.77% | **NO** | 0.2775266615926583 |
| h=6 | 201 | Zero-Privileged Challenger (eps=100) | Secondary Baseline / Sensitivity Probe |  15.02M |   +529.0k |  5.98% | **NO** | 0.3814126343317394 |
| h=6 | 201 | Privileged STGQ (Oracle Reference) | Oracle Upper Reference (Non-Competitive) |  15.50M |  +1015.0k |  5.92% | **NO** | 0.1211035967161128 |
| h=6 | 202 | Site-Local Wspd-Bins | Primary Baseline |  12.49M |     +0.0k |  8.06% | **NO** | N/A |
| h=6 | 202 | Direct Consequence Quantile MLP | Secondary Baseline / Sensitivity Probe |  26.57M | +14121.2k | 44.24% | **YES** | N/A |
| h=6 | 202 | Zero-Privileged Challenger (eps=50) | Primary Challenger |  12.31M |   -178.3k |  9.48% | **NO** | 0.0361972659767194 |
| h=6 | 202 | Zero-Privileged Challenger (eps=20) | Secondary Baseline / Sensitivity Probe |  12.41M |    -73.3k |  9.46% | **NO** | 0.0527707593742662 |
| h=6 | 202 | Zero-Privileged Challenger (eps=100) | Secondary Baseline / Sensitivity Probe |  12.56M |    +71.9k |  6.52% | **NO** | 0.0604052799646104 |
| h=6 | 202 | Privileged STGQ (Oracle Reference) | Oracle Upper Reference (Non-Competitive) |  13.06M |   +570.2k |  7.94% | **NO** | 0.0 |
| h=6 | 203 | Site-Local Wspd-Bins | Primary Baseline |  16.20M |     +0.0k | 10.40% | **NO** | N/A |
| h=6 | 203 | Direct Consequence Quantile MLP | Secondary Baseline / Sensitivity Probe |  40.24M | +24027.4k | 55.04% | **YES** | N/A |
| h=6 | 203 | Zero-Privileged Challenger (eps=50) | Primary Challenger |  16.35M |   +159.9k |  7.64% | **NO** | 0.05816260024095 |
| h=6 | 203 | Zero-Privileged Challenger (eps=20) | Secondary Baseline / Sensitivity Probe |  16.36M |   +161.8k |  7.63% | **NO** | 0.0641266217353507 |
| h=6 | 203 | Zero-Privileged Challenger (eps=100) | Secondary Baseline / Sensitivity Probe |  16.33M |   +135.4k |  7.78% | **NO** | 0.0641272513435552 |
| h=6 | 203 | Privileged STGQ (Oracle Reference) | Oracle Upper Reference (Non-Competitive) |  16.37M |   +178.3k |  8.76% | **NO** | 0.2601849653488572 |
| h=6 | 204 | Site-Local Wspd-Bins | Primary Baseline |  16.17M |     +0.0k |  9.35% | **NO** | N/A |
| h=6 | 204 | Direct Consequence Quantile MLP | Secondary Baseline / Sensitivity Probe |  16.42M |   +265.8k | 13.38% | **NO** | N/A |
| h=6 | 204 | Zero-Privileged Challenger (eps=50) | Primary Challenger |  16.01M |   -152.1k | 11.15% | **NO** | 0.0670489464015239 |
| h=6 | 204 | Zero-Privileged Challenger (eps=20) | Secondary Baseline / Sensitivity Probe |  16.03M |   -129.7k | 11.68% | **NO** | 0.0622874875393074 |
| h=6 | 204 | Zero-Privileged Challenger (eps=100) | Secondary Baseline / Sensitivity Probe |  16.01M |   -151.6k | 10.95% | **NO** | 0.0797619768032945 |
| h=6 | 204 | Privileged STGQ (Oracle Reference) | Oracle Upper Reference (Non-Competitive) |  16.09M |    -71.3k |  8.26% | **NO** | 0.1004953548858735 |
| h=6 | 205 | Site-Local Wspd-Bins | Primary Baseline |  14.67M |     +0.0k |  7.83% | **NO** | N/A |
| h=6 | 205 | Direct Consequence Quantile MLP | Secondary Baseline / Sensitivity Probe |  14.58M |    -82.7k |  7.09% | **NO** | N/A |
| h=6 | 205 | Zero-Privileged Challenger (eps=50) | Primary Challenger |  14.60M |    -63.4k |  6.75% | **NO** | 0.087495271706451 |
| h=6 | 205 | Zero-Privileged Challenger (eps=20) | Secondary Baseline / Sensitivity Probe |  14.59M |    -74.9k |  6.80% | **NO** | 0.0863743981011296 |
| h=6 | 205 | Zero-Privileged Challenger (eps=100) | Secondary Baseline / Sensitivity Probe |  14.61M |    -55.6k |  6.69% | **NO** | 0.0793819602588022 |
| h=6 | 205 | Privileged STGQ (Oracle Reference) | Oracle Upper Reference (Non-Competitive) |  14.60M |    -58.1k |  7.71% | **NO** | 0.0 |

---

## 5. Protocol Compliance & Hard Assertions Verification

1. **Proxy Label Separation (Correction 1):** Proxy label $\tilde{Z}_t = \mathbb{I}(v_t > 10.5 \land P_{\text{atv}} < 1500 - \epsilon)$ used strictly as an auxiliary weak-supervision loss, not treated as independent ground truth.
2. **Primary Estimand (Correction 2):** Primary ranking evaluated by paired downstream PSREI difference with hierarchical cluster Block Bootstrap ($B=2000$).
3. **Held-Out Secondary Diagnostic (Correction 3):** Blade pitch registers strictly held-out; secondary NMI/Brier reported for diagnostic characterization only and strictly isolated from model selection.
4. **Preregistered Sensitivity (Correction 4):** Evaluated across preregistered grid $\epsilon \in \{20.0, 50.0, 100.0\}\text{ kW}$.
5. **Decoupled Oracle Reference (Correction 5):** Privileged STGQ-Modular demarcated explicitly as Oracle Upper Reference, not a competitive baseline.
6. **Hard Assertions (Correction 6):** Pre-flight checks passed verifying zero pitch channel variance in input tensors and pitch-independent checkpoint selection.

---

## 6. Verdict Derivation & Role Classification Provenance

1. **Role classification is table-driven, never substring-driven.** An earlier
   version evaluated `"Privileged" in model_name` first, which labelled every
   `Zero-Privileged Challenger` variant as an Oracle upper reference. Roles now
   come from `scripts/exp02_verdict.py:assign_model_role`, which matches exact
   registered names and explicit prefix families and otherwise degrades to the
   least privileged role.
2. **The verdict is a pure function of the measured statistics.** An earlier
   version hard-coded the outcome string, then later hard-coded a different
   outcome string; both are replaced by
   `scripts/exp02_verdict.py:derive_verdict`. The four conditions and their
   PASS/FAIL detail are printed in Section 1 of this report.
3. **Bootstrap field semantics.** The paired bootstrap quantity is
   $P(\Delta \le 0)$, the empirical probability of non-inferiority. It is **not**
   a two-sided p-value. The earlier decision rule
   `challenger_wins = (delta < 0) and (p < 0.05)` was internally contradictory:
   a negative delta pushes $P(\Delta \le 0)$ toward 1.0, never below 0.05, so the
   conjunction was effectively unsatisfiable and the report emitted a fixed
   negative verdict irrespective of the data.
4. **Reproducibility boundary.** The joint two-level confidence intervals in
   Section 3 require per-seed block-level paired differences, which the frozen
   benchmark CSV does not persist; they are reproducible only by re-running the
   benchmark. Section 3's median/mean/std columns and the Sections 1-2 verdict
   are reproducible from the frozen CSV alone.
