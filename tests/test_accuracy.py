"""独立实际边界解析解、隐式算法交叉及细网格启动回归。"""

import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from common.problem_spec import Q1
from common.radial import solve_radial
from validate_accuracy import bessel_heat


class AccuracyTests(unittest.TestCase):
    def test_actual_boundary_heat_converges_to_independent_modes(self):
        times = np.array([60, 100, 300, 900, 1800.0])
        opts = dict(sample_times=times, rtol=2e-11, atol=2e-12,
                    align_boundary_knots=True, latent_heat=False)
        coarse = solve_radial(Q1, n_internal=81, **opts)
        fine = solve_radial(Q1, n_internal=161, **opts)
        exact = bessel_heat(times, fine.r)
        error_coarse = np.max(np.abs(coarse.T-exact))
        error_fine = np.max(np.abs(fine.T-exact))
        self.assertLess(error_fine, error_coarse/3)
        self.assertLess(error_fine, 1.5e-4)

    def test_boundary_knots_radau_matches_bdf(self):
        opts = dict(n_internal=41, t_end=300, sample_times=[0, 60, 61, 300],
                    rtol=2e-11, atol=2e-12, align_boundary_knots=True)
        bdf = solve_radial(Q1, **opts)
        radau = solve_radial(Q1, method="Radau", **opts)
        np.testing.assert_allclose(radau.T, bdf.T, rtol=0, atol=2e-7)
        np.testing.assert_allclose(radau.C, bdf.C, rtol=0, atol=2e-8)

    def test_fine_surface_startup_remains_positive(self):
        sol = solve_radial(Q1, n_internal=5121, t_end=1, sample_times=[0, 1],
                           rtol=2e-11, atol=2e-12, align_boundary_knots=True)
        self.assertGreater(float(np.min(sol.C)), 0)
        self.assertLess(sol.meta["mass_balance_relative"], 1e-11)


if __name__ == "__main__":
    unittest.main(verbosity=2)
