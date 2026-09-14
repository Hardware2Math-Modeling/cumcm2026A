"""从正式结果、缓存、验证报告生成论文表图和全部数值宏。"""
import json
import numpy as np
import pandas as pd
import openpyxl
from _bootstrap import setup
setup()
from common import paths, units, plotting
from common.boundary import Boundary
from common.psychrometrics import humidity_ratio
from common.numerical_settings import production_options
from common.solution import Solution


def load(q):
    with np.load(paths.OUTPUTS_CACHE/f"{q}.npz") as f:
        return Solution(f["t"],f["r"],f["T"],f["C"],json.loads(str(f["meta"])))


def report():
    return json.loads((paths.RESULTS_DIR/"validation/latent.json").read_text(encoding="utf-8"))


def write_table(df, caption, label, name):
    from make_tables import to_booktabs
    (paths.TABLES_DIR/f"{name}.tex").write_text(to_booktabs(df,caption,label),encoding="utf-8")


def tables():
    from make_tables import TABLES
    paths.TABLES_DIR.mkdir(parents=True,exist_ok=True)
    # 规则时刻直接来自正式xlsx；非整步事件行来自同次求解事件CSV。
    for key,(caption,label) in TABLES.items():
        df=pd.read_csv(paths.RESULTS_TABLES/f"{key}.csv")
        q=key[:2]
        scale=1. if q=="q1" else 3600.
        requested=df.iloc[:,0].to_numpy()*scale
        wanted={int(round(t)):i for i,t in enumerate(requested) if abs(t-round(t))<1e-5 and (q in ('q1','q2') or i<len(requested)-1)}
        book=openpyxl.load_workbook(paths.result_path(q),read_only=True,data_only=True)
        sheet=("温度" if key.endswith('temp') else "水分浓度") if q in ('q1','q2') else "Sheet1"
        iterator=book[sheet].iter_rows(values_only=True)
        headers=list(next(iterator)); positions=[headers.index(str(c)) for c in df.columns[1:]]
        for row in iterator:
            if row[0] in wanted:
                df.iloc[wanted[row[0]],1:]=[np.nan if row[j] is None else row[j] for j in positions]
            if row[0]>=max(wanted):
                break
        book.close()
        df=df.rename(columns={df.columns[0]:"时间/s" if key.startswith("q1") else "时间/h"})
        unit="°C" if key.endswith("temp") else "kg/kg"
        write_table(df,caption+f"（{unit}；距离单位：cm）",label,key)
    summaries={q:json.loads((paths.RESULTS_DIR/f"{q}_summary.json").read_text(encoding="utf-8")) for q in ("q1","q2","q3","q4")}
    v=report()
    s1,s2=load("q1"),load("q2")
    i2=int(np.searchsorted(s2.t,10800.))
    scalars={}
    for name,s,i in (("QOne",s1,-1),("QTwo",s2,i2)):
        for suffix,field,j in (("CenterT","T",0),("SurfaceT","T",-1),("CenterC","C",0),("SurfaceC","C",-1)):
            value=getattr(s,field)[i,j]
            scalars[name+suffix]=f"{units.k_to_c(value) if field=='T' else value:.4f}"
    for q,name in (("q3","QThree"),("q4","QFour")):
        scalars[name+"EndH"]=f"{summaries[q]['event_time_s']/3600.:.4f}"
        scalars[name+"StrictEndH"]=f"{summaries[q]['first_output_below_s']/3600.:.4f}"
    scalars["QFourEndRadiusCm"]=f"{100*summaries['q4']['event_R']:.4f}"
    scalars.update(EnvTempC="60",EnvRHPercent="20",EnvC=f"{humidity_ratio(333.15,.20):.6f}")
    options=production_options("q1")
    scalars.update(ProductionNodes=str(options["n_internal"]),ProductionRtol=f"{options['rtol']:.1e}",ProductionAtol=f"{options['atol']:.1e}",ProductionMaxStep=f"{options['max_step']:g}",
                   QOneMassError=f"{summaries['q1']['mass_balance_relative']:.2e}",QOneEnergyError=f"{summaries['q1']['q1_energy_balance_relative']:.2e}",
                   MaxMassError=f"{max(s['mass_balance_relative'] for s in summaries.values()):.2e}")
    from common.radial import RadialModel
    from common.problem_spec import Q1,Q3,Q4
    audit=[]
    for spec in (Q1,Q3,Q4):
        m=RadialModel(spec,41)
        for t in (0.,7200.,86400.):
            y=m.initial(); y[:41]+=2*m.xi**2; y[41:82]-=.2*m.xi**2
            dy=m.rhs(t,y)
            capacity=spec.properties.rho(y[41:82],y[:41])*spec.properties.cp(y[41:82],y[:41])
            value=abs(m.radius(t)**2*np.dot(m.weights*capacity,dy[:41])-dy[83])
            audit.append({"q":spec.name,"t_s":t,"absolute_residual_W_per_m":float(value)})
    (paths.RESULTS_DIR/"validation/energy_audit.json").write_text(json.dumps(audit,indent=2),encoding="utf-8")
    scalars["MaxInstantEnergyError"]=f"{max(x['absolute_residual_W_per_m'] for x in audit):.2e}"
    fine=[g for g in v["grid"] if g["n"]==2561]
    scalars.update(MaxGridTempError=f"{max(g['delta_T_K'] for g in fine):.2e}",MaxGridMoistError=f"{max(g['delta_C'] for g in fine):.2e}",MaxGridEndErrorH=f"{max(g['delta_event_s'] or 0 for g in fine)/3600.:.2e}",
                   MaxTimeTempError=f"{max(g['delta_T_K'] for g in v['time']):.2e}",MaxTimeMoistError=f"{max(g['delta_C'] for g in v['time']):.2e}",MaxTimeEndErrorH=f"{max(g['delta_event_s'] or 0 for g in v['time'])/3600.:.2e}")
    fixed=next(a for a in v["ablation"] if a["case"]=="fixed_radius_same_appendix4")
    scalars["QFourShrinkReductionPercent"]=f"{100*(1-fixed['base_h']/fixed['event_h']):.2f}"
    scalars["QFourFixedEndH"]=f"{fixed['event_h']:.4f}"
    layer=json.loads((paths.RESULTS_DIR/"validation/q4_boundary_layer.json").read_text(encoding="utf-8"))
    scalars["OutputGridCError"]=f"{layer['rows'][-1]['physical_output_max_C_difference']:.2e}"
    fitted_check=json.loads((paths.RESULTS_DIR/"validation/fitted_numerics.json").read_text(encoding="utf-8"))
    scalars["FitOutputGridCError"]=f"{max(r['delta_output_C'] for r in fitted_check['rows']):.2e}"
    scalars["FitGridEndErrorS"]=f"{max(r['delta_event_s'] for r in fitted_check['rows']):.4f}"
    rows=[]
    for g in v["grid"]:
        if "delta_T_K" in g:
            rows.append([g["q"].upper(),g["n"],f"{g['delta_T_K']:.2e}",f"{g['delta_C']:.2e}","—" if g["delta_event_s"] is None else f"{g['delta_event_s']:.4f}"])
    write_table(pd.DataFrame(rows,columns=["题号","节点数","温度差/K","含水率差","终点差/s"]),"相邻加密网格比较（最大场差与连续终点差）","tab:all-validation","all_validation")
    label={"55C_20RH":"55°C、20\\% RH","60C_40RH":"60°C、40\\% RH","Lewis_one":"Lewis数为1","equilibrium_C_005":"供水平衡含水率0.05"}
    rows=[[x["q"].upper(),label[x["case"]],x["event_h"],x["delta_h"]] for x in v["sensitivity"]]
    for x in v["ablation"]:
        rows.append([x["q"].upper(),"同参数不计潜热" if x["case"]=="no_latent" else "附录4固定半径",x["event_h"],x["event_h"]-x["base_h"]])
    write_table(pd.DataFrame(rows,columns=["题号","比较条件","时间/h","相对基准差/h"]),"工况与结构假设敏感性（161节点，全部为方案计算）","tab:sensitivity","sensitivity")
    fit_path=paths.RESULTS_DIR/"validation/ambient_fit.json"
    if fit_path.exists():
        fit=json.loads(fit_path.read_text(encoding="utf-8"))
        selected=fit["selected"]
        scalars.update(FitTempC=f"{selected['T_inf_K']-273.15:.4f}",FitTempLowC=f"{selected['T_inf_ci95_K'][0]-273.15:.4f}",FitTempHighC=f"{selected['T_inf_ci95_K'][1]-273.15:.4f}",FitRMSE=f"{selected['rmse_K']:.4f}")
        scalars["FitHoldoutRMSE"]=f"{selected['holdout_rmse_K']:.4f}"
        params=fit['candidates']['logistic_fixed_initial']['parameters']
        scalars["FitShapeB"]=f"{params['B_dimensionless']:.6f}"
        scalars["FitTauS"]=f"{params['tau_s']:.4f}"
        modelnames={'exponential_free':'自由初值指数','exponential_fixed_initial':'固定初值指数','logistic_fixed_initial':'有限平台Logistic','weibull_fixed_initial':'Weibull饱和曲线'}
        rows=[[modelnames[k],item['T_asymptote_C'],item['full_fit']['rmse_K'],item['holdout']['rmse_K']] for k,item in fit['candidates'].items()]
        write_table(pd.DataFrame(rows,columns=['候选模型','平台/°C','全段RMSE/K','留出RMSE/K']),"附件温度曲线的拟合候选比较","tab:ambient-models","ambient_models")
        scenario_path=paths.RESULTS_DIR/"scenarios/fitted_temperature/comparison.json"
        if scenario_path.exists():
            scenario=json.loads(scenario_path.read_text(encoding="utf-8"))
            for q,name in (("q3","FitQThreeEndH"),("q4","FitQFourEndH")):
                scalars[name]=f"{scenario[q]['event_time_s']/3600:.4f}"
            rows=[["文献设定",60.,float(scalars['QThreeEndH']),float(scalars['QFourEndH'])],["附件拟合渐近值",selected['T_inf_K']-273.15,float(scalars['FitQThreeEndH']),float(scalars['FitQFourEndH'])]]
            write_table(pd.DataFrame(rows,columns=["恒温方案","温度/°C","Q3时间/h","Q4时间/h"]),"两种恒温温度来源的比较（相对湿度均为20\\%）","tab:temperature-scenarios","temperature_scenarios")
    (paths.TABLES_DIR/"all_values.tex").write_text("% 自动生成，不得手抄结果\n"+"\n".join("\\newcommand{\\"+k+"}{"+val+"}" for k,val in scalars.items())+"\n",encoding="utf-8")
    notation=(paths.ROOT/"docs/NOTATION.md").read_text(encoding="utf-8")
    section=notation.split("## 0.",1)[1].split("## 1.",1)[0]
    rows=[]
    for line in section.splitlines():
        cells=[x.strip() for x in line.strip().strip("|").split("|")]
        if len(cells)==4 and cells[1].startswith("`\\"):
            macro=cells[1].replace("`","").replace(",",r",\,")
            rows.append("$"+macro+"$ & "+cells[3].replace("_",r"\_")+r" \\")
    (paths.TABLES_DIR/"notation.tex").write_text("\\begin{longtable}{lp{10cm}}\n\\toprule 符号 & 含义 \\\\ \\midrule\n"+"\n".join(rows)+"\n\\bottomrule\\end{longtable}\n",encoding="utf-8")
    print("Generated all paper tables and result macros.",flush=True)
    return 0


def figures():
    from matplotlib import pyplot as plt
    plotting.apply_style()
    plt.rcParams.update({'font.size':11,'axes.labelsize':12,'axes.titlesize':12,
                         'legend.fontsize':11,'xtick.labelsize':11,'ytick.labelsize':11})
    def save(fig,name):
        fig.savefig(paths.FIGURES_DIR/f"{name}.pdf",bbox_inches="tight")
        plt.close(fig)
    s1,s2,s3,s4=(load(f"q{i}") for i in range(1,5))
    for field in ("T","C"):
        fig,ax=plt.subplots(figsize=(6.0,4.0))
        for t in (100,600,1200,1800):
            i=int(np.searchsorted(s1.t,t))
            y=s1.T[i]-273.15 if field=="T" else s1.C[i]
            ax.plot(s1.r*100,y,marker='o',markersize=2.5,label=f"t = {t} s")
        ax.set(xlabel="到药材中心的距离 / cm",ylabel="温度 / °C" if field=="T" else "干基含水率 / (kg/kg)")
        ax.legend();save(fig,f"fig1-{field}-profiles")
    b=Boundary.for_problem("q2")
    fig,ax=plt.subplots(2,1,figsize=(6.0,6.5))
    mask=s2.t<=10800
    for j,label in ((0,"轴心"),(-1,"表面")):
        ax[0].plot(s2.t[mask]/3600,s2.T[mask,j]-273.15,label=label)
        ax[1].plot(s2.t[mask]/3600,s2.C[mask,j],label=label)
    ax[0].plot(s2.t[mask]/3600,b.ambient(s2.t[mask])[0]-273.15,"--",label="烘房")
    for a,y in zip(ax,("温度 / °C","干基含水率 / (kg/kg)")):
        a.set(xlabel="时间 / h",ylabel=y);a.legend()
    fig.tight_layout();save(fig,"fig2-history")
    fig,ax=plt.subplots(figsize=(6.0,4.0))
    for j in (0,5,10,15,20):
        ax.plot(s3.t/3600,s3.C[:,j],label=f"r={j/10:g} cm")
    ax.axhline(.15,color="black",ls="--",label="各处达标阈值")
    ax.set(xlabel="时间 / h",ylabel="干基含水率 / (kg/kg)");ax.legend(ncol=2);save(fig,"fig3-drying")
    fig,ax=plt.subplots(2,1,figsize=(6.0,6.5))
    ax[0].plot(s4.t/3600,np.array(s4.meta['R'])*100)
    ax[0].set(xlabel="时间 / h",ylabel="药材半径 / cm")
    for t in (6*3600,18*3600,30*3600,s4.t[-1]):
        i=int(np.argmin(abs(s4.t-t)))
        ax[1].plot(s4.r/s4.r[-1]*s4.meta['R'][i]*100,s4.C[i],label=f"{s4.t[i]/3600:.1f} h")
    ax[1].set(xlabel="实际径向位置 / cm",ylabel="干基含水率 / (kg/kg)");ax[1].legend()
    fig.tight_layout();save(fig,"fig4-shrinkage")
    v=report();fig,ax=plt.subplots(2,1,figsize=(6.0,6.5))
    for q in ('q1','q3','q4'):
        rows=[g for g in v['grid'] if g['q']==q and 'delta_T_K' in g]
        for a,key in zip(ax,('delta_T_K','delta_C')):
            a.loglog([g['n'] for g in rows],[g[key] for g in rows],'o-',label=q.upper())
    for a,y in zip(ax,('相邻网格最大温度差 / K','相邻网格最大含水率差')):
        a.set(xlabel="细网格节点数",ylabel=y);a.legend()
    fig.tight_layout();save(fig,"fig-validation")
    path=paths.DATA_PROCESSED/"ambient_fit.csv"
    if path.exists():
        df=pd.read_csv(path)
        fig,ax=plt.subplots(figsize=(6.0,4.0))
        ax.scatter(df['t_s']/3600,df['T_observed_K']-273.15,s=7,label="附件1")
        ax.plot(df['t_s']/3600,df['T_fitted_K']-273.15,label="有限平台Logistic拟合")
        held=df['t_s']>10800
        ax.plot(df.loc[held,'t_s']/3600,df.loc[held,'T_train3h_logistic_fixed_initial_K']-273.15,':',label="前3 h拟合的留出预测")
        fit=json.loads((paths.RESULTS_DIR/"validation/ambient_fit.json").read_text(encoding="utf-8"))
        ax.axhline(fit['selected']['T_inf_K']-273.15,ls="--",color="black",label="拟合渐近温度")
        ax.set(xlabel="时间 / h",ylabel="烘房温度 / °C");ax.legend();save(fig,"fig-ambient-fit")
    print("Generated all paper figures.",flush=True)
    return 0


if __name__=="__main__":
    import sys
    if '--figures-only' not in sys.argv:
        tables()
    figures()
