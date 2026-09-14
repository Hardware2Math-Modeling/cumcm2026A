"""results/  ->  paper/figs/*.pdf

运行： make figs

设计意图（AGENTS.md §2）：
    插图**从交付物本身**重绘，而不是从求解器的内存对象。
    这样「论文里的图和交付的 xlsx 一定一致」——如果两者对不上，说明有人手工改过 xlsx。

本脚本出两类图：
    1. 四问的通用图（`figures_for`）：温度/水分浓度的径向剖面与时间历程；
    2. 论文专用的补充图（`extra_figures`）：时空热力图、参数集对照、
       收缩与半径、灵敏度/收敛对照、物性缩放。
    第 2 类**只从 `results/`（交付 xlsx、展示 csv、validation/*.json）与
    `data/processed/`（题目附件解析结果）读取**，不读 `outputs/cache/`
    ——缓存可能来自早期设置（实测 `outputs/cache/q4.npz` 仍是 641 节点的旧运行）。

⚠️ 不要手工编辑 paper/figs/*.pdf，下次 make 就覆盖了。
"""

from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

from _bootstrap import setup
setup()

from common import io_excel, paths, plotting, units  # noqa: E402
from common.solution import Solution  # noqa: E402

#: 要出图的问题号。四问都要出，漏一个就会让对应论文小节引用到不存在的图。
PROBLEMS: tuple[int, ...] = (1, 2, 3, 4)


def load_solution(problem: str) -> Solution | None:
    """把 results/resultN.xlsx 读回成 Solution（SI 单位）。

    若交付物尚不存在则返回 None —— 框架阶段这是正常状态，不算失败。
    """
    path = paths.result_path(problem)
    if not path.exists():
        return None

    # 工作表名以模板实测为准（AGENTS.md 铁律 3）：result1/2 是「温度」+「水分浓度」，
    # result3/4 是 Sheet1。此处曾写死 io_excel.SHEET_MOISTURE，
    # 导致问题 3/4 永远被"跳过"、一张图都出不来。
    layout = io_excel.layout(problem)
    sheet_of = {field: name for name, field in layout.sheets}

    sheets = pd.read_excel(path, sheet_name=None)
    df_c = sheets.get(sheet_of.get("C"))
    if df_c is None:
        print(f"  !! {paths.rel(path)} 里没有「{sheet_of.get('C')}」工作表，跳过")
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
    r_cm = np.asarray(r_cm, dtype=float)

    # 问题 4 的固定物理位置会随失水收缩落到域外，导出层按 R(t) 掩码成 NaN
    # （AGENTS.md §5：域外留空）。有效时段过短的位置（如 1.9 cm：只在最初几分钟
    # 位于域内）画出来是一条近乎空的曲线，反而误导读者，故按覆盖率阈值剔除并报告。
    MIN_COVERAGE = 0.5
    coverage = np.mean(np.isfinite(C), axis=0)
    keep = [i for i in range(len(cols)) if coverage[i] >= MIN_COVERAGE]
    if not keep:
        print(f"  !! {paths.rel(path)} 的浓度列有效覆盖率全部低于 {MIN_COVERAGE:.0%}，跳过")
        return None
    if len(keep) != len(cols):
        dropped = [(cols[i], f"{coverage[i]:.0%}") for i in range(len(cols)) if i not in keep]
        print(f"    · 剔除有效时段过短的位置列 {dropped}（问题 4 收缩所致）")
        cols = [cols[i] for i in keep]
        r_cm = r_cm[keep]
        C = C[:, keep]

    r = units.cm_to_m(r_cm)

    t_sheet = sheet_of.get("T")
    df_t = sheets.get(t_sheet) if t_sheet else None
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
    for n in PROBLEMS:
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

    print()
    print("· 论文专用补充图：")
    for f in extra_figures():
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


# =============================================================
# 论文专用补充图
# =============================================================


def _json(rel: str) -> dict:
    return json.loads((paths.ROOT / rel).read_text(encoding="utf-8"))


def _ascii_log_ticks(ax) -> None:
    """把对数轴的刻度标签改成 ASCII 形式（如 1e-09）。

    matplotlib 默认用 Unicode 减号（U+2212）写 $10^{-9}$；中文字体常缺该字形，
    PDF 里会印成一个方块（实测 `fig-validation.pdf` 的 (b) 面板出现过）。
    这里显式指定刻度与标签，绕开字体缺字问题。
    """
    from matplotlib.ticker import FixedLocator, FuncFormatter

    lo, hi = ax.get_ylim()
    ticks = [t for t in np.logspace(np.floor(np.log10(lo)), np.ceil(np.log10(hi)),
                                    int(np.ceil(np.log10(hi)) - np.floor(np.log10(lo)) + 1))
             if lo <= t <= hi]
    if not ticks:
        return
    ax.yaxis.set_major_locator(FixedLocator(ticks))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _pos: f"{v:.0e}"))


def _moist_history_axes(ax, problem: str, locations_cm, *, scale: str = "linear") -> None:
    """从交付 xlsx 画若干位置的含水率历程（不读求解器缓存）。"""
    sol = load_solution(problem)
    if sol is None:
        raise FileNotFoundError(f"results/result{problem[-1]}.xlsx 不存在")
    t_h = units.s_to_h(sol.t)
    r_cm = units.m_to_cm(sol.r)
    for target in locations_cm:
        i = int(np.argmin(np.abs(r_cm - target)))
        if abs(r_cm[i] - target) > 0.05:
            continue
        ax.plot(t_h, sol.C[:, i], label=f"$r$ = {r_cm[i]:.1f} cm")
    ax.set_xlabel("时间 / h")
    ax.set_ylabel("水分浓度 / (kg/kg，干基)")
    ax.set_yscale(scale)
    ax.legend(fontsize=8)


def fig_property_scaling() -> str:
    """三套物性随含水率/温度的变化（说明"变物性"到底变多少）。"""
    import matplotlib.pyplot as plt

    C = np.linspace(0.05, 2.55, 400)
    w = C / (1.0 + C)
    T = np.linspace(301.15, 323.315, 400)

    rho2, cp2, k2 = np.full_like(C, 820.0), np.full_like(C, 2600.0), np.full_like(C, 0.36)
    rho3, cp3, k3 = 650 + 128 * C, 1450 + 2736 * w, 0.21 + 0.38 * w
    rho4, cp4, k4 = 760 + 90 * C, 1850 + 2150 * w, 0.12 + 0.20 * w
    D2 = 7e-9 * np.exp(-0.89 / C)
    D3 = 2.4e-3 * np.exp(-0.45 / C[:, None] - 3850 / T[None, :])
    D4 = 4.2e-4 * np.exp(-0.30 / C[:, None] - 3850 / T[None, :])

    fig, axes = plt.subplots(2, 2, figsize=(7.6, 5.2))
    ax = axes[0, 0]
    ax.plot(C, rho2, "--", label="附录 2")
    ax.plot(C, rho3, label="附录 3")
    ax.plot(C, rho4, label="附录 4")
    ax.set_xlabel("水分浓度 $C$ / (kg/kg)")
    ax.set_ylabel(r"$\rho$ / (kg/m$^3$)")
    ax.legend(fontsize=8)

    ax = axes[0, 1]
    ax.plot(C, cp2, "--", label="附录 2")
    ax.plot(C, cp3, label="附录 3")
    ax.plot(C, cp4, label="附录 4")
    ax.set_xlabel("水分浓度 $C$ / (kg/kg)")
    ax.set_ylabel(r"$c_p$ / (J/(kg$\cdot$K))")
    ax.legend(fontsize=8)

    ax = axes[1, 0]
    ax.semilogy(C, D2, "--", label="附录 2（仅含 $C$）")
    ax.semilogy(C, D3[:, 0], label="附录 3（$T$=28 °C）")
    ax.semilogy(C, D3[:, -1], ":", label="附录 3（$T$=50.2 °C）")
    ax.semilogy(C, D4[:, -1], "-.", label="附录 4（$T$=50.2 °C）")
    ax.set_xlabel("水分浓度 $C$ / (kg/kg)")
    ax.set_ylabel("$D$ / (m$^2$/s)")
    ax.legend(fontsize=8)
    _ascii_log_ticks(ax)

    ax = axes[1, 1]
    for Cv, style in ((2.55, "-"), (0.5, "--"), (0.15, ":")):
        ax.semilogy(T, 2.4e-3 * np.exp(-0.45 / Cv - 3850 / T), style,
                    label=f"附录 3，$C$={Cv}")
    ax.set_xlabel("温度 $T$ / K")
    ax.set_ylabel("$D$ / (m$^2$/s)")
    ax.legend(fontsize=8)
    _ascii_log_ticks(ax)

    fig.suptitle("三套物性参数集的量级与变化幅度")
    fig.tight_layout()
    return str(plotting._save(fig, "fig-prop-scaling"))


def fig_moist_2d() -> str:
    """问题 3 的水分浓度时空分布（等值线 + 填色）。"""
    import matplotlib.pyplot as plt

    sol = load_solution("q3")
    t_h = units.s_to_h(sol.t)
    r_cm = units.m_to_cm(sol.r)
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    tt, rr = np.meshgrid(t_h, r_cm, indexing="ij")
    levels = np.linspace(0.0, 2.6, 27)
    cf = ax.contourf(tt, rr, sol.C, levels=levels, cmap="viridis")
    cs = ax.contour(tt, rr, sol.C, levels=[0.15, 0.3, 0.6, 1.0, 1.5, 2.0, 2.5],
                    colors="w", linewidths=0.6)
    ax.clabel(cs, fmt="%.2f", fontsize=7, colors="w")
    ax.axvline(t_h[-1], color="r", ls="--", lw=1.2)
    ax.text(t_h[-1], r_cm[-1] * 0.55, f" 烘干结束 {t_h[-1]:.2f} h",
            color="r", fontsize=8, rotation=90, va="center")
    ax.set_xlabel("时间 / h")
    ax.set_ylabel("到药材中心的距离 / cm")
    ax.set_title("问题 3：水分浓度的时空分布（等值线标注值为 kg/kg）")
    fig.colorbar(cf, ax=ax, label="水分浓度 / (kg/kg，干基)")
    fig.tight_layout()
    return str(plotting._save(fig, "fig-moist-2d"))


def fig_param_comparison() -> str:
    """附录 3 与附录 4 在同一固定半径下的干燥快慢对照。

    曲线只用交付物（result2.xlsx = 附录 3 固定半径；结果文件即可，
    附录 4 固定半径的对照算例没有交付文件），故本图只画**有交付物支撑的曲线**，
    附录 4 固定半径的终点以竖线 + 文本标注（数值来自
    results/validation/numerics.json 的 fixed_radius_control）。
    """
    import matplotlib.pyplot as plt

    report = _json("results/validation/numerics.json")
    fixed = next(x for x in report["fixed_radius_control"] if x["q"] == "q4")
    q3 = _json("results/q3_summary.json")
    q4 = _json("results/q4_summary.json")

    fig, ax = plt.subplots(figsize=(6.6, 4.2))
    _moist_history_axes(ax, "q3", (0.0, 1.0, 2.0))
    ax.set_title("固定半径下附录 3（问题 2、3）的水分浓度历程")
    ax.axvline(q3["event_time_s"] / 3600.0, color="k", ls="--", lw=1.2)
    ax.annotate(f"问题 3 终点 {q3['event_time_s'] / 3600.0:.2f} h",
                xy=(q3["event_time_s"] / 3600.0, 2.2),
                xytext=(q3["event_time_s"] / 3600.0 - 14, 2.3),
                fontsize=8, color="k")
    ax.annotate(f"附录 4 固定半径对照终点 {fixed['event_h']:.2f} h\n"
                f"（$N_r$={fixed['n']}，无数值交付文件，只标终点）",
                xy=(fixed["event_h"], 1.0), xytext=(fixed["event_h"] - 40, 1.35),
                fontsize=8, color="tab:red",
                arrowprops=dict(arrowstyle="->", color="tab:red", lw=1.0))
    ax.axvline(fixed["event_h"], color="tab:red", ls=":", lw=1.2)
    ax.axvline(q4["event_time_s"] / 3600.0, color="tab:green", ls="-.", lw=1.2)
    ax.annotate(f"问题 4（收缩）终点 {q4['event_time_s'] / 3600.0:.2f} h",
                xy=(q4["event_time_s"] / 3600.0, 0.4),
                xytext=(q4["event_time_s"] / 3600.0 + 4, 0.75),
                fontsize=8, color="tab:green")
    ax.set_xlim(0, 135)
    fig.tight_layout()
    return str(plotting._save(fig, "fig-param-comparison"))


def fig_q4_shrink() -> str:
    """附件 2 的半径收缩 $R(t)$、表面位置与表面含水率。"""
    import matplotlib.pyplot as plt

    rad = pd.read_csv(paths.ROOT / "data" / "processed" / "radius.csv")
    sol = load_solution("q4")
    q4 = _json("results/q4_summary.json")
    t_end_h = q4["event_time_s"] / 3600.0

    fig, ax = plt.subplots(figsize=(6.6, 4.0))
    ax.plot(rad["t_s"] / 3600.0, rad["R_m"] * 100, "o-", ms=2.4,
            label="附件 2 实测半径 $R(t)$")
    ax.axhline(2.0, color="gray", ls=":", lw=1.0)
    ax.text(0.5, 2.01, "初始半径 2.0000 cm", fontsize=8, color="gray")
    ax.axvline(t_end_h, color="tab:red", ls="--", lw=1.2)
    ax.plot([t_end_h], [q4["event_R"] * 100], "r*", ms=11)
    ax.annotate(f"烘干结束 {t_end_h:.2f} h\n$R$ = {q4['event_R'] * 100:.4f} cm",
                xy=(t_end_h, q4["event_R"] * 100),
                xytext=(t_end_h + 2, 1.45), fontsize=8, color="tab:red")
    ax.set_xlabel("时间 / h")
    ax.set_ylabel("药材半径 $R$ / cm")
    ax.set_title("失水收缩引起的半径变化与烘干结束时刻")
    ax.legend(fontsize=8)
    ax.set_xlim(0, 72)
    fig.tight_layout()
    return str(plotting._save(fig, "fig-q4-shrink"))


def fig_validation_and_sensitivity() -> str:
    """（a）网格收敛；（b）BDF 与 Radau 的差异；（c）环境外推灵敏度。"""
    import matplotlib.pyplot as plt

    acc = _json("results/validation/accuracy.json")
    acc4 = _json("results/validation/accuracy-q4.json")
    report = _json("results/validation/numerics.json")

    fig, axes = plt.subplots(1, 3, figsize=(11.4, 3.6))

    ax = axes[0]
    for key, label, marker in (("q1", "问题 1（温度）", "o"),
                               ("q3", "问题 2、3（温度）", "s"),
                               ("q4", "问题 4（温度）", "^")):
        entries = [e for e in acc["grid"] if e["q"] == key] if key != "q4" else acc4["grid"]
        n = [e["n"] for e in entries if e.get("delta_T_K")]
        d = [e["delta_T_K"] for e in entries if e.get("delta_T_K")]
        if n:
            ax.loglog(n, d, marker + "-", label=label)
    ref_n = np.array([1281.0, 5121.0])
    ax.loglog(ref_n, 5e-6 * (ref_n / 1281.0) ** -2, "k--", lw=0.9,
              label="二阶参考斜率")
    ax.set_xlabel("节点数 $N_r$")
    ax.set_ylabel("相邻网格最大温差 / K")
    ax.set_title("(a) 空间网格收敛")
    ax.legend(fontsize=7)
    _ascii_log_ticks(ax)

    ax = axes[1]
    cross = [(e["q"], e["delta_T_K"], e["delta_C"]) for e in acc["cross_solver"]]
    c4 = acc4["cross_solver"]
    cross.append(("q4", c4["delta_T_K"], c4["delta_C"]))
    name = {"q1": "问题 1", "q3": "问题 2、3", "q4": "问题 4"}
    x = np.arange(len(cross))
    ax.bar(x - 0.2, [c[1] for c in cross], width=0.4, label="最大温差 / K")
    ax.bar(x + 0.2, [c[2] for c in cross], width=0.4,
           label="最大含水率差 / (kg/kg)")
    ax.set_yscale("log")
    ax.set_xticks(x)
    ax.set_xticklabels([name[c[0]] for c in cross], fontsize=8)
    ax.set_title("(b) BDF 与 Radau IIA 之差（$N_r$=161）")
    _ascii_log_ticks(ax)
    ax.legend(fontsize=7)

    ax = axes[2]
    by_case = {(s["q"], s["case"]): s for s in report["sensitivity"]}
    cases = ["last_hour_T_min", "last_hour_T_max", "last_hour_C_min",
             "last_hour_C_max"]
    short = ["$T_\\infty$ 最低", "$T_\\infty$ 最高", "$C_\\infty$ 最低",
             "$C_\\infty$ 最高"]
    delta = [by_case[("q3", c)]["delta_h"] for c in cases]
    colors = ["tab:red" if d > 0 else "tab:blue" for d in delta]
    ax.barh(np.arange(len(cases)), delta, color=colors)
    ax.axvline(0, color="k", lw=1.0)
    ax.set_yticks(np.arange(len(cases)))
    ax.set_yticklabels(short, fontsize=8)
    ax.set_xlabel("问题 2、3 终点时刻变化 / h")
    ax.set_title("(c) 4 h 后环境外推的灵敏度")
    ax.invert_yaxis()

    fig.tight_layout()
    return str(plotting._save(fig, "fig-validation"))


#: 需要交付物才能画、且与问题号无关的补充图
def extra_figures() -> list[str]:
    made: list[str] = []
    builders = (
        ("fig-prop-scaling", fig_property_scaling),
        ("fig-moist-2d", fig_moist_2d),
        ("fig-param-comparison", fig_param_comparison),
        ("fig-q4-shrink", fig_q4_shrink),
        ("fig-validation", fig_validation_and_sensitivity),
    )
    for name, build in builders:
        try:
            made.append(build())
        except FileNotFoundError as e:
            print(f"    !! {name}: 缺少输入（{e}），跳过")
    return made


if __name__ == "__main__":
    raise SystemExit(main())
