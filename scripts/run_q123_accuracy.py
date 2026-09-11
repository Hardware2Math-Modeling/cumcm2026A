"""重算第1--3问；只读依赖与模板预检，不安装依赖。"""

import importlib
import platform

from _runner import run
from common.io_excel import verify_layout_against_template


def main(questions=("q1", "q3", "q2")):
    print("Python:", platform.python_version(), flush=True)
    for name in ("numpy", "scipy", "pandas", "openpyxl", "matplotlib"):
        module = importlib.import_module(name)
        print(name, module.__version__, flush=True)
    for question in questions:
        problems = verify_layout_against_template(question)
        if problems:
            raise RuntimeError(str(problems))
    for question in questions:
        code = run(question)
        if code:
            return code
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
