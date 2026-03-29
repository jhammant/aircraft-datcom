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

## API Reference

### Atmosphere

#### `standard_atmosphere(z: float) -> AtmosphereResult`

Compute US Standard Atmosphere 1962 properties at geometric altitude *z* (ft).
Returns pressure, temperature, density, speed of sound, and all gradients.
Raises `ValueError` for altitudes outside [-16 404, 2 296 588] ft.

```python
atm = standard_atmosphere(35000)
atm.temperature   # 394.06 deg R
atm.pressure       # 499.34 lb/ft^2
atm.density        # 7.38e-4 slugs/ft^3
atm.speed_of_sound # 973.14 ft/s
```

#### `sea_level_properties() -> AtmosphereResult`

Shorthand for `standard_atmosphere(0.0)`.

### Flight Condition

#### `flight_condition(altitude_ft, mach) -> FlightCondition`

Compute V, q, Re/ft, viscosity from altitude and Mach.
Raises `ValueError` for negative Mach.

```python
fc = flight_condition(30000, 0.8)
fc.velocity          # ft/s
fc.dynamic_pressure  # lb/ft^2
fc.reynolds_per_ft   # Re per foot
fc.viscosity         # slug/(ft*s)
```

#### `reynolds_number(fc, ref_length_ft) -> float`

Reynolds number for a given reference length.

### Geometry

#### `WingGeometry(chord_root, semi_span_i, semi_span_o, total_semi_span, chord_inboard, chord_tip, ...)`

Compute wing planform geometry (area, AR, taper, MAC, spanwise MAC station).
Supports single-panel and cranked (inboard+outboard) configurations.
Raises `ValueError` for negative chords/spans or impossible geometry.

Computed attributes: `area_total`, `aspect_ratio`, `taper_ratio_total`,
`mac_total`, `y_mac_total`, `area_exposed`, and per-panel values.

#### `BodyGeometry(x_stations, cross_sections, perimeters, radii, base_area=0, nose_type='ogive')`

Compute body geometry from station arrays.
Raises `ValueError` for < 2 stations or mismatched array lengths.

Computed attributes: `length`, `max_cross_section`, `fineness_ratio`,
`max_diameter`, `base_diameter`.

#### `compute_nose_length(x_stations, cross_sections) -> float`

Find the station where cross-section first decreases.

### Lift-Curve Slope

#### `compute_lift_slope(wing, mach, sweep_half_chord_deg=0, section_cl_alpha=2*pi, cl_max_section=1.6) -> LiftSlopeResult`

Compute CL_alpha from geometry using the Helmbold/Polhamus formula.
Subsonic only -- raises `ValueError` for Mach >= 1.0.

```python
ls = compute_lift_slope(wing, mach=0.6, sweep_half_chord_deg=25.0)
ls.cl_alpha_per_rad   # CL_alpha in /rad
ls.cl_alpha_per_deg   # CL_alpha in /deg
ls.cl_max             # estimated CL_max
ls.alpha_cl_max_deg   # alpha at CL_max
ls.beta               # Prandtl-Glauert factor
```

### Aerodynamic Coefficients

#### `lift_coefficient(wing, mach, cl_alpha_per_rad, alphas_deg, ...) -> LiftResult`

CL vs alpha. Linear below CL_max, post-stall blending above.

#### `drag_coefficient(wing, mach, reynolds, cl_alpha_per_rad, alphas_deg, cl_array, ...) -> DragResult`

CD = CD0 + CL^2/(pi*AR*e). Skin friction (Karman-Schoenherr) + form factor
+ Oswald efficiency.

#### `moment_coefficient(wing, mach, cl_alpha_per_rad, alphas_deg, cl_array, ...) -> MomentResult`

CM about CG from AC position with Prandtl-Glauert Mach correction.

#### `body_aero(body, mach, reynolds, alphas_deg, ...) -> BodyAeroResult`

Body-alone CL, CD, CM via slender-body theory + Allen-Perkins crossflow.
Raises `ValueError` for empty alphas or non-positive s_ref.

### Wing-Body Combination

#### `wing_body_aero(...) -> WingBodyResult`

Combined wing-body coefficients using K_W(B) and K_B(W) interference factors
from DATCOM figures 4.3.1.2-10A/B.

Returns: `cl_alpha_wb`, `k_wb`, `k_bw`, `cd0_wb`, `r_wb`, `x_ac_wb`,
and arrays `cl_wb`, `cd_wb`, `cm_wb`.

### Flaps

#### `flap_increment(flap_chord_ratio, flap_deflection_deg, cl_alpha_per_rad, ...) -> FlapResult`

Incremental delta_CL, delta_CD, delta_CM from trailing-edge flap deflection.
Supports plain, split, slotted, and fowler types.
Raises `ValueError` for invalid geometry or unknown flap type.

### Input Parser

#### `parse_datcom_input(text: str) -> list[DatcomCase]`

Parse a DATCOM input string into a list of cases. Handles `$NAMELIST$`
groups, control cards, NACA specs, booleans, FORTRAN repeat notation,
and multi-case inheritance.

#### `parse_datcom_file(path) -> list[DatcomCase]`

Parse from a file path.

### Utilities

#### `table_lookup(x, xtab, ytab) -> float`

1-D linear interpolation with clamped extrapolation (TBFUNX).

#### `table_lookup_2d(x1, x2, x1tab, x2tab, ytab) -> float`

Bilinear interpolation (TLINEX).

#### `table_lookup_3d(x1, x2, x3, x1tab, x2tab, x3tab, ytab) -> float`

Trilinear interpolation (TLIN3X).

#### `trapz(y, x) -> float`

Trapezoidal integration (TRAPZ).

#### `equal_space(x_in, y_in, n_out=20) -> (x_eq, y_eq, dy_dx)`

Redistribute data onto equally-spaced abscissae (EQSPC1).

## Error Handling

All public functions validate inputs and raise `ValueError` with
descriptive messages:

- Altitude out of range (atmosphere)
- Negative chords, spans, or zero total span (geometry)
- Mismatched array lengths (body geometry)
- Negative Mach number (flight condition)
- Supersonic Mach in subsonic method (lift slope)
- Invalid flap geometry or type (flaps)
- Empty alpha arrays or zero reference area (body aero)

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
  tests/                Unit and integration tests
```

## Testing

```bash
python -m pytest pydatcom/tests/ -v
```

## Reference

Finck, R.D., "USAF Stability and Control DATCOM", AFWAL-TR-83-3048,
Wright-Patterson AFB, Ohio, 1978 (revised 1996).

## License

The original DATCOM code is U.S. Government work (public domain).
This Python translation is released under the Unlicense.
