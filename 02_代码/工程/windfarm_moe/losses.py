from __future__ import annotations

import torch
import torch.nn.functional as F


def masked_mse_loss(pred: torch.Tensor, target: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
    weight = mask.float()
    safe_pred = torch.nan_to_num(pred)
    safe_target = torch.nan_to_num(target)
    denom = weight.sum().clamp_min(1.0)
    return (((safe_pred - safe_target) ** 2) * weight).sum() / denom


def masked_mae(pred: torch.Tensor, target: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
    weight = mask.float()
    safe_pred = torch.nan_to_num(pred)
    safe_target = torch.nan_to_num(target)
    denom = weight.sum().clamp_min(1.0)
    return ((safe_pred - safe_target).abs() * weight).sum() / denom


def alignment_loss(
    gate_logits: torch.Tensor,
    regime_anchor: torch.Tensor,
    valid_mask: torch.Tensor,
    class_weights: torch.Tensor,
    num_classes: int,
) -> torch.Tensor:
    logits = gate_logits[..., :num_classes].reshape(-1, num_classes)
    targets = regime_anchor.reshape(-1)
    valid = valid_mask.reshape(-1) > 0.0
    if not torch.any(valid):
        return logits.sum() * 0.0
    return F.cross_entropy(logits[valid], targets[valid], weight=class_weights)


def auxiliary_bce_loss(
    logits: torch.Tensor,
    targets: torch.Tensor,
    valid_mask: torch.Tensor,
    pos_weight: torch.Tensor | None = None,
) -> torch.Tensor:
    valid = valid_mask.reshape(-1) > 0.0
    if not torch.any(valid):
        return logits.sum() * 0.0
    flat_logits = logits.reshape(-1)[valid]
    flat_targets = targets.reshape(-1).float()[valid]
    return F.binary_cross_entropy_with_logits(flat_logits, flat_targets, pos_weight=pos_weight)


def physics_force_loss(
    gate_logits: torch.Tensor,
    regime_anchor: torch.Tensor,
    valid_mask: torch.Tensor,
    mppt_expert_index: int = 1,
    pitch_expert_index: int = 2,
    class_weights: torch.Tensor | None = None,
) -> torch.Tensor:
    # Only supervise the physically meaningful MPPT <-> pitch switch.
    valid = (valid_mask > 0.0) & ((regime_anchor == 1) | (regime_anchor == 2))
    if not torch.any(valid):
        return gate_logits.sum() * 0.0
    paired_logits = torch.stack(
        [
            gate_logits[..., mppt_expert_index],
            gate_logits[..., pitch_expert_index],
        ],
        dim=-1,
    )
    binary_targets = (regime_anchor == 2).long()
    flat_logits = paired_logits.reshape(-1, 2)
    flat_targets = binary_targets.reshape(-1)
    flat_valid = valid.reshape(-1)
    return F.cross_entropy(flat_logits[flat_valid], flat_targets[flat_valid], weight=class_weights)


def gate_smoothness_loss(
    gate_prob: torch.Tensor,
    edge_index: torch.Tensor,
    edge_weight: torch.Tensor,
) -> torch.Tensor:
    valid = edge_index >= 0
    src = edge_index.clamp_min(0)
    batch_idx = torch.arange(gate_prob.size(0), device=gate_prob.device).view(-1, 1, 1)
    src_gate = gate_prob[batch_idx, src]
    target_gate = gate_prob.unsqueeze(2).expand_as(src_gate)
    diff_sq = ((target_gate - src_gate) ** 2).sum(dim=-1)
    weighted = diff_sq * edge_weight * valid.float()
    denom = (edge_weight * valid.float()).sum().clamp_min(1.0)
    return weighted.sum() / denom


def moe_load_balancing_loss(
    gate_prob: torch.Tensor,
    top_k: int = 1,
    sample_mask: torch.Tensor | None = None,
) -> torch.Tensor:
    if gate_prob.numel() == 0:
        return gate_prob.sum() * 0.0

    num_experts = gate_prob.shape[-1]
    flat_gate = gate_prob.reshape(-1, num_experts)
    if sample_mask is not None:
        valid = sample_mask.reshape(-1) > 0.0
        if not torch.any(valid):
            return flat_gate.sum() * 0.0
        flat_gate = flat_gate[valid]

    importance = flat_gate.mean(dim=0).clamp_min(1e-8)
    importance = importance / importance.sum()

    top_k = max(1, min(int(top_k), num_experts))
    top_indices = torch.topk(flat_gate, k=top_k, dim=-1).indices
    load = flat_gate.new_zeros((flat_gate.shape[0], num_experts))
    load.scatter_(1, top_indices, 1.0 / top_k)
    load = load.mean(dim=0)
    return num_experts * torch.sum(load * importance) - 1.0
