"""Inspect saved coordinate/mask identities only; no prediction or metric evaluation."""
import hashlib
import json
from pathlib import Path

import numpy as np

BASE = Path(__file__).resolve().parent


def main():
    rows = []
    for seed in range(201, 206):
        path = BASE / f"recovered/R/results/runs/seed{seed}/pitch_withheld/evaluation_coordinates.npz"
        with np.load(path, allow_pickle=False) as saved:
            pitch_mask = np.isfinite(saved["true_pitch"])
            decision_mask = saved["mask"]
            rows.append({"seed": seed, "source": path.relative_to(BASE).as_posix(),
                         "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                         "shape": list(decision_mask.shape),
                         "same_grid_shape": pitch_mask.shape == decision_mask.shape,
                         "current_pitch_mask_equals_decision_mask": bool(np.array_equal(pitch_mask, decision_mask)),
                         "target_indices_equal_anchors_plus6": bool(np.array_equal(saved["target_indices"], saved["anchors"] + 6)),
                         "publication_indices_equal_anchors_minus6": bool(np.array_equal(saved["publication_indices"], saved["anchors"] - 6)),
                         "decision_mask_sha256": hashlib.sha256(decision_mask.tobytes()).hexdigest(),
                         "current_pitch_mask_sha256": hashlib.sha256(pitch_mask.tobytes()).hexdigest()})
    print(json.dumps({"scope": "Existing coordinate/mask identity only; no new outcome metric or statistical interval",
                      "rows": rows, "all_five_same_mask_definition_in_coordinates":
                      all(row["current_pitch_mask_equals_decision_mask"] for row in rows)}, indent=2))


if __name__ == "__main__":
    main()
