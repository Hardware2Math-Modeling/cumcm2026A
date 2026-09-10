"""脚本引导：把仓库根的 src/ 加入 sys.path。

用法（每个 scripts/*.py 的第一行导入）：
    from _bootstrap import ROOT, setup  # noqa: F401
    setup()

这样无需 `pip install -e .`，`python scripts/run_q1.py` 也能直接跑。
tests/ 走的是 pyproject.toml 里的 pythonpath 配置，不需要这个。
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT: Path = Path(__file__).resolve().parents[1]
SRC: Path = ROOT / "src"


def setup() -> None:
    """幂等地把 src/ 放到 sys.path 最前面，并确保输出目录存在。"""
    s = str(SRC)
    if s not in sys.path:
        sys.path.insert(0, s)

    from common import paths

    paths.ensure_output_dirs()
