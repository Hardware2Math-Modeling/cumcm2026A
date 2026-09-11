"""源码 -> paper/tab/code_*.tex（lstinputlisting 片段），供论文附录引用。

运行： conda run -n tf2 --no-capture-output python scripts/make_code_appendix.py
      （`make tables` 会顺带调用一次）

设计意图：附录里的源程序**不允许手抄**。手抄必然导致附录与仓库实际代码不同步，
而竞赛规则明确要求「缺少必要的源程序、程序不能运行或运行结果与论文不符，
可能会被取消评奖资格」。故采用生成方式：直接把仓库文件原样排入附录。

产物：
    paper/tab/code_<slug>.tex   片段（\\subsection* + \\lstinputlisting）
    paper/tab/code_<slug>.py    源码本体（供 lstinputlisting 读取，随论文入库）
    paper/tab/code_index.tex    支撑材料文件列表

⚠️ 不要手工编辑 paper/tab/code_*.tex，下次生成就覆盖了。
"""

from __future__ import annotations

import sys

from _bootstrap import setup

setup()

from common import paths  # noqa: E402

#: 需要收进附录的源程序（按阅读顺序）。路径相对仓库根。
#: 只收**支撑模型与结果**的程序；绘图/辅助脚本若不影响结论可略。
FILES: tuple[tuple[str, str], ...] = (
    ("src/common/numerical_settings.py", "正式数值设置（网格与误差容差）"),
    ("src/common/correlations.py", "附录 2/3/4 三套物性公式集与单位校验"),
    ("src/common/boundary.py", "附件 1/2 的读取、分段线性插值与半径不可外推约束"),
    ("src/common/problem_spec.py", "四个问题的规格定义（几何、初值、判据、参数集）"),
    ("src/common/radial.py", "核心求解器：材料坐标有限体积 + 自适应 BDF + 事件检测"),
    ("src/common/export.py", "内部解到交付网格的映射（含问题 4 的域外留空）"),
    ("src/common/io_excel.py", "交付文件写出与格式硬校验"),
    ("src/q1/solver.py", "问题一求解入口"),
    ("src/q4/solver.py", "问题四求解入口（材料坐标与收缩）"),
    ("scripts/_runner.py", "单问执行流程（求解 → 交付 → 展示表 → 清单）"),
    ("scripts/run_all.py", "四问一次性执行入口"),
    ("scripts/make_tables.py", "论文表格与数值宏的生成"),
    ("scripts/make_figs.py", "论文插图的生成"),
    ("scripts/make_code_appendix.py", "本附录自身的生成脚本"),
    ("scripts/validate_numerics.py", "守恒、网格加密与环境外推灵敏度验证"),
    ("scripts/validate_accuracy.py", "网格/时间精度、Bessel 解析解与 Radau 交叉验证"),
    ("scripts/verify_accuracy_outputs.py", "交付文件全单元格回读与 SHA-256 校验"),
    ("tests/test_numerics.py", "数值正确性回归测试"),
)


def _slug(path: str) -> str:
    return path.replace("/", "_").replace(".py", "")


def main() -> int:
    paths.TABLES_DIR.mkdir(parents=True, exist_ok=True)
    missing: list[str] = []

    index = [
        "% 本文件由 scripts/make_code_appendix.py 自动生成，请勿手工编辑",
        "\\subsection*{支撑材料文件列表}",
        "本节列出支撑本论文模型、结果与结论的全部程序与数据文件。"
        "以下源代码均与随文提交的支撑材料一致，可直接运行复现论文中的全部数值结果。",
        "\\begin{itemize}\\itemsep1pt",
    ]

    for rel, title in FILES:
        source = paths.ROOT / rel
        if not source.exists():
            missing.append(rel)
            continue
        body = source.read_text(encoding="utf-8")
        # lstlisting 会把行尾的反斜杠当作续行，Python 源码里极少出现；
        # 制表符统一换成 4 空格，避免 XeLaTeX 下制表位错乱。
        body = body.replace("\t", "    ").replace("\r\n", "\n")
        if not body.endswith("\n"):
            body += "\n"
        (paths.TABLES_DIR / f"code_{_slug(rel)}.py").write_text(body, encoding="utf-8")

        fragment = "\n".join([
            "% 本文件由 scripts/make_code_appendix.py 自动生成，请勿手工编辑",
            "\\subsection*{\\texttt{%s}：%s}" % (rel.replace("_", "\\_"), title),
            "\\addcontentsline{toc}{subsection}{\\texttt{%s}}" % rel.replace("_", "\\_"),
            f"\\lstinputlisting{{tab/code_{_slug(rel)}.py}}",
            "\\par\\medskip",
            "",
        ])
        (paths.TABLES_DIR / f"code_{_slug(rel)}.tex").write_text(fragment, encoding="utf-8")
        index.append("  \\item \\texttt{%s}：%s" % (rel.replace("_", "\\_"), title))

    index += [
        "\\end{itemize}",
        "此外，支撑材料还包含：交付结果文件 \\texttt{results/result1$\\sim$4.xlsx}；"
        "验证报告 \\texttt{results/validation/*.json}（网格加密、时间精度、灵敏度、"
        "解析解对照与独立复算）；论文插图的矢量源文件 \\texttt{paper/figs/*.pdf}；"
        "附件 1、附件 2 的解析结果 \\texttt{data/processed/*.csv}；"
        "以及题面要求的说明见附录~\\ref{app:ai}。",
        "",
    ]
    (paths.TABLES_DIR / "code_index.tex").write_text("\n".join(index), encoding="utf-8")

    print(f"已生成 {len(FILES) - len(missing)} 个源程序片段到 paper/tab/")
    if missing:
        print(f"!! 以下文件不存在，未收进附录：{missing}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
