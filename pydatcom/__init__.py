"""
PyDATCOM - Python translation of the USAF Digital DATCOM.

A preliminary design tool for estimating aerodynamic stability and control
characteristics of aircraft configurations. Originally written in FORTRAN
at the USAF Flight Dynamics Laboratory (now Wright Laboratory) circa 1976,
based on the USAF Stability and Control DATCOM handbook methods.

Reference:
    Finck, R.D., "USAF Stability and Control DATCOM", AFWAL-TR-83-3048,
    Wright-Patterson AFB, Ohio, 1978 (revised 1996).
"""

from pydatcom.atmosphere import standard_atmosphere, sea_level_properties
from pydatcom.geometry import WingGeometry, BodyGeometry
from pydatcom.aero import (
    lift_coefficient,
    drag_coefficient,
    moment_coefficient,
    body_aero,
)
from pydatcom.flight_condition import flight_condition, reynolds_number
from pydatcom.lift_slope import compute_lift_slope
from pydatcom.wing_body import wing_body_aero
from pydatcom.flaps import flap_increment
from pydatcom.input_parser import parse_datcom_input, parse_datcom_file

__version__ = "0.2.0"
__all__ = [
    # Atmosphere
    "standard_atmosphere",
    "sea_level_properties",
    # Geometry
    "WingGeometry",
    "BodyGeometry",
    # Aero (component)
    "lift_coefficient",
    "drag_coefficient",
    "moment_coefficient",
    "body_aero",
    # Flight condition
    "flight_condition",
    "reynolds_number",
    # Lift slope
    "compute_lift_slope",
    # Wing-body
    "wing_body_aero",
    # Flaps
    "flap_increment",
    # Input parser
    "parse_datcom_input",
    "parse_datcom_file",
]
