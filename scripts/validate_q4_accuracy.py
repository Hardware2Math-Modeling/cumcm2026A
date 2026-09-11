"""第四问移动材料域的嵌套网格与BDF/Radau精度验证。"""

import json

import numpy as np

from _bootstrap import setup

setup()

from common.numerical_settings import production_options
from common.paths import ROOT
from common.problem_spec import Q4
from common.radial import solve_radial
from common.solution import Solution


def main():
    folder = ROOT / "outputs" / "accuracy-q4"
    folder.mkdir(parents=True, exist_ok=True)
    dest = ROOT / "results" / "validation" / "accuracy-q4.json"
    options = production_options("q4")
    options.pop("n_internal")
    times = np.r_[np.arange(0, 10801, 60), np.arange(4, 49)*3600.0]
    report = {"settings": options, "grid": [],
              "sampling": "0--3 h every 60 s, 4--48 h hourly; nested material nodes; continuous event"}
    previous = None
    for n in (641, 1281, 2561, 5121):
        cache = folder / f"q4_{n}.npz"
        if cache.exists():
            with np.load(cache) as f:
                s = Solution(f["t"], f["r"], f["T"], f["C"], json.loads(str(f["meta"])))
        else:
            print(f"START q4 n={n}", flush=True)
            s = solve_radial(Q4, n_internal=n, sample_times=times, **options)
            np.savez_compressed(cache, t=s.t, r=s.r, T=s.T, C=s.C, meta=json.dumps(s.meta))
        row = {"n": n, "event_s": s.meta["event_time_s"],
               "mass_residual": s.meta["mass_balance_relative"], "seconds": s.meta["wall_time_s"]}
        if previous is not None:
            np.testing.assert_allclose(s.r[::2], previous.r, rtol=0, atol=1e-16)
            row.update(delta_T_K=float(np.max(np.abs(s.T[:, ::2]-previous.T))),
                       delta_C=float(np.max(np.abs(s.C[:, ::2]-previous.C))),
                       delta_event_s=s.meta["event_time_s"]-previous.meta["event_time_s"])
        previous = s
        report["grid"].append(row)
        print(json.dumps(row), flush=True)
        dest.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("START q4 Radau/BDF cross-check", flush=True)
    a = solve_radial(Q4, n_internal=161, sample_times=times, **options)
    b = solve_radial(Q4, n_internal=161, sample_times=times, method="Radau", **options)
    report["cross_solver"] = dict(n=161, delta_T_K=float(np.max(np.abs(a.T-b.T))),
                                 delta_C=float(np.max(np.abs(a.C-b.C))),
                                 delta_event_s=a.meta["event_time_s"]-b.meta["event_time_s"])
    print(json.dumps(report["cross_solver"]), flush=True)
    dest.write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
