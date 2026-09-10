"""路径常量。任何模块都不许自己拼 "../.."，一律从这里取。"""

from __future__ import annotations

from pathlib import Path

# src/common/paths.py -> parents[2] == 仓库根
ROOT: Path = Path(__file__).resolve().parents[2]

# --- 只读冻结的题目原件 ------------------------------------------------------
PROBLEM_DIR: Path = ROOT / "problem"
PROBLEM_PDF: Path = PROBLEM_DIR / "A题.pdf"
ATTACHMENT_DIR: Path = PROBLEM_DIR / "附件"
TEMPLATE_DIR: Path = ATTACHMENT_DIR / "附件3"  # result1~4.xlsx 模板

# --- 数据 --------------------------------------------------------------------
DATA_DIR: Path = ROOT / "data"
DATA_RAW: Path = DATA_DIR / "raw"
DATA_INTERIM: Path = DATA_DIR / "interim"
DATA_PROCESSED: Path = DATA_DIR / "processed"

# --- 代码 --------------------------------------------------------------------
SRC_DIR: Path = ROOT / "src"
SCRIPTS_DIR: Path = ROOT / "scripts"
TESTS_DIR: Path = ROOT / "tests"

# --- 交付物（入库）----------------------------------------------------------
RESULTS_DIR: Path = ROOT / "results"
RESULTS_TABLES: Path = RESULTS_DIR / "tables"  # 论文用展示网格的 csv

# --- 论文 --------------------------------------------------------------------
PAPER_DIR: Path = ROOT / "paper"
FIGURES_DIR: Path = PAPER_DIR / "figs"  # 图片直接写到这里，不要再复制
TABLES_DIR: Path = PAPER_DIR / "tab"  # 生成的 booktabs 片段
PAPER_BUILD: Path = PAPER_DIR / "build"

# --- 可重建产物（gitignore）-------------------------------------------------
OUTPUTS_DIR: Path = ROOT / "outputs"
OUTPUTS_CACHE: Path = OUTPUTS_DIR / "cache"
OUTPUTS_LOGS: Path = OUTPUTS_DIR / "logs"

# --- 文档 --------------------------------------------------------------------
DOCS_DIR: Path = ROOT / "docs"
MODEL_DOCS: Path = DOCS_DIR / "model"


def rel(path: str | Path) -> str:
    """转为相对仓库根的字符串路径。用于日志、xlsx 溯源信息、错误消息。"""
    p = Path(path).resolve()
    try:
        return str(p.relative_to(ROOT))
    except ValueError:
        return str(p)


def ensure_output_dirs() -> None:
    """创建所有可写目录。脚本入口调用一次即可（首次 clone 后目录可能不存在）。"""
    for d in (
        DATA_RAW,
        DATA_INTERIM,
        DATA_PROCESSED,
        RESULTS_DIR,
        RESULTS_TABLES,
        FIGURES_DIR,
        TABLES_DIR,
        PAPER_BUILD,
        OUTPUTS_CACHE,
        OUTPUTS_LOGS,
    ):
        d.mkdir(parents=True, exist_ok=True)


def template_path(problem: str) -> Path:
    """交付模板路径。problem 取 'q1'..'q4' 或 'result1'..'result4'。"""
    n = _problem_number(problem)
    return TEMPLATE_DIR / f"result{n}.xlsx"


def result_path(problem: str) -> Path:
    """交付物路径。"""
    n = _problem_number(problem)
    return RESULTS_DIR / f"result{n}.xlsx"


def attachment_path(n: int) -> Path:
    """附件路径。n=1 -> 烘房条件；n=2 -> 半径随时间变化。"""
    if n not in (1, 2):
        raise ValueError(f"附件编号只支持 1 或 2，收到 {n}")
    return ATTACHMENT_DIR / f"附件{n}.xlsx"


def _problem_number(problem: str) -> int:
    key = str(problem).strip().lower().removeprefix("result").removeprefix("q")
    if key not in {"1", "2", "3", "4"}:
        raise ValueError(f"问题编号只能是 1~4 或 q1~q4 或 result1~result4，收到 {problem!r}")
    return int(key)
