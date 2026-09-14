"""附件 1 环境边界的可选 Logistic 拟合。

主结果默认使用 ``model.py`` 中的分段线性插值和末值保持。若运行时指定
``--ambient fit``，本文件只拟合烘房温度和水分浓度边界，不拟合药材内部场。
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import openpyxl
from scipy.optimize import least_squares


@dataclass(frozen=True)
class LogisticCurve:
    plateau: float
    gap: float
    tau_s: float
    log_shape: float

    def __call__(self, t_s):
        t_s = np.asarray(t_s, dtype=float)
        a = np.exp(self.log_shape)
        z = self.logistic_fraction(t_s)
        out = self.plateau - self.gap * z
        return float(out) if out.ndim == 0 else out

    def logistic_fraction(self, t_s):
        t_s = np.asarray(t_s, dtype=float)
        a = np.exp(self.log_shape)
        with np.errstate(over="ignore"):
            return (1.0 + a) / (1.0 + a * np.exp(t_s / self.tau_s))


@dataclass(frozen=True)
class FittedAmbient:
    temperature: LogisticCurve  # K
    concentration: LogisticCurve  # kg/kg

    def ambient(self, t_s):
        return self.temperature(t_s), self.concentration(t_s)


def read_attachment1(path):
    """读取附件 1，温度在这里转换为 K。"""
    book = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        rows = list(book.active.values)
    finally:
        book.close()
    if tuple(rows[0]) != ("时间", "温度", "水分浓度"):
        raise ValueError("附件1表头不是 时间/温度/水分浓度")
    data = np.asarray(rows[1:], dtype=float)
    return data[:, 0], data[:, 1] + 273.15, data[:, 2]


def fit_curve(t_s: np.ndarray, y: np.ndarray) -> LogisticCurve:
    """有界非线性最小二乘拟合有限平台的 Logistic 曲线。"""
    t_s = np.asarray(t_s, dtype=float)
    y = np.asarray(y, dtype=float)
    scale = max(float(np.ptp(y)), np.finfo(float).eps)
    offset = float(np.min(y))
    duration = float(t_s[-1])
    normalized = (y - offset) / scale

    def residual(p):
        plateau, gap, tau_fraction, log_shape = p
        curve = plateau - gap * LogisticCurve(0.0, 1.0, tau_fraction * duration, log_shape).logistic_fraction(t_s)
        return curve - normalized

    lower = np.array([0.0, 0.0, max(np.diff(t_s)[0] / duration / 10.0, 1e-8), -8.0])
    upper = np.array([5.0, 10.0, 100.0, 5.0])
    starts = (
        [1.01, 1.01, 0.15, -2.0],
        [1.01, 1.01, 0.40, 0.0],
        [1.01, 1.01, 0.40, 2.0],
    )
    solutions = [
        least_squares(residual, np.clip(s, lower + 1e-9, upper - 1e-9), bounds=(lower, upper))
        for s in starts
    ]
    best = min(solutions, key=lambda s: s.cost)
    p = best.x.copy()
    return LogisticCurve(
        plateau=offset + scale * p[0],
        gap=scale * p[1],
        tau_s=duration * p[2],
        log_shape=p[3],
    )


def fit_boundary(path) -> FittedAmbient:
    t_s, T_amb, C_amb = read_attachment1(path)
    return FittedAmbient(fit_curve(t_s, T_amb), fit_curve(t_s, C_amb))

