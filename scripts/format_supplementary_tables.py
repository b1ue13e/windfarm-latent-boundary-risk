import pandas as pd
from pathlib import Path

def fmt_num(v):
    return f"{int(round(v)):,}".replace(",", "{,}")

def fmt_pct(v):
    return f"{v*100:.2f}\\%"

root = Path("artifacts/clean_evidence_v2/risk_layer_benchmark")
h1_agg = pd.read_csv(root / "h1_lead1" / "cross_seed_aggregate.csv", header=[0,1])
h1_agg.columns = [c[0] if "Unnamed" in c[1] else f"{c[0]}_{c[1]}" for c in h1_agg.columns]

regimes = ["clean", "delay6", "sensor_noise", "markov_burst"]
regime_labels = {"clean": "Clean", "delay6": "Delay-6", "sensor_noise": "Noise", "markov_burst": "Markov"}
models = [
    "Continuous Physical Quantile",
    "Frozen Backbone MLP",
    "Global Quantile",
    "Joint Dense Head",
    "Joint Routed",
    "Missingness-Aware GBDT"
]

print("=== TABLE A11j ===")
lines_a11j = []
for reg in regimes:
    r_sub = h1_agg[h1_agg["regime"] == reg]
    reg_lbl = regime_labels[reg]
    first = True
    for m in models:
        m_row = r_sub[r_sub["model"] == m]
        if m_row.empty: continue
        c_m, c_s = m_row["total_cost_mean"].values[0], m_row["total_cost_std"].values[0]
        v_m, v_s = m_row["violation_rate_mean"].values[0], m_row["violation_rate_std"].values[0]
        r_m, r_s = m_row["total_reserve_mean"].values[0], m_row["total_reserve_std"].values[0]
        s_m, s_s = m_row["total_shortage_mean"].values[0], m_row["total_shortage_std"].values[0]
        p_m, p_s = m_row["pinball_loss_mean"].values[0], m_row["pinball_loss_std"].values[0]

        reg_ltx = f"\\textbf{{{reg_lbl}}}" if first else ""
        m_ltx = f"\\textbf{{{m} (Ours)}}" if m == "Joint Routed" else ("Frozen-Embedding Direct Quantile MLP" if "Frozen" in m else m)
        v_str = f"${fmt_pct(v_m)} \\pm {fmt_pct(v_s)}$" + ("^{\\dagger}" if v_m > 0.10 else "")
        c_str = f"${fmt_num(c_m)} \\pm {fmt_num(c_s)}$"
        if m == "Continuous Physical Quantile" and reg in ["clean", "markov_burst"]:
            c_str = f"$\\mathbf{{{fmt_num(c_m)} \\pm {fmt_num(c_s)}}}$"
        elif m == "Joint Routed" and reg in ["delay6", "sensor_noise"]:
            c_str = f"$\\mathbf{{{fmt_num(c_m)} \\pm {fmt_num(c_s)}}}$"

        r_str = f"${fmt_num(r_m)} \\pm {fmt_num(r_s)}$"
        s_str = f"${fmt_num(s_m)} \\pm {fmt_num(s_s)}$"
        p_str = f"${p_m:.2f} \\pm {p_s:.2f}$"
        lines_a11j.append(f"{reg_ltx} & {m_ltx} & {c_str} & {v_str} & {r_str} & {s_str} & {p_str} \\\\")
        first = False
    lines_a11j.append("\\midrule")

out_a11j = "\n".join(lines_a11j[:-1])
print(out_a11j)

print("\n=== TABLE A11k ===")
h1_paired = pd.read_csv(root / "h1_lead1" / "paired_significance.csv")
lines_a11k = []
for reg in regimes:
    r_sub = h1_paired[h1_paired["regime"] == reg]
    reg_lbl = regime_labels[reg]
    first = True
    for _, row in r_sub.iterrows():
        m = row["model"]
        delta = row["mean_cost_delta"]
        ci_lo = row["ci_95_lo"]
        ci_hi = row["ci_95_hi"]
        signif = row["significant_95"]
        p_val = row["p_value"]

        reg_ltx = f"\\textbf{{{reg_lbl}}}" if first else ""
        m_ltx = "Frozen-Embedding Direct Quantile MLP" if "Frozen" in m else m
        d_str = f"{'+' if delta > 0 else ''}{fmt_num(delta)}"
        ci_str = f"[{'+' if ci_lo > 0 else ''}{fmt_num(ci_lo)}, {'+' if ci_hi > 0 else ''}{fmt_num(ci_hi)}]"

        if delta > 0 and signif:
            verdict = f"Routed lower ($p = {p_val:.3f}$)"
        elif delta > 0:
            verdict = f"Statistical parity (CI crosses 0, $p = {p_val:.3f}$)"
        elif "Physical" in m and reg in ["delay6", "sensor_noise"]:
            verdict = f"Viol. Exceeded ($p = {p_val:.3f}$)"
        else:
            verdict = f"Baseline lower ($p = {p_val:.3f}$)"

        lines_a11k.append(f"{reg_ltx} & {m_ltx} & {d_str} & {ci_str} & {verdict} \\\\")
        first = False
    lines_a11k.append("\\midrule")

out_a11k = "\n".join(lines_a11k[:-1])
print(out_a11k)
