"""run_q1~q4 的公共执行逻辑。

流程：spec -> solver.solve -> 交付表格 -> 写 xlsx -> 打印摘要

四问求解器均已实现（src/q1~q4/solver.py 统一转发到 src/common/radial.py，
物理规格见 docs/model/numerics.md）。本文件负责**流程与交付**：
求解、写 results/resultN.xlsx（经 io_excel 硬校验）、导出论文展示网格 csv、
写 qN_summary.json 与 outputs/ 缓存。
"""

from __future__ import annotations

import sys
import time
import traceback
import json
import numpy as np

from _bootstrap import setup

setup()

from common import export, io_excel, paths, problem_spec  # noqa: E402


def run(problem: str) -> int:
    spec = problem_spec.get(problem)
    print("=" * 72)
    print(spec.describe())
    print("=" * 72)

    # 1) 求解
    t0 = time.perf_counter()
    try:
        solver = __import__(f"{spec.name}.solver", fromlist=["solve"])
    except ImportError as e:
        print(f"!! 无法导入 {spec.name}.solver：{e}")
        return 1

    try:
        sol = solver.solve(spec, n_internal=641)
    except NotImplementedError as e:
        print()
        print(f"⏸  {spec.name} 的求解器尚未实现。这不是故障，是框架的预期状态。")
        print()
        print(str(e))
        print()
        print("下一步：")
        print(f"  1. @model 完成 docs/model/{spec.name}.md（控制方程 + 离散格式 + 边界条件）")
        print(f"  2. @impl 实现 src/{spec.name}/solver.py")
        print(f"  3. 重跑 make {spec.name}")
        return 2
    except Exception:
        print("!! 求解过程抛出异常：")
        traceback.print_exc()
        return 1

    wall = time.perf_counter() - t0
    sol.meta.setdefault("wall_time_s", round(wall, 3))
    print(f"  求解完成，耗时 {wall:.2f} s")
    print("  " + export.summarize(sol, spec))
    print("  正在流式写入结果文件……", flush=True)

    # 2) 交付物
    try:
        sheets = export.result_sheets(sol, spec)
        dest = io_excel.write_result(spec.name, sheets)
    except io_excel.ResultFormatError as e:
        print()
        print("!! 交付格式校验未通过，**没有写出文件**：")
        print(str(e))
        return 1

    print(f"  交付物 {paths.rel(dest)}  ({dest.stat().st_size} B)")
    for name, df in sheets.items():
        print(f"    工作表「{name}」 {df.shape[0]} 行 x {df.shape[1]} 列")

    # 3) 论文用展示网格
    _write_table_csvs(sol, spec)
    metadata = {k:v for k,v in sol.meta.items() if k not in {"R","event_T","event_C"}}
    (paths.RESULTS_DIR / f"{problem}_summary.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    paths.OUTPUTS_CACHE.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(paths.OUTPUTS_CACHE / f"{problem}.npz", t=sol.t, r=sol.r,
                        T=sol.T,C=sol.C,meta=json.dumps(sol.meta))

    print()
    print("  提示：别忘了 make tables figs，以及更新 docs/TASKS.md")
    return 0


def _write_table_csvs(sol, spec) -> None:
    """把论文要用的展示网格写成 csv，供 make tables 消费。"""
    import numpy as np

    from common import problem_spec as ps

    made = []
    if spec.name == "q1":
        times = np.array([100, 300, 600, 900, 1200, 1500, 1800], dtype=float)
        made.append(("q1_temp", export.table_rows(sol, spec, times_s=times, field="T")))
        made.append(("q1_moist", export.table_rows(sol, spec, times_s=times, field="C")))
    elif spec.name == "q2":
        times = np.arange(0.5, 3.01, 0.5) * 3600.0
        made.append(("q2_temp", export.table_rows(sol, spec, times_s=times, field="T")))
        made.append(("q2_moist", export.table_rows(sol, spec, times_s=times, field="C")))
    else:
        # 问题 3/4：每隔 6 h 一行，最后一行是烘干结束时间
        t_end = float(sol.meta["event_time_s"])
        times = list(np.arange(6.0, t_end / 3600.0, 6.0) * 3600.0) + [t_end]
        # 问题 4 表 6 的末列是「药材表面」而非固定 2 cm，故只取 0~1.5 的固定列
        dists = ps.TABLE_R_CM[:-1] if spec.uses_shrinkage else ps.TABLE_R_CM
        made.append(
            (
                f"{spec.name}_moist",
                export.table_rows(
                    sol,
                    spec,
                    times_s=np.array(times),
                    distances_cm=dists,
                    include_surface=spec.uses_shrinkage,
                ),
            )
        )

    for name, df in made:
        p = io_excel.write_table_csv(df.reset_index(), name)
        print(f"  展示表格 {paths.rel(p)}  ({df.shape[0]} 行)")


def main(problem: str) -> int:
    return run(problem)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "q1"))
