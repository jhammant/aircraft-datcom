"""Tests for the US Standard Atmosphere 1962 model."""

import numpy as np
import pytest

from pydatcom.atmosphere import standard_atmosphere, sea_level_properties


class TestSeaLevel:
    """Verify sea-level properties against the 1962 standard."""

    def test_temperature(self):
        atm = sea_level_properties()
        assert atm.temperature == pytest.approx(518.67, rel=1e-4)

    def test_pressure(self):
        atm = sea_level_properties()
        assert atm.pressure == pytest.approx(2116.22, rel=1e-3)

    def test_density(self):
        atm = sea_level_properties()
        assert atm.density == pytest.approx(0.002377, rel=1e-2)

    def test_speed_of_sound(self):
        atm = sea_level_properties()
        assert atm.speed_of_sound == pytest.approx(1116.45, rel=1e-3)

    def test_altitude_is_zero(self):
        atm = sea_level_properties()
        assert atm.altitude == 0.0


class TestTropopause:
    """The tropopause (~36 089 ft) is an isothermal layer boundary."""

    def test_temperature_drops(self):
        atm = standard_atmosphere(36089.0)
        # TMS at tropopause ~ 389.97 R; kinetic T = TMS since M = M0 below 295 kft
        assert atm.temperature == pytest.approx(389.97, rel=1e-3)

    def test_pressure(self):
        atm = standard_atmosphere(36089.0)
        assert atm.pressure == pytest.approx(472.68, rel=1e-2)


class TestHighAltitude:
    """Verify behaviour above 295 276 ft where molecular weight varies."""

    def test_300k_ft(self):
        atm = standard_atmosphere(300_000.0)
        # At 300 kft we're just above the mesopause; temperature ~ 330 R
        assert atm.temperature > 300.0
        # Pressure should be very low
        assert atm.pressure < 1.0

    def test_density_decreases_with_altitude(self):
        rho_sl = standard_atmosphere(0.0).density
        rho_50k = standard_atmosphere(50_000.0).density
        rho_100k = standard_atmosphere(100_000.0).density
        assert rho_sl > rho_50k > rho_100k > 0

    def test_speed_of_sound_at_altitude(self):
        # Speed of sound drops with temperature in troposphere
        a_sl = standard_atmosphere(0.0).speed_of_sound
        a_30k = standard_atmosphere(30_000.0).speed_of_sound
        assert a_sl > a_30k


class TestNegativeAltitude:
    """Below sea level (Dead Sea, Death Valley, etc.)."""

    def test_below_sea_level(self):
        atm = standard_atmosphere(-1000.0)
        sl = sea_level_properties()
        assert atm.pressure > sl.pressure
        assert atm.temperature > sl.temperature
        assert atm.density > sl.density


class TestGradients:
    """Verify that gradients have physically correct signs."""

    def test_pressure_gradient_negative(self):
        atm = standard_atmosphere(20_000.0)
        assert atm.d_p_dz < 0  # pressure decreases with altitude

    def test_density_gradient_negative(self):
        atm = standard_atmosphere(20_000.0)
        assert atm.d_rho_dz < 0  # density decreases with altitude
