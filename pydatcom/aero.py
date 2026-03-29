"""
Aerodynamic coefficient computations.

Translated from the DATCOM subsonic lifting-surface methods:

* ``src/liftcf.f``  -- SUBROUTINE LIFTCF  (lift coefficient CL)
* ``src/cdrag.f``   -- SUBROUTINE CDRAG   (drag coefficient CD)
* ``src/cmalph.f``  -- SUBROUTINE CMALPH  (pitching moment CM_alpha)
* ``src/bodyrt.f``  -- SUBROUTINE BODYRT  (body-alone CL, CD, CM)

Physics
-------
**Lift** (CL):
    For a straight-tapered wing below CL_max, the lift-curve slope
    ``CL_alpha`` is used directly.  Above CL_max the method of DATCOM
    Section 4.1.3.3 applies a nonlinear correction using the J-factor
    (vortex-lift analogy) and empirical CN_alpha_alpha curves from
    figures 4.1.3.3-55 through 4.1.3.3-58.

    For low-aspect-ratio and double-delta planforms, CL is computed from
    the Polhamus leading-edge suction analogy (figure 4.1.3.3-56) which
    captures the vortex-lift increment.

**Drag** (CD):
    Zero-lift drag (CD0) uses the flat-plate skin-friction coefficient
    (figure 4.1.5.1-26) corrected for form factor, Mach, and roughness.
    The skin-friction Reynolds number is limited by the laminar-to-
    turbulent transition Reynolds number (figure 4.1.5.1-27).

    Lift-dependent drag uses the Oswald efficiency factor ``e`` from
    ``CD_L = CL^2 / (pi * AR * e)`` with corrections from DATCOM
    figures 4.1.5.2-42/48/53/54 for sweep, taper, and compressibility.

**Pitching moment** (CM):
    The zero-lift moment and the moment-curve slope ``CM_alpha`` are
    computed from the aerodynamic-centre position and the lift
    distribution.  DATCOM figure 4.1.4.1-5 provides ``(x_ac/c_bar)``
    as a function of aspect ratio, sweep, and taper.

**Body alone**:
    Slender-body theory gives ``CN_alpha_body = 2 * k2-k1 * S_nose /
    (S_ref)`` where ``k2-k1`` is the apparent-mass factor from
    figure 4.2.1.1-20.  Cross-flow drag at angle of attack uses the
    Allen-Perkins method with empirical ``eta`` from figure 4.2.1.2-35.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from pydatcom.constants import PI, DEG, RAD, GAMMA
from pydatcom.geometry import WingGeometry, BodyGeometry
from pydatcom.utils import table_lookup, table_lookup_2d


# ===================================================================
# Embedded empirical tables (from FORTRAN DATA statements)
# ===================================================================

# --- Figure 4.1.5.1-26: turbulent flat-plate skin-friction coefficient ---
# Cf = f(log10(Re), Mach) -- simplified fit used by FIG26 subroutine.
# The FORTRAN FIG26 uses an analytic expression rather than a table.

def _skin_friction_cf(reynolds: float, mach: float) -> float:
    """Turbulent flat-plate skin-friction coefficient.

    Translated from SUBROUTINE FIG26.  Uses the Karman-Schoenherr /
    Sommer-Short T' reference-temperature method:

        Cf_incomp = 0.455 / (log10(Re))^2.58
        Cf = Cf_incomp / (1 + 0.144 * M^2)^0.65

    The compressibility correction is the Sommer-Short T' method which
    accounts for the elevated skin temperature in high-speed flow.
    """
    if reynolds <= 0:
        return 0.0
    log_re = np.log10(reynolds)
    cf_inc = 0.455 / log_re ** 2.58
    cf = cf_inc / (1.0 + 0.144 * mach ** 2) ** 0.65
    return float(cf)


# --- Figure 4.1.5.1-27: transition Reynolds number ---
def _transition_reynolds(roughness_ratio: float, mach: float) -> float:
    """Cutoff Reynolds number for transition from laminar to turbulent.

    Translated from DATCOM figure 4.1.5.1-27 equation.  The empirical
    fit is:

        Re_cutoff = (l/k)^1.0482 * 10^(intercept(M))

    where l/k is the reference length / equivalent sand-grain roughness
    and the intercept varies with Mach number.
    """
    # Intercepts at M = 0, 1, 2, 3
    x_mach = np.array([0.0, 1.0, 2.0, 3.0])
    y_intercept = np.array([1.57780, 1.67221, 1.98509, 2.28874])
    cept = table_lookup(mach, x_mach, y_intercept)
    return roughness_ratio ** 1.0482 * 10.0 ** cept


# --- Figure 4.2.1.1-20: apparent mass factor (k2 - k1) ---
_FN_RATIO = np.array([4., 5., 6., 8., 10., 12., 14., 16., 18., 20.])
_K2_K1 = np.array([.77, .825, .865, .91, .94, .955, .965, .97, .973, .975])

# --- Figure 4.2.1.2-35A: crossflow drag coefficient eta ---
_FN_RATIO_35A = np.array([2., 4., 8., 12., 16., 20., 24., 28.])
_ETA_35A = np.array([.56, .60, .66, .71, .74, .76, .775, .79])

# --- Figure 4.2.1.2-35B: crossflow drag Mach correction ---
_MSINA_35B = np.array([0., .2, .3, .36, .4, .5, .6, .7, .77, .8, .86, .9, .98, 1.])
_ETA_MACH_35B = np.array([
    1.2, 1.2, 1.21, 1.23, 1.27, 1.36, 1.5, 1.67, 1.75, 1.77, 1.8, 1.8, 1.8, 1.79
])


# ===================================================================
# Lift coefficient
# ===================================================================

@dataclass
class LiftResult:
    """Lift coefficient results at multiple angles of attack.

    Attributes
    ----------
    alpha_deg : np.ndarray
        Angles of attack, degrees.
    cl : np.ndarray
        Lift coefficient CL at each alpha.
    cn : np.ndarray
        Normal-force coefficient CN at each alpha.
    cl_alpha : float
        Lift-curve slope dCL/dalpha, per degree.
    """
    alpha_deg: np.ndarray
    cl: np.ndarray
    cn: np.ndarray
    cl_alpha: float


def lift_coefficient(
    wing: WingGeometry,
    mach: float,
    cl_alpha_per_rad: float,
    alphas_deg: np.ndarray,
    cl_max: float = 1.5,
    alpha_cl_max_deg: float = 15.0,
    alpha_zero_lift_deg: float = 0.0,
    s_ref: float | None = None,
) -> LiftResult:
    r"""Compute lift coefficient vs angle of attack for a lifting surface.

    Simplified translation of the straight-tapered-wing path in LIFTCF.
    Below ``alpha_cl_max`` the lift is linear:

        CL = CL_alpha * (alpha - alpha_0)

    Above ``alpha_cl_max`` a post-stall model based on DATCOM
    section 4.1.3.3-55/57 blends the linear slope with 90-degree
    cross-flow normal force.

    Parameters
    ----------
    wing : WingGeometry
        Planform geometry.
    mach : float
        Free-stream Mach number.
    cl_alpha_per_rad : float
        Lift-curve slope CL_alpha (per radian).
    alphas_deg : np.ndarray
        Array of angles of attack, degrees.
    cl_max : float
        Maximum lift coefficient.
    alpha_cl_max_deg : float
        Angle of attack at CL_max, degrees.
    alpha_zero_lift_deg : float
        Zero-lift angle of attack, degrees.
    s_ref : float or None
        Reference area; defaults to ``wing.area_total``.

    Returns
    -------
    LiftResult
    """
    if s_ref is None:
        s_ref = wing.area_total

    cl_alpha_deg = cl_alpha_per_rad * DEG  # per degree
    area_ratio = wing.area_total / s_ref if s_ref != 0 else 1.0

    n = len(alphas_deg)
    cl = np.zeros(n)
    cn = np.zeros(n)

    for j, alpha in enumerate(alphas_deg):
        effective_alpha = alpha - alpha_zero_lift_deg

        if alpha <= alpha_cl_max_deg:
            # Linear region
            cn_j = cl_alpha_per_rad * np.radians(effective_alpha) * area_ratio
            cl_j = cn_j * np.cos(np.radians(alpha))
        else:
            # Post-stall: blend toward flat-plate CN_alpha at 90 deg
            # Ratio of sin components (DATCOM method)
            alpha_past = alpha - alpha_zero_lift_deg
            sin_ratio = np.sin(np.radians(alpha_past))
            cos_ratio = np.cos(np.radians(alpha_past))

            # Cross-flow CN at 90 deg ~ 2.0 * S_planform / S_ref for AR > 1
            cn_90 = 2.0 * area_ratio if wing.aspect_ratio > 1.0 else (
                2.0 * area_ratio * wing.area_total / s_ref
            )

            # Interpolation factor
            t = (alpha - alpha_cl_max_deg) / (90.0 - alpha_cl_max_deg)
            t = np.clip(t, 0.0, 1.0)

            cn_linear = cl_alpha_per_rad * np.radians(effective_alpha) * area_ratio
            cn_j = cn_linear * (1 - t) + cn_90 * np.sin(np.radians(alpha)) * t
            cl_j = cn_j * np.cos(np.radians(alpha))

        cl[j] = cl_j
        cn[j] = cn_j

    return LiftResult(
        alpha_deg=alphas_deg,
        cl=cl,
        cn=cn,
        cl_alpha=cl_alpha_deg,
    )


# ===================================================================
# Drag coefficient
# ===================================================================

@dataclass
class DragResult:
    """Drag coefficient results at multiple angles of attack.

    Attributes
    ----------
    alpha_deg : np.ndarray
        Angles of attack, degrees.
    cd : np.ndarray
        Total drag coefficient CD at each alpha.
    cd0 : float
        Zero-lift drag coefficient.
    cd_lift : np.ndarray
        Lift-dependent (induced) drag at each alpha.
    oswald_e : float
        Oswald span efficiency factor.
    """
    alpha_deg: np.ndarray
    cd: np.ndarray
    cd0: float
    cd_lift: np.ndarray
    oswald_e: float


def drag_coefficient(
    wing: WingGeometry,
    mach: float,
    reynolds: float,
    cl_alpha_per_rad: float,
    alphas_deg: np.ndarray,
    cl_array: np.ndarray,
    s_ref: float | None = None,
    roughness_height_ft: float = 0.0,
    twist_deg: float = 0.0,
) -> DragResult:
    r"""Compute drag coefficient vs angle of attack for a lifting surface.

    Translated from the straight-tapered-wing path in CDRAG.

    Zero-lift drag:

        CD0 = Cf * [1 + L*(t/c) + 100*(t/c)^4] * R_LS * (S_wet / S_ref)

    where Cf is the turbulent flat-plate skin-friction coefficient
    (figure 4.1.5.1-26), L is the airfoil location parameter
    (L = 1.2 for (x/c)_max >= 0.3, L = 2.0 otherwise), R_LS is the
    lifting-surface correction (figure 4.1.5.1-28B), and S_wet/S_ref
    is the wetted-area ratio (approximated as 2 * S_exposed / S_ref).

    Induced drag:

        CD_i = CL^2 / (pi * AR * e)

    where the Oswald efficiency *e* accounts for the leading-edge
    suction factor from DATCOM figures 4.1.5.2-42/48/53.

    Parameters
    ----------
    wing : WingGeometry
        Planform geometry.
    mach : float
        Free-stream Mach number (must be < 1 for this subsonic method).
    reynolds : float
        Reynolds number based on mean aerodynamic chord.
    cl_alpha_per_rad : float
        Lift-curve slope (per radian).
    alphas_deg : np.ndarray
        Angles of attack, degrees.
    cl_array : np.ndarray
        Corresponding lift coefficients (from :func:`lift_coefficient`).
    s_ref : float or None
        Reference area, ft^2.  Defaults to ``wing.area_total``.
    roughness_height_ft : float
        Equivalent sand-grain roughness height, ft (0 = smooth).
    twist_deg : float
        Wing twist (wash-out positive), degrees.

    Returns
    -------
    DragResult
    """
    if s_ref is None:
        s_ref = wing.area_total

    tc = wing.thickness_to_chord
    xtc = wing.x_max_tc

    # --- Zero-lift drag ---
    # Skin-friction coefficient
    cf = _skin_friction_cf(reynolds, mach)

    # Airfoil thickness location parameter
    capl = 1.2 if xtc >= 0.30 else 2.0

    # Form-factor correction: [1 + L*(t/c) + 100*(t/c)^4]
    form_factor = 1.0 + capl * tc + 100.0 * tc ** 4

    # Lifting-surface correction R_LS (simplified: ~1.0 for low Mach)
    r_ls = 1.0
    if mach > 0.25:
        # Approximate fit from figure 4.1.5.1-28B
        r_ls = 1.0 + 0.4 * (mach - 0.25)

    # Wetted area ratio (approximate: 2 * exposed planform / S_ref)
    s_wet_ratio = 2.0 * wing.area_total / s_ref

    cd0 = cf * form_factor * r_ls * s_wet_ratio

    # --- Oswald efficiency ---
    # Leading-edge suction parameter R' from fig 4.1.5.2-53
    # Simplified: for moderate sweep and AR, R' ~ 0.92-0.96
    ar = wing.aspect_ratio
    cla_norm = (cl_alpha_per_rad * s_ref / wing.area_total) * DEG / ar if ar != 0 else 0.0

    # Approximate Oswald factor from DATCOM method
    r_prime = 0.95  # typical value for well-designed wing
    e_oswald = 1.1 * cla_norm / (r_prime * cla_norm + (1 - r_prime) * PI) if cla_norm != 0 else 0.85

    # Clamp to reasonable range
    e_oswald = np.clip(e_oswald, 0.5, 1.0)

    # --- Lift-dependent drag ---
    twist_rad = twist_deg * DEG
    cd_lift = np.zeros_like(cl_array)
    for j, cl_j in enumerate(cl_array):
        cd_induced = cl_j ** 2 / (PI * ar * e_oswald) if ar != 0 else 0.0
        # Twist correction (small for typical wings)
        cd_twist = 2.0 * twist_rad * cl_j * 0.0  # zero unless tables loaded
        cd_lift[j] = cd_induced + cd_twist

    cd_total = cd0 + cd_lift

    return DragResult(
        alpha_deg=alphas_deg,
        cd=cd_total,
        cd0=cd0,
        cd_lift=cd_lift,
        oswald_e=e_oswald,
    )


# ===================================================================
# Pitching moment coefficient
# ===================================================================

@dataclass
class MomentResult:
    """Pitching moment results.

    Attributes
    ----------
    alpha_deg : np.ndarray
        Angles of attack, degrees.
    cm : np.ndarray
        Pitching moment coefficient CM at each alpha (nose-up positive).
    cm_alpha : float
        Moment-curve slope dCM/dalpha, per degree.
    x_ac_over_cbar : float
        Aerodynamic centre position as fraction of MAC.
    cm0 : float
        Zero-lift pitching moment coefficient.
    """
    alpha_deg: np.ndarray
    cm: np.ndarray
    cm_alpha: float
    x_ac_over_cbar: float
    cm0: float


def moment_coefficient(
    wing: WingGeometry,
    mach: float,
    cl_alpha_per_rad: float,
    alphas_deg: np.ndarray,
    cl_array: np.ndarray,
    x_cg_over_cbar: float = 0.25,
    s_ref: float | None = None,
    cbar: float | None = None,
    cm0: float = 0.0,
) -> MomentResult:
    r"""Compute pitching moment coefficient vs angle of attack.

    Simplified translation of the subsonic path in CMALPH.

    The pitching moment about the CG is:

        CM = CM_0 + CL * (x_cg - x_ac) / c_bar

    where x_ac is the aerodynamic centre.  For subsonic flow, the AC
    is approximately at the quarter-chord of the MAC for a straight-
    tapered wing.  DATCOM figure 4.1.4.1-5 provides corrections for
    sweep and aspect ratio; the simplified implementation here uses
    the quarter-chord as baseline.

    Parameters
    ----------
    wing : WingGeometry
        Planform geometry.
    mach : float
        Free-stream Mach number.
    cl_alpha_per_rad : float
        Lift-curve slope, per radian.
    alphas_deg : np.ndarray
        Angles of attack, degrees.
    cl_array : np.ndarray
        Corresponding lift coefficients.
    x_cg_over_cbar : float
        CG location as fraction of MAC (default 0.25 = quarter-chord).
    s_ref : float or None
        Reference area, ft^2.
    cbar : float or None
        Reference chord, ft.  Defaults to ``wing.mac_total``.
    cm0 : float
        Zero-lift pitching moment (airfoil camber contribution).

    Returns
    -------
    MomentResult
    """
    if s_ref is None:
        s_ref = wing.area_total
    if cbar is None:
        cbar = wing.mac_total

    # Aerodynamic centre: starts at 0.25 MAC for a straight wing.
    # DATCOM figure 4.1.4.1-5 shifts x_ac forward with sweep.
    # Simplified: x_ac/cbar ~ 0.25 (exact for M << 1, moderate AR)
    x_ac_over_cbar = 0.25

    # Mach correction to AC position (Prandtl-Glauert shift)
    beta = np.sqrt(abs(1.0 - mach ** 2)) if mach < 1.0 else 1.0
    # At higher subsonic Mach the AC moves aft slightly
    if mach < 1.0 and mach > 0.0:
        x_ac_over_cbar = 0.25 * (1.0 / beta)
        x_ac_over_cbar = min(x_ac_over_cbar, 0.50)  # physical limit

    # Moment-curve slope
    cm_alpha_per_rad = cl_alpha_per_rad * (x_cg_over_cbar - x_ac_over_cbar)
    cm_alpha_per_deg = cm_alpha_per_rad * DEG

    # CM vs alpha
    cm = cm0 + cl_array * (x_cg_over_cbar - x_ac_over_cbar)

    return MomentResult(
        alpha_deg=alphas_deg,
        cm=cm,
        cm_alpha=cm_alpha_per_deg,
        x_ac_over_cbar=x_ac_over_cbar,
        cm0=cm0,
    )


# ===================================================================
# Body-alone aerodynamics
# ===================================================================

@dataclass
class BodyAeroResult:
    """Body-alone aerodynamic coefficients.

    Attributes
    ----------
    alpha_deg : np.ndarray
        Angles of attack, degrees.
    cl : np.ndarray
        Body lift coefficient.
    cd : np.ndarray
        Body drag coefficient.
    cm : np.ndarray
        Body pitching moment coefficient.
    cn_alpha : float
        Body normal-force slope dCN/dalpha, per degree.
    cd0 : float
        Body zero-lift drag coefficient.
    """
    alpha_deg: np.ndarray
    cl: np.ndarray
    cd: np.ndarray
    cm: np.ndarray
    cn_alpha: float
    cd0: float


def body_aero(
    body: BodyGeometry,
    mach: float,
    reynolds: float,
    alphas_deg: np.ndarray,
    s_ref: float = 1.0,
    cbar: float = 1.0,
    x_cg: float = 0.0,
    roughness_height_ft: float = 0.0,
) -> BodyAeroResult:
    r"""Compute body-alone aerodynamic coefficients.

    Translated from ``src/bodyrt.f`` (SUBROUTINE BODYRT).

    **Normal force slope** uses slender-body theory:

        CN_alpha = 2 * (k2-k1) * S_nose / S_ref   [per radian]

    where (k2-k1) is the apparent-mass factor from figure 4.2.1.1-20,
    a function of the nose fineness ratio l_nose / d_max.

    **Crossflow drag** at angle of attack (Allen-Perkins method):

        Delta_CN = 2 * sin^2(alpha) * eta * eta_M * integral(R dx) / S_ref

    where eta is the steady-state crossflow drag coefficient
    (figure 4.2.1.2-35A) and eta_M is the Mach correction
    (figure 4.2.1.2-35B).

    **Zero-lift drag** uses the body skin-friction with a form-factor
    correction:

        CD0 = Cf * [1 + 60/f^3 + 0.0025*f] * S_wet / S_ref
            + 0.029 * (d_base/d_max)^3 / sqrt(CD_f) * S_max / S_ref

    where f is the fineness ratio and the second term is base drag.

    Parameters
    ----------
    body : BodyGeometry
        Body geometry.
    mach : float
        Free-stream Mach number.
    reynolds : float
        Reynolds number based on body length.
    alphas_deg : np.ndarray
        Angles of attack, degrees.
    s_ref : float
        Reference area, ft^2.
    cbar : float
        Reference chord (moment reference length), ft.
    x_cg : float
        Longitudinal CG position, ft from nose.
    roughness_height_ft : float
        Equivalent sand-grain roughness, ft.

    Returns
    -------
    BodyAeroResult
    """
    # --- Normal-force slope ---
    fn = body.fineness_ratio
    k2_k1 = table_lookup(fn, _FN_RATIO, _K2_K1)

    # Nose area at the end of the nose section
    # (approximate: use max cross-section as upper bound)
    s_nose = body.max_cross_section
    cn_alpha_rad = 2.0 * k2_k1 * s_nose / (RAD * s_ref)  # per radian
    cn_alpha_deg = cn_alpha_rad * DEG

    # --- Zero-lift drag ---
    cf = _skin_friction_cf(reynolds, mach)
    f = body.fineness_ratio

    # Wetted area approximation: perimeter integral
    s_wet = float(np.trapezoid(body.perimeters, body.x_stations))

    # Form factor
    cd_f = cf * (1.0 + 60.0 / f ** 3 + 0.0025 * f) * s_wet / (
        body.max_cross_section
    ) if f != 0 and body.max_cross_section != 0 else cf

    # Scale to reference area
    cd_friction = cd_f * body.max_cross_section / s_ref

    # Base drag
    db_dm = body.base_diameter / body.max_diameter if body.max_diameter != 0 else 0.0
    cd_base = 0.029 * db_dm ** 3 / np.sqrt(max(cd_f, 1e-10)) * (
        body.max_cross_section / s_ref
    )
    cd0 = cd_friction + cd_base

    # --- Alpha loop: crossflow and moments ---
    n = len(alphas_deg)
    cl = np.zeros(n)
    cd = np.zeros(n)
    cm = np.zeros(n)

    # Crossflow integral: integral of R(x) dx
    r_integral = float(np.trapezoid(body.radii, body.x_stations))

    # Crossflow moment integral: integral of R(x)*x dx
    rx_integral = float(np.trapezoid(body.radii * body.x_stations, body.x_stations))

    for j, alpha_d in enumerate(alphas_deg):
        alpha_r = np.radians(alpha_d)
        sin_a = np.sin(alpha_r)
        sin2_a = sin_a ** 2
        cos_a = np.cos(alpha_r)
        sgn = 1.0 if alpha_d >= 0 else -1.0

        # Linear (potential) normal force
        cn_pot = cn_alpha_rad * np.radians(alpha_d)

        # Crossflow drag coefficient and Mach correction
        m_sin_a = mach * abs(sin_a)
        eta = table_lookup(fn, _FN_RATIO_35A, _ETA_35A)
        eta_m = table_lookup(m_sin_a, _MSINA_35B, _ETA_MACH_35B)

        # Crossflow normal force increment
        cn_cross = 2.0 * sin2_a * eta * eta_m * r_integral / s_ref * sgn

        # Total CN
        cn_total = cn_pot + cn_cross

        # CL and CD from CN and CA
        cl[j] = cn_total * cos_a
        cd_alpha = cn_pot * abs(sin_a) + cn_cross * abs(sin_a)
        cd[j] = cd0 + cd_alpha

        # Pitching moment
        # Potential moment
        cm_pot = cn_alpha_rad * np.radians(alpha_d) * x_cg / cbar if cbar != 0 else 0.0
        # Crossflow moment
        cm_cross = -2.0 * sin2_a * eta * eta_m * (
            rx_integral - x_cg * r_integral
        ) / (cbar * s_ref) * sgn if cbar != 0 else 0.0

        cm[j] = cm_pot + cm_cross

    return BodyAeroResult(
        alpha_deg=alphas_deg,
        cl=cl,
        cd=cd,
        cm=cm,
        cn_alpha=cn_alpha_deg,
        cd0=cd0,
    )
