"""从当前正式计算与验证报告生成四问论文插图。"""
from _bootstrap import setup
setup()

def main():
    from build_paper_assets import figures
    return figures()

if __name__ == "__main__":
    raise SystemExit(main())
