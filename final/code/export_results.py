from pathlib import Path
import json,shutil
import numpy as np
from scipy.interpolate import PchipInterpolator
import openpyxl
from openpyxl.cell import WriteOnlyCell
from openpyxl.styles import Font,PatternFill,Alignment
from solve_model import ROOT,AIR,RAD,PLATEAU

def fixed_sample(x,arr,q):
 out=np.empty((len(arr),len(q)))
 for i in range(0,len(arr),64):out[i:i+64]=PchipInterpolator(x,arr[i:i+64],axis=1)(q)
 return out

def write_book(path,times,fields,rheads,extra=None):
 wb=openpyxl.Workbook(write_only=True)
 for name,array in fields.items():
  ws=wb.create_sheet(name);ws.freeze_panes='B2'
  ws.column_dimensions['A'].width=22
  for k in range(2,len(rheads)+2):ws.column_dimensions[openpyxl.utils.get_column_letter(k)].width=13
  heads=['时间/s；径向位置/cm']+list(rheads)
  row=[]
  for v in heads:
   c=WriteOnlyCell(ws,value=v);c.font=Font(name='微软雅黑',bold=True,color='FFFFFF');c.fill=PatternFill('solid',fgColor='18384F');c.alignment=Alignment(horizontal='center');row.append(c)
  ws.append(row)
  for t,vals in zip(times,array):
   c=WriteOnlyCell(ws,value=float(t));c.number_format='0.0000';row=[c]
   for v in vals:
    c=WriteOnlyCell(ws,value=None if not np.isfinite(v) else round(float(v),4));c.number_format='0.0000';row.append(c)
   ws.append(row)
 if extra is not None:
  ws=wb.create_sheet('当前表面位置');ws.append(['时间/s','当前半径/cm'])
  for t,r in zip(times,extra):ws.append([float(t),float(r)*100])
 ws=wb.create_sheet('说明')
 notes=['计算采用圆柱径向有效传热传质模型；具体假设、验证见同文件夹PDF及JSON。','各场值按四位小数输出；时间单位s、距离单位cm、温度°C、含水率kg/kg。','附件1空气水分数值作为有效边界干基值；不是从吸附等温线严格换算得到。','前4h环境按附件1分段线性插值；4h后取3～4h环境数据均值恒定。','第二、三问采用附录3；第四问采用附录4及均匀径向材料收缩、长度固定。','第三、四问末行是最大含水率达到0.15的临界时刻；严格低于发生在其后，舍入显示可仍为0.1500。','第四问固定半径列超出当前区域的格子留空；药材表面列对应该行当前R(t)，见当前表面位置表。','这些是明确模型下的数值答案；物理假设不确定性不能由四位小数消除。']
 for s in notes:ws.append([s])
 wb.save(path)

def main():
 summary={};plots={'air':AIR,'radius':RAD}
 for kind,name in [(1,'q1_s2560'),(23,'q23_s2560'),(4,'q4_s2560')]:
  z=np.load(ROOT/'程序与验证'/f'{name}.npz');times=z['times'];x=z['x'];T=z['T'];C=z['C'];rads=z['R']
  meta=json.loads((ROOT/'程序与验证'/f'{name}.json').read_text(encoding='utf-8'));summary[str(kind)]=meta
  if kind in [1,23]:
   lim=1800 if kind==1 else 10800;idx=np.flatnonzero((times>=1)&(times<=lim))
   valsT=fixed_sample(x,T[idx],np.linspace(0,1,21));valsC=fixed_sample(x,C[idx],np.linspace(0,1,21))
   q=1 if kind==1 else 2
   write_book(ROOT/f'result{q}.xlsx',times[idx],{'温度':valsT,'水分浓度':valsC},np.round(np.linspace(0,2,21),1))
   st=np.array([100,300,600,900,1200,1500,1800]) if kind==1 else np.arange(1800,10801,1800)
   summary[f'q{q}_table_times_s']=st.tolist();summary[f'q{q}_table_T']=valsT[st-1][:,::5].tolist();summary[f'q{q}_table_C']=valsC[st-1][:,::5].tolist()
   if kind==1:
    plots['q1_times']=times[idx];plots['q1_T21']=valsT;plots['q1_C21']=valsC
    ids=np.arange(0,1801,10);gx=np.linspace(0,1,201)
    plots['q1_field_times']=times[ids];plots['q1_field_x']=gx
    plots['q1_Tfield']=fixed_sample(x,T[ids],gx);plots['q1_Cfield']=fixed_sample(x,C[ids],gx)
    plots['q1_profile_times']=st;plots['q1_Tprofiles']=fixed_sample(x,T[st],gx);plots['q1_Cprofiles']=fixed_sample(x,C[st],gx)
  if kind in [23,4]:
   ids=np.flatnonzero((times>0)&(np.isclose(times%60,0,atol=1e-6)))
   if ids[-1]!=len(times)-1:ids=np.r_[ids,len(times)-1]
   tt=times[ids]
   if kind==23:
    val=fixed_sample(x,C[ids],np.linspace(0,1,21))
    write_book(ROOT/'result3.xlsx',tt,{'水分浓度':val},np.round(np.linspace(0,2,21),1))
   else:
    rr=np.arange(20)*.001;val=np.full((len(ids),21),np.nan)
    for j,i in enumerate(ids):
     inside=rr<=rads[i]+1e-12;val[j,np.flatnonzero(inside)]=PchipInterpolator(x,C[i])(rr[inside]/rads[i]);val[j,-1]=C[i,-1]
    write_book(ROOT/'result4.xlsx',tt,{'水分浓度':val},list(np.round(np.arange(20)*.1,1))+['药材表面'],rads[ids])
   plots[f'q{kind}_times']=tt;plots[f'q{kind}_maxC']=C[ids].max(axis=1);plots[f'q{kind}_surfaceC']=C[ids,-1];plots[f'q{kind}_R']=rads[ids]
   tc=z['tableC'];ts=z['tabletimes'];rows=[]
   for j,t in enumerate(ts):
    R=.02 if kind==23 else np.interp(t,RAD[:,0],RAD[:,1])*.01
    loc=np.array([0,.005,.01,.015,.02]) if kind==23 else np.array([0,.005,.01,.015])
    vv=[float(PchipInterpolator(x,tc[j])(r/R)) if r<=R+1e-12 else None for r in loc]
    if kind==4:vv+=[float(tc[j,-1])]
    rows.append({'time_h':float(t/3600),'radius_cm':float(R*100),'C':vv})
   summary[f'q{3 if kind==23 else 4}_table']=rows
   summary[f'q{kind}_post_threshold_reporting_h']=float(np.ceil(meta['finish_h']*1e4)/1e4)
  del T,C
 np.savez_compressed(ROOT/'程序与验证'/'绘图与摘要数据.npz',**plots)
 (ROOT/'程序与验证'/'最终结果摘要.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
 inp=ROOT/'输入数据';inp.mkdir(exist_ok=True)
 for name in ['附件1.xlsx','附件2.xlsx']:shutil.copy2(Path.home()/'Desktop'/'A题'/'附件'/name,inp/name)
 shutil.copy2(Path.home()/'Desktop'/'A题'/'A题.pdf',inp/'原题.pdf')
 print('exported',[(p.name,p.stat().st_size) for p in ROOT.glob('*.xlsx')]);print('final hours',summary['23']['finish_h'],summary['4']['finish_h'])

if __name__=='__main__':main()
