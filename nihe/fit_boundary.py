"""Fit attachment 1 with monotone, finite-asymptote ambient boundary curves."""

from __future__ import annotations

import argparse
import hashlib
import os
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import openpyxl
import scipy
from scipy.optimize import brentq, least_squares
from scipy.special import expit

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "problem" / "附件" / "附件1.xlsx"
MODELS = ("exponential", "weibull", "logistic", "gompertz", "quadratic")
LABELS = {
    "exponential": "单指数",
    "weibull": "广义指数",
    "logistic": "归一化 Logistic",
    "gompertz": "归一化 Gompertz",
    "quadratic": "二次指数",
}
FIELD_LABELS = {"T_amb": "烘房温度", "C_amb": "烘房水分浓度"}
PARAMETER_NAMES = {
    "exponential": ("plateau", "gap", "tau_s"),
    "weibull": ("plateau", "gap", "tau_s", "power"),
    "logistic": ("plateau", "gap", "tau_s", "log_shape"),
    "gompertz": ("plateau", "gap", "tau_s", "log_shape"),
    "quadratic": ("plateau", "gap", "tau_s", "curvature"),
}


def read_attachment(path: Path = SOURCE) -> tuple[np.ndarray, dict, dict]:
    """Read original measurements without editing, filtering, or imputing them."""
    path = Path(path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        if workbook.sheetnames != ["Sheet1"]:
            raise ValueError(f"Unexpected worksheets: {workbook.sheetnames}")
        rows = list(workbook["Sheet1"].values)
    finally:
        workbook.close()
    if tuple(rows[0]) != ("时间", "温度", "水分浓度"):
        raise ValueError(f"Unexpected attachment headers: {rows[0]}")
    if any(
        len(row) != 3
        or any(isinstance(value, bool) or not isinstance(value, (int, float)) for value in row)
        for row in rows[1:]
    ):
        raise ValueError("Every observation must have three numeric, nonempty cells.")
    values = np.asarray(rows[1:], dtype=float)
    if len(values) < 40 or not np.isfinite(values).all():
        raise ValueError("Need at least 40 finite observations.")
    time_s = values[:, 0]
    if time_s[0] != 0 or np.any(np.diff(time_s) <= 0):
        raise ValueError("Time must start at zero and increase strictly.")
    if not np.allclose(np.diff(time_s), np.diff(time_s)[0]):
        raise ValueError("Block bootstrap requires regularly spaced observations.")
    fields = {"T_amb": values[:, 1] + 273.15, "C_amb": values[:, 2].copy()}
    if np.any(fields["T_amb"] <= 0) or np.any(fields["C_amb"] < 0):
        raise ValueError("Nonphysical observations: nonpositive Kelvin or negative moisture.")
    if any(np.ptp(observations) <= 0 for observations in fields.values()):
        raise ValueError("A constant series cannot identify a transient curve.")
    metadata = {
        "sha256": digest,
        "sheet": "Sheet1",
        "range": f"A1:C{len(rows)}",
        "count": len(values),
        "dt_s": float(np.diff(time_s)[0]),
        "end_s": float(time_s[-1]),
    }
    return time_s, fields, metadata


def remaining(model: str, time_s, tau_s: float, shape: float = 1.0):
    """Return a dimensionless fraction decreasing from one to zero."""
    time_s = np.asarray(time_s, dtype=float)
    if not np.isfinite(time_s).all() or np.any(time_s < 0):
        raise ValueError("Prediction times must be finite and nonnegative seconds.")
    if tau_s <= 0:
        raise ValueError("tau_s must be positive.")
    scaled_time = time_s / tau_s
    with np.errstate(over="ignore"):
        if model == "exponential":
            return np.exp(-scaled_time)
        if model == "weibull":
            if shape <= 0:
                raise ValueError("Weibull power must be positive.")
            return np.exp(-scaled_time**shape)
        if model == "logistic":
            return expit(-scaled_time - shape) / expit(-shape)
        if model == "gompertz":
            coefficient = np.exp(shape)
            return -np.expm1(-coefficient * np.exp(-scaled_time)) / -np.expm1(-coefficient)
        if model == "quadratic":
            if shape < 0:
                raise ValueError("Quadratic curvature must be nonnegative.")
            if shape == 0:
                return np.exp(-scaled_time)
            return np.exp(-scaled_time - shape * scaled_time**2)
    raise ValueError(f"Unknown model: {model}")


@dataclass
class Curve:
    model: str
    parameters: np.ndarray
    rmse: float
    aicc: float
    residual_lag1: float
    bound_hits: tuple[str, ...]
    failed_starts: int

    @property
    def plateau(self) -> float:
        return float(self.parameters[0])

    def predict(self, time_s):
        plateau, gap, tau_s = self.parameters[:3]
        shape = self.parameters[3] if len(self.parameters) > 3 else 1.0
        return plateau - gap * remaining(self.model, time_s, tau_s, shape)

    def settling_time(self, fraction: float = 0.01) -> float:
        """Time after which the remaining gap is at most fraction of the initial gap."""
        if not 0 < fraction < 1:
            raise ValueError("fraction must be between zero and one.")
        tau_s = self.parameters[2]
        shape = self.parameters[3] if len(self.parameters) > 3 else 1.0
        return float(
            brentq(
                lambda time_s: remaining(self.model, time_s, tau_s, shape) - fraction,
                0.0,
                tau_s * 1e8,
            )
        )


def fit_curve(
    model: str,
    time_s: np.ndarray,
    observations: np.ndarray,
    *,
    loss: str = "linear",
    warm: Curve | None = None,
) -> Curve:
    """Constrained multi-start nonlinear regression, with training-only scaling."""
    if model not in MODELS:
        raise ValueError(f"Unknown model: {model}")
    time_s = np.asarray(time_s, dtype=float)
    observations = np.asarray(observations, dtype=float)
    if (
        time_s.ndim != 1
        or observations.shape != time_s.shape
        or len(time_s) < 10
        or not np.isfinite(time_s).all()
        or not np.isfinite(observations).all()
        or time_s[0] != 0
        or np.any(np.diff(time_s) <= 0)
    ):
        raise ValueError("Fit requires matching finite 1-D series, starting at t=0.")
    offset = float(np.min(observations))
    scale = float(np.ptp(observations))
    if scale <= 0:
        raise ValueError("Cannot fit a transient to a constant series.")
    normalized = (observations - offset) / scale
    duration = float(time_s[-1])
    lower = [0.0, 0.0, float(np.min(np.diff(time_s))) / duration / 10]
    upper = [5.0, 10.0, 100.0]
    shapes = [1.0]
    if model == "weibull":
        lower += [0.25]
        upper += [5.0]
        shapes = [0.7, 1.3, 2.0]
    elif model in ("logistic", "gompertz"):
        lower += [-8.0]
        upper += [5.0]
        shapes = [-2.0, 0.0, 2.0]
    elif model == "quadratic":
        lower += [0.0]
        upper += [20.0]
        shapes = [0.0, 0.5, 2.0]
    lower = np.asarray(lower)
    upper = np.asarray(upper)
    starts = []
    for tau_fraction in (0.15, 0.4):
        for shape in shapes:
            initial = [1.01, 1.01, tau_fraction]
            if model != "exponential":
                initial.append(shape)
            starts.append(np.asarray(initial))
    if warm is not None:
        initial = warm.parameters.copy()
        initial[0] = (initial[0] - offset) / scale
        initial[1] /= scale
        initial[2] /= duration
        starts = [np.clip(initial, lower + 1e-9, upper - 1e-9)]

    def residual(parameters):
        shape = parameters[3] if len(parameters) > 3 else 1.0
        prediction = parameters[0] - parameters[1] * remaining(
            model, time_s, parameters[2] * duration, shape
        )
        return prediction - normalized

    candidates = []
    failed_starts = 0
    for initial in starts:
        result = least_squares(
            residual,
            initial,
            bounds=(lower, upper),
            loss=loss,
            f_scale=0.01,
            ftol=1e-11,
            xtol=1e-11,
            gtol=1e-11,
            max_nfev=3000,
        )
        if result.success and np.isfinite(result.fun).all():
            candidates.append(result)
        else:
            failed_starts += 1
    if not candidates:
        raise RuntimeError(f"All {failed_starts} starts failed for {model}.")
    result = min(candidates, key=lambda candidate: candidate.cost)
    normalized_parameters = result.x
    bound_hits = tuple(
        name
        for index, name in enumerate(PARAMETER_NAMES[model])
        if min(
            normalized_parameters[index] - lower[index],
            upper[index] - normalized_parameters[index],
        )
        < 1e-5 * (upper[index] - lower[index])
    )
    parameters = normalized_parameters.copy()
    parameters[0] = offset + scale * parameters[0]
    parameters[1] *= scale
    parameters[2] *= duration
    residuals = residual(normalized_parameters) * scale
    count = len(time_s)
    parameter_count = len(parameters) + 1
    mse = float(np.mean(residuals**2))
    aicc = count * np.log(max(mse, np.finfo(float).tiny)) + 2 * parameter_count
    aicc += 2 * parameter_count * (parameter_count + 1) / (count - parameter_count - 1)
    lag1 = 0.0
    if np.std(residuals[:-1]) > 0 and np.std(residuals[1:]) > 0:
        lag1 = float(np.corrcoef(residuals[:-1], residuals[1:])[0, 1])
    return Curve(
        model, parameters, np.sqrt(mse), float(aicc), lag1, bound_hits, failed_starts
    )


def compare_models(time_s: np.ndarray, observations: np.ndarray) -> tuple[list, str]:
    """Choose by expanding-window validation; reserve the final eighth for testing."""
    duration = float(time_s[-1])
    comparisons = []
    for model in MODELS:
        folds = []
        for fraction in (0.5, 0.625, 0.75):
            train = time_s <= duration * fraction
            valid = (time_s > duration * fraction) & (
                time_s <= duration * (fraction + 0.125)
            )
            curve = fit_curve(model, time_s[train], observations[train])
            errors = curve.predict(time_s[valid]) - observations[valid]
            folds.append(
                {
                    "train_end_s": float(time_s[train][-1]),
                    "rmse": float(np.sqrt(np.mean(errors**2))),
                    "plateau": curve.plateau,
                    "bound_hits": curve.bound_hits,
                    "failed_starts": curve.failed_starts,
                }
            )
        train = time_s <= duration * 0.875
        test = ~train
        test_curve = fit_curve(model, time_s[train], observations[train])
        test_errors = test_curve.predict(time_s[test]) - observations[test]
        curve = fit_curve(model, time_s, observations)
        comparisons.append(
            {
                "model": model,
                "curve": curve,
                "folds": folds,
                "cv_rmse": float(np.sqrt(np.mean([fold["rmse"] ** 2 for fold in folds]))),
                "test_rmse": float(np.sqrt(np.mean(test_errors**2))),
                "test_curve": test_curve,
            }
        )
    selected = min(comparisons, key=lambda entry: entry["cv_rmse"])["model"]
    return comparisons, selected


def bootstrap_plateau(
    curve: Curve,
    time_s: np.ndarray,
    observations: np.ndarray,
    *,
    repetitions: int,
    block_length: int,
    seed: int,
) -> dict:
    """Circular residual-block bootstrap, conditional on one selected model."""
    if repetitions < 20 or not 1 <= block_length <= len(time_s):
        raise ValueError("Need >=20 bootstrap replicates and a valid block length.")
    generator = np.random.default_rng(seed)
    fitted = curve.predict(time_s)
    residuals = observations - fitted
    residuals -= np.mean(residuals)
    plateaus = []
    failures = []
    bound_hits = 0
    for replicate in range(repetitions):
        starts = generator.integers(0, len(time_s), size=int(np.ceil(len(time_s) / block_length)))
        indices = (starts[:, None] + np.arange(block_length)) % len(time_s)
        resampled = fitted + residuals[indices.ravel()[: len(time_s)]]
        try:
            refit = fit_curve(curve.model, time_s, resampled, warm=curve)
        except RuntimeError as error:
            failures.append(f"replicate={replicate}: {error}")
            continue
        bound_hits += bool(refit.bound_hits)
        plateaus.append(refit.plateau)
    if len(plateaus) < 0.95 * repetitions:
        raise RuntimeError(f"Bootstrap unreliable: {len(failures)}/{repetitions} failed.")
    return {
        "interval": np.quantile(plateaus, [0.025, 0.975]),
        "success": len(plateaus),
        "failures": failures,
        "bound_hits": bound_hits,
        "block_length": block_length,
        "seed": seed,
    }


@dataclass
class FittedBoundary:
    T_amb: Curve
    C_amb: Curve

    def ambient(self, time_s):
        """Return ambient temperature (K) and moisture concentration (kg/kg)."""
        return self.T_amb.predict(time_s), self.C_amb.predict(time_s)


def fit_boundary(path: Path = SOURCE) -> FittedBoundary:
    """Select and refit both curves from the workbook, without writing any files."""
    time_s, fields, _ = read_attachment(path)
    curves = {}
    for field, observations in fields.items():
        comparisons, selected = compare_models(time_s, observations)
        curves[field] = next(entry["curve"] for entry in comparisons if entry["model"] == selected)
    return FittedBoundary(**curves)


def analyze(repetitions: int, seed: int) -> tuple[np.ndarray, dict, dict, dict]:
    time_s, fields, metadata = read_attachment()
    analyses = {}
    for field_index, (field, observations) in enumerate(fields.items()):
        comparisons, selected = compare_models(time_s, observations)
        curve = next(entry["curve"] for entry in comparisons if entry["model"] == selected)
        sensitivity = []
        for fraction in (0.5, 0.625, 0.75, 0.875, 1.0):
            mask = time_s <= time_s[-1] * fraction
            refit = fit_curve(selected, time_s[mask], observations[mask])
            sensitivity.append((float(time_s[mask][-1]), refit))
        intervals = [
            bootstrap_plateau(
                curve,
                time_s,
                observations,
                repetitions=repetitions,
                block_length=block_length,
                seed=seed + 100 * field_index + block_length,
            )
            for block_length in (1, 6, 12)
        ]
        robust = fit_curve(selected, time_s, observations, loss="soft_l1")
        analyses[field] = {
            "comparisons": comparisons,
            "curve": curve,
            "sensitivity": sensitivity,
            "bootstrap": intervals,
            "robust": robust,
        }
    if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != metadata["sha256"]:
        raise RuntimeError("The source workbook changed during analysis.")
    return time_s, fields, metadata, analyses


def plot_results(time_s, fields, analyses) -> None:
    os.environ.setdefault("MPLCONFIGDIR", str(HERE / ".cache" / "matplotlib"))
    os.environ.setdefault("XDG_CACHE_HOME", str(HERE / ".cache"))
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.alpha": 0.18,
            "figure.dpi": 150,
        }
    )
    colors = ("#d26439", "#277f9d")
    figure, axes = plt.subplots(2, 2, figsize=(11, 7), layout="constrained")
    grid_s = np.linspace(0, 6 * 3600, 1000)
    for row, (field, observations) in enumerate(fields.items()):
        color = colors[row]
        analysis = analyses[field]
        curve = analysis["curve"]
        shift = 273.15 if field == "T_amb" else 0.0
        unit = "Temperature (°C)" if field == "T_amb" else "Moisture concentration (kg/kg)"
        axis = axes[row, 0]
        axis.axvspan(time_s[-1] / 3600, 6, color="#f4e6ce", alpha=0.6, label="Extrapolation")
        axis.scatter(time_s / 3600, observations - shift, s=9, color="#526173", alpha=0.6, label="Observed")
        axis.plot(grid_s / 3600, curve.predict(grid_s) - shift, color=color, lw=2, label=curve.model)
        axis.axhline(curve.plateau - shift, color=color, ls="--", lw=1.2, label="Fitted asymptote")
        axis.set(xlabel="Time (h)", ylabel=unit, xlim=(0, 6))
        axis.set_title(f"{field}: asymptote = {curve.plateau - shift:.6f}", loc="left")
        axis.legend(fontsize=8, loc="lower right")
        axis = axes[row, 1]
        tail = time_s >= 2.5 * 3600
        axis.scatter(time_s[tail] / 3600, observations[tail] - shift, s=12, color="#526173", alpha=0.6)
        axis.plot(grid_s / 3600, curve.predict(grid_s) - shift, color=color, lw=2)
        axis.axhline(curve.plateau - shift, color=color, ls="--", lw=1.2)
        interval = analysis["bootstrap"][1]["interval"] - shift
        axis.axhspan(*interval, color=color, alpha=0.16, label="95% asymptote interval (block=6)")
        axis.axvline(time_s[-1] / 3600, color="#526173", ls=":", lw=1)
        margin = np.ptp(observations[tail]) * 0.15
        axis.set(
            xlabel="Time (h)",
            ylabel=unit,
            xlim=(2.5, 6),
            ylim=(min(observations[tail].min() - shift, interval[0]) - margin,
                  max(observations[tail].max() - shift, interval[1]) + margin),
        )
        axis.set_title("Plateau detail (band is not a prediction interval)", loc="left", fontsize=10)
        axis.legend(fontsize=8, loc="lower right")
    figure.suptitle(
        f"Attachment 1 | Ambient boundary curves fitted from {len(time_s)} observations",
        fontsize=14,
    )
    for suffix in ("png", "pdf"):
        figure.savefig(HERE / f"fitted_curves.{suffix}", bbox_inches="tight")
    plt.close(figure)

    figure, axes = plt.subplots(2, 2, figsize=(11, 7), layout="constrained")
    for row, (field, observations) in enumerate(fields.items()):
        color = colors[row]
        analysis = analyses[field]
        curve = analysis["curve"]
        axis = axes[row, 0]
        for entry in analysis["comparisons"]:
            axis.plot(
                time_s / 3600,
                observations - entry["curve"].predict(time_s),
                lw=1,
                alpha=0.9 if entry["model"] == curve.model else 0.5,
                label=entry["model"],
            )
        axis.axhline(0, color="#263645", lw=1)
        axis.set(xlabel="Time (h)", ylabel="Observed - fitted (K)" if field == "T_amb" else "Observed - fitted (kg/kg)")
        axis.set_title(f"{field}: residual comparison", loc="left")
        axis.legend(fontsize=8)
        axis = axes[row, 1]
        entries = analysis["comparisons"]
        positions = np.arange(len(entries))
        axis.bar(positions - 0.18, [entry["cv_rmse"] for entry in entries], 0.36, color=color, label="Rolling validation")
        axis.bar(positions + 0.18, [entry["test_rmse"] for entry in entries], 0.36, color="#abb8c2", label="Final 0.5 h test")
        axis.set_xticks(positions, [entry["model"] for entry in entries], rotation=20)
        axis.set(ylabel="RMSE (K)" if field == "T_amb" else "RMSE (kg/kg)", yscale="log")
        axis.set_title("Selection uses rolling validation only", loc="left")
        axis.legend(fontsize=8)
    for suffix in ("png", "pdf"):
        figure.savefig(HERE / f"model_diagnostics.{suffix}", bbox_inches="tight")
    plt.close(figure)


def write_report(time_s, fields, metadata, analyses, repetitions, seed) -> None:
    lines = [
        "# 问题二：从附件 1 拟合烘房稳定温度与水分浓度",
        "",
        "## 1. 结论与数据来源",
        "",
        "本报告由 `fit_boundary.py` 实际运行生成，不把末次观测、尾段均值或经验设定值当作拟合平台。",
        "拟合对象是环境边界 `T_amb(t)`、`C_amb(t)`，对应项目符号 "
        "$T_\\infty(t)$、$C_\\infty(t)$，不是药材内部的 $T(r,t)$、$C(r,t)$。",
        "**这里的“湿度”是附件标注的水分浓度（kg/kg），不是相对湿度（%）。**",
        "",
        f"- 原件：`problem/附件/附件1.xlsx`，`{metadata['sheet']}!{metadata['range']}`。",
        f"- SHA-256：`{metadata['sha256']}`。",
        f"- 共 {metadata['count']} 行观测，时间 {time_s[0]:.0f}–{time_s[-1]:.0f} s，间隔 {metadata['dt_s']:.0f} s。",
        "- 读取后不删点、不插补、不平滑原始观测；温度在读取边界转换为 K，计算时间一律 s。",
        "- 题意依据：`problem/A题.pdf` 第 2 页问题二、第 3 页附录 1。"
        "附件 2 是半径数据，不作为温湿环境的拟合输入。",
        "- 问题二展示的前 3 h 全部在实测区间内；2–3 天的全过程需要额外的环境外推假设。",
        "",
        "| 拟合对象 | 所选模型 | 拟合稳定值 | 块长 6 的近似 95% 平台区间 | 全样本 RMSE | 末段测试 RMSE |",
        "|---|---|---:|---|---:|---:|",
    ]
    for field, analysis in analyses.items():
        curve = analysis["curve"]
        shift = 273.15 if field == "T_amb" else 0.0
        unit = "°C" if field == "T_amb" else "kg/kg"
        interval = analysis["bootstrap"][1]["interval"] - shift
        selected = next(entry for entry in analysis["comparisons"] if entry["model"] == curve.model)
        lines.append(
            f"| {FIELD_LABELS[field]} | {LABELS[curve.model]} | {curve.plateau - shift:.8f} {unit} "
            f"| [{interval[0]:.8f}, {interval[1]:.8f}] {unit} "
            f"| {curve.rmse:.8g} | {selected['test_rmse']:.8g} |"
        )
    lines += [
        "",
        "温度误差的数值单位为 K（与 °C 温差相同），水分浓度误差单位为 kg/kg。"
        "较多小数用于复算，不代表测量精度或长期预测精度。",
        "",
        "![拟合曲线及平台细节](fitted_curves.png)",
        "",
        "## 2. 候选曲线与约束",
        "",
        "每一列独立拟合，统一写成“**平台 − 初始差值 × 剩余比例**”。"
        "下表中的 `plateau`、`gap`、`tau_s`、`power`、`log_shape`、`curvature` "
        "仅为本目录的拟合参数名，不改项目正式物理符号表。",
        "所有模型均满足：初值为 `plateau-gap`，当时间趋于无穷时趋于 `plateau`，"
        "且非负 `gap` 下单调上升；波动被保留在残差中，不要求拟合线穿过每个观测点。",
        "",
        "| 模型 | 剩余比例（`t` 为秒） | 均值模型参数数 |",
        "|---|---|---:|",
        "| 单指数 | `exp(-t/tau_s)` | 3 |",
        "| 广义指数 | `exp(-(t/tau_s)**power)` | 4 |",
        "| 归一化 Logistic | `(1+exp(log_shape))/(1+exp(log_shape+t/tau_s))` | 4 |",
        "| 归一化 Gompertz | `(1-exp(-exp(log_shape)*exp(-t/tau_s)))/(1-exp(-exp(log_shape)))` | 4 |",
        "| 二次指数 | `exp(-t/tau_s-curvature*(t/tau_s)**2)` | 4 |",
        "",
        "Logistic 用 `expit` 等价实现，Gompertz 用 `expm1` 避免小量相减。"
        "广义指数 `power<1` 时起点斜率可能无界，因此它只是候选经验曲线，不解释为设备动力学。",
        "",
        "采用 SciPy `least_squares` 的带界非线性最小二乘，多组初值求解并取最小目标值。"
        "每次拟合仅用自己的训练集极差归一化，避免时间验证泄漏。"
        "归一化平台界为 [0,5]，差值 [0,10]，时间尺度为 [采样间隔/10, 100×训练时长]；"
        "`power` 界为 [0.25,5]，`log_shape` 为 [-8,5]，`curvature` 为 [0,20]。"
        "这些是计算搜索界而非题目物性参数，未指定稳定温度或浓度；触界情况在下方明确记录。",
        "",
        "不使用神经网络：本任务只有两条短单变量序列，需要有限极限和可解释外推。"
        "这里直接比较具有这些约束的低维曲线，不声称机器学习不能拟合。",
        "",
        "## 3. 时间验证与模型比较",
        "",
        "不随机打乱时间。三个扩展训练窗口分别为 0–2 h、0–2.5 h、0–3 h，"
        "各自预测紧接着的 0.5 h，合并为滚动验证 RMSE，**只按该分数选模型**。"
        "最后 3.5–4 h 不参与选择，用 0–3.5 h 重新拟合后评估末段测试误差。"
        "选型结束才用全部 0–4 h 估计最终平台。最后半小时虽提供独立于选型的误差检查，"
        "但仍不能验证 72 h 外推；本报告也展示其他候选的测试分数，不据此重新选型。",
        "",
        "AICc 仅辅助诊断：按高斯独立误差计算，参数数包含误差方差。"
        "自相关较强时其假设不成立，不能只看 AICc 或全样本误差做决定。",
    ]
    for field, analysis in analyses.items():
        shift = 273.15 if field == "T_amb" else 0.0
        lines += [
            "",
            f"### {FIELD_LABELS[field]}",
            "",
            "| 模型 | 平台（°C 或 kg/kg） | 全样本 RMSE | 滚动验证 RMSE | 末段测试 RMSE | AICc | 残差一阶相关 | 全样本触界 |",
            "|---|---:|---:|---:|---:|---:|---:|---|",
        ]
        for entry in analysis["comparisons"]:
            curve = entry["curve"]
            lines.append(
                f"| {LABELS[curve.model]} | {curve.plateau - shift:.8f} "
                f"| {curve.rmse:.8g} | {entry['cv_rmse']:.8g} "
                f"| {entry['test_rmse']:.8g} | {curve.aicc:.3f} | {curve.residual_lag1:.4f} "
                f"| {', '.join(curve.bound_hits) or '无'} |"
            )
        ranked = sorted(analysis["comparisons"], key=lambda entry: entry["cv_rmse"])
        improvement = 100 * (1 - ranked[0]["cv_rmse"] / ranked[1]["cv_rmse"])
        lines += [
            "",
            f"所选模型相对第二名（{LABELS[ranked[1]['model']]}）的滚动验证 RMSE 仅降低 "
            f"{improvement:.3f}%。这是候选集合内的数值排序，不是模型唯一正确或统计显著优胜的证明。"
            "候选平台的差异可作为模型形式敏感性的对照，不能当作另一种置信区间。",
        ]
        lines += [
            "",
            "| 模型 | 2–2.5 h 验证 RMSE | 2.5–3 h 验证 RMSE | 3–3.5 h 验证 RMSE |",
            "|---|---:|---:|---:|",
        ]
        for entry in analysis["comparisons"]:
            lines.append(
                f"| {LABELS[entry['model']]} | "
                + " | ".join(f"{fold['rmse']:.8g}" for fold in entry["folds"])
                + " |"
            )
    lines += [
        "",
        "![模型残差与验证误差](model_diagnostics.png)",
        "",
        "## 4. 最终参数、稳定时间与数值核对",
        "",
        "以下参数为全样本拟合值：温度平台、差值使用 K，浓度使用 kg/kg，时间尺度使用 s。"
        "调用时保留内部完整浮点数；本表保留 12 位有效数字供复算。",
        "",
        "| 对象 | 参数 | 数值 |",
        "|---|---|---:|",
    ]
    for field, analysis in analyses.items():
        curve = analysis["curve"]
        for index, name in enumerate(PARAMETER_NAMES[curve.model]):
            value = curve.parameters[index]
            lines.append(f"| `{field}` | `{name}` | {value:.12g} |")
    if all(analysis["curve"].model == "logistic" for analysis in analyses.values()):
        lines += [
            "",
            "本次两条曲线均为 Logistic。将参数代入，下面以 °C、kg/kg 展示，"
            "其中 `t` 的单位仍为秒；进入 PDE 前温度须加 273.15：",
            "",
        ]
        for field, analysis in analyses.items():
            plateau, gap, tau_s, log_shape = analysis["curve"].parameters
            shift = 273.15 if field == "T_amb" else 0.0
            coefficient = np.exp(log_shape)
            symbol = r"T_\infty(t)\;[{}^\circ\mathrm{C}]" if field == "T_amb" else r"C_\infty(t)"
            lines += [
                "$$",
                f"{symbol} = {plateau - shift:.12g}"
                + rf" - \frac{{{gap * (1 + coefficient):.12g}}}"
                + rf"{{1 + {coefficient:.12g}\exp(t/{tau_s:.12g})}}.",
                "$$",
                "",
            ]
    lines += [
        "",
        "“稳定”没有唯一时刻。以下采用自定的相对判据：剩余平台差不超过拟合初始差值的 1% 或 0.1%。"
        "这不是题目给定的阶段切换条件；全过程建议使用连续曲线，不在这个时刻突然切换常数。",
        "",
        "| 对象 | 1% 判据时刻 / h | 0.1% 判据时刻 / h | 初始拟合值 | 最后观测值 | 最后 1 h 均值 |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for field, analysis in analyses.items():
        curve = analysis["curve"]
        shift = 273.15 if field == "T_amb" else 0.0
        lines.append(
            f"| `{field}` | {curve.settling_time(0.01) / 3600:.6f} "
            f"| {curve.settling_time(0.001) / 3600:.6f} | {float(curve.predict(0)) - shift:.8f} "
            f"| {fields[field][-1] - shift:.8f} | {np.mean(fields[field][time_s >= time_s[-1] - 3600]) - shift:.8f} |"
        )
    lines += [
        "",
        "上表温度绝对值以 °C 展示，浓度以 kg/kg 展示。末次值、尾均值只作对照，不进入平台约束。",
        "",
        "| 时间 / h | 拟合烘房温度 / °C | 拟合水分浓度 / (kg/kg) | 证据类型 |",
        "|---|---:|---:|---|",
    ]
    for hour in (0, 0.5, 1, 1.5, 2, 2.5, 3, 4, 6, 24, 48, 72):
        temperature = float(analyses["T_amb"]["curve"].predict(hour * 3600)) - 273.15
        concentration = float(analyses["C_amb"]["curve"].predict(hour * 3600))
        lines.append(
            f"| {hour:g} | {temperature:.8f} | {concentration:.8f} "
            f"| {'实测区间内的拟合' if hour * 3600 <= time_s[-1] else '无实测验证的外推'} |"
        )
    lines += [
        "",
        "## 5. 不确定性与稳健性",
        "",
        f"随机基准种子为 {seed}，每个对象、每种块长进行 {repetitions} 次残差重采样。"
        "在固定拟合时刻上循环抽取连续残差块，叠加到拟合曲线上重新拟合；"
        "重采样是统计诊断，不作为新观测。取平台分布的 2.5% 与 97.5% 分位数。"
        "块长 1（独立残差对照）、6、12 个采样点是本分析的敏感性设置，不是题目参数。",
        "",
        "**这些是给定模型及残差平稳假设下的近似平台区间，不是未来单点预测区间，"
        "也不包含模型选择、测量系统偏差和 4 h 后控制工况变化。**"
        "若残差有系统形状或自相关，重采样区间不能修复模型误设。",
        "",
        "| 对象 | 块长 / 点 | 近似 95% 平台区间（°C 或 kg/kg） | 成功次数 | 触界次数 | 实际随机种子 |",
        "|---|---:|---|---:|---:|---:|",
    ]
    warnings = []
    for field, analysis in analyses.items():
        shift = 273.15 if field == "T_amb" else 0.0
        for result in analysis["bootstrap"]:
            interval = result["interval"] - shift
            lines.append(
                f"| `{field}` | {result['block_length']} | [{interval[0]:.8f}, {interval[1]:.8f}] "
                f"| {result['success']}/{repetitions} | {result['bound_hits']} | {result['seed']} |"
            )
            warnings.extend(f"{field} bootstrap: {failure}" for failure in result["failures"])
        for entry in analysis["comparisons"]:
            checks = [("full", entry["curve"]), ("test_train", entry["test_curve"])]
            for context, curve in checks:
                if curve.bound_hits or curve.failed_starts:
                    warnings.append(
                        f"{field}/{curve.model}/{context}: bounds={curve.bound_hits}, "
                        f"failed_starts={curve.failed_starts}"
                    )
            for fold in entry["folds"]:
                if fold["bound_hits"] or fold["failed_starts"]:
                    warnings.append(
                        f"{field}/{entry['model']}/train_end={fold['train_end_s']}: "
                        f"bounds={fold['bound_hits']}, failed_starts={fold['failed_starts']}"
                    )
        checks = [(f"cutoff_{end_s:g}s", curve) for end_s, curve in analysis["sensitivity"]]
        checks.append(("soft_l1", analysis["robust"]))
        for context, curve in checks:
            if curve.bound_hits or curve.failed_starts:
                warnings.append(
                    f"{field}/{curve.model}/{context}: bounds={curve.bound_hits}, "
                    f"failed_starts={curve.failed_starts}"
                )
    lines += [
        "",
        "### 截断观测时长的敏感性",
        "",
        "固定最终所选模型，仅改变用于估计的观测时长；此表不是第二次模型选择。",
        "",
        "| 训练到 / h | 温度平台 / °C | 浓度平台 / (kg/kg) |",
        "|---|---:|---:|",
    ]
    for index, temperature_item in enumerate(analyses["T_amb"]["sensitivity"]):
        concentration_item = analyses["C_amb"]["sensitivity"][index]
        lines.append(
            f"| {temperature_item[0] / 3600:g} | {temperature_item[1].plateau - 273.15:.8f} "
            f"| {concentration_item[1].plateau:.8f} |"
        )
    lines += [
        "",
        "### 稳健损失对照",
        "",
        "在同一归一化尺度用 `soft_l1` 重拟合，`f_scale=0.01` 为训练极差的 1%，"
        "不删除大残差观测，也不替代已选的普通最小二乘主结果。",
        "",
        "| 对象 | 普通最小二乘平台 | soft_l1 平台 | 两者之差 |",
        "|---|---:|---:|---:|",
    ]
    for field, analysis in analyses.items():
        shift = 273.15 if field == "T_amb" else 0.0
        lines.append(
            f"| `{field}` | {analysis['curve'].plateau - shift:.8f} "
            f"| {analysis['robust'].plateau - shift:.8f} "
            f"| {analysis['robust'].plateau - analysis['curve'].plateau:.8g} |"
        )
    lines += ["", "### 求解告警", ""]
    lines += [f"- `{warning}`" for warning in sorted(set(warnings))] or [
        "- 候选拟合、时间验证与截断拟合未发现失败初值或参数触界；bootstrap 成功与触界次数见表。"
    ]
    lines += [
        "",
        "## 6. 问题二接入方式与范围",
        "",
        "- 推荐在全过程边界中使用 `FittedBoundary.ambient(time_s)` 的连续输出，"
        "温度返回 K、水分浓度返回 kg/kg；平台值可用于描述长期恒温环境，但不应从 t=0 就替换为常数。",
        "- 初始环境读数视为含噪观测，因此初值也参与拟合，未强制穿过附件首点。"
        "题目给定的药材初始温度与干基含水率不因此改变。",
        "- 4 h 以后继续趋于同一平台，是“控制工况保持不变”的外推假设，"
        "不是附件证实的事实；请勿把图中的 6–72 h 曲线称为实测。",
        "- 当前 `src/common/boundary.py` 使用观测间线性插值并在末尾保持最后读数。"
        "本任务没有替换该模块、重跑 PDE、更新 result2.xlsx，故不声称药材场或最终干燥时长已经改变。",
        "- 按用户限定，所有算法、报告和图均在 `nihe/`；未修改 `docs/NOTATION.md`、"
        "`docs/DECISIONS.md` 或任务看板。正式接入前需由相应 Owner 同步边界拟合决策与参数记号。",
        "",
        "## 7. 复现",
        "",
        "```bash",
        f"conda run -n tf2 python -B nihe/fit_boundary.py --bootstrap {repetitions} --seed {seed}",
        "conda run -n tf2 python -B -m unittest discover -s nihe -p 'test_*.py' -v",
        "```",
        "",
        f"本次库版本：NumPy {np.__version__}，SciPy {scipy.__version__}，openpyxl {openpyxl.__version__}。",
        "图件同时输出 PNG（Markdown 预览）与 PDF（矢量版）。图和表中的数值均来自本次运行。",
        "",
        "算法依据：SciPy 官方 `scipy.optimize.least_squares` 文档（有界最小二乘、稳健损失）；"
        "Forecasting: Principles and Practice 第 3 版 §5.10（按时间滚动验证）。"
        "这些只用于算法核对，不提供题目参数。具体曲线、区间和验证结果以本目录代码为准。",
    ]
    (HERE / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bootstrap", type=int, default=300)
    parser.add_argument("--seed", type=int, default=20260912)
    args = parser.parse_args()
    if args.bootstrap < 20:
        parser.error("--bootstrap must be at least 20.")
    time_s, fields, metadata, analyses = analyze(args.bootstrap, args.seed)
    plot_results(time_s, fields, analyses)
    write_report(time_s, fields, metadata, analyses, args.bootstrap, args.seed)
    for field, analysis in analyses.items():
        curve = analysis["curve"]
        print(f"{field}: model={curve.model}, plateau_SI={curve.plateau:.12g}, RMSE={curve.rmse:.8g}")
    print(f"Report: {HERE / 'REPORT.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
