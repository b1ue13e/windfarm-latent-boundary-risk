import os
import shutil
import re
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PKG_DIR = os.path.join(ROOT, "standalone_ieee_package")
os.makedirs(PKG_DIR, exist_ok=True)
os.makedirs(os.path.join(PKG_DIR, "figures"), exist_ok=True)

# 1. Copy IEEEtran.cls
pkg_cls = os.path.join(PKG_DIR, "IEEEtran.cls")
cls_candidates = [
    os.environ.get("IEEETRAN_CLS"),
    pkg_cls,
    os.path.join(ROOT, "IEEEtran.cls"),
    os.path.join(ROOT, "artifacts", "tste_submission_freeze_20260923", "03_STANDALONE_LATEX_PACKAGE", "IEEEtran.cls"),
    "E:/MiKTeX/tex/latex/ieeetran/IEEEtran.cls",
]
for cand in cls_candidates:
    if cand and os.path.exists(cand) and cand != pkg_cls:
        shutil.copy2(cand, pkg_cls)
        print("Copied IEEEtran.cls")
        break

# 2. Copy TUptm.fd
tuptm_source = os.path.join(ROOT, "TUptm.fd")
if os.path.exists(tuptm_source):
    shutil.copy2(tuptm_source, os.path.join(PKG_DIR, "TUptm.fd"))
    print("Copied TUptm.fd")

# 3. Copy references.bib
bib_source = os.path.join(ROOT, "references.bib")
if os.path.exists(bib_source):
    shutil.copy2(bib_source, os.path.join(PKG_DIR, "references.bib"))
    print("Copied references.bib")

# 4. Copy figures
fig1_source = os.path.join(ROOT, "figures", "figure1_decision_boundaries.pdf")
if os.path.exists(fig1_source):
    shutil.copy2(fig1_source, os.path.join(PKG_DIR, "figures", "figure1_decision_boundaries.pdf"))
    print("Copied figure1_decision_boundaries.pdf")

fig_source = os.path.join(ROOT, "artifacts", "final_evidence_package", "export", "figures", "figure2_data_boundary.pdf")
if os.path.exists(fig_source):
    shutil.copy2(fig_source, os.path.join(PKG_DIR, "figures", "figure2_data_boundary.pdf"))
    print("Copied figure2_data_boundary.pdf")

# 5. Generate main.tex
tex_source = os.path.join(ROOT, "build", "paper_tste_ieee.tex")
if os.path.exists(tex_source):
    with open(tex_source, "r", encoding="utf-8") as f:
        content = f.read()
    # Update figure path to local figures/ directory
    content = content.replace("artifacts/final_evidence_package/export/figures/figure2_data_boundary.pdf", "figures/figure2_data_boundary.pdf")
    
    main_tex_path = os.path.join(PKG_DIR, "main.tex")
    with open(main_tex_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Generated {main_tex_path}")

# 6. Test compilation of standalone package
xelatex_cmd = os.environ.get("XELATEX_PATH") or shutil.which("xelatex")
if not xelatex_cmd:
    for cand in [r"E:\MiKTeX\miktex\bin\x64\xelatex.exe", r"C:\texlive\2025\bin\windows\xelatex.exe"]:
        if os.path.exists(cand):
            xelatex_cmd = cand
            break
if xelatex_cmd and (os.path.isabs(xelatex_cmd) and os.path.exists(xelatex_cmd) or not os.path.isabs(xelatex_cmd)):
    print(f"Testing standalone compilation with xelatex ({xelatex_cmd})...")
    res = subprocess.run(
        [xelatex_cmd, "-interaction=nonstopmode", "-halt-on-error", "main.tex"],
        cwd=PKG_DIR,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore",
    )
    if res.returncode == 0:
        # Run second pass
        subprocess.run(
            [xelatex_cmd, "-interaction=nonstopmode", "-halt-on-error", "main.tex"],
            cwd=PKG_DIR,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
        )
        pdf_path = os.path.join(PKG_DIR, "main.pdf")
        if os.path.exists(pdf_path):
            import pypdf
            reader = pypdf.PdfReader(pdf_path)
            print(f"SUCCESS: Standalone main.pdf compiled cleanly! Page count: {len(reader.pages)}")
        else:
            print("ERROR: main.pdf not found after compilation.")
    else:
        print("ERROR: Standalone compilation failed:")
        print(res.stderr[:500] if res.stderr else res.stdout[-500:])
