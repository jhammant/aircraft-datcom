"""Tests for interpolation and numerical utilities."""

import numpy as np
import pytest

from pydatcom.utils import (
    table_lookup,
    table_lookup_2d,
    table_lookup_3d,
    trapz,
    equal_space,
    angles_from_tan,
)


class TestTableLookup:
    def test_exact_match(self):
        x = np.array([1.0, 2.0, 3.0])
        y = np.array([10.0, 20.0, 30.0])
        assert table_lookup(2.0, x, y) == pytest.approx(20.0)

    def test_interpolation(self):
        x = np.array([0.0, 1.0])
        y = np.array([0.0, 10.0])
        assert table_lookup(0.5, x, y) == pytest.approx(5.0)

    def test_clamp_below(self):
        x = np.array([1.0, 2.0, 3.0])
        y = np.array([10.0, 20.0, 30.0])
        assert table_lookup(0.0, x, y) == pytest.approx(10.0)

    def test_clamp_above(self):
        x = np.array([1.0, 2.0, 3.0])
        y = np.array([10.0, 20.0, 30.0])
        assert table_lookup(5.0, x, y) == pytest.approx(30.0)

    def test_single_point(self):
        x = np.array([1.0])
        y = np.array([42.0])
        assert table_lookup(1.0, x, y) == pytest.approx(42.0)


class TestTableLookup2D:
    def test_corner_values(self):
        x1 = np.array([0.0, 1.0])
        x2 = np.array([0.0, 1.0])
        y = np.array([[1.0, 2.0], [3.0, 4.0]])
        assert table_lookup_2d(0.0, 0.0, x1, x2, y) == pytest.approx(1.0)
        assert table_lookup_2d(1.0, 1.0, x1, x2, y) == pytest.approx(4.0)

    def test_center_interpolation(self):
        x1 = np.array([0.0, 1.0])
        x2 = np.array([0.0, 1.0])
        y = np.array([[0.0, 0.0], [0.0, 4.0]])
        assert table_lookup_2d(0.5, 0.5, x1, x2, y) == pytest.approx(1.0)

    def test_clamping(self):
        x1 = np.array([0.0, 1.0])
        x2 = np.array([0.0, 1.0])
        y = np.array([[1.0, 2.0], [3.0, 4.0]])
        # Below range on both axes -> corner (0,0)
        assert table_lookup_2d(-1.0, -1.0, x1, x2, y) == pytest.approx(1.0)


class TestTableLookup3D:
    def test_corner(self):
        x1 = np.array([0.0, 1.0])
        x2 = np.array([0.0, 1.0])
        x3 = np.array([0.0, 1.0])
        y = np.zeros((2, 2, 2))
        y[1, 1, 1] = 8.0
        assert table_lookup_3d(1.0, 1.0, 1.0, x1, x2, x3, y) == pytest.approx(8.0)

    def test_center(self):
        x1 = np.array([0.0, 1.0])
        x2 = np.array([0.0, 1.0])
        x3 = np.array([0.0, 1.0])
        y = np.zeros((2, 2, 2))
        y[1, 1, 1] = 8.0
        assert table_lookup_3d(0.5, 0.5, 0.5, x1, x2, x3, y) == pytest.approx(1.0)


class TestTrapz:
    def test_constant_function(self):
        x = np.array([0.0, 1.0, 2.0])
        y = np.array([3.0, 3.0, 3.0])
        assert trapz(y, x) == pytest.approx(6.0)

    def test_linear_function(self):
        x = np.array([0.0, 1.0, 2.0])
        y = np.array([0.0, 1.0, 2.0])
        assert trapz(y, x) == pytest.approx(2.0)

    def test_single_interval(self):
        x = np.array([0.0, 4.0])
        y = np.array([1.0, 3.0])
        assert trapz(y, x) == pytest.approx(8.0)


class TestEqualSpace:
    def test_output_length(self):
        x = np.array([0.0, 1.0, 3.0, 5.0])
        y = np.array([0.0, 2.0, 4.0, 6.0])
        x_eq, y_eq, dy = equal_space(x, y, n_out=10)
        assert len(x_eq) == 10
        assert len(y_eq) == 10
        assert len(dy) == 10

    def test_endpoints_preserved(self):
        x = np.array([1.0, 5.0])
        y = np.array([10.0, 50.0])
        x_eq, y_eq, _ = equal_space(x, y, n_out=5)
        assert x_eq[0] == pytest.approx(1.0)
        assert x_eq[-1] == pytest.approx(5.0)
        assert y_eq[0] == pytest.approx(10.0)
        assert y_eq[-1] == pytest.approx(50.0)


class TestAnglesFromTan:
    def test_zero(self):
        s, c, t = angles_from_tan(0.0)
        assert s == pytest.approx(0.0, abs=1e-15)
        assert c == pytest.approx(1.0)
        assert t == 0.0

    def test_45_degrees(self):
        s, c, t = angles_from_tan(1.0)
        assert s == pytest.approx(np.sin(np.pi / 4))
        assert c == pytest.approx(np.cos(np.pi / 4))
        assert t == 1.0

    def test_negative(self):
        s, c, t = angles_from_tan(-1.0)
        assert s == pytest.approx(-np.sin(np.pi / 4))
        assert t == -1.0
