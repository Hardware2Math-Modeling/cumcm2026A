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
    # 本次用户只要求第一问论文：数值表直接从正式xlsx读取，不从手抄CSV拼装。
    import json
    from common.io_excel import read_attachment
    source = paths.RESULTS_DIR / "result1.xlsx"
    sheets = pd.read_excel(source, sheet_name=None)
    paths.TABLES_DIR.mkdir(parents=True, exist_ok=True)
    times = [100,300,600,900,1200,1500,1800]
    for sheet,key,unit in (("温度","q1_temp","°C"),("水分浓度","q1_moist","kg/kg")):
        df=sheets[sheet].set_index(sheets[sheet].columns[0])
        df.columns=[str(c) for c in df.columns]
        chosen=df.loc[times,["0","0.5","1","1.5","2"]].copy()
        chosen.index.name="时间/s"
        chosen=chosen.reset_index()
        caption,label=TABLES[key]
        text=to_booktabs(chosen,caption+f"（{unit}；距离单位：cm）",label)
        (paths.TABLES_DIR/f"{key}.tex").write_text(text,encoding="utf-8")
    report=json.loads((paths.RESULTS_DIR/"validation/numerics.json").read_text(encoding="utf-8"))
    grid=[x for x in report["grid"] if x["q"]=="q1"]
    rows=[]
    for g in grid:
        rows.append([g["n"], "--" if "delta_T_K" not in g else f'{g["delta_T_K"]:.2e}',
                     "--" if "delta_C" not in g else f'{g["delta_C"]:.2e}'])
    frame=pd.DataFrame(rows,columns=["节点数",r"相邻加密温度差/K",r"相邻加密含水率差"])
    # 科学计数法列须保留字符串，避免四位小数把误差显示成0。
    tex=to_booktabs(frame,"空间网格加密验证（七个指定时刻、21个输出位置的最大差）","tab:validation")
    for g in grid[1:]:
        for key in ("delta_T_K","delta_C"):
            tex=tex.replace(f'{g[key]:.4f}',f'{g[key]:.2e}',1)
    (paths.TABLES_DIR/"q1_validation.tex").write_text(tex,encoding="utf-8")
    summary=json.loads((paths.RESULTS_DIR/"q1_summary.json").read_text(encoding="utf-8"))
    temperature=sheets["温度"].set_index(sheets["温度"].columns[0])
    moisture=sheets["水分浓度"].set_index(sheets["水分浓度"].columns[0])
    scalars={"QOneCenterT":f'{temperature.loc[1800,"0"]:.4f}',
             "QOneSurfaceT":f'{temperature.loc[1800,"2"]:.4f}',
             "QOneCenterC":f'{moisture.loc[1800,"0"]:.4f}',
             "QOneSurfaceC":f'{moisture.loc[1800,"2"]:.4f}',
             "QOneMassError":f'{summary["mass_balance_relative"]:.2e}',
             "QOneEnergyError":f'{summary["q1_energy_balance_relative"]:.2e}'}
    temporal=next(x for x in report["time"] if x["q"]=="q1")
    scalars["QOneTimeErrorT"]=f'{temporal["delta_T_K"]:.2e}'
    scalars["QOneTimeErrorC"]=f'{temporal["delta_C"]:.2e}'
    (paths.TABLES_DIR/"q1_values.tex").write_text("\n".join(
        "\\newcommand{\\"+k+"}{"+v+"}" for k,v in scalars.items())+"\n",encoding="utf-8")
    # 符号表从唯一真源解析生成，不手工复制一套定义。
    notation=(paths.ROOT/"docs/NOTATION.md").read_text(encoding="utf-8")
    section=notation.split("## 0.",1)[1].split("## 1.",1)[0]
    symbol_rows=[]
    for line in section.splitlines():
        fields=[x.strip() for x in line.strip().strip("|").split("|")]
        if len(fields)==4 and fields[0].startswith("$") and fields[0] not in {r"$\xi$",r"$R_0$",r"$w$",r"$\theta$"}:
            symbol_rows.append(fields[0]+" & "+fields[3]+r" \\")
    (paths.TABLES_DIR/"notation.tex").write_text(
        r"\begin{longtable}{ll}"+"\n"+r"\toprule 符号 & 含义 \\ \midrule"+"\n"+
        "\n".join(symbol_rows)+"\n"+r"\bottomrule\end{longtable}",encoding="utf-8")
    print("已从result1.xlsx及验证报告生成第一问表格、数值宏、符号表。")
    return 0


def legacy_all_tables() -> int:
    src_dir = paths.RESULTS_TABLES
    csvs = sorted(src_dir.glob("*.csv")) if src_dir.exists() else []
    if not csvs:
        print(f"⚠️ {paths.rel(src_dir)} 下没有 csv。先跑 make q1..q4。")
        print("   本步骤不需要求解器已实现 —— 求解器就绪后会自动产出。")
        return 0

    paths.TABLES_DIR.mkdir(parents=True, exist_ok=True)
    made = 0
    for csv in csvs:
        caption, label = TABLES.get(csv.stem, (csv.stem, f"tab:{csv.stem}"))
        df = pd.read_csv(csv)
        tex = to_booktabs(df, caption, label)
        dest = paths.TABLES_DIR / f"{csv.stem}.tex"
        dest.write_text(tex, encoding="utf-8")
        print(f"  {paths.rel(csv)}  ->  {paths.rel(dest)}  ({df.shape[0]} 行 x {df.shape[1]} 列)")
        made += 1

    print(f"\n生成 {made} 个表格片段。论文里用 \\input{{tab/<name>}} 引入。")
    print("⚠️ 不要把表格内容手抄进 paper/sections/ —— 数字只有一处来源。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
