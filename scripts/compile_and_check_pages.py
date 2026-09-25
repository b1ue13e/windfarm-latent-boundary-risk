import subprocess
import os
import sys
import pypdf

import shutil

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
pandoc = os.environ.get("PANDOC_PATH") or shutil.which("pandoc") or os.path.join(root, 'tools', 'pandoc-3.9.0.2', 'pandoc.exe')
xelatex = os.environ.get("XELATEX_PATH") or shutil.which("xelatex")
if not xelatex:
    for candidate in [r'E:\MiKTeX\miktex\bin\x64\xelatex.exe', r'C:\texlive\2025\bin\windows\xelatex.exe']:
        if os.path.exists(candidate):
            xelatex = candidate
            break

if xelatex and os.path.exists(xelatex):
    os.environ['PATH'] = os.path.dirname(xelatex) + os.pathsep + os.environ.get('PATH', '')

os.makedirs('build', exist_ok=True)
if os.path.exists('TUptm.fd'):
    import shutil
    shutil.copy('TUptm.fd', 'build/TUptm.fd')

def compile_pdf(md_file, label):
    tex_file = os.path.join('build', f'{label}.tex')
    pdf_file = os.path.join('build', f'{label}.pdf')
    csl_file = os.path.join(root, 'IEEE.csl')

    print(f"=== Compiling {md_file} -> {pdf_file} ===")
    cmd_pandoc = [
        pandoc, md_file,
        '--citeproc',
        '--csl', csl_file,
        '--standalone',
        '-t', 'latex',
        '-o', tex_file
    ]
    res_p = subprocess.run(cmd_pandoc, capture_output=True, text=True, encoding="utf-8", errors="ignore")
    if res_p.returncode != 0:
        print("Pandoc stdout:", res_p.stdout)
        print("Pandoc stderr:", res_p.stderr)
        sys.exit(1)
    print("Pandoc generated tex successfully.")

    cmd_xelatex = [
        xelatex,
        '-interaction=nonstopmode',
        '-halt-on-error',
        '-output-directory=build',
        tex_file
    ]
    for p in range(1, 3):
        print(f"XeLaTeX pass {p}...")
        res_x = subprocess.run(cmd_xelatex, capture_output=True, text=True, encoding="utf-8", errors="ignore")
        if res_x.returncode != 0:
            print("XeLaTeX stdout:", res_x.stdout[-1500:])
            print("XeLaTeX stderr:", res_x.stderr)
            sys.exit(1)

    reader = pypdf.PdfReader(pdf_file)
    n_pages = len(reader.pages)
    print(f"--> Built {pdf_file}: {n_pages} pages.")
    return n_pages

if __name__ == '__main__':
    main_pages = compile_pdf('paper_tste_ieee.md', 'paper_tste_ieee')
    supp_pages = compile_pdf('paper_tste_supplementary.md', 'paper_tste_supplementary')
    print("\nSummary:")
    print(f"Main paper: {main_pages} pages (Target: 10)")
    print(f"Supplementary: {supp_pages} pages")
