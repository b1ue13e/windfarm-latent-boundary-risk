"""Joint uncertainty and stability report generator (EXP-01 & EXP-02).

SCOPE LIMIT (corrected 2026-10-13): this script resamples SEED-LEVEL mean deltas
only. It does NOT perform a two-level (seed x day-cluster) hierarchical bootstrap,
and its intervals must not be described as such. The frozen benchmark CSV does not
persist per-seed block-level delta arrays, so a true two-level joint interval is
not reproducible from the archived CSV alone; producing one requires re-running
the benchmark with `--output-blocks`. Intervals written by this script are
therefore labelled `seed_level_ci_95` and the report states the limitation.

Also corrects the outcome field naming: `P(delta <= 0)` is an empirical
NON-INFERIORITY probability (PSREI is a cost), not a two-sided p-value.

Outputs artifacts/joint_uncertainty_summary.json and
docs/JOINT_UNCERTAINTY_AUDIT_REPORT.md.
"""

import json
from pathlib import Path
import numpy as np
import pandas as pd


def seed_level_bootstrap_from_records(
    deltas: np.ndarray,
    n_boot: int = 5000,
    random_seed: int = 42,
) -> dict:
    """Bootstrap the MEAN over seeds by resampling the seed-level deltas.

    This is a one-level (seed-only) bootstrap. With n_seeds = 5 the resampled
    distribution is coarse, and the interval reflects between-seed variability
    only -- it does not represent day-cluster (within-seed) uncertainty.

    Args:
        deltas: 1D array of seed-level mean deltas (n_seeds,)
    """
    rng = np.random.default_rng(random_seed)
    n_seeds = len(deltas)
    if n_seeds == 0:
        return {}

    # Resample seeds with replacement
    seed_boot = rng.choice(deltas, size=(n_boot, n_seeds), replace=True).mean(axis=1)

    ci_low = float(np.quantile(seed_boot, 0.025))
    ci_high = float(np.quantile(seed_boot, 0.975))
    # P(delta <= 0): for a COST metric, higher = challenger non-inferior.
    p_non_inferior = float(np.mean(seed_boot <= 0.0))

    return {
        "mean_delta_kwh": float(np.mean(deltas)),
        "median_delta_kwh": float(np.median(deltas)),
        "seed_std_kwh": float(np.std(deltas, ddof=1)) if n_seeds > 1 else 0.0,
        "seed_level_ci_95": [ci_low, ci_high],
        "p_non_inferior": p_non_inferior,
        "seed_values": [float(x) for x in deltas],
        "uncertainty_scope": "seed_level_only",
        "n_seeds": int(n_seeds),
    }


# Backwards-compatible alias: external callers/tests may import the old name.
hierarchical_bootstrap_from_records = seed_level_bootstrap_from_records


def main():
    root = Path(".")
    exp01_csv = root / "artifacts/external_matched_control_benchmark.csv"
    exp02_csv = root / "artifacts/zero_privileged_supervision_benchmark.csv"
    out_json = root / "artifacts/joint_uncertainty_summary.json"
    out_md = root / "docs/JOINT_UNCERTAINTY_AUDIT_REPORT.md"

    results_all = {}

    # =========================================================================
    # 1. EXP-01 Audit: External-Farm Matched Benchmark
    # =========================================================================
    if exp01_csv.exists():
        df1 = pd.read_csv(exp01_csv)
        exp01_summary = []

        for (farm, horizon, model), grp in df1.groupby(["farm", "horizon", "model"]):
            if model == "Site-Local Wspd-Bins":
                continue
            deltas = grp["delta_psrei_mean_kwh"].values
            viols = grp["violation_rate_pct"].values

            stats = hierarchical_bootstrap_from_records(deltas)
            stats["farm"] = farm
            stats["horizon"] = horizon
            stats["model"] = model
            stats["mean_viol_pct"] = float(np.mean(viols))
            stats["median_viol_pct"] = float(np.median(viols))

            # Catastrophic run check
            cat_count = int(np.sum((viols > 20.0) | (deltas > 1.5e7)))
            stats["catastrophic_rate"] = float(cat_count / len(grp))
            stats["catastrophic_count"] = cat_count
            stats["n_seeds"] = len(grp)

            exp01_summary.append(stats)

        results_all["EXP-01"] = exp01_summary

    # =========================================================================
    # 2. EXP-02 Audit: Zero-Privileged Supervision Benchmark
    # =========================================================================
    if exp02_csv.exists():
        df2 = pd.read_csv(exp02_csv)
        exp02_summary = []

        for (horizon, model), grp in df2.groupby(["horizon", "model"]):
            if model == "Site-Local Wspd-Bins":
                continue
            deltas = grp["full_delta_psrei_mean"].values
            viols = grp["full_violation_rate_pct"].values
            role = grp["model_role"].iloc[0]

            stats = hierarchical_bootstrap_from_records(deltas)
            stats["horizon"] = horizon
            stats["model"] = model
            stats["role"] = role
            stats["mean_viol_pct"] = float(np.mean(viols))
            stats["median_viol_pct"] = float(np.median(viols))

            cat_count = int(np.sum((viols > 15.0) | (deltas > 1e7)))
            stats["catastrophic_rate"] = float(cat_count / len(grp))
            stats["catastrophic_count"] = cat_count
            stats["n_seeds"] = len(grp)

            exp02_summary.append(stats)

        results_all["EXP-02"] = exp02_summary

    # Save JSON summary
    out_json.parent.mkdir(parents=True, exist_ok=True)
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(results_all, f, indent=2)
    print(f"[OK] Generated {out_json}")

    # =========================================================================
    # 3. Generate Authoritative Markdown Report
    # =========================================================================
    md = f"""# Joint Uncertainty & Stability Audit Report (EXP-01 & EXP-02)

**Audit Date:** 2026-10-13
**Purpose:** Records joint stability analysis for EXP-01 and EXP-02.
**Governing Standard:** `docs/SCIENTIFIC_CONTRACT.md`

**Method and scope (corrected 2026-10-13):**
- **Uncertainty procedure:** one-level **seed-resampling** bootstrap over the 5
  model seeds. With n = 5 this is coarse and captures between-seed variability
  only. It is **not** a two-level (seed x day-cluster) hierarchical bootstrap, and
  the intervals below are labelled `seed-level` accordingly.
- **Reproducibility limit:** the archived benchmark CSV stores only seed-level
  summaries, so a true two-level joint interval cannot be reconstructed from it.
  `scripts/hierarchical_bootstrap.py` implements the two-level procedure and must
  be re-run against block-level deltas (`--output-blocks`) to produce one.
- **`P(Delta <= 0)` is a non-inferiority probability, not a two-sided p-value.**
  PSREI is a cost, so a HIGHER value indicates the challenger was cheaper or equal.
- **Stability and catastrophic runs:** catastrophic failure rate and robust
  medians are reported as first-class results alongside the mean.

---

## 1. EXP-01: External-Farm Matched Benchmark Joint Uncertainty

*Primary Endpoint:* $h=6$ Transferred STGQ-Modular vs. Site-Local Wspd-Bins on Penmanshiel and Kelmarsh.

| Farm | Horizon | Model | Median Delta (kWh) | Mean Delta (kWh) | Seed Std (kWh) | Seed-level 95% CI (kWh) | P(Delta <= 0) | Catastrophic Rate |
| :--- | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
"""
    if "EXP-01" in results_all:
        for r in results_all["EXP-01"]:
            ci_str = f"[{r['seed_level_ci_95'][0]/1e3:+8.1f}k, {r['seed_level_ci_95'][1]/1e3:+8.1f}k]"
            md += (
                f"| {r['farm']} | {r['horizon']} | {r['model']} | "
                f"{r['median_delta_kwh']/1e3:+8.1f}k | {r['mean_delta_kwh']/1e3:+8.1f}k | "
                f"{r['seed_std_kwh']/1e3:8.1f}k | {ci_str} | "
                f"{r['p_non_inferior']:.3f} | {r['catastrophic_rate']*100:.1f}% ({r['catastrophic_count']}/{r['n_seeds']}) |\n"
            )

    def _ci(r):
        lo, hi = r["seed_level_ci_95"]
        return f"[{lo/1e3:+,.1f}k, {hi/1e3:+,.1f}k]"

    def _crosses_zero(r):
        lo, hi = r["seed_level_ci_95"]
        return lo <= 0.0 <= hi

    md += "\n### Key Scientific Findings for EXP-01 (derived from the table above):\n"
    if "EXP-01" in results_all:
        for r in results_all["EXP-01"]:
            read = (
                "no advantage established (interval crosses zero)"
                if _crosses_zero(r)
                else ("cost penalty" if r["mean_delta_kwh"] > 0 else "cost advantage")
            )
            md += (
                f"- **{r['farm']} {r['horizon']} ({r['model']}):** median "
                f"{r['median_delta_kwh']/1e3:+,.1f}k kWh, mean {r['mean_delta_kwh']/1e3:+,.1f}k kWh, "
                f"seed-level 95% CI {_ci(r)} kWh, P(Delta <= 0) = {r['p_non_inferior']:.3f} "
                f"-> {read}; catastrophic rate {r['catastrophic_rate']*100:.1f}% "
                f"({r['catastrophic_count']}/{r['n_seeds']}).\n"
            )
    md += (
        "\n*Note:* No-Graph Architectural Control is an unmatched 4,865-parameter control; "
        "its cost penalties do not establish causal necessity of spatial graph structure "
        "(see `docs/NO_GRAPH_CONTROL_AUDIT.md`).\n"
    )

    md += r"""
---

## 2. EXP-02: Zero-Privileged Supervision Benchmark Joint Uncertainty

*Primary Endpoint:* $h=6$ Zero-Privileged Challenger ($\epsilon=50$ kW) vs. Site-Local Wspd-Bins under strict pitch withholding.

| Horizon | Model | Role | Median Delta (kWh) | Mean Delta (kWh) | Seed Std (kWh) | Seed-level 95% CI (kWh) | P(Delta <= 0) | Catastrophic Rate |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
"""
    if "EXP-02" in results_all:
        for r in results_all["EXP-02"]:
            ci_str = f"[{r['seed_level_ci_95'][0]/1e3:+8.1f}k, {r['seed_level_ci_95'][1]/1e3:+8.1f}k]"
            md += (
                f"| {r['horizon']} | {r['model']} | {r['role']} | "
                f"{r['median_delta_kwh']/1e3:+8.1f}k | {r['mean_delta_kwh']/1e3:+8.1f}k | "
                f"{r['seed_std_kwh']/1e3:8.1f}k | {ci_str} | "
                f"{r['p_non_inferior']:.3f} | {r['catastrophic_rate']*100:.1f}% ({r['catastrophic_count']}/{r['n_seeds']}) |\n"
            )

    md += "\n### Key Scientific Findings for EXP-02 (derived from the table above):\n"
    if "EXP-02" in results_all:
        for r in results_all["EXP-02"]:
            md += (
                f"- **Horizon {r['horizon']} ({r['model']}):** median "
                f"{r['median_delta_kwh']/1e3:+,.1f}k kWh, mean {r['mean_delta_kwh']/1e3:+,.1f}k kWh, "
                f"seed-level 95% CI {_ci(r)} kWh, P(Delta <= 0) = {r['p_non_inferior']:.3f}, "
                f"catastrophic rate {r['catastrophic_rate']*100:.1f}% "
                f"({r['catastrophic_count']}/{r['n_seeds']}).\n"
            )
        h6 = None
        for r in results_all["EXP-02"]:
            if str(r.get("horizon")) == "6" and "eps=50" in str(r.get("model")):
                h6 = r
                break
        if h6:
            worst = max(h6["seed_values"])
            widx = h6["seed_values"].index(worst)
            md += (
                f"\n**Stability reading.** The h=6 mean ({h6['mean_delta_kwh']/1e3:+,.1f}k kWh) is not a "
                f"central tendency: the seed-level median is {h6['median_delta_kwh']/1e3:+,.1f}k kWh, and "
                f"the mean is dominated by the worst seed (Seed {201 + widx}: {worst:+,.0f} kWh). "
                f"With only {h6['n_seeds']} seeds the seed-only interval is coarse, so the median is the "
                f"more robust summary.\n"
            )
    md += (
        "\n**Bounded conclusion.** Under the zero-privileged protocol, no stable decision "
        "advantage over simple local wind-speed conditioning is established. The h=1 point "
        "estimate is favourable but statistically inconclusive; h=6 shows a mean driven by one "
        "catastrophic seed rather than a consistent deficit. This is not evidence that "
        "consequence signals carry no mutual information.\n"
    )


    md += """
---

## 3. Disaggregated Seed Data Matrix

### EXP-01 Seed Values (Delta PSREI in kWh):
"""
    if "EXP-01" in results_all:
        for r in results_all["EXP-01"]:
            seed_strs = [f"Seed {201+i}: {round(v):+d}" for i, v in enumerate(r['seed_values'])]
            md += f"- **{r['farm']} {r['horizon']} ({r['model']}):** {', '.join(seed_strs)}\n"

    md += """
### EXP-02 Seed Values (Delta PSREI in kWh):
"""
    if "EXP-02" in results_all:
        for r in results_all["EXP-02"]:
            seed_strs = [f"Seed {201+i}: {round(v):+d}" for i, v in enumerate(r['seed_values'])]
            md += f"- **{r['horizon']} ({r['model']}):** {', '.join(seed_strs)}\n"

    md += """
---
*Generated by scripts/generate_joint_uncertainty_report.py (seed-level bootstrap).*
"""
    out_md.write_text(md, encoding="utf-8")
    print(f"[OK] Generated {out_md}")


if __name__ == "__main__":
    main()
