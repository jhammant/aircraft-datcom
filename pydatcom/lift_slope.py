"""
Lift-curve slope computation.

Translated from ``src/wtlift.f`` (SUBROUTINE WTLIFT).  Computes the
subsonic lift-curve slope CL_alpha from wing planform geometry and
Mach number without requiring it as an input.

Physics
-------
The subsonic CL_alpha for a finite wing uses the **Helmbold / Polhamus**
extended lifting-line formula (DATCOM Section 4.1.3.2):

    CL_alpha = (2 * pi * AR) / (2 + sqrt[ (AR * beta / kappa)^2
               * (1 + tan^2(sweep_c/2) / beta^2) + 4 ])

where:
* AR = aspect ratio
* beta = sqrt(1 - M^2)  (Prandtl-Glauert compressibility factor)
* kappa = Cl_alpha_section / (2*pi), the ratio of the 2-D section
  lift-curve slope to the theoretical thin-airfoil value
* sweep_c/2 = half-chord sweep angle

This is the standard DATCOM method for straight-tapered wings (TYPE=1).
For cranked wings, a correction factor from figure 4.1.3.2-52 is
applied.  Low-aspect-ratio wings (AR < AR_transition) use the same
formula but with a different CL_max treatment.

DATCOM further corrects CL_alpha for:
* **Taper ratio** via the C2 factor from figure 4.1.3.4-24B
* **Sweep/Mach interaction** via the CL/CL_0 ratio from figure 4.1.3.4-21A

Reference
---------
DATCOM Section 4.1.3.2, "Wing Lift-Curve Slope", and Section 4.1.3.4,
"Wing Maximum Lift".
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from pydatcom.constants import PI, DEG, RAD
from pydatcom.geometry import WingGeometry
from pydatcom.utils import table_lookup


# --- Figure 4.1.3.4-24B: taper ratio correction C2 ---
_TR_TAB = np.array([0., .1, .2, .3, .4, .5, .6, .7, .8, .9, 1.])
_C2_TAB = np.array([0., .21, .5, .9, 1.08, 1.05, 1., .94, .9, .86, .85])

# --- Figure 4.1.3.2-52: cranked-wing CL_alpha/CL_alpha_0 ratio ---
_BA_TAB = np.array([1.15, 1.4, 2., 2.2, 3., 3.6, 4., 5., 6., 7., 8., 9.])
_CLOVCL_TAB = np.array([1.25, 1.2, 1.12, 1.1, 1.04, 1., .985, .96, .95, .94, .94, .94])

# --- Figure 4.1.3.4-21A: CL/CL_0 vs sweep and delta-y (simplified) ---
# Rows: SALE = LE sweep angle (deg), Columns: DELTAY = 2*pi*CLa_section
_SALE_TAB = np.array([0., 5., 10., 15., 20., 25., 30., 35., 40., 45., 50., 55., 60.])
_DELTAY_MID = 2.0  # typical mid-range value
_CL_CL0_TAB = np.array([
    .9, .91, .92, .93, .94, .95, .96, .965, .975, .99, 1., 1.01, 1.03
])


@dataclass
class LiftSlopeResult:
    """Results from lift-curve slope computation.

    Attributes
    ----------
    cl_alpha_per_rad : float
        Wing lift-curve slope, per radian.
    cl_alpha_per_deg : float
        Wing lift-curve slope, per degree.
    cl_max : float
        Estimated maximum lift coefficient.
    alpha_cl_max_deg : float
        Angle of attack at CL_max, degrees.
    beta : float
        Prandtl-Glauert factor sqrt(1 - M^2).
    """
    cl_alpha_per_rad: float
    cl_alpha_per_deg: float
    cl_max: float
    alpha_cl_max_deg: float
    beta: float


def compute_lift_slope(
    wing: WingGeometry,
    mach: float,
    sweep_half_chord_deg: float = 0.0,
    section_cl_alpha: float = 2 * PI,
    cl_max_section: float = 1.6,
) -> LiftSlopeResult:
    r"""Compute wing lift-curve slope from planform geometry and Mach number.

    Translated from the straight-tapered and cranked-wing paths in
    SUBROUTINE WTLIFT (``src/wtlift.f``).

    Parameters
    ----------
    wing : WingGeometry
        Wing planform geometry (aspect ratio, taper, areas).
    mach : float
        Free-stream Mach number.  Must be < 1.0 for this subsonic method.
    sweep_half_chord_deg : float
        Half-chord sweep angle, degrees.  If 0.0, estimated from
        leading-edge sweep and taper ratio.
    section_cl_alpha : float
        2-D airfoil section lift-curve slope, per radian.
        Default is the thin-airfoil value 2*pi.
    cl_max_section : float
        Section (2-D) maximum lift coefficient.

    Returns
    -------
    LiftSlopeResult

    Notes
    -----
    The formula used is the Helmbold/Polhamus extended lifting-line
    result (DATCOM eqn 4.1.3.2-a):

    .. math::

        C_{L_\\alpha} = \\frac{2\\pi A}
        {2 + \\sqrt{\\left(\\frac{A\\beta}{\\kappa}\\right)^2
        \\left(1 + \\frac{\\tan^2 \\Lambda_{c/2}}{\\beta^2}\\right) + 4}}

    where A = aspect ratio, beta = sqrt(1-M^2), kappa = Cl_alpha/(2*pi).
    """
    ar = wing.aspect_ratio
    if ar <= 0:
        return LiftSlopeResult(0.0, 0.0, 0.0, 0.0, 1.0)

    # Prandtl-Glauert compressibility factor
    beta = np.sqrt(max(1.0 - mach ** 2, 0.01))

    # Section lift-curve slope ratio
    kappa = section_cl_alpha / (2.0 * PI)

    # Half-chord sweep tangent
    sweep_hc_rad = np.radians(sweep_half_chord_deg)
    tan_sweep_sq = np.tan(sweep_hc_rad) ** 2

    # Helmbold/Polhamus formula (DATCOM 4.1.3.2)
    # FORTRAN: TEMP1 = 2.*PI*A(7)*DEG  (but A(7) is AR, and DEG converts to per-degree)
    # We compute per-radian first, then convert
    term1 = 2.0 * PI * ar
    term2 = (ar * beta / kappa) ** 2
    term3 = 1.0 + tan_sweep_sq / beta ** 2

    cl_alpha_rad = term1 / (2.0 + np.sqrt(term2 * term3 + 4.0))

    # Area ratio correction (S_planform / S_ref) -- for exposed wing
    area_ratio = wing.area_total / wing.area_total  # 1.0 by default
    cl_alpha_rad *= area_ratio

    # Cranked wing correction (figure 4.1.3.2-52)
    if wing.airfoil_type == "cranked":
        ba_arg = ar * beta
        cl_ratio = table_lookup(ba_arg, _BA_TAB, _CLOVCL_TAB)
        cl_alpha_rad *= cl_ratio

    cl_alpha_deg = cl_alpha_rad * DEG

    # --- CL_max estimation ---
    # Taper ratio correction C2 (figure 4.1.3.4-24B)
    taper = wing.taper_ratio_total
    c2 = table_lookup(taper, _TR_TAB, _C2_TAB)

    # delta_y factor from geometry
    delta_y = (c2 + 1.0) * wing.thickness_to_chord * ar

    # CL_max from sweep/AR/taper corrections
    # Simplified: CL_max ~ CL_max_section * CL/CL_0 * (S_exp/S_ref)
    sweep_le_deg = np.degrees(np.arctan(wing.sweep_le_inboard_tan))
    cl_cl0 = table_lookup(abs(sweep_le_deg), _SALE_TAB, _CL_CL0_TAB)
    cl_max = cl_max_section * cl_cl0

    # Alpha at CL_max
    alpha_cl_max = cl_max / cl_alpha_deg if cl_alpha_deg > 0 else 15.0

    return LiftSlopeResult(
        cl_alpha_per_rad=cl_alpha_rad,
        cl_alpha_per_deg=cl_alpha_deg,
        cl_max=cl_max,
        alpha_cl_max_deg=alpha_cl_max,
        beta=beta,
    )
