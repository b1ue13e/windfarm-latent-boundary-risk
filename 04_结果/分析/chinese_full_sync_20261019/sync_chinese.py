"""Synchronize the Chinese manuscript without executing research code."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from translations import CAPTIONS, MATH_TEXT, SOURCE_SHA256, TABLE_NOTES, TRANSLATIONS, VISIBLE_TEXT

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
TOKEN = re.compile(
    r"\\begin\{equation\}.*?\\end\{equation\}|\$(?:\\.|[^$])*?\$|\[@[^\]]+\]|\\(?:ref|label)\{[^}]+\}",
    re.S,
)

HEADER = r"""---
documentclass: ctexart
classoption:
  - UTF8
  - a4paper
  - 11pt
mainfont: TeX Gyre Termes
mathfont: TeX Gyre Termes Math
bibliography: references.bib
csl: IEEE.csl
citeproc: true
link-citations: false
numbersections: true
secnumdepth: 3
date: ""
geometry:
  - margin=21mm
header-includes:
  - \usepackage{graphicx}
  - \usepackage{tabularx}
  - \usepackage{booktabs}
  - \usepackage{float}
  - \usepackage{enumitem}
  - \usepackage{adjustbox}
  - \setlist{nosep}
  - \setlength{\emergencystretch}{3em}
  - \linespread{1.12}
  - \setcounter{topnumber}{4}
  - \setcounter{bottomnumber}{4}
  - \setcounter{totalnumber}{8}
---

\title{遥测退化条件下风电机组备用决策的信息价值与充分性}
\author{李俊宇\quad 杜俊涛\thanks{通讯作者：\texttt{dujuntao@aufe.edu.cn}}\\
安徽财经大学统计与应用数学学院，蚌埠 233030，中国}
\date{}
\maketitle

> **中文全文同步版（2026-10-19）**：依据现行英文正文`paper_tste_ieee.md`逐节同步。模型标识、数学记号、数值、引文与原图保留；图表标题和说明译为中文，原图内英文标注沿用既有图件。全文中的历史诊断、主要确认与次要分析保持各自证据范围；文档同步不构成新增实验或恢复项目执行。

"""


def command_argument(text: str, command: str, replacement: str) -> str:
    marker = "\\" + command + "{"
    start = text.index(marker) + len(marker)
    depth, i = 1, start
    while depth:
        if text[i] == "{" and text[i - 1] != "\\":
            depth += 1
        elif text[i] == "}" and text[i - 1] != "\\":
            depth -= 1
        i += 1
    return text[:start] + replacement + text[i - 1 :]


def translated_prose(index: int, original: str) -> tuple[str, dict]:
    tokens = [m.group(0) for m in TOKEN.finditer(original)]
    template = TRANSLATIONS[index]
    used = [int(i) for i in re.findall(r"\{(\d+)\}", template)]
    assert sorted(used) == list(range(len(tokens))), (index, used, len(tokens))
    rendered = re.sub(r"\{(\d+)\}", lambda m: tokens[int(m[1])], template)
    return rendered, dict(index=index, type="prose", protected_tokens=len(tokens),
                          source_sha256=hashlib.sha256(original.encode()).hexdigest())


def translated_float(index: int, original: str) -> tuple[str, dict]:
    rendered = command_argument(original, "caption", CAPTIONS[index])
    if index in TABLE_NOTES:
        head, tail = rendered.rsplit(r"\selectfont ", 1)
        suffix = "}\n\\end{tabular*}" if index != 60 else "\n\\end{table}"
        end = tail.index(suffix)
        rendered = head + r"\selectfont " + TABLE_NOTES[index] + tail[end:]
    # Preserve mathematical strings, paths, references and labels during text translation.
    protected = []
    def mask(match):
        protected.append(match.group(0))
        return f"@@TOKEN{len(protected)-1}@@"
    rendered = TOKEN.sub(mask, rendered)
    for source, target in sorted(VISIBLE_TEXT.items(), key=lambda item: -len(item[0])):
        rendered = rendered.replace(source, target)
    rendered = re.sub(r"@@TOKEN(\d+)@@", lambda m: protected[int(m[1])], rendered)
    # Adapt tables to the Chinese reading layout without touching data rows.
    rendered = re.sub(r"(\\begin\{tabular\*?\}.*?\\end\{tabular\*?\})",
                      r"\\begin{adjustbox}{max width=\\linewidth}\n\1\n\\end{adjustbox}", rendered, flags=re.S)
    rendered = rendered.replace("width=\\columnwidth,keepaspectratio",
                                "width=\\columnwidth,height=0.75\\textheight,keepaspectratio")
    return rendered, dict(index=index, type="float", source_sha256=hashlib.sha256(original.encode()).hexdigest())


def main() -> None:
    path = ROOT / "paper_tste_ieee.md"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == SOURCE_SHA256, "English source changed"
    source = path.read_text(encoding="utf-8")
    body = source[source.index(r"\begin{abstract}") :]
    blocks = re.split(r"\n[ \t]*\n", body)
    pieces, ledger = [], []
    for index, block in enumerate(blocks):
        original = block.strip()
        if not original:
            continue
        if index in TRANSLATIONS:
            rendered, entry = translated_prose(index, original)
        else:
            assert index in CAPTIONS, (index, original[:120])
            rendered, entry = translated_float(index, original)
        for source_text, chinese_text in MATH_TEXT.items():
            rendered = rendered.replace(source_text, chinese_text)
        assert "\t" not in rendered, (index, "Unexpected tab; check string escapes")
        pieces.append(rendered)
        ledger.append(entry)
    content = HEADER + "\n\n".join(pieces) + "\n"
    targets = ["paper_tste_chinese.md", "manuscript/paper_chinese_topjournal_final.md",
               "manuscript/paper_tste_chinese_topjournal.md"]
    for name in targets:
        (ROOT / name).write_text(content, encoding="utf-8", newline="\n")
    result = dict(english_source="paper_tste_ieee.md", english_sha256=SOURCE_SHA256,
                  translated_segments=len(ledger), ledger=ledger, targets=targets,
                  output_sha256=hashlib.sha256(content.encode()).hexdigest(),
                  scope="Manuscript translation only; no scientific execution")
    (OUT / "translation_ledger.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "ledger"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
