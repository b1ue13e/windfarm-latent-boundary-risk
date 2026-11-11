"""Export the actual typeset page and package the active editable figure."""
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
report=json.loads((Q/"FINAL_CHECKS.json").read_text())
assert report["status"]=="PASS"
copy=B/"manuscript_fig1_integrated_v7.pdf"
shutil.copy2(B/"manuscript.pdf",copy)
doc=fitz.open(copy)
single=fitz.open();single.insert_pdf(doc,from_page=1,to_page=1)
page_pdf=B/"manuscript_fig1_integrated_v7_page2.pdf"
if page_pdf.exists():page_pdf.unlink()
single.save(page_pdf)
(Q/"pages").mkdir(exist_ok=True)
for i,p in enumerate(doc):
    p.get_pixmap(matrix=fitz.Matrix(1.6,1.6),alpha=False).save(Q/"pages"/f"page_{i+1}.png")
(B/"README.md").write_text("""# TSTE 英文研究论文初稿

标题：Current Power as Incremental Telemetry for Wind Power Reserve Decisions

当前正文为manuscript_fig1_integrated_v7.pdf，与manuscript.pdf一致。图1正文排版页单独保存为manuscript_fig1_integrated_v7_page2.pdf；补充材料为supplementary.pdf。权威源是manuscript.tex、实际引用的sections/*.tex及references.bib；manuscript.md为便读导出副本。

图1以展开方法的主计算台为主体，直接连接遥测、历史校准和未来观测。每个真实序列仅出现一次，不再使用上方插画与下方三栏。当前文件在figures/v7，绘图入口为figure_code/overview_v7.py，数据复用source_data/v3与source_data/v4。详见FIG1_INTEGRATED_V7_README_CN.md。

图2—4仍使用figures/v2及source_data/v2，未改其内容。sections/result_figures_body.tex集中声明三幅结果图，旧版本保留。

本机使用已安装的MiKTeX XeLaTeX。绘图后运行python qa/build_pdfs.py --quick --document manuscript和python qa/export_reading_copy.py。核对入口为qa/verify_draft.py与qa/fig1_integrated_v7/verify_scene.py。

生成式候选图未用于本版图1。场景、设备、文字、曲线和连接全部为可编辑矢量。工作检查记录放在qa，不进入正文。作者身份、基金、利益冲突、数据代码公开范围和AI辅助声明仍须作者在投稿前核对。尚未投稿。
""",encoding="utf-8")
acceptance=dict(status="FIG1_INTEGRATED_V7_COMPLETE",pages=len(doc),main_figures=4,
    checks=f"{sum(c['passed'] for c in report['checks'])}/{len(report['checks'])} source, data and scene checks; 18/18 manuscript checks",
    artifacts={p.name:sha(p) for p in [copy,page_pdf,B/"manuscript.pdf",B/"figures/v7/fig1_overview.pdf"]},
    visual_review="All seven main pages inspected; method-screen text and source/history/outcome connections checked at final size.",
    structure="One continuous vector scene; enlarged central method; no repeated plot series or lower three-column section",
    data_preservation="45 prior result sources and original physical/action records unchanged; Figures 2-4 byte-identical",
    new_fits=0,new_inference=0,new_calibrations=0,new_resampling=0,
    git_snapshot="See qa/fig1_integrated_v7/GIT_SAVE.json")
(B/"qa/ACCEPTANCE.json").write_text(json.dumps(acceptance,indent=2),encoding="utf-8")
files={B/n for n in ["README.md","AUTHOR_NOTES_CN.md","FIG1_INTEGRATED_V7_README_CN.md",
    "manuscript.tex","manuscript.md","manuscript.pdf",copy.name,page_pdf.name,
    "supplementary.tex","supplementary.pdf","references.bib",
    "figure_code/overview_v7.py","figure_code/overview_v3.py","figure_code/results_v2.py",
    "qa/build_pdfs.py","qa/export_reading_copy.py","qa/fig1_integrated_v7/FIGURE_CONTRACT_CN.md",
    "source_data/v3/scada_example.csv","source_data/v3/decision_example.csv"]}
for folder in ["sections","figures/v7","source_data/v4","source_data/v2"]:
    files.update(p for p in (B/folder).rglob("*") if p.is_file() and "__pycache__" not in p.parts)
for name in ["fig2_measurement","fig3_cross_year","fig4_temporal"]:
    files.update((B/"figures/v2").glob(name+".*"))
bundle=B/"tste_fig1_integrated_v7.zip"
with zipfile.ZipFile(bundle,"w",compression=zipfile.ZIP_DEFLATED) as z:
    for p in sorted(files):z.write(p,p.relative_to(B).as_posix())
with zipfile.ZipFile(bundle) as z:
    assert z.testzip() is None
    assert z.read(copy.name)==copy.read_bytes()
    assert not any(n.startswith(("figures/v5/","figures/v6/","corpus/")) for n in z.namelist())
r=dict(bundle=bundle.name,files=len(files),bytes=bundle.stat().st_size,
    sha256=sha(bundle),pdf_sha256=sha(copy),pages=len(doc))
(Q/"DELIVERY.json").write_text(json.dumps(r,indent=2),encoding="utf-8")
print(json.dumps(r,indent=2))
