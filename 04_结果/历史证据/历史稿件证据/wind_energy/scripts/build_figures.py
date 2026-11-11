"""Render Wind Energy figures from frozen summaries only; never refit or resample."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import Rectangle
import numpy as np

PROJECT = Path(__file__).resolve().parents[1]
REPO = PROJECT.parents[1]
CONFIRMATION = "analyses/independent_confirmation_execution_20261019"
DEVELOPMENT = "analyses/claim_revision_recovery_20261019"
PRIMARY = f"{CONFIRMATION}/recovered/results/aggregate/primary.json"
SECONDARY = f"{CONFIRMATION}/recovered/results/aggregate/secondary_span3.json"
PROTOCOL = "experiments/independent_confirmation_execution_20261019/protocol.json"
FREEZE = f"{CONFIRMATION}/history_freeze/freeze.json"
UNLOCK = f"{CONFIRMATION}/unlocked_actual_receipt.json"
TOWIE_CASES = f"{CONFIRMATION}/derived/secondary_cases.csv"
WTB_CASES = f"{DEVELOPMENT}/necessity/necessity.csv"
SOURCES = [PRIMARY, SECONDARY, PROTOCOL, FREEZE, UNLOCK, TOWIE_CASES, WTB_CASES,
           "windfarm_moe/independent_confirmation.py",
           "windfarm_moe/information_subset.py"]
FIGURE_NAMES = ["fig1_information_freeze", "fig2_primary_confirmation", "fig3_secondary_minimality",
                "fig4_identification_boundary"]
BLUE, ORANGE, GRAY = "#0072B2", "#D55E00", "#757575"
STATUS_ORDER = ["NO_CERTIFIED_SUFFICIENT_POLICY", "MINIMUM_UNRESOLVED",
                "FINITE_FAMILY_MINIMUM_IDENTIFIED"]
STATUS_CODE = {STATUS_ORDER[0]: "N", STATUS_ORDER[1]: "U", STATUS_ORDER[2]: "M"}
CONDITIONS = ["pitch_withheld", "fresh", "delay1", "delay2", "delay3", "delay6_stress"]
CONDITION_LABELS = ["Pitch withheld", "Fresh", "Delay 10 min", "Delay 20 min",
                    "Delay 30 min", "Delay 60 min"]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(relative: str, repo: Path = REPO):
    return json.loads((repo / relative).read_text(encoding="utf-8"))


def read_csv(relative: str, repo: Path = REPO):
    with (repo / relative).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def primary_rows(repo: Path = REPO) -> list[dict]:
    original = read_json(PRIMARY, repo)
    group = original["bounds"]["groups"][0]
    assert original["labels"] == ["P1/HGB/q0.95", "WPQ36/HGB/q0.95"]
    rows = [dict(panel="a", metric="Relative mean cost", label="P1 vs WPQ36",
                 point=100 * group["relative_ratio_point"][0][1],
                 lower=100 * group["relative_ratio_lower"][0][1],
                 upper=100 * group["relative_ratio_upper"][0][1], unit="percent",
                 source=PRIMARY, source_field="bounds.groups[0].relative_ratio_*[0][1]")]
    for instance in range(5):
        for policy, label in enumerate(original["labels"]):
            rows.append(dict(panel="b", metric="Event rate", label=label,
                             seed=201 + instance,
                             point=100 * group["risk_point"][instance][policy],
                             lower=100 * group["risk_lower"][instance][policy],
                             upper=100 * group["risk_upper"][instance][policy],
                             unit="percent", source=PRIMARY,
                             source_field=f"bounds.groups[0].risk_*[{instance}][{policy}]"))
    return rows


def secondary_rows(repo: Path = REPO) -> tuple[list[dict], list[dict]]:
    data = next(r for r in read_json(SECONDARY, repo)["results"]
                if r["condition"] == "pitch_withheld")
    decision = next(r for r in data["secondary_retrospective_full_q"] if r["epsilon"] == .02)
    labels = data["labels"]
    assert labels[41] == "P1/HGB/q0.925"
    assert 42 not in decision["sufficient_set"]["eligible_indices"]
    points = []
    for j, label in enumerate(labels):
        if any(label.startswith(prefix) for prefix in ("Common/HGB/", "P1/HGB/", "WPQ36/HGB/")):
            points.append(dict(panel="a", label=label, index=j,
                               cost=data["mean_cost"][j],
                               cost_lower=data["mean_cost_ci_low"][j],
                               cost_upper=data["mean_cost_ci_high"][j],
                               max_instance_risk_upper=100 * max(r[j] for r in data["risk_upper"]),
                               risk_unit="percent", cost_unit="kWh-equivalent / valid turbine interval",
                               source=SECONDARY,
                               source_field=f"results[pitch_withheld].mean_cost_*[{j}],risk_upper[:,{j}]"))
    excluded = []
    audit = decision["minimum_audit"]
    assert audit["status"] == "FINITE_FAMILY_MINIMUM_IDENTIFIED"
    assert len(audit["smaller"]) == len(audit["excluded"]) == 15
    for witness in audit["excluded"]:
        j = witness["index"]
        excluded.append(dict(panel="b", label=labels[j], index=j, reason=witness["reason"],
                             witness_policy=labels[witness["witness_policy"]] if "witness_policy" in witness else "",
                             ratio_lower=witness.get("ratio_lower", ""),
                             witness_seed_indices=";".join(map(str, witness.get("witness_seed_indices", []))),
                             source=SECONDARY,
                             source_field="results[pitch_withheld].secondary_retrospective_full_q[epsilon=.02].minimum_audit"))
    return points, excluded


def boundary_rows(repo: Path = REPO) -> tuple[list[dict], list[dict]]:
    towie = [dict(r, panel="a", source=TOWIE_CASES) for r in read_csv(TOWIE_CASES, repo)
             if int(r["span"]) == 3]
    wtb = [dict(r, panel="b", source=WTB_CASES) for r in read_csv(WTB_CASES, repo)
           if int(r["span"]) == 3 and float(r["epsilon"]) == .02]
    assert len(towie) == 30 and len(wtb) == 28
    assert sum(r["analysis"] == "primary_historical_recipe" for r in wtb) == 14
    assert sum(r["analysis"] == "secondary_retrospective_grid" for r in wtb) == 14
    return towie, wtb


def write_csv(path: Path, rows: list[dict]):
    fields = list(dict.fromkeys(k for row in rows for k in row))
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def panel_label(ax, label: str, title: str):
    ax.text(0, 1.12, label, transform=ax.transAxes, fontweight="bold", fontsize=10,
            ha="left", va="bottom")
    ax.text(.055, 1.12, title, transform=ax.transAxes, fontsize=9,
            ha="left", va="bottom")


def configure_style():
    matplotlib.rcParams.update({"font.family": "sans-serif", "font.sans-serif": ["Arial", "DejaVu Sans"],
        "font.size": 8, "axes.labelsize": 8, "xtick.labelsize": 8, "ytick.labelsize": 8,
        "axes.titlesize": 9, "legend.fontsize": 8, "svg.fonttype": "none", "pdf.fonttype": 42,
        "axes.spines.top": False, "axes.spines.right": False, "axes.linewidth": .7,
        "lines.linewidth": 1, "legend.frameon": False, "savefig.facecolor": "white"})


def fig1():
    fig = plt.figure(figsize=(180 / 25.4, 125 / 25.4))
    grid = fig.add_gridspec(2, 1, left=.075, right=.97, top=.90, bottom=.12,
                           hspace=.8, height_ratios=[1, 1])
    a, b = [fig.add_subplot(grid[i]) for i in range(2)]
    panel_label(a, "a", "Shared forecast; different incremental reserve inputs")
    a.set(xlim=(0, 1), ylim=(0, 1))
    a.axis("off")
    boxes = [(0.00, .53, .27, .40, "Upstream W/P history\n36 steps per channel", "#E9ECEF"),
             (.355, .53, .29, .40, "Frozen forecast F\nClock + turbine ID", "#E9ECEF"),
             (.73, .53, .27, .40, "Reserve policy\nP1 or WPQ36", "#DEEDF6")]
    for x, y, w, h, text, color in boxes:
        a.add_patch(Rectangle((x, y), w, h, facecolor=color, edgecolor="none"))
        a.text(x + w / 2, y + h / 2, text, ha="center", va="center", linespacing=1.5)
    for x1, x2 in ((.275, .35), (.65, .725)):
        a.annotate("", xy=(x2, .73), xytext=(x1, .73), arrowprops={"arrowstyle": "->", "color": GRAY})
    a.text(.00, .25, "Forecast inputs end at t − 60 min; target is t + 60 min.", va="center")
    a.text(.00, .03, "P1 adds current P; WPQ36 adds W/P/Q history. Both retain the shared forecast.", va="center")
    panel_label(b, "b", "Historical choice frozen before the original 2025 confirmation")
    protocol = read_json(PROTOCOL)
    names = {"point_fit": "Forecast fit", "policy_fit": "Policy fit", "offset_fit": "Offset fit",
             "selection": "Selection", "confirmation": "Confirmation"}
    rows = []
    for key, (start, end) in protocol["windows"].items():
        begin, finish = [datetime.fromisoformat(v.replace("Z", "+00:00")) for v in (start, end)]
        left, right = mdates.date2num(begin), mdates.date2num(finish)
        color = BLUE if key == "confirmation" else "#DBE0E4"
        b.barh(.5, right-left-5, left=left+2.5, height=.34, color=color, edgecolor="none")
        b.text((left+right)/2, .5, names[key], ha="center", va="center",
               color="white" if key == "confirmation" else "#222222")
        rows.append(dict(stage=key, start=start, end=end, source=PROTOCOL, source_field=f"windows.{key}"))
    b.set(ylim=(0, 1), yticks=[])
    b.set_xlim(mdates.date2num(datetime(2023, 1, 1)), mdates.date2num(datetime(2026, 1, 1)))
    b.xaxis.set_major_locator(mdates.YearLocator())
    b.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    b.spines[["left", "bottom"]].set_visible(False)
    b.tick_params(axis="x", length=0)
    frozen = read_json(FREEZE)["created_utc"]
    unlocked = read_json(UNLOCK)["event"]["utc"]
    fig.text(.075, .035, "Actual sequence (19 Oct 2026 UTC): package created 04:27:16; unlock 04:30:57.",
             ha="left", va="bottom")
    rows.extend([dict(stage="package_created", start=frozen, end="", source=FREEZE, source_field="created_utc"),
                 dict(stage="actual_unlock", start=unlocked, end="", source=UNLOCK, source_field="event.utc")])
    return fig, [a, b], rows


def fig2():
    rows = primary_rows()
    fig, axes = plt.subplots(1, 2, figsize=(180 / 25.4, 90 / 25.4))
    fig.subplots_adjust(left=.08, right=.98, bottom=.22, top=.80, wspace=.40)
    a, b = axes
    panel_label(a, "a", "Paired mean cost")
    r = rows[0]
    a.errorbar(r["point"], .45, xerr=[[r["point"]-r["lower"]], [r["upper"]-r["point"]]],
               fmt="o", color=BLUE, capsize=4, markersize=6)
    a.axvline(0, color=GRAY, lw=.7, ymin=.25, ymax=.8)
    a.axvline(2, color=ORANGE, linestyle="--", lw=1, ymax=.8)
    a.text(2, .92, "2% margin", ha="right", color=ORANGE)
    a.text(.02, .09, "+0.564% [0.357, 0.771]%", transform=a.transAxes)
    a.set(xlim=(-.15, 2.2), ylim=(0, 1), yticks=[], xlabel="Cost relative to frozen reference (%)")
    a.set_xticks([0, .5, 1, 1.5, 2])
    a.spines["left"].set_visible(False)
    panel_label(b, "b", "Event rate by fixed instance")
    for j, label in enumerate(["P1/HGB/q0.95", "WPQ36/HGB/q0.95"]):
        selected = [r for r in rows[1:] if r["label"] == label]
        y = np.arange(5) + (-.12 if j == 0 else .12)
        point = np.asarray([r["point"] for r in selected])
        lo = np.asarray([r["lower"] for r in selected])
        hi = np.asarray([r["upper"] for r in selected])
        b.errorbar(point, y, xerr=[point-lo, hi-point], fmt="o" if j == 0 else "s",
                   color=BLUE if j == 0 else GRAY, markersize=4, capsize=2,
                   label="P1" if j == 0 else "WPQ36")
    b.axvline(10, color=ORANGE, linestyle="--", lw=1)
    b.set(xlim=(4.2, 10.6), ylim=(4.5, -.5), yticks=range(5),
          yticklabels=[str(i) for i in range(201, 206)], xlabel="Event rate (%)")
    b.legend(loc="lower left", bbox_to_anchor=(.0, 1.01), ncol=2, borderaxespad=0,
             handletextpad=.4, columnspacing=.9)
    fig.text(.08, .045, "Primary comparison: P1/HGB/q=.950 versus WPQ36/HGB/q=.950; original joint bounds.")
    return fig, list(axes), rows


def fig3():
    points, excluded = secondary_rows()
    fig = plt.figure(figsize=(180 / 25.4, 160 / 25.4))
    grid = fig.add_gridspec(2, 1, height_ratios=[1.6, 1], left=.15, right=.97,
                           top=.91, bottom=.13, hspace=.72)
    a, b = [fig.add_subplot(grid[i]) for i in range(2)]
    panel_label(a, "a", "Secondary full-q evidence; selected HGB policies")
    for prefix, color, marker, label in [("Common/", GRAY, "^", "Common"),
                                        ("WPQ36/", ORANGE, "s", "WPQ36"),
                                        ("P1/", BLUE, "o", "P1")]:
        chosen = [r for r in points if r["label"].startswith(prefix)]
        costs = np.asarray([r["cost"] for r in chosen])
        lower = np.asarray([r["cost_lower"] for r in chosen])
        upper = np.asarray([r["cost_upper"] for r in chosen])
        risks = [r["max_instance_risk_upper"] for r in chosen]
        a.errorbar(costs, risks, xerr=[costs-lower, upper-costs], fmt=marker,
                   color=color, markersize=4, elinewidth=.7, capsize=2, alpha=.9, label=label)
    for name, marker in [("P1/HGB/q0.95", "*"), ("P1/HGB/q0.925", "D")]:
        r = next(r for r in points if r["label"] == name)
        a.scatter([r["cost"]], [r["max_instance_risk_upper"]], marker=marker, s=75,
                  color=BLUE, edgecolors="white", linewidth=.6, zorder=5)
    a.axhline(10, color=ORANGE, ls="--", lw=.8)
    a.set(xlim=(57, 128), ylim=(0, 15.5), xlabel="Mean cost (kWh-equivalent / valid turbine interval)",
          ylabel="Maximum instance event-rate upper bound (%)")
    a.legend(loc="upper right", ncol=3, handlelength=1.3, columnspacing=1.1)
    a.text(0, -.32, "Diamond: q=.925 secondary minimum; star: q=.950 primary choice",
           transform=a.transAxes, va="top")
    panel_label(b, "b", "All 15 strictly smaller registered candidates excluded")
    # Each column is one actual registered candidate, never an independent replicate.
    matrix = np.zeros((2, len(excluded)))
    for j, row in enumerate(excluded):
        matrix[0 if row["reason"] == "RISK_LOWER_ABOVE_CAP" else 1, j] = 1
    b.pcolormesh(np.arange(16)-.5, np.arange(3)-.5, matrix, shading="flat",
                 cmap=ListedColormap(["#F4F4F4", "#C9E1F0"]), vmin=0, vmax=1,
                 edgecolors="none")
    b.set(xlim=(-.5, 14.5), ylim=(1.5, -.5))
    for i in range(2):
        for j in range(len(excluded)):
            if matrix[i, j]:
                b.text(j, i, "R" if i == 0 else "C", ha="center", va="center")
    b.set(yticks=[0, 1], yticklabels=["Risk evidence", "Cost evidence"],
          xticks=range(15), xticklabels=[r["label"].split("/q")[1].replace("0.", ".") for r in excluded])
    b.tick_params(axis="both", length=0)
    for spine in b.spines.values():
        spine.set_visible(False)
    for center, text in [(2, "Common/HGB"), (7, "Common/MLP"), (12, "P1/Persistence")]:
        b.text(center, 1.86, text, ha="center", va="top", clip_on=False)
    fig.text(.15, .035, "Full-q secondary analysis: 74,500 coordinates; q=.950 is outside the 2% sufficient set.")
    return fig, [a, b], points + excluded


def fig4():
    towie, wtb = boundary_rows()
    fig, axes = plt.subplots(1, 2, figsize=(180 / 25.4, 105 / 25.4))
    fig.subplots_adjust(left=.17, right=.98, bottom=.27, top=.82, wspace=.70)
    a, b = axes
    palette = ListedColormap(["#FFFFFF", "#E2E2E2", "#F6D7B0", "#C9E1F0"])
    epsilons = [0, .005, .01, .02, .05]
    array = np.zeros((6, 5))
    for i, condition in enumerate(CONDITIONS):
        for j, epsilon in enumerate(epsilons):
            row = next(r for r in towie if r["condition"] == condition and float(r["epsilon"]) == epsilon)
            array[i, j] = STATUS_ORDER.index(row["minimum_status"]) + 1
    a.pcolormesh(np.arange(6)-.5, np.arange(7)-.5, array, cmap=palette,
                 vmin=0, vmax=3, shading="flat", edgecolors="none")
    a.set(xlim=(-.5, 4.5), ylim=(5.5, -.5))
    for i in range(6):
        for j in range(5):
            a.text(j, i, ["", "N", "U", "M"][int(array[i, j])], ha="center", va="center")
    a.set(xticks=range(5), xticklabels=["0", "0.5", "1", "2", "5"],
          yticks=range(6), yticklabels=CONDITION_LABELS, xlabel="Relative cost tolerance (%)")
    panel_label(a, "a", "Towie: secondary full-q")
    budgets = [10000, 40000, 120000, 360000]
    array = np.zeros((6, 4))
    for i, condition in enumerate(CONDITIONS):
        for j, budget in enumerate(budgets):
            match = [r for r in wtb if r["condition"] == condition and int(r["budget"]) == budget]
            if match:
                assert len(match) == 2
                assert len({r["status"] for r in match}) == 1
                array[i, j] = STATUS_ORDER.index(match[0]["status"]) + 1
    b.pcolormesh(np.arange(5)-.5, np.arange(7)-.5, array, cmap=palette,
                 vmin=0, vmax=3, shading="flat", edgecolors="none")
    b.set(xlim=(-.5, 3.5), ylim=(5.5, -.5))
    for i in range(6):
        for j in range(4):
            b.text(j, i, ["–", "N", "U", "M"][int(array[i, j])], ha="center", va="center")
    b.set(xticks=range(4), xticklabels=["10k", "40k", "120k", "360k"],
          yticks=range(6), yticklabels=CONDITION_LABELS, xlabel="Training-row budget")
    panel_label(b, "b", "WTB: 2% tolerance")
    for axis in axes:
        axis.tick_params(length=0)
        for spine in axis.spines.values():
            spine.set_visible(False)
    fig.text(.17, .15, "N  Sufficiency not certified     U  Minimum unresolved     M  Finite-family minimum")
    fig.text(.17, .09, "Three-day blocks. WTB cells combine agreeing primary and secondary classifications; – not run.")
    fig.text(.17, .035, "Shared data across cells; no independent-replication interpretation.")
    return fig, list(axes), towie + wtb


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=PROJECT)
    parser.add_argument("--skill-scripts", type=Path,
                        default=Path.home() / ".agents/skills/nature-figure/scripts")
    parser.add_argument("--only", nargs="+", choices=FIGURE_NAMES,
                        help="Render only these figures and preserve all other exports")
    args = parser.parse_args(argv)
    output = args.output_root.resolve()
    if not output.is_relative_to(PROJECT.resolve()):
        raise ValueError("Figure outputs must remain inside the new manuscript project")
    for name in ("figures", "source_data", "qa"):
        (output / name).mkdir(parents=True, exist_ok=True)
    skill = args.skill_scripts.resolve()
    sys.path.insert(0, str(skill))
    from audit_panel_alignment import require_matplotlib_panel_alignment
    configure_style()
    hashes = {source: sha256(REPO / source) for source in SOURCES}
    audit_tools = ["audit_panel_alignment.py", "validate_figure.py", "audit_pdf_text.py",
                   "audit_figure_collisions.py"]
    receipt = {"utc": datetime.now(timezone.utc).isoformat(), "python": sys.version,
               "matplotlib": matplotlib.__version__, "numpy": np.__version__, "host": platform.node(),
               "source_sha256": hashes, "script_sha256": sha256(Path(__file__)),
               "qa_tool_sha256": {name: sha256(skill / name) for name in audit_tools},
               "scope": "Frozen-summary rendering only; no fit, inference, calibration, resampling or new interval",
               "figures": []}
    validate = subprocess.run([sys.executable, "-X", "utf8", str(skill / "validate_figure.py"), str(Path(__file__)),
                               "--json"], capture_output=True, text=True, encoding="utf-8")
    (output / "qa/source_validation.json").write_text(validate.stdout, encoding="utf-8")
    if validate.returncode:
        raise RuntimeError(f"Figure source validator failed: {validate.stderr} {validate.stdout}")
    names = FIGURE_NAMES
    if args.only:
        previous = json.loads((output / "qa/build_figures_receipt.json").read_text(encoding="utf-8"))
        receipt["previous_build_receipt"] = previous
        receipt["selective_revision"] = args.only
        receipt["figures"] = [dict(row, source_script_sha256=previous["script_sha256"])
                              for row in previous["figures"] if row["name"] not in args.only]
    for name, builder in zip(names, (fig1, fig2, fig3, fig4)):
        if args.only and name not in args.only:
            continue
        figure, axes, rows = builder()
        figure.canvas.draw()
        require_matplotlib_panel_alignment(figure, axes=axes, panel_ids=["a", "b"],
            json_out=output / f"qa/{name}.alignment.json", require_panel_labels=True)
        write_csv(output / f"source_data/{name}.csv", rows)
        base = output / "figures" / name
        figure.savefig(base.with_suffix(".pdf"), dpi=600)
        figure.savefig(base.with_suffix(".svg"), dpi=600)
        figure.savefig(base.with_suffix(".png"), dpi=600)
        # A grayscale QA preview is rendered in the selected Python backend.
        import PIL.Image
        with PIL.Image.open(base.with_suffix(".png")) as image:
            image.convert("L").save(output / f"qa/{name}.grayscale.png", dpi=(600, 600))
        plt.close(figure)
        text_audit = subprocess.run([sys.executable, "-X", "utf8", str(skill / "audit_pdf_text.py"),
            str(base.with_suffix(".pdf")), "--min-pt", "5", "--json"], capture_output=True,
            text=True, encoding="utf-8")
        (output / f"qa/{name}.text.json").write_text(text_audit.stdout, encoding="utf-8")
        collision = subprocess.run([sys.executable, "-X", "utf8", str(skill / "audit_figure_collisions.py"),
            str(base.with_suffix(".pdf")), "--json-out", str(output / f"qa/{name}.collision.json"),
            "--overlay-pdf", str(output / f"qa/{name}.collision.pdf")], capture_output=True,
            text=True, encoding="utf-8")
        if text_audit.returncode or collision.returncode:
            raise RuntimeError(f"Rendered QA failed for {name}: {text_audit.stdout} {collision.stdout}")
        # Refresh the diagnostic even when the CLI has no finding to mark; this
        # prevents an earlier failed-layout overlay from masquerading as final QA.
        from audit_figure_collisions import write_overlay_pdf
        collision_report = json.loads((output / f"qa/{name}.collision.json").read_text(encoding="utf-8"))
        write_overlay_pdf(base.with_suffix(".pdf"), output / f"qa/{name}.collision.pdf",
                          collision_report["findings"])
        import fitz
        with fitz.open(base.with_suffix(".pdf")) as document:
            pixels = document[0].get_pixmap(matrix=fitz.Matrix(96 / 72, 96 / 72), alpha=False)
            preview = PIL.Image.frombytes("RGB", (pixels.width, pixels.height), pixels.samples)
            preview.save(output / f"qa/{name}.pdf_preview.png", dpi=(96, 96))
        receipt["figures"].append({"name": name, "csv_rows": len(rows),
            "source_script_sha256": sha256(Path(__file__)),
            "width_mm": 180, "png_dpi": 600,
            "pdf_sha256": sha256(base.with_suffix(".pdf"))})
    if hashes != {source: sha256(REPO / source) for source in SOURCES}:
        raise RuntimeError("Protected evidence changed during rendering")
    receipt["protected_sources_unchanged"] = True
    receipt["figures"].sort(key=lambda row: row["name"])
    sheet = PIL.Image.new("RGB", (1400, 1120), "white")
    for index, name in enumerate(names):
        with PIL.Image.open(output / f"qa/{name}.pdf_preview.png") as preview:
            sheet.paste(preview, ((index % 2) * 700, (index // 2) * 510))
    sheet.save(output / "qa/final_size_contact_sheet.png", dpi=(96, 96))
    (output / "qa/build_figures_receipt.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print(json.dumps(receipt["figures"], indent=2))


if __name__ == "__main__":
    main()
