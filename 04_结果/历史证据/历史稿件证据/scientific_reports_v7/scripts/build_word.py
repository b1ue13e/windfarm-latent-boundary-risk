"""Create editable Word companions from the same manuscript and SI sources."""
from pathlib import Path
import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
from zipfile import ZipFile

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT=Path(__file__).resolve().parents[1]
BUILD=ROOT/'build/word'
PANDOC=Path(os.environ.get('PANDOC',str(ROOT.parents[1]/'tools/pandoc-3.9.0.2/pandoc.exe')))
if not PANDOC.is_file():
    located=shutil.which('pandoc')
    if not located:raise FileNotFoundError('Pandoc is required')
    PANDOC=Path(located)


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def remove_children(parent,tag):
    for child in list(parent.findall(qn(tag))):parent.remove(child)


def base_styles(doc,si=False):
    sec=doc.sections[0]
    # Match the existing manuscript review layout rather than introduce a template.
    sec.page_width=Cm(21);sec.page_height=Cm(29.7)
    sec.top_margin=sec.bottom_margin=sec.left_margin=sec.right_margin=Cm(2.3)
    sec.header_distance=sec.footer_distance=Cm(1.0)
    for style in doc.styles:
        if style.type in [1,2]:
            style.font.name='Times New Roman';style.font.color.rgb=RGBColor(0,0,0)
            style.font.underline=False
            fonts=style.element.find('.//'+qn('w:rFonts'))
            if fonts is not None:
                for key in list(fonts.attrib):
                    if 'theme' in key.lower():del fonts.attrib[key]
                fonts.set(qn('w:eastAsia'),'Times New Roman')
                fonts.set(qn('w:cs'),'Times New Roman')
    for name in ['Normal','Body Text','First Paragraph']:
        if name in doc.styles:
            st=doc.styles[name];st.font.size=Pt(10.5 if si else 11)
            st.paragraph_format.space_after=Pt(6)
            st.paragraph_format.line_spacing=1.08
            st.paragraph_format.first_line_indent=Cm(0)
            st.paragraph_format.widow_control=True
    for name,size in [('Title',15),('Subtitle',11),('Author',11),('Date',10),('Heading 1',13),('Heading 2',11),('Heading 3',10.5),('Caption',9.5),('Image Caption',9.5),('Table Caption',9.5),('Bibliography',9.5)]:
        if name not in doc.styles:continue
        st=doc.styles[name];st.font.size=Pt(size)
        st.font.bold=name.startswith('Heading')
        if name in ['Title','Subtitle','Caption','Image Caption','Table Caption']:st.font.italic=False
        pf=st.paragraph_format
        pf.space_before=Pt(10 if name.startswith('Heading') else 0)
        pf.space_after=Pt(5 if name.startswith('Heading') else 7)
        pf.keep_with_next=name.startswith('Heading')
        if name in ['Title','Subtitle','Author','Date']:pf.alignment=WD_ALIGN_PARAGRAPH.CENTER
        if name=='Bibliography':pf.line_spacing=1.0;pf.space_after=Pt(4)
        ppr=st.element.find(qn('w:pPr'))
        if ppr is not None:remove_children(ppr,'w:pBdr')
    footer=sec.footer.paragraphs[0]
    footer.alignment=WD_ALIGN_PARAGRAPH.CENTER
    for child in list(footer._p):
        if child.tag!=qn('w:pPr'):footer._p.remove(child)
    field=OxmlElement('w:fldSimple');field.set(qn('w:instr'),'PAGE')
    footer._p.append(field)
    for run in footer.runs:run.font.size=Pt(9)


def table_widths(header):
    if header[:2]==['Estimator','Input'] and len(header)==6:return [2,6,2.1,2.1,2.1,2.1]
    if len(header)==9:return [1.7,1.7,3,1,1.7,1.7,1.7,1.7,2.2]
    if len(header)==8:return [2.2,1.7,3.1,1.9,1.9,1.9,1.7,2]
    if len(header)==7:return [1.9,1.7,3.9,1.6,1.1,2.1,4.1]
    if len(header)==4 and header[0]=='Stage':return [3.8,3.6,3,6]
    if len(header)==4:return [5.6,2,3.1,5.7]
    if len(header)==5 and header[0]=='Fixed-fit seed':return [2.3,3.2,3.2,3.6,4.1]
    if len(header)==5 and header[-1]=='Uniformly small pitch increment':return [2,2.4,3.5,3.5,5]
    if len(header)==5:return [1.8,4.7,3.3,3.3,3.3]
    return [16.4/len(header)]*len(header)


def polish_docx(path,si):
    doc=Document(path);base_styles(doc,si)
    for paragraph in doc.paragraphs:
        text=paragraph.text
        if text.startswith('School of Statistics') or text.startswith('Anhui University') or text.startswith('Correspondence:'):
            paragraph.alignment=WD_ALIGN_PARAGRAPH.CENTER
            paragraph.paragraph_format.space_after=Pt(3)
            for run in paragraph.runs:run.font.size=Pt(10)
        if paragraph._p.xpath('.//w:drawing'):
            paragraph.paragraph_format.keep_with_next=True
            paragraph.paragraph_format.space_before=Pt(4)
            paragraph.paragraph_format.space_after=Pt(3)
            paragraph.alignment=WD_ALIGN_PARAGRAPH.CENTER
        if text.startswith('Supplementary Table') or text.startswith('Table 1.'):
            paragraph.paragraph_format.keep_with_next=True
            paragraph.paragraph_format.space_before=Pt(6)
            for run in paragraph.runs:run.font.size=Pt(9.5)
    for table in doc.tables:
        header=[c.text.strip() for c in table.rows[0].cells]
        widths=table_widths(header);assert abs(sum(widths)-16.4)<0.01
        table.autofit=False
        for col,width in zip(table.columns,widths):col.width=Cm(width)
        pr=table._tbl.tblPr
        total_width=pr.find(qn('w:tblW'))
        total_width.set(qn('w:type'),'dxa');total_width.set(qn('w:w'),str(round(16.4/2.54*1440)))
        remove_children(pr,'w:tblBorders')
        borders=OxmlElement('w:tblBorders')
        for edge in ['top','bottom']:
            node=OxmlElement('w:'+edge);node.set(qn('w:val'),'single');node.set(qn('w:sz'),'6');node.set(qn('w:color'),'777777');borders.append(node)
        layout=pr.find(qn('w:tblLayout'))
        pr.insert(list(pr).index(layout) if layout is not None else len(pr),borders)
        for ri,row in enumerate(table.rows):
            trpr=row._tr.get_or_add_trPr()
            remove_children(trpr,'w:cantSplit');remove_children(trpr,'w:tblHeader')
            node=OxmlElement('w:cantSplit');trpr.append(node)
            if ri==0:
                node=OxmlElement('w:tblHeader');trpr.append(node)
            for ci,(cell,width) in enumerate(zip(row.cells,widths)):
                cell.width=Cm(width)
                tcpr=cell._tc.get_or_add_tcPr();margins=OxmlElement('w:tcMar')
                for side,n in [('top',55),('bottom',55),('left',65),('right',65)]:
                    node=OxmlElement('w:'+side);node.set(qn('w:w'),str(n));node.set(qn('w:type'),'dxa');margins.append(node)
                tcpr.append(margins)
                for para in cell.paragraphs:
                    pf=para.paragraph_format;pf.space_before=pf.space_after=Pt(0)
                    pf.line_spacing=1.0;pf.keep_with_next=False
                    para.alignment=WD_ALIGN_PARAGRAPH.LEFT if ci<2 else WD_ALIGN_PARAGRAPH.RIGHT
                    for run in para.runs:run.font.size=Pt(9.5);run.font.bold=ri==0
    doc.core_properties.author='Junyu Li and Juntao Du'
    doc.core_properties.last_modified_by='OpenAI Codex'
    doc.core_properties.comments=''
    doc.save(path)


def word_source(stem):
    text=(ROOT/(stem+'.md')).read_text(encoding='utf-8')
    _,front,body=text.split('---',2)
    title=re.search(r'^title: "(.*)"',front,re.M).group(1)
    meta={'title':title,'author':'Junyu Li and Juntao Du','date':'','lang':'en-GB',
          'bibliography':'references.bib','csl':'scientific-reports-brackets.csl','link-citations':True}
    # JSON strings are valid YAML values and preserve punctuation without shell interpolation.
    header='---\n'+''.join(k+': '+json.dumps(v,ensure_ascii=False)+'\n' for k,v in meta.items())+'---\n\n'
    if stem=='manuscript':
        abstract=front.split('abstract: |\n',1)[1].strip()
        body=('School of Statistics and Applied Mathematics\n\n'
              'Anhui University of Finance and Economics, Bengbu 233030, China\n\n'
              'Correspondence: Juntao Du, dujuntao@aufe.edu.cn\n\n'
              '# Abstract\n\n'+abstract+'\n\n'+body.lstrip())
        tex=(ROOT/'tables/table1.tex').read_text(encoding='utf-8')
        caption=re.search(r'\\caption\*\{(.*?)\}\s*\\small',tex,re.S).group(1)
        caption=re.sub(r'\\textbf\{([^{}]+)\}',r'**\1**',caption)
        with (ROOT/'tables/table1.csv').open(encoding='utf-8-sig',newline='') as handle:rows=list(csv.reader(handle))
        table='| '+' | '.join(rows[0])+' |\n| '+' | '.join(['---']*len(rows[0]))+' |\n'+''.join('| '+' | '.join(r)+' |\n' for r in rows[1:])
        body=body.replace(r'\input{tables/table1.tex}',caption+'\n\n'+table)
    else:
        subtitle=re.search(r'^subtitle: "(.*)"',front,re.M).group(1)
        header=header.replace('---\n\n','subtitle: '+json.dumps(subtitle)+'\n---\n\n')
    body=re.sub(r'\]\(figures/([^\n)]+)\.pdf\)\{width=100%\}',r'](figures/\1.png){width=16.4cm}',body)
    body=re.sub(r'\\rm\s+([A-Za-z]+)',r'\\mathrm{\1}',body)
    body=body.replace(r'\bar C',r'\overline{C}')
    # Word uses two native display equations for the same grouped definitions.
    def word_displays(match):
        lines=match.group(1).replace('\n&','\n').split(r'\\[4pt]')
        return '\n\n'.join('$$\n'+line.strip()+'\n$$' for line in lines)
    body=re.sub(r'\$\$\s*\\begin\{aligned\}(.*?)\\end\{aligned\}\s*\$\$',word_displays,body,flags=re.S)
    body=body.replace(r'\mid',r'\mathrel{|}')
    return header+body


def main():
    BUILD.mkdir(parents=True,exist_ok=True)
    reference=BUILD/'reference.docx'
    template=subprocess.run([str(PANDOC),'--print-default-data-file=reference.docx'],capture_output=True,check=True)
    reference.write_bytes(template.stdout)
    doc=Document(reference);base_styles(doc);doc.save(reference)
    receipt=[]
    for stem in ['manuscript','supplementary']:
        source=BUILD/(stem+'_word.md');source.write_text(word_source(stem),encoding='utf-8')
        target=ROOT/(stem+'.docx')
        cmd=[str(PANDOC),str(source),'--standalone','--citeproc','--from=markdown+tex_math_dollars',
             '--reference-doc='+str(reference),'--resource-path='+str(ROOT),'--output='+str(target)]
        result=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,encoding='utf-8')
        (BUILD/(stem+'_pandoc.log')).write_text(result.stdout+result.stderr,encoding='utf-8')
        result.check_returncode()
        if 'Could not convert TeX math' in result.stderr or 'not found' in result.stderr.lower():raise RuntimeError(result.stderr)
        polish_docx(target,stem=='supplementary')
        with ZipFile(target) as z:xml=z.read('word/document.xml').decode('utf-8')
        assert '<m:oMath' in xml,'Native Word equations are absent'
        assert '\\input' not in xml
        receipt.append({'document':target.name,'source_sha256':sha(ROOT/(stem+'.md')),
                        'docx_sha256':sha(target),'native_math':True,
                        'figures':len(Document(target).inline_shapes),'tables':len(Document(target).tables)})
    (ROOT/'author_working/qa/word_build.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print('Word companions generated from manuscript and SI sources.')


if __name__=='__main__':main()
