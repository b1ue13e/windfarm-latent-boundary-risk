"""Crop inspected primary-source Figure 1 examples for a local study board."""
from pathlib import Path as NativePath
import sys
_PROJECT_ROOT = next(p for p in NativePath(__file__).resolve().parents if (p / "AGENTS.md").is_file())
sys.path.insert(0, str(_PROJECT_ROOT / "02_公共资源/工程"))
from repo_paths import Path, repository_root
import fitz
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.image as mpimg

B=Path(__file__).resolve().parents[2]
Q=Path(__file__).resolve().parent
R=Q/"references"
cases=[
    ("Nature Energy · Howland et al. (2022)", R/"howland2022.pdf",1,(105,45,520,268),
     "Physical scene first; model roles below"),
    ("Applied Energy · Zheng et al. (2023)",R/"zheng2023.pdf",3,(138,45,465,303),
     "Equipment context paired with a decision timeline"),
    ("Applied Energy · Verdone et al. (2024)",R/"verdone2024.pdf",1,(95,48,498,140),
     "Small data views explain what moves through the method"),
    ("IEEE TSTE · Dumas et al. (2022)",B/"corpus/dumas2021.pdf",1,(310,45,590,142),
     "Forecast, decision, operation and evaluation have separate roles"),
]
plt.rcParams.update({"font.family":"sans-serif","font.sans-serif":["Arial"],"font.size":10})
fig,axs=plt.subplots(2,2,figsize=(12,8),gridspec_kw={"hspace":.31,"wspace":.12})
for ax,(title,path,index,rect,note) in zip(axs.flat,cases):
    d=fitz.open(path);png=R/(path.stem+"_fig1_crop.png")
    d[index].get_pixmap(clip=fitz.Rect(rect),dpi=190).save(str(png))
    ax.imshow(mpimg.imread(png));ax.axis("off")
    ax.set_title(title,loc="left",fontsize=10.5,fontweight="bold",pad=9)
    ax.text(0,-.07,note,transform=ax.transAxes,fontsize=9,color="#526472",va="top")
fig.suptitle("Figure 1 references for visual study",x=.07,ha="left",fontsize=16,fontweight="bold")
fig.subplots_adjust(left=.06,right=.97,bottom=.06,top=.89)
fig.savefig(Q/"reference_board.png",dpi=160)
fig.savefig(Q/"reference_board.pdf")
plt.close(fig)
print("Reference board exported; publisher figures are study references only.")
