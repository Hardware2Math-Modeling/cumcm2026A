"""Plot archived table values only; does not solve the model."""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
P=Path(__file__).resolve().parent
s=json.loads((P/'checks'/'最终结果摘要.json').read_text(encoding='utf-8'))
plt.rcParams.update({'font.sans-serif':['Microsoft YaHei'],'axes.unicode_minus':False,
                     'font.size':10,'pdf.fonttype':42})
t=np.array(s['q2_table_times_s'])/3600
fig,axs=plt.subplots(1,2,figsize=(9,3.4))
for ax,key,ylabel in zip(axs,['T','C'],['温度 / °C','干基含水率 / (kg/kg)']):
    a=np.array(s['q2_table_'+key])
    for i,color,label in [(0,'#244f72','中心'),(2,'#8ca391','距中心1 cm'),(4,'#b76556','表面')]:
        ax.plot(t,a[:,i],'-o',color=color,label=label,ms=4,lw=1.6)
    ax.set_xlabel('时间 / h');ax.set_ylabel(ylabel);ax.grid(alpha=.18);ax.legend(frameon=False)
    ax.spines[['top','right']].set_visible(False)
fig.tight_layout()
fig.savefig(P/'figures'/'q2_summary.pdf',bbox_inches='tight')
print('Supplementary figure saved from existing summary data.')
