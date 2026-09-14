"""拟合温度情景：641与1281网格在全部60s输出点和连续终点比较。"""
import json
import numpy as np
from _bootstrap import setup
setup()
from common import export, paths
from common.boundary import Boundary
from common.problem_spec import Q3,Q4
from common.radial import solve_radial
from common.solution import Solution


def main():
    fit=json.loads((paths.RESULTS_DIR/"validation/ambient_fit.json").read_text(encoding="utf-8"))
    temp=fit["selected"]["T_inf_K"]
    report={"temperature_K":temp,"rows":[]}
    for spec in (Q3,Q4):
        with np.load(paths.OUTPUTS_CACHE/f"fitted_temperature/{spec.name}.npz") as f:
            ref=Solution(f['t'],f['r'],f['T'],f['C'],json.loads(str(f['meta'])))
        # 两个网格严格达标时刻可能相差一个输出格，比较共同时间范围。
        times=ref.t[:-1]
        s=solve_radial(spec,n_internal=641,rtol=2e-10,atol=2e-11,max_step=60.,align_boundary_knots=True,
                       boundary=Boundary.for_problem(spec.name,temp-273.15,.2),sample_times=times)
        if spec.name=="q4":
            columns=export.result_sheets(s,spec)['Sheet1'].iloc[:,1:].to_numpy()
            reference=export.result_sheets(ref,spec)['Sheet1'].iloc[:-1,1:].to_numpy()
        else:
            columns,reference=s.C,ref.C[:-1]
        row={"q":spec.name,"coarse_n":641,"fine_n":1281,
             "delta_output_C":float(np.nanmax(abs(columns-reference))),
             "delta_event_s":abs(s.meta['event_time_s']-ref.meta['event_time_s']),
             "mass_balance_relative":s.meta['mass_balance_relative'],
             "sample_count":len(times)}
        report['rows'].append(row)
        print(row,flush=True)
        (paths.RESULTS_DIR/"validation/fitted_numerics.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
