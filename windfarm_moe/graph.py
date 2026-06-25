from __future__ import annotations

from typing import Any

import numpy as np


def build_static_candidates(
    coords: np.ndarray,
    candidate_k: int,
    max_distance: float,
) -> dict[str, Any]:
    num_nodes = coords.shape[0]
    deltas = coords[None, :, :] - coords[:, None, :]
    distances = np.sqrt(np.sum(deltas**2, axis=-1))
    np.fill_diagonal(distances, np.inf)
    neighbor_order = np.argsort(distances, axis=1)[:, :candidate_k]
    src_list: list[int] = []
    dst_list: list[int] = []
    dx_list: list[float] = []
    dy_list: list[float] = []
    dist_list: list[float] = []
    for src in range(num_nodes):
        for dst in neighbor_order[src]:
            dist = float(distances[src, dst])
            if not np.isfinite(dist) or dist > max_distance:
                continue
            delta = coords[dst] - coords[src]
            src_list.append(src)
            dst_list.append(int(dst))
            dx_list.append(float(delta[0]))
            dy_list.append(float(delta[1]))
            dist_list.append(dist)
    src = np.asarray(src_list, dtype=np.int16)
    dst = np.asarray(dst_list, dtype=np.int16)
    dx = np.asarray(dx_list, dtype=np.float32)
    dy = np.asarray(dy_list, dtype=np.float32)
    dist = np.asarray(dist_list, dtype=np.float32)
    static_weight = np.exp(-dist / max_distance).astype(np.float32)
    incoming_groups = [np.where(dst == node)[0] for node in range(num_nodes)]
    return {
        "src": src,
        "dst": dst,
        "dx": dx,
        "dy": dy,
        "dist": dist,
        "static_weight": static_weight,
        "incoming_groups": incoming_groups,
    }


def build_dynamic_graph(
    wdir_deg: np.ndarray,
    candidates: dict[str, Any],
    max_in_edges: int,
    cone_half_angle_deg: float,
    parallel_scale: float,
    cross_scale: float,
    direction_is_from: bool,
    chunk_size: int = 1024,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    total_steps, num_nodes = wdir_deg.shape
    src = candidates["src"].astype(np.int64)
    dx = candidates["dx"].astype(np.float32)
    dy = candidates["dy"].astype(np.float32)
    static_weight = candidates["static_weight"].astype(np.float32)
    incoming_groups = candidates["incoming_groups"]
    edge_index = np.full((total_steps, num_nodes, max_in_edges), -1, dtype=np.int16)
    edge_weight = np.zeros((total_steps, num_nodes, max_in_edges), dtype=np.float32)

    for start in range(0, total_steps, chunk_size):
        end = min(start + chunk_size, total_steps)
        current_wdir = wdir_deg[start:end][:, src]
        valid_dir = np.isfinite(current_wdir)
        theta = np.deg2rad(np.where(valid_dir, current_wdir, 0.0))
        if direction_is_from:
            theta = theta + np.pi
        flow_x = np.sin(theta)
        flow_y = np.cos(theta)
        d_parallel = dx[None, :] * flow_x + dy[None, :] * flow_y
        d_cross = np.abs(dx[None, :] * flow_y - dy[None, :] * flow_x)
        cone_mask = (d_parallel > 0.0) & (
            np.rad2deg(np.arctan2(d_cross, np.maximum(d_parallel, 1e-6))) <= cone_half_angle_deg
        )
        dynamic_weight = np.exp(-d_parallel / parallel_scale) * np.exp(-d_cross / cross_scale)
        weights = np.where(valid_dir & cone_mask, dynamic_weight, 0.0).astype(np.float32)
        weights = np.where(valid_dir, weights, static_weight[None, :]).astype(np.float32)

        for node in range(num_nodes):
            edge_ids = incoming_groups[node]
            if edge_ids.size == 0:
                continue
            group_weights = weights[:, edge_ids]
            top_k = min(max_in_edges, group_weights.shape[1])
            if top_k == group_weights.shape[1]:
                part = np.tile(np.arange(top_k, dtype=np.int64), (group_weights.shape[0], 1))
            else:
                part = np.argpartition(-group_weights, kth=top_k - 1, axis=1)[:, :top_k]
            selected_weight = np.take_along_axis(group_weights, part, axis=1)
            order = np.argsort(-selected_weight, axis=1)
            part = np.take_along_axis(part, order, axis=1)
            selected_weight = np.take_along_axis(selected_weight, order, axis=1)
            selected_src = src[edge_ids][part]
            active = selected_weight > 0.0
            src_buffer = np.full((end - start, max_in_edges), -1, dtype=np.int16)
            weight_buffer = np.zeros((end - start, max_in_edges), dtype=np.float32)
            src_buffer[:, :top_k] = np.where(active, selected_src, -1)
            weight_buffer[:, :top_k] = np.where(active, selected_weight, 0.0)
            edge_index[start:end, node] = src_buffer
            edge_weight[start:end, node] = weight_buffer

    wake_score = edge_weight.sum(axis=-1).astype(np.float32)
    return edge_index, edge_weight, wake_score


def haversine_distance_km(coords_latlon_deg: np.ndarray) -> np.ndarray:
    coords = np.asarray(coords_latlon_deg, dtype=np.float64)
    lat = np.deg2rad(coords[:, 0])
    lon = np.deg2rad(coords[:, 1])
    dlat = lat[None, :] - lat[:, None]
    dlon = lon[None, :] - lon[:, None]
    a = (
        np.sin(dlat / 2.0) ** 2
        + np.cos(lat)[:, None] * np.cos(lat)[None, :] * np.sin(dlon / 2.0) ** 2
    )
    c = 2.0 * np.arctan2(np.sqrt(a), np.sqrt(np.maximum(1.0 - a, 1e-12)))
    return (6371.0 * c).astype(np.float32)


def build_haversine_gaussian_graph(
    coords_latlon_deg: np.ndarray,
    candidate_k: int,
    sigma_km: float | None = None,
) -> tuple[np.ndarray, np.ndarray, dict[str, float]]:
    distances = haversine_distance_km(coords_latlon_deg)
    num_nodes = distances.shape[0]
    np.fill_diagonal(distances, np.inf)
    neighbor_order = np.argsort(distances, axis=1)[:, :candidate_k]
    adjacency = np.zeros((num_nodes, num_nodes), dtype=np.float32)
    for src in range(num_nodes):
        adjacency[src, neighbor_order[src]] = 1.0
    adjacency = np.maximum(adjacency, adjacency.T)
    kept_distances = distances[np.where(adjacency > 0.0)]
    if kept_distances.size == 0:
        sigma = 1.0 if sigma_km is None else float(sigma_km)
    else:
        sigma = float(np.median(kept_distances)) if sigma_km is None else float(sigma_km)
    sigma = max(sigma, 1e-3)
    weights = np.exp(-(distances**2) / (2.0 * sigma**2)).astype(np.float32)
    weights = np.where(adjacency > 0.0, weights, 0.0).astype(np.float32)

    max_edges = int(np.max((adjacency > 0.0).sum(axis=1))) if adjacency.any() else 0
    edge_index = np.full((num_nodes, max_edges), -1, dtype=np.int16)
    edge_weight = np.zeros((num_nodes, max_edges), dtype=np.float32)
    for node in range(num_nodes):
        neighbors = np.where(adjacency[node] > 0.0)[0]
        if neighbors.size == 0:
            continue
        neighbor_weights = weights[node, neighbors]
        order = np.argsort(-neighbor_weights)
        neighbors = neighbors[order]
        neighbor_weights = neighbor_weights[order]
        edge_index[node, : neighbors.size] = neighbors.astype(np.int16)
        edge_weight[node, : neighbors.size] = neighbor_weights.astype(np.float32)
    meta = {
        "candidate_k": int(candidate_k),
        "sigma_km": float(sigma),
    }
    return edge_index, edge_weight, meta
