"""results/tables/*.csv  ->  paper/tab/*.tex（booktabs 三线表片段）

运行： make tables

设计意图（AGENTS.md §2）：
    论文里的表 1~表 6 **不允许手抄数字**。数字永远只有一处来源 —— results/。
    论文用 \\input{tab/tabN} 引入本脚本生成的片段。

⚠️ 不要手工编辑 paper/tab/*.tex，下次 make 就覆盖了。
   格式不对请提需求改本脚本（@impl 所有）。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

from _bootstrap import setup

setup()

from common import paths  # noqa: E402

#: 表格列名 -> 论文表头的映射规则：
#: 生成的 csv 第一列是时间，其余列是「到药材中心的距离/cm」。
#: 表头文字与 docs/NOTATION.md 保持一致。


def _fmt(v: float) -> str:
    """保留四位小数（题目要求）。NaN 输出为空。"""
    if isinstance(v, str):
        return v
    try:
        f = float(v)
    except (TypeError, ValueError):
        return str(v)
    if f != f:  # NaN
        return ""
    return f"{f:.4f}"


def _num_columns(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if c != df.columns[0]]


def to_booktabs(df: pd.DataFrame, caption: str, label: str) -> str:
    """生成一个 booktabs 三线表片段（无竖线，符合数模论文规范）。"""
    head, *body = df.columns.tolist()
    ncols = len(df.columns)

    lines = [
        "% 本文件由 scripts/make_tables.py 自动生成，请勿手工编辑",
        "\\begin{table}[htbp]",
        "  \\centering",
        f"  \\caption{{{caption}}}",
        f"  \\label{{{label}}}",
        "  \\begin{tabular}{" + "c" * ncols + "}",
        "    \\toprule",
        f"    {head} & " + " & ".join(str(c) for c in body) + " \\\\",
        "    \\midrule",
    ]
    for _, row in df.iterrows():
        cells = [_fmt(row[head])] + [_fmt(row[c]) for c in body]
        lines.append("    " + " & ".join(cells) + " \\\\")
    lines += [
        "    \\bottomrule",
        "  \\end{tabular}",
        "\\end{table}",
        "",
    ]
    return "\n".join(lines)


#: csv 文件名 -> (论文表标题, 标签)。表号由论文正文引用决定，这里给的是默认值。
TABLES: dict[str, tuple[str, str]] = {
    "q1_temp": ("30 分钟内药材的温度", "tab:q1-temperature"),
    "q1_moist": ("30 分钟内药材的水分浓度", "tab:q1-moisture"),
    "q2_temp": ("3 小时内药材的温度", "tab:q2-temperature"),
    "q2_moist": ("3 小时内药材的水分浓度", "tab:q2-moisture"),
    "q3_moist": ("药材烘干过程的水分浓度", "tab:q3-moisture"),
    "q4_moist": ("考虑收缩的药材烘干过程的水分浓度", "tab:q4-moisture"),
}


def main() -> int:
    from build_paper_assets import tables
    return tables()


if __name__ == "__main__":
    sys.exit(main())
