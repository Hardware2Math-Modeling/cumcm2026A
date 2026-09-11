"""附件温度拟合所得恒温值+文献20%RH，独立输出Q2—4。"""
import json
from _runner import run
from common import paths
from common.boundary import Boundary


def main():
    fit=json.loads((paths.RESULTS_DIR/"validation/ambient_fit.json").read_text(encoding="utf-8"))
    T=fit["selected"]["T_inf_K"]
    paths.RESULTS_DIR=paths.RESULTS_DIR/"scenarios/fitted_temperature"
    paths.RESULTS_TABLES=paths.RESULTS_DIR/"tables"
    paths.OUTPUTS_CACHE=paths.OUTPUTS_CACHE/"fitted_temperature"
    paths.ensure_output_dirs()
    comparison={"temperature_K":T,"relative_humidity":.20,"source":"results/validation/ambient_fit.json"}
    for q in ("q3","q4","q2"):
        code=run(q,boundary=Boundary.for_problem(q,T-273.15,.20))
        if code:
            return code
        comparison[q]=json.loads((paths.RESULTS_DIR/f"{q}_summary.json").read_text(encoding="utf-8"))
        (paths.RESULTS_DIR/"comparison.json").write_text(json.dumps(comparison,indent=2),encoding="utf-8")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
