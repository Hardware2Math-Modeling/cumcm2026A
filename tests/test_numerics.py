"""独立解析解、守恒、边界、变域及输出掩码验证；可直接用unittest。"""
import sys
import unittest
from pathlib import Path

import numpy as np
from scipy.optimize import brentq
from scipy.special import j0, j1

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"src"))
from common import correlations, export, io_excel
from common.boundary import Boundary
from common.problem_spec import Q1, Q3, Q4
from common.radial import RadialModel, outward_flux, solve_radial


class NumericalTests(unittest.TestCase):
    def test_property_units_and_zero_limit(self):
        for p in (correlations.Appendix2(),correlations.Appendix3(),correlations.Appendix4()):
            self.assertEqual(float(p.D(0,300)),0)
            with self.assertRaises(ValueError):
                p.D(1,50)
        self.assertAlmostEqual(float(correlations.Appendix2().D(2.55,301.15)),
                               7e-9*np.exp(-0.89/2.55),places=18)
        self.assertAlmostEqual(float(correlations.Appendix3().D(1,300)),
                               2.4e-3*np.exp(-0.45-3850/300),places=18)
        self.assertAlmostEqual(float(correlations.Appendix4().D(1,300)),
                               4.2e-4*np.exp(-0.30-3850/300),places=18)

    def test_boundary_sign_and_equilibrium(self):
        self.assertLess(outward_flux(300,320,25),0)
        b=Boundary.from_attachments()
        b.T_amb[:]=Q1.initial.T
        b.C_amb[:]=Q1.initial.C
        m=RadialModel(Q1,41,b)
        np.testing.assert_allclose(m.rhs(600,m.initial()),0,atol=1e-13)

    def test_instantaneous_mass_and_heat_balance(self):
        for spec in (Q1,Q3,Q4):
            m=RadialModel(spec,41)
            y=m.initial()
            y[:41]+=2*m.xi**2
            y[41:82]-=0.2*m.xi**2
            dy=m.rhs(7200,y)
            self.assertLess(abs(m.weights@dy[41:82]+dy[82]),1e-16)
            capacity=spec.properties.rho(y[41:82],y[:41])*spec.properties.cp(y[41:82],y[:41])
            self.assertLess(abs(m.radius(7200)**2*np.dot(m.weights*capacity,dy[:41])-dy[83]),1e-12)

    def test_jacobian_directional_derivative(self):
        m=RadialModel(Q3,21)
        y=m.initial()
        y[:21]+=m.xi
        y[21:42]-=m.xi/4
        d=np.random.default_rng(2026).normal(size=len(y))
        eps=1e-5
        reference=(m.rhs(500,y+eps*d)-m.rhs(500,y-eps*d))/(2*eps)
        np.testing.assert_allclose(m.jacobian(500,y)@d,reference,rtol=5e-5,atol=2e-7)

    def test_constant_radius_reduces_to_fixed_model(self):
        b=Boundary.from_attachments()
        b.R[:]=Q4.geometry.radius0
        moving=RadialModel(Q4,41,b)
        fixed=RadialModel(Q4,41,b,fixed_radius=True)
        y=moving.initial()
        y[:41]+=moving.xi
        np.testing.assert_allclose(moving.rhs(3600,y),fixed.rhs(3600,y),atol=0)

    def test_closed_system_conservation_and_bessel_heat_solution(self):
        b=Boundary.from_attachments()
        b.T_amb[:]=Q1.initial.T+10
        b.C_amb[:]=Q1.initial.C
        times=np.array([100,600,1800.])
        s=solve_radial(Q1,boundary=b,n_internal=321,sample_times=times)
        # 圆柱第三类边界解析级数，独立于有限体积实现。
        p=Q1.properties
        k=float(p.k(1,300)); alpha=k/float(p.rho(1,300)*p.cp(1,300))
        Bi=correlations.h_conv("q1")*Q1.geometry.radius0/k
        f=lambda x:x*j1(x)-Bi*j0(x)
        scan=np.linspace(1e-8,130,20000)
        roots=[brentq(f,a,b) for a,b in zip(scan[:-1],scan[1:]) if f(a)*f(b)<0]
        expected=np.zeros_like(s.T)
        for z in roots:
            A=2*j1(z)/(z*(j0(z)**2+j1(z)**2))
            expected+=A*np.exp(-alpha*z*z*times[:,None]/Q1.geometry.radius0**2)*j0(z*s.r/Q1.geometry.radius0)
        exact=Q1.initial.T+10-10*expected
        self.assertLess(float(np.max(np.abs(s.T-exact))),2e-4)
        np.testing.assert_allclose(s.C,Q1.initial.C,atol=1e-11)
        self.assertLess(s.meta["mass_balance_relative"],1e-10)
        self.assertLess(s.meta["q1_energy_balance_relative"],1e-8)

    def test_q4_outside_domain_mask_is_strict(self):
        s=solve_radial(Q4,n_internal=41,seek_end=False,t_end=1800,sample_times=[0,60,120])
        df=export.result_sheets(s,Q4)
        io_excel._validate("q4",df,io_excel.layout("q4"))
        df["Sheet1"].iloc[1,1]=np.nan
        with self.assertRaises(io_excel.ResultFormatError):
            io_excel._validate("q4",df,io_excel.layout("q4"))

    def test_radius_extrapolation_rejected(self):
        with self.assertRaises(ValueError):
            Boundary.from_attachments().radius(259201)


if __name__=="__main__":
    unittest.main(verbosity=2)
