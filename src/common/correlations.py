"""物性公式（附录 2 / 3 / 4 三套）。

铁律（AGENTS.md 铁律 5）：ρ、c_p、k、D 一律通过本模块获取。
在 src/q*/ 里直接写常数（如 0.36）属于严重错误。

⚠️ 当前状态：**接口已冻结，实现待填**。
   公式请从 problem/A题.pdf 的附录逐字抄录到 docs/model/correlations.md，
   再由 @impl 实现于此。本文件不预先填入任何公式，防止与原文不一致。

接口约定（不要改）：
    - C 一律是**干基**含水率 (kg/kg)。公式里需要湿基 w = C/(1+C) 时，在函数内部换算，
      不要把这个负担丢给调用方 —— 否则必然有人在某处传错。
    - T 一律是**开尔文** (K)。附录 3/4 的 D 公式含 exp(-3850/T)。
    - 返回单位见各方法 docstring。
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import numpy as np
from numpy.typing import ArrayLike

from . import units

#: 附录 3/4 的 D 公式含 exp(-3850/T)，T 必须 > 200 K 才可能是开尔文
_KELVIN_CHECK = True


def wet_basis(C: ArrayLike) -> np.ndarray:
    """干基含水率 C (kg/kg) → 湿基质量分数 w = C/(1+C) (kg/kg)。

    附录 3/4 的 c_p、k 公式里出现的 C/(C+1) 就是这个量。
    见 docs/model/correlations.md §1。
    """
    C = np.asarray(C, dtype=float)
    return C / (1.0 + C)


def _prepare(C: ArrayLike, T: ArrayLike, *, where: str) -> tuple[np.ndarray, np.ndarray]:
    """统一入参检查。所有 PropertySet 方法都应先调用它。"""
    C_arr = np.asarray(C, dtype=float)
    T_arr = np.asarray(T, dtype=float)
    if np.any(C_arr < 0.0):
        raise ValueError(f"水分浓度 C 出现负值{_at(where)}")
    if _KELVIN_CHECK:
        units.assert_kelvin(T_arr, where=where)
    return C_arr, T_arr


@runtime_checkable
class PropertySet(Protocol):
    """一套物性公式。附录 2 / 3 / 4 各实现一个。

    三套公式**不可混用**（AGENTS.md §4.3）：
        Q1          -> Appendix2（常数物性）
        Q2, Q3      -> Appendix3（变物性）
        Q4          -> Appendix4（变物性 + 收缩）
    """

    name: str
    appendix: int

    def rho(self, C: ArrayLike, T: ArrayLike) -> np.ndarray:
        """含湿药材表观密度，kg/m^3。

        ⚠️ 这是**表观**密度（随 C 变化）。扩散方程需要的干基密度 ρ_d 与此不同，
           换算关系见 docs/DECISIONS.md D-001（尚未定稿）。
        """
        ...

    def cp(self, C: ArrayLike, T: ArrayLike) -> np.ndarray:
        """定压比热容，J/(kg·K)。"""
        ...

    def k(self, C: ArrayLike, T: ArrayLike) -> np.ndarray:
        """导热系数，W/(m·K)。"""
        ...

    def D(self, C: ArrayLike, T: ArrayLike) -> np.ndarray:
        """水分扩散系数，m^2/s。"""
        ...


class _NotImplementedPropertySet:
    """骨架：三套公式集的公共占位实现。

    子类只需填 `name` / `appendix` 和四个方法。填之前请先更新
    docs/model/correlations.md，并完成量纲校验。
    """

    name: str = "UNSET"
    appendix: int = 0

    def _todo(self, method: str) -> NotImplementedError:
        return NotImplementedError(
            f"{type(self).__name__}.{method}() 尚未实现。\n"
            f"  步骤 1: 从 problem/A题.pdf 附录 {self.appendix} 逐字抄录公式到 "
            f"docs/model/correlations.md\n"
            f"  步骤 2: 在 docs/model/correlations.md 完成量纲校验\n"
            f"  步骤 3: 实现本方法，注意 C 是干基、T 是开尔文\n"
            f"  见 AGENTS.md 铁律 5 与 docs/model/correlations.md"
        )

    def rho(self, C, T):  # noqa: N803
        raise self._todo("rho")

    def cp(self, C, T):
        raise self._todo("cp")

    def k(self, C, T):  # noqa: N803
        raise self._todo("k")

    def D(self, C, T):  # noqa: N803
        raise self._todo("D")


class Appendix2(_NotImplementedPropertySet):
    """问题 1：常数物性。见 docs/model/correlations.md §2。"""

    name = "appendix2"
    appendix = 2


class Appendix3(_NotImplementedPropertySet):
    """问题 2、3：变物性，ρ/c_p/k 依赖 C，D 依赖 C 与 T。见 docs/model/correlations.md §3。"""

    name = "appendix3"
    appendix = 3


class Appendix4(_NotImplementedPropertySet):
    """问题 4：变物性（与附录 3 数值不同）+ 尺寸收缩。见 docs/model/correlations.md §4。"""

    name = "appendix4"
    appendix = 4


# --- 工况参数（不是"物性"，但同样集中在这里）--------------------------------


def h_conv(problem: str) -> float:
    """对流换热系数，W/(m^2·K)。

    问题 1 由附录 2 给出。问题 2/3/4 题目是否给出需核对 —— 若未给出，
    必须在 docs/DECISIONS.md 里记录取值与出处（AGENTS.md 铁律 2）。
    """
    raise NotImplementedError(
        f"h_conv({problem!r}) 尚未实现。请在 docs/model/correlations.md 中确认"
        f"各问题对应的对流换热系数及其出处。"
    )


def h_mass(problem: str) -> float:
    """对流传质系数，m/s。问题 1 由附录 2 给出。"""
    raise NotImplementedError(
        f"h_mass({problem!r}) 尚未实现。见 docs/model/correlations.md。"
    )


def latent_heat_vaporization(T: ArrayLike) -> np.ndarray:
    """水的汽化潜热，J/kg。

    ⚠️ 题目**未给出**该参数。必须有明确出处（docs/DECISIONS.md D-003）。
    出处未确定前不要实现本函数 —— 不要填一个"大概"的值进来。
    """
    raise NotImplementedError(
        "汽化潜热题目未给出，出处待定（docs/DECISIONS.md D-003）。\n"
        "确定出处后：写清取自哪本手册/哪个来源、对应什么温度，再实现本函数。\n"
        "AGENTS.md 铁律 2：任何数字必须有出处，不许编造。"
    )


def _at(where: str) -> str:
    return f"（位置：{where}）" if where else ""
