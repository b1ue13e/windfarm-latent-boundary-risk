"""TSTE figure redesign from saved records. No fitting or statistical inference."""
from pathlib import Path as NativePath
import sys
_PROJECT_ROOT = next(p for p in NativePath(__file__).resolve().parents if (p / "AGENTS.md").is_file())
sys.path.insert(0, str(_PROJECT_ROOT / "02_代码/工程"))
from repo_paths import Path, repository_root
import sys
import json
import calendar
import re
from xml.etree import ElementTree as ET
import numpy as np
import pandas as pd
import matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle, FancyBboxPatch, FancyArrowPatch
from matplotlib.lines import Line2D
from matplotlib.colors import TwoSlopeNorm, LinearSegmentedColormap
from matplotlib.transforms import ScaledTranslation

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "source_data/v2"
OUT = BASE / "figures/v14"
QA = BASE / "qa/figure_rebuild_v14"
OUT.mkdir(parents=True, exist_ok=True)
QA.mkdir(parents=True, exist_ok=True)
from audit_panel_alignment import require_matplotlib_panel_alignment

BLUE = "#146F86"
RUST = "#B8613E"
INK = "#263C48"
SLATE = "#7F929C"
GREY = "#CBD5DA"
PALE = "#EDF5F7"
SAND = "#F8EFE8"
EDGE = "#B8C9D1"
CMAP = LinearSegmentedColormap.from_list("Paired cost", [BLUE, "#FAFAF7", RUST])
mpl.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["Arial"], "font.size": 8,
    "axes.labelsize": 8, "axes.titlesize": 9, "xtick.labelsize": 7,
    "ytick.labelsize": 7, "legend.fontsize": 7.5, "axes.spines.top": False,
    "axes.spines.right": False, "axes.linewidth": .65, "axes.edgecolor": EDGE,
    "xtick.major.width": .65, "ytick.major.width": .65,
    "xtick.major.size": 2.4, "ytick.major.size": 2.4,
    "axes.labelpad": 4, "text.color": INK, "axes.labelcolor": INK,
    "xtick.color": INK, "ytick.color": INK, "lines.solid_capstyle": "round",
    "pdf.fonttype": 42, "svg.fonttype": "none", "legend.frameon": False,
    "savefig.facecolor": "white", "hatch.linewidth": .5,
})
LEGEND = dict(frameon=False, handlelength=1.8, handletextpad=.55,
              columnspacing=1.7, labelspacing=.6, borderaxespad=0)


def label(ax, letter, title):
    trans = ax.transAxes + ScaledTranslation(-12 / 72, 10 / 72, ax.figure.dpi_scale_trans)
    ax.text(0, 1, letter, transform=trans, weight="bold", fontsize=9, va="bottom")
    ax.set_title(title, loc="left", pad=10, weight="bold")


def save(fig, name, **kwargs):
    fig.canvas.draw()
    require_matplotlib_panel_alignment(fig, json_out=QA / f"{name}.alignment.json",
        tolerance_pt=1.5, require_panel_labels=True, strict=True, **kwargs)
    fig.savefig(OUT / f"{name}.pdf", dpi=300)
    fig.savefig(OUT / f"{name}.svg", dpi=300)
    fig.savefig(OUT / f"{name}.png", dpi=600)
    # Matplotlib adds an external SVG DTD that is unnecessary for a self-contained asset.
    svg = OUT / f"{name}.svg"
    content = re.sub(r"<!DOCTYPE[^>]*>", "", svg.read_text(encoding="utf-8"))
    ET.register_namespace("", "http://www.w3.org/2000/svg")
    ET.register_namespace("xlink", "http://www.w3.org/1999/xlink")
    root = ET.fromstring(content)
    # SVG presentation attributes use the same user units as Matplotlib's px styles.
    # Explicit unitless attributes avoid a checker treating local px as physical px.
    for node in root.iter():
        style = node.get("style", "")
        size = re.search(r"font-size:\s*([0-9.]+)px", style)
        if size:
            node.set("font-size", size.group(1))
            node.set("style", re.sub(r"font-size:\s*[0-9.]+px;?\s*", "", style))
    svg.write_bytes(ET.tostring(root, encoding="utf-8", xml_declaration=True))
    plt.close(fig)


def architecture():
    fig = plt.figure(figsize=(7.16, 4.65))
    gs = fig.add_gridspec(2, 1, height_ratios=[1, 2.45], left=.055,
                         right=.98, bottom=.045, top=.92, hspace=.55)
    a, b = [fig.add_subplot(gs[j]) for j in range(2)]
    for ax in [a, b]:
        ax.set(xlim=(-1.2, 101.2), ylim=(-2, 102))
        ax.axis("off")
    label(a, "a", "Information arrives in two stages")
    a.plot([3, 96], [43, 43], color=SLATE, lw=1.1)
    a.add_patch(FancyArrowPatch((94, 43), (99, 43), arrowstyle="-|>",
                              mutation_scale=8, color=SLATE, lw=1.1))
    a.add_patch(Rectangle((3, 38), 31, 10, facecolor=GREY, edgecolor="none"))
    a.text(18.5, 68, "36 wind-speed and\npower observations", ha="center", fontsize=8)
    for x, time, text, col in [(35, "t − 6", "Latest forecast input", SLATE),
                               (65, "t", "Reserve decision", BLUE),
                               (95, "t + 6", "10-min target", RUST)]:
        a.plot([x, x], [37, 50], color=col, lw=1.3)
        a.text(x, 24, time, ha="center", weight="bold", fontsize=9)
        a.text(x, 6, text, ha="center", fontsize=7.5)
    for lo, hi in [(35, 65), (65, 95)]:
        a.annotate("", (hi, 68), (lo, 68), arrowprops=dict(arrowstyle="<->", color=SLATE, lw=.7))
        a.text((lo + hi) / 2, 80, "1 hour", ha="center", fontsize=8)
    label(b, "b", "From a fixed forecast to a reserve request")

    def box(x, y, w, h, text, fill="white", edge=EDGE, size=8, weight="normal"):
        b.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.25,rounding_size=1",
                                   facecolor=fill, edgecolor=edge, lw=.8))
        b.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=size,
               weight=weight, linespacing=1.55)

    def arrow(start, end, col=INK, style="-", width=.9):
        b.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>",
            mutation_scale=8, color=col, lw=width, linestyle=style, shrinkA=1.5, shrinkB=2))

    b.add_patch(Rectangle((-.8, 30), 101.6, 32, facecolor=PALE, edgecolor="none", zorder=0))
    b.text(0, 65, "Decision-time computation", fontsize=8, color=BLUE, weight="bold")
    box(0, 34, 18, 24, "Frozen forecast\nF for t + 6")
    box(22, 34, 18, 24, "Reserve inputs\nF + clock + ID\n+ telemetry", fill=PALE, edge=BLUE, size=7.5)
    box(44, 34, 18, 24, "HGB or MLP\n0.90 pinball loss", size=7.7)
    box(66, 34, 12, 24, "First clip\na = max(f, 0)", size=7.2)
    box(82, 34, 18, 24, "Reserve request r\nmax(a + b, 0)", fill=PALE, edge=BLUE, size=7.5)
    for x0, x1 in [(18, 22), (40, 44), (62, 66), (78, 82)]:
        arrow((x0, 46), (x1, 46), BLUE, width=1.1)
    box(22, 80, 18, 18, "Selected telemetry\navailable by t", fill=PALE, edge=BLUE, size=7.5)
    box(44, 80, 18, 18, "Historical fit\nFixed parameters", size=7.5)
    box(82, 80, 18, 18, "Earlier calibration\nFixed offset b", fill=SAND, edge=RUST, size=7.5)
    for x, col in [(31, BLUE), (53, SLATE), (91, RUST)]:
        arrow((x, 80), (x, 58), col)
    box(36, 0, 64, 20, "At t + 6: observe power P and calculate S = max(F − P, 0)\nScore r: procurement R, uncovered U, cost C = R + 10U", fill=SAND, edge=RUST, size=7.8)
    arrow((91, 34), (91, 20), RUST)
    b.plot([9, 9, 30], [34, 10, 10], color=SLATE, lw=.8)
    arrow((30, 10), (36, 10), SLATE)
    b.text(16, 16, "Fixed F", fontsize=7.5, va="center")
    save(fig, "fig1_architecture", panel_ids=["a", "b"], column_groups=[["a", "b"]])


def decision_example():
    d = pd.read_csv(BASE / "source_data/v10/decision_construction.csv")
    q = pd.read_csv(BASE / "source_data/v4/historical_offsets.csv")
    dt = pd.to_datetime(d.decision_utc)
    assert len(d) == 144 and ((pd.to_datetime(d.target_utc) - dt) == pd.Timedelta(hours=1)).all()
    offset = float(q.loc[np.isclose(q.calibration_q, .95), "offset_kw"].iloc[0])
    assert np.allclose(d.reserve_kw, np.maximum(d.raw_kw + offset, 0))
    fig = plt.figure(figsize=(7.16, 4.5))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.35, 1], left=.10, right=.97,
                         bottom=.13, top=.86, hspace=.75, wspace=.43)
    a = fig.add_subplot(gs[0, :]); b = fig.add_subplot(gs[1, 0]); c = fig.add_subplot(gs[1, 1])
    for key, color, style, name in [("raw_kw", SLATE, (0, (4, 2)), "Raw estimate a"),
            ("reserve_kw", BLUE, "-", "Reserve request r"),
            ("shortfall_kw", RUST, "-", "Subsequent shortfall S")]:
        a.plot(dt, d[key], color=color, ls=style, lw=.85 if key == "shortfall_kw" else 1.1, label=name)
    a.fill_between(dt, d.reserve_kw, d.shortfall_kw, where=d.shortfall_kw > d.reserve_kw,
                   color=RUST, alpha=.20, linewidth=0)
    a.set(ylabel="Power (kW)", xlim=(dt.min(), dt.max()), ylim=(0, max(d.shortfall_kw.max(), d.reserve_kw.max()) * 1.08))
    a.xaxis.set_major_locator(mdates.HourLocator(byhour=[0, 6, 12, 18]))
    a.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    a.set_xlabel("Decision time (UTC, 1 January 2026); each target is one hour later")
    label(a, "a", "A complete day of reserve requests and realized shortfalls")
    h, l = a.get_legend_handles_labels()
    fig.legend(h, l, loc="upper center", bbox_to_anchor=(.55, .985), ncol=3, **LEGEND)
    hi = max(d.reserve_kw.max(), d.shortfall_kw.max()) * 1.05
    b.plot([0, 300], [0, 300], ls=(0, (3, 3)), color=SLATE, lw=.75)
    covered = d.shortfall_kw <= d.reserve_kw
    for mask, col, marker, name in [(covered, BLUE, "o", "Covered"), (~covered, RUST, "^", "Uncovered")]:
        b.scatter(d.reserve_kw[mask], d.shortfall_kw[mask], s=12, marker=marker,
                  color=col, alpha=.75, linewidths=0, label=name)
    b.set(xlim=(0, hi), ylim=(0, 300), xlabel="Requested reserve (kW)", ylabel="Subsequent shortfall (kW)")
    label(b, "b", "All 144 decision outcomes")
    b.legend(loc="upper right", **LEGEND)
    x = np.arange(len(q))
    c.axhline(0, color=SLATE, lw=.65)
    c.vlines(x, 0, q.offset_kw, color=GREY, lw=3)
    c.scatter(x, q.offset_kw, color=[BLUE if np.isclose(z, .95) else SLATE for z in q.calibration_q], s=26, zorder=3)
    c.set(xticks=x, xticklabels=[f"{z:.3f}" for z in q.calibration_q], xlim=(-.4, 4.6), ylim=(-25, 350),
          xlabel="Historical residual-quantile level q", ylabel="Fixed offset b (kW)")
    c.text(1.0, 190, f"Primary q = 0.95\nb = {offset:.2f} kW", color=BLUE, fontsize=8)
    c.annotate("", (2, offset + 7), (2, 165), arrowprops=dict(arrowstyle="->", color=BLUE, lw=.75))
    label(c, "c", "Historical calibration offsets")
    save(fig, "fig2_decision_example", panel_ids=["a", "b", "c"], row_groups=[["b", "c"]])


def measurement():
    f = pd.read_csv(DATA / "measurement_fit.csv")
    d = pd.read_csv(DATA / "measurement_daily.csv")
    co = pd.read_csv(DATA / "measurement_contrasts.csv")
    arms = ["O6", "OZ6", "Praw", "OP6"]
    labels = ["Delayed\nbackground\n118 inputs", "Current\npitch\n119", "Current\npower\n119", "Power + two\ndifferences\n121"]
    fig, axs = plt.subplots(2, 2, figsize=(7.16, 5.0))
    fig.subplots_adjust(left=.115, right=.97, bottom=.17, top=.90, wspace=.44, hspace=1.0)
    for ax, est, letter in zip(axs[0], ["HGB", "MLP"], ["a", "b"]):
        z = f[f.estimator == est].pivot(index="seed", columns="arm", values="C")[arms]
        for seed, row in z.iterrows():
            ax.plot(range(4), row, color=SLATE, alpha=.7, lw=.7, marker="o", ms=2.8)
        means = z.mean()
        ax.plot(range(4), means, color=BLUE, lw=1.8, marker="D", ms=4, zorder=4)
        for j, value in enumerate(means):
            ax.text(j, z.iloc[:, j].max() + 1.8, f"{value:.2f}", ha="center", fontsize=7.5, color=BLUE)
        ax.set(xticks=range(4), xticklabels=labels, xlim=(-.25, 3.25), ylim=(26, 53), yticks=[30, 40, 50],
               ylabel="Decision cost\n(kWh-equivalent / interval)")
        ax.tick_params(axis="x", length=0, pad=5)
        ax.axvspan(1.75, 2.25, color=PALE, zorder=0)
        label(ax, letter, f"{est}: matched changes in the input")
    fig.legend([Line2D([], [], color=SLATE, marker="o", ms=3, lw=.7),
                Line2D([], [], color=BLUE, marker="D", ms=4, lw=1.8)],
                ["Each of five fixed fits", "Five-fit mean"], loc="upper center",
                bbox_to_anchor=(.55, .995), ncol=2, **LEGEND)
    ax = axs[1, 0]
    keys = ["Praw-minus-O6", "Praw-minus-OZ6", "Praw-minus-OP6"]
    for j, key in enumerate(keys):
        for est, dy, col, marker in [("HGB", .13, BLUE, "o"), ("MLP", -.13, RUST, "s")]:
            r = co[(co.comparison == key) & (co.estimator == est)].iloc[0]
            p, lo, hi = [float(r[k]) * 100 for k in ["point", "lower", "upper"]]
            ax.errorbar(p, 2-j+dy, xerr=[[p-lo], [hi-p]], fmt=marker, color=col, ms=4,
                        capsize=2.5, lw=.9, label=est if j == 0 else None)
    ax.axvline(0, color=SLATE, ls=(0, (3, 3)), lw=.75)
    ax.set(yticks=[2, 1, 0], yticklabels=["vs. delayed", "vs. pitch", "vs. power +\ndifferences"],
           xlabel="Current-power cost difference (%)", xlim=(-20, 6), ylim=(-.6, 2.6), xticks=[-20, -10, 0, 5])
    ax.tick_params(axis="y", length=0)
    label(ax, "c", "Which update lowers expected cost?")
    ax.legend(loc="upper left", bbox_to_anchor=(0, -.29), ncol=2, **LEGEND)
    ax = axs[1, 1]
    rows = []
    for est in ["HGB", "MLP"]:
        z = d[d.estimator == est].pivot(index="day", columns="arm", values="C")
        rows.append((z.Praw-z.OZ6).to_numpy())
    mat = np.array(rows)
    limit = np.ceil(np.abs(mat).max())
    im = ax.pcolormesh(np.arange(210.5, 246), np.arange(-.5, 2), mat,
                      cmap=CMAP, norm=TwoSlopeNorm(vmin=-limit, vcenter=0, vmax=limit), shading="flat")
    ax.set_ylim(1.5, -.5)
    ax.set(yticks=[0, 1], yticklabels=["HGB", "MLP"], xticks=[211, 220, 230, 240, 245],
           xlabel="Evaluation day (all 35 days)")
    ax.tick_params(axis="y", length=0)
    label(ax, "d", "The advantage varies across weather days")
    cb = fig.add_axes([.625, .075, .29, .022])
    bar = fig.colorbar(im, cax=cb, orientation="horizontal", ticks=[-limit, 0, limit])
    bar.solids.set_rasterized(False)
    bar.solids.set_edgecolor("face")
    cb.set_xlabel("Power − pitch cost (kWh-equivalent / interval)", fontsize=7, labelpad=3)
    save(fig, "fig3_measurement", exclude_axes=[cb])


def crossyear():
    s = pd.read_csv(DATA / "cross_year_summary.csv")
    fits = pd.read_csv(DATA / "cross_year_fits.csv")
    fig, axs = plt.subplots(2, 2, figsize=(7.16, 5.0))
    fig.subplots_adjust(left=.13, right=.97, top=.89, bottom=.13, hspace=.72, wspace=.48)
    a, b, c, d = axs.ravel()
    cats = [("Common", 4, 4, GREY), ("Power", 1, 36, BLUE),
            ("Wind speed", 0, 36, "#90B5C1"), ("Reactive power", 0, 36, "#D9E7EB")]
    left = [0, 0]
    for name, n0, n1, col in cats:
        for j, n in enumerate([n0, n1]):
            a.barh(1-j, n, left=left[j], height=.42, color=col, linewidth=0)
            left[j] += n
    a.set(yticks=[1, 0], yticklabels=["Current\npower", "Three-channel\nhistory"],
           xlim=(0, 124), ylim=(-.7, 1.7), xticks=[0, 36, 72, 108], xlabel="Raw reserve-input columns")
    a.text(8, 1, "5", va="center", color=BLUE, weight="bold")
    a.text(115, 0, "112", va="center", weight="bold")
    a.tick_params(axis="y", length=0)
    a.text(.02, .97, "Same upstream W/P forecast", transform=a.transAxes, va="top", fontsize=7.5)
    label(a, "a", "What is reduced at the reserve layer?")
    fig.legend([Rectangle((0, 0), 1, 1, facecolor=x[3]) for x in cats], [x[0] for x in cats],
               loc="upper center", bbox_to_anchor=(.55, .995), ncol=4, **LEGEND)
    b.add_patch(Rectangle((-.12, 0), 2.12, 10, facecolor=PALE, edgecolor="none", zorder=0))
    b.axvline(2, color=RUST, lw=.8, ls=(0, (3, 3)))
    b.axhline(10, color=RUST, lw=.8, ls=(0, (3, 3)))
    for year, mark, delta in [(2025, "o", -17), (2026, "D", 13)]:
        r = s[(s.year == year) & (s.arm == "P1")].iloc[0]
        ref = s[(s.year == year) & (s.arm == "WPQ36")].iloc[0]
        p, lo, hi = [100*r[k] for k in ["cost_delta", "cost_low", "cost_high"]]
        b.errorbar(p, 100*r.risk_upper, xerr=[[p-lo], [hi-p]], fmt=mark, color=BLUE, ms=5,
                   capsize=2.4, lw=1.0, zorder=3)
        b.scatter(0, 100*ref.risk_upper, marker=mark, s=24, facecolors="white", edgecolors=SLATE, zorder=4)
        b.annotate(str(year) if year == 2025 else "2026 Jan–Apr", (p, 100*r.risk_upper),
                   xytext=(0, delta), textcoords="offset points", ha="center", fontsize=7.5)
    b.set(xlim=(-.12, 2.3), ylim=(0, 11.4), xticks=[0, 1, 2], yticks=[0, 5, 10],
           xlabel="Relative mean cost premium (%)", ylabel="Maximum event-rate upper bound (%)")
    b.text(.04, .08, "Shading: declared comparison region", transform=b.transAxes, fontsize=7)
    label(b, "b", "Cost and event-frequency requirements")
    for year, start in [(2025, 0), (2026, 4)]:
        r = s[(s.year == year) & (s.arm == "P1")].iloc[0]
        ref = s[(s.year == year) & (s.arm == "WPQ36")].iloc[0]
        vals = [r.R-ref.R, 10*(r.U-ref.U), r.C-ref.C]
        assert abs(vals[0]+vals[1]-vals[2]) < 1e-10
        for j, (value, col) in enumerate(zip(vals, [SLATE, RUST, BLUE])):
            bottom = vals[0] if j == 1 else 0
            c.bar(start+j, value, bottom=bottom, color=col, width=.65)
            c.text(start+j, max(0, bottom+value)+.025, f"{value:+.3f}", ha="center", fontsize=7)
        c.plot([start+.35, start+.65], [vals[0], vals[0]], color=SLATE, lw=.7)
        c.plot([start+1.35, start+1.65], [vals[2], vals[2]], color=SLATE, lw=.7)
    c.axhline(0, color=INK, lw=.6)
    c.set(xticks=[0, 1, 2, 4, 5, 6], xticklabels=["ΔR", "10ΔU", "ΔC"]*2,
           ylim=(-.08, .74), yticks=[0, .2, .4, .6], ylabel="Cost change\n(kWh-equivalent / interval)")
    c.text(1, -.27, "2025", transform=c.get_xaxis_transform(), ha="center", fontsize=8)
    c.text(5, -.27, "2026 Jan–Apr", transform=c.get_xaxis_transform(), ha="center", fontsize=8)
    label(c, "c", "Where does the small premium arise?")
    for year, marker in [(2025, "o"), (2026, "D")]:
        for arm, col, fill in [("P1", BLUE, BLUE), ("WPQ36", SLATE, "white")]:
            z = fits[(fits.year == year) & (fits.arm == arm)]
            assert len(z) == 5
            d.scatter(100*z.V, z.U, marker=marker, s=26, color=fill, edgecolors=col, linewidths=.8, zorder=3)
    d.set(xlabel="Shortfall-event frequency (%)", ylabel="Uncovered shortfall (kWh / interval)",
           xlim=(4.9, 7.4), ylim=(1.55, 2.10), xticks=[5, 6, 7], yticks=[1.6, 1.8, 2.0])
    d.text(5.05, 1.60, "2025: circles", fontsize=7.5)
    d.text(6.02, 2.045, "2026: diamonds", fontsize=7.5)
    d.legend([Line2D([], [], marker="o", color=BLUE, linestyle="none", ms=4),
              Line2D([], [], marker="o", color=SLATE, markerfacecolor="white", linestyle="none", ms=4)],
             ["Current power", "History"], loc="upper left", bbox_to_anchor=(0, -.28), ncol=2, **LEGEND)
    label(d, "d", "Frequency and severity are different")
    save(fig, "fig4_cross_year")


def temporal():
    data = pd.read_csv(DATA / "cross_year_daily.csv", parse_dates=["date"])
    fig = plt.figure(figsize=(7.16, 4.55))
    gs = fig.add_gridspec(18, 3, left=.08, right=.975, bottom=.22, top=.89,
                         width_ratios=[1, 1, 1.2], wspace=.70, hspace=.22)
    a = fig.add_subplot(gs[:12, :2]); b = fig.add_subplot(gs[14:, :2]); c = fig.add_subplot(gs[:, 2])
    norm = TwoSlopeNorm(vmin=-8, vcenter=0, vmax=8)
    for year, ax, nmonths, letter in [(2025, a, 12, "a"), (2026, b, 4, "b")]:
        d = data[data.year == year]
        z = d.pivot(index="date", columns=["arm", "seed"], values="C")
        delta = (z.P1-z.WPQ36).mean(axis=1)
        assert len(delta) == (365 if year == 2025 else 120)
        mat = np.full((nmonths, 31), np.nan)
        for date, value in delta.items():
            mat[date.month-1, date.day-1] = value
        image = ax.pcolormesh(np.arange(.5, 32), np.arange(.5, nmonths+1.5),
                             np.ma.masked_invalid(mat), cmap=CMAP, norm=norm, shading="flat")
        ax.set_ylim(nmonths+.5, .5)
        for date, value in delta.items():
            if pd.isna(value):
                ax.add_patch(Rectangle((date.day-.5, date.month-.5), 1, 1,
                              facecolor=GREY, edgecolor=SLATE, lw=.2))
                ax.plot([date.day-.45, date.day+.45], [date.month+.45, date.month-.45],
                        color=SLATE, lw=.55)
        ax.set(yticks=np.arange(1, nmonths+1), yticklabels=[calendar.month_abbr[k] for k in range(1, nmonths+1)],
               xticks=[1, 5, 10, 15, 20, 25, 31], xlabel="Day of month" if year == 2026 else None)
        ax.tick_params(axis="both", length=0, pad=3)
        if year == 2025:
            ax.tick_params(axis="x", labelbottom=False)
        for spine in ax.spines.values(): spine.set_visible(False)
        label(ax, letter, f"{year}: {'all 365 days' if year == 2025 else 'all 120 days'}")
        refmean = z.WPQ36.mean(axis=1)
        valid = delta.notna()
        c.scatter(refmean[valid], delta[valid], marker="o" if year == 2025 else "D",
                  s=9 if year == 2025 else 12, color=BLUE if year == 2025 else RUST,
                  alpha=.62, linewidths=0, label=str(year))
    c.axhline(0, color=SLATE, lw=.7, ls=(0, (3, 3)))
    c.set(xlim=(0, 290), ylim=(-8, 8), xticks=[0, 100, 200], yticks=[-8, -4, 0, 4, 8],
           xlabel="History-reference daily cost\n(kWh-equivalent / interval)",
           ylabel="Current power − history daily cost\n(kWh-equivalent / interval)")
    c.legend(loc="upper right", **LEGEND)
    label(c, "c", "Daily cost context")
    cb = fig.add_axes([.105, .085, .435, .022])
    bar = fig.colorbar(image, cax=cb, orientation="horizontal", ticks=[-8, -4, 0, 4, 8])
    bar.solids.set_rasterized(False)
    bar.solids.set_edgecolor("face")
    cb.set_xlabel("Current power − history cost (kWh-equivalent / interval)", fontsize=7, labelpad=3)
    fig.text(.65, .068, "Hatched: no eligible targets\n11–22 September 2025", fontsize=7.5, va="center")
    save(fig, "fig5_temporal", panel_ids=["a", "b", "c"], exclude_axes=[cb], column_groups=[["a", "b"]])


if __name__ == "__main__":
    functions = {"architecture": architecture, "example": decision_example,
                 "measurement": measurement, "crossyear": crossyear, "temporal": temporal}
    for key in (sys.argv[1:] or functions):
        functions[key]()
        print(f"Exported {key}", flush=True)
