"""问题 4 求解器 —— 考虑失水收缩的烘干时长。

⏸ **尚未实现。** 这是框架搭建阶段的预期状态。全卷技术含量最高的一问。

本质：移动边界问题
------------------
求解域 r ∈ [0, R(t)]，R(t) 由 problem/附件/附件2.xlsx 给出（2.000 -> 1.198 cm，收缩 40.1%）。

  方案 A（推荐）：坐标变换 ξ = r/R(t) ∈ [0,1]，映射到固定计算域
                  → 方程里多出对流项，需正确推导
  方案 B：真正的移动网格 / ALE —— 复杂度高一个数量级，3 天赛程不建议
  方案 C：用附件 2 的 R(t) 按比例缩放固定网格（等价于 A 的离散版）

见 docs/DECISIONS.md D-006。

⚠️ 物性用**附录 4**（与问题 2/3 的附录 3 不同，数值也不同）。不可混用。

必须验证
--------
- 退化检验：令 R(t) = R0 常数，结果应与"问题 3 改用附录 4 参数"一致
  → 这是坐标变换正确性的**最强检验**
- 质量守恒：干物质总量恒定
- R(t) 一致性：若用干物质守恒反推 R(t)，与附件 2 的差异有多大？（论文亮点）
- 网格收敛：Δξ 与 Δt 的收敛阶

⚠️ 交付物 result4.xlsx 的最后一列是"药材表面"而非固定 2 cm，
   列头与内容都随时间变化。**先跑 make probe 确认模板怎么表示。**
"""

from __future__ import annotations

from common.problem_spec import ProblemSpec
from common.solution import Solution

TODO = """
问题 4 求解器尚未实现。

  前置条件：
    [ ] docs/model/q4.md §3「控制方程与坐标变换」完整推导完成
    [ ] docs/model/correlations.md §4 附录 4 公式整理完成
    [ ] src/common/correlations.py 的 Appendix4 已实现
    [ ] docs/DECISIONS.md 中 D-006（移动边界方案）、D-010（半径平台的理解）已定稿

  实现要点：
    - 交付网格的含义要先确认：result4 的"距离"是固定物理坐标还是随 R(t) 缩放？
      跑 make probe 看模板，这直接决定后处理怎么写
    - 对流项的空间离散（迎风/中心）与 CFL 条件需实算确认
    - 退化检验（R = const）必须通过，否则坐标变换推错了
"""


def solve(spec: ProblemSpec, **opts) -> Solution:
    """求解问题 4。签名见 docs/INTERFACES.md §8。

    注意：spec.uses_shrinkage 为 True，R(t) 需从 data/processed/radius.csv 插值取得
    （插值方式见 docs/DECISIONS.md D-004）。
    """
    raise NotImplementedError(TODO)
