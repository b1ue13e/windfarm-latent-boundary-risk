# No-Graph Architectural Control: Complexity & Parameter Equivalence Audit

**Audit Status:** AUTHORITATIVE AUDIT & TERMINOLOGY RULING  
**Effective Date:** 2026-10-11  
**Associated Experiment:** EXP-01 (`artifacts/external_matched_control_benchmark.csv`)  
**Computing Environment:** NVIDIA A100-PCIE-40GB (Metis Cloud Node) & Local Verification  

---

## 1. Rationale and Background

In earlier exploratory drafts, the single-turbine MLP baseline was informally labeled as a *“capacity-matched No-Graph MLP”*. 
A rigorous scientific review identified that:
1. No parameter count, training iteration, or compute equivalence table was formally recorded in the evidence ledger.
2. Sizing a single-turbine network to match the dimension of a local representation vector does not constitute identical farm-level parameter count or FLOPs equivalence with a full multi-turbine Spatio-Temporal Graph WaveNet MoE.

To preserve strict scientific honesty and prevent over-claiming, this audit establishes the exact parameter breakdown, compute profiles, and formal nomenclature.

---

## 2. Parameter and Layer Breakdown

| Model / Baseline | Architecture | Spatial Graph | Total Parameters | Trainable Parameters | FLOPs Scaling per Step |
|---|---|:---:|---:|---:|:---:|
| **STGQ-Modular** | Graph WaveNet + MoE | **Yes** (Diffusion Conv) | **110,012** | **110,012** | $O(N^2 + N \cdot T \cdot C)$ |
| **No-Graph Architectural Control** | Multi-Layer Perceptron | **No** (Severed) | **4,865** | **4,865** | $O(N \cdot C)$ |
| **Site-Local Wspd-Bins** | 10-bin Empirical Quantile | **No** (Direct Table) | **10** | **0** | $O(N \log K)$ |

### Detailed Layer Breakdown

#### STGQ-Modular Submodules
- **Spatio-Temporal Graph WaveNet Encoder**: 76,736 parameters (69.8%)
  - Directed spatial graph diffusion convolutions, temporal causal dilated GLU layers, residual projections.
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
