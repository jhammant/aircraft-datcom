"""
Wing, tail, and body geometry computations.

Translated from ``src/wtgeom.f`` (SUBROUTINE WTGEOM) and ``src/bodyrt.f``
body geometry sections.

Physics
-------
DATCOM models lifting surfaces as trapezoidal planforms that may have an
inboard panel (glove/crank) and an outboard panel.  Key geometric
parameters are:

* **Aspect ratio** AR = b^2 / S_ref, where b is the span and S_ref the
  reference area.
* **Taper ratio** lambda = c_tip / c_root.
* **Sweep angles** at various chord fractions (leading edge, quarter-chord,
  half-chord, trailing edge, and maximum-thickness line).
* **Mean aerodynamic chord** (MAC) for each panel and the composite planform.

Bodies are described by a set of cross-section stations giving x-position,
cross-sectional area S(x), perimeter P(x), and equivalent radius R(x).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from pydatcom.constants import PI, DEG, RAD


# ---------------------------------------------------------------------------
# Wing / Tail geometry
# ---------------------------------------------------------------------------

@dataclass
class WingGeometry:
    r"""Compute and store wing (or tail) planform geometry.

    This class translates SUBROUTINE WTGEOM(A, AIN).  Input mirrors the
    FORTRAN ``AIN`` array entries; output mirrors the ``A`` array entries.

    The planform may consist of:
      - A single panel (no cranked/glove section) when ``semi_span_i`` is
        zero or equal to ``semi_span_o``.
      - An inboard + outboard panel when ``semi_span_i > 0``.

    Parameters
    ----------
    chord_root : float
        Root chord, ft.                            (AIN(1))
    semi_span_i : float
        Inboard panel semi-span, ft.  0 for a simple taper.  (AIN(2))
    semi_span_o : float
        Outboard panel semi-span (from root), ft.  (AIN(3))
    total_semi_span : float
        Total semi-span, ft.                       (AIN(4))
    chord_inboard : float
        Chord at the break (crank) station, ft.    (AIN(5))
    chord_tip : float
        Tip chord, ft.                             (AIN(6))
    sweep_le_inboard_tan : float
        Tangent of leading-edge sweep, inboard panel. (derived from AIN(9)
        and geometry)
    thickness_to_chord : float
        Maximum thickness-to-chord ratio (t/c).    (AIN(16))
    x_max_tc : float
        Chordwise location of max t/c (fraction of chord). (AIN(18))
    airfoil_type : str
        One of ``'straight'``, ``'double_delta'``, ``'cranked'``,
        ``'curved'``.  Maps to DATCOM WTYPE codes.

    Computed Attributes
    -------------------
    area_total : float
        Total planform area (both sides), ft^2.     (A(3))
    area_inboard : float
        Inboard panel area (one side), ft^2.        (A(1))
    area_outboard : float
        Outboard panel area (one side), ft^2.       (A(2))
    aspect_ratio : float
        Aspect ratio = b^2 / S_total.              (A(7))
    taper_ratio_inboard : float
        Inboard panel taper ratio.                  (A(25))
    taper_ratio_outboard : float
        Outboard panel taper ratio.                 (A(28))
    taper_ratio_total : float
        Overall taper ratio c_tip / c_root.         (A(27))
    mac_inboard : float
        Mean aerodynamic chord, inboard panel, ft.  (A(121))
    mac_outboard : float
        Mean aerodynamic chord, outboard panel, ft. (A(17))
    mac_total : float
        Composite mean aerodynamic chord, ft.       (A(16))
    y_mac_total : float
        Spanwise station of composite MAC, ft.      (A(31))
    """

    # --- Inputs ---
    chord_root: float
    semi_span_i: float
    semi_span_o: float
    total_semi_span: float
    chord_inboard: float
    chord_tip: float
    sweep_le_inboard_tan: float = 0.0
    thickness_to_chord: float = 0.12
    x_max_tc: float = 0.30
    airfoil_type: str = "straight"

    # --- Computed outputs (populated by __post_init__) ---
    area_inboard: float = field(init=False, default=0.0)
    area_outboard: float = field(init=False, default=0.0)
    area_total: float = field(init=False, default=0.0)
    area_exposed: float = field(init=False, default=0.0)
    aspect_ratio: float = field(init=False, default=0.0)
    aspect_ratio_inboard: float = field(init=False, default=0.0)
    taper_ratio_inboard: float = field(init=False, default=0.0)
    taper_ratio_outboard: float = field(init=False, default=0.0)
    taper_ratio_total: float = field(init=False, default=0.0)
    mac_inboard: float = field(init=False, default=0.0)
    mac_outboard: float = field(init=False, default=0.0)
    mac_total: float = field(init=False, default=0.0)
    y_mac_inboard: float = field(init=False, default=0.0)
    y_mac_outboard: float = field(init=False, default=0.0)
    y_mac_total: float = field(init=False, default=0.0)

    def __post_init__(self):
        """Translate the geometry kernel of WTGEOM.

        Raises
        ------
        ValueError
            If any chord or span is negative, or total_semi_span is zero.
        """
        if self.chord_root < 0 or self.chord_tip < 0 or self.chord_inboard < 0:
            raise ValueError("Chord lengths must be non-negative.")
        if self.total_semi_span <= 0:
            raise ValueError("total_semi_span must be positive.")
        if self.semi_span_i < 0 or self.semi_span_o < 0:
            raise ValueError("Semi-span values must be non-negative.")
        if self.semi_span_o > self.total_semi_span:
            raise ValueError(
                f"semi_span_o ({self.semi_span_o}) cannot exceed "
                f"total_semi_span ({self.total_semi_span})."
            )
        cr = self.chord_root
        si = self.semi_span_i      # AIN(2) -- 0 for single panel
        so = self.semi_span_o      # AIN(3)
        bt = self.total_semi_span  # AIN(4)
        ci = self.chord_inboard    # AIN(5) -- break chord
        ct = self.chord_tip        # AIN(6)

        # Detect single-panel (no inboard glove)
        single_panel = (si == 0.0)
        if single_panel:
            ci = cr   # AIN(5) = AIN(1) when no inboard break

        # Panel spans
        span_outer = bt - si          # A(21) = AIN(4) - AIN(2)
        span_from_root = so - si      # A(23) = AIN(3) - AIN(2)
        frac_span = span_from_root / span_outer if span_outer != 0 else 0.0  # A(19)

        # Taper ratios
        self.taper_ratio_inboard = ci / ct if ct != 0 else 1.0  # A(25)

        # Chord at the outboard-panel root station
        c_out_root = ct * (self.taper_ratio_inboard +
                           (1.0 - self.taper_ratio_inboard) * frac_span)  # A(10)

        chord_ratio_out = ci / c_out_root if c_out_root != 0 else 1.0  # A(26)
        self.taper_ratio_outboard = cr / ci if ci != 0 else 1.0  # A(28)
        self.taper_ratio_total = chord_ratio_out * self.taper_ratio_outboard  # A(27)

        # Panel areas (one side)
        self.area_inboard = (c_out_root + ci) * span_from_root     # A(1)
        self.area_outboard = (ci + cr) * si                        # A(2)
        self.area_total = self.area_inboard + self.area_outboard   # A(3)

        area_exp = (ct + ci) * span_outer                          # A(119)
        self.area_exposed = area_exp + self.area_outboard          # A(4)

        # Aspect ratios  AR = 4 * b^2 / S  (one-side convention in DATCOM)
        def _ar(span, area):
            return 4.0 * span ** 2 / area if area != 0 else 0.0

        self.aspect_ratio_inboard = _ar(span_from_root, self.area_inboard)  # A(5)
        self.aspect_ratio = _ar(so, self.area_total)                        # A(7)

        # Mean aerodynamic chords  MAC = 2c_r(1 + lam + lam^2) / (3(1 + lam))
        def _mac(c_r, lam):
            return 2.0 * c_r * (1.0 + lam + lam ** 2) / (3.0 * (1.0 + lam))

        self.mac_inboard = _mac(c_out_root, chord_ratio_out)   # A(15) -> A(121) analog
        self.mac_outboard = _mac(ci, self.taper_ratio_outboard) # A(17)
        self.mac_total = (
            (self.area_inboard * self.mac_inboard +
             self.area_outboard * self.mac_outboard) / self.area_total
            if self.area_total != 0 else 0.0
        )  # A(16)

        # Spanwise stations of MAC
        def _ymac(span, lam):
            return span * (1.0 + 2.0 * lam) / (3.0 * (1.0 + lam))

        self.y_mac_inboard = _ymac(span_from_root, chord_ratio_out)   # A(32)
        self.y_mac_outboard = (
            _ymac(si, self.taper_ratio_outboard) + span_from_root
            if not single_panel else 0.0
        )  # A(33)
        self.y_mac_total = (
            (self.area_inboard * self.y_mac_inboard +
             self.area_outboard * self.y_mac_outboard) / self.area_total
            if self.area_total != 0 else 0.0
        )  # A(31)


# ---------------------------------------------------------------------------
# Body geometry
# ---------------------------------------------------------------------------

@dataclass
class BodyGeometry:
    r"""Axisymmetric body geometry description.

    Translates the geometry-setup portions of ``src/bodyrt.f`` and the
    BODYI COMMON block.

    Parameters
    ----------
    x_stations : np.ndarray
        Longitudinal station positions, ft.  (X array in BODYIN)
    cross_sections : np.ndarray
        Cross-sectional area at each station, ft^2.  (S array)
    perimeters : np.ndarray
        Wetted perimeter at each station, ft.  (P array)
    radii : np.ndarray
        Equivalent radius at each station, ft.  (R array)
    base_area : float
        Base (aft-end) cross-sectional area, ft^2.  (DS)
    nose_type : str
        ``'conical'`` or ``'ogive'`` (affects drag estimates).

    Computed Attributes
    -------------------
    length : float
        Overall body length, ft.
    max_cross_section : float
        Maximum cross-sectional area, ft^2.
    x_max_section : float
        Station of maximum cross-section, ft.
    fineness_ratio : float
        Body length / equivalent max diameter.
    base_diameter : float
        Equivalent base diameter, ft.
    max_diameter : float
        Equivalent maximum diameter, ft.
    """

    x_stations: np.ndarray
    cross_sections: np.ndarray
    perimeters: np.ndarray
    radii: np.ndarray
    base_area: float = 0.0
    nose_type: str = "ogive"

    # Computed
    length: float = field(init=False, default=0.0)
    max_cross_section: float = field(init=False, default=0.0)
    x_max_section: float = field(init=False, default=0.0)
    fineness_ratio: float = field(init=False, default=0.0)
    base_diameter: float = field(init=False, default=0.0)
    max_diameter: float = field(init=False, default=0.0)

    def __post_init__(self):
        """Compute derived body geometry properties.

        Raises
        ------
        ValueError
            If input arrays have mismatched lengths or fewer than 2 stations.
        """
        xs = self.x_stations
        ss = self.cross_sections
        n = len(xs)
        if n < 2:
            raise ValueError("At least 2 body stations are required.")
        if len(ss) != n or len(self.perimeters) != n or len(self.radii) != n:
            raise ValueError(
                f"All body arrays must have the same length (got x={n}, "
                f"S={len(ss)}, P={len(self.perimeters)}, R={len(self.radii)})."
            )

        self.length = float(xs[-1])                       # BD(1)

        # Maximum cross-section
        idx_max = int(np.argmax(ss))
        self.x_max_section = float(xs[idx_max])           # BD(2)
        self.max_cross_section = float(ss[idx_max])       # BD(3) = BD(56)

        # Enforce minimum base area (DATCOM clamps to 30 % of Smax)
        if self.base_area <= 0.3 * self.max_cross_section:
            self.base_area = 0.3 * self.max_cross_section

        # Equivalent diameters
        self.max_diameter = np.sqrt(4.0 * self.max_cross_section / PI)   # BD(85)
        self.base_diameter = np.sqrt(4.0 * self.base_area / PI)          # BD(86)
        if self.max_diameter != 0:
            self.fineness_ratio = self.length / self.max_diameter         # BD(75)


def compute_nose_length(x_stations: np.ndarray, cross_sections: np.ndarray) -> float:
    """Estimate nose length as station where cross-section first reaches max.

    In DATCOM, the nose length is the distance from the tip to the station
    where cross-section area stops increasing monotonically.  This drives
    the ``CNA_alpha`` (normal-force slope) estimate for the body.
    """
    for i in range(1, len(cross_sections)):
        if cross_sections[i] < cross_sections[i - 1]:
            return float(x_stations[i - 1])
    return float(x_stations[-1])
