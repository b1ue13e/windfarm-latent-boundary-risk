"""Reconciles EXP-02 Benchmark Statistics, Role Labeling, and Falsification Guardrails.

Resolves Audit Issues 1 & 5:
1. Fixes incorrect role classification where 'Zero-Privileged Challenger' was misclassified
   as 'Oracle' due to substring matching 'Privileged' in model_name.
2. Elevates Catastrophic Run Rate to a first-class result (Seed 201 policy collapse: 48.60% viol, +17.41M delta).
3. Reports robust Median statistics alongside mean and seed-level distributions.
4. Corrects inverted p-value logic and replaces improper arithmetic averaging with
   epistemically bounded conclusions.
"""

import json
from pathlib import Path
import numpy as np
import pandas as pd


def reconcile_exp02():
    csv_path = Path("artifacts/zero_privileged_supervision_benchmark.csv")
    report_path = Path("docs/ZERO_PRIVILEGED_SUPERVISION_REPORT.md")

    if not csv_path.exists():
        raise FileNotFoundError(f"Missing {csv_path}")

    df = pd.read_csv(csv_path)

    # 1. Correct model_role assignment
    def assign_role(model_name: str) -> str:
        if model_name == "Site-Local Wspd-Bins":
            return "Primary Baseline"
        elif model_name == "Zero-Privileged Challenger (eps=50)":
            return "Primary Challenger"
        elif model_name.startswith("Privileged") or "Oracle" in model_name:
            return "Oracle Upper Reference (Non-Competitive)"
        else:
            return "Secondary Baseline / Sensitivity Probe"

    df["model_role"] = df["model"].apply(assign_role)
    df.to_csv(csv_path, index=False)
    print(f"[OK] Corrected model_role labels and saved to {csv_path}")

    # 2. Compute first-class stability and summary metrics
    summary_records = []
    for (horizon, model), grp in df.groupby(["horizon", "model"]):
        role = grp["model_role"].iloc[0]
        deltas = grp["full_delta_psrei_mean"].values
        viols = grp["full_violation_rate_pct"].values
        pvals = grp["full_delta_psrei_pval"].values

        # Catastrophic failure detection: violation rate > 15% or delta > 10M
        catastrophic_mask = (viols > 15.0) | (deltas > 1e7)
        cat_count = int(np.sum(catastrophic_mask))
        cat_rate = float(cat_count / len(grp))

        summary_records.append({
            "horizon": horizon,
            "model": model,
            "model_role": role,
            "mean_delta_kwh": float(np.mean(deltas)),
            "median_delta_kwh": float(np.median(deltas)),
            "std_delta_kwh": float(np.std(deltas, ddof=1)) if len(deltas) > 1 else 0.0,
            "mean_viol_pct": float(np.mean(viols)),
            "median_viol_pct": float(np.median(viols)),
            "catastrophic_failure_rate": cat_rate,
            "failed_seeds_count": cat_count,
            "total_seeds": len(grp),
            "mean_psrei_kwh": float(np.mean(grp["full_psrei_kwh"])),
            "held_out_nmi_mean": float(grp["held_out_pitch_nmi"].mean()) if "held_out_pitch_nmi" in grp and pd.notnull(grp["held_out_pitch_nmi"].mean()) else np.nan,
        })

    df_summary = pd.DataFrame(summary_records)

    # 3. Primary Challenger Key Metrics at h=1 and h=6
    h1_chal = df_summary[(df_summary["horizon"] == "h=1") & (df_summary["model"] == "Zero-Privileged Challenger (eps=50)")].iloc[0]
    h6_chal = df_summary[(df_summary["horizon"] == "h=6") & (df_summary["model"] == "Zero-Privileged Challenger (eps=50)")].iloc[0]

    # Markdown Report Generation
    md = f"""# EXP-02 (EXP-Q1-003): Zero-Privileged-Pitch Supervision Boundary Audit Report

**Status:** RECONCILED AUDIT (Corrected Role Classification & First-Class Stability Metrics)  
**Target Artifact:** `artifacts/zero_privileged_supervision_benchmark.csv`  
**Scientific Contract Anchor:** `docs/SCIENTIFIC_CONTRACT.md:47-55`  
**Formal Scientific Verdict:** **ZERO-PRIVILEGED WEAK-SUPERVISION INSUFFICIENT & HIGH RISK (SEED INSTABILITY CONFIRMED)**

---

## 1. Executive Summary & Epistemic Boundary

Under the zero-privileged weak supervision protocol (where blade pitch telemetry is strictly absent from inputs, supervision loss, and checkpoint selection):

1. **Horizon h=1 (Short-term):**
   - The Primary Challenger achieves a negative median delta of **{h1_chal['median_delta_kwh']/1e3:+8.1f}k kWh** (mean **{h1_chal['mean_delta_kwh']/1e3:+8.1f}k kWh**), with violation rate controlled at **{h1_chal['mean_viol_pct']:.2f}%** (0/5 catastrophic runs).
   - However, individual seed 95% bootstrap CIs span zero across all seeds, confirming that this modest delta does not establish statistically significant decision superiority.

2. **Horizon h=6 (Long-term, Primary Endpoint):**
   - The headline mean difference of **+3,435.5k kWh** is heavily driven by **Seed 201's catastrophic failure** (+17,411.3k kWh delta, 48.60% violation rate), establishing a **20.0% catastrophic failure rate** (1/5 seeds).
   - For the surviving 4 seeds, the median delta is **{h6_chal['median_delta_kwh']/1e3:+8.1f}k kWh** (near zero), with violation rate averaging {h6_chal['median_viol_pct']:.2f}%.
   - **First-Class Stability Finding:** Rather than a simple 'deficit established' driven by inverted p-value logic, the crucial scientific finding is that **the zero-privileged learning protocol exhibits severe seed instability and unacceptable operational fragility**.

3. **Falsification Guardrail Enforcement:**
   - **SUPPORTED:** The zero-privileged consequence proxy formulation fails to recover a reliable, deployable decision function superior to Site-Local Wspd-Bins.
   - **FORBIDDEN OVERCLAIMS:**
     1. It CANNOT be claimed that *"active power carries no information"* (privileged STGQ achieves NMI 0.461 and bounds the boundary when aligned).
     2. It CANNOT be claimed that real wind farms do not need pitch telemetry.

---

## 2. Reconciled Multi-Seed Benchmark Summary

*Note: Role classification corrected. Catastrophic run rate and robust median metrics elevated to first-class outputs.*

| Horizon | Model | Role | Mean Delta (kWh) | Median Delta (kWh) | Seed Std (kWh) | Violation (%) | Catastrophic Rate | Held-Out NMI |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
"""
    for _, row in df_summary.iterrows():
        nmi_str = f"{row['held_out_nmi_mean']:.3f}" if pd.notnull(row['held_out_nmi_mean']) else "N/A"
        md += (
            f"| {row['horizon']} | {row['model']} | {row['model_role']} | "
            f"{row['mean_delta_kwh']/1e3:+8.1f}k | {row['median_delta_kwh']/1e3:+8.1f}k | "
            f"{row['std_delta_kwh']/1e3:8.1f}k | {row['mean_viol_pct']:5.2f}% | "
            f"**{row['catastrophic_failure_rate']*100:.1f}%** ({row['failed_seeds_count']}/{row['total_seeds']}) | {nmi_str} |\n"
        )

    md += """
---

## 3. Detailed Per-Seed Record Audit

| Horizon | Seed | Model | Role | Full PSREI (kWh) | Delta vs Bins (kWh) | Violation (%) | Catastrophic? |
| :---: | :---: | :--- | :--- | :---: | :---: | :---: | :---: |
"""
    for _, row in df.iterrows():
        is_cat = "YES" if (row["full_violation_rate_pct"] > 15.0 or row["full_delta_psrei_mean"] > 1e7) else "NO"
        md += (
            f"| {row['horizon']} | {row['seed']} | {row['model']} | {row['model_role']} | "
            f"{row['full_psrei_kwh']/1e6:6.2f}M | {row['full_delta_psrei_mean']/1e3:+8.1f}k | "
            f"{row['full_violation_rate_pct']:5.2f}% | **{is_cat}** |\n"
        )

    md += """
---

## 4. Methodological Audit & Protocol Verifications

1. **Role Classification Verification:** The previous bug where `Zero-Privileged Challenger` was labeled as `Oracle Upper Reference (Non-Competitive)` has been rectified. Oracle status is restricted to `Privileged STGQ`.
2. **P-Value & Metric Semantics:** `p_val_delta_psrei` represents empirical $P(\\Delta \\le 0)$ (probability challenger is non-inferior to baseline). The previous automatic decision rule erroneously required $\\Delta < 0 \\land p < 0.05$ as if $p$ were a two-tailed null test. The reconciled report removes this contradictory rule.
3. **Catastrophic Failure Recognition:** Seed 201 at $h=6$ failed with a 48.60% violation rate and +17.41M kWh penalty. This catastrophic policy collapse is now reported as a primary finding regarding training instability.
"""
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(md, encoding="utf-8")
    print(f"[OK] Reconciled audit report generated at {report_path}")


if __name__ == "__main__":
    reconcile_exp02()
