"""Tests for the display precision setting (``mpt.configure(precision=...)``).

Precision must affect only the *displayed* numbers: the expression is still
evaluated with full precision and the macro's return value stays unrounded.
"""

import os

import pytest

import mathprint_main
from mathprint import mpt

_HERE = os.path.abspath(__file__)


@pytest.fixture(autouse=True)
def restore_precision():
    """Keep precision state isolated per test."""
    saved = dict(mathprint_main.Printer.precision_scopes)
    mathprint_main.Printer.precision_scopes.clear()
    yield
    mathprint_main.Printer.precision_scopes.clear()
    mathprint_main.Printer.precision_scopes.update(saved)


# --- The formatter ---------------------------------------------------------

@pytest.mark.parametrize("value, precision, expected", [
    (3.123123412, 4, "3.123"),
    (23.00134, 4, "23"),
    (0.00123456, 4, "0.001235"),
    (2.5, 4, "2.5"),
    (10.0, 4, "10"),
    (5, 4, "5"),
    (0.0, 4, "0"),
    (-3.14159, 3, "-3.14"),
    (123456.789, 4, "123500"),
    (1e-7, 4, "0.0000001"),
    (3.14159265, 8, "3.1415926"),
])
def test_format_number(value, precision, expected):
    assert mathprint_main.Numbers.format(value, precision) == expected


def test_format_number_ignores_bools_and_non_numbers():
    assert mathprint_main.Numbers.format(True, 4) is None
    assert mathprint_main.Numbers.format("text", 4) is None
    assert mathprint_main.Numbers.format((1, 2), 4) is None


def test_format_number_ignores_symbolic():
    sp = pytest.importorskip("sympy")
    assert mathprint_main.Numbers.format(sp.Integer(5) + sp.Integer(3), 4) is None


def test_format_number_handles_complex():
    assert mathprint_main.Numbers.format(1.234567 + 2.345678j, 4) == "1.235+2.346j"
    assert mathprint_main.Numbers.format(1.234567 - 2.345678j, 4) == "1.235-2.346j"


# --- The `precision` option ------------------------------------------------

def test_precision_option_enable_reset():
    assert mpt.configure(precision=4) == _HERE
    assert mathprint_main.Printer.precision_of(_HERE) == 4
    assert mpt.configure(precision=None) == _HERE
    assert mathprint_main.Printer.precision_of(_HERE) is None


def test_precision_scoped_to_calling_file():
    mpt.configure(precision=4)
    assert mathprint_main.Printer.precision_of(_HERE) == 4
    assert mathprint_main.Printer.precision_of(os.path.abspath("other.py")) is None


def test_precision_rejects_non_positive():
    with pytest.raises(ValueError):
        mpt.configure(precision=0)


# --- Effect on output ------------------------------------------------------

def test_default_is_full_precision(capsys):
    v = 3.123123412
    result = mpt[v + 0]
    assert capsys.readouterr().out.splitlines() == ["v + 0", "3.123123412 + 0", "3.123123412"]
    assert result == 3.123123412


def test_precision_rounds_display_but_not_the_value(capsys):
    mpt.configure(precision=4)
    v = 3.123123412
    result = mpt[v + 0]
    assert capsys.readouterr().out.splitlines() == ["v + 0", "3.123 + 0", "3.123"]
    # The actual value keeps every digit; only the display is rounded.
    assert result == 3.123123412


def test_precision_in_assignment_value_line(capsys):
    mpt.configure(precision=4)
    v = 23.00134
    mpt[r := v * 1]
    out = capsys.readouterr().out.splitlines()
    assert out == ["r := v * 1", "r := 23 * 1", "r := 23"]
    assert r == 23.00134


def test_precision_reset_restores_full_precision(capsys):
    mpt.configure(precision=4)
    mpt.configure(precision=None)
    v = 3.123123412
    mpt[v + 0]
    assert capsys.readouterr().out.splitlines() == ["v + 0", "3.123123412 + 0", "3.123123412"]


def test_precision_leaves_non_numbers_alone(capsys):
    sp = pytest.importorskip("sympy")
    mpt.configure(precision=4)

    a = sp.symbols("a")
    mpt[a + 0]
    out = capsys.readouterr().out.splitlines()
    assert out == ["a + 0", "a + 0", "a"]
