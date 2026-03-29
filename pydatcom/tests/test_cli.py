"""Tests for the CLI entry point."""

import json
from pathlib import Path

import pytest

from pydatcom.cli import main


SPROB_PATH = str(Path(__file__).parent.parent.parent / "data" / "sprob.in")


class TestAtmos:
    def test_sea_level(self, capsys):
        main(["atmos", "0"])
        out = capsys.readouterr().out
        assert "518.67" in out  # sea-level temperature
        assert "Speed of sound" in out

    def test_high_altitude(self, capsys):
        main(["atmos", "35000"])
        out = capsys.readouterr().out
        assert "35000.0 ft" in out

    def test_negative_altitude(self, capsys):
        main(["atmos", "-1000"])
        out = capsys.readouterr().out
        assert "-1000.0 ft" in out


class TestParse:
    @pytest.mark.skipif(not Path(SPROB_PATH).exists(), reason="sprob.in not found")
    def test_parse_outputs_json(self, capsys):
        main(["parse", SPROB_PATH])
        out = capsys.readouterr().out
        data = json.loads(out)
        assert isinstance(data, list)
        assert len(data) >= 1
        assert "case_id" in data[0]

    @pytest.mark.skipif(not Path(SPROB_PATH).exists(), reason="sprob.in not found")
    def test_parse_has_namelists(self, capsys):
        main(["parse", SPROB_PATH])
        out = capsys.readouterr().out
        data = json.loads(out)
        assert "FLTCON" in data[0]["namelists"]


class TestRun:
    @pytest.mark.skipif(not Path(SPROB_PATH).exists(), reason="sprob.in not found")
    def test_run_produces_output(self, capsys):
        main(["run", SPROB_PATH])
        out = capsys.readouterr().out
        assert "CASE 1" in out
        assert "Mach" in out


class TestVersion:
    def test_version(self, capsys):
        with pytest.raises(SystemExit) as exc:
            main(["--version"])
        assert exc.value.code == 0
        out = capsys.readouterr().out
        assert "pydatcom" in out


class TestNoArgs:
    def test_no_args_shows_help(self, capsys):
        with pytest.raises(SystemExit) as exc:
            main([])
        assert exc.value.code == 0
        out = capsys.readouterr().out
        assert "pydatcom" in out.lower() or "usage" in out.lower() or "PyDATCOM" in out
