import os
import re
import subprocess

def format_latex_table(table_lines, caption):
    rows = []
    for line in table_lines:
        line_clean = line.strip()
        if not line_clean.startswith("|"):
            continue
        # Check if separator row (|:---|:---:|...)
        if re.match(r"^\|[\s\-:|]+\|$", line_clean):
            continue
        cols = [c.strip() for c in line_clean.strip("|").split("|")]
        rows.append(cols)
    if not rows:
        return ""

    num_cols = len(rows[0])
    # Define column spec
    col_spec = "@{\\extracolsep{\\fill}}" + "c" * num_cols

    tex_table = []
    tex_table.append(r"\begin{table*}[htbp]")
    tex_table.append(r"\centering")
    clean_caption = caption.replace("**", "").strip()
    tex_table.append(f"\\caption{{{clean_caption}}}")
    tex_table.append(r"\zihao{6}")
    tex_table.append(f"\\begin{{tabular*}}{{\\textwidth}}{{{col_spec}}}")
    tex_table.append(r"\toprule")

    # Header row
    header = " & ".join([f"\\textbf{{{c}}}" for c in rows[0]]) + r" \\"
    header = header.replace("%", r"\%").replace(r"\\%", r"\%")
    tex_table.append(header)
    tex_table.append(r"\midrule")

    # Body rows
    for row in rows[1:]:
        cells = []
        for cell in row:
            c_clean = re.sub(r"\*\*(.*?)\*\*", r"\\textbf{\1}", cell)
            c_clean = c_clean.replace("%", r"\%").replace(r"\\%", r"\%")
            cells.append(c_clean)
        tex_table.append(" & ".join(cells) + r" \\")

    tex_table.append(r"\bottomrule")
    tex_table.append(r"\end{tabular*}")
    tex_table.append(r"\end{table*}")
    return "\n".join(tex_table)

def build_chinese_topjournal_tex():
    with open("manuscript/paper_chinese_topjournal_final.md", "r", encoding="utf-8") as f:
        md_text = f.read()

    # Extract title
    title_match = re.search(r"^#\s+(.*)$", md_text, flags=re.M)
    title = title_match.group(1).strip() if title_match else "风电运行备用决策"

    # Extract abstract
    abstract_match = re.search(r"###\s+摘要\s*\n\n(.*?)\n\n\*\*关键词：\*\*(.*?)\n", md_text, flags=re.DOTALL)
    if abstract_match:
        abstract_text = abstract_match.group(1).strip()
        keywords_text = abstract_match.group(2).strip()
    else:
        abstract_text = ""
        keywords_text = ""

    tex = []
    tex.append(r"\documentclass[UTF8,twocolumn,10pt]{ctexart}")
    tex.append(r"\usepackage[a4paper,left=1.6cm,right=1.6cm,top=2.2cm,bottom=2.0cm]{geometry}")
    tex.append(r"\usepackage{amsmath,amssymb,amsfonts,bm}")
    tex.append(r"\usepackage{booktabs,array,makecell,multirow}")
    tex.append(r"\usepackage{graphicx}")
    tex.append(r"\usepackage{cite}")
    tex.append(r"\usepackage{float}")
    tex.append(r"\usepackage{hyperref}")
    tex.append(r"\hypersetup{colorlinks=true,linkcolor=black,citecolor=black,urlcolor=blue}")
    tex.append("")
    tex.append(r"\ctexset{")
    tex.append(r"  section = {")
    tex.append(r"    format = {\zihao{4}\bfseries\raggedright},")
    tex.append(r"    name = {,、\hspace{-0.3em}},")
    tex.append(r"    number = {\chinese{section}},")
    tex.append(r"    aftername = {\ },")
    tex.append(r"  },")
    tex.append(r"  subsection = {")
    tex.append(r"    format = {\zihao{-4}\bfseries\raggedright},")
    tex.append(r"    name = {,.\hspace{-0.2em}},")
    tex.append(r"    number = {\arabic{section}.\arabic{subsection}},")
    tex.append(r"    aftername = {\ },")
    tex.append(r"  }")
    tex.append(r"}")
    tex.append("")
    tex.append(f"\\title{{\\zihao{{2}}\\bfseries {title}}}")
    tex.append(r"\author{\zihao{4} 杜俊涛$^{1*}$, 张三$^{2}$ \\ \zihao{5}$^1$安徽财经大学 统计与应用数学学院，蚌埠 233030；\\ $^2$清华大学 电机工程与应用电子技术系，北京 100084}")
    tex.append(r"\date{}")
    tex.append("")
    tex.append(r"\begin{document}")
    tex.append(r"\maketitle")
    tex.append("")
    tex.append(r"\begin{abstract}")
    tex.append(r"\zihao{5}")
    tex.append(r"\textbf{摘要：}" + abstract_text + r"\\[0.5em]")
    tex.append(r"\textbf{关键词：}" + keywords_text)
    tex.append(r"\end{abstract}")
    tex.append("")

    sec1_pos = md_text.find("## 1 引言")
    ref_pos = md_text.find("## 参考文献")
    body_md = md_text[sec1_pos:ref_pos]

    lines = body_md.split("\n")
    in_table = False
    table_lines = []
    table_caption = ""
    in_formula = False
    formula_lines = []

    for line in lines:
        line_s = line.strip()

        # Handle formula blocks $$ ... $$
        if line_s.startswith("$$"):
            if line_s.endswith("$$") and len(line_s) > 4:
                # single line formula
                f_body = line_s[2:-2].strip()
                f_body = re.sub(r"\\tag\{(\d+)\}", r"\\tag{\1}", f_body)
                tex.append(r"\begin{equation}")
                tex.append(f_body)
                tex.append(r"\end{equation}")
                continue
            elif not in_formula:
                in_formula = True
                formula_lines = []
                continue
            else:
                in_formula = False
                f_body = "\n".join(formula_lines).strip()
                tex.append(r"\begin{equation}")
                tex.append(f_body)
                tex.append(r"\end{equation}")
                formula_lines = []
                continue
        if in_formula:
            if line_s.endswith("$$"):
                in_formula = False
                formula_lines.append(line_s[:-2].strip())
                f_body = "\n".join(formula_lines).strip()
                tex.append(r"\begin{equation}")
                tex.append(f_body)
                tex.append(r"\end{equation}")
                formula_lines = []
            else:
                formula_lines.append(line_s)
            continue

        # Check section headings
        if line_s.startswith("## 1 "):
            tex.append(r"\section{引言}")
            continue
        elif line_s.startswith("## 2 "):
            tex.append(r"\section{系统建模、遥测退化与备用决策形式化}")
            continue
        elif line_s.startswith("## 3 "):
            tex.append(r"\section{潜伏控制相变反演与正交两阶段决策方法}")
            continue
        elif line_s.startswith("## 4 "):
            tex.append(r"\section{实证算例、机制消融与工业选型准则}")
            continue
        elif line_s.startswith("## 5 "):
            tex.append(r"\section{结论与研究展望}")
            continue
        elif line_s.startswith("### 2.1 "):
            tex.append(r"\subsection{风电机组分段气动相变与机电动力学响应}")
            continue
        elif line_s.startswith("### 2.2 "):
            tex.append(r"\subsection{SCADA 遥测退化工况阶梯形式化}")
            continue
        elif line_s.startswith("### 2.3 "):
            tex.append(r"\subsection{日前备用决策与非对称报童考核损失}")
            continue
        elif line_s.startswith("### 3.1 "):
            tex.append(r"\subsection{基于机电动力学响应的潜伏状态反演机制}")
            continue
        elif line_s.startswith("### 3.2 "):
            tex.append(r"\subsection{预测期望定标与残差分位数估计解耦架构}")
            continue
        elif line_s.startswith("### 4.1 "):
            tex.append(r"\subsection{算例风电场与实验测试设置}")
            continue
        elif line_s.startswith("### 4.2 "):
            tex.append(r"\subsection{遥测退化阶梯下的基准性能对比}")
            continue
        elif line_s.startswith("### 4.3 "):
            tex.append(r"\subsection{机制消融、因果认知重构与工业选型准则}")
            continue
        elif line_s.startswith("---"):
            continue

        # Catch Table Caption
        if line_s.startswith("**表 "):
            table_caption = line_s.replace("**", "").strip()
            continue

        # Table detection
        if line_s.startswith("|"):
            if not in_table:
                in_table = True
                table_lines = [line_s]
            else:
                table_lines.append(line_s)
            continue
        else:
            if in_table:
                in_table = False
                tbl_tex = format_latex_table(table_lines, table_caption)
                if tbl_tex:
                    tex.append(tbl_tex)
                table_lines = []
                table_caption = ""

        # Normal text paragraph
        if line_s:
            p_line = re.sub(r"\*\*(.*?)\*\*", r"\\textbf{\1}", line_s)
            # escape % but not \%
            p_line = re.sub(r"(?<!\\)%", r"\%", p_line)
            tex.append(p_line + "\n")

    if in_table:
        tbl_tex = format_latex_table(table_lines, table_caption)
        if tbl_tex:
            tex.append(tbl_tex)

    # Add References
    tex.append(r"\begin{thebibliography}{99}")
    ref_section = md_text[ref_pos:]
    ref_matches = re.findall(r"\[(\d+)\]\s+(.*?)(?=\[\d+\]|```|$)", ref_section, flags=re.DOTALL)
    for num, ref_content in ref_matches:
        ref_c = ref_content.strip().replace("\n", " ")
        ref_c = re.sub(r"\s+", " ", ref_c)
        ref_c = ref_c.replace("&", r"\&")
        ref_c = re.sub(r"(?<!\\)%", r"\%", ref_c)
        tex.append(f"\\bibitem{{{num}}} {ref_c}")
    tex.append(r"\end{thebibliography}")
    tex.append(r"\end{document}")

    output_tex = "\n".join(tex)
    os.makedirs("build", exist_ok=True)
    with open("build/paper_chinese_topjournal.tex", "w", encoding="utf-8") as f:
        f.write(output_tex)
    print("Generated build/paper_chinese_topjournal.tex successfully.")

if __name__ == "__main__":
    build_chinese_topjournal_tex()
