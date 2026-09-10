"""单位换算。

铁律（AGENTS.md §4.1）：代码内部一律 SI —— 长度用 m，温度用 K。
只有在「写入 result*.xlsx」和「画图」的最后一步才转成 cm / °C / h。

禁止在 src/q*/ 里出现 0.01 或 273.15 字面量，用本模块的常量。
"""

from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike, NDArray

# --- 常量 --------------------------------------------------------------------
CM_TO_M: float = 1.0e-2
M_TO_CM: float = 1.0e2
MM_TO_M: float = 1.0e-3

S_TO_H: float = 1.0 / 3600.0
H_TO_S: float = 3600.0

C_TO_K: float = 273.15  # T[K] = T[°C] + C_TO_K
K_TO_C: float = -273.15  # T[°C] = T[K] + K_TO_C

#: 绝对零度。用于合理性断言。
T_ABS_ZERO_K: float = 0.0
#: 防呆阈值：附录 3/4 的 D 公式含 exp(-3850/T)，T 必须是开尔文。
#: 传摄氏度进来会静默产生看似合理的结果，因此设这个下限做断言。
T_KELVIN_SANITY_MIN: float = 200.0


# --- 换算函数（标量或 ndarray 均可）------------------------------------------
def cm_to_m(x: ArrayLike) -> NDArray | float:
    """厘米 → 米。"""
    return np.asarray(x) * CM_TO_M if isinstance(x, (np.ndarray, list, tuple)) else x * CM_TO_M


def m_to_cm(x: ArrayLike) -> NDArray | float:
    """米 → 厘米。"""
    return np.asarray(x) * M_TO_CM if isinstance(x, (np.ndarray, list, tuple)) else x * M_TO_CM


def c_to_k(x: ArrayLike) -> NDArray | float:
    """摄氏度 → 开尔文。"""
    return np.asarray(x) + C_TO_K if isinstance(x, (np.ndarray, list, tuple)) else x + C_TO_K


def k_to_c(x: ArrayLike) -> NDArray | float:
    """开尔文 → 摄氏度。"""
    return np.asarray(x) + K_TO_C if isinstance(x, (np.ndarray, list, tuple)) else x + K_TO_C


def s_to_h(x: ArrayLike) -> NDArray | float:
    """秒 → 小时。"""
    return np.asarray(x) * S_TO_H if isinstance(x, (np.ndarray, list, tuple)) else x * S_TO_H


def h_to_s(x: ArrayLike) -> NDArray | float:
    """小时 → 秒。"""
    return np.asarray(x) * H_TO_S if isinstance(x, (np.ndarray, list, tuple)) else x * H_TO_S


# --- 断言 --------------------------------------------------------------------
def assert_kelvin(T: ArrayLike, *, where: str = "") -> None:
    """防呆：确认温度是开尔文。

    附录 3/4 的扩散系数公式含 exp(-3850/T)。若把 60 °C 当成 60 传进去，
    数值会错得离谱却「看起来还在合理范围」——这是本项目最危险的一类错误。
    """
    arr = np.asarray(T, dtype=float)
    if not np.all(np.isfinite(arr)):
        raise ValueError(f"温度含 NaN/Inf{_at(where)}")
    if arr.size and float(np.min(arr)) < T_KELVIN_SANITY_MIN:
        raise ValueError(
            f"温度最小值为 {float(np.min(arr)):.3f}，低于防呆阈值 "
            f"{T_KELVIN_SANITY_MIN} K。看起来你传的是摄氏度而不是开尔文"
            f"{_at(where)}。请用 units.c_to_k() 转换。"
        )


def assert_positive(x: ArrayLike, *, name: str, where: str = "") -> None:
    """防呆：物理量必须为正（半径、密度、扩散系数等）。"""
    arr = np.asarray(x, dtype=float)
    if not np.all(np.isfinite(arr)):
        raise ValueError(f"{name} 含 NaN/Inf{_at(where)}")
    if arr.size and float(np.min(arr)) <= 0.0:
        raise ValueError(f"{name} 出现非正值（最小 {float(np.min(arr)):.6g}）{_at(where)}")


def _at(where: str) -> str:
    return f"（位置：{where}）" if where else ""
