from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description="Clone a cache while recomputing loss weights from the train split.")
    parser.add_argument("--source-cache", type=Path, default=ROOT / "artifacts" / "cache_strictmask" / "wtb_245d")
    parser.add_argument("--target-cache", type=Path, required=True)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    source = args.source_cache
    target = args.target_cache
    if not (source / "metadata.json").exists():
        raise FileNotFoundError(f"Missing source cache metadata: {source}")
    if target.exists():
        if not args.overwrite:
            raise FileExistsError(f"Target cache already exists: {target}")
        shutil.rmtree(target)
    shutil.copytree(source, target, copy_function=_copy_or_hardlink)

    metadata_path = target / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    train_end = int(metadata["split_bounds"]["train"][1])
    regime = np.load(target / "regime_primary.npy", mmap_mode="r")
    valid = np.load(target / "regime_primary_valid.npy", mmap_mode="r")

    metadata["primary_class_weights"] = _inverse_frequency_weights(regime[:train_end], valid[:train_end], 3)
    pitch_labels = np.zeros_like(regime[:train_end], dtype=np.int16)
    pitch_labels[regime[:train_end] == 2] = 1
    pitch_valid = ((regime[:train_end] == 1) | (regime[:train_end] == 2)).astype(np.float32)
    metadata["pitch_force_weights"] = _inverse_frequency_weights(pitch_labels, pitch_valid, 2)
    metadata["class_weight_source_split"] = "train"
    metadata["class_weight_source_cache"] = str(source)
    metadata["class_weight_boundary_note"] = (
        "Arrays are copied from the source strict cache; only alignment and pitch-force "
        "loss class weights are recomputed from the training split."
    )
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(f"Wrote train-weight cache: {target}")


def _copy_or_hardlink(src: str, dst: str) -> str:
    if Path(src).suffix.lower() not in {".npy"}:
        return shutil.copy2(src, dst)
    try:
        Path(dst).parent.mkdir(parents=True, exist_ok=True)
        Path(dst).hardlink_to(src)
    except OSError:
        shutil.copy2(src, dst)
    return dst


def _inverse_frequency_weights(labels: np.ndarray, valid: np.ndarray, num_classes: int) -> list[float]:
    mask = np.asarray(valid).reshape(-1) > 0
    flat = np.asarray(labels).reshape(-1)[mask]
    if flat.size == 0:
        return [1.0] * int(num_classes)
    counts = np.bincount(flat.astype(np.int64), minlength=int(num_classes)).astype(np.float64)
    counts = np.where(counts > 0.0, counts, 1.0)
    weights = counts.sum() / (float(num_classes) * counts)
    weights = weights / weights.mean()
    return [float(value) for value in weights]


if __name__ == "__main__":
    main()
