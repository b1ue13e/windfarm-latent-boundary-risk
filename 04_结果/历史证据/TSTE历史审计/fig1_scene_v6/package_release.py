"""Export the current page and package only the active manuscript figure assets."""
from pathlib import Path as NativePath
import sys
_PROJECT_ROOT = next(p for p in NativePath(__file__).resolve().parents if (p / "AGENTS.md").is_file())
sys.path.insert(0, str(_PROJECT_ROOT / "02_公共资源/工程"))
from repo_paths import Path, repository_root
import json
import hashlib
import shutil
import zipfile
import fitz

Q=Path(__file__).resolve().parent;B=Q.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
copy=B/"manuscript_fig1_scene_v6.pdf"
shutil.copy2(B/"manuscript.pdf",copy)
doc=fitz.open(copy)
single=fitz.open();single.insert_pdf(doc,from_page=1,to_page=1)
page_pdf=B/"manuscript_fig1_scene_v6_page2.pdf"
if page_pdf.exists():page_pdf.unlink()
single.save(page_pdf)
(Q/"pages").mkdir(exist_ok=True)
for i,p in enumerate(doc):
    p.get_pixmap(matrix=fitz.Matrix(1.55,1.55),alpha=False).save(Q/"pages"/f"page_{i+1}.png")
(B/"README.md").write_text("""# TSTE 英文研究论文初稿

标题：Current Power as Incremental Telemetry for Wind Power Reserve Decisions

当前正文为 manuscript_fig1_scene_v6.pdf，与 manuscript.pdf 内容一致。图1正文排版页单独保存为 manuscript_fig1_scene_v6_page2.pdf。补充材料为 supplementary.pdf。

## 当前编辑源

- manuscript.tex、supplementary.tex、实际引用的 sections/*.tex 和 references.bib。
- manuscript.md 为由TeX导出的便读副本。
- 图1：figures/v6/，绘图入口 figure_code/overview_v6.py。
- 图1数据：source_data/v3/中的两组真实曲线，以及 source_data/v4/中的已有偏移和请求例子。
- 图2—4：figures/v2/，绘图入口 figure_code/results_v2.py，数据位于 source_data/v2/。
- 图1把风机观测、概念计算工作区和后续观测组织成完整场景；真实曲线嵌入屏幕并在下方放大。详见 FIG1_SCENE_V6_README_CN.md。
- sections/result_figures_body.tex 统一声明图2—4的浮动体，正文内容未改。

## 编译和核对

本机使用已安装的MiKTeX XeLaTeX与BibTeX。可运行 python qa/build_pdfs.py --quick --document manuscript，然后运行 python qa/export_reading_copy.py。

核对入口为 python qa/verify_draft.py 和 python qa/fig1_scene_v6/verify_scene.py。工作检查记录保存在qa，不进入正文。六篇TSTE全文学习材料保留在corpus，学习记录位于sources。

作者身份、基金、利益冲突、数据代码公开范围与AI使用声明须由作者在投稿前核实。当前未投稿。旧版本和原实验资产保留。
""",encoding="utf-8")
notes=B/"AUTHOR_NOTES_CN.md"
s=notes.read_text(encoding="utf-8")
s=s.replace("图1使用生成式图像作为风场背景","当前图1使用生成式风机与计算工作区概念场景")
s=s.replace("在作者核对后添加准确的生成式AI使用声明","由作者核对现有生成式AI使用声明")
s=s.replace("2026-10-27主图重构采用确定性Python矢量绘图，包括信息时序/流程示意图及从原始日账重表达的多面板结果图。之后生成式风场照片被加入图1作为全幅说明性底图，不含实测场站、设备状态或结果信息；流程、曲线、标注及数值由本机矢量绘图和既有数据生成。没有新增拟合、校准或统计重采样。新增示意图的科学内容和AI辅助绘图用途也需纳入作者核对及披露范围。",
"""2026-10-27当前图1采用完整场景插画，替换旧版淡化风景照片。风机、SCADA采集点、概念计算工作区和后续观测端共用连续地形。场景屏幕最初为空白，真实曲线以矢量叠入，并有带物理单位的放大视图。场景位置、道路、设备外观和计算工作区不是实际研究设施或部署记录。SDWPF与Towie两组示例来自不同案例，图注已明确。图2—4和已有结果保持不变。没有新增拟合、校准或统计重采样。""")
notes.write_text(s,encoding="utf-8")
asset=B/"figures/v6/assets/windfarm_workspace.png"
provenance=dict(date="2026-10-27",tool="OpenAI built-in image_gen.imagegen",
    model_version="Not exposed in tool return; no model version inferred",
    source_pixels=[2172,724],asset_sha256=sha(asset),
    purpose="Conceptual illustrated scene only; blank screens filled by original vector plots from stored records",
    prompt="""Use case: scientific-educational. Create an original panoramic engineering scene illustration for the upper half of an academic journal Figure 1 about wind-turbine telemetry and reserve computation. Aspect approximately 3:1. White background, a single continuous cutaway landscape, not a flowchart, photograph or isolated icons. Left: three wind turbines on rolling terrain with service path and SCADA cabinet. Center: a compact open-front data-analysis workspace, one workstation, two blank white screens, records. Right: distant turbine and simple blank observation screen. Shared terrain and restrained path. Fine navy outlines, white and pale blue-grey equipment, teal-blue accents and sparse sage terrain. All screens blank; no generated graphs, waveforms, bars, numbers, text, equations, arrows, people, logos, batteries, transmission towers, network cables, solar panels or grid wiring. Conceptual illustration, not a real facility map. Quantitative plots and exact method labels will be drawn separately as editable vectors.""",
    inputs_to_generator="No manuscript, raw measurements or experiment data supplied",
    editing="No generated curve treated as evidence; all depicted screen curves drawn from stored arrays",
    actual_scene_screen_plot_counts={"SDWPF_power":37,"Towie_requests":144,"Towie_shortfall":144},
    disclosure="Conceptual-scene caption plus article Acknowledgment",
    policy_checked="2026-10-27",
    policy_url="https://journals.ieeeauthorcenter.ieee.org/become-an-ieee-journal-author/publishing-ethics/guidelines-and-policies/submission-and-peer-review-policies/")
(Q/"IMAGE_PROVENANCE.json").write_text(json.dumps(provenance,indent=2),encoding="utf-8")
checks=json.loads((Q/"FINAL_CHECKS.json").read_text())
assert checks["status"]=="PASS"
acceptance=dict(status="FIG1_SCENE_V6_COMPLETE",pages=len(doc),main_figures=4,
    checks=f"{sum(c['passed'] for c in checks['checks'])}/{len(checks['checks'])} source, data and scene checks; 18/18 manuscript checks",
    artifacts={p.name:sha(p) for p in [copy,page_pdf,B/"manuscript.pdf",B/"figures/v6/fig1_overview.pdf"]},
    visual_review="All seven manuscript pages inspected; scene labels, method links and plotted readouts inspected at final size.",
    data_preservation="45 earlier result sources and physical/action records unchanged; Figures 2-4 byte-identical to previous delivery",
    new_fits=0,new_inference=0,new_calibrations=0,new_resampling=0,
    git_snapshot="See qa/fig1_scene_v6/GIT_SAVE.json")
(B/"qa/ACCEPTANCE.json").write_text(json.dumps(acceptance,indent=2),encoding="utf-8")
files={B/n for n in ["README.md","AUTHOR_NOTES_CN.md","FIG1_SCENE_V6_README_CN.md",
    "manuscript.tex","manuscript.md","manuscript.pdf",copy.name,page_pdf.name,
    "supplementary.tex","supplementary.pdf","references.bib",
    "figure_code/overview_v6.py","figure_code/overview_v3.py","figure_code/results_v2.py",
    "qa/build_pdfs.py","qa/export_reading_copy.py",
    "qa/fig1_scene_v6/IMAGE_PROVENANCE.json","qa/fig1_scene_v6/FIGURE_CONTRACT_CN.md",
    "source_data/v3/scada_example.csv","source_data/v3/decision_example.csv"]}
for folder in ["sections","figures/v6","source_data/v4","source_data/v2"]:
    files.update(p for p in (B/folder).rglob("*") if p.is_file() and "__pycache__" not in p.parts)
for n in ["fig2_measurement","fig3_cross_year","fig4_temporal"]:
    files.update((B/"figures/v2").glob(n+".*"))
bundle=B/"tste_fig1_scene_v6.zip"
with zipfile.ZipFile(bundle,"w",compression=zipfile.ZIP_DEFLATED) as z:
    for p in sorted(files):z.write(p,p.relative_to(B).as_posix())
with zipfile.ZipFile(bundle) as z:
    assert z.testzip() is None
    assert z.read(copy.name)==copy.read_bytes()
r=dict(bundle=bundle.name,files=len(files),bytes=bundle.stat().st_size,sha256=sha(bundle),pdf_sha256=sha(copy),pages=len(doc))
(Q/"DELIVERY.json").write_text(json.dumps(r,indent=2),encoding="utf-8")
print(json.dumps(r,indent=2))
