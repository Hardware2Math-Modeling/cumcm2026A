"""问题 1 求解器 —— 预热平衡阶段温度与水分浓度变化规律。

⏸ **尚未实现。** 这是框架搭建阶段的预期状态。

实现步骤
--------
1. 等 `@model` 完成 `docs/model/q1.md`（控制方程、定解条件、离散格式、稳定性）
2. 在 `docs/model/correlations.md` 完成附录 2 的公式整理与量纲校验
3. 实现 `PropertySet`（`src/common/correlations.py` 的 `Appendix2`）
4. 实现本模块，按 docs/INTERFACES.md §8 的签名
5. 补测试（见下方"必须验证"）

必须验证（docs/model/q1.md §9）
-------------------------------
- 能量守恒：域内能量变化 == 通过 r=R 的对流换热积分（相对误差 < 1e-6）
- 网格收敛：Δr 减半，误差按预期阶下降；记录实测阶数
- 边界条件：r=0 处数值解满足 ∂T/∂r = 0
- 极限情形：h → ∞ 时表面温度迅速趋于 T_∞
- 交付格式：result1.xlsx 与模板一致（工作表名、行列数、四位小数）

⚠️ 本模块内部一律 SI：长度 m，温度 K，时间 s。转 cm/°C 只发生在 io/plotting。
⚠️ 物性必须经 src/common/correlations.py 获取，不许在此硬编码任何常数（AGENTS.md 铁律 5）。
"""

from __future__ import annotations

from common.problem_spec import ProblemSpec
from common.solution import Solution

TODO = """
问题 1 求解器尚未实现。

  前置条件（缺一不可）：
    [ ] docs/model/q1.md 定稿 —— 控制方程、边界条件、离散格式、稳定性分析
    [ ] docs/model/correlations.md §2 附录 2 公式整理 + 量纲校验完成
    [ ] src/common/correlations.py 的 Appendix2 已实现
    [ ] docs/DECISIONS.md 中 D-001（干物质密度）、D-002（蒸发潜热是否进边界）、
        D-008（数值格式）、D-011（烘房浓度基准）已定稿

  实现要点：
    - 圆柱坐标一维轴对称；r=0 处有坐标奇性，需用控制体积积分或 L'Hôpital 处理
    - 内部步长可比交付步长（1 s）细，但必须在 meta 里记录 dt_internal
      并在 docs/DECISIONS.md 给出步长无关性验证
    - 返回 Solution(t, r, T, C, meta)，形状约定见 src/common/solution.py
"""


def solve(spec: ProblemSpec, **opts) -> Solution:
    """求解问题 1。签名见 docs/INTERFACES.md §8。"""
    raise NotImplementedError(TODO)
