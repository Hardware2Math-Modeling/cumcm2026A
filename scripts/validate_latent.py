"""潜热互补边界模型独立数值验证；缓存含代码指纹，防复用旧模型结果。"""
import hashlib
import json
import numpy as np
from _bootstrap import setup
setup()
from common import export, paths
from common.boundary import Boundary
from common.problem_spec import Q1, Q3, Q4
from common.radial import solve_radial


def main():
    signature = hashlib.sha256(b"".join(p.read_bytes() for p in sorted((paths.ROOT/"src").rglob("*.py")))).hexdigest()
    report = {"model_version":"latent-v2", "source_fingerprint":signature,
              "grid":[], "time":[], "sensitivity":[], "ablation":[]}
    dest = paths.RESULTS_DIR/"validation/latent.json"
    folder = paths.OUTPUTS_CACHE/"latent_validation"
    folder.mkdir(parents=True, exist_ok=True)
    settings = dict(rtol=2e-10, atol=2e-11, max_step=60., align_boundary_knots=True)
    runs = {}

    def save():
        dest.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")

    def solve_cached(spec, label, **options):
        key = hashlib.sha256((signature+spec.name+label+repr(options)).encode()).hexdigest()[:16]
        file = folder/f"{spec.name}_{label}_{key}.npz"
        if file.exists():
            from common.solution import Solution
            with np.load(file) as f:
                return Solution(f["t"],f["r"],f["T"],f["C"],json.loads(str(f["meta"])))
        print("START", spec.name,label,flush=True)
        s = solve_radial(spec,**options)
        np.savez_compressed(file,t=s.t,r=s.r,T=s.T,C=s.C,meta=json.dumps(s.meta))
        return s

    def fields(s,spec):
        if spec.name != "q4":
            return s.T,s.C
        return tuple(export.result_sheets(s,spec)["Sheet1"].iloc[:,1:].to_numpy() for _ in (0,))

    def diff(s,ref,spec):
        if spec.name == "q4":
            # 同时验证全材料域及固定物理交付位置，避免遗漏薄表层。
            Ts=np.array([np.interp(ref.r,s.r,row) for row in s.T])
            Cs=np.array([np.interp(ref.r,s.r,row) for row in s.C])
        else:
            Ts,Cs=s.T,s.C
        return {"delta_T_K":float(np.max(np.abs(Ts-ref.T))),
                "delta_C":float(np.max(np.abs(Cs-ref.C))),
                "delta_event_s":abs(s.meta["event_time_s"]-ref.meta["event_time_s"]) if s.meta["event_time_s"] else None}

    for spec in (Q1,Q3,Q4):
        times = np.arange(0.,1801.,10.) if spec.name=="q1" else np.unique(np.r_[np.arange(0.,10801.,60.),np.arange(4.,40.)*3600.])
        previous=None
        for n in (321,641,1281,2561):
            s=solve_cached(spec,f"grid{n}",n_internal=n,sample_times=times,**settings)
            runs[spec.name,n]=s
            row={"q":spec.name,"n":n,"event_s":s.meta["event_time_s"],
                 "wall_time_s":s.meta["wall_time_s"],"mass_residual":s.meta["mass_balance_relative"],
                 "q1_energy_residual":s.meta["q1_energy_balance_relative"]}
            if previous is not None:
                row.update(diff(s,previous,spec))
            report["grid"].append(row)
            print(row,flush=True)
            save()
            previous=s
        # 同空间网格的BDF/Radau交叉，检验时间积分，不冒充独立空间模型。
        cross_times = times if spec.name=="q1" else np.array([0.,10800.,86400.,129600.])
        ref=solve_cached(spec,"bdf81",n_internal=81,sample_times=cross_times,**settings)
        s=solve_cached(spec,"radau81",method="Radau",n_internal=81,sample_times=cross_times,**settings)
        report["time"].append({"q":spec.name,"n":81,**diff(s,ref,spec)})
        save()
    # 参数均为方案比较/结构假设扰动，不标记为额外实测数据。
    for spec in (Q3,Q4):
        base=solve_cached(spec,"sensitivity_base",n_internal=161,sample_times=[0.],**settings)
        cases=[("55C_20RH",dict(boundary=Boundary.for_problem(spec.name,55.,.20))),
               ("60C_40RH",dict(boundary=Boundary.for_problem(spec.name,60.,.40))),
               ("Lewis_one",dict(lewis=1.))]
        for label,extra in cases:
            s=solve_cached(spec,label,n_internal=161,sample_times=[0.],**settings,**extra)
            row={"q":spec.name,"case":label,"event_h":s.meta["event_time_s"]/3600.,
                 "base_h":base.meta["event_time_s"]/3600.,
                 "delta_h":(s.meta["event_time_s"]-base.meta["event_time_s"])/3600.}
            report["sensitivity"].append(row)
            print(row,flush=True)
            save()
        s=solve_cached(spec,"no_latent",n_internal=161,sample_times=[0.],latent_heat=False,**settings)
        report["ablation"].append({"q":spec.name,"case":"no_latent","event_h":s.meta["event_time_s"]/3600.,"base_h":base.meta["event_time_s"]/3600.})
        save()
    s=solve_cached(Q4,"fixed_radius",n_internal=161,sample_times=[0.],fixed_radius=True,t_end=7*86400.,**settings)
    report["ablation"].append({"q":"q4","case":"fixed_radius_same_appendix4","event_h":s.meta["event_time_s"]/3600.,"base_h":base.meta["event_time_s"]/3600.})
    report["settings"]=settings
    report["production_n"]=1281
    report["sampling"]="Q1 every 10 s at all 21 output radii; Q3/Q4 every 60 s through 3 h and hourly from 4 to 39 h, plus continuous termination event; Q4 material grids compared by interpolation."
    save()
    print(dest,flush=True)


if __name__=="__main__":
    main()
