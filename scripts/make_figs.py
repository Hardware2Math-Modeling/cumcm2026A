"""results/result*.xlsx  ->  paper/figs/*.pdf

运行： make figs

设计意图：插图**从交付物本身**重绘，而不是从求解器的内存对象。
    这样「论文里的图和交付的 xlsx 一定一致」——如果两者对不上，说明有人手工改过 xlsx。

⚠️ 不要手工编辑 paper/figs/*.pdf，下次 make 就覆盖了。
"""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from _bootstrap import setup

setup()

from common import io_excel, paths, plotting, units  # noqa: E402
from common.solution import Solution  # noqa: E402


def load_solution(problem: str) -> Solution | None:
    """把 results/resultN.xlsx 读回成 Solution（SI 单位）。

    若交付物尚不存在则返回 None —— 框架阶段这是正常状态，不算失败。
    """
    path = paths.result_path(problem)
    if not path.exists():
        return None

    sheets = pd.read_excel(path, sheet_name=None)
    df_c = sheets.get(io_excel.SHEET_MOISTURE)
    if df_c is None:
        print(f"  !! {paths.rel(path)} 里没有「{io_excel.SHEET_MOISTURE}」工作表，跳过")
        return None

    # 时间列：按模板表头判断单位（h 还是 s）
    t = df_c.iloc[:, 0].to_numpy(dtype=float)
    head = str(df_c.columns[0]).lower()
    if head.endswith("/h") or "小时" in head or head.strip() == "h":
        t = units.h_to_s(t)

    r_cm, cols = _numeric_distance_columns(df_c)
    if not cols:
        print(f"  !! {paths.rel(path)} 的距离列无法解析，跳过")
        return None

    C = df_c[cols].to_numpy(dtype=float)
    r = units.cm_to_m(r_cm)

    df_t = sheets.get(io_excel.SHEET_TEMPERATURE)
    if df_t is not None:
        T = units.c_to_k(df_t[cols].to_numpy(dtype=float))
    else:
        # result3/4 没有温度表。Solution 要求 T，用 NaN 占位，
        # 只画水分浓度图（plot_profiles(field="C") 不会碰 T）。
        T = np.full_like(C, np.nan)

    return Solution(t=t, r=r, T=T, C=C, meta={"source": paths.rel(path)})


def _numeric_distance_columns(df: pd.DataFrame) -> tuple[np.ndarray, list[str]]:
    """返回 (距离/cm 数组, 可用的列名)。跳过"药材表面"这类非数值列。"""
    cols: list[str] = []
    vals: list[float] = []
    for c in df.columns[1:]:
        try:
            vals.append(float(c))
            cols.append(c)
        except (TypeError, ValueError):
            print(f"    · 跳过非数值距离列「{c}」（问题 4 的『药材表面』列需单独处理）")
    return np.asarray(vals, dtype=float), cols


def figures_for(problem: str, sol: Solution) -> list[str]:
    made: list[str] = []
    n = problem[-1]

    if np.isfinite(sol.T).any():
        made.append(
            str(
                plotting.plot_profiles(
                    sol,
                    field="T",
                    times=[sol.t[-1] * f for f in (0.1, 0.3, 0.6, 1.0)],
                    out=f"fig{n}-T-profiles",
                    title=f"药材温度的径向分布（问题 {n}）",
                )
            )
        )

    made.append(
        str(
            plotting.plot_profiles(
                sol,
                field="C",
                times=[sol.t[-1] * f for f in (0.1, 0.3, 0.6, 1.0)],
                out=f"fig{n}-C-profiles",
                title=f"药材水分浓度的径向分布（问题 {n}）",
            )
        )
    )

    span_cm = float(units.m_to_cm(sol.r[-1]))
    locs = [d for d in (0.0, 0.5, 1.0, 1.5, span_cm) if d <= span_cm + 1e-9]
    made.append(
        str(
            plotting.plot_history(
                sol,
                locations_cm=sorted(set(locs)),
                field="C",
                out=f"fig{n}-C-history",
                title=f"不同径向位置的水分浓度历程（问题 {n}）",
            )
        )
    )
    return made


def main() -> int:
    if not plotting.check_fonts():
        print("!! 中文字体缺失，图里的中文会变成方块。请先装字体。")
        print("   macOS 一般自带 Songti SC；若在容器/CI 里，装 fonts-noto-cjk。")
        return 1

    paths.FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    total = 0
    any_found = False
    for n in (1, 2, 3, 4):
        problem = f"q{n}"
        sol = load_solution(problem)
        if sol is None:
            print(f"· {problem}: results/result{n}.xlsx 不存在，跳过")
            continue
        any_found = True
        print(f"· {problem}: {sol.summary()}")
        for f in figures_for(problem, sol):
            print(f"    -> {paths.rel(f)}")
            total += 1

    if not any_found:
        print()
        print("⚠️ 还没有任何交付物。先跑 make q1..q4。")
        print("   本步骤不需要求解器已实现 —— 求解器就绪后会自动产出。")
    else:
        print(f"\n共生成 {total} 张图（矢量 PDF）到 {paths.rel(paths.FIGURES_DIR)}")
        print("论文里用 \\includegraphics{figs/<name>.pdf} 引用，不要再复制图片。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
