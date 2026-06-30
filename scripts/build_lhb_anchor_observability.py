from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
IN_DIR = ROOT / "artifacts" / "external_wind_lhb_anchor_intervention_full"
OUT_DIR = ROOT / "artifacts" / "external_wind_lhb_anchor_intervention_full"

KEY_ROWS = [
    "actual",
    "anchor_pab_zero",
    "anchor_wspd_zero",
    "anchor_patv_zero",
    "anchor_boundary_zero",
    "anchor_random_physics",
    "anchor_wspd_only",
    "anchor_pab_only",
]


def _fmt(value: float, digits: int = 3) -> str:
    return f"{float(value):.{digits}f}"


def main() -> None:
    summary = pd.read_csv(IN_DIR / "mechanism_intervention_summary.csv")
    effects = pd.read_csv(IN_DIR / "mechanism_intervention_effects.csv")
    summary = summary.set_index("intervention")
    effects = effects.set_index("intervention")

    actual_nmi = float(summary.loc["actual", "nmi_mean"])
    pab_zero_nmi = float(summary.loc["anchor_pab_zero", "nmi_mean"])
    wspd_zero_nmi = float(summary.loc["anchor_wspd_zero", "nmi_mean"])
    patv_zero_nmi = float(summary.loc["anchor_patv_zero", "nmi_mean"])
    boundary_zero_nmi = float(summary.loc["anchor_boundary_zero", "nmi_mean"])
    random_nmi = float(summary.loc["anchor_random_physics", "nmi_mean"])

    guard = {
        "status": "complete_anchor_observability_audited",
        "claim_gate": "anchor_observable_positive_control_not_anchor_free_discovery",
        "n_runs": int(summary.loc["actual", "n_runs"]),
        "actual_nmi_mean": actual_nmi,
        "pab_zero_nmi_mean": pab_zero_nmi,
        "wspd_zero_nmi_mean": wspd_zero_nmi,
        "patv_zero_nmi_mean": patv_zero_nmi,
        "boundary_zero_nmi_mean": boundary_zero_nmi,
        "random_physics_nmi_mean": random_nmi,
        "drop_nmi_boundary_zero_mean": float(effects.loc["anchor_boundary_zero", "drop_nmi_mean"]),
        "drop_nmi_random_physics_mean": float(effects.loc["anchor_random_physics", "drop_nmi_mean"]),
        "checks": {
            "actual_replays_reference": bool(abs(actual_nmi - 0.9408064155015372) < 1e-9),
            "patv_not_load_bearing": bool(abs(patv_zero_nmi - actual_nmi) < 0.05),
            "pab_or_wspd_alone_retains_partial_alignment": bool(pab_zero_nmi > 0.50 and wspd_zero_nmi > 0.50),
            "joint_boundary_anchor_is_load_bearing": bool(boundary_zero_nmi < 0.05),
            "randomized_anchor_collapses_alignment": bool(random_nmi < 0.10),
        },
        "claim_use": (
            "La Haute Borne should be described as an anchor-observable positive-control replication. "
            "The replay audit rules out active-power feedback as the driver and shows that Wspd/Pab boundary anchors, "
            "jointly, are load-bearing; it does not support anchor-free discovery wording."
        ),
    }
    guard["checks"]["all_checks_pass"] = bool(all(guard["checks"].values()))
    (OUT_DIR / "lhb_anchor_observability_guard.json").write_text(json.dumps(guard, indent=2), encoding="utf-8")

    rows = []
    for name in KEY_ROWS:
        rows.append(
            {
                "intervention": name,
                "nmi_mean": float(summary.loc[name, "nmi_mean"]),
                "ari_mean": float(summary.loc[name, "ari_mean"]),
                "drop_nmi_mean": 0.0 if name == "actual" else float(effects.loc[name, "drop_nmi_mean"]),
                "dominant_flip_rate_mean": float(summary.loc[name, "dominant_flip_rate_mean"]),
            }
        )
    compact = pd.DataFrame(rows)
    compact.to_csv(OUT_DIR / "lhb_anchor_observability_compact.csv", index=False)

    lines = [
        r"\begin{table}[H]",
        r"\centering",
        r"\scriptsize",
        r"\setlength{\tabcolsep}{4pt}",
        r"\renewcommand{\arraystretch}{1.05}",
        r"\caption*{\textbf{Table A9.} La Haute Borne anchor-observability replay audit.}",
        r"\begin{tabular}{lccc}",
        r"\toprule",
        r"Replay condition & NMI & $\Delta$NMI & Interpretation \\",
        r"\midrule",
    ]
    labels = {
        "actual": ("Actual replay", "reference"),
        "anchor_pab_zero": ("Zero pitch anchor", "partial alignment remains"),
        "anchor_wspd_zero": ("Zero wind-speed anchor", "partial alignment remains"),
        "anchor_patv_zero": ("Zero active-power anchor", "not load-bearing"),
        "anchor_boundary_zero": ("Zero wind+pitch anchors", "alignment collapses"),
        "anchor_random_physics": ("Randomize anchor physics", "alignment collapses"),
        "anchor_wspd_only": ("Wind-speed only", "single-anchor partial control"),
        "anchor_pab_only": ("Pitch only", "single-anchor partial control"),
    }
    for row in rows:
        label, interp = labels[row["intervention"]]
        lines.append(
            f"{label} & {_fmt(row['nmi_mean'])} & {_fmt(row['drop_nmi_mean'])} & {interp} " + r"\\"
        )
    lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}", ""])
    (OUT_DIR / "table_lhb_anchor_observability.tex").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(guard, indent=2))


if __name__ == "__main__":
    main()
