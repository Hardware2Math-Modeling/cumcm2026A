"""不依赖pytest的正式网格、时间步及环境敏感性验证。"""
import json

import numpy as np

from _bootstrap import setup
setup()
from common.boundary import Boundary
from common.paths import RESULTS_DIR
from common.problem_spec import Q1, Q3, Q4
from common.radial import solve_radial


def main():
    folder = RESULTS_DIR / "validation"
    folder.mkdir(parents=True, exist_ok=True)
    report = {"grid": [], "time": [], "sensitivity": [], "fixed_radius_control": []}
    runs = {}
    for spec in (Q1, Q3, Q4):
        for n in (81, 161, 321, 641):
            times = np.array([100,300,600,900,1200,1500,1800.]) if spec.name=="q1" else np.array([0,10800,86400.])
            s = solve_radial(spec,n_internal=n,sample_times=times)
            runs[spec.name,n] = s
            row = {"q": spec.name,"n": n,"seconds":s.meta["wall_time_s"],
                   "event_h": s.meta["event_time_s"]/3600 if s.meta["event_time_s"] else None,
                   "mass_residual":s.meta["mass_balance_relative"],
                   "energy_residual":s.meta["q1_energy_balance_relative"]}
            if n>81:
                previous = runs[spec.name,(n-1)//2+1]
                # q4解使用材料坐标；直接对齐嵌套网格。
                T, C = (s.T[:,::2],s.C[:,::2]) if spec.name=="q4" else (s.T,s.C)
                row["delta_T_K"] = float(np.max(np.abs(T-previous.T)))
                row["delta_C"] = float(np.max(np.abs(C-previous.C)))
                if row["event_h"]:
                    row["delta_event_s"] = s.meta["event_time_s"]-previous.meta["event_time_s"]
            report["grid"].append(row)
            print(json.dumps(row),flush=True)
            (folder/"numerics.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
        ref = runs[spec.name,641]
        s = solve_radial(spec,n_internal=641,rtol=2e-10,atol=2e-11,max_step=60,sample_times=times)
        row={"q":spec.name,"delta_T_K":float(np.max(np.abs(s.T-ref.T))),
             "delta_C":float(np.max(np.abs(s.C-ref.C))),
             "delta_event_s":s.meta["event_time_s"]-ref.meta["event_time_s"] if s.meta["event_time_s"] else None}
        report["time"].append(row)
        print("time",json.dumps(row),flush=True)
    # 扰动幅度完全取自附件末1小时的实测上下限，不虚构试验数据。
    b = Boundary.from_attachments()
    mask = b.ambient_t >= b.ambient_t[-1]-3600
    cases=[("last_hour_T_min",float(b.T_amb[mask].min()-b.T_amb[-1]),0.0),
           ("last_hour_T_max",float(b.T_amb[mask].max()-b.T_amb[-1]),0.0),
           ("last_hour_C_min",0.0,float(b.C_amb[mask].min()-b.C_amb[-1])),
           ("last_hour_C_max",0.0,float(b.C_amb[mask].max()-b.C_amb[-1]))]
    for spec in (Q3,Q4):
        for name,dT,dC in cases:
            boundary=Boundary.from_attachments(late_T_shift=dT,late_C_shift=dC)
            s=solve_radial(spec,n_internal=161,boundary=boundary,sample_times=[0])
            row={"q":spec.name,"case":name,"shift_T_K":dT,"shift_C":dC,
                 "event_h":s.meta["event_time_s"]/3600,
                 "delta_h":(s.meta["event_time_s"]-runs[spec.name,161].meta["event_time_s"])/3600}
            report["sensitivity"].append(row)
            print("sensitivity",json.dumps(row),flush=True)
    s=solve_radial(Q4,n_internal=161,fixed_radius=True,t_end=7*86400,sample_times=[0])
    report["fixed_radius_control"].append({"q":"q4","n":161,"event_h":s.meta["event_time_s"]/3600,
        "moving_h":runs["q4",161].meta["event_time_s"]/3600})
    (folder/"numerics.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print("验证结果:",folder/"numerics.json",flush=True)


if __name__=="__main__":
    main()
