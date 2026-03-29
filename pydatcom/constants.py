"""
Physical and mathematical constants used throughout DATCOM.

All values match the original FORTRAN DATA statements. The atmospheric
model uses US Standard Atmosphere 1962 constants; aerodynamic routines
use the standard sea-level gravitational acceleration and air properties.
"""

import numpy as np

# --- Mathematical constants ---
PI = np.pi
DEG = PI / 180.0          # radians per degree
RAD = 180.0 / PI          # degrees per radian

# --- Earth and gravitational constants ---
G0 = 32.1740484           # sea-level gravitational acceleration, ft/s^2
R0 = 20_890_855.0         # mean Earth radius, ft
GMRS = 0.018743418        # g0 * M0 / R* , deg Rankine / ft

# --- Air properties (sea level, standard day) ---
GAMMA = 1.4               # ratio of specific heats for air (cp/cv)
M0 = 28.9644              # sea-level mean molecular weight of air

# --- Sea-level reference values (US Std Atm 1962) ---
T_SL = 518.67             # temperature, deg Rankine  (= 59 degF)
P_SL = 2116.2165          # pressure, lb/ft^2
RHO_SL = 0.0023769        # density, slugs/ft^3
CS_SL = 1116.45           # speed of sound, ft/s
