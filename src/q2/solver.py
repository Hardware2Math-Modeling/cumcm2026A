"""问题 2 求解器 —— 整个烘干过程的温度与水分浓度变化规律。

⏸ **尚未实现。** 这是框架搭建阶段的预期状态。

与问题 1 的关键差异
-------------------
- 物性用**附录 3**（变物性，ρ/c_p/k 依赖 C，D 依赖 C 与 T），不是附录 2
- 传热-传质**双向耦合**，非线性
- 时段是整个烘干过程（2~3 天），**必须先做计算量评估**（见下）

⚠️ 计算量：2~3 天 × 1 s 步长 = 17~26 万步。先算单步耗时再外推，
   别写完才发现要跑 8 小时（AGENTS.md §4.4）。必要时用变步长/自适应积分器，
   但任何降级都要在 docs/DECISIONS.md 记录并给出精度验证。

必须验证
--------
- 质量守恒：干物质总量恒定；水分总量变化 == 表面传质通量积分
- 能量守恒：域内能量变化 == 对流换热量 − 蒸发带走的热量
- 两阶段连续性：切换点处 T、C 无跳变
- 物理合理性：C 单调下降；表面 C ≤ 中心 C；T ≤ T_∞

⚠️ 本模块内部一律 SI。物性经 correlations.Appendix3 获取，不许硬编码。
"""

from __future__ import annotations

from common.problem_spec import ProblemSpec
from common.solution import Solution

TODO = """
问题 2 求解器尚未实现。

  前置条件（缺一不可）：
    [ ] docs/model/q2.md 定稿
    [ ] src/common/correlations.py 的 Appendix3 已实现
    [ ] docs/DECISIONS.md 中 D-002（表面蒸发潜热）、D-003（汽化潜热取值）、
        D-005（阶段切换判据）、D-008（数值格式）、D-009（4h 后环境条件）已定稿
    [ ] 计算量评估已完成（单步耗时 x 总步数），结果写入 docs/DECISIONS.md

  实现要点：
    - 变系数 k(r), D(r) 的界面值取法（算术/调和平均）需在 q2.md 说明理由
    - 非线性项策略（显式滞后 / Newton / 固定点）+ 收敛判据
    - 交付完整结果要求"每隔 1 s"，跨 2~3 天 —— 内存与 I/O 都要评估
"""


def solve(spec: ProblemSpec, **opts) -> Solution:
    """求解问题 2。签名见 docs/INTERFACES.md §8。"""
    raise NotImplementedError(TODO)
