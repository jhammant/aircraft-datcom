"""Tests for aerodynamic coefficient computations."""

import numpy as np
import pytest

from pydatcom.geometry import WingGeometry, BodyGeometry
from pydatcom.aero import lift_coefficient, drag_coefficient, moment_coefficient, body_aero


@pytest.fixture
def simple_wing():
    """A moderate-AR straight-tapered wing for testing."""
    return WingGeometry(
        chord_root=6.0,
        semi_span_i=0.0,
        semi_span_o=15.0,
        total_semi_span=15.0,
        chord_inboard=6.0,
        chord_tip=3.0,
        thickness_to_chord=0.12,
        x_max_tc=0.30,
    )


@pytest.fixture
def alphas():
    return np.array([0.0, 2.0, 4.0, 6.0, 8.0, 10.0, 12.0])


class TestLift:
    def test_zero_alpha_zero_lift(self, simple_wing, alphas):
        result = lift_coefficient(
            simple_wing, mach=0.3, cl_alpha_per_rad=2 * np.pi,
            alphas_deg=alphas,
        )
        assert result.cl[0] == pytest.approx(0.0, abs=1e-6)

    def test_positive_alpha_positive_lift(self, simple_wing, alphas):
        result = lift_coefficient(
            simple_wing, mach=0.3, cl_alpha_per_rad=2 * np.pi,
            alphas_deg=alphas,
        )
        assert all(result.cl[1:] > 0)

    def test_lift_increases_with_alpha(self, simple_wing, alphas):
        result = lift_coefficient(
            simple_wing, mach=0.3, cl_alpha_per_rad=2 * np.pi,
            alphas_deg=alphas,
        )
        # CL should be monotonically increasing for pre-stall alphas
        for i in range(len(alphas) - 1):
            assert result.cl[i + 1] > result.cl[i]

    def test_cl_alpha_slope(self, simple_wing):
        result = lift_coefficient(
            simple_wing, mach=0.3, cl_alpha_per_rad=2 * np.pi,
            alphas_deg=np.array([0.0, 1.0]),
        )
        # Finite-difference slope should match cl_alpha
        slope = (result.cl[1] - result.cl[0]) / 1.0  # per degree
        assert slope == pytest.approx(result.cl_alpha, rel=0.1)


class TestDrag:
    def test_cd0_positive(self, simple_wing, alphas):
        cl = np.array([0.0, 0.2, 0.4, 0.6, 0.8, 1.0, 1.1])
        result = drag_coefficient(
            simple_wing, mach=0.3, reynolds=5e6,
            cl_alpha_per_rad=2 * np.pi, alphas_deg=alphas, cl_array=cl,
        )
        assert result.cd0 > 0

    def test_drag_minimum_near_zero_lift(self, simple_wing, alphas):
        cl = np.array([0.0, 0.2, 0.4, 0.6, 0.8, 1.0, 1.1])
        result = drag_coefficient(
            simple_wing, mach=0.3, reynolds=5e6,
            cl_alpha_per_rad=2 * np.pi, alphas_deg=alphas, cl_array=cl,
        )
        # Minimum CD should be at or near zero lift
        assert result.cd[0] == pytest.approx(result.cd0, rel=0.01)

    def test_drag_increases_with_lift(self, simple_wing, alphas):
        cl = np.array([0.0, 0.2, 0.4, 0.6, 0.8, 1.0, 1.1])
        result = drag_coefficient(
            simple_wing, mach=0.3, reynolds=5e6,
            cl_alpha_per_rad=2 * np.pi, alphas_deg=alphas, cl_array=cl,
        )
        # CD should increase with |CL|
        for i in range(len(cl) - 1):
            assert result.cd[i + 1] >= result.cd[i]

    def test_oswald_factor_reasonable(self, simple_wing, alphas):
        cl = np.array([0.0, 0.2, 0.4, 0.6, 0.8, 1.0, 1.1])
        result = drag_coefficient(
            simple_wing, mach=0.3, reynolds=5e6,
            cl_alpha_per_rad=2 * np.pi, alphas_deg=alphas, cl_array=cl,
        )
        assert 0.5 <= result.oswald_e <= 1.0


class TestMoment:
    def test_cm_at_ac(self, simple_wing, alphas):
        """When CG is at the AC, CM should be constant (= CM0)."""
        cl = np.array([0.0, 0.2, 0.4, 0.6, 0.8, 1.0, 1.1])
        result = moment_coefficient(
            simple_wing, mach=0.3, cl_alpha_per_rad=2 * np.pi,
            alphas_deg=alphas, cl_array=cl,
            x_cg_over_cbar=result.x_ac_over_cbar
            if hasattr((result := moment_coefficient(
                simple_wing, mach=0.3, cl_alpha_per_rad=2 * np.pi,
                alphas_deg=alphas, cl_array=cl,
            )), 'x_ac_over_cbar') else 0.25,
        )
        # When x_cg = x_ac, CM should be approximately constant
        cm_range = result.cm.max() - result.cm.min()
        assert cm_range < 0.01

    def test_forward_cg_stable(self, simple_wing, alphas):
        """Forward CG (< x_ac) should give negative dCM/dalpha (stable)."""
        cl = np.array([0.0, 0.2, 0.4, 0.6, 0.8, 1.0, 1.1])
        result = moment_coefficient(
            simple_wing, mach=0.3, cl_alpha_per_rad=2 * np.pi,
            alphas_deg=alphas, cl_array=cl,
            x_cg_over_cbar=0.15,  # well forward of AC
        )
        assert result.cm_alpha < 0  # stable


class TestBodyAero:
    @pytest.fixture
    def body(self):
        x = np.linspace(0, 20, 21)
        # Ogive-like body
        r = np.where(x <= 10, x / 10.0 * 1.5, 1.5 * (1.0 - (x - 10) / 20.0))
        s = np.pi * r ** 2
        p = 2.0 * np.pi * r
        return BodyGeometry(x_stations=x, cross_sections=s, perimeters=p,
                            radii=r, base_area=0.5)

    def test_cn_alpha_positive(self, body, alphas):
        result = body_aero(body, mach=0.3, reynolds=1e7,
                           alphas_deg=alphas, s_ref=10.0, cbar=5.0)
        assert result.cn_alpha > 0

    def test_cd0_positive(self, body, alphas):
        result = body_aero(body, mach=0.3, reynolds=1e7,
                           alphas_deg=alphas, s_ref=10.0, cbar=5.0)
        assert result.cd0 > 0

    def test_zero_alpha_zero_cl(self, body):
        result = body_aero(body, mach=0.3, reynolds=1e7,
                           alphas_deg=np.array([0.0]), s_ref=10.0, cbar=5.0)
        assert abs(result.cl[0]) < 1e-6
