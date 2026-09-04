"""P1 statistical hardening: median/IQR for farm signature probes, per-seed
pass-rates for the window scan, and time-block bootstrap CIs for the reserve
audit.

Outputs:
  - farm_median_iqr.csv        median/IQR for every farm/variant NMI
  - window_scan_pass_rate.csv  per-seed pass-rate for the window scan
  - time_block_bootstrap.csv   week-block bootstrap CI for gate-bin vs global
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(".")


def farm_median_iqr() -> pd.DataFrame:
    rows = []
    suites = {
        "WTB": ("artifacts/signature_gate_guard_20260901/anchor_stress_run_status.csv", "wtb"),
        "LHB": ("artifacts/signature_gate_lhb_guard_20260902/anchor_stress_run_status.csv", "lhb"),
        "Penmanshiel": ("artifacts/signature_gate_farms_guard_20260903/penmanshiel/anchor_stress_run_status.csv", "pen"),
        "Kelmarsh": ("artifacts/signature_gate_farms_guard_20260903/kelmarsh/anchor_stress_run_status.csv", "kel"),
        "Penmanshiel-sec": ("artifacts/signature_gate_farms_guard_20260903/penmanshiel_sec/anchor_stress_run_status.csv", "pen_sec"),
        "Penmanshiel-rand": ("artifacts/signature_gate_farms_guard_20260903/penmanshiel_rand/anchor_stress_run_status.csv", "pen_rand"),
        "Kelmarsh-sec": ("artifacts/signature_gate_farms_guard_20260903/kelmarsh_sec/anchor_stress_run_status.csv", "kel_sec"),
        "Kelmarsh-rand": ("artifacts/signature_gate_farms_guard_20260903/kelmarsh_rand/anchor_stress_run_status.csv", "kel_rand"),
    }
    for farm, (path, _key) in suites.items():
        p = ROOT / path
        if not p.exists():
            continue
        df = pd.read_csv(p)
        for variant, group in df.groupby("variant"):
            nmi = pd.to_numeric(group["nmi"], errors="coerce").dropna()
            if nmi.empty:
                continue
            rows.append({
                "farm": farm,
                "variant": variant,
                "n_seeds": int(nmi.size),
                "nmi_mean": float(nmi.mean()),
                "nmi_std": float(nmi.std(ddof=0)),
                "nmi_median": float(nmi.median()),
                "nmi_q25": float(nmi.quantile(0.25)),
                "nmi_q75": float(nmi.quantile(0.75)),
                "nmi_min": float(nmi.min()),
                "nmi_max": float(nmi.max()),
            })
    out = pd.DataFrame(rows)
    out.to_csv(ROOT / "artifacts" / "p1_stats_20260904" / "farm_median_iqr.csv", index=False)
    return out


def window_pass_rate() -> pd.DataFrame:
    rows = []
    suites = {
        "Penmanshiel-sec": "artifacts/signature_gate_farms_guard_20260903/penmanshiel_sec/anchor_stress_run_status.csv",
        "Penmanshiel-rand": "artifacts/signature_gate_farms_guard_20260903/penmanshiel_rand/anchor_stress_run_status.csv",
        "Kelmarsh-sec": "artifacts/signature_gate_farms_guard_20260903/kelmarsh_sec/anchor_stress_run_status.csv",
        "Kelmarsh-rand": "artifacts/signature_gate_farms_guard_20260903/kelmarsh_rand/anchor_stress_run_status.csv",
    }
    for farm, path in suites.items():
        df = pd.read_csv(ROOT / path)
        nmi = pd.to_numeric(df["nmi"], errors="coerce").dropna()
        passed = (nmi >= 0.20).sum()
        rows.append({
            "farm": farm,
            "n_seeds": int(nmi.size),
            "n_pass": int(passed),
            "pass_rate": float(passed / max(nmi.size, 1)),
        })
    out = pd.DataFrame(rows)
    out.to_csv(ROOT / "artifacts" / "p1_stats_20260904" / "window_scan_pass_rate.csv", index=False)
    return out


def time_block_bootstrap() -> pd.DataFrame:
    daily = pd.read_csv(
        ROOT / "artifacts" / "decision_reserve_trainweight_allclean_20260830" / "reserve_decision_daily_costs.csv"
    )
    rows = []
    for model in ["Boundary-forced router", "Physics-Aligned MoE"]:
        sub = daily[(daily["model"] == model) & (daily["cost_ratio"] == 10.0)]
        for seed in sorted(sub["seed"].unique()):
            s = sub[sub["seed"] == seed]
            gate = s[s["policy"] == "gate-bin"].sort_values("day")["daily_cost"].to_numpy()
            glob = s[s["policy"] == "global"].sort_values("day")["daily_cost"].to_numpy()
            n = min(len(gate), len(glob))
            diff = gate[:n] - glob[:n]
            # week-block bootstrap (6-day blocks ~ 1 week at 144 slots/day? days are indices)
            block = 7
            n_blocks = n // block
            blocks = diff[: n_blocks * block].reshape(n_blocks, block).sum(axis=1)
            rng = np.random.default_rng(20260904 + seed)
            boots = rng.choice(blocks, size=(20000, n_blocks), replace=True).sum(axis=1)
            rows.append({
                "model": model,
                "seed": int(seed),
                "n_days": int(n),
                "observed_delta": float(diff.sum()),
                "week_block_ci_low": float(np.percentile(boots, 2.5)),
                "week_block_ci_high": float(np.percentile(boots, 97.5)),
            })
    out = pd.DataFrame(rows)
    out.to_csv(ROOT / "artifacts" / "p1_stats_20260904" / "time_block_bootstrap.csv", index=False)
    print(out.to_string(index=False))
    return out


def main() -> None:
    out_dir = ROOT / "artifacts" / "p1_stats_20260904"
    out_dir.mkdir(parents=True, exist_ok=True)
    fm = farm_median_iqr()
    print("=== farm median/IQR ===")
    print(fm.to_string(index=False))
    print()
    wp = window_pass_rate()
    print("=== window pass-rate ===")
    print(wp.to_string(index=False))
    print()
    print("=== time-block bootstrap ===")
    time_block_bootstrap()
    print("P1_STATS_DONE")


if __name__ == "__main__":
    main()
