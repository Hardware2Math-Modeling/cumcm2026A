"""框架级冒烟测试。

这些测试验证的是**框架本身是通的**：路径、单位、数据读取、格式校验。
**不涉及任何物理求解** —— 求解器的测试由 @impl 在实现后补（见 docs/OWNERS.md §2）。

跑法： make check   （或 make test-fast）
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from common import io_excel, paths, problem_spec, units
from common.solution import Solution


# --- 路径 -------------------------------------------------------------------


def test_root_is_repo_root():
    assert (paths.ROOT / "AGENTS.md").exists(), "ROOT 定位错误"
    assert (paths.ROOT / "problem" / "A题.pdf").exists(), "题目原件缺失"


def test_template_and_result_paths():
    assert paths.template_path("q1").name == "result1.xlsx"
    assert paths.template_path("result3").name == "result3.xlsx"
    assert paths.result_path("4").name == "result4.xlsx"
    with pytest.raises(ValueError):
        paths.template_path("q9")


def test_rel_is_relative():
    assert paths.rel(paths.ROOT / "AGENTS.md") == "AGENTS.md"


# --- 单位 -------------------------------------------------------------------


def test_unit_roundtrip():
    assert units.m_to_cm(units.cm_to_m(2.0)) == pytest.approx(2.0)
    assert units.k_to_c(units.c_to_k(28.0)) == pytest.approx(28.0)
    assert units.h_to_s(1.0) == pytest.approx(3600.0)
    assert units.c_to_k(28.0) == pytest.approx(301.15)


def test_unit_conversion_on_arrays():
    arr = units.cm_to_m(np.array([0.0, 0.5, 2.0]))
    assert arr.shape == (3,)
    assert arr[2] == pytest.approx(0.02)


def test_assert_kelvin_rejects_celsius():
    """把摄氏度当开尔文传是本题最危险的错误，必须有防呆。"""
    with pytest.raises(ValueError, match="摄氏度"):
        units.assert_kelvin(np.array([28.0, 50.0]))
    units.assert_kelvin(np.array([301.15, 323.15]))  # 不抛


def test_assert_kelvin_rejects_nan():
    with pytest.raises(ValueError, match="NaN"):
        units.assert_kelvin(np.array([300.0, np.nan]))


def test_wet_basis():
    from common.correlations import wet_basis

    assert wet_basis(0.0) == pytest.approx(0.0)
    assert wet_basis(1.0) == pytest.approx(0.5)
    assert wet_basis(2.55) == pytest.approx(2.55 / 3.55)


# --- 题目常量 ---------------------------------------------------------------


def test_spec_constants_match_problem():
    """题目给定量必须与 problem/A题.pdf 一致。改动这里请先核对题目。"""
    assert problem_spec.LENGTH_M == pytest.approx(0.25)
    assert problem_spec.RADIUS0_M == pytest.approx(0.02)
    assert problem_spec.INITIAL_T_C == pytest.approx(28.0)
    assert problem_spec.INITIAL_C_DRY == pytest.approx(2.55)
    assert problem_spec.TARGET_C_DRY == pytest.approx(0.15)
    assert problem_spec.Q1_T_END_S == pytest.approx(1800.0)


def test_geometry_aspect_ratio():
    g = problem_spec.Geometry()
    assert g.aspect_ratio == pytest.approx(25.0 / 4.0)


def test_geometry_rejects_short_cylinder():
    """长径比过小意味着一维径向简化（D-007）不成立，应拒绝。"""
    with pytest.raises(ValueError, match="长径比"):
        problem_spec.Geometry(length=0.05, radius0=0.02)


def test_all_specs_defined_and_consistent():
    assert set(problem_spec.ALL) == {"q1", "q2", "q3", "q4"}
    for spec in problem_spec.ALL.values():
        n_t, n_r = spec.grid.shape
        assert n_t > 1 and n_r > 1
        assert spec.grid.r[0] == 0.0, "交付网格必须包含轴心 r=0"
        assert spec.grid.r[-1] == pytest.approx(spec.geometry.radius0)


def test_spec_property_sets_do_not_mix():
    """附录 2/3/4 不可混用（AGENTS.md §4.3）。"""
    assert problem_spec.Q1.properties.appendix == 2
    assert problem_spec.Q2.properties.appendix == 3
    assert problem_spec.Q3.properties.appendix == 3
    assert problem_spec.Q4.properties.appendix == 4
    assert problem_spec.Q1.uses_shrinkage is False
    assert problem_spec.Q4.uses_shrinkage is True


def test_q1_grid_matches_delivery_requirement():
    """问题 1：交付 0~1800 s 每隔 1 s、0~2 cm 每隔 0.1 cm。"""
    g = problem_spec.Q1.grid
    assert g.shape == (1801, 21)


# --- 附件读取 ---------------------------------------------------------------


def test_read_attachment1_structure():
    df = io_excel.read_attachment(1)
    assert list(df.columns) == ["时间", "温度", "水分浓度"]
    assert len(df) == 241
    t = df["时间"].to_numpy(dtype=float)
    assert t[0] == 0.0
    assert t[-1] == pytest.approx(14400.0)
    assert np.allclose(np.diff(t), 60.0)


def test_read_attachment2_structure():
    df = io_excel.read_attachment(2)
    assert list(df.columns) == ["时间", "半径"]
    assert len(df) == 145
    t = df["时间"].to_numpy(dtype=float)
    assert t[-1] == pytest.approx(259200.0)
    r = df["半径"].to_numpy(dtype=float)
    assert r[0] == pytest.approx(2.0)
    assert np.all(np.diff(r) <= 0), "半径应单调不增"


def test_ambient_and_herb_concentration_magnitudes_differ():
    """D-011：烘房水分浓度与药材初始值差一个数量级以上，基准问题必须论证。"""
    df = io_excel.read_attachment(1)
    assert df["水分浓度"].max() < problem_spec.INITIAL_C_DRY / 10


def test_ambient_coverage_is_shorter_than_process():
    """D-009：附件 1 只覆盖 4 h，而烘干过程 72 h，存在信息缺口。"""
    df = io_excel.read_attachment(1)
    assert df["时间"].max() == pytest.approx(problem_spec.AMBIENT_COVERAGE_S)
    assert problem_spec.AMBIENT_COVERAGE_S < problem_spec.RADIUS_COVERAGE_S


def test_radius_plateaus_at_end():
    """D-010：附件 2 末段半径出现平台，需在建模时解释。"""
    df = io_excel.read_attachment(2)
    r = df["半径"].to_numpy(dtype=float)
    assert r[-1] == pytest.approx(r[-2])


# --- 交付模板与格式校验 -----------------------------------------------------


@pytest.mark.parametrize("problem", ["q1", "q2", "q3", "q4"])
def test_layout_matches_real_template(problem):
    """实测布局必须与 problem/附件/附件3 的真实模板一致。

    这是**防止赛方更新模板而我们没跟上**的守门测试。
    失败时跑 `make probe` 看差异，然后更新 io_excel.LAYOUTS 的实测结论。
    """
    mism = io_excel.verify_layout_against_template(problem)
    assert not mism, "布局与模板不一致：\n  - " + "\n  - ".join(mism)


def test_template_sheet_names_are_as_measured():
    """result1/2 是 温度+水分浓度；result3/4 的工作表名是 Sheet1（实测，不是猜的）。"""
    assert set(io_excel.layout("q1").sheet_names) == {"温度", "水分浓度"}
    assert set(io_excel.layout("q2").sheet_names) == {"温度", "水分浓度"}
    assert set(io_excel.layout("q3").sheet_names) == {"Sheet1"}
    assert set(io_excel.layout("q4").sheet_names) == {"Sheet1"}


def test_result3_and_4_have_no_temperature_sheet():
    """result3/4 只有水分浓度 —— 多写一个温度表会被校验拦下。"""
    assert all(f == "C" for _, f in io_excel.layout("q3").sheets)
    assert all(f == "C" for _, f in io_excel.layout("q4").sheets)


def test_distance_columns_are_full_01cm_grid():
    """模板里的 0, 0.1, 0.2, …, 2 是示意（'…' 是省略），实际应为 21 列。"""
    heads = io_excel.layout("q1").distance_headers()
    assert len(heads) == 21
    assert heads[0] == "0"
    assert heads[1] == "0.1"
    assert heads[-1] == "2"


def test_result4_last_column_is_surface_text():
    """问题 4 的末列是文字「药材表面」，不是数值 2。"""
    heads = io_excel.layout("q4").distance_headers()
    assert heads[-1] == io_excel.SURFACE_HEADER
    assert heads[-2] == "1.9"


def test_delivery_time_unit_is_seconds():
    """实测：模板 A 列数据是 1 或 60（秒），**不是**题目表 3~表 6 表头写的 h。"""
    assert io_excel.layout("q1").dt_s == 1.0
    assert io_excel.layout("q2").dt_s == 1.0
    assert io_excel.layout("q3").dt_s == 60.0
    assert io_excel.layout("q4").dt_s == 60.0


def test_result_sheets_columns_match_layout():
    """export 生成的工作表列结构必须与布局一致，否则写出去会被校验拦下。"""
    from common import export

    sol = _dummy_solution(n_t=1801)
    sheets = export.result_sheets(sol, problem_spec.Q1)
    for name, df in sheets.items():
        assert list(df.columns) == io_excel.layout("q1").expected_columns(), name
    assert sheets["水分浓度"].shape == (1801, 22)  # 1 列时间 + 21 列距离


def test_result_sheets_q4_surface_column():
    from common import export

    sol = _dummy_solution(n_t=101, radius=problem_spec.RADIUS0_M)
    sheets = export.result_sheets(sol, problem_spec.Q4)
    df = sheets["Sheet1"]
    assert list(df.columns) == io_excel.layout("q4").expected_columns()
    assert io_excel.SURFACE_HEADER in df.columns


def test_write_result_rejects_wrong_sheet_names(tmp_path, monkeypatch):
    """格式校验必须是硬失败，不能静默写出错误交付物（AGENTS.md 铁律 3）。"""
    import pandas as pd

    monkeypatch.setattr(paths, "RESULTS_DIR", tmp_path)
    with pytest.raises(io_excel.ResultFormatError, match="工作表名不匹配"):
        io_excel.write_result("q1", {"错的表名": pd.DataFrame({io_excel.TIME_HEADER: [1.0]})})


def test_write_result_rejects_wrong_column_count(tmp_path, monkeypatch):
    """模板只有 4 个距离列是示意；实际必须写满 21 列，少写要报错。"""
    import pandas as pd

    monkeypatch.setattr(paths, "RESULTS_DIR", tmp_path)
    short = {io_excel.TIME_HEADER: [1.0, 2.0]}
    for h in ["0", "0.1", "0.2", "2"]:
        short[h] = [0.0, 0.0]
    sheets = {n: pd.DataFrame(short) for n in io_excel.layout("q1").sheet_names}
    with pytest.raises(io_excel.ResultFormatError, match="列结构不匹配"):
        io_excel.write_result("q1", sheets)


def test_write_result_rejects_nan(tmp_path, monkeypatch):
    from common import export

    monkeypatch.setattr(paths, "RESULTS_DIR", tmp_path)
    sol = _dummy_solution(n_t=1801)
    sheets = export.result_sheets(sol, problem_spec.Q1)
    sheets["水分浓度"].iloc[3, 1] = float("nan")
    with pytest.raises(io_excel.ResultFormatError, match="NaN"):
        io_excel.write_result("q1", sheets)


def test_write_result_accepts_valid_sheets(tmp_path, monkeypatch):
    """正例：合规的工作表应能写出，且文件真实存在。"""
    from common import export

    monkeypatch.setattr(paths, "RESULTS_DIR", tmp_path)
    sol = _dummy_solution(n_t=1801)
    dest = io_excel.write_result("q1", export.result_sheets(sol, problem_spec.Q1))
    assert dest.exists()
    back = pd.read_excel(dest, sheet_name=None)
    assert set(back) == {"温度", "水分浓度"}
    assert back["水分浓度"].shape == (1801, 22)


def test_write_result_rejects_uneven_time_step(tmp_path, monkeypatch):
    from common import export

    monkeypatch.setattr(paths, "RESULTS_DIR", tmp_path)
    sol = _dummy_solution(n_t=1801)
    t = sol.t.copy()
    t[5] += 0.5
    sol.t = t
    with pytest.raises(io_excel.ResultFormatError, match="时间步长"):
        io_excel.write_result("q1", export.result_sheets(sol, problem_spec.Q1))


# --- Solution ---------------------------------------------------------------


def _dummy_solution(
    t_end_s: float = 1800.0,
    n_t: int = 19,
    n_r: int = 21,
    radius: float = problem_spec.RADIUS0_M,
) -> Solution:
    t = np.linspace(0.0, t_end_s, n_t)
    r = np.linspace(0.0, radius, n_r)
    T = np.full((n_t, n_r), 300.0)
    C = np.linspace(2.55, 0.10, n_t)[:, None] * np.ones((1, n_r))
    return Solution(t=t, r=r, T=T, C=C)


def test_solution_shape_validation():
    with pytest.raises(ValueError, match="形状不一致"):
        Solution(
            t=np.zeros(3),
            r=np.zeros(4),
            T=np.zeros((3, 4)),
            C=np.zeros((3, 5)),
        )


def test_solution_first_time_below_uses_max_over_r():
    """终点判据取 max_r C（题目说"各处"），不是平均值。"""
    sol = _dummy_solution()
    t_hit = sol.first_time_below(0.15)
    assert t_hit == pytest.approx(sol.t[-1])


def test_solution_first_time_below_raises_when_never_reached():
    """达不到终点时必须报错，不许静默返回（AGENTS.md 铁律 10）。"""
    sol = _dummy_solution()
    with pytest.raises(ValueError, match="从未低于"):
        sol.first_time_below(0.05)


def test_solution_table_grid_is_21_by_21_for_q1():
    sol = _dummy_solution(n_t=1801)
    assert sol.shape == (1801, 21)
    assert sol.surface_index == 20


# --- 未实现的东西必须显式失败 -----------------------------------------------


def test_property_sets_match_appendices():
    """原题三套密度关系，独立点值核验。"""
    from common import correlations

    for cls, expected in zip((correlations.Appendix2, correlations.Appendix3,
                             correlations.Appendix4),(820,778,850)):
        ps = cls()
        assert ps.rho(1.0,300.0) == pytest.approx(expected)


def test_solvers_have_callable_entrypoints():
    """数值验证在test_numerics.py，框架只检查入口。"""
    for n in (1, 2, 3, 4):
        mod = __import__(f"q{n}.solver", fromlist=["solve"])
        assert callable(mod.solve)


def test_latent_heat_requires_sourced_value():
    """汽化潜热题目未给出，出处未定前不许实现（AGENTS.md 铁律 2）。"""
    from common import correlations

    with pytest.raises(NotImplementedError, match="出处"):
        correlations.latent_heat_vaporization(np.array([300.0]))
