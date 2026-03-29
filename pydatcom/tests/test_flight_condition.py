"""Tests for flight condition computations."""

import numpy as np
import pytest

from pydatcom.flight_condition import flight_condition, reynolds_number


class TestSeaLevel:
    def test_velocity_from_mach(self):
        fc = flight_condition(0.0, 0.3)
        # V = M * a = 0.3 * ~1116 ft/s
        assert fc.velocity == pytest.approx(0.3 * fc.speed_of_sound, rel=1e-6)

    def test_dynamic_pressure(self):
        fc = flight_condition(0.0, 0.3)
        expected_q = 0.5 * fc.density * fc.velocity ** 2
        assert fc.dynamic_pressure == pytest.approx(expected_q, rel=1e-6)

    def test_reynolds_per_ft(self):
        fc = flight_condition(0.0, 0.3)
        assert fc.reynolds_per_ft > 0
        # Sea-level, M=0.3: Re/ft should be around 2e6
        assert 1e6 < fc.reynolds_per_ft < 5e6

    def test_viscosity_positive(self):
        fc = flight_condition(0.0, 0.3)
        assert fc.viscosity > 0


class TestAltitude:
    def test_density_decreases(self):
        fc_sl = flight_condition(0.0, 0.5)
        fc_alt = flight_condition(30000.0, 0.5)
        assert fc_alt.density < fc_sl.density

    def test_reynolds_decreases_with_altitude(self):
        fc_sl = flight_condition(0.0, 0.5)
        fc_alt = flight_condition(40000.0, 0.5)
        assert fc_alt.reynolds_per_ft < fc_sl.reynolds_per_ft


class TestReynoldsNumber:
    def test_scales_with_length(self):
        fc = flight_condition(0.0, 0.3)
        re1 = reynolds_number(fc, 1.0)
        re5 = reynolds_number(fc, 5.0)
        assert re5 == pytest.approx(5.0 * re1, rel=1e-6)

    def test_matches_per_ft(self):
        fc = flight_condition(0.0, 0.3)
        assert reynolds_number(fc, 1.0) == pytest.approx(fc.reynolds_per_ft, rel=1e-6)
