"""打印 problem/附件/附件3/result1~4.xlsx 的真实结构。

运行： make probe

**开工第一件事就是跑这个**（AGENTS.md 铁律 3：不许猜交付物格式）。
把输出贴进 data/README.md §4 与 docs/INTERFACES.md §6。
"""

from __future__ import annotations

import sys

from _bootstrap import setup

setup()

from common import io_excel, paths  # noqa: E402


def main() -> int:
    print("=" * 72)
    print("交付模板结构探查 —— 以实际文件为准，不要按题目文字描述猜测")
    print("=" * 72)
    for n in (1, 2, 3, 4):
        try:
            print(io_excel.probe_template(f"q{n}"))
        except FileNotFoundError as e:
            print(f"  !! {e}")
        print("-" * 72)

    print()
    print("=" * 72)
    print("附件结构")
    print("=" * 72)
    for n in (1, 2):
        df = io_excel.read_attachment(n)
        t = df["时间"].to_numpy(dtype=float)
        step = float(t[1] - t[0]) if t.size > 1 else float("nan")
        print(
            f"附件{n}: {paths.rel(paths.attachment_path(n))}\n"
            f"  列名={list(df.columns)}  行数={len(df)}\n"
            f"  时间 {t.min():.0f}~{t.max():.0f} s  步长={step:.0f} s"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
