"""Conservative radial finite volumes + adaptive sparse BDF. SI units.
rho(C) used as effective thermal density, not simultaneous exact dry-mass closure.
Uniform radial material shrinkage in Q4, fixed length and homogeneous reference dry density.
"""
from pathlib import Path
import argparse,json,time
import numpy as np
from scipy.integrate import solve_ivp
from scipy.sparse import lil_matrix,coo_matrix
from scipy.interpolate import PchipInterpolator
import openpyxl

ROOT=Path(__file__).resolve().parents[1]
DATA=Path.home()/'Desktop'/'A题'/'附件'
AIR=np.array(list(openpyxl.load_workbook(DATA/'附件1.xlsx',data_only=True).active.values)[1:],float)
RAD=np.array(list(openpyxl.load_workbook(DATA/'附件2.xlsx',data_only=True).active.values)[1:],float)
PLATEAU=AIR[AIR[:,0]>=10800,1:].mean(axis=0)

def props(C,T,kind):
 if kind==1:
  return np.full_like(C,820.),np.full_like(C,2600.),np.full_like(C,.36),7e-9*np.exp(-.89/C)
 if kind==23:
  return 650+128*C,1450+2736*C/(1+C),.21+.38*C/(1+C),2.4e-3*np.exp(-.45/C-3850/(T+273.15))
 return 760+90*C,1850+2150*C/(1+C),.12+.20*C/(1+C),4.2e-4*np.exp(-.30/C-3850/(T+273.15))

def run(kind=1,n=160,rtol=2e-9,maxstep=30.,plateau='mean',tag=None,limit_h=120.,mesh=0.):
 started=time.perf_counter();nodes=n+1;u=np.linspace(0,1,nodes)
 x=u if mesh==0 else 1-np.sinh(mesh*(1-u))/np.sinh(mesh)
 dx=np.diff(x)
 faces=np.r_[0,(x[1:]+x[:-1])/2,1]
 volumes=np.diff(faces**2)/2
 late=PLATEAU if plateau=='mean' else AIR[-1,1:]
 def env(t):
  if t>14400:return late
  return np.array([np.interp(t,AIR[:,0],AIR[:,1]),np.interp(t,AIR[:,0],AIR[:,2])])
 def radius(t):return np.interp(t,RAD[:,0],RAD[:,1])*.01 if kind==4 else .02
 def rhs(t,y):
  T=y[:2*nodes:2];C=y[1:2*nodes:2]
  rho,cp,k,D=props(C,T,kind)
  # Face transport evaluated at midpoint state, preserving a shared interface flux.
  _,_,kf,Df=props((C[1:]+C[:-1])/2,(T[1:]+T[:-1])/2,kind)
  R=radius(t);Ta,Ca=env(t)
  heat=np.empty(nodes+1,dtype=y.dtype);water=np.empty(nodes+1,dtype=y.dtype)
  heat[0]=0;water[0]=0
  heat[1:-1]=-faces[1:-1]*kf*np.diff(T)/dx/(R*R)
  water[1:-1]=-faces[1:-1]*Df*np.diff(C)/dx/(R*R)
  heat[-1]=25*(T[-1]-Ta)/R
  water[-1]=8e-7*(C[-1]-Ca)/R
  out=np.empty_like(y)
  out[:2*nodes:2]=-np.diff(heat)/(volumes*rho*cp)
  out[1:2*nodes:2]=-np.diff(water)/volumes
  out[-2]=2*water[-1] # reference dry-mass averaged moisture removed
  out[-1]=-2*heat[-1]/(820*2600) # exact mean temperature gain for Q1
  return out
 size=2*nodes+2;sparsity=lil_matrix((size,size),dtype=int)
 for i in range(nodes):
  sparsity[2*i:2*i+2,2*max(0,i-1):2*min(nodes,i+2)]=1
 sparsity[-2,2*nodes-1]=1;sparsity[-1,2*nodes-2]=1
 rows,cols=sparsity.nonzero()
 def jac(t,y):
  # Complex-step colored derivatives avoid unreliable finite differences on zero columns.
  vals=np.empty(len(rows));eps=1e-25
  for color in range(6):
   yc=y.astype(complex);yc[color:2*nodes:6]+=1j*eps
   der=rhs(t,yc).imag/eps;mask=cols%6==color
   vals[mask]=der[rows[mask]]
  return coo_matrix((vals,(rows,cols)),shape=(size,size)).tocsc()
 y=np.empty(size);y[:2*nodes:2]=28.;y[1:2*nodes:2]=2.55;y[-2:]=0
 def event(t,y):return np.max(y[1:2*nodes:2])-.15
 event.terminal=True;event.direction=-1
 end=1800. if kind==1 else limit_h*3600
 segments=[];stats=[]
 for a,b,step in [(0,min(14400.,end),maxstep),(14400.,end,900.)]:
  if b<=a:continue
  # Stop first segment at data end; second segment uses its own constant environment.
  fun=rhs
  if a==14400:
   original_env=env
   def env(t):return late
  sol=solve_ivp(fun,(a,b),y,method='BDF',rtol=rtol,atol=rtol*np.r_[np.tile([.1,.01],nodes),.01,.1],jac=jac,dense_output=True,max_step=step,events=None if kind==1 else event)
  if not sol.success:raise RuntimeError(sol.message)
  segments.append(sol);stats.append({'nfev':sol.nfev,'njev':sol.njev,'nlu':sol.nlu,'steps':len(sol.t)-1})
  y=sol.y[:,-1]
  if sol.t_events is not None and len(sol.t_events[0]):break
 final=float(segments[-1].t[-1])
 reached=bool(kind==1 or abs(np.max(y[1:2*nodes:2])-.15)<1e-7)
 def evaluate(times):
  times=np.asarray(times,float);out=np.empty((size,len(times)))
  for ix,t in enumerate(times):
   s=segments[0] if t<=segments[0].t[-1] else segments[1]
   out[:,ix]=s.sol(float(t))
  return out
 # Dense export times: 1 second in first 3 h, 60 seconds afterwards, ending exactly at threshold.
 times=np.arange(0,min(final,10800.)+1e-7,1.)
 if final>10800:times=np.r_[times,np.arange(10860,final,60.),final]
 elif abs(times[-1]-final)>1e-7:times=np.r_[times,final]
 states=evaluate(times)
 T=states[:2*nodes:2].T;C=states[1:2*nodes:2].T
 rad=np.array([radius(t) for t in times])
 moisture_error=np.max(np.abs(2*(C@volumes)+states[-2]-2.55))
 heat_error=np.max(np.abs(2*(T@volumes)-28-states[-1])) if kind==1 else None
 tabletimes=np.array([100,300,600,900,1200,1500,1800.]) if kind==1 else np.r_[np.arange(21600,final,21600),final]
 tablestates=evaluate(tabletimes)
 summary={'kind':kind,'n':n,'rtol':rtol,'maxstep_early':maxstep,'plateau':plateau,'plateau_T_C':late.tolist(),'finish_s':final,'finish_h':final/3600,'reached':reached,'elapsed_s':time.perf_counter()-started,'stats':stats,'water_balance_error':float(moisture_error),'heat_mean_balance_error_C':None if heat_error is None else float(heat_error),'min_C':float(C.min()),'max_C':float(C.max()),'min_T':float(T.min()),'max_T':float(T.max()),'final_maxC':float(C[-1].max()),'final_argmax_x':float(x[C[-1].argmax()])}
 summary['mesh_sinh_beta']=mesh
 name=tag or f'q{kind}_n{n}'
 np.savez_compressed(ROOT/'程序与验证'/f'{name}.npz',times=times,x=x,T=T,C=C,R=rad,tabletimes=tabletimes,tableT=tablestates[:2*nodes:2].T,tableC=tablestates[1:2*nodes:2].T)
 (ROOT/'程序与验证'/f'{name}.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps(summary,ensure_ascii=False),flush=True)
 return summary

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--kind',type=int,default=1);p.add_argument('--n',type=int,default=160);p.add_argument('--rtol',type=float,default=2e-9);p.add_argument('--maxstep',type=float,default=30.);p.add_argument('--plateau',default='mean');p.add_argument('--tag');p.add_argument('--limit-h',type=float,default=120.);p.add_argument('--mesh',type=float,default=0.)
 a=p.parse_args();run(a.kind,a.n,a.rtol,a.maxstep,a.plateau,a.tag,a.limit_h,a.mesh)
