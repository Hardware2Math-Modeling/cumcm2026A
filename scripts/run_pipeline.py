"""完整本地复现：计算、拟合、验证、表图、XeLaTeX、ZIP；不联网提交。"""
import argparse
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--skip-compute',action='store_true',help='已完成两种工况计算时，仅更新验证后续交付')
    parser.add_argument('--skip-validation',action='store_true',help='已有对应当前模型的验证报告时跳过昂贵加密重算')
    args=parser.parse_args()
    def python(script,*options):
        subprocess.run([sys.executable,str(ROOT/script),*options],cwd=ROOT,check=True)
    python('scripts/probe_templates.py')
    python('scripts/fit_ambient_temperature.py')
    if not args.skip_compute:
        python('run_all.py')
        python('scripts/run_fitted_scenario.py')
    if not args.skip_validation:
        python('scripts/validate_latent.py')
        python('scripts/validate_fitted_scenario.py')
    python('scripts/audit_q4_boundary_layer.py')
    python('scripts/selfcheck.py')
    for pattern in ('test_numerics.py','test_accuracy.py'):
        subprocess.run([sys.executable,'-m','unittest','discover','-s','tests','-p',pattern,'-v'],cwd=ROOT,check=True)
    python('scripts/verify_accuracy_outputs.py')
    python('scripts/verify_accuracy_outputs.py','--fitted')
    python('scripts/build_paper_assets.py')
    python('paper/build_sources.py')
    subprocess.run(['latexmk','-xelatex','-interaction=nonstopmode','-halt-on-error','-outdir=build','main.tex'],cwd=ROOT/'paper',check=True)
    python('scripts/package_delivery.py')
    return 0


if __name__=='__main__':
    raise SystemExit(main())
