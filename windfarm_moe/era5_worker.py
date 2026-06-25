from __future__ import annotations

import argparse
import json
import math
import tempfile
import zipfile
from pathlib import Path

import numpy as np
import xarray as xr

try:
    from .graph import build_haversine_gaussian_graph
    from .regimes import ERA5_PRIMARY_NAMES, compute_era5_regime_from_sshf, compute_era5_regime_from_t2m_gradient
except ImportError:
    from graph import build_haversine_gaussian_graph
    from regimes import ERA5_PRIMARY_NAMES, compute_era5_regime_from_sshf, compute_era5_regime_from_t2m_gradient


def ensure_dir(path: Path | str) -> Path:
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_json(path: Path | str, payload: dict) -> None:
    path = Path(path)

    def _default(obj):
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, Path):
            return str(obj)
        raise TypeError(f"Object of type {type(obj)!r} is not JSON serializable")

    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=True, default=_default)


def _forward_fill_2d(values: np.ndarray) -> np.ndarray:
    result = np.asarray(values, dtype=np.float32).copy()
    missing = np.isnan(result)
    if not missing.any():
        return result
    row_indices = np.where(~missing, np.arange(result.shape[0], dtype=np.int32)[:, None], 0)
    np.maximum.accumulate(row_indices, axis=0, out=row_indices)
    col_indices = np.arange(result.shape[1], dtype=np.int32)[None, :]
    return result[row_indices, col_indices]


def fill_with_train_mean(values: np.ndarray, train_stop: int) -> tuple[np.ndarray, float]:
    filled = _forward_fill_2d(values)
    train_mean = float(np.nanmean(filled[:train_stop]))
    if math.isnan(train_mean):
        train_mean = 0.0
    filled = np.where(np.isfinite(filled), filled, train_mean)
    return filled.astype(np.float32), train_mean


def standardize(values: np.ndarray, train_stop: int) -> tuple[np.ndarray, float, float]:
    train_mean = float(values[:train_stop].mean())
    train_std = float(values[:train_stop].std())
    train_std = train_std if train_std > 1e-6 else 1.0
    normalized = ((values - train_mean) / train_std).astype(np.float32)
    return normalized, train_mean, train_std


def _extract_archives(root_dir: Path, output_dir: Path, pattern: str, max_archives: int | None) -> list[Path]:
    archives = sorted(root_dir.glob(pattern))
    if max_archives is not None:
        archives = archives[:max_archives]
    if not archives:
        raise FileNotFoundError(f"No ERA5 archives matched pattern: {pattern}")
    raw_dir = ensure_dir(Path(tempfile.gettempdir()) / "codex_era5_nc")
    extracted_paths: list[Path] = []
    for index, archive in enumerate(archives):
        out_path = raw_dir / f"era5_source_{index:02d}.nc"
        if not out_path.exists():
            with zipfile.ZipFile(archive) as zf:
                info = zf.infolist()[0]
                with zf.open(info) as src, out_path.open("wb") as dst:
                    dst.write(src.read())
        extracted_paths.append(out_path)
    return extracted_paths


def _load_concat_dataset(nc_files: list[Path]) -> xr.Dataset:
    datasets = []
    for path in nc_files:
        datasets.append(xr.open_dataset(path, engine="netcdf4"))
    try:
        combined = xr.concat(datasets, dim="valid_time")
        combined = combined.sortby("valid_time")
        return combined.load()
    finally:
        for dataset in datasets:
            dataset.close()


def _prepare_feature_stack(feature_map: dict[str, np.ndarray], train_stop: int) -> tuple[np.ndarray, np.ndarray, dict]:
    feature_arrays = []
    feature_masks = []
    stats = {}
    for name, values in feature_map.items():
        mask = np.isfinite(values).astype(np.float32)
        filled, fill_mean = fill_with_train_mean(values, train_stop)
        standardized, mean, std = standardize(filled, train_stop)
        feature_arrays.append(standardized)
        feature_masks.append(mask)
        stats[name] = {
            "fill_mean": fill_mean,
            "mean": mean,
            "std": std,
        }
    return (
        np.stack(feature_arrays, axis=-1).astype(np.float32),
        np.stack(feature_masks, axis=-1).astype(np.float32),
        stats,
    )


def _standardize_physics_stack(physics: np.ndarray, train_stop: int) -> tuple[np.ndarray, dict[str, dict[str, float]]]:
    standardized = np.zeros_like(physics, dtype=np.float32)
    stats = {}
    for idx in range(physics.shape[-1]):
        filled, _ = fill_with_train_mean(physics[..., idx], train_stop)
        normalized, mean, std = standardize(filled, train_stop)
        standardized[..., idx] = normalized
        stats[str(idx)] = {"mean": mean, "std": std}
    return standardized.astype(np.float32), stats


def build_era5_cache(
    root_dir: Path,
    output_dir: Path,
    zip_pattern: str,
    patch_size: int,
    hist_len: int,
    pred_len: int,
    max_archives: int | None,
    candidate_k: int,
) -> None:
    output_dir = ensure_dir(output_dir)
    nc_files = _extract_archives(root_dir, output_dir, zip_pattern, max_archives)
    ds = _load_concat_dataset(nc_files)
    time_name = "valid_time" if "valid_time" in ds.coords else "time"
    lat_name = "latitude"
    lon_name = "longitude"

    total_time = int(ds.sizes[time_name])
    lat_size = int(ds.sizes[lat_name])
    lon_size = int(ds.sizes[lon_name])
    row_start = max(0, (lat_size - patch_size) // 2)
    col_start = max(0, (lon_size - patch_size) // 2)
    row_end = min(lat_size, row_start + patch_size)
    col_end = min(lon_size, col_start + patch_size)
    patch = ds.isel({lat_name: slice(row_start, row_end), lon_name: slice(col_start, col_end)})

    u10 = patch["u10"].to_numpy().astype(np.float32)
    v10 = patch["v10"].to_numpy().astype(np.float32)
    ws10 = np.sqrt(u10**2 + v10**2).astype(np.float32)
    t2m = patch["t2m"].to_numpy().astype(np.float32)
    d2m = patch["d2m"].to_numpy().astype(np.float32)
    sshf = patch["sshf"].to_numpy().astype(np.float32) if "sshf" in patch.data_vars else None
    ssr = patch["ssr"].to_numpy().astype(np.float32) if "ssr" in patch.data_vars else np.zeros_like(ws10)
    tp = patch["tp"].to_numpy().astype(np.float32) if "tp" in patch.data_vars else np.zeros_like(ws10)

    height = patch.sizes[lat_name]
    width = patch.sizes[lon_name]
    num_nodes = height * width
    minimum_stop = hist_len + pred_len + 1
    train_stop = max(minimum_stop, int(round(total_time * 0.6)))
    val_stop = max(train_stop + pred_len + 1, int(round(total_time * 0.8)))
    val_stop = min(val_stop, total_time)
    if val_stop >= total_time:
        val_stop = max(train_stop + 1, total_time - 1)

    if sshf is not None:
        regime_primary, regime_meta = compute_era5_regime_from_sshf(sshf.reshape(total_time, num_nodes), train_stop)
        regime_source = "sshf"
        sshf_flat = sshf.reshape(total_time, num_nodes)
    else:
        regime_primary, regime_meta = compute_era5_regime_from_t2m_gradient(t2m.reshape(total_time, num_nodes), train_stop)
        regime_source = "t2m_gradient"
        sshf_flat = np.zeros((total_time, num_nodes), dtype=np.float32)

    sshf_grad = np.zeros_like(sshf_flat, dtype=np.float32)
    sshf_grad[1:] = sshf_flat[1:] - sshf_flat[:-1]

    feature_map = {
        "WindSpeed10": ws10.reshape(total_time, num_nodes),
        "u10": u10.reshape(total_time, num_nodes),
        "v10": v10.reshape(total_time, num_nodes),
        "t2m": t2m.reshape(total_time, num_nodes),
        "d2m": d2m.reshape(total_time, num_nodes),
        "sshf": sshf_flat,
        "ssr": ssr.reshape(total_time, num_nodes),
        "tp": tp.reshape(total_time, num_nodes),
    }
    features, feature_mask, feature_stats = _prepare_feature_stack(feature_map, train_stop)

    target = ws10.reshape(total_time, num_nodes).astype(np.float32)
    target_mask = np.isfinite(target).astype(np.float32)
    regime_primary_valid = np.ones_like(target_mask, dtype=np.float32)
    t2m_flat = t2m.reshape(total_time, num_nodes).astype(np.float32)
    physics = np.stack([sshf_flat, t2m_flat, target, sshf_grad], axis=-1).astype(np.float32)
    physics_model, physics_model_stats = _standardize_physics_stack(physics, train_stop)

    lats = patch[lat_name].to_numpy().astype(np.float32)
    lons = patch[lon_name].to_numpy().astype(np.float32)
    lon_grid, lat_grid = np.meshgrid(lons, lats)
    coords = np.stack([lat_grid.reshape(-1), lon_grid.reshape(-1)], axis=-1).astype(np.float32)
    base_edge_index, base_edge_weight, graph_meta = build_haversine_gaussian_graph(coords, candidate_k=candidate_k)
    edge_index = np.repeat(base_edge_index[None, :, :], total_time, axis=0).astype(np.int16)
    edge_weight = np.repeat(base_edge_weight[None, :, :], total_time, axis=0).astype(np.float32)

    node_ids = np.arange(num_nodes, dtype=np.int32)
    time_index = patch[time_name].to_numpy()

    np.save(output_dir / "features.npy", features)
    np.save(output_dir / "feature_mask.npy", feature_mask)
    np.save(output_dir / "target.npy", target)
    np.save(output_dir / "target_mask.npy", target_mask)
    np.save(output_dir / "regime_primary.npy", regime_primary.astype(np.int16))
    np.save(output_dir / "regime_primary_valid.npy", regime_primary_valid)
    np.save(output_dir / "physics.npy", physics)
    np.save(output_dir / "physics_model.npy", physics_model)
    np.save(output_dir / "edge_index.npy", edge_index)
    np.save(output_dir / "edge_weight.npy", edge_weight)
    np.save(output_dir / "coords.npy", coords)
    np.save(output_dir / "time_index.npy", time_index)
    np.save(output_dir / "node_ids.npy", node_ids)

    counts = np.bincount(regime_primary.reshape(-1), minlength=3).astype(np.float64)
    counts = np.where(counts > 0, counts, 1.0)
    weights = counts.sum() / (len(counts) * counts)
    weights = (weights / weights.mean()).astype(np.float32).tolist()
    metadata = {
        "dataset": "era5",
        "num_steps": total_time,
        "num_nodes": num_nodes,
        "feature_names": list(feature_map.keys()),
        "physics_names": ["sshf", "t2m", "wind_speed", "sshf_grad"],
        "primary_regime_names": list(ERA5_PRIMARY_NAMES),
        "aux_regime_names": [],
        "primary_num_classes": 3,
        "steps_per_hour": 1,
        "hist_len": hist_len,
        "pred_len": pred_len,
        "split_bounds": {
            "train": [0, train_stop],
            "val": [train_stop, val_stop],
            "test": [val_stop, total_time],
        },
        "feature_stats": feature_stats,
        "physics_model_stats": physics_model_stats,
        "primary_class_weights": weights,
        "patch_shape": [int(height), int(width)],
        "regime_source": regime_source,
        "regime_meta": regime_meta,
        "graph_meta": graph_meta,
        "source_archives": [path.name for path in nc_files],
    }
    save_json(output_dir / "metadata.json", metadata)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ERA5 cache builder")
    parser.add_argument("--root-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--zip-pattern", default="era5*.zip")
    parser.add_argument("--patch-size", type=int, default=16)
    parser.add_argument("--hist-len", type=int, default=36)
    parser.add_argument("--pred-len", type=int, default=24)
    parser.add_argument("--max-archives", type=int, default=None)
    parser.add_argument("--candidate-k", type=int, default=8)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    build_era5_cache(
        root_dir=Path(args.root_dir),
        output_dir=Path(args.output_dir),
        zip_pattern=args.zip_pattern,
        patch_size=args.patch_size,
        hist_len=args.hist_len,
        pred_len=args.pred_len,
        max_archives=args.max_archives,
        candidate_k=args.candidate_k,
    )


if __name__ == "__main__":
    main()
