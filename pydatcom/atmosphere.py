"""
US Standard Atmosphere 1962 model.

Translated from ``src/atmos.f`` (SUBROUTINE ATMOS). Computes atmospheric
properties as a function of geometric altitude using an inverse-square
gravitational field. Results agree with the COESA document within 1 %
at all altitudes up to 700 km (2 296 588 ft).

Physics
-------
Below 295 276 ft the *molecular-scale temperature* (TMS) is piecewise-linear
in *geopotential altitude* H = R0*Z/(R0+Z), and pressure is obtained from
the barometric formula:

    P = P_j * (TM_j / TMS)^(g0*M0 / (R* * dTMS/dH))       (non-zero lapse)
    P = P_j * exp(g0*M0*(H_j - H) / (R* * TMS))            (isothermal)

Above 295 276 ft TMS is piecewise-linear in *geometric altitude* Z, and
the molecular weight varies with altitude, requiring a modified pressure
integral that accounts for the inverse-square gravity:

    P = P_j * exp[ ... integral involving (R0/(R0+Z))^2 ... ]

The speed of sound is:

    a = 49.022164 * sqrt(TMS)   [ft/s]

which comes from a = sqrt(gamma * R* * TMS / M0) with gamma = 1.4.

Density is derived from the equation of state:

    rho = (g0*M0 / R*) * P / (g0 * TMS)

and the *kinetic* temperature is T = M * TMS / M0  where M is the local
molecular weight.

Reference
---------
U.S. Standard Atmosphere, 1962.  U.S. Government Printing Office,
Washington, D.C., 1962.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from pydatcom.constants import G0, R0, GMRS, M0

# ---------------------------------------------------------------------------
# Atmosphere layer data (from FORTRAN DATA statements in atmos.f)
# ---------------------------------------------------------------------------

# Geopotential altitude breakpoints [ft] -- used below 295 276 ft
_HG = np.array([
    -16404.0, 0.0, 36089.0, 65617.0, 104987.0,
    154199.0, 170604.0, 200131.0, 250186.0, 291160.0,
])

# Geometric altitude breakpoints [ft] -- used above 295 276 ft
_ZM = np.array([
    295276.0, 328084.0, 360892.0, 393701.0, 492126.0,
    524934.0, 557743.0, 623360.0, 754593.0, 984252.0,
    1312336.0, 1640420.0, 1968504.0, 2296588.0,
])

# Molecular weight profile above 295 276 ft
_WM = np.array([
    28.9644, 28.88, 28.56, 28.07, 26.92,
    26.66, 26.40, 25.85, 24.70, 22.66,
    19.94, 17.94, 16.84, 16.17,
])

# Molecular-scale temperature [deg Rankine] at each layer boundary.
# First 10 entries correspond to _HG layers; next 13 to _ZM layers.
_TM = np.array([
    577.17, 518.67, 389.97, 389.97, 411.57,
    487.17, 487.17, 454.77, 325.17, 325.17,
    379.17, 469.17, 649.17, 1729.17, 1999.17,
    2179.17, 2431.17, 2791.17, 3295.17, 3889.17,
    4357.17, 4663.17, 4861.17,
])

# Pressure [lb/ft^2] at each layer boundary.
# First 10 for _HG layers; next 12 for _ZM layers.
_PM = np.array([
    3711.0839, 2116.2165, 472.67563, 114.34314,
    18.128355, 2.3162178, 1.2321972, 3.8030279e-01,
    2.1671352e-02, 3.4313478e-03, 6.2773411e-04, 1.5349091e-04,
    5.2624212e-05, 1.0561806e-05, 7.7083076e-06, 5.8267151e-06,
    3.5159854e-06, 1.4520255e-06, 3.9290563e-07, 8.4030242e-08,
    2.2835256e-08, 7.1875452e-09,
])


@dataclass
class AtmosphereResult:
    """Atmospheric properties at a given geometric altitude.

    Attributes
    ----------
    altitude : float
        Geometric altitude, ft.
    speed_of_sound : float
        Speed of sound, ft/s.
    d_cs_dz : float
        Normalised sound-speed gradient (1/a)(da/dZ), 1/ft.
    pressure : float
        Static pressure, lb/ft^2.
    d_p_dz : float
        Pressure gradient dP/dZ, lb/ft^3.
    density : float
        Air density, slugs/ft^3.
    d_rho_dz : float
        Normalised density gradient (1/rho)(drho/dZ), 1/ft.
    temperature : float
        Kinetic temperature, deg Rankine.
    d_t_dz : float
        Temperature gradient dT/dZ, deg Rankine/ft.
    """

    altitude: float
    speed_of_sound: float
    d_cs_dz: float
    pressure: float
    d_p_dz: float
    density: float
    d_rho_dz: float
    temperature: float
    d_t_dz: float


def standard_atmosphere(z: float) -> AtmosphereResult:
    """Compute US Standard Atmosphere 1962 properties at geometric altitude *z*.

    This is a direct translation of SUBROUTINE ATMOS(A3, A8, A4) from
    ``src/atmos.f``.

    Parameters
    ----------
    z : float
        Geometric altitude in feet.  Valid from -16 404 ft to 2 296 588 ft
        (approximately -5 km to 700 km).

    Returns
    -------
    AtmosphereResult
        Dataclass with all nine atmospheric quantities and their gradients.

    Raises
    ------
    ValueError
        If *z* is outside the valid altitude range.
    """
    if z < -16404.0 or z > 2296588.0:
        raise ValueError(
            f"Altitude {z:.0f} ft is outside the valid range "
            f"[-16404, 2296588] ft for the US Standard Atmosphere 1962."
        )
    g = G0 * (R0 / (R0 + z)) ** 2

    if z <= 295276.0:
        # --- TMS is piecewise-linear in geopotential altitude H ---
        h = R0 * z / (R0 + z)

        # Find the layer containing H
        j = 0
        for i in range(1, 10):
            if _HG[i] >= h:
                j = i - 1
                break

        # Molecular-scale temperature lapse rate and TMS
        elh = (_TM[j + 1] - _TM[j]) / (_HG[j + 1] - _HG[j])
        tms = _TM[j] + elh * (h - _HG[j])
        elz = elh * g / G0
        dmdz = 0.0
        em = M0

        # Pressure
        if elh != 0.0:
            # Non-zero lapse rate: barometric formula (power law)
            pressure = _PM[j] * (_TM[j] / tms) ** (GMRS / elh)
        else:
            # Isothermal layer: exponential decay
            pressure = _PM[j] * np.exp(GMRS * (_HG[j] - h) / tms)
    else:
        # --- TMS is piecewise-linear in geometric altitude Z ---
        k = 0
        j_idx = 0
        for i in range(1, 14):
            if _ZM[i] >= z:
                j_idx = i + 8  # index into _TM (offset by lower-atmosphere entries)
                k = i - 1
                break

        elz = (_TM[j_idx + 1] - _TM[j_idx]) / (_ZM[k + 1] - _ZM[k])
        tms = _TM[j_idx] + elz * (z - _ZM[k])
        dmdz = (_WM[k + 1] - _WM[k]) / (_ZM[k + 1] - _ZM[k])
        em = _WM[k] + dmdz * (z - _ZM[k])
        zlz = z - tms / elz

        # Pressure equation for TMS linear with Z (accounts for inverse-square g)
        pressure = _PM[j_idx] * np.exp(
            GMRS / elz * (R0 / (R0 + zlz)) ** 2 * (
                (z - _ZM[k]) * (R0 + zlz) / ((R0 + z) * (R0 + _ZM[k]))
                - np.log(tms * (R0 + _ZM[k]) / (_TM[j_idx] * (R0 + z)))
            )
        )

    # Speed of sound: a = sqrt(gamma * R* * TMS / M0)
    # The constant 49.022164 = sqrt(1.4 * 1545.31 / 28.9644) in ft-lb units
    cs = 49.022164 * np.sqrt(tms)
    d_cs_dz = 0.5 * elz / tms

    # Density from equation of state
    rho = GMRS * pressure / (G0 * tms)
    d_rho_dz = -(rho * g / pressure + elz / tms)
    d_p_dz = -rho * g

    # Kinetic temperature (differs from TMS above ~295 000 ft where M < M0)
    temperature = em * tms / M0
    d_t_dz = (em * elz + tms * dmdz) / M0

    return AtmosphereResult(
        altitude=z,
        speed_of_sound=cs,
        d_cs_dz=d_cs_dz,
        pressure=pressure,
        d_p_dz=d_p_dz,
        density=rho,
        d_rho_dz=d_rho_dz,
        temperature=temperature,
        d_t_dz=d_t_dz,
    )


def sea_level_properties() -> AtmosphereResult:
    """Return standard sea-level atmospheric properties (Z = 0 ft)."""
    return standard_atmosphere(0.0)
