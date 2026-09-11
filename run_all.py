"""四问正式复现入口：先预检依赖和模板，再计算及输出。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "scripts"))

from run_q123_accuracy import main as compute_main


def main():
    code = compute_main(("q1", "q3", "q4", "q2"))
    return code

if __name__ == "__main__":
    raise SystemExit(main())
