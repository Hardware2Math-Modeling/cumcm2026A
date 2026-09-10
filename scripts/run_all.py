"""Windows/POSIX共用四问复现入口；不含论文第二至四问生成。"""
from _runner import run


if __name__ == "__main__":
    for question in ("q1", "q3", "q4", "q2"):
        code = run(question)
        if code:
            raise SystemExit(code)
