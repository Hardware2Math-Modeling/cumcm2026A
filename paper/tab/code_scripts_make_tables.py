"""results/  ->  paper/tab/*.tex（booktabs 三线表片段 + 数值宏）

运行： make tables

设计意图（AGENTS.md §2）：
    论文里的表 1~表 6 **不允许手抄数字**。数字永远只有一处来源 —— results/。
    论文用 \\geninput{tab/tabN}{...} 引入本脚本生成的片段。

本脚本生成五类产物：

1. 题目指定的表 1~表 6（q1_temp/q1_moist/q2_temp/q2_moist/q3_moist/q4_moist）
   —— 表 1/表 2 直接从 `results/result1.xlsx` 选题目指定的 7 个时刻 × 5 个位置；
      表 3~表 6 由 `results/tables/*.csv`（`scripts/_runner.py` 输出的展示网格）转换。
2. 符号表 `notation.tex`（**符号 / 说明 / 单位 三列**，从 `docs/NOTATION.md` 解析）。
3. 数值宏 `q1_values.tex`（第一问，历史文件名，main.tex 用 \\qonevalues 引入）
   与 `problem_values.tex` / `accuracy_values.tex`（第二~四问与验证数字）。
4. 验证与对照表：`validation_grid.tex`（四问网格收敛）、`validation_time.tex`
   （时间精度交叉验证）、`sensitivity.tex`（4 h 后环境外推灵敏度）、
   `ambient_stats.tex`（附件 1 末小时统计）、`property_sets.tex`（三套物性公式）。
5. 保存/换算说明表 `symbol_units_note` 不单独出表，单位写进符号表第三列。

⚠️ 不要手工编辑 paper/tab/*.tex，下次 make 就覆盖了。
   格式不对请提需求改本脚本（@impl 所有）。
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd

from _bootstrap import setup

setup()

from common import paths  # noqa: E402


# =============================================================
# 基础工具
# =============================================================


def _fmt(v: float) -> str:
    """保留四位小数（题目要求）。NaN 输出为空。"""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return str(v)
    if f != f:  # NaN
        return ""
    return f"{f:.4f}"


def _sci(v: float, digits: int = 2) -> str:
    """科学计数法（误差列专用）。"""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return str(v)
    if f != f:
        return "--"
    return f"{f:.{digits}e}"


def _num_columns(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if c != df.columns[0]]


def to_booktabs(
    df: pd.DataFrame,
    caption: str,
    label: str,
    *,
    formats: list | None = None,
    size: str | None = None,
    resize: float | None = None,
    note: str | None = None,
) -> str:
    """生成一个 booktabs 三线表片段（无竖线，符合数模论文规范）。

    Parameters
    ----------
    formats : 每列的格式化函数（长度 = 列数）；缺省用 ``_fmt``（四位小数）。
    size    : 字号命令，如 ``"\\\\small"``。
    resize  : 若给定，用 ``\\\\resizebox`` 压到该比例的 ``\\\\linewidth``。
    note    : 表下注释（如"共 3433 行，此处每隔 6 h 摘录"）。
    """
    head, *body = df.columns.tolist()
    ncols = len(df.columns)
    fmts = formats or [_fmt] * ncols
    if len(fmts) != ncols:
        raise ValueError(f"formats 长度 {len(fmts)} 与列数 {ncols} 不符")

    def cell(value, fmt) -> str:
        s = str(fmt(value))
        # 科学计数法里的 "e-05" 在表格中读起来别扭，统一成 LaTeX 数学写法
        return re.sub(r"([0-9.]+)e([+-]?)([0-9]+)", r"$\1\\times10^{\2\3}$", s)

    lines = [
        "% 本文件由 scripts/make_tables.py 自动生成，请勿手工编辑",
        "\\begin{table}[htbp]",
        "  \\centering",
        f"  \\caption{{{caption}}}",
        f"  \\label{{{label}}}",
    ]
    if size:
        lines.append(f"  {size}")
    if resize:
        lines.append(f"  \\resizebox{{{resize}\\linewidth}}{{!}}{{%")
    inner = "    " if resize else "  "
    lines += [
        f"{inner}\\begin{{tabular}}{{{'c' * ncols}}}",
        f"{inner}  \\toprule",
        f"{inner}  {head} & " + " & ".join(str(c) for c in body) + " \\\\",
        f"{inner}  \\midrule",
    ]
    for _, row in df.iterrows():
        cells = [cell(row[head], fmts[0])] + [
            cell(row[c], fmts[i + 1]) for i, c in enumerate(body)
        ]
        lines.append(f"{inner}  " + " & ".join(cells) + " \\\\")
    lines += [
        f"{inner}  \\bottomrule",
        f"{inner}\\end{{tabular}}",
    ]
    if resize:
        lines.append("  }")
    if note:
        lines.append(f"  \\par\\smallskip\\footnotesize {note}")
    lines += ["\\end{table}", ""]
    return "\n".join(lines)


def _write_tex(name: str, text: str) -> Path:
    paths.TABLES_DIR.mkdir(parents=True, exist_ok=True)
    dest = paths.TABLES_DIR / f"{name}.tex"
    dest.write_text(text, encoding="utf-8")
    return dest


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


#: 交付文件（尤其 result2.xlsx，27 MB / 20.6 万行）读一次就要几十秒，
#: 而正文要取它多个时刻的多个位置 —— 必须缓存，否则同一文件被反复全量解析。
_SHEET_CACHE: dict[str, pd.DataFrame] = {}


def _delivery_sheet(problem: str) -> pd.DataFrame:
    """读交付文件里含水分浓度的那张工作表，索引为时间。只读一次。"""
    if problem in _SHEET_CACHE:
        return _SHEET_CACHE[problem]

    path = paths.result_path(problem)
    from common import io_excel  # noqa: PLC0415  （延迟导入，避免 bootstrap 顺序问题）

    layout = io_excel.layout(problem)
    sheet = next(name for name, field in layout.sheets if field == "C")
    frame = pd.read_excel(path, sheet_name=sheet)
    frame = frame.set_index(frame.columns[0])
    frame.columns = [str(c) for c in frame.columns]
    _SHEET_CACHE[problem] = frame
    return frame


def _state(problem: str, t_s: float, column: str) -> float:
    """交付文件里 (时刻, 位置) 的水分浓度。时刻必须恰好落在交付行上。"""
    frame = _delivery_sheet(problem)
    if t_s not in frame.index:
        raise KeyError(f"{problem} 交付文件没有 t={t_s} s 这一行")
    return float(frame.loc[t_s, column])


# =============================================================
# 表 1~表 6：题目指定的展示网格
# =============================================================

#: csv 文件名 -> (论文表标题, 标签)。表号由论文正文引用决定，这里给的是默认值。
TABLES: dict[str, tuple[str, str]] = {
    "q1_temp": ("30 分钟内药材的温度", "tab:q1-temperature"),
    "q1_moist": ("30 分钟内药材的水分浓度", "tab:q1-moisture"),
    "q2_temp": ("3 小时内药材的温度", "tab:q2-temperature"),
    "q2_moist": ("3 小时内药材的水分浓度", "tab:q2-moisture"),
    "q3_moist": ("药材烘干过程的水分浓度", "tab:q3-moisture"),
    "q4_moist": ("考虑收缩的药材烘干过程的水分浓度", "tab:q4-moisture"),
}

#: csv 名 -> 时间列单位。题目表 1/表 2 用秒，表 3~表 6 用小时。
TIME_UNIT: dict[str, str] = {
    "q1_temp": "s",
    "q1_moist": "s",
    "q2_temp": "h",
    "q2_moist": "h",
    "q3_moist": "h",
    "q4_moist": "h",
}

#: csv 名 -> 表内数值单位。
VALUE_UNIT: dict[str, str] = {
    "q1_temp": "°C",
    "q2_temp": "°C",
    "q1_moist": "kg/kg",
    "q2_moist": "kg/kg",
    "q3_moist": "kg/kg",
    "q4_moist": "kg/kg",
}


def tables_from_csvs(skip: set[str] | None = None) -> int:
    """把 results/tables/*.csv 逐个转成 paper/tab/*.tex，返回生成个数。"""
    skip = skip or set()
    src_dir = paths.RESULTS_TABLES
    csvs = sorted(src_dir.glob("*.csv")) if src_dir.exists() else []
    if not csvs:
        print(f"⚠️ {paths.rel(src_dir)} 下没有 csv。先跑 make q1..q4。")
        return 0

    made = 0
    for csv in csvs:
        if csv.stem in skip:
            continue
        df = pd.read_csv(csv)
        df = df.rename(columns={df.columns[0]: f"时间/{TIME_UNIT.get(csv.stem, 's')}"})
        caption, label = TABLES.get(csv.stem, (csv.stem, f"tab:{csv.stem}"))
        if csv.stem in VALUE_UNIT:
            caption = f"{caption}（{VALUE_UNIT[csv.stem]}；距离单位：cm）"
        note = None
        if csv.stem in {"q3_moist", "q4_moist"}:
            note = ("表中最后一行为烘干结束时刻；"
                    "问题 4 的末列为该时刻的药材表面位置，"
                    "固定位置落在当时药材之外时留空。")
        text = to_booktabs(df, caption, label, note=note)
        _write_tex(csv.stem, text)
        print(f"  {paths.rel(csv)}  ->  paper/tab/{csv.stem}.tex  "
              f"({df.shape[0]} 行 x {df.shape[1]} 列)")
        made += 1
    return made


# =============================================================
# 符号表（三列：符号 / 说明 / 单位）
# =============================================================

#: 论文符号表的**行序**。符号的真源是 `docs/NOTATION.md`（铁律 9），
#: 但该文件是"三层映射表"（论文符号 / LaTeX 宏 / Python 变量）的形式，
#: 论文需要的是"符号 / 说明 / 单位"。故此处只登记**顺序**与**单位**，
#: 含义一律从 `docs/NOTATION.md` §0 逐字读取（不重写，避免两处不同步）。
_SYMBOL_ORDER: list[str] = [
    r"$T$", r"$C$", r"$t$", r"$r$", r"$R$", r"$R_0$", r"$L$",
    r"$\rho$", r"$c_p$", r"$k$", r"$D$", r"$h$", r"$h_m$",
    r"$T_\infty$", r"$C_\infty$", r"$w$",
    r"$\xi$", r"$\xi_i$", r"$\xi_{i\pm1/2}$", r"$V_i$",
    r"$F^T_{i+1/2}$", r"$F^C_{i+1/2}$",
    r"$\Delta t$", r"$\Delta r$", r"$N_r$", r"$n$", r"$i$",
]

#: 符号 -> 单位（论文展示口径；代码内部一律 SI，见表下注释）
_UNIT: dict[str, str] = {
    r"$T$": "°C（展示）/ K（代码）",
    r"$C$": "kg/kg（干基）",
    r"$t$": "s（代码）/ h、min（展示）",
    r"$r$": "cm（展示）/ m（代码）",
    r"$R$": "cm（展示）/ m（代码）",
    r"$R_0$": "cm（展示）/ m（代码）",
    r"$L$": "cm（展示）/ m（代码）",
    r"$\rho$": "kg/m$^3$",
    r"$c_p$": "J/(kg$\\cdot$K)",
    r"$k$": "W/(m$\\cdot$K)",
    r"$D$": "m$^2$/s",
    r"$h$": "W/(m$^2\\cdot$K)",
    r"$h_m$": "m/s",
    r"$T_\infty$": "°C（展示）/ K（代码）",
    r"$C_\infty$": "kg/kg",
    r"$w$": "kg/kg",
    r"$\xi$": "—",
    r"$\xi_i$": "—",
    r"$\xi_{i\pm1/2}$": "—",
    r"$V_i$": "—",
    r"$F^T_{i+1/2}$": "K$\\cdot$W/(m$\\cdot$K)",
    r"$F^C_{i+1/2}$": "kg$\\cdot$m/(kg$\\cdot$s)",
    r"$\Delta t$": "s",
    r"$\Delta r$": "cm",
    r"$N_r$": "—",
    r"$n$": "—",
    r"$i$": "—",
}


def _notation_meanings() -> dict[str, str]:
    """从 docs/NOTATION.md 读出「符号 -> 含义」，读不到就抛错，不静默降级。

    §0 是「论文符号 / LaTeX 宏 / Python 变量 / 含义」四列（主符号），
    §8 是「符号 / 含义 / 单位 / 代码对应」四列（离散化与移动边界符号），
    §5 是「符号 / 含义 / 代码对应」三列（数值方法索引）。三处的含义列位置不同，
    故分别解析；**不在本脚本里重写含义**，避免与真源两处不同步。
    """
    text = (paths.ROOT / "docs" / "NOTATION.md").read_text(encoding="utf-8")
    out: dict[str, str] = {}

    def _sections(marker: str) -> str:
        try:
            return text.split(marker, 1)[1].split("## ", 1)[0]
        except IndexError as exc:  # pragma: no cover - 真源结构变了才会走到
            raise RuntimeError(f"docs/NOTATION.md 缺少 {marker!r} 节") from exc

    for line in _sections("## 0.").splitlines():          # 含义在第 4 列
        fields = [x.strip() for x in line.strip().strip("|").split("|")]
        if len(fields) == 4 and fields[0].startswith("$"):
            out[fields[0]] = fields[3]
    for line in _sections("## 8.").splitlines():          # 含义在第 2 列
        fields = [x.strip() for x in line.strip().strip("|").split("|")]
        if len(fields) == 4 and fields[0].startswith("$"):
            out.setdefault(fields[0], fields[1])
    for line in _sections("## 5.").splitlines():          # 含义在第 2 列
        fields = [x.strip() for x in line.strip().strip("|").split("|")]
        if len(fields) == 3 and fields[0].startswith("$"):
            out.setdefault(fields[0], fields[1])

    missing = [s for s in _SYMBOL_ORDER if s not in out]
    if missing:
        raise RuntimeError(f"docs/NOTATION.md 里找不到这些符号：{missing}")
    return out


def write_notation_table() -> Path:
    meanings = _notation_meanings()
    lines = [
        "% 本文件由 scripts/make_tables.py 从 docs/NOTATION.md 自动生成，请勿手工编辑",
        "\\begin{table}[htbp]",
        "  \\centering",
        "  \\caption{符号说明}",
        "  \\label{tab:notation}",
        "  \\small",
        "  \\begin{tabular}{lll}",
        "    \\toprule",
        "    符号 & 说明 & 单位 \\\\",
        "    \\midrule",
    ]
    for sym in _SYMBOL_ORDER:
        lines.append(f"    {sym} & {meanings[sym]} & {_UNIT[sym]} \\\\")
    lines += [
        "    \\bottomrule",
        "  \\end{tabular}",
        "  \\par\\smallskip\\footnotesize 说明：程序内部一律 SI（长度用 m、温度用 K、"
        "时间用 s），仅在写入交付文件与绘制插图时换算为 cm、°C、h；"
        "结果文件中的距离列以 cm 计、时间列以 s 计。"
        "题面出现的汽化潜热与平衡含水率未被本文引入（题目未给出其取值或吸附等温线），"
        "故未列入本表。",
        "\\end{table}",
        "",
    ]
    return _write_tex("notation", "\n".join(lines))


# =============================================================
# 三套物性公式集
# =============================================================

#: 附录 2/3/4 的系数。数值来自题目原文（problem/A题.pdf 附录 2~4）。
#: 本表只做**系数转录**，公式形式在论文正文里写；数值由 results 侧无法给出
#: （题目直接给定），故此处是唯一允许的"题给常数"手写位置，且与
#: src/common/correlations.py 的实现逐项一致。
_PROPERTY_SETS = [
    # (物性, 附录2, 附录3, 附录4)
    (r"$\rho$ / (kg/m$^3$)", r"$820$", r"$650+128C$", r"$760+90C$"),
    (r"$c_p$ / (J/(kg$\cdot$K))", r"$2600$",
     r"$1450+2736w$", r"$1850+2150w$"),
    (r"$k$ / (W/(m$\cdot$K))", r"$0.36$",
     r"$0.21+0.38w$", r"$0.12+0.20w$"),
    (r"$D$ / (m$^2$/s)",
     r"$7\times10^{-9}e^{-0.89/C}$",
     r"$2.4\times10^{-3}e^{-0.45/C}e^{-3850/T}$",
     r"$4.2\times10^{-4}e^{-0.30/C}e^{-3850/T}$"),
    (r"$h$ / (W/(m$^2\cdot$K))", r"$25$", r"$25$（沿用）", r"$25$（沿用）"),
    (r"$h_m$ / (m/s)", r"$8\times10^{-7}$", r"$8\times10^{-7}$（沿用）",
     r"$8\times10^{-7}$（沿用）"),
    ("适用问题", "问题 1", "问题 2、3", "问题 4"),
]


def write_property_table() -> Path:
    df = pd.DataFrame(
        [list(row) for row in _PROPERTY_SETS],
        columns=["物性/参数", "附录 2（常数物性）", "附录 3（变物性）",
                 "附录 4（变物性 + 收缩）"],
    )
    text = to_booktabs(
        df,
        "题目给出的三套物性参数集（$w = C/(1+C)$；附录 3/4 的 $D$ 公式中 $T$ 必须用 K）",
        "tab:property-sets",
        formats=[str] * 4,
        size="\\small",
        note="附录 3/4 未另给 $h$ 与 $h_m$，本文按题目附录 2 的取值沿用，"
             "并在模型假设中披露这一取值来源。",
    )
    return _write_tex("property_sets", text)


# =============================================================
# 数值宏：论文正文唯一允许出现结果数字的地方
# =============================================================


def _macros(pairs: list[tuple[str, str]]) -> str:
    return "\n".join(f"\\newcommand{{\\{k}}}{{{v}}}" for k, v in pairs) + "\n"


def write_values() -> tuple[Path, Path]:
    """写 q1_values.tex（历史文件名）与 problem_values.tex（二~四问 + 公共量）。"""
    results = paths.RESULTS_DIR
    summaries = {q: _load_json(results / f"{q}_summary.json")
                 for q in ("q1", "q2", "q3", "q4")}
    acc = _load_json(results / "validation" / "accuracy.json")
    acc4 = _load_json(results / "validation" / "accuracy-q4.json")
    report = _load_json(results / "validation" / "numerics.json")

    # ---- 表 1/表 2 的末行（第一问） ----
    s1 = pd.read_excel(results / "result1.xlsx", sheet_name=None)
    temp = s1["温度"].set_index(s1["温度"].columns[0])
    moist = s1["水分浓度"].set_index(s1["水分浓度"].columns[0])

    q1 = summaries["q1"]
    q1_pairs = [
        ("QOneCenterT", f'{temp.loc[1800, "0"]:.4f}'),
        ("QOneSurfaceT", f'{temp.loc[1800, "2"]:.4f}'),
        ("QOneCenterC", f'{moist.loc[1800, "0"]:.4f}'),
        ("QOneSurfaceC", f'{moist.loc[1800, "2"]:.4f}'),
        ("QOneMassError", _sci(q1["mass_balance_relative"])),
        ("QOneEnergyError", _sci(q1["q1_energy_balance_relative"])),
    ]
    # 时间误差分离：accuracy.json 的 cross_solver 段（BDF vs Radau IIA，161 节点）
    cross1 = next(x for x in acc["cross_solver"] if x["q"] == "q1")
    q1_pairs += [
        ("QOneRadauT", _sci(cross1["delta_T_K"])),
        ("QOneRadauC", _sci(cross1["delta_C"])),
    ]
    # Bessel 谱展开参考
    q1_pairs += [
        ("QOneBesselModes", _sci(acc["bessel"]["modes_delta_T_K"])),
        ("QOneBesselN2561", _sci(acc["bessel"]["max_error_by_grid_K"]["2561"])),
        ("QOneBesselN5121", _sci(acc["bessel"]["max_error_by_grid_K"]["5121"])),
    ]
    q1_tex = _write_tex("q1_values", _macros(q1_pairs))

    # ---- 二~四问与公共量 ----
    q2, q3, q4 = summaries["q2"], summaries["q3"], summaries["q4"]
    grid3 = [g for g in acc["grid"] if g["q"] == "q3"]
    grid4 = acc4["grid"]
    cross3 = next(x for x in acc["cross_solver"] if x["q"] == "q3")
    fixed = next(x for x in report["fixed_radius_control"] if x["q"] == "q4")
    sens = {(s["q"], s["case"]): s for s in report["sensitivity"]}

    def h_of(seconds: float) -> str:
        return f"{seconds / 3600.0:.4f}"

    pairs: list[tuple[str, str]] = [
        # 公共
        ("QGridProduction", f'{q1["n_internal"]}'),
        # 问题二
        ("QTwoEventH", h_of(q2["event_time_s"])),
        ("QTwoEventS", f'{q2["event_time_s"]:.2f}'),
        ("QTwoLastRowS", f'{q2["first_output_below_s"]:.0f}'),
        ("QTwoSurfaceH3", f'{_state("q2", 10800, "2"):.4f}'),
        ("QTwoCenterH3B", f'{_state("q2", 10800, "0"):.4f}'),
        ("QTwoSurfaceH24", f'{_state("q2", 86400, "2"):.4f}'),
        ("QTwoCenterH24", f'{_state("q2", 86400, "0"):.4f}'),
        ("QTwoSurfaceH48", f'{_state("q2", 172800, "2"):.4f}'),
        ("QTwoCenterH48", f'{_state("q2", 172800, "0"):.4f}'),
        ("QTwoFinalSurface", f'{_state("q2", q2["first_output_below_s"], "2"):.4f}'),
        ("QTwoFinalCenter", f'{_state("q2", q2["first_output_below_s"], "0"):.4f}'),
        # 问题三
        ("QThreeEventH", h_of(q3["event_time_s"])),
        ("QThreeEventS", f'{q3["event_time_s"]:.2f}'),
        ("QThreeLastRowS", f'{q3["first_output_below_s"]:.0f}'),
        ("QThreeLastRowHN", h_of(q3["first_output_below_s"])),
        ("QThreeSurfaceEnd", f'{_state("q3", q3["first_output_below_s"], "2"):.4f}'),
        ("QThreeGap", f'{q3["first_output_below_s"] - q3["event_time_s"]:.2f}'),
        ("QThreeGridEventDiff", _sci(grid3[-1]["delta_event_s"])),
        ("QThreeGridEventDiffPrevX", _sci(grid3[-2]["delta_event_s"])),
        ("QThreeGridFieldDC", _sci(grid3[-1]["delta_C"])),
        ("QThreeRadauT", _sci(cross3["delta_T_K"])),
        ("QThreeRadauC", _sci(cross3["delta_C"])),
        ("QThreeRadauEvent", _sci(abs(cross3["delta_event_s"]))),
        ("QThreeSensTMin", _sci(abs(sens[("q3", "last_hour_T_min")]["delta_h"]), 3)),
        ("QThreeSensTMax", _sci(abs(sens[("q3", "last_hour_T_max")]["delta_h"]), 3)),
        ("QThreeSensUpH", f'{sens[("q3", "last_hour_T_min")]["event_h"]:.4f}'),
        ("QThreeSensDownH", f'{sens[("q3", "last_hour_T_max")]["event_h"]:.4f}'),
        # 问题四
        ("QFourEventH", h_of(q4["event_time_s"])),
        ("QFourEventS", f'{q4["event_time_s"]:.2f}'),
        ("QFourLastRowS", f'{q4["first_output_below_s"]:.0f}'),
        ("QFourEventR", f'{q4["event_R"] * 100:.4f}'),
        ("QFourSurfaceEnd", f'{_state("q4", q4["first_output_below_s"], "药材表面"):.4f}'),
        ("QFourShrinkPct", f'{(1 - q4["event_R"] / 0.02) * 100:.1f}'),
        ("QFourFixedRadiusHN", f'{fixed["event_h"]:.4f}'),
        ("QFourFixedRadiusN", f'{fixed["n"]}'),
        ("QFourMovingHN", f'{fixed["moving_h"]:.4f}'),
        ("QFourShrinkEffectPct",
         f'{(1 - fixed["moving_h"] / fixed["event_h"]) * 100:.1f}'),
        ("QFourNetEffectPct",
         "%.1f" % ((q3["event_time_s"] / 3600.0 - q4["event_time_s"] / 3600.0)
                   / (q3["event_time_s"] / 3600.0) * 100.0)),
        ("QFourGridEventDiff", _sci(grid4[-1]["delta_event_s"])),
        ("QFourGridFieldDC", _sci(grid4[-1]["delta_C"])),
        ("QFourSensTMin", _sci(abs(sens[("q4", "last_hour_T_min")]["delta_h"]), 3)),
        ("QFourSensTMax", _sci(abs(sens[("q4", "last_hour_T_max")]["delta_h"]), 3)),
        # 质量审计
        ("QTwoMassError", _sci(q2["mass_balance_relative"])),
        ("QThreeMassError", _sci(q3["mass_balance_relative"])),
        ("QFourMassError", _sci(q4["mass_balance_relative"])),
        # 计算量（墙钟时间因机器而异，只用于"计算量可控"的定性结论）
        ("QTwoWallS", f'{q2["wall_time_s"]:.1f}'),
        ("QThreeWallS", f'{q3["wall_time_s"]:.1f}'),
        ("QFourWallS", f'{q4["wall_time_s"]:.1f}'),
    ]
    prob_tex = _write_tex("problem_values", _macros(pairs))
    return q1_tex, prob_tex


# =============================================================
# 验证表：网格收敛、时间精度、灵敏度、附件统计
# =============================================================


def write_validation_tables() -> list[Path]:
    results = paths.RESULTS_DIR
    acc = _load_json(results / "validation" / "accuracy.json")
    acc4 = _load_json(results / "validation" / "accuracy-q4.json")
    report = _load_json(results / "validation" / "numerics.json")
    made: list[Path] = []

    who = {"q1": "问题 1", "q3": "问题 2、3（同模型）", "q4": "问题 4"}
    rows = []
    # accuracy.json 的每条自带 "q" 字段；accuracy-q4.json 单独成表，故补上。
    grid_entries = list(acc["grid"]) + [{**e, "q": "q4"} for e in acc4["grid"]]
    for entry in grid_entries:
        q = entry["q"]
        rows.append([
            who.get(q, q), entry["n"],
            "--" if entry.get("delta_T_K") is None else _sci(entry["delta_T_K"]),
            "--" if entry.get("delta_C") is None else _sci(entry["delta_C"]),
            "--" if entry.get("delta_event_s") is None else _sci(entry["delta_event_s"], 3),
            _sci(entry["mass_residual"]),
        ])
    df = pd.DataFrame(rows, columns=[
        "方程与参数集", "节点数 $N_r$", "相邻网格最大温差/K",
        "相邻网格最大含水率差/(kg/kg)", "终点时刻差/s", "质量收支相对残差"])
    made.append(_write_tex("validation_grid", to_booktabs(
        df,
        "空间网格加密验证（交付网格上的场量最大差与烘干终点时刻差）",
        "tab:validation-grid",
        formats=[str] * 6, size="\\small", resize=0.98,
        note="相邻网格指与上一档（节点数减半）的对比；问题 1 无终点判据，故该列为空。"
             "节点数 1281 与 2561 为精度改进过程中的中间档，正式计算取 2561。")))

    # ---- 时间精度：BDF vs Radau IIA（161 节点） + 旧容差下的收敛研究 ----
    cross = acc["cross_solver"]
    t_rows = []
    for c in cross:
        t_rows.append([who.get(c["q"], c["q"]), c["n"], _sci(c["delta_T_K"]),
                       _sci(c["delta_C"]),
                       "--" if c.get("delta_event_s") is None
                       else _sci(abs(c["delta_event_s"]), 3)])
    c4 = acc4["cross_solver"]
    t_rows.append([who["q4"], c4["n"], _sci(c4["delta_T_K"]), _sci(c4["delta_C"]),
                   _sci(abs(c4["delta_event_s"]), 3)])
    for t in report["time"]:
        if t["q"] == "q3":
            t_rows.append(["问题 2、3（容差与步长收紧对照）", 641,
                           _sci(t["delta_T_K"]), _sci(t["delta_C"]),
                           _sci(abs(t["delta_event_s"]), 3)])
    df_t = pd.DataFrame(t_rows, columns=[
        "方程与参数集", "节点数 $N_r$", "最大温差/K", "最大含水率差/(kg/kg)",
        "终点时刻差/s"])
    made.append(_write_tex("validation_time", to_booktabs(
        df_t,
        "时间积分精度交叉验证（同一空间离散下更换时间方法或收紧误差控制）",
        "tab:validation-time",
        formats=[str] * 5, size="\\small",
        note="前四行是 BDF 与 Radau IIA（五阶）在同一网格上的差异，"
             "用于把时间误差与空间误差分离；最后一行为把相对/绝对容差各收紧十倍、"
             "最大步长减半后的差异。事件定位精度受积分器容差限制，故终点时刻差"
             "比场量差更能反映事件检测的可靠性。")))

    # ---- 灵敏度（4 h 后环境外推） ----
    s_rows = []
    label = {"last_hour_T_min": "末小时最低 $T_\\infty$（$-0.408$ K）",
             "last_hour_T_max": "末小时最高 $T_\\infty$（$+0.071$ K）",
             "last_hour_C_min": "末小时最低 $C_\\infty$（$-1.1\\times10^{-4}$ kg/kg）",
             "last_hour_C_max": "末小时最高 $C_\\infty$（$+3.8\\times10^{-4}$ kg/kg）"}
    order = ["last_hour_T_min", "last_hour_T_max", "last_hour_C_min", "last_hour_C_max"]
    by_case = {(s["q"], s["case"]): s for s in report["sensitivity"]}
    for case in order:
        s3 = by_case[("q3", case)]
        s4 = by_case[("q4", case)]
        # 注意：每个单元格只能放**一个**字符串。早期版本把两个数塞进同一列，
        # pandas 会把它们折成 Series 再打印出 "Name: 0, dtype: object"（实测踩过）。
        s_rows.append([
            label[case],
            f'{s3["event_h"]:.4f}', f'{s3["delta_h"]:+.4f}',
            f'{s4["event_h"]:.4f}', f'{s4["delta_h"]:+.4f}',
        ])
    df_s = pd.DataFrame(s_rows, columns=[
        "扰动（相对末值保持）", "问题 2、3 终点/h", "问题 2、3 变化/h",
        "问题 4 终点/h", "问题 4 变化/h"])
    made.append(_write_tex("sensitivity", to_booktabs(
        df_s,
        "4 h 之后环境条件外推假设的灵敏度分析（扰动幅度取自附件 1 末小时的实测上下限）",
        "tab:sensitivity",
        formats=[str, str, str, str, str], size="\\small",
        note="扰动幅度是附件 1 最后 1 h 内 $T_\\infty$、$C_\\infty$ 的实测最小值与最大值"
             "相对末值的偏移；参照算例取 $N_r=161$。温度方向的敏感度比浓度方向高约"
             "两个数量级。")))

    # ---- 附件 1 末小时统计（驱动数据的离散程度） ----
    amb = pd.read_csv(paths.ROOT / "data" / "processed" / "ambient.csv")
    last = amb[amb["t_s"] >= 10800]
    rows = [
        ["$T_\\infty$", f'{amb["T_inf_K"].iloc[-1] - 273.15:.3f}',
         f'{last["T_inf_K"].min() - 273.15:.3f}',
         f'{last["T_inf_K"].max() - 273.15:.3f}',
         f'{last["T_inf_K"].std(ddof=0):.4f}'],
        ["$C_\\infty$", f'{amb["C_inf"].iloc[-1]:.5f}',
         f'{last["C_inf"].min():.5f}', f'{last["C_inf"].max():.5f}',
         f'{last["C_inf"].std(ddof=0):.6f}'],
    ]
    df_a = pd.DataFrame(rows, columns=[
        "驱动量", "4 h 末值（外推所用值）", "末小时最小值", "末小时最大值",
        "末小时标准差"])
    made.append(_write_tex("ambient_stats", to_booktabs(
        df_a,
        "附件 1 环境驱动数据的统计特征（$T_\\infty$ 单位 °C，$C_\\infty$ 单位 kg/kg）",
        "tab:ambient-stats",
        formats=[str] * 5, size="\\small",
        note="附件 1 共 241 个测量点（步长 60 s），仅覆盖 0~4 h；"
             "4 h 之后取末值保持，故末值既是外推的取值、也是外推不确定性的中心。")))

    return made


def write_q1_validation() -> Path:
    """第一问的网格加密表（保留历史文件名 q1_validation.tex，供 09_evaluation 引用）。"""
    report = _load_json(paths.RESULTS_DIR / "validation" / "numerics.json")
    grid = [x for x in report["grid"] if x["q"] == "q1"]
    rows = []
    for g in grid:
        rows.append([g["n"],
                     "--" if g.get("delta_T_K") is None else _sci(g["delta_T_K"]),
                     "--" if g.get("delta_C") is None else _sci(g["delta_C"])])
    frame = pd.DataFrame(rows, columns=["节点数 $N_r$", "相邻加密温度差/K",
                                        "相邻加密含水率差/(kg/kg)"])
    return _write_tex("q1_validation", to_booktabs(
        frame, "第一问空间网格加密验证（题目指定七个时刻、21 个输出位置的最大差）",
        "tab:validation", formats=[str] * 3, size="\\small"))


# =============================================================
# main
# =============================================================


def main() -> int:
    results = paths.RESULTS_DIR
    paths.TABLES_DIR.mkdir(parents=True, exist_ok=True)
    source = results / "result1.xlsx"
    if not source.exists():
        print(f"!! 缺少 {paths.rel(source)}，请先跑 make q1")
        return 1

    sheets = pd.read_excel(source, sheet_name=None)
    times = [100, 300, 600, 900, 1200, 1500, 1800]
    for sheet, key, unit in (("温度", "q1_temp", "°C"), ("水分浓度", "q1_moist", "kg/kg")):
        df = sheets[sheet].set_index(sheets[sheet].columns[0])
        df.columns = [str(c) for c in df.columns]
        chosen = df.loc[times, ["0", "0.5", "1", "1.5", "2"]].copy()
        chosen.index.name = "时间/s"
        chosen = chosen.reset_index()
        caption, label = TABLES[key]
        text = to_booktabs(chosen, caption + f"（{unit}；距离单位：cm）", label)
        _write_tex(key, text)

    made = [
        write_q1_validation(),
        write_notation_table(),
        write_property_table(),
        *write_values(),
        *write_validation_tables(),
    ]
    for p in made:
        print(f"  生成 {paths.rel(p)}")

    print()
    made_csv = tables_from_csvs(skip={"q1_temp", "q1_moist"})
    print(f"\n共生成 {len(made)} 个验证/符号/数值片段 + {made_csv} 张展示表。")
    print("⚠️ 不要把表格内容手抄进 paper/sections/ —— 数字只有一处来源。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
