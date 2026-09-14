from pathlib import Path
import json,re,hashlib
import pymupdf
from PIL import Image,ImageOps,ImageDraw

ROOT=Path(__file__).resolve().parent
pdf=ROOT/'main.pdf'
d=pymupdf.open(pdf)
pages=[];bad=[];missing=[];fonts={}
for i,p in enumerate(d):
    t=p.get_text()
    pages.append({'page':i+1,'characters':len(t),'first_lines':t.splitlines()[:3],
                  'last_lines':t.splitlines()[-3:]})
    if '\x00' in t or '\ufffd' in t:missing.append(i+1)
    for b in p.get_text('blocks'):
        if b[0]<0 or b[1]<0 or b[2]>p.rect.width+.5 or b[3]>p.rect.height+.5:
            bad.append({'page':i+1,'bbox':b[:4]})
    for f in p.get_fonts(full=True):
        fonts[f[0]]=f[3]
    p.get_pixmap(matrix=pymupdf.Matrix(1.3,1.3)).save(ROOT/'checks'/f'page_{i+1:02d}.png')

for start in range(0,len(d),4):
    canvas=Image.new('RGB',(1600,2290),'#d5d9db')
    for j,i in enumerate(range(start,min(start+4,len(d)))):
        im=Image.open(ROOT/'checks'/f'page_{i+1:02d}.png').convert('RGB')
        im.thumbnail((775,1100))
        x=15+(j%2)*800;y=15+(j//2)*1145
        canvas.paste(im,(x,y))
        ImageDraw.Draw(canvas).text((x+5,y+1104),f'Page {i+1}',fill='black')
    canvas.save(ROOT/'checks'/f'sheet_{start//4+1:02d}.jpg',quality=88)
log=(ROOT/'main.log').read_text(encoding='utf-8',errors='replace')
refs=[i+1 for i,p in enumerate(d) if '参考文献' in p.get_text()[:50]]
report={
 'pages_total':len(d),'reference_pages':refs,'pages_abstract_through_references':max(refs) if refs else None,
 'abstract_one_page':'关键词' in d[0].get_text() and '1.1' not in d[0].get_text(),
 'missing_glyph_pages':missing,'out_of_page_text':bad,
 'overfull_warnings':re.findall(r'Overfull.*',log),
 'undefined_warnings':re.findall(r'.*(?:undefined|Rerun to get).*',log),
 'citations_count':len(re.findall(r'\\bibitem', (ROOT/'sections'/'09_references.tex').read_text(encoding='utf-8'))),
 'figures_count':len(re.findall(r'\\newlabel\{fig:',(ROOT/'main.aux').read_text(encoding='utf-8'))),
 'tables_count':len(re.findall(r'\\newlabel\{tab:',(ROOT/'main.aux').read_text(encoding='utf-8'))),
 'fonts':[{'name':n,'embedded':bool(d.extract_font(x)[3]) or ('/Subtype /Type3' in d.xref_object(x) and '/CharProcs' in d.xref_object(x)),
           'kind':'glyph_programs' if '/Subtype /Type3' in d.xref_object(x) else 'font_file'} for x,n in fonts.items()],
 'bookmarks':len(d.get_toc()),'pages':pages,
 'pdf_sha256':hashlib.sha256(pdf.read_bytes()).hexdigest()
}
s=json.loads((ROOT/'checks'/'最终结果摘要.json').read_text(encoding='utf-8'))
expected={11:sum(s['q1_table_T'],[]),12:sum(s['q1_table_C'],[]),
          15:sum(s['q2_table_T'],[])+sum(s['q2_table_C'],[]),
          18:[v for row in s['q3_table'] for v in row['C']],
          22:[v for row in s['q4_table'] for v in row['C'] if v is not None]}
report['result_table_checks']=[
 {'page':pg,'checked_values':len(vals),'missing_values':[f'{v:.4f}' for v in vals if f'{v:.4f}' not in d[pg-1].get_text()]}
 for pg,vals in expected.items()]
archive=Path.home()/'Documents'/'A题计算工作记录_20260910'/'程序与验证'
report['original_code_unchanged']=all(p.read_bytes()==(archive/p.name).read_bytes() for p in (ROOT/'code').glob('*.py'))
report['footer_checks']=[]
for i,p in enumerate(d):
    hits=[w for w in p.get_text('words') if w[4]==str(i+1) and w[1]>p.rect.height-65]
    report['footer_checks'].append(bool(hits) and abs((hits[-1][0]+hits[-1][2])/2-p.rect.width/2)<3)
(ROOT/'checks'/'pdf_audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k not in ['pages','fonts']},ensure_ascii=False,indent=2))
for p in pages:print(p['page'],p['characters'],p['first_lines'])
