from pathlib import Path
import numpy as np,json
from scipy.special import j0,j1,jn_zeros
from scipy.optimize import brentq
from scipy.interpolate import PchipInterpolator
from solve_model import AIR,ROOT

def extract(name,field):
 z=np.load(ROOT/'程序与验证'/f'{name}.npz')
 return PchipInterpolator(z['x'],z[field],axis=1)(np.linspace(0,1,21))

def analytic_heat(modes=240):
 Bi=25*.02/.36;alpha=.36/(820*2600);z0=jn_zeros(0,modes);z1=jn_zeros(1,modes)
 roots=np.array([brentq(lambda s:s*j1(s)-Bi*j0(s),0 if i==0 else z1[i-1],z0[i],xtol=1e-13) for i in range(modes)])
 mu=alpha*roots**2/.02**2
 A=2*Bi/((roots**2+Bi**2)*j0(roots))
 phi=j0(np.linspace(0,1,21)[:,None]*roots)*A
 lag=np.zeros(modes);out=[np.full(21,28.)]
 for t in range(1,1801):
  Ta=np.interp(t,AIR[:,0],AIR[:,1]);Told=np.interp(t-1,AIR[:,0],AIR[:,1]);slope=Ta-Told
  lag=lag*np.exp(-mu)+slope*(-np.expm1(-mu))/mu
  out.append(Ta-phi@lag)
 return np.array(out)

if __name__=='__main__':
 result={}
 reference=analytic_heat(360)
 result['analytic_heat_series_240_vs_360_max_C']=float(np.max(abs(analytic_heat(240)-reference)))
 for name in ['q1_n640','q1_n1280','q1_s1280','q1_s2560']:
  if (ROOT/'程序与验证'/f'{name}.npz').exists():
   result[name+'_analytic_heat_max_C']=float(np.max(abs(extract(name,'T')-reference)))
 pairs=[('q1_s1280','q1_s2560'),('q23_s640','q23_s1280'),('q23_s1280','q23_s2560'),('q4_s640','q4_s1280'),('q4_s1280','q4_s2560'),('q23_s1280','q23_timecheck'),('q4_s1280','q4_timecheck')]
 for a,b in pairs:
  if not all((ROOT/'程序与验证'/f'{s}.npz').exists() for s in [a,b]):continue
  za=np.load(ROOT/'程序与验证'/f'{a}.npz');zb=np.load(ROOT/'程序与验证'/f'{b}.npz')
  ca=za['C'];cb=zb['C'];xa=za['x'];xb=zb['x'];ra=za['R']
  # Compare common early times and all prescribed fixed-radius output locations.
  common=min(np.count_nonzero(za['times']<=10800),np.count_nonzero(zb['times']<=10800))
  for field in ['T','C']:
   va=PchipInterpolator(za['x'],za[field][:common],axis=1)(np.linspace(0,1,21))
   vb=PchipInterpolator(zb['x'],zb[field][:common],axis=1)(np.linspace(0,1,21))
   result[f'{a}_vs_{b}_{field}_early_max']=float(np.max(abs(va-vb)))
  result[f'{a}_vs_{b}_finish_s']=float(abs(za['times'][-1]-zb['times'][-1]))
  common_times,ia,ib=np.intersect1d(za['times'],zb['times'],return_indices=True)
  use=(common_times%60==0)
  if a.startswith('q1'):use=np.ones_like(use,dtype=bool)
  ia=ia[use];ib=ib[use]
  worst=0.
  for j,k in zip(ia,ib):
   R=float(ra[j]);points=np.r_[np.arange(0,.02001,.001)[np.arange(0,.02001,.001)<=R+1e-12]/R,1.]
   va=PchipInterpolator(xa,ca[j])(points)
   vb=PchipInterpolator(xb,cb[k])(points)
   worst=max(worst,float(np.max(abs(va-vb))))
  result[f'{a}_vs_{b}_C_all_common_outputs_max']=worst
 np.savez_compressed(ROOT/'程序与验证'/'q1_heat_series_reference.npz',T=reference,times=np.arange(1801),r_cm=np.linspace(0,2,21))
 (ROOT/'程序与验证'/'精度核验.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps(result,ensure_ascii=False,indent=2))
