"""Tests for DATCOM input file parser."""

import pytest

from pydatcom.input_parser import parse_datcom_input, DatcomCase


SIMPLE_INPUT = """\
 $FLTCON NMACH=1.0,MACH(1)=0.60,NALPHA=5.,ALSCHD(1)=-2.0,0.0,2.0,4.0,8.0,
  RNNUB(1)=4.28E6$
 $OPTINS SREF=8.85,CBARR=2.46,BLREF=4.28$
 $SYNTHS XCG=4.14,ZCG=-0.20$
CASEID SIMPLE TEST CASE
SAVE
NEXT CASE
"""

BODY_INPUT = """\
 $BODY NX=10.0,
  X(1)=0.0,0.258,0.589,1.26,2.26,2.59,2.93,3.59,4.57,6.26,
  S(1)=0.0,0.080,0.160,0.323,0.751,0.883,0.939,1.032,1.032,1.032$
 $BODY BNOSE=1.,BLN=2.59,BLA=3.67$
CASEID BODY CASE
NEXT CASE
"""

MULTI_CASE_INPUT = """\
 $FLTCON NMACH=1.0,MACH(1)=0.60$
 $OPTINS SREF=2.25$
CASEID CASE 1
SAVE
NEXT CASE
 $FLTCON NMACH=2.0,MACH(1)=0.90,1.40$
CASEID CASE 2
NEXT CASE
"""

BOOLEAN_INPUT = """\
 $FLTCON HYPERS=.TRUE.$
 $SYNTHS VERTUP=.FALSE.$
CASEID BOOL TEST
NEXT CASE
"""

REPEAT_INPUT = """\
 $VTSCHR CLALPA(1)=2*0.141$
CASEID REPEAT TEST
NEXT CASE
"""


class TestSimpleParsing:
    def test_parses_one_case(self):
        cases = parse_datcom_input(SIMPLE_INPUT)
        assert len(cases) >= 1

    def test_case_id(self):
        cases = parse_datcom_input(SIMPLE_INPUT)
        assert cases[0].case_id == "SIMPLE TEST CASE"

    def test_fltcon_mach(self):
        cases = parse_datcom_input(SIMPLE_INPUT)
        assert "FLTCON" in cases[0].namelists
        assert cases[0].namelists["FLTCON"]["NMACH"] == pytest.approx(1.0)
        assert cases[0].namelists["FLTCON"]["MACH"] == pytest.approx(0.60)

    def test_optins(self):
        cases = parse_datcom_input(SIMPLE_INPUT)
        assert cases[0].namelists["OPTINS"]["SREF"] == pytest.approx(8.85)
        assert cases[0].namelists["OPTINS"]["CBARR"] == pytest.approx(2.46)

    def test_synths(self):
        cases = parse_datcom_input(SIMPLE_INPUT)
        assert cases[0].namelists["SYNTHS"]["XCG"] == pytest.approx(4.14)
        assert cases[0].namelists["SYNTHS"]["ZCG"] == pytest.approx(-0.20)

    def test_save_control(self):
        cases = parse_datcom_input(SIMPLE_INPUT)
        assert "SAVE" in cases[0].controls

    def test_alpha_array(self):
        cases = parse_datcom_input(SIMPLE_INPUT)
        alschd = cases[0].namelists["FLTCON"]["ALSCHD"]
        assert isinstance(alschd, list)
        assert len(alschd) == 5
        assert alschd[0] == pytest.approx(-2.0)
        assert alschd[4] == pytest.approx(8.0)

    def test_scientific_notation(self):
        cases = parse_datcom_input(SIMPLE_INPUT)
        rnnub = cases[0].namelists["FLTCON"]["RNNUB"]
        assert rnnub == pytest.approx(4.28e6)


class TestBodyNamelist:
    def test_merged_body_groups(self):
        cases = parse_datcom_input(BODY_INPUT)
        body = cases[0].namelists["BODY"]
        assert body["NX"] == pytest.approx(10.0)
        assert body["BNOSE"] == pytest.approx(1.0)
        assert body["BLN"] == pytest.approx(2.59)

    def test_body_arrays(self):
        cases = parse_datcom_input(BODY_INPUT)
        body = cases[0].namelists["BODY"]
        assert isinstance(body["X"], list)
        assert len(body["X"]) == 10
        assert body["X"][0] == pytest.approx(0.0)


class TestMultiCase:
    def test_two_cases(self):
        cases = parse_datcom_input(MULTI_CASE_INPUT)
        assert len(cases) >= 2

    def test_second_case_inherits(self):
        cases = parse_datcom_input(MULTI_CASE_INPUT)
        # Second case should still have OPTINS from first case
        assert "OPTINS" in cases[1].namelists

    def test_second_case_overrides(self):
        cases = parse_datcom_input(MULTI_CASE_INPUT)
        assert cases[1].namelists["FLTCON"]["NMACH"] == pytest.approx(2.0)


class TestBooleans:
    def test_true(self):
        cases = parse_datcom_input(BOOLEAN_INPUT)
        assert cases[0].namelists["FLTCON"]["HYPERS"] is True

    def test_false(self):
        cases = parse_datcom_input(BOOLEAN_INPUT)
        assert cases[0].namelists["SYNTHS"]["VERTUP"] is False


class TestRepeatNotation:
    def test_fortran_repeat(self):
        cases = parse_datcom_input(REPEAT_INPUT)
        clalpa = cases[0].namelists["VTSCHR"]["CLALPA"]
        assert isinstance(clalpa, list)
        assert len(clalpa) == 2
        assert clalpa[0] == pytest.approx(0.141)
        assert clalpa[1] == pytest.approx(0.141)
