"""提交用总入口。

例：
    python -m submission_code.run --question all
    python -m submission_code.run --question 3 --criterion center

默认把四个 ``resultN.xlsx`` 写入仓库的 ``results/``；用 ``--output`` 可改目录。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

if __package__:
    from .io import write_result
    from .model import Boundary, solve
else:  # 允许直接执行 python submission_code/run.py
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from submission_code.io import write_result
    from submission_code.model import Boundary, solve


def one(question: str, root: Path, output: Path, ambient: str, criterion: str, nodes: int):
    result = solve(
        question,
        Boundary(root, ambient=ambient),
        n=nodes,
        criterion=criterion,
    )
    path = write_result(result, output)
    summary = {
        "question": result.question,
        "ambient": ambient,
        "criterion": criterion,
        "nodes": nodes,
        "event_time_s": result.event_time_s,
        "event_time_h": None if result.event_time_s is None else result.event_time_s / 3600.0,
        "first_output_s": float(result.t[-1]),
        "center_C_final": float(result.C[-1, 0]),
        "max_C_final": float(np_max(result.C[-1])),
        "surface_C_final": float(result.C[-1, -1]),
        "surface_radius_cm_final": float(result.R[-1] * 100.0),
        "file": str(path),
    }
    summary_path = output / f"result{question[-1]}_submission_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"{question}: event={summary['event_time_h']} h, "
        f"output_end={summary['first_output_s']:.0f} s -> {path}"
    )
    return summary


def np_max(values):
    """局部函数避免在入口中混入除模型外的计算细节。"""
    return max(float(x) for x in values)


def main() -> int:
    parser = argparse.ArgumentParser(description="药材烘干四问提交代码")
    parser.add_argument("--question", "-q", default="all", choices=("1", "2", "3", "4", "all"))
    parser.add_argument(
        "--ambient",
        choices=("measured", "fit"),
        default="measured",
        help="环境边界：实测分段线性（默认）或 Logistic 拟合",
    )
    parser.add_argument(
        "--criterion",
        choices=("max", "center"),
        default="max",
        help="q3/q4 终点判据：全场最大值（默认）或中心值",
    )
    parser.add_argument("--nodes", type=int, default=2561, help="材料坐标内部节点数")
    parser.add_argument("--output", type=Path, default=None, help="Excel 输出目录，默认为 results/")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    output = args.output or root / "results"
    questions = ("q1", "q2", "q3", "q4") if args.question == "all" else (f"q{args.question}",)
    all_summary = [one(q, root, output, args.ambient, args.criterion, args.nodes) for q in questions]
    (output / "submission_summary.json").write_text(
        json.dumps(all_summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
