"""
Flight condition setup.

Connects the atmosphere model to aerodynamic calculations by computing
flow properties (Reynolds number, dynamic pressure, etc.) from altitude
and Mach number.  This mirrors the role of the FLGTCD COMMON block and
the flight-condition loop in the FORTRAN main program.

Physics
-------
Given geometric altitude Z and Mach number M:

* Speed of sound *a* and density *rho* come from the standard atmosphere.
* True airspeed V = M * a.
* Dynamic pressure q = 0.5 * rho * V^2.
* Reynolds number per unit length Re/L = rho * V / mu, where the dynamic
  viscosity mu is obtained from Sutherland's law:

      mu = mu_ref * (T/T_ref)^1.5 * (T_ref + S) / (T + S)

  with mu_ref = 3.737e-7 slug/(ft*s), T_ref = 518.67 R, S = 198.72 R.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from pydatcom.atmosphere import standard_atmosphere, AtmosphereResult
from pydatcom.constants import G0


# Sutherland's law constants (imperial units)
_MU_REF = 3.737e-7    # reference viscosity, slug/(ft*s) at T_ref
_T_REF = 518.67       # reference temperature, deg Rankine (= 59 degF)
_S_SUTH = 198.72      # Sutherland constant for air, deg Rankine


def _dynamic_viscosity(temperature_rankine: float) -> float:
    """Dynamic viscosity of air via Sutherland's law.

    Parameters
    ----------
    temperature_rankine : float
        Kinetic temperature, deg Rankine.

    Returns
    -------
    float
        Dynamic viscosity mu, slug/(ft*s).
    """
    t = temperature_rankine
    return _MU_REF * (t / _T_REF) ** 1.5 * (_T_REF + _S_SUTH) / (t + _S_SUTH)


@dataclass
class FlightCondition:
    """Computed flow properties at a given altitude and Mach number.

    Attributes
    ----------
    altitude_ft : float
        Geometric altitude, ft.
    mach : float
        Free-stream Mach number.
    velocity : float
        True airspeed, ft/s.
    dynamic_pressure : float
        Free-stream dynamic pressure q, lb/ft^2.
    reynolds_per_ft : float
        Reynolds number per foot of reference length.
    temperature : float
        Free-stream static temperature, deg Rankine.
    pressure : float
        Free-stream static pressure, lb/ft^2.
    density : float
        Free-stream density, slugs/ft^3.
    speed_of_sound : float
        Speed of sound, ft/s.
    viscosity : float
        Dynamic viscosity, slug/(ft*s).
    atmosphere : AtmosphereResult
        Full atmosphere state (for access to gradients, etc.).
    """

    altitude_ft: float
    mach: float
    velocity: float
    dynamic_pressure: float
    reynolds_per_ft: float
    temperature: float
    pressure: float
    density: float
    speed_of_sound: float
    viscosity: float
    atmosphere: AtmosphereResult


def flight_condition(altitude_ft: float, mach: float) -> FlightCondition:
    """Compute flow properties from altitude and Mach number.

    Parameters
    ----------
    altitude_ft : float
        Geometric altitude, ft.
    mach : float
        Free-stream Mach number (must be > 0).

    Returns
    -------
    FlightCondition
    """
    atm = standard_atmosphere(altitude_ft)
    velocity = mach * atm.speed_of_sound
    q = 0.5 * atm.density * velocity ** 2
    mu = _dynamic_viscosity(atm.temperature)
    re_per_ft = atm.density * velocity / mu if mu > 0 else 0.0

    return FlightCondition(
        altitude_ft=altitude_ft,
        mach=mach,
        velocity=velocity,
        dynamic_pressure=q,
        reynolds_per_ft=re_per_ft,
        temperature=atm.temperature,
        pressure=atm.pressure,
        density=atm.density,
        speed_of_sound=atm.speed_of_sound,
        viscosity=mu,
        atmosphere=atm,
    )


def reynolds_number(fc: FlightCondition, ref_length_ft: float) -> float:
    """Reynolds number based on a reference length.

    Parameters
    ----------
    fc : FlightCondition
        Flow properties.
    ref_length_ft : float
        Reference length (e.g. MAC or body length), ft.

    Returns
    -------
    float
        Reynolds number (dimensionless).
    """
    return fc.reynolds_per_ft * ref_length_ft
