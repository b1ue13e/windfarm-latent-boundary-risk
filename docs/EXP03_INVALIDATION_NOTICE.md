# EXP-03 Invalidation Notice (2026-10-12)

**Status:** INVALID / MUST NOT BE CITED  
**Effective Date:** 2026-10-12T23:59:00+08:00  
**Registry Entry:** `docs/EXPERIMENT_REGISTRY.md:397-450`  
**Original Artifacts:** `artifacts/exp03_async/` (PRESERVED but marked invalid)  
**Superseding Protocol:** EXP-03-R (not yet executed; see below)

---

## Reconciliation Addendum (2026-10-13, F6)

> **This notice remains a historical provenance record of the 2026-10-12 invalidation. It is superseded
> in part, and the reader must not treat it as a current statement of EXP-03's status.**
>
> `docs/EXPERIMENT_REGISTRY.md` (EXP-03) now records the **EXP-03-R hardened reconciled rerun** as
> CONCLUDED. The rerun artifact `artifacts/exp03_async/psrei_vs_delay.csv` was written in commit
> `f583c572` and did not exist at the time this notice was authored. Per-defect current state:
>
> | Defect | 2026-10-12 notice | Current state (2026-10-13) |
> |---|---|---|
> | **F3.1** Information asymmetry | `Patv` delayed, actual cache feature `Patv_hist` read fresh | **FIXED** — `(Patv_hist, Patv)` alias resolution delays all 5 consumed channels symmetrically (`run_exp03_async_benchmark.py:164-183`) |
> | **F3.2** Proxy label collapse | 0 positives; thresholds on standardized features | **FIXED** — physical thresholds applied after unstandardizing via `metadata.json.feature_stats` (`:67-88`) |
> | **F3.3** Population collapse | 100% → 2.47% at $\tau=6$ | **CHANGED, NOT ELIMINATED** — evaluated cells now constant at 408,937/408,939 via causal LOCF, but LOCF *imputes* values: `drop_fraction` still reaches **60.25%** and `stale_fraction` **99.79%** at $\tau=6$. The curve is now locally non-collapsing but late-delay points measure near-total staleness. |
> | **F3.4** Incomplete provenance | trace `d1619e…` covers node 0 / first 144 steps / $\tau=0$ | **NOT FIXED — RE-LABELLED.** The new digest `18079b46…` is likewise an internal accumulator over node 0 / first 144 steps (`:498,515-516,597`), not a hash of the archived trace, and is not recomputable from any artifact. `arrival_trace.jsonl` still contains zero delayed packets; `missing_mask.json` is now an all-`false` placeholder. Full-grid packet provenance remains OUTSTANDING. |
>
> **Consequence:** F3.1 and F3.2 were genuinely repaired. F3.3 was mitigated, not eliminated. F3.4 was
> **re-badged rather than fixed**, and the earlier claim that it was "Resolved" was inaccurate — corrected
> in `docs/EXPERIMENT_REGISTRY.md` (EXP-03, F4) and `docs/EXP03_ASYNCHRONOUS_REPORT.md`. No manuscript
> claim should rest on EXP-03 packet-level provenance.

---

## Executive Summary

EXP-03 (Integer-Step Asynchronous Packet Arrival Envelope Benchmark) is **scientifically invalid** and must not be cited or used in manuscript claims. While the experiment was executed in good faith with preregistration and extensive protocol documentation, post-execution forensic audit revealed four critical defects that jointly render the current results uninterpretable:

1. **Information Asymmetry:** The causal packet simulator delayed `Wspd, Patv, Etmp, Itmp, Prtv`, but the actual cache feature is `Patv_hist`. The challenger read **fresh active power** (the established dominant mediator), while the baseline only read delayed `Wspd`.
2. **Proxy Label Collapse:** Physical thresholds ($v_{\text{rated}}=10.5$ m/s, $P_{\text{rated}}-\epsilon=1450$ kW) were applied to **standardized features** (ranges ≈[-1.55, 4.96] and [-0.91, 2.84]), yielding **zero positives** across 570,974 validation samples.
3. **Population Collapse:** Effective coverage fell from 100% at $\tau=0$ to 2.47% at $\tau=6$ due to causal buffer missingness directly entering `mask_test_h`. Baseline total PSREI collapsed from ≈14.80M to 0.37M kWh. The curve does not represent a fixed-population latency response.
4. **Incomplete Provenance:** The archived `arrival_trace.jsonl` (SHA256 `d1619e...`) covers only node 0, first 144 steps, $\tau=0$; `missing_mask.json` is a `t % 5 != 0` placeholder. The 70-row full grid (7 delays × 5 seeds × 2 horizons) lacks verifiable packet-level audit.

These defects are **not parameter choices or judgment calls**—they are protocol violations that invalidate the comparison. The experiment must be **withdrawn** and replaced with a corrected protocol (EXP-03-R).

---

## Detailed Findings

### F3.1 — Information Asymmetry (VERIFIED)

**Finding:** `simulate_asynchronous_scada_stream()` (lines 121-179) declares channels:
```python
channels = ["Wspd", "Patv", "Etmp", "Itmp", "Prtv"]
```
and delays them according to the Poisson+jitter arrival model. However, the WTB cache uses `Patv_hist` (not `Patv`). The main script correctly resolves to `Patv_hist` when constructing model inputs (line 310), but the simulator does **not** apply delays to `Patv_hist`. Consequently:

- **Challenger models** read contemporaneous `Patv_hist` (fresh active power).
- **Baseline (Site-Local Wspd-Bins)** only reads delayed `Wspd`.

Since active power is the established dominant mediator (C2 Active-Power-Only: NMI 0.461, transition recall 62.9%), this is not a minor feature-engineering difference—it is a **core comparator information-set violation**.

**Evidence:**
- `scripts/run_exp03_async_benchmark.py:132-145` (channel list and delay application)
- `scripts/run_exp03_async_benchmark.py:310,340-348` (model input construction uses `Patv_hist`)
- `artifacts/cache_strictmask_trainweights/wtb_245d/metadata.json` (feature names confirm `Patv_hist`)

**Consequence:** The primary estimand $\Delta\text{PSREI}(\tau)$ is **undefined under same-information rules**. The challenger had a systematic information advantage.

---

### F3.2 — Proxy Label Collapse (VERIFIED)

**Finding:** The zero-privileged proxy label $\tilde{Z}_t = \mathbb{I}(v_t > v_{\text{rated}} \land P_{\text{atv}, t} < P_{\text{rated}} - \epsilon)$ is computed on **standardized features** (line 371):

```python
z_proxy = (wspd_val_raw[valid_val] > V_RATED) & (val_inputs[..., patv_idx][valid_val] < P_RATED - EPSILON)
```

where `V_RATED = 10.5` and `P_RATED - EPSILON = 1450.0`. However, the cache standardizes features using global mean/std:

- `Wspd` standardized range: ≈[-1.55, 4.96] (physical range 0-25 m/s)
- `Patv_hist` standardized range: ≈[-0.91, 2.84] (physical range 0-1650 kW)

Therefore, the condition `wspd_val_raw > 10.5` is **never true**, and `val_inputs[..., patv_idx] < 1450.0` is **always true**. Read-only recomputation confirms **0 positives** across 570,974 validation samples. The proxy head trained to classify a degenerate all-zero target, which is not equivalent to EXP-02's intentional zero-privileged protocol.

**Evidence:**
- `scripts/run_exp03_async_benchmark.py:335-371`
- `artifacts/cache_strictmask_trainweights/wtb_245d/metadata.json` (feature_stats)
- Read-only computation: `np.sum(z_proxy) = 0`

**Consequence:** The "Zero-Privileged Challenger" identity is mislabeled. The model trained a trivial constant classifier, not a weak-supervision regime proxy.

---

### F3.3 — Population Collapse (VERIFIED)

**Finding:** The causal buffer drops late packets and marks them as missing (`valid_mask[t, n] = False`). This `async_mask` directly enters the decision metric mask:

```python
mask_test_h = (m_test[:, h_idx, :] > 0.5) & test_async_valid
```

As latency increases, more packets are dropped, shrinking the effective population. Read-only recomputation of valid fractions:

| τ | Valid Fraction | h=6 Baseline PSREI (kWh) |
|---|---:|---:|
| 0 | 100.00% | 14,482,310 |
| 1 | 99.98% | 14,501,709 |
| 2 | 98.12% | 14,263,174 |
| 3 | 81.35% | 11,837,455 |
| 4 | 43.44% | 6,330,555 |
| 5 | 13.26% | 1,947,355 |
| 6 | 2.47% | 361,924 |

The PSREI curve is driven by **sample deletion**, not by a latency-conditional distribution shift on a fixed population. The primary estimand requires either:
- Fixed dispatch anchors (coverage-invariant population), or
- Explicit per-cell PSREI and transparent drop-fraction reporting.

Neither was implemented.

**Evidence:**
- `scripts/run_exp03_async_benchmark.py:402-445` (mask construction and metric computation)
- `artifacts/exp03_async/psrei_vs_delay.csv` (PSREI collapse visible across all seeds)
- Read-only computation of `np.mean(test_async_valid, axis=(0,1))` per delay level

**Consequence:** The reported $\Delta\text{PSREI}(\tau)$ curve **cannot be interpreted as a causal latency effect**. It confounds dropout with decision quality.

---

### F3.4 — Incomplete Provenance (VERIFIED)

**Finding:** The packet trace and missing mask artifacts do not represent the executed grid:

1. **Trace Sampling (lines 413-414):**
   ```python
   if len(saved_packets) == 0:
       saved_packets = packets
   ```
   `packets` comes from `simulate_asynchronous_scada_stream()` (lines 148-157), which only saves **node 0, first 144 steps** for audit. The condition `if len(saved_packets) == 0` ensures only the **first delay level** ($\tau=0$) is materialized.

2. **Missing Mask Placeholder (lines 489-493):**
   ```python
   mask_sample = [
       {"step": int(t), "channel": "Wspd", "received": bool(t % 5 != 0)}
       for t in range(min(48, len(rel_anchors_test)))
   ]
   ```
   This is a hand-coded `t % 5` pattern, not the actual `async_mask` used in evaluation.

3. **Trace Hash (lines 474-486):**
   The SHA256 digest `d1619efce7f02412d826e3811bfa2a2346e6bc1b1fcd2b02a9d10f163f0736ff` covers only the `τ=0` sample, not the full 70-configuration grid.

**Evidence:**
- `scripts/run_exp03_async_benchmark.py:135-177,402-445,474-493`
- `artifacts/exp03_async/arrival_trace.jsonl` (144 packets, node 0 only)
- `artifacts/exp03_async/missing_mask.json` (48 placeholder entries)

**Consequence:** **Trace integrity claims in the registry are false**. The experiment cannot be independently verified at packet level.

---

## Scientific Impact

| Claim / Inference | Status |
|---|---|
| "Complex representations provide no hedge against telemetry latency" | **INVALID** — information asymmetry |
| "Site-Local Wspd-Bins maintains superior violation control" | **INVALID** — confounded by population collapse |
| "$\tau^* = 1$ (h=1) or $\tau^* = 0$ (h=6)" | **INVALID** — curve is not interpretable |
| "Synthetic asynchronous envelope" | **VALID LABEL** — correctly labeled as synthetic, but underlying comparison is broken |

**No manuscript claim may cite EXP-03 current results.** All references to asynchronous decision robustness, $\tau^*$, or operating-target sensitivity under latency must be removed or marked UNKNOWN pending EXP-03-R.

---

## Corrective Protocol: EXP-03-R (Not Yet Executed)

A valid replacement experiment (EXP-03-R) must satisfy:

### Hard Requirements

**Implementation status (2026-10-13):** The F2 code defect is fixed in `scripts/run_exp03_async_benchmark.py`: proxy construction now reads `feature_stats` from `metadata.json`, converts `Wspd` and `Patv_hist` back to physical units, and hard-fails on degenerate labels. Regression coverage is in `tests/test_exp03_async_arrival.py`. This fixes the implementation defect only; the historical EXP-03 artifacts remain invalid and EXP-03-R has not been executed.

1. **Strict Information Parity:**
   - Identify all features actually used by both baseline and challenger.
   - Delay **every channel** in that set, including `Patv_hist` (or whatever active-power proxy is used).
   - Verify zero fresh-feature leakage with hard assertions.

2. **Physical Proxy Labels:**
   - Either unnormalize features before thresholding, or redefine thresholds in standardized space.
   - Verify proxy positives $> 0$ before training.
   - Report proxy reconstruction metrics separately from decision metrics.

3. **Fixed Population or Transparent Dropout:**
   - **Option A (Fixed Anchors):** Define dispatch decision times $t_1, \ldots, t_M$ beforehand; evaluate only at those times regardless of packet arrivals. Missing data becomes model input uncertainty, not population dropout.
   - **Option B (Transparent Dropout):** Report per-delay:
     - Valid fraction $f(\tau)$
     - Total PSREI (scales with $f$)
     - Per-cell PSREI (does not scale with $f$)
     - Drop/late fractions by channel
   - The primary estimand must explicitly state which denominator it uses.

4. **Complete Provenance:**
   - Materialize the **full packet trace** for at least one (delay, seed, horizon) configuration.
   - Save the **actual `async_mask`** used in evaluation (not a placeholder).
   - Compute and report the trace hash **per configuration** or at least per delay level.
   - Include packet-level unit tests that verify causal ordering, late drops, and no-backfill semantics.

### Acceptance Criteria

- ✅ `pytest tests/test_exp03r_protocol.py` passes with **coverage of runner-level features** (not just toy isolated functions).
- ✅ Baseline and challenger PSREI are computed on **the same valid cells** (mask parity).
- ✅ Archived `arrival_trace_full.jsonl` covers at least 10,000 packets across multiple nodes/steps/channels.
- ✅ `missing_mask_actual.json` matches the evaluation mask (random sample spot-check passes).
- ✅ Primary estimand is defined with explicit population/denominator and remains interpretable under dropout.

### Falsification Guardrail (Preserved from EXP-03)

If corrected EXP-03-R shows that the challenger **still fails to beat Site-Local Wspd-Bins** under fixed population and true same-information comparison, the scientific conclusion is:

> **"Under strict information parity and causal packet arrival, learned representations provide no statistically significant decision buffer against telemetry latency relative to simple local conditioning."**

This is a **valid negative result** and must be preserved. The defect is not in the null outcome—it is in the protocol execution that made the current outcome uninterpretable.

---

## Procedural Recommendations

1. **Do NOT rerun EXP-03 under the current script.** Archive `scripts/run_exp03_async_benchmark.py` and `artifacts/exp03_async/` as historical evidence of the defect.

2. **Create a new Experiment ID: EXP-03-R** (or EXP-Q2-004). Do not overwrite EXP-03's registry entry—preserve it as a cautionary record.

3. **Do NOT update `docs/SCIENTIFIC_CONTRACT.md` based on EXP-03 results.** The contract's current silence on asynchronous robustness is correct.

4. **Update `docs/EXPERIMENT_REGISTRY.md`** to mark EXP-03 as INVALID with a pointer to this notice.

5. **Remove all EXP-03 references from the manuscript** (if any exist). If latency robustness is a claimed contribution, downgrade it to UNKNOWN pending EXP-03-R.

6. **Independent falsification and review** of EXP-03-R must occur **before** any manuscript integration.

---

## Audit Trail

- **Discovery Date:** 2026-10-12 (Reverse Scientific Audit RA00-RA06)
- **Audit Lead:** Repository adversarial audit protocol
- **Independent Verification:** Scientific-falsifier (`.agent_state/FALSIFICATION_REPORT.md`, 2026-10-12T23:30:00+08:00)
- **Evidence Ledger:** `.agent_state/EVIDENCE_LEDGER.md:1123-1156` (T96-T98)
- **Invalidation Approved By:** Read-only audit; no result files modified
- **Superseding Protocol Status:** Not yet executed; frozen as requirement specification

---

## Acknowledgments

This invalidation was discovered through systematic forensic audit and read-only code/artifact inspection. The original experiment was executed in good faith with extensive preregistration and documentation. The defect lies in protocol implementation, not in scientific intent. Honest negative results and protocol corrections are core to the project's integrity contract.

---

**FINAL VERDICT:** EXP-03 is **INVALID** and must not be cited. A corrective experiment (EXP-03-R) is required before any claim about asynchronous telemetry robustness can be scientifically supported.
