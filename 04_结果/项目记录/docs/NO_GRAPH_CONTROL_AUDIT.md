> 2026-10-15 correction: encoder names below were checked against runtime construction. Performance numbers from historical EXP01 v2 are not reinstated as current matched evidence; v4 is separately INVALID (see EXP01_INVALIDATION_20261015.md). Nominal parameter counts do not prove equal training, active-parameter count, FLOPs or graph causality.

# No-Graph Architectural Control: Complexity & Parameter Equivalence Audit

**Audit Status:** AUTHORITATIVE AUDIT & TERMINOLOGY RULING  
**Effective Date:** 2026-10-11 (parameter breakdown) / 2026-10-13 (claim-ceiling and v2-magnitude revision)  
**Associated Experiment:** EXP-01 corrected v2 (`artifacts/external_matched_control_benchmark.csv`)  
**Computing Environment:** NVIDIA A100-PCIE-40GB (Metis Cloud Node) & Local Verification  

> **Revision notice.** The parameter breakdown and nomenclature ruling below date from 2026-10-11 and remain in force.
> The performance magnitudes and the causal-necessity ceiling were revised on 2026-10-13 after EXP-01 was
> corrected to v2. The 2026-10-11 draft quoted v1 magnitudes (+1,050k to +2,154k kWh on Penmanshiel,
> +888k to +1,501k kWh on Kelmarsh); those belong to the superseded v1 protocol, in which shortfall was
> derived from the transferred challenger's own prediction. They MUST NOT be cited. See
> `docs/EXPERIMENT_REGISTRY.md` (EXP-01) and `docs/F6_CONTROL_PLANE_REPOLLUTION_AUDIT.md`.

---

## 1. Rationale and Background

In earlier exploratory drafts, the single-turbine MLP baseline was informally labeled as a *“capacity-matched No-Graph MLP”*. 
A rigorous scientific review identified that:
1. No parameter count, training iteration, or compute equivalence table was formally recorded in the evidence ledger.
2. Sizing a single-turbine network to match the dimension of a local representation vector does not constitute identical farm-level parameter count or FLOPs equivalence with a full multi-turbine Directed-Diffusion GRU MoE.

To preserve strict scientific honesty and prevent over-claiming, this audit establishes the exact parameter breakdown, compute profiles, and formal nomenclature.

---

## 2. Parameter and Layer Breakdown

| Model / Baseline | Architecture | Spatial Graph | Total Parameters | Trainable Parameters | FLOPs Scaling per Step |
|---|---|:---:|---:|---:|:---:|
| **STGQ-Modular** | Directed-Diffusion GRU + MoE | **Yes** (Diffusion Conv) | **110,012** | **110,012** | $O(N^2 + N \cdot T \cdot C)$ |
| **No-Graph Architectural Control** | Multi-Layer Perceptron | **No** (Severed) | **4,865** | **4,865** | $O(N \cdot C)$ |
| **Site-Local Wspd-Bins** | 10-bin Empirical Quantile | **No** (Direct Table) | **10** | **0** | $O(N \log K)$ |

### Detailed Layer Breakdown

#### STGQ-Modular Submodules
- **Directed-Diffusion GRU Encoder**: 76,736 parameters (69.8%)
  - Two directed-diffusion spatial blocks, a two-layer temporal GRU, and layer normalization.
- **Physics-Aligned Regime Gate**: 4,676 parameters (4.3%)
  - Multi-layer routing network mapping concatenated context and physics anchors to operating regime probabilities.
- **Regime Expert Heads**: 22,880 parameters (20.8%)
  - 4 specialized linear projection modules for regime-specific point/interval estimation.
- **Dense Head**: 5,720 parameters (5.2%)

#### No-Graph Architectural Control Layers
- `Linear(5, 64)` + `LayerNorm(64)`: 384 + 128 = 512 parameters
- `Linear(64, 64)` + `LayerNorm(64)`: 4,160 + 128 = 4,288 parameters
- `Linear(64, 1)` + `ReLU`: 65 parameters
- **Total**: 4,865 parameters

---

## 3. Formal Scientific Ruling on Nomenclature

1. **Mandatory Formal Name:** **No-Graph Architectural Control**  
   The baseline must be described as an *architectural control* that severs inter-turbine spatial graph connectivity and isolates single-turbine SCADA feature processing.
2. **Forbidden Phrasing:**
   - *“Strictly capacity-matched MLP”* (Prohibited: STGQ has ~23x more parameters).
   - *“Compute-equivalent control”* (Prohibited: STGQ requires spatial graph convolution over $N$ turbines).
3. **Scientific Value of the Baseline (corrected v2 magnitudes):**
   On the corrected v2 protocol, the No-Graph Architectural Control incurs a PSREI cost penalty versus the
   non-parametric **Site-Local Wspd-Bins** of approximately +16.88M to +19.59M kWh on Penmanshiel and
   +3.40M to +3.67M kWh on Kelmarsh (per-site $h=1$/$h=6$ range). This supports only the following bounded statement:
   - Increasing neural parametrization without spatio-temporal structure does not by itself restore
     competitive calibration relative to a simple local empirical quantile table.
   - The non-parametric empirical quantile table is a **minimum-sufficient decision model** under
     deployment-time pitch withholding.

---

## 4. Causal Necessity Boundary: UNPROVEN / NOT ESTABLISHED

A critical finding from the 2026-10-12 Scientific Audit is that the performance deficit of the No-Graph Architectural Control relative to STGQ-Modular cannot be causally attributed to the absence of the spatial graph alone:

1. **Confounded Asymmetries:**
   - **Parameter Asymmetry:** The No-Graph MLP has 4,865 parameters, whereas STGQ-Modular has 110,012 parameters (a 22.6x capacity difference).
   - **Training Protocol Asymmetry:** In `scripts/run_exp01_matched_control_benchmark.py`, the No-Graph MLP was trained solely on the target farm's validation split (with an internal 70/30 split), whereas STGQ-Modular received full source-domain pretraining across 134 turbines followed by transfer/fine-tuning.
   - **Architectural Modality:** Single-turbine feedforward vs. multi-turbine spatio-temporal convolutions.
2. **Authoritative Claim Ceiling:**
   - **UNPROVEN / NOT ESTABLISHED:** It **MUST NOT BE CLAIMED** that *"external spatial graph structure is causally necessary for downstream reserve decision quality"* or that *"spatial graph convolution is the causal mechanism preventing catastrophic shortfall"*.
   - **Supported Claim:** Increasing neural parametrization via an isolated single-turbine MLP trained on local validation data fails to achieve competitive calibration and is decisively outperformed by the non-parametric **Site-Local Wspd-Bins** baseline.
   - **Status in Scientific Contract:** Formally locked as `UNPROVEN / NOT ESTABLISHED`.
