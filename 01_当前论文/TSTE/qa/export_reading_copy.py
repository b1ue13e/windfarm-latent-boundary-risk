"""Export a readable Markdown copy from the authoritative TeX sections."""
from pathlib import Path as NativePath
import sys
_PROJECT_ROOT = next(p for p in NativePath(__file__).resolve().parents if (p / "AGENTS.md").is_file())
sys.path.insert(0, str(_PROJECT_ROOT / "02_代码/工程"))
from repo_paths import Path, repository_root
import re

B = Path(__file__).resolve().parents[1]

def group(text, command):
    match=re.search(re.escape(command)+r"\{", text)
    if not match: return ""
    start=match.end(); depth=1
    for i in range(start,len(text)):
        if text[i]=="{" and (i==0 or text[i-1]!="\\"): depth+=1
        elif text[i]=="}" and text[i-1]!="\\":
            depth-=1
            if depth==0: return text[start:i]
    raise ValueError(command)

aux=(B/"build/manuscript.aux").read_text(encoding="utf-8")
cites=dict(re.findall(r"\\bibcite\{([^}]+)\}\{([^}]+)\}",aux))
labels=dict(re.findall(r"\\newlabel\{([^}]+)\}\{\{([^}]+)\}",aux))
counts={"figure":0,"table":0}

def float_md(match):
    s=match.group(0); kind="figure" if "\\begin{figure" in s else "table"
    counts[kind]+=1; num=counts[kind]; caption=group(s,r"\caption")
    if kind=="figure":
        filename=re.search(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}",s).group(1)
        return f"\n\n[Figure {num}]({filename}). {caption}\n\n"
    tab=re.search(r"\\begin\{tabularx?\}[^\n]*\n(.*?)\\end\{tabularx?\}",s,re.S)
    if not tab: raise ValueError("unrecognized table")
    clean=re.sub(r"\\(?:toprule|midrule|bottomrule)","",tab.group(1))
    rows=[[c.strip() for c in row.strip().split("&")] for row in clean.split(r"\\") if row.strip()]
    result=f"\n\n**Table {num}. {caption}**\n\n"
    result+="| "+" | ".join(rows[0])+" |\n"
    result+="| "+" | ".join(["---"]*len(rows[0]))+" |\n"
    result+="\n".join("| "+" | ".join(row)+" |" for row in rows[1:])+"\n\n"
    if r"\parbox" in s:
        note=re.search(r"\\parbox\{[^}]+\}\{\\footnotesize (.*?)\}\s*\\end",s,re.S)
        if note: result+=note.group(1)+"\n\n"
    return result

def convert(text):
    text=text.replace(r"\FloatBarrier","")
    text=re.sub(r"\\begin\{(figure\*?|table\*?)\}.*?\\end\{\1\}",float_md,text,flags=re.S)
    text=re.sub(r"\\section\{([^}]+)\}",r"## \1",text)
    text=re.sub(r"\\subsection\{([^}]+)\}",r"### \1",text)
    text=re.sub(r"\\label\{[^}]+\}","",text)
    text=re.sub(r"\\cite\{([^}]+)\}",lambda m:"["+", ".join(cites[k] for k in m.group(1).split(","))+"]",text)
    text=re.sub(r"\\ref\{([^}]+)\}",lambda m:labels.get(m.group(1),m.group(1)),text)
    text=text.replace(r"\begin{equation}","\n$$\n").replace(r"\end{equation}","\n$$\n")
    text=text.replace(r"\%","%").replace(r"\_","_").replace("~"," ").replace("--","–")
    return re.sub(r"\n{3,}","\n\n",text).strip()

main=(B/"manuscript.tex").read_text(encoding="utf-8")
title=group(main,r"\title")
abstract=main.split(r"\begin{abstract}",1)[1].split(r"\end{abstract}",1)[0]
pieces=[f"# {title}\n\nJunyu Li and Juntao Du\n\n## Abstract\n\n"+convert(abstract)]
for section in re.findall(r"\\input\{([^}]+)\}",main):
    pieces.append(convert((B/(section+".tex")).read_text(encoding="utf-8")))
bbl=(B/"build/manuscript.bbl").read_text(encoding="utf-8")
refs=[]
for key,entry in re.findall(r"\\bibitem\{([^}]+)\}(.*?)(?=\\bibitem|\\end\{thebibliography\})",bbl,re.S):
    entry=re.sub(r"\\newblock\s*"," ",entry).strip()
    entry=re.sub(r"\\emph\{([^}]+)\}",r"*\1*",entry)
    entry=entry.replace(r"\BIBentryALTinterwordspacing","").replace(r"\BIBentrySTDinterwordspacing","")
    entry=re.sub(r"\s+"," ",entry).replace("~"," ").replace("--","–")
    refs.append(f"{cites[key]}. {entry}")
pieces.append("## References\n\n"+"\n\n".join(refs))
(B/"manuscript.md").write_text("\n\n".join(pieces)+"\n",encoding="utf-8")
print("Markdown reading copy exported from TeX; PDF remains the typeset reading copy.")
