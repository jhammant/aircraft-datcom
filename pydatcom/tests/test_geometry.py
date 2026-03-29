"""Tests for wing and body geometry computations."""

import numpy as np
import pytest

from pydatcom.geometry import WingGeometry, BodyGeometry, compute_nose_length


class TestSimpleRectangularWing:
    """A rectangular (untapered, unswept) wing is the simplest case."""

    @pytest.fixture
    def wing(self):
        # 10 ft chord, 20 ft semi-span, no crank
        return WingGeometry(
            chord_root=10.0,
            semi_span_i=0.0,
            semi_span_o=20.0,
            total_semi_span=20.0,
            chord_inboard=10.0,
            chord_tip=10.0,
        )

    def test_area(self, wing):
        # DATCOM stores area as (c_root + c_tip) * semi_span per panel
        # For rectangular: (10 + 10) * 20 = 400 (one-side planform * 2 chords)
        assert wing.area_total == pytest.approx(400.0, rel=1e-2)

    def test_aspect_ratio(self, wing):
        # DATCOM: A(7) = 4 * so^2 / A(3) = 4 * 400 / 400 = 4
        expected_ar = 4.0 * 20.0 ** 2 / 400.0
        assert wing.aspect_ratio == pytest.approx(expected_ar, rel=1e-3)

    def test_taper_ratio(self, wing):
        # Rectangular: taper = 1.0
        assert wing.taper_ratio_inboard == pytest.approx(1.0, rel=1e-3)

    def test_mac(self, wing):
        # Rectangular MAC = chord
        assert wing.mac_total == pytest.approx(10.0, rel=1e-2)


class TestTaperedWing:
    """A simple tapered wing (no crank)."""

    @pytest.fixture
    def wing(self):
        return WingGeometry(
            chord_root=12.0,
            semi_span_i=0.0,
            semi_span_o=15.0,
            total_semi_span=15.0,
            chord_inboard=12.0,
            chord_tip=4.0,
        )

    def test_area(self, wing):
        # Trapezoidal: S = (c_root + c_tip)/2 * span (one side, but
        # DATCOM stores as (c_root + c_tip) * semi_span per panel pair)
        expected = (4.0 + 12.0) * 15.0  # inner panel: (c_out_root + ci)*span
        assert wing.area_total == pytest.approx(expected, rel=1e-2)

    def test_taper_less_than_one(self, wing):
        assert wing.taper_ratio_inboard >= 1.0  # ci/ct = 12/4 = 3


class TestBodyGeometry:
    """Verify body geometry computations."""

    @pytest.fixture
    def body(self):
        x = np.array([0, 2, 5, 10, 15, 20], dtype=float)
        s = np.array([0, 1.0, 5.0, 8.0, 8.0, 3.0], dtype=float)
        p = np.array([0, 3.5, 7.9, 10.0, 10.0, 6.1], dtype=float)
        r = np.array([0, 0.56, 1.26, 1.60, 1.60, 0.98], dtype=float)
        return BodyGeometry(x_stations=x, cross_sections=s, perimeters=p,
                            radii=r, base_area=3.0)

    def test_length(self, body):
        assert body.length == 20.0

    def test_max_cross_section(self, body):
        assert body.max_cross_section == 8.0

    def test_fineness_ratio(self, body):
        d_max = np.sqrt(4 * 8.0 / np.pi)
        assert body.fineness_ratio == pytest.approx(20.0 / d_max, rel=1e-3)

    def test_base_area_clamped(self, body):
        # 3.0 > 0.3 * 8.0 = 2.4, so base area should stay at 3.0
        assert body.base_area == 3.0


class TestNoseLength:
    def test_monotonic_body(self):
        x = np.array([0, 5, 10, 15])
        s = np.array([0, 2, 4, 6])
        assert compute_nose_length(x, s) == 15.0  # never decreases

    def test_boat_tailed_body(self):
        x = np.array([0, 5, 10, 15, 20])
        s = np.array([0, 2, 5, 5, 3])
        # Nose ends where cross-section first strictly decreases
        assert compute_nose_length(x, s) == 15.0
