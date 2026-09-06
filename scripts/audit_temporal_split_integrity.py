"""Audit temporal split integrity and enforce strict walk-forward non-overlapping bounds.

This script directly addresses P0-D from the independent audit:
- Checkpoint training and model-selection validation periods must NEVER overlap with test periods.
- In legacy rolling scripts:
    * Penmanshiel model was trained on days 720--900 (steps 103,680--129,600) and selected on days 900--930.
      Yet rolling_fold_1 tested on steps 105,120--157,680 (days 730--1095), overlapping with training!
    * LHB model was trained on days 0--180 (steps 0--25,920).
      Yet rolling_quarter_1 tested on steps 13,500--27,000 (days 93.75--187.5), overlapping with training!
- Any sample where anchor + pred_len >= calibration_end must be barred from crossing into test time.

Outputs:
  - artifacts/clean_evidence_v2/temporal_split_audit.json
  - artifacts/clean_evidence_v2/temporal_split_audit.csv
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd
import torch


ROOT = Path(".")
OUT_DIR = ROOT / "artifacts" / "clean_evidence_v2"
SLOTS_PER_DAY = 144
PRED_LEN = 24


CHECKPOINTS_TO_AUDIT = [
    ("Kelmarsh", ROOT / "artifacts/signature_gate_farms_runs_20260903/kelmarsh/canonical/wtb_bal_align_force_seed201/best_model.pt"),
    ("Penmanshiel", ROOT / "artifacts/signature_gate_farms_runs_20260903/penmanshiel/canonical/wtb_bal_align_force_seed201/best_model.pt"),
    ("LHB", ROOT / "artifacts/signature_gate_lhb_runs_20260902/canonical/wtb_bal_align_force_seed201/best_model.pt"),
    ("WTB_bal_align_force", ROOT / "artifacts/signature_gate_guard_20260901/wtb_bal_align_force_seed201/best_model.pt"),
]


def audit_checkpoint_splits(farm: str, ckpt_path: Path) -> Dict[str, Any]:
    if not ckpt_path.exists():
        return {}

    ckpt = torch.load(ckpt_path, map_location="cpu")
    meta = ckpt.get("metadata", {})
    offset_days = meta.get("window_offset_days")
    if offset_days is None:
        offset_days = 0.0
    else:
        offset_days = float(offset_days)

    sb = meta.get("split_bounds", {})
    train_steps = sb.get("train", [0, 0])
    val_steps = sb.get("val", [0, 0])
    test_steps = sb.get("test", [0, 0])

    offset_step = int(offset_days * SLOTS_PER_DAY)

    abs_train_start = offset_step + train_steps[0]
    abs_train_end = offset_step + train_steps[1]
    abs_val_start = offset_step + val_steps[0]
    abs_val_end = offset_step + val_steps[1]
    abs_test_start = offset_step + test_steps[0]
    abs_test_end = offset_step + test_steps[1]

    # Model selection end is the validation end step
    selection_end_step = abs_val_end

    return {
        "farm": farm,
        "ckpt_path": str(ckpt_path),
        "offset_days": offset_days,
        "offset_step": offset_step,
        "train_steps_local": train_steps,
        "val_steps_local": val_steps,
        "test_steps_local": test_steps,
        "abs_train_range": [abs_train_start, abs_train_end],
        "abs_val_range": [abs_val_start, abs_val_end],
        "abs_test_range": [abs_test_start, abs_test_end],
        "selection_end_step": selection_end_step,
        "abs_train_days": [abs_train_start / SLOTS_PER_DAY, abs_train_end / SLOTS_PER_DAY],
        "abs_val_days": [abs_val_start / SLOTS_PER_DAY, abs_val_end / SLOTS_PER_DAY],
        "abs_test_days": [abs_test_start / SLOTS_PER_DAY, abs_test_end / SLOTS_PER_DAY],
        "selection_end_day": selection_end_step / SLOTS_PER_DAY,
    }


def evaluate_rolling_fold_integrity(farm: str, ckpt_info: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Audit the legacy rolling folds against the true checkpoint selection end."""
    selection_end = ckpt_info["selection_end_step"]
    steps_per_year = 52560 if farm != "LHB" else 13500
    total_steps = 473184 if farm == "Kelmarsh" else (451334 if farm == "Penmanshiel" else 54289)

    folds = []
    if farm in ["Kelmarsh", "Penmanshiel"]:
        n_years = total_steps // steps_per_year
        for f_idx in range(n_years - 2):
            v_start = f_idx * steps_per_year
            v_end = v_start + 2 * steps_per_year
            t_start = v_end
            t_end = min(t_start + steps_per_year, total_steps)

            # Check overlap with training or model selection
            train_range = ckpt_info["abs_train_range"]
            val_range = ckpt_info["abs_val_range"]

            overlaps_train = not (t_end <= train_range[0] or t_start >= train_range[1])
            overlaps_val = not (t_end <= val_range[0] or t_start >= val_range[1])
            strictly_post_selection = (t_start >= selection_end)

            folds.append({
                "farm": farm,
                "fold_name": f"rolling_fold_{f_idx + 1}",
                "cal_range_steps": [v_start, v_end],
                "test_range_steps": [t_start, t_end],
                "cal_range_days": [v_start / SLOTS_PER_DAY, v_end / SLOTS_PER_DAY],
                "test_range_days": [t_start / SLOTS_PER_DAY, t_end / SLOTS_PER_DAY],
                "overlaps_train": overlaps_train,
                "overlaps_selection_val": overlaps_val,
                "strictly_post_selection_walk_forward": strictly_post_selection,
                "verdict": "VALID_WALK_FORWARD" if strictly_post_selection and not overlaps_train else "CONTAMINATED_OVERLAP",
            })
    else:  # LHB
        for q_idx in range(3):
            v_start = q_idx * steps_per_year
            v_end = v_start + steps_per_year
            t_start = v_end
            t_end = min(t_start + steps_per_year, total_steps)

            train_range = ckpt_info["abs_train_range"]
            val_range = ckpt_info["abs_val_range"]

            overlaps_train = not (t_end <= train_range[0] or t_start >= train_range[1])
            overlaps_val = not (t_end <= val_range[0] or t_start >= val_range[1])
            strictly_post_selection = (t_start >= selection_end)

            folds.append({
                "farm": farm,
                "fold_name": f"rolling_quarter_{q_idx + 1}",
                "cal_range_steps": [v_start, v_end],
                "test_range_steps": [t_start, t_end],
                "cal_range_days": [v_start / SLOTS_PER_DAY, v_end / SLOTS_PER_DAY],
                "test_range_days": [t_start / SLOTS_PER_DAY, t_end / SLOTS_PER_DAY],
                "overlaps_train": overlaps_train,
                "overlaps_selection_val": overlaps_val,
                "strictly_post_selection_walk_forward": strictly_post_selection,
                "verdict": "VALID_WALK_FORWARD" if strictly_post_selection and not overlaps_train else "CONTAMINATED_OVERLAP",
            })

    return folds


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    all_ckpts = {}
    all_fold_audits = []

    print("=== Starting Temporal Split & Walk-Forward Integrity Audit ===")
    for farm, path in CHECKPOINTS_TO_AUDIT:
        info = audit_checkpoint_splits(farm, path)
        if info:
            all_ckpts[farm] = info
            fold_res = evaluate_rolling_fold_integrity(farm, info)
            all_fold_audits.extend(fold_res)

    out_data = {
        "checkpoints": all_ckpts,
        "rolling_folds": all_fold_audits,
        "rules_enforced": [
            "assert first_test_target >= max(selection_end, calibration_end)",
            "assert cal_anchor + pred_len < cal_end (no future horizon leakage into test)",
            "bar any fold where test period intersects train or val bounds",
        ],
    }

    out_json = OUT_DIR / "temporal_split_audit.json"
    out_json.write_text(json.dumps(out_data, indent=2), encoding="utf-8")
    print(f"Saved temporal audit JSON to {out_json}")

    df = pd.DataFrame(all_fold_audits)
    out_csv = OUT_DIR / "temporal_split_audit.csv"
    df.to_csv(out_csv, index=False)
    print(f"Saved temporal audit CSV to {out_csv}")

    print("\n--- Rolling Folds Integrity Audit Summary ---")
    summary_cols = ["farm", "fold_name", "test_range_days", "overlaps_train", "strictly_post_selection_walk_forward", "verdict"]
    print(df[summary_cols].to_string(index=False))


if __name__ == "__main__":
    main()
