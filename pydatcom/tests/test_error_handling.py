"""Tests for input validation and error handling across all modules."""

import numpy as np
import pytest

from pydatcom.atmosphere import standard_atmosphere
from pydatcom.geometry import WingGeometry, BodyGeometry
from pydatcom.flight_condition import flight_condition
from pydatcom.lift_slope import compute_lift_slope
from pydatcom.aero import body_aero
from pydatcom.flaps import flap_increment


class TestAtmosphereErrors:
    def test_altitude_too_high(self):
        with pytest.raises(ValueError, match="outside the valid range"):
            standard_atmosphere(3_000_000.0)

    def test_altitude_too_low(self):
        with pytest.raises(ValueError, match="outside the valid range"):
            standard_atmosphere(-20_000.0)

    def test_boundary_low_valid(self):
        # Should not raise at exact lower boundary
        result = standard_atmosphere(-16404.0)
        assert result.pressure > 0

    def test_boundary_high_valid(self):
        # Should not raise at exact upper boundary
        result = standard_atmosphere(2296588.0)
        assert result.pressure > 0


class TestWingGeometryErrors:
    def test_negative_chord(self):
        with pytest.raises(ValueError, match="non-negative"):
            WingGeometry(
                chord_root=-1.0, semi_span_i=0.0, semi_span_o=10.0,
                total_semi_span=10.0, chord_inboard=5.0, chord_tip=3.0,
            )

    def test_zero_semi_span(self):
        with pytest.raises(ValueError, match="positive"):
            WingGeometry(
                chord_root=5.0, semi_span_i=0.0, semi_span_o=10.0,
                total_semi_span=0.0, chord_inboard=5.0, chord_tip=3.0,
            )

    def test_negative_semi_span(self):
        with pytest.raises(ValueError, match="non-negative"):
            WingGeometry(
                chord_root=5.0, semi_span_i=-1.0, semi_span_o=10.0,
                total_semi_span=10.0, chord_inboard=5.0, chord_tip=3.0,
            )

    def test_semi_span_o_exceeds_total(self):
        with pytest.raises(ValueError, match="cannot exceed"):
            WingGeometry(
                chord_root=5.0, semi_span_i=0.0, semi_span_o=15.0,
                total_semi_span=10.0, chord_inboard=5.0, chord_tip=3.0,
            )


class TestBodyGeometryErrors:
    def test_too_few_stations(self):
        with pytest.raises(ValueError, match="At least 2"):
            BodyGeometry(
                x_stations=np.array([0.0]),
                cross_sections=np.array([0.0]),
                perimeters=np.array([0.0]),
                radii=np.array([0.0]),
            )

    def test_mismatched_lengths(self):
        with pytest.raises(ValueError, match="same length"):
            BodyGeometry(
                x_stations=np.array([0.0, 1.0, 2.0]),
                cross_sections=np.array([0.0, 1.0]),  # too short
                perimeters=np.array([0.0, 1.0, 2.0]),
                radii=np.array([0.0, 0.5, 1.0]),
            )


class TestFlightConditionErrors:
    def test_negative_mach(self):
        with pytest.raises(ValueError, match="non-negative"):
            flight_condition(0.0, -0.5)

    def test_zero_mach_valid(self):
        fc = flight_condition(0.0, 0.0)
        assert fc.velocity == 0.0
        assert fc.dynamic_pressure == 0.0


class TestLiftSlopeErrors:
    def test_supersonic_mach(self):
        wing = WingGeometry(
            chord_root=5.0, semi_span_i=0.0, semi_span_o=10.0,
            total_semi_span=10.0, chord_inboard=5.0, chord_tip=3.0,
        )
        with pytest.raises(ValueError, match="transonic/supersonic"):
            compute_lift_slope(wing, mach=1.2)

    def test_mach_exactly_one(self):
        wing = WingGeometry(
            chord_root=5.0, semi_span_i=0.0, semi_span_o=10.0,
            total_semi_span=10.0, chord_inboard=5.0, chord_tip=3.0,
        )
        with pytest.raises(ValueError, match="transonic/supersonic"):
            compute_lift_slope(wing, mach=1.0)


class TestBodyAeroErrors:
    @pytest.fixture
    def valid_body(self):
        x = np.array([0.0, 5.0, 10.0])
        r = np.array([0.0, 1.0, 0.5])
        return BodyGeometry(
            x_stations=x, cross_sections=np.pi * r ** 2,
            perimeters=2 * np.pi * r, radii=r,
        )

    def test_empty_alphas(self, valid_body):
        with pytest.raises(ValueError, match="must not be empty"):
            body_aero(valid_body, mach=0.3, reynolds=1e6,
                      alphas_deg=np.array([]), s_ref=1.0)

    def test_zero_sref(self, valid_body):
        with pytest.raises(ValueError, match="s_ref must be positive"):
            body_aero(valid_body, mach=0.3, reynolds=1e6,
                      alphas_deg=np.array([0.0]), s_ref=0.0)


class TestFlapErrors:
    def test_inboard_ge_outboard(self):
        with pytest.raises(ValueError, match="must be less than"):
            flap_increment(
                flap_chord_ratio=0.25, flap_deflection_deg=20.0,
                cl_alpha_per_rad=6.0,
                flap_span_inboard=5.0, flap_span_outboard=3.0,
                wing_semi_span=10.0,
            )

    def test_zero_semi_span(self):
        with pytest.raises(ValueError, match="positive"):
            flap_increment(
                flap_chord_ratio=0.25, flap_deflection_deg=20.0,
                cl_alpha_per_rad=6.0,
                flap_span_inboard=1.0, flap_span_outboard=5.0,
                wing_semi_span=0.0,
            )

    def test_bad_flap_type(self):
        with pytest.raises(ValueError, match="Unknown flap_type"):
            flap_increment(
                flap_chord_ratio=0.25, flap_deflection_deg=20.0,
                cl_alpha_per_rad=6.0,
                flap_span_inboard=1.0, flap_span_outboard=5.0,
                wing_semi_span=10.0, flap_type="turboflap",
            )

    def test_zero_chord_ratio(self):
        with pytest.raises(ValueError, match="positive"):
            flap_increment(
                flap_chord_ratio=0.0, flap_deflection_deg=20.0,
                cl_alpha_per_rad=6.0,
                flap_span_inboard=1.0, flap_span_outboard=5.0,
                wing_semi_span=10.0,
            )
