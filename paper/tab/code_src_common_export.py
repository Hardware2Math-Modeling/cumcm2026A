"""Solution -> 交付物表格（result*.xlsx 的工作表 + 论文用展示网格）。

列结构一律取自 `io_excel.layout()`（`make probe` 实测结论），不自己发明。
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import io_excel, problem_spec, units
from .io_excel import SURFACE_HEADER, TIME_HEADER, ResultLayout
from .problem_spec import ProblemSpec
from .solution import Solution


def _sample_rows(t: np.ndarray, target: np.ndarray) -> np.ndarray:
    """对每个目标时刻，找最近的网格索引（不插值，避免引入额外误差）。"""
    return np.array([int(np.argmin(np.abs(t - x))) for x in target], dtype=int)


def _extract(field_2d: np.ndarray, r: np.ndarray, r_target_cm: np.ndarray) -> np.ndarray:
    """把 (n_t, n_r) 的场在指定物理半径上取值。

    若目标半径与网格对齐（常见情形）直接索引；否则按行线性插值。
    """
    r_cm = units.m_to_cm(r)
    # 注意：必须先比长度再 np.allclose —— 形状不同时 allclose 会直接抛 broadcast 错误
    if r_cm.size == r_target_cm.size and np.allclose(np.sort(r_target_cm), np.sort(r_cm)):
        order = np.argsort(r_cm)
        return field_2d[:, order]

    out = np.empty((field_2d.shape[0], r_target_cm.size))
    for i in range(field_2d.shape[0]):
        out[i] = np.interp(r_target_cm, r_cm, field_2d[i])
    return out


def result_sheets(sol: Solution, spec: ProblemSpec) -> dict[str, pd.DataFrame]:
    """构造 result*.xlsx 的工作表。

    工作表名、列数、表头、时间单位一律按 `io_excel.layout(spec.name)`：
        · A 列 = `时间\\到药材中心的距离`，单位 **秒**
        · 距离列 = 0, 0.1, 0.2, …, 2.0（共 21 列；问题 4 末列是「药材表面」）
    """
    lay: ResultLayout = io_excel.layout(spec.name)
    headers = lay.distance_headers()

    # 交付网格的目标半径：问题 1~3 是 0~2.0 的全 21 列；
    # 问题 4 前 20 列是固定物理位置 0~1.9，末列「药材表面」另行处理。
    target_cm = np.array([float(h) for h in headers if _is_numeric(h)], dtype=float)
    has_surface_col = lay.last_header == SURFACE_HEADER

    sheets: dict[str, pd.DataFrame] = {}
    for sheet_name, field in lay.sheets:
        df = pd.DataFrame({TIME_HEADER: sol.t})  # 单位：秒（模板如此）

        values = sol.T if field == "T" else sol.C
        if spec.uses_shrinkage and sol.meta.get("coordinate") == "material":
            vals = np.empty((len(sol.t), len(target_cm)))
            for i, R in enumerate(sol.meta["R"]):
                physical_r = sol.r / spec.geometry.radius0 * R
                vals[i] = np.interp(units.cm_to_m(target_cm), physical_r, values[i],
                                    right=np.nan)
        else:
            vals = _extract(values, sol.r, target_cm)
        if field == "T":
            vals = units.k_to_c(vals)

        for j, head in enumerate(headers):
            if has_surface_col and head == SURFACE_HEADER:
                # 问题 4：末列 = 当时的表面节点值，而非固定 2 cm 处的值
                df[SURFACE_HEADER] = (
                    units.k_to_c(sol.T[:, -1]) if field == "T" else sol.C[:, -1]
                )
            else:
                df[head] = vals[:, j]

        sheets[sheet_name] = df
    return sheets


def _is_numeric(s: str) -> bool:
    try:
        float(s)
        return True
    except (TypeError, ValueError):
        return False


#: 论文表格的时间单位：问题 1 用秒（表 1/表 2），问题 2~4 用小时（表 3~表 6）
TABLE_TIME_UNIT: dict[str, str] = {"q1": "s", "q2": "h", "q3": "h", "q4": "h"}


def table_rows(
    sol: Solution,
    spec: ProblemSpec,
    *,
    times_s: np.ndarray,
    distances_cm: tuple[float, ...] = problem_spec.TABLE_R_CM,
    field: str = "C",
    include_surface: bool = False,
) -> pd.DataFrame:
    """论文表 1~表 6 所需的展示网格。

    Parameters
    ----------
    times_s : 展示时刻，单位秒（内部按最近网格点取值，不插值）
    include_surface : 问题 4 的末列是「药材表面」而非固定距离

    返回的 DataFrame 索引单位由 `TABLE_TIME_UNIT` 决定（q1 秒，q2~q4 小时）。
    """
    field = field.upper()
    times_s = np.asarray(times_s, dtype=float)
    if np.any(times_s < sol.t[0]) or np.any(times_s > sol.t[-1]):
        raise ValueError("展示时间超出求解结果，不允许最近邻冒充")

    cols: dict[str, np.ndarray] = {}
    for d in distances_cm:
        cols[f"{d:g}"] = []
    if include_surface:
        cols[SURFACE_HEADER] = []
    values = sol.T if field == "T" else sol.C
    for t in times_s:
        event_time = sol.meta.get("event_time_s")
        if event_time is not None and abs(t-event_time) < 1e-6:
            vals = np.asarray(sol.meta[f"event_{field}"])
            R = sol.meta["event_R"]
            r = np.asarray(sol.meta["internal_xi"])*R
        else:
            vals = np.asarray([np.interp(t, sol.t, values[:,j]) for j in range(sol.n_r)])
            R = np.interp(t, sol.t, sol.meta["R"]) if spec.uses_shrinkage else spec.geometry.radius0
            r = sol.r/spec.geometry.radius0*R
        if field == "T":
            vals = units.k_to_c(vals)
        for d in distances_cm:
            cols[f"{d:g}"].append(np.interp(units.cm_to_m(d), r, vals, right=np.nan))
        if include_surface:
            cols[SURFACE_HEADER].append(vals[-1])

    index = np.asarray(times_s, dtype=float)
    if TABLE_TIME_UNIT.get(spec.name, "s") == "h":
        index = units.s_to_h(index)

    out = pd.DataFrame(cols, index=pd.Index(index, name="时间"))
    out.columns.name = "到药材中心的距离/cm"
    return out


def summarize(sol: Solution, spec: ProblemSpec) -> str:
    """跑完打印的一行摘要，便于在日志里追溯。"""
    return (
        f"[{spec.name}] {sol.summary()} | "
        f"max_r C 终值={sol.max_C_over_r()[-1]:.4f} kg/kg | "
        f"内部步长={sol.meta.get('dt_internal', '未记录')}"
    )
