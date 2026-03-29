"""
Wing-body interference and combination.

Translated from:

* ``src/wblift.f``  -- SUBROUTINE WBLIFT  (wing-body lift)
* ``src/wbdrag.f``  -- SUBROUTINE WBDRAG  (wing-body drag)
* ``src/wbcm.f``    -- SUBROUTINE WBCM    (wing-body pitching moment)

Physics
-------
When a wing is mounted on a body, each component modifies the flow
around the other.  DATCOM accounts for this with multiplicative
interference factors:

**Lift:**
    CL_alpha_WB = CL_alpha_body + [K_W(B) + K_B(W)] * CL_alpha_wing

    where K_W(B) is the ratio of wing lift in the presence of the body
    to wing-alone lift (figure 4.3.1.2-10A), and K_B(W) is the ratio
    of body lift due to the wing to wing-alone lift (figure 4.3.1.2-10B).
    Both are functions of the body-diameter-to-wing-span ratio d/b.

**Drag:**
    CD0_WB = (CD0_wing + CD0_body) * R_WB

    where R_WB is the wing-body drag interference factor from
    figure 4.3.3.1-37, a function of Reynolds number and Mach.

**Moment:**
    The aerodynamic centre shifts due to the body carry-over lift.
    DATCOM uses an ellipse curve-fit between the beta*A = 0 and
    beta*A = 4 limits (figure 4.3.2.1-36B) to find the wing-body
    x_ac position.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from pydatcom.constants import PI, DEG, RAD
from pydatcom.utils import table_lookup, table_lookup_2d


# ===================================================================
# Empirical tables from FORTRAN DATA statements
# ===================================================================

# --- Figure 4.3.1.2-10A: K_W(B) vs d/b ---
_DB_TAB = np.array([0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0])
_KWB_TAB = np.array([1.0, 1.08, 1.16, 1.26, 1.36, 1.46, 1.56, 1.67, 1.78, 1.89, 2.0])

# --- Figure 4.3.1.2-10B: K_B(W) vs d/b ---
_KBW_TAB = np.array([0.0, 0.13, 0.29, 0.45, 0.62, 0.80, 1.0, 1.22, 1.45, 1.70, 2.0])

# --- Figure 4.3.1.2-12A1: wing-body incidence correction K1 ---
_K12A1_TAB = np.array([1.0, 0.97, 0.95, 0.94, 0.94, 0.94, 0.94, 0.95, 0.96, 0.98, 0.99])

# --- Figure 4.3.1.2-12A2: wing-body incidence correction K2 ---
_K12A2_TAB = np.array([0.0, 0.11, 0.21, 0.31, 0.41, 0.51, 0.60, 0.70, 0.80, 0.90, 1.0])

# --- Figure 4.3.1.2-12C: large d/b correction ---
_DB_12C = np.array([0.0, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.83, 0.9, 1.0])
_K12C_TAB = np.array([1.0, 1.0, 0.999, 0.99, 0.98, 0.965, 0.95, 0.933, 0.92, 0.92, 0.928, 0.95, 1.0])

# --- Figure 4.3.3.1-37: wing-body drag ratio R_WB ---
# Simplified to M=0.6 row (typical subsonic)
_RE_37 = np.array([
    3e6, 5e6, 7e6, 1e7, 1.5e7, 2e7, 2.5e7, 3e7, 3.5e7,
    4e7, 4.5e7, 5e7, 6e7, 7e7, 8e7, 1e8, 1.5e8, 2e8, 7e8,
])
_RWB_M06 = np.array([
    .980, .984, .989, .9965, 1.008, 1.020, 1.0325, 1.0375, 1.035,
    1.0315, 1.028, 1.023, 1.019, 1.0155, 1.015, 1.015, 1.015, 1.015, 1.015,
])

# --- Figure 4.3.2.2-21C: body carry-over AC shift ---
_RATIO_21C = np.array([
    0.0, .025, .050, .075, .10, .15, .20, .30, .40, .50, .60, .70, .80
])
_BRAC_21C = np.array([
    0.0, .056, .101, .130, .152, .190, .22, .266, .301, .33, .348, .365, .375
])


@dataclass
class WingBodyResult:
    """Combined wing-body aerodynamic coefficients.

    Attributes
    ----------
    cl_alpha_wb : float
        Wing-body lift-curve slope, per degree.
    k_wb : float
        K_W(B) interference factor (wing lift amplification by body).
    k_bw : float
        K_B(W) interference factor (body lift due to wing).
    cd0_wb : float
        Wing-body zero-lift drag coefficient.
    r_wb : float
        Wing-body drag interference ratio.
    x_ac_wb : float
        Wing-body aerodynamic centre, fraction of reference chord.
    cl_wb : np.ndarray
        Combined CL at each angle of attack.
    cd_wb : np.ndarray
        Combined CD at each angle of attack.
    cm_wb : np.ndarray
        Combined CM at each angle of attack.
    """
    cl_alpha_wb: float
    k_wb: float
    k_bw: float
    cd0_wb: float
    r_wb: float
    x_ac_wb: float
    cl_wb: np.ndarray
    cd_wb: np.ndarray
    cm_wb: np.ndarray


def wing_body_aero(
    cl_alpha_wing_deg: float,
    cl_alpha_body_deg: float,
    cd0_wing: float,
    cd0_body: float,
    body_diameter: float,
    wing_span: float,
    alphas_deg: np.ndarray,
    cl_wing: np.ndarray,
    cd_wing: np.ndarray,
    cl_body: np.ndarray,
    cd_body: np.ndarray,
    cm_body: np.ndarray,
    reynolds: float = 1e7,
    mach: float = 0.3,
    wing_incidence_deg: float = 0.0,
    x_ac_wing_over_cbar: float = 0.25,
    s_ref: float = 1.0,
    cbar: float = 1.0,
    x_cg: float = 0.0,
    x_wing: float = 0.0,
) -> WingBodyResult:
    r"""Compute combined wing-body aerodynamic coefficients.

    Translated from SUBROUTINES WBLIFT, WBDRAG, and WBCM.

    Parameters
    ----------
    cl_alpha_wing_deg : float
        Wing-alone lift-curve slope, per degree.
    cl_alpha_body_deg : float
        Body-alone lift-curve slope (CN_alpha), per degree.
    cd0_wing : float
        Wing-alone zero-lift drag coefficient.
    cd0_body : float
        Body-alone zero-lift drag coefficient.
    body_diameter : float
        Maximum body diameter, ft.
    wing_span : float
        Total wing span (= 2 * semi-span), ft.
    alphas_deg : np.ndarray
        Angles of attack, degrees.
    cl_wing, cd_wing : np.ndarray
        Wing-alone CL and CD at each alpha.
    cl_body, cd_body, cm_body : np.ndarray
        Body-alone CL, CD, CM at each alpha.
    reynolds : float
        Reynolds number based on body length.
    mach : float
        Free-stream Mach number.
    wing_incidence_deg : float
        Wing incidence angle relative to body axis, degrees.
    x_ac_wing_over_cbar : float
        Wing AC position as fraction of MAC.
    s_ref : float
        Reference area, ft^2.
    cbar : float
        Reference chord, ft.
    x_cg : float
        CG position, ft from nose.
    x_wing : float
        Wing leading-edge position, ft from nose.

    Returns
    -------
    WingBodyResult
    """
    # Body-diameter-to-wing-span ratio
    ratio = body_diameter / wing_span if wing_span > 0 else 0.0

    # --- Lift interference factors ---
    if ratio <= 0.80:
        # Standard interference factors (figures 4.3.1.2-10A and 10B)
        k_wb = table_lookup(ratio, _DB_TAB, _KWB_TAB)
        k_bw = table_lookup(ratio, _DB_TAB, _KBW_TAB)

        # Wing-body CL_alpha
        cl_alpha_wb_deg = cl_alpha_body_deg + (k_wb + k_bw) * cl_alpha_wing_deg
    else:
        # Large d/b: use figure 4.3.1.2-12C
        k12c = table_lookup(ratio, _DB_12C, _K12C_TAB)
        k_wb = k12c
        k_bw = 0.0
        cl_alpha_wb_deg = k12c * cl_alpha_wing_deg

    # Incidence corrections (figures 4.3.1.2-12A1 and 12A2)
    if wing_incidence_deg != 0.0 and ratio <= 0.80:
        k1 = table_lookup(ratio, _DB_TAB, _K12A1_TAB)
        k2 = table_lookup(ratio, _DB_TAB, _K12A2_TAB)
    else:
        k1 = 1.0
        k2 = 0.0

    # --- Drag interference ---
    r_wb = table_lookup(reynolds, _RE_37, _RWB_M06)
    cd0_wb = (cd0_wing + cd0_body) * r_wb

    # --- Aerodynamic centre ---
    # Body carry-over correction (figure 4.3.2.2-21C)
    brac = table_lookup(ratio, _RATIO_21C, _BRAC_21C)
    x_ac_wb = x_ac_wing_over_cbar + brac * ratio

    # --- Alpha loop ---
    n = len(alphas_deg)
    cl_wb = np.zeros(n)
    cd_wb = np.zeros(n)
    cm_wb = np.zeros(n)

    for j in range(n):
        # Wing-body lift (WBLIFT: BW(J+20) = BODY(J+20) + (WB(2)+WB(3))*CLINT)
        cl_wb[j] = cl_body[j] + (k_wb + k_bw) * cl_wing[j]

        # Wing-body drag (WBDRAG: BW(J) = WB(17) + BD(J+214) + D(J+35))
        cd_lift_body = cd_body[j] - cd0_body
        cd_lift_wing = cd_wing[j] - cd0_wing
        cd_wb[j] = cd0_wb + cd_lift_body + cd_lift_wing

        # Wing-body moment
        # Simple combination: body moment + wing CL * (x_cg - x_ac_wb)/cbar
        arm = (x_cg - (x_wing + x_ac_wb * cbar)) / cbar if cbar > 0 else 0.0
        cm_wb[j] = cm_body[j] + cl_wing[j] * (k_wb + k_bw) * arm

    return WingBodyResult(
        cl_alpha_wb=cl_alpha_wb_deg,
        k_wb=k_wb,
        k_bw=k_bw,
        cd0_wb=cd0_wb,
        r_wb=r_wb,
        x_ac_wb=x_ac_wb,
        cl_wb=cl_wb,
        cd_wb=cd_wb,
        cm_wb=cm_wb,
    )
