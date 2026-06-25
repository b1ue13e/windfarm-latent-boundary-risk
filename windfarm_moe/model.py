from __future__ import annotations

from contextlib import nullcontext
import math

import torch
import torch.nn as nn
import torch.nn.functional as F

from .config import ModelConfig


def directed_neighbor_aggregations(
    x: torch.Tensor,
    edge_index: torch.Tensor,
    edge_weight: torch.Tensor,
) -> tuple[torch.Tensor, torch.Tensor]:
    batch_size, _, channels = x.shape
    _, _, max_edges = edge_index.shape
    edge_weight = edge_weight.to(dtype=x.dtype)
    valid = edge_index >= 0
    src = edge_index.clamp_min(0)
    batch_idx = torch.arange(batch_size, device=x.device).view(batch_size, 1, 1)
    gathered = x[batch_idx, src]
    weighted = gathered * edge_weight.unsqueeze(-1) * valid.unsqueeze(-1)
    incoming = weighted.sum(dim=2)

    outgoing = x.new_zeros(x.shape)
    target_feat = x.unsqueeze(2).expand(-1, -1, max_edges, -1)
    contrib = target_feat * edge_weight.unsqueeze(-1) * valid.unsqueeze(-1)
    scatter_index = src.unsqueeze(-1).expand(-1, -1, -1, channels).reshape(batch_size, -1, channels)
    outgoing.scatter_add_(1, scatter_index, contrib.reshape(batch_size, -1, channels))
    return incoming, outgoing


class DirectedDiffusionBlock(nn.Module):
    def __init__(self, input_dim: int, output_dim: int, dropout: float) -> None:
        super().__init__()
        self.self_proj = nn.Linear(input_dim, output_dim)
        self.in_proj = nn.Linear(input_dim, output_dim)
        self.out_proj = nn.Linear(input_dim, output_dim)
        self.dropout = nn.Dropout(dropout)
        self.norm = nn.LayerNorm(output_dim)
        self.residual = nn.Linear(input_dim, output_dim) if input_dim != output_dim else nn.Identity()

    def forward(self, x: torch.Tensor, edge_index: torch.Tensor, edge_weight: torch.Tensor) -> torch.Tensor:
        incoming, outgoing = directed_neighbor_aggregations(x, edge_index, edge_weight)
        update = self.self_proj(x) + self.in_proj(incoming) + self.out_proj(outgoing)
        update = self.dropout(F.gelu(update))
        return self.norm(update + self.residual(x))


class DiffusionGraphConv(nn.Module):
    def __init__(self, input_dim: int, output_dim: int) -> None:
        super().__init__()
        self.self_proj = nn.Linear(input_dim, output_dim)
        self.in_proj = nn.Linear(input_dim, output_dim)
        self.out_proj = nn.Linear(input_dim, output_dim)

    def forward(self, x: torch.Tensor, edge_index: torch.Tensor, edge_weight: torch.Tensor) -> torch.Tensor:
        incoming, outgoing = directed_neighbor_aggregations(x, edge_index, edge_weight)
        return self.self_proj(x) + self.in_proj(incoming) + self.out_proj(outgoing)


class GraphAttentionBlock(nn.Module):
    def __init__(self, input_dim: int, output_dim: int, dropout: float) -> None:
        super().__init__()
        self.query = nn.Linear(input_dim, output_dim, bias=False)
        self.key = nn.Linear(input_dim, output_dim, bias=False)
        self.value = nn.Linear(input_dim, output_dim, bias=False)
        self.self_proj = nn.Linear(input_dim, output_dim)
        self.dropout = nn.Dropout(dropout)
        self.norm = nn.LayerNorm(output_dim)
        self.residual = nn.Linear(input_dim, output_dim) if input_dim != output_dim else nn.Identity()

    def forward(self, x: torch.Tensor, edge_index: torch.Tensor, edge_weight: torch.Tensor) -> torch.Tensor:
        batch_size, _, _ = x.shape
        valid = edge_index >= 0
        src = edge_index.clamp_min(0)
        batch_idx = torch.arange(batch_size, device=x.device).view(batch_size, 1, 1)
        neighbors = x[batch_idx, src]

        query = self.query(x).unsqueeze(2)
        key = self.key(neighbors)
        value = self.value(neighbors)
        scores = (query * key).sum(dim=-1) / math.sqrt(max(key.size(-1), 1))
        scores = scores + edge_weight.to(dtype=x.dtype)
        scores = scores.masked_fill(~valid, torch.finfo(scores.dtype).min)
        attn = torch.softmax(scores, dim=-1)
        attn = torch.where(valid, attn, torch.zeros_like(attn))
        attn = attn / attn.sum(dim=-1, keepdim=True).clamp_min(1e-6)

        aggregated = (attn.unsqueeze(-1) * value).sum(dim=2)
        update = self.self_proj(x) + aggregated
        update = self.dropout(F.gelu(update))
        return self.norm(update + self.residual(x))


class CausalTemporalGLU(nn.Module):
    def __init__(self, input_dim: int, output_dim: int, kernel_size: int, dilation: int, dropout: float) -> None:
        super().__init__()
        self.padding = (kernel_size - 1) * dilation
        self.filter_conv = nn.Conv2d(
            input_dim,
            output_dim,
            kernel_size=(kernel_size, 1),
            dilation=(dilation, 1),
            padding=(self.padding, 0),
        )
        self.gate_conv = nn.Conv2d(
            input_dim,
            output_dim,
            kernel_size=(kernel_size, 1),
            dilation=(dilation, 1),
            padding=(self.padding, 0),
        )
        self.dropout = nn.Dropout(dropout)

    def _trim(self, x: torch.Tensor) -> torch.Tensor:
        if self.padding <= 0:
            return x
        return x[:, :, :-self.padding, :]

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        filtered = torch.tanh(self._trim(self.filter_conv(x)))
        gate = torch.sigmoid(self._trim(self.gate_conv(x)))
        return self.dropout(filtered * gate)


class STGCNBlock(nn.Module):
    def __init__(self, channels: int, kernel_size: int, dropout: float) -> None:
        super().__init__()
        self.temporal_in = CausalTemporalGLU(channels, channels, kernel_size=kernel_size, dilation=1, dropout=dropout)
        self.graph_conv = DiffusionGraphConv(channels, channels)
        self.temporal_out = CausalTemporalGLU(channels, channels, kernel_size=kernel_size, dilation=1, dropout=dropout)
        self.norm = nn.LayerNorm(channels)

    def forward(
        self,
        x: torch.Tensor,
        edge_index_hist: torch.Tensor,
        edge_weight_hist: torch.Tensor,
    ) -> torch.Tensor:
        residual = x
        hidden = self.temporal_in(x)
        hidden_time = hidden.permute(0, 2, 3, 1)
        per_step = []
        for step in range(hidden_time.size(1)):
            per_step.append(self.graph_conv(hidden_time[:, step], edge_index_hist[:, step], edge_weight_hist[:, step]))
        hidden_time = torch.stack(per_step, dim=1)
        hidden = hidden_time.permute(0, 3, 1, 2)
        hidden = self.temporal_out(hidden)
        hidden = hidden + residual
        hidden = self.norm(hidden.permute(0, 2, 3, 1)).permute(0, 3, 1, 2)
        return hidden


class SpatioTemporalEncoder(nn.Module):
    def __init__(self, input_dim: int, config: ModelConfig) -> None:
        super().__init__()
        hidden = config.hidden_dim
        self.input_proj = nn.Linear(input_dim, hidden)
        self.spatial_blocks = nn.ModuleList(
            [
                DirectedDiffusionBlock(hidden, hidden, config.dropout),
                DirectedDiffusionBlock(hidden, hidden, config.dropout),
            ]
        )
        self.temporal_gru = nn.GRU(
            input_size=hidden,
            hidden_size=hidden,
            num_layers=2,
            batch_first=True,
            dropout=config.dropout,
        )
        self.temporal_norm = nn.LayerNorm(hidden)

    def forward(
        self,
        x_hist: torch.Tensor,
        edge_index_hist: torch.Tensor,
        edge_weight_hist: torch.Tensor,
        feature_mask_hist: torch.Tensor,
    ) -> torch.Tensor:
        hidden = torch.cat([x_hist, feature_mask_hist], dim=-1)
        hidden = self.input_proj(hidden)
        for block in self.spatial_blocks:
            per_step = []
            for step in range(hidden.size(1)):
                per_step.append(block(hidden[:, step], edge_index_hist[:, step], edge_weight_hist[:, step]))
            hidden = torch.stack(per_step, dim=1)
        batch_size, history, num_nodes, channels = hidden.shape
        gru_input = hidden.permute(0, 2, 1, 3).reshape(batch_size * num_nodes, history, channels)
        # cuDNN GRU can crash on process teardown with some Windows CUDA builds.
        gru_context = torch.backends.cudnn.flags(enabled=False) if gru_input.is_cuda else nullcontext()
        with gru_context:
            gru_output, _ = self.temporal_gru(gru_input)
        context = gru_output[:, -1].reshape(batch_size, num_nodes, channels)
        return self.temporal_norm(context)


class GraphAttentionTemporalEncoder(nn.Module):
    def __init__(self, input_dim: int, config: ModelConfig) -> None:
        super().__init__()
        hidden = config.hidden_dim
        self.input_proj = nn.Linear(input_dim, hidden)
        self.spatial_blocks = nn.ModuleList(
            [
                GraphAttentionBlock(hidden, hidden, config.dropout),
                GraphAttentionBlock(hidden, hidden, config.dropout),
            ]
        )
        self.temporal_gru = nn.GRU(
            input_size=hidden,
            hidden_size=hidden,
            num_layers=2,
            batch_first=True,
            dropout=config.dropout,
        )
        self.temporal_norm = nn.LayerNorm(hidden)

    def forward(
        self,
        x_hist: torch.Tensor,
        edge_index_hist: torch.Tensor,
        edge_weight_hist: torch.Tensor,
        feature_mask_hist: torch.Tensor,
    ) -> torch.Tensor:
        hidden = torch.cat([x_hist, feature_mask_hist], dim=-1)
        hidden = self.input_proj(hidden)
        for block in self.spatial_blocks:
            per_step = []
            for step in range(hidden.size(1)):
                per_step.append(block(hidden[:, step], edge_index_hist[:, step], edge_weight_hist[:, step]))
            hidden = torch.stack(per_step, dim=1)
        batch_size, history, num_nodes, channels = hidden.shape
        gru_input = hidden.permute(0, 2, 1, 3).reshape(batch_size * num_nodes, history, channels)
        gru_context = torch.backends.cudnn.flags(enabled=False) if gru_input.is_cuda else nullcontext()
        with gru_context:
            gru_output, _ = self.temporal_gru(gru_input)
        context = gru_output[:, -1].reshape(batch_size, num_nodes, channels)
        return self.temporal_norm(context)


def _sinusoidal_positional_encoding(
    length: int,
    dim: int,
    device: torch.device,
    dtype: torch.dtype,
) -> torch.Tensor:
    position = torch.arange(length, device=device, dtype=dtype).unsqueeze(1)
    scale = -math.log(10000.0) / max((dim // 2) - 1, 1)
    div_term = torch.exp(torch.arange(0, dim, 2, device=device, dtype=dtype) * scale)
    encoding = torch.zeros((length, dim), device=device, dtype=dtype)
    encoding[:, 0::2] = torch.sin(position * div_term)
    encoding[:, 1::2] = torch.cos(position * div_term[: encoding[:, 1::2].shape[1]])
    return encoding


class TemporalGraphTransformerEncoder(nn.Module):
    def __init__(self, input_dim: int, config: ModelConfig) -> None:
        super().__init__()
        hidden = config.hidden_dim
        num_heads = 4 if hidden % 4 == 0 else 2
        self.input_proj = nn.Linear(input_dim, hidden)
        self.spatial_block = GraphAttentionBlock(hidden, hidden, config.dropout)
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=hidden,
            nhead=num_heads,
            dim_feedforward=hidden * 4,
            dropout=config.dropout,
            activation="gelu",
            batch_first=True,
        )
        self.temporal_encoder = nn.TransformerEncoder(encoder_layer, num_layers=2)
        self.temporal_norm = nn.LayerNorm(hidden)

    def forward(
        self,
        x_hist: torch.Tensor,
        edge_index_hist: torch.Tensor,
        edge_weight_hist: torch.Tensor,
        feature_mask_hist: torch.Tensor,
    ) -> torch.Tensor:
        hidden = torch.cat([x_hist, feature_mask_hist], dim=-1)
        hidden = self.input_proj(hidden)
        per_step = []
        for step in range(hidden.size(1)):
            per_step.append(self.spatial_block(hidden[:, step], edge_index_hist[:, step], edge_weight_hist[:, step]))
        hidden = torch.stack(per_step, dim=1)
        batch_size, history, num_nodes, channels = hidden.shape
        transformer_input = hidden.permute(0, 2, 1, 3).reshape(batch_size * num_nodes, history, channels)
        transformer_input = transformer_input + _sinusoidal_positional_encoding(
            history,
            channels,
            transformer_input.device,
            transformer_input.dtype,
        ).unsqueeze(0)
        transformer_output = self.temporal_encoder(transformer_input)
        context = transformer_output[:, -1].reshape(batch_size, num_nodes, channels)
        return self.temporal_norm(context)


class TemporalConvResidualBlock(nn.Module):
    def __init__(self, input_dim: int, output_dim: int, kernel_size: int, dilation: int, dropout: float) -> None:
        super().__init__()
        self.padding = (kernel_size - 1) * dilation
        self.conv1 = nn.Conv1d(input_dim, output_dim, kernel_size, padding=self.padding, dilation=dilation)
        self.conv2 = nn.Conv1d(output_dim, output_dim, kernel_size, padding=self.padding, dilation=dilation)
        self.dropout = nn.Dropout(dropout)
        self.norm = nn.GroupNorm(1, output_dim)
        self.residual = nn.Conv1d(input_dim, output_dim, kernel_size=1) if input_dim != output_dim else nn.Identity()

    def _trim(self, x: torch.Tensor) -> torch.Tensor:
        if self.padding <= 0:
            return x
        return x[..., :-self.padding]

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        residual = self.residual(x)
        hidden = self._trim(self.conv1(x))
        hidden = self.dropout(F.gelu(hidden))
        hidden = self._trim(self.conv2(hidden))
        hidden = self.dropout(F.gelu(hidden))
        return self.norm(hidden + residual)


class TemporalConvEncoder(nn.Module):
    def __init__(self, input_dim: int, config: ModelConfig) -> None:
        super().__init__()
        hidden = config.hidden_dim
        self.blocks = nn.ModuleList(
            [
                TemporalConvResidualBlock(input_dim, hidden, kernel_size=3, dilation=1, dropout=config.dropout),
                TemporalConvResidualBlock(hidden, hidden, kernel_size=3, dilation=2, dropout=config.dropout),
                TemporalConvResidualBlock(hidden, hidden, kernel_size=3, dilation=4, dropout=config.dropout),
            ]
        )
        self.output_norm = nn.LayerNorm(hidden)

    def forward(
        self,
        x_hist: torch.Tensor,
        edge_index_hist: torch.Tensor,
        edge_weight_hist: torch.Tensor,
        feature_mask_hist: torch.Tensor,
    ) -> torch.Tensor:
        del edge_index_hist, edge_weight_hist
        hidden = torch.cat([x_hist, feature_mask_hist], dim=-1)
        batch_size, history, num_nodes, channels = hidden.shape
        temporal = hidden.permute(0, 2, 3, 1).reshape(batch_size * num_nodes, channels, history)
        for block in self.blocks:
            temporal = block(temporal)
        context = temporal[..., -1].reshape(batch_size, num_nodes, -1)
        return self.output_norm(context)


class STGCNEncoder(nn.Module):
    def __init__(self, input_dim: int, config: ModelConfig) -> None:
        super().__init__()
        hidden = config.hidden_dim
        self.input_proj = nn.Linear(input_dim, hidden)
        self.blocks = nn.ModuleList(
            [
                STGCNBlock(hidden, kernel_size=3, dropout=config.dropout),
                STGCNBlock(hidden, kernel_size=3, dropout=config.dropout),
            ]
        )
        self.output_norm = nn.LayerNorm(hidden)

    def forward(
        self,
        x_hist: torch.Tensor,
        edge_index_hist: torch.Tensor,
        edge_weight_hist: torch.Tensor,
        feature_mask_hist: torch.Tensor,
    ) -> torch.Tensor:
        hidden = torch.cat([x_hist, feature_mask_hist], dim=-1)
        hidden = self.input_proj(hidden)
        hidden = hidden.permute(0, 3, 1, 2)
        for block in self.blocks:
            hidden = block(hidden, edge_index_hist, edge_weight_hist)
        context = hidden[:, :, -1, :].permute(0, 2, 1)
        return self.output_norm(context)


class GraphWaveNetBlock(nn.Module):
    def __init__(self, channels: int, dilation: int, dropout: float) -> None:
        super().__init__()
        self.temporal = CausalTemporalGLU(channels, channels, kernel_size=2, dilation=dilation, dropout=dropout)
        self.graph_conv = DiffusionGraphConv(channels, channels)
        self.skip_proj = nn.Conv2d(channels, channels, kernel_size=1)
        self.residual_proj = nn.Conv2d(channels, channels, kernel_size=1)
        self.norm = nn.LayerNorm(channels)

    def forward(
        self,
        x: torch.Tensor,
        edge_index_hist: torch.Tensor,
        edge_weight_hist: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        hidden = self.temporal(x)
        hidden_time = hidden.permute(0, 2, 3, 1)
        per_step = []
        for step in range(hidden_time.size(1)):
            per_step.append(self.graph_conv(hidden_time[:, step], edge_index_hist[:, step], edge_weight_hist[:, step]))
        hidden_time = torch.stack(per_step, dim=1)
        hidden = hidden_time.permute(0, 3, 1, 2)
        skip = self.skip_proj(hidden)
        hidden = self.residual_proj(hidden) + x
        hidden = self.norm(hidden.permute(0, 2, 3, 1)).permute(0, 3, 1, 2)
        return hidden, skip


class GraphWaveNetEncoder(nn.Module):
    def __init__(self, input_dim: int, config: ModelConfig) -> None:
        super().__init__()
        hidden = config.hidden_dim
        self.input_proj = nn.Linear(input_dim, hidden)
        self.blocks = nn.ModuleList(
            [
                GraphWaveNetBlock(hidden, dilation=1, dropout=config.dropout),
                GraphWaveNetBlock(hidden, dilation=2, dropout=config.dropout),
                GraphWaveNetBlock(hidden, dilation=4, dropout=config.dropout),
            ]
        )
        self.end_proj = nn.Conv2d(hidden, hidden, kernel_size=1)
        self.output_norm = nn.LayerNorm(hidden)

    def forward(
        self,
        x_hist: torch.Tensor,
        edge_index_hist: torch.Tensor,
        edge_weight_hist: torch.Tensor,
        feature_mask_hist: torch.Tensor,
    ) -> torch.Tensor:
        hidden = torch.cat([x_hist, feature_mask_hist], dim=-1)
        hidden = self.input_proj(hidden).permute(0, 3, 1, 2)
        skip_total = None
        for block in self.blocks:
            hidden, skip = block(hidden, edge_index_hist, edge_weight_hist)
            skip_total = skip if skip_total is None else skip_total + skip
        skip_total = self.end_proj(F.gelu(skip_total))
        context = skip_total[:, :, -1, :].permute(0, 2, 1)
        return self.output_norm(context)


class PatchTSTEncoder(nn.Module):
    def __init__(self, input_dim: int, config: ModelConfig, patch_len: int = 4, patch_stride: int = 2) -> None:
        super().__init__()
        hidden = config.hidden_dim
        self.patch_len = patch_len
        self.patch_stride = patch_stride
        self.patch_proj = nn.Linear(input_dim * patch_len, hidden)
        num_heads = 4 if hidden % 4 == 0 else 2
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=hidden,
            nhead=num_heads,
            dim_feedforward=hidden * 4,
            dropout=config.dropout,
            activation="gelu",
            batch_first=True,
        )
        self.temporal_encoder = nn.TransformerEncoder(encoder_layer, num_layers=2)
        self.output_norm = nn.LayerNorm(hidden)

    def forward(
        self,
        x_hist: torch.Tensor,
        edge_index_hist: torch.Tensor,
        edge_weight_hist: torch.Tensor,
        feature_mask_hist: torch.Tensor,
    ) -> torch.Tensor:
        del edge_index_hist, edge_weight_hist
        hidden = torch.cat([x_hist, feature_mask_hist], dim=-1)
        batch_size, history, num_nodes, channels = hidden.shape
        if history < self.patch_len:
            pad_len = self.patch_len - history
            hidden = F.pad(hidden, (0, 0, 0, 0, pad_len, 0))
            history = hidden.size(1)
        series = hidden.permute(0, 2, 1, 3).reshape(batch_size * num_nodes, history, channels)
        patches = series.unfold(dimension=1, size=self.patch_len, step=self.patch_stride)
        patch_tokens = patches.reshape(batch_size * num_nodes, patches.size(1), self.patch_len * channels)
        patch_tokens = self.patch_proj(patch_tokens)
        patch_tokens = patch_tokens + _sinusoidal_positional_encoding(
            patch_tokens.size(1),
            patch_tokens.size(2),
            patch_tokens.device,
            patch_tokens.dtype,
        ).unsqueeze(0)
        encoded = self.temporal_encoder(patch_tokens)
        context = encoded[:, -1].reshape(batch_size, num_nodes, -1)
        return self.output_norm(context)


class ExpertHead(nn.Module):
    def __init__(self, hidden_dim: int, pred_len: int, dropout: float) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, pred_len),
        )

    def forward(self, context: torch.Tensor) -> torch.Tensor:
        return self.net(context)


class RegimeAwareForecaster(nn.Module):
    def __init__(self, feature_dim: int, pred_len: int, mode: str, config: ModelConfig) -> None:
        super().__init__()
        self.mode = mode
        self.pred_len = pred_len
        self.num_experts = config.num_experts
        self.primary_num_classes = config.primary_num_classes
        self.gate_physics_dim = config.gate_physics_dim
        self.tau = config.tau
        if mode == "baseline_stgcn":
            self.encoder = STGCNEncoder(feature_dim * 2, config)
        elif mode == "baseline_graph_wavenet":
            self.encoder = GraphWaveNetEncoder(feature_dim * 2, config)
        elif mode == "baseline_patchtst":
            self.encoder = PatchTSTEncoder(feature_dim * 2, config)
        elif mode == "baseline_gat_gru":
            self.encoder = GraphAttentionTemporalEncoder(feature_dim * 2, config)
        elif mode == "baseline_graph_transformer":
            self.encoder = TemporalGraphTransformerEncoder(feature_dim * 2, config)
        elif mode == "baseline_tcn":
            self.encoder = TemporalConvEncoder(feature_dim * 2, config)
        else:
            self.encoder = SpatioTemporalEncoder(feature_dim * 2, config)
        hidden = config.hidden_dim
        self.is_baseline_mode = mode in {
            "baseline_dense",
            "baseline_stgcn",
            "baseline_graph_wavenet",
            "baseline_patchtst",
            "baseline_gat_gru",
            "baseline_graph_transformer",
            "baseline_tcn",
        }
        self.dense_head = ExpertHead(hidden, pred_len, config.dropout)
        if self.is_baseline_mode:
            self.experts = nn.ModuleList()
            self.gate = None
        else:
            self.experts = nn.ModuleList(
                [ExpertHead(hidden, pred_len, config.dropout) for _ in range(config.num_experts)]
            )
            if mode in {"moe_no_phys", "moe_context_align"}:
                gate_input_dim = hidden
            elif mode == "moe_anchor_only":
                gate_input_dim = config.gate_physics_dim
            else:
                gate_input_dim = hidden + config.gate_physics_dim
            self.gate = nn.Sequential(
                nn.Linear(gate_input_dim, config.gate_hidden_dim),
                nn.GELU(),
                nn.Dropout(config.dropout),
                nn.Linear(config.gate_hidden_dim, config.num_experts),
            )

    def forward(
        self,
        x_hist: torch.Tensor,
        edge_index_hist: torch.Tensor,
        edge_weight_hist: torch.Tensor,
        feature_mask_hist: torch.Tensor,
        anchor_physics: torch.Tensor | None = None,
    ) -> tuple[torch.Tensor, torch.Tensor | None, dict[str, torch.Tensor]]:
        edge_index_hist = edge_index_hist.long()
        feature_mask_hist = feature_mask_hist.float()
        context = self.encoder(x_hist, edge_index_hist, edge_weight_hist, feature_mask_hist)
        if self.is_baseline_mode:
            pred = self.dense_head(context).transpose(1, 2)
            return pred, None, {"context": context}

        if anchor_physics is None:
            anchor_physics = x_hist.new_zeros((x_hist.shape[0], x_hist.shape[2], self.gate_physics_dim))
        if anchor_physics.shape[-1] != self.gate_physics_dim:
            if anchor_physics.shape[-1] > self.gate_physics_dim:
                anchor_physics = anchor_physics[..., : self.gate_physics_dim]
            else:
                pad = self.gate_physics_dim - anchor_physics.shape[-1]
                anchor_physics = F.pad(anchor_physics, (0, pad))
        if self.mode in {"moe_no_phys", "moe_context_align"}:
            gate_input = context
        elif self.mode == "moe_anchor_only":
            gate_input = anchor_physics
        else:
            gate_input = torch.cat([context, anchor_physics], dim=-1)
        gate_logits = self.gate(gate_input)
        gate_prob = torch.softmax(gate_logits / self.tau, dim=-1)
        expert_outputs = torch.stack([expert(context) for expert in self.experts], dim=-2)
        pred = (gate_prob.unsqueeze(-1) * expert_outputs).sum(dim=-2).transpose(1, 2)
        aux = {
            "context": context,
            "gate_logits": gate_logits,
            "expert_outputs": expert_outputs,
            "anchor_physics": anchor_physics,
        }
        return pred, gate_prob, aux
