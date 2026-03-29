"""Tests for flap effects."""

import numpy as np
import pytest

from pydatcom.flaps import flap_increment


class TestPlainFlap:
    def test_positive_deflection_positive_lift(self):
        result = flap_increment(
            flap_chord_ratio=0.25,
            flap_deflection_deg=20.0,
            cl_alpha_per_rad=2 * np.pi,
            flap_span_inboard=1.0,
            flap_span_outboard=8.0,
            wing_semi_span=10.0,
        )
        assert result.delta_cl > 0

    def test_negative_deflection_negative_lift(self):
        result = flap_increment(
            flap_chord_ratio=0.25,
            flap_deflection_deg=-20.0,
            cl_alpha_per_rad=2 * np.pi,
            flap_span_inboard=1.0,
            flap_span_outboard=8.0,
            wing_semi_span=10.0,
        )
        assert result.delta_cl < 0

    def test_zero_deflection_zero_increment(self):
        result = flap_increment(
            flap_chord_ratio=0.25,
            flap_deflection_deg=0.0,
            cl_alpha_per_rad=2 * np.pi,
            flap_span_inboard=1.0,
            flap_span_outboard=8.0,
            wing_semi_span=10.0,
        )
        assert result.delta_cl == pytest.approx(0.0, abs=1e-10)

    def test_drag_always_positive(self):
        for delta in [10, 20, 30, -10, -20]:
            result = flap_increment(
                flap_chord_ratio=0.25,
                flap_deflection_deg=float(delta),
                cl_alpha_per_rad=2 * np.pi,
                flap_span_inboard=1.0,
                flap_span_outboard=8.0,
                wing_semi_span=10.0,
            )
            assert result.delta_cd >= 0


class TestFlapSpan:
    def test_wider_flap_more_lift(self):
        r_narrow = flap_increment(
            flap_chord_ratio=0.25,
            flap_deflection_deg=20.0,
            cl_alpha_per_rad=2 * np.pi,
            flap_span_inboard=3.0,
            flap_span_outboard=5.0,
            wing_semi_span=10.0,
        )
        r_wide = flap_increment(
            flap_chord_ratio=0.25,
            flap_deflection_deg=20.0,
            cl_alpha_per_rad=2 * np.pi,
            flap_span_inboard=1.0,
            flap_span_outboard=8.0,
            wing_semi_span=10.0,
        )
        assert r_wide.delta_cl > r_narrow.delta_cl

    def test_kb_between_zero_and_one(self):
        result = flap_increment(
            flap_chord_ratio=0.25,
            flap_deflection_deg=20.0,
            cl_alpha_per_rad=2 * np.pi,
            flap_span_inboard=2.0,
            flap_span_outboard=8.0,
            wing_semi_span=10.0,
        )
        assert 0 < result.k_b < 1.0


class TestFlapChordRatio:
    def test_larger_cfc_more_lift(self):
        r_small = flap_increment(
            flap_chord_ratio=0.10,
            flap_deflection_deg=20.0,
            cl_alpha_per_rad=2 * np.pi,
            flap_span_inboard=1.0,
            flap_span_outboard=8.0,
            wing_semi_span=10.0,
        )
        r_large = flap_increment(
            flap_chord_ratio=0.30,
            flap_deflection_deg=20.0,
            cl_alpha_per_rad=2 * np.pi,
            flap_span_inboard=1.0,
            flap_span_outboard=8.0,
            wing_semi_span=10.0,
        )
        assert r_large.delta_cl > r_small.delta_cl


class TestKPrimeCorrection:
    def test_kprime_decreases_with_deflection(self):
        r10 = flap_increment(
            flap_chord_ratio=0.25,
            flap_deflection_deg=10.0,
            cl_alpha_per_rad=2 * np.pi,
            flap_span_inboard=1.0,
            flap_span_outboard=8.0,
            wing_semi_span=10.0,
        )
        r40 = flap_increment(
            flap_chord_ratio=0.25,
            flap_deflection_deg=40.0,
            cl_alpha_per_rad=2 * np.pi,
            flap_span_inboard=1.0,
            flap_span_outboard=8.0,
            wing_semi_span=10.0,
        )
        assert r40.k_prime < r10.k_prime


class TestMoment:
    def test_positive_flap_nosedown_moment(self):
        """Positive flap deflection should give nose-down (negative) moment."""
        result = flap_increment(
            flap_chord_ratio=0.25,
            flap_deflection_deg=20.0,
            cl_alpha_per_rad=2 * np.pi,
            flap_span_inboard=1.0,
            flap_span_outboard=8.0,
            wing_semi_span=10.0,
        )
        assert result.delta_cm < 0
