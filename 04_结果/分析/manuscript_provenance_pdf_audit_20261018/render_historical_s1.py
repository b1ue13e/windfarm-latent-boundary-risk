"""Render historical plotting literals without running their original producer."""
import ast
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "figures"
SOURCE = ROOT / "scripts/plot_rmse_vs_reserve_risk.py"
tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
assignment = next(n for n in tree.body if isinstance(n, ast.Assign)
                  and any(isinstance(t, ast.Name) and t.id == "models" for t in n.targets))
records = ast.literal_eval(assignment.value)
assert len(records) == 8
OUT.mkdir(exist_ok=True)
payload = {
    "source": str(SOURCE.relative_to(ROOT)),
    "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
    "status": "Historical plotting literals; not independently bound model outputs",
    "operation": "AST literal extraction and rendering only; no producer execution",
    "uncertainty": "Unavailable in the plotting records; no error bars invented",
    "records": records,
}
(OUT / "historical_plotting_records.json").write_text(
    json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
names = ["iTransformer", "Graph WaveNet", "Joint routed", "Frozen backbone + residual Q",
         "Boundary-forced router", "Missingness-aware GBDT", "Recalibrated physics", "Physical rule"]
colors = ["#000000", "#E69F00", "#56B4E9", "#009E73", "#0072B2", "#D55E00", "#CC79A7", "#777777"]
markers = ["o", "s", "^", "D", "v", "P", "X", "h"]
offsets = [(-8, 5), (-8, -10), (-13, -10), (6, 5), (5, 5), (6, 3), (-12, 7), (-12, -12)]
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8, "pdf.fonttype": 42})
fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.6))
fig.subplots_adjust(left=.09, right=.98, bottom=.34, top=.83, wspace=.32)
handles = []
for i, (row, name, color, marker, offset) in enumerate(zip(records, names, colors, markers, offsets), 1):
    for ax, key in zip(axes, ["shortage", "recall"]):
        handle = ax.scatter(row["rmse"], row[key], s=26, marker=marker,
                            facecolor="none" if i == 4 else color,
                            edgecolor=color if i == 4 else "black", linewidth=.7, zorder=3)
        label_offset = ((-12, -3) if i == 1 else (5, 5)) if key == "recall" and i <= 2 else offset
        ax.annotate(str(i), (row["rmse"], row[key]), xytext=label_offset,
                    textcoords="offset points", fontsize=7)
    handles.append(handle)
for ax, title, ylabel, limits in zip(
        axes, ["A  Historical shortage", "B  Historical recall"],
        ["Delay-6 shortage (MWh)", "Delay-6 regime recall"], [(0, 140), (0, .5)]):
    ax.set(xlim=(220, 292), ylim=limits, xlabel="Historical RMSE (kW)", ylabel=ylabel)
    ax.set_title(title, loc="left", fontsize=9)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", color=".88", linewidth=.5)
fig.suptitle("Historical plotting literals - execution binding unverified", fontsize=9, y=.97)
fig.legend(handles, [f"{i}  {name}" for i, name in enumerate(names, 1)],
           loc="lower center", bbox_to_anchor=(.5, .015), ncol=2, frameon=False, fontsize=7.3)
fig.savefig(OUT / "figure_s1_historical_literals.pdf")
fig.savefig(OUT / "figure_s1_historical_literals.png", dpi=300)
plt.close(fig)
