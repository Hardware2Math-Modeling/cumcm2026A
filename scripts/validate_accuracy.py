"""Q1--3精度审计；保持物理模型与附件线性插值不变。"""

import json
import platform

import numpy as np
import scipy
from scipy.optimize import brentq
from scipy.special import j0, j1, jn_zeros

from _bootstrap import setup

setup()

from common.boundary import Boundary
from common.correlations import h_conv
from common.paths import ROOT
from common.problem_spec import Q1, Q3
from common.radial import solve_radial


def bessel_heat(times, r, modes=512):
    """Q1实际分段线性环境的Bessel模态卷积；每段时间积分解析计算。

    对T-T_inf展开，模态满足q'=-lambda*q-T_inf'。
    Robin本征值满足z*J1(z)=Bi*J0(z)。无有限体积或ODE误差。
    """
    b = Boundary.from_attachments()
    p = Q1.properties
    R = Q1.geometry.radius0
    k = float(p.k(Q1.initial.C, Q1.initial.T))
    alpha = k / float(p.rho(Q1.initial.C, Q1.initial.T)
                      * p.cp(Q1.initial.C, Q1.initial.T))
    Bi = h_conv("q1") * R / k
    ends = np.r_[0.0, jn_zeros(0, modes)]
    z = np.array([brentq(lambda x: x*j1(x)-Bi*j0(x),
                        ends[i]+1e-10, ends[i+1]) for i in range(modes)])
    lam = alpha*z*z/(R*R)
    coefficients = 2*j1(z)/(z*(j0(z)**2+j1(z)**2))
    basis = coefficients[:, None]*j0(z[:, None]*np.asarray(r)[None, :]/R)
    states = np.zeros((len(b.ambient_t), modes))
    states[0] = Q1.initial.T-b.T_amb[0]
    slopes = np.diff(b.T_amb)/np.diff(b.ambient_t)
    for i, dt in enumerate(np.diff(b.ambient_t)):
        states[i+1] = states[i]*np.exp(-lam*dt)+slopes[i]*np.expm1(-lam*dt)/lam
    out = []
    for t in times:
        i = min(np.searchsorted(b.ambient_t, t, side="right")-1, len(slopes)-1)
        dt = t-b.ambient_t[i]
        q = states[i]*np.exp(-lam*dt)+slopes[i]*np.expm1(-lam*dt)/lam
        out.append(float(b.ambient(t)[0])+q@basis)
    return np.asarray(out)


def differences(a, b):
    return {"delta_T_K": float(np.max(np.abs(a.T-b.T))),
            "delta_C": float(np.max(np.abs(a.C-b.C))),
            "delta_event_s": (a.meta["event_time_s"]-b.meta["event_time_s"]
                              if a.meta["event_time_s"] is not None else None)}


def main():
    folder = ROOT / "outputs" / "accuracy-v2"
    folder.mkdir(parents=True, exist_ok=True)
    dest = ROOT / "results" / "validation" / "accuracy.json"
    report = {"python": platform.python_version(), "numpy": np.__version__,
              "scipy": scipy.__version__, "grid": [], "cross_solver": [],
              "sampling": {"q1": "every second 0--1800 s; all 21 output radii",
                           "q3": "every 60 s 0--3 h; every hour 4--54 h; all 21 radii; continuous event"}}
    settings = dict(rtol=2e-11, atol=2e-12, max_step=60, align_boundary_knots=True)

    def save():
        dest.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    for spec in (Q1, Q3):
        times = (np.arange(1801, dtype=float) if spec.name == "q1" else
                 np.r_[np.arange(0, 10801, 60), np.arange(4, 55)*3600.0])
        runs = {}
        for n in (641, 1281, 2561, 5121):
            cache = folder / f"{spec.name}_{n}.npz"
            if cache.exists():
                from common.solution import Solution
                with np.load(cache) as f:
                    s = Solution(f["t"], f["r"], f["T"], f["C"], json.loads(str(f["meta"])))
            else:
                print(f"START {spec.name} n={n}", flush=True)
                s = solve_radial(spec, n_internal=n, sample_times=times, **settings)
                np.savez_compressed(cache, t=s.t, r=s.r, T=s.T, C=s.C,
                                    meta=json.dumps(s.meta))
            row = {"q": spec.name, "n": n, "seconds": s.meta["wall_time_s"],
                   "mass_residual": s.meta["mass_balance_relative"],
                   "event_s": s.meta["event_time_s"]}
            if runs:
                previous = runs[(n-1)//2+1]
                row.update(differences(s, previous))
                row["richardson_fine_T_K"] = row["delta_T_K"]/3
                row["richardson_fine_C"] = row["delta_C"]/3
                if row["delta_event_s"] is not None:
                    row["richardson_fine_event_s"] = abs(row["delta_event_s"])/3
            runs[n] = s
            report["grid"].append(row)
            print(json.dumps(row), flush=True)
            save()
        if spec.name == "q1":
            exact = bessel_heat(times, runs[2561].r)
            exact_fine = bessel_heat(times, runs[2561].r, modes=1024)
            report["bessel"] = {
                "modes_delta_T_K": float(np.max(np.abs(exact-exact_fine))),
                "max_error_by_grid_K": {str(n): float(np.max(np.abs(s.T-exact_fine)))
                                        for n, s in runs.items()}}
            save()
        # 独立五阶隐式RK在同一网格隔离时间推进误差，不冒充空间独立验证。
        print(f"START Radau cross-check {spec.name}", flush=True)
        bdf = solve_radial(spec, n_internal=161, sample_times=times, **settings)
        radau = solve_radial(spec, n_internal=161, sample_times=times, method="Radau", **settings)
        report["cross_solver"].append({"q": spec.name, "n": 161,
                                      **differences(radau, bdf)})
        print(json.dumps(report["cross_solver"][-1]), flush=True)
        save()
    report["settings"] = settings
    report["note"] = "Richardson estimates assume the observed second-order asymptotic regime; not physical uncertainty bounds."
    save()


if __name__ == "__main__":
    main()
