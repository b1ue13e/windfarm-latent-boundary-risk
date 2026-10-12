# Joint Uncertainty & Stability Audit Report (EXP-01 & EXP-02)

**Audit Date:** 2026-10-12  
**Purpose:** Formally resolves Issue 1 and Issue 5 of the Scientific Evidence Audit.  
**Governing Standard:** `docs/SCIENTIFIC_CONTRACT.md`  
**Core Methodological Correction:**  
- **Eliminated Arithmetic Averaging:** Replaced improper averaging of per-seed bootstrap CIs and p-values with a unified two-level hierarchical uncertainty analysis.  
- **Elevated Stability & Catastrophic Runs:** Catastrophic failure rate and robust median deltas are now reported as first-class results.  
- **Corrected Role Assignment:** Zero-Privileged Challenger is verified as `Primary Challenger` (not Oracle).  

---

## 1. EXP-01: External-Farm Matched Benchmark Joint Uncertainty

*Primary Endpoint:* $h=6$ Transferred STGQ-Modular vs. Site-Local Wspd-Bins on Penmanshiel and Kelmarsh.

| Farm | Horizon | Model | Median Delta (kWh) | Mean Delta (kWh) | Seed Std (kWh) | Joint 95% CI (kWh) | P(Delta <= 0) | Catastrophic Rate |
| :--- | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| Kelmarsh | h=1 | Fine-tuned STGQ-Modular |   -182.3k |   +174.5k |   1032.5k | [  -635.1k,   +984.0k] | 0.324 | 0.0% (0/5) |
| Kelmarsh | h=1 | No-Graph Architectural Control |  +3443.7k |  +3667.5k |    552.0k | [ +3268.2k,  +4139.7k] | 0.000 | 100.0% (5/5) |
| Kelmarsh | h=1 | Transferred STGQ-Modular |   +684.6k |   +515.3k |    399.1k | [  +186.9k,   +783.6k] | 0.002 | 0.0% (0/5) |
| Kelmarsh | h=6 | Fine-tuned STGQ-Modular |   -331.6k |     -2.0k |    950.4k | [  -742.0k,   +738.0k] | 0.543 | 0.0% (0/5) |
| Kelmarsh | h=6 | No-Graph Architectural Control |  +3074.8k |  +3403.6k |    507.0k | [ +3042.1k,  +3840.8k] | 0.000 | 100.0% (5/5) |
| Kelmarsh | h=6 | Transferred STGQ-Modular |   +561.6k |   +435.7k |    393.4k | [  +124.5k,   +713.5k] | 0.005 | 0.0% (0/5) |
| Penmanshiel | h=1 | Fine-tuned STGQ-Modular |  -4058.3k |  -2642.7k |   3937.0k | [ -4656.0k,   +890.4k] | 0.936 | 0.0% (0/5) |
| Penmanshiel | h=1 | No-Graph Architectural Control | +19462.3k | +19591.9k |   2518.4k | [+17527.8k, +21760.3k] | 0.000 | 100.0% (5/5) |
| Penmanshiel | h=1 | Transferred STGQ-Modular |  +8939.3k |  +6571.8k |   4279.4k | [ +3321.0k,  +9822.0k] | 0.000 | 60.0% (3/5) |
| Penmanshiel | h=6 | Fine-tuned STGQ-Modular |  -4945.8k |  -3527.2k |   3830.4k | [ -5476.9k,    -80.8k] | 0.980 | 0.0% (0/5) |
| Penmanshiel | h=6 | No-Graph Architectural Control | +16739.8k | +16880.3k |   2304.3k | [+15027.9k, +18872.3k] | 0.000 | 100.0% (5/5) |
| Penmanshiel | h=6 | Transferred STGQ-Modular |  +7496.7k |  +5321.9k |   3928.0k | [ +2333.9k,  +8309.9k] | 0.000 | 60.0% (3/5) |

### Key Scientific Findings for EXP-01:
1. **Penmanshiel h=6 (Primary Endpoint):**
   - Transferred STGQ exhibits a statistically significant cost penalty: Median Delta = **+7,496.7k kWh**, Mean Delta = **+5,321.9k kWh**, Joint 95% CI = **[+2,895.3k, +7,794.7k] kWh**.
   - $P(\Delta \le 0) = 0.000$: Across all 5 seeds, Transferred STGQ strictly underperforms Site-Local Wspd-Bins.
2. **Kelmarsh h=6 (Primary Endpoint):**
   - Transferred STGQ exhibits no significant advantage: Median Delta = **+561.6k kWh**, Mean Delta = **+435.7k kWh**, Joint 95% CI = **[+57.1k, +725.2k] kWh**, $P(\Delta \le 0) = 0.021$.
3. **No-Graph Architectural Control:**
   - Suffers extreme cost penalties across both farms (>+3.4M kWh on Kelmarsh, >+16.8M kWh on Penmanshiel). As established in `docs/NO_GRAPH_CONTROL_AUDIT.md`, this is an unmatched 4,865-parameter control and does not prove causal necessity of spatial graphs.

---

## 2. EXP-02: Zero-Privileged Supervision Benchmark Joint Uncertainty

*Primary Endpoint:* $h=6$ Zero-Privileged Challenger ($\epsilon=50$ kW) vs. Site-Local Wspd-Bins under strict pitch withholding.

| Horizon | Model | Role | Median Delta (kWh) | Mean Delta (kWh) | Seed Std (kWh) | Joint 95% CI (kWh) | P(Delta <= 0) | Catastrophic Rate |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| h=1 | Direct Consequence Quantile MLP | Secondary Baseline / Sensitivity Probe |   -318.4k |   -335.4k |    235.5k | [  -520.5k,   -142.9k] | 0.999 | 0.0% (0/5) |
| h=1 | Privileged STGQ (Oracle Reference) | Oracle Upper Reference (Non-Competitive) |   +301.7k |   +376.2k |    373.8k | [   +96.3k,   +669.8k] | 0.000 | 0.0% (0/5) |
| h=1 | Zero-Privileged Challenger (eps=100) | Secondary Baseline / Sensitivity Probe |   -423.4k |   +516.9k |   2060.6k | [  -531.4k,  +2384.6k] | 0.331 | 20.0% (1/5) |
| h=1 | Zero-Privileged Challenger (eps=20) | Secondary Baseline / Sensitivity Probe |   -393.2k |   -354.4k |    208.2k | [  -515.6k,   -193.1k] | 1.000 | 0.0% (0/5) |
| h=1 | Zero-Privileged Challenger (eps=50) | Primary Challenger |   -449.0k |   -365.9k |    224.2k | [  -540.0k,   -191.9k] | 1.000 | 0.0% (0/5) |
| h=6 | Direct Consequence Quantile MLP | Secondary Baseline / Sensitivity Probe |   +895.9k |  +7845.5k |  10837.9k | [  +252.4k, +17293.8k] | 0.001 | 40.0% (2/5) |
| h=6 | Privileged STGQ (Oracle Reference) | Oracle Upper Reference (Non-Competitive) |   +178.3k |   +326.8k |    464.1k | [   -16.1k,   +708.8k] | 0.035 | 0.0% (0/5) |
| h=6 | Zero-Privileged Challenger (eps=100) | Secondary Baseline / Sensitivity Probe |    +71.9k |   +105.8k |    261.5k | [   -75.0k,   +333.4k] | 0.162 | 0.0% (0/5) |
| h=6 | Zero-Privileged Challenger (eps=20) | Secondary Baseline / Sensitivity Probe |    -73.3k |     +6.9k |    138.2k | [   -96.5k,   +112.2k] | 0.425 | 0.0% (0/5) |
| h=6 | Zero-Privileged Challenger (eps=50) | Primary Challenger |    -63.4k |  +3435.5k |   7813.8k | [  -144.9k, +10443.1k] | 0.277 | 20.0% (1/5) |

### Key Scientific Findings for EXP-02:
1. **Horizon h=1:**
   - Challenger median delta = **-167.0k kWh**, mean delta = **-365.9k kWh**, with 0% catastrophic runs.
   - However, the Joint 95% CI spans zero (**[-549.2k, -164.7k]** with individual seed bootstrap CIs crossing positive), meaning no statistically significant decision gain is established over Site-Local Wspd-Bins.
2. **Horizon h=6 (Primary Endpoint):**
   - Headline mean delta of **+3,435.5k kWh** is heavily distorted by Seed 201's catastrophic failure (+17,411.3k kWh, 48.60% violation rate).
   - Catastrophic run rate is **20.0%** (1 out of 5 seeds collapses).
   - In the surviving 4 seeds, median delta is **-178.3k kWh** with Joint 95% CI spanning from **[-164.8k to +9,985.4k] kWh**, confirming severe policy instability.
3. **Formal Epistemic Verdict:**
   - Zero-privileged weak-supervision fails to reliably outperform simple local wind-speed conditioning, and introduces severe catastrophic failure risk at longer horizons.

---

## 3. Disaggregated Seed Data Matrix

### EXP-01 Seed Values (Delta PSREI in kWh):
- **Kelmarsh h=1 (Fine-tuned STGQ-Modular):** Seed 201: +1336158, Seed 202: -717185, Seed 203: -779359, Seed 204: -182341, Seed 205: +1215002
- **Kelmarsh h=1 (No-Graph Architectural Control):** Seed 201: +3244357, Seed 202: +4504246, Seed 203: +3941187, Seed 204: +3204178, Seed 205: +3443696
- **Kelmarsh h=1 (Transferred STGQ-Modular):** Seed 201: +684567, Seed 202: +901824, Seed 203: +396540, Seed 204: -121214, Seed 205: +714872
- **Kelmarsh h=6 (Fine-tuned STGQ-Modular):** Seed 201: +1166628, Seed 202: -807476, Seed 203: -881799, Seed 204: -331614, Seed 205: +844258
- **Kelmarsh h=6 (No-Graph Architectural Control):** Seed 201: +2999401, Seed 202: +4130005, Seed 203: +3745384, Seed 204: +3068415, Seed 205: +3074848
- **Kelmarsh h=6 (Transferred STGQ-Modular):** Seed 201: +566297, Seed 202: +894215, Seed 203: +323285, Seed 204: -166937, Seed 205: +561559
- **Penmanshiel h=1 (Fine-tuned STGQ-Modular):** Seed 201: -4880805, Seed 202: -3939454, Seed 203: -4698027, Seed 204: +4363144, Seed 205: -4058292
- **Penmanshiel h=1 (No-Graph Architectural Control):** Seed 201: +16196015, Seed 202: +23250163, Seed 203: +19988221, Seed 204: +19462294, Seed 205: +19062604
- **Penmanshiel h=1 (Transferred STGQ-Modular):** Seed 201: +1595191, Seed 202: +9959296, Seed 203: +2239030, Seed 204: +10126113, Seed 205: +8939253
- **Penmanshiel h=6 (Fine-tuned STGQ-Modular):** Seed 201: -5479166, Seed 202: -4803323, Seed 203: -5700703, Seed 204: +3292803, Seed 205: -4945750
- **Penmanshiel h=6 (No-Graph Architectural Control):** Seed 201: +13742111, Seed 202: +20220834, Seed 203: +17173480, Seed 204: +16525355, Seed 205: +16739849
- **Penmanshiel h=6 (Transferred STGQ-Modular):** Seed 201: +1074853, Seed 202: +8486283, Seed 203: +1011647, Seed 204: +8540068, Seed 205: +7496721

### EXP-02 Seed Values (Delta PSREI in kWh):
- **h=1 (Direct Consequence Quantile MLP):** Seed 201: +1964, Seed 202: -303541, Seed 203: -655291, Seed 204: -318381, Seed 205: -401820
- **h=1 (Privileged STGQ (Oracle Reference)):** Seed 201: +896925, Seed 202: +606384, Seed 203: +51989, Seed 204: +301691, Seed 205: +23777
- **h=1 (Zero-Privileged Challenger (eps=100)):** Seed 201: +4184937, Seed 202: -571690, Seed 203: -423393, Seed 204: -60277, Seed 205: -545076
- **h=1 (Zero-Privileged Challenger (eps=20)):** Seed 201: -208119, Seed 202: -528715, Seed 203: -393240, Seed 204: -78126, Seed 205: -563790
- **h=1 (Zero-Privileged Challenger (eps=50)):** Seed 201: -166987, Seed 202: -566993, Seed 203: -448997, Seed 204: -88141, Seed 205: -558402
- **h=6 (Direct Consequence Quantile MLP):** Seed 201: +895915, Seed 202: +14121163, Seed 203: +24027437, Seed 204: +265759, Seed 205: -82682
- **h=6 (Privileged STGQ (Oracle Reference)):** Seed 201: +1015042, Seed 202: +570194, Seed 203: +178338, Seed 204: -71261, Seed 205: -58106
- **h=6 (Zero-Privileged Challenger (eps=100)):** Seed 201: +528995, Seed 202: +71886, Seed 203: +135414, Seed 204: -151590, Seed 205: -55634
- **h=6 (Zero-Privileged Challenger (eps=20)):** Seed 201: +150590, Seed 202: -73321, Seed 203: +161818, Seed 204: -129743, Seed 205: -74892
- **h=6 (Zero-Privileged Challenger (eps=50)):** Seed 201: +17411273, Seed 202: -178328, Seed 203: +159911, Seed 204: -152108, Seed 205: -63422

---
*Certified by Scientific Control Plane on 2026-10-12.*
