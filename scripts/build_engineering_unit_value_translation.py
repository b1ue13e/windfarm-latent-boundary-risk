from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from windfarm_moe.operational_cost import run_engineering_unit_value_translation

DECISION_DIR = ROOT / "artifacts" / "decision_reserve_wtb_operational_windows"
TOY_COST_DIR = ROOT / "artifacts" / "reserve_toy_operational_cost"
OUT_DIR = ROOT / "artifacts" / "final_evidence_package" / "export" / "tables"


def main() -> None:
    out_dir = run_engineering_unit_value_translation(
        decision_dir=DECISION_DIR,
        toy_cost_dir=TOY_COST_DIR,
        output_dir=OUT_DIR,
        main_ratio=10.0,
        reserve_prices_eur_per_mwh=[50.0, 100.0, 200.0],
    )
    print(f"Wrote {out_dir / 'engineering_unit_value_translation.csv'}")


if __name__ == "__main__":
    main()
