import pandas as pd
import numpy as np
from pathlib import Path

csv_path = Path("artifacts/exp03_async/psrei_vs_delay.csv")
df = pd.read_csv(csv_path)

print(f"Loaded {len(df)} rows from {csv_path}")

for h in ["h=1", "h=6"]:
    sub = df[df["horizon"] == h]
    print(f"\n==================== HORIZON: {h} ====================")
    agg = sub.groupby("delay_tau").agg({
        "delay_minutes": "first",
        "baseline_psrei": "mean",
        "challenger_psrei": "mean",
        "delta_psrei_mean": "mean",
        "delta_psrei_ci_lower": "mean",
        "delta_psrei_ci_upper": "mean",
        "baseline_viol_pct": "mean",
        "challenger_viol_pct": "mean",
        "p_val": "mean",
    }).reset_index()
    
    # Critical threshold tau*: smallest delay where 95% CI upper >= 0
    tau_star = None
    for _, r in agg.iterrows():
        if r["delta_psrei_ci_upper"] >= 0.0:
            tau_star = int(r["delay_tau"])
            break
    print(f"Critical threshold tau* ({h}): {tau_star} integer steps ({tau_star*10 if tau_star is not None else 'N/A'} min)")

    # 5%, 10%, 15% sensitivity crossings
    for tgt in [5.0, 10.0, 15.0]:
        c_delay = None
        for _, r in agg.iterrows():
            if r["challenger_viol_pct"] >= tgt:
                c_delay = int(r["delay_tau"])
                break
        print(f"  Operating target {tgt}% crossing ({h}): tau={c_delay if c_delay is not None else '>6'}")

    print("\nSummary Table:")
    for _, r in agg.iterrows():
        d = int(r["delay_tau"])
        m = int(r["delay_minutes"])
        b_p = r["baseline_psrei"] / 1e6
        c_p = r["challenger_psrei"] / 1e6
        d_p = r["delta_psrei_mean"] / 1e3
        ci_l = r["delta_psrei_ci_lower"] / 1e3
        ci_u = r["delta_psrei_ci_upper"] / 1e3
        p = r["p_val"]
        v_b = r["baseline_viol_pct"]
        v_c = r["challenger_viol_pct"]
        print(f"  tau={d} ({m:2d}m) | Base={b_p:6.2f}M | Chal={c_p:6.2f}M | Delta={d_p:+7.1f}k [{ci_l:+7.1f}k, {ci_u:+7.1f}k] | p={p:.3f} | V_base={v_b:5.2f}% | V_chal={v_c:5.2f}%")
