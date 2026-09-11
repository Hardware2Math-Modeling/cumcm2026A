"""圆柱节点中心有限体积＋BDF；干基材料坐标模型见 docs/model/numerics.md。"""

import time

import numpy as np
from scipy.integrate import solve_ivp
from scipy.sparse import coo_matrix, lil_matrix

from .boundary import Boundary
from .correlations import h_conv, h_mass, latent_heat_vaporization
from .solution import Solution
from .psychrometrics import gas_evaporation_capacity, LEWIS_NUMBER


def outward_flux(value_surface, value_ambient, coefficient):
    """向外为正的Robin通量；加热时热通量为负。"""
    return coefficient * (value_surface - value_ambient)


def grid_weights(n):
    # 表面二次加密，解析干燥后期低D区域的薄层。
    xi = 1.0-(1.0-np.linspace(0.0, 1.0, n))**2
    faces = np.r_[0.0, (xi[1:] + xi[:-1]) / 2.0, 1.0]
    weights = np.diff(faces**2) / 2.0
    return xi, faces, weights


class RadialModel:
    def __init__(self, spec, n=161, boundary=None, fixed_radius=False, latent_heat=True):
        self.spec = spec
        self.n = n
        self.xi, self.faces, self.weights = grid_weights(n)
        self.boundary = boundary or Boundary.for_problem(spec.name)
        self.moving = spec.uses_shrinkage and not fixed_radius
        self.h_conv = h_conv(spec.name)
        self.h_mass = h_mass(spec.name)
        self.latent_heat = latent_heat
        self.moisture_boundary = "supply_gas"
        self.lewis = LEWIS_NUMBER
        self.equilibrium_C = 0.0
        self.rho_d0 = float(spec.properties.rho(spec.initial.C, spec.initial.T)) / (1 + spec.initial.C)

    def dry_density(self, t):
        return self.rho_d0 * (self.spec.geometry.radius0 / self.radius(t))**2

    def surface_fluxes(self, t, T_s, C_s):
        T_amb, C_amb = self.boundary.ambient(t)
        if self.moisture_boundary == "legacy_effective":
            moisture = outward_flux(C_s, C_amb, self.h_mass)
        else:
            supply = self.dry_density(t) * self.h_mass * (C_s-self.equilibrium_C)
            gas = gas_evaporation_capacity(T_s, C_amb, self.h_conv, self.lewis)
            # 物理互补边界，允许气相凝结；绝不裁剪数值状态T或C。
            moisture = np.minimum(supply, gas) / self.dry_density(t)
        convective = self.h_conv * (T_amb - T_s)
        latent = self.dry_density(t) * moisture * latent_heat_vaporization(T_s) if self.latent_heat else 0.0
        return moisture, convective, latent

    def radius(self, t):
        return self.boundary.radius(t) if self.moving else self.spec.geometry.radius0

    def initial(self):
        # 最后两项是边界累计质量损失（归一化干物质基准）和加热量。
        return np.r_[np.full(self.n, self.spec.initial.T),
                     np.full(self.n, self.spec.initial.C), 0.0, 0.0]

    def rhs(self, t, y):
        n = self.n
        T, C = y[:n], y[n:2*n]
        p = self.spec.properties
        R = self.radius(t)
        k = p.k(C, T)
        D = p.D(C, T)
        capacity = p.rho(C, T) * p.cp(C, T)
        # q = r * coefficient * field_r，正号表示向内输运贡献。
        qT, qC = np.zeros(n+1), np.zeros(n+1)
        qT[1:-1] = self.faces[1:-1] * (k[1:]+k[:-1])/2 * np.diff(T)/np.diff(self.xi)
        qC[1:-1] = self.faces[1:-1] * (D[1:]+D[:-1])/2 * np.diff(C)/np.diff(self.xi)
        moisture, convective, latent = self.surface_fluxes(t, T[-1], C[-1])
        qT[-1] = R * (convective - latent)
        qC[-1] = -R * moisture
        dT = np.diff(qT) / (R*R*self.weights*capacity)
        dC = np.diff(qC) / (R*R*self.weights)
        loss_rate = -qC[-1] / (R*R)
        heat_rate = qT[-1]
        return np.r_[dT, dC, loss_rate, heat_rate]

    def sparsity(self):
        n = self.n
        s = lil_matrix((2*n+2, 2*n+2), dtype=int)
        for i in range(n):
            near = list(range(max(0,i-1), min(n,i+2)))
            s[i, near] = 1
            s[i, [j+n for j in near]] = 1
            s[i+n, near] = 1
            s[i+n, [j+n for j in near]] = 1
        s[2*n, 2*n-1] = 1
        s[2*n+1, n-1] = 1
        s[2*n+1, 2*n-1] = 1
        return s.tocsr()

    def jacobian(self, t, y):
        """六色差分Jacobian，累计量对应的零列不作自适应扰动。

        防止SciPy默认差分反复放大严格零导数列的扰动因子而溢出。
        累计通量行使用解析导数；不屏蔽运行时警告。
        """
        n = self.n
        baseline = self.rhs(t, y)
        steps = np.sqrt(np.finfo(float).eps)*np.maximum(np.abs(y), 1.0)
        rows, cols, data = [], [], []
        for field in range(2):
            for color in range(3):
                ids = np.arange(color, n, 3)+field*n
                perturbed = y.copy()
                perturbed[ids] += steps[ids]
                difference = self.rhs(t, perturbed)-baseline
                for j in ids:
                    i = j % n
                    for row_field in range(2):
                        for k in range(max(0,i-1),min(n,i+2)):
                            row = row_field*n+k
                            rows.append(row)
                            cols.append(j)
                            data.append(difference[row]/steps[j])
        for j in (n-1, 2*n-1):
            perturbed = y.copy()
            perturbed[j] += steps[j]
            difference = self.rhs(t, perturbed) - baseline
            for row in (2*n, 2*n+1):
                rows.append(row)
                cols.append(j)
                data.append(difference[row] / steps[j])
        return coo_matrix((data,(rows,cols)),shape=(2*n+2,2*n+2)).tocsc()


def solve_radial(spec, **opts):
    start = time.perf_counter()
    n = int(opts.get("n_internal", 321))
    if n < 3:
        raise ValueError("至少需要三个空间节点")
    boundary = opts.get("boundary") or Boundary.for_problem(spec.name)
    model = RadialModel(spec, n, boundary, opts.get("fixed_radius", False), opts.get("latent_heat", True))
    model.moisture_boundary = opts.get("moisture_boundary", "supply_gas")
    model.lewis = opts.get("lewis", LEWIS_NUMBER)
    model.equilibrium_C = opts.get("equilibrium_C", 0.0)
    rtol = float(opts.get("rtol", 2e-9))
    atol = float(opts.get("atol", 2e-10))
    max_step = float(opts.get("max_step", 120.0))
    method = opts.get("method", "BDF")
    if method not in {"BDF", "Radau"}:
        raise ValueError("刚性积分方法必须为BDF或Radau")
    align_boundary_knots = bool(opts.get("align_boundary_knots", False))
    horizon = float(opts.get("t_end", spec.grid.t_end))
    target = spec.extra.get("target_C", 0.15)
    seek_end = opts.get("seek_end", spec.name != "q1")

    def event(t, y):
        return np.max(y[n:2*n]) - target

    event.direction = -1
    event.terminal = True
    # 在4小时边界外推接点重启，避免跳过敏感性算例的参数跳变。
    split = boundary.ambient_t[-1]
    knots = boundary.ambient_t if align_boundary_knots else np.array([split])
    if align_boundary_knots and model.moving:
        knots = np.unique(np.r_[knots, boundary.radius_t])
    edges = [0.0] + [float(x) for x in knots if 0 < x < horizon] + [horizon]
    pieces = []
    y0 = model.initial()
    event_time = None

    def starting_step(t0, t1, state, step_limit):
        if not align_boundary_knots:
            return None
        # 默认启动估计含显式试探；极细表面单元会使其越过C=0。
        # 限制初始试探为局部浓度变化时间尺度的1%，不裁剪状态。
        rate = model.rhs(t0, state)[n:2*n]
        active = np.abs(rate) > 0
        scale = np.min(state[n:2*n][active] / np.abs(rate[active])) if active.any() else 1.0
        return min(1.0, step_limit, t1-t0, 0.01*scale)

    for a, b in zip(edges[:-1], edges[1:]):
        step = min(max_step, 30.0) if a < split else max_step
        result = solve_ivp(model.rhs, (a,b), y0, method=method, rtol=rtol, atol=atol,
                           max_step=step, jac=model.jacobian, dense_output=True,
                           first_step=starting_step(a, b, y0, step),
                           events=event if seek_end else None)
        if not result.success:
            raise RuntimeError(f"{spec.name} {method}失败: {result.message}")
        pieces.append(result)
        y0 = result.y[:, -1]
        if seek_end and result.t_events[0].size:
            event_time = float(result.t_events[0][0])
            # 正式xlsx保留均匀输出，继续到首个严格合格输出点。
            output_end = (np.floor(event_time/spec.grid.dt)+1)*spec.grid.dt
            if output_end > horizon:
                raise ValueError("终点后的首个输出时刻超出可计算范围")
            tail = solve_ivp(model.rhs, (event_time, output_end), y0, method=method,
                             rtol=rtol, atol=atol, max_step=step,
                             first_step=starting_step(event_time, output_end, y0, step),
                             jac=model.jacobian, dense_output=True)
            if not tail.success:
                raise RuntimeError(tail.message)
            pieces.append(tail)
            horizon = output_end
            break
    if seek_end and event_time is None:
        raise ValueError(f"{spec.name} 在{horizon/3600:g} h内未达到全场<{target}; "
                         f"末值={np.max(y0[n:2*n]):.8f}，需复核或延长获准范围")

    t = np.asarray(opts.get("sample_times", np.arange(0.0, horizon+spec.grid.dt/2,
                                                     spec.grid.dt)), dtype=float)
    if np.any(t < 0) or np.any(t > horizon+1e-8):
        raise ValueError("采样时刻超出已求解区间")
    r = (model.xi*spec.geometry.radius0
         if model.moving else spec.grid.r)
    T, C = np.empty((len(t), len(r))), np.empty((len(t),len(r)))
    radii = np.asarray([model.radius(x) for x in t])
    max_mass_residual = 0.0
    max_energy_residual = 0.0
    initial_mass = model.weights.sum()*spec.initial.C
    initial_capacity = float(np.asarray(spec.properties.rho(spec.initial.C,spec.initial.T)
                                         *spec.properties.cp(spec.initial.C,spec.initial.T)))
    for piece in pieces:
        raw_mass_error = np.abs(model.weights@piece.y[n:2*n] + piece.y[2*n]-initial_mass)
        max_mass_residual = max(max_mass_residual, float(raw_mass_error.max()/initial_mass))
        indexes = np.flatnonzero((t >= piece.t[0]-1e-8) & (t <= piece.t[-1]+1e-8))
        for chunk in np.array_split(indexes, max(1, int(np.ceil(len(indexes)/1024)))):
            if not len(chunk):
                continue
            states = piece.sol(t[chunk])
            mass_error = np.abs(model.weights@states[n:2*n] + states[2*n] - initial_mass)
            max_mass_residual = max(max_mass_residual, float(mass_error.max()/initial_mass))
            if spec.name == "q1":
                energy = initial_capacity*spec.geometry.radius0**2*(
                    model.weights@(states[:n]-spec.initial.T))
                scale = max(1.0, float(np.max(np.abs(states[2*n+1]))))
                max_energy_residual = max(max_energy_residual,
                    float(np.max(np.abs(energy-states[2*n+1]))/scale))
            for j, idx in enumerate(chunk):
                # q4保存材料坐标场；r是参考半径，实际半径由meta.R逐行给出。
                xi_target = r/spec.geometry.radius0
                T[idx] = np.interp(xi_target, model.xi, states[:n,j])
                C[idx] = np.interp(xi_target, model.xi, states[n:2*n,j])
    if not np.all(np.isfinite(T)) or not np.all(np.isfinite(C)) or np.min(C)<0:
        raise RuntimeError("非有限值或负浓度；拒绝写出")
    final_raw = pieces[-1].y[:, -1]
    event_state = pieces[-2].y[:, -1] if event_time is not None else None
    meta = {"n_internal": n, "dt_internal": f"adaptive {method}, max_step={max_step}s",
            "theta": None, "rtol": rtol, "atol": atol,
            "n_iterations": sum(x.nfev for x in pieces),
            "residual": max_mass_residual, "mass_balance_relative": max_mass_residual,
            "q1_energy_balance_relative": max_energy_residual if spec.name=="q1" else None,
            "wall_time_s": time.perf_counter()-start, "event_time_s": event_time,
            "first_output_below_s": horizon if seek_end else None,
            "coordinate": "material" if model.moving else "physical",
            "R": radii.tolist(), "method": f"nodal finite volume + {method}",
            "align_boundary_knots": align_boundary_knots,
            "max_C_final_internal": float(np.max(final_raw[n:2*n])),
            "radial_C_monotone_final": bool(np.all(np.diff(final_raw[n:2*n]) <= 1e-9)),
            "event_C": event_state[n:2*n].tolist() if event_state is not None else None,
            "event_T": event_state[:n].tolist() if event_state is not None else None,
            "event_R": float(model.radius(event_time)) if event_time is not None else None,
            "internal_xi": model.xi.tolist(), "mesh": "surface_graded_power_2"}
    meta.update(latent_heat=model.latent_heat, rho_d0_kg_m3=model.rho_d0,
                min_T_K=float(T.min()), min_C=float(C.min()),
                boundary_description=getattr(boundary, "description", "attachment effective moisture boundary"))
    return Solution(t, r, T, C, meta)
