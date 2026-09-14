"""四问的最小可运行模型：圆柱径向有限体积 + BDF。

状态向量为 ``[T_0...T_{n-1}, C_0...C_{n-1}, loss, heat]``。
温度用 K、长度用 m、时间用 s；只有 ``export.py`` 转换为题目表格单位。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import openpyxl
from scipy.integrate import solve_ivp
from scipy.sparse import lil_matrix

from .criterion import event as criterion_event
from .fit import fit_boundary

LENGTH_M = 0.25
RADIUS0_M = 0.02
T0_K = 301.15
C0 = 2.55
TARGET_C = 0.15
H_CONV = 25.0
H_MASS = 8.0e-7


class Properties:
    """附录 2、3、4 的物性公式。"""

    def __init__(self, appendix: int):
        if appendix not in (2, 3, 4):
            raise ValueError("appendix 必须是 2、3 或 4")
        self.appendix = appendix

    def values(self, C, T):
        C = np.asarray(C, dtype=float)
        T = np.asarray(T, dtype=float)
        if np.any(C < 0) or np.any(T < 200):
            raise ValueError("物性函数要求 C>=0 且 T 为开尔文")
        w = C / (1.0 + C)
        if self.appendix == 2:
            rho = np.full(np.broadcast(C, T).shape, 820.0)
            cp = np.full_like(rho, 2600.0)
            k = np.full_like(rho, 0.36)
            D = 7.0e-9 * np.exp(-0.89 / np.maximum(C, np.finfo(float).tiny))
        elif self.appendix == 3:
            rho = 650.0 + 128.0 * C
            cp = 1450.0 + 2736.0 * w
            k = 0.21 + 0.38 * w
            D = 2.4e-3 * np.exp(-0.45 / np.maximum(C, np.finfo(float).tiny) - 3850.0 / T)
        else:
            rho = 760.0 + 90.0 * C
            cp = 1850.0 + 2150.0 * w
            k = 0.12 + 0.20 * w
            D = 4.2e-4 * np.exp(-0.30 / np.maximum(C, np.finfo(float).tiny) - 3850.0 / T)
        return rho, cp, k, D


class Boundary:
    """附件 1/2 的边界数据；ambient='fit' 时只替换环境边界。"""

    def __init__(self, root: Path, ambient: str = "measured"):
        self.root = Path(root)
        self.t_air, self.T_air, self.C_air = self._read(
            self.root / "problem" / "附件" / "附件1.xlsx", 3
        )
        self.t_radius, self.radius_cm = self._read(
            self.root / "problem" / "附件" / "附件2.xlsx", 2
        )
        self.fit = fit_boundary(self.root / "problem" / "附件" / "附件1.xlsx") if ambient == "fit" else None
        if ambient not in ("measured", "fit"):
            raise ValueError("ambient 只能是 measured 或 fit")
        self.ambient_mode = ambient

    @staticmethod
    def _read(path: Path, columns: int):
        book = openpyxl.load_workbook(path, read_only=True, data_only=True)
        try:
            rows = list(book.active.values)
        finally:
            book.close()
        data = np.asarray(rows[1:], dtype=float)
        if data.shape[1] != columns:
            raise ValueError(f"{path} 列数不符")
        if columns == 3:
            return data[:, 0], data[:, 1] + 273.15, data[:, 2]
        return data[:, 0], data[:, 1]

    def ambient(self, t_s):
        if self.fit is not None:
            return self.fit.ambient(t_s)
        late = np.asarray(t_s) > self.t_air[-1]
        T = np.interp(t_s, self.t_air, self.T_air)
        C = np.interp(t_s, self.t_air, self.C_air)
        return T + late * 0.0, C + late * 0.0

    def radius(self, t_s):
        if np.any(np.asarray(t_s) > self.t_radius[-1] + 1e-7):
            raise ValueError("问题4时间超过附件2的72小时范围")
        return np.interp(t_s, self.t_radius, self.radius_cm) * 0.01


def grid(n: int):
    """表面加密材料坐标网格和无量纲控制体积。"""
    xi = 1.0 - (1.0 - np.linspace(0.0, 1.0, n)) ** 2
    faces = np.r_[0.0, (xi[1:] + xi[:-1]) / 2.0, 1.0]
    weights = np.diff(faces**2) / 2.0
    return xi, faces, weights


@dataclass
class Result:
    question: str
    t: np.ndarray
    T: np.ndarray
    C: np.ndarray
    R: np.ndarray
    xi: np.ndarray
    event_time_s: float | None
    criterion: str


def solve(
    question: str,
    boundary: Boundary,
    *,
    n: int = 2561,
    rtol: float = 2.0e-11,
    atol: float = 2.0e-12,
    max_step: float = 60.0,
    criterion: str = "max",
) -> Result:
    """求解 q1~q4；q3/q4 用阈值事件，q1/q2 同样积分到首次达标。"""
    question = question.lower().replace("result", "q")
    if question not in ("q1", "q2", "q3", "q4"):
        raise ValueError("question 必须是 q1、q2、q3 或 q4")
    if criterion not in ("max", "center"):
        raise ValueError("criterion 只能是 max 或 center")
    appendix = {"q1": 2, "q2": 3, "q3": 3, "q4": 4}[question]
    moving = question == "q4"
    xi, faces, weights = grid(n)
    props = Properties(appendix)
    N = 2 * n + 2

    def radius(t_s):
        return boundary.radius(t_s) if moving else RADIUS0_M

    def rhs(t_s, y):
        T, C = y[:n], y[n : 2 * n]
        R = float(radius(t_s))
        T_amb, C_amb = boundary.ambient(t_s)
        T_amb, C_amb = float(T_amb), float(C_amb)
        rho, cp, k, D = props.values(C, T)
        kf = (k[1:] + k[:-1]) / 2.0
        Df = (D[1:] + D[:-1]) / 2.0
        qT = np.zeros(n + 1)
        qC = np.zeros(n + 1)
        qT[1:-1] = faces[1:-1] * kf * np.diff(T) / np.diff(xi)
        qC[1:-1] = faces[1:-1] * Df * np.diff(C) / np.diff(xi)
        qT[-1] = R * H_CONV * (T_amb - T[-1])
        qC[-1] = -R * H_MASS * (C[-1] - C_amb)
        dT = np.diff(qT) / (R * R * weights * rho * cp)
        dC = np.diff(qC) / (R * R * weights)
        loss_rate = -qC[-1] / (R * R)
        return np.r_[dT, dC, loss_rate, qT[-1]]

    sparsity = lil_matrix((N, N), dtype=int)
    for i in range(n):
        near = list(range(max(0, i - 1), min(n, i + 2)))
        sparsity[i, near] = 1
        sparsity[i, [j + n for j in near]] = 1
        sparsity[i + n, near] = 1
        sparsity[i + n, [j + n for j in near]] = 1
    sparsity[2 * n, n - 1] = 1
    sparsity[2 * n, 2 * n - 1] = 1
    sparsity[2 * n + 1, n - 1] = 1

    def event(t_s, y):
        return criterion_event(y[n : 2 * n], TARGET_C, criterion)

    event.terminal = True
    event.direction = -1

    y0 = np.r_[np.full(n, T0_K), np.full(n, C0), 0.0, 0.0]
    horizon = 1800.0 if question == "q1" else 259200.0
    seek_end = question != "q1"
    dt_out = 1.0 if question in ("q1", "q2") else 60.0
    knots = np.unique(np.r_[boundary.t_air, boundary.t_radius if moving else []])
    edges = [0.0] + [float(t) for t in knots if 0 < t < horizon] + [horizon]
    pieces = []
    event_time = None

    def first_step(a, b, state, limit):
        rate = rhs(a, state)[n : 2 * n]
        active = np.abs(rate) > 0
        scale = np.min(state[n : 2 * n][active] / np.abs(rate[active])) if np.any(active) else 1.0
        return min(1.0, limit, b - a, 0.01 * scale)

    for a, b in zip(edges[:-1], edges[1:]):
        step = min(max_step, 30.0) if a < boundary.t_air[-1] else max_step
        solution = solve_ivp(
            rhs,
            (a, b),
            y0,
            method="BDF",
            rtol=rtol,
            atol=atol,
            max_step=step,
            first_step=first_step(a, b, y0, step),
            jac_sparsity=sparsity,
            dense_output=True,
            events=event if seek_end else None,
        )
        if not solution.success:
            raise RuntimeError(solution.message)
        pieces.append(solution)
        y0 = solution.y[:, -1]
        if seek_end and solution.t_events[0].size:
            event_time = float(solution.t_events[0][0])
            output_end = (np.floor(event_time / dt_out) + 1.0) * dt_out
            tail = solve_ivp(
                rhs,
                (event_time, output_end),
                y0,
                method="BDF",
                rtol=rtol,
                atol=atol,
                max_step=step,
                first_step=first_step(event_time, output_end, y0, step),
                jac_sparsity=sparsity,
                dense_output=True,
            )
            if not tail.success:
                raise RuntimeError(tail.message)
            pieces.append(tail)
            horizon = output_end
            break
    if seek_end and event_time is None:
        raise RuntimeError("在附件2覆盖时长内未达到 C<0.15")

    t = np.arange(0.0, horizon + 0.5 * dt_out, dt_out)
    # 内部网格只用于积分和事件；结果只保留题目要求的 0.1 cm 输出网格。
    # 这样问题 2 的两天结果不会把 2561 节点全部存入内存。
    xi_out = np.linspace(0.0, 1.0, 21)
    T = np.empty((len(t), xi_out.size))
    C = np.empty((len(t), xi_out.size))
    for piece in pieces:
        ids = np.flatnonzero((t >= piece.t[0] - 1e-8) & (t <= piece.t[-1] + 1e-8))
        for chunk in np.array_split(ids, max(1, int(np.ceil(len(ids) / 256)))):
            if len(chunk):
                state = piece.sol(t[chunk])
                for j, row in enumerate(chunk):
                    T[row] = np.interp(xi_out, xi, state[:n, j])
                    C[row] = np.interp(xi_out, xi, state[n : 2 * n, j])
    R = np.asarray([radius(x) for x in t])
    if criterion == "center" and event_time is not None:
        event_state = pieces[-2].y[:, -1]
        if np.max(event_state[n : 2 * n]) > TARGET_C + 1e-8:
            raise RuntimeError("中心事件先触发，但全场仍未达标")
    return Result(question, t, T, C, R, xi_out, event_time, criterion)
