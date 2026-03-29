"""Tests for lift-curve slope computation."""

import numpy as np
import pytest

from pydatcom.geometry import WingGeometry
from pydatcom.lift_slope import compute_lift_slope
from pydatcom.constants import PI


@pytest.fixture
def rectangular_wing():
    return WingGeometry(
        chord_root=5.0,
        semi_span_i=0.0,
        semi_span_o=20.0,
        total_semi_span=20.0,
        chord_inboard=5.0,
        chord_tip=5.0,
    )


@pytest.fixture
def swept_tapered_wing():
    return WingGeometry(
        chord_root=10.0,
        semi_span_i=0.0,
        semi_span_o=15.0,
        total_semi_span=15.0,
        chord_inboard=10.0,
        chord_tip=3.0,
        sweep_le_inboard_tan=0.577,  # ~30 deg LE sweep
        thickness_to_chord=0.12,
    )


class TestBasicLiftSlope:
    def test_positive_cl_alpha(self, rectangular_wing):
        result = compute_lift_slope(rectangular_wing, mach=0.3)
        assert result.cl_alpha_per_rad > 0
        assert result.cl_alpha_per_deg > 0

    def test_less_than_2pi(self, rectangular_wing):
        """Finite-wing CL_alpha should be less than 2*pi (infinite wing)."""
        result = compute_lift_slope(rectangular_wing, mach=0.0)
        assert result.cl_alpha_per_rad < 2 * PI

    def test_per_deg_conversion(self, rectangular_wing):
        result = compute_lift_slope(rectangular_wing, mach=0.3)
        assert result.cl_alpha_per_deg == pytest.approx(
            result.cl_alpha_per_rad * PI / 180.0, rel=1e-6
        )


class TestMachEffect:
    def test_cl_alpha_increases_with_mach(self, rectangular_wing):
        """Prandtl-Glauert: CL_alpha increases as M approaches 1."""
        r_low = compute_lift_slope(rectangular_wing, mach=0.2)
        r_high = compute_lift_slope(rectangular_wing, mach=0.8)
        assert r_high.cl_alpha_per_rad > r_low.cl_alpha_per_rad

    def test_beta_correct(self, rectangular_wing):
        result = compute_lift_slope(rectangular_wing, mach=0.6)
        assert result.beta == pytest.approx(np.sqrt(1 - 0.36), rel=1e-3)


class TestSweepEffect:
    def test_sweep_reduces_cl_alpha(self, rectangular_wing):
        r_unswept = compute_lift_slope(rectangular_wing, mach=0.3,
                                        sweep_half_chord_deg=0.0)
        r_swept = compute_lift_slope(rectangular_wing, mach=0.3,
                                      sweep_half_chord_deg=30.0)
        assert r_swept.cl_alpha_per_rad < r_unswept.cl_alpha_per_rad


class TestCLMax:
    def test_cl_max_positive(self, swept_tapered_wing):
        result = compute_lift_slope(swept_tapered_wing, mach=0.3)
        assert result.cl_max > 0

    def test_alpha_cl_max_positive(self, swept_tapered_wing):
        result = compute_lift_slope(swept_tapered_wing, mach=0.3)
        assert result.alpha_cl_max_deg > 0


class TestHighAR:
    def test_approaches_2pi_for_high_ar(self):
        """Very high AR wing should approach 2*pi CL_alpha."""
        wing = WingGeometry(
            chord_root=1.0,
            semi_span_i=0.0,
            semi_span_o=100.0,
            total_semi_span=100.0,
            chord_inboard=1.0,
            chord_tip=1.0,
        )
        result = compute_lift_slope(wing, mach=0.0)
        # Should be close to 2*pi but somewhat less
        assert result.cl_alpha_per_rad > 0.9 * 2 * PI
        assert result.cl_alpha_per_rad < 2 * PI
