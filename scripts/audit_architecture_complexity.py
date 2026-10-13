"""Architecture and Computational Complexity Audit: STGQ-Modular vs. No-Graph Architectural Control

This script calculates exact parameter counts, layer-wise breakdowns,
and computational characteristics of:
1. STGQ-Modular (RegimeAwareForecaster with Spatio-Temporal Graph WaveNet & Physics-Aligned MoE)
2. No-Graph Architectural Control (NoGraphQuantileMLP)
3. Direct Wind-Speed Bins (Non-parametric empirical quantile lookup)

Generates:
- artifacts/no_graph_architecture_audit.json
- docs/NO_GRAPH_CONTROL_AUDIT.md
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

import numpy as np
import torch
import torch.nn as nn

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from windfarm_moe.config import ModelConfig
from windfarm_moe.model import RegimeAwareForecaster


class NoGraphQuantileMLP(nn.Module):
    """Single-turbine architectural control predicting residual quantile directly.
    
    Severed from spatial graph interactions: each turbine is processed independently.
    Input features: [Wspd, Temp, Patv, Wspd^2, Patv_norm] (5 features, pitch completely withheld).
    """
    def __init__(self, in_features: int = 5, hidden_dim: int = 64):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_features, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Dropout(0.05),
            nn.Linear(hidden_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, 1),
            nn.ReLU(),  # Reserves are strictly non-negative
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x).squeeze(-1)


def count_parameters(model: nn.Module) -> dict:
    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    layer_breakdown = {}
    for name, p in model.named_parameters():
        layer_breakdown[name] = {
            "shape": list(p.shape),
            "numel": p.numel(),
            "requires_grad": p.requires_grad,
        }
    return {
        "total_parameters": total_params,
        "trainable_parameters": trainable_params,
        "layers": layer_breakdown,
    }


def main():
    print("=" * 70)
    print("   ARCHITECTURE & COMPUTATIONAL COMPLEXITY AUDIT")
    print("   STGQ-Modular vs. No-Graph Architectural Control")
    print("=" * 70)

    # 1. Instantiate STGQ-Modular with canonical repository config
    cfg = ModelConfig()
    feature_dim = 11
    pred_len = 24
    stgq_model = RegimeAwareForecaster(
        feature_dim=feature_dim,
        pred_len=pred_len,
        mode="moe_full",
        config=cfg,
    )

    stgq_stats = count_parameters(stgq_model)
    stgq_encoder_params = sum(p.numel() for n, p in stgq_model.named_parameters() if "encoder" in n)
    stgq_gate_params = sum(p.numel() for n, p in stgq_model.named_parameters() if "gate" in n)
    stgq_experts_params = sum(p.numel() for n, p in stgq_model.named_parameters() if "experts" in n)
    stgq_dense_params = sum(p.numel() for n, p in stgq_model.named_parameters() if "dense_head" in n)

    print(f"\n1. STGQ-Modular (Physics-Aligned Spatio-Temporal Graph MoE):")
    print(f"   - Total Parameters: {stgq_stats['total_parameters']:,}")
    print(f"   - Trainable Parameters: {stgq_stats['trainable_parameters']:,}")
    print(f"   - Spatio-Temporal Encoder (Graph WaveNet): {stgq_encoder_params:,} ({stgq_encoder_params/stgq_stats['total_parameters']*100:.1f}%)")
    print(f"   - Regime Router / Gate Head: {stgq_gate_params:,} ({stgq_gate_params/stgq_stats['total_parameters']*100:.1f}%)")
    print(f"   - Regime Expert Heads (4 experts): {stgq_experts_params:,} ({stgq_experts_params/stgq_stats['total_parameters']*100:.1f}%)")
    print(f"   - Dense Head: {stgq_dense_params:,} ({stgq_dense_params/stgq_stats['total_parameters']*100:.1f}%)")

    # 2. Instantiate No-Graph Architectural Control MLP
    nograph_model = NoGraphQuantileMLP(in_features=5, hidden_dim=64)
    nograph_stats = count_parameters(nograph_model)

    print(f"\n2. No-Graph Architectural Control (Single-Turbine MLP):")
    print(f"   - Total Parameters: {nograph_stats['total_parameters']:,}")
    print(f"   - Trainable Parameters: {nograph_stats['trainable_parameters']:,}")
    for name, info in nograph_stats["layers"].items():
        print(f"     * {name:20s}: shape {str(info['shape']):15s} -> {info['numel']:,} params")

    # 3. Direct Wind-Speed Bins
    wspd_bins_params = 10  # 10 scalar quantile values
    print(f"\n3. Site-Local Wspd-Bins (Primary Baseline):")
    print(f"   - Parametric Form: Non-parametric empirical quantile table (10 bins)")
    print(f"   - Parameters: {wspd_bins_params} stored scalar reserve numbers per site-horizon")
    print(f"   - Neural parameters: 0")

    # 4. Comparative Synthesis
    ratio = stgq_stats['total_parameters'] / nograph_stats['total_parameters']
    print(f"\n4. Comparative Structural Synthesis:")
    print(f"   - Parameter Ratio (STGQ / No-Graph): {ratio:.1f}x ({stgq_stats['total_parameters']:,} vs {nograph_stats['total_parameters']:,})")
    print(f"   - Spatial Topology: STGQ incorporates directed graph diffusion & wake interaction; No-Graph is strictly severed.")
    print(f"   - Architectural Terminology Decision: Must be designated 'No-Graph Architectural Control', NOT 'Strict Capacity-Matched'.")

    # Save structured audit artifact
    audit_data = {
        "stgq_modular": {
            "architecture": "RegimeAwareForecaster (Spatio-Temporal Graph WaveNet + Physics-Aligned MoE)",
            "total_parameters": stgq_stats["total_parameters"],
            "trainable_parameters": stgq_stats["trainable_parameters"],
            "component_breakdown": {
                "spatio_temporal_encoder": stgq_encoder_params,
                "regime_gate_router": stgq_gate_params,
                "expert_heads": stgq_experts_params,
                "dense_head": stgq_dense_params,
            },
            "spatial_graph_interaction": True,
            "receptive_field_temporal_steps": 24,
            "training_epochs": 100,
            "batch_size": 32,
        },
        "no_graph_control": {
            "architecture": "NoGraphQuantileMLP (Single-turbine MLP with LayerNorm & GELU)",
            "total_parameters": nograph_stats["total_parameters"],
            "trainable_parameters": nograph_stats["trainable_parameters"],
            "input_features": ["Wspd", "Temp", "Patv", "Wspd^2", "Patv_norm"],
            "spatial_graph_interaction": False,
            "receptive_field_temporal_steps": 1,
            "training_epochs": 10,
            "batch_size": 256,
        },
        "site_local_wspd_bins": {
            "architecture": "Non-parametric 10-bin empirical conditional quantile",
            "total_parameters": 10,
            "trainable_parameters": 0,
            "spatial_graph_interaction": False,
        },
        "designation_ruling": {
            "original_informal_term": "capacity-matched No-Graph MLP",
            "formal_scientific_term": "No-Graph Architectural Control",
            "justification": (
                f"STGQ-Modular comprises {stgq_stats['total_parameters']:,} parameters across graph diffusion "
                f"and mixture-of-experts blocks, whereas the single-turbine MLP contains "
                f"{nograph_stats['total_parameters']:,} parameters "
                f"(a {ratio:.1f}x parameter ratio). "
                "Because the single-turbine MLP was sized to match the capacity of a single-turbine local feedforward block "
                "rather than the full multi-node spatio-temporal graph system, it functions as an architectural lesion control "
                "(severing spatial graph interactions) rather than an identical-capacity or FLOPs-matched model. "
                "The scientific claim ceiling must formally designate it as a No-Graph Architectural Control."
            ),
            "parameter_ratio_stgq_over_nograph": round(ratio, 2),
            "causal_necessity_of_spatial_graph": "UNPROVEN / NOT ESTABLISHED",
        },
    }

    out_json = REPO_ROOT / "artifacts" / "no_graph_architecture_audit.json"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(audit_data, f, indent=2, ensure_ascii=False)
    print(f"\nWritten audit artifact to: {out_json}")

    # Generate Markdown documentation
    doc_path = REPO_ROOT / "docs" / "NO_GRAPH_CONTROL_AUDIT.md"

    # v2 (superseding) No-Graph deltas vs Site-Local Wspd-Bins, read from the frozen
    # corrected-v2 benchmark. v1 magnitudes must never be re-emitted by this generator.
    # The reported magnitude is the 5-seed mean, matching the registry's EXP-01 entry.
    def _nograph_delta(farm: str, horizon: str) -> float:
        import csv as _csv

        vals: list[float] = []
        with (REPO_ROOT / "artifacts" / "external_matched_control_benchmark.csv").open(
            "r", encoding="utf-8-sig", newline=""
        ) as fh:
            for r in _csv.DictReader(fh):
                if (
                    r.get("farm") == farm
                    and r.get("horizon") == horizon
                    and r.get("model") == "No-Graph Architectural Control"
                ):
                    vals.append(float(r["delta_psrei_mean_kwh"]))
        if not vals:
            raise KeyError(f"missing No-Graph rows for {farm} {horizon}")
        return sum(vals) / len(vals)

    def _range_m(farm: str) -> str:
        vals = [_nograph_delta(farm, h) for h in ("h=1", "h=6")]
        return f"+{min(vals)/1e6:.2f}M to +{max(vals)/1e6:.2f}M kWh"

    nograph_pen = _range_m("Penmanshiel")
    nograph_kel = _range_m("Kelmarsh")

    doc_content = f"""# No-Graph Architectural Control: Complexity & Parameter Equivalence Audit

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
2. Sizing a single-turbine network to match the dimension of a local representation vector does not constitute identical farm-level parameter count or FLOPs equivalence with a full multi-turbine Spatio-Temporal Graph WaveNet MoE.

To preserve strict scientific honesty and prevent over-claiming, this audit establishes the exact parameter breakdown, compute profiles, and formal nomenclature.

---

## 2. Parameter and Layer Breakdown

| Model / Baseline | Architecture | Spatial Graph | Total Parameters | Trainable Parameters | FLOPs Scaling per Step |
|---|---|:---:|---:|---:|:---:|
| **STGQ-Modular** | Graph WaveNet + MoE | **Yes** (Diffusion Conv) | **{stgq_stats['total_parameters']:,}** | **{stgq_stats['trainable_parameters']:,}** | $O(N^2 + N \\cdot T \\cdot C)$ |
| **No-Graph Architectural Control** | Multi-Layer Perceptron | **No** (Severed) | **{nograph_stats['total_parameters']:,}** | **{nograph_stats['trainable_parameters']:,}** | $O(N \\cdot C)$ |
| **Site-Local Wspd-Bins** | 10-bin Empirical Quantile | **No** (Direct Table) | **10** | **0** | $O(N \\log K)$ |

### Detailed Layer Breakdown

#### STGQ-Modular Submodules
- **Spatio-Temporal Graph WaveNet Encoder**: {stgq_encoder_params:,} parameters ({stgq_encoder_params/stgq_stats['total_parameters']*100:.1f}%)
  - Directed spatial graph diffusion convolutions, temporal causal dilated GLU layers, residual projections.
- **Physics-Aligned Regime Gate**: {stgq_gate_params:,} parameters ({stgq_gate_params/stgq_stats['total_parameters']*100:.1f}%)
  - Multi-layer routing network mapping concatenated context and physics anchors to operating regime probabilities.
- **Regime Expert Heads**: {stgq_experts_params:,} parameters ({stgq_experts_params/stgq_stats['total_parameters']*100:.1f}%)
  - 4 specialized linear projection modules for regime-specific point/interval estimation.
- **Dense Head**: {stgq_dense_params:,} parameters ({stgq_dense_params/stgq_stats['total_parameters']*100:.1f}%)

#### No-Graph Architectural Control Layers
- `Linear(5, 64)` + `LayerNorm(64)`: 384 + 128 = 512 parameters
- `Linear(64, 64)` + `LayerNorm(64)`: 4,160 + 128 = 4,288 parameters
- `Linear(64, 1)` + `ReLU`: 65 parameters
- **Total**: {nograph_stats['total_parameters']:,} parameters

---

## 3. Formal Scientific Ruling on Nomenclature

1. **Mandatory Formal Name:** **No-Graph Architectural Control**  
   The baseline must be described as an *architectural control* that severs inter-turbine spatial graph connectivity and isolates single-turbine SCADA feature processing.
2. **Forbidden Phrasing:**
   - *“Strictly capacity-matched MLP”* (Prohibited: STGQ has ~{ratio:.0f}x more parameters).
   - *“Compute-equivalent control”* (Prohibited: STGQ requires spatial graph convolution over $N$ turbines).
3. **Scientific Value of the Baseline (corrected v2 magnitudes):**
   On the corrected v2 protocol, the No-Graph Architectural Control incurs a PSREI cost penalty versus the
   non-parametric **Site-Local Wspd-Bins** of approximately {nograph_pen} on Penmanshiel and
   {nograph_kel} on Kelmarsh (per-site $h=1$/$h=6$ range). This supports only the following bounded statement:
   - Increasing neural parametrization without spatio-temporal structure does not by itself restore
     competitive calibration relative to a simple local empirical quantile table.
   - The non-parametric empirical quantile table is a **minimum-sufficient decision model** under
     deployment-time pitch withholding.

---

## 4. Causal Necessity Boundary: UNPROVEN / NOT ESTABLISHED

A critical finding from the 2026-10-12 Scientific Audit is that the performance deficit of the No-Graph Architectural Control relative to STGQ-Modular cannot be causally attributed to the absence of the spatial graph alone:

1. **Confounded Asymmetries:**
   - **Parameter Asymmetry:** The No-Graph MLP has {nograph_stats['total_parameters']:,} parameters, whereas STGQ-Modular has {stgq_stats['total_parameters']:,} parameters (a {ratio:.1f}x capacity difference).
   - **Training Protocol Asymmetry:** In `scripts/run_exp01_matched_control_benchmark.py`, the No-Graph MLP was trained solely on the target farm's validation split (with an internal 70/30 split), whereas STGQ-Modular received full source-domain pretraining across 134 turbines followed by transfer/fine-tuning.
   - **Architectural Modality:** Single-turbine feedforward vs. multi-turbine spatio-temporal convolutions.
2. **Authoritative Claim Ceiling:**
   - **UNPROVEN / NOT ESTABLISHED:** It **MUST NOT BE CLAIMED** that *"external spatial graph structure is causally necessary for downstream reserve decision quality"* or that *"spatial graph convolution is the causal mechanism preventing catastrophic shortfall"*.
   - **Supported Claim:** Increasing neural parametrization via an isolated single-turbine MLP trained on local validation data fails to achieve competitive calibration and is decisively outperformed by the non-parametric **Site-Local Wspd-Bins** baseline.
   - **Status in Scientific Contract:** Formally locked as `UNPROVEN / NOT ESTABLISHED`.
"""
    with open(doc_path, "w", encoding="utf-8") as f:
        f.write(doc_content)
    print(f"Written audit documentation to: {doc_path}")


if __name__ == "__main__":
    main()
