"""Tests for wing-body combination."""

import numpy as np
import pytest

from pydatcom.wing_body import wing_body_aero


@pytest.fixture
def alphas():
    return np.array([0., 2., 4., 6., 8., 10.])


@pytest.fixture
def basic_inputs(alphas):
    """Typical wing + body inputs for a moderate configuration."""
    n = len(alphas)
    cl_alpha_w = 0.08  # per degree
    cl_alpha_b = 0.005  # per degree
    cl_wing = cl_alpha_w * alphas
    cl_body = cl_alpha_b * alphas
    cd0_w = 0.010
    cd0_b = 0.005
    cd_wing = cd0_w + 0.05 * cl_wing ** 2
    cd_body = cd0_b + 0.01 * cl_body ** 2
    cm_body = -0.002 * alphas
    return dict(
        cl_alpha_wing_deg=cl_alpha_w,
        cl_alpha_body_deg=cl_alpha_b,
        cd0_wing=cd0_w,
        cd0_body=cd0_b,
        body_diameter=2.0,
        wing_span=10.0,
        alphas_deg=alphas,
        cl_wing=cl_wing,
        cd_wing=cd_wing,
        cl_body=cl_body,
        cd_body=cd_body,
        cm_body=cm_body,
    )


class TestInterferenceFactors:
    def test_kwb_greater_than_one(self, basic_inputs):
        result = wing_body_aero(**basic_inputs)
        # d/b = 2/10 = 0.2, K_W(B) should be > 1
        assert result.k_wb > 1.0

    def test_kbw_positive(self, basic_inputs):
        result = wing_body_aero(**basic_inputs)
        assert result.k_bw > 0.0

    def test_cl_alpha_wb_greater_than_components(self, basic_inputs):
        result = wing_body_aero(**basic_inputs)
        # Combined CL_alpha should exceed body alone
        assert result.cl_alpha_wb > basic_inputs["cl_alpha_body_deg"]


class TestCombinedCoefficients:
    def test_cl_wb_at_zero_alpha(self, basic_inputs):
        result = wing_body_aero(**basic_inputs)
        assert result.cl_wb[0] == pytest.approx(0.0, abs=1e-6)

    def test_cl_wb_positive_at_positive_alpha(self, basic_inputs):
        result = wing_body_aero(**basic_inputs)
        assert all(result.cl_wb[1:] > 0)

    def test_cd_wb_positive(self, basic_inputs):
        result = wing_body_aero(**basic_inputs)
        assert all(result.cd_wb > 0)

    def test_drag_ratio_reasonable(self, basic_inputs):
        result = wing_body_aero(**basic_inputs)
        assert 0.8 < result.r_wb < 1.2


class TestLargeBodyRatio:
    def test_large_db_ratio(self, alphas):
        """When d/b > 0.8, uses figure 4.3.1.2-12C path."""
        n = len(alphas)
        result = wing_body_aero(
            cl_alpha_wing_deg=0.08,
            cl_alpha_body_deg=0.005,
            cd0_wing=0.01,
            cd0_body=0.005,
            body_diameter=9.0,  # d/b = 0.9
            wing_span=10.0,
            alphas_deg=alphas,
            cl_wing=0.08 * alphas,
            cd_wing=0.01 + 0.05 * (0.08 * alphas) ** 2,
            cl_body=0.005 * alphas,
            cd_body=0.005 * np.ones(n),
            cm_body=-0.002 * alphas,
        )
        # Should still produce valid results
        assert result.cl_alpha_wb > 0
        assert result.k_bw == 0.0  # large d/b path sets K_B(W) = 0
