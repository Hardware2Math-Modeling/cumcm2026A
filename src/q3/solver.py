"""问题3入口；物理和数值规格见 docs/model/numerics.md。"""
from common.radial import solve_radial


def solve(spec, **opts):
    return solve_radial(spec, **opts)
