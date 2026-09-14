from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle,FancyArrowPatch,Rectangle
from matplotlib.font_manager import FontProperties
from solve_model import ROOT
from check_accuracy import extract,analytic_heat

OUT=ROOT/'图片';OUT.mkdir(exist_ok=True)
plt.rcParams.update({'font.family':'Microsoft YaHei','axes.unicode_minus':False,'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'axes.titleweight':'bold','axes.labelcolor':'#253746','text.color':'#253746','axes.edgecolor':'#647680','figure.facecolor':'white','savefig.facecolor':'white','lines.linewidth':1.8})
COL=['#124E78','#088F8F','#67AD72','#E7A33E','#C64C52']
d=np.load(ROOT/'程序与验证'/'绘图与摘要数据.npz')
s=json.loads((ROOT/'程序与验证'/'最终结果摘要.json').read_text(encoding='utf-8'))
def save(fig,name):
 fig.savefig(OUT/f'{name}.png',dpi=240,bbox_inches='tight');fig.savefig(OUT/f'{name}.pdf',bbox_inches='tight');plt.close(fig)

fig,ax=plt.subplots(figsize=(9.2,3));ax.set_xlim(0,10);ax.set_ylim(0,3.5);ax.axis('off')
for radius,color in [(1.18,'#DFEEEE'),(.96,'#B8DADA'),(.72,'#8AC2C4'),(.45,'#5DA7B0')]:ax.add_patch(Circle((1.55,1.75),radius,facecolor=color,edgecolor='#187C87',lw=.6))
ax.plot([1.55,2.73],[1.75,1.75],color='#143F58');ax.text(1.67,1.88,'r → R = 2 cm',fontsize=9)
ax.text(.55,.16,'圆柱横截面；长度 L = 25 cm',fontsize=9)
for y,color,label in [(2.65,'#C64C52','热量：空气 → 表面 → 内部'),(1.95,'#187E9C','水分：内部 → 表面 → 空气')]:
 ax.annotate('',xy=(3.1,y),xytext=(4.05,y),arrowprops={'arrowstyle':'->' if y>2 else '<-','color':color,'lw':2});ax.text(4.15,y-.1,label,color=color,fontsize=12)
ax.text(4.15,1.10,'初始：T = 28°C，C = 2.55 kg/kg',fontsize=11)
ax.text(4.15,.60,'外界输入：附件 1 的温度、有效水分数值',fontsize=10)
ax.text(4.15,.10,'边界交换 + 内部守恒 → T(r,t)、C(r,t)',fontsize=11,fontweight='bold')
save(fig,'图1_物理过程示意')

air=d['air'];a=air[air[:,0]<=1800]
fig,axes=plt.subplots(1,2,figsize=(9.2,2.8),layout='constrained')
for ax,col,label,color in [(axes[0],1,'烘房温度 / °C',COL[0]),(axes[1],2,'有效外界水分值 / (kg/kg)',COL[1])]:
 ax.plot(a[:,0]/60,a[:,col],'-o',ms=3,color=color);ax.set(xlabel='时间 / min',ylabel=label,xlim=(0,30));ax.grid(alpha=.18)
save(fig,'图2_前30分钟烘房环境')

times=d['q1_profile_times'];r=d['q1_field_x']*2
for key,ylabel,name in [('T','温度 / °C','图3_温度径向分布'),('C','干基含水率 / (kg/kg)','图4_水分径向分布')]:
 fig,ax=plt.subplots(figsize=(8.9,3.05),layout='constrained')
 for idx,color in zip([0,1,2,4,6],COL):ax.plot(r,d[f'q1_{key}profiles'][idx],color=color,label=f'{int(times[idx])} s')
 ax.set(xlabel='距中心轴的距离 / cm',ylabel=ylabel,xlim=(0,2));ax.grid(alpha=.18);ax.legend(ncol=5,loc='best',fontsize=9)
 save(fig,name)

fig,axes=plt.subplots(1,2,figsize=(9.2,3.35),layout='constrained')
for ax,key,title in zip(axes,['T','C'],['温度 / °C','干基含水率 / (kg/kg)']):
 im=ax.pcolormesh(d['q1_field_x']*2,d['q1_field_times']/60,d[f'q1_{key}field'],shading='auto',cmap='inferno' if key=='T' else 'viridis')
 ax.set(xlabel='距中心轴的距离 / cm',ylabel='时间 / min',title=title);fig.colorbar(im,ax=ax,shrink=.88)
save(fig,'图5_温度水分时空分布')

fig,axes=plt.subplots(1,2,figsize=(9.2,3.0),layout='constrained')
for ax,key,label in [(axes[0],'T','温度 / °C'),(axes[1],'C','干基含水率 / (kg/kg)')]:
 for j,color in zip([0,5,10,15,20],COL):ax.plot(d['q1_times']/60,d[f'q1_{key}21'][:,j],color=color,label=f'{j/10:.1f} cm')
 ax.set(xlabel='时间 / min',ylabel=label,xlim=(0,30));ax.grid(alpha=.18);ax.legend(ncol=2,fontsize=8)
save(fig,'图6_指定位置时间曲线')

ref=analytic_heat(360);t=d['q1_times'];err=np.max(np.abs(d['q1_T21']-ref[1:]),axis=1)
coarse=extract('q1_s1280','C')[1:];cerr=np.max(abs(coarse-d['q1_C21']),axis=1)
fig,axes=plt.subplots(1,2,figsize=(9.2,2.9),layout='constrained')
axes[0].plot(t/60,err,color=COL[0]);axes[0].set(xlabel='时间 / min',ylabel='最大温度差 / °C',title='与 360 项级数参考解比较')
axes[1].plot(t/60,cerr,color=COL[1]);axes[1].set(xlabel='时间 / min',ylabel='最大含水率差 / (kg/kg)',title='1280 与 2560 区间网格比较')
for ax in axes:ax.ticklabel_format(axis='y',style='sci',scilimits=(0,0));ax.grid(alpha=.18)
save(fig,'图7_独立验证与网格收敛')

fig,axes=plt.subplots(1,2,figsize=(9.2,3.25),layout='constrained')
for kind,label,color in [(23,'问题3：固定半径',COL[0]),(4,'问题4：考虑收缩',COL[1])]:
 axes[0].plot(d[f'q{kind}_times']/3600,d[f'q{kind}_maxC'],label=label,color=color)
 axes[0].scatter([s[str(kind)]['finish_h']],[.15],color=color,s=25)
axes[0].axhline(.15,color=COL[4],ls='--',lw=1,label='达标阈值 0.15');axes[0].set(xlabel='时间 / h',ylabel='全体最大干基含水率 / (kg/kg)');axes[0].legend(fontsize=8);axes[0].grid(alpha=.18)
rad=d['radius'];axes[1].plot(rad[:,0]/3600,rad[:,1],color=COL[2]);axes[1].axvline(s['4']['finish_h'],ls='--',color=COL[1],lw=1);axes[1].set(xlabel='时间 / h',ylabel='半径 / cm',title='附件2半径与问题4结束位置');axes[1].grid(alpha=.18)
save(fig,'图8_全程干燥与收缩')
print('generated',len(list(OUT.glob('*.png'))),'figures')
