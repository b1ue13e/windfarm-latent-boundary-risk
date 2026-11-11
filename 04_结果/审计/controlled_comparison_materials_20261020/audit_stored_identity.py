"""Compare already-saved coordinates and action copies, without evaluating losses."""
import csv
import json
from pathlib import Path

import numpy as np

BASE = Path(__file__).resolve().parent
WORKSPACE = BASE.parent.parent


def main():
    parent_rows = []
    for worker in range(10):
        receipt_path = WORKSPACE / f"experiments/state_calibration_controls_20261020/evidence/results/evaluate/{worker}/receipt.json"
        receipt = json.loads(receipt_path.read_text())
        estimator, seed = receipt["estimator"], receipt["seed"]
        with (BASE / "study_M/ENVIRONMENT_INDEX_M.csv").open(encoding="utf-8-sig", newline="") as handle:
            entries = [row for row in csv.DictReader(handle)
                       if row["estimator"] == estimator and int(row["seed"]) == seed]
        control_path = BASE / f"recovered/M_controls/results/evaluate/{worker}/actions.npz"
        with np.load(control_path, allow_pickle=False) as controls:
            for entry in entries:
                task, cell = entry["task"], entry["cell"]
                pilot_path = BASE / f"recovered/M_pilot/results/evaluation/{task}/actions.npz"
                with np.load(pilot_path, allow_pickle=False) as pilot:
                    equal = bool(np.array_equal(pilot["calibrated"], controls["Original|" + cell]))
                parent_rows.append({"worker": worker, "task": task, "seed": seed,
                                    "estimator": estimator, "cell": cell,
                                    "saved_original_action_arrays_equal": equal})
    with np.load(BASE / "recovered/R/results/runs/seed201/pitch_withheld/evaluation_coordinates.npz",
                 allow_pickle=False) as source_r, np.load(BASE / "recovered/M_pilot/results/prepared/evaluation.npz",
                                                          allow_pickle=False) as source_m:
        shared = {key: bool(np.array_equal(source_r[key], source_m[key], equal_nan=True))
                  for key in ["anchors", "target_indices", "publication_indices", "forecast", "shortfall"]}
        shared["R_future_target_mask_equals_M_target_mask"] = bool(np.array_equal(source_r["mask"], source_m["target_mask"]))
        shared["R_decision_mask_equals_M_primary_mask"] = bool(np.array_equal(source_r["mask"], source_m["primary_mask"]))
        shared["M_primary_mask_subset_of_R_decision_mask"] = bool(np.all(~source_m["primary_mask"] | source_r["mask"]))
    result = {"scope": "Saved-input and saved-action identity only; no metrics, inference, calibration or bootstrap",
              "parent_action_pairs": parent_rows,
              "all_60_original_action_pairs_equal": len(parent_rows) == 60 and all(row["saved_original_action_arrays_equal"] for row in parent_rows),
              "shared_coordinate_comparison": shared,
              "no_new_outcome_estimate_or_test": True}
    print(json.dumps(result, indent=2))
    if not result["all_60_original_action_pairs_equal"]:
        raise SystemExit(1)
    if not all(shared[key] for key in ["anchors", "target_indices", "publication_indices", "forecast", "shortfall",
                                      "R_future_target_mask_equals_M_target_mask", "M_primary_mask_subset_of_R_decision_mask"]):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
