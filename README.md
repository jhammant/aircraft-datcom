# USAF Digital DATCOM — Now in Python

**52,000 lines of 1970s FORTRAN. Every fighter jet since the F-16. Now in Python.**

The USAF Digital DATCOM is one of the most consequential pieces of
aerospace software ever written. Developed at Wright-Patterson Air Force
Base in 1976, it encodes decades of wind tunnel data, empirical methods,
and aerodynamic theory into a tool that can predict the stability and
control characteristics of virtually any aircraft configuration — from a
paper napkin sketch to a preliminary design.

For forty years, engineers at Lockheed, Boeing, Northrop, General
Dynamics, and dozens of other companies used DATCOM to size wings, place
tails, check stability margins, and estimate performance before building
a single wind tunnel model. The F-16, F/A-18, F-117, and countless other
aircraft passed through DATCOM during their early design phases.

The original code is 354 FORTRAN source files, written in a style that
predates structured programming, with single-letter variable names,
COMMON blocks the size of city blocks, and empirical tables embedded as
DATA statements. It is brilliant engineering — and virtually unreadable
to a modern programmer.

**PyDATCOM changes that.**

## What this is

This repository contains:

1. **The original FORTRAN source** (`src/`) — 354 files, ~52,000 lines,
   compilable with `gfortran -std=legacy -fallow-argument-mismatch`.

2. **PyDATCOM** (`pydatcom/`) — a Python/NumPy translation of the core
   methods, with physics docstrings, readable variable names, and a
   pip-installable package.

3. **A validation report** (`docs/validation.md`) comparing PyDATCOM
   against the original FORTRAN output and published wind tunnel data.

## Quick start

```bash
pip install -e ".[dev]"

# What's the atmosphere at 35,000 ft?
pydatcom atmos 35000

# Parse a classic DATCOM input file
pydatcom parse data/sprob.in

# Run a subsonic analysis
pydatcom run data/sprob.in
```

```python
import numpy as np
from pydatcom import (
    flight_condition, compute_lift_slope,
    WingGeometry, lift_coefficient, drag_coefficient,
)

# F-16-like wing: AR=3, 40° sweep, 3% thickness
fc = flight_condition(altitude_ft=0, mach=0.6)
wing = WingGeometry(
    chord_root=16.5, semi_span_i=0.0, semi_span_o=15.0,
    total_semi_span=15.0, chord_inboard=16.5, chord_tip=3.5,
    sweep_le_inboard_tan=0.839, thickness_to_chord=0.04,
)
ls = compute_lift_slope(wing, mach=0.6, sweep_half_chord_deg=25.0)
print(f"CL_alpha = {ls.cl_alpha_per_deg:.4f} /deg")  # ~0.06 /deg
```

## Accuracy

PyDATCOM matches the original FORTRAN output and agrees with published
wind tunnel data within the expected accuracy of handbook methods:

| Module | Method | Typical accuracy |
|---|---|---|
| Atmosphere | US Std Atm 1962 (exact translation) | < 0.01% |
| Lift slope | Helmbold/Polhamus formula | 1–5% |
| Zero-lift drag | Skin friction + form factor | 5–15% |
| Induced drag | Oswald efficiency method | 5–10% |
| Body aero | Slender body + Allen-Perkins | 10–20% |
| Wing-body | K_W(B) / K_B(W) interference | 5–15% |
| Pitching moment | AC position method | 10–20% |

See [`docs/validation.md`](docs/validation.md) for detailed comparisons
against FORTRAN DATCOM output, NACA 0012 data, and F-16 published values.

## Performance

| | Time | Notes |
|---|---:|---|
| FORTRAN (gfortran -O2) | 0.01 s | 17-case sprob.in |
| Python (PyDATCOM) | 0.06 s | Same input, includes startup |

The FORTRAN is ~6x faster wall-clock, but Python startup dominates.
For the actual aerodynamic computation, both are effectively instantaneous.
PyDATCOM's advantage is integration with modern Python tooling — scipy
optimizers, matplotlib plotting, jupyter notebooks, parametric sweeps.

## What's translated

| FORTRAN | Python | What |
|---|---|---|
| `atmos.f` | `atmosphere.py` | US Standard Atmosphere 1962 |
| `wtgeom.f` | `geometry.py` | Wing/tail planform geometry |
| `bodyrt.f` | `geometry.py` + `aero.py` | Body geometry and aerodynamics |
| `wtlift.f` | `lift_slope.py` | CL_alpha from geometry (Helmbold/Polhamus) |
| `liftcf.f` | `aero.py` | Lift coefficient vs alpha |
| `cdrag.f` | `aero.py` | Drag coefficient (friction + induced) |
| `cmalph.f` | `aero.py` | Pitching moment coefficient |
| `wblift.f` / `wbdrag.f` / `wbcm.f` | `wing_body.py` | Wing-body interference |
| `liftfp.f` | `flaps.py` | Trailing-edge flap effects |
| `input.f` | `input_parser.py` | Classic DATCOM `$NAMELIST$` input parser |
| `TBFUNX` / `TLINEX` / `TLIN3X` | `utils.py` | Table interpolation |

## Package structure

```text
pydatcom/
  __init__.py           Public API (11 modules, 92 tests)
  atmosphere.py         US Standard Atmosphere 1962
  constants.py          Physical constants
  geometry.py           Wing/tail/body geometry
  aero.py               CL, CD, CM, body aero
  flight_condition.py   Altitude + Mach → V, q, Re
  lift_slope.py         CL_alpha from planform geometry
  wing_body.py          Wing-body interference factors
  flaps.py              Trailing-edge flap effects
  input_parser.py       Classic DATCOM input format parser
  utils.py              Interpolation utilities
  cli.py                Command-line interface
  tests/                92 tests
```

## Testing

```bash
cd pydatcom && python3 -m pytest tests/ -v
# 92 passed
```

## Building the original FORTRAN

```bash
gfortran -std=legacy -w -fallow-argument-mismatch -finit-local-zero -O2 \
  -o datcom_fortran $(ls src/*.f | grep -v dplot.f)
./datcom_fortran data/sprob.in
cat output.dat
```

## Documentation

- [`pydatcom/README.md`](pydatcom/README.md) — Package API documentation
- [`docs/validation.md`](docs/validation.md) — Accuracy and performance validation
- [`doc/`](doc/) — Original USAF DATCOM User's Manual (Vol 1 & 2, PDF)

## References

1. Finck, R.D., "USAF Stability and Control DATCOM", AFWAL-TR-83-3048,
   Wright-Patterson AFB, Ohio, 1978 (revised 1996).
2. Abbott, I.H. and von Doenhoff, A.E., "Theory of Wing Sections",
   Dover, 1959.

## License

The original DATCOM code is U.S. Government work (public domain).
The Python translation is released under the Unlicense.
