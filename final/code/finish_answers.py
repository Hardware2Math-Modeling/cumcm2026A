from pathlib import Path
import json,shutil,math
import openpyxl
ROOT=Path(__file__).resolve().parents[1]
DEST=Path.home()/'Desktop'/'A题_计算答案'
DEST.mkdir(exist_ok=True)
s=json.loads((ROOT/'程序与验证'/'最终结果摘要.json').read_text(encoding='utf-8'))
lines=['A题四问计算答案','',
'以下为明确简化模型下的数值答案，不是题目未明确条件下的唯一物理答案。',
'采用：径向有效导热扩散模型；忽略蒸发潜热；附件1空气水分数值作为有效边界值。',
'前4小时环境按附件1线性插值；4小时后使用3～4小时均值：49.9989344262°C、0.0499875410 kg/kg。',
'第4问采用附录4物性、附件2半径线性插值、均匀径向材料收缩及长度固定，密度用于有效热容量。',
'计算采用表面加密有限体积网格（2560个径向区间）及自适应隐式BDF时间积分。',
'',f'问题3：整体含水率达到0.15的临界时间约 {s["23"]["finish_h"]:.4f} h。',
f'问题4：整体含水率达到0.15的临界时间约 {s["4"]["finish_h"]:.4f} h。',
'以上是连续时间的临界值，严格低于发生在其后。考虑已检查的数值误差，按下一整秒报告更稳妥：',
'第三问206907 s（约57.4742 h），第四问183932 s（约51.0922 h）；这是阈值后的报告时刻。',
'不要仅凭Excel中四舍五入后的0.1500判断未舍入数值是否已经严格达标。','']
def fmt(v):return '—' if v is None else f'{v:.4f}'
for q in [1,2]:
 for field,label,unit in [('T','温度','°C'),('C','干基含水率','kg/kg')]:
  lines+=[f'问题{q}：{label}（{unit}）','时间/'+('s' if q==1 else 'h')+'\t0 cm\t0.5 cm\t1 cm\t1.5 cm\t2 cm']
  for t,row in zip(s[f'q{q}_table_times_s'],s[f'q{q}_table_{field}']):
   tt=str(t) if q==1 else f'{t/3600:.1f}'
   lines.append(tt+'\t'+'\t'.join(map(fmt,row)))
  lines+=['']
for q in [3,4]:
 lines+=[f'问题{q}：全过程干基含水率（kg/kg）','时间/h\t0 cm\t0.5 cm\t1 cm\t1.5 cm\t'+('2 cm' if q==3 else '当前表面')+('\t当前半径/cm' if q==4 else '')]
 for row in s[f'q{q}_table']:
  line=f'{row["time_h"]:.4f}\t'+'\t'.join(map(fmt,row['C']))
  if q==4:line+=f'\t{row["radius_cm"]:.4f}'
  lines.append(line)
 lines+=['']
lines+=['结果文件说明：','result1.xlsx：1～1800 s，每秒、每0.1 cm，温度与含水率两个结果表。','result2.xlsx：1～10800 s，每秒、每0.1 cm，温度与含水率两个结果表。','result3.xlsx：每60 s到结束临界时刻，另补临界时刻一行，每0.1 cm的含水率。','result4.xlsx：每60 s到结束临界时刻，固定距离列超出当前半径时留空，末列给当前表面值；附半径工作表。','','验证：','第一问与360项圆柱热传导级数参考解比较，输出点最大温差约2.8×10^-7°C。','第一问1280与2560区间网格比较，输出点最大含水率差约6.9×10^-7 kg/kg。','第三问1280与2560区间网格的结束时间差约0.0243 s；第四问约0.0095 s。','收紧时间容差十倍后，第三、四问结束时间变化均小于0.001 s。','参考干质量基准下的全体水分收支误差约10^-14 kg/kg（数值舍入尺度）。','','假设敏感性：','若4小时后改为保持附件最后一个环境值50.165°C、0.04986 kg/kg，则640区间验证网格上，','第三问约57.1694 h，第四问约50.8242 h。这种假设影响远大于网格与时间积分误差。','因此四位小数表示本模型的数值结果，并不意味着真实烘干时长具备四位小数的物理精度。']
(DEST/'四问答案与说明.txt').write_text('\n'.join(lines),encoding='utf-8-sig')
checks=[]
for q in range(1,5):
 src=ROOT/f'result{q}.xlsx';dest=DEST/src.name;shutil.copy2(src,dest)
 wb=openpyxl.load_workbook(dest,read_only=True,data_only=True)
 for ws in wb:
  if ws.title not in ['温度','水分浓度']:continue
  rows=ws.iter_rows(values_only=True);header=next(rows);count=0;prev=0;last=None
  for row in rows:
   assert row[0]>prev,(q,ws.title,row[0],prev)
   prev=row[0];count+=1;last=row
   for v in row[1:]:
    if v is None:assert q==4
    else:assert isinstance(v,(float,int)) and math.isfinite(v)
  if q==1:assert count==1800
  if q==2:assert count==10800
  checks.append({'file':dest.name,'sheet':ws.title,'rows':count,'columns':len(header),'last_time_s':last[0]})
 wb.close()
(DEST/'数据文件核验.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf-8')
for f in ['精度核验.json','最终结果摘要.json']:
 if (ROOT/'程序与验证'/f).exists():shutil.copy2(ROOT/'程序与验证'/f,DEST/f)
print('READY',DEST);print(json.dumps(checks,ensure_ascii=False))
