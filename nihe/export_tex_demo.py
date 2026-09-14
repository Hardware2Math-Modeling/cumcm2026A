"""Regenerate the LaTeX numbers and compact figure directly from the fitting code."""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np

from fit_boundary import LABELS, analyze

HERE = Path(__file__).resolve().parent


def main() -> int:
    time_s, fields, metadata, analyses = analyze(300, 20260912)
    definitions = []

    def define(name, value):
        definitions.append(r"\newcommand{\nihe" + name + "}{" + str(value) + "}")

    define("Count", metadata["count"])
    define("SourceHash", metadata["sha256"])
    for field, prefix in (("T_amb", "Temp"), ("C_amb", "Moist")):
        analysis = analyses[field]
        curve = analysis["curve"]
        if curve.model != "logistic":
            raise RuntimeError("The selected model changed; revise the LaTeX derivation first.")
        plateau, gap, tau_s, log_shape = curve.parameters
        coefficient = np.exp(log_shape)
        shift = 273.15 if field == "T_amb" else 0
        define(prefix + "Plateau", f"{plateau:.11f}")
        define(prefix + "Display", f"{plateau - shift:.8f}")
        define(prefix + "Amplitude", f"{gap * (1 + coefficient):.11f}")
        define(prefix + "Shape", f"{coefficient:.11f}")
        define(prefix + "Tau", f"{tau_s:.8f}")
        define(prefix + "PlateauPrint", f"{plateau:.8g}")
        define(prefix + "AmplitudePrint", f"{gap * (1 + coefficient):.8g}")
        define(prefix + "ShapePrint", f"{coefficient:.8g}")
        define(prefix + "TauPrint", f"{tau_s:.8g}")
        precision = 4 if field == "T_amb" else 7
        define(prefix + "StablePrint", f"{plateau - shift:.{precision}f}")
        define(prefix + "RMSE", f"{curve.rmse:.8f}")
        interval = analysis["bootstrap"][1]["interval"] - shift
        define(prefix + "Low", f"{interval[0]:.8f}")
        define(prefix + "High", f"{interval[1]:.8f}")
        define(prefix + "Settling", f"{curve.settling_time(0.01) / 3600:.4f}")
        tail_mean = float(np.mean(fields[field][time_s >= 10800]))
        define(prefix + "Mean", f"{tail_mean - shift:.8f}")
        define(prefix + "DeltaMean", f"{plateau - tail_mean:.8f}")
    rows = []
    for index, entry in enumerate(analyses["T_amb"]["comparisons"]):
        moisture_entry = analyses["C_amb"]["comparisons"][index]
        rows.append(
            f"{LABELS[entry['model']]} & {entry['cv_rmse']:.6f} & "
            f"{entry['test_rmse']:.6f} & {moisture_entry['cv_rmse'] * 1e4:.4f} & "
            f"{moisture_entry['test_rmse'] * 1e4:.4f}" + r" \\"
        )
    (HERE / "fit_values.tex").write_text("\n".join(definitions) + "\n", encoding="utf-8")
    table = [
        r"\begin{tabular}{lrrrr}",
        r"\toprule",
        r"& \multicolumn{2}{c}{温度RMSE / K}"
        r"& \multicolumn{2}{c}{浓度RMSE / $(10^{-4}\,\mathrm{kg/kg})$}\\",
        r"\cmidrule(lr){2-3}\cmidrule(lr){4-5}",
        r"模型 & 滚动验证 & 末段测试 & 滚动验证 & 末段测试\\",
        r"\midrule",
        *rows,
        r"\bottomrule",
        r"\end{tabular}",
    ]
    (HERE / "fit_comparison_rows.tex").write_text("\n".join(table) + "\n", encoding="utf-8")
    os.environ.setdefault("MPLCONFIGDIR", str(HERE / ".cache" / "matplotlib"))
    os.environ.setdefault("XDG_CACHE_HOME", str(HERE / ".cache"))
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update(
        {
            "font.family": ["Songti SC", "DejaVu Sans"],
            "axes.unicode_minus": False,
            "font.size": 14,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "pdf.fonttype": 42,
        }
    )
    figure, axes = plt.subplots(1, 2, figsize=(9.2, 3.2), layout="constrained")
    grid_s = np.linspace(0, 21600, 800)
    for index, (field, observations) in enumerate(fields.items()):
        axis = axes[index]
        curve = analyses[field]["curve"]
        shift = 273.15 if field == "T_amb" else 0
        color = "#247C82" if field == "T_amb" else "#19394F"
        axis.axvspan(4, 6, color="#EDF4F5", label="外推区间")
        axis.scatter(time_s / 3600, observations - shift, s=9, color="#8A9399", label="附件观测")
        axis.plot(grid_s / 3600, curve.predict(grid_s) - shift, color=color, lw=1.8, label="Logistic 拟合")
        axis.axhline(curve.plateau - shift, color="#AD613E", ls="--", lw=1, label="拟合平台")
        axis.set(
            xlim=(0, 6),
            xlabel="时间 / h",
            ylabel="烘房温度 / °C" if field == "T_amb" else "水分浓度 / (kg/kg)",
        )
        axis.grid(alpha=0.18)
        axis.legend(loc="lower right", fontsize=13.5, framealpha=0.95)
    figure.savefig(HERE / "fit_for_paper.pdf", metadata={"CreationDate": None, "ModDate": None})
    figure.savefig(HERE / "fit_for_paper.png", dpi=180)
    plt.close(figure)
    print("Generated fit_values.tex, fit_comparison_rows.tex, fit_for_paper.pdf/.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
