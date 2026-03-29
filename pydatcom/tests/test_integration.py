"""Integration tests: end-to-end workflows using real DATCOM input data."""

import numpy as np
import pytest
from pathlib import Path

from pydatcom.input_parser import parse_datcom_file
from pydatcom.flight_condition import flight_condition, reynolds_number
from pydatcom.geometry import WingGeometry, BodyGeometry
from pydatcom.lift_slope import compute_lift_slope
from pydatcom.aero import lift_coefficient, drag_coefficient, body_aero
from pydatcom.wing_body import wing_body_aero


SPROB_PATH = Path(__file__).parent.parent.parent / "data" / "sprob.in"


@pytest.mark.skipif(not SPROB_PATH.exists(), reason="sprob.in not found")
class TestSampleInput:
    """Parse the included sample input and run a basic analysis."""

    def test_parse_sample(self):
        cases = parse_datcom_file(SPROB_PATH)
        assert len(cases) >= 1
        assert "FLTCON" in cases[0].namelists

    def test_first_case_has_body(self):
        cases = parse_datcom_file(SPROB_PATH)
        assert "BODY" in cases[0].namelists
        body = cases[0].namelists["BODY"]
        assert "NX" in body
        assert "X" in body

    def test_first_case_mach(self):
        cases = parse_datcom_file(SPROB_PATH)
        mach = cases[0].namelists["FLTCON"]["MACH"]
        assert mach == pytest.approx(0.60)


class TestEndToEnd:
    """Full analysis pipeline: flight condition -> geometry -> aero."""

    def test_wing_body_pipeline(self):
        # Define flight condition
        fc = flight_condition(altitude_ft=0.0, mach=0.6)

        # Define wing
        wing = WingGeometry(
            chord_root=1.16,
            semi_span_i=0.0,
            semi_span_o=1.50,
            total_semi_span=1.50,
            chord_inboard=1.16,
            chord_tip=0.346,
            sweep_le_inboard_tan=1.0,  # 45 deg
            thickness_to_chord=0.06,
            x_max_tc=0.40,
        )

        # Define body
        x = np.array([0.0, .175, .322, .530, .85, 1.46, 2.50, 3.43, 3.97, 4.57])
        r = np.array([0.0, .0417, .0833, .125, .1665, .208, .208, .208, .178, .138])
        s = np.pi * r ** 2
        p = 2.0 * np.pi * r
        body = BodyGeometry(x_stations=x, cross_sections=s, perimeters=p,
                            radii=r, base_area=np.pi * 0.138 ** 2)

        # Compute lift slope
        ls = compute_lift_slope(wing, mach=0.6, sweep_half_chord_deg=30.0,
                                section_cl_alpha=2 * np.pi * 0.95)
        assert ls.cl_alpha_per_rad > 0

        # Compute Reynolds number
        re = reynolds_number(fc, wing.mac_total)
        assert re > 0

        # Define alphas
        alphas = np.array([-2., 0., 2., 4., 8., 12.])
        s_ref = 2.25
        cbar = 0.822

        # Wing aero
        w_lift = lift_coefficient(wing, mach=0.6, cl_alpha_per_rad=ls.cl_alpha_per_rad,
                                   alphas_deg=alphas, s_ref=s_ref)
        w_drag = drag_coefficient(wing, mach=0.6, reynolds=re,
                                   cl_alpha_per_rad=ls.cl_alpha_per_rad,
                                   alphas_deg=alphas, cl_array=w_lift.cl,
                                   s_ref=s_ref)

        # Body aero
        re_body = reynolds_number(fc, body.length)
        b_aero = body_aero(body, mach=0.6, reynolds=re_body,
                           alphas_deg=alphas, s_ref=s_ref, cbar=cbar)

        # Wing-body combination
        wb = wing_body_aero(
            cl_alpha_wing_deg=ls.cl_alpha_per_deg,
            cl_alpha_body_deg=b_aero.cn_alpha,
            cd0_wing=w_drag.cd0,
            cd0_body=b_aero.cd0,
            body_diameter=2 * 0.208,
            wing_span=2 * 1.50,
            alphas_deg=alphas,
            cl_wing=w_lift.cl,
            cd_wing=w_drag.cd,
            cl_body=b_aero.cl,
            cd_body=b_aero.cd,
            cm_body=b_aero.cm,
            reynolds=re_body,
            mach=0.6,
        )

        # Sanity checks
        assert wb.cl_alpha_wb > 0
        assert wb.cd0_wb > 0
        assert wb.k_wb > 1.0  # body enhances wing lift
        assert wb.cl_wb[1] == pytest.approx(0.0, abs=0.05)  # near zero at alpha=0
        assert all(wb.cd_wb > 0)
