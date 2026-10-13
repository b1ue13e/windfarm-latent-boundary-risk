"""Regenerate the corrected Regime-2 recalibration absorption table.

Root cause of Issue F5 (metric-definition error):
  scripts/verify_replication.py C05 previously computed the token labelled
  "recalibration shortage absorption" as

      1 - no_pitch_CLEAN_shortage / all_CLEAN_shortage
        = 1 - 57.073338575235994 / 127.5520249263407 = 55.25%

  Both endpoints are `phys_clean` (uncalibrated physics). The numerator is the
  PITCH-WITHHELD clean shortage, so the ratio measures the effect of withholding
  pitch telemetry -- recalibration does not participate in the comparison at all.
  It also silently crossed channel_mode, which is a Regime-3 contrast, not Regime 2.

  The true Regime-2 quantity is the within-channel_mode, within-lag contrast
  between `phys_clean_shortage_mean` and `phys_recal_shortage_mean` at
  channel_mode='all'.

Source: artifacts/single_task_dense_vs_multitask_moe_ablation.csv
        (lead_step=0, 5-seed means; no duplicate (lead,lag,channel_mode) keys)
"""

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "artifacts" / "single_task_dense_vs_multitask_moe_ablation.csv"
OUT = ROOT / "artifacts" / "regime2_recalibration_absorption.csv"

rows = list(csv.DictReader(SRC.open("r", encoding="utf-8-sig")))

# lead_step=0 is the primary (headline) latency configuration.
primary = [r for r in rows if r["lead_step"] == "0"]
grid = [
    r for r in primary
    if r["channel_mode"] == "all" and r["lag_steps"] in {"0", "1", "2", "3", "6"}
]
grid.sort(key=lambda r: int(r["lag_steps"]))


def f(r, k):
    return float(r[k])


records = []
for r in grid:
    clean_s = f(r, "phys_clean_shortage_mean")
    recal_s = f(r, "phys_recal_shortage_mean")
    clean_c = f(r, "phys_clean_cost_mean")
    recal_c = f(r, "phys_recal_cost_mean")
    clean_v = f(r, "phys_clean_viol_mean")
    recal_v = f(r, "phys_recal_viol_mean")
    records.append({
        "tau_min": int(r["lag_minutes"]),
        "lag_steps": int(r["lag_steps"]),
        "channel_mode": r["channel_mode"],
        "phys_clean_shortage_mwh": round(clean_s, 4),
        "phys_recal_shortage_mwh": round(recal_s, 4),
        "shortage_absorption_pct": round((clean_s - recal_s) / clean_s * 100.0, 2),
        "phys_clean_cost_kwh": round(clean_c, 1),
        "phys_recal_cost_kwh": round(recal_c, 1),
        "phys_clean_viol": round(clean_v, 4),
        "phys_recal_viol": round(recal_v, 4),
        "recal_target_satisfied": recal_v <= 0.10,
    })

with OUT.open("w", encoding="utf-8", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(records[0].keys()))
    w.writeheader()
    w.writerows(records)

print(f"wrote {OUT.relative_to(ROOT)}  ({len(records)} rows)")
for rec in records:
    print("  tau=%-3d min  clean=%8.3f  recal=%8.3f  absorption=%6.2f%%  viol %.4f->%.4f"
          % (rec["tau_min"], rec["phys_clean_shortage_mwh"],
             rec["phys_recal_shortage_mwh"], rec["shortage_absorption_pct"],
             rec["phys_clean_viol"], rec["phys_recal_viol"]))

# Machine-checkable assertions used by the repair.
op_grid = [r for r in records if r["tau_min"] in (10, 20, 30)]
assert all(r["recal_target_satisfied"] for r in op_grid), "operational grid must satisfy target"
h60 = next(r for r in records if r["tau_min"] == 60)
assert abs(h60["shortage_absorption_pct"] - 66.46) < 0.05, "tau=60 absorption is 66.46%"
assert abs(h60["phys_recal_shortage_mwh"] - 42.787) < 0.01, "tau=60 recal shortage is 42.787 MWh"

print("\nassertions OK: operational grid 10-30 min absorbs %.2f%%-%.2f%%; tau=60 absorbs %.2f%%"
      % (op_grid[0]["shortage_absorption_pct"], op_grid[-1]["shortage_absorption_pct"],
         h60["shortage_absorption_pct"]))
