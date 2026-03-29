"""
High-lift device (flap) effects.

Translated from ``src/liftfp.f`` (SUBROUTINE LIFTFP).  Computes the
incremental lift, drag, and moment due to trailing-edge flap deflection.

Physics
-------
DATCOM treats flap effects as increments to the clean-wing coefficients:

    CL_flap = CL_clean + delta_CL_flap
    CD_flap = CD_clean + delta_CD_flap

The incremental lift is:

    delta_CL = CL_alpha * delta_alpha_flap * K_b * S_flapped / S_ref

where:
* CL_alpha is the wing lift-curve slope
* delta_alpha_flap = (Cl_delta / Cl_alpha) * delta_f is the effective
  angle-of-attack increment due to flap deflection delta_f
* Cl_delta is the 2-D section flap effectiveness from thin-airfoil
  theory corrected by the empirical factor K' (figure 6.1.1.1-40)
* K_b is the span-loading correction from figure 6.1.4.1-15

The 2-D theoretical flap effectiveness is:

    (Cl_delta)_theory = 2 * [arccos(1 - 2*cf/c) + 2*sqrt(cf/c*(1-cf/c))]

where cf/c is the flap-chord-to-airfoil-chord ratio.  This is corrected
by K' from figure 6.1.1.1-39A (subsonic) for thickness and Mach effects.

Flap types supported:
* Plain (simple hinged trailing edge)
* Split (lower surface only)
* Slotted (single, double, triple)
* Fowler

Reference
---------
DATCOM Section 6.1.1.1, "Two-Dimensional Lift Effectiveness of
Trailing-Edge High-Lift and Control Devices".
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from pydatcom.constants import PI, DEG, RAD
from pydatcom.utils import table_lookup, table_lookup_2d


# ===================================================================
# Empirical tables from FORTRAN DATA statements
# ===================================================================

# --- Figure 6.1.1.1-39A: 2-D section flap effectiveness (Cl_delta)_theory ---
# X = cf/c (flap chord ratio), Y = Cl_delta_theory (per radian)
_CFC_39A = np.array([0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50])
_CLDELTA_39A = np.array([1.77, 2.50, 3.00, 3.46, 3.82, 4.16, 4.69, 5.14])

# --- Figure 6.1.1.1-40: empirical correction K' vs delta and cf/c ---
# Simplified: K' at delta=10 deg for various cf/c
_CFC_40 = np.array([0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50])
_KPRIME_D10 = np.array([1.0, 1.0, 0.994, 0.989, 0.97, 0.938, 0.9])
_KPRIME_D20 = np.array([0.90, 0.89, 0.87, 0.85, 0.80, 0.75, 0.695])
_KPRIME_D40 = np.array([0.641, 0.618, 0.595, 0.569, 0.541, 0.513, 0.490])
_KPRIME_D60 = np.array([0.562, 0.531, 0.500, 0.480, 0.461, 0.440, 0.423])

# --- Figure 6.1.4.1-15: spanwise correction K_b ---
_ETA_KB = np.array([0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 1.0])
_KB_TAPER0 = np.array([0.0, 0.160, 0.305, 0.440, 0.560, 0.670, 0.772, 0.860, 0.930, 0.96, 0.981, 1.0])
_KB_TAPER05 = np.array([0.0, 0.140, 0.270, 0.400, 0.515, 0.630, 0.735, 0.830, 0.912, 0.947, 0.972, 1.0])
_KB_TAPER1 = np.array([0.0, 0.125, 0.255, 0.370, 0.490, 0.600, 0.705, 0.800, 0.885, 0.921, 0.955, 1.0])


# Flap-type drag factors (empirical, from DATCOM Section 6.1.5)
_FLAP_CD_FACTOR = {
    "plain": 0.0023,
    "split": 0.0045,
    "slotted": 0.0015,
    "fowler": 0.0010,
}


@dataclass
class FlapResult:
    """Incremental aerodynamic effects from flap deflection.

    Attributes
    ----------
    delta_cl : float
        Incremental lift coefficient due to flap deflection.
    delta_cd : float
        Incremental drag coefficient due to flap deflection.
    delta_cm : float
        Incremental pitching moment coefficient.
    delta_alpha_0_deg : float
        Change in zero-lift angle of attack, degrees.
    cl_delta_section : float
        2-D section flap effectiveness, per radian.
    k_prime : float
        Empirical correction factor.
    k_b : float
        Spanwise loading correction factor.
    """
    delta_cl: float
    delta_cd: float
    delta_cm: float
    delta_alpha_0_deg: float
    cl_delta_section: float
    k_prime: float
    k_b: float


def flap_increment(
    flap_chord_ratio: float,
    flap_deflection_deg: float,
    cl_alpha_per_rad: float,
    flap_span_inboard: float,
    flap_span_outboard: float,
    wing_semi_span: float,
    wing_taper_ratio: float = 0.5,
    flap_type: str = "plain",
    mach: float = 0.0,
    s_ref: float = 1.0,
    s_flapped: float | None = None,
    x_flap_hinge_over_c: float = 0.75,
) -> FlapResult:
    r"""Compute incremental aerodynamic effects of a trailing-edge flap.

    Translated from the core path of SUBROUTINE LIFTFP (``src/liftfp.f``).

    Parameters
    ----------
    flap_chord_ratio : float
        cf/c -- ratio of flap chord (aft of hinge) to wing chord.
        Typically 0.10 to 0.40.
    flap_deflection_deg : float
        Flap deflection angle, degrees (positive = down).
    cl_alpha_per_rad : float
        Wing lift-curve slope, per radian.
    flap_span_inboard : float
        Inboard end of flap, ft from centreline.
    flap_span_outboard : float
        Outboard end of flap, ft from centreline.
    wing_semi_span : float
        Wing semi-span, ft.
    wing_taper_ratio : float
        Wing taper ratio (0 = pointed tip, 1 = rectangular).
    flap_type : str
        ``'plain'``, ``'split'``, ``'slotted'``, or ``'fowler'``.
    mach : float
        Free-stream Mach number.
    s_ref : float
        Reference area, ft^2.
    s_flapped : float or None
        Flapped planform area, ft^2.  If None, estimated from spans.
    x_flap_hinge_over_c : float
        Chordwise location of flap hinge line, fraction of chord.

    Returns
    -------
    FlapResult
    """
    if flap_span_inboard >= flap_span_outboard:
        raise ValueError(
            f"flap_span_inboard ({flap_span_inboard}) must be less than "
            f"flap_span_outboard ({flap_span_outboard})."
        )
    if wing_semi_span <= 0:
        raise ValueError("wing_semi_span must be positive.")
    if flap_chord_ratio <= 0:
        raise ValueError("flap_chord_ratio must be positive.")
    if flap_type not in _FLAP_CD_FACTOR:
        raise ValueError(
            f"Unknown flap_type {flap_type!r}. "
            f"Valid types: {', '.join(_FLAP_CD_FACTOR)}."
        )

    delta_f = flap_deflection_deg
    cfc = np.clip(flap_chord_ratio, 0.01, 0.50)

    # --- 2-D section flap effectiveness (figure 6.1.1.1-39A) ---
    cl_delta_theory = table_lookup(cfc, _CFC_39A, _CLDELTA_39A)

    # --- Empirical correction K' (figure 6.1.1.1-40) ---
    abs_delta = abs(delta_f)
    if abs_delta <= 10.0:
        k_prime = table_lookup(cfc, _CFC_40, _KPRIME_D10)
    elif abs_delta <= 20.0:
        k10 = table_lookup(cfc, _CFC_40, _KPRIME_D10)
        k20 = table_lookup(cfc, _CFC_40, _KPRIME_D20)
        t = (abs_delta - 10.0) / 10.0
        k_prime = k10 * (1 - t) + k20 * t
    elif abs_delta <= 40.0:
        k20 = table_lookup(cfc, _CFC_40, _KPRIME_D20)
        k40 = table_lookup(cfc, _CFC_40, _KPRIME_D40)
        t = (abs_delta - 20.0) / 20.0
        k_prime = k20 * (1 - t) + k40 * t
    else:
        k40 = table_lookup(cfc, _CFC_40, _KPRIME_D40)
        k60 = table_lookup(cfc, _CFC_40, _KPRIME_D60)
        t = np.clip((abs_delta - 40.0) / 20.0, 0.0, 1.0)
        k_prime = k40 * (1 - t) + k60 * t

    # Effective section Cl_delta
    cl_delta_section = cl_delta_theory * k_prime  # per radian

    # --- Change in zero-lift angle (section) ---
    delta_alpha_0_section = -cl_delta_section * np.radians(delta_f) / cl_alpha_per_rad
    delta_alpha_0_deg = np.degrees(delta_alpha_0_section) if cl_alpha_per_rad > 0 else 0.0

    # --- Spanwise correction K_b (figure 6.1.4.1-15) ---
    eta_i = flap_span_inboard / wing_semi_span if wing_semi_span > 0 else 0.0
    eta_o = flap_span_outboard / wing_semi_span if wing_semi_span > 0 else 1.0

    # Select K_b table based on taper ratio
    if wing_taper_ratio <= 0.25:
        kb_tab = _KB_TAPER0
    elif wing_taper_ratio <= 0.75:
        kb_tab = _KB_TAPER05
    else:
        kb_tab = _KB_TAPER1

    kb_o = table_lookup(eta_o, _ETA_KB, kb_tab)
    kb_i = table_lookup(eta_i, _ETA_KB, kb_tab)
    k_b = kb_o - kb_i

    # --- Incremental lift ---
    # delta_CL = Cl_delta * K' * delta_f * K_b * (S_flapped/S_ref)
    if s_flapped is None:
        # Estimate flapped area as fraction of total planform
        s_flapped = s_ref * k_b  # approximate

    delta_cl = (cl_delta_section * np.radians(delta_f) * k_b *
                s_flapped / s_ref)

    # Sign convention: positive deflection = positive lift increment
    # (already handled by delta_f sign)

    # --- Incremental drag ---
    cd_factor = _FLAP_CD_FACTOR.get(flap_type, 0.0023)
    # delta_CD ~ factor * delta_f^2 * (S_flapped/S_ref) for plain/split flaps
    delta_cd = cd_factor * (delta_f * DEG) ** 2 * s_flapped / s_ref

    # --- Incremental moment ---
    # delta_CM ~ -delta_CL * (x_hinge/c - x_ac/c)
    # Flap hinge is aft of AC, so moment is nose-down for positive CL increment
    moment_arm = x_flap_hinge_over_c - 0.25  # relative to AC at quarter-chord
    delta_cm = -delta_cl * moment_arm

    return FlapResult(
        delta_cl=delta_cl,
        delta_cd=delta_cd,
        delta_cm=delta_cm,
        delta_alpha_0_deg=delta_alpha_0_deg,
        cl_delta_section=cl_delta_section,
        k_prime=k_prime,
        k_b=k_b,
    )
