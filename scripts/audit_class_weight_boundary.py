from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from windfarm_moe.regimes import inverse_frequency_weights_from_labels

OUT = ROOT / "artifacts" / "class_weight_boundary_audit"
DEFAULT_CACHES = [
    ROOT / "artifacts" / "cache_strictmask" / "wtb_245d",
    ROOT / "artifacts" / "cache_strictmask_trainweights" / "wtb_245d",
    ROOT / "artifacts" / "cache" / "wtb_245d",
    ROOT / "artifacts" / "cache_external_wind" / "external_wind_la_haute_borne_chronological",
]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for cache_dir in DEFAULT_CACHES:
        if cache_dir.exists():
            rows.append(_audit_cache(cache_dir))
    frame = pd.DataFrame(rows)
    out_csv = OUT / "class_weight_boundary_audit.csv"
    out_json = OUT / "class_weight_boundary_audit.json"
    frame.to_csv(out_csv, index=False)
    has_train_only_cache = bool(not frame.empty and frame["metadata_matches_train_only"].astype(bool).any())
    has_legacy_full_cache = bool(not frame.empty and frame["metadata_matches_full_period"].astype(bool).any())
    if has_train_only_cache and has_legacy_full_cache:
        status = "complete_train_only_source_with_legacy_cache_boundary"
    elif has_train_only_cache:
        status = "complete_train_only_weight_boundary"
    else:
        status = "complete_legacy_class_weight_boundary_identified"
    payload = {
        "status": status,
        "claim_use": (
            "Class-weight boundary audit. Current preprocessing source computes regime "
            "and pitch-forcing weights from the training split only. Rows marked as "
            "metadata_matches_full_period identify frozen legacy caches used by older "
            "reported checkpoints; train-only caches support current reruns, and the "
            "separate sensitivity audit checks whether the boundary-router claim survives "
            "that loss-weight provenance correction."
        ),
        "csv": str(out_csv),
        "rows": rows,
    }
    out_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {out_csv}")


def _audit_cache(cache_dir: Path) -> dict[str, Any]:
    metadata = json.loads((cache_dir / "metadata.json").read_text(encoding="utf-8"))
    regime = np.load(cache_dir / "regime_primary.npy", mmap_mode="r")
    valid = np.load(cache_dir / "regime_primary_valid.npy", mmap_mode="r")
    train_end = int(metadata["split_bounds"]["train"][1])
    primary_meta = [float(v) for v in metadata.get("primary_class_weights", [])]
    primary_full = inverse_frequency_weights_from_labels(regime, valid, 3)
    primary_train = inverse_frequency_weights_from_labels(regime[:train_end], valid[:train_end], 3)

    pitch_labels = np.zeros_like(regime, dtype=np.int16)
    pitch_labels[regime == 2] = 1
    pitch_valid = ((regime == 1) | (regime == 2)).astype(np.float32)
    pitch_meta = [float(v) for v in metadata.get("pitch_force_weights", [])]
    pitch_full = inverse_frequency_weights_from_labels(pitch_labels, pitch_valid, 2)
    pitch_train = inverse_frequency_weights_from_labels(pitch_labels[:train_end], pitch_valid[:train_end], 2)

    return {
        "cache_dir": str(cache_dir.relative_to(ROOT)),
        "train_end": train_end,
        "metadata_source_split": str(metadata.get("class_weight_source_split", "legacy_unspecified")),
        "metadata_matches_train_only": _close(primary_meta, primary_train) and _close(pitch_meta, pitch_train),
        "metadata_matches_full_period": _close(primary_meta, primary_full) and _close(pitch_meta, pitch_full),
        "primary_metadata": _fmt_list(primary_meta),
        "primary_train_only": _fmt_list(primary_train),
        "primary_full_period": _fmt_list(primary_full),
        "pitch_metadata": _fmt_list(pitch_meta),
        "pitch_train_only": _fmt_list(pitch_train),
        "pitch_full_period": _fmt_list(pitch_full),
    }


def _close(left: list[float], right: list[float]) -> bool:
    if len(left) != len(right):
        return False
    return bool(np.allclose(np.asarray(left), np.asarray(right, dtype=np.float64), rtol=1e-6, atol=1e-6))


def _fmt_list(values: list[float]) -> str:
    return ";".join(f"{float(v):.8f}" for v in values)


if __name__ == "__main__":
    main()
