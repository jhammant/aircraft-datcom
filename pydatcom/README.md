# PyDATCOM

Python translation of the **USAF Digital DATCOM** -- a preliminary design
tool for estimating static stability, control, and aerodynamic
characteristics of aircraft configurations.

The original FORTRAN program (~52 000 lines, 354 source files) was written
at the USAF Flight Dynamics Laboratory (Wright-Patterson AFB) in the 1970s.
PyDATCOM translates the core methods into readable, documented Python with
NumPy, preserving the empirical tables and physics while making the code
accessible for modern workflows.

## Installation

```bash
pip install -e ".[dev]"
```

Requires Python >= 3.9 and NumPy >= 1.21.

## Quick start

```python
import numpy as np
from pydatcom import (
    flight_condition, reynolds_number,
    WingGeometry, BodyGeometry,
    compute_lift_slope,
    lift_coefficient, drag_coefficient, moment_coefficient,
    body_aero, wing_body_aero, flap_increment,
)

# 1. Flight condition
fc = flight_condition(altitude_ft=30_000, mach=0.6)
print(f"q = {fc.dynamic_pressure:.1f} lb/ft^2, Re/ft = {fc.reynolds_per_ft:.0f}")

# 2. Wing geometry
wing = WingGeometry(
    chord_root=10.0, semi_span_i=0.0, semi_span_o=15.0,
    total_semi_span=15.0, chord_inboard=10.0, chord_tip=3.0,
    thickness_to_chord=0.12,
)

# 3. Lift-curve slope (computed, not an input!)
ls = compute_lift_slope(wing, mach=0.6, sweep_half_chord_deg=20.0)
print(f"CL_alpha = {ls.cl_alpha_per_deg:.4f} /deg")

# 4. Aerodynamic coefficients
alphas = np.arange(-2, 14, 2.0)
re = reynolds_number(fc, wing.mac_total)
cl = lift_coefficient(wing, 0.6, ls.cl_alpha_per_rad, alphas)
cd = drag_coefficient(wing, 0.6, re, ls.cl_alpha_per_rad, alphas, cl.cl)

for a, c, d in zip(alphas, cl.cl, cd.cd):
    print(f"  alpha={a:5.1f}  CL={c:7.4f}  CD={d:8.5f}")
```

## CLI

```bash
# Standard atmosphere at 35 000 ft
pydatcom atmos 35000

# Parse a classic DATCOM input file to JSON
pydatcom parse data/sprob.in

# Run subsonic analysis from DATCOM input
pydatcom run data/sprob.in
```

## Package structure

```text
pydatcom/
  __init__.py           Public API
  atmosphere.py         US Standard Atmosphere 1962  (src/atmos.f)
  constants.py          Physical constants
  geometry.py           Wing/tail/body geometry      (src/wtgeom.f, src/bodyrt.f)
  aero.py               CL, CD, CM, body aero        (src/liftcf.f, cdrag.f, cmalph.f, bodyrt.f)
  flight_condition.py   Altitude+Mach -> V, q, Re    (FLGTCD common block)
  lift_slope.py         CL_alpha from geometry        (src/wtlift.f)
  wing_body.py          Wing-body interference        (src/wblift.f, wbdrag.f, wbcm.f)
  flaps.py              Trailing-edge flap effects    (src/liftfp.f)
  input_parser.py       Classic DATCOM input parser   (src/input.f)
  utils.py              Interpolation utilities       (TBFUNX, TLINEX, TLIN3X, TRAPZ)
  cli.py                Command-line interface
  tests/                92 tests covering all modules
```

## What is translated

| FORTRAN subroutine(s) | Python module | Physics |
|---|---|---|
| ATMOS | `atmosphere.py` | Full US Std Atm 1962, inverse-square gravity, 9 output quantities |
| WTGEOM | `geometry.py` | Planform area, AR, taper, MAC, sweep for single/cranked wings |
| BODYRT (geometry) | `geometry.py` | Body length, max cross-section, fineness ratio |
| WTLIFT | `lift_slope.py` | Helmbold/Polhamus CL_alpha with Mach, sweep, taper corrections |
| LIFTCF | `aero.py` | Linear + post-stall CL for straight-tapered wings |
| CDRAG | `aero.py` | CD0 (skin friction + form factor) + induced drag, Oswald e |
| CMALPH | `aero.py` | CM from AC position with Prandtl-Glauert correction |
| BODYRT (aero) | `aero.py` | Slender-body CN_alpha + Allen-Perkins crossflow + base drag |
| WBLIFT, WBDRAG, WBCM | `wing_body.py` | K_W(B), K_B(W) interference; combined CL, CD, CM |
| LIFTFP | `flaps.py` | Section effectiveness, K', K_b spanwise correction |
| INPUT | `input_parser.py` | $NAMELIST$ groups, control cards, NACA specs, multi-case |
| TBFUNX, TLINEX, TLIN3X, TRAPZ | `utils.py` | 1-D / 2-D / 3-D table interpolation, trapezoidal integration |

## Testing

```bash
pytest pydatcom/tests/ -v
```

92 tests covering atmosphere, geometry, aero coefficients, flight conditions,
lift-curve slope, wing-body combination, flap effects, input parsing, and
end-to-end integration.

## Reference

Finck, R.D., "USAF Stability and Control DATCOM", AFWAL-TR-83-3048,
Wright-Patterson AFB, Ohio, 1978 (revised 1996).

## License

The original DATCOM code is U.S. Government work (public domain).
This Python translation is released under the Unlicense.
