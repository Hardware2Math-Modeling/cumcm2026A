"""题目常量与四个问题的静态定义。

把"题目给的东西"集中成结构化对象，避免散落在代码里（AGENTS.md 铁律 5 的延伸）。
只放**题目明确的给定量**，不放任何需要建模决定的量。
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .correlations import Appendix2, Appendix3, Appendix4, PropertySet
from .paths import rel

# --- 题目给定量（来源：problem/A题.pdf）------------------------------------

#: 药材长度 L = 25 cm（题目：形状大致呈圆柱形，长为 25 cm）
LENGTH_M: float = 0.25

#: 初始半径 R0 = 2 cm
RADIUS0_M: float = 0.02

#: 初始温度 28 °C
INITIAL_T_C: float = 28.0

#: 初始水分浓度（干基）2.55 kg/kg
INITIAL_C_DRY: float = 2.55

#: 问题 3 的烘干终点判据：各处水分浓度应低于 0.15 kg/kg
TARGET_C_DRY: float = 0.15

#: 问题 1 的求解时段：1800 s
Q1_T_END_S: float = 1800.0

#: 问题 2 的表 3/表 4 展示时段：3 h
Q2_TABLE_T_END_S: float = 3.0 * 3600.0

#: 交付完整结果的时间步长（题目要求"每隔 1 s"）
DT_OUTPUT_DEFAULT_S: float = 1.0

#: 问题 3/4 交付完整结果的时间步长（题目要求"每隔 60 s"）
DT_OUTPUT_Q34_S: float = 60.0

#: 交付空间步长：0.1 cm
DR_OUTPUT_M: float = 0.1 * 1e-2

#: 论文表格的展示距离网格：0, 0.5, 1, 1.5, 2 cm
TABLE_R_CM: tuple[float, ...] = (0.0, 0.5, 1.0, 1.5, 2.0)

#: 附件 1 的覆盖时长（实测 14400 s = 4 h）—— 问题 2/3/4 需要外推，见 D-009
AMBIENT_COVERAGE_S: float = 14400.0

#: 附件 2 的覆盖时长（实测 259200 s = 72 h）
RADIUS_COVERAGE_S: float = 259200.0


@dataclass(frozen=True)
class Geometry:
    """几何。单位：m。"""

    length: float = LENGTH_M
    radius0: float = RADIUS0_M

    def __post_init__(self) -> None:
        if not (self.length > 0 and self.radius0 > 0):
            raise ValueError(f"几何参数必须为正：L={self.length}, R0={self.radius0}")
        # 长径比：用于论证一维径向简化的合理性（docs/DECISIONS.md D-007）
        if self.length / self.radius0 < 5.0:
            raise ValueError(
                f"长径比仅 {self.length / self.radius0:.2f}，一维径向简化（D-007）可能不成立。"
                f"若确实要这样建模，请先更新 docs/DECISIONS.md 的论证。"
            )

    @property
    def aspect_ratio(self) -> float:
        """长径比 L/(2R0)。用于论文里论证轴向均匀假设。"""
        return self.length / (2.0 * self.radius0)


@dataclass(frozen=True)
class InitialState:
    """初始条件。T 用 K，C 用干基 kg/kg。"""

    T: float = INITIAL_T_C + 273.15  # noqa: N815
    C: float = INITIAL_C_DRY  # noqa: N815

    def __post_init__(self) -> None:
        if self.T < 200.0:
            raise ValueError(f"初始温度 {self.T} 看起来不是开尔文。请写 °C + 273.15。")
        if self.C < 0.0:
            raise ValueError(f"初始水分浓度不能为负：{self.C}")


@dataclass(frozen=True)
class Grid:
    """交付网格（不是内部计算网格）。

    内部网格可能更细，那时求解器负责插值到本网格，并必须在
    docs/DECISIONS.md 里记录 + 给出步长无关性验证（AGENTS.md §4.2）。
    """

    dt: float  # s
    t_end: float  # s
    dr: float = DR_OUTPUT_M  # m
    radius: float = RADIUS0_M  # m，问题 4 中会随时间变化

    def __post_init__(self) -> None:
        if self.dt <= 0 or self.t_end <= 0 or self.dr <= 0:
            raise ValueError("网格参数必须为正")
        if self.t_end < self.dt:
            raise ValueError(f"总时长 {self.t_end} 小于一个时间步 {self.dt}")

    @property
    def t(self) -> np.ndarray:
        """时间节点，(n_t,) s。"""
        n = int(round(self.t_end / self.dt)) + 1
        return np.linspace(0.0, self.t_end, n)

    @property
    def r(self) -> np.ndarray:
        """径向节点，(n_r,) m。i=0 对应轴心 r=0。"""
        n = int(round(self.radius / self.dr)) + 1
        return np.linspace(0.0, self.radius, n)

    @property
    def shape(self) -> tuple[int, int]:
        return (self.t.size, self.r.size)


@dataclass(frozen=True)
class ProblemSpec:
    """一个问题的完整静态定义。"""

    name: str  # "q1" | "q2" | "q3" | "q4"
    title: str
    geometry: Geometry
    initial: InitialState
    grid: Grid
    properties: PropertySet
    uses_shrinkage: bool = False  # 问题 4 为 True
    extra: dict = field(default_factory=dict)

    def describe(self) -> str:
        n_t, n_r = self.grid.shape
        return (
            f"[{self.name}] {self.title}\n"
            f"  几何   : L={self.geometry.length} m, R0={self.geometry.radius0} m, "
            f"长径比={self.geometry.aspect_ratio:.1f}\n"
            f"  初值   : T={self.initial.T:.2f} K, C={self.initial.C} kg/kg(干基)\n"
            f"  交付网格: {n_t} 时间步 x {n_r} 空间节点 "
            f"(dt={self.grid.dt}s, dr={self.grid.dr * 100}cm, t_end={self.grid.t_end}s)\n"
            f"  物性集 : {self.properties.name} (附录 {self.properties.appendix})\n"
            f"  收缩   : {'是' if self.uses_shrinkage else '否'}"
        )


# --- 四个问题的定义 ----------------------------------------------------------
# t_end 中，问题 2/3/4 的"整个烘干过程"时长本身就是待求结果（问题 3/4），
# 或是需要先估算的上界（问题 2）。因此这里只给一个**占位上界**，
# 真正取值必须在 docs/DECISIONS.md 定稿后由 @impl 更新。

#: 占位上界：附件 2 覆盖 72 h。⚠️ 这是数据覆盖时长，不是题目给的答案。
_T_END_PLACEHOLDER_S: float = 259200.0

Q1 = ProblemSpec(
    name="q1",
    title="预热平衡阶段温度与水分浓度变化规律",
    geometry=Geometry(),
    initial=InitialState(),
    grid=Grid(dt=DT_OUTPUT_DEFAULT_S, t_end=Q1_T_END_S),
    properties=Appendix2(),
    uses_shrinkage=False,
)

Q2 = ProblemSpec(
    name="q2",
    title="整个烘干过程的温度与水分浓度变化规律",
    geometry=Geometry(),
    initial=InitialState(),
    grid=Grid(dt=DT_OUTPUT_DEFAULT_S, t_end=_T_END_PLACEHOLDER_S),
    properties=Appendix3(),
    uses_shrinkage=False,
    extra={"table_t_end": Q2_TABLE_T_END_S},
)

Q3 = ProblemSpec(
    name="q3",
    title="确定药材烘干所需的时间",
    geometry=Geometry(),
    initial=InitialState(),
    grid=Grid(dt=DT_OUTPUT_Q34_S, t_end=_T_END_PLACEHOLDER_S),
    properties=Appendix3(),
    uses_shrinkage=False,
    extra={"target_C": TARGET_C_DRY},
)

Q4 = ProblemSpec(
    name="q4",
    title="考虑失水收缩的烘干时长",
    geometry=Geometry(),
    initial=InitialState(),
    grid=Grid(dt=DT_OUTPUT_Q34_S, t_end=_T_END_PLACEHOLDER_S),
    properties=Appendix4(),
    uses_shrinkage=True,  # R(t) 来自 problem/附件/附件2.xlsx
    extra={"target_C": TARGET_C_DRY},
)

ALL: dict[str, ProblemSpec] = {"q1": Q1, "q2": Q2, "q3": Q3, "q4": Q4}


def get(problem: str) -> ProblemSpec:
    key = str(problem).strip().lower()
    if key.startswith("result"):
        key = "q" + key.removeprefix("result")
    if key not in ALL:
        raise KeyError(f"未知问题 {problem!r}，可选：{sorted(ALL)}")
    return ALL[key]


def describe_all() -> str:
    return "\n\n".join(spec.describe() for spec in ALL.values())


def source_note() -> str:
    """溯源信息。写进 xlsx 的元数据或日志，便于回答「这个数从哪来的」。"""
    return (
        f"spec 定义: {rel(__file__)}\n"
        f"题目原件: problem/A题.pdf\n"
        f"模板原件: problem/附件/附件3/resultN.xlsx\n"
        f"环境数据: problem/附件/附件1.xlsx (0~{AMBIENT_COVERAGE_S:.0f} s)\n"
        f"半径数据: problem/附件/附件2.xlsx (0~{RADIUS_COVERAGE_S:.0f} s)"
    )
