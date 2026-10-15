# -*- coding: utf-8 -*-
"""
Generate publication-quality Chinese Top-Journal Word (.docx) document
from manuscript/paper_chinese_topjournal_final.md
"""
import re
import os
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import qn, nsdecls

def set_cell_borders(cell, top=None, bottom=None, left=None, right=None):
    """Set custom cell borders using OXML."""
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcBorders = OxmlElement('w:tcBorders')
    
    borders = {'top': top, 'bottom': bottom, 'left': left, 'right': right}
    for edge, val in borders.items():
        if val is not None:
            border = OxmlElement(f'w:{edge}')
            border.set(qn('w:val'), val.get('val', 'single'))
            border.set(qn('w:sz'), str(val.get('sz', 4)))
            border.set(qn('w:space'), '0')
            border.set(qn('w:color'), val.get('color', 'auto'))
            tcBorders.append(border)
        else:
            border = OxmlElement(f'w:{edge}')
            border.set(qn('w:val'), 'none')
            tcBorders.append(border)
            
    tcPr.append(tcBorders)

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    """Set cell inner padding."""
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for m, val in [('top', top), ('bottom', bottom), ('left', left), ('right', right)]:
        node = OxmlElement(f'w:{m}')
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)

def set_run_font(run, font_name_ascii="Times New Roman", font_name_ea="宋体", size_pt=12, bold=False, italic=False, color_rgb=(0,0,0)):
    """Set both Western and EastAsian fonts for a run."""
    run.font.name = font_name_ascii
    run.font.size = Pt(size_pt)
    run.bold = bold
    run.italic = italic
    run.font.color.rgb = RGBColor(*color_rgb)
    
    rPr = run._r.get_or_add_rPr()
    rFonts = OxmlElement('w:rFonts')
    rFonts.set(qn('w:ascii'), font_name_ascii)
    rFonts.set(qn('w:hAnsi'), font_name_ascii)
    rFonts.set(qn('w:eastAsia'), font_name_ea)
    rFonts.set(qn('w:cs'), font_name_ascii)
    rPr.append(rFonts)

def add_styled_paragraph(doc, text="", style='Normal', space_before=0, space_after=2, line_spacing=1.25, indent=0, align=WD_ALIGN_PARAGRAPH.LEFT):
    p = doc.add_paragraph()
    p.alignment = align
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing = line_spacing
    if indent > 0:
        p.paragraph_format.first_line_indent = Pt(indent)
    return p

def clean_inline_math(text):
    """Convert LaTeX notation into clean academic text for Word."""
    # Replace common LaTeX math fragments with readable unicode
    t = text
    replacements = [
        (r'\ge', '≥'),
        (r'\le', '≤'),
        (r'\in', '∈'),
        (r'\times', '×'),
        (r'\pm', '±'),
        (r'\approx', '≈'),
        (r'\to', '→'),
        (r'\sim', '~'),
        (r'\cdot', '·'),
        (r'\circ', '°'),
        (r'\partial', '∂'),
        (r'\min', 'min'),
        (r'\max', 'max'),
        (r'\mathbb{R}_+', 'R₊'),
        (r'\mathbb{I}', 'I'),
        (r'\mathbb{E}', 'E'),
        (r'\mathcal{I}', 'I'),
        (r'\mathcal{L}', 'L'),
        (r'\rho_{\text{air}}', 'ρ_air'),
        (r'\rho', 'ρ'),
        (r'\tau_{\text{delay}}', 'τ_delay'),
        (r'\tau_e', 'τ_e'),
        (r'\tau', 'τ'),
        (r'\eta_g', 'η_g'),
        (r'\beta_{\text{opt}}', 'β_opt'),
        (r'\beta_{m,t}', 'β_{m,t}'),
        (r'\beta', 'β'),
        (r'\lambda_{m,t}', 'λ_{m,t}'),
        (r'\lambda', 'λ'),
        (r'\omega_{m,t}', 'ω_{m,t}'),
        (r'\omega', 'ω'),
        (r'\epsilon_{m,t}^e', 'ε^e_{m,t}'),
        (r'\epsilon', 'ε'),
        (r'\theta', 'θ'),
        (r'\phi', 'ϕ'),
        (r'\psi', 'ψ'),
        (r'\pi_{m,t}', 'π_{m,t}'),
        (r'\pi', 'π'),
        (r'\alpha', 'α'),
        (r'\Delta', 'Δ'),
        (r'\nabla', '∇'),
        (r'P_{\text{rated}}', 'P_rated'),
        (r'v_{\text{rated}}', 'v_rated'),
        (r'P_{m,t}^{\text{aero}}', 'P^aero_{m,t}'),
        (r'c_{\text{short}}', 'c_short'),
        (r'c_{\text{res}}', 'c_res'),
        (r'R^*_{t+h}', 'R*_{t+h}'),
        (r'q^*', 'q*'),
        (r'\text{AUROC}', 'AUROC'),
        (r'\text{MSE}', 'MSE'),
        (r'\text{Cost}', 'Cost'),
        (r'\text{withheld}', 'withheld'),
        (r'\text{align}', 'align'),
        (r'\text{res}', 'res'),
        (r'\text{short}', 'short'),
        (r'\text{viol}', 'viol'),
        (r'\text{min}', 'min'),
    ]
    for old, new in replacements:
        t = t.replace(old, new)
    # Remove remaining backslashes from clean LaTeX tags
    t = re.sub(r'\\text\{([^}]+)\}', r'\1', t)
    t = re.sub(r'\\mathbf\{([^}]+)\}', r'\1', t)
    t = re.sub(r'\\mathit\{([^}]+)\}', r'\1', t)
    t = re.sub(r'\\hat\{([^}]+)\}', r'\1̂', t)
    t = re.sub(r'\\bar\{([^}]+)\}', r'\1̄', t)
    t = t.replace(r'\%', '%')
    t = t.replace(r'\_', '_')
    return t

def format_mixed_text(p, text, default_size=12, default_bold=False, default_italic=False, default_ea='宋体', default_ascii='Times New Roman'):
    """Split text into bold, math ($...$), and regular text, adding runs properly."""
    # Pattern to find bold (**...**) and inline math ($...$)
    tokens = re.split(r'(\*\*[^*]+\*\*|\$[^\$]+\$)', text)
    for token in tokens:
        if not token:
            continue
        if token.startswith('**') and token.endswith('**'):
            inner = token[2:-2]
            # inner might contain math
            sub_tokens = re.split(r'(\$[^\$]+\$)', inner)
            for st in sub_tokens:
                if st.startswith('$') and st.endswith('$'):
                    math_txt = clean_inline_math(st[1:-1])
                    run = p.add_run(math_txt)
                    set_run_font(run, font_name_ascii=default_ascii, font_name_ea=default_ea, size_pt=default_size, bold=True, italic=True)
                else:
                    run = p.add_run(st)
                    set_run_font(run, font_name_ascii=default_ascii, font_name_ea=default_ea, size_pt=default_size, bold=True, italic=default_italic)
        elif token.startswith('$') and token.endswith('$'):
            math_txt = clean_inline_math(token[1:-1])
            run = p.add_run(math_txt)
            set_run_font(run, font_name_ascii="Cambria Math", font_name_ea=default_ea, size_pt=default_size, bold=default_bold, italic=True)
        else:
            run = p.add_run(token)
            set_run_font(run, font_name_ascii=default_ascii, font_name_ea=default_ea, size_pt=default_size, bold=default_bold, italic=default_italic)

def build_docx(md_path, docx_path):
    print(f"Reading {md_path}...")
    with open(md_path, 'r', encoding='utf-8') as f:
        md_text = f.read()

    doc = docx.Document()

    # Set page layout to A4, 2.54 cm margins
    for section in doc.sections:
        section.page_width = Inches(8.27)  # 21.0 cm
        section.page_height = Inches(11.69) # 29.7 cm
        section.top_margin = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin = Inches(1.0)
        section.right_margin = Inches(1.0)

    # Split text into lines
    lines = md_text.split('\n')
    idx = 0
    total_lines = len(lines)

    in_table = False
    table_lines = []
    in_math_block = False
    math_lines = []
    in_bib_block = False

    while idx < total_lines:
        line = lines[idx].strip()

        # Handle horizontal divider
        if line == '---':
            idx += 1
            continue

        # Handle Code block (e.g. bibtex)
        if line.startswith('```'):
            in_bib_block = not in_bib_block
            idx += 1
            continue

        if in_bib_block:
            # Format reference entries
            if line.startswith('[') and ']' in line:
                p = add_styled_paragraph(doc, space_before=2, space_after=3, line_spacing=1.15, align=WD_ALIGN_PARAGRAPH.JUSTIFY)
                p.paragraph_format.left_indent = Pt(24)
                p.paragraph_format.first_line_indent = Pt(-24)
                format_mixed_text(p, line, default_size=10, default_ea='宋体', default_ascii='Times New Roman')
            idx += 1
            continue

        # Handle Math block ($$...$$)
        if line.startswith('$$'):
            if line.endswith('$$') and len(line) > 2:
                # single line math block
                formula = line[2:-2].strip()
                p = add_styled_paragraph(doc, space_before=6, space_after=6, line_spacing=1.25, align=WD_ALIGN_PARAGRAPH.CENTER)
                cleaned = clean_inline_math(formula)
                run = p.add_run(cleaned)
                set_run_font(run, font_name_ascii="Cambria Math", font_name_ea="宋体", size_pt=11.5, italic=True)
                idx += 1
                continue
            else:
                # multiline math block start
                in_math_block = True
                math_lines = []
                idx += 1
                continue

        if in_math_block:
            if line.endswith('$$'):
                in_math_block = False
                formula = " ".join(math_lines + [line[:-2].strip()])
                p = add_styled_paragraph(doc, space_before=6, space_after=6, line_spacing=1.25, align=WD_ALIGN_PARAGRAPH.CENTER)
                cleaned = clean_inline_math(formula)
                run = p.add_run(cleaned)
                set_run_font(run, font_name_ascii="Cambria Math", font_name_ea="宋体", size_pt=11.5, italic=True)
                idx += 1
                continue
            else:
                math_lines.append(line)
                idx += 1
                continue

        # Handle Tables (| ... |)
        if line.startswith('|') and line.endswith('|'):
            table_lines.append(line)
            idx += 1
            # peek next line
            if idx < total_lines and not (lines[idx].strip().startswith('|') and lines[idx].strip().endswith('|')):
                # Table ended, render it
                render_table(doc, table_lines)
                table_lines = []
            continue

        # Handle Title (# ...)
        if line.startswith('# '):
            title_text = line[2:].strip()
            p = add_styled_paragraph(doc, space_before=12, space_after=12, line_spacing=1.25, align=WD_ALIGN_PARAGRAPH.CENTER)
            run = p.add_run(title_text)
            set_run_font(run, font_name_ascii="SimHei", font_name_ea="黑体", size_pt=20, bold=True)
            idx += 1
            continue

        # Handle Level 1 Heading (## ...)
        if line.startswith('## '):
            h_text = line[3:].strip()
            p = add_styled_paragraph(doc, space_before=14, space_after=6, line_spacing=1.25, align=WD_ALIGN_PARAGRAPH.LEFT)
            p.paragraph_format.keep_with_next = True
            run = p.add_run(h_text)
            set_run_font(run, font_name_ascii="SimHei", font_name_ea="黑体", size_pt=15, bold=True)
            idx += 1
            continue

        # Handle Level 2 Heading (### ...)
        if line.startswith('### '):
            h_text = line[4:].strip()
            if h_text == '摘要':
                p = add_styled_paragraph(doc, space_before=10, space_after=4, line_spacing=1.25, align=WD_ALIGN_PARAGRAPH.CENTER)
                p.paragraph_format.keep_with_next = True
                run = p.add_run("摘  要")
                set_run_font(run, font_name_ascii="SimHei", font_name_ea="黑体", size_pt=13, bold=True)
            else:
                p = add_styled_paragraph(doc, space_before=10, space_after=4, line_spacing=1.25, align=WD_ALIGN_PARAGRAPH.LEFT)
                p.paragraph_format.keep_with_next = True
                run = p.add_run(h_text)
                set_run_font(run, font_name_ascii="SimHei", font_name_ea="黑体", size_pt=13, bold=True)
            idx += 1
            continue

        # Handle Author block
        if line.startswith('**作者信息**') or line.startswith('**作者单位**') or line.startswith('**通讯作者**'):
            p = add_styled_paragraph(doc, space_before=2, space_after=4, line_spacing=1.2, align=WD_ALIGN_PARAGRAPH.CENTER)
            format_mixed_text(p, line, default_size=11, default_ea='楷体', default_ascii='Times New Roman')
            idx += 1
            continue

        # Handle Images (![...](...))
        m_img = re.match(r'!\[(.*?)\]\((.*?)\)', line)
        if m_img:
            img_rel_path = m_img.group(2).strip()
            # Search candidates for image file
            cand_paths = [
                img_rel_path,
                os.path.abspath(img_rel_path),
                os.path.join(os.path.dirname(os.path.abspath(md_path)), img_rel_path),
                os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(md_path))), img_rel_path),
                os.path.join("figures", os.path.basename(img_rel_path)),
            ]
            found_img = None
            for cp in cand_paths:
                if os.path.exists(cp):
                    found_img = cp
                    break

            if found_img:
                p_img = doc.add_paragraph()
                p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p_img.paragraph_format.space_before = Pt(8)
                p_img.paragraph_format.space_after = Pt(2)
                p_img.paragraph_format.keep_with_next = True
                run_img = p_img.add_run()
                # 5.8 inches width nicely fits within 8.27 - 2 = 6.27 inches margins
                run_img.add_picture(found_img, width=Inches(5.8))
                print(f"  [Word] Embedded figure: {found_img}")
            else:
                print(f"  [Word WARNING] Figure not found: {img_rel_path}")

            idx += 1
            continue

        # Handle Figure Caption (**图 X** ...)
        if line.startswith('**图') and ('**' in line[3:]):
            p = add_styled_paragraph(doc, space_before=2, space_after=8, line_spacing=1.2, align=WD_ALIGN_PARAGRAPH.CENTER)
            format_mixed_text(p, line, default_size=10.5, default_bold=True, default_ea='黑体', default_ascii='Times New Roman')
            idx += 1
            continue

        # Handle Table Caption (**表 X** ...)
        if line.startswith('**表') and ('**' in line[3:]):
            p = add_styled_paragraph(doc, space_before=10, space_after=4, line_spacing=1.2, align=WD_ALIGN_PARAGRAPH.CENTER)
            p.paragraph_format.keep_with_next = True
            format_mixed_text(p, line, default_size=10.5, default_bold=True, default_ea='黑体', default_ascii='Times New Roman')
            idx += 1
            continue

        # Handle Keywords
        if line.startswith('**关键词**'):
            p = add_styled_paragraph(doc, space_before=6, space_after=14, line_spacing=1.25, indent=0, align=WD_ALIGN_PARAGRAPH.JUSTIFY)
            p.paragraph_format.left_indent = Pt(24)
            p.paragraph_format.right_indent = Pt(24)
            format_mixed_text(p, line, default_size=10.5, default_ea='楷体', default_ascii='Times New Roman')
            idx += 1
            continue

        # Empty line
        if not line:
            idx += 1
            continue

        # Regular body paragraph
        p = add_styled_paragraph(doc, space_before=0, space_after=3, line_spacing=1.25, indent=24, align=WD_ALIGN_PARAGRAPH.JUSTIFY)
        format_mixed_text(p, line, default_size=12, default_ea='宋体', default_ascii='Times New Roman')
        idx += 1

    # Save document
    os.makedirs(os.path.dirname(docx_path), exist_ok=True)
    doc.save(docx_path)
    print(f"Successfully saved Word document to: {docx_path}")

def render_table(doc, raw_lines):
    """Render a standard Chinese academic three-line table (三线表)."""
    rows_data = []
    for l in raw_lines:
        cells = [c.strip() for c in l.split('|')[1:-1]]
        # Filter out divider lines like |:---|:---:|
        if any(c.startswith(':-') or c.startswith('--') or c.endswith('-:') for c in cells):
            continue
        rows_data.append(cells)

    if not rows_data:
        return

    num_rows = len(rows_data)
    num_cols = len(rows_data[0])

    table = doc.add_table(rows=num_rows, cols=num_cols)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = True

    # Borders for academic three-line table
    top_border = {'val': 'single', 'sz': 12, 'color': '000000'}    # 1.5 pt
    mid_border = {'val': 'single', 'sz': 6, 'color': '000000'}     # 0.75 pt
    bot_border = {'val': 'single', 'sz': 12, 'color': '000000'}    # 1.5 pt

    for r_idx, row in enumerate(rows_data):
        for c_idx, cell_value in enumerate(row):
            if c_idx >= num_cols:
                continue
            cell = table.cell(r_idx, c_idx)
            cell.text = "" # Clear default paragraph
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.line_spacing = 1.15

            # Font styling: header bold, body regular
            is_header = (r_idx == 0)
            format_mixed_text(p, cell_value, default_size=10, default_bold=is_header, default_ea='黑体' if is_header else '宋体', default_ascii='Times New Roman')

            # Three-line table borders
            b_top = top_border if r_idx == 0 else None
            b_bot = mid_border if r_idx == 0 else (bot_border if r_idx == num_rows - 1 else None)
            set_cell_borders(cell, top=b_top, bottom=b_bot, left=None, right=None)
            set_cell_margins(cell, top=80, bottom=80, left=100, right=100)

    # Add small spacing after table
    p_spacer = doc.add_paragraph()
    p_spacer.paragraph_format.space_before = Pt(0)
    p_spacer.paragraph_format.space_after = Pt(6)

if __name__ == '__main__':
    src = "manuscript/paper_chinese_topjournal_final.md"
    dst = "manuscript/论文_潜伏控制相变与遥测退化约束下的风电运行备用决策_最小充分模型准则.docx"
    build_docx(src, dst)
    dst2 = "build/paper_chinese_topjournal.docx"
    build_docx(src, dst2)
