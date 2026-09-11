"""求解结果容器。

放在 common/ 而不是各题的 solver 里，是为了避免 plotting / io 反向依赖 src/qN/。
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass
class Solution:
    """一个问题的数值解。

    形状约定（**不要改**，下游的 io/plotting 都依赖它）：
        T, C : (n_t, n_r)
        t    : (n_t,)
        r    : (n_r,)

    ⚠️ 单位：内部一律 SI —— t 用 s，r 用 m，T 用 K，C 用干基 kg/kg。
       转成 cm / °C / h 只发生在 io_excel.write_result 与 plotting 里。
    """

    t: np.ndarray  # (n_t,)     s
    r: np.ndarray  # (n_r,)     m
    T: np.ndarray  # (n_t, n_r) K          # noqa: N815
    C: np.ndarray  # (n_t, n_r) kg/kg 干基  # noqa: N815
    meta: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.t = np.asarray(self.t, dtype=float)
        self.r = np.asarray(self.r, dtype=float)
        self.T = np.asarray(self.T, dtype=float)
        self.C = np.asarray(self.C, dtype=float)
        n_t, n_r = self.T.shape
        if self.C.shape != (n_t, n_r):
            raise ValueError(f"T 与 C 形状不一致：{self.T.shape} vs {self.C.shape}")
        if self.t.size != n_t or self.r.size != n_r:
            raise ValueError(
                f"网格与场形状不匹配：t={self.t.size}, r={self.r.size}, T={self.T.shape}"
            )

    @property
    def shape(self) -> tuple[int, int]:
        return self.T.shape

    @property
    def n_t(self) -> int:
        return self.t.size

    @property
    def n_r(self) -> int:
        return self.r.size

    @property
    def surface_index(self) -> int:
        """表面节点索引。"""
        return self.n_r - 1

    def center_series(self) -> np.ndarray:
        """轴心 (r=0) 的时间序列，形状 (n_t,)。"""
        return self.C[:, 0]

    def surface_series(self) -> np.ndarray:
        """表面节点的时间序列，形状 (n_t,)。"""
        return self.C[:, self.surface_index]

    def max_C_over_r(self) -> np.ndarray:
        """各时刻全场最大水分浓度，形状 (n_t,)。问题 3/4 的终点判据用。"""
        return self.C.max(axis=1)

    def first_time_below(self, target: float, *, strict: bool = True) -> float:
        """首次满足「全场水分浓度低于 target」的时刻，单位 s。

        问题 3/4 的终点判据：题目要求「药材各处的水分浓度应低于 0.15 kg/kg」，
        因此取 max_r C 而非平均值（最慢干燥的是轴心）。
        """
        m = self.max_C_over_r()
        cond = m < target if strict else m <= target
        idx = np.flatnonzero(cond)
        if idx.size == 0:
            raise ValueError(
                f"在 {self.t[-1]:.0f} s 内全场水分浓度从未低于 {target}。"
                f"当前终值 max_r C = {m[-1]:.4f}。"
                f"要么延长求解时段，要么先检查模型（AGENTS.md 铁律 10：不许静默降级）。"
            )
        return float(self.t[idx[0]])

    def summary(self) -> str:
        def span(a: np.ndarray, fmt: str) -> str:
            """min~max，忽略 NaN。

            问题 4 的固定物理位置会随收缩落到域外并被掩码成 NaN，
            直接用 ndarray.min()/max() 会让整条摘要变成 "nan~nan"。
            """
            finite = a[np.isfinite(a)]
            if finite.size == 0:
                return "—"
            return f"{finite.min():{fmt}}~{finite.max():{fmt}}"

        return (
            f"Solution({self.n_t} x {self.n_r}) "
            f"t: {self.t[0]:.1f}~{self.t[-1]:.1f} s | "
            f"r: {self.r[0] * 100:.2f}~{self.r[-1] * 100:.2f} cm | "
            f"T: {span(self.T, '.2f')} K | "
            f"C: {span(self.C, '.4f')} kg/kg"
        )
