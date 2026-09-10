"""框架自检 —— **不依赖 pytest**，只要有 numpy/pandas 就能跑。

运行： make selfcheck

用途：
    本仓库的正式测试在 tests/（pytest）。但竞赛现场的环境常常没装 pytest，
    而「框架是通的」这件事必须随时可验证。因此把最关键的几条不变式抽到这里，
    用纯 assert 表达。

    `make check` 在检测到没有 pytest 时会自动回退到本脚本。

覆盖：
    路径定位 / 单位换算与防呆 / 题目常量与附录不混用 / 附件结构 /
    交付模板结构（实测布局）/ 交付格式校验会硬失败 / Solution 语义
"""

from __future__ import annotations

import sys
import traceback

import numpy as np
import pandas as pd

from _bootstrap import setup

setup()

from common import correlations, io_excel, paths, problem_spec, units  # noqa: E402
from common.solution import Solution  # noqa: E402

_FAILED: list[tuple[str, str]] = []
_PASSED = 0


def check(name: str):
    """把函数注册为一条自检项。"""

    def deco(fn):
        try:
            fn()
        except Exception as e:  # noqa: BLE001
            _FAILED.append((name, f"{type(e).__name__}: {e}"))
            print(f"  ✗ {name}")
            print(f"      {type(e).__name__}: {e}")
            if "--verbose" in sys.argv:
                traceback.print_exc()
        else:
            globals()["_PASSED"] += 1
            print(f"  ✓ {name}")
        return fn

    return deco


print("=" * 72)
print("框架自检")
print("=" * 72)

# --- 路径 -------------------------------------------------------------------


@check("仓库根定位正确，题目原件存在")
def _():
    assert (paths.ROOT / "AGENTS.md").exists(), "AGENTS.md 不在仓库根"
    assert (paths.ROOT / "problem" / "A题.pdf").exists(), "题目原件缺失"
    assert paths.template_path("q1").name == "result1.xlsx"
    assert paths.result_path("4").name == "result4.xlsx"


# --- 单位 -------------------------------------------------------------------


@check("单位换算往返一致")
def _():
    assert abs(units.m_to_cm(units.cm_to_m(2.0)) - 2.0) < 1e-12
    assert abs(units.k_to_c(units.c_to_k(28.0)) - 28.0) < 1e-12
    assert abs(units.c_to_k(28.0) - 301.15) < 1e-12
    assert abs(units.h_to_s(1.0) - 3600.0) < 1e-12


@check("摄氏度冒充开尔文会被防呆断言拦下")
def _():
    try:
        units.assert_kelvin(np.array([28.0, 50.0]))
    except ValueError as e:
        assert "摄氏度" in str(e), f"错误信息应提示摄氏度，实际：{e}"
    else:
        raise AssertionError("未拦下摄氏度，防呆失效（这是本项目最危险的错误）")
    units.assert_kelvin(np.array([301.15, 323.15]))  # 正常开尔文不应抛


@check("干基/湿基换算正确")
def _():
    assert abs(correlations.wet_basis(0.0) - 0.0) < 1e-12
    assert abs(correlations.wet_basis(1.0) - 0.5) < 1e-12
    assert abs(correlations.wet_basis(2.55) - 2.55 / 3.55) < 1e-12


# --- 题目常量 ---------------------------------------------------------------


@check("题目给定量与 A题.pdf 一致")
def _():
    assert problem_spec.LENGTH_M == 0.25  # 长 25 cm
    assert problem_spec.RADIUS0_M == 0.02  # 半径 2 cm
    assert problem_spec.INITIAL_T_C == 28.0
    assert problem_spec.INITIAL_C_DRY == 2.55
    assert problem_spec.TARGET_C_DRY == 0.15
    assert problem_spec.Q1_T_END_S == 1800.0
    assert problem_spec.Geometry().aspect_ratio == 6.25  # L/(2R0) = 25/4


@check("附录 2/3/4 未混用；仅问题 4 有收缩")
def _():
    assert problem_spec.Q1.properties.appendix == 2
    assert problem_spec.Q2.properties.appendix == 3
    assert problem_spec.Q3.properties.appendix == 3
    assert problem_spec.Q4.properties.appendix == 4
    assert problem_spec.Q1.uses_shrinkage is False
    assert problem_spec.Q4.uses_shrinkage is True


@check("问题 1 交付网格 = 1801 时间点 x 21 空间点")
def _():
    assert problem_spec.Q1.grid.shape == (1801, 21), problem_spec.Q1.grid.shape
    assert problem_spec.Q1.grid.r[0] == 0.0, "交付网格必须含轴心 r=0"


# --- 附件 -------------------------------------------------------------------


@check("附件 1 结构：241 点 / 60 s 步长 / 覆盖 4 h")
def _():
    df = io_excel.read_attachment(1)
    assert list(df.columns) == ["时间", "温度", "水分浓度"]
    assert len(df) == 241
    t = df["时间"].to_numpy(dtype=float)
    assert t[-1] == 14400.0 and np.allclose(np.diff(t), 60.0)


@check("附件 2 结构：145 点 / 1800 s 步长 / 覆盖 72 h / 半径单调不增")
def _():
    df = io_excel.read_attachment(2)
    assert list(df.columns) == ["时间", "半径"]
    assert len(df) == 145
    r = df["半径"].to_numpy(dtype=float)
    t = df["时间"].to_numpy(dtype=float)
    assert t[-1] == 259200.0
    assert r[0] == 2.0 and np.all(np.diff(r) <= 0)
    assert abs(r[-1] - r[-2]) < 1e-12, "D-010：末段应有半径平台"


@check("数据缺口 D-009 / D-011 确实存在（不是幻觉）")
def _():
    a1 = io_excel.read_attachment(1)
    assert a1["时间"].max() == problem_spec.AMBIENT_COVERAGE_S < problem_spec.RADIUS_COVERAGE_S
    assert a1["水分浓度"].max() < problem_spec.INITIAL_C_DRY / 10, "D-011 量级差异应 > 10 倍"


# --- 交付模板（实测布局）----------------------------------------------------


@check("实测布局与 problem/附件/附件3 的真实模板一致")
def _():
    bad: list[str] = []
    for p in ("q1", "q2", "q3", "q4"):
        bad += io_excel.verify_layout_against_template(p)
    assert not bad, "布局与模板不一致：\n      - " + "\n      - ".join(bad)


@check("工作表名按模板：result1/2 是 温度+水分浓度，result3/4 是 Sheet1")
def _():
    assert set(io_excel.layout("q1").sheet_names) == {"温度", "水分浓度"}
    assert set(io_excel.layout("q2").sheet_names) == {"温度", "水分浓度"}
    assert set(io_excel.layout("q3").sheet_names) == {"Sheet1"}
    assert set(io_excel.layout("q4").sheet_names) == {"Sheet1"}


@check("距离列是完整 21 列（模板里的 '…' 是省略示意）")
def _():
    h = io_excel.layout("q1").distance_headers()
    assert len(h) == 21 and h[0] == "0" and h[1] == "0.1" and h[-1] == "2"
    h4 = io_excel.layout("q4").distance_headers()
    assert h4[-1] == io_excel.SURFACE_HEADER and h4[-2] == "1.9"


@check("交付时间单位是秒（不是题目表 3~表 6 表头写的 h）")
def _():
    assert io_excel.layout("q1").dt_s == 1.0
    assert io_excel.layout("q3").dt_s == 60.0


# --- 交付生成与格式校验 -----------------------------------------------------


def _dummy(n_t: int = 1801, radius: float = problem_spec.RADIUS0_M) -> Solution:
    return Solution(
        t=np.linspace(0.0, problem_spec.Q1_T_END_S, n_t),
        r=np.linspace(0.0, radius, 21),
        T=np.full((n_t, 21), 300.0),
        C=np.linspace(2.55, 0.10, n_t)[:, None] * np.ones((1, 21)),
    )


@check("export 生成的列结构与布局一致（1 列时间 + 21 列距离）")
def _():
    from common import export

    sheets = export.result_sheets(_dummy(), problem_spec.Q1)
    for name, df in sheets.items():
        assert list(df.columns) == io_excel.layout("q1").expected_columns(), name
    assert sheets["水分浓度"].shape == (1801, 22), sheets["水分浓度"].shape


@check("问题 4 末列是「药材表面」")
def _():
    from common import export

    sheets = export.result_sheets(_dummy(n_t=101), problem_spec.Q4)
    df = sheets["Sheet1"]
    assert list(df.columns) == io_excel.layout("q4").expected_columns()
    assert io_excel.SURFACE_HEADER in df.columns


@check("格式校验是硬失败：工作表名错 / 列数少 / 含 NaN 都必须抛异常")
def _():
    import tempfile
    from pathlib import Path

    from common import export

    saved = paths.RESULTS_DIR
    try:
        with tempfile.TemporaryDirectory() as d:
            paths.RESULTS_DIR = Path(d)

            try:
                io_excel.write_result("q1", {"错的表名": pd.DataFrame({io_excel.TIME_HEADER: [1.0]})})
            except io_excel.ResultFormatError as e:
                assert "工作表名不匹配" in str(e)
            else:
                raise AssertionError("工作表名错误未被拦下")

            short = {io_excel.TIME_HEADER: [1.0, 2.0]}
            for h in ["0", "0.1", "0.2", "2"]:
                short[h] = [0.0, 0.0]
            try:
                io_excel.write_result(
                    "q1", {n: pd.DataFrame(short) for n in io_excel.layout("q1").sheet_names}
                )
            except io_excel.ResultFormatError as e:
                assert "列结构不匹配" in str(e)
            else:
                raise AssertionError("列数不足未被拦下")

            sheets = export.result_sheets(_dummy(), problem_spec.Q1)
            sheets["水分浓度"].iloc[3, 1] = float("nan")
            try:
                io_excel.write_result("q1", sheets)
            except io_excel.ResultFormatError as e:
                assert "NaN" in str(e)
            else:
                raise AssertionError("NaN 未被拦下")
    finally:
        paths.RESULTS_DIR = saved


@check("合规工作表能正常写出，且能被读回")
def _():
    import tempfile
    from pathlib import Path

    from common import export

    saved = paths.RESULTS_DIR
    try:
        with tempfile.TemporaryDirectory() as d:
            paths.RESULTS_DIR = Path(d)
            dest = io_excel.write_result("q1", export.result_sheets(_dummy(), problem_spec.Q1))
            assert dest.exists()
            back = pd.read_excel(dest, sheet_name=None)
            assert set(back) == {"温度", "水分浓度"}
            assert back["水分浓度"].shape == (1801, 22)
    finally:
        paths.RESULTS_DIR = saved


# --- Solution 语义 ----------------------------------------------------------


@check("终点判据取 max_r（题目说「各处」），且达不到时抛错")
def _():
    sol = _dummy(n_t=19)
    assert sol.shape == (19, 21)
    assert sol.surface_index == 20
    assert abs(sol.first_time_below(0.15) - sol.t[-1]) < 1e-9
    try:
        sol.first_time_below(0.05)
    except ValueError as e:
        assert "从未低于" in str(e)
    else:
        raise AssertionError("达不到终点时应抛错，不许静默返回（铁律 10）")


@check("形状不一致的 Solution 会被拒绝")
def _():
    try:
        Solution(
            t=np.zeros(3), r=np.zeros(4), T=np.zeros((3, 4)), C=np.zeros((3, 5))
        )
    except ValueError as e:
        assert "形状不一致" in str(e)
    else:
        raise AssertionError("T/C 形状不一致未被拒绝")


# --- 骨架阶段的预期状态 -----------------------------------------------------


@check("物性公式与求解器均未实现（骨架阶段的预期状态）")
def _():
    for cls in (correlations.Appendix2, correlations.Appendix3, correlations.Appendix4):
        try:
            cls().rho(np.array([1.0]), np.array([300.0]))
        except NotImplementedError:
            pass
        else:
            raise AssertionError(f"{cls.__name__} 不应静默返回假数据（铁律 2）")

    for n in (1, 2, 3, 4):
        mod = __import__(f"q{n}.solver", fromlist=["solve"])
        try:
            mod.solve(problem_spec.get(f"q{n}"))
        except NotImplementedError:
            pass
        else:
            raise AssertionError(f"q{n} 求解器不应返回假结果")


@check("汽化潜热在出处未定前必须拒绝实现（铁律 2）")
def _():
    try:
        correlations.latent_heat_vaporization(np.array([300.0]))
    except NotImplementedError as e:
        assert "出处" in str(e)
    else:
        raise AssertionError("不应给出无出处的数值")


# --- 汇总 -------------------------------------------------------------------

print()
print("=" * 72)
if _FAILED:
    print(f"✗ {len(_FAILED)} 项失败，{_PASSED} 项通过")
    for name, err in _FAILED:
        print(f"    - {name}: {err}")
    print("=" * 72)
    sys.exit(1)

print(f"✓ 全部 {_PASSED} 项自检通过")
print("=" * 72)
