"""Plot stored estimates only: no research-module imports, fitting or resampling."""
from pathlib import Path
import csv
import hashlib
import json
import platform
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
import numpy as np

HERE = Path(__file__).resolve().parents[1]
DATA = HERE / "source_data"
FIG = HERE / "figures"
QA = HERE / "qa"
QA_TOOLS = Path.home() / ".agents/skills/nature-figure/scripts"
sys.path.insert(0, str(QA_TOOLS))
from audit_panel_alignment import require_matplotlib_panel_alignment

BLUE, ORANGE, GRAY = "#175A7D", "#AE6429", "#777777"
plt.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["Arial", "DejaVu Sans"],
    "font.size": 8.5, "axes.titlesize": 9, "axes.labelsize": 8,
    "xtick.labelsize": 8, "ytick.labelsize": 8,
    "axes.spines.right": False, "axes.spines.top": False,
    "axes.linewidth": 1, "xtick.major.width": 1, "ytick.major.width": 1,
    "pdf.fonttype": 42, "svg.fonttype": "none", "legend.frameon": False,
    "savefig.facecolor": "white", "figure.facecolor": "white",
})
WIDTH = 180 / 25.4
FIELDS = []


def read_csv(name):
    with (DATA / name).open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def label(ax, letter):
    ax.text(-0.12, 1.12, letter, transform=ax.transAxes, weight="bold", fontsize=9,
            va="bottom", ha="left", clip_on=False)


def interval(ax, p, lo, hi, y, color=BLUE, marker="o", hollow=False, linestyle="-"):
    assert np.isfinite([p, lo, hi]).all() and lo <= p <= hi
    ax.errorbar(p, y, xerr=[[p - lo], [hi - p]], fmt=marker,
                color=color, markerfacecolor="white" if hollow else color,
                markeredgewidth=1, markersize=4.1, capsize=2.4,
                elinewidth=1.15, linestyle="none", zorder=4)


def zero(ax):
    ax.axvline(0, color="#AAAAAA", linewidth=1, zorder=0)
    ax.tick_params(axis="y", length=0, pad=5)


def save(fig, name):
    fig.canvas.draw()
    require_matplotlib_panel_alignment(fig, json_out=QA / f"{name}.alignment.json",
        overlay_svg=QA / f"{name}.alignment.svg", tolerance_pt=1.5,
        gutter_tolerance_pt=1.5, panel_ids=list("abcde")[:len(fig.axes)], strict=True)
    fig.savefig(FIG / f"{name}.pdf", metadata={"Title": name, "Creator": "Matplotlib; stored evidence projection"})
    fig.savefig(FIG / f"{name}.svg")
    fig.savefig(FIG / f"{name}.png", dpi=600)
    plt.close(fig)


def timing():
    fig, axes = plt.subplots(2, 1, figsize=(WIDTH, 4.05))
    fig.subplots_adjust(left=.16, right=.98, top=.90, bottom=.13, hspace=.65)
    ax = axes[0]
    ax.set_xlim(-9, 9); ax.set_ylim(-.95, 1.05); ax.axis("off")
    ax.annotate("", xy=(7.5, .05), xytext=(-7.5, .05),
                arrowprops={"arrowstyle": "->", "lw": 1.2, "color": GRAY})
    ax.scatter([-6, 0, 6], [.05]*3, c=[GRAY, BLUE, ORANGE], s=28, zorder=4)
    ax.text(-6, .31, "Forecast published\nt − 6", ha="center", fontsize=8.5)
    ax.text(0, .31, "Reserve issue\nt", ha="center", fontsize=8.5)
    ax.text(6, .31, "One target interval\nt + 6", ha="center", fontsize=8.5)
    ax.text(0, .87, "Common forecast already uses upstream wind and power histories",
            ha="center", fontsize=8.5)
    ax.text(0, -.48, "Fresh power / pitch can update the reserve layer;\n"
            "a recovered score reuses arrived inputs and historical supervision.",
            ha="center", va="center", fontsize=8.3)
    ax.text(0, -.91, "One step = 10 min; forecast lead at publication = 12 steps",
            ha="center", fontsize=7.5, color="#444444")
    label(ax, "a")
    ax = axes[1]
    colors = ["#D8E1E6", "#C8D7D0", "#90B5C4", "#D8C69D", "#B8A5C5", "#E4B899"]
    stages = [
        (1, 90, 1, "Point forecast", colors[0]), (91, 135, 1, "State fit", colors[1]),
        (136, 175, 1, "Policy\n120k", colors[2]), (176, 210, 1, "Offset", colors[3]),
        (211, 245, 1, "Score", colors[5]),
        (1, 90, 0, "Inherited", colors[0]), (136, 175, 0, "Policy\n360k", colors[2]),
        (176, 192, 0, "Offset", colors[3]), (193, 210, 0, "Select", colors[4]),
        (211, 245, 0, "Score", colors[5]),
    ]
    for start, end, y, text, color in stages:
        ax.add_patch(Rectangle((start-1, y-.27), end-start+1, .54,
                              facecolor=color, edgecolor="white", linewidth=1))
        ax.text((start+end)/2-1, y, text, ha="center", va="center", fontsize=7.1)
    ax.text(112, 0, "No state fit", ha="center", va="center", fontsize=7.3, color=GRAY)
    ax.set_yticks([0, 1], ["Measurement", "Reconstruction"])
    ax.set_xlim(0, 245); ax.set_ylim(-.55, 1.55)
    ax.set_xticks([0, 89, 134, 174, 209, 244], ["1", "90", "135", "175", "210", "245"])
    ax.set_xlabel("Dataset day (both studies share the final 35 days)")
    ax.tick_params(axis="y", length=0, pad=6)
    ax.spines["left"].set_visible(False)
    label(ax, "b")
    save(fig, "fig1_information_and_timing")


COMPARISONS = ["fresh_state", "old_state", "old_power", "P_premium_vs_Z", "residual_state"]
COMPARISON_LABELS = ["Pitch after fresh history", "Pitch after old history", "Power after old history",
                     "Power versus pitch update", "Pitch after power update"]


def measurement():
    rows = read_csv("display_M_cost.csv")
    fig, axes = plt.subplots(2, 2, figsize=(WIDTH, 4.8), sharex=True, sharey=True)
    fig.subplots_adjust(left=.30, right=.98, bottom=.13, top=.88, wspace=.27, hspace=.45)
    for index, (recipe, estimator) in enumerate([(r,e) for r in ["Original", "Common"] for e in ["HGB", "MLP"]]):
        ax = axes.flat[index]; family = "154" if recipe == "Original" else "596"
        selected = [row for row in rows if row["recipe"] == recipe and row["estimator"] == estimator and row["family"] == family]
        assert len(selected) == 5
        for y, comparison in zip(range(4, -1, -1), COMPARISONS):
            row = next(row for row in selected if row["comparison"] == comparison)
            values = [float(row[key]) for key in ["point", "lower", "upper"]]
            if row["kind"] == "G":
                p, lo, hi = -100*values[0], -100*values[2], -100*values[1]
            else:
                assert row["A"] == "OP6" and row["B"] == "OZ6"
                p, lo, hi = [100*v for v in values]
            interval(ax, p, lo, hi, y, BLUE if estimator == "HGB" else ORANGE)
            FIELDS.append(dict(figure="fig2", source="display_M_cost.csv", comparison=comparison,
                               recipe=recipe, estimator=estimator, family=family,
                               source_values=values, displayed_values=[p,lo,hi],
                               transformation="-G with endpoint reversal, times100" if row["kind"] == "G" else "D times100"))
        zero(ax); ax.set_xlim(-23, 7); ax.set_ylim(-.5, 4.5)
        ax.set_xticks([-20,-10,0,5]); ax.set_yticks(range(4,-1,-1), COMPARISON_LABELS)
        ax.set_title(f"{estimator}: {recipe.lower()} calibration\n{family}-coordinate family", loc="left", pad=10)
        label(ax, "abcd"[index])
        if index >= 2: ax.set_xlabel("Relative cost difference (%)")
    save(fig, "fig2_measurement_cost")


def reconstruction():
    allrows = read_csv("display_R_cost.csv")
    rows = [row for row in allrows if row["condition"] == "pitch_withheld" and row["block_span"] == "3"]
    assert len(rows) == 6
    fig, axes = plt.subplots(1, 3, figsize=(WIDTH, 3.25))
    fig.subplots_adjust(left=.17, right=.98, bottom=.27, top=.75, wspace=1.07)
    selections = [[("B-A", "History − base"), ("E-B", "Compressed\n− history")],
                  [("C-B", "Score − history"), ("D-B", "Pitch − history"),
                   ("C-WindScore", "Score − base\nscore control"), ("C-ShuffledScore", "Score − shuffled\nscore control")]]
    for ax, selected, title, xlim in zip(axes[:2], selections,
            ["History and\ncompression", "Measured and\nrecovered pitch"], [(-5.2,4.0),(-.31,.06)]):
        labels=[]
        for y,(key,text) in zip(range(len(selected)-1,-1,-1),selected):
            row=next(r for r in rows if r["comparison"]==key)
            p,lo,hi=[float(row[k]) for k in ["point","simultaneous_ci_lower","simultaneous_ci_upper"]]
            interval(ax,p,lo,hi,y);labels.append(text)
            FIELDS.append(dict(figure="fig3",source="display_R_cost.csv",record_index=row["record_index"],
                               displayed_values=[p,lo,hi],transformation="None; absolute cost difference"))
        zero(ax);ax.set_yticks(range(len(selected)-1,-1,-1),labels,fontsize=7.2)
        ax.set_ylim(-.55,len(selected)-.45);ax.set_xlim(*xlim)
        ax.set_xlabel("Cost difference\n(kWh-equivalent / cell)",fontsize=7.5)
        ax.set_title(title,loc="left",pad=16)
    axes[0].set_xticks([-5,0,4]); axes[1].set_xticks([-.3,-.15,0])
    mse=read_csv("display_R_mse_per_fit.csv")
    ax=axes[2]
    for x,probe in enumerate(["pitch","wind","shuffle"]):
        values=sorted([row for row in mse if row["probe"]==probe],key=lambda row:int(row["fit_seed"]))
        assert len(values)==5
        for row,offset in zip(values,[-.16,-.08,0,.08,.16]):
            value=float(row["value"]);assert value>0
            ax.scatter(x+offset,value,s=17,c=BLUE if probe=="pitch" else GRAY,zorder=3)
            FIELDS.append(dict(figure="fig3",source="display_R_mse_per_fit.csv",seed=row["fit_seed"],probe=probe,
                               displayed_value=value,interval="not available; points only"))
    ax.set_yscale("log"); ax.set_ylim(30,3000);ax.set_xlim(-.45,2.45)
    ax.set_yticks([50,200,1000], ["50","200","1,000"])
    ax.minorticks_off();ax.set_xticks([0,1,2],["Pitch\ntarget","Base\ninputs","Shuffled\ntarget"],fontsize=7)
    ax.set_ylabel("Pitch MSE (degree²; log scale)",fontsize=7.5)
    ax.set_title("Pitch reconstruction\npoints by fixed fit",loc="left",pad=16)
    for a,l in zip(axes,"abc"):label(a,l)
    save(fig,"fig3_reconstruction_and_controls")


def decomposition():
    rows=read_csv("display_M_decomposition.csv");cost=read_csv("display_M_cost.csv")
    fig,axes=plt.subplots(1,3,figsize=(WIDTH,2.55))
    fig.subplots_adjust(left=.13,right=.98,bottom=.27,top=.70,wspace=.38)
    for column,metric in enumerate(["mean_R","mean_U","cost"]):
        ax=axes[column]
        for y,estimator in [(1,"HGB"),(0,"MLP")]:
            for recipe,offset,hollow in [("Original",.12,True),("Common",-.12,False)]:
                if metric=="cost":
                    row=next(r for r in cost if r["recipe"]==recipe and r["estimator"]==estimator and r["family"]=="596" and r["comparison"]=="residual_state")
                    p,lo,hi=-100*float(row["point"]),-100*float(row["upper"]),-100*float(row["lower"])
                else:
                    row=next(r for r in rows if r["recipe"]==recipe and r["estimator"]==estimator and r["metric"]==metric and r["comparison"]=="residual_state")
                    p,lo,hi=[100*float(row[k]) for k in ["point","lower","upper"]]
                interval(ax,p,lo,hi,y+offset,BLUE if estimator=="HGB" else ORANGE,hollow=hollow)
                FIELDS.append(dict(figure="fig4",source=row["source"],metric=metric,estimator=estimator,recipe=recipe,
                                   displayed_values=[p,lo,hi],transformation="-G times100" if metric=="cost" else "stored normalized difference times100"))
        zero(ax);ax.set_ylim(-.45,1.45);ax.set_yticks([1,0],["HGB","MLP"] if column==0 else [])
        titles=["Procurement","Weighted shortfall","Proxy cost"]
        xlabels=["ΔR / C* (%)","10 ΔU / C* (%)","ΔC / C(power) (%)"]
        ax.set_title(titles[column],loc="left",pad=14);ax.set_xlabel(xlabels[column],fontsize=7.4);label(ax,"abc"[column])
        ax.locator_params(axis="x",nbins=4)
    handles=[Line2D([],[],marker='o',color=GRAY,markerfacecolor='white',linestyle='none',label='Original calibration'),
             Line2D([],[],marker='o',color=GRAY,linestyle='none',label='Common calibration')]
    fig.legend(handles=handles,loc="upper center",bbox_to_anchor=(.52,1),ncol=2,fontsize=8)
    save(fig,"fig4_procurement_shortfall")


def sensitivity():
    rows=read_csv("display_R_cost.csv")
    fig,axes=plt.subplots(1,2,figsize=(WIDTH,3.6))
    fig.subplots_adjust(left=.20,right=.98,bottom=.23,top=.75,wspace=.78)
    groups=[[("B-A","History − base"),("E-B","Compressed − history")],
            [("C-B","Score − history"),("D-B","Pitch − history"),("C-WindScore","Score − base score"),("C-ShuffledScore","Score − shuffled score")]]
    for ax,comparisons,xlim in zip(axes,groups,[(-5.5,4.2),(-.35,.12)]):
        for y,(key,text) in zip(range(len(comparisons)-1,-1,-1),comparisons):
            for span,offset,marker,color in [(1,.18,"s",GRAY),(3,0,"o",BLUE),(7,-.18,"^",ORANGE)]:
                row=next(r for r in rows if r['condition']=='pitch_withheld' and r['comparison']==key and r['block_span']==str(span))
                p,lo,hi=[float(row[k]) for k in ['point','simultaneous_ci_lower','simultaneous_ci_upper']]
                interval(ax,p,lo,hi,y+offset,color,marker=marker)
        zero(ax);ax.set_yticks(range(len(comparisons)-1,-1,-1),[t for k,t in comparisons],fontsize=7.3)
        ax.set_ylim(-.55,len(comparisons)-.45);ax.set_xlim(*xlim);ax.set_xlabel('Cost difference (kWh-equivalent / cell)',fontsize=7.3)
    axes[0].set_title('History and compression',loc='left',pad=15)
    axes[1].set_title('Pitch and score controls',loc='left',pad=15)
    for ax,l in zip(axes,'ab'):label(ax,l)
    handles=[Line2D([],[],color=c,marker=m,linewidth=1.15,label=t) for c,m,t in [(GRAY,'s','1-day'),(BLUE,'o','3-day primary'),(ORANGE,'^','7-day')]]
    fig.legend(handles=handles,loc='upper center',bbox_to_anchor=(.5,1),ncol=3,fontsize=8)
    save(fig,'figS1_block_sensitivity')


def main():
    FIG.mkdir(exist_ok=True);QA.mkdir(exist_ok=True)
    timing();measurement();reconstruction();decomposition();sensitivity()
    inputs={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(DATA.iterdir()) if p.is_file()}
    (QA/'figure_receipt.json').write_text(json.dumps({'backend':'Python/Matplotlib',
        'matplotlib':matplotlib.__version__,'numpy':np.__version__,'python':sys.version,
        'source_sha256':inputs,'plotted_fields':FIELDS,'new_statistics':False,
        'row_selection':{'M_cost':{'input':30,'fig2':20,'rule':'Original154 and Common596; Original596 sensitivity retained in source/SI'},
                         'R_cost':{'input':108,'fig3':6,'rule':'pitch_withheld span3; sensitivity shows18 original span records'},
                         'R_MSE':{'input':15,'fig3':15,'exclusion':None}},
        'source_code_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},indent=2)+'\n')
    print('Five existing-evidence figures exported; no research workflow invoked.')


if __name__=='__main__':
    main()
