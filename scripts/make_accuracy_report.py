"""从真实精度审计生成方法说明与科学图，不手抄数值。"""

import json

import numpy as np

from _bootstrap import setup

setup()

from common.paths import ROOT
from common import plotting
import matplotlib.pyplot as plt


def main():
    folder = ROOT / "results" / "validation"
    audit = json.loads((folder / "accuracy.json").read_text(encoding="utf-8"))
    q1 = [x for x in audit["grid"] if x["q"] == "q1"]
    q3 = [x for x in audit["grid"] if x["q"] == "q3"]
    fourth = json.loads((folder / "accuracy-q4.json").read_text(encoding="utf-8"))
    q4 = [dict(q="q4", **x) for x in fourth["grid"]]
    if len(q3) != 4 or len(audit["cross_solver"]) != 2:
        raise RuntimeError("精度验证尚未完成，拒绝生成完成报告")
    if len(q4) != 4 or "cross_solver" not in fourth:
        raise RuntimeError("第四问精度验证尚未完成")
    heat = audit["bessel"]["max_error_by_grid_K"]
    summary = json.loads((ROOT / "results" / "q3_summary.json").read_text(encoding="utf-8"))
    summary4 = json.loads((ROOT / "results" / "q4_summary.json").read_text(encoding="utf-8"))
    records = ["|问题|节点数|相邻网格最大温度差/K|最大含水率差|阈值时间/s|",
               "|---|---:|---:|---:|---:|"]
    for x in q1+q3+q4:
        dT = f'{x["delta_T_K"]:.6e}' if "delta_T_K" in x else "—"
        dC = f'{x["delta_C"]:.6e}' if "delta_C" in x else "—"
        event = f'{x["event_s"]:.8f}' if x["event_s"] is not None else "—"
        records.append(f'|{x["q"]}|{x["n"]}|{dT}|{dC}|{event}|')
    cross = "\n".join(f'- {x["q"]}：温度差 {x["delta_T_K"]:.6e} K，'
                       f'含水率差 {x["delta_C"]:.6e}，阈值时间差 '
                       f'{str(x["delta_event_s"])+" s" if x["delta_event_s"] is not None else "不适用"}。'
                       for x in audit["cross_solver"]+[dict(q="q4", **fourth["cross_solver"])])
    text = f"""# 四问精度改进与编程交接

物理模型：effective-radial-v1；数值版本：accuracy-v2。正式入口为 `python run_all.py`，单问仍可用 `python scripts/run_q1.py` 等。Python 调用须通过所用 Conda 环境运行。

## 选取的方法

|方法|本次处理|理由|
|---|---|---|
|非均匀网格、表面加密|采用，641提升至2561节点|解析陡峭表面梯度；5121节点参考核验|
|方法线、自适应BDF、非线性隐式求解|保留并收紧误差|原程序已有；更换成固定BDF2或CN不保证提升|
|边界时间折点对齐|新增|逐个附件时间节点重启，避免高阶时间公式跨越导数折点|
|Radau IIA|独立时间交叉验证|与BDF比较；共享空间离散，不能当空间独立验证|
|Richardson|用于误差估计|不将外推场作为正式输出，保留有限体积守恒与非负性|
|Bessel谱展开|第1问温度的独立参考|实际分段线性驱动逐段解析卷积；非恒温测试替代物|
|PCHIP/三次样条环境插值|不替代原线性插值|数据之间没有真值，不能由光滑度推出物理预测更准确|
|四阶紧致、谱配点、高阶有限元|不采用为主解法|现有误差已受控；中心与非线性Robin边界需额外验证|
|动态AMR、移动网格|本次不新增|固定域可用离线嵌套加密达到所需精度；动态重映射增加误差|
|二维轴对称|本次不采用|需要定义端面边界与轴向输出位置，属于模型修改|

粘贴材料有以下技术错误：所给紧致二阶导数公式连二次多项式都不满足；标准均匀网格四阶形式的左侧邻点系数为1/10，右侧系数为6/5。`r=R(i/N)^gamma`、gamma>1加密轴心，表面加密应使用现有的`r/R=1-(1-i/(N-1))^2`。光滑函数分段线性插值的函数值误差通常为二阶，并非笼统的一阶；插值阶次也不等于实测驱动的真实性。长与直径之比为6.25，12.5是长与半径之比。

## 正式数值设置

节点2561；BDF；rtol=2e-11、atol=2e-12；前4小时最大步长30 s，之后60 s。附件1每60 s节点重启积分。为防默认启动的显式预测在细表面单元产生负浓度，首步不超过局部浓度变化尺度的1%。所有物性仍从 `correlations.py` 读取，未裁剪负浓度。

这些设置适用于全部四问；第2、3问共享附录3方程、初值与边界，区别为输出频率。第4问采用原收缩材料坐标与附录4物性，还在附件2的半径插值节点重启时间积分。

## 实际验证证据

第1问比较每秒0—1800 s、21个交付位置；第2/3模型比较前3小时每60 s、4—54小时每小时、21个位置，以及连续终点；第4问比较前3小时每60 s、4—48小时每小时、嵌套材料节点与连续终点。场误差仅对已列采样网格成立，不声称逐秒所有时刻的严格上界。表中“—”表示无前一级对比或不适用。

{chr(10).join(records)}

第1问独立Bessel参考使用1024个模态；512与1024模态的最大差为 {audit['bessel']['modes_delta_T_K']:.6e} K。641节点温度最大误差为 {heat['641']:.6e} K，2561节点为 {heat['2561']:.6e} K，误差降低 {heat['641']/heat['2561']:.2f} 倍（相同收紧时间设置下的空间比较）。

2561与5121节点间，第1问温度最大差 {q1[-1]['delta_T_K']:.6e} K，含水率最大差 {q1[-1]['delta_C']:.6e} kg/kg。第二阶Richardson估计2561节点含水率剩余误差约为其4/3，即 {q1[-1]['delta_C']*4/3:.6e} kg/kg；这是渐近误差估计，不是严格物理误差界。

第3问2561与5121节点终点差为 {abs(q3[-1]['delta_event_s']):.6e} s，2561节点剩余误差估计约 {abs(q3[-1]['delta_event_s'])*4/3:.6e} s。正式2561节点阈值时间为 {summary['event_time_s']:.9f} s，即 {summary['event_time_s']/3600:.9f} h；首个严格合格的60 s采样点为 {summary['first_output_below_s']:.0f} s。阈值处等于0.15，严格小于发生在其后，舍入为0.1500不代表未达标。

第4问正式阈值为 {summary4['event_time_s']:.9f} s，即 {summary4['event_time_s']/3600:.9f} h；首个严格达标输出为 {summary4['first_output_below_s']:.0f} s。2561与5121节点的阈值差为 {abs(q4[-1]['delta_event_s']):.6e} s，材料节点含水率最大差为 {q4[-1]['delta_C']:.6e}。含水率相邻网格差约缩小四倍，但最后两级事件时间差未严格呈四倍比例，故不对该终点强行作二阶Richardson误差界声明。固定物理位置超出当时半径时留空，表面列始终使用真实表面值。

同一161节点网格上BDF与Radau差异：
{cross}

机器精度量级的质量收支残差只证明离散收支闭合。无蒸发潜热、有效浓度Robin边界、一维简化与4小时末值外推的结构误差未由本次加密消除。

## 环境、复现与交接

实际环境：Python {audit['python']}，NumPy {audit['numpy']}，SciPy {audit['scipy']}，Conda 26A；没有新增依赖。现有environment.yml声明Python 3.12，本机26A实测为3.11.15，本次如实记录，未自动改装环境。

精度审计：`python scripts/validate_accuracy.py` 和 `python scripts/validate_q4_accuracy.py`；全部输出回读：`python scripts/verify_accuracy_outputs.py`；报告重建：`python scripts/make_accuracy_report.py`。审计缓存位于忽略的outputs目录；删除缓存可完整重跑。单问manifest记录输入SHA256与结果SHA256。完整独立目录复现核验记录于 `results/validation/accuracy-reproduction.json`；以数值数组和工作表内容比较，不要求含生成时间戳的xlsx压缩文件逐字节相同。

论文图：`paper/figs/fig1-accuracy.pdf`。旧第一问正文仍写641节点与旧容差，已在docs/TASKS.md向@paper登记；请用本报告更新相应叙述。建模规格同步已向@model登记。未越过所有权直接修改其正文。

官方算法说明：[SciPy BDF](https://docs.scipy.org/doc/scipy/reference/generated/scipy.integrate.BDF.html)（自动1—5阶），[SciPy Radau](https://docs.scipy.org/doc/scipy/reference/generated/scipy.integrate.Radau.html)（五阶Radau IIA）。
"""
    (folder / "accuracy-methods.md").write_text(text, encoding="utf-8")
    plotting.apply_style()
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.8))
    n = np.array([x["n"] for x in q1])
    axes[0].loglog(n, [heat[str(x)] for x in n], "o-", label="Q1 vs Bessel reference")
    axes[0].set(xlabel="Radial nodes", ylabel="Maximum temperature error (K)")
    axes[1].loglog([x["n"] for x in q3[1:]],
                   [abs(x["delta_event_s"]) for x in q3[1:]], "o-",
                   label="Q3 consecutive-grid difference")
    axes[1].loglog([x["n"] for x in q4[1:]],
                   [abs(x["delta_event_s"]) for x in q4[1:]], "s-",
                   label="Q4 consecutive-grid difference")
    axes[1].set(xlabel="Radial nodes (finer grid)", ylabel="Drying event difference (s)")
    for ax in axes:
        ax.grid(True, which="both", alpha=.25)
        ax.legend(fontsize=9)
    fig.tight_layout()
    (ROOT / "paper" / "figs").mkdir(parents=True, exist_ok=True)
    fig.savefig(ROOT / "paper" / "figs" / "fig1-accuracy.pdf")
    fig.savefig(ROOT / "outputs" / "cache" / "fig1-accuracy.png", dpi=160)
    plt.close(fig)
    print("Accuracy report and figure generated.")


if __name__ == "__main__":
    main()
