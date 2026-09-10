"""问题 3 求解器 —— 确定药材烘干所需的时间。

⏸ **尚未实现。** 这是框架搭建阶段的预期状态。

本题不是新模型，是**求根问题**
------------------------------
复用问题 2 的模型，求最小的 t_end 使  max_r C(r, t_end) <= 0.15 kg/kg

  题目说"药材各处的水分浓度应低于 0.15"，因此取 max_r（轴心最慢），不是平均值。

难点在三处
----------
1. 单调性：需先论证 M(t) = max_r C(r,t) 关于 t 单调递减，才能用二分法
2. 计算量：每次试算都是跨越数十小时的昂贵求解，**不能暴力扫描**
   → 优先考虑 solve_ivp 的 events 事件检测（一次积分到位）
   → 备选：先粗网格定位区间，再在区间内精细求解（需给出粗网格误差上界）
3. 网格无关性：max_r 的取值依赖网格，Δr 越细 max 越大、t_end 越长

必须验证
--------
- 实测 M(t) 单调递减（存下序列并画图，图进论文）
- 网格无关性：Δr 减半后 t_end 的变化量 < 阈值（写下阈值与实测值）
- 判据正确性：t_end 时刻 max C <= 0.15 成立；t_end - δ 时不成立
- 交叉验证：两种求根策略结果一致

⚠️ 交付物 result3.xlsx **只有水分浓度，没有温度表** —— 以模板为准。
"""

from __future__ import annotations

from common.problem_spec import ProblemSpec
from common.solution import Solution

TODO = """
问题 3 求解器尚未实现。

  前置条件：
    [ ] 问题 2 求解器已跑通（本问复用其模型）
    [ ] docs/model/q3.md 定稿，尤其是 §5「求解策略」的单调性论证
    [ ] docs/DECISIONS.md 中 D-002、D-005、D-009 已定稿

  实现要点：
    - 终点判据用 Solution.first_time_below(target)（已实现，直接复用）
    - 求根策略写在 docs/model/q3.md §5.2，按其实现
    - 把 M(t) 序列和求根过程记录下来，供论文出图
"""


def solve(spec: ProblemSpec, **opts) -> Solution:
    """求解问题 3。签名见 docs/INTERFACES.md §8。

    注意：返回的 Solution 应覆盖到**整个烘干过程结束**（t_end），
    而不只是到某个展示时刻。交付物要求"每隔 60 s"的完整结果。
    """
    raise NotImplementedError(TODO)
