"""问题 3/4 的干燥终点判据。

``max`` 是论文正式结果采用的口径：药材所有位置都必须低于阈值。
``center`` 是可选的中心判据；本题的数值解中最大含水率在中心，故两者应一致。
"""

from __future__ import annotations

import numpy as np


def value(C: np.ndarray, mode: str = "max") -> float:
    """返回当前场用于事件检测的标量。"""
    C = np.asarray(C, dtype=float)
    if C.ndim != 1:
        raise ValueError("C 必须是一维径向场")
    if mode == "max":
        return float(np.max(C))
    if mode == "center":
        return float(C[0])
    raise ValueError("criterion 只能是 'max' 或 'center'")


def event(C: np.ndarray, target: float = 0.15, mode: str = "max") -> float:
    """事件函数：低于零表示达到干燥要求。"""
    return value(C, mode) - float(target)


def check(C: np.ndarray, target: float = 0.15, mode: str = "max") -> bool:
    """严格判断是否达标；mode=center 时同时检查全场，防止误报。"""
    C = np.asarray(C, dtype=float)
    if mode == "center":
        return bool(C[0] < target and np.max(C) < target)
    return bool(np.max(C) < target)

