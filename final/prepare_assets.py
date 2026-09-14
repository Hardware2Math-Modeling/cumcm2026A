"""Read existing summaries and copy figures. Does not invoke the PDE solver."""
from pathlib import Path
import json, shutil

ROOT=Path(__file__).resolve().parent
ARCHIVE=Path.home()/'Documents'/'A题计算工作记录_20260910'
S=json.loads((ARCHIVE/'程序与验证'/'最终结果摘要.json').read_text(encoding='utf-8'))
V=json.loads((ARCHIVE/'程序与验证'/'精度核验.json').read_text(encoding='utf-8'))
for d in ['figures','tables','code','checks','sections']:
    (ROOT/d).mkdir(exist_ok=True)
for i in range(1,9):
    p=next((ARCHIVE/'图片').glob(f'图{i}_*.pdf'))
    shutil.copy2(p,ROOT/'figures'/f'fig{i}.pdf')
for p in (ARCHIVE/'程序与验证').glob('*.py'):
    shutil.copy2(p,ROOT/'code'/p.name)
for name in ['最终结果摘要.json','精度核验.json']:
    shutil.copy2(ARCHIVE/'程序与验证'/name,ROOT/'checks'/name)

def table(name,head,rows,caption,label,small=False):
    n=len(head)
    tex=r'\begin{table}[H]\centering'+'\n'
    if small:tex+=r'\small'+'\n'
    tex+=r'\caption{'+caption+r'}\label{'+label+'}\n'
    tex+=r'\begin{tabular}{'+'c'*n+r'}\toprule'+'\n'
    tex+=' & '.join(head)+r'\\ \midrule'+'\n'
    tex+='\n'.join(' & '.join(row)+r'\\' for row in rows)
    tex+='\n'+r'\bottomrule\end{tabular}\end{table}'+'\n'
    (ROOT/'tables'/f'{name}.tex').write_text(tex,encoding='utf-8')

for q in [1,2]:
    for var in ['T','C']:
        head=['时间/'+('s' if q==1 else 'h')]+[f'{r:g} cm' for r in [0,.5,1,1.5,2]]
        rows=[[str(t) if q==1 else f'{t/3600:.1f}']+[f'{v:.4f}' for v in vals]
              for t,vals in zip(S[f'q{q}_table_times_s'],S[f'q{q}_table_{var}'])]
        cap=f'问题{q}：'+('温度分布（'+r'$^\circ$C）' if var=='T' else r'干基含水率分布（kg/kg）')
        table(f'q{q}_{var}',head,rows,cap,f'tab:q{q}{var}')
table('q3',['时间/h','0 cm','0.5 cm','1 cm','1.5 cm','2 cm'],
 [[f'{r["time_h"]:.4f}']+[f'{v:.4f}' for v in r['C']] for r in S['q3_table']],
 '问题3：固定半径下全程干基含水率（kg/kg）','tab:q3')
table('q4',['时间/h','0 cm','0.5 cm','1 cm','表面',r'$R$/cm'],
 [[f'{r["time_h"]:.4f}']+[f'{v:.4f}' for v in r['C'][:3]]+[f'{r["C"][-1]:.4f}',f'{r["radius_cm"]:.4f}'] for r in S['q4_table']],
 '问题4：实际位置的干基含水率（kg/kg）与当前半径','tab:q4')
rows=[]
for name in ['n160','n320','s640','s1280','s2560']:
    a=json.loads((ARCHIVE/'程序与验证'/f'q23_{name}.json').read_text(encoding='utf-8'))
    b=json.loads((ARCHIVE/'程序与验证'/f'q4_{name}.json').read_text(encoding='utf-8'))
    rows.append([('均匀' if name[0]=='n' else '表面加密')+name[1:],f'{a["finish_h"]:.7f}',f'{b["finish_h"]:.7f}'])
table('grids',['网格方案','问题3时间/h','问题4时间/h'],rows,'空间网格细化后的临界时间','tab:grids')
print('Prepared 8 vector figures, 7 tables, and archived source files. No PDE recomputation.')
