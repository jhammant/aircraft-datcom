"""
Interpolation and numerical utilities.

Translates the family of DATCOM interpolation routines (TBFUNX, TLINEX,
TLIN3X, TRAPZ, etc.) into numpy-based equivalents.
"""

from __future__ import annotations

import numpy as np


def table_lookup(x: float, xtab: np.ndarray, ytab: np.ndarray) -> float:
    """Linearly interpolate *ytab* at *x* given breakpoints *xtab*.

    Translates the core path of SUBROUTINE TBFUNX.  Extrapolation is
    clamped to the nearest table value (flat extrapolation) to match
    DATCOM convention.

    Parameters
    ----------
    x : float
        Independent variable value.
    xtab : np.ndarray
        Monotonically increasing breakpoint array.
    ytab : np.ndarray
        Dependent variable array (same length as *xtab*).

    Returns
    -------
    float
        Interpolated value.
    """
    return float(np.interp(x, xtab, ytab))


def table_lookup_2d(
    x1: float,
    x2: float,
    x1tab: np.ndarray,
    x2tab: np.ndarray,
    ytab: np.ndarray,
) -> float:
    """Bilinear interpolation on a 2-D table.

    Translates the core path of SUBROUTINE TLINEX.  *ytab* is stored in
    FORTRAN column-major order: ``ytab[i, j]`` corresponds to
    ``(x1tab[i], x2tab[j])``.

    Parameters
    ----------
    x1, x2 : float
        Independent variable values.
    x1tab : np.ndarray, shape (n1,)
        Breakpoints for first dimension.
    x2tab : np.ndarray, shape (n2,)
        Breakpoints for second dimension.
    ytab : np.ndarray, shape (n1, n2)
        Table values.

    Returns
    -------
    float
        Interpolated value.
    """
    # Clamp indices
    i1 = np.searchsorted(x1tab, x1, side="right") - 1
    i1 = np.clip(i1, 0, len(x1tab) - 2)
    i2 = np.searchsorted(x2tab, x2, side="right") - 1
    i2 = np.clip(i2, 0, len(x2tab) - 2)

    # Fractional positions
    dx1 = x1tab[i1 + 1] - x1tab[i1]
    dx2 = x2tab[i2 + 1] - x2tab[i2]
    t1 = (x1 - x1tab[i1]) / dx1 if dx1 != 0.0 else 0.0
    t2 = (x2 - x2tab[i2]) / dx2 if dx2 != 0.0 else 0.0
    t1 = np.clip(t1, 0.0, 1.0)
    t2 = np.clip(t2, 0.0, 1.0)

    # Bilinear
    y00 = ytab[i1, i2]
    y10 = ytab[i1 + 1, i2]
    y01 = ytab[i1, i2 + 1]
    y11 = ytab[i1 + 1, i2 + 1]
    return float(
        y00 * (1 - t1) * (1 - t2)
        + y10 * t1 * (1 - t2)
        + y01 * (1 - t1) * t2
        + y11 * t1 * t2
    )


def table_lookup_3d(
    x1: float,
    x2: float,
    x3: float,
    x1tab: np.ndarray,
    x2tab: np.ndarray,
    x3tab: np.ndarray,
    ytab: np.ndarray,
) -> float:
    """Trilinear interpolation on a 3-D table.

    Translates the core path of SUBROUTINE TLIN3X.

    Parameters
    ----------
    x1, x2, x3 : float
        Independent variable values.
    x1tab, x2tab, x3tab : np.ndarray
        Breakpoint arrays for each dimension.
    ytab : np.ndarray, shape (n1, n2, n3)
        Table values.

    Returns
    -------
    float
        Interpolated value.
    """
    def _frac(val, tab):
        i = np.searchsorted(tab, val, side="right") - 1
        i = np.clip(i, 0, len(tab) - 2)
        dx = tab[i + 1] - tab[i]
        t = (val - tab[i]) / dx if dx != 0.0 else 0.0
        t = np.clip(t, 0.0, 1.0)
        return int(i), float(t)

    i1, t1 = _frac(x1, x1tab)
    i2, t2 = _frac(x2, x2tab)
    i3, t3 = _frac(x3, x3tab)

    result = 0.0
    for d1, w1 in ((i1, 1 - t1), (i1 + 1, t1)):
        for d2, w2 in ((i2, 1 - t2), (i2 + 1, t2)):
            for d3, w3 in ((i3, 1 - t3), (i3 + 1, t3)):
                result += w1 * w2 * w3 * ytab[d1, d2, d3]
    return result


def trapz(y: np.ndarray, x: np.ndarray) -> float:
    """Trapezoidal integration (translation of SUBROUTINE TRAPZ).

    Parameters
    ----------
    y : np.ndarray
        Integrand values.
    x : np.ndarray
        Abscissa values (same length as *y*).

    Returns
    -------
    float
        Definite integral approximation.
    """
    return float(np.trapezoid(y, x))


def equal_space(x_in: np.ndarray, y_in: np.ndarray, n_out: int = 20):
    """Redistribute data onto equally-spaced abscissae.

    Translates SUBROUTINE EQSPC1. Returns *(x_eq, y_eq, dy_dx)* where
    *x_eq* has *n_out* equally-spaced points spanning the input range,
    *y_eq* is the linearly-interpolated ordinate, and *dy_dx* is the
    numerical derivative at each point.
    """
    x_eq = np.linspace(x_in[0], x_in[-1], n_out)
    y_eq = np.interp(x_eq, x_in, y_in)
    dy_dx = np.gradient(y_eq, x_eq)
    return x_eq, y_eq, dy_dx


def angles_from_tan(tan_value: float):
    """Return (sin, cos, tan) given a tangent value.

    Matches the DATCOM ANGLES subroutine which packs sin/cos/tan into an
    array given a sweep-angle tangent.
    """
    angle = np.arctan(tan_value)
    return np.sin(angle), np.cos(angle), tan_value
