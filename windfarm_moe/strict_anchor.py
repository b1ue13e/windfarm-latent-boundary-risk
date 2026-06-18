from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from .utils import ensure_dir, load_json, save_json


def _anchor_feature_indices(metadata: dict[str, Any]) -> tuple[int, int]:
    feature_names = [str(name) for name in metadata.get("feature_names", [])]
    try:
        return feature_names.index("Wspd"), feature_names.index("Pab_mean")
    except ValueError as exc:
        raise ValueError("Strict-anchor mask requires Wspd and Pab_mean in feature_names.") from exc


def strict_anchor_mask_report(cache_dir: Path | str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    cache_dir = Path(cache_dir)
    metadata_path = cache_dir / "metadata.json"
    if metadata is None:
        metadata = load_json(metadata_path) if metadata_path.exists() else {}
    try:
        wspd_idx, pab_idx = _anchor_feature_indices(metadata)
    except ValueError:
        return {
            "can_check": False,
            "strict_anchor_violations": None,
            "reason": "Wspd or Pab_mean is missing from feature_names",
        }

    feature_mask_path = cache_dir / "feature_mask.npy"
    regime_valid_path = cache_dir / "regime_primary_valid.npy"
    if not feature_mask_path.exists() or not regime_valid_path.exists():
        return {
            "can_check": False,
            "strict_anchor_violations": None,
            "reason": "feature_mask.npy or regime_primary_valid.npy is missing",
        }

    feature_mask = np.load(feature_mask_path, mmap_mode="r")
    regime_valid = np.load(regime_valid_path, mmap_mode="r")
    anchor_valid = (feature_mask[..., wspd_idx] > 0.0) & (feature_mask[..., pab_idx] > 0.0)
    violations = (~anchor_valid) & (regime_valid > 0.0)
    strict_anchor_violations = int(violations.sum())
    patch_metadata = metadata.get("strict_anchor_mask_patch", {})
    return {
        "can_check": True,
        "anchor_feature_names": ["Wspd", "Pab_mean"],
        "anchor_feature_indices": [int(wspd_idx), int(pab_idx)],
        "total_missing_anchor_cells": int((~anchor_valid).sum()),
        "strict_anchor_violations": strict_anchor_violations,
        "strict_anchor_pass": strict_anchor_violations == 0,
        "metadata_patch_present": bool(patch_metadata),
        "metadata_removed_regime_valid": patch_metadata.get("removed_regime_valid"),
        "metadata_removed_aux_valid": patch_metadata.get("removed_aux_valid"),
        "metadata_patch_violations_after_patch": patch_metadata.get("strict_anchor_violations_after_patch"),
    }


def patch_strict_anchor_mask(cache_dir: Path | str, output_dir: Path | str | None = None) -> Path:
    cache_dir = Path(cache_dir)
    metadata_path = cache_dir / "metadata.json"
    if not metadata_path.exists():
        raise FileNotFoundError(f"Missing cache metadata: {metadata_path}")
    metadata = load_json(metadata_path)
    wspd_idx, pab_idx = _anchor_feature_indices(metadata)

    feature_mask_path = cache_dir / "feature_mask.npy"
    regime_valid_path = cache_dir / "regime_primary_valid.npy"
    if not feature_mask_path.exists() or not regime_valid_path.exists():
        raise FileNotFoundError("Strict-anchor mask requires feature_mask.npy and regime_primary_valid.npy.")

    feature_mask = np.load(feature_mask_path, mmap_mode="r")
    anchor_valid = (feature_mask[..., wspd_idx] > 0.0) & (feature_mask[..., pab_idx] > 0.0)
    regime_valid = np.load(regime_valid_path)
    patched_regime_valid = np.where(anchor_valid, regime_valid, 0.0).astype(np.float32)
    removed_regime_valid = int(((regime_valid > 0.0) & (~anchor_valid)).sum())
    np.save(regime_valid_path, patched_regime_valid)

    removed_aux_valid = 0
    aux_valid_path = cache_dir / "regime_aux_valid.npy"
    if aux_valid_path.exists():
        aux_valid = np.load(aux_valid_path)
        patched_aux_valid = np.where(anchor_valid, aux_valid, 0.0).astype(np.float32)
        removed_aux_valid = int(((aux_valid > 0.0) & (~anchor_valid)).sum())
        np.save(aux_valid_path, patched_aux_valid)

    report = {
        "cache_dir": str(cache_dir),
        "anchor_feature_names": ["Wspd", "Pab_mean"],
        "anchor_feature_indices": [int(wspd_idx), int(pab_idx)],
        "total_missing_anchor_cells": int((~anchor_valid).sum()),
        "removed_regime_valid": removed_regime_valid,
        "removed_aux_valid": removed_aux_valid,
        "strict_anchor_violations_after_patch": int(((patched_regime_valid > 0.0) & (~anchor_valid)).sum()),
    }
    metadata["strict_anchor_mask_patch"] = {
        "version": 1,
        "anchor_feature_names": report["anchor_feature_names"],
        "anchor_feature_indices": report["anchor_feature_indices"],
        "total_missing_anchor_cells": report["total_missing_anchor_cells"],
        "removed_regime_valid": report["removed_regime_valid"],
        "removed_aux_valid": report["removed_aux_valid"],
        "strict_anchor_violations_after_patch": report["strict_anchor_violations_after_patch"],
    }
    save_json(metadata_path, metadata)

    if output_dir is None:
        output_dir = cache_dir
    output_dir = ensure_dir(output_dir)
    save_json(output_dir / "strict_anchor_mask_patch_report.json", report)
    (output_dir / "README.md").write_text(
        "# Strict-anchor mask patch\n\n"
        "This patch intersects WTB regime-valid masks with observed anchor Wspd and Pab_mean features.\n\n"
        f"- Cache: `{cache_dir}`\n"
        f"- Missing anchor cells: `{report['total_missing_anchor_cells']}`\n"
        f"- Removed primary regime-valid cells: `{removed_regime_valid}`\n"
        f"- Removed auxiliary regime-valid cells: `{removed_aux_valid}`\n"
        f"- Violations after patch: `{report['strict_anchor_violations_after_patch']}`\n",
        encoding="utf-8",
    )
    return output_dir
