"""交付物 xlsx 读写。

⚠️ **模板是交付格式的唯一真源**（AGENTS.md 铁律 3）。
   本模块的布局常量是 `make probe` 实测 `problem/附件/附件3/*.xlsx` 得到的，
   **不是**从题目文字描述猜的。题目文字与模板冲突时，以模板为准。

实测结论（`make probe` 复核，2026 賽前）：

    ┌──────────┬──────────────────┬────────┬───────────────────────────┐
    │ 文件     │ 工作表           │ 时间步 │ 最后一列                  │
    ├──────────┼──────────────────┼────────┼───────────────────────────┤
    │ result1  │ 温度, 水分浓度   │ 1 s    │ 2                         │
    │ result2  │ 温度, 水分浓度   │ 1 s    │ 2                         │
    │ result3  │ Sheet1           │ 60 s   │ 2                         │
    │ result4  │ Sheet1           │ 60 s   │ 药材表面（文字，非数值）  │
    └──────────┴──────────────────┴────────┴───────────────────────────┘

    · A1 是斜线表头 `时间\\到药材中心的距离`，其余表头是距离数值（cm）。
    · 距离列是**完整的 0.1 cm 网格**：0, 0.1, 0.2, …, 2.0 —— 共 **21 列**。
      模板里用 `…` 省略，那是示意，不是只有 4 列。
    · **时间单位是秒**，尽管题目表 3~表 6 的表头写的是 h。
      模板 A 列数据是 1 或 60（秒），论文表格才用小时。
    · result3/result4 **没有温度表**，且工作表名是 `Sheet1`，不是「水分浓度」。
"""

from __future__ import annotations

import math
import warnings
from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import paths

#: 斜线表头（A1 原文）
TIME_HEADER = "时间\\到药材中心的距离"

#: result4 最后一列是文字
SURFACE_HEADER = "药材表面"

#: 题目要求：所有结果保留四位小数
DECIMALS = 4

#: 交付空间网格：0 ~ 2 cm，步长 0.1 cm -> 21 列
N_DISTANCE_COLUMNS = 21

#: 兼容旧名（论文/文档里引用过）
SHEET_TEMPERATURE = "温度"
SHEET_MOISTURE = "水分浓度"

#: 附件 1 / 附件 2 的列名（实测）
ATTACH1_COLUMNS = ("时间", "温度", "水分浓度")
ATTACH2_COLUMNS = ("时间", "半径")


class ResultFormatError(ValueError):
    """交付物格式不符合模板。**不要捕获它然后继续写出**——格式错了就是错了。"""


# --- 布局定义（实测，不是猜的）----------------------------------------------


@dataclass(frozen=True)
class ResultLayout:
    """一个 result 文件的真实结构。"""

    problem: str
    sheets: tuple[tuple[str, str], ...]  # (工作表名, 物理量 "T" | "C")
    dt_s: float  # 交付时间步长（秒）
    last_header: str = "2"  # 最后一列的表头

    @property
    def sheet_names(self) -> tuple[str, ...]:
        return tuple(name for name, _ in self.sheets)

    def distance_headers(self) -> list[str]:
        """距离列的表头。数值用 %g，例如 0, 0.1, ..., 2。"""
        headers = [f"{i * 0.1:g}" for i in range(N_DISTANCE_COLUMNS)]
        headers[-1] = self.last_header
        return headers

    def expected_columns(self) -> list[str]:
        return [TIME_HEADER, *self.distance_headers()]


LAYOUTS: dict[str, ResultLayout] = {
    "q1": ResultLayout("q1", (("温度", "T"), ("水分浓度", "C")), 1.0),
    "q2": ResultLayout("q2", (("温度", "T"), ("水分浓度", "C")), 1.0),
    "q3": ResultLayout("q3", (("Sheet1", "C"),), 60.0),
    "q4": ResultLayout("q4", (("Sheet1", "C"),), 60.0, last_header=SURFACE_HEADER),
}


def layout(problem: str) -> ResultLayout:
    key = str(problem).strip().lower()
    if key.startswith("result"):
        key = "q" + key.removeprefix("result")
    elif not key.startswith("q"):
        key = "q" + key
    if key not in LAYOUTS:
        raise ValueError(f"问题编号只能是 1~4（或 q1~q4 / result1~result4），收到 {problem!r}")
    return LAYOUTS[key]


# --- 读 ---------------------------------------------------------------------


def read_attachment(n: int) -> pd.DataFrame:
    """读取 problem/附件/附件<N>.xlsx。

    n=1 -> 烘房温度与水分浓度的时间序列（0~14400 s，步长 60 s）
    n=2 -> 药材半径随时间变化（0~259200 s，步长 1800 s）

    返回的 DataFrame 列名与原件一致，**单位也与原件一致**（时间 s、半径 cm、温度 °C）。
    换算成 SI 是调用方的事（用 units 模块）。
    """
    path = paths.attachment_path(n)
    if not path.exists():
        raise FileNotFoundError(f"附件不存在：{paths.rel(path)}")

    df = pd.read_excel(path, sheet_name=0)
    df.columns = [str(c).strip() for c in df.columns]

    expected = ATTACH1_COLUMNS if n == 1 else ATTACH2_COLUMNS
    if tuple(df.columns) != expected:
        raise ResultFormatError(
            f"{paths.rel(path)} 的列名与预期不符。\n"
            f"  预期: {expected}\n"
            f"  实际: {tuple(df.columns)}\n"
            f"题目原件可能已更新，请核对后同步本模块的常量与 data/README.md。"
        )

    t = df["时间"].to_numpy(dtype=float)
    if t.size and not (pd.Series(t).diff().dropna() > 0).all():
        raise ResultFormatError(f"{paths.rel(path)} 的时间列非严格单调递增。")

    return df


def read_template(problem: str) -> dict[str, pd.DataFrame]:
    """读取 problem/附件/附件3/result<N>.xlsx 的原始内容（含 `…` 示意列）。

    用于 `make probe` 与交叉核对。**不要用它来推导列结构** ——
    用 `layout(problem)`（那是实测结论的结构化形式）。
    """
    path = paths.template_path(problem)
    if not path.exists():
        raise FileNotFoundError(f"交付模板不存在：{paths.rel(path)}")
    sheets = pd.read_excel(path, sheet_name=None)
    return {str(k).strip(): v for k, v in sheets.items()}


def verify_layout_against_template(problem: str) -> list[str]:
    """把实测布局与实际模板文件对一遍。返回不一致项（空列表表示一致）。

    CI 里跑这个：如果赛方更新了模板，这里会立刻报出来。
    """
    lay = layout(problem)
    sheets = read_template(problem)
    problems: list[str] = []

    if set(sheets) != set(lay.sheet_names):
        problems.append(
            f"{problem} 工作表名不一致：模板={sorted(sheets)} 布局={sorted(lay.sheet_names)}"
        )

    for name, df in sheets.items():
        cols = [str(c).strip() for c in df.columns]
        if not cols:
            continue
        if cols[0] != TIME_HEADER:
            problems.append(f"{problem}/{name} A1 表头不一致：模板={cols[0]!r} 期望={TIME_HEADER!r}")
        last = cols[-1]
        if last != lay.last_header:
            problems.append(
                f"{problem}/{name} 末列表头不一致：模板={last!r} 期望={lay.last_header!r}"
            )

    # 时间步长：模板给的是示意数据（1 或 60），核对首行
    for name, df in sheets.items():
        t = pd.to_numeric(df.iloc[:, 0], errors="coerce").dropna()
        if t.size:
            step = float(t.iloc[1] - t.iloc[0]) if t.size > 1 else float(t.iloc[0])
            if not math.isclose(step, lay.dt_s):
                problems.append(
                    f"{problem}/{name} 时间步长不一致：模板={step:g} 期望={lay.dt_s:g}"
                )
    return problems


# --- 写 ---------------------------------------------------------------------


def write_result(problem: str, sheets: dict[str, pd.DataFrame]) -> paths.Path:
    """写出 results/result<N>.xlsx，并与**实测布局**做一致性校验。

    校验不通过直接抛 ResultFormatError，**不写出文件**。
    数值统一四舍五入到 DECIMALS 位。
    """
    lay = layout(problem)
    _validate(problem, sheets, lay)

    rounded: dict[str, pd.DataFrame] = {}
    for name, df in sheets.items():
        out = df.copy()
        num_cols = out.select_dtypes(include="number").columns
        out[num_cols] = out[num_cols].round(DECIMALS)
        rounded[name] = out

    dest = paths.result_path(problem)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(dest, engine="openpyxl") as writer:
        for name, df in rounded.items():
            df.to_excel(writer, sheet_name=name, index=False)
    return dest


def _validate(problem: str, sheets: dict[str, pd.DataFrame], lay: ResultLayout) -> None:
    """交付前的硬校验。宁可在这里炸，也不要在提交后被发现格式错了。"""
    errors: list[str] = []

    if set(sheets) != set(lay.sheet_names):
        errors.append(
            f"工作表名不匹配。\n    模板/布局: {sorted(lay.sheet_names)}\n    待写: {sorted(sheets)}"
        )

    expected_cols = lay.expected_columns()
    for name in set(sheets) & set(lay.sheet_names):
        df = sheets[name]
        got = [str(c) for c in df.columns]
        if got != expected_cols:
            diff = _first_diff(got, expected_cols)
            errors.append(
                f"工作表「{name}」列结构不匹配（{diff}）。\n"
                f"    期望 {len(expected_cols)} 列：{expected_cols[:4]} ... {expected_cols[-1]!r}\n"
                f"    实际 {len(got)} 列：{got[:4]} ... {got[-1]!r}\n"
                f"    提示：距离列是 0~2 cm 步长 0.1 cm 的完整 21 列网格。"
            )
            continue

        if df.empty:
            errors.append(f"工作表「{name}」为空。")
            continue

        t = pd.to_numeric(df.iloc[:, 0], errors="coerce").to_numpy(dtype=float)
        if not np.all(np.isfinite(t)):
            errors.append(f"工作表「{name}」时间列含非数值。")
        else:
            d = np.diff(t)
            if d.size and not np.allclose(d, lay.dt_s, rtol=0, atol=1e-6):
                errors.append(
                    f"工作表「{name}」时间步长不是均匀的 {lay.dt_s:g} s"
                    f"（实测 min={d.min():g}, max={d.max():g}）。"
                )
            if t.size and not math.isclose(t[0], lay.dt_s) and not math.isclose(t[0], 0.0):
                warnings.warn(
                    f"{problem}/{name} 时间列首值为 {t[0]:g}，模板示意数据从 "
                    f"{lay.dt_s:g} 开始。请确认是否要包含 t=0 这一行。",
                    stacklevel=3,
                )

        vals = df.iloc[:, 1:].to_numpy(dtype=float) if df.shape[1] > 1 else np.empty((0, 0))
        if vals.size and not np.all(np.isfinite(vals)):
            bad = [c for c in df.columns[1:] if not _finite(df[c])]
            errors.append(f"工作表「{name}」以下列含 NaN/Inf：{bad}")

    if errors:
        raise ResultFormatError(
            f"result{problem[-1]} 交付校验未通过，未写出文件：\n  - "
            + "\n  - ".join(errors)
            + "\n\n模板见 problem/附件/附件3/。先跑 make probe 查看真实结构。"
            + "见 AGENTS.md 铁律 3。"
        )


def _first_diff(got: list[str], want: list[str]) -> str:
    if len(got) != len(want):
        return f"列数 {len(got)} != {len(want)}"
    for i, (a, b) in enumerate(zip(got, want, strict=False)):
        if a != b:
            return f"第 {i + 1} 列 {a!r} != {b!r}"
    return "未知"


def _finite(s: pd.Series) -> bool:
    try:
        return all(math.isfinite(float(v)) for v in s)
    except (TypeError, ValueError):
        return False


def write_table_csv(df: pd.DataFrame, name: str) -> paths.Path:
    """写论文用的展示网格数值表到 results/tables/<name>.csv。

    这是 `scripts/make_tables.py` 的输入。**不要手工编辑这些 csv**——
    它们是生成物，下次 make 就覆盖了。
    """
    paths.RESULTS_TABLES.mkdir(parents=True, exist_ok=True)
    dest = paths.RESULTS_TABLES / f"{name}.csv"
    df.round(DECIMALS).to_csv(dest, index=False)
    return dest


# --- 探查 -------------------------------------------------------------------


def probe_template(problem: str) -> str:
    """打印模板的真实结构。**开工第一件事就是跑这个**（AGENTS.md 铁律 3）。"""
    lay = layout(problem)
    path = paths.template_path(problem)
    lines = [f"{paths.rel(path)}"]
    sheets = read_template(problem)
    for name, df in sheets.items():
        lines.append(f"  工作表「{name}」  模板内列数={df.shape[1]}（含 '…' 示意列）")
        lines.append(f"    表头原文: {[str(c) for c in df.columns]}")
        t = pd.to_numeric(df.iloc[:, 0], errors="coerce").dropna()
        if t.size:
            lines.append(f"    时间列示意值: {list(t)}")
    lines.append("  ── 实测布局（写交付物按这个）──")
    lines.append(f"    工作表: {list(lay.sheet_names)}  时间步长: {lay.dt_s:g} s")
    lines.append(
        f"    应为 {len(lay.expected_columns())} 列 = 1 列时间 + "
        f"{N_DISTANCE_COLUMNS} 列距离(0~2 cm 步长 0.1)"
    )
    lines.append(f"    A1 表头: {TIME_HEADER!r}   末列表头: {lay.last_header!r}")
    mism = verify_layout_against_template(problem)
    if mism:
        lines.append("    ⚠️ 布局与模板文件不一致：")
        lines += [f"       - {m}" for m in mism]
    else:
        lines.append("    ✓ 布局与模板文件一致")
    return "\n".join(lines)
