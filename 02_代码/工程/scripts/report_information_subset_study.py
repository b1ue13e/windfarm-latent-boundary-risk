"""Export the frozen study's full tables and learning curves from real results."""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from repo_paths import Path, repository_root
import platform
import sys

import numpy as np


def sha(p):
    h = hashlib.sha256()
    with Path(p).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def rows_from_result(result):
    rows, frontiers = [], []
    for group in result["results"]:
        picked = {p["index"]: p["qualified"] for p in group["historical_choices"]}
        risk = np.asarray(group["risk_point"])
        lower, upper = np.asarray(group["risk_lower"]), np.asarray(group["risk_upper"])
        for i, label in enumerate(group["labels"]):
            subset, estimator, n, q = label.split("/")
            rows.append(dict(span_days=group["span"], condition=group["condition"], group_budget=group["budget"],
                             policy=label, subset=subset, estimator=estimator, fit_rows=int(n[1:]), offset_q=float(q[1:]),
                             historical_selected=i in picked, historical_qualified=picked.get(i, False),
                             mean_cost_kwh=group["mean_cost"][i], cost_marginal_ci_lower=group["mean_cost_ci_low"][i],
                             cost_marginal_ci_upper=group["mean_cost_ci_high"][i],
                             max_instance_risk=float(risk[:, i].max()), joint_max_instance_risk_lower=float(lower[:, i].max()),
                             joint_max_instance_risk_upper=float(upper[:, i].max())))
        for field in ("primary_historical_recipe", "secondary_retrospective_grid"):
            labels = ([p["label"] for p in group["historical_choices"]] if field.startswith("primary") else group["labels"])
            for identified in group[field]:
                frontiers.append(dict(span_days=group["span"], condition=group["condition"], group_budget=group["budget"],
                      analysis=field, epsilon=identified["epsilon"], status=identified["status"],
                      minimum_resource_policies=";".join(labels[i] for i in identified["minimum_resource_indices"])))
    return rows, frontiers


def write_csv(path, rows):
    with Path(path).open("x", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def plot_curves(rows, output):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8, "axes.spines.top": False,
                         "axes.spines.right": False, "pdf.fonttype": 42, "svg.fonttype": "none"})
    picked = [r for r in rows if r["condition"] == "pitch_withheld" and r["span_days"] == 3 and r["historical_selected"] and r["estimator"] != "Persistence"]
    subsets = list(dict.fromkeys(r["subset"] for r in picked))
    for metric, low, high, label, filename in [
            ("mean_cost_kwh", "cost_marginal_ci_lower", "cost_marginal_ci_upper", "Cost (kWh / valid turbine interval)", "cost_sample_curves"),
            ("max_instance_risk", "joint_max_instance_risk_lower", "joint_max_instance_risk_upper", "Maximum instance violation rate", "risk_sample_curves")]:
        fig, axes = plt.subplots(6, 4, figsize=(11.7, 13.0), layout="constrained")
        for ax, subset in zip(axes.flat, subsets):
            for estimator, color, marker, style in [("HGB", "#0072B2", "o", "-"), ("MLP", "#D55E00", "^", "--")]:
                data = sorted((r for r in picked if r["subset"] == subset and r["estimator"] == estimator), key=lambda r: r["fit_rows"])
                x = np.array([r["fit_rows"] for r in data]) / 1000
                y = np.array([r[metric] for r in data])
                ax.plot(x, y, color=color, marker=marker, linestyle=style, label=estimator, markersize=3, linewidth=1)
                ax.fill_between(x, [r[low] for r in data], [r[high] for r in data], color=color, alpha=.13)
                failed = np.array([not r["historical_qualified"] for r in data])
                ax.scatter(x[failed], y[failed], marker="x", color="black", s=30, linewidth=.8, zorder=5)
            ax.set_title(subset, loc="left", fontsize=9)
            ax.set_xscale("log")
            ax.set_xticks([10, 40, 120, 360], labels=["10", "40", "120", "360"])
            ax.grid(axis="y", alpha=.2, linewidth=.5)
            if metric == "max_instance_risk":
                ax.axhline(.1, color="#555555", linestyle=":", linewidth=.7)
        for ax in list(axes.flat)[len(subsets):]:
            ax.set_visible(False)
        axes.flat[0].legend(frameon=False, fontsize=8)
        fig.supxlabel("Training rows (thousands); shared nested prefixes, fixed calendar coverage")
        fig.supylabel(label)
        caption = "Historical q choices; x = history not risk-qualified. "
        caption += "Bands: marginal 95% shared-day bootstrap cost intervals." if metric == "mean_cost_kwh" else "Bands: simultaneous approximate risk bounds."
        fig.suptitle("Previously inspected WTB development; no independent confirmation\n" + caption, fontsize=10)
        fig.savefig(output / (filename + ".pdf"))
        fig.savefig(output / (filename + ".png"), dpi=200)
        plt.close(fig)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    before = sha(args.input)
    result = json.loads(args.input.read_text(encoding="utf-8"))
    if result["status"] != "DEVELOPMENT_ONLY" or result["deployment_certified"]:
        raise ValueError("Unexpected evidence status")
    args.output.mkdir(exist_ok=False, parents=True)
    rows, frontiers = rows_from_result(result)
    write_csv(args.output / "all_policies.csv", rows)
    write_csv(args.output / "historical_learning_curves.csv", [r for r in rows if r["historical_selected"]])
    write_csv(args.output / "frontiers.csv", frontiers)
    plot_curves(rows, args.output)
    if sha(args.input) != before:
        raise ValueError("Input changed")
    (args.output / "receipt.json").write_text(json.dumps(dict(input_sha256=before, source_sha256=sha(__file__),
          finished_utc=datetime.now(timezone.utc).isoformat(), python=sys.version, host=platform.node(),
          argv=sys.argv, note="Derived development tables/plots only; all rows retained; no candidate retuning"), indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
