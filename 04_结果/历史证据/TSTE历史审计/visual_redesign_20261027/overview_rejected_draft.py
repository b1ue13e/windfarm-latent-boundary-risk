#!/usr/bin/env python3
"""Render the TSTE information-to-reserve overview schematic.

The drawing is deliberately data-free.  It encodes only the causal timing,
arrived-information sets, reserve rule, outcome calculation, and the two study
input contrasts specified by the manuscript.
"""

from __future__ import annotations

from pathlib import Path as NativePath
import sys
_PROJECT_ROOT = next(p for p in NativePath(__file__).resolve().parents if (p / "AGENTS.md").is_file())
sys.path.insert(0, str(_PROJECT_ROOT / "02_公共资源/工程"))
from repo_paths import Path, repository_root
import re

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle
from matplotlib.text import Text


ROOT = Path(__file__).resolve().parents[1]
FIG_DIR = ROOT / "figures" / "v2"
QA_DIR = ROOT / "qa" / "visual_redesign_20261027"
FIG_STEM = "fig1_overview"

WIDTH_IN = 7.16
HEIGHT_IN = 5.00

INK = "#17212b"
MUTED = "#586674"
RULE = "#cbd4dc"
PALE = "#f7f9fb"
SLATE = "#496276"
SLATE_PALE = "#edf2f5"
BLUE = "#1767b0"
BLUE_PALE = "#e7f1fa"
RUST = "#a95f49"
RUST_PALE = "#f6eee9"


def configure_style() -> None:
    """Use an embedded Arial face and publication-safe Matplotlib defaults."""
    arial = Path("C:/Windows/Fonts/arial.ttf")
    arial_bold = Path("C:/Windows/Fonts/arialbd.ttf")
    if not arial.exists():
        raise FileNotFoundError("Arial is required for the figure export")
    font_manager.fontManager.addfont(str(arial))
    if arial_bold.exists():
        font_manager.fontManager.addfont(str(arial_bold))
    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial"],
            "font.size": 8.5,
            "text.color": INK,
            "axes.edgecolor": RULE,
            "axes.linewidth": 0.6,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
            "svg.hashsalt": "tste-overview-v2",
            "savefig.facecolor": "white",
            "figure.facecolor": "white",
            "savefig.dpi": 600,
            "savefig.bbox": "standard",
            "savefig.pad_inches": 0.0,
        }
    )


def rounded_box(
    ax,
    x: float,
    y: float,
    w: float,
    h: float,
    *,
    face: str = "white",
    edge: str = RULE,
    lw: float = 0.8,
    radius: float = 0.025,
    zorder: int = 3,
) -> FancyBboxPatch:
    patch = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle=f"round,pad=0.008,rounding_size={radius}",
        linewidth=lw,
        edgecolor=edge,
        facecolor=face,
        zorder=zorder,
    )
    ax.add_patch(patch)
    return patch


def label(
    ax,
    x: float,
    y: float,
    value: str,
    *,
    size: float = 8.5,
    color: str = INK,
    weight: str = "normal",
    ha: str = "left",
    va: str = "center",
    zorder: int = 6,
    **kwargs,
) -> Text:
    return ax.text(
        x,
        y,
        value,
        fontsize=size,
        color=color,
        fontweight=weight,
        ha=ha,
        va=va,
        zorder=zorder,
        **kwargs,
    )


def arrow(
    ax,
    start: tuple[float, float],
    end: tuple[float, float],
    *,
    color: str = SLATE,
    lw: float = 1.1,
    style: str = "-|>",
    mutation_scale: float = 8.0,
    connectionstyle: str = "arc3,rad=0",
    zorder: int = 4,
) -> FancyArrowPatch:
    patch = FancyArrowPatch(
        start,
        end,
        arrowstyle=style,
        mutation_scale=mutation_scale,
        linewidth=lw,
        color=color,
        connectionstyle=connectionstyle,
        shrinkA=0.0,
        shrinkB=0.0,
        zorder=zorder,
    )
    ax.add_patch(patch)
    return patch


def panel_heading(ax, x: float, y: float, letter: str, title: str) -> None:
    label(ax, x, y, letter, size=10.0, weight="bold", va="bottom")
    label(ax, x + 0.045, y, title, size=9.2, weight="bold", va="bottom")


def draw_timeline(ax) -> None:
    panel_heading(ax, 0.020, 0.955, "a", "Information and timing")

    x0, x1, y_axis = 0.115, 0.955, 0.755
    positions = {"t-6": 0.255, "t": 0.535, "t+6": 0.845}
    ax.plot([x0, x1], [y_axis, y_axis], color=SLATE, lw=1.0, zorder=2)
    ax.plot([x1], [y_axis], marker=">", ms=4.0, color=SLATE, zorder=3)
    label(ax, 0.958, 0.728, "time", size=8.0, color=MUTED, ha="right", va="top")

    # The 36-sample wind-speed/power history is drawn as a quiet sample comb.
    hist_x0, hist_x1 = 0.115, positions["t-6"]
    ax.plot([hist_x0, hist_x1], [0.705, 0.705], color=SLATE, lw=0.7, zorder=2)
    for idx in range(10):
        xx = hist_x0 + (idx + 0.55) * (hist_x1 - hist_x0) / 10
        ax.plot([xx, xx], [0.705, 0.741], color=SLATE, lw=0.55, alpha=0.5, zorder=2)
    label(ax, (hist_x0 + hist_x1) / 2, 0.675, "36 x 10 min W/P samples", size=8.0, color=SLATE, weight="bold", ha="center")

    # Decision-time measurements are visibly separate from forecast history.
    ax.plot([positions["t"], positions["t"]], [0.690, 0.755], color=BLUE, lw=1.6, zorder=4)
    ax.plot([positions["t"], positions["t"]], [0.690, 0.704], color=RUST, lw=1.6, zorder=4)
    ax.plot([positions["t"]], [0.690], marker="o", ms=4.8, mfc=BLUE, mec="white", mew=0.7, zorder=5)
    label(ax, positions["t"] + 0.018, 0.700, "current measurement", size=8.1, color=BLUE, weight="bold")
    label(ax, positions["t"] + 0.018, 0.669, "active power or pitch", size=8.0, color=RUST)

    ax.plot([positions["t+6"], positions["t+6"]], [0.705, 0.755], color=INK, lw=1.1, zorder=4)
    ax.plot([positions["t+6"]], [0.755], marker="o", ms=4.4, mfc="white", mec=INK, mew=1.0, zorder=5)

    for tick, tick_text, subtitle in [
        (positions["t-6"], "t - 6", "latest forecast input"),
        (positions["t"], "t", "reserve decision"),
        (positions["t+6"], "t + 6", "realized power"),
    ]:
        ax.plot([tick, tick], [y_axis - 0.018, y_axis + 0.018], color=INK, lw=0.85, zorder=3)
        label(ax, tick, 0.790, tick_text, size=8.8, weight="bold", ha="center")
        label(ax, tick, 0.821, subtitle, size=8.0, color=MUTED, ha="center")

    # The common forecast is held fixed; no issuance timestamp is implied.
    fy = 0.866
    arrow(ax, (positions["t-6"], fy), (positions["t+6"], fy), color=SLATE, lw=1.15, mutation_scale=8.0)
    label(ax, (positions["t-6"] + positions["t+6"]) / 2, fy + 0.043, "Common forecast F held fixed", size=8.5, color=SLATE, weight="bold", ha="center")

    # Compact elapsed-time labels stay inside panel a, beneath the axis, and
    # do not compete with panel b for vertical space.
    label(ax, (positions["t"] + positions["t+6"]) / 2, 0.630, "decision to target: 60 min", size=8.0, color=BLUE, ha="center")


def draw_main_path(ax) -> None:
    panel_heading(ax, 0.020, 0.505, "b", "Reserve decision and cost evaluation")

    # Fixed two-row grid.  Boxes never overlap, and every arrow terminates at
    # the border of its intended node.
    rounded_box(ax, 0.020, 0.400, 0.190, 0.095, face=PALE, edge=RULE, lw=0.8)
    label(ax, 0.033, 0.474, "Common inputs", size=8.2, weight="bold")
    label(ax, 0.033, 0.449, "F   sin clock   cos clock", size=8.0, color=MUTED)
    label(ax, 0.033, 0.424, "turbine ID", size=8.0, color=MUTED)

    rounded_box(ax, 0.020, 0.295, 0.190, 0.080, face=BLUE_PALE, edge=BLUE, lw=1.0)
    label(ax, 0.033, 0.350, "Current measurement", size=8.1, color=BLUE, weight="bold")
    label(ax, 0.033, 0.320, "active power or pitch", size=8.0, color=RUST)

    rounded_box(ax, 0.280, 0.400, 0.200, 0.095, face="white", edge=RULE, lw=0.8)
    label(ax, 0.293, 0.474, "Reserve learner", size=8.2, weight="bold")
    label(ax, 0.293, 0.449, "HGB or MLP", size=8.0, color=MUTED)
    label(ax, 0.293, 0.424, "0.90 pinball loss", size=8.0, color=MUTED)

    rounded_box(ax, 0.540, 0.400, 0.200, 0.095, face="white", edge=RULE, lw=0.8)
    label(ax, 0.553, 0.474, "Historical offset", size=8.2, weight="bold")
    label(ax, 0.553, 0.449, "a = max(f(x), 0)", size=8.0, color=MUTED)
    label(ax, 0.553, 0.424, "r = max(a + bq, 0)", size=8.0)

    rounded_box(ax, 0.800, 0.400, 0.180, 0.095, face=BLUE_PALE, edge=BLUE, lw=0.9)
    label(ax, 0.813, 0.474, "Reserve request r", size=8.2, color=BLUE, weight="bold")
    label(ax, 0.813, 0.449, "available at t", size=8.0, color=MUTED)

    rounded_box(ax, 0.280, 0.200, 0.200, 0.080, face=RUST_PALE, edge=RUST, lw=0.8)
    label(ax, 0.293, 0.255, "Realized power", size=8.2, color=RUST, weight="bold")
    label(ax, 0.293, 0.225, "Pfuture at t+6", size=8.0)

    rounded_box(ax, 0.580, 0.100, 0.120, 0.070, face=SLATE_PALE, edge=SLATE, lw=0.8)
    label(ax, 0.640, 0.145, "Same F", size=8.0, color=SLATE, weight="bold", ha="center")
    label(ax, 0.640, 0.118, "shared forecast", size=8.0, color=MUTED, ha="center")

    rounded_box(ax, 0.540, 0.200, 0.200, 0.080, face=RUST_PALE, edge=RUST, lw=0.8)
    label(ax, 0.553, 0.255, "Shortfall S", size=8.2, color=RUST, weight="bold")
    label(ax, 0.553, 0.225, "S = max(F - Pfuture, 0)", size=8.0)

    rounded_box(ax, 0.800, 0.185, 0.180, 0.110, face="white", edge=INK, lw=0.8)
    label(ax, 0.813, 0.270, "Cost evaluation", size=8.2, weight="bold")
    label(ax, 0.813, 0.244, "C = Δr + 10Δ max(S-r, 0)", size=8.0)
    label(ax, 0.813, 0.218, "Δ = 1/6 h", size=8.0, color=MUTED)

    # Top row.  The current-measurement path enters the learner at its lower
    # left edge and never traverses box text.
    arrow(ax, (0.210, 0.448), (0.280, 0.448), color=SLATE, lw=1.0, mutation_scale=7.0)
    ax.plot([0.210, 0.245, 0.245], [0.335, 0.335, 0.435], color=BLUE, lw=1.1, zorder=3)
    arrow(ax, (0.245, 0.435), (0.280, 0.435), color=BLUE, lw=1.1, mutation_scale=7.0)
    arrow(ax, (0.480, 0.448), (0.540, 0.448), color=SLATE, lw=1.0, mutation_scale=7.0)
    arrow(ax, (0.740, 0.448), (0.800, 0.448), color=SLATE, lw=1.0, mutation_scale=7.0)

    # Bottom row.  Same F is a labelled duplicate of the shared forecast and
    # enters S directly; it is not a new measurement or model.
    arrow(ax, (0.480, 0.240), (0.540, 0.240), color=RUST, lw=1.0, mutation_scale=7.0)
    arrow(ax, (0.640, 0.170), (0.640, 0.200), color=SLATE, lw=1.0, mutation_scale=7.0)
    arrow(ax, (0.740, 0.240), (0.800, 0.240), color=RUST, lw=1.0, mutation_scale=7.0)
    arrow(ax, (0.890, 0.400), (0.890, 0.295), color=BLUE, lw=1.1, mutation_scale=7.0)


def draw_study_strip(ax) -> None:
    """Show only the reserve-layer input contrasts for the two studies."""
    panel_heading(ax, 0.020, 0.125, "c", "Reserve-layer study inputs")
    y = 0.026
    h = 0.074

    rounded_box(ax, 0.020, y, 0.460, h, face=PALE, edge=RULE, lw=0.8)
    label(ax, 0.034, y + 0.056, "SDWPF (134 turbines)", size=8.2, weight="bold")
    label(ax, 0.034, y + 0.034, "119: 118 delayed + current P or pitch", size=8.0)
    label(ax, 0.034, y + 0.011, "121: add two power differences", size=8.0, color=MUTED)

    rounded_box(ax, 0.515, y - 0.006, 0.460, h, face=PALE, edge=RULE, lw=0.8)
    label(ax, 0.529, y + 0.050, "Hill of Towie (21 turbines, HGB)", size=8.2, weight="bold")
    label(ax, 0.529, y + 0.028, "5: current power + common", size=8.0, color=BLUE, weight="bold")
    label(ax, 0.529, y + 0.005, "112: WPQ 36 + common; q = 0.95", size=8.0, color=MUTED)


def build_figure() -> plt.Figure:
    configure_style()
    fig = plt.figure(figsize=(WIDTH_IN, HEIGHT_IN), facecolor="white")
    ax = fig.add_axes([0.0, 0.0, 1.0, 1.0])
    # Layout coordinates are axes fractions; Matplotlib converts live text and
    # stroke widths to physical points at the fixed 7.16 x 4.72 in canvas size.
    ax.set_xlim(0.0, 1.0)
    ax.set_ylim(0.0, 1.0)
    ax.axis("off")

    draw_timeline(ax)
    draw_main_path(ax)
    draw_study_strip(ax)

    # A single restrained rule separates the causal setup from its consequences.
    return fig


def save_figure(fig: plt.Figure) -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    QA_DIR.mkdir(parents=True, exist_ok=True)
    pdf = FIG_DIR / f"{FIG_STEM}.pdf"
    svg = FIG_DIR / f"{FIG_STEM}.svg"
    png = FIG_DIR / f"{FIG_STEM}.png"

    pdf_metadata = {"Title": "TSTE telemetry-to-reserve overview", "Author": "TSTE manuscript"}
    svg_metadata = {"Title": "TSTE telemetry-to-reserve overview", "Creator": "Matplotlib"}
    fig.savefig(pdf, format="pdf", dpi=600, metadata=pdf_metadata)
    fig.savefig(svg, format="svg", metadata=svg_metadata)
    fig.savefig(png, format="png", dpi=600, metadata=pdf_metadata)

    # The schematic auditor intentionally rejects DTD declarations.  Matplotlib
    # adds the standard SVG 1.1 DTD, which is unnecessary for a self-contained
    # file and is stripped here to retain a fully editable, production-safe SVG.
    svg_text = svg.read_text(encoding="utf-8")
    svg_text = re.sub(
        r'<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1\.1//EN"\s*"http://www\.w3\.org/Graphics/SVG/1\.1/DTD/svg11\.dtd">',
        "",
        svg_text,
        count=1,
    )
    svg.write_text(svg_text, encoding="utf-8")


def main() -> None:
    # Muted-rust labels and the one explanatory note are authored in plain
    # Arial, avoiding Matplotlib's smaller synthetic math-font fallback.
    fig = build_figure()
    save_figure(fig)
    plt.close(fig)


if __name__ == "__main__":
    main()
